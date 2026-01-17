# Feature: Process Definition

> YAML-based process definition with validation, versioning, and publishing workflow

---

## Overview

Process definitions are declarative YAML documents that describe workflows. They specify steps, dependencies, triggers, and outputs. Definitions follow a lifecycle: **Draft** -> **Published** -> **Archived**.

**Key Capabilities:**
- YAML-based schema with step types (agent_task, gateway, approval, timer, notification, sub_process)
- Multi-level validation (YAML syntax, schema, semantic, agent existence)
- Version management with immutable published versions
- Live preview in editor

---

## Entry Points

- **UI**: `ProcessList.vue` -> "Create Process" button -> `ProcessEditor.vue`
- **UI**: `ProcessList.vue` -> Click process card -> `ProcessEditor.vue` (edit mode)
- **API**: `POST /api/processes` - Create new process
- **API**: `PUT /api/processes/{id}` - Update draft process
- **API**: `POST /api/processes/{id}/publish` - Publish draft

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  ProcessEditor.vue                                                       │    │
│  │  ├── YAML Editor (Monaco with syntax highlighting)                       │    │
│  │  ├── Live Preview (flow diagram)                                         │    │
│  │  ├── Validation panel (errors/warnings)                                  │    │
│  │  └── Roles Tab (RoleMatrix.vue)                                         │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼ POST /api/processes
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Backend                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  routers/processes.py                                                    │    │
│  │  ├── create_process()       - Parse YAML, validate, save draft          │    │
│  │  ├── update_process()       - Update draft only                          │    │
│  │  ├── validate_yaml()        - Validate without saving                    │    │
│  │  ├── publish_process()      - Validate and publish                       │    │
│  │  └── archive_process()      - Archive published process                  │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  services/validator.py                                                   │    │
│  │  ├── validate_yaml()        - Full validation pipeline                   │    │
│  │  ├── _validate_schema()     - Required fields, types                     │    │
│  │  ├── _validate_step_schema()- Step-type-specific rules                   │    │
│  │  ├── _validate_step_roles() - EMI pattern validation                     │    │
│  │  ├── _check_agents()        - Agent existence (warnings)                 │    │
│  │  └── _check_sub_processes() - Sub-process existence (warnings)           │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  domain/aggregates.py - ProcessDefinition                                │    │
│  │  ├── from_yaml_dict()       - Parse YAML dict to aggregate               │    │
│  │  ├── validate()             - Domain invariant checks                    │    │
│  │  ├── publish()              - Transition to PUBLISHED                    │    │
│  │  ├── archive()              - Transition to ARCHIVED                     │    │
│  │  └── create_new_version()   - Clone for new version                      │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  repositories/sqlite_definitions.py                                      │    │
│  │  ├── save()                 - Upsert definition                          │    │
│  │  ├── get_by_id()            - Load by ProcessId                          │    │
│  │  ├── list_all()             - Paginated list with filters                │    │
│  │  └── delete()               - Remove definition                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## YAML Schema

### Minimal Example

```yaml
name: simple-research
version: 1
description: Research a topic using an agent

steps:
  - id: research
    type: agent_task
    agent: research-agent
    message: Research the topic: {{input.topic}}
```

### Full Example with All Features

```yaml
name: content-pipeline
version: 1
description: Generate, review, and publish content

triggers:
  - id: daily-run
    type: schedule
    cron: "0 9 * * *"
    timezone: America/New_York

steps:
  - id: research
    name: Research Topic
    type: agent_task
    agent: research-agent
    message: Research the topic: {{input.topic}}
    timeout: 10m
    retry:
      max_attempts: 3
      initial_delay: 10s
      backoff_multiplier: 2
    roles:
      executor: research-agent
      informed:
        - analyst-agent

  - id: write
    name: Write Draft
    type: agent_task
    agent: writer-agent
    message: |
      Write an article based on:
      {{steps.research.output}}
    depends_on: [research]
    timeout: 15m
    roles:
      executor: writer-agent
      monitors:
        - editor-agent

  - id: review
    name: Human Review
    type: human_approval
    title: Review Draft
    description: Please review the generated content
    assignees:
      - editor@example.com
    timeout: 48h
    depends_on: [write]

  - id: check-approval
    name: Check Decision
    type: gateway
    gateway_type: exclusive
    depends_on: [review]
    routes:
      - condition: "{{steps.review.decision}} == 'approved'"
        target: publish
      - condition: "{{steps.review.decision}} == 'rejected'"
        target: revise
    default_route: revise

  - id: revise
    name: Revise Draft
    type: agent_task
    agent: writer-agent
    message: |
      Revise based on feedback:
      {{steps.review.feedback}}
    depends_on: [check-approval]
    condition: "{{steps.review.decision}} == 'rejected'"

  - id: publish
    name: Publish
    type: notification
    channel: slack
    message: "New article published: {{steps.write.title}}"
    depends_on: [check-approval]
    condition: "{{steps.review.decision}} == 'approved'"

outputs:
  - name: article
    source: "{{steps.write.output}}"
    description: The final article content
```

---

## Step Types

| Type | Required Fields | Description |
|------|-----------------|-------------|
| `agent_task` | `agent`, `message` | Execute task via Trinity agent |
| `human_approval` | - | Gate requiring human decision |
| `gateway` | - | Conditional branching |
| `timer` | - | Wait for duration/timestamp |
| `notification` | `channel`, `message` | Send notification |
| `sub_process` | `process_name` | Call another process |

### Step Type: agent_task

```yaml
- id: research
  type: agent_task
  agent: research-agent         # Required: agent name
  message: Research {{input.topic}}  # Required: task message
  timeout: 5m                   # Optional: default 5m
  model: claude-sonnet-4-20250514        # Optional: specific model
  temperature: 0.7              # Optional: 0-2
  retry:
    max_attempts: 3             # Default: 1
    initial_delay: 10s          # Default: 5s
    backoff_multiplier: 2       # Default: 2
  on_error:
    action: fail_process        # fail_process | skip_step | goto_step
    target_step: error-handler  # Required if action is goto_step
```

### Step Type: human_approval

```yaml
- id: review
  type: human_approval
  title: Review Required        # Optional: display title
  description: Please review    # Optional: details
  assignees:                    # Optional: if empty, anyone can approve
    - user@example.com
  timeout: 24h                  # Optional: default 24h
```

### Step Type: gateway

```yaml
- id: decision
  type: gateway
  gateway_type: exclusive       # exclusive | parallel | inclusive
  routes:
    - condition: "{{steps.check.result}} == 'pass'"
      target: success
    - condition: "{{steps.check.result}} == 'fail'"
      target: failure
  default_route: failure        # Optional: fallback if no routes match
```

### Step Type: sub_process

```yaml
- id: call-child
  type: sub_process
  process_name: child-process   # Required: name of process to call
  version: 2                    # Optional: specific version
  input_mapping:                # Optional: map parent data to child input
    topic: "{{input.topic}}"
  output_key: result            # Optional: key in output, default "result"
  wait_for_completion: true     # Optional: default true
  timeout: 1h                   # Optional: default 1h
```

---

## Validation Levels

Validation happens in four levels:

### Level 1: YAML Syntax

```python
# validator.py:199-206
try:
    data = yaml.safe_load(yaml_content)
except yaml.YAMLError as e:
    result.add_error(message=f"Invalid YAML syntax: {e}")
```

### Level 2: Schema Validation

```python
# validator.py:284-353 (_validate_schema)
# Required fields: name, steps
# Type checks: steps must be a list
# Step-type-specific fields (agent_task requires agent, message)
```

### Level 3: Semantic Validation

```python
# aggregates.py:203-239 (ProcessDefinition.validate)
# - Duplicate step IDs
# - Invalid dependency references
# - Circular dependencies
# - Empty process name
# - No steps defined
```

### Level 4: Agent/Process Existence (Warnings)

```python
# validator.py:624-695 (_check_agents)
# Warns if referenced agent doesn't exist or isn't running
# Warns if sub-process doesn't exist or isn't published
```

---

## API Endpoints

| Method | Path | Description | File:Line |
|--------|------|-------------|-----------|
| POST | `/api/processes` | Create new process | processes.py:180-219 |
| GET | `/api/processes` | List processes | processes.py:222-256 |
| GET | `/api/processes/{id}` | Get process detail | processes.py:259-278 |
| PUT | `/api/processes/{id}` | Update draft process | processes.py:281-347 |
| DELETE | `/api/processes/{id}` | Delete process | processes.py:350-378 |
| POST | `/api/processes/{id}/validate` | Validate existing | processes.py:381-405 |
| POST | `/api/processes/validate` | Validate YAML | processes.py:408-421 |
| POST | `/api/processes/{id}/publish` | Publish draft | processes.py:424-475 |
| POST | `/api/processes/{id}/archive` | Archive process | processes.py:478-519 |
| POST | `/api/processes/{id}/new-version` | Create new version | processes.py:522-549 |

---

## Flow Details

### 1. Create Process Flow

**User Action:** Click "Create Process" -> Write YAML -> Click "Save"

```
ProcessEditor.vue                 Backend                           Database
----------------                  -------                           --------
User types YAML
onValidate() debounced (300ms)
POST /api/processes/validate  →   validate_yaml()               
                                  ├── yaml.safe_load()
                                  ├── _validate_schema()
                                  ├── ProcessDefinition.from_yaml_dict()
                                  └── _check_agents() (warnings)
                              ←   ValidationResponse
Show errors/warnings

User clicks "Save"
POST /api/processes           →   create_process()
                                  ├── validate_yaml()
                                  ├── ProcessDefinition.from_yaml_dict()
                                  └── repo.save(definition)        → INSERT
                              ←   ProcessDetail
Navigate to editor with ID
```

### 2. Publish Process Flow

**User Action:** Click "Publish" button on draft process

```
ProcessEditor.vue                 Backend                           Database
----------------                  -------                           --------
User clicks "Publish"
POST /{id}/publish            →   publish_process()
                                  ├── repo.get_by_id()             → SELECT
                                  ├── Check status == DRAFT
                                  ├── definition.publish()
                                  │   └── definition.validate()
                                  ├── repo.save(published)         → UPDATE
                                  └── _register_process_schedules()
                              ←   ProcessDetail (status=published)
Update UI to show published
```

### 3. Version Management Flow

**User Action:** Click "New Version" on published process

```
ProcessList.vue                   Backend                           Database
---------------                   -------                           --------
User clicks "New Version"
POST /{id}/new-version        →   create_new_version()
                                  ├── repo.get_by_id()             → SELECT
                                  ├── definition.create_new_version()
                                  │   ├── Generate new ProcessId
                                  │   ├── Increment version
                                  │   └── Set status=DRAFT
                                  └── repo.save(new_version)       → INSERT
                              ←   ProcessDetail (new ID, status=draft)
Navigate to new version editor
```

---

## Domain Model

### ProcessDefinition Aggregate

```python
# aggregates.py:34-362

@dataclass
class ProcessDefinition:
    id: ProcessId
    name: str
    description: str
    version: Version
    status: DefinitionStatus      # draft, published, archived
    steps: list[StepDefinition]
    outputs: list[OutputConfig]
    triggers: list[TriggerConfig]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    @classmethod
    def from_yaml_dict(cls, data: dict) -> ProcessDefinition:
        """Parse YAML dictionary into aggregate."""

    def validate(self) -> list[str]:
        """Run domain invariant checks."""

    def publish(self) -> ProcessDefinition:
        """Validate and transition to PUBLISHED."""

    def archive(self) -> ProcessDefinition:
        """Transition to ARCHIVED."""

    def create_new_version(self) -> ProcessDefinition:
        """Clone with incremented version and new ID."""
```

### StepDefinition Entity

```python
# entities.py:76-266

@dataclass
class StepDefinition:
    id: StepId
    name: str
    type: StepType
    config: StepConfig            # Type-specific config
    dependencies: list[StepId]
    condition: Optional[str]
    retry_policy: RetryPolicy
    error_policy: ErrorPolicy
    compensation: Optional[CompensationConfig]
    roles: Optional[StepRoles]    # EMI pattern

    @classmethod
    def from_dict(cls, data: dict) -> StepDefinition:
        """Parse from YAML step dict."""
```

---

## Database Schema

```sql
-- repositories/sqlite_definitions.py

CREATE TABLE process_definitions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    yaml_content TEXT,
    steps_json TEXT,
    outputs_json TEXT,
    triggers_json TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    published_at TEXT
);

CREATE INDEX idx_definitions_name ON process_definitions(name);
CREATE INDEX idx_definitions_status ON process_definitions(status);
```

---

## Frontend Components

### ProcessEditor.vue

| Section | Lines | Purpose |
|---------|-------|---------|
| YAML Editor | 50-120 | Monaco editor with YAML mode |
| Validation Panel | 130-180 | Display errors/warnings |
| Flow Preview | 200-280 | Visual step diagram |
| Tabs (YAML/Roles) | 300-350 | Switch between editor and role matrix |

### Key Methods

```javascript
// ProcessEditor.vue

// Debounced validation on YAML change
const onYamlChange = useDebounceFn(async (content) => {
  const result = await processesStore.validateYaml(content)
  validationErrors.value = result.errors
  validationWarnings.value = result.warnings
}, 300)

// Save process
async function saveProcess() {
  if (isNew.value) {
    const process = await processesStore.createProcess(yamlContent.value)
    router.push(`/processes/${process.id}`)
  } else {
    await processesStore.updateProcess(processId, yamlContent.value)
  }
}

// Publish process
async function publishProcess() {
  await processesStore.publishProcess(processId)
}
```

---

## Error Handling

| Error | HTTP Status | Message |
|-------|-------------|---------|
| Invalid YAML syntax | 422 | "Invalid YAML syntax: {details}" |
| Missing required field | 422 | "Missing required field: 'name'" |
| Invalid step type | 422 | "Invalid step type 'foo'" |
| Circular dependency | 422 | "Circular dependency detected: a -> b -> a" |
| Update non-draft | 400 | "Cannot update process in 'published' status" |
| Publish non-draft | 400 | "Cannot publish process in 'archived' status" |
| Delete published | 400 | "Cannot delete PUBLISHED processes. Archive first." |

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- At least one agent created (for agent existence warnings)

### Test Cases

1. **Create minimal process**
   - Action: Create process with just name and one agent_task step
   - Expected: Saves as draft, warnings about agent not existing

2. **Validation errors**
   - Action: Submit YAML missing required fields
   - Expected: 422 with specific error messages and paths

3. **Circular dependency detection**
   - Action: Create steps where A depends on B, B depends on A
   - Expected: Error "Circular dependency detected"

4. **Publish workflow**
   - Action: Save draft -> Publish
   - Expected: Status changes to published, becomes immutable

5. **Version management**
   - Action: Create new version from published process
   - Expected: New draft with incremented version number

---

## Related Flows

- [process-execution.md](./process-execution.md) - How definitions are executed
- [agent-roles-emi.md](./agent-roles-emi.md) - EMI role validation details
- [process-scheduling.md](./process-scheduling.md) - Trigger configuration

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-16 | Initial creation |
