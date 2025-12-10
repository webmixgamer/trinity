# Phase 6: Workplan System (test-worker)

> **Purpose**: Validate Pillar I (Explicit Planning) - task DAG creation, dependencies, and workplan tracking
> **Duration**: ~20 minutes
> **Assumes**: Phase 5 PASSED (agent collaboration working, 8 agents running)
> **Output**: Workplan creation and task tracking verified
> **Agent**: test-worker

---

## Prerequisites

- ✅ Phase 5 PASSED
- ✅ All 8 agents running from GitHub templates
- ✅ test-worker agent exists and running
- ✅ Trinity meta-prompt injected in agents

---

## Background

**Pillar I: Explicit Planning**

Trinity agents can create workplans - task DAGs that:
- Persist outside the context window
- Have explicit dependencies between tasks
- Track state: pending → active → completed/failed
- Auto-archive when all tasks complete

The test-worker agent is configured to create and execute workplans on command.

---

## Test Steps

### Step 1: Navigate to test-worker Agent
**Action**:
1. Navigate to http://localhost:3000/agents/test-worker
2. Wait for page to load

**Verify**:
- [ ] Agent detail page loads
- [ ] Status shows "running"
- [ ] Chat tab is active

**Take Snapshot**: `phase6-01-worker-initial.png`

---

### Step 2: Check Plans Tab Initial State
**Action**:
1. Click "Plans" tab in agent detail page

**Expected**:
- Empty state or no active plans
- Message: "No workplans" or similar

**Verify**:
- [ ] Plans tab exists and is clickable
- [ ] No existing workplans (or document if there are)

**Take Snapshot**: `phase6-02-plans-empty.png`

---

### Step 3: Trigger Workplan Creation
**Action**:
1. Click Chat tab
2. Send message: "Create a workplan to process 3 tasks with dependencies"

**Expected**:
- Agent acknowledges request
- Creates workplan with task structure
- Response includes plan ID and task list

**Verify**:
- [ ] Response confirms workplan creation
- [ ] Plan ID or name mentioned
- [ ] Task list mentioned in response

**Wait**: 15-20 seconds for agent to process

**Take Snapshot**: `phase6-03-workplan-created.png`

---

### Step 4: Verify Workplan in Plans Tab
**Action**:
1. Click "Plans" tab
2. Wait for plans to load

**Expected**:
- At least one workplan visible
- Workplan shows:
  - Plan name/ID
  - Status (pending/active/completed)
  - Task count
  - Creation timestamp

**Verify**:
- [ ] Workplan appears in list
- [ ] Status badge visible (pending, active, or completed)
- [ ] Task count displayed

**Take Snapshot**: `phase6-04-plans-list.png`

---

### Step 5: Verify Task Details
**Action**:
1. Click on the workplan to expand/view details
2. Examine task list

**Expected**:
- Task list shows:
  - Task names/descriptions
  - Individual task status (pending, active, completed, failed)
  - Dependencies (if any)
  - Order/sequence

**Verify**:
- [ ] Tasks listed with names
- [ ] Each task has status indicator
- [ ] Dependencies shown (task-2 depends on task-1, etc.)
- [ ] Status indicators: ● pending, ◉ active, ✓ completed

**Take Snapshot**: `phase6-05-task-details.png`

---

### Step 6: Verify Task Status on Dashboard
**Action**:
1. Navigate to Dashboard (/)
2. Find test-worker node

**Expected**:
- Tasks indicator on node shows current task
- NOT showing "—" (dash indicates no tasks)
- Should show "Task 1/3" or similar

**CRITICAL VALIDATION**:
- [ ] Task indicator shows task name/progress, NOT "—"

**If stuck at "—"**: Document as bug - task tracking not working

**Take Snapshot**: `phase6-06-dashboard-tasks.png`

---

### Step 7: Execute Tasks via Chat
**Action**:
1. Navigate back to test-worker agent
2. Send: "Execute the next pending task"
3. Wait for response
4. Repeat for remaining tasks

**Expected**:
- Each message triggers task execution
- Task status transitions: pending → active → completed
- Response confirms task completion

**Verify**:
- [ ] Task 1 completes
- [ ] Task 2 unblocks (if dependent on task 1)
- [ ] Tasks transition correctly

**Take Snapshot**: `phase6-07-task-execution.png`

---

### Step 8: Verify Context Growth During Workplan
**Action**:
1. Check context percentage after task executions
2. Compare to initial state

**CRITICAL VALIDATION**:
- [ ] Context % INCREASED (not stuck at 0%)
- [ ] Multiple task executions = higher context %

**If stuck at 0%**: Document as critical bug

**Take Snapshot**: `phase6-08-context-growth.png`

---

### Step 9: Complete All Tasks
**Action**:
1. Continue sending execution commands until all tasks done
2. Send: "Complete all remaining tasks"

**Expected**:
- All tasks marked as completed
- Workplan status changes to "completed"
- Plan may move to archive

**Verify**:
- [ ] All tasks show ✓ completed
- [ ] No pending tasks remain
- [ ] Workplan status = completed

**Take Snapshot**: `phase6-09-all-tasks-complete.png`

---

### Step 10: Verify Workplan Archival
**Action**:
1. Check Plans tab
2. Look for archive section or completed plans

**Expected**:
- Completed workplan visible in archive or marked as done
- Active plans section empty (if no other plans)

**Verify**:
- [ ] Completed plan accessible
- [ ] Can view historical task execution

**Take Snapshot**: `phase6-10-plan-archived.png`

---

### Step 11: Verify API Endpoints (Fallback)
**Action**: Use API to verify workplan state

```bash
# Get plans summary
curl -s http://localhost:8000/api/agents/test-worker/plans \
  -H "Authorization: Bearer $TOKEN" | jq

# Get specific plan details
curl -s http://localhost:8000/api/agents/test-worker/plans/{plan_id} \
  -H "Authorization: Bearer $TOKEN" | jq

# Get aggregate stats
curl -s http://localhost:8000/api/plans/summary \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Verify**:
- [ ] API returns workplan data
- [ ] Tasks have correct status
- [ ] Dependencies listed

---

## Critical Validations

| Validation | Status | Notes |
|------------|--------|-------|
| Plans tab shows workplan | [ ] | Must list created plan |
| Tasks have status indicators | [ ] | pending/active/completed |
| Dependencies displayed | [ ] | Task order/blocking shown |
| Task indicator NOT "—" | [ ] | Must show actual task name |
| Context % increases | [ ] | Not stuck at 0% |
| Workplan completes | [ ] | Status changes after all tasks done |

---

## Success Criteria

Phase 6 is **PASSED** when:
- ✅ Workplan created from chat command
- ✅ Plans tab shows workplan with tasks
- ✅ Tasks show dependencies and status
- ✅ Task status transitions work (pending → active → completed)
- ✅ Dashboard shows task progress (not "—")
- ✅ Context % grows during execution
- ✅ Workplan marked complete after all tasks done

## Failure Conditions

Phase 6 **FAILS** if:
- ❌ Plans tab doesn't show workplan
- ❌ Tasks have no status indicators
- ❌ Task indicator stuck at "—" on Dashboard
- ❌ Context stuck at 0%
- ❌ Workplan never completes

---

## Known Issues

1. **Task indicator "—"**: Dashboard may not update task indicator in real-time
   - Workaround: Check Plans tab directly

2. **Context at 0%**: Known bug - context calculation may not work
   - Document and continue

3. **Plan not visible**: If UI doesn't show plan, verify via API

---

## Next Phase

Proceed to **Phase 7: Scheduling** (`PHASE_07_SCHEDULING.md`)

---

## Troubleshooting

### Workplan Not Created
- Check agent logs: `docker logs agent-test-worker`
- Verify Trinity injection: Agent should have `.trinity/` directory
- Try explicit command: "Create a workplan named 'test-plan' with tasks: task-1, task-2, task-3"

### Tasks Not Executing
- Check agent is processing (not stuck)
- Verify dependencies (blocked tasks can't execute)
- Try: "Execute task-1 now"

### Plans Tab Empty
- Use API to verify plans exist
- Check for JavaScript errors in browser console
- Refresh page and retry

### Context Not Growing
- Known bug - document as critical issue
- Verify token counting is implemented
- Check API: `GET /api/agents/test-worker` for context stats

---

## Screenshots Summary

| Screenshot | Purpose |
|------------|---------|
| phase6-01-worker-initial.png | Initial agent state |
| phase6-02-plans-empty.png | Plans tab before creation |
| phase6-03-workplan-created.png | Chat creating workplan |
| phase6-04-plans-list.png | Plans tab with workplan |
| phase6-05-task-details.png | Task list and dependencies |
| phase6-06-dashboard-tasks.png | Dashboard task indicator |
| phase6-07-task-execution.png | Task execution via chat |
| phase6-08-context-growth.png | Context percentage |
| phase6-09-all-tasks-complete.png | Completed workplan |
| phase6-10-plan-archived.png | Archived/completed state |

---

**Phase Status**: Testing Pillar I - Explicit Planning
**Artifacts**: Workplan created, tasks executed, plan archived
**Next**: Phase 7 - Scheduling
