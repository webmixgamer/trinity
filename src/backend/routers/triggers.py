"""
Trigger Endpoints

Handles webhook triggers for starting process executions.

Reference: BACKLOG_CORE.md - E8-02
"""

import logging
import hmac
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel

from services.process_engine.domain import (
    WebhookTriggerConfig,
    ProcessDefinition,
    DefinitionStatus,
)

# Reuse centralized repository and engine instances
from routers.processes import get_repository as get_process_repo
from routers.executions import get_execution_engine


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/triggers", tags=["triggers"])


# =============================================================================
# Schemas
# =============================================================================


class TriggerResponse(BaseModel):
    """Response from a trigger invocation."""
    execution_id: str
    process_name: str
    status: str
    message: str


class TriggerInfo(BaseModel):
    """Information about a trigger."""
    id: str
    type: str
    process_name: str
    process_id: str
    enabled: bool
    webhook_url: str
    description: str


# =============================================================================
# Helper Functions
# =============================================================================


def _find_trigger(trigger_id: str) -> tuple[Optional[ProcessDefinition], Optional[WebhookTriggerConfig]]:
    """
    Find a webhook trigger by ID across all published processes.
    
    Returns:
        Tuple of (ProcessDefinition, WebhookTriggerConfig) if found, (None, None) otherwise.
    """
    repo = get_process_repo()
    
    # Use proper repository method to get published processes
    published_processes = repo.list_all(status=DefinitionStatus.PUBLISHED)
    
    for process in published_processes:
        for trigger in process.triggers:
            if isinstance(trigger, WebhookTriggerConfig) and trigger.id == trigger_id:
                return process, trigger
    
    return None, None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=list[TriggerInfo])
async def list_triggers(request: Request):
    """
    List all webhook triggers across all processes.
    
    Returns a list of all configured triggers with their webhook URLs.
    """
    repo = get_process_repo()
    triggers = []
    
    # Use proper repository method to get published processes
    published_processes = repo.list_all(status=DefinitionStatus.PUBLISHED)
    
    for process in published_processes:
        for trigger in process.triggers:
            if isinstance(trigger, WebhookTriggerConfig):
                base_url = str(request.base_url).rstrip('/')
                webhook_url = f"{base_url}/api/triggers/webhook/{trigger.id}"
                triggers.append(TriggerInfo(
                    id=trigger.id,
                    type="webhook",
                    process_name=process.name,
                    process_id=str(process.id),
                    enabled=trigger.enabled,
                    webhook_url=webhook_url,
                    description=trigger.description,
                ))
    
    return triggers


@router.post("/webhook/{trigger_id}", response_model=TriggerResponse)
async def invoke_webhook(
    trigger_id: str,
    request: Request,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
):
    """
    Invoke a webhook trigger to start a process execution.
    
    The trigger_id must match a configured webhook trigger in a published process.
    The request body (JSON) will be available as `trigger.payload` in the process.
    
    Optional authentication via X-Webhook-Secret header if the trigger has a secret.
    """
    # Find the trigger and its process
    process, trigger = _find_trigger(trigger_id)
    
    if not process or not trigger:
        raise HTTPException(status_code=404, detail=f"Trigger not found: {trigger_id}")
    
    if not trigger.enabled:
        raise HTTPException(status_code=403, detail="Trigger is disabled")
    
    # Verify secret if configured
    if trigger.secret:
        if not x_webhook_secret:
            raise HTTPException(status_code=401, detail="Webhook secret required")
        
        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(trigger.secret, x_webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    # Parse request body as trigger payload
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    # Build input data with trigger context
    input_data = {
        "trigger": {
            "type": "webhook",
            "id": trigger_id,
            "payload": body,
        },
        **body,  # Also include body at top level for convenience
    }
    
    # Create and start execution using centralized engine
    engine = get_execution_engine()
    
    try:
        execution = await engine.start(
            definition=process,
            input_data=input_data,
            triggered_by="webhook",
        )
        
        logger.info(f"Webhook trigger '{trigger_id}' started execution {execution.id} for process '{process.name}'")
        
        return TriggerResponse(
            execution_id=str(execution.id),
            process_name=process.name,
            status=execution.status.value,
            message=f"Execution started successfully via webhook trigger",
        )
        
    except Exception as e:
        logger.error(f"Failed to start execution via webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")


@router.get("/webhook/{trigger_id}/info", response_model=TriggerInfo)
async def get_trigger_info(trigger_id: str, request: Request):
    """
    Get information about a specific webhook trigger.
    """
    process, trigger = _find_trigger(trigger_id)
    
    if not process or not trigger:
        raise HTTPException(status_code=404, detail=f"Trigger not found: {trigger_id}")
    
    base_url = str(request.base_url).rstrip('/')
    return TriggerInfo(
        id=trigger.id,
        type="webhook",
        process_name=process.name,
        process_id=str(process.id),
        enabled=trigger.enabled,
        webhook_url=f"{base_url}/api/triggers/webhook/{trigger.id}",
        description=trigger.description,
    )
