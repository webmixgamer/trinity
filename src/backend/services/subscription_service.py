"""
Subscription Service (SUB-001)

Handles injection of Claude Max/Pro subscription credentials into agents
and detection of authentication mode.

IMPORTANT: Claude Code prioritizes ANTHROPIC_API_KEY env var over OAuth
credentials in ~/.claude/.credentials.json. When a subscription is assigned,
the ANTHROPIC_API_KEY must be removed from the container environment so
Claude Code falls through to the OAuth token. The lifecycle and helpers
modules handle this by omitting the env var during container creation/recreation.
"""

import json
import logging
import asyncio
import httpx
from typing import Optional

from database import db
from db_models import AgentAuthStatus
from services.docker_service import get_agent_container, get_agent_status_from_container

logger = logging.getLogger(__name__)


async def inject_subscription_to_agent(
    agent_name: str,
    subscription_id: str,
    max_retries: int = 5,
    retry_delay: float = 2.0
) -> dict:
    """
    Inject subscription credentials into a running agent.

    Decrypts the subscription credentials and writes them to the agent's
    ~/.claude/.credentials.json file via the agent's internal API.

    Args:
        agent_name: Name of the agent
        subscription_id: ID of the subscription to inject
        max_retries: Number of connection retries
        retry_delay: Seconds between retries

    Returns:
        dict with injection status
    """
    # Get the decrypted credentials
    credentials_json = db.get_subscription_credentials(subscription_id)
    if not credentials_json:
        return {
            "status": "failed",
            "error": "Subscription credentials not found or decryption failed"
        }

    # Check if agent is running
    container = get_agent_container(agent_name)
    if not container:
        return {
            "status": "skipped",
            "reason": "agent_not_found"
        }

    agent_status = get_agent_status_from_container(container)
    if agent_status.status != "running":
        return {
            "status": "skipped",
            "reason": "agent_not_running"
        }

    # Inject credentials via agent API
    last_error = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                # Write to ~/.claude/.credentials.json
                response = await client.post(
                    f"http://agent-{agent_name}:8000/api/credentials/inject",
                    json={
                        "files": {
                            ".claude/.credentials.json": credentials_json
                        }
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"Injected subscription credentials into agent {agent_name}"
                    )
                    return {
                        "status": "success",
                        "files_written": result.get("files_written", [".claude/.credentials.json"])
                    }
                else:
                    last_error = f"Agent returned status {response.status_code}"

        except httpx.RequestError as e:
            last_error = str(e)
            logger.warning(
                f"Subscription injection attempt {attempt + 1} failed for {agent_name}: {last_error}"
            )

        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)

    logger.error(
        f"Failed to inject subscription into agent {agent_name} after {max_retries} attempts: {last_error}"
    )
    return {
        "status": "failed",
        "error": last_error
    }


async def inject_subscription_on_start(agent_name: str) -> dict:
    """
    Inject subscription credentials on agent startup if assigned.

    Called from lifecycle.start_agent_internal() after other injections.

    Args:
        agent_name: Name of the agent

    Returns:
        dict with injection status
    """
    # Check if agent has a subscription assigned
    subscription_id = db.get_agent_subscription_id(agent_name)
    if not subscription_id:
        return {
            "status": "skipped",
            "reason": "no_subscription_assigned"
        }

    # Get subscription info for logging
    subscription = db.get_subscription(subscription_id)
    if not subscription:
        logger.warning(
            f"Agent {agent_name} has subscription_id {subscription_id} but subscription not found"
        )
        return {
            "status": "failed",
            "error": "assigned_subscription_not_found"
        }

    logger.info(
        f"Injecting subscription '{subscription.name}' into agent {agent_name} on startup"
    )

    return await inject_subscription_to_agent(agent_name, subscription_id)


async def get_agent_auth_mode(agent_name: str) -> AgentAuthStatus:
    """
    Detect the authentication mode for an agent.

    Checks:
    1. If agent has a subscription assigned (uses subscription)
    2. If agent has use_platform_api_key enabled (uses API key)
    3. Otherwise not_configured

    For running agents, also checks actual file presence via agent API.

    Args:
        agent_name: Name of the agent

    Returns:
        AgentAuthStatus with detected mode
    """
    # Check for subscription assignment
    subscription = db.get_agent_subscription(agent_name)
    has_subscription = subscription is not None

    # Check for platform API key setting
    has_api_key = db.get_use_platform_api_key(agent_name) or False

    # Determine auth mode
    if has_subscription:
        auth_mode = "subscription"
    elif has_api_key:
        auth_mode = "api_key"
    else:
        auth_mode = "not_configured"

    # For running agents, verify actual credential presence
    container = get_agent_container(agent_name)
    if container:
        agent_status = get_agent_status_from_container(container)
        if agent_status.status == "running":
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"http://agent-{agent_name}:8000/api/credentials/status",
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        status = response.json()
                        files = status.get("files", {})

                        # Check for .credentials.json (subscription auth)
                        has_credentials_file = files.get(".claude/.credentials.json", {}).get("exists", False)

                        # If we think we have subscription but file doesn't exist, it may not be injected yet
                        if auth_mode == "subscription" and not has_credentials_file:
                            logger.debug(
                                f"Agent {agent_name} has subscription assigned but .credentials.json not present"
                            )

            except Exception as e:
                logger.debug(f"Could not verify credentials for agent {agent_name}: {e}")

    return AgentAuthStatus(
        agent_name=agent_name,
        auth_mode=auth_mode,
        subscription_name=subscription.name if subscription else None,
        subscription_id=subscription.id if subscription else None,
        has_api_key=has_api_key,
    )
