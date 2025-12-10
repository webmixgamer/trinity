# Update Workplan Task Status

Update the status of a task within a workplan.

## Usage

```
/workplan-update <plan-id> <task-id> <status> [result]
```

### Status Values

- `active` - Start working on this task
- `completed` - Task finished successfully
- `failed` - Task failed (include reason in result)
- `pending` - Reset task to pending
- `blocked` - Manually block task

## Instructions

1. Load the workplan from `plans/active/{plan-id}.yaml`
2. Find the task by task-id
3. Update the task:
   - Set new status
   - Set `started_at` if status = active
   - Set `completed_at` if status = completed/failed
   - Set `result` if provided
4. Update dependent tasks:
   - If task completed, unblock tasks that depended on it
   - If task failed, consider failing dependent tasks
5. Update overall workplan status:
   - If all tasks completed → workplan status = completed
   - If any critical task failed → consider workplan status = failed
6. Save the updated workplan

## Side Effects

When marking a task `completed`:
- All tasks that ONLY depended on this task become `pending`
- Check if workplan is now complete

When marking a task `failed`:
- Tasks depending on this remain `blocked`
- Consider if workplan should be marked `failed`

## Examples

```
# Start working on task-2
/workplan-update plan-abc123 task-2 active

# Complete task-2 with result
/workplan-update plan-abc123 task-2 completed "Created User model with email/password fields"

# Mark task-3 as failed
/workplan-update plan-abc123 task-3 failed "API endpoint already exists"
```

## Output

After updating, display the updated workplan status (same as `/workplan-status`).
