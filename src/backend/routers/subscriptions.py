"""
Subscription credential management routes (SUB-001).

Provides endpoints for registering Claude Max/Pro subscriptions
and assigning them to agents.

Key insight: Claude Code prioritizes ANTHROPIC_API_KEY env var over OAuth
credentials in ~/.claude/.credentials.json. When assigning a subscription,
we must remove ANTHROPIC_API_KEY from the container so Claude Code uses
the subscription's OAuth token.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List

from models import User
from database import db
from dependencies import get_current_user
from db_models import (
    SubscriptionCredentialCreate,
    SubscriptionCredential,
    SubscriptionWithAgents,
    AgentAuthStatus,
)

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])
logger = logging.getLogger(__name__)


def require_admin(current_user: User):
    """Verify user is an admin."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


# ============================================================================
# Subscription CRUD
# ============================================================================

@router.post("", response_model=SubscriptionCredential)
async def register_subscription(
    request: SubscriptionCredentialCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Register a new subscription credential.

    Admin-only. Takes the raw credentials JSON from ~/.claude/.credentials.json
    and encrypts it for storage. Use upsert semantics - if a subscription with
    the same name exists, it will be updated.

    Example:
        cat ~/.claude/.credentials.json | pbcopy
        # Then use the API or MCP tool to register
    """
    require_admin(current_user)

    try:
        # Validate that credentials_json is valid JSON
        import json
        try:
            json.loads(request.credentials_json)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="credentials_json must be valid JSON"
            )

        # Get the user's ID
        user = db.get_user_by_username(current_user.username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        subscription = db.create_subscription(
            name=request.name,
            credentials_json=request.credentials_json,
            owner_id=user["id"],
            subscription_type=request.subscription_type,
            rate_limit_tier=request.rate_limit_tier,
        )

        logger.info(f"Registered subscription '{request.name}' by {current_user.username}")
        return subscription

    except HTTPException:
        raise  # Let HTTP exceptions propagate as-is
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to register subscription: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register subscription: {str(e)}")


@router.get("", response_model=List[SubscriptionWithAgents])
async def list_subscriptions(
    current_user: User = Depends(get_current_user)
):
    """
    List all subscriptions with their assigned agents.

    Admin-only. Returns subscription metadata and agent assignments.
    Never returns the encrypted credentials.
    """
    require_admin(current_user)

    return db.list_subscriptions_with_agents()


@router.get("/{subscription_id}", response_model=SubscriptionWithAgents)
async def get_subscription(
    subscription_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get details for a specific subscription.

    Admin-only. Returns subscription metadata and assigned agents.
    """
    require_admin(current_user)

    # Try by ID first, then by name
    subscription = db.get_subscription(subscription_id)
    if not subscription:
        subscription = db.get_subscription_by_name(subscription_id)

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # Get assigned agents
    agents = db.get_agents_by_subscription(subscription.id)

    return SubscriptionWithAgents(
        **subscription.model_dump(),
        agents=agents
    )


@router.delete("/{subscription_id}")
async def delete_subscription(
    subscription_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a subscription.

    Admin-only. Cascade clears all agent assignments - agents will fall back
    to API key authentication.
    """
    require_admin(current_user)

    # Try by ID first, then by name
    subscription = db.get_subscription(subscription_id)
    if not subscription:
        subscription = db.get_subscription_by_name(subscription_id)

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # Get agents that will be affected
    affected_agents = db.get_agents_by_subscription(subscription.id)

    deleted = db.delete_subscription(subscription.id)

    if deleted:
        logger.info(
            f"Deleted subscription '{subscription.name}' by {current_user.username}, "
            f"cleared {len(affected_agents)} agent assignments"
        )
        return {
            "success": True,
            "message": f"Subscription '{subscription.name}' deleted",
            "agents_cleared": affected_agents
        }

    raise HTTPException(status_code=500, detail="Failed to delete subscription")


# ============================================================================
# Agent Subscription Assignment
# ============================================================================

@router.put("/agents/{agent_name}")
async def assign_subscription_to_agent(
    agent_name: str,
    subscription_name: str = Query(..., description="Name of subscription to assign"),
    current_user: User = Depends(get_current_user)
):
    """
    Assign a subscription to an agent.

    Owner access required. If the agent is running, credentials will be
    injected immediately.
    """
    # Check agent access (owner or admin)
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied to this agent")

    # Get subscription by name
    subscription = db.get_subscription_by_name(subscription_name)
    if not subscription:
        raise HTTPException(status_code=404, detail=f"Subscription '{subscription_name}' not found")

    try:
        db.assign_subscription_to_agent(agent_name, subscription.id)

        logger.info(
            f"Assigned subscription '{subscription_name}' to agent '{agent_name}' "
            f"by {current_user.username}"
        )

        # If agent is running, restart it so ANTHROPIC_API_KEY env var is
        # removed from the container (Claude Code prioritizes API key over
        # OAuth credentials — the key must be absent for subscription to work).
        from services.docker_service import get_agent_container, get_agent_status_from_container
        from services.docker_utils import container_stop
        from services.subscription_service import inject_subscription_to_agent
        from services.agent_service import start_agent_internal

        container = get_agent_container(agent_name)
        restart_result = None
        injection_result = {"status": "skipped", "reason": "agent_not_running"}

        if container:
            agent_status = get_agent_status_from_container(container)
            if agent_status.status == "running":
                try:
                    await container_stop(container)
                    start_result = await start_agent_internal(agent_name)
                    restart_result = "success"
                    injection_result = start_result.get("subscription_result", {})
                    logger.info(
                        f"Restarted agent '{agent_name}' to apply subscription "
                        f"(removed ANTHROPIC_API_KEY from container env)"
                    )
                except Exception as e:
                    logger.error(f"Failed to restart agent '{agent_name}' for subscription: {e}")
                    restart_result = f"failed: {e}"
                    # Fall back to injection-only (may not work if API key still present)
                    injection_result = await inject_subscription_to_agent(agent_name, subscription.id)

        if injection_result.get("status") == "failed":
            logger.error(
                f"Subscription injection failed for agent '{agent_name}': "
                f"{injection_result.get('error', 'unknown')}"
            )

        return {
            "success": True,
            "message": f"Subscription '{subscription_name}' assigned to agent '{agent_name}'",
            "agent_name": agent_name,
            "subscription_name": subscription_name,
            "injection_result": injection_result,
            "restart_result": restart_result,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/agents/{agent_name}")
async def clear_agent_subscription(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Clear subscription assignment from an agent.

    Owner access required. Agent will fall back to API key authentication.
    """
    # Check agent access
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied to this agent")

    # Get current subscription for logging
    current_sub = db.get_agent_subscription(agent_name)

    db.clear_agent_subscription(agent_name)

    if current_sub:
        logger.info(
            f"Cleared subscription '{current_sub.name}' from agent '{agent_name}' "
            f"by {current_user.username}"
        )

    # Restart running agent so ANTHROPIC_API_KEY is restored (if use_platform_api_key=1)
    restart_result = None
    from services.docker_service import get_agent_container, get_agent_status_from_container
    from services.docker_utils import container_stop
    from services.agent_service import start_agent_internal
    container = get_agent_container(agent_name)
    if container:
        agent_status = get_agent_status_from_container(container)
        if agent_status.status == "running":
            try:
                await container_stop(container)
                await start_agent_internal(agent_name)
                restart_result = "success"
                logger.info(f"Restarted agent '{agent_name}' to restore API key after subscription removal")
            except Exception as e:
                logger.error(f"Failed to restart agent '{agent_name}' after subscription removal: {e}")
                restart_result = f"failed: {e}"

    return {
        "success": True,
        "message": f"Subscription cleared from agent '{agent_name}'",
        "agent_name": agent_name,
        "previous_subscription": current_sub.name if current_sub else None,
        "restart_result": restart_result,
    }


@router.get("/agents/{agent_name}/auth", response_model=AgentAuthStatus)
async def get_agent_auth_status(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the authentication status for an agent.

    Returns whether the agent is using subscription, API key, or not configured.
    Owner access required.
    """
    # Check agent access
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied to this agent")

    try:
        from services.subscription_service import get_agent_auth_mode
        return await get_agent_auth_mode(agent_name)
    except Exception as e:
        logger.error(f"Failed to get auth status for agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
