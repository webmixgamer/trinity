# Understanding Step Types

Steps are the building blocks of every process. Each step type serves a different purpose in your workflow.

## Overview

| Step Type | Purpose | Use When |
|-----------|---------|----------|
| `agent_task` | Execute work via an AI agent | You need an agent to process, generate, or analyze |
| `human_approval` | Pause for human review | Quality gates, compliance, or decisions needed |
| `gateway` | Make conditional decisions | Branching logic based on previous outputs |
| `timer` | Wait for a duration | Rate limiting, scheduled delays, or coordination |

---

## Agent Task

The most common step type. Sends a message to an AI agent and waits for the response.

### Basic Structure

```yaml
- id: analyze-data
  name: Analyze Data
  type: agent_task
  agent: analyst
  message: |
    Analyze the following data and identify key trends:
    {{input.data}}
  timeout: 10m
```

### Required Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier for the step |
| `type` | Must be `agent_task` |
| `agent` | Name of the agent to execute the task |
| `message` | The prompt/instructions sent to the agent |

### Optional Fields

| Field | Description | Default |
|-------|-------------|---------|
| `name` | Human-readable name | Same as `id` |
| `depends_on` | List of step IDs that must complete first | `[]` |
| `timeout` | Maximum execution time | `30m` |
| `retry` | Retry configuration on failure | No retry |

### Timeout Format

Timeouts use duration strings:
- `30s` — 30 seconds
- `5m` — 5 minutes
- `1h` — 1 hour
- `1d` — 1 day

### Retry Configuration

```yaml
- id: flaky-api-call
  type: agent_task
  agent: api-agent
  message: Fetch data from external API
  timeout: 2m
  retry:
    max_attempts: 3
    delay: 30s
```

---

## Human Approval

Pauses the process until a human approves or rejects.

### Basic Structure

```yaml
- id: manager-review
  name: Manager Review
  type: human_approval
  depends_on: [draft-report]
  title: Review Report Draft
  description: |
    Please review the draft report:
    {{steps.draft-report.output}}
    
    Approve to proceed with publication.
  timeout: 24h
```

### Required Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `type` | Must be `human_approval` |
| `title` | Short title shown in approval UI |
| `description` | Detailed description of what to review |

### Optional Fields

| Field | Description | Default |
|-------|-------------|---------|
| `timeout` | Time to wait before timeout action | `24h` |
| `timeout_action` | What happens on timeout: `approve`, `reject`, or `skip` | `skip` |

### Accessing Approval Decisions

After approval, you can access the decision in subsequent steps:

```yaml
- id: next-step
  depends_on: [manager-review]
  message: |
    The manager {{steps.manager-review.output.decision}}.
    Comments: {{steps.manager-review.output.comments}}
```

---

## Gateway

Makes decisions based on conditions. Routes execution to different paths.

### Basic Structure

```yaml
- id: check-severity
  name: Check Severity
  type: gateway
  depends_on: [triage]
  conditions:
    - expression: "{{steps.triage.output.severity}} == 'high'"
      next: escalate
    - expression: "{{steps.triage.output.severity}} == 'medium'"
      next: standard-handling
    - default: true
      next: archive
```

### Required Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `type` | Must be `gateway` |
| `conditions` | List of condition/next pairs |

### Condition Expressions

Conditions use simple comparison expressions:

```yaml
# Equality
"{{steps.x.output.status}} == 'approved'"

# Numeric comparison
"{{steps.x.output.score}} > 80"

# Contains (for strings/arrays)
"{{steps.x.output.tags}} contains 'urgent'"

# Boolean
"{{steps.x.output.is_valid}} == true"
```

### Default Case

Always include a default condition to handle unexpected values:

```yaml
conditions:
  - expression: "..."
    next: path-a
  - default: true
    next: fallback-path
```

---

## Timer

Pauses execution for a specified duration.

### Basic Structure

```yaml
- id: cooldown
  name: Rate Limit Cooldown
  type: timer
  depends_on: [api-call]
  duration: 1m
```

### Required Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `type` | Must be `timer` |
| `duration` | How long to wait (e.g., `30s`, `5m`, `1h`) |

### Use Cases

1. **Rate Limiting**
   ```yaml
   - id: wait-between-calls
     type: timer
     duration: 2s
   ```

2. **Scheduled Delays**
   ```yaml
   - id: wait-for-processing
     type: timer
     duration: 5m
   ```

3. **Business Hours Wait**
   Combined with gateways to handle time-based logic.

---

## Step Dependencies

Dependencies control execution order. Steps without dependencies run in parallel at process start.

### Sequential Execution

```yaml
steps:
  - id: step-a
    ...
  - id: step-b
    depends_on: [step-a]  # Waits for step-a
  - id: step-c
    depends_on: [step-b]  # Waits for step-b
```

### Parallel Execution

```yaml
steps:
  - id: task-1
    ...  # Runs immediately
  - id: task-2
    ...  # Runs in parallel with task-1
  - id: combine
    depends_on: [task-1, task-2]  # Waits for both
```

### Fan-out / Fan-in

```yaml
steps:
  - id: start
    ...
    
  - id: path-a
    depends_on: [start]
  - id: path-b
    depends_on: [start]
  - id: path-c
    depends_on: [start]
    
  - id: merge
    depends_on: [path-a, path-b, path-c]
```

---

## Best Practices

### 1. Use Descriptive IDs
```yaml
# Good
- id: validate-customer-email
  
# Avoid
- id: step1
```

### 2. Set Appropriate Timeouts
Match timeouts to expected duration plus buffer:
- Quick API calls: `30s` - `2m`
- Complex analysis: `5m` - `15m`
- Human approval: `1h` - `48h`

### 3. Add Human Checkpoints
For critical workflows, add approval steps before irreversible actions.

### 4. Handle Errors
Configure retries for steps that may fail transiently.

## Next Steps

- [YAML Schema Reference](/processes/docs/reference/yaml-schema) — Complete schema documentation
- [Variable Interpolation](/processes/docs/reference/variables) — Advanced variable usage
