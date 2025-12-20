# Feature: Workplan UI (AgentDetail Workplan Tab)

> **Status**: IMPLEMENTED
> **Requirement**: 9.8 (Phase 9 - Pillar I: Explicit Planning)
> **Created**: 2025-12-06
> **Last Updated**: 2025-12-19 (Line number verification after dark mode + modular refactor)
> **Related**: [workplan-system.md](workplan-system.md) (backend infrastructure)

---

## Overview

The Workplan UI provides a dedicated interface for viewing and managing Workplan plans within the AgentDetail page. Users can view plan summaries, filter by status, inspect individual plans with full task graph visualization, and manage plan lifecycle (pause, resume, delete).

## User Story

As a **user**, I want to view and manage my agent's Workplan plans so that I can monitor progress, understand dependencies, and control plan execution.

---

## Entry Points

- **UI**: `src/frontend/src/views/AgentDetail.vue:284-295` - Workplan tab button
- **Component**: `src/frontend/src/components/WorkplanPanel.vue` - Main Workplan UI component (537 lines)
- **API**:
  - `GET /api/agents/{name}/plans` - List plans
  - `GET /api/agents/{name}/plans/summary` - Summary statistics
  - `GET /api/agents/{name}/plans/{plan_id}` - Single plan details
  - `PUT /api/agents/{name}/plans/{plan_id}` - Update plan (pause/resume)
  - `DELETE /api/agents/{name}/plans/{plan_id}` - Delete plan

---

## Frontend Layer

### Component: WorkplanPanel.vue

> **File**: `src/frontend/src/components/WorkplanPanel.vue`
> **Lines**: 1-537 (318 template, 219 script)

#### Props

```javascript
// Lines 324-333
const props = defineProps({
  agentName: {
    type: String,
    required: true
  },
  agentStatus: {
    type: String,
    default: 'stopped'
  }
})
```

#### State

```javascript
// Lines 338-343
const plans = ref([])           // List of plan summaries
const summary = ref(null)       // Aggregate statistics
const loading = ref(false)      // Loading state
const selectedPlan = ref(null)  // Full plan for modal display
const statusFilter = ref('')    // Status filter: '', 'active', 'completed', 'failed', 'paused'
const agentNotRunning = ref(false)  // Agent availability state
```

#### Computed Properties

| Property | Line | Description |
|----------|------|-------------|
| `filteredPlans` | 356-359 | Plans filtered by statusFilter |
| `taskProgressPercent` | 361-364 | Overall task completion % from summary |
| `completedTaskCount` | 366-369 | Tasks completed in selected plan |
| `planProgressPercent` | 371-374 | Progress % for selected plan |

#### Key Methods

| Method | Line | Description |
|--------|------|-------------|
| `loadPlans()` | 377-405 | Load summary + plans in parallel |
| `viewPlan(planId)` | 407-414 | Load full plan and open modal |
| `pausePlan()` | 416-429 | Update plan status to 'paused' |
| `resumePlan()` | 431-444 | Update plan status to 'active' |
| `deletePlan()` | 446-463 | Delete plan with confirmation (uses ConfirmDialog) |

#### Watchers

| Watcher | Line | Description |
|---------|------|-------------|
| `watch(() => props.agentName)` | 520-523 | Reload on agent change |
| `watch(() => props.agentStatus)` | 525-527 | Reload on status change |
| `watch(statusFilter)` | 529-531 | Reload on filter change |

### Integration in AgentDetail.vue

> **File**: `src/frontend/src/views/AgentDetail.vue`

**Import** (line 1022):
```javascript
import WorkplanPanel from '../components/WorkplanPanel.vue'
```

**Tab Button** (lines 284-295):
```vue
<button
  @click="activeTab = 'plans'"
  :class="[
    'px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
    activeTab === 'plans'
      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
  ]"
  title="This agent's internal task breakdown"
>
  Workplan
</button>
```

**Tab Content** (lines 910-913):
```vue
<!-- Plans Tab Content -->
<div v-if="activeTab === 'plans'" class="p-6">
  <WorkplanPanel :agent-name="agent.name" :agent-status="agent.status" />
</div>
```

### State Management: agents.js

> **File**: `src/frontend/src/stores/agents.js`
> **Lines**: 378-436

#### Plan Actions

| Action | Line | API Call |
|--------|------|----------|
| `getAgentPlans(name, status)` | 378-386 | `GET /api/agents/{name}/plans?status={status}` |
| `getAgentPlansSummary(name)` | 388-394 | `GET /api/agents/{name}/plans/summary` |
| `getAgentPlan(name, planId)` | 396-402 | `GET /api/agents/{name}/plans/{planId}` |
| `createAgentPlan(name, planData)` | 404-410 | `POST /api/agents/{name}/plans` |
| `updateAgentPlan(name, planId, updates)` | 412-418 | `PUT /api/agents/{name}/plans/{planId}` |
| `deleteAgentPlan(name, planId)` | 420-426 | `DELETE /api/agents/{name}/plans/{planId}` |
| `updateAgentTask(name, planId, taskId, taskUpdate)` | 428-436 | `PUT /api/agents/{name}/plans/{planId}/tasks/{taskId}` |

---

## Backend Layer

### Proxy Endpoints

> **File**: `src/backend/routers/agents.py`
> **Lines**: 1692-1979

All endpoints are proxies to the agent container's internal API.

| Endpoint | Method | Line | Description |
|----------|--------|------|-------------|
| `/api/agents/{name}/plans` | GET | 1692 | List all plans |
| `/api/agents/{name}/plans` | POST | 1734 | Create new plan |
| `/api/agents/{name}/plans/summary` | GET | 1784 | Get summary stats |
| `/api/agents/{name}/plans/{plan_id}` | GET | 1839 | Get single plan |
| `/api/agents/{name}/plans/{plan_id}` | PUT | 1880 | Update plan metadata |
| `/api/agents/{name}/plans/{plan_id}` | DELETE | 1931 | Delete plan |
| `/api/agents/{name}/plans/{plan_id}/tasks/{task_id}` | PUT | 1979 | Update task status |

### Authorization

All endpoints verify:
1. User is authenticated (`current_user: User = Depends(get_current_user)`)
2. User has access to agent (`db.can_user_access_agent()`)
3. Agent container exists and is running

### Error Handling

```python
# Agent not found
if not container:
    raise HTTPException(status_code=404, detail="Agent not found")

# Agent not running
if container.status != "running":
    raise HTTPException(status_code=400, detail="Agent must be running to view plans")

# Timeout
except httpx.TimeoutException:
    raise HTTPException(status_code=504, detail="Agent request timed out")
```

### Audit Logging

Plan management operations are audit logged:

```python
await log_audit_event(
    event_type="plan_management",
    action="create|update|delete",
    user_id=current_user.username,
    agent_name=agent_name,
    ip_address=request.client.host if request.client else None,
    result="success",
    details={"plan_id": plan_id, ...}
)
```

---

## Agent Layer (Container Internal API)

### Plans API

> **File**: `docker/base-image/agent_server/routers/plans.py`
> **Lines**: 1-433 (19 helper functions, 8 route handlers)

| Endpoint | Line | Function |
|----------|------|----------|
| `GET /api/plans` | 124 | `list_plans()` |
| `POST /api/plans` | 187 | `create_plan()` |
| `GET /api/plans/summary` | 241 | `get_plans_summary()` |
| `GET /api/plans/{plan_id}` | 315 | `get_plan()` |
| `PUT /api/plans/{plan_id}` | 329 | `update_plan()` |
| `DELETE /api/plans/{plan_id}` | 359 | `delete_plan()` |
| `PUT /api/plans/{plan_id}/tasks/{task_id}` | 377 | `update_task()` |

See [workplan-system.md](workplan-system.md) for complete API documentation.

### Plan Storage

Plans are stored as YAML files in the agent container:
- Active plans: `/home/developer/plans/active/{plan-id}.yaml`
- Archived plans: `/home/developer/plans/archive/{plan-id}.yaml`

---

## UI Components

### Summary Stats Cards (lines 39-68)

Five statistics cards displayed in a grid:
1. **Total Plans** - Total count
2. **Active** - Active plan count (blue)
3. **Completed** - Completed plan count (green)
4. **Total Tasks** - Total task count
5. **Task Progress** - Completion % with progress bar

### Current Task Banner (lines 70-93)

Displayed when `summary.current_task` exists:
- Pulsing blue indicator
- Task name and plan name
- "View Plan" button

### Plan List (lines 118-153)

For each plan:
- Plan name with status badge
- Task count and completion count
- Progress bar (color varies by status)
- Relative timestamp
- Clickable to open detail modal

### Status Filter (lines 11-20)

Dropdown with options:
- All Plans
- Active
- Completed
- Failed
- Paused

### Plan Detail Modal (lines 155-305)

Full-page modal with:
- Header: Plan name, status badge, description, timestamps
- Progress bar: Overall completion
- Task list with:
  - Status icon (checkmark, pulse, X, lock)
  - Task name and ID
  - Description
  - Dependencies list
  - Result (if completed)
  - Start/complete timestamps
- Footer actions: Pause/Resume, Delete, Close

### ConfirmDialog Integration (lines 307-316)

Uses shared ConfirmDialog component for delete confirmation.

### Task Status Icons

| Status | Icon | Color |
|--------|------|-------|
| completed | Checkmark | Green |
| active | Pulsing dot | Blue |
| failed | X | Red |
| blocked | Lock | Yellow |
| pending | Empty dot | Gray |

---

## Data Flow

```
+------------------------------------------------------------------+
|                      USER ACTION FLOW                             |
|                                                                   |
|  User clicks Workplan tab in AgentDetail                          |
|         |                                                         |
|         v                                                         |
|  WorkplanPanel component mounts                                   |
|         |                                                         |
|         v                                                         |
|  onMounted() -> loadPlans()                                       |
|         |                                                         |
|         +------ Promise.all([                                     |
|         |         getAgentPlansSummary(agentName),                |
|         |         getAgentPlans(agentName, statusFilter)          |
|         |       ])                                                |
|         |                                                         |
|         v                                                         |
|  agents.js store makes HTTP requests:                             |
|    GET /api/agents/{name}/plans/summary                           |
|    GET /api/agents/{name}/plans?status={filter}                   |
|         |                                                         |
|         v                                                         |
|  Backend (routers/agents.py) proxies to agent container:          |
|    GET http://agent-{name}:8000/api/plans/summary                 |
|    GET http://agent-{name}:8000/api/plans                         |
|         |                                                         |
|         v                                                         |
|  Agent-server (routers/plans.py) reads from /home/developer/plans |
|         |                                                         |
|         v                                                         |
|  Response flows back -> UI updates:                               |
|    - Summary stats cards populated                                |
|    - Current task banner (if active task)                         |
|    - Plan list rendered with progress bars                        |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
|                     PLAN DETAIL FLOW                              |
|                                                                   |
|  User clicks a plan in the list                                   |
|         |                                                         |
|         v                                                         |
|  viewPlan(planId) called                                          |
|         |                                                         |
|         v                                                         |
|  getAgentPlan(agentName, planId)                                  |
|    GET /api/agents/{name}/plans/{plan_id}                         |
|         |                                                         |
|         v                                                         |
|  selectedPlan = response (full plan with tasks)                   |
|         |                                                         |
|         v                                                         |
|  Modal opens with:                                                |
|    - Plan metadata                                                |
|    - Overall progress bar                                         |
|    - Task graph with dependencies shown                           |
|    - Action buttons (Pause/Resume/Delete)                         |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
|                    PLAN ACTION FLOW                               |
|                                                                   |
|  User clicks Pause/Resume/Delete in modal                         |
|         |                                                         |
|         v                                                         |
|  pausePlan() / resumePlan() / deletePlan()                        |
|         |                                                         |
|         v                                                         |
|  updateAgentPlan(name, planId, { status: 'paused'|'active' })     |
|  -or- deleteAgentPlan(name, planId)                               |
|         |                                                         |
|         v                                                         |
|  PUT/DELETE /api/agents/{name}/plans/{plan_id}                    |
|         |                                                         |
|         v                                                         |
|  Backend audit logs the action                                    |
|  Backend proxies to agent container                               |
|         |                                                         |
|         v                                                         |
|  Agent updates plan file / removes plan file                      |
|         |                                                         |
|         v                                                         |
|  UI updates:                                                      |
|    - For update: selectedPlan updated, loadPlans() refreshes list |
|    - For delete: selectedPlan = null, loadPlans() refreshes list  |
+------------------------------------------------------------------+
```

---

## Error Handling

| Error Case | HTTP Status | UI Behavior |
|------------|-------------|-------------|
| Agent not found | 404 | Error logged, no UI update |
| Agent not running | 400 | `agentNotRunning = true`, special UI state shown |
| Agent timeout | 504 | `agentNotRunning = true`, special UI state shown |
| Plan not found | 404 | Error logged, modal closed if relevant |
| Permission denied | 403 | Error logged, no access |

### Agent Not Running State (lines 100-108)

Special UI displayed when agent is stopped:
- Stop sign icon
- "Agent must be running to view workplan" message
- Explanation: "Start the agent to access its workplan system"

### Empty State (lines 109-117)

When agent is running but has no plans:
- Clipboard icon
- "No workplan yet" message
- Explanation about using /workplan commands

---

## Security Considerations

1. **Authentication**: All API calls include auth headers via `authStore.authHeader`
2. **Authorization**: Backend verifies `can_user_access_agent()` on every request
3. **Audit Logging**: All plan create/update/delete operations logged
4. **Confirmation**: Delete requires user confirmation (`confirm()` dialog)
5. **Input Validation**: Status updates validated against allowed values

---

## Styling

All styling includes dark mode variants (Tailwind dark: prefix).

### Status Badge Colors (getStatusBadgeClass, lines 466-475)

| Status | Light Mode | Dark Mode |
|--------|------------|-----------|
| active | bg-blue-100 text-blue-800 | bg-blue-900/50 text-blue-300 |
| completed | bg-green-100 text-green-800 | bg-green-900/50 text-green-300 |
| failed | bg-red-100 text-red-800 | bg-red-900/50 text-red-300 |
| paused | bg-yellow-100 text-yellow-800 | bg-yellow-900/50 text-yellow-300 |

### Progress Bar Colors (getProgressBarClass, lines 477-485)

| Status | Color |
|--------|-------|
| active | bg-blue-500 |
| completed | bg-green-500 |
| failed | bg-red-500 |
| paused | bg-yellow-500 |

### Task Border Colors (getTaskBorderClass, lines 487-495)

| Status | Light Border/Background | Dark Border/Background |
|--------|------------------------|----------------------|
| completed | border-green-200 bg-green-50/50 | border-green-800 bg-green-900/20 |
| active | border-blue-300 bg-blue-50/50 | border-blue-700 bg-blue-900/20 |
| failed | border-red-200 bg-red-50/50 | border-red-800 bg-red-900/20 |
| blocked | border-yellow-200 bg-yellow-50/50 | border-yellow-800 bg-yellow-900/20 |

---

## Testing

### Prerequisites
- Services running (backend, frontend, agent container)
- Agent created and started
- User authenticated

### Test: Basic Plan Viewing

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to agent detail page | Page loads with tabs |
| 2 | Click "Workplan" tab | WorkplanPanel renders, loading spinner shows briefly |
| 3 | Wait for load | Summary stats cards appear, plan list visible (or empty state) |

### Test: Status Filtering

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Have plans with different statuses | All plans visible with "All Plans" filter |
| 2 | Select "Active" filter | Only active plans shown |
| 3 | Select "Completed" filter | Only completed plans shown |
| 4 | Select "All Plans" again | All plans visible again |

### Test: Plan Detail Modal

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click on a plan in the list | Modal opens with full plan details |
| 2 | Verify plan metadata | Name, description, timestamps displayed |
| 3 | Verify progress bar | Shows correct completion % |
| 4 | Verify task list | All tasks shown with correct status icons |
| 5 | Click "Close" button | Modal closes |

### Test: Plan Actions

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open active plan modal | "Pause Plan" button visible |
| 2 | Click "Pause Plan" | Plan status changes to "paused", list refreshes |
| 3 | Open paused plan modal | "Resume Plan" button visible |
| 4 | Click "Resume Plan" | Plan status changes to "active" |
| 5 | Click "Delete" | Confirmation dialog appears |
| 6 | Confirm delete | Plan removed, modal closes, list refreshes |

### Test: Agent Not Running

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Stop the agent | Agent status shows "stopped" |
| 2 | Click "Workplan" tab | Special "Agent must be running" message displayed |
| 3 | Start the agent | Plans load automatically (watcher triggers) |

### Test: Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| No plans exist | Empty state with explanation shown |
| Plan with 0 tasks | Plan shows in list with 0/0 tasks |
| Very long task name | Truncated with ellipsis |
| Task with long result | Scrollable result box (max-h-24) |
| Multiple active tasks | Only first shown in current task banner |

---

## Related Flows

- **Upstream**: [workplan-system.md](workplan-system.md) - Backend Workplan infrastructure
- **Related**: [agent-lifecycle.md](agent-lifecycle.md) - Agent start required before viewing plans
- **Related**: [agent-network.md](agent-network.md) - Also displays plan stats

---

## Test Verification

> **Last Tested**: 2025-12-20
> **Status**: All Tests Passing

### Test Results Summary

| Test Suite | Result | Notes |
|------------|--------|-------|
| Basic Plan Viewing | Pass | Workplan tab loads, summary stats display correctly |
| Status Filtering | Pass | All filters (All/Active/Completed/Failed/Paused) work correctly |
| Plan Detail Modal | Pass | Modal shows full plan with tasks, timestamps, progress |
| Plan Actions | Pass | Pause/Resume toggles status, Delete removes plan with confirmation |
| Agent Not Running | Pass | Shows "Agent must be running to view plans" message |
| Empty State | Pass | Shows "No plans yet" with helpful guidance text |
| Long Names | Pass | Long plan/task names display properly without breaking layout |

### Issues Found

None - all features working as documented.

---

## Revision History

| Date | Changes |
|------|---------|
| 2025-12-19 | Line number verification after dark mode and modular agent-server refactor. Updated all frontend line numbers, backend router lines, added dark mode styling details |
| 2025-12-07 | Terminology refactor: Plans tab -> Workplan tab, PlansPanel -> WorkplanPanel, Task DAG -> Workplan |
| 2025-12-07 | Added Test Verification section - all tests passing |
| 2025-12-06 | Initial documentation of WorkplanPanel.vue component |
