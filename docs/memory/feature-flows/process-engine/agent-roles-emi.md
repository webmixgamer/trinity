# Feature: Agent Roles (EMI Pattern)

> Executor/Monitor/Informed role assignments for process steps enabling multi-agent collaboration

---

## Overview

The EMI (Executor/Monitor/Informed) pattern defines agent roles within process steps:

| Role | Cardinality | Purpose |
|------|-------------|---------|
| **Executor** | Exactly one | The agent that performs the actual work |
| **Monitor** | Zero or more | Agents that own the outcome and can intervene |
| **Informed** | Zero or more | Agents that receive events for learning/awareness |

This pattern enables multi-agent collaboration where specialized agents work together while maintaining clear accountability.

---

## Entry Points

- **YAML**: `roles:` block in step definition
- **UI**: `ProcessEditor.vue` -> "Roles" tab -> `RoleMatrix.vue`
- **Backend**: Role validation in `ProcessValidator`
- **Notification**: `InformedAgentNotifier` on step completion/failure

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  ProcessEditor.vue                                                       │    │
│  │  ├── YAML Tab (direct roles editing)                                    │    │
│  │  └── Roles Tab                                                          │    │
│  │      └── RoleMatrix.vue                                                 │    │
│  │          ├── Step list (rows)                                           │    │
│  │          ├── Role columns (Executor, Monitors, Informed)                │    │
│  │          └── Agent selection (dropdown + multi-select)                  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ YAML with roles
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Backend                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  services/validator.py - ProcessValidator                                │    │
│  │  └── _validate_step_roles()                                              │    │
│  │      ├── Executor required if roles specified                           │    │
│  │      ├── Monitors must be list                                          │    │
│  │      ├── Informed must be list                                          │    │
│  │      └── Warn if agent in multiple roles                                │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      │ On step complete/fail                     │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  engine/execution_engine.py                                              │    │
│  │  └── _notify_informed_agents()                                           │    │
│  │      └── InformedAgentNotifier.notify_step_completed()                  │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  services/informed_notifier.py - InformedAgentNotifier                   │    │
│  │  ├── _deliver_via_mcp()         - Real-time MCP message                 │    │
│  │  └── _write_to_memory()         - NDJSON file persistence               │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Agent Containers                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │
│  │  executor-agent │  │  monitor-agent  │  │  informed-agent │                 │
│  │  (does work)    │  │  (can intervene)│  │  (learns)       │                 │
│  │                 │  │                 │  │                 │                 │
│  │                 │  │                 │  │  .trinity/      │                 │
│  │                 │  │                 │  │   events/       │                 │
│  │                 │  │                 │  │    *.ndjson     │                 │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## YAML Configuration

### Basic Role Assignment

```yaml
- id: research
  type: agent_task
  agent: research-agent
  message: Research the topic
  roles:
    executor: research-agent
```

### Full EMI Pattern

```yaml
- id: critical-analysis
  type: agent_task
  agent: analyst-agent
  message: Perform critical analysis
  roles:
    executor: analyst-agent          # Required
    monitors:                        # Optional
      - quality-agent
      - manager-agent
    informed:                        # Optional
      - learning-agent
      - archive-agent
```

### Role-Only Step (Non-Agent)

```yaml
- id: approval
  type: human_approval
  title: Manager Approval
  roles:
    executor: approval-system        # Can be system/process name
    monitors:
      - manager-agent
    informed:
      - audit-agent
```

---

## Domain Model

### StepRoles Entity

```python
# entities.py:34-73

@dataclass
class StepRoles:
    """
    EMI role assignments for a process step.
    """
    executor: str                     # Required - agent that performs work
    monitors: list[str] = field(default_factory=list)   # Can intervene
    informed: list[str] = field(default_factory=list)   # Receive notifications

    @classmethod
    def from_dict(cls, data: dict) -> "StepRoles":
        return cls(
            executor=data.get("executor", ""),
            monitors=data.get("monitors", []),
            informed=data.get("informed", []),
        )

    def to_dict(self) -> dict:
        result = {"executor": self.executor}
        if self.monitors:
            result["monitors"] = self.monitors
        if self.informed:
            result["informed"] = self.informed
        return result

    def all_agents(self) -> list[str]:
        """Return all agents involved in this step."""
        agents = [self.executor] if self.executor else []
        agents.extend(self.monitors)
        agents.extend(self.informed)
        return agents
```

### AgentRole Enum

```python
# enums.py

class AgentRole(str, Enum):
    EXECUTOR = "executor"
    MONITOR = "monitor"
    INFORMED = "informed"
```

### InformedNotification Event

```python
# events.py

@dataclass
class InformedNotification:
    """Domain event for notifying informed agents."""
    event_type_name: str           # step_completed, step_failed
    process_name: str
    execution_id: ExecutionId
    step_id: StepId
    step_name: str
    output_summary: str            # Truncated output
    timestamp: datetime = field(default_factory=_utcnow)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type_name,
            "process_name": self.process_name,
            "execution_id": str(self.execution_id),
            "step_id": str(self.step_id),
            "step_name": self.step_name,
            "output_summary": self.output_summary,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
```

---

## Validation

### Role Validation Rules

```python
# validator.py:426-511 (_validate_step_roles)

def _validate_step_roles(self, step: dict, index: int, step_type: str, result: ValidationResult):
    roles = step.get("roles", {})

    if not isinstance(roles, dict):
        result.add_error("Field 'roles' must be an object")
        return

    # Executor is required if roles are specified
    executor = roles.get("executor")
    if not executor:
        result.add_error("Roles must include an 'executor' agent")
    elif not isinstance(executor, str):
        result.add_error("Field 'executor' must be a string")
    else:
        # For agent_task, executor should match step's agent field
        if step_type == "agent_task":
            step_agent = step.get("agent")
            if step_agent and executor != step_agent:
                result.add_warning(
                    f"Role executor '{executor}' differs from step agent '{step_agent}'"
                )

    # Validate monitors list
    monitors = roles.get("monitors", [])
    if not isinstance(monitors, list):
        result.add_error("Field 'monitors' must be a list")
    else:
        for monitor in monitors:
            if not isinstance(monitor, str):
                result.add_error("Monitor must be a string (agent name)")
            elif executor and monitor == executor:
                result.add_warning(f"Agent '{monitor}' is both executor and monitor (redundant)")

    # Validate informed list
    informed = roles.get("informed", [])
    if not isinstance(informed, list):
        result.add_error("Field 'informed' must be a list")
    else:
        for agent in informed:
            if not isinstance(agent, str):
                result.add_error("Informed agent must be a string")
            elif executor and agent == executor:
                result.add_warning(f"Agent '{agent}' is both executor and informed (redundant)")
            elif isinstance(monitors, list) and agent in monitors:
                result.add_warning(f"Agent '{agent}' is in both monitors and informed")
```

---

## InformedAgentNotifier

### Notification Flow

```python
# informed_notifier.py:57-125

class InformedAgentNotifier:
    """Delivers step events to informed agents."""

    async def notify_step_completed(
        self,
        step: StepDefinition,
        event: StepCompleted,
        execution_context: dict,
    ) -> list[NotificationResult]:
        if not step.roles or not step.roles.informed:
            return []

        notification = InformedNotification(
            event_type_name="step_completed",
            process_name=execution_context.get("process_name"),
            execution_id=event.execution_id,
            step_id=event.step_id,
            step_name=event.step_name,
            output_summary=self._summarize_output(event.output),
            metadata={
                "cost": str(event.cost),
                "duration_seconds": event.duration.seconds,
            },
        )

        return await self._notify_agents(step.roles.informed, notification)

    async def notify_step_failed(self, step, event, context) -> list[NotificationResult]:
        # Similar to notify_step_completed, with error details
        ...
```

### Delivery Mechanisms

```python
# informed_notifier.py:193-240

async def _notify_single_agent(self, agent_name: str, notification) -> NotificationResult:
    result = NotificationResult(agent_name=agent_name)

    # Check if agent is running
    is_running = False
    if self._agent_checker:
        exists, is_running = self._agent_checker(agent_name)

    # Try MCP delivery if agent is running
    if is_running and self._mcp_client:
        result.mcp_delivered = await self._deliver_via_mcp(agent_name, notification)

    # Always try memory persistence
    if self._agent_data_path:
        result.memory_written = await self._write_to_memory(agent_name, notification)

    return result
```

### Memory Persistence (NDJSON)

```python
# informed_notifier.py:269-316

async def _write_to_memory(self, agent_name: str, notification) -> bool:
    """Write notification to agent's memory file in NDJSON format."""
    events_dir = self._agent_data_path / agent_name / ".trinity" / "events"

    # Date-based file naming
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    events_file = events_dir / f"notifications_{today}.ndjson"

    # Append to NDJSON file
    with open(events_file, "a") as f:
        f.write(json.dumps(notification.to_dict()) + "\n")

    return True
```

---

## ExecutionEngine Integration

### Notification on Step Completion

```python
# execution_engine.py:596-606

# In _handle_step_success()
# Notify informed agents (EMI pattern) - run async, don't block
if self.informed_notifier and step_def.roles and step_def.roles.informed:
    asyncio.create_task(self._notify_informed_agents(
        step_def,
        step_completed_event,
        execution,
    ))
```

### Notification on Step Failure

```python
# execution_engine.py:692-699

# In _handle_step_failure()
# Notify informed agents (EMI pattern) - run async, don't block
if self.informed_notifier and step_def.roles and step_def.roles.informed:
    asyncio.create_task(self._notify_informed_agents_failure(
        step_def,
        step_failed_event,
        execution,
    ))
```

---

## Frontend: RoleMatrix.vue

### Component Structure

```vue
<template>
  <div class="overflow-x-auto">
    <table class="min-w-full">
      <thead>
        <tr>
          <th>Step</th>
          <th>Executor</th>
          <th>Monitors</th>
          <th>Informed</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="step in steps" :key="step.id">
          <td>{{ step.name }}</td>
          <td>
            <select v-model="step.roles.executor" @change="emitUpdate">
              <option v-for="agent in agents" :value="agent.name">
                {{ agent.name }}
              </option>
            </select>
          </td>
          <td>
            <MultiSelect
              v-model="step.roles.monitors"
              :options="agents"
              @change="emitUpdate"
            />
          </td>
          <td>
            <MultiSelect
              v-model="step.roles.informed"
              :options="agents"
              @change="emitUpdate"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
const props = defineProps({
  steps: Array,      // Step definitions
  agents: Array,     // Available agents
})

const emit = defineEmits(['update'])

function emitUpdate() {
  emit('update', props.steps)
}
</script>
```

### ProcessEditor Integration

```javascript
// ProcessEditor.vue

function handleRolesUpdate(updatedSteps) {
  // Update roles in YAML
  const yamlObj = yaml.load(yamlContent.value)
  yamlObj.steps = updatedSteps
  yamlContent.value = yaml.dump(yamlObj)
}
```

---

## Notification File Format

Notifications are stored in NDJSON (newline-delimited JSON):

**Path**: `{agent_data_path}/{agent_name}/.trinity/events/notifications_YYYY-MM-DD.ndjson`

**Format**:

```json
{"event_type":"step_completed","process_name":"content-pipeline","execution_id":"uuid","step_id":"research","step_name":"Research Topic","output_summary":"{...}","timestamp":"2026-01-16T10:30:00Z","metadata":{"cost":"$0.10","duration_seconds":45}}
{"event_type":"step_failed","process_name":"content-pipeline","execution_id":"uuid","step_id":"write","step_name":"Write Draft","output_summary":"Agent timeout","timestamp":"2026-01-16T10:31:00Z","metadata":{"error_code":"TIMEOUT","retry_count":3}}
```

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- Multiple agents created
- Published process with roles defined

### Test Cases

1. **Role validation**
   - Action: Create step with roles but no executor
   - Expected: Validation error

2. **Redundancy warning**
   - Action: Add same agent as executor and monitor
   - Expected: Validation warning

3. **Informed notification delivery**
   - Action: Run process, watch informed agent events directory
   - Expected: NDJSON file created with notification

4. **RoleMatrix UI**
   - Action: Select agents in role matrix
   - Expected: YAML updates with roles block

5. **MCP delivery (if running)**
   - Action: Run process with running informed agent
   - Expected: Agent receives MCP message

---

## Related Flows

- [process-definition.md](./process-definition.md) - Role schema in YAML
- [process-execution.md](./process-execution.md) - Notification triggering

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-16 | Initial creation |
