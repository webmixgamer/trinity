# Agent Scheduling Feature Flow

> Automated task execution for agents using cron-style scheduling

---

## Feature Overview

The Agent Scheduling feature enables users to automate agent tasks by configuring cron-based schedules. The platform-managed scheduler (APScheduler) executes scheduled tasks by sending messages to agents at specified times.

**Important**: All scheduled executions go through the [Execution Queue System](execution-queue.md) to prevent collisions with user chat or agent-to-agent calls.

**Key Capabilities:**
- Cron expression scheduling (5-field format)
- Timezone support (UTC, EST, PST, etc.)
- Execution history tracking
- Enable/disable individual schedules
- Manual trigger for testing
- WebSocket real-time updates
- Queue-aware execution (429 on queue full)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  AgentDetail.vue (Schedules Tab)                                 │    │
│  │  └── SchedulesPanel.vue                                          │    │
│  │      ├── Schedule List (enable/disable, trigger, edit, delete)   │    │
│  │      ├── Create/Edit Modal (cron presets, timezone)              │    │
│  │      └── Execution History (expandable per schedule)             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ HTTP/REST
┌─────────────────────────────────────────────────────────────────────────┐
│                              Backend                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  routers/schedules.py                                            │    │
│  │  ├── CRUD endpoints (create, read, update, delete)               │    │
│  │  ├── Control endpoints (enable, disable, trigger)                │    │
│  │  └── Execution history endpoints                                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  services/scheduler_service.py (APScheduler)                     │    │
│  │  ├── Initialize: Load enabled schedules on startup               │    │
│  │  ├── Add/Remove jobs based on schedule state                     │    │
│  │  ├── Execute: Send message to agent via HTTP                     │    │
│  │  └── Broadcast: WebSocket events for execution status            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  database.py (SQLite)                                            │    │
│  │  ├── agent_schedules: Schedule configurations                    │    │
│  │  └── schedule_executions: Execution history                      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ HTTP POST /api/chat
┌─────────────────────────────────────────────────────────────────────────┐
│                          Agent Container                                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  agent-server.py                                                 │    │
│  │  └── Receives scheduled message, processes with Claude           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Flow Details

### 1. Create Schedule Flow

**User Action:** Click "New Schedule" → Fill form → Click "Create"

```
Frontend                          Backend                           Database
────────                          ───────                           ────────
SchedulesPanel.vue               schedules.py:94                →  database.py:1067
POST /api/agents/{name}/          create_schedule()                 create_schedule()
schedules                         validate cron expression          INSERT agent_schedules
                                  ↓
                                  scheduler_service.py:add_schedule()
                                  APScheduler.add_job()
```

**Files:**
- `src/frontend/src/components/SchedulesPanel.vue` - Schedule creation form
- `src/backend/routers/schedules.py:94-135` - create_schedule endpoint
- `src/backend/database.py:1067-1117` - db.create_schedule()
- `src/backend/services/scheduler_service.py:add_schedule()` - APScheduler job creation

### 2. Schedule Execution Flow (Automatic)

**Trigger:** APScheduler cron trigger fires

```
Scheduler                         Backend                           Agent
---------                         -------                           -----
APScheduler fires                 scheduler_service.py:169
_execute_schedule()
                                  # EXECUTION QUEUE (Added 2025-12-06)
                                  queue.create_execution(source=SCHEDULE)
                                  queue.submit() -> "running" or QueueFullError

                                  create_execution(running)    ->   agent-{name}:8000
                                  broadcast(started)                POST /api/chat
                                  |
                                  httpx.post() to agent
                                  |
                                  update_execution(success/failed)
                                  broadcast(completed)
                                  update_schedule_run_times()
                                  |
                                  queue.complete()  # Release queue slot
```

**Queue Full Handling**: If the agent's queue is full (3 pending requests), the scheduled execution fails with error "Agent queue full (N waiting), skipping scheduled execution".

**Files:**
- `src/backend/services/scheduler_service.py:169-401` - _execute_schedule() with queue integration
- `src/backend/services/execution_queue.py` - Execution queue service (NEW)
- `src/backend/database.py:1318-1348` - create_schedule_execution()
- `src/backend/database.py:1350-1378` - update_execution_status()

### 3. Manual Trigger Flow

**User Action:** Click play button on schedule

```
Frontend                          Backend                           Agent
────────                          ───────                           ─────
SchedulesPanel.vue               schedules.py:285              →    agent-{name}:8000
POST .../trigger                  trigger_schedule()                POST /api/chat
                                  ↓
                                  scheduler_service.py:283
                                  trigger_schedule()
                                  create_execution(manual)
                                  asyncio.create_task()
```

**Files:**
- `src/frontend/src/components/SchedulesPanel.vue` - triggerSchedule() method
- `src/backend/routers/schedules.py:285-318` - trigger_schedule endpoint
- `src/backend/services/scheduler_service.py:283-319` - trigger_schedule()

### 4. Enable/Disable Flow

**User Action:** Toggle enable/disable button

```
Frontend                          Backend                           Scheduler
────────                          ───────                           ─────────
SchedulesPanel.vue               schedules.py:220/252         →    scheduler_service.py
POST .../enable or disable        enable_schedule()                 enable_schedule()
                                  disable_schedule()                disable_schedule()
                                  ↓                                 APScheduler add/remove
                                  db.set_schedule_enabled()
```

**Files:**
- `src/frontend/src/components/SchedulesPanel.vue` - toggleSchedule() method
- `src/backend/routers/schedules.py:220-285` - enable/disable endpoints
- `src/backend/services/scheduler_service.py` - enable/disable_schedule()

### 5. Delete Schedule Flow

**User Action:** Click delete → Confirm

```
Frontend                          Backend                           Database
────────                          ───────                           ────────
SchedulesPanel.vue               schedules.py:192             →    database.py:1243
DELETE .../schedules/{id}         delete_schedule()                 delete_schedule()
                                  scheduler_service.remove()        DELETE executions
                                  ↓                                 DELETE schedule
                                  db.delete_schedule()
```

**Files:**
- `src/frontend/src/components/SchedulesPanel.vue` - deleteSchedule() method
- `src/backend/routers/schedules.py:192-217` - delete_schedule endpoint
- `src/backend/services/scheduler_service.py` - remove_schedule()
- `src/backend/database.py:1243-1264` - db.delete_schedule()

### 6. View All Executions (Executions Tab)

**User Action:** Click "Executions" tab on AgentDetail.vue

```
Frontend                          Backend                           Database
────────                          ───────                           ────────
ExecutionsPanel.vue              schedules.py:334              →    database.py:1462
GET /api/agents/{name}/           get_agent_executions()            get_agent_executions()
executions?limit=100              authorization check                SELECT FROM schedule_executions
                                  ↓                                  WHERE agent_name = ?
                                  return ExecutionResponse[]         ORDER BY started_at DESC
```

**Files:**
- `src/frontend/src/components/ExecutionsPanel.vue` - loadExecutions() method
- `src/backend/routers/schedules.py:334-349` - get_agent_executions endpoint
- `src/backend/database.py:1462-1492` - db.get_agent_executions()

**Frontend Computed Stats (calculated client-side):**
- `successRate` - % of executions with status="success"
- `totalCost` - Sum of all execution costs
- `avgDuration` - Average duration_ms of completed executions

---

## API Endpoints

| Method | Path | Description | File:Line |
|--------|------|-------------|-----------|
| GET | `/api/agents/{name}/schedules` | List schedules | schedules.py:77 |
| POST | `/api/agents/{name}/schedules` | Create schedule | schedules.py:94 |
| GET | `/api/agents/{name}/schedules/{id}` | Get schedule | schedules.py:135 |
| PUT | `/api/agents/{name}/schedules/{id}` | Update schedule | schedules.py:158 |
| DELETE | `/api/agents/{name}/schedules/{id}` | Delete schedule | schedules.py:210 |
| POST | `/api/agents/{name}/schedules/{id}/enable` | Enable | schedules.py:245 |
| POST | `/api/agents/{name}/schedules/{id}/disable` | Disable | schedules.py:279 |
| POST | `/api/agents/{name}/schedules/{id}/trigger` | Manual trigger | schedules.py:313 |
| GET | `/api/agents/{name}/schedules/{id}/executions` | Execution history | schedules.py:359 |
| GET | `/api/agents/{name}/executions` | All agent executions | schedules.py:384 |
| GET | `/api/agents/{name}/executions/{id}` | Get specific execution | schedules.py:401 |
| GET | `/api/agents/scheduler/status` | Scheduler status (admin) | schedules.py:426 |

---

## Database Schema

### agent_schedules
**Location**: `src/backend/database.py:257-271`

```sql
CREATE TABLE agent_schedules (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    name TEXT NOT NULL,
    cron_expression TEXT NOT NULL,      -- "0 9 * * *" format
    message TEXT NOT NULL,               -- Task message to send
    enabled INTEGER DEFAULT 1,
    timezone TEXT DEFAULT 'UTC',
    description TEXT,
    owner_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_run_at TEXT,                    -- Last execution time
    next_run_at TEXT,                    -- Calculated next run
    FOREIGN KEY (owner_id) REFERENCES users(id)
);
```

### schedule_executions
**Location**: `src/backend/database.py:273-295`

```sql
CREATE TABLE schedule_executions (
    id TEXT PRIMARY KEY,
    schedule_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL,                -- pending, running, success, failed
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_ms INTEGER,
    message TEXT NOT NULL,               -- The message that was sent
    response TEXT,                       -- Agent's response (truncated to 10KB)
    error TEXT,                          -- Error message if failed
    triggered_by TEXT NOT NULL,          -- "schedule" or "manual"
    -- Observability fields (added 2025-11-29)
    context_used INTEGER,                -- Tokens used in context window
    context_max INTEGER,                 -- Max context window size
    cost REAL,                           -- Execution cost in USD
    tool_calls TEXT,                     -- JSON array of tool calls
    FOREIGN KEY (schedule_id) REFERENCES agent_schedules(id)
);
```

---

## WebSocket Events

Broadcast via `manager.broadcast()` for real-time UI updates:

### schedule_execution_started
**Location**: `src/backend/services/scheduler_service.py:204-210`

```json
{
  "type": "schedule_execution_started",
  "agent": "agent-name",
  "schedule_id": "abc123",
  "execution_id": "def456",
  "schedule_name": "Daily Report"
}
```

### schedule_execution_completed
**Location**: `src/backend/services/scheduler_service.py:265-274`

```json
{
  "type": "schedule_execution_completed",
  "agent": "agent-name",
  "schedule_id": "abc123",
  "execution_id": "def456",
  "status": "success",          // or "failed"
  "error": null                 // error message if failed
}
```

---

## Cron Expression Format

5-field cron format: `minute hour day month day_of_week`

| Field | Values | Example |
|-------|--------|---------|
| Minute | 0-59 | `*/15` (every 15 min) |
| Hour | 0-23 | `9` (9 AM) |
| Day | 1-31 | `*` (every day) |
| Month | 1-12 | `*` (every month) |
| Day of Week | 0-6 (Sun=0) | `1` (Monday) |

**Common Presets:**
- `0 9 * * *` - Daily at 9 AM
- `0 9 * * 1` - Weekly on Monday at 9 AM
- `0 */6 * * *` - Every 6 hours
- `*/30 * * * *` - Every 30 minutes

---

## Dependencies

**Python packages** (docker/backend/Dockerfile):
- `apscheduler==3.10.4` - Async job scheduler
- `croniter==2.0.1` - Cron expression parsing
- `pytz==2024.1` - Timezone support

---

## Related Files

| Category | File | Purpose |
|----------|------|---------|
| Backend | `src/backend/routers/schedules.py` | REST API endpoints (77-349) |
| Backend | `src/backend/services/scheduler_service.py` | APScheduler service (1-400+) |
| Backend | `src/backend/database.py` | Models & DB operations (1067-1492) |
| Backend | `src/backend/main.py` | Scheduler lifecycle initialization |
| Frontend | `src/frontend/src/components/SchedulesPanel.vue` | Schedule management UI |
| Frontend | `src/frontend/src/components/ExecutionsPanel.vue` | Execution history UI |
| Frontend | `src/frontend/src/views/AgentDetail.vue` | Tab integration |
| Docker | `docker/backend/Dockerfile` | Dependencies |

---

## Execution Observability

Each execution now tracks detailed observability data extracted from the agent's response:

### Fields Captured

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `context_used` | INTEGER | session.context_tokens | Tokens used in context window |
| `context_max` | INTEGER | session.context_window | Maximum context window size |
| `cost` | REAL | metadata.cost_usd | Cost in USD for this execution |
| `tool_calls` | TEXT | execution_log (JSON) | Array of tool calls made |

### UI Features

1. **Progress Bar**: Visual context usage indicator (green < 50%, yellow < 75%, orange < 90%, red >= 90%)
2. **Cost Display**: Formatted as `$0.0123` in execution rows
3. **Execution Detail Modal**: Click any execution to see full details:
   - Message sent
   - Response received
   - Tool calls with duration and success status
   - Error details if failed
4. **Executions Tab**: Dedicated tab on AgentDetail.vue showing:
   - All executions across all schedules
   - Summary stats (total, success rate, total cost, avg duration)
   - Sortable table view with full observability data

---

## Scheduler Service Implementation

### Initialization
**Location**: `src/backend/services/scheduler_service.py:49-72`

```python
def initialize(self):
    """Initialize the scheduler and load all enabled schedules."""
    if self._initialized:
        return

    # Create scheduler with memory job store
    jobstores = {
        'default': MemoryJobStore()
    }

    self.scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        timezone=pytz.UTC
    )

    # Load all enabled schedules from database
    schedules = db.list_all_enabled_schedules()
    for schedule in schedules:
        self._add_job(schedule)

    # Start the scheduler
    self.scheduler.start()
    self._initialized = True
    logger.info(f"Scheduler initialized with {len(schedules)} enabled schedules")
```

### Cron Parsing
**Location**: `src/backend/services/scheduler_service.py:85-106`

```python
def _parse_cron(self, cron_expression: str) -> Dict:
    """
    Parse a cron expression into APScheduler CronTrigger kwargs.

    Format: minute hour day month day_of_week
    Examples:
      - "0 9 * * *" = Every day at 9:00 AM
      - "*/15 * * * *" = Every 15 minutes
      - "0 0 * * 0" = Every Sunday at midnight
    """
    parts = cron_expression.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expression}. Expected 5 parts.")

    return {
        'minute': parts[0],
        'hour': parts[1],
        'day': parts[2],
        'month': parts[3],
        'day_of_week': parts[4]
    }
```

---

## Activity Stream Integration (NEW: Req 9.7)

**Implemented**: 2025-12-02

Schedule executions now create persistent activity records in the unified activity stream for cross-platform observability.

### Activity Tracking Flow

**Schedule Start** (`scheduler_service.py:187-198`):
```python
# Track schedule start activity
schedule_activity_id = await activity_service.track_activity(
    agent_name=schedule.agent_name,
    activity_type=ActivityType.SCHEDULE_START,
    user_id=schedule.owner_id,
    triggered_by="schedule",
    details={
        "schedule_id": schedule.id,
        "schedule_name": schedule.name,
        "cron_expression": schedule.cron_expression
    }
)
```

**Schedule Completion** (`scheduler_service.py:277-288`):
```python
# Track schedule completion
await activity_service.complete_activity(
    activity_id=schedule_activity_id,
    status="completed",
    details={
        "related_execution_id": execution.id,
        "context_used": context_used,
        "context_max": context_max,
        "cost_usd": cost,
        "tool_count": len(execution_log) if execution_log else 0
    }
)
```

**Schedule Failure** (`scheduler_service.py:303-309`):
```python
# Track schedule failure
await activity_service.complete_activity(
    activity_id=schedule_activity_id,
    status="failed",
    error=error_msg,
    details={"related_execution_id": execution.id}
)
```

### Database Records

Each schedule execution creates:
1. **schedule_executions** record (existing): Full execution details, response, error, cost, tool_calls
2. **agent_activities** record (NEW): Unified activity stream with:
   - `activity_type`: "schedule_start"
   - `related_execution_id`: Links to schedule_executions table
   - `duration_ms`: Calculated on completion
   - Parent-child relationships with tool calls (future)

### WebSocket Events

Activity events broadcast in addition to existing schedule events:
```json
{
  "type": "agent_activity",
  "agent_name": "my-agent",
  "activity_id": "uuid-123",
  "activity_type": "schedule_start",
  "activity_state": "started",
  "action": "Running: Daily Report",
  "timestamp": "2025-12-02T09:00:00.000Z",
  "details": {
    "schedule_name": "Daily Report",
    "schedule_id": "sched-456"
  }
}
```

### Query Examples

**Get all schedule activities for an agent**:
```bash
curl "http://localhost:8000/api/agents/my-agent/activities?activity_type=schedule_start&limit=20"
```

**Get schedule activity with execution details**:
```sql
SELECT a.*, se.response, se.error, se.cost, se.tool_calls
FROM agent_activities a
JOIN schedule_executions se ON a.related_execution_id = se.id
WHERE a.activity_type = 'schedule_start'
  AND a.agent_name = 'my-agent'
ORDER BY a.started_at DESC
```

**Cross-agent schedule timeline**:
```bash
curl "http://localhost:8000/api/activities/timeline?activity_types=schedule_start&start_time=2025-12-02T00:00:00"
```

### Benefits

- Unified observability across chat and schedules
- Parent-child relationships (future: tool calls within schedules)
- Cross-agent timeline queries
- Real-time WebSocket monitoring
- Full audit trail with user attribution

See: `activity-stream.md` for complete details

---

## Status
**Updated 2025-12-29** - Fixed API endpoint line numbers to match current schedules.py (post-refactoring)
**Updated 2025-12-06** - Added Execution Queue integration documentation

---

## Related Flows

- **Integrates With**:
  - Execution Queue (`execution-queue.md`) - All scheduled executions go through queue (Added 2025-12-06)
  - Activity Stream (`activity-stream.md`) - Schedule activities tracked persistently
- **Related**:
  - ~~Agent Chat~~ (`agent-chat.md` - DEPRECATED) - Chat API still uses queue; user now uses Terminal ([agent-terminal.md](agent-terminal.md))
  - MCP Orchestration (`mcp-orchestration.md`) - All three sources share the queue
