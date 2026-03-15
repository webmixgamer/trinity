"""
Trinity status API endpoints.

NOTE: The inject and reset endpoints have been removed (Issue #136).
Platform instructions are now injected at runtime via --append-system-prompt
on every Claude Code invocation. No file-based injection needed.
"""
import logging

from fastapi import APIRouter

from ..models import TrinityStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/trinity/status", response_model=TrinityStatusResponse)
async def get_trinity_status():
    """Check Trinity platform integration status."""
    return TrinityStatusResponse(
        injected=True,  # Always true — injection is per-request via --append-system-prompt
    )
