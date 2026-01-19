# Feature: Activity Monitoring (In-Memory Real-Time)

## Overview
Real-time visibility into Claude Code tool execution during agent chat sessions. Shows currently running tools, tool counts, timeline with durations, and drill-down details. This is an **in-memory, ephemeral** system optimized for live monitoring.

**Note**: As of 2025-12-02, this is complemented by the **Unified Activity Stream** (Req 9.7) which provides persistent database tracking. See `activity-stream.md` for the persistent layer.

## User Story
As an agent operator, I want to see what tools Claude is using in real-time so that I can understand agent behavior and debug issues.

## Comparison: In-Memory vs Persistent Activity Tracking

| Feature | Activity Monitoring (This Flow) | Unified Activity Stream |
|---------|--------------------------------|------------------------|
| Storage | In-memory (agent container) | Database (SQLite) |
| Persistence | Lost on container restart | Permanent |
| Scope | Current session only | All sessions, all time |
| Granularity | Tool-level with full I/O | Activity-level with metadata |
| Polling | 5-second HTTP polling | Database queries + WebSocket |
| Purpose | Real-time debugging | Analytics, audit, history |
| Access | Per-agent endpoint | Cross-agent timeline queries |
| Performance | Fast (in-memory) | Indexed queries |

## Entry Points
- **UI**: `src/frontend/src/components/UnifiedActivityPanel.vue` - Activity panel component
- **UI**: `src/frontend/src/views/AgentDetail.vue` - ~~Embedded in chat tab~~ (Chat tab replaced by Terminal, see [agent-terminal.md](agent-terminal.md))
- **API**: `GET /api/agents/{name}/activity` - Poll for activity summary
- **API**: `GET /api/agents/{name}/activity/{tool_id}` - Get full tool call details

---

## Frontend Layer

### Components

**UnifiedActivityPanel.vue** (`src/frontend/src/components/UnifiedActivityPanel.vue`)
- Status indicator with pulsing dot when running
- Tool chips sorted by frequency (Read x12, Bash x5)
- Expanded timeline with timestamps and durations
- Detail modal showing full input/output on click

**AgentDetail.vue** (`src/frontend/src/views/AgentDetail.vue`)
```vue
<UnifiedActivityPanel
  :agent-name="agent.name"
  :activity="sessionActivity"
  :session-cost="sessionInfo.total_cost_usd"
/>
```

### State Management (`src/frontend/src/stores/agents.js`)
```javascript
async getSessionActivity(name) {
  const response = await axios.get(`/api/agents/${name}/activity`, {...})
  return response.data
}

async getActivityDetail(name, toolId) {
  const response = await axios.get(`/api/agents/${name}/activity/${toolId}`, {...})
  return response.data
}
```

### Polling Logic (AgentDetail.vue)
```javascript
const startActivityPolling = () => {
  loadSessionActivity()  // Load immediately
  activityRefreshInterval = setInterval(loadSessionActivity, 5000)  // Every 5 seconds
}
```

---

## Backend Layer (`src/backend/routers/chat.py`)

### Endpoints
| Line | Endpoint | Purpose |
|------|----------|---------|
| 681-723 | `GET /api/agents/{name}/activity` | Activity summary |
| 726-757 | `GET /api/agents/{name}/activity/{tool_id}` | Tool call details |
| 760-790 | `DELETE /api/agents/{name}/activity` | Clear activity |

### Proxy Pattern (`routers/chat.py:681-723`)
```python
@router.get("/{name}/activity")
async def get_agent_activity(name: str, current_user: User = Depends(get_current_user)):
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if container.status != "running":
        return {"status": "idle", "active_tool": None, "tool_counts": {}, ...}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://agent-{name}:8000/api/activity",
                timeout=10.0
            )
            return response.json()
    except httpx.HTTPError:
        return {"status": "idle", ...}  # Graceful fallback
```

---

## Agent Layer (`docker/base-image/agent_server/`)

> **Note**: The agent-server was refactored from a monolithic `agent-server.py` to a modular package at `docker/base-image/agent_server/`. Activity tracking is handled in the routers and state modules.

### Session Activity State (`docker/base-image/agent_server/state.py:68-80`)
```python
def _create_empty_activity(self) -> Dict:
    """Create empty session activity structure"""
    return {
        "status": "idle",
        "active_tool": None,
        "tool_counts": {},
        "timeline": [],
        "totals": {
            "calls": 0,
            "duration_ms": 0,
            "started_at": None
        }
    }
```

Tool outputs stored separately for drill-down (`state.py:40`):
```python
self.tool_outputs: Dict[str, str] = {}
```

### Stream-JSON Parsing (`agent_server/routers/chat.py`)

Claude Code outputs one JSON object per line with `--output-format stream-json`:
```json
{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "...", "name": "Read", "input": {...}}]}}
{"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "...", "content": [...]}]}}
```

### Real-Time Tool Tracking

**start_tool_execution** (`agent_server/routers/chat.py`)
```python
def start_tool_execution(tool_id: str, tool: str, input_data: Dict):
    agent_state.session_activity["status"] = "running"
    agent_state.session_activity["active_tool"] = {
        "name": display_name,
        "input_summary": input_summary,
        "started_at": now.isoformat()
    }
    agent_state.session_activity["timeline"].insert(0, timeline_entry)
    agent_state.session_activity["tool_counts"][display_name] += 1
```

**complete_tool_execution** (`agent_server/routers/chat.py`)
```python
def complete_tool_execution(tool_id: str, success: bool, output: str = None):
    entry["duration_ms"] = duration_ms
    entry["success"] = success
    entry["status"] = "completed"
    agent_state.tool_outputs[tool_id] = output  # Store for drill-down
    agent_state.session_activity["active_tool"] = None
```

### Input Summary Generation (`agent_server/routers/chat.py`)
- Read/Edit/Write: Shows shortened file path
- Grep: Shows pattern
- Bash: Shows first 50 chars of command
- MCP tools: Shows first relevant parameter

---

## Data Structures

### SessionActivity Response
```json
{
  "status": "running",
  "active_tool": {
    "name": "Read",
    "input_summary": ".../main.py",
    "started_at": "2025-11-28T10:30:00.000Z"
  },
  "tool_counts": {
    "Read": 12,
    "Bash": 5,
    "Grep": 3
  },
  "timeline": [
    {
      "id": "tool_123",
      "tool": "Read",
      "input_summary": ".../file.py",
      "duration_ms": 45,
      "success": true,
      "status": "completed"
    }
  ],
  "totals": {
    "calls": 20,
    "duration_ms": 5430
  }
}
```

### ToolCallDetail Response (drill-down)
```json
{
  "id": "tool_123",
  "tool": "Read",
  "input": {"file_path": "/path/to/file.py"},
  "output": "# Full file contents here...",
  "duration_ms": 45,
  "success": true
}
```

---

## ThreadPoolExecutor for Non-blocking I/O

```python
# agent_server/routers/chat.py
_executor = ThreadPoolExecutor(max_workers=2)

# Run blocking subprocess in thread pool - allows polling during execution
loop = asyncio.get_event_loop()
stderr_output, return_code = await loop.run_in_executor(
    _executor, read_subprocess_output
)
```

---

## Side Effects
- **No WebSocket**: Uses polling (5-second interval)
- **No Database**: Activity stored in-memory on agent container
- **No Audit Log**: Activity is ephemeral

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Agent not found | 404 | "Agent not found" |
| Agent not running | 400 | "Agent is not running" |
| Tool call not found | 404 | "Tool call {id} not found" |
| Agent unreachable | (returns empty) | Falls back to empty activity |

---

## Security Considerations

- Authorization via `get_current_user` dependency
- Agent container only accessible via Docker internal network
- Full tool outputs stored only in agent memory (not persisted)
- Output truncated to 5000 chars in drill-down modal

---

## Testing

### Manual Testing
```bash
# Start an agent
curl -X POST http://localhost:8000/api/agents/test-agent/start

# Send a chat message (triggers tool execution)
curl -X POST http://localhost:8000/api/agents/test-agent/chat \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "List all files in the current directory"}'

# Poll activity while agent is working
curl http://localhost:8000/api/agents/test-agent/activity \
  -H "Authorization: Bearer $TOKEN"

# Get specific tool call details
curl http://localhost:8000/api/agents/test-agent/activity/tool_123 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Status
**Last Updated**: 2025-12-30
**Verified**: All line numbers updated for current codebase structure (modular agent_server package)

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-01-12 | **Polling interval optimization**: Changed from 2-second to 5-second polling interval for reduced API load. Updated composable `useSessionActivity.js:117`. |
| 2025-12-30 | **Updated line numbers**: Backend chat.py activity endpoints now at lines 681-790 (moved due to code additions). Updated agent-server references from monolithic `agent-server.py` to modular `agent_server/` package structure. |
| 2025-12-02 | Initial documentation |

---

## Related Flows

- **Upstream**: ~~Agent Chat~~ Agent Terminal (`agent-terminal.md`) or scheduled executions - Triggers Claude Code execution
- **Parallel**: Unified Activity Stream (`activity-stream.md`) - Persistent database tracking (NEW: Req 9.7)
- **Downstream**: None (terminal display feature)

## Complementary Systems

This in-memory activity monitoring system works alongside the persistent activity stream:

1. **In-Memory (This Flow)**: Optimized for real-time UI updates, full tool I/O, current session only
2. **Persistent (activity-stream.md)**: Optimized for historical queries, analytics, cross-agent timelines

Both systems track the same tool executions but serve different purposes. The in-memory system is faster for live monitoring, while the persistent system enables long-term analysis and compliance.
