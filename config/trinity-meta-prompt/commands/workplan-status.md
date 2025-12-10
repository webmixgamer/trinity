# Check Workplan Status

Display the current status of a workplan or all active workplans.

## Usage

```
/workplan-status [plan-id]
```

If no plan-id is provided, shows all active workplans.

## Instructions

1. Read workplan file(s) from `plans/active/`
2. Display status summary:
   - Workplan name and ID
   - Overall status (active/completed/failed/paused)
   - Task progress (X of Y completed)
   - Current active task (if any)
   - Blocked tasks and their dependencies

## Output Format

### Single Workplan

```
Workplan: {workplan-name} ({plan-id})
Status: {status}
Progress: {completed}/{total} tasks

Tasks:
  [x] task-1: Research existing patterns (completed)
  [>] task-2: Create user model (active)
  [ ] task-3: Implement login (blocked by task-2)
  [ ] task-4: Add tests (pending)
```

### All Workplans

```
Active Workplans:
  1. implement-auth (plan-abc123) - 2/5 tasks - active
  2. refactor-api (plan-def456) - 0/3 tasks - paused

Completed Workplans (recent):
  3. fix-login-bug (plan-ghi789) - 3/3 tasks - completed
```

## Legend

- `[x]` = completed
- `[>]` = active (currently working)
- `[ ]` = pending or blocked
- `[!]` = failed
