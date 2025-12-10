# Create a New Workplan

Create a new task workplan for the given objective.

## Usage

```
/workplan-create <workplan-name>
```

## Instructions

When this command is invoked, create a new workplan:

1. Generate a unique workplan ID: `plan-{timestamp}-{random}`
2. Create the workplan file at `plans/active/{plan-id}.yaml`
3. Structure the workplan with:
   - Clear task breakdown (aim for 3-10 tasks)
   - Explicit dependencies between tasks
   - Descriptive task names and descriptions

## Workplan Template

```yaml
id: {plan-id}
name: "{workplan-name}"
description: "{description of what this workplan accomplishes}"
created: "{ISO8601 timestamp}"
status: active
tasks:
  - id: task-1
    name: "{task name}"
    description: "{what this task accomplishes}"
    status: pending
    dependencies: []
    started_at: null
    completed_at: null
    result: null
```

## After Creation

1. Report the workplan ID and task list to the user
2. Begin working on the first task (set status to `active`)
3. Update the workplan as you make progress

## Example

```
/workplan-create implement-user-auth
```

Creates a workplan like:
```yaml
id: plan-1733400000-abc123
name: "implement-user-auth"
description: "Add user authentication to the application"
created: "2025-12-05T10:00:00Z"
status: active
tasks:
  - id: task-1
    name: "Research existing auth patterns"
    status: pending
    dependencies: []
  - id: task-2
    name: "Create user model"
    status: blocked
    dependencies: [task-1]
  - id: task-3
    name: "Implement login endpoint"
    status: blocked
    dependencies: [task-2]
```
