"""
Trinity status API endpoints.

NOTE: The inject and reset endpoints have been removed (Issue #136).
Platform instructions are now injected at runtime via --append-system-prompt
on every Claude Code invocation. No file-based injection needed.
"""
import logging
from pathlib import Path

from fastapi import APIRouter

from ..models import TrinityStatusResponse
from ..config import TRINITY_META_PROMPT_DIR, WORKSPACE_DIR

logger = logging.getLogger(__name__)
router = APIRouter()


def check_trinity_status() -> dict:
    """Check Trinity platform integration status."""
    workspace = WORKSPACE_DIR

    files = {
        ".trinity/prompt.md": (workspace / ".trinity" / "prompt.md").exists(),
    }

    directories = {
        ".trinity": (workspace / ".trinity").exists(),
    }

    return {
        "meta_prompt_mounted": TRINITY_META_PROMPT_DIR.exists(),
        "files": files,
        "directories": directories,
        "claude_md_has_trinity_section": False,  # No longer file-based
        "injected": True,  # Always true — injection is now per-request via --append-system-prompt
    }


@router.get("/api/trinity/status", response_model=TrinityStatusResponse)
async def get_trinity_status():
    """Check Trinity platform integration status."""
    status = check_trinity_status()
    return TrinityStatusResponse(**status)
