# Feature: Execution Termination

## Overview

Execution Termination allows users to stop running Claude Code executions mid-flight by sending graceful signals (SIGINT) to the subprocess, with fallback to force kill (SIGKILL) if needed. This feature enables users to cancel long-running or stuck tasks without waiting for them to complete.

## User Story

As an agent operator, I want to stop a running task execution so that I can cancel stuck or unnecessary operations and reclaim agent resources.

## Entry Points

- **UI**: `src/frontend/src/components/TasksPanel.vue:239-255` - Stop button for running tasks
- **API (Backend)**: `POST /api/agents/{name}/executions/{execution_id}/terminate`
- **API (Agent)**: `POST /api/executions/{execution_id}/terminate`
- **API (Agent)**: `GET /api/executions/running`

---

## Architecture

```
+---------------------------+      +---------------------------+      +----------------------------+
|       TasksPanel.vue      |      |     Backend chat.py       |      |   Agent agent_server/      |
|---------------------------|      |---------------------------|      |----------------------------|
| Stop Button (running task)|----->| POST /{name}/executions/  |----->| POST /api/executions/      |
|                           |      | {execution_id}/terminate  |      | {execution_id}/terminate   |
|---------------------------|      |---------------------------|      |----------------------------|
| terminateTask()           |      | Proxy to agent container  |      | ProcessRegistry.terminate()|
| loadRunningExecutions()   |      | Clear queue on success    |      | SIGINT -> wait 5s -> SIGKILL
+---------------------------+      | Track activity            |      +----------------------------+
                                   +---------------------------+
```

---

## Agent Layer

### Process Registry (`docker/base-image/agent_server/services/process_registry.py`)

Thread-safe registry for tracking running subprocess handles.

**Class**: `ProcessRegistry` (lines 18-163)

| Method | Description |
|--------|-------------|
| `register(execution_id, process, metadata)` | Register a running subprocess with metadata |
| `unregister(execution_id)` | Remove a completed process from registry |
| `terminate(execution_id, graceful_timeout=5)` | Graceful SIGINT -> SIGKILL termination |
| `get_status(execution_id)` | Get status of a registered process |
| `list_running()` | List all currently running executions |
| `cleanup_finished()` | Remove entries for finished processes |

**Termination Flow** (lines 54-110):
```python
def terminate(self, execution_id: str, graceful_timeout: int = 5) -> dict:
    # 1. Check if process exists
    if not entry:
        return {"success": False, "reason": "not_found"}

    # 2. Check if already finished
    if process.poll() is not None:
        return {"success": False, "reason": "already_finished", "returncode": ...}

    # 3. Graceful termination (SIGINT = Ctrl+C)
    process.send_signal(signal.SIGINT)

    try:
        process.wait(timeout=graceful_timeout)  # Wait 5 seconds
    except subprocess.TimeoutExpired:
        # 4. Force kill if graceful didn't work
        process.kill()
        process.wait(timeout=2)

    return {"success": True, "returncode": process.returncode}
```

### Process Registration in Claude Code (`docker/base-image/agent_server/services/claude_code.py`)

**Conversational Chat** (lines 468-536):
```python
# Generate execution_id
execution_id = str(uuid.uuid4())

# Register process after Popen
registry = get_process_registry()
registry.register(execution_id, process, metadata={
    "type": "chat",
    "message_preview": prompt[:100]
})

try:
    # ... execute and parse response ...
    metadata.execution_id = execution_id  # Include in response metadata
finally:
    # Always unregister when done
    registry.unregister(execution_id)
```

**Headless Task** (lines 644-751):
```python
# Use task_session_id for headless tasks
registry = get_process_registry()
registry.register(task_session_id, process, metadata={
    "type": "task",
    "message_preview": prompt[:100]
})

try:
    # ... execute and parse response ...
    metadata.execution_id = task_session_id  # Include in response metadata
finally:
    registry.unregister(task_session_id)
```

### Agent Server Endpoints (`docker/base-image/agent_server/routers/chat.py`)

**POST /api/executions/{execution_id}/terminate** (lines 241-260):
```python
@router.post("/api/executions/{execution_id}/terminate")
async def terminate_execution(execution_id: str):
    registry = get_process_registry()
    result = registry.terminate(execution_id)

    if result["success"]:
        return {"status": "terminated", "execution_id": execution_id}
    elif result["reason"] == "not_found":
        raise HTTPException(status_code=404, detail="Execution not found")
    elif result["reason"] == "already_finished":
        return {"status": "already_finished", "execution_id": execution_id, "returncode": ...}
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Termination failed"))
```

**GET /api/executions/running** (lines 263-271):
```python
@router.get("/api/executions/running")
async def list_running_executions():
    registry = get_process_registry()
    return {"executions": registry.list_running()}
```

**GET /api/executions/{execution_id}/status** (lines 274-285):
```python
@router.get("/api/executions/{execution_id}/status")
async def get_execution_status(execution_id: str):
    registry = get_process_registry()
    status = registry.get_status(execution_id)
    if not status:
        raise HTTPException(status_code=404, detail="Execution not found")
    return status
```

---

## Backend Layer

### Proxy Endpoints (`src/backend/routers/chat.py`)

**POST /api/agents/{name}/executions/{execution_id}/terminate** (lines 1059-1131):
```python
@router.post("/{name}/executions/{execution_id}/terminate")
async def terminate_agent_execution(name: str, execution_id: str, current_user: User = ...):
    # 1. Validate agent exists and is running
    container = get_agent_container(name)
    if not container or container.status != "running":
        raise HTTPException(...)

    # 2. Proxy termination request to agent container
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"http://agent-{name}:8000/api/executions/{execution_id}/terminate"
        )

    # 3. Clear queue state if termination succeeded
    if result.get("status") in ["terminated", "already_finished"]:
        queue = get_execution_queue()
        await queue.force_release(name)

    # 4. Track activity
    await activity_service.track_activity(
        agent_name=name,
        activity_type=ActivityType.EXECUTION_CANCELLED,
        details={"execution_id": execution_id, "status": result.get("status")}
    )

    return result
```

**GET /api/agents/{name}/executions/running** (lines 1134-1159):
```python
@router.get("/{name}/executions/running")
async def get_agent_running_executions(name: str, current_user: User = ...):
    # Proxy to agent container
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"http://agent-{name}:8000/api/executions/running"
        )
        return response.json()
```

---

## Frontend Layer

### TasksPanel.vue (`src/frontend/src/components/TasksPanel.vue`)

**Stop Button UI** (lines 239-255):
```vue
<!-- Stop Button (for running tasks) -->
<button
  v-if="task.status === 'running' && task.execution_id"
  @click="terminateTask(task)"
  :disabled="terminatingTaskId === task.id"
  class="p-1.5 text-gray-400 hover:text-red-600 ..."
  title="Stop execution"
>
  <!-- Spinner when terminating, stop icon otherwise -->
</button>
```

**State** (lines 482, 491):
```javascript
const terminatingTaskId = ref(null)        // ID of task being terminated
const runningExecutions = ref([])           // Running executions from agent
```

**Load Running Executions** (lines 619-634):
```javascript
async function loadRunningExecutions() {
  if (props.agentStatus !== 'running') {
    runningExecutions.value = []
    return
  }
  const response = await axios.get(`/api/agents/${props.agentName}/executions/running`, {
    headers: authStore.authHeader
  })
  runningExecutions.value = response.data.executions || []
}
```

**Execution ID Matching** (lines 509-530):
```javascript
// Enhance running tasks with execution_id from runningExecutions
const enhanceWithExecutionId = (task) => {
  if (task.status !== 'running' || task.execution_id) {
    return task
  }
  // Match by message preview (first 100 chars)
  const messagePreview = task.message.substring(0, 100)
  const match = runningExecutions.value.find(e =>
    e.metadata?.message_preview === messagePreview
  )
  if (match) {
    return { ...task, execution_id: match.execution_id }
  }
  // If only one running execution, assume it's this task
  if (runningExecutions.value.length === 1) {
    return { ...task, execution_id: runningExecutions.value[0].execution_id }
  }
  return task
}
```

**Terminate Task** (lines 742-777):
```javascript
async function terminateTask(task) {
  if (!task.execution_id) {
    console.error('No execution_id available for termination')
    return
  }

  terminatingTaskId.value = task.id

  try {
    await axios.post(
      `/api/agents/${props.agentName}/executions/${task.execution_id}/terminate`,
      {},
      { headers: authStore.authHeader }
    )

    // Update task status locally while we wait for refresh
    const idx = pendingTasks.value.findIndex(t => t.id === task.id)
    if (idx !== -1) {
      pendingTasks.value[idx].status = 'failed'
      pendingTasks.value[idx].error = 'Execution terminated by user'
    }

    // Refresh data to get updated status
    await loadAllData()
  } catch (error) {
    console.error('Failed to terminate task:', error)
  } finally {
    terminatingTaskId.value = null
  }
}
```

---

## Data Models

### ExecutionMetadata (`docker/base-image/agent_server/models.py:82`)
```python
class ExecutionMetadata(BaseModel):
    # ... other fields ...
    execution_id: Optional[str] = None  # Unique ID for process registry (termination)
```

### ActivityType (`src/backend/models.py:135`)
```python
class ActivityType(str, Enum):
    # ... other types ...
    EXECUTION_CANCELLED = "execution_cancelled"
```

---

## Side Effects

### Activity Tracking

When a task is terminated, an activity record is created:
```python
await activity_service.track_activity(
    agent_name=name,
    activity_type=ActivityType.EXECUTION_CANCELLED,
    user_id=current_user.id,
    triggered_by="user",
    details={
        "execution_id": execution_id,
        "status": "terminated" | "already_finished",
        "returncode": int  # Process exit code
    }
)
```

### Queue State

The execution queue is force-released after successful termination to allow new executions:
```python
queue = get_execution_queue()
await queue.force_release(name)
```

---

## Signal Handling

| Signal | Purpose | Timeout |
|--------|---------|---------|
| `SIGINT` | Graceful termination (Ctrl+C) | 5 seconds |
| `SIGKILL` | Force kill (after SIGINT timeout) | 2 seconds |

Claude Code handles SIGINT gracefully, finishing its current operation before exiting. This allows tools like `Write` or `Bash` to complete their current action.

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Agent not found | 404 | Agent not found |
| Agent not running | 503 | Agent is not running |
| Execution not found | 404 | Execution not found |
| Already finished | 200 | status: "already_finished" |
| Connection error | 502 | Failed to connect to agent |
| Timeout | 504 | Timeout connecting to agent |
| Termination error | 500 | Termination failed |

---

## Security Considerations

1. **Authentication**: All termination endpoints require valid JWT token via `get_current_user`
2. **Authorization**: Only users with agent access can terminate executions (implicit via agent container access)
3. **Queue Protection**: Queue is force-released after termination to prevent stuck state
4. **Audit Trail**: All terminations are tracked in activity log with user ID

---

## Related Flows

- **Upstream**: [execution-queue.md](execution-queue.md) - Queue management and execution tracking
- **Upstream**: [parallel-headless-execution.md](parallel-headless-execution.md) - Task execution that generates execution_id
- **Related**: [tasks-tab.md](tasks-tab.md) - UI component displaying stop button
- **Related**: [activity-stream.md](activity-stream.md) - Activity tracking for cancellations

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-01-12 | Initial documentation - Execution Termination feature |
