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
- **Make Repeatable** - Create schedule from existing task execution (2026-01-12)

**Refactored (2025-12-31):**
- Access control via `AuthorizedAgent` dependency (not inline checks)
- Agent HTTP communication via `AgentClient` service (not raw httpx)

**Fixed (2025-01-02):**
- Scheduler now uses `AgentClient.task()` instead of `AgentClient.chat()` to ensure execution logs are stored in raw Claude Code `stream-json` format for proper display in the [Execution Log Viewer](execution-log-viewer.md)

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
--------                          -------                           --------
SchedulesPanel.vue               schedules.py:85                 → database.py:1067
POST /api/agents/{name}/          create_schedule()                 create_schedule()
schedules                         validate cron expression          INSERT agent_schedules
                                  ↓
                                  scheduler_service.py:510
                                  add_schedule() → _add_job()
                                  APScheduler.add_job()
```

**Files:**
- `src/frontend/src/components/SchedulesPanel.vue` - Schedule creation form
- `src/backend/routers/schedules.py:85-113` - create_schedule endpoint
- `src/backend/database.py:1067-1117` - db.create_schedule()
- `src/backend/services/scheduler_service.py:510-513` - add_schedule()
- `src/backend/services/scheduler_service.py:111-143` - _add_job() APScheduler integration

### 1b. Make Repeatable Flow (Create Schedule from Task)

**User Action:** Click calendar icon on completed task in Tasks tab → Fill remaining form fields → Click "Create"

```
Frontend                          Frontend                          Frontend
--------                          --------                          --------
TasksPanel.vue:251-261           AgentDetail.vue:583-594           SchedulesPanel.vue:790-802
User clicks calendar icon        handleCreateSchedule()            watch(initialMessage)
makeRepeatable(task)             - Set schedulePrefillMessage      - Detect new message
emit('create-schedule', msg)     - Switch to 'schedules' tab       - Pre-fill formData.message
                                                                   - Open create form modal
```

**Data Flow:**
1. User clicks calendar icon on a task row in TasksPanel.vue
2. `makeRepeatable(task)` emits `create-schedule` event with `task.message`
3. AgentDetail.vue `handleCreateSchedule(message)` handler:
   - Sets `schedulePrefillMessage` ref to the message
   - Switches `activeTab` to `'schedules'`
   - Clears prefill after 100ms delay (allows reuse)
4. SchedulesPanel.vue receives `initialMessage` prop
5. Watch on `initialMessage` (with `immediate: true`) fires:
   - Pre-fills `formData.message` with the task message
   - Resets other form fields (name, cron_expression, description, timezone)
   - Opens create form (`showCreateForm = true`)
6. User fills in schedule name, cron expression, and submits (uses same Create Schedule Flow above)

**Files:**
- `src/frontend/src/components/TasksPanel.vue:251-261` - Calendar button in action row
- `src/frontend/src/components/TasksPanel.vue:451` - `defineEmits(['create-schedule'])`
- `src/frontend/src/components/TasksPanel.vue:654-657` - `makeRepeatable(task)` function
- `src/frontend/src/views/AgentDetail.vue:84` - `@create-schedule="handleCreateSchedule"` event binding
- `src/frontend/src/views/AgentDetail.vue:148` - `:initial-message="schedulePrefillMessage"` prop
- `src/frontend/src/views/AgentDetail.vue:261` - `schedulePrefillMessage` ref
- `src/frontend/src/views/AgentDetail.vue:583-594` - `handleCreateSchedule(message)` handler
- `src/frontend/src/components/SchedulesPanel.vue:487-490` - `initialMessage` prop definition
- `src/frontend/src/components/SchedulesPanel.vue:790-802` - Watch handler for `initialMessage`

### 2. Schedule Execution Flow (Automatic)

**Trigger:** APScheduler cron trigger fires

```
Scheduler                         Backend                           Agent
---------                         -------                           -----
APScheduler fires                 scheduler_service.py:169
_execute_schedule()
                                  # EXECUTION QUEUE (Added 2025-12-06)
                                  queue.create_execution(source=SCHEDULE)

                                  # CREATE DB RECORD FIRST (Fixed 2026-01-11)
                                  # Execution record created BEFORE activity so we have
                                  # the database ID for related_execution_id linkage
                                  execution = db.create_schedule_execution()
                                  |
                                  # ACTIVITY TRACKING with related_execution_id
                                  activity_service.track_activity(
                                    related_execution_id=execution.id  # For SQL JOINs
                                  )
                                  |
                                  broadcast(started)
                                  queue.submit() -> "running" or QueueFullError
                                  |
                                  # AGENT CLIENT (Fixed 2025-01-02)
                                  client = get_agent_client(agent_name)
                                  task_response = await client.task(message)
                                  |                                 POST /api/task
                                  # Response parsing via _parse_task_response()
                                  task_response.metrics.context_used
                                  task_response.metrics.cost_usd
                                  task_response.metrics.execution_log_json  # Raw Claude Code format
                                  |
                                  update_execution(success/failed)
                                  broadcast(completed)
                                  update_schedule_run_times()
                                  |
                                  queue.complete()  # Release queue slot
```

**Note**: Changed from `client.chat()` to `client.task()` on 2025-01-02. The `/api/task` endpoint returns raw Claude Code `stream-json` format which is required for the [Execution Log Viewer](execution-log-viewer.md) to properly render execution transcripts.

**Queue Full Handling**: If the agent's queue is full (3 pending requests), the scheduled execution fails with error "Agent queue full (N waiting), skipping scheduled execution".

**Files:**
- `src/backend/services/scheduler_service.py:169-381` - _execute_schedule() with queue and AgentClient.task()
- `src/backend/services/agent_client.py:194-281` - AgentClient.task() and _parse_task_response()
- `src/backend/services/execution_queue.py` - Execution queue service
- `src/backend/database.py:1318-1348` - create_schedule_execution()
- `src/backend/database.py:1350-1378` - update_execution_status()

**Key Implementation Detail (2026-01-11):**
Execution record is created BEFORE tracking the activity (lines 206-215). This ensures we have the database execution ID available for `related_execution_id` field in the activity, enabling structured SQL queries to find all activities for a given execution.

### 3. Manual Trigger Flow

**User Action:** Click play button on schedule

```
Frontend                          Backend                           Agent
--------                          -------                           -----
SchedulesPanel.vue               schedules.py:236              →    agent-{name}:8000
POST .../trigger                  trigger_schedule()                POST /api/task
                                  ↓
                                  scheduler_service.py:382
                                  trigger_schedule()
                                  create_execution(manual)
                                  asyncio.create_task(_execute_manual_trigger)
                                  ↓
                                  scheduler_service.py:420
                                  _execute_manual_trigger()
                                  # FULL ACTIVITY TRACKING (Added 2026-01-11)
                                  activity_service.track_activity(
                                    related_execution_id=execution_id
                                  )
                                  queue.create_execution()
                                  queue.submit()
                                  client = get_agent_client(...)
                                  client.task(message)  # Uses /api/task for raw log format
                                  activity_service.complete_activity()
                                  queue.complete()
```

**Note**: Manual triggers now have full activity tracking with `related_execution_id` linkage (added 2026-01-11), matching the automatic schedule execution flow.

**Files:**
- `src/frontend/src/components/SchedulesPanel.vue` - triggerSchedule() method
- `src/backend/routers/schedules.py:236-260` - trigger_schedule endpoint
- `src/backend/services/scheduler_service.py:382-418` - trigger_schedule()
- `src/backend/services/scheduler_service.py:420-568` - _execute_manual_trigger() with queue integration and activity tracking

### 4. Enable/Disable Flow

**User Action:** Toggle enable/disable button

```
Frontend                          Backend                           Scheduler
--------                          -------                           ---------
SchedulesPanel.vue               schedules.py:200/218         →    scheduler_service.py
POST .../enable or disable        enable_schedule()                 enable_schedule():525
                                  disable_schedule()                disable_schedule():533
                                  ↓                                 APScheduler add/remove
                                  db.set_schedule_enabled()
```

**Access Control:** Uses `AuthorizedAgent` dependency - only users with agent access can toggle.

**Files:**
- `src/frontend/src/components/SchedulesPanel.vue` - toggleSchedule() method
- `src/backend/routers/schedules.py:200-233` - enable/disable endpoints with AuthorizedAgent
- `src/backend/services/scheduler_service.py:525-536` - enable/disable_schedule()

### 5. Delete Schedule Flow

**User Action:** Click delete → Confirm

```
Frontend                          Backend                           Database
--------                          -------                           --------
SchedulesPanel.vue               schedules.py:174             →    database.py:1243
DELETE .../schedules/{id}         delete_schedule()                 delete_schedule()
                                  scheduler_service.remove():515    DELETE executions
                                  ↓                                 DELETE schedule
                                  db.delete_schedule()
```

**Access Control:** Uses `CurrentUser` dependency with manual ownership check via `db.delete_schedule()`.

**Files:**
- `src/frontend/src/components/SchedulesPanel.vue` - deleteSchedule() method
- `src/backend/routers/schedules.py:174-196` - delete_schedule endpoint
- `src/backend/services/scheduler_service.py:515-517` - remove_schedule()
- `src/backend/database.py:1243-1264` - db.delete_schedule()

### 6. View All Executions (Executions Tab)

**User Action:** Click "Executions" tab on AgentDetail.vue

```
Frontend                          Backend                           Database
--------                          -------                           --------
ExecutionsPanel.vue              schedules.py:283              →    database.py:1462
GET /api/agents/{name}/           get_agent_executions()            get_agent_executions()
executions?limit=100              AuthorizedAgent dependency         SELECT FROM schedule_executions
                                  ↓                                  WHERE agent_name = ?
                                  return ExecutionResponse[]         ORDER BY started_at DESC
```

**Access Control:** Uses `AuthorizedAgent` dependency - `name: AuthorizedAgent` validates access automatically.

**Files:**
- `src/frontend/src/components/ExecutionsPanel.vue` - loadExecutions() method
- `src/backend/routers/schedules.py:283-290` - get_agent_executions endpoint with AuthorizedAgent
- `src/backend/database.py:1462-1492` - db.get_agent_executions()

**Frontend Computed Stats (calculated client-side):**
- `successRate` - % of executions with status="success"
- `totalCost` - Sum of all execution costs
- `avgDuration` - Average duration_ms of completed executions

---

## API Endpoints

| Method | Path | Description | File:Line | Access |
|--------|------|-------------|-----------|--------|
| GET | `/api/agents/{name}/schedules` | List schedules | schedules.py:78 | AuthorizedAgent |
| POST | `/api/agents/{name}/schedules` | Create schedule | schedules.py:85 | CurrentUser |
| GET | `/api/agents/{name}/schedules/{id}` | Get schedule | schedules.py:116 | AuthorizedAgent |
| PUT | `/api/agents/{name}/schedules/{id}` | Update schedule | schedules.py:132 | CurrentUser |
| DELETE | `/api/agents/{name}/schedules/{id}` | Delete schedule | schedules.py:174 | CurrentUser |
| POST | `/api/agents/{name}/schedules/{id}/enable` | Enable | schedules.py:200 | AuthorizedAgent |
| POST | `/api/agents/{name}/schedules/{id}/disable` | Disable | schedules.py:218 | AuthorizedAgent |
| POST | `/api/agents/{name}/schedules/{id}/trigger` | Manual trigger | schedules.py:236 | AuthorizedAgent |
| GET | `/api/agents/{name}/schedules/{id}/executions` | Execution history | schedules.py:265 | AuthorizedAgent |
| GET | `/api/agents/{name}/executions` | All agent executions | schedules.py:283 | AuthorizedAgent |
| GET | `/api/agents/{name}/executions/{id}` | Get specific execution | schedules.py:293 | AuthorizedAgent |
| GET | `/api/agents/{name}/executions/{id}/log` | Get execution log | schedules.py:309 | AuthorizedAgent |
| GET | `/api/agents/scheduler/status` | Scheduler status (admin) | schedules.py:354 | Admin only |

### Access Control Pattern

Endpoints use FastAPI dependencies from `src/backend/dependencies.py`:

```python
# Type aliases used in schedules router
from dependencies import AuthorizedAgent, CurrentUser

# AuthorizedAgent dependency (schedules.py:78)
@router.get("/{name}/schedules")
async def list_agent_schedules(name: AuthorizedAgent):
    # name is validated and returned by get_authorized_agent()
    # Raises 403 if user cannot access agent
    ...

# CurrentUser dependency (schedules.py:85)
@router.post("/{name}/schedules")
async def create_schedule(
    name: str,
    schedule_data: ScheduleCreate,
    current_user: User = Depends(get_current_user)
):
    # Manual check via db.create_schedule() which validates access
    ...
```

**Dependency definitions** (`src/backend/dependencies.py:168-259`):

| Dependency | Purpose | Check |
|------------|---------|-------|
| `AuthorizedAgent` | Read access to agent | `db.can_user_access_agent()` |
| `OwnedAgent` | Owner access (delete, share) | `db.can_user_share_agent()` |
| `CurrentUser` | Authenticated user | JWT/MCP key validation |

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
    started_at TEXT NOT NULL,            -- UTC timestamp with 'Z' suffix
    completed_at TEXT,                   -- UTC timestamp with 'Z' suffix
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

> **Timezone Note (2026-01-15)**: All timestamps (`started_at`, `completed_at`, `last_run_at`, `next_run_at`) are stored as UTC with 'Z' suffix. Backend uses `utc_now_iso()` from `utils/helpers.py`. See [Timezone Handling Guide](/docs/TIMEZONE_HANDLING.md).

---

## WebSocket Events

Broadcast via `scheduler_service._broadcast()` for real-time UI updates:

### schedule_execution_started
**Location**: `src/backend/services/scheduler_service.py:226-233`

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
**Location**: `src/backend/services/scheduler_service.py:305-312` (success) or `333-340` (failure)

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
- `httpx` - Async HTTP client (used by AgentClient)

---

## Agent HTTP Client Service

**Added**: 2025-12-31 (Plan 03 refactoring)

The scheduler uses `AgentClient` from `src/backend/services/agent_client.py` for all HTTP communication with agent containers. This centralizes URL construction, timeout handling, and response parsing.

### Usage in Scheduler

**Location**: `src/backend/services/scheduler_service.py:263-278`

```python
from services.agent_client import get_agent_client, AgentClientError, AgentNotReachableError

# Send task to agent using AgentClient.task() for raw log format
# Changed from client.chat() to client.task() on 2025-01-02
client = get_agent_client(schedule.agent_name)
task_response = await client.task(schedule.message)

# Update execution status with parsed response
db.update_execution_status(
    execution_id=execution.id,
    status="success",
    response=task_response.response_text,
    context_used=task_response.metrics.context_used,
    context_max=task_response.metrics.context_max,
    cost=task_response.metrics.cost_usd,
    tool_calls=task_response.metrics.tool_calls_json,
    execution_log=task_response.metrics.execution_log_json  # Raw Claude Code format
)
```

### AgentClient API

**Location**: `src/backend/services/agent_client.py`

| Method | Purpose | Timeout |
|--------|---------|---------|
| `task(message)` | Execute stateless task (raw log format) | 900s (15 min) |
| `chat(message, stream)` | Send chat message (simplified log format) | 900s (15 min) |
| `get_session()` | Get context info | 5s |
| `health_check()` | Check agent health | 5s |
| `inject_trinity_prompt()` | Inject meta-prompt | 10s |

**Important**: The scheduler uses `task()` not `chat()`. The `task()` method calls `/api/task` which returns raw Claude Code `stream-json` format required by the log viewer. The `chat()` method calls `/api/chat` which returns a simplified format that is not compatible with `parseExecutionLog()`.

### Response Models

**AgentChatResponse** (`agent_client.py:34-39`):
```python
@dataclass
class AgentChatResponse:
    response_text: str           # Agent's text response (truncated to 10KB)
    metrics: AgentChatMetrics    # Parsed observability data
    raw_response: Dict[str, Any] # Original JSON from agent
```

**AgentChatMetrics** (`agent_client.py:23-31`):
```python
@dataclass
class AgentChatMetrics:
    context_used: int            # Tokens in context window
    context_max: int             # Max context window size
    context_percent: float       # Usage percentage
    cost_usd: Optional[float]    # Execution cost
    tool_calls_json: Optional[str]      # JSON array of tool calls
    execution_log_json: Optional[str]   # Full execution transcript
```

### Error Handling

**Exceptions** (`agent_client.py:54-69`):

| Exception | Meaning | HTTP Equivalent |
|-----------|---------|-----------------|
| `AgentNotReachableError` | Connection failed or timeout | 503 Service Unavailable |
| `AgentRequestError` | Agent returned error status | 4xx/5xx from agent |
| `AgentClientError` | Base exception | General failure |

**Scheduler error handling** (`scheduler_service.py:314-340`):
```python
try:
    client = get_agent_client(schedule.agent_name)
    chat_response = await client.chat(schedule.message, stream=False)
    # ... success handling
except AgentNotReachableError as e:
    error_msg = f"Agent not reachable: {str(e)}"
    # ... failure handling with specific message
except Exception as e:
    error_msg = str(e)
    # ... generic failure handling
```

---

## Related Files

| Category | File | Purpose |
|----------|------|---------|
| Backend | `src/backend/routers/schedules.py` | REST API endpoints (78-366) |
| Backend | `src/backend/services/scheduler_service.py` | APScheduler service (1-560) |
| Backend | `src/backend/services/agent_client.py` | Agent HTTP client (NEW) |
| Backend | `src/backend/services/execution_queue.py` | Execution queue service |
| Backend | `src/backend/dependencies.py` | Access control dependencies (NEW) |
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
**Location**: `src/backend/services/scheduler_service.py:53-76`

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
**Location**: `src/backend/services/scheduler_service.py:89-109`

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
**Updated**: 2026-01-11 - `related_execution_id` now a top-level field for structured SQL queries

Schedule executions now create persistent activity records in the unified activity stream for cross-platform observability.

### Activity Tracking Flow

**Schedule Start** (`scheduler_service.py:217-231`):
```python
# Track schedule start activity WITH related_execution_id as top-level field
# Note: Execution record is created FIRST (line 206) so we have the database ID
schedule_activity_id = await activity_service.track_activity(
    agent_name=schedule.agent_name,
    activity_type=ActivityType.SCHEDULE_START,
    user_id=schedule.owner_id,
    triggered_by="schedule",
    related_execution_id=execution.id,  # Database ID - enables SQL JOINs
    details={
        "schedule_id": schedule.id,
        "schedule_name": schedule.name,
        "cron_expression": schedule.cron_expression,
        "execution_id": execution.id,  # Also in details for WebSocket events
        "queue_execution_id": queue_execution.id
    }
)
```

**Schedule Completion** (`scheduler_service.py:299-311`):
```python
# Track schedule completion
await activity_service.complete_activity(
    activity_id=schedule_activity_id,
    status="completed",
    details={
        "related_execution_id": execution.id,
        "context_used": task_response.metrics.context_used,
        "context_max": task_response.metrics.context_max,
        "cost_usd": task_response.metrics.cost_usd,
        "tool_count": len(execution_log) if execution_log else 0,
        "queue_execution_id": queue_execution.id
    }
)
```

**Schedule Failure** (`scheduler_service.py:326-332`):
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
   - ID format: `token_urlsafe(16)` - permanent, used for API and UI navigation
2. **agent_activities** record (NEW): Unified activity stream with:
   - `activity_type`: "schedule_start"
   - `related_execution_id`: Links to `schedule_executions.id` - enables structured SQL queries
   - `duration_ms`: Calculated on completion
   - Parent-child relationships with tool calls (future)

**Activity Linkage Pattern** (2026-01-11):
```sql
-- Find all activities for a given execution
SELECT * FROM agent_activities
WHERE related_execution_id = ?
ORDER BY started_at;

-- Join activities with execution details
SELECT a.*, e.status, e.cost, e.duration_ms
FROM agent_activities a
JOIN schedule_executions e ON a.related_execution_id = e.id
WHERE e.agent_name = ?;
```

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
**Updated 2026-01-15** - Added timezone handling note for UTC timestamps with 'Z' suffix
**Updated 2026-01-12** - Added "Make Repeatable" flow documentation - create schedule from existing task via calendar icon in Tasks tab
**Updated 2026-01-11** - Execution record created BEFORE activity tracking for proper `related_execution_id` linkage. Manual trigger now has full activity tracking with queue integration.
**Updated 2025-01-02** - Scheduler now uses `AgentClient.task()` instead of `AgentClient.chat()` for raw log format compatibility with execution log viewer
**Updated 2025-12-31** - Documented access control dependencies and AgentClient service (Plan 02/03 refactoring)
**Updated 2025-12-29** - Fixed API endpoint line numbers to match current schedules.py (post-refactoring)
**Updated 2025-12-06** - Added Execution Queue integration documentation

---

## Related Flows

- **Integrates With**:
  - Execution Queue (`execution-queue.md`) - All scheduled executions go through queue (Added 2025-12-06)
  - Activity Stream (`activity-stream.md`) - Schedule activities tracked persistently
- **Upstream**:
  - Tasks Tab (`tasks-tab.md`) - "Make Repeatable" button emits `create-schedule` event to pre-fill schedule creation form (Added 2026-01-12)
- **Related**:
  - ~~Agent Chat~~ (`agent-chat.md` - DEPRECATED) - Chat API still uses queue; user now uses Terminal ([agent-terminal.md](agent-terminal.md))
  - MCP Orchestration (`mcp-orchestration.md`) - All three sources share the queue
