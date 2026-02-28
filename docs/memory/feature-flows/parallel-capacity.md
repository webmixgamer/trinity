# Feature Flow: Parallel Execution Capacity

> **Requirement**: CAPACITY-001 - Per-Agent Parallel Execution Capacity
> **Status**: Implemented (Phase 1: Backend)
> **Created**: 2026-02-28
> **Updated**: 2026-02-28
> **Priority**: P1

## Revision History

| Date | Changes |
|------|---------|
| 2026-02-28 | Initial implementation - Database, Redis slots, REST API, task endpoint integration |

## Overview

This feature implements configurable per-agent parallel execution capacity with Redis-based slot tracking. Each agent has a `max_parallel_tasks` setting (1-10, default 3), and the `/api/agents/{name}/task` endpoint enforces this limit by returning HTTP 429 when capacity is reached.

## Problem Statement

**Prior Limitation**: Trinity had no limit on parallel `/api/task` executions per agent. An orchestrator could spawn unlimited concurrent tasks, causing:
1. Resource exhaustion (CPU, memory, API tokens)
2. Cost explosion (unbounded Claude API usage)
3. Agent unavailability for critical operations

**Solution**: Slot-based capacity tracking with Redis ZSET for automatic cleanup.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Parallel Capacity Flow                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Client                                                                  │
│     │                                                                    │
│     ├── POST /api/agents/{name}/task                                    │
│     │                                                                    │
│     v                                                                    │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │  Backend (chat.py:596-617)                                      │     │
│  │                                                                  │     │
│  │  1. Create execution record in database                         │     │
│  │  2. Get max_parallel_tasks from SQLite                          │     │
│  │  3. Call slot_service.acquire_slot()                            │     │
│  │     ├── Check ZCARD < max_parallel_tasks                        │     │
│  │     ├── If full → Return False                                  │     │
│  │     └── If available → ZADD + store metadata → Return True      │     │
│  │  4. If not acquired → Return 429 Too Many Requests              │     │
│  │  5. If acquired → Execute task                                  │     │
│  │  6. On completion → slot_service.release_slot()                 │     │
│  └────────────────────────────────────────────────────────────────┘     │
│                                                                          │
│  ┌─────────────────────┐         ┌─────────────────────────────────┐    │
│  │  SQLite             │         │  Redis                          │    │
│  │  agent_ownership    │         │  agent:slots:{name} (ZSET)      │    │
│  │  max_parallel_tasks │         │  agent:slot:{name}:{id} (HASH)  │    │
│  └─────────────────────┘         └─────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Slot Acquisition (Task Start)

```
POST /api/agents/{name}/task
       │
       v
┌─────────────────────────────────────────────────┐
│ 1. db.get_max_parallel_tasks(name)              │
│    → Returns max_parallel_tasks (1-10, def: 3)  │
│                                                  │
│ 2. slot_service.acquire_slot(                   │
│      agent_name, execution_id,                  │
│      max_parallel_tasks, message_preview        │
│    )                                             │
│    ├── Clean stale slots (ZREMRANGEBYSCORE)     │
│    ├── Check: ZCARD < max?                      │
│    ├── If YES: ZADD + HSET metadata             │
│    └── Return True/False                        │
└─────────────────────────────────────────────────┘
       │
       ├── slot_acquired=False → 429 Too Many Requests
       │
       └── slot_acquired=True → Execute task
```

### 2. Slot Release (Task Complete)

```
Task completes (success or failure)
       │
       v
┌─────────────────────────────────────────────────┐
│ slot_service.release_slot(agent_name, exec_id)  │
│                                                  │
│ 1. ZREM agent:slots:{name} {execution_id}       │
│ 2. DEL agent:slot:{name}:{execution_id}         │
└─────────────────────────────────────────────────┘
```

### 3. Capacity Query

```
GET /api/agents/{name}/capacity
       │
       v
┌─────────────────────────────────────────────────┐
│ 1. db.get_max_parallel_tasks(name)              │
│ 2. slot_service.get_slot_state(name, max_tasks) │
│    → active_slots, available_slots, slot_list   │
│ 3. Return AgentCapacity response                │
└─────────────────────────────────────────────────┘
```

## Key Files

### Database Layer (SQLite)

| File | Line | Purpose |
|------|------|---------|
| `src/backend/db/migrations.py` | 28, 59, 557-570 | Migration #21: Add max_parallel_tasks column |
| `src/backend/db/agents.py` | 519-580 | `get_max_parallel_tasks()`, `set_max_parallel_tasks()`, `get_all_agents_parallel_capacity()` |

### Redis Slot Service

| File | Line | Purpose |
|------|------|---------|
| `src/backend/services/slot_service.py` | 1-322 | SlotService class with all slot operations |
| `src/backend/services/slot_service.py` | 54-62 | SlotService.__init__() - Redis connection |
| `src/backend/services/slot_service.py` | 77-128 | acquire_slot() - Atomic slot acquisition |
| `src/backend/services/slot_service.py` | 130-152 | release_slot() - Slot release and cleanup |
| `src/backend/services/slot_service.py` | 154-199 | get_slot_state() - Detailed slot info |
| `src/backend/services/slot_service.py` | 201-221 | get_all_slot_states() - Bulk query for Dashboard |
| `src/backend/services/slot_service.py` | 247-271 | cleanup_stale_slots() - 30-min TTL enforcement |

### REST API Endpoints

| File | Line | Purpose |
|------|------|---------|
| `src/backend/routers/agents.py` | 238-263 | `GET /api/agents/slots` - Bulk slot state |
| `src/backend/routers/agents.py` | 1365-1416 | `GET /api/agents/{name}/capacity` - Get capacity |
| `src/backend/routers/agents.py` | 1419-1461 | `PUT /api/agents/{name}/capacity` - Update capacity |

### Task Endpoint Integration

| File | Line | Purpose |
|------|------|---------|
| `src/backend/routers/chat.py` | 20 | Import get_slot_service |
| `src/backend/routers/chat.py` | 596-617 | Slot acquisition before task execution |
| `src/backend/routers/chat.py` | 606-617 | 429 response when at capacity |
| `src/backend/routers/chat.py` | 680 | Async mode: `release_slot=True` flag |
| `src/backend/routers/chat.py` | 427-539 | `_execute_task_background()` with slot release |
| `src/backend/routers/chat.py` | 931 | Sync mode: slot release in finally block |

### Pydantic Models

| File | Line | Purpose |
|------|------|---------|
| `src/backend/db_models.py` | 893-923 | `CapacityUpdate`, `SlotInfo`, `AgentCapacity`, `BulkSlotState` |

### Tests

| File | Line | Purpose |
|------|------|---------|
| `tests/test_capacity.py` | 1-383 | 24 tests for capacity endpoints and validation |

## API Specifications

### GET /api/agents/{name}/capacity

**Authentication**: Required (JWT)
**Authorization**: Must have access to agent

**Response** (200):
```json
{
  "agent_name": "research-agent",
  "max_parallel_tasks": 5,
  "active_slots": 3,
  "available_slots": 2,
  "slots": [
    {
      "slot_number": 1,
      "execution_id": "abc123",
      "started_at": "2026-02-28T10:00:00",
      "message_preview": "Research the market...",
      "duration_seconds": 45
    },
    {
      "slot_number": 2,
      "execution_id": "def456",
      "started_at": "2026-02-28T10:01:00",
      "message_preview": "Analyze competitor...",
      "duration_seconds": 30
    }
  ]
}
```

### PUT /api/agents/{name}/capacity

**Authentication**: Required (JWT)
**Authorization**: Agent owner only

**Request**:
```json
{
  "max_parallel_tasks": 5
}
```

**Response** (200):
```json
{
  "message": "Capacity updated",
  "agent_name": "research-agent",
  "max_parallel_tasks": 5
}
```

**Validation Errors** (400):
- `max_parallel_tasks` not provided
- Value not an integer
- Value < 1 or > 10

### GET /api/agents/slots (Bulk)

**Authentication**: Required (JWT)
**Purpose**: Dashboard polling endpoint

**Response** (200):
```json
{
  "agents": {
    "research-agent": {"max": 5, "active": 3},
    "writer-agent": {"max": 3, "active": 1},
    "orchestrator": {"max": 5, "active": 5}
  },
  "timestamp": "2026-02-28T10:05:00Z"
}
```

### POST /api/agents/{name}/task (Updated)

**429 Response** (at capacity):
```json
{
  "detail": "Agent 'research-agent' is at capacity (5 parallel tasks). Try again later."
}
```

Headers: `Retry-After: 30` (optional, not currently implemented)

## Database Schema

### SQLite: agent_ownership table

```sql
-- Column added by migration #21
ALTER TABLE agent_ownership ADD COLUMN max_parallel_tasks INTEGER DEFAULT 3;
```

### Redis: Slot Tracking

**Slot Set (ZSET)**:
```
Key: agent:slots:{agent_name}
Type: Sorted Set
Score: Unix timestamp (execution start time)
Member: execution_id

Operations:
- ZADD agent:slots:research-agent 1709114400 "exec_abc123"
- ZCARD agent:slots:research-agent  # Count active
- ZREM agent:slots:research-agent "exec_abc123"  # Release
- ZREMRANGEBYSCORE agent:slots:research-agent 0 {30_min_ago}  # Cleanup
```

**Slot Metadata (HASH)**:
```
Key: agent:slot:{agent_name}:{execution_id}
Type: Hash
Fields:
  - started_at: ISO timestamp
  - message_preview: First 100 chars of message
  - slot_number: Assigned slot (1-N)
TTL: 30 minutes (EXPIRE)
```

## Slot Lifecycle

### 1. Slot Acquisition Logic

```python
# src/backend/services/slot_service.py:77-128
async def acquire_slot(self, agent_name, execution_id, max_parallel_tasks, message_preview=""):
    # 1. Clean stale slots (>30 min old)
    await self._cleanup_stale_slots_for_agent(agent_name)

    # 2. Check capacity
    current_count = self.redis.zcard(slots_key)
    if current_count >= max_parallel_tasks:
        return False  # At capacity

    # 3. Add slot
    self.redis.zadd(slots_key, {execution_id: time.time()})

    # 4. Store metadata with TTL
    self.redis.hset(metadata_key, mapping={...})
    self.redis.expire(metadata_key, 1800)  # 30 min

    return True
```

### 2. Slot Release Logic

```python
# src/backend/services/slot_service.py:130-152
async def release_slot(self, agent_name, execution_id):
    # 1. Remove from ZSET
    self.redis.zrem(slots_key, execution_id)

    # 2. Delete metadata
    self.redis.delete(metadata_key)
```

### 3. Stale Slot Cleanup

```python
# src/backend/services/slot_service.py:223-245
async def _cleanup_stale_slots_for_agent(self, agent_name):
    cutoff = time.time() - SLOT_TTL_SECONDS  # 30 min

    # Get stale entries
    stale = self.redis.zrangebyscore(slots_key, "-inf", cutoff)

    # Remove from ZSET
    self.redis.zremrangebyscore(slots_key, "-inf", cutoff)

    # Clean up metadata
    for execution_id in stale:
        self.redis.delete(metadata_key)
```

## Error Handling

| Error Case | HTTP Status | Detail |
|------------|-------------|--------|
| Agent not found | 404 | "Agent not found" |
| Access denied | 403 | "Access denied" |
| Not owner (PUT) | 403 | "Only owners can change capacity settings" |
| At capacity (task) | 429 | "Agent '{name}' is at capacity ({N} parallel tasks). Try again later." |
| Invalid capacity value | 400 | "max_parallel_tasks must be an integer between 1 and 10" |
| Missing field | 400 | "max_parallel_tasks is required" |

## Security Considerations

1. **Authorization**: Only agent owners can modify `max_parallel_tasks`
2. **Validation**: Strict range enforcement (1-10)
3. **Atomic operations**: Redis operations prevent race conditions
4. **TTL safety net**: Orphaned slots auto-expire after 30 minutes
5. **No credential exposure**: Message previews truncated to 100 chars

## Testing

### Test Coverage

| Test Class | Tests | Purpose |
|------------|-------|---------|
| TestCapacityAuthentication | 3 | Auth requirements for all endpoints |
| TestCapacityGet | 4 | GET /capacity structure and defaults |
| TestCapacityUpdate | 9 | PUT /capacity validation and persistence |
| TestBulkSlotState | 4 | GET /slots structure and content |
| TestSlotTracking | 1 | Slot acquisition/release during task |
| TestCapacityEnforcement | 1 | Capacity limit documentation |
| TestSlotInfoStructure | 1 | Slot detail field validation |

### Running Tests

```bash
cd tests && pytest test_capacity.py -v
```

## Related Flows

- **Upstream**: [parallel-headless-execution.md](parallel-headless-execution.md) - Task endpoint that enforces capacity
- **Upstream**: [execution-queue.md](execution-queue.md) - Sequential queue (bypassed by parallel tasks)
- **Downstream**: [agent-dashboard.md](agent-dashboard.md) - Will display capacity meters (Phase 2)
- **Downstream**: [dashboard-timeline-view.md](dashboard-timeline-view.md) - Will display swim lanes (Phase 3)

## Future Enhancements (Phases 2-4)

### Phase 2: Dashboard Capacity Meter
- Replace activity dot with horizontal capacity bar
- Visual states: idle (gray), partial (green/yellow), full (red pulse)
- Tooltip with slot details

### Phase 3: Timeline Swim Lanes
- Fixed N lanes per agent (N = max_parallel_tasks)
- Execution bars rendered in assigned slot lanes
- Empty lanes shown as faint placeholders

### Phase 4: MCP Tools & UI Configuration
- `set_agent_capacity(name, max)` MCP tool
- `get_agent_capacity(name)` MCP tool
- Capacity slider in Agent Detail UI
