# Feature: Cleanup Service (CLEANUP-001)

## Overview
Background service that periodically recovers stuck intermediate states by marking stale executions, activities, and Redis slots as failed. Runs every 5 minutes with an immediate startup sweep.

## User Story
As a platform operator, I want stuck executions and activities to be automatically recovered so that the system does not accumulate phantom "running" states that block capacity and mislead dashboards.

## Entry Points
- **Lifecycle**: `src/backend/main.py:265-269` - Started in `lifespan()` during backend boot
- **API (status)**: `GET /api/monitoring/cleanup-status` - Admin-only status check
- **API (trigger)**: `POST /api/monitoring/cleanup-trigger` - Admin-only manual trigger

## Frontend Layer
No dedicated frontend UI. The cleanup service is a headless backend service. Status and manual triggers are available through the monitoring API endpoints (accessible via API docs or admin tools).

## Backend Layer

### Service: CleanupService
**File**: `src/backend/services/cleanup_service.py`

#### Configuration Constants (lines 23-26)
```python
CLEANUP_INTERVAL_SECONDS = 300        # 5 minutes
EXECUTION_STALE_TIMEOUT_MINUTES = 120  # SCHED-ASYNC-001: increased from 30 to support long-running tasks
ACTIVITY_STALE_TIMEOUT_MINUTES = 120   # SCHED-ASYNC-001: increased from 30 to support long-running tasks
NO_SESSION_TIMEOUT_SECONDS = 60       # Issue #106: fast-fail executions without Claude session
```

#### CleanupReport (lines 29-47)
Dataclass holding results from a single cleanup cycle:
- `stale_executions: int` - Executions marked failed (stale timeout)
- `no_session_executions: int` - Executions failed due to no Claude session (Issue #106)
- `orphaned_skipped: int` - Skipped executions finalized (Issue #106)
- `stale_activities: int` - Activities marked failed
- `stale_slots: int` - Redis slots cleaned
- `total` property: Sum of all five fields
- `to_dict()` method: Serializes for API responses

#### CleanupService class (line 48)
Singleton pattern via global `cleanup_service` instance (line 141).

**State fields**:
- `poll_interval: int` - Configurable interval (default 300s)
- `_task: Optional[asyncio.Task]` - Background asyncio task
- `_running: bool` - Service running flag
- `last_run_at: Optional[str]` - ISO timestamp of last run
- `last_report: Optional[CleanupReport]` - Results from last cycle

**Methods**:
- `start()` (line 58): Creates asyncio task for `_cleanup_loop()`, sets `_running = True`
- `stop()` (line 66): Sets `_running = False`, cancels task
- `run_cleanup()` (line 74): Single cleanup cycle (called by loop and manual trigger)
- `_cleanup_loop()` (line 114): Main loop - runs initial sweep, then sleeps `poll_interval` between cycles

### Cleanup Cycle (`run_cleanup`, lines 74-130)

Five sequential operations, each wrapped in individual try/except:

1. **Mark stale executions as failed** (lines 80-87)
   ```python
   count = db.mark_stale_executions_failed(EXECUTION_STALE_TIMEOUT_MINUTES)
   ```
   Calls `DatabaseManager.mark_stale_executions_failed()` which delegates to `ScheduleOperations.mark_stale_executions_failed()`.

2. **Fast-fail no-session executions** (lines 89-96, Issue #106)
   ```python
   count = db.mark_no_session_executions_failed(NO_SESSION_TIMEOUT_SECONDS)
   ```
   Marks `running` executions with no `claude_session_id` older than 60 seconds as failed. These are silent launch failures where the backend failed to start a Claude session.

3. **Finalize orphaned skipped executions** (lines 98-105, Issue #106)
   ```python
   count = db.finalize_orphaned_skipped_executions()
   ```
   Defensive cleanup for `skipped` executions missing `completed_at`. Sets `completed_at = started_at` and `duration_ms = 0`.

4. **Mark stale activities as failed** (lines 107-114)
   ```python
   count = db.mark_stale_activities_failed(ACTIVITY_STALE_TIMEOUT_MINUTES)
   ```
   Calls `DatabaseManager.mark_stale_activities_failed()` which delegates to `ActivityOperations.mark_stale_activities_failed()`.

5. **Cleanup stale Redis slots** (lines 116-122)
   ```python
   slot_service = get_slot_service()
   count = await slot_service.cleanup_stale_slots()
   ```
   Calls `SlotService.cleanup_stale_slots()` which scans all `agent:slots:*` keys and removes entries older than 30 minutes.

### Startup Loop (`_cleanup_loop`, lines 114-137)

```
1. Run immediate startup sweep (run_cleanup)
2. Log startup results
3. While _running:
   a. Sleep poll_interval (300s)
   b. Run cleanup cycle
   c. Handle CancelledError for graceful shutdown
```

### Lifespan Registration

**File**: `src/backend/main.py`

**Import** (line 86):
```python
from services.cleanup_service import cleanup_service
```

**Start** (lines 265-269):
```python
try:
    cleanup_service.start()
    print("Cleanup service started")
except Exception as e:
    print(f"Error starting cleanup service: {e}")
```

**Stop** (lines 300-305):
```python
try:
    cleanup_service.stop()
    print("Cleanup service stopped")
except Exception as e:
    print(f"Error stopping cleanup service: {e}")
```

### API Endpoints

**File**: `src/backend/routers/monitoring.py`

#### GET /api/monitoring/cleanup-status (lines 455-473)
- **Auth**: Admin only (`require_admin`)
- **Response**:
  ```json
  {
    "running": true,
    "interval_seconds": 300,
    "last_run_at": "2026-03-11T10:00:00Z",
    "last_report": {
      "stale_executions": 0,
      "no_session_executions": 0,
      "orphaned_skipped": 0,
      "stale_activities": 0,
      "stale_slots": 0,
      "total": 0
    }
  }
  ```

#### POST /api/monitoring/cleanup-trigger (lines 476-491)
- **Auth**: Admin only (`require_admin`)
- **Behavior**: Runs `cleanup_service.run_cleanup()` synchronously
- **Response**:
  ```json
  {
    "status": "completed",
    "report": {
      "stale_executions": 2,
      "no_session_executions": 1,
      "orphaned_skipped": 0,
      "stale_activities": 1,
      "stale_slots": 0,
      "total": 4
    }
  }
  ```

## Data Layer

### Database Operations

#### mark_stale_executions_failed (ScheduleOperations)
**File**: `src/backend/db/schedules.py:971-1013`

**SQL** (finds stale rows):
```sql
SELECT id, started_at FROM schedule_executions
WHERE status = 'running'
AND started_at < datetime('now', '-120 minutes')
```

**SQL** (updates each row):
```sql
UPDATE schedule_executions
SET status = 'failed',
    completed_at = ?,
    duration_ms = ?,
    error = 'Marked as failed by cleanup: exceeded 120-minute timeout'
WHERE id = ?
```

#### mark_no_session_executions_failed (ScheduleOperations) — Issue #106
**File**: `src/backend/db/schedules.py:1015-1055`

**SQL** (finds no-session rows):
```sql
SELECT id, started_at FROM schedule_executions
WHERE status = 'running'
AND claude_session_id IS NULL
AND started_at < datetime('now', '-60 seconds')
```

**SQL** (updates each row):
```sql
UPDATE schedule_executions
SET status = 'failed',
    completed_at = ?,
    duration_ms = ?,
    error = 'Silent launch failure: no Claude session created within 60 seconds'
WHERE id = ?
```

#### finalize_orphaned_skipped_executions (ScheduleOperations) — Issue #106
**File**: `src/backend/db/schedules.py:1057-1075`

**SQL** (single update):
```sql
UPDATE schedule_executions
SET completed_at = COALESCE(started_at, ?),
    duration_ms = 0
WHERE status = 'skipped'
AND completed_at IS NULL
```

#### mark_stale_activities_failed (ActivityOperations)
**File**: `src/backend/db/activities.py:187-225`

**SQL** (finds stale rows):
```sql
SELECT id, started_at FROM agent_activities
WHERE activity_state = 'started'
AND started_at < datetime('now', '-30 minutes')
```

**SQL** (updates each row):
```sql
UPDATE agent_activities
SET activity_state = 'failed',
    completed_at = ?,
    duration_ms = ?,
    error = 'Marked as failed by cleanup: exceeded 30-minute timeout'
WHERE id = ?
```

**Delegation chain**:
- `cleanup_service.run_cleanup()` -> `db.mark_stale_activities_failed(30)`
- `DatabaseManager.mark_stale_activities_failed()` (line 686-688) -> `self._activity_ops.mark_stale_activities_failed(30)`
- `ActivityOperations.mark_stale_activities_failed()` (line 187)

### Redis Operations

#### cleanup_stale_slots (SlotService)
**File**: `src/backend/services/slot_service.py:247-271`

**Logic**:
1. Scans all keys matching `agent:slots:*` pattern via `SCAN`
2. For each agent, calls `_cleanup_stale_slots_for_agent()` (line 223)
3. Removes ZSET entries with score (timestamp) older than 30 minutes:
   ```
   ZREMRANGEBYSCORE agent:slots:{name} -inf {cutoff_timestamp}
   ```
4. Deletes corresponding metadata keys: `agent:slot:{name}:{execution_id}`

**TTL**: `SLOT_TTL_SECONDS = 1800` (30 minutes, line 30)

## Side Effects
- **Logging**: Each cleanup cycle logs results at INFO level when resources are cleaned
- **Error Logging**: Individual operation failures logged at ERROR level without stopping other operations
- **No WebSocket Broadcasts**: Cleanup runs silently; no real-time notifications to frontend
- **No Activity Records**: Cleanup itself does not create activity entries (avoids recursion)

## Error Handling

| Error Case | Handling | Impact |
|------------|----------|--------|
| Stale execution marking fails | Logged, continues to activities/slots | Partial cleanup |
| Stale activity marking fails | Logged, continues to slots | Partial cleanup |
| Redis slot cleanup fails | Logged, cycle ends | Partial cleanup |
| Entire cleanup cycle crashes | Logged, next cycle still runs | Temporary gap |
| Service start fails | Logged in lifespan, backend starts normally | No auto-cleanup |
| CancelledError in sleep/cleanup | Loop exits gracefully | Normal shutdown |

| API Error Case | HTTP Status | Message |
|----------------|-------------|---------|
| Not admin | 403 | Access forbidden |
| Not authenticated | 401 | Not authenticated |

## Architecture Notes

### Resilience Design
- Each of the three cleanup steps is independently wrapped in try/except
- One step failing does not prevent the others from running
- The background loop survives individual cycle failures
- Backend startup is not blocked if the cleanup service fails to start

### Timeout Values
Execution and activity timeouts were increased to 120 minutes (SCHED-ASYNC-001) to support long-running scheduled tasks (10-60+ min). Redis slot TTL remains at 30 minutes since slots are released by TaskExecutionService on completion.
- Executions: `EXECUTION_STALE_TIMEOUT_MINUTES = 120`
- Activities: `ACTIVITY_STALE_TIMEOUT_MINUTES = 120`
- Slots: `SLOT_TTL_SECONDS = 1800` (30 minutes)

### No Frontend Dependency
This is a purely backend service. The only "UI" is the two admin API endpoints under `/api/monitoring/` which can be invoked via Swagger UI at `http://localhost:8000/docs`.

## Testing

### Prerequisites
- Backend running (`docker-compose up backend`)
- Redis running (`docker-compose up redis`)
- Admin credentials available

### Test Steps

1. **Verify service starts on boot**
   **Action**: Check backend startup logs
   **Expected**: Log line "Cleanup service started"
   **Verify**: `docker-compose logs backend | grep "Cleanup service started"`

2. **Check cleanup status**
   **Action**: `GET /api/monitoring/cleanup-status` with admin token
   **Expected**: Returns running=true, interval_seconds=300
   **Verify**: `last_run_at` is set (startup sweep ran)

3. **Trigger manual cleanup**
   **Action**: `POST /api/monitoring/cleanup-trigger` with admin token
   **Expected**: Returns status="completed" with report
   **Verify**: All counts are 0 if no stale resources

4. **Verify stale execution cleanup**
   **Action**: Create an execution record with `status='running'` and `started_at` > 30 min ago
   **Expected**: Next cleanup cycle marks it as `status='failed'`
   **Verify**: Check `error` field contains "Marked as failed by cleanup"

5. **Verify stale activity cleanup**
   **Action**: Create an activity with `activity_state='started'` and `started_at` > 30 min ago
   **Expected**: Next cleanup cycle marks it as `activity_state='failed'`
   **Verify**: Check `error` field contains "Marked as failed by cleanup"

## Related Flows
- [parallel-capacity.md](parallel-capacity.md) - Slot service that cleanup calls into
- [task-execution-service.md](task-execution-service.md) - Creates executions that may become stale
- [activity-stream.md](activity-stream.md) - Creates activities that may become stale
- [agent-monitoring.md](agent-monitoring.md) - Monitoring router hosts the cleanup endpoints
- [scheduler-service.md](scheduler-service.md) - Scheduler creates executions that cleanup recovers

## File Summary

| File | Role |
|------|------|
| `src/backend/services/cleanup_service.py` | Service class and global instance |
| `src/backend/db/schedules.py:971-1013` | `mark_stale_executions_failed()` |
| `src/backend/db/schedules.py:1015-1055` | `mark_no_session_executions_failed()` (Issue #106) |
| `src/backend/db/schedules.py:1057-1075` | `finalize_orphaned_skipped_executions()` (Issue #106) |
| `src/backend/db/activities.py:187-225` | `mark_stale_activities_failed()` |
| `src/backend/database.py:682-688` | Delegation methods on DatabaseManager |
| `src/backend/services/slot_service.py:247-271` | `cleanup_stale_slots()` Redis cleanup |
| `src/backend/main.py:86,265-269,300-305` | Import, start in lifespan, stop on shutdown |
| `src/backend/routers/monitoring.py:455-491` | `/cleanup-status` and `/cleanup-trigger` endpoints |
| `tests/test_cleanup_service.py` | API integration tests for cleanup (Issue #106) |
