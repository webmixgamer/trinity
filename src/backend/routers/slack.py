"""
Slack integration router (SLACK-001).

Thin HTTP layer that delegates to the channel adapter abstraction.

Public Endpoints (no auth):
- POST /api/public/slack/events - Receive Slack webhook events (webhook mode only)
- GET /api/public/slack/oauth/callback - OAuth completion redirect

Authenticated Endpoints:
- GET /api/agents/{name}/public-links/{link_id}/slack - Connection status
- POST /api/agents/{name}/public-links/{link_id}/slack/connect - Start OAuth
- DELETE /api/agents/{name}/public-links/{link_id}/slack - Disconnect
- PUT /api/agents/{name}/public-links/{link_id}/slack - Update settings
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from database import db
from dependencies import get_current_user
from models import User
from services.slack_service import slack_service
from db_models import SlackConnectionStatus, SlackOAuthInitResponse
from services.settings_service import get_slack_signing_secret

logger = logging.getLogger(__name__)


# =========================================================================
# Transport reference — set by startup hook in main.py
# =========================================================================

_webhook_transport = None


def set_webhook_transport(transport):
    """Set the webhook transport instance (called from main.py startup)."""
    global _webhook_transport
    _webhook_transport = transport


# =========================================================================
# Public Router (no authentication required)
# =========================================================================

public_router = APIRouter(prefix="/api/public/slack", tags=["slack-public"])


class SlackEventResponse(BaseModel):
    """Response to Slack events (always return 200)."""
    ok: bool = True
    challenge: Optional[str] = None


@public_router.post("/events", response_model=SlackEventResponse)
async def handle_slack_event(request: Request):
    """
    Handle incoming Slack webhook events.

    Only active in webhook transport mode. Socket Mode bypasses this endpoint.
    Always returns 200 to prevent Slack retries.
    """
    if _webhook_transport:
        result = await _webhook_transport.handle_http_request(request)
        return SlackEventResponse(**result)

    # No webhook transport — maybe using Socket Mode, or not configured
    # Still handle URL verification challenges for initial setup
    try:
        body = await request.body()
        import json
        event_data = json.loads(body)
        if event_data.get("type") == "url_verification":
            return SlackEventResponse(ok=True, challenge=event_data.get("challenge"))
    except Exception:
        pass

    logger.warning("Slack webhook event received but no webhook transport configured")
    return SlackEventResponse(ok=False)


@public_router.get("/oauth/callback")
async def slack_oauth_callback(code: str = None, state: str = None, error: str = None):
    """
    Handle Slack OAuth callback.

    Exchanges code for token and creates connection.
    Redirects to frontend with success/error status.
    """
    # Handle OAuth errors
    if error:
        logger.error(f"Slack OAuth error: {error}")
        return RedirectResponse(
            slack_service.get_oauth_callback_redirect("unknown", success=False, error=error)
        )

    if not code or not state:
        return RedirectResponse(
            slack_service.get_oauth_callback_redirect("unknown", success=False, error="missing_params")
        )

    # Decode and verify state
    valid, state_data = slack_service.decode_oauth_state(state)
    if not valid or not state_data:
        return RedirectResponse(
            slack_service.get_oauth_callback_redirect("unknown", success=False, error="invalid_state")
        )

    link_id = state_data["link_id"]
    agent_name = state_data["agent_name"]
    user_id = state_data["user_id"]

    # Exchange code for token
    success, result = await slack_service.exchange_oauth_code(code)
    if not success:
        return RedirectResponse(
            slack_service.get_oauth_callback_redirect(agent_name, success=False, error=result.get("error"))
        )

    # Create workspace connection + legacy connection + channel binding
    try:
        team_id = result["team_id"]
        team_name = result.get("team_name")
        bot_token = result["access_token"]

        # 1. Create/update workspace (new table)
        db.create_slack_workspace(
            team_id=team_id,
            team_name=team_name,
            bot_token=bot_token,
            connected_by=user_id
        )

        # 2. Create legacy connection (backward compat)
        try:
            db.create_slack_connection(
                link_id=link_id,
                slack_team_id=team_id,
                slack_team_name=team_name,
                slack_bot_token=bot_token,
                connected_by=user_id
            )
        except Exception:
            pass  # May fail on existing — ok

        # 3. Create Slack channel for this agent and bind it
        try:
            success, channel_id, error = await slack_service.create_channel(bot_token, agent_name)
            if success and channel_id:
                db.bind_slack_channel_to_agent(
                    team_id=team_id,
                    slack_channel_id=channel_id,
                    slack_channel_name=agent_name,
                    agent_name=agent_name,
                    created_by=user_id,
                    is_dm_default=True,  # First agent is DM default
                )
                logger.info(f"Agent {agent_name} bound to Slack channel #{agent_name}")
            else:
                logger.warning(f"Failed to create Slack channel for {agent_name}: {error}")
        except Exception as e:
            logger.warning(f"Failed to create channel binding: {e}")

        logger.info(f"Slack connection created for workspace {team_name}")

        return RedirectResponse(
            slack_service.get_oauth_callback_redirect(agent_name, success=True)
        )

    except Exception as e:
        logger.error(f"Failed to create Slack connection: {e}")
        return RedirectResponse(
            slack_service.get_oauth_callback_redirect(agent_name, success=False, error="database_error")
        )


# =========================================================================
# Authenticated Router (requires login)
# =========================================================================

auth_router = APIRouter(tags=["slack"])


@auth_router.get("/api/agents/{name}/public-links/{link_id}/slack", response_model=SlackConnectionStatus)
async def get_slack_connection_status(
    name: str,
    link_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get Slack connection status for a public link."""
    if not db.can_user_access_agent(current_user.username, name):
        raise HTTPException(status_code=403, detail="Access denied")

    link = db.get_public_link(link_id)
    if not link or link["agent_name"] != name:
        raise HTTPException(status_code=404, detail="Public link not found")

    connection = db.get_slack_connection_by_link(link_id)
    if not connection:
        return SlackConnectionStatus(connected=False)

    connected_by_user = db.get_user_by_id(int(connection["connected_by"])) if connection.get("connected_by") else None
    connected_by_email = connected_by_user.get("email", "unknown") if connected_by_user else "unknown"

    return SlackConnectionStatus(
        connected=True,
        team_id=connection["slack_team_id"],
        team_name=connection["slack_team_name"],
        connected_at=connection["connected_at"],
        connected_by=connected_by_email,
        enabled=connection["enabled"]
    )


@auth_router.post("/api/agents/{name}/public-links/{link_id}/slack/connect")
async def connect_slack(
    name: str,
    link_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Connect an agent to Slack.

    If workspace not yet connected: returns OAuth URL (frontend opens it).
    If workspace already connected: creates a Slack channel for the agent and binds it.
    """
    if not db.can_user_share_agent(current_user.username, name):
        raise HTTPException(status_code=403, detail="Only owners can connect Slack")

    link = db.get_public_link(link_id)
    if not link or link["agent_name"] != name:
        raise HTTPException(status_code=404, detail="Public link not found")

    # Check if workspace is already connected (any agent)
    # Look for existing workspace connection in new table
    existing_workspaces = []
    # Check legacy connections for any workspace
    all_connections = db.get_slack_connection_by_link(link_id)
    if all_connections:
        existing_workspaces.append(all_connections)

    # Also check new slack_workspaces table
    # We need to find ANY connected workspace — for now check legacy
    # TODO: add get_all_workspaces() method

    # Check if this agent already has a channel binding
    # by looking through all connected workspaces
    # For now, try to find a workspace connection from any source
    workspace = None
    try:
        # Try to get workspace from legacy connections
        # (We'll iterate through all link connections)
        import sqlite3
        from db.connection import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Check new workspaces table first
            cursor.execute("SELECT team_id, bot_token, team_name FROM slack_workspaces WHERE enabled = 1 LIMIT 1")
            row = cursor.fetchone()
            if row:
                workspace = {"team_id": row[0], "bot_token": row[1], "team_name": row[2]}
            else:
                # Fallback: check legacy table
                cursor.execute("SELECT slack_team_id, slack_bot_token, slack_team_name FROM slack_link_connections WHERE enabled = 1 LIMIT 1")
                row = cursor.fetchone()
                if row:
                    workspace = {"team_id": row[0], "bot_token": row[1], "team_name": row[2]}
    except Exception as e:
        logger.error(f"Error checking workspace: {e}")

    if workspace:
        # Workspace connected — create channel and bind agent
        try:
            # Create Slack channel named after the agent
            success, channel_id, error = await slack_service.create_channel(
                workspace["bot_token"], name
            )
            if not success:
                raise HTTPException(status_code=400, detail=f"Failed to create Slack channel: {error}")

            # Bind channel to agent
            agents_in_workspace = db.get_slack_agents_for_workspace(workspace["team_id"])
            is_first = len(agents_in_workspace) == 0

            db.bind_slack_channel_to_agent(
                team_id=workspace["team_id"],
                slack_channel_id=channel_id,
                slack_channel_name=name,
                agent_name=name,
                created_by=str(current_user.id),
                is_dm_default=is_first,  # First agent is DM default
            )

            # Also create legacy connection for backward compat
            try:
                db.create_slack_connection(
                    link_id=link_id,
                    slack_team_id=workspace["team_id"],
                    slack_team_name=workspace.get("team_name"),
                    slack_bot_token=workspace["bot_token"],
                    connected_by=str(current_user.id)
                )
            except Exception:
                pass  # May fail on UNIQUE — that's ok

            logger.info(f"Agent {name} bound to Slack channel #{name} in workspace {workspace.get('team_name')}")

            return {
                "status": "connected",
                "channel_id": channel_id,
                "channel_name": name,
                "workspace": workspace.get("team_name"),
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to bind agent to Slack channel: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    else:
        # No workspace connected — need OAuth first
        if not get_slack_signing_secret():
            raise HTTPException(status_code=400, detail="Slack integration not configured")

        state = slack_service.encode_oauth_state(link_id, name, str(current_user.id))

        try:
            oauth_url = slack_service.get_oauth_url(state)
            return {"status": "oauth_required", "oauth_url": oauth_url}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@auth_router.delete("/api/agents/{name}/public-links/{link_id}/slack")
async def disconnect_slack(
    name: str,
    link_id: str,
    current_user: User = Depends(get_current_user)
):
    """Disconnect Slack workspace from public link."""
    if not db.can_user_share_agent(current_user.username, name):
        raise HTTPException(status_code=403, detail="Only owners can disconnect Slack")

    link = db.get_public_link(link_id)
    if not link or link["agent_name"] != name:
        raise HTTPException(status_code=404, detail="Public link not found")

    deleted = db.delete_slack_connection_by_link(link_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="No Slack connection found")

    logger.info(f"Slack disconnected from link {link_id} by user {current_user.id}")
    return {"disconnected": True}


@auth_router.put("/api/agents/{name}/public-links/{link_id}/slack")
async def update_slack_connection(
    name: str,
    link_id: str,
    enabled: bool = None,
    current_user: User = Depends(get_current_user)
):
    """Update Slack connection settings (enable/disable)."""
    if not db.can_user_share_agent(current_user.username, name):
        raise HTTPException(status_code=403, detail="Only owners can modify Slack settings")

    link = db.get_public_link(link_id)
    if not link or link["agent_name"] != name:
        raise HTTPException(status_code=404, detail="Public link not found")

    connection = db.get_slack_connection_by_link(link_id)
    if not connection:
        raise HTTPException(status_code=404, detail="No Slack connection found")

    db.update_slack_connection(connection["id"], enabled=enabled)
    return {"updated": True, "enabled": enabled}
