"""
Process Execution API Router

Provides REST API endpoints for managing process executions.
Part of the Process-Driven Platform feature.

Reference: BACKLOG_MVP.md - E2-05
"""

import asyncio
import logging
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from pydantic import BaseModel, Field

from dependencies import get_current_user, CurrentUser
from services.process_engine.domain import (
    ProcessDefinition,
    ProcessExecution,
    ProcessId,
    ExecutionId,
    ExecutionStatus,
    StepStatus,
    DefinitionStatus,
)
from services.process_engine.repositories import (
    SqliteProcessDefinitionRepository,
    SqliteProcessExecutionRepository,
    SqliteEventRepository,
)
from services.process_engine.services import OutputStorage, EventLogger
from services.process_engine.events import InMemoryEventBus, get_websocket_publisher
from services.process_engine.engine import (
    ExecutionEngine,
    StepHandlerRegistry,
    AgentTaskHandler,
    HumanApprovalHandler,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/executions", tags=["executions"])


# =============================================================================
# Pydantic Models for API
# =============================================================================


class ExecutionStartRequest(BaseModel):
    """Request body for starting a new execution."""
    input_data: dict[str, Any] = Field(default_factory=dict, description="Input data for the process")
    triggered_by: str = Field(default="api", description="What triggered this execution")


class StepError(BaseModel):
    """Error details for a failed step."""
    message: str
    code: Optional[str] = None
    attempt: Optional[int] = None
    failed_at: Optional[str] = None


class StepExecutionSummary(BaseModel):
    """Summary of a step execution."""
    step_id: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[StepError] = None
    retry_count: int = 0
    parallel_level: int = 0  # Execution level for parallel visualization


class ExecutionSummary(BaseModel):
    """Summary view of an execution."""
    id: str
    process_id: str
    process_name: str
    status: str
    triggered_by: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str


class ExecutionDetail(BaseModel):
    """Detailed view of an execution."""
    id: str
    process_id: str
    process_version: str
    process_name: str
    status: str
    triggered_by: str
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    total_cost: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    steps: List[StepExecutionSummary]
    has_parallel_steps: bool = False  # True if process has parallel execution


class ExecutionListResponse(BaseModel):
    """Response for listing executions."""
    executions: List[ExecutionSummary]
    total: int
    limit: int
    offset: int


# =============================================================================
# Dependencies
# =============================================================================


# Singleton instances for the process engine components
_definition_repo: Optional[SqliteProcessDefinitionRepository] = None
_execution_repo: Optional[SqliteProcessExecutionRepository] = None
_event_repo: Optional[SqliteEventRepository] = None
_event_bus: Optional[InMemoryEventBus] = None
_handler_registry: Optional[StepHandlerRegistry] = None
_event_logger: Optional[EventLogger] = None

# Database path configuration
import os
from pathlib import Path
DB_PATH = os.getenv("TRINITY_DB_PATH", str(Path.home() / "trinity-data" / "trinity.db"))


def get_definition_repo() -> SqliteProcessDefinitionRepository:
    """Get the process definition repository."""
    global _definition_repo
    if _definition_repo is None:
        process_db_path = DB_PATH.replace(".db", "_processes.db")
        os.makedirs(os.path.dirname(process_db_path), exist_ok=True)
        _definition_repo = SqliteProcessDefinitionRepository(process_db_path)
    return _definition_repo


def get_execution_repo() -> SqliteProcessExecutionRepository:
    """Get the process execution repository."""
    global _execution_repo
    if _execution_repo is None:
        exec_db_path = DB_PATH.replace(".db", "_executions.db")
        os.makedirs(os.path.dirname(exec_db_path), exist_ok=True)
        _execution_repo = SqliteProcessExecutionRepository(exec_db_path)
    return _execution_repo


def get_event_repo() -> SqliteEventRepository:
    """Get the event repository."""
    global _event_repo
    if _event_repo is None:
        event_db_path = DB_PATH.replace(".db", "_events.db")
        os.makedirs(os.path.dirname(event_db_path), exist_ok=True)
        _event_repo = SqliteEventRepository(event_db_path)
    return _event_repo


def get_event_bus() -> InMemoryEventBus:
    """Get the event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = InMemoryEventBus()
        # Register WebSocket publisher to broadcast events
        websocket_publisher = get_websocket_publisher()
        websocket_publisher.register_with_event_bus(_event_bus)
    return _event_bus


def get_handler_registry() -> StepHandlerRegistry:
    """Get the step handler registry."""
    global _handler_registry
    if _handler_registry is None:
        _handler_registry = StepHandlerRegistry()
        # Register default handlers
        _handler_registry.register(AgentTaskHandler())
        _handler_registry.register(HumanApprovalHandler())
    return _handler_registry


def get_event_logger() -> EventLogger:
    """Get and start the event logger."""
    global _event_logger
    if _event_logger is None:
        repo = get_event_repo()
        bus = get_event_bus()
        _event_logger = EventLogger(repo, bus)
        _event_logger.start()
    return _event_logger


def get_execution_engine() -> ExecutionEngine:
    """Get the execution engine."""
    execution_repo = get_execution_repo()
    output_storage = OutputStorage(execution_repo)
    
    # Ensure event logger is running
    get_event_logger()
    
    return ExecutionEngine(
        execution_repo=execution_repo,
        event_bus=get_event_bus(),
        output_storage=output_storage,
        handler_registry=get_handler_registry(),
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/processes/{process_id}/execute", response_model=ExecutionDetail, status_code=201)
async def start_execution(
    process_id: str,
    current_user: CurrentUser,
    request: ExecutionStartRequest = Body(default_factory=ExecutionStartRequest),
    background_tasks: BackgroundTasks = None,
):
    """
    Start a new execution of a process.
    
    The execution runs asynchronously in the background.
    Returns the initial execution state immediately.
    """
    definition_repo = get_definition_repo()
    
    # Get the process definition
    try:
        pid = ProcessId(process_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid process ID format")
    
    definition = definition_repo.get_by_id(pid)
    if not definition:
        raise HTTPException(status_code=404, detail="Process definition not found")
    
    # Only published processes can be executed
    if definition.status != DefinitionStatus.PUBLISHED:
        raise HTTPException(
            status_code=400,
            detail=f"Process is not published (status: {definition.status.value})"
        )
    
    # Create the execution
    execution_repo = get_execution_repo()
    execution = ProcessExecution.create(
        definition=definition,
        input_data=request.input_data,
        triggered_by=request.triggered_by,
    )
    execution_repo.save(execution)
    
    logger.info(f"Created execution {execution.id} for process '{definition.name}' by user {current_user.username}")
    
    # Run execution in background
    if background_tasks:
        background_tasks.add_task(_run_execution, str(execution.id), str(definition.id))
    
    return _to_detail(execution, definition)


async def _run_execution(execution_id: str, process_id: str):
    """Background task to run an execution."""
    try:
        definition_repo = get_definition_repo()
        execution_repo = get_execution_repo()
        engine = get_execution_engine()
        
        definition = definition_repo.get_by_id(ProcessId(process_id))
        execution = execution_repo.get_by_id(ExecutionId(execution_id))
        
        if definition and execution:
            await engine.resume(execution, definition)
            
    except Exception as e:
        logger.exception(f"Error running execution {execution_id}")
        # Update execution to failed state
        try:
            execution_repo = get_execution_repo()
            execution = execution_repo.get_by_id(ExecutionId(execution_id))
            if execution and execution.status not in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
                execution.fail(str(e))
                execution_repo.save(execution)
        except Exception:
            pass


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    current_user: CurrentUser,
    status: Optional[str] = Query(None, description="Filter by status"),
    process_id: Optional[str] = Query(None, description="Filter by process ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List all executions with optional filters.
    """
    execution_repo = get_execution_repo()
    
    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = ExecutionStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    # Filter by process if specified
    if process_id:
        try:
            pid = ProcessId(process_id)
            executions = execution_repo.list_by_process(pid, limit=limit, offset=offset)
            total = len(executions)  # Simplified count
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid process ID format")
    else:
        executions = execution_repo.list_all(limit=limit, offset=offset, status=status_filter)
        total = execution_repo.count(status=status_filter)
    
    return ExecutionListResponse(
        executions=[_to_summary(e) for e in executions],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{execution_id}", response_model=ExecutionDetail)
async def get_execution(
    execution_id: str,
    current_user: CurrentUser,
):
    """
    Get detailed information about a specific execution.
    """
    execution_repo = get_execution_repo()
    definition_repo = get_definition_repo()
    
    try:
        eid = ExecutionId(execution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution ID format")
    
    execution = execution_repo.get_by_id(eid)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    # Get definition for parallel structure info
    definition = definition_repo.get_by_id(execution.process_id)
    
    return _to_detail(execution, definition)


@router.post("/{execution_id}/cancel", response_model=ExecutionDetail)
async def cancel_execution(
    execution_id: str,
    current_user: CurrentUser,
):
    """
    Cancel a running execution.
    """
    execution_repo = get_execution_repo()
    definition_repo = get_definition_repo()
    
    try:
        eid = ExecutionId(execution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution ID format")
    
    execution = execution_repo.get_by_id(eid)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING, ExecutionStatus.PAUSED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel execution in status: {execution.status.value}"
        )
    
    execution.cancel(f"Cancelled by {current_user.username}")
    execution_repo.save(execution)
    
    logger.info(f"Execution {execution_id} cancelled by {current_user.username}")
    
    definition = definition_repo.get_by_id(execution.process_id)
    return _to_detail(execution, definition)


@router.post("/{execution_id}/retry", response_model=ExecutionDetail, status_code=201)
async def retry_execution(
    execution_id: str,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks = None,
):
    """
    Retry a failed execution.
    
    Creates a new execution with the same input data.
    """
    execution_repo = get_execution_repo()
    definition_repo = get_definition_repo()
    
    try:
        eid = ExecutionId(execution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution ID format")
    
    execution = execution_repo.get_by_id(eid)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    if execution.status != ExecutionStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Can only retry failed executions (status: {execution.status.value})"
        )
    
    # Get the process definition
    definition = definition_repo.get_by_id(execution.process_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Process definition not found")
    
    # Create new execution with same input
    new_execution = ProcessExecution.create(
        definition=definition,
        input_data=execution.input_data,
        triggered_by="retry",
    )
    execution_repo.save(new_execution)
    
    logger.info(f"Created retry execution {new_execution.id} for failed execution {execution_id}")
    
    # Run in background
    if background_tasks:
        background_tasks.add_task(_run_execution, str(new_execution.id), str(definition.id))
    
    return _to_detail(new_execution, definition)


@router.get("/{execution_id}/events")
async def get_execution_events(
    execution_id: str,
    current_user: CurrentUser,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    Get audit log of events for an execution.
    """
    event_repo = get_event_repo()
    
    try:
        eid = ExecutionId(execution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution ID format")
    
    events = event_repo.get_by_execution_id(eid, limit=limit, offset=offset)
    return [e.to_dict() for e in events]


@router.get("/{execution_id}/steps/{step_id}/output")
async def get_step_output(
    execution_id: str,
    step_id: str,
    current_user: CurrentUser,
):
    """
    Get the output of a specific step.
    """
    execution_repo = get_execution_repo()
    output_storage = OutputStorage(execution_repo)
    
    try:
        eid = ExecutionId(execution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution ID format")
    
    from services.process_engine.domain import StepId
    try:
        sid = StepId(step_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid step ID format")
    
    output = output_storage.retrieve(eid, sid)
    if output is None:
        raise HTTPException(status_code=404, detail="Step output not found")
    
    return {"output": output}


# =============================================================================
# Helper Functions
# =============================================================================


def _to_summary(execution: ProcessExecution) -> ExecutionSummary:
    """Convert execution to summary response."""
    return ExecutionSummary(
        id=str(execution.id),
        process_id=str(execution.process_id),
        process_name=execution.process_name,
        status=execution.status.value,
        triggered_by=execution.triggered_by,
        started_at=execution.started_at.isoformat() if execution.started_at else None,
        completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
        created_at=execution.started_at.isoformat() if execution.started_at else "",
    )


def _to_detail(
    execution: ProcessExecution,
    definition: Optional[ProcessDefinition] = None,
) -> ExecutionDetail:
    """Convert execution to detail response."""
    from services.process_engine.engine import DependencyResolver
    
    # Calculate parallel structure if definition available
    parallel_levels: dict[str, int] = {}
    has_parallel = False
    if definition:
        resolver = DependencyResolver(definition)
        parallel_structure = resolver.get_parallel_structure()
        parallel_levels = parallel_structure.step_levels
        has_parallel = parallel_structure.has_parallel_execution()
    
    steps = []
    for step_id, step_exec in execution.step_executions.items():
        step_error = None
        if step_exec.error:
            if isinstance(step_exec.error, dict):
                step_error = StepError(
                    message=step_exec.error.get("message", "Unknown error"),
                    code=step_exec.error.get("code"),
                    attempt=step_exec.error.get("attempt"),
                    failed_at=step_exec.error.get("failed_at"),
                )
            else:
                step_error = StepError(message=str(step_exec.error))
        
        steps.append(StepExecutionSummary(
            step_id=step_id,
            status=step_exec.status.value,
            started_at=step_exec.started_at.isoformat() if step_exec.started_at else None,
            completed_at=step_exec.completed_at.isoformat() if step_exec.completed_at else None,
            error=step_error,
            retry_count=step_exec.retry_count,
            parallel_level=parallel_levels.get(step_id, 0),
        ))
    
    duration = None
    if execution.duration:
        duration = execution.duration.seconds
    
    return ExecutionDetail(
        id=str(execution.id),
        process_id=str(execution.process_id),
        process_version=str(execution.process_version),
        process_name=execution.process_name,
        status=execution.status.value,
        triggered_by=execution.triggered_by,
        input_data=execution.input_data,
        output_data=execution.output_data,
        total_cost=str(execution.total_cost) if execution.total_cost else None,
        started_at=execution.started_at.isoformat() if execution.started_at else None,
        completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
        duration_seconds=duration,
        steps=steps,
        has_parallel_steps=has_parallel,
    )
