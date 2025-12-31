"""
Schedule management routes for the Trinity backend.

Provides CRUD operations for agent schedules and execution history.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import json

from models import User
from dependencies import get_current_user, get_authorized_agent, AuthorizedAgent, CurrentUser
from database import db, Schedule, ScheduleCreate, ScheduleExecution
from services.scheduler_service import scheduler_service

router = APIRouter(prefix="/api/agents", tags=["schedules"])


# Request/Response Models

class ScheduleUpdateRequest(BaseModel):
    """Request model for updating a schedule."""
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    message: Optional[str] = None
    enabled: Optional[bool] = None
    timezone: Optional[str] = None
    description: Optional[str] = None


class ScheduleResponse(BaseModel):
    """Response model for schedule data."""
    id: str
    agent_name: str
    name: str
    cron_expression: str
    message: str
    enabled: bool
    timezone: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]

    class Config:
        from_attributes = True


class ExecutionResponse(BaseModel):
    """Response model for execution data."""
    id: str
    schedule_id: str
    agent_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    message: str
    response: Optional[str]
    error: Optional[str]
    triggered_by: str
    # Observability fields
    context_used: Optional[int] = None
    context_max: Optional[int] = None
    cost: Optional[float] = None
    tool_calls: Optional[str] = None
    execution_log: Optional[str] = None  # Full Claude Code execution transcript (JSON)

    class Config:
        from_attributes = True


# Schedule CRUD Endpoints

@router.get("/{name}/schedules", response_model=List[ScheduleResponse])
async def list_agent_schedules(name: AuthorizedAgent):
    """List all schedules for an agent."""
    schedules = db.list_agent_schedules(name)
    return [ScheduleResponse(**s.model_dump()) for s in schedules]


@router.post("/{name}/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    name: str,
    schedule_data: ScheduleCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new schedule for an agent."""
    # Validate cron expression
    try:
        from croniter import croniter
        croniter(schedule_data.cron_expression)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cron expression: {str(e)}"
        )

    schedule = db.create_schedule(name, current_user.username, schedule_data)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create schedule - access denied or agent not found"
        )

    # Add to scheduler if enabled
    if schedule.enabled:
        scheduler_service.add_schedule(schedule)

    return ScheduleResponse(**schedule.model_dump())


@router.get("/{name}/schedules/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    name: AuthorizedAgent,
    schedule_id: str
):
    """Get a specific schedule."""
    schedule = db.get_schedule(schedule_id)
    if not schedule or schedule.agent_name != name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    return ScheduleResponse(**schedule.model_dump())


@router.put("/{name}/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    name: str,
    schedule_id: str,
    updates: ScheduleUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """Update a schedule."""
    schedule = db.get_schedule(schedule_id)
    if not schedule or schedule.agent_name != name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    # Validate cron expression if being updated
    if updates.cron_expression:
        try:
            from croniter import croniter
            croniter(updates.cron_expression)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cron expression: {str(e)}"
            )

    # Build updates dict
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}

    updated_schedule = db.update_schedule(schedule_id, current_user.username, update_dict)
    if not updated_schedule:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update schedule - access denied"
        )

    # Update in scheduler
    scheduler_service.update_schedule(updated_schedule)

    return ScheduleResponse(**updated_schedule.model_dump())


@router.delete("/{name}/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    name: str,
    schedule_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a schedule."""
    schedule = db.get_schedule(schedule_id)
    if not schedule or schedule.agent_name != name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    # Remove from scheduler first
    scheduler_service.remove_schedule(schedule_id)

    if not db.delete_schedule(schedule_id, current_user.username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete schedule - access denied"
        )


# Schedule Control Endpoints

@router.post("/{name}/schedules/{schedule_id}/enable")
async def enable_schedule(
    name: AuthorizedAgent,
    schedule_id: str
):
    """Enable a schedule."""
    schedule = db.get_schedule(schedule_id)
    if not schedule or schedule.agent_name != name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    scheduler_service.enable_schedule(schedule_id)

    return {"status": "enabled", "schedule_id": schedule_id}


@router.post("/{name}/schedules/{schedule_id}/disable")
async def disable_schedule(
    name: AuthorizedAgent,
    schedule_id: str
):
    """Disable a schedule."""
    schedule = db.get_schedule(schedule_id)
    if not schedule or schedule.agent_name != name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    scheduler_service.disable_schedule(schedule_id)

    return {"status": "disabled", "schedule_id": schedule_id}


@router.post("/{name}/schedules/{schedule_id}/trigger")
async def trigger_schedule(
    name: AuthorizedAgent,
    schedule_id: str
):
    """Manually trigger a schedule execution."""
    schedule = db.get_schedule(schedule_id)
    if not schedule or schedule.agent_name != name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    execution_id = await scheduler_service.trigger_schedule(schedule_id)
    if not execution_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger schedule"
        )

    return {
        "status": "triggered",
        "schedule_id": schedule_id,
        "execution_id": execution_id
    }


# Execution History Endpoints

@router.get("/{name}/schedules/{schedule_id}/executions", response_model=List[ExecutionResponse])
async def get_schedule_executions(
    name: AuthorizedAgent,
    schedule_id: str,
    limit: int = 50
):
    """Get execution history for a schedule."""
    schedule = db.get_schedule(schedule_id)
    if not schedule or schedule.agent_name != name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    executions = db.get_schedule_executions(schedule_id, limit=limit)
    return [ExecutionResponse(**e.model_dump()) for e in executions]


@router.get("/{name}/executions", response_model=List[ExecutionResponse])
async def get_agent_executions(
    name: AuthorizedAgent,
    limit: int = 50
):
    """Get all executions for an agent across all schedules."""
    executions = db.get_agent_executions(name, limit=limit)
    return [ExecutionResponse(**e.model_dump()) for e in executions]


@router.get("/{name}/executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    name: AuthorizedAgent,
    execution_id: str
):
    """Get details of a specific execution."""
    execution = db.get_execution(execution_id)
    if not execution or execution.agent_name != name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )

    return ExecutionResponse(**execution.model_dump())


@router.get("/{name}/executions/{execution_id}/log")
async def get_execution_log(
    name: AuthorizedAgent,
    execution_id: str
):
    """
    Get the full execution log for a specific execution.

    Returns the raw Claude Code execution transcript as JSON array.
    This includes all tool calls, thinking, and responses.
    """
    execution = db.get_execution(execution_id)
    if not execution or execution.agent_name != name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )

    if not execution.execution_log:
        return {
            "execution_id": execution_id,
            "has_log": False,
            "log": None,
            "message": "No execution log available for this execution"
        }

    # Parse the JSON log for structured response
    try:
        log_data = json.loads(execution.execution_log)
    except json.JSONDecodeError:
        log_data = execution.execution_log

    return {
        "execution_id": execution_id,
        "agent_name": name,
        "has_log": True,
        "log": log_data,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "status": execution.status
    }


# Scheduler Status Endpoint

@router.get("/scheduler/status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_user)
):
    """Get scheduler status (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return scheduler_service.get_scheduler_status()
