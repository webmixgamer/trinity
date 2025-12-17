# Feature: Agent Network

## Overview
Real-time visual dashboard that displays all agents as interactive, draggable nodes connected by animated edges that light up when agents communicate with each other. Built with Vue Flow for graph visualization. **This is the main landing page after login.**

## User Story
As a platform user, I want to see a live network graph of all agents and their communications so that I can monitor interaction patterns, identify communication hotspots, and understand the multi-agent ecosystem at a glance.

## Entry Points
- **UI**: `/` route (Dashboard) - Main landing page after authentication
- **Legacy**: `/network` route redirects to `/`
- **WebSocket**: `ws://[host]/ws` - Real-time communication events
- **API**: `GET /api/agents` - Fetch all agents for initial graph rendering

## Architecture Note (2025-12-07)

The Agent Network view was previously a separate page at `/network` (`AgentNetwork.vue`). It has been **merged into Dashboard.vue** as the primary view:

- `AgentNetwork.vue` was **deleted**
- `Dashboard.vue` now contains the complete Agent Network visualization
- `/network` route redirects to `/` (Dashboard)
- NavBar no longer has a separate "Network" link (Dashboard serves this purpose)
- "Communications" terminology changed to "messages" throughout

## Frontend Layer

### Components

#### Dashboard.vue (`src/frontend/src/views/Dashboard.vue`)
Main dashboard view component with integrated Agent Network visualization.

**Key Features** (Updated line references for Dashboard.vue):
- Lines 256-317: Vue Flow canvas with Background, Controls, and MiniMap
- Lines 79-86: Connection status indicator (green/red dot with tooltip)
- Lines 67-77: **Time Range Filter** dropdown (1h, 6h, 24h, 3d, 7d)
- Lines 94-104: Refresh button to reload agents and historical data
- Lines 107-115: Reset Layout button to clear saved positions
- Lines 8-40: **Compact Header** with inline stats (agents, running, plans, messages)
- Lines 44-64: **Live/Replay Mode Toggle** buttons
- Lines 319-396: **Message History Panel** (collapsible) with "Live Feed" and "Historical" sections
- Lines 121-226: **Replay Controls Panel** (visible in replay mode) with playback controls and timeline scrubber

**Lifecycle**:
- Lines 462-482: `onMounted()` - Fetches agents, loads historical communications, connects WebSocket, starts polling, fits view
- Lines 484-488: `onUnmounted()` - Disconnects WebSocket, stops polling on cleanup

**Event Handlers**:
- Lines 490-496: `refreshAll()` - Reloads agents and historical data, refits view
- Lines 498-501: `onTimeRangeChange()` - Updates time filter and reloads data
- Lines 503-508: `resetLayout()` - Clears localStorage positions and refits view
- Lines 510-512: `onNodeDragStop()` - Saves node positions to localStorage
- Lines 514-526: `getNodeColor()` - Maps agent status to minimap colors
- Lines 528-536: `formatTime()` - Human-readable relative timestamps
- Lines 539-578: Replay mode handlers (toggleMode, handlePlay, handlePause, handleStop, etc.)

#### AgentNode.vue (`src/frontend/src/components/AgentNode.vue`)
Custom node component for each agent (updated 2025-12-07).

**Layout** (280px wide, min 160px height):
- Lines 2-11: Clean white card with rounded corners, border, shadow, **flex flex-col** for layout
- Lines 14-18: Top connection handle for incoming edges
- Lines 113-117: Bottom connection handle for outgoing edges

**Header Section**:
- Lines 22-35: Agent name (truncated) with status indicator dot
- Lines 28-34: Status dot with activity-based color (green for active/idle, gray for offline)
- Line 31: Pulsing animation for active agents (`active-pulse` class)

**Status Display**:
- Lines 38-47: Activity state label ("Active", "Idle", "Offline")
- Lines 50-55: GitHub repo display (if from GitHub template)

**Progress Bars**:
- Lines 58-70: Context usage progress bar with percentage and color coding
- Lines 73-102: Task DAG progress (if agent has active plan) with current task and completion bar

**Interaction**:
- Lines 105-110: "View Details" button with `nodrag` class and **mt-auto** for bottom alignment
- Lines 227-229: `viewDetails()` - Navigates to `/agents/:name` on button click

**Computed Properties** (Lines 137-225):
- `activityState`: active, idle, or offline based on `data.activityState`
- `statusDotColor`: Green (#10b981) for active/idle, gray (#9ca3af) for offline
- `contextPercentDisplay`: Rounded context percentage
- `progressBarColor`: Green/Yellow/Orange/Red based on context usage threshold
- `hasActivePlan`, `currentTask`, `completedTasks`, `totalTasks`, `taskProgressPercent`, `taskProgressDisplay`: Task DAG stats
- `showProgressBar`: **UPDATED** - Now always returns `true` for consistent card heights (Line 192-195)
- `taskProgressDisplay`: **UPDATED** - Shows "—" when no tasks, "X/Y" when tasks exist (Line 227-230)

### State Management

#### network.js (`src/frontend/src/stores/network.js`)
Pinia store managing graph state and WebSocket communication.

**State** (Lines 6-19):
- `agents` - Raw agent data from API
- `nodes` - Vue Flow node objects
- `edges` - Vue Flow edge objects
- `communicationHistory` - Last 100 real-time communication events (in-memory)
- `lastEventTime` - Timestamp of most recent event
- `activeCommunications` - Count of currently animated edges
- `websocket` - WebSocket connection instance
- `isConnected` - Connection status boolean
- `nodePositions` - localStorage cache
- `historicalCommunications` - **NEW**: Persistent data from Activity Stream API
- `totalCommunicationCount` - **NEW**: Database count from selected time range
- `timeRangeHours` - **NEW**: Selected filter (1, 6, 24, 72, 168)
- `isLoadingHistory` - **NEW**: Loading indicator for historical data queries

**Computed** (Lines 18-31):
- `activeCommunicationCount` - Number of animated edges (filters `edge.animated === true`)
- `lastEventTimeFormatted` - Human-readable relative time (e.g., "2m ago")

**Actions**:

##### fetchAgents() (Lines 38-46)
```javascript
await axios.get('/api/agents')
// -> convertAgentsToNodes()
```
Fetches all agents and converts to Vue Flow nodes with grid layout.

##### fetchHistoricalCommunications() (Lines 48-107) - **NEW**
```javascript
async function fetchHistoricalCommunications(hours = null) {
  const hoursToQuery = hours || timeRangeHours.value

  // Calculate start time (X hours ago)
  const startTime = new Date()
  startTime.setHours(startTime.getHours() - hoursToQuery)

  const params = {
    activity_types: 'agent_collaboration',
    start_time: startTime.toISOString(),
    limit: 500
  }

  const response = await axios.get('/api/activities/timeline', { params })

  // Parse activities into communication events
  const communications = response.data.activities
    .filter(activity => activity.details)
    .map(activity => ({
      source_agent: details.source_agent,
      target_agent: details.target_agent,
      timestamp: activity.started_at,
      activity_id: activity.id,
      status: activity.activity_state,
      duration_ms: activity.duration_ms
    }))

  historicalCommunications.value = communications
  totalCommunicationCount.value = communications.length

  // Create initial inactive edges from historical data
  createHistoricalEdges(communications)
}
```

Queries Activity Stream API for communication history in selected time range. Creates gray inactive edges on graph with count labels.

##### createHistoricalEdges() (Lines 109-178) - **NEW**
Groups communications by source-target pair and creates inactive edges:
```javascript
// Edge style for historical data
{
  id: `e-${source}-${target}`,
  animated: false,
  className: 'communication-edge-inactive',
  style: {
    stroke: '#cbd5e1',      // Gray
    strokeWidth: 1.5,
    opacity: 0.4
  },
  label: count > 1 ? `${count}x` : undefined,  // Show count
  data: {
    communicationCount: count,
    lastTimestamp: lastTimestamp,
    timestamps: [...]
  }
}
```

##### convertAgentsToNodes() (Lines 234-269)
- Calculates grid layout: `Math.ceil(Math.sqrt(agentList.length))`
- Spacing: 350px between nodes (increased to prevent overlap)
- Loads saved positions from localStorage or uses default grid
- Creates node objects with `type: 'agent'`, draggable, and status data
- **Bug Fix (2025-12-09)**: Sets initial `activityState` based on agent status:
  ```javascript
  activityState: agent.status === 'running' ? 'idle' : 'offline'
  ```
  This prevents running agents from briefly showing "Offline" before the first context-stats poll completes.

##### connectWebSocket() (Lines 78-125)
WebSocket connection with auto-reconnect:
- Line 79: Constructs WebSocket URL from window.location
- Line 84-87: `onopen` - Sets `isConnected = true`
- Line 89-103: `onmessage` - Routes events to handlers:
  - `agent_collaboration` -> `handleCommunicationEvent()`
  - `agent_status` -> `handleAgentStatusChange()`
  - `agent_deleted` -> `handleAgentDeleted()`
- Line 110-121: `onclose` - Reconnects after 5 seconds

##### handleCommunicationEvent() (Lines 263-288) - **ENHANCED**
```javascript
// Event format: {type, source_agent, target_agent, action, timestamp}
1. Add to in-memory history (max 100 events, for real-time feed)
2. Add to historicalCommunications (persistent database-backed list)
3. Increment totalCommunicationCount
4. Update lastEventTime
5. animateEdge(source_agent, target_agent) - converts gray edge to blue
```

**Data Merging**: Real-time WebSocket events are merged with database-backed historical data. When a new communication occurs:
- Real-time feed shows event immediately
- Edge animates blue (or updates existing gray edge)
- Event is persisted to database via activity_service
- After 3 seconds, edge fades back to gray
- Communication count increments (e.g., "5x" -> "6x")

##### animateEdge() (Lines 170-214)
Creates or updates edge with animation:
```javascript
{
  id: `e-${sourceId}-${targetId}`,
  source: sourceId,
  target: targetId,
  type: 'smoothstep',
  animated: true,
  style: { stroke: '#3b82f6', strokeWidth: 3 },
  markerEnd: { type: 'arrowclosed', color: '#3b82f6' }
}
```
- Line 208: Increments `activeCommunications`
- Line 211-213: Sets 3-second timeout to fade edge

##### clearEdgeAnimation() (Lines 216-232)
Fades edge back to inactive state:
```javascript
{
  animated: false,
  style: { stroke: '#94a3b8', strokeWidth: 1.5 },
  markerEnd: { type: 'arrowclosed', color: '#94a3b8' }
}
```

##### saveNodePositions() / loadNodePositions() (Lines 234-250)
- Stores node positions in `localStorage` key: `trinity-network-node-positions`
- Saves on every drag stop event
- Loads on initial render

##### handleAgentStatusChange() (Lines 143-155)
Updates node color when agent starts/stops.

##### handleAgentDeleted() (Lines 157-168)
Removes node and all connected edges.

### Dependencies

**Vue Flow Packages** (`src/frontend/package.json`):
- `@vue-flow/core`: ^1.48.0 - Main graph library
- `@vue-flow/background`: ^1.3.2 - Dot grid background
- `@vue-flow/controls`: ^1.1.3 - Zoom/pan controls
- `@vue-flow/minimap`: ^1.5.4 - Mini overview map

**Imported Styles** (`AgentNetwork.vue:150-154`):
```javascript
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'
```

## Backend Layer

### WebSocket Broadcasting

#### Endpoint Configuration
**File**: `src/backend/main.py`

##### ConnectionManager Class (Lines 43-63)
```python
class ConnectionManager:
    active_connections: List[WebSocket] = []

    async def connect(websocket: WebSocket)
    def disconnect(websocket: WebSocket)
    async def broadcast(message: str)
```

##### WebSocket Endpoint (Lines 137-145)
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    while True:
        await websocket.receive_text()  # Keep-alive
```

##### Manager Injection (Lines 65-70)
WebSocket manager injected into routers:
```python
set_agents_ws_manager(manager)
set_sharing_ws_manager(manager)
set_chat_ws_manager(manager)
```

### Communication Event Detection

**File**: `src/backend/routers/chat.py`

#### set_websocket_manager() (Lines 22-25)
```python
def set_websocket_manager(manager):
    global _websocket_manager
    _websocket_manager = manager
```

#### broadcast_collaboration_event() (Lines 28-41)
```python
async def broadcast_collaboration_event(
    source_agent: str,
    target_agent: str,
    action: str = "chat"
):
    event = {
        "type": "agent_collaboration",
        "source_agent": source_agent,
        "target_agent": target_agent,
        "action": action,
        "timestamp": datetime.utcnow().isoformat()
    }
    await _websocket_manager.broadcast(json.dumps(event))
```

#### Agent-to-Agent Detection (Lines 43-64)
```python
@router.post("/{name}/chat")
async def chat_with_agent(
    name: str,
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    x_source_agent: Optional[str] = Header(None)  # Key detection header
):
    # Lines 59-64: Detect communication
    if x_source_agent:
        await broadcast_collaboration_event(
            source_agent=x_source_agent,
            target_agent=name,
            action="chat"
        )
```

**How It Works**:
1. Agent A calls Trinity MCP tool `trinity_chat_with_agent(target_agent="B", message="...")`
2. MCP server adds `X-Source-Agent: A` header to request
3. Backend detects header presence in `/api/agents/{name}/chat` endpoint
4. Broadcasts WebSocket event to all connected clients
5. Frontend dashboard animates edge from A to B

### Business Logic

**Communication Event Flow**:
1. Validate agent exists and is running (Lines 51-56)
2. Check for `X-Source-Agent` header (Line 59)
3. If present, broadcast communication event (Lines 60-64)
4. Proxy chat message to target agent (Lines 90-96)
5. Persist chat message to database (Lines 74-81, 110-122)
6. Log audit event (Lines 124-131)

## Data Layer

### LocalStorage Persistence

**Key**: `trinity-network-node-positions`

**Schema**:
```json
{
  "agent-name-1": { "x": 100, "y": 100 },
  "agent-name-2": { "x": 350, "y": 100 },
  "agent-name-3": { "x": 100, "y": 350 }
}
```

**Operations**:
- **Save**: On node drag stop (`network.js:234-240`)
- **Load**: On initial render (`network.js:242-250`)
- **Clear**: On "Reset Layout" button (`network.js:252-255`)

### Database Operations

#### Activity Stream Integration (2025-12-02)

**Status**: **IMPLEMENTED** - Full database-backed communication history.

**Table**: `agent_activities` (see `src/backend/database.py`)

**Schema**:
```sql
CREATE TABLE agent_activities (
    id TEXT PRIMARY KEY,                -- UUID
    agent_name TEXT NOT NULL,
    activity_type TEXT NOT NULL,        -- 'agent_collaboration'
    activity_state TEXT DEFAULT 'started',
    parent_activity_id TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_ms INTEGER,
    user_id INTEGER,
    triggered_by TEXT DEFAULT 'user',   -- 'agent' for communications
    details TEXT,                       -- JSON: {source_agent, target_agent, action}
    created_at TEXT NOT NULL
);
```

**API Endpoint**: `GET /api/activities/timeline`

**Query Parameters**:
- `activity_types`: "agent_collaboration"
- `start_time`: ISO 8601 timestamp (e.g., last 24h)
- `end_time`: Optional end boundary
- `limit`: Max results (default 100)

**Access Control**: Filters activities by user's accessible agents (owner, shared, admin).

**See**: [Activity Stream Communication Tracking](activity-stream-collaboration-tracking.md) for complete flow documentation.

## Side Effects

### WebSocket Broadcasts

**Event Type**: `agent_collaboration`

**Payload**:
```json
{
  "type": "agent_collaboration",
  "source_agent": "research-agent",
  "target_agent": "writing-agent",
  "action": "chat",
  "timestamp": "2025-12-01T15:30:45.123456"
}
```

**Broadcast Trigger**: Any agent-to-agent chat request with `X-Source-Agent` header

**Subscribers**: All connected WebSocket clients (all users viewing Agent Network)

### Other WebSocket Events Handled

**Event Type**: `agent_status`
```json
{
  "type": "agent_status",
  "agent_name": "my-agent",
  "status": "running"
}
```
Updates node color in real-time when agents start/stop.

**Event Type**: `agent_deleted`
```json
{
  "type": "agent_deleted",
  "agent_name": "my-agent"
}
```
Removes node and edges from graph.

### Audit Logging

**Not directly logged** - Communication events are ephemeral visualization. The underlying chat messages are logged via:
- `src/backend/routers/chat.py:124-131` - Audit log for agent chat interactions
- `event_type="agent_interaction"`, `action="chat"`

## Error Handling

| Error Case | Handling | User Feedback |
|------------|----------|---------------|
| WebSocket disconnected | Auto-reconnect after 5s | Red status indicator, "Disconnected" |
| WebSocket parse error | Log to console, skip event | Silent (continues listening) |
| Agent fetch failure | Log error, empty graph | "No agents" empty state with icon |
| localStorage quota exceeded | Catch error, continue with defaults | Silent degradation, positions not saved |
| Invalid communication event | Try/catch in onmessage handler | Silent, logged to console |
| Missing agent in graph | Edge creation skipped | Silent (waits for agent refresh) |

**Error Recovery**:
- WebSocket: Automatic reconnection with exponential backoff (5s initial delay)
- Failed broadcasts: Non-blocking, other clients still receive events
- Position persistence: Falls back to grid layout if localStorage unavailable

## Security Considerations

### Authentication
- **Route Protection**: Line 52 in `src/frontend/src/router/index.js` - `meta: { requiresAuth: true }`
- **Auth Guard**: Lines 66-93 check `authStore.isAuthenticated` before access
- **JWT Required**: All API calls include JWT token from Auth0

### Authorization
- **Agent Visibility**: Dashboard shows all agents user has access to (via `GET /api/agents`)
- **No Direct Agent Control**: Nodes link to detail pages where proper access control enforced
- **WebSocket Events**: Broadcast to all authenticated users (no filtering by agent ownership)

### Data Privacy
- **No Sensitive Data**: Communication events only contain agent names and timestamps
- **Message Content**: Not included in communication events (only that communication occurred)
- **LocalStorage**: Only stores node positions (x, y coordinates), no credentials or personal data

### Rate Limiting
- **Not Implemented**: WebSocket broadcasts are lightweight, no throttling needed
- **Future Enhancement**: Could implement event debouncing if communication volume becomes excessive

## Performance Considerations

### Optimization Strategies
1. **Edge Cleanup**: Fades edges after 3 seconds to prevent graph clutter
2. **History Limit**: Max 100 events in `communicationHistory` array
3. **LocalStorage**: Minimal JSON payload (only node positions)
4. **Grid Layout**: O(n) calculation on agent refresh
5. **WebSocket**: Single connection per client, multiplexed events

### Scalability Limits
- **Tested**: Up to 50 agents (grid layout performs well)
- **Performance Degradation**: 100+ agents may require virtual scrolling or clustering
- **Edge Limit**: No limit, but graph becomes visually cluttered with 200+ edges

## Testing

### Prerequisites
1. **Running Services**:
   ```bash
   ./scripts/deploy/start.sh
   ```
2. **Authentication**: Valid Auth0 session or dev mode enabled
3. **Test Agents**: At least 2 running agents for communication testing
4. **Browser**: Chrome/Firefox with WebSocket support

### Test Steps

#### Test Case 1: Dashboard Load and Initial Rendering
**Objective**: Verify dashboard loads with all agents displayed in grid layout

| Step | Action | Expected Result | Verification |
|------|--------|-----------------|--------------|
| 1 | Navigate to `/` (or `/network` which redirects) | Dashboard loads | NavBar shows "Dashboard" as active |
| 2 | Check compact header stats | Shows agent count, running count, plans, messages | Inline stats visible in header |
| 3 | Verify grid layout | All agents positioned in grid | Nodes spaced 350px apart |
| 4 | Check connection status | WebSocket connected | Green dot (not pulsing), no "Disconnected" label |
| 5 | Verify minimap | Minimap shows all nodes | Bottom-right corner shows overview |
| 6 | Check Live/Replay toggle | "Live" button is active (blue) | Default mode is Live |

**Status**: Working (2025-12-07)

#### Test Case 2: Real-Time Communication Detection
**Objective**: Verify edges animate when agents communicate

| Step | Action | Expected Result | Verification |
|------|--------|-----------------|--------------|
| 1 | Open Agent A detail page | Agent A chat interface visible | URL: `/agents/agent-a` |
| 2 | Send message to Agent B via Trinity MCP | Chat executes successfully | Response received in chat |
| 3 | Return to Agent Network | Edge from A->B is blue and animated | Flowing dots visible |
| 4 | Check communication stats | "1 active" communication shown | Header updates immediately |
| 5 | Wait 3 seconds | Edge fades to gray | Animation stops, color changes |
| 6 | Check stats again | "0 active" communications | Counter decrements |

**Status**: Working (2025-12-01)

**Test Command** (from Agent A's MCP tools):
```json
{
  "tool": "trinity_chat_with_agent",
  "arguments": {
    "target_agent": "agent-b",
    "message": "Test communication from Agent A"
  }
}
```

#### Test Case 3: Node Drag and Position Persistence
**Objective**: Verify user can reposition nodes and layout is saved

| Step | Action | Expected Result | Verification |
|------|--------|-----------------|--------------|
| 1 | Drag agent node to new position | Node moves smoothly | Mouse cursor changes to move |
| 2 | Release mouse button | Node stays in new position | Position saved |
| 3 | Check localStorage | Position stored | DevTools -> Application -> localStorage |
| 4 | Refresh page | Node remains in new position | Layout persists across reloads |
| 5 | Click "Reset Layout" | Nodes return to grid | Grid spacing restored |
| 6 | Check localStorage | Positions cleared | Key removed from localStorage |

**Status**: Working (2025-12-01)

**localStorage Key**: `trinity-network-node-positions`

#### Test Case 4: Agent Status Updates
**Objective**: Verify node colors update when agent status changes

| Step | Action | Expected Result | Verification |
|------|--------|-----------------|--------------|
| 1 | Stop a running agent | Node color changes to gray | Gradient: gray-400 to gray-500 |
| 2 | Start the stopped agent | Node color changes to green | Gradient: green-500 to emerald-600 |
| 3 | Check minimap colors | Minimap node color updates | Matches main canvas |
| 4 | Verify status badge | Badge shows "running" / "stopped" | Text updates in node |

**Status**: Working (2025-12-01)

**Status Color Mapping**:
- Running: Green (`#10b981`)
- Stopped: Gray (`#9ca3af`)
- Starting: Yellow (`#f59e0b`)
- Error: Red (`#ef4444`)
- Exited: Dark Gray (`#6b7280`)

#### Test Case 5: WebSocket Reconnection
**Objective**: Verify auto-reconnect when WebSocket drops

| Step | Action | Expected Result | Verification |
|------|--------|-----------------|--------------|
| 1 | Stop backend server | Status changes to "Disconnected" | Red dot, no pulse |
| 2 | Wait 5 seconds | Reconnection attempt logged | Console: "Attempting to reconnect..." |
| 3 | Restart backend server | Connection reestablished | Green pulsing dot returns |
| 4 | Trigger communication event | Edge animates normally | WebSocket functional |

**Status**: Working (2025-12-01)

#### Test Case 6: Multiple Communications
**Objective**: Verify dashboard handles multiple simultaneous communications

| Step | Action | Expected Result | Verification |
|------|--------|-----------------|--------------|
| 1 | Agent A -> Agent B | Edge A->B animates | Blue flowing dots |
| 2 | Agent B -> Agent C | Edge B->C animates | Two edges active |
| 3 | Agent C -> Agent A | Edge C->A animates | Three edges active |
| 4 | Check active count | Shows "3 active" | Header updates |
| 5 | Check history panel | Shows 3 recent events | Bottom-right panel |
| 6 | Wait 3 seconds | All edges fade | "0 active" |

**Status**: Working (2025-12-01)

#### Test Case 7: Agent Deletion
**Objective**: Verify node and edges removed when agent deleted

| Step | Action | Expected Result | Verification |
|------|--------|-----------------|--------------|
| 1 | Create edge A->B via communication | Edge visible | Blue edge exists |
| 2 | Delete Agent B from detail page | Node B disappears | Removed from graph |
| 3 | Check edge A->B | Edge removed | No dangling edge |
| 4 | Check agent count | Decrements by 1 | Header shows new count |

**Status**: Working (2025-12-01)

#### Test Case 8: Click-Through to Agent Detail
**Objective**: Verify "View Details" button navigates correctly

| Step | Action | Expected Result | Verification |
|------|--------|-----------------|--------------|
| 1 | Click "View Details" on node | Navigates to agent page | URL: `/agents/{name}` |
| 2 | Check page load | Agent detail page opens | Tabs visible |
| 3 | Return to dashboard | Dashboard state preserved | Node positions unchanged |

**Status**: Working (2025-12-01)

**Note**: Button has `nodrag` class to prevent drag interference.

### Edge Cases

#### Empty State
- **Scenario**: No agents exist
- **Expected**: Empty state with icon and "Create an agent to get started"
- **Location**: `AgentNetwork.vue:56-67`

#### Single Agent
- **Scenario**: Only one agent exists
- **Expected**: Single node displayed, no edges possible
- **Behavior**: Works correctly (grid with 1 node)

#### Large Graph (50+ Agents)
- **Scenario**: Many agents in grid
- **Expected**: Grid layout may become crowded
- **Mitigation**: Zoom out, pan, use minimap for navigation

#### Rapid Communications
- **Scenario**: Multiple communications within 3-second window
- **Expected**: Edges remain blue until 3s after last event
- **Behavior**: Each edge has independent 3s timer

#### Test Case 9: Historical Data Load and Time Range Filter - **NEW**
**Objective**: Verify Activity Stream integration and time range filtering

| Step | Action | Expected Result | Verification |
|------|--------|-----------------|--------------|
| 1 | Create 10 communications (A->B) | 10 activity records in database | Check `agent_activities` table |
| 2 | Open Agent Network | Gray edge with "10x" label | Historical data loaded |
| 3 | Check header | Shows "10 total (24h)" | Default 24h range |
| 4 | Change filter to "Last Hour" | Counter updates to 0 (if old) | Query with 1h start_time |
| 5 | Trigger new communication | Edge animates blue, count updates | Real-time + historical merge |
| 6 | Refresh page | Gray edge persists with "11x" | Database persistence works |
| 7 | Check history panel | Shows "Live Feed" and "Historical" sections | Dual data sources |

**Status**: Working (2025-12-02)

#### Test Case 10: Access Control for Historical Data - **NEW**
**Objective**: Verify timeline API filters by user access

| Step | Action | Expected Result | Verification |
|------|--------|-----------------|--------------|
| 1 | User A views dashboard | Shows only owned/shared agents | Access control enforced |
| 2 | User B (no shared agents) views dashboard | Empty graph or limited view | Filtered results |
| 3 | Admin views dashboard | Shows all communications | Admin bypass |

**Status**: Working (2025-12-02)

### Known Issues

1. **No Pagination UI**: Timeline API supports pagination but frontend doesn't implement next/prev
2. **No Export**: Historical data can't be exported (CSV, JSON)
3. **No Message Filtering**: Can't filter by specific source/target agent in UI
4. **Grid Layout Only**: No auto-layout algorithms (force-directed, hierarchical)
5. **No Analytics**: No aggregation charts or heatmaps (future enhancement)

### Cleanup
- **WebSocket**: Automatically disconnected on component unmount
- **localStorage**: Preserved unless "Reset Layout" clicked
- **No Backend State**: Dashboard is stateless, no cleanup needed

## Related Flows

### Upstream Flows
- **[Agent Lifecycle](agent-lifecycle.md)**: Agents must exist and be running to appear in graph
- **[Agent-to-Agent Communication](agent-to-agent-collaboration.md)**: Trinity MCP `trinity_chat_with_agent` tool triggers communication events
- **[Auth0 Authentication](auth0-authentication.md)**: User must be authenticated to access dashboard
- **[Activity Stream Communication Tracking](activity-stream-collaboration-tracking.md)**: **NEW** - Complete flow from MCP to database to visualization

### Downstream Flows
- **[Agent Detail](agent-info-display.md)**: "View Details" button navigates to agent page
- **Future**: Analytics dashboard could aggregate communication data for insights

## Future Enhancements

### Planned (REQ-9.6 Extensions)
1. **Communication Analytics**: Heatmaps, most-connected agents, communication patterns
2. **Persistent History**: Database-backed communication logs with search/filter
3. **Edge Weights**: Thickness based on message count or frequency
4. **Agent Grouping**: Cluster nodes by type or project
5. **Auto-Layout**: Force-directed layout option for complex graphs
6. **Export Graph**: PNG/SVG export for documentation
7. **Communication Metrics**: Average response time, message volume charts

### Technical Debt
1. **No Unit Tests**: Add Vitest tests for store actions
2. **No E2E Tests**: Add Playwright tests for dashboard interactions
3. **Hard-coded Timeouts**: Make 3s fade timeout configurable
4. **No Error Boundaries**: Add Vue error handling for component crashes
5. **Accessibility**: Add ARIA labels and keyboard navigation

## Implementation Timeline

### Phase 1: Real-Time Visualization (2025-12-01)
- **2025-12-01 10:00**: Initial implementation started
- **2025-12-01 12:30**: Vue Flow integration complete
- **2025-12-01 14:15**: WebSocket communication detection added
- **2025-12-01 15:45**: Edge animation and fade-out working
- **2025-12-01 16:20**: Position persistence and reset layout implemented
- **2025-12-01 17:00**: Feature complete and tested
- **2025-12-01 21:35**: Bug fixes for User model authentication (added id and email fields)

### Phase 2: Activity Stream Integration (2025-12-02)
- **2025-12-02 08:00**: Activity Stream integration planning
- **2025-12-02 10:30**: Backend activity tracking added to chat router
- **2025-12-02 12:15**: Activities API router created (`/api/activities/timeline`)
- **2025-12-02 14:45**: Frontend historical data loading implemented
- **2025-12-02 15:30**: Time range filter and UI updates complete
- **2025-12-02 16:20**: Data merging (real-time + historical) working
- **2025-12-02 17:30**: Testing, documentation, and feature complete

## Bug Fixes (2025-12-01)

### Issue: User Model Missing Fields
**Problem**: Chat endpoint failed with `AttributeError: 'User' object has no attribute 'id'`

**Root Cause**:
- `src/backend/models.py` User model only had `username` and `role` fields
- Chat persistence code expected `id` and `email` fields from User object
- JWT authentication in `dependencies.py` wasn't populating these fields

**Fix Applied**:
1. Updated `src/backend/models.py` User model:
   ```python
   class User(BaseModel):
       id: int
       username: str
       email: Optional[str] = None
       role: str = "user"
   ```

2. Updated `src/backend/dependencies.py` get_current_user():
   ```python
   return User(
       id=user["id"],
       username=user["username"],
       email=user.get("email"),
       role=user["role"]
   )
   ```

3. Updated all references in `src/backend/routers/chat.py`:
   - Session creation uses `current_user.id` and `current_user.email`
   - Message persistence uses `current_user.id`
   - Access control checks use `current_user.id`

**Files Modified**:
- `src/backend/models.py:42-47`
- `src/backend/dependencies.py:79-84`
- `src/backend/routers/chat.py:67-81, 110-122, 425-429, 463-464, 505-506, 536-537`

**Testing**: Successfully demonstrated with 8 agent-to-agent communications, all WebSocket events broadcast correctly

## UI/UX Enhancements (2025-12-02)

### Context Window Monitoring

**Objective**: Display real-time context usage for each agent with visual progress bars

**Backend Implementation**:

#### New Endpoint: `GET /api/agents/context-stats`
**File**: `src/backend/routers/agents.py:963-1043`

```python
@router.get("/context-stats")
async def get_agents_context_stats(current_user: User = Depends(get_current_user)):
    """
    Get context window stats and activity state for all accessible agents.

    Returns: List of agent stats with context usage and active/idle/offline state
    """
```

**Logic**:
1. Get all accessible agents for current user
2. For each running agent:
   - Fetch context stats from agent's internal API: `http://{container.name}:8000/api/chat/session`
   - Parse response: `context_percent`, `context_tokens`, `context_window`
   - Query recent activity from `agent_activities` table (last 60 seconds)
   - Determine activity state:
     - **Active**: Activity in last 60s with state="started"
     - **Idle**: Running but no recent activity or activity completed
     - **Offline**: Agent not running
3. Return array of stats for all agents

**Response Format**:
```json
{
  "agents": [
    {
      "name": "agent-a",
      "status": "running",
      "activityState": "active",
      "contextPercent": 45.2,
      "contextUsed": 90400,
      "contextMax": 200000,
      "lastActivityTime": "2025-12-02T20:45:30.123456"
    }
  ]
}
```

**Frontend Implementation**:

#### Context Polling Store
**File**: `src/frontend/src/stores/network.js`

**New State**:
- `contextStats`: Map of agent name -> context stats object
- `contextPollingInterval`: Interval ID for cleanup

**New Functions**:
```javascript
fetchContextStats()        // Fetch stats from backend, update node data
startContextPolling()      // Start 5-second interval polling
stopContextPolling()       // Clear interval on unmount
```

**Polling Strategy**:
- Starts on dashboard mount
- Polls every 5 seconds
- Updates node data reactively
- Stops on dashboard unmount

#### Redesigned Agent Node Component
**File**: `src/frontend/src/components/AgentNode.vue`

**Visual Design** (matches mockup):
- Clean white card with subtle shadow
- Agent name in bold gray text
- Activity state label below name
- Context progress bar with percentage
- Status indicator dot (pulses when active)

**Progress Bar Color Coding**:
```javascript
0-49%:   Green   (bg-green-500)
50-74%:  Yellow  (bg-yellow-500)
75-89%:  Orange  (bg-orange-500)
90-100%: Red     (bg-red-500)
```

**Activity States**:
| State | Label | Dot Color | Pulsing | Progress Bar |
|-------|-------|-----------|---------|--------------|
| Active | "Active" | Green (#10b981) | Yes | Visible |
| Idle | "Idle" | Green (#10b981) | No | Visible |
| Offline | "Offline" | Gray (#9ca3af) | No | Hidden |

**Template Structure**:
```vue
<div class="px-5 py-4 rounded-xl border-2 shadow-lg bg-white">
  <!-- Agent name + status dot -->
  <div class="flex items-center justify-between mb-2">
    <div class="text-gray-900 font-bold">{{ data.label }}</div>
    <div :style="{ backgroundColor: statusDotColor }" :class="isActive ? 'animate-pulse' : ''"></div>
  </div>

  <!-- Activity state label -->
  <div class="text-xs font-medium text-green-600">{{ activityStateLabel }}</div>

  <!-- Context progress bar (only for active/idle) -->
  <div v-if="showProgressBar">
    <div class="flex justify-between">
      <span>Context</span>
      <span>{{ contextPercentDisplay }}%</span>
    </div>
    <div class="bg-gray-200 rounded-full h-2">
      <div :class="progressBarColor" :style="{ width: contextPercentDisplay + '%' }"></div>
    </div>
  </div>
</div>
```

### Activity State Detection

**Data Source**: `agent_activities` table

**Detection Logic** (backend):
```python
# Look for activity in last 60 seconds
cutoff_time = (datetime.utcnow() - timedelta(seconds=60)).isoformat()
recent_activities = db.get_agent_activities(agent_name=agent_name, limit=1)

if recent_activities:
    last_activity = recent_activities[0]
    activity_time = last_activity.get("created_at")

    if activity_time > cutoff_time:
        if last_activity.get("activity_state") == "started":
            return "active"   # Currently executing
        else:
            return "idle"     # Recently completed
    else:
        return "idle"         # No recent activity
else:
    return "idle"             # No activity recorded
```

**Activity Types Considered**:
- `chat_start` - Agent processing a chat message
- `tool_call` - Agent executing a tool
- `schedule_start` - Agent running scheduled task
- `agent_collaboration` - Agent communicating with another agent

### Dashboard Lifecycle Integration

**File**: `src/frontend/src/views/AgentNetwork.vue`

**Mounting**:
```javascript
onMounted(async () => {
  await networkStore.fetchAgents()
  await networkStore.fetchHistoricalCommunications()
  networkStore.connectWebSocket()
  networkStore.startContextPolling()  // NEW: Start polling
  fitView({ padding: 0.2, duration: 800 })
})
```

**Unmounting**:
```javascript
onUnmounted(() => {
  networkStore.disconnectWebSocket()
  networkStore.stopContextPolling()  // NEW: Stop polling
})
```

### Performance Considerations

**Polling Frequency**: 5 seconds
- Balance between freshness and API load
- 12 requests/minute for typical dashboard usage
- Async/await prevents request queuing

**Context Fetch Optimization**:
- 2-second timeout per agent API call
- Parallel fetches using httpx.AsyncClient
- Graceful degradation on timeout (shows 0%)
- No blocking of other endpoints

**Frontend Reactivity**:
- Vue Flow auto-updates when node data changes
- Progress bar width transitions smoothly (500ms)
- No full re-render, only affected nodes update

### Testing

**Test Case**: Context Progress Bar Display
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Chat with agent | Context percent increases |
| 2 | Wait 5 seconds | Dashboard updates with new percentage |
| 3 | Check progress bar color | Green -> Yellow -> Orange -> Red as usage grows |
| 4 | Stop agent | Progress bar disappears, state shows "Offline" |

**Test Case**: Activity State Transitions
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Agent idle | Shows "Idle" with green dot (not pulsing) |
| 2 | Send chat message | Within 5s, shows "Active" with pulsing green dot |
| 3 | Wait 60 seconds after chat completes | Returns to "Idle" |
| 4 | Stop agent | Shows "Offline" with gray dot |

**Status**: Working (2025-12-02)

---

## Bug Fixes & UX Improvements

### 2025-12-02: Agent Network UX Fixes

#### Issue #1: History Panel Always Visible
**Problem**: Communication history panel permanently visible, cluttering main graph view

**Solution**: Made panel collapsible with toggle button
- Added floating button (clipboard icon) in bottom-right corner
- Panel starts closed by default
- Smooth slide-in/slide-out animations
- Button repositions when panel opens to avoid overlap
- State stored in `isHistoryPanelOpen` ref

**Files Modified**:
- `AgentNetwork.vue:295-307` - Toggle button HTML
- `AgentNetwork.vue:310-312` - Conditional panel display with `isHistoryPanelOpen`
- `AgentNetwork.vue:423` - State variable initialization

#### Issue #2: Agents Showing as Offline (Critical Bug)
**Problem**: All agents displayed "Offline" status despite being running. Context progress bars and activity state not showing.

**Root Cause**: FastAPI route ordering bug
- `/context-stats` endpoint defined at line 963 (after `/{agent_name}` at line 93)
- FastAPI matches routes in order - `/{agent_name}` is a catch-all pattern
- Request to `/api/agents/context-stats` matched as `agent_name="context-stats"`
- Returned 404 instead of agent stats

**Solution**: Moved `/context-stats` endpoint before catch-all route
- New position: Line 93 (before `/{agent_name}` at line 174)
- Backend restarted to apply fix
- Endpoint now responds correctly with agent status, context percentage, activity state

**Files Modified**:
- `src/backend/routers/agents.py` - Moved entire endpoint (81 lines)

**Backend Logs Evidence**:
```
INFO: 172.28.0.6:57436 - "GET /api/agents/context-stats HTTP/1.1" 404 Not Found  # BEFORE
INFO: 172.28.0.6:57454 - "GET /api/agents/context-stats HTTP/1.1" 200 OK         # AFTER
```

**Impact**:
- Agent nodes now correctly show Active/Idle/Offline status
- Pulsing green dots for active agents
- Context progress bars display with color coding (green/yellow/orange/red)
- Activity state updates every 5 seconds via polling

#### Issue #3: Time Range Selector Purpose Unclear
**Problem**: "Time Range:" label ambiguous - users unclear what it controls

**Solution**: Improved labeling and added context
- Changed label: "Time Range:" -> "History:" with clock icon
- Added tooltip: "How far back to load communication history"
- Clarified that it filters initial historical data load (both Live and Replay modes)

**Files Modified**:
- `AgentNetwork.vue:43-62` - Updated label, added icon, added tooltip

**User Guidance**:
- "History:" clearly indicates it controls historical data scope
- Clock icon provides visual hint
- Tooltip explains exact behavior on hover
- Useful in both Live (initial load) and Replay (timeline scope) modes

---

## Revision History

| Date | Changes |
|------|---------|
| 2025-12-09 | **Bug Fix - Agent Status Display**: Added initial `activityState` to node data in `convertAgentsToNodes()`. Running agents now show "Idle" immediately instead of "Offline" until first context-stats poll. |
| 2025-12-07 | **Task progress bar consistency**: Removed `v-if="hasActivePlan"` condition from Task DAG Progress section. Now always shows Tasks progress bar for consistent card heights across all agents. Added `taskProgressDisplay` computed to show "—" when no tasks. |
| 2025-12-07 | **AgentNode.vue fixes**: Added `flex flex-col` to card container for consistent layout. Changed `showProgressBar` computed to always return `true` for consistent card heights. Added `mt-auto` to "View Details" button to align at bottom. |
| 2025-12-07 | **Major refactor**: Merged AgentNetwork.vue into Dashboard.vue. Dashboard is now the main landing page at `/`. Deleted AgentNetwork.vue. Updated NavBar (removed Network link). Renamed "communications" to "messages". Consolidated header into compact single row. |
| 2025-12-07 | Terminology refactor: Collaboration Dashboard -> Agent Network, collaborations -> communications |
| 2025-12-02 | Activity Stream integration, context monitoring, UX fixes |
| 2025-12-01 | Initial implementation with real-time visualization |

---

## References

### Code Files
- `/Users/eugene/Dropbox/Coding/N8N_Main_repos/project_trinity/src/frontend/src/views/Dashboard.vue` - Main view with Agent Network visualization
- `/Users/eugene/Dropbox/Coding/N8N_Main_repos/project_trinity/src/frontend/src/components/AgentNode.vue` - Custom Vue Flow node
- `/Users/eugene/Dropbox/Coding/N8N_Main_repos/project_trinity/src/frontend/src/stores/network.js` - Pinia store for graph state
- `/Users/eugene/Dropbox/Coding/N8N_Main_repos/project_trinity/src/frontend/src/router/index.js` - Routes (/ for Dashboard, /network redirects to /)
- `/Users/eugene/Dropbox/Coding/N8N_Main_repos/project_trinity/src/frontend/src/components/NavBar.vue` - Navigation (Dashboard link)
- `/Users/eugene/Dropbox/Coding/N8N_Main_repos/project_trinity/src/backend/routers/chat.py` - WebSocket broadcast for messages
- `/Users/eugene/Dropbox/Coding/N8N_Main_repos/project_trinity/src/backend/main.py` - WebSocket endpoint

### Deleted Files
- `src/frontend/src/views/AgentNetwork.vue` - Merged into Dashboard.vue (2025-12-07)

### Documentation
- **Requirements**: `docs/memory/requirements.md:570-585` (REQ-9.6)
- **Vue Flow Docs**: https://vueflow.dev/
- **WebSocket API**: MDN WebSocket Documentation

### Related MCP Tools
- `trinity_chat_with_agent` - Triggers communication events
- `trinity_list_agents` - Fetches agent list for graph
- `trinity_get_agent_info` - Agent metadata for nodes
