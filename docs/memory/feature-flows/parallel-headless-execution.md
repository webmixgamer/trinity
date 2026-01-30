# Feature Flow: Parallel Headless Execution

> **Requirement**: 12.1 - Parallel Headless Execution
> **Status**: Implemented
> **Created**: 2025-12-22
> **Updated**: 2026-01-23 (verified line numbers and code references)
> **Verified**: 2026-01-23

## Revision History

| Date | Changes |
|------|---------|
| 2026-01-30 | **Async mode (fire-and-forget)**: Added `async_mode` parameter for non-blocking execution. Backend spawns background task, returns immediately with `execution_id`. Poll for results. New section documents implementation, use cases, and API. |
| 2026-01-23 | Verified all line numbers against current codebase. Updated file references. |
| 2026-01-12 | Added max_turns parameter for runaway prevention |
| 2025-12-31 | Added execution log persistence details |
| 2025-12-22 | Initial documentation |

## Overview

This feature enables Trinity agents to execute multiple independent tasks in parallel without blocking the main conversation context. It unlocks agent-to-agent orchestration patterns where an orchestrator can delegate to multiple workers simultaneously.

## Problem Statement

**Prior Limitation**: Trinity agents could only process one request at a time due to:
1. Platform-level execution queue (Redis) that serializes requests
2. Container-level execution lock (`asyncio.Lock`)
3. Use of `--continue` flag which requires sequential execution to maintain conversation context

**Solution**: New parallel task mode that bypasses queue and lock, runs stateless (no --continue).

## Two Execution Modes

| Mode | Endpoint | Context | Parallel | Use Case |
|------|----------|---------|----------|----------|
| **Sequential Chat** | `POST /api/agents/{name}/chat` | Maintains conversation | No | Interactive chat, multi-turn reasoning |
| **Parallel Task** | `POST /api/agents/{name}/task` | Stateless | Yes | Agent delegation, batch processing |

## Architecture Diagram

```
                                    +-----------------------------+
                                    |     Sequential Chat         |
User/Agent --> POST /chat --------->|  Execution Queue (Redis)    |--> claude --continue
                                    |  One at a time              |
                                    +-----------------------------+

                                    +-----------------------------+
                                    |     Parallel Task           |
User/Agent --> POST /task --------->|  No queue, no lock          |--> claude -p (headless)
              (can send N)          |  N concurrent allowed       |    (N processes)
                                    +-----------------------------+
```

## Data Flow

### 1. MCP Tool Call (Orchestrator Agent)

```
Orchestrator Agent
       |
       v
+---------------------------------------------+
| chat_with_agent(                            |
|   agent_name: "worker-1",                   |
|   message: "Process file X",                |
|   parallel: true,                           |
|   timeout_seconds: 300                      |
| )                                           |
+---------------------------------------------+
       |
       v
   MCP Server (src/mcp-server)
       |
       v
   client.task(name, message, options)
       |
       v
   POST /api/agents/{name}/task
```

### 2. Backend Processing

```
POST /api/agents/{name}/task
       |
       v
+---------------------------------------------+
| 1. Validate agent exists and is running     |
| 2. Check access permissions                 |
| 3. Track activity (ActivityType.CHAT_START  |
|    with parallel_mode: true)                |
| 4. Build payload with options               |
| 5. Proxy to agent container                 |
|    (NO EXECUTION QUEUE)                     |
+---------------------------------------------+
       |
       v
   POST http://agent-{name}:8000/api/task
```

### 3. Agent Container Execution

```
POST /api/task
       |
       v
+---------------------------------------------+
| execute_headless_task()                     |
|                                             |
| - NO execution lock acquired                |
| - Build command:                            |
|   claude -p --output-format stream-json     |
|   --verbose --dangerously-skip-permissions  |
|   [--model X] [--allowedTools Y]            |
|   [--append-system-prompt Z]                |
|   [--max-turns N]                           |
|   [--mcp-config ~/.mcp.json]                |
|                                             |
| - NO --continue flag (stateless)            |
| - Parse streaming JSON output               |
| - Return response with session_id           |
+---------------------------------------------+
```

## Key Files

### Agent Server (docker/base-image/agent_server/)

| File | Line | Purpose |
|------|------|---------|
| `models.py` | 215-232 | ParallelTaskRequest, ParallelTaskResponse models |
| `services/claude_code.py` | 553-739 | execute_headless_task() function |
| `services/gemini_runtime.py` | 489-642 | execute_headless() for Gemini CLI |
| `services/runtime_adapter.py` | 99-129 | AgentRuntime.execute_headless() interface |
| `routers/chat.py` | 96-137 | POST /api/task endpoint |

### Backend (src/backend/)

| File | Line | Purpose |
|------|------|---------|
| `models.py` | 109-117 | ParallelTaskRequest model with max_turns and async_mode |
| `routers/chat.py` | 418-525 | `_execute_task_background()` helper for async mode |
| `routers/chat.py` | 527-817 | POST /api/agents/{name}/task endpoint (async mode at 619-645) |
| `routers/schedules.py` | 323-336 | GET /api/agents/{name}/executions/{id} endpoint (polling) |
| `routers/schedules.py` | 339-379 | GET /api/agents/{name}/executions/{id}/log endpoint |
| `services/agent_client.py` | 194-287 | AgentClient.task() method |

### MCP Server (src/mcp-server/)

| File | Line | Purpose |
|------|------|---------|
| `src/client.ts` | 399-454 | task() method with async_mode option |
| `src/tools/chat.ts` | 132-284 | chat_with_agent tool with parallel and async parameters |
| `src/tools/chat.ts` | 187-194 | async parameter definition |

## API Specifications

### Agent Server: POST /api/task

**Request**:
```json
{
  "message": "string",           // Required: Task to execute
  "model": "sonnet|opus|haiku",  // Optional: Model override
  "allowed_tools": ["Read"],     // Optional: Tool restrictions
  "system_prompt": "string",     // Optional: Additional instructions
  "timeout_seconds": 900,        // Optional: Timeout (default 15 min)
  "max_turns": 50,               // Optional: Max agentic turns (runaway prevention)
  "execution_id": "uuid"         // Optional: Database execution ID for process registry
}
```

**Response**:
```json
{
  "response": "string",          // Claude's response
  "execution_log": [...],        // Tool calls and results (also saved to DB)
  "metadata": {
    "cost_usd": 0.01,
    "duration_ms": 5000,
    "input_tokens": 1000,
    "output_tokens": 500,
    "tool_count": 3
  },
  "session_id": "uuid",          // Unique per task
  "timestamp": "2025-12-22T..."
}
```

**Note**: The `execution_log` is persisted to the `schedule_executions` database table and can be retrieved via `GET /api/agents/{name}/executions/{execution_id}/log`.

### Backend: POST /api/agents/{name}/task

Same request/response as agent server, with additional:
- Authentication via JWT token
- Access control validation
- Activity tracking
- Audit logging
- **Execution log persistence** - Full transcript saved to `schedule_executions.execution_log`
- **Process registry** - Passes `execution_id` to agent for termination tracking

### Backend: GET /api/agents/{name}/executions/{execution_id}/log

Retrieve the full execution log for any task execution.

**File**: `src/backend/routers/schedules.py:339-379`

**Response**:
```json
{
  "execution_id": "abc123",
  "agent_name": "worker-1",
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

### MCP Tool: chat_with_agent

**Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| agent_name | string | required | Target agent |
| message | string | required | Task to execute |
| parallel | boolean | false | Enable parallel mode |
| model | string | null | Model override (parallel only) |
| allowed_tools | string[] | null | Tool restrictions (parallel only) |
| system_prompt | string | null | Additional instructions (parallel only) |
| timeout_seconds | number | 300 | Timeout in seconds (parallel only) |
| max_turns | number | null | Max agentic turns for runaway prevention (parallel only) |
| async | boolean | false | Fire-and-forget mode - return immediately with execution_id (parallel only) |

## Key Differences: Chat vs Task

| Aspect | Chat (Sequential) | Task (Parallel) |
|--------|-------------------|-----------------|
| Endpoint | POST /api/chat | POST /api/task |
| Execution Queue | Yes (Redis) | No |
| Execution Lock | Yes (asyncio.Lock) | No |
| --continue flag | Yes | No |
| Conversation context | Maintained | Stateless |
| Session updates | Yes | No |
| Concurrent requests | 1 per agent | N per agent |
| Use case | Interactive chat | Batch processing |

## Runaway Prevention: max_turns Parameter

**Added**: 2026-01-12

The `max_turns` parameter limits the number of agentic turns an agent can take before the CLI exits. This prevents runaway agents that get stuck in infinite loops or continue executing far beyond expected scope.

### How It Works

When `max_turns` is specified:

1. **Agent Server** passes `--max-turns N` to the Claude Code or Gemini CLI command
2. **CLI** counts each agentic turn (tool use + tool result cycle)
3. **At limit**: CLI exits with an error, returning partial results
4. **Response**: Includes whatever work was completed before the limit

### Implementation Details

**Claude Code** (`docker/base-image/agent_server/services/claude_code.py:622-625`):
```python
if max_turns is not None:
    cmd.extend(["--max-turns", str(max_turns)])
    logger.info(f"[Headless Task] Limiting to {max_turns} agentic turns")
```

**Gemini CLI** (`docker/base-image/agent_server/services/gemini_runtime.py:542-544`):
```python
if max_turns is not None:
    cmd.extend(["--max-turns", str(max_turns)])
    logger.info(f"[Headless Task {session_id}] Limiting to {max_turns} agentic turns")
```

### Usage Examples

**Conservative limit for simple tasks**:
```json
{
  "message": "Read the README.md file and summarize it",
  "max_turns": 5
}
```

**Higher limit for complex analysis**:
```json
{
  "message": "Analyze this codebase and create a report",
  "max_turns": 50,
  "timeout_seconds": 1800
}
```

**Combined with tool restrictions**:
```json
{
  "message": "Search for security vulnerabilities",
  "allowed_tools": ["Read", "Grep", "Glob"],
  "max_turns": 100,
  "timeout_seconds": 3600
}
```

### Recommended Values

| Task Type | Recommended max_turns | Rationale |
|-----------|----------------------|-----------|
| Simple queries | 5-10 | Few file reads needed |
| Code analysis | 25-50 | Multiple file traversals |
| Refactoring | 50-100 | Many edit operations |
| Deep research | 100-200 | Extensive exploration |
| Unlimited | null (default) | Trusted orchestrators only |

### When to Use

- **Always** for user-triggered parallel tasks
- **Always** for scheduled tasks without human supervision
- **Recommended** for agent-to-agent delegation
- **Optional** for interactive chat (human can cancel)

### Relationship with timeout_seconds

Both parameters provide safety limits:

| Parameter | Protects Against | Behavior at Limit |
|-----------|-----------------|-------------------|
| `timeout_seconds` | Wall-clock time exceeded | Process killed, HTTP 504 |
| `max_turns` | Too many agentic operations | CLI exits gracefully, HTTP 500 |

Use both together for comprehensive protection:
```json
{
  "message": "Complex task",
  "max_turns": 50,
  "timeout_seconds": 900
}
```

## Async Mode (Fire-and-Forget)

**Added**: 2026-01-30

Async mode enables non-blocking task execution where the API returns immediately with an `execution_id` that can be polled later for results.

### How It Works

When `async_mode=true` is specified:

1. **Backend creates execution record** with `status="running"`
2. **Spawns background task** via `asyncio.create_task()`
3. **Returns immediately** with `execution_id` for polling
4. **Background task executes** the Claude Code command
5. **Updates execution record** when complete (success/failed)
6. **Completes activities** asynchronously

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Async Mode Flow                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Orchestrator                                                    │
│       │                                                          │
│       ├── POST /api/agents/worker/task {async_mode: true}       │
│       │                                                          │
│       v                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Backend (chat.py)                                       │    │
│  │                                                          │    │
│  │  1. Create execution record (status="running")           │    │
│  │  2. Track activities (CHAT_START)                        │    │
│  │  3. asyncio.create_task(_execute_task_background(...))   │    │
│  │  4. Return immediately:                                  │    │
│  │     { status: "accepted", execution_id: "abc123" }       │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│       │<────────────────────┘  (immediate response)              │
│       │                                                          │
│       │  Poll: GET /api/agents/worker/executions/abc123          │
│       │                                                          │
│                        (Background task runs independently)      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  _execute_task_background()                               │   │
│  │                                                           │   │
│  │  - Calls agent container /api/task                        │   │
│  │  - On success: db.update_execution_status("success")      │   │
│  │  - On failure: db.update_execution_status("failed")       │   │
│  │  - Completes activities                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Details

**Backend Model** (`src/backend/models.py:117`):
```python
class ParallelTaskRequest(BaseModel):
    # ... existing fields ...
    async_mode: Optional[bool] = False  # If true, return immediately with execution_id
```

**Background Task Handler** (`src/backend/routers/chat.py:418-525`):
```python
async def _execute_task_background(
    agent_name: str,
    request: ParallelTaskRequest,
    execution_id: str,
    task_activity_id: str,
    collaboration_activity_id: Optional[str],
    x_source_agent: Optional[str]
):
    """
    Background task execution for async mode.
    Runs the task and updates execution record/activities when complete.
    """
    try:
        # Call agent container
        response = await agent_post_with_retry(agent_name, "/api/task", payload, ...)

        # Update execution record with success
        db.update_execution_status(execution_id=execution_id, status="success", ...)

        # Complete activities
        await activity_service.complete_activity(task_activity_id, ...)

    except Exception as e:
        # Update execution record with failure
        db.update_execution_status(execution_id=execution_id, status="failed", error=str(e))

        # Complete activities with failure
        await activity_service.complete_activity(task_activity_id, status="failed", ...)
```

**Endpoint Logic** (`src/backend/routers/chat.py:619-645`):
```python
# Async mode: spawn task in background and return immediately
if request.async_mode:
    # Update execution status to "running"
    if execution_id:
        db.update_execution_status(execution_id=execution_id, status="running")

    # Spawn background task
    asyncio.create_task(
        _execute_task_background(
            agent_name=name,
            request=request,
            execution_id=execution_id,
            task_activity_id=task_activity_id,
            collaboration_activity_id=collaboration_activity_id,
            x_source_agent=x_source_agent
        )
    )

    # Return immediately with execution_id for polling
    return {
        "status": "accepted",
        "execution_id": execution_id,
        "agent_name": name,
        "message": "Task accepted. Poll GET /api/agents/{name}/executions/{execution_id} for results.",
        "async_mode": True
    }
```

**MCP Client** (`src/mcp-server/src/client.ts:399-454`):
```typescript
async task(name: string, message: string, options?: {
  // ... existing options ...
  async_mode?: boolean;  // If true, return immediately with execution_id
}, sourceAgent?: string) {
  // Async mode returns immediately; sync mode waits for full execution
  const timeout = options?.async_mode ? 30 : (options?.timeout_seconds || 600) + 10;
  // ...
}
```

**MCP Tool** (`src/mcp-server/src/tools/chat.ts:187-194`):
```typescript
async: z
  .boolean()
  .optional()
  .default(false)
  .describe(
    "If true, return immediately with execution_id (fire-and-forget). " +
    "Only applies when parallel=true. Poll the execution endpoint for results."
  ),
```

### API Specification

**Request**:
```json
{
  "message": "Process large dataset",
  "async_mode": true,
  "model": "sonnet",
  "timeout_seconds": 3600
}
```

**Immediate Response** (HTTP 200):
```json
{
  "status": "accepted",
  "execution_id": "abc123xyz789",
  "agent_name": "worker-1",
  "message": "Task accepted. Poll GET /api/agents/{name}/executions/{execution_id} for results.",
  "async_mode": true
}
```

**Polling Endpoint**: `GET /api/agents/{name}/executions/{execution_id}`

**Response when running**:
```json
{
  "id": "abc123xyz789",
  "agent_name": "worker-1",
  "status": "running",
  "message": "Process large dataset",
  "triggered_by": "manual",
  "started_at": "2026-01-30T10:00:00Z",
  "completed_at": null,
  "response": null,
  "cost": null
}
```

**Response when complete**:
```json
{
  "id": "abc123xyz789",
  "agent_name": "worker-1",
  "status": "success",
  "message": "Process large dataset",
  "triggered_by": "manual",
  "started_at": "2026-01-30T10:00:00Z",
  "completed_at": "2026-01-30T10:05:00Z",
  "response": "Dataset processed successfully. 10,000 records analyzed.",
  "cost": 0.15,
  "context_used": 50000,
  "context_max": 200000
}
```

### Use Cases

#### 1. Fan-Out Pattern
Spawn multiple long-running tasks without blocking:

```python
# Orchestrator spawns 10 workers, doesn't wait
execution_ids = []
for i, batch in enumerate(data_batches):
    result = mcp__trinity__chat_with_agent(
        agent_name=f"worker-{i}",
        message=f"Process batch: {batch}",
        parallel=true,
        async=true
    )
    execution_ids.append(result["execution_id"])

# Continue with other work while workers process...

# Later: collect results
for agent_name, exec_id in zip(worker_names, execution_ids):
    result = poll_execution(agent_name, exec_id)  # Helper to wait for completion
    results.append(result)
```

#### 2. Background Analysis
Trigger analysis that runs independently:

```python
# Start long-running analysis
result = mcp__trinity__chat_with_agent(
    agent_name="analysis-agent",
    message="Analyze codebase for security vulnerabilities",
    parallel=true,
    async=true,
    timeout_seconds=7200  # 2 hours
)

# Don't wait - check results later via UI or API
print(f"Analysis started: {result['execution_id']}")
```

#### 3. Scheduled Cleanup
System agent triggers maintenance without blocking:

```python
# Nightly cleanup across fleet
for agent in get_all_agents():
    mcp__trinity__chat_with_agent(
        agent_name=agent,
        message="Run nightly cleanup: clear temp files, rotate logs",
        parallel=true,
        async=true
    )
# All cleanup jobs run concurrently, system agent continues
```

### Key Differences: Sync vs Async

| Aspect | Sync (async_mode=false) | Async (async_mode=true) |
|--------|------------------------|-------------------------|
| Return time | After task completes | Immediately |
| Response | Full result with execution_log | execution_id only |
| HTTP timeout | timeout_seconds + 10 | 30 seconds |
| Result retrieval | In response | Poll endpoint |
| Error handling | Exception in response | Poll for error status |
| Connection held | Yes, for duration | No, released immediately |

### Limitations and Considerations

1. **No streaming in async mode**: Cannot use SSE streaming with async; poll for final result only
2. **Orphaned tasks**: If backend restarts, background tasks are lost (execution stays "running")
3. **No cancellation via async**: Must use separate termination endpoint
4. **Database required**: execution_id comes from database record; fails if DB unavailable
5. **Activity completion async**: Activities complete after task finishes, not at request time

---

## Live Execution Streaming

Task executions can be monitored in real-time via Server-Sent Events (SSE).

### Endpoint

**Backend**: `GET /api/agents/{name}/executions/{execution_id}/stream`
**File**: `src/backend/routers/chat.py:1196-1257`

**Agent Server**: `GET /api/executions/{execution_id}/stream`
**File**: `docker/base-image/agent_server/routers/chat.py:295-369`

### Process Registry

The process registry (`docker/base-image/agent_server/services/process_registry.py`) enables:
- Tracking running executions
- Terminating executions
- Live log streaming via pub/sub

## Testing

Tests are in `tests/test_parallel_task.py`:

| Test Class | Purpose |
|------------|---------|
| TestParallelTaskEndpoint | Endpoint existence, 404/503 handling |
| TestParallelTaskResponse | Response format validation |
| TestParallelTaskOptions | Model, timeout parameter handling |
| TestParallelTaskStateless | Verifies no context pollution |
| TestParallelExecution | Multiple concurrent tasks |

Run tests:
```bash
cd tests && pytest test_parallel_task.py -v
```

## Use Cases

### 1. Orchestrator-Worker Pattern
```
Orchestrator spawns 5 parallel workers:
  +-> Worker 1: "Process file A" (parallel=true)
  +-> Worker 2: "Process file B" (parallel=true)
  +-> Worker 3: "Process file C" (parallel=true)
  +-> Worker 4: "Process file D" (parallel=true)
  +-> Worker 5: "Process file E" (parallel=true)

All 5 execute concurrently, no queue blocking.
```

### 2. Batch Processing
```
System Agent runs nightly batch:
  for each agent in fleet:
    chat_with_agent(agent, "Run health check", parallel=true)
```

### 3. Research Tasks
```
Orchestrator gathers info from multiple sources:
  +-> Research Agent 1: "Find info about X" (parallel=true)
  +-> Research Agent 2: "Find info about Y" (parallel=true)
  +-> Research Agent 3: "Find info about Z" (parallel=true)

Combine results after all complete.
```

## Security Considerations

1. **Access Control**: Same rules as chat - owner, shared, or admin
2. **Rate Limiting**: Consider implementing concurrency limits
3. **Audit Trail**: All parallel tasks logged with user attribution
4. **Tool Restrictions**: `allowed_tools` parameter for sandboxing
5. **Timeout**: Hard limit (`timeout_seconds`) prevents wall-clock runaway
6. **Turn Limit**: `max_turns` prevents infinite agentic loops

## Future Enhancements

1. **Concurrency Limits**: Agent-level (default 5), platform-level (default 50)
2. **Activity Type**: New `parallel_task` activity type (currently reuses CHAT_START)
3. **Session Persistence**: Optional session persistence with TTL for resume
4. **Batch API**: `POST /api/agents/{name}/batch` for multiple tasks
5. **Priority Queue**: Priority parameter for urgent tasks
