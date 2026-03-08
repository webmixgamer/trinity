# Operating Room (OPS-001)

> **Status**: Implemented (Phases 1-4)
> **Requirements**: [OPERATOR_QUEUE_OPERATING_ROOM.md](../../requirements/OPERATOR_QUEUE_OPERATING_ROOM.md)
> **Tests**: `tests/test_operator_queue.py`

---

## Overview

The Operating Room is a unified inbox where operators monitor and respond to agent requests in real time. Agents communicate through a standardized file-based protocol (`~/.trinity/operator-queue.json`), which the platform syncs to a database and presents as actionable cards.

Three request types:
- **Approval** -- Agent needs a yes/no or multi-choice decision
- **Question** -- Agent needs freeform guidance
- **Alert** -- Agent is reporting a situation (acknowledgement only)

## User Story

As an operator, I want a single inbox where I can see and respond to all agent requests so that I can manage my fleet efficiently without switching between terminals.

---

## Entry Points

- **UI**: `src/frontend/src/views/OperatingRoom.vue` -- `/operating-room` route
- **API**: `GET /api/operator-queue` -- List queue items
- **API**: `POST /api/operator-queue/{id}/respond` -- Submit response
- **API**: `GET /api/operator-queue/stats` -- Queue statistics
- **NavBar**: Badge count on "Ops" link (`src/frontend/src/components/NavBar.vue:40-53`)
- **Agent**: Writes `~/.trinity/operator-queue.json` inside container

---

## Frontend Layer

### Components

| File | Lines | Purpose |
|------|-------|---------|
| `src/frontend/src/views/OperatingRoom.vue` | 1-109 | Main page -- card feed with Open/Resolved tabs, starts polling on mount |
| `src/frontend/src/components/operator/QueueCard.vue` | 1-257 | Expandable card -- agent avatar, markdown body, inline response controls |
| `src/frontend/src/components/operator/ResolvedCard.vue` | 1-68 | Compact resolved item -- checkmark, response text, timestamp |
| `src/frontend/src/components/operator/QueueList.vue` | 1-195 | Filterable list view (type, priority, agent, status) with priority indicators |
| `src/frontend/src/components/operator/QueueStats.vue` | 1-88 | Stats sidebar -- pending by priority, today's total, avg response time, by agent |
| `src/frontend/src/components/operator/QueueItemDetail.vue` | 1-286 | Detail panel -- full item view with response controls (approval/question/alert) |
| `src/frontend/src/components/NavBar.vue` | 40-53 | "Ops" nav link with live pending count badge |

### Route

```
/operating-room -> OperatingRoom.vue (requiresAuth: true)
```

Registered in `src/frontend/src/router/index.js:135-139`:
```javascript
{
  path: '/operating-room',
  name: 'OperatingRoom',
  component: () => import('../views/OperatingRoom.vue'),
  meta: { requiresAuth: true }
}
```

### State Management

**Store**: `src/frontend/src/stores/operatorQueue.js` (194 lines)

**State:**
- `items` (ref) -- Array of queue items from backend API
- `expandedItemId` (ref) -- Currently expanded card (null = none)
- `activeTab` (ref) -- `'open'` or `'resolved'`
- `loading` (ref) -- Loading state
- `error` (ref) -- Error message

**Getters (computed):**
- `openItems` -- Pending items sorted by priority order (critical=0, high=1, medium=2, low=3), then by created_at ascending
- `resolvedItems` -- Items with status responded/acknowledged, sorted by responded_at descending
- `pendingCount` -- Count of items with status=pending (drives NavBar badge)
- `criticalCount` -- Count of pending items with priority=critical (drives badge color: red+pulse vs orange)
- `openItemsByAgent` -- Open items grouped by agent_name
- `getProfile(agentName)` -- Returns `{initials, color, role}` using deterministic hash of agent name against 8 Tailwind colors

**Actions:**
- `fetchItems()` -- `GET /api/operator-queue?limit=200` with auth header (line 82-97)
- `respondToItem(id, response, responseText)` -- `POST /api/operator-queue/{id}/respond`, optimistic local update, auto-advance to next open item (line 99-126)
- `acknowledgeItem(id)` -- Shorthand that calls `respondToItem(id, 'acknowledged', '')` (line 128-130)
- `toggleExpand(id)` -- Toggle expandedItemId (line 132-134)
- `handleWebSocketEvent(data)` -- Handles real-time updates from WebSocket (line 137-157)
- `startPolling(interval)` -- Begin polling with initial fetch + setInterval (default 15s, called with 10s from OperatingRoom.vue) (line 160-164)
- `stopPolling()` -- Clear poll timer (line 166-171)

### API Calls

```javascript
// List items (fetchItems)
await axios.get('/api/operator-queue', {
  params: { limit: 200 },
  headers: authStore.authHeader
})

// Respond to item (respondToItem)
await axios.post(`/api/operator-queue/${id}/respond`, {
  response: response,
  response_text: responseText || null
}, { headers: authStore.authHeader })
```

### WebSocket Events

Handled in `src/frontend/src/utils/websocket.js:96-98`:

Events are keyed by `type` (not `event`), dispatched from the `default` case in the WebSocket message handler:

```javascript
if (data.type === 'operator_queue_new' ||
    data.type === 'operator_queue_responded' ||
    data.type === 'operator_queue_acknowledged') {
  operatorQueueStore.handleWebSocketEvent(data)
}
```

Event handling in the store (`handleWebSocketEvent`, line 137-157):
- `operator_queue_new` -- Triggers full `fetchItems()` refetch to get complete item data
- `operator_queue_responded` -- Updates item status, response, and responded_by locally (avoids refetch)
- `operator_queue_acknowledged` -- Updates item status to 'acknowledged' locally

### Response Controls by Type

| Type | UI Control (QueueCard.vue) | Submit Action |
|------|---------------------------|---------------|
| Approval | Option buttons (green/red/blue border) + optional text input + Send (line 99-133) | `respondToItem(id, selectedOption, note)` |
| Question | Textarea + "Send Answer" button (line 136-156) | `respondToItem(id, answerText, '')` |
| Alert | "Got it" button (line 159-166) | `acknowledgeItem(id)` |

### NavBar Badge

`src/frontend/src/components/NavBar.vue:40-53`:

- Imports `useOperatorQueueStore` (line 229, 238)
- Badge shows `operatorQueueStore.pendingCount` with max display of "99+"
- Color: `bg-red-500 animate-pulse` when `criticalCount > 0`, otherwise `bg-orange-500`
- Badge hidden when `pendingCount === 0`

### UX Behaviors

1. **Auto-expand first item** on page load -- `watch` on `openItems.length` in `OperatingRoom.vue:104-108`
2. **Auto-advance** after responding -- next open item expands automatically (store `respondToItem` line 119-122)
3. **Collapse on click** -- X button in QueueCard header (`@click.stop="store.toggleExpand(item.id)"` line 52)
4. **Context collapsible** -- "Show details" toggle in QueueCard (line 70-94)
5. **Badge in NavBar** -- Orange for pending, red+pulse for critical
6. **Polling fallback** -- 10s interval from OperatingRoom.vue, 15s default in store
7. **Form reset** -- `watch(isExpanded)` in QueueCard resets selectedOption, responseText, showContext on collapse (line 191-197)

---

## Backend Layer

### Registration

**`src/backend/main.py`**:
- Router import: line 70 -- `from routers.operator_queue import router as operator_queue_router, set_websocket_manager as set_operator_queue_ws_manager`
- Sync service import: line 82 -- `from services.operator_queue_service import operator_queue_service, set_websocket_manager as set_opqueue_sync_ws_manager`
- WebSocket manager injection: line 193-194 -- `set_operator_queue_ws_manager(manager)` and `set_opqueue_sync_ws_manager(manager)`
- Router registration: line 357 -- `app.include_router(operator_queue_router)`
- Service start (lifespan): line 254-258 -- `operator_queue_service.start()`
- Service stop (lifespan): line 290-294 -- `operator_queue_service.stop()`

### Endpoints

**Router**: `src/backend/routers/operator_queue.py` (164 lines)

Prefix: `/api/operator-queue`, Tags: `["operator-queue"]`

All endpoints require JWT authentication via `get_current_user` dependency.

| Method | Path | Handler | Line | Description |
|--------|------|---------|------|-------------|
| GET | `/api/operator-queue` | `list_queue_items()` | 45-66 | List with filters: status, type, priority, agent_name, since, limit (1-500, default 100), offset |
| GET | `/api/operator-queue/stats` | `get_queue_stats()` | 69-74 | Counts by status/type/priority/agent, avg response time, responded today |
| GET | `/api/operator-queue/{item_id}` | `get_queue_item()` | 77-86 | Single item by ID; 404 if not found |
| POST | `/api/operator-queue/{item_id}/respond` | `respond_to_queue_item()` | 89-127 | Submit operator response. Validates status=pending, broadcasts WebSocket event |
| POST | `/api/operator-queue/{item_id}/cancel` | `cancel_queue_item()` | 130-147 | Cancel pending item. Validates status=pending |
| GET | `/api/operator-queue/agents/{agent_name}` | `get_agent_queue_items()` | 150-163 | Items for specific agent with optional status filter, limit (1-500, default 50) |

**Request model** (line 35-38):
```python
class OperatorResponse(BaseModel):
    response: str
    response_text: Optional[str] = None
```

**Respond endpoint flow** (line 89-127):
1. Fetch existing item from DB
2. Validate item exists (404 if not)
3. Validate item status is "pending" (400 if not)
4. Call `db.respond_to_operator_queue_item()` with response, user ID, user email
5. Broadcast `operator_queue_responded` WebSocket event via `_websocket_manager`
6. Return updated item

**WebSocket broadcast payload** (line 117-125):
```json
{
  "type": "operator_queue_responded",
  "data": {
    "id": "<item_id>",
    "agent_name": "<agent_name>",
    "responded_by_email": "<user_email>",
    "response": "<response_text>"
  }
}
```

### Sync Service

**File**: `src/backend/services/operator_queue_service.py` (239 lines)

Background async service that bridges agent containers and the database. Global singleton instance at line 238.

**Constants**:
- `QUEUE_FILE_PATH = ".trinity/operator-queue.json"` (line 30)
- `DEFAULT_POLL_INTERVAL = 5` seconds (line 31)

**Poll cycle** (`_poll_cycle`, line 79-100):
1. Gets running agents via `list_all_agents_fast()` (lazy import from `services.docker_service`)
2. Filters to only `status == "running"` agents
3. Calls `db.mark_operator_queue_expired()` for items past `expires_at`
4. Concurrently syncs each agent via `asyncio.gather(*tasks)`

**Agent sync** (`_sync_agent`, line 102-188):
1. Creates `AgentClient(agent_name)` and reads `~/.trinity/operator-queue.json` via `client.read_file()` with 5s timeout
2. Parses JSON, iterates `requests` array
3. For each request with `status=pending` not already in DB: creates DB record via `db.create_operator_queue_item()`, adds to `new_items` list
4. For each request with `status=acknowledged`: marks acknowledged in DB via `db.mark_operator_queue_acknowledged()`
5. Broadcasts `operator_queue_new` WebSocket events for new items (line 155-170)
6. Broadcasts `operator_queue_acknowledged` WebSocket events for acknowledged items (line 172-183)
7. Checks for `responded` items via `db.get_operator_queue_responded_for_agent()`, writes responses back to agent

**Response write-back** (`_write_responses_to_agent`, line 190-234):
1. Builds lookup map of responded items by ID
2. Iterates agent's JSON requests, updates matching pending items with response data
3. Writes updated JSON back to agent via `client.write_file(QUEUE_FILE_PATH, content, timeout=10.0, platform=True)`
4. Sets `status=responded`, `response`, `response_text`, `responded_by`, `responded_at` fields in the agent's JSON

**WebSocket broadcast payloads**:

`operator_queue_new` (line 158-168):
```json
{
  "type": "operator_queue_new",
  "data": {
    "id": "<item_id>",
    "agent_name": "<agent_name>",
    "type": "approval|question|alert",
    "priority": "critical|high|medium|low",
    "title": "<title>",
    "created_at": "<iso_timestamp>"
  }
}
```

`operator_queue_acknowledged` (line 175-182):
```json
{
  "type": "operator_queue_acknowledged",
  "data": {
    "id": "<item_id>",
    "agent_name": "<agent_name>"
  }
}
```

**Lifecycle**: Started in `main.py` lifespan (line 254-258), stopped on shutdown (line 290-294).

### Database Delegation

**File**: `src/backend/database.py` (lines 1195-1230)

`DatabaseManager` delegates to `self._operator_queue_ops` (initialized at line 254 as `OperatorQueueOperations()`):

| DatabaseManager Method | Delegates To | Line |
|----------------------|-------------|------|
| `create_operator_queue_item(agent_name, item)` | `create_item()` | 1199-1200 |
| `get_operator_queue_item(item_id)` | `get_item()` | 1202-1203 |
| `list_operator_queue_items(**kwargs)` | `list_items()` | 1205-1206 |
| `respond_to_operator_queue_item(...)` | `respond_to_item()` | 1208-1212 |
| `cancel_operator_queue_item(item_id)` | `cancel_item()` | 1214-1215 |
| `mark_operator_queue_acknowledged(item_id)` | `mark_acknowledged()` | 1217-1218 |
| `mark_operator_queue_expired()` | `mark_expired()` | 1220-1221 |
| `get_operator_queue_stats()` | `get_stats()` | 1223-1224 |
| `get_operator_queue_responded_for_agent(agent_name)` | `get_responded_items_for_agent()` | 1226-1227 |
| `operator_queue_item_exists(item_id)` | `item_exists()` | 1229-1230 |

---

## Data Layer

### Database Table

**Table**: `operator_queue` (in `src/backend/db/schema.py:531-553`)

```sql
CREATE TABLE IF NOT EXISTS operator_queue (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    priority TEXT NOT NULL DEFAULT 'medium',
    title TEXT NOT NULL,
    question TEXT NOT NULL,
    options TEXT,                    -- JSON array for approval type
    context TEXT,                    -- JSON object metadata from agent
    execution_id TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    response TEXT,
    response_text TEXT,
    responded_by_id TEXT,
    responded_by_email TEXT,
    responded_at TEXT,
    acknowledged_at TEXT,
    FOREIGN KEY (responded_by_id) REFERENCES users(id)
)
```

**Indexes** (`src/backend/db/schema.py:699-704`):
```sql
CREATE INDEX IF NOT EXISTS idx_operator_queue_agent ON operator_queue(agent_name);
CREATE INDEX IF NOT EXISTS idx_operator_queue_status ON operator_queue(status);
CREATE INDEX IF NOT EXISTS idx_operator_queue_priority ON operator_queue(priority);
CREATE INDEX IF NOT EXISTS idx_operator_queue_type ON operator_queue(type);
CREATE INDEX IF NOT EXISTS idx_operator_queue_created ON operator_queue(created_at DESC);
```

### Database Operations

**File**: `src/backend/db/operator_queue.py` (335 lines) -- `OperatorQueueOperations` class

| Method | Line | Description |
|--------|------|-------------|
| `_row_to_item(row)` | 20-41 | Convert DB row (18 columns) to dict, JSON-parses options and context |
| `create_item(agent_name, item)` | 50-86 | INSERT OR IGNORE from agent JSON data. Extracts execution_id from `context.execution_id` |
| `get_item(item_id)` | 88-100 | SELECT single item by ID |
| `list_items(...)` | 102-153 | Filtered list with dynamic WHERE clauses. Sort: pending first, then by priority order, then created_at DESC |
| `respond_to_item(...)` | 155-192 | UPDATE status=responded WHERE status=pending. Sets response, responded_by_id, responded_by_email, responded_at |
| `cancel_item(item_id)` | 194-210 | UPDATE status=cancelled WHERE status=pending |
| `mark_acknowledged(item_id)` | 212-223 | UPDATE status=acknowledged WHERE status=responded. Sets acknowledged_at |
| `mark_expired()` | 225-241 | UPDATE status=expired WHERE status=pending AND expires_at < now. Returns count |
| `get_stats()` | 243-306 | Aggregate counts by status, type (pending), priority (pending), agent (pending). Calculates avg_response_seconds and responded_today |
| `get_pending_item_ids()` | 308-313 | SELECT id WHERE status=pending |
| `get_responded_items_for_agent(agent_name)` | 315-327 | SELECT WHERE agent_name=? AND status=responded (for sync service write-back) |
| `item_exists(item_id)` | 329-334 | SELECT 1 existence check |

**List query sort order** (line 133-144):
```sql
ORDER BY
    CASE status WHEN 'pending' THEN 0 ELSE 1 END,
    CASE priority
        WHEN 'critical' THEN 0
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
        ELSE 4
    END,
    created_at DESC
LIMIT ? OFFSET ?
```

---

## Agent Protocol

### File Format

Agents write to `~/.trinity/operator-queue.json`:

```json
{
  "$schema": "operator-queue-v1",
  "requests": [
    {
      "id": "req-20260307-001",
      "type": "approval",
      "status": "pending",
      "priority": "high",
      "title": "Short summary",
      "question": "Full description. Markdown supported.",
      "options": ["approve", "reject"],
      "context": { "key": "value" },
      "created_at": "2026-03-07T10:00:00Z"
    }
  ]
}
```

### Status Lifecycle

```
Agent creates -> pending -> responded (by operator) -> acknowledged (by agent)
                         -> cancelled (by operator)
                         -> expired (by platform, if expires_at passed)
```

### Meta-Prompt Integration

**File**: `config/trinity-meta-prompt/prompt.md`

Contains "Operator Communication" section that instructs agents on:
- The file-based queue protocol and JSON schema
- Three request types and when to use them
- How to check for and acknowledge responses
- File hygiene rules (keep minimal items in JSON)

---

## Side Effects

- **WebSocket broadcast**: `operator_queue_new` -- When new items are synced from agents (sync service, line 155-170)
- **WebSocket broadcast**: `operator_queue_responded` -- When operator submits response (router, line 116-125)
- **WebSocket broadcast**: `operator_queue_acknowledged` -- When agent acknowledges response (sync service, line 172-183)
- **File write**: Response data written back to agent container JSON via `AgentClient.write_file()` (sync service, line 218-234)
- **NavBar badge**: Updates pending count in real time via WebSocket events and polling

---

## Error Handling

| Error Case | HTTP Status | Message | Source |
|------------|-------------|---------|--------|
| Item not found | 404 | "Queue item not found" | `operator_queue.py:85,99,137` |
| Respond to non-pending | 400 | "Cannot respond to item with status '{status}'" | `operator_queue.py:101-105` |
| Cancel non-pending | 400 | "Cannot cancel item with status '{status}'" | `operator_queue.py:140-144` |
| Missing response body | 422 | Validation error (Pydantic) | FastAPI automatic |
| Unauthenticated | 401 | "Not authenticated" | `get_current_user` dependency |
| Invalid JSON in agent file | -- | Logged as warning, skipped | `operator_queue_service.py:123` |
| Agent unreachable | -- | Silently skipped (no log) | `operator_queue_service.py:109-111` |
| Write-back failure | -- | Logged as warning/error | `operator_queue_service.py:230-234` |

---

## Testing

### Test File

`tests/test_operator_queue.py` -- registered in `tests/registry.json`

### Test Categories

- **Authentication** (6 tests): All endpoints require JWT auth
- **List items** (10 tests): Structure, pagination, filters, validation
- **Get item** (2 tests): Found and not found cases
- **Stats** (6 tests): Response structure and field types
- **Respond** (5 tests): Happy path, already responded, not found, validation
- **Cancel** (3 tests): Happy path, already responded, not found
- **Agent items** (5 tests): Per-agent queries, filters, empty results

### Prerequisites

- Backend running at `http://localhost:8000`
- Admin user authenticated
- Queue items present (seeded by sync service or direct DB insert)

### Test Steps

1. **List items**: `GET /api/operator-queue` -> 200 with `{items, count}`
2. **Filter by status**: `GET /api/operator-queue?status=pending` -> only pending items
3. **Get stats**: `GET /api/operator-queue/stats` -> `{by_status, by_type, ...}`
4. **Respond to item**: `POST /api/operator-queue/{id}/respond` -> 200, status=responded
5. **Cancel item**: `POST /api/operator-queue/{id}/cancel` -> 200, status=cancelled

---

## Complete Data Flow

### Flow 1: Agent Creates Request -> Operator Sees It

```
1. Agent writes ~/.trinity/operator-queue.json with new request (status=pending)
2. OperatorQueueSyncService._poll_cycle() runs every 5s
3. _sync_agent() reads file via AgentClient.read_file()
4. New item detected (not in DB) -> db.create_operator_queue_item()
5. WebSocket broadcast: {type: "operator_queue_new", data: {...}}
6. websocket.js dispatches to operatorQueueStore.handleWebSocketEvent()
7. Store calls fetchItems() -> GET /api/operator-queue
8. OperatingRoom.vue re-renders with new card
9. NavBar badge count updates via computed pendingCount
```

### Flow 2: Operator Responds to Request

```
1. User clicks option button or types answer in QueueCard.vue
2. submitApproval() / submitAnswer() calls store.respondToItem()
3. POST /api/operator-queue/{id}/respond -> router respond_to_queue_item()
4. Router validates item exists and status=pending
5. db.respond_to_operator_queue_item() -> UPDATE status=responded
6. Router broadcasts WebSocket: {type: "operator_queue_responded", data: {...}}
7. Store optimistic update: item.status = 'responded'
8. Store auto-advances: expands next open item
9. Next sync cycle: _sync_agent() finds responded items
10. _write_responses_to_agent() writes response back to agent's JSON file
11. Agent reads updated JSON, processes response, sets status=acknowledged
12. Next sync cycle detects acknowledged -> db.mark_operator_queue_acknowledged()
13. WebSocket broadcast: {type: "operator_queue_acknowledged", data: {...}}
```

### Flow 3: Item Expiration

```
1. Agent creates request with expires_at field
2. OperatorQueueSyncService._poll_cycle() calls db.mark_operator_queue_expired()
3. SQL: UPDATE status=expired WHERE status=pending AND expires_at < now
4. Item no longer appears in open items on next fetch
```

---

## UI Layout

```
+------------------------------------------+
| Operating Room                            |
| Your agents need your input on N items    |
|                                           |
| [Open (5)]  [Resolved]                    |
|                                           |
| +-- Card (expanded) --------------------+ |
| | (DA) deploy-agent . 2m ago         X  | |
| | Deploy PR #47 to production?          | |
| | [Needs approval] [critical]           | |
| | ____________________________________  | |
| | PR #47 has 47 changed files...        | |
| |                                       | |
| | > Show details                        | |
| |                                       | |
| | [Approve] [Reject] [Defer]           | |
| | [Add a note...          ] [Send]      | |
| +---------------------------------------+ |
|                                           |
| +-- Card (collapsed) -------------------+ |
| | (CA) content-agent . 1m ago           | |
| | OpenAI API rate limit exceeded        | |
| | [Heads up] [critical]                 | |
| +---------------------------------------+ |
+------------------------------------------+
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Layout | Single-column card feed | Calm, inbox-like -- not a dense operational dashboard |
| Agent identity | Avatar + name on every card | Users associate items with agents, not types |
| Response UX | Inline expand with auto-advance | Process items sequentially like messages |
| Context display | Collapsible "Show details" | Keep cards clean, details on demand |
| Type labels | "Needs approval" / "Question" / "Heads up" | Business-friendly, not technical jargon |
| Alert response | "Got it" button | Low friction acknowledgement |
| Sync direction | Platform polls agents | Agents don't need to know about the platform API |
| Poll interval | 5 seconds (sync service), 10s (frontend) | Fast enough for human interaction |
| WebSocket key | `type` field (not `event`) | Distinct from agent lifecycle events which use `event` field |

---

## File Inventory

### Backend Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/backend/main.py` | 70, 82, 193-194, 254-258, 290-294, 357 | Router/service imports, WS injection, lifespan start/stop, router registration |
| `src/backend/routers/operator_queue.py` | 164 | REST API endpoints (6 endpoints) |
| `src/backend/services/operator_queue_service.py` | 239 | Background sync service (poll, create, write-back) |
| `src/backend/db/operator_queue.py` | 335 | Database operations class (12 methods) |
| `src/backend/db/schema.py` | 529-553, 699-704 | Table definition + 5 indexes |
| `src/backend/database.py` | 127, 254, 1195-1230 | Import, init, delegation methods (10 methods) |

### Frontend Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/frontend/src/views/OperatingRoom.vue` | 109 | Main page with tabs, polling lifecycle |
| `src/frontend/src/stores/operatorQueue.js` | 194 | Pinia store (state, getters, actions, WS handler) |
| `src/frontend/src/components/operator/QueueCard.vue` | 257 | Expandable card with response controls |
| `src/frontend/src/components/operator/ResolvedCard.vue` | 68 | Compact resolved card |
| `src/frontend/src/components/operator/QueueList.vue` | 195 | Filterable list view |
| `src/frontend/src/components/operator/QueueStats.vue` | 88 | Stats sidebar |
| `src/frontend/src/components/operator/QueueItemDetail.vue` | 286 | Full item detail panel |
| `src/frontend/src/components/NavBar.vue` | 40-53, 229, 238 | "Ops" link + badge |
| `src/frontend/src/router/index.js` | 135-139 | Route registration |
| `src/frontend/src/utils/websocket.js` | 4, 12, 96-98 | Import store, init store, dispatch WS events |

---

## Not Yet Implemented

### Phase 5: MCP Tools & Polish
- [ ] MCP tools: `list_operator_queue`, `respond_to_operator_request`, `get_operator_queue_stats`
- [ ] Activity feed integration (log responses as activities)
- [ ] Batch operations (respond to multiple items)
- [ ] Sound/desktop notifications for critical items
- [ ] Keyboard shortcuts (j/k navigation, Enter to respond)

---

## Related Flows

- [Agent Notifications](agent-notifications.md) -- Separate notification system for non-interactive alerts
- [Agent Terminal](agent-terminal.md) -- Direct agent interaction
- [MCP Orchestration](mcp-orchestration.md) -- Agent-to-agent communication tools
