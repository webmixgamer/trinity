"""
Process Execution Engine

The core orchestrator for process execution. Manages the execution
lifecycle, coordinates step handlers, and emits domain events.

Reference: BACKLOG_MVP.md - E2-03
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from ..domain import (
    ProcessDefinition,
    ProcessExecution,
    StepDefinition,
    StepId,
    ExecutionStatus,
    StepStatus,
    StepType,
    OnErrorAction,
    Money,
    Duration,
    # Events
    ProcessStarted,
    ProcessCompleted,
    ProcessFailed,
    ProcessCancelled,
    StepStarted,
    StepCompleted,
    StepFailed,
    StepRetrying,
    StepSkipped,
    StepWaitingApproval,
    # Compensation Events
    CompensationStarted,
    CompensationCompleted,
    CompensationFailed,
)
from ..repositories import ProcessExecutionRepository
from ..services import OutputStorage
from ..events import EventBus

from .dependency_resolver import DependencyResolver
from .step_handler import (
    StepHandler,
    StepHandlerRegistry,
    StepContext,
    StepResult,
    get_default_registry,
)


logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


@dataclass
class ExecutionConfig:
    """
    Configuration for the execution engine.
    """
    # Default timeout for steps without explicit timeout
    default_step_timeout: Duration = None

    # Whether to stop on first failure or continue with independent steps
    stop_on_failure: bool = True

    # Maximum retries for failed steps (0 = no retries)
    max_retries: int = 0

    # Enable parallel execution of independent steps
    parallel_execution: bool = True

    # Maximum concurrent steps (0 = unlimited)
    max_concurrent_steps: int = 0

    def __post_init__(self):
        if self.default_step_timeout is None:
            self.default_step_timeout = Duration.from_minutes(5)


class ExecutionEngine:
    """
    Orchestrates process execution.

    Responsibilities:
    - Manage execution lifecycle (start, pause, resume, cancel)
    - Resolve step dependencies and determine execution order
    - Dispatch steps to appropriate handlers
    - Update execution state and emit events
    - Handle errors and retries

    Example usage:
    ```python
    engine = ExecutionEngine(
        execution_repo=repo,
        event_bus=bus,
        output_storage=storage,
    )

    execution = await engine.start(definition, input_data={"topic": "AI"})
    # or
    execution = await engine.resume(existing_execution)
    ```
    """

    def __init__(
        self,
        execution_repo: ProcessExecutionRepository,
        event_bus: Optional[EventBus] = None,
        output_storage: Optional[OutputStorage] = None,
        handler_registry: Optional[StepHandlerRegistry] = None,
        config: Optional[ExecutionConfig] = None,
    ):
        """
        Initialize the execution engine.

        Args:
            execution_repo: Repository for persisting execution state
            event_bus: Optional event bus for publishing domain events
            output_storage: Optional output storage service
            handler_registry: Optional custom handler registry
            config: Optional execution configuration
        """
        self.execution_repo = execution_repo
        self.event_bus = event_bus
        self.output_storage = output_storage
        self.handler_registry = handler_registry or get_default_registry()
        self.config = config or ExecutionConfig()

    async def start(
        self,
        definition: ProcessDefinition,
        input_data: Optional[dict[str, Any]] = None,
        triggered_by: str = "manual",
    ) -> ProcessExecution:
        """
        Start a new process execution.

        Args:
            definition: The process definition to execute
            input_data: Optional input data for the process
            triggered_by: What triggered this execution (manual, schedule, api)

        Returns:
            The completed (or failed) execution
        """
        # Create execution
        execution = ProcessExecution.create(
            definition=definition,
            input_data=input_data or {},
            triggered_by=triggered_by,
        )

        # Save initial state
        self.execution_repo.save(execution)

        logger.info(f"Starting execution {execution.id} for process '{definition.name}'")

        # Run the execution
        return await self._run(definition, execution)

    async def resume(
        self,
        execution: ProcessExecution,
        definition: ProcessDefinition,
    ) -> ProcessExecution:
        """
        Resume a paused or partially completed execution.

        Args:
            execution: The execution to resume
            definition: The process definition

        Returns:
            The completed (or failed) execution
        """
        if execution.status == ExecutionStatus.COMPLETED:
            logger.warning(f"Execution {execution.id} is already completed")
            return execution

        if execution.status == ExecutionStatus.CANCELLED:
            raise ValueError("Cannot resume cancelled execution")

        if execution.status == ExecutionStatus.PAUSED:
            execution.resume()
            # Reset WAITING_APPROVAL steps to PENDING so they get re-executed
            # The handler will check if approval was given and complete/fail accordingly
            for step_id, step_exec in execution.step_executions.items():
                if step_exec.status == StepStatus.WAITING_APPROVAL:
                    step_exec.status = StepStatus.PENDING
                    logger.info(f"Reset step '{step_id}' from WAITING_APPROVAL to PENDING for re-execution")
            self.execution_repo.save(execution)

        logger.info(f"Resuming execution {execution.id}")

        return await self._run(definition, execution)

    async def cancel(
        self,
        execution: ProcessExecution,
        reason: str = "Cancelled by user",
    ) -> ProcessExecution:
        """
        Cancel a running execution.

        Args:
            execution: The execution to cancel
            reason: Reason for cancellation

        Returns:
            The cancelled execution
        """
        execution.cancel(reason)
        self.execution_repo.save(execution)

        await self._publish_event(ProcessCancelled(
            execution_id=execution.id,
            process_id=execution.process_id,
            process_name=execution.process_name,
            reason=reason,
            cancelled_by="user",
        ))

        logger.info(f"Cancelled execution {execution.id}: {reason}")

        return execution

    async def _run(
        self,
        definition: ProcessDefinition,
        execution: ProcessExecution,
    ) -> ProcessExecution:
        """
        Main execution loop.

        Executes steps in dependency order until complete or failed.
        Supports parallel execution of independent steps.
        """
        resolver = DependencyResolver(definition)

        # Start execution if not already running
        if execution.status == ExecutionStatus.PENDING:
            execution.start()
            self.execution_repo.save(execution)

            await self._publish_event(ProcessStarted(
                execution_id=execution.id,
                process_id=execution.process_id,
                process_name=execution.process_name,
                triggered_by=execution.triggered_by,
            ))

        # Execute steps until done
        while True:
            # Check if cancelled or paused
            if execution.status == ExecutionStatus.CANCELLED:
                break

            if execution.status == ExecutionStatus.PAUSED:
                logger.info(f"Execution {execution.id} paused (waiting for approval)")
                break

            # Check for failures (if stop_on_failure is enabled)
            if resolver.has_failed_steps(execution) and self.config.stop_on_failure:
                await self._fail_execution(execution, "Step execution failed", definition)
                break

            # Get all ready steps
            ready_step_ids = resolver.get_ready_steps(execution)

            if not ready_step_ids:
                # No more steps ready
                if resolver.is_complete(execution):
                    # All done - complete execution
                    await self._complete_execution(execution, definition)
                    break
                elif resolver.has_failed_steps(execution):
                    # Failed steps blocking progress
                    await self._fail_execution(execution, "Step execution failed", definition)
                    break
                else:
                    # Check if steps are still running (parallel execution)
                    running_steps = resolver.get_running_steps(execution)
                    if running_steps:
                        # Wait a bit and continue - steps are still running
                        await asyncio.sleep(0.1)
                        continue
                    # Shouldn't happen - deadlock
                    logger.error("No steps ready but execution not complete")
                    await self._fail_execution(execution, "Execution deadlock", definition)
                    break

            # Get step definitions
            step_defs = []
            for step_id in ready_step_ids:
                step_def = resolver.get_step_definition(step_id)
                if step_def is None:
                    await self._fail_execution(execution, f"Step definition not found: {step_id}", definition)
                    return execution
                step_defs.append(step_def)

            # Execute steps (parallel or sequential)
            if self.config.parallel_execution and len(step_defs) > 1:
                # Parallel execution
                await self._execute_steps_parallel(execution, step_defs, definition)
            else:
                # Sequential execution (one step at a time)
                for step_def in step_defs:
                    await self._execute_step(execution, step_def, definition)
                    # Check if execution was failed/cancelled during step execution
                    if execution.status in (ExecutionStatus.FAILED, ExecutionStatus.CANCELLED):
                        break

            # Check if execution was failed/cancelled during step execution
            if execution.status in (ExecutionStatus.FAILED, ExecutionStatus.CANCELLED):
                break

        return execution

    async def _execute_steps_parallel(
        self,
        execution: ProcessExecution,
        step_defs: list[StepDefinition],
        definition: ProcessDefinition,
    ) -> None:
        """
        Execute multiple steps in parallel.

        Uses asyncio.gather to run steps concurrently.
        Respects max_concurrent_steps configuration.
        """
        step_names = [s.name for s in step_defs]
        logger.info(f"Executing {len(step_defs)} steps in parallel: {step_names}")

        # Apply concurrency limit if configured
        if self.config.max_concurrent_steps > 0:
            semaphore = asyncio.Semaphore(self.config.max_concurrent_steps)

            async def limited_execute(step_def: StepDefinition):
                async with semaphore:
                    await self._execute_step(execution, step_def, definition)

            tasks = [limited_execute(step_def) for step_def in step_defs]
        else:
            tasks = [
                self._execute_step(execution, step_def, definition)
                for step_def in step_defs
            ]

        # Run all steps concurrently
        # Using return_exceptions=True to continue even if some fail
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_step(
        self,
        execution: ProcessExecution,
        step_def: StepDefinition,
        definition: ProcessDefinition,
    ) -> None:
        """
        Execute a single step with retry logic.
        """
        step_id = step_def.id

        # Get handler
        handler = self.handler_registry.get_for_step(step_def)
        if handler is None:
            logger.warning(f"No handler for step type '{step_def.type}', skipping")
            execution.step_executions[str(step_id)].skip(f"No handler for type: {step_def.type}")
            self.execution_repo.save(execution)

            await self._publish_event(StepSkipped(
                execution_id=execution.id,
                step_id=step_id,
                step_name=step_def.name,
                reason=f"No handler for type: {step_def.type}",
            ))
            return

        # Evaluate step condition (for gateway routing)
        if step_def.condition:
            from ..services import ConditionEvaluator, EvaluationContext
            condition_evaluator = ConditionEvaluator()
            eval_context = EvaluationContext(
                input_data=execution.input_data,
                step_outputs=self._build_step_outputs(execution),
                execution_id=str(execution.id),
                process_name=execution.process_name,
            )

            try:
                condition_result = condition_evaluator.evaluate(step_def.condition, eval_context)
                if not condition_result:
                    logger.info(f"Step '{step_def.name}' skipped: condition not met ({step_def.condition})")
                    execution.step_executions[str(step_id)].skip(f"Condition not met: {step_def.condition}")
                    self.execution_repo.save(execution)

                    await self._publish_event(StepSkipped(
                        execution_id=execution.id,
                        step_id=step_id,
                        step_name=step_def.name,
                        reason=f"Condition not met: {step_def.condition}",
                    ))
                    return
            except Exception as e:
                logger.error(f"Error evaluating condition for step '{step_def.name}': {e}")
                # On condition evaluation error, continue with step execution

        # Start step (initial)
        execution.start_step(step_id)
        self.execution_repo.save(execution)

        await self._publish_event(StepStarted(
            execution_id=execution.id,
            step_id=step_id,
            step_name=step_def.name,
            step_type=step_def.type,
        ))

        logger.info(f"Executing step '{step_def.name}' ({step_id})")

        # Retry loop
        retry_policy = step_def.retry_policy
        max_attempts = retry_policy.max_attempts
        attempt = 0

        while attempt < max_attempts:
            attempt += 1

            # Build context
            step_outputs = {}
            if self.output_storage:
                step_outputs = self.output_storage.get_all_outputs(execution.id)

            context = StepContext(
                execution=execution,
                step_definition=step_def,
                step_outputs=step_outputs,
                input_data=execution.input_data,
            )

            # Execute with timeout
            try:
                timeout_seconds = self.config.default_step_timeout.seconds
                if hasattr(step_def.config, 'timeout') and step_def.config.timeout:
                    timeout_seconds = step_def.config.timeout.seconds

                result = await asyncio.wait_for(
                    handler.execute(context, step_def.config),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                result = StepResult.fail(
                    f"Step timed out after {timeout_seconds}s",
                    error_code="TIMEOUT",
                )
            except Exception as e:
                logger.exception(f"Step '{step_def.name}' raised exception (attempt {attempt}/{max_attempts})")
                result = StepResult.fail(str(e), error_code="EXCEPTION")

            # Handle result
            if result.success:
                await self._handle_step_success(execution, step_def, result)
                return

            # Handle waiting state (e.g., human approval)
            if result.waiting:
                await self._handle_step_waiting(execution, step_def, result)
                return

            # If we reached here, it failed. Check if we should retry.
            # Record the attempt failure
            execution.record_step_attempt(step_id, result.error or "Unknown error", result.error_code)
            self.execution_repo.save(execution)

            # Some errors should not be retried (human decisions, validation errors)
            non_retryable_errors = {"APPROVAL_REJECTED", "VALIDATION_ERROR", "INVALID_CONFIG"}
            if result.error_code in non_retryable_errors:
                logger.info(f"Step '{step_def.name}' failed with non-retryable error: {result.error_code}")
                await self._handle_step_failure(execution, step_def, result, definition)
                return

            if attempt < max_attempts:
                # Calculate delay with exponential backoff
                delay_seconds = retry_policy.initial_delay.seconds * (retry_policy.backoff_multiplier ** (attempt - 1))
                next_retry_at = datetime.now(timezone.utc).fromtimestamp(
                    datetime.now(timezone.utc).timestamp() + delay_seconds
                )

                logger.info(f"Step '{step_def.name}' failed, retrying in {delay_seconds}s (attempt {attempt}/{max_attempts})")

                await self._publish_event(StepRetrying(
                    execution_id=execution.id,
                    step_id=step_id,
                    step_name=step_def.name,
                    error_message=result.error or "Unknown error",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    next_retry_at=next_retry_at,
                ))

                # Wait before next attempt
                await asyncio.sleep(delay_seconds)

                # Check if cancelled during sleep
                if execution.status == ExecutionStatus.CANCELLED:
                    return
            else:
                # All attempts failed
                await self._handle_step_failure(execution, step_def, result, definition)
                return

    async def _handle_step_success(
        self,
        execution: ProcessExecution,
        step_def: StepDefinition,
        result: StepResult,
    ) -> None:
        """Handle successful step completion."""
        step_id = step_def.id
        output = result.output or {}

        # Complete the step
        execution.complete_step(step_id, output)
        self.execution_repo.save(execution)

        # Store output
        if self.output_storage and output:
            self.output_storage.store(execution.id, step_id, output)

        # Calculate duration
        step_exec = execution.step_executions[str(step_id)]
        duration = step_exec.duration

        await self._publish_event(StepCompleted(
            execution_id=execution.id,
            step_id=step_id,
            step_name=step_def.name,
            output=output,
            duration=duration,
        ))

        logger.info(f"Step '{step_def.name}' completed successfully")

    async def _handle_step_waiting(
        self,
        execution: ProcessExecution,
        step_def: StepDefinition,
        result: StepResult,
    ) -> None:
        """Handle step waiting for external input (e.g., approval)."""
        step_id = step_def.id
        output = result.output or {}

        # Set step to waiting approval status
        step_exec = execution.step_executions[str(step_id)]
        step_exec.wait_for_approval()

        # Pause the execution
        execution.pause()
        self.execution_repo.save(execution)

        # Emit event
        await self._publish_event(StepWaitingApproval(
            execution_id=execution.id,
            step_id=step_id,
            step_name=step_def.name,
            approval_id=output.get("approval_id", ""),
            title=output.get("title", ""),
            assignees=output.get("assignees", []),
        ))

        logger.info(f"Step '{step_def.name}' waiting for approval")

    async def _handle_step_failure(
        self,
        execution: ProcessExecution,
        step_def: StepDefinition,
        result: StepResult,
        definition: Optional[ProcessDefinition] = None,
    ) -> None:
        """Handle step failure after all retries exhausted."""
        step_id = step_def.id
        error_policy = step_def.error_policy

        # Fail the step in state
        execution.fail_step(step_id, result.error or "Unknown error", result.error_code)

        # Check error policy
        action = error_policy.action

        if action == OnErrorAction.SKIP_STEP:
            logger.info(f"Error policy for '{step_def.name}' is SKIP_STEP, marking as skipped")
            execution.step_executions[str(step_id)].skip(f"Skipped after failure: {result.error}")
            self.execution_repo.save(execution)

            await self._publish_event(StepSkipped(
                execution_id=execution.id,
                step_id=step_id,
                step_name=step_def.name,
                reason=f"Skipped after failure: {result.error}",
            ))
            return

        elif action == OnErrorAction.GOTO_STEP and error_policy.target_step:
            # For MVP, we'll implement GOTO by skipping intermediate steps
            # This is a bit tricky in the current topological resolver
            # For now, let's just log it and fail the process as fallback
            logger.warning(f"GOTO_STEP not fully implemented in MVP, failing process")
            # Fall through to fail process
            pass

        # Default: fail process
        self.execution_repo.save(execution)

        step_exec = execution.step_executions[str(step_id)]

        await self._publish_event(StepFailed(
            execution_id=execution.id,
            step_id=step_id,
            step_name=step_def.name,
            error_message=result.error or "Unknown error",
            error_code=result.error_code,
            retry_count=step_exec.retry_count,
            will_retry=False,
        ))

        logger.error(f"Step '{step_def.name}' failed after all retries: {result.error}")

        if action == OnErrorAction.FAIL_PROCESS:
            await self._fail_execution(execution, f"Step '{step_def.name}' failed: {result.error}", definition)

    def _build_step_outputs(self, execution: ProcessExecution) -> dict[str, Any]:
        """
        Build step outputs dictionary for condition evaluation.

        Returns a dict mapping step_id -> output data.
        """
        if self.output_storage:
            return self.output_storage.get_all_outputs(execution.id)
        return {}

    async def _complete_execution(
        self,
        execution: ProcessExecution,
        definition: ProcessDefinition,
    ) -> None:
        """Complete the execution successfully."""
        # Gather outputs based on definition
        output_data = {}
        if self.output_storage:
            all_outputs = self.output_storage.get_all_outputs(execution.id)

            # Map defined outputs
            for output_config in definition.outputs:
                # For MVP, just use the source step's output
                # Full expression evaluation comes in E2-07
                source = output_config.source
                if source.startswith("{{steps.") and source.endswith(".output}}"):
                    step_id = source[8:-9]  # Extract step ID
                    if step_id in all_outputs:
                        output_data[output_config.name] = all_outputs[step_id]

        execution.complete(output_data=output_data)
        self.execution_repo.save(execution)

        await self._publish_event(ProcessCompleted(
            execution_id=execution.id,
            process_id=execution.process_id,
            process_name=execution.process_name,
            output_data=output_data,
            total_cost=execution.total_cost,
            total_duration=execution.duration or Duration(seconds=0),
        ))

        logger.info(f"Execution {execution.id} completed successfully")

    async def _fail_execution(
        self,
        execution: ProcessExecution,
        error: str,
        definition: Optional[ProcessDefinition] = None,
    ) -> None:
        """
        Fail the execution and run any compensation handlers.

        Compensations run in reverse order of step completion.
        """
        execution.fail(error)
        self.execution_repo.save(execution)

        # Get failed steps for context
        failed_steps = execution.get_failed_step_ids()

        # Determine failed step ID (required field)
        failed_step_id = StepId(failed_steps[0]) if failed_steps else StepId("unknown")

        await self._publish_event(ProcessFailed(
            execution_id=execution.id,
            process_id=execution.process_id,
            process_name=execution.process_name,
            error_message=error,
            failed_step_id=failed_step_id,
        ))

        logger.error(f"Execution {execution.id} failed: {error}")

        # Run compensation handlers for completed steps (reverse order)
        if definition:
            await self._run_compensations(execution, definition)

    async def _run_compensations(
        self,
        execution: ProcessExecution,
        definition: ProcessDefinition,
    ) -> None:
        """
        Run compensation handlers for completed steps in reverse order.

        Compensation actions are defined in step definitions and execute
        when the process fails after the step has completed.
        """
        # Get completed step IDs in order of completion
        completed_step_ids = []
        for step_id, step_exec in execution.step_executions.items():
            if step_exec.status == StepStatus.COMPLETED and step_exec.completed_at:
                completed_step_ids.append((step_id, step_exec.completed_at))

        # Sort by completion time (most recent first for reverse order)
        completed_step_ids.sort(key=lambda x: x[1], reverse=True)

        # Find steps with compensation defined
        steps_with_compensation = []
        for step_id, _ in completed_step_ids:
            step_def = next(
                (s for s in definition.steps if str(s.id) == step_id),
                None
            )
            if step_def and step_def.compensation:
                steps_with_compensation.append(step_def)

        if not steps_with_compensation:
            return

        logger.info(f"Running {len(steps_with_compensation)} compensation handlers")

        # Emit CompensationStarted event
        await self._publish_event(CompensationStarted(
            execution_id=execution.id,
            process_id=execution.process_id,
            process_name=execution.process_name,
            compensation_count=len(steps_with_compensation),
        ))

        for step_def in steps_with_compensation:
            try:
                await self._execute_compensation(execution, step_def)
            except Exception as e:
                logger.error(f"Compensation for step '{step_def.name}' failed: {e}")
                # Emit CompensationFailed event
                await self._publish_event(CompensationFailed(
                    execution_id=execution.id,
                    step_id=step_def.id,
                    step_name=step_def.name,
                    compensation_type=step_def.compensation.type if step_def.compensation else "unknown",
                    error_message=str(e),
                ))
                # Continue with other compensations even if one fails

    async def _execute_compensation(
        self,
        execution: ProcessExecution,
        step_def: StepDefinition,
    ) -> None:
        """
        Execute a single compensation action.

        Compensation can be:
        - agent_task: Send a message to an agent
        - notification: Send a notification
        """
        compensation = step_def.compensation
        if not compensation:
            return

        comp_type = compensation.type
        logger.info(f"Executing compensation for step '{step_def.name}' (type={comp_type})")

        # Build context for template substitution
        step_outputs = self._build_step_outputs(execution)

        if comp_type == "agent_task":
            # Execute compensation via agent
            handler = self.handler_registry.get_handler(StepType.AGENT_TASK)
            if handler:
                from .step_handler import StepContext
                from ..domain import AgentTaskConfig

                config = AgentTaskConfig.from_dict({
                    "agent": compensation.agent or "",
                    "message": compensation.message or f"Rollback for step: {step_def.name}",
                    "timeout": str(compensation.timeout),
                })

                context = StepContext(
                    execution=execution,
                    step_definition=step_def,
                    step_outputs=step_outputs,
                    input_data=execution.input_data,
                )

                result = await handler.execute(context, config)
                if result.success:
                    logger.info(f"Compensation for '{step_def.name}' completed successfully")
                    await self._publish_event(CompensationCompleted(
                        execution_id=execution.id,
                        step_id=step_def.id,
                        step_name=step_def.name,
                        compensation_type="agent_task",
                    ))
                else:
                    logger.warning(f"Compensation for '{step_def.name}' failed: {result.error}")
                    await self._publish_event(CompensationFailed(
                        execution_id=execution.id,
                        step_id=step_def.id,
                        step_name=step_def.name,
                        compensation_type="agent_task",
                        error_message=result.error or "Unknown error",
                    ))

        elif comp_type == "notification":
            # Send compensation notification
            handler = self.handler_registry.get_handler(StepType.NOTIFICATION)
            if handler:
                from .step_handler import StepContext
                from ..domain import NotificationConfig

                config = NotificationConfig.from_dict({
                    "channel": compensation.channel,
                    "message": compensation.message or f"Rollback triggered for: {step_def.name}",
                    "webhook_url": compensation.webhook_url,
                })

                context = StepContext(
                    execution=execution,
                    step_definition=step_def,
                    step_outputs=step_outputs,
                    input_data=execution.input_data,
                )

                result = await handler.execute(context, config)
                if result.success:
                    logger.info(f"Compensation notification for '{step_def.name}' sent")
                    await self._publish_event(CompensationCompleted(
                        execution_id=execution.id,
                        step_id=step_def.id,
                        step_name=step_def.name,
                        compensation_type="notification",
                    ))
                else:
                    logger.warning(f"Compensation notification failed: {result.error}")
                    await self._publish_event(CompensationFailed(
                        execution_id=execution.id,
                        step_id=step_def.id,
                        step_name=step_def.name,
                        compensation_type="notification",
                        error_message=result.error or "Unknown error",
                    ))
        else:
            logger.warning(f"Unknown compensation type: {comp_type}")

    async def _publish_event(self, event) -> None:
        """Publish a domain event if event bus is configured."""
        if self.event_bus:
            await self.event_bus.publish(event)
