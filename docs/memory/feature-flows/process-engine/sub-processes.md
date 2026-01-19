# Feature: Sub-Processes

> Calling other processes as steps within a parent workflow, with parent-child linking and breadcrumb navigation

---

## Overview

Sub-Processes enable composable, reusable workflows by allowing one process to call another as a step. The parent process waits for the child to complete and receives its output.

**Key Capabilities:**
- Call any published process as a step
- Map input data from parent to child
- Capture child output in parent context
- Parent-child execution linking
- Breadcrumb navigation in UI
- Cost aggregation

---

## Entry Points

- **YAML**: `type: sub_process` step in process definition
- **UI**: `ProcessExecutionDetail.vue` shows child executions
- **UI**: Breadcrumb navigation for nested executions
- **API**: `/api/executions/{id}` includes parent/child links

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Parent Process                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  steps:                                                                  │    │
│  │    - id: research                                                        │    │
│  │      type: agent_task                                                    │    │
│  │      ...                                                                 │    │
│  │                                                                          │    │
│  │    - id: call-analysis                                                   │    │
│  │      type: sub_process           ───────────────────────────────┐       │    │
│  │      process_name: analysis-flow                                 │       │    │
│  │      input_mapping:                                              │       │    │
│  │        data: "{{steps.research.output}}"                        │       │    │
│  │      output_key: analysis_result                                │       │    │
│  │                                                                  │       │    │
│  │    - id: summarize                                              │       │    │
│  │      type: agent_task                                           │       │    │
│  │      depends_on: [call-analysis]                                │       │    │
│  │      message: "Summarize: {{steps.call-analysis.analysis_result}}"      │    │
│  └──────────────────────────────────────────────────────────────────┼──────┘    │
└─────────────────────────────────────────────────────────────────────┼───────────┘
                                                                      │
                                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Child Process: analysis-flow                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  input: {data: ...}                                                      │    │
│  │                                                                          │    │
│  │  steps:                                                                  │    │
│  │    - id: analyze                                                         │    │
│  │      type: agent_task                                                    │    │
│  │      ...                                                                 │    │
│  │                                                                          │    │
│  │  output: {result: ...}                                                   │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ProcessExecution                                                                │
│    parent_execution_id: <parent-uuid>                                           │
│    parent_step_id: call-analysis                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## YAML Configuration

### Basic Sub-Process Step

```yaml
- id: run-analysis
  type: sub_process
  process_name: analysis-flow    # Required: name of published process
  depends_on: [research]
```

### With Input Mapping

```yaml
- id: run-analysis
  type: sub_process
  process_name: analysis-flow
  version: 2                      # Optional: specific version
  input_mapping:                  # Optional: map parent data to child input
    topic: "{{input.topic}}"
    research_data: "{{steps.research.output}}"
  output_key: analysis            # Optional: key for child output (default: result)
  wait_for_completion: true       # Optional: default true
  timeout: 1h                     # Optional: default 1h
  depends_on: [research]
```

### Full Example: Parent Process

```yaml
name: content-pipeline
version: 1
description: Research, analyze, and write content

steps:
  - id: research
    type: agent_task
    agent: research-agent
    message: Research the topic: {{input.topic}}

  - id: analyze
    type: sub_process
    process_name: analysis-process
    input_mapping:
      data: "{{steps.research.output}}"
    output_key: analysis
    depends_on: [research]

  - id: write
    type: agent_task
    agent: writer-agent
    message: |
      Write based on analysis:
      {{steps.analyze.analysis}}
    depends_on: [analyze]

outputs:
  - name: article
    source: "{{steps.write.output}}"
```

---

## SubProcessHandler

### Handler Implementation

```python
# handlers/sub_process.py:39-198

class SubProcessHandler(StepHandler):
    """Handler for sub_process step type."""

    def __init__(
        self,
        definition_repo: ProcessDefinitionRepository,
        engine_factory: Callable[[], ExecutionEngine],
        expression_evaluator: ExpressionEvaluator,
    ):
        self._definition_repo = definition_repo
        self._engine_factory = engine_factory
        self.expression_evaluator = expression_evaluator

    async def execute(self, context: StepContext, config: StepConfig) -> StepResult:
        # 1. Load child process definition
        child_definition = self._load_child_definition(
            config.process_name,
            config.version
        )
        if not child_definition:
            return StepResult.fail("Sub-process not found", "PROCESS_NOT_FOUND")

        # 2. Map input data from parent to child
        child_input = self._map_input_data(config.input_mapping, context)

        # 3. Execute child process
        engine = self._engine_factory()
        child_execution = await engine.start(
            definition=child_definition,
            input_data=child_input,
            triggered_by="sub_process",
            parent_execution_id=context.execution.id,
            parent_step_id=context.step_definition.id,
        )

        # 4. Return result based on child status
        if child_execution.status.value == "completed":
            return StepResult.ok({
                config.output_key: child_execution.output_data,
                "child_execution_id": str(child_execution.id),
                "child_cost": str(child_execution.total_cost),
            })
        elif child_execution.status.value == "failed":
            return StepResult.fail(f"Sub-process failed: {error}")
        elif child_execution.status.value == "paused":
            return StepResult.wait({"child_execution_id": str(child_execution.id)})
```

### Input Mapping

```python
# handlers/sub_process.py:236-283

def _map_input_data(self, input_mapping: dict, context: StepContext) -> dict:
    """Map parent context data to child input."""
    if not input_mapping:
        # If no mapping, pass parent input as-is
        return context.input_data.copy()

    child_input = {}
    eval_context = EvaluationContext(
        input_data=context.input_data,
        step_outputs=context.step_outputs,
        execution_id=str(context.execution.id),
        process_name=context.execution.process_name,
    )

    for child_key, expression in input_mapping.items():
        if isinstance(expression, str) and "{{" in expression:
            value = self.expression_evaluator.evaluate(expression, eval_context)
            child_input[child_key] = value
        else:
            child_input[child_key] = expression

    return child_input
```

---

## Parent-Child Linking

### ProcessExecution Fields

```python
# aggregates.py:364-393

@dataclass
class ProcessExecution:
    # ... other fields ...

    # Sub-process tracking
    parent_execution_id: Optional[ExecutionId] = None
    parent_step_id: Optional[StepId] = None
    child_execution_ids: list[ExecutionId] = field(default_factory=list)

    def add_child_execution(self, child_id: ExecutionId) -> None:
        """Add a child execution ID to track sub-process calls."""
        if child_id not in self.child_execution_ids:
            self.child_execution_ids.append(child_id)

    def is_sub_process(self) -> bool:
        """Check if this execution is a sub-process (has a parent)."""
        return self.parent_execution_id is not None

    def has_children(self) -> bool:
        """Check if this execution has spawned child processes."""
        return len(self.child_execution_ids) > 0
```

### Linking During Execution

```python
# execution_engine.py:167-188 (start method)

async def start(
    self,
    definition: ProcessDefinition,
    input_data: Optional[dict] = None,
    triggered_by: str = "manual",
    parent_execution_id: Optional[ExecutionId] = None,
    parent_step_id: Optional[StepId] = None,
) -> ProcessExecution:
    execution = ProcessExecution.create(
        definition=definition,
        input_data=input_data,
        triggered_by=triggered_by,
        parent_execution_id=parent_execution_id,
        parent_step_id=parent_step_id,
    )

    # If this is a sub-process, update parent to track child
    if parent_execution_id:
        parent_execution = self.execution_repo.get_by_id(parent_execution_id)
        if parent_execution:
            parent_execution.add_child_execution(execution.id)
            self.execution_repo.save(parent_execution)
```

---

## Breadcrumb Navigation

### Building Breadcrumbs

```javascript
// ProcessExecutionDetail.vue

const breadcrumbs = ref([])

async function buildBreadcrumbs(execution) {
  const crumbs = []

  // Start with current execution
  let current = execution
  crumbs.unshift({
    id: current.id,
    process_name: current.process_name
  })

  // Walk up the parent chain
  while (current.parent_execution_id) {
    try {
      const parent = await api.get(`/api/executions/${current.parent_execution_id}`)
      crumbs.unshift({
        id: parent.id,
        process_name: parent.process_name
      })
      current = parent
    } catch (e) {
      break
    }
  }

  breadcrumbs.value = crumbs
}
```

### UI Display

```vue
<!-- ProcessExecutionDetail.vue:8-24 -->

<nav v-if="breadcrumbs.length > 1" class="flex items-center space-x-2 text-sm mb-4">
  <HomeIcon class="w-4 h-4 text-gray-400" />
  <template v-for="(crumb, index) in breadcrumbs" :key="crumb.id">
    <ChevronRightIcon class="w-4 h-4 text-gray-400" />
    <router-link
      v-if="index < breadcrumbs.length - 1"
      :to="`/executions/${crumb.id}`"
      class="text-indigo-600 hover:text-indigo-800"
    >
      {{ crumb.process_name }}
    </router-link>
    <span v-else class="text-gray-700 font-medium">
      {{ crumb.process_name }}
    </span>
  </template>
</nav>
```

### Visual Example

```
Home > content-pipeline > analysis-process > current-step
       ↑ clickable        ↑ clickable       ↑ current (bold)
```

---

## Child Execution Indicators

### Badges in Execution Detail

```vue
<!-- Parent indicator -->
<p v-if="execution.parent_execution_id" class="mt-1">
  <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700">
    <ArrowUpIcon class="w-3 h-3" />
    Called by:
    <router-link :to="`/executions/${execution.parent_execution_id}`">
      {{ execution.parent_execution_id.substring(0, 8) }}...
    </router-link>
    <span v-if="execution.parent_step_id">(step: {{ execution.parent_step_id }})</span>
  </span>
</p>

<!-- Children indicator -->
<p v-if="execution.child_execution_ids?.length > 0" class="mt-1">
  <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-teal-100 text-teal-700">
    <ArrowDownIcon class="w-3 h-3" />
    {{ execution.child_execution_ids.length }} child execution(s)
  </span>
</p>
```

---

## Validation

### Recursive Detection

The validator detects direct self-recursion:

```python
# validator.py:727-750 (_check_recursive_sub_processes)

def _check_recursive_sub_processes(self, definition: ProcessDefinition, result: ValidationResult):
    for step in definition.steps:
        if step.type == StepType.SUB_PROCESS:
            if isinstance(step.config, SubProcessConfig):
                process_name = step.config.process_name
                # Check for direct self-recursion
                if process_name == definition.name:
                    result.add_error(
                        message=f"Sub-process step references itself (recursive call to '{process_name}')",
                        path=f"steps[{i}].process_name",
                    )
```

### Sub-Process Existence Check

```python
# validator.py:697-725 (_check_sub_processes)

def _check_sub_processes(self, definition: ProcessDefinition, result: ValidationResult):
    if not self.process_checker:
        return

    for step in definition.steps:
        if step.type == StepType.SUB_PROCESS:
            process_name = step.config.process_name
            version = step.config.version
            exists = self.process_checker(process_name, version)
            if not exists:
                result.add_warning(
                    message=f"Sub-process '{process_name}' not found or not published",
                    path=f"steps[{i}].process_name",
                )
```

---

## API Response

Execution detail includes parent/child links:

```json
{
  "id": "child-execution-uuid",
  "process_id": "analysis-process-uuid",
  "process_name": "analysis-process",
  "status": "completed",
  "triggered_by": "sub_process",
  "parent_execution_id": "parent-execution-uuid",
  "parent_step_id": "call-analysis",
  "child_execution_ids": [],
  "input_data": {"data": "..."},
  "output_data": {"result": "..."},
  "total_cost": "$0.15"
}
```

---

## Cost Aggregation

Child costs are included in step output and can be aggregated by the parent:

```python
# SubProcessHandler returns cost info
output = {
    config.output_key: child_execution.output_data,
    "child_execution_id": str(child_execution.id),
    "child_cost": str(child_execution.total_cost),
}
```

---

## Error Handling

| Error | Code | Cause |
|-------|------|-------|
| Process not found | `PROCESS_NOT_FOUND` | Child process doesn't exist or isn't published |
| Configuration error | `CONFIGURATION_ERROR` | Handler not properly configured |
| Sub-process failed | `SUB_PROCESS_FAILED` | Child execution failed |
| Unexpected state | `UNEXPECTED_STATE` | Child ended in unexpected status |
| Recursive call | (validation error) | Process calls itself |

---

## Testing

### Prerequisites
- Two published processes (parent and child)
- Child process must be published before parent

### Test Cases

1. **Basic sub-process call**
   - Action: Run parent with sub-process step
   - Expected: Child executes, output returned to parent

2. **Input mapping**
   - Action: Map parent data to child input
   - Expected: Child receives mapped values

3. **Breadcrumb navigation**
   - Action: Navigate to child execution
   - Expected: Breadcrumbs show parent chain

4. **Recursive detection**
   - Action: Try to create process that calls itself
   - Expected: Validation error

5. **Child failure handling**
   - Action: Child process fails
   - Expected: Parent step fails with child error

---

## Related Flows

- [process-definition.md](./process-definition.md) - Sub-process step configuration
- [process-execution.md](./process-execution.md) - How child execution is triggered
- [process-monitoring.md](./process-monitoring.md) - Breadcrumb UI details

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-16 | Initial creation |
