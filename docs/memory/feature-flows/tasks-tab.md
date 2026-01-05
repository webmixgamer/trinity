# Feature: Tasks Tab

## Overview

The Tasks tab provides a unified view for headless agent executions within the Agent Detail page. It consolidates all task executions (manual, scheduled, agent-to-agent) into a single interface with the ability to trigger new tasks directly, monitor running tasks and queue status in real-time, and re-run historical tasks.

**Log Format Standardization (2025-01-02)**: All execution types (manual tasks, scheduled executions, manual triggers) now use the `/api/task` endpoint which returns raw Claude Code `stream-json` format. This ensures the [Execution Log Viewer](execution-log-viewer.md) can properly render all execution transcripts.

## User Story

As an agent operator, I want to view and trigger headless task executions from a single location so that I can manage agent workloads without entering the terminal or managing multiple interfaces.

## Entry Points

- **UI**: `src/frontend/src/views/AgentDetail.vue:201-204` - Tasks tab button
- **UI**: `src/frontend/src/components/TasksPanel.vue` - Main component
- **API**: `POST /api/agents/{name}/task` - Execute a parallel task (creates execution record)
- **API**: `POST /api/agents/{name}/chat` - Agent-to-agent chat (creates execution record when `X-Source-Agent` header present) *(added 2025-12-30)*
- **API**: `GET /api/agents/{name}/executions` - Get execution history
- **API**: `GET /api/agents/{name}/executions/{execution_id}/log` - Get full execution log *(added 2025-12-31)*
- **API**: `GET /api/agents/{name}/queue` - Get queue status
- **API**: `POST /api/agents/{name}/queue/clear` - Clear queued tasks
- **API**: `POST /api/agents/{name}/queue/release` - Force release queue

---

## Frontend Layer

### Components

**AgentDetail.vue:884-885** - Tab content rendering:
```vue
<!-- Tasks Tab Content -->
<div v-if="activeTab === 'tasks'" class="p-6">
  <TasksPanel v-if="agent" :agent-name="agent.name" :agent-status="agent.status" />
</div>
```

**TasksPanel.vue** - Main tasks component with the following sections:
- **Header (lines 4-47)**: Title, queue status indicator, refresh button
- **New Task Input (lines 49-78)**: Textarea for task message, Run button
- **Summary Stats (lines 81-100)**: Total tasks, success rate, total cost, avg duration
- **Task History (lines 102-235)**: Scrollable list of all tasks with expand/collapse
- **Queue Management (lines 237-256)**: Force release and clear queue buttons

### State Management

**TasksPanel.vue:264-289** - Local reactive state:
```javascript
const props = defineProps({
  agentName: { type: String, required: true },
  agentStatus: { type: String, default: 'stopped' }
})

// State
const executions = ref([])           // Server-persisted executions
const pendingTasks = ref([])         // Local tasks awaiting server response
const queueStatus = ref(null)        // Current queue status
const loading = ref(true)
const newTaskMessage = ref('')       // New task input
const taskLoading = ref(false)       // Submit in progress
const expandedTaskId = ref(null)     // Currently expanded task
```

**Computed Properties (lines 291-316)**:
```javascript
// Combine local pending tasks with server executions for seamless UX
const allTasks = computed(() => {
  const pending = pendingTasks.value.filter(p => {
    return !executions.value.some(e => e.message === p.message && e.started_at === p.started_at)
  })
  return [...pending, ...executions.value]
})

const successRate = computed(() => { /* ... */ })
const totalCost = computed(() => { /* ... */ })
const avgDuration = computed(() => { /* ... */ })
```

### API Calls

**Load Executions (lines 329-338)**:
```javascript
async function loadExecutions() {
  const response = await axios.get(`/api/agents/${props.agentName}/executions?limit=100`, {
    headers: authStore.authHeader
  })
  executions.value = response.data
}
```

**Load Queue Status (lines 341-354)**:
```javascript
async function loadQueueStatus() {
  if (props.agentStatus !== 'running') {
    queueStatus.value = null
    return
  }
  const response = await axios.get(`/api/agents/${props.agentName}/queue`, {
    headers: authStore.authHeader
  })
  queueStatus.value = response.data
}
```

**Run New Task (lines 357-433)**:
```javascript
async function runNewTask() {
  // Create local pending task for immediate UI feedback
  const localTask = {
    id: 'local-' + Date.now(),
    message: taskMessage,
    status: 'running',
    triggered_by: 'manual',
    started_at: new Date().toISOString(),
    // ... other fields
  }
  pendingTasks.value.unshift(localTask)

  // Submit to server
  const response = await axios.post(`/api/agents/${props.agentName}/task`, {
    message: taskMessage
  }, { headers: authStore.authHeader })

  // Update local task with response data
  // Refresh server executions
  await loadExecutions()
  loadQueueStatus()
}
```

**Queue Management (lines 448-475)**:
```javascript
async function forceReleaseQueue() {
  await axios.post(`/api/agents/${props.agentName}/queue/release`, {}, {
    headers: authStore.authHeader
  })
  await loadQueueStatus()
}

async function clearQueue() {
  await axios.post(`/api/agents/${props.agentName}/queue/clear`, {}, {
    headers: authStore.authHeader
  })
  await loadQueueStatus()
}
```

### Polling

Queue status is polled every 5 seconds when agent is running (watch handler on agentStatus prop).

---

## Backend Layer

### Endpoints

#### POST /api/agents/{name}/task

**File**: `src/backend/routers/chat.py:358-569`

Execute a stateless task in parallel mode (no conversation context).

**Request Model** (`src/backend/models.py`):
```python
class ParallelTaskRequest(BaseModel):
    message: str  # The task to execute
    model: Optional[str] = None  # Model override: sonnet, opus, haiku
    allowed_tools: Optional[List[str]] = None  # Tool restrictions
    system_prompt: Optional[str] = None  # Additional instructions
    timeout_seconds: Optional[int] = 300  # Execution timeout
```

**Business Logic (lines 358-569)**:
1. Validate agent container exists and is running
2. Determine execution source (user or agent-to-agent via `X-Source-Agent` header)
3. **Create task execution record in database** via `db.create_task_execution()`
4. Track activity via `activity_service.track_activity()`
5. If agent-to-agent, broadcast collaboration event via WebSocket
6. Forward request to agent's internal `/api/task` endpoint
7. Update execution record with result (success/failure, cost, duration)
8. Log audit event

**Key difference from /chat**: This endpoint does NOT use the execution queue - tasks run in parallel.

#### GET /api/agents/{name}/executions

**File**: `src/backend/routers/schedules.py:384-398`

Get all executions for an agent across all schedules and manual triggers.

```python
@router.get("/{name}/executions", response_model=List[ExecutionResponse])
async def get_agent_executions(
    name: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    if not db.can_user_access_agent(current_user.username, name):
        raise HTTPException(status_code=403, detail="Access denied")
    executions = db.get_agent_executions(name, limit=limit)
    return [ExecutionResponse(**e.model_dump()) for e in executions]
```

#### GET /api/agents/{name}/queue

**File**: `src/backend/routers/agents.py:445-451`
**Service**: `src/backend/services/agent_service/queue.py:18-43`

Get execution queue status for an agent.

```python
@router.get("/{agent_name}/queue")
async def get_agent_queue_status(agent_name: str, current_user: User = Depends(get_current_user)):
    return await get_agent_queue_status_logic(agent_name, current_user)
```

Returns `QueueStatus` model with:
- `is_busy`: Whether agent is currently executing
- `current_execution`: Details of running execution
- `queue_length`: Number of waiting executions
- `queued_executions`: List of queued execution details

#### GET /api/agents/{name}/executions/{execution_id}/log

**File**: `src/backend/routers/schedules.py:426-473`

Get the full execution log for a specific execution. *(Added 2025-12-31)*

```python
@router.get("/{name}/executions/{execution_id}/log")
async def get_execution_log(
    name: str,
    execution_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the full execution log for a specific execution."""
```

**Response** (log available):
```json
{
  "execution_id": "abc123",
  "agent_name": "my-agent",
  "has_log": true,
  "log": [
    {"type": "assistant", "message": {...}},
    {"type": "tool_use", "name": "Read", "input": {...}},
    {"type": "tool_result", "content": [...]}
  ],
  "started_at": "2025-12-31T10:00:00Z",
  "completed_at": "2025-12-31T10:01:00Z",
  "status": "success"
}
```

**Response** (no log):
```json
{
  "execution_id": "abc123",
  "has_log": false,
  "log": null,
  "message": "No execution log available for this execution"
}
```

#### POST /api/agents/{name}/queue/clear

**File**: `src/backend/routers/agents.py:454-460`
**Service**: `src/backend/services/agent_service/queue.py:46-82`

Clear all queued executions for an agent (does not stop running execution).

#### POST /api/agents/{name}/queue/release

**File**: `src/backend/routers/agents.py:463-469`
**Service**: `src/backend/services/agent_service/queue.py:85-124`

Force release an agent from its running state (emergency use for stuck executions).

---

## Agent Layer

### Agent Server Endpoint

**File**: `docker/base-image/agent_server/routers/chat.py:83-119`

```python
@router.post("/api/task")
async def execute_task(request: ParallelTaskRequest):
    """
    Execute a stateless task in parallel mode (no conversation context).

    Unlike /api/chat, this endpoint:
    - Does NOT acquire execution lock (parallel allowed)
    - Does NOT use --continue flag (stateless)
    - Each call is independent and can run concurrently
    """
    response_text, execution_log, metadata, session_id = await execute_headless_task(
        prompt=request.message,
        model=request.model,
        allowed_tools=request.allowed_tools,
        system_prompt=request.system_prompt,
        timeout_seconds=request.timeout_seconds or 300
    )

    return {
        "response": response_text,
        "execution_log": [entry.model_dump() for entry in execution_log],
        "metadata": metadata.model_dump(),
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }
```

### Claude Code Execution

The `execute_headless_task()` function in `agent_server/services/claude_code.py` runs Claude Code without conversation context:

```bash
claude --print --output-format stream-json --model {model} "prompt"
```

**Key differences from conversational chat**:
- No `--continue` flag (fresh context each time)
- No conversation history updates
- No execution lock (parallel allowed)
- Unique session ID generated per execution

---

## Data Layer

### Database Operations

**File**: `src/backend/db/schedules.py:298-328`

**Create Task Execution**:
```python
def create_task_execution(self, agent_name: str, message: str, triggered_by: str = "manual") -> Optional[ScheduleExecution]:
    """Create a new execution record for a manual/API-triggered task (no schedule)."""
    execution_id = self._generate_id()
    now = datetime.utcnow().isoformat()

    cursor.execute("""
        INSERT INTO schedule_executions (
            id, schedule_id, agent_name, status, started_at, message, triggered_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        execution_id,
        "__manual__",  # Special marker for manual/API-triggered tasks
        agent_name,
        "running",
        now,
        message,
        triggered_by
    ))
```

**Update Execution Status** (`src/backend/db/schedules.py:362-405`):
```python
def update_execution_status(
    self,
    execution_id: str,
    status: str,
    response: str = None,
    error: str = None,
    context_used: int = None,
    context_max: int = None,
    cost: float = None,
    tool_calls: str = None
) -> bool:
    # Calculate duration from started_at
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)
    # Update record
```

**Get Agent Executions** (`src/backend/db/schedules.py:419-429`):
```python
def get_agent_executions(self, agent_name: str, limit: int = 50) -> List[ScheduleExecution]:
    """Get all executions for an agent across all schedules."""
    cursor.execute("""
        SELECT * FROM schedule_executions
        WHERE agent_name = ?
        ORDER BY started_at DESC
        LIMIT ?
    """, (agent_name, limit))
```

**Note**: The `create_task_execution` method was added 2025-12-28 specifically for manual task persistence.

### Database Schema

**Table**: `schedule_executions`

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT | Unique execution ID |
| `schedule_id` | TEXT | Schedule ID or `__manual__` for tasks |
| `agent_name` | TEXT | Agent name |
| `status` | TEXT | pending, running, success, failed |
| `started_at` | TEXT | ISO timestamp |
| `completed_at` | TEXT | ISO timestamp (nullable) |
| `duration_ms` | INTEGER | Execution duration in ms |
| `message` | TEXT | Task message |
| `response` | TEXT | Claude's response (nullable) |
| `error` | TEXT | Error message if failed (nullable) |
| `triggered_by` | TEXT | manual, schedule, agent |
| `context_used` | INTEGER | Tokens used (nullable) |
| `context_max` | INTEGER | Context window size (nullable) |
| `cost` | REAL | Cost in USD (nullable) |
| `tool_calls` | TEXT | JSON array of tool calls (nullable) |
| `execution_log` | TEXT | Full Claude Code execution transcript (JSON, nullable) *(added 2025-12-31)* |

---

## Execution Queue (Redis)

**File**: `src/backend/services/execution_queue.py`

The execution queue ensures only one execution runs per agent at a time for the `/chat` endpoint. **Note: The `/task` endpoint bypasses this queue entirely for parallel execution.**

### Queue Configuration

```python
MAX_QUEUE_SIZE = 3           # Max queued requests per agent
EXECUTION_TTL = 600          # 10 minutes max execution time
QUEUE_WAIT_TIMEOUT = 120     # 120 seconds max wait in queue
```

### Redis Keys

- `agent:running:{agent_name}` - Currently running execution (JSON)
- `agent:queue:{agent_name}` - Waiting queue (Redis list)

### QueueStatus Model

```python
class QueueStatus(BaseModel):
    agent_name: str
    is_busy: bool
    current_execution: Optional[Execution] = None
    queue_length: int
    queued_executions: List[Execution] = []
```

---

## Side Effects

### WebSocket Broadcasts

**Agent Collaboration Event** (when X-Source-Agent header present):
```python
{
    "type": "agent_collaboration",
    "source_agent": "orchestrator",
    "target_agent": "worker",
    "action": "parallel_task",
    "timestamp": "2025-12-28T10:00:00Z"
}
```

### Audit Log

**File**: `src/backend/routers/chat.py:430-443`

```python
await log_audit_event(
    event_type="agent_interaction",
    action="parallel_task",
    user_id=current_user.username,
    agent_name=name,
    resource=f"agent-{name}",
    result="success",
    details={
        "source": source.value,
        "source_agent": x_source_agent,
        "session_id": response_data.get("session_id"),
        "execution_id": execution_id
    }
)
```

### Activity Tracking

Tasks are tracked in the `agent_activities` table via `activity_service.track_activity()`:
- Activity type: `CHAT_START` (reused for tasks)
- Details include: parallel_mode=True, model, timeout_seconds, execution_id

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Agent not found | 404 | Agent not found |
| Agent not running | 503 | Agent is not running |
| Task timeout | 504 | Task execution timed out after N seconds |
| HTTP error to agent | 503 | Failed to execute task. The agent may be unavailable. |
| Access denied | 403 | Access denied |

---

## UI States

### Queue Status Indicator

**Idle State** (green):
```
[Green dot] Idle
```

**Busy State** (yellow pulsing):
```
[Yellow pulsing dot] Busy | 2 queued
```

### Task Status Badges

| Status | Badge Color | Indicator |
|--------|-------------|-----------|
| running | Yellow | Pulsing dot |
| success | Green | Solid dot |
| failed | Red | Solid dot |
| queued | Gray | Solid dot |

### Trigger Badges

| Trigger | Color |
|---------|-------|
| manual | Blue |
| schedule | Purple |
| agent | Gray |

---

## Security Considerations

1. **Authorization**: All endpoints require authentication via `get_current_user`
2. **Agent Access**: `db.can_user_access_agent()` check before any operation
3. **No Credential Exposure**: Task messages may contain sensitive data but are stored in database (not logged)
4. **Queue Protection**: Queue clear/release endpoints require agent access permissions

---

## Related Flows

- **Upstream**: [parallel-headless-execution.md](parallel-headless-execution.md) - Core `/task` endpoint implementation
- **Upstream**: [execution-queue.md](execution-queue.md) - Queue system (bypassed by tasks)
- **Related**: [scheduling.md](scheduling.md) - Scheduled executions share the same database table (now use `/api/task` for log format)
- **Related**: [execution-log-viewer.md](execution-log-viewer.md) - Log viewer that renders execution transcripts
- **Downstream**: [activity-monitoring.md](activity-monitoring.md) - Activity tracking for tasks

---

## Revision History

| Date | Changes |
|------|---------|
| 2025-01-02 | Added note about log format standardization - all execution types now use `/api/task` for raw Claude Code format |
| 2025-12-31 | Initial documentation - execution log viewer added |

---

## Testing

### Prerequisites
- Trinity platform running (`./scripts/deploy/start.sh`)
- At least one agent created and running

### Test Steps

1. **Navigate to Tasks Tab**
   - Go to Agent Detail page for any agent
   - Click "Tasks" tab
   - **Expected**: Tasks panel loads with empty state or existing executions

2. **Submit New Task (Agent Running)**
   - Enter task message: "What is 2+2?"
   - Click "Run" button
   - **Expected**:
     - Task appears immediately with "running" status (local optimistic update)
     - After completion, status changes to "success"
     - Response can be expanded by clicking task row

3. **Submit Task (Agent Stopped)**
   - Stop the agent
   - Attempt to submit task
   - **Expected**:
     - Run button is disabled
     - Warning message: "Agent must be running to execute tasks"

4. **Re-run Historical Task**
   - Click re-run icon on any completed task
   - **Expected**: Task message populates input and submits automatically

5. **Queue Status (with /chat endpoint)**
   - Open terminal tab and start a long-running task
   - Switch to Tasks tab
   - **Expected**: Queue status shows "Busy" indicator

6. **Force Release Queue**
   - When queue shows "Busy"
   - Click "Force Release Queue"
   - **Expected**: Queue indicator returns to "Idle"

### Edge Cases
- Submit empty task (should be disabled)
- Submit very long task message (should work, message truncated in display)
- Multiple rapid task submissions (all should complete independently)

### Status
Verified 2025-12-31 - Execution log storage and retrieval endpoint added
