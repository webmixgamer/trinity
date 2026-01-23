# Feature: Process Execution

> Core execution engine that orchestrates process steps with parallel execution, retry logic, and event publishing

---

## Overview

The Execution Engine is the core orchestrator for process execution. It manages the execution lifecycle, resolves step dependencies, dispatches steps to appropriate handlers, and emits domain events.

**Key Capabilities:**
- Parallel execution of independent steps
- Retry logic with exponential backoff
- Step-type-specific handlers (agent_task, gateway, approval, timer, notification, sub_process)
- Event publishing for real-time monitoring
- Cost tracking and aggregation
- Compensation handling on failure

---

## Entry Points

- **UI**: `ProcessList.vue` -> "Start" button -> `POST /api/processes/{id}/execute`
- **UI**: `ProcessExecutionDetail.vue` -> "Retry" button -> `POST /api/executions/{id}/retry`
- **API**: `POST /api/processes/{id}/execute` - Start new execution
- **API**: `POST /api/executions/{id}/cancel` - Cancel running execution
- **API**: `POST /api/executions/{id}/retry` - Retry failed execution
- **Scheduled**: Process schedule triggers

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  ProcessList.vue / ProcessExecutionDetail.vue                           │    │
│  │  ├── Start button -> POST /api/processes/{id}/execute                    │    │
│  │  ├── Cancel button -> POST /api/executions/{id}/cancel                   │    │
│  │  └── Retry button -> POST /api/executions/{id}/retry                     │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Backend                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  routers/executions.py                                                   │    │
│  │  ├── start_execution()      - Create execution, call engine.start()      │    │
│  │  ├── cancel_execution()     - Call engine.cancel()                       │    │
│  │  └── retry_execution()      - Create new execution from failed           │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  engine/execution_engine.py - ExecutionEngine                            │    │
│  │  ├── start()                - Create and run new execution               │    │
│  │  ├── resume()               - Resume paused execution                    │    │
│  │  ├── cancel()               - Cancel running execution                   │    │
│  │  ├── _run()                 - Main execution loop                        │    │
│  │  ├── _execute_step()        - Execute single step with retry             │    │
│  │  └── _execute_steps_parallel() - Execute multiple steps concurrently     │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  engine/dependency_resolver.py - DependencyResolver                      │    │
│  │  ├── get_ready_steps()      - Steps ready to execute (deps satisfied)    │    │
│  │  ├── is_complete()          - All steps done?                            │    │
│  │  ├── has_failed_steps()     - Any failures?                              │    │
│  │  └── get_parallel_structure() - Identify parallel groups                 │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  engine/handlers/                                                        │    │
│  │  ├── agent_task.py          - AgentTaskHandler + AgentGateway            │    │
│  │  ├── human_approval.py      - HumanApprovalHandler + ApprovalGateway     │    │
│  │  ├── gateway.py             - GatewayHandler + GatewayRouter             │    │
│  │  ├── timer.py               - TimerHandler                               │    │
│  │  ├── notification.py        - NotificationHandler                        │    │
│  │  └── sub_process.py         - SubProcessHandler                          │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  events/bus.py - EventBus                                                │    │
│  │  ├── publish(event)         - Broadcast to subscribers                   │    │
│  │  └── Publishers:                                                         │    │
│  │      ├── websocket_publisher.py - Real-time UI updates                   │    │
│  │      └── webhook_publisher.py   - External notifications                 │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Execution State Machine

```
                                    ┌──────────────────────────────────────────┐
                                    │                                          │
                                    │              PENDING                     │
                                    │         (Initial State)                  │
                                    │                                          │
                                    └────────────────┬─────────────────────────┘
                                                     │
                                                     │ start()
                                                     ▼
                                    ┌──────────────────────────────────────────┐
                                    │                                          │
           ┌────────────────────────│             RUNNING                      │────────────────────────┐
           │                        │                                          │                        │
           │                        └────────────────┬─────────────────────────┘                        │
           │                                         │                                                  │
           │ pause()                                 │                                                  │ cancel()
           │ (waiting approval)                      │                                                  │
           ▼                                         │                                                  ▼
┌──────────────────────┐                             │                            ┌──────────────────────┐
│                      │                             │                            │                      │
│       PAUSED         │                             │                            │     CANCELLED        │
│ (Awaiting Approval)  │                             │                            │                      │
│                      │                             │                            └──────────────────────┘
└──────────┬───────────┘                             │
           │                                         │
           │ resume()                                │
           │ (approval received)                     │
           └─────────────────────────────────────────┤
                                                     │
                                                     │ complete() / fail()
                                                     ▼
                              ┌────────────────────────────────────────────────┐
                              │                    │                           │
                              │                    │                           │
                              ▼                    ▼                           │
                    ┌──────────────────┐  ┌──────────────────┐                │
                    │                  │  │                  │                │
                    │    COMPLETED     │  │     FAILED       │                │
                    │                  │  │                  │                │
                    └──────────────────┘  └──────────────────┘                │
                                                                               │
```

### Step Status Values

| Status | Description |
|--------|-------------|
| `PENDING` | Not started, waiting for dependencies |
| `RUNNING` | Currently executing |
| `COMPLETED` | Finished successfully with output |
| `FAILED` | Failed after all retries exhausted |
| `SKIPPED` | Skipped due to condition or error policy |
| `WAITING_APPROVAL` | Human approval step awaiting decision |

---

## Flow Details

### 1. Start Execution Flow

**User Action:** Click "Start" button on process card

```
ProcessList.vue                   Backend                             Engine
---------------                   -------                             ------
User clicks "Start"
POST /api/processes/{id}/execute
                              →   start_execution()
                                  ├── Load definition
                                  ├── Create input_data from request
                                  └── engine.start(definition, input_data)
                                                                    → start()
                                                                      ├── ProcessExecution.create()
                                                                      ├── Initialize step_executions (all PENDING)
                                                                      ├── repo.save(execution)
                                                                      ├── publish(ProcessStarted)
                                                                      └── _run()
                                                                            ↓
                                                                        [Execution Loop]
```

### 2. Main Execution Loop (_run)

```python
# execution_engine.py:260-350 (_run method)

while True:
    # Check cancelled/paused
    if execution.status in (CANCELLED, PAUSED):
        break

    # Check for failures (if stop_on_failure enabled)
    if resolver.has_failed_steps(execution) and config.stop_on_failure:
        await _fail_execution(execution, "Step execution failed")
        break

    # Get ready steps
    ready_step_ids = resolver.get_ready_steps(execution)

    if not ready_step_ids:
        if resolver.is_complete(execution):
            # All done
            await _complete_execution(execution)
            break
        elif resolver.has_failed_steps(execution):
            await _fail_execution(execution, "Step execution failed")
            break
        else:
            # Check for running steps (parallel)
            running_steps = resolver.get_running_steps(execution)
            if running_steps:
                await asyncio.sleep(0.1)
                continue
            # Deadlock - shouldn't happen
            await _fail_execution(execution, "Execution deadlock")
            break

    # Execute steps
    if config.parallel_execution and len(ready_step_ids) > 1:
        await _execute_steps_parallel(execution, step_defs)
    else:
        for step_def in step_defs:
            await _execute_step(execution, step_def)
```

### 3. Single Step Execution with Retry

```python
# execution_engine.py:386-543 (_execute_step method)

async def _execute_step(execution, step_def):
    # Get handler for step type
    handler = registry.get_for_step(step_def)

    # Evaluate step condition (skip if false)
    if step_def.condition:
        if not evaluator.evaluate(step_def.condition, context):
            execution.step_executions[step_id].skip("Condition not met")
            publish(StepSkipped)
            return

    # Start step
    execution.start_step(step_id)
    publish(StepStarted)

    # Retry loop
    retry_policy = step_def.retry_policy
    max_attempts = retry_policy.max_attempts
    attempt = 0

    while attempt < max_attempts:
        attempt += 1

        # Build context
        context = StepContext(execution, step_def, step_outputs, input_data)

        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                handler.execute(context, step_def.config),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            result = StepResult.fail("Step timed out", error_code="TIMEOUT")

        # Handle result
        if result.success:
            await _handle_step_success(execution, step_def, result)
            return

        if result.waiting:
            await _handle_step_waiting(execution, step_def, result)
            return

        # Failed - retry?
        if attempt < max_attempts:
            delay = retry_policy.initial_delay.seconds * (backoff ** (attempt - 1))
            publish(StepRetrying)
            await asyncio.sleep(delay)
        else:
            await _handle_step_failure(execution, step_def, result)
```

### 4. Parallel Execution

```python
# execution_engine.py:352-384 (_execute_steps_parallel)

async def _execute_steps_parallel(execution, step_defs):
    # Apply concurrency limit if configured
    if config.max_concurrent_steps > 0:
        semaphore = asyncio.Semaphore(config.max_concurrent_steps)

        async def limited_execute(step_def):
            async with semaphore:
                await _execute_step(execution, step_def)

        tasks = [limited_execute(sd) for sd in step_defs]
    else:
        tasks = [_execute_step(execution, sd) for sd in step_defs]

    # Run all concurrently
    await asyncio.gather(*tasks, return_exceptions=True)
```

---

## Step Handlers

### Handler Interface

```python
# step_handler.py

class StepHandler(ABC):
    @property
    @abstractmethod
    def step_type(self) -> StepType:
        """Return the step type this handler supports."""

    @abstractmethod
    async def execute(self, context: StepContext, config: StepConfig) -> StepResult:
        """Execute the step and return result."""


@dataclass
class StepResult:
    success: bool
    output: Optional[dict] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    waiting: bool = False  # True if waiting for external input

    @classmethod
    def ok(cls, output: dict) -> "StepResult":
        return cls(success=True, output=output)

    @classmethod
    def fail(cls, error: str, error_code: str = None) -> "StepResult":
        return cls(success=False, error=error, error_code=error_code)

    @classmethod
    def wait(cls, output: dict = None) -> "StepResult":
        return cls(success=False, waiting=True, output=output)
```

### Handler Registry

```python
# step_handler.py

class StepHandlerRegistry:
    """Registry of step type handlers."""

    def __init__(self):
        self._handlers: dict[StepType, StepHandler] = {}

    def register(self, handler: StepHandler) -> None:
        self._handlers[handler.step_type] = handler

    def get(self, step_type: StepType) -> Optional[StepHandler]:
        return self._handlers.get(step_type)

    def get_for_step(self, step_def: StepDefinition) -> Optional[StepHandler]:
        return self._handlers.get(step_def.type)


def get_default_registry() -> StepHandlerRegistry:
    """Create registry with all default handlers."""
    registry = StepHandlerRegistry()
    registry.register(AgentTaskHandler())
    registry.register(HumanApprovalHandler())
    registry.register(GatewayHandler())
    registry.register(TimerHandler())
    registry.register(NotificationHandler())
    registry.register(SubProcessHandler())
    return registry
```

### Template Variable Substitution

Handlers use `ExpressionEvaluator` to substitute template variables in step configuration fields. This enables dynamic content based on process inputs and previous step outputs.

**Supported Variables:**

| Pattern | Description | Example |
|---------|-------------|---------|
| `{{input.X}}` | Process input data | `{{input.company_name}}` |
| `{{steps.X.output}}` | Full step output | `{{steps.research.output}}` |
| `{{steps.X.output.Y}}` | Nested field in step output | `{{steps.research.output.summary}}` |
| `{{execution.id}}` | Execution ID | `exec_abc123...` |
| `{{process.name}}` | Process name | `due-diligence-workflow` |

**Handler Template Support:**

| Handler | Fields with Template Support |
|---------|------------------------------|
| `AgentTaskHandler` | `message`, `agent` |
| `HumanApprovalHandler` | `title`, `description` |
| `NotificationHandler` | `message` |
| `GatewayHandler` | Condition expressions |
| `SubProcessHandler` | `input_mapping` values |

Example usage in YAML:
```yaml
- id: review
  type: human_approval
  title: Review {{input.company_name}} - {{input.deal_type}}
  description: |
    Intake result: {{steps.intake.output.response}}
    Risk score: {{steps.intake.output.score}}
```

See [human-approval.md](./human-approval.md) for detailed template variable documentation.

### AgentTaskHandler

```python
# handlers/agent_task.py:137-257

class AgentTaskHandler(StepHandler):
    """Executes agent_task steps via AgentGateway."""

    async def execute(self, context: StepContext, config: StepConfig) -> StepResult:
        # Substitute variables in message
        message = self._substitute_variables(config.message, context)
        agent_name = self._substitute_variables(config.agent, context)

        # Check agent availability
        if not await self.gateway.check_agent_available(agent_name):
            return StepResult.fail(f"Agent '{agent_name}' not available", "AGENT_UNAVAILABLE")

        # Send message to agent
        result = await self.gateway.send_message(
            agent_name=agent_name,
            message=message,
            timeout=config.timeout.seconds,
        )

        # Build output with response and cost
        output = {
            "response": result["response"],
            "agent": agent_name,
        }
        if result.get("cost"):
            output["cost"] = str(result["cost"])
        if result.get("token_usage"):
            output["token_usage"] = result["token_usage"].to_dict()

        return StepResult.ok(output)
```

---

## Domain Events

Events published during execution:

| Event | When | Data |
|-------|------|------|
| `ProcessStarted` | Execution begins | execution_id, process_id, triggered_by |
| `ProcessCompleted` | All steps done | output_data, total_cost, duration |
| `ProcessFailed` | Step failure or error | error_message, failed_step_id |
| `ProcessCancelled` | User cancellation | reason, cancelled_by |
| `StepStarted` | Step execution begins | step_id, step_name, step_type |
| `StepCompleted` | Step succeeds | output, cost, duration |
| `StepFailed` | Step fails (final) | error_message, retry_count |
| `StepRetrying` | Step failed, will retry | attempt, max_attempts, next_retry_at |
| `StepSkipped` | Step skipped | reason |
| `StepWaitingApproval` | Awaiting human input | approval_id, assignees |
| `CompensationStarted` | Rollback begins | compensation_count |
| `CompensationCompleted` | Rollback succeeds | step_name, type |
| `CompensationFailed` | Rollback fails | step_name, error_message |

---

## DependencyResolver

The DependencyResolver determines which steps can execute based on dependency satisfaction.

```python
# dependency_resolver.py:59-315

class DependencyResolver:
    def get_ready_steps(self, execution: ProcessExecution) -> list[StepId]:
        """Get steps ready to execute (all deps satisfied)."""
        ready = []
        satisfied = set(execution.get_completed_step_ids())
        satisfied.update(execution.get_skipped_step_ids())

        for step in self.definition.steps:
            if step_exec.status != StepStatus.PENDING:
                continue

            deps_satisfied = all(str(dep) in satisfied for dep in step.dependencies)
            if deps_satisfied:
                ready.append(step.id)

        return ready

    def get_parallel_structure(self) -> ParallelStructure:
        """Analyze process for parallel execution groups."""
        # Calculate level for each step (longest path from entry)
        # Steps at same level can run in parallel
        ...
```

### Parallel Groups Example

```yaml
steps:
  - id: start          # Level 0
    type: agent_task

  - id: task-a         # Level 1 (parallel with task-b)
    depends_on: [start]

  - id: task-b         # Level 1 (parallel with task-a)
    depends_on: [start]

  - id: merge          # Level 2
    depends_on: [task-a, task-b]
```

Results in:
- Level 0: [start]
- Level 1: [task-a, task-b] <- Parallel execution
- Level 2: [merge]

---

## Error Handling and Retry

### Retry Policy

```yaml
# In step definition
retry:
  max_attempts: 3       # Total attempts (default: 1)
  initial_delay: 10s    # Delay before first retry
  backoff_multiplier: 2 # Exponential backoff
```

### Error Policy

```yaml
on_error:
  action: fail_process  # fail_process | skip_step | goto_step
  target_step: cleanup  # Required if action is goto_step
```

### Non-Retryable Errors

Some errors bypass retry:

| Error Code | Description |
|------------|-------------|
| `APPROVAL_REJECTED` | Human rejected approval |
| `VALIDATION_ERROR` | Invalid configuration |
| `INVALID_CONFIG` | Handler config error |

---

## Compensation (Rollback)

When a process fails after some steps have completed, compensation handlers run in reverse order.

```yaml
steps:
  - id: create-record
    type: agent_task
    agent: db-agent
    message: Create record
    compensation:
      type: agent_task
      agent: db-agent
      message: Delete record {{steps.create-record.output.id}}

  - id: send-email
    type: notification
    # ... if this fails, create-record compensation runs
```

```python
# execution_engine.py:823-982 (_run_compensations)

async def _run_compensations(execution, definition):
    # Get completed steps in reverse order
    completed_steps = sorted(
        [(id, exec.completed_at) for id, exec in step_executions.items()
         if exec.status == COMPLETED],
        key=lambda x: x[1],
        reverse=True  # Most recent first
    )

    for step_id, _ in completed_steps:
        step_def = definition.get_step(step_id)
        if step_def and step_def.compensation:
            await _execute_compensation(execution, step_def)
```

---

## API Endpoints

| Method | Path | Description | File:Line |
|--------|------|-------------|-----------|
| POST | `/api/processes/{id}/execute` | Start execution | executions.py:45-90 |
| GET | `/api/executions` | List all executions | executions.py:93-120 |
| GET | `/api/executions/{id}` | Get execution detail | executions.py:123-145 |
| POST | `/api/executions/{id}/cancel` | Cancel execution | executions.py:148-180 |
| POST | `/api/executions/{id}/retry` | Retry failed execution | executions.py:183-220 |
| POST | `/api/executions/{id}/resume` | Resume paused execution | executions.py:223-260 |

---

## Database Schema

```sql
-- repositories/sqlite_executions.py

CREATE TABLE process_executions (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL,
    process_name TEXT NOT NULL,
    process_version TEXT NOT NULL,
    status TEXT NOT NULL,
    input_data TEXT,             -- JSON
    output_data TEXT,            -- JSON
    step_executions TEXT,        -- JSON map: step_id -> StepExecution
    triggered_by TEXT,
    started_at TEXT,
    completed_at TEXT,
    total_cost TEXT,
    retry_of TEXT,               -- Original execution if retry
    parent_execution_id TEXT,    -- For sub-processes
    parent_step_id TEXT,
    child_execution_ids TEXT     -- JSON array
);

CREATE INDEX idx_executions_process ON process_executions(process_id);
CREATE INDEX idx_executions_status ON process_executions(status);
CREATE INDEX idx_executions_started ON process_executions(started_at);
```

---

## Configuration

```python
# execution_engine.py:66-89

@dataclass
class ExecutionConfig:
    # Default timeout for steps without explicit timeout
    default_step_timeout: Duration = Duration.from_minutes(5)

    # Stop on first failure or continue with independent steps
    stop_on_failure: bool = True

    # Maximum retries for failed steps (0 = no retries)
    max_retries: int = 0

    # Enable parallel execution of independent steps
    parallel_execution: bool = True

    # Maximum concurrent steps (0 = unlimited)
    max_concurrent_steps: int = 0
```

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- At least one published process definition
- Required agents created and running

### Test Cases

1. **Sequential execution**
   - Action: Start process with linear dependencies (A -> B -> C)
   - Expected: Steps execute in order, events emitted

2. **Parallel execution**
   - Action: Start process with parallel steps (A -> [B, C] -> D)
   - Expected: B and C run concurrently, D waits for both

3. **Retry on failure**
   - Action: Step fails with transient error, retry configured
   - Expected: StepRetrying event, then success or final failure

4. **Cancel execution**
   - Action: Cancel running execution
   - Expected: Status changes to CANCELLED, running steps stop

5. **Compensation on failure**
   - Action: Step with compensation fails after another completes
   - Expected: Compensation runs in reverse order

---

## Related Flows

- [process-definition.md](./process-definition.md) - How definitions are created
- [process-monitoring.md](./process-monitoring.md) - UI for watching executions
- [human-approval.md](./human-approval.md) - Approval step handler details
- [sub-processes.md](./sub-processes.md) - SubProcessHandler details

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-23 | Added Template Variable Substitution section with handler support table |
| 2026-01-16 | Initial creation |
