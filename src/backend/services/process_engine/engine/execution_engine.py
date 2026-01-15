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
    StepSkipped,
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
            # Check if cancelled
            if execution.status == ExecutionStatus.CANCELLED:
                break
            
            # Check for failures
            if resolver.has_failed_steps(execution) and self.config.stop_on_failure:
                await self._fail_execution(execution, "Step execution failed")
                break
            
            # Get next step to execute
            next_step_id = resolver.get_next_step(execution)
            
            if next_step_id is None:
                # No more steps ready
                if resolver.is_complete(execution):
                    # All done - complete execution
                    await self._complete_execution(execution, definition)
                    break
                elif resolver.has_failed_steps(execution):
                    # Failed steps blocking progress
                    await self._fail_execution(execution, "Step execution failed")
                    break
                else:
                    # Shouldn't happen in sequential execution
                    logger.error("No steps ready but execution not complete")
                    await self._fail_execution(execution, "Execution deadlock")
                    break
            
            # Execute the step
            step_def = resolver.get_step_definition(next_step_id)
            if step_def is None:
                await self._fail_execution(execution, f"Step definition not found: {next_step_id}")
                break
            
            await self._execute_step(execution, step_def, definition)
        
        return execution
    
    async def _execute_step(
        self,
        execution: ProcessExecution,
        step_def: StepDefinition,
        definition: ProcessDefinition,
    ) -> None:
        """
        Execute a single step.
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
        
        # Start step
        execution.start_step(step_id)
        self.execution_repo.save(execution)
        
        await self._publish_event(StepStarted(
            execution_id=execution.id,
            step_id=step_id,
            step_name=step_def.name,
            step_type=step_def.type.value,
        ))
        
        logger.info(f"Executing step '{step_def.name}' ({step_id})")
        
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
            logger.exception(f"Step '{step_def.name}' raised exception")
            result = StepResult.fail(str(e), error_code="EXCEPTION")
        
        # Handle result
        if result.success:
            await self._handle_step_success(execution, step_def, result)
        else:
            await self._handle_step_failure(execution, step_def, result)
    
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
    
    async def _handle_step_failure(
        self,
        execution: ProcessExecution,
        step_def: StepDefinition,
        result: StepResult,
    ) -> None:
        """Handle step failure."""
        step_id = step_def.id
        
        # Fail the step
        execution.fail_step(step_id, result.error or "Unknown error")
        self.execution_repo.save(execution)
        
        step_exec = execution.step_executions[str(step_id)]
        
        await self._publish_event(StepFailed(
            execution_id=execution.id,
            step_id=step_id,
            step_name=step_def.name,
            error_message=result.error or "Unknown error",
            error_code=result.error_code,
            retry_count=step_exec.retry_count,
            will_retry=False,  # No retry in MVP
        ))
        
        logger.error(f"Step '{step_def.name}' failed: {result.error}")
    
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
    ) -> None:
        """Fail the execution."""
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
    
    async def _publish_event(self, event) -> None:
        """Publish a domain event if event bus is configured."""
        if self.event_bus:
            await self.event_bus.publish(event)
