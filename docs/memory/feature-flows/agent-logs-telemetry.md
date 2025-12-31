# Feature: Agent Logs & Live Telemetry

## Overview
Real-time monitoring of agent containers through logs viewing and live telemetry metrics. Provides visibility into container health (CPU, memory, network) and debugging capability through log output.

## User Story
As a platform user, I want to monitor my agent's resource usage and view logs so that I can debug issues and ensure healthy operation.

---

## Entry Points

### Logs Viewing
- **UI**: `src/frontend/src/views/AgentDetail.vue` - Logs tab
- **API**: `GET /api/agents/{name}/logs?tail=100`

### Live Telemetry
- **UI**: `src/frontend/src/views/AgentDetail.vue` - Header stats bar
- **API**: `GET /api/agents/{name}/stats`

---

## Frontend Layer

### Components

#### AgentDetail.vue - Live Stats Bar
**Location**: `src/frontend/src/views/AgentDetail.vue:123-177`

Displays real-time telemetry in the agent header when status is "running":

| Line | Element | Purpose |
|------|---------|---------|
| 124-128 | Loading indicator | Shows "Loading stats..." with spinner |
| 129-177 | Stats display row | CPU, Memory, Network, Uptime metrics |
| 130-141 | CPU widget | Progress bar with color coding (green/yellow/red) |
| 143-157 | Memory widget | Progress bar showing MB / GB with percentage |
| 159-168 | Network widget | RX (green) and TX (blue) byte counts |
| 170-177 | Uptime widget | Time since container started |

**Color Thresholds**:
- Green: < 50%
- Yellow: 50-80%
- Red: > 80%

#### AgentDetail.vue - Logs Tab
**Location**: `src/frontend/src/views/AgentDetail.vue` (Logs tab content in template)

Features:
- Scrollable log container
- Line count selector: 50, 100, 200, 500
- Auto-refresh toggle
- Manual refresh button
- Smart auto-scroll (pauses when user scrolls up)
- Monospace font display

### State Management

**Location**: `src/frontend/src/stores/agents.js`

```javascript
// Line 125-131: Get agent logs
async getAgentLogs(name, tail = 100) {
  const response = await axios.get(`/api/agents/${name}/logs`, {
    params: { tail },
    headers: authStore.authHeader
  })
  return response.data.logs
}

// Line 183-189: Get agent stats
async getAgentStats(name) {
  const response = await axios.get(`/api/agents/${name}/stats`, {
    headers: authStore.authHeader
  })
  return response.data
}
```

### Reactive State

**Location**: `src/frontend/src/views/AgentDetail.vue` (script section)

```javascript
const logs = ref('')
const logLines = ref(100)           // Lines to fetch: 50, 100, 200, 500
const agentStats = ref(null)        // Live telemetry data
const statsLoading = ref(false)     // Stats loading indicator
const autoRefreshLogs = ref(false)  // Auto-refresh toggle
const userScrolledUp = ref(false)   // Smart scroll tracking
```

### Polling Behavior

**Stats Polling** (when agent is running):
- Interval: 5 seconds
- Method: `startStatsPolling()` in `onMounted()`
- Cleanup: `stopStatsPolling()` in `onUnmounted()`

**Logs Auto-Refresh** (optional):
- Interval: 10 seconds
- User-controlled toggle
- Smart scroll: Auto-scroll to bottom unless user scrolled up

---

## Backend Layer

### Endpoints

#### GET /api/agents/{agent_name}/logs
**File**: `src/backend/routers/agents.py:404-430`

**Handler**:
```python
@router.get("/{agent_name}/logs")
async def get_agent_logs_endpoint(
    agent_name: str,
    request: Request,
    tail: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get agent container logs."""
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        logs = container.logs(tail=tail).decode('utf-8')

        await log_audit_event(
            event_type="agent_access",
            action="view_logs",
            user_id=current_user.username,
            agent_name=agent_name,
            ip_address=request.client.host if request.client else None,
            result="success"
        )

        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")
```

**Parameters**:
- `tail`: Number of lines (default: 100)

**Response**:
```json
{
  "logs": "string with newline-separated log entries"
}
```

#### GET /api/agents/{agent_name}/stats
**File**: `src/backend/routers/agents.py:433-440` (delegates to service layer)
**Business Logic**: `src/backend/services/agent_service/stats.py:101-162`

**Handler** (thin router layer):
```python
@router.get("/{agent_name}/stats")
async def get_agent_stats_endpoint(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get live container stats (CPU, memory, network) for an agent."""
    return await get_agent_stats_logic(agent_name, current_user)
```

**Service Logic** (`services/agent_service/stats.py`):
```python
async def get_agent_stats_logic(agent_name: str, current_user: User) -> dict:
    """Get live container stats (CPU, memory, network) for an agent."""
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    container.reload()
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent is not running")

    stats = container.stats(stream=False)  # One-shot, not streaming

    # Calculate CPU, memory, network, uptime...
    # (See business logic section for calculation details)

    return {
        "cpu_percent": round(cpu_percent, 1),
        "memory_used_bytes": memory_used_actual,
        "memory_limit_bytes": memory_limit,
        "memory_percent": round((memory_used_actual / memory_limit * 100) if memory_limit > 0 else 0, 1),
        "network_rx_bytes": network_rx,
        "network_tx_bytes": network_tx,
        "uptime_seconds": uptime_seconds,
        "status": container.status
    }
```

### Business Logic

> **Note**: Business logic has been refactored from `agents.py` to `services/agent_service/stats.py`

#### CPU Calculation
**Location**: `src/backend/services/agent_service/stats.py:119-130`

```python
cpu_stats = stats.get("cpu_stats", {})
precpu_stats = stats.get("precpu_stats", {})

cpu_delta = cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - \
            precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
system_delta = cpu_stats.get("system_cpu_usage", 0) - \
               precpu_stats.get("system_cpu_usage", 0)

if system_delta > 0 and cpu_delta > 0:
    num_cpus = len(cpu_stats.get("cpu_usage", {}).get("percpu_usage", [])) or 1
    cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
```

#### Memory Calculation
**Location**: `src/backend/services/agent_service/stats.py:132-136`

```python
memory_stats = stats.get("memory_stats", {})
memory_used = memory_stats.get("usage", 0)
memory_limit = memory_stats.get("limit", 0)
cache = memory_stats.get("stats", {}).get("cache", 0)
memory_used_actual = max(0, memory_used - cache)  # Subtract cache
```

#### Network Stats
**Location**: `src/backend/services/agent_service/stats.py:138-140`

```python
networks = stats.get("networks", {})
network_rx = sum(net.get("rx_bytes", 0) for net in networks.values())
network_tx = sum(net.get("tx_bytes", 0) for net in networks.values())
```

#### Uptime Calculation
**Location**: `src/backend/services/agent_service/stats.py:142-149`

```python
started_at = container.attrs.get("State", {}).get("StartedAt", "")
uptime_seconds = 0
if started_at:
    try:
        start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00").split(".")[0])
        uptime_seconds = int((datetime.now(start_time.tzinfo) - start_time).total_seconds())
    except Exception:
        pass
```

---

## Data Layer

### Docker API Operations
- `container.logs(tail=N)` - Fetch last N lines of container stdout/stderr
- `container.stats(stream=False)` - One-shot container metrics
- `container.attrs["State"]["StartedAt"]` - Container start timestamp
- `container.reload()` - Refresh container state

### No Database Operations
This feature reads directly from Docker API - no database persistence.

---

## UI Display

### Telemetry Stats Bar (Header)
| Metric | Display | Color Coding |
|--------|---------|--------------|
| CPU | `XX.X%` with progress bar | Green (<50%), Yellow (50-80%), Red (>80%) |
| Memory | `847 MB / 4 GB` with progress bar | Similar thresholds |
| Network | `↓1.2 MB ↑456 KB` | Green for RX, Blue for TX |
| Uptime | `2h 15m` | Gray |

### Logs Tab Features
- Scrollable container (max-height: 500px)
- Line count selector: 50, 100, 200, 500
- Auto-refresh toggle (10-second interval)
- Manual refresh button
- Smart auto-scroll (pauses when user scrolls up)
- Monospace font with line wrapping

---

## Side Effects

### Audit Logging
**Location**: `src/backend/routers/agents.py:419-425`

```python
await log_audit_event(
    event_type="agent_access",
    action="view_logs",
    user_id=current_user.username,
    agent_name=agent_name,
    ip_address=request.client.host if request.client else None,
    result="success"
)
```

**Note**: Only logs viewing is audited, not stats (too frequent for audit log).

### No WebSocket Broadcasts
Stats and logs are pull-based, not push-based.

---

## Error Handling

| Error Case | HTTP Status | UI Behavior |
|------------|-------------|-------------|
| Agent not found | 404 | Show error toast |
| Agent not running (stats) | 400 | Hide stats bar, show "Stats unavailable" |
| Docker API error | 500 | Log error, don't crash |
| Stats calculation error | 500 | Return error message |

---

## Security Considerations

### Authorization
- Requires authenticated user via `get_current_user`
- Access allowed for owner, shared users, and admins
- No credential data exposed in logs (container logs only)

### Rate Limiting
- 5-second polling interval prevents API overload
- `stream=False` for stats prevents long-running connections

---

## Related Flows

- **Upstream**: [Agent Lifecycle](agent-lifecycle.md) - Container must exist
- **Related**: [Activity Monitoring](activity-monitoring.md) - Real-time tool execution (different data source)
- **Related**: [Agent Chat](agent-chat.md) - Session info also displayed in header

---

## MCP Server Integration

The MCP server provides similar functionality via:
- `get_agent_logs(agent_name, lines)` - Retrieve container logs
- `get_agent(name)` - Get agent status (includes running/stopped)

See [MCP Orchestration](mcp-orchestration.md) for MCP tool details.

---

## Status
**Last Updated**: 2025-12-30
**Verified**: All line numbers updated for current codebase structure

---

## Revision History

| Date | Changes |
|------|---------|
| 2025-12-30 | **Updated for service layer refactor**: Stats logic moved from `agents.py` to `services/agent_service/stats.py`. Logs endpoint now at lines 404-430 (was 558-584). Stats endpoint now at 433-440 delegating to service layer. Updated all business logic line references to stats.py. |
| 2025-12-02 | Initial documentation |
