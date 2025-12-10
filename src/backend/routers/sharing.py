"""
Agent sharing routes for the Trinity backend.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Request

from models import User
from database import db, AgentShare, AgentShareRequest
from dependencies import get_current_user
from services.audit_service import log_audit_event
from services.docker_service import get_agent_container

router = APIRouter(prefix="/api/agents", tags=["sharing"])

# WebSocket manager will be injected from main.py
manager = None

def set_websocket_manager(ws_manager):
    """Set the WebSocket manager for broadcasting events."""
    global manager
    manager = ws_manager


@router.post("/{agent_name}/share", response_model=AgentShare)
async def share_agent_endpoint(
    agent_name: str,
    share_request: AgentShareRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Share an agent with another user by email."""
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if not db.can_user_share_agent(current_user.username, agent_name):
        await log_audit_event(
            event_type="agent_sharing",
            action="share",
            user_id=current_user.username,
            agent_name=agent_name,
            ip_address=request.client.host if request.client else None,
            result="unauthorized",
            severity="warning",
            details={"target_email": share_request.email}
        )
        raise HTTPException(status_code=403, detail="You don't have permission to share this agent")

    current_user_data = db.get_user_by_username(current_user.username)
    current_user_email = (current_user_data.get("email") or "") if current_user_data else ""
    if current_user_email and current_user_email.lower() == share_request.email.lower():
        raise HTTPException(status_code=400, detail="Cannot share an agent with yourself")

    share = db.share_agent(agent_name, current_user.username, share_request.email)
    if not share:
        raise HTTPException(status_code=409, detail=f"Agent is already shared with {share_request.email}")

    await log_audit_event(
        event_type="agent_sharing",
        action="share",
        user_id=current_user.username,
        agent_name=agent_name,
        ip_address=request.client.host if request.client else None,
        result="success",
        details={"shared_with": share_request.email}
    )

    if manager:
        await manager.broadcast(json.dumps({
            "event": "agent_shared",
            "data": {"name": agent_name, "shared_with": share_request.email}
        }))

    return share


@router.delete("/{agent_name}/share/{email}")
async def unshare_agent_endpoint(
    agent_name: str,
    email: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Remove sharing access for a user."""
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if not db.can_user_share_agent(current_user.username, agent_name):
        await log_audit_event(
            event_type="agent_sharing",
            action="unshare",
            user_id=current_user.username,
            agent_name=agent_name,
            ip_address=request.client.host if request.client else None,
            result="unauthorized",
            severity="warning",
            details={"target_email": email}
        )
        raise HTTPException(status_code=403, detail="You don't have permission to modify sharing for this agent")

    success = db.unshare_agent(agent_name, current_user.username, email)
    if not success:
        raise HTTPException(status_code=404, detail=f"No sharing found for {email}")

    await log_audit_event(
        event_type="agent_sharing",
        action="unshare",
        user_id=current_user.username,
        agent_name=agent_name,
        ip_address=request.client.host if request.client else None,
        result="success",
        details={"removed_user": email}
    )

    if manager:
        await manager.broadcast(json.dumps({
            "event": "agent_unshared",
            "data": {"name": agent_name, "removed_user": email}
        }))

    return {"message": f"Sharing removed for {email}"}


@router.get("/{agent_name}/shares", response_model=list[AgentShare])
async def get_agent_shares_endpoint(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get all users an agent is shared with."""
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if not db.can_user_share_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to view sharing for this agent")

    shares = db.get_agent_shares(agent_name)
    return shares
