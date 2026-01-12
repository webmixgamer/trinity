# Feature Flow: Parallel Headless Execution

> **Requirement**: 12.1 - Parallel Headless Execution
> **Status**: Implemented
> **Created**: 2025-12-22
> **Updated**: 2026-01-12 (max_turns parameter for runaway prevention)
> **Verified**: 2025-12-31

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
                                    ┌─────────────────────────────┐
                                    │     Sequential Chat         │
User/Agent ──► POST /chat ─────────►│  Execution Queue (Redis)    │──► claude --continue
                                    │  One at a time              │
                                    └─────────────────────────────┘

                                    ┌─────────────────────────────┐
                                    │     Parallel Task           │
User/Agent ──► POST /task ─────────►│  No queue, no lock          │──► claude -p (headless)
              (can send N)          │  N concurrent allowed       │    (N processes)
                                    └─────────────────────────────┘
```

## Data Flow

### 1. MCP Tool Call (Orchestrator Agent)

```
Orchestrator Agent
       │
       ▼
┌─────────────────────────────────────────────┐
│ chat_with_agent(                            │
│   agent_name: "worker-1",                   │
│   message: "Process file X",                │
│   parallel: true,                           │
│   timeout_seconds: 300                      │
│ )                                           │
└─────────────────────────────────────────────┘
       │
       ▼
   MCP Server (src/mcp-server)
       │
       ▼
   client.task(name, message, options)
       │
       ▼
   POST /api/agents/{name}/task
```

### 2. Backend Processing

```
POST /api/agents/{name}/task
       │
       ▼
┌─────────────────────────────────────────────┐
│ 1. Validate agent exists and is running     │
│ 2. Check access permissions                 │
│ 3. Track activity (ActivityType.CHAT_START  │
│    with parallel_mode: true)                │
│ 4. Build payload with options               │
│ 5. Proxy to agent container                 │
│    (NO EXECUTION QUEUE)                     │
└─────────────────────────────────────────────┘
       │
       ▼
   POST http://agent-{name}:8000/api/task
```

### 3. Agent Container Execution

```
POST /api/task
       │
       ▼
┌─────────────────────────────────────────────┐
│ execute_headless_task()                     │
│                                             │
│ - NO execution lock acquired                │
│ - Build command:                            │
│   claude -p --output-format stream-json     │
│   --verbose --dangerously-skip-permissions  │
│   [--model X] [--allowedTools Y]            │
│   [--append-system-prompt Z]                │
│   [--max-turns N]                           │
│   [--mcp-config ~/.mcp.json]                │
│                                             │
│ - NO --continue flag (stateless)            │
│ - Parse streaming JSON output               │
│ - Return response with session_id           │
└─────────────────────────────────────────────┘
```

## Key Files

### Agent Server (docker/base-image/agent_server/)

| File | Line | Purpose |
|------|------|---------|
| `models.py` | 214-231 | ParallelTaskRequest, ParallelTaskResponse models |
| `services/claude_code.py` | 536-731 | execute_headless_task() function |
| `services/gemini_runtime.py` | 489-642 | execute_headless() for Gemini CLI |
| `services/runtime_adapter.py` | 98-127 | AgentRuntime.execute_headless() interface |
| `routers/chat.py` | 93-133 | POST /api/task endpoint |

### Backend (src/backend/)

| File | Line | Purpose |
|------|------|---------|
| `models.py` | 103-110 | ParallelTaskRequest model with max_turns |
| `routers/chat.py` | 358-475 | POST /api/agents/{name}/task endpoint |

### MCP Server (src/mcp-server/)

| File | Line | Purpose |
|------|------|---------|
| `src/client.ts` | 344-396 | task() method for API calls |
| `src/tools/chat.ts` | 132-270 | chat_with_agent tool with parallel parameter |

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
  "max_turns": 50                // Optional: Max agentic turns (runaway prevention)
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

**Note**: As of 2025-12-31, the `execution_log` is persisted to the `schedule_executions` database table and can be retrieved via `GET /api/agents/{name}/executions/{execution_id}/log`.

### Backend: POST /api/agents/{name}/task

Same request/response as agent server, with additional:
- Authentication via JWT token
- Access control validation
- Activity tracking
- Audit logging
- **Execution log persistence** - Full transcript saved to `schedule_executions.execution_log` *(added 2025-12-31)*

### Backend: GET /api/agents/{name}/executions/{execution_id}/log *(added 2025-12-31)*

Retrieve the full execution log for any task execution.

**File**: `src/backend/routers/schedules.py:426-473`

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
| timeout_seconds | number | 900 | Timeout in seconds (parallel only) |
| max_turns | number | null | Max agentic turns for runaway prevention (parallel only) |

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

**Claude Code** (`docker/base-image/agent_server/services/claude_code.py:604-606`):
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
  ├─► Worker 1: "Process file A" (parallel=true)
  ├─► Worker 2: "Process file B" (parallel=true)
  ├─► Worker 3: "Process file C" (parallel=true)
  ├─► Worker 4: "Process file D" (parallel=true)
  └─► Worker 5: "Process file E" (parallel=true)

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
  ├─► Research Agent 1: "Find info about X" (parallel=true)
  ├─► Research Agent 2: "Find info about Y" (parallel=true)
  └─► Research Agent 3: "Find info about Z" (parallel=true)

Combine results after all complete.
```

## Security Considerations

1. **Access Control**: Same rules as chat - owner, shared, or admin
2. **Rate Limiting**: Consider implementing concurrency limits
3. **Audit Trail**: All parallel tasks logged with user attribution
4. **Tool Restrictions**: `allowed_tools` parameter for sandboxing
5. **Timeout**: Hard limit (`timeout_seconds`) prevents wall-clock runaway
6. **Turn Limit**: `max_turns` prevents infinite agentic loops (added 2026-01-12)

## Future Enhancements

1. **Concurrency Limits**: Agent-level (default 5), platform-level (default 50)
2. **Activity Type**: New `parallel_task` activity type (currently reuses CHAT_START)
3. **Session Persistence**: Optional session persistence with TTL for resume
4. **Batch API**: `POST /api/agents/{name}/batch` for multiple tasks
5. **Priority Queue**: Priority parameter for urgent tasks
