# Feature: Workplan System (Pillar I - Explicit Planning)

> **Status**: FULLY IMPLEMENTED (Backend + Frontend)
> **Requirement**: 9.8 (Phase 9)
> **Created**: 2025-12-05
> **Updated**: 2025-12-20 (Line number verification, command naming clarification)
> **Last Tested**: 2025-12-20

---

## Overview

External task graph representation that persists outside the agent's context window. Enables plan visibility, cross-agent coordination, and failure recovery.

## User Stories

1. As a **user**, I want to see what tasks my agent is working on so I can monitor progress.
2. As an **agent**, I want to create plans that survive context resets so I don't lose progress.
3. As a **platform**, I want to aggregate task status across agents for the Agent Network.

---

## Architecture (Centralized via Agent Server)

### Design Principles

1. **Agent Server owns all injection logic** - No file manipulation in startup.sh
2. **API-driven injection** - Backend triggers injection via REST API
3. **Idempotent operations** - Can inject/reset multiple times safely
4. **Clear separation** - Mount provides read-only source, agent-server does the work

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **Trinity Meta-Prompt** | Read-only source mounted at `/trinity-meta-prompt` |
| **Agent Server** | **Owns injection logic** - copies files, creates dirs, updates CLAUDE.md |
| **Backend** | Triggers injection after agent starts, proxies plan queries, aggregates stats |
| **Dashboard** | Visualizes workplans, shows progress per agent and global stats |
| **network.js** | Fetches and caches plan stats, updates node data every 5s |
| **AgentNode.vue** | Displays current task, task progress bar (purple) |

### Data Flow

```
+-------------------------------------------------------------------------+
|                         INJECTION FLOW                                   |
|                                                                          |
|  Backend: start_agent()                                                  |
|         |                                                                |
|         v                                                                |
|  Agent container starts with /trinity-meta-prompt mounted                |
|         |                                                                |
|         v                                                                |
|  Backend calls: POST agent:8000/api/trinity/inject                       |
|         |                                                                |
|         v                                                                |
|  +-------------------------------------------------------------+        |
|  |  Agent Server /api/trinity/inject handler:                   |        |
|  |  1. Check if /trinity-meta-prompt exists                     |        |
|  |  2. Create .trinity/ directory                               |        |
|  |  3. Copy prompt.md -> .trinity/prompt.md                     |        |
|  |  4. Create .claude/commands/trinity/ directory               |        |
|  |  5. Copy commands/*.md -> .claude/commands/trinity/          |        |
|  |  6. Create plans/active/ and plans/archive/                  |        |
|  |  7. Append Trinity section to CLAUDE.md                      |        |
|  |  8. Return {status: "injected", files: [...]}                |        |
|  +-------------------------------------------------------------+        |
|                                                                          |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                         PLAN CREATION FLOW                               |
|                                                                          |
|  User: "Research and write a blog post about AI agents"                 |
|                              |                                           |
|                              v                                           |
|  +-------------------------------------------------------------+        |
|  |  Agent (Claude) receives task                                |        |
|  |  Trinity Meta-Prompt says: "For multi-step tasks, use        |        |
|  |  /workplan-create"                                           |        |
|  +-------------------------------------------------------------+        |
|                              |                                           |
|                              v                                           |
|  +-------------------------------------------------------------+        |
|  |  Agent runs /workplan-create                                 |        |
|  |  - Breaks goal into tasks                                    |        |
|  |  - Identifies dependencies                                   |        |
|  |  - Writes plans/active/{plan-id}.yaml                       |        |
|  +-------------------------------------------------------------+        |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                         PLAN VISIBILITY FLOW                             |
|                                                                          |
|  +--------------+     +--------------+     +----------------------+      |
|  | Agent        |     |   Backend    |     |    Agent Server      |      |
|  |  Network     |---->|   API        |---->|    (in container)    |      |
|  |              |     |              |     |                      |      |
|  | GET /agents/ |     | Proxy to     |     | GET /api/plans       |      |
|  | {name}/plans |     | agent:8000   |     |                      |      |
|  +--------------+     +--------------+     +----------+-----------+      |
|                                                       |                  |
|                                                       v                  |
|                                            +--------------------+        |
|                                            |  plans/active/     |        |
|                                            |   plan-abc123.yaml |        |
|                                            +--------------------+        |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    DASHBOARD VISUALIZATION FLOW                          |
|                                                                          |
|  +------------------------------------------------------------------+   |
|  |  network.js store (every 5 seconds)                               |   |
|  |                                                                    |   |
|  |  fetchPlanStats() ------------------------------------------------>|   |
|  |       |                                                            |   |
|  |       v                                                            |   |
|  |  GET /api/agents/plans/aggregate                                   |   |
|  |       |                                                            |   |
|  |       v                                                            |   |
|  |  +-------------------------------------------------------------+  |   |
|  |  | Response:                                                    |  |   |
|  |  | {                                                           |  |   |
|  |  |   total_plans: 3, active_plans: 2,                          |  |   |
|  |  |   total_tasks: 12, completed_tasks: 5,                      |  |   |
|  |  |   agent_summaries: [                                        |  |   |
|  |  |     { agent_name: "agent-a", current_task: {...}, ... }     |  |   |
|  |  |   ]                                                         |  |   |
|  |  | }                                                           |  |   |
|  |  +-------------------------------------------------------------+  |   |
|  |       |                                                            |   |
|  |       +------------------+------------------------------------+   |   |
|  |       v                  v                                    v   |   |
|  |  aggregatePlanStats   planStats{}                      node.data  |   |
|  |  (header display)     (per-agent)                   (AgentNode)   |   |
|  +------------------------------------------------------------------+   |
|                                                                          |
|  +------------------------------------------------------------------+   |
|  |  Dashboard.vue Compact Header (Agent Network view)                |   |
|  |  +------------------------------------------------------------+  |   |
|  |  | 6 agents - 2 running - 2 plans - 15 messages (24h)         |  |   |
|  |  +------------------------------------------------------------+  |   |
|  +------------------------------------------------------------------+   |
|                                                                          |
|  +------------------------------------------------------------------+   |
|  |  AgentNode.vue (per agent with active plan)                       |   |
|  |  +------------------------------------------------------------+  |   |
|  |  | agent-a                                            [*]     |  |   |
|  |  | Active                                                      |  |   |
|  |  | Context [============--------] 45%                         |  |   |
|  |  | Current Task: Write introduction section                    |  |   |
|  |  | Tasks   [======--------------] 2/5                         |  |   |
|  |  | [View Details]                                              |  |   |
|  |  +------------------------------------------------------------+  |   |
|  +------------------------------------------------------------------+   |
+-------------------------------------------------------------------------+
```

---

## Implementation Files

> **Architecture Change (2025-12-06)**: The agent-server has been refactored from a monolithic file into a modular package structure at `docker/base-image/agent_server/`.

| File | Changes | Status |
|------|---------|--------|
| `config/trinity-meta-prompt/prompt.md` | Trinity system prompt with planning instructions (95 lines) | DONE |
| `config/trinity-meta-prompt/commands/workplan-*.md` | Planning commands (4 files) | DONE |
| `docker/base-image/agent_server/routers/plans.py` | Plan API endpoints (433 lines) | DONE |
| `docker/base-image/agent_server/routers/trinity.py` | Trinity injection API endpoints (354 lines) | DONE |
| `docker/base-image/startup.sh:155` | Injection code removed (comment only) | DONE |
| `src/backend/routers/agents.py:50-111,114-154,1573-2030` | inject helper + start integration + proxy endpoints | DONE |
| `src/frontend/src/stores/network.js:23-24,604-669,965-966,1004` | Plan stats state + fetchPlanStats() | DONE |
| `src/frontend/src/components/AgentNode.vue:72-102,206-230` | Task progress display + computed properties | DONE |
| `src/frontend/src/views/Dashboard.vue:23-27` | Header plan stats display (compact inline format) | DONE |

> **Note (2025-12-07)**: AgentNetwork.vue was merged into Dashboard.vue. The plan stats are now shown in the compact header inline with other stats.

---

## Agent Server Trinity Injection API (IMPLEMENTED)

> **File**: `docker/base-image/agent_server/routers/trinity.py`
> **Lines**: 1-354

### Key Functions

- `check_trinity_injection_status()` (lines 27-76): Check if Trinity has been injected
- `GET /api/trinity/status` (lines 79-83): Check injection status
- `POST /api/trinity/inject` (lines 86-304): Inject Trinity meta-prompt
- `POST /api/trinity/reset` (lines 307-353): Reset injection

> **Note**: The `check_trinity_injection_status()` function at lines 33-36 references `trinity-plan-*` command filenames. However, the actual command files are named `workplan-*.md`. The injection logic at lines 136-141 correctly copies whatever files exist in the `commands/` directory regardless of naming.

### `POST /api/trinity/inject`

Injects Trinity meta-prompt and planning infrastructure into agent workspace.

**Request Body** (optional):
```json
{
  "force": false,  // If true, re-inject even if already done
  "custom_prompt": "..." // Optional custom instructions to add
}
```

**Response**:
```json
{
  "status": "injected",
  "already_injected": false,
  "files_created": [
    ".trinity/prompt.md",
    ".trinity/vector-memory.md",
    ".claude/commands/trinity/workplan-create.md",
    ".claude/commands/trinity/workplan-status.md",
    ".claude/commands/trinity/workplan-update.md",
    ".claude/commands/trinity/workplan-list.md"
  ],
  "directories_created": [
    ".trinity",
    ".claude/commands/trinity",
    "plans/active",
    "plans/archive",
    "vector-store"
  ],
  "claude_md_updated": true
}
```

**Error Response** (if mount missing):
```json
{
  "status": "error",
  "error": "Trinity meta-prompt not mounted at /trinity-meta-prompt"
}
```

### `POST /api/trinity/reset`

Resets Trinity injection to clean state (removes injected files).

**Response**:
```json
{
  "status": "reset",
  "files_removed": [...],
  "directories_removed": [...]
}
```

### `GET /api/trinity/status`

Check current injection status.

**Response**:
```json
{
  "injected": true,
  "meta_prompt_mounted": true,
  "files": {
    ".trinity/prompt.md": true,
    ".claude/commands/trinity/trinity-plan-create.md": true,
    ".claude/commands/trinity/trinity-plan-status.md": true,
    ".claude/commands/trinity/trinity-plan-update.md": true,
    ".claude/commands/trinity/trinity-plan-list.md": true
  },
  "directories": {
    "plans/active": true,
    "plans/archive": true,
    "vector-store": true
  },
  "vector_memory": {
    "vector-store": true,
    ".trinity/vector-memory.md": true,
    "chroma_mcp_configured": true
  },
  "claude_md_has_trinity_section": true
}
```

---

## Agent Server Plan API (IMPLEMENTED)

> **File**: `docker/base-image/agent_server/routers/plans.py`
> **Lines**: 1-433

### IMPORTANT: Route Ordering

The `/api/plans/summary` endpoint **MUST** be defined BEFORE `/api/plans/{plan_id}` to avoid FastAPI matching "summary" as a plan_id. See lines 239-241.

### Endpoints

| Endpoint | Method | Line | Description |
|----------|--------|------|-------------|
| `/api/plans` | GET | 124 | List all plans |
| `/api/plans` | POST | 187 | Create new plan |
| `/api/plans/summary` | GET | 241 | Aggregated stats for dashboard |
| `/api/plans/{plan_id}` | GET | 315 | Get plan details |
| `/api/plans/{plan_id}` | PUT | 329 | Update plan metadata |
| `/api/plans/{plan_id}` | DELETE | 359 | Delete plan |
| `/api/plans/{plan_id}/tasks/{task_id}` | PUT | 377 | Update task status |

### Key Functions

```python
# Lines 24-43
def load_plan(plan_id: str) -> Optional[dict]:
    """Load a plan from file (active or archive)."""

# Lines 46-79
def save_plan(plan: dict) -> bool:
    """Save a plan to file, moving to archive if completed/failed."""

# Lines 82-104
def update_blocked_tasks(plan: dict) -> None:
    """Update blocked status based on dependencies.
    When a task completes, tasks that depended on it become pending."""

# Lines 107-121
def check_plan_completion(plan: dict) -> None:
    """Check if plan should be marked as completed.
    When all tasks are completed, plan status becomes completed."""
```

---

## Backend Proxy Endpoints (IMPLEMENTED)

> **File**: `src/backend/routers/agents.py`
> **Lines**: 1566-2030

### IMPORTANT: Route Ordering

The aggregate endpoint **MUST** come BEFORE agent-specific routes. See lines 1570-1571.

### Endpoints

| Endpoint | Line | Description |
|----------|------|-------------|
| `GET /api/agents/plans/aggregate` | 1573 | Cross-agent plan aggregation |
| `GET /api/agents/{name}/plans` | 1692 | List agent's plans |
| `POST /api/agents/{name}/plans` | 1734 | Create new plan |
| `GET /api/agents/{name}/plans/summary` | 1784 | Get agent's plan summary |
| `GET /api/agents/{name}/plans/{plan_id}` | 1839 | Get specific plan |
| `PUT /api/agents/{name}/plans/{plan_id}` | 1880 | Update plan |
| `DELETE /api/agents/{name}/plans/{plan_id}` | 1931 | Delete plan |
| `PUT /api/agents/{name}/plans/{plan_id}/tasks/{task_id}` | 1979 | Update task status |

### Backend Integration (IMPLEMENTED)

> **File**: `src/backend/routers/agents.py`
> **Lines**: 50-111 (helper), 114-154 (start_agent_internal)

**Helper function** `inject_trinity_meta_prompt()` (lines 50-111):
- Calls `POST agent:8000/api/trinity/inject` with retries
- Max 5 retries with 2-second delay between attempts
- Handles connection errors gracefully (agent starting up)
- Fetches system-wide `trinity_prompt` setting for custom instructions (line 73)

**Integration in `start_agent_internal()`** (lines 114-154):
```python
# After container.start() - lines 144-148
container.start()

# Inject Trinity meta-prompt
trinity_result = await inject_trinity_meta_prompt(agent_name)
trinity_status = trinity_result.get("status", "unknown")

# Return message includes injection status - lines 150-154
return {
    "message": f"Agent {agent_name} started",
    "trinity_injection": trinity_status,
    "trinity_result": trinity_result
}
```

---

## Plan File Format

Stored at: `plans/active/{plan-id}.yaml` (or `plans/archive/` when completed)

```yaml
id: "plan-1733400000-abc123"
name: "Research and write blog post"
description: "Research AI agents and produce a blog post"
created: "2025-12-05T10:00:00"
updated: "2025-12-05T10:21:00"
status: "active"  # active | completed | failed | paused

tasks:
  - id: "task-1"
    name: "Research topic"
    description: "Find relevant sources"
    status: "completed"
    dependencies: []
    started_at: "2025-12-05T10:01:00"
    completed_at: "2025-12-05T10:15:00"
    result: "Found 12 relevant sources"

  - id: "task-2"
    name: "Create outline"
    status: "completed"
    dependencies: ["task-1"]

  - id: "task-3"
    name: "Write draft"
    status: "active"
    dependencies: ["task-2"]

  - id: "task-4"
    name: "Review and publish"
    status: "blocked"
    dependencies: ["task-3"]
```

---

## Task State Machine

```
                    +----------------------------------+
                    |                                  |
                    v                                  |
+---------+    +---------+    +-----------+    +------+----+
| pending |--->| active  |--->| completed |    |  failed   |
+---------+    +---------+    +-----------+    +-----------+
     |              |                               ^
     |              |                               |
     v              +-------------------------------+
+---------+
| blocked |  (waiting on dependencies)
+---------+
```

**Auto-Transitions:**
- `blocked -> pending`: When all dependencies complete
- `pending -> blocked`: When a dependency is incomplete
- Plan `status` -> `completed`: When all tasks complete

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Meta-prompt not mounted | 500 | Trinity meta-prompt not mounted |
| Agent not found | 404 | Agent not found |
| Agent not running | 400 | Agent must be running |
| Plan not found | 404 | Plan not found: {plan_id} |
| Task not found | 404 | Task not found: {task_id} |
| Invalid status | 400 | Invalid status: {status} |
| Permission denied | 403 | You don't have permission |

---

## Security Considerations

- All endpoints require authentication
- Access control via `can_user_access_agent()` check
- Plan operations audit-logged (`plan_management` event type)
- Plans stored inside agent container (isolated per-agent)
- Meta-prompt mounted read-only

---

## Testing

### Prerequisites
- [x] Services running (backend, agent)
- [x] Test agent created and started
- [x] `/trinity-meta-prompt` mounted in agent

### Test: Injection API (VERIFIED 2025-12-06)
1. **POST /api/trinity/inject**
   - [x] Returns 200 with files_created list
   - [x] `.trinity/prompt.md` exists
   - [x] `.claude/commands/trinity/` has 4 command files
   - [x] `plans/active/` and `plans/archive/` directories exist
   - [x] CLAUDE.md updated with Trinity Planning System section

2. **GET /api/trinity/status**
   - [x] All files show `true`
   - [x] All directories show `true`
   - [x] `claude_md_has_trinity_section: true`

3. **POST /api/trinity/reset**
   - [x] Returns 200 with files_removed list
   - [x] `.trinity/` directory removed
   - [x] Trinity section removed from CLAUDE.md

### Test: Plan API (VERIFIED 2025-12-06)
1. **Create plan with dependencies**
   - [x] task-1 starts as `pending`
   - [x] task-2 starts as `blocked` (depends on task-1)

2. **Complete task-1**
   - [x] task-2 auto-changes from `blocked` to `pending`

3. **Complete all tasks**
   - [x] Plan auto-completes
   - [x] Plan file moves to `plans/archive/`

### Production Verification (2025-12-06)
- **Tested on**: https://your-domain.com
- **Agent**: workplan-test (running)
- **Tester**: Claude Code via MCP + direct API

#### Trinity Injection API
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/trinity/status` | Pass | All files present, claude_md_has_trinity_section: true |
| `POST /api/trinity/inject` | Pass | Idempotent, creates all required files |
| `POST /api/trinity/reset` | Pass | Removes injected files |

#### Agent Plan API
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/plans` | Pass | Returns plans list with count |
| `POST /api/plans` | Pass | Creates plan with DAG dependencies |
| `GET /api/plans/summary` | Pass | Returns aggregate stats |
| `GET /api/plans/{id}` | Pass | Returns full plan with tasks |
| `PUT /api/plans/{id}/tasks/{task_id}` | Pass | Updates task, triggers dependency unblocking |
| `DELETE /api/plans/{id}` | Pass | Removes plan from storage |

#### Dependency Logic
| Test Case | Status | Notes |
|-----------|--------|-------|
| Single dependency (task-1 -> task-2) | Pass | task-2 unblocks when task-1 completes |
| Multiple dependencies (task-2,3 -> task-4) | Pass | task-4 stays blocked until BOTH complete |
| AND logic verification | Pass | Completing only task-2 keeps task-4 blocked |
| Plan auto-completion | Pass | Plan status -> completed when all tasks done |
| Plan auto-archiving | Pass | Plan file moves from active/ to archive/ |

#### Backend Proxy Endpoints
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/agents/{name}/plans/summary` | Pass | Proxies to agent |
| `GET /api/agents/{name}/plans` | Pass | Returns 2 plans |
| `POST /api/agents/{name}/plans` | Pass | Creates plan via proxy |
| `GET /api/agents/{name}/plans/{id}` | Pass | Returns full plan details |
| `PUT /api/agents/{name}/plans/{id}/tasks/{id}` | Pass | Updates task via proxy |
| `DELETE /api/agents/{name}/plans/{id}` | Pass | Deletes plan via proxy |
| `GET /api/agents/plans/aggregate` | Pass | Cross-agent summary (6 agents, 2 plans) |

#### Test Summary
- **Total Tests**: 20
- **Passed**: 20
- **Failed**: 0
- **Coverage**: Full lifecycle (create, read, update, delete, dependencies, archiving)

---

## Revision History

| Date | Changes |
|------|---------|
| 2025-12-20 | Line number verification, command naming note added, Last Tested date updated |
| 2025-12-19 | Path verification after agent-server modular refactor - updated all line numbers |
| 2025-12-07 | Terminology refactor: Task DAG -> Workplan, /trinity-plan-* -> /workplan-* |
| 2025-12-06 | Updated agent-server references to new modular structure |
| 2025-12-06 | Plans API now in `agent_server/routers/plans.py` (lines 1-433) |
| 2025-12-06 | Trinity injection API now in `agent_server/routers/trinity.py` (lines 1-354) |
| 2025-12-05 | Initial design and backend implementation |
| 2025-12-06 02:30 | Architecture change: Centralized injection via agent-server API |
| 2025-12-06 02:30 | IMPLEMENTED: All injection logic moved to agent-server.py |
| 2025-12-06 02:30 | IMPLEMENTED: Backend calls POST /api/trinity/inject on agent start |
| 2025-12-06 02:30 | VERIFIED: Production testing on your-domain.com |
| 2025-12-06 | Documentation updated with correct line numbers and verified status |
| 2025-12-06 00:25 | COMPREHENSIVE TESTING: Full production test suite - 20/20 tests passed |
| 2025-12-06 | FRONTEND: Workplan visualization in Agent Network |

---

## Frontend Visualization (IMPLEMENTED)

> **Status**: DONE
> **Implemented**: 2025-12-06

### Overview

Real-time Workplan visualization in the Agent Network. Shows agent planning activity, current tasks, and progress across all agents.

### Components

#### 1. Store: `network.js`

**New State** (lines 23-24):
```javascript
planStats: {}              // Map of agent name -> plan stats
aggregatePlanStats: {      // Global stats across all agents
  total_plans: 0,
  active_plans: 0,
  completed_plans: 0,
  total_tasks: 0,
  completed_tasks: 0,
  active_tasks: 0,
  completion_rate: 0
}
```

**Function**: `fetchPlanStats()` (lines 604-669)
- Fetches from `GET /api/agents/plans/aggregate`
- Parses `agent_summaries` array
- Updates node data with per-agent plan info
- Called every 5 seconds via `startContextPolling()`

#### 2. AgentNode.vue

**Task DAG Progress Display** (lines 72-102):
- Current task name with pulsing icon (when agent has active task)
- Task progress bar (purple, shows completed/total)
- Always visible for consistent card height

**Computed Properties** (lines 206-230):
```javascript
hasActivePlan    // true if agent has plans
currentTask      // Name of currently active task
completedTasks   // Number of completed tasks
totalTasks       // Total task count
taskProgressPercent  // Percentage complete
taskProgressDisplay  // "X/Y" format or "-" if no tasks
```

**Visual Design**:
- Purple color scheme for workplan (distinguishes from context green)
- Progress bar below context progress bar
- Current task truncates with tooltip for full name

#### 3. Dashboard.vue Header (Agent Network View)

**Plan Stats Display** (Lines 23-27):
- Shows when `aggregatePlanStats.active_plans > 0`
- Inline format: "X plans" in the compact header row
- Purple accent text color (#9333ea) matches AgentNode task display

> **Note (2025-12-07)**: Previously in AgentNetwork.vue, now integrated into Dashboard.vue compact header.

### Data Flow

```
+--------------------+     +-------------------+     +------------------+
| Backend Aggregate  |---->| network.js        |---->| AgentNode.vue    |
| /plans/aggregate   |     | fetchPlanStats()  |     | Task progress UI |
+--------------------+     +-------------------+     +------------------+
                                   |
                                   v
                           +----------------------+
                           | Dashboard.vue        |
                           | Compact header stats |
                           +----------------------+
```

### Polling Frequency

- Plan stats fetched every 5 seconds (same interval as context stats)
- Integrated into existing `startContextPolling()` function (lines 672-688)
- Stops when entering Replay mode, resumes in Live mode

### UI/UX Considerations

1. **Progressive disclosure**: Workplan section only shows when agent has plans
2. **Consistent theming**: Purple color for tasks, green for context
3. **Non-intrusive**: Doesn't add height unless needed
4. **Real-time updates**: Reflects planning activity within 5 seconds

### Frontend Testing

#### Test: Dashboard Header Stats
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/` (Dashboard) with no plans | Header shows only agent/running/messages stats |
| 2 | Create a plan on any agent | Header shows plan count inline: "X plans" |
| 3 | Wait 5 seconds | Stats update automatically |

> **Note (2025-12-07)**: `/network` now redirects to `/` (Dashboard). The compact header shows inline stats format.

#### Test: AgentNode Task Progress
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create plan with tasks on agent | Agent node shows purple task section |
| 2 | Check current task display | Shows task name with pulsing blue icon |
| 3 | Complete tasks | Progress bar updates (e.g., "2/4") |
| 4 | Complete all tasks | Task section may hide (no active plan) |

#### Test: Polling Behavior
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open browser DevTools Network tab | See `/api/agents/plans/aggregate` calls every 5s |
| 2 | Switch to Replay mode | Polling stops |
| 3 | Switch back to Live mode | Polling resumes |

#### Test: Edge Cases
| Scenario | Expected Behavior |
|----------|-------------------|
| Agent offline | No task section shown (activityState = "offline") |
| No plans exist | Task section hidden, header stats hidden |
| Plan with 0 tasks | Task section hidden |
| API error (404) | Silent fail, no console error spam |

**Last Tested**: 2025-12-20
**Status**: Frontend build successful, ready for integration testing
