"""
Agent Service Dashboard - Dashboard configuration operations.

Handles fetching dashboard configuration from agents.
"""
import logging

import httpx
from fastapi import HTTPException

from models import User
from database import db
from services.docker_service import get_agent_container

logger = logging.getLogger(__name__)


async def get_agent_dashboard_logic(
    agent_name: str,
    current_user: User
) -> dict:
    """
    Get agent dashboard configuration.

    Returns dashboard configuration from agent's dashboard.yaml file.
    The agent controls both layout and data via a single YAML file.

    Widget types supported:
    - metric: Single numeric value with optional trend
    - status: Colored status badge
    - progress: Progress bar (0-100)
    - text: Simple text
    - markdown: Rich text with markdown rendering
    - table: Tabular data
    - list: Bullet or numbered list
    - link: Clickable link or button
    - image: Image display
    - divider: Horizontal separator
    - spacer: Vertical space

    Returns:
    - agent_name: Name of the agent
    - has_dashboard: Whether agent has a dashboard.yaml file
    - config: Dashboard configuration (title, description, refresh, sections)
    - last_modified: File modification timestamp
    - status: Agent status (running/stopped)
    - error: Error message if parsing failed
    """
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to access this agent")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    container.reload()

    # If agent is not running, return basic info
    if container.status != "running":
        return {
            "agent_name": agent_name,
            "has_dashboard": False,
            "config": None,
            "last_modified": None,
            "status": "stopped",
            "error": "Agent must be running to read dashboard"
        }

    # Agent is running - fetch dashboard from agent's internal API
    try:
        agent_url = f"http://agent-{agent_name}:8000/api/dashboard"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(agent_url)
            if response.status_code == 200:
                data = response.json()
                data["agent_name"] = agent_name
                data["status"] = "running"
                return data
            else:
                return {
                    "agent_name": agent_name,
                    "has_dashboard": False,
                    "config": None,
                    "last_modified": None,
                    "status": "running",
                    "error": f"Failed to fetch dashboard: HTTP {response.status_code}"
                }
    except httpx.TimeoutException:
        return {
            "agent_name": agent_name,
            "has_dashboard": False,
            "config": None,
            "last_modified": None,
            "status": "running",
            "error": "Agent is starting up, please try again"
        }
    except Exception as e:
        logger.error(f"Failed to fetch dashboard for agent {agent_name}: {e}")
        return {
            "agent_name": agent_name,
            "has_dashboard": False,
            "config": None,
            "last_modified": None,
            "status": "running",
            "error": f"Failed to read dashboard: {str(e)}"
        }
