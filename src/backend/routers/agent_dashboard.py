"""
Agent Dashboard routes.

Provides endpoint for fetching agent dashboard configuration.
Uses /api/agent-dashboard prefix to avoid confusion with main dashboard.
"""
import logging
from fastapi import APIRouter, Depends

from models import User
from dependencies import get_current_user
from services.agent_service.dashboard import get_agent_dashboard_logic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent-dashboard", tags=["agent-dashboard"])


@router.get("/{name}")
async def get_agent_dashboard(
    name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get agent dashboard configuration.

    Returns dashboard configuration from the agent's dashboard.yaml file.
    The agent controls both layout and data through a single YAML file.

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
    """
    return await get_agent_dashboard_logic(name, current_user)
