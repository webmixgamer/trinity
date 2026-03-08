"""
Avatar generation and serving router (AVATAR-001).

REST endpoints for AI-generated agent avatars.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from database import db
from dependencies import get_current_user
from models import User
from services.image_generation_service import get_image_generation_service

router = APIRouter(prefix="/api/agents", tags=["avatars"])
logger = logging.getLogger(__name__)

AVATAR_DIR = Path("/data/avatars")


class AvatarGenerateRequest(BaseModel):
    identity_prompt: str


@router.get("/{agent_name}/avatar")
async def get_avatar(agent_name: str):
    """Serve cached avatar PNG for an agent. No auth required — avatars are public assets."""
    avatar_path = AVATAR_DIR / f"{agent_name}.png"
    if not avatar_path.exists():
        raise HTTPException(status_code=404, detail="No avatar found")

    return FileResponse(
        avatar_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/{agent_name}/avatar/identity")
async def get_avatar_identity(
    agent_name: str,
    current_user: User = Depends(get_current_user),
):
    """Return avatar identity prompt and metadata."""
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied")

    identity = db.get_avatar_identity(agent_name)
    avatar_path = AVATAR_DIR / f"{agent_name}.png"

    return {
        "agent_name": agent_name,
        "identity_prompt": identity["identity_prompt"] if identity else None,
        "updated_at": identity["updated_at"] if identity else None,
        "has_avatar": avatar_path.exists(),
    }


@router.post("/{agent_name}/avatar/generate")
async def generate_avatar(
    agent_name: str,
    request: AvatarGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate an avatar from an identity prompt using the image generation service."""
    # Only owner/admin can generate
    owner = db.get_agent_owner(agent_name)
    if not owner:
        raise HTTPException(status_code=404, detail="Agent not found")

    is_admin = current_user.role == "admin"
    is_owner = owner["owner_username"] == current_user.username
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Only the agent owner can generate avatars")

    identity_prompt = request.identity_prompt.strip()
    if not identity_prompt:
        raise HTTPException(status_code=400, detail="identity_prompt cannot be empty")

    if len(identity_prompt) > 500:
        raise HTTPException(status_code=400, detail="identity_prompt must be 500 characters or less")

    service = get_image_generation_service()
    if not service.available:
        raise HTTPException(
            status_code=501,
            detail="Image generation not available: GEMINI_API_KEY not configured",
        )

    result = await service.generate_image(
        prompt=identity_prompt,
        use_case="avatar",
        aspect_ratio="1:1",
        refine_prompt=True,
        agent_name=agent_name,
    )

    if not result.success:
        raise HTTPException(status_code=422, detail=result.error)

    # Save avatar to disk
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    avatar_path = AVATAR_DIR / f"{agent_name}.png"
    avatar_path.write_bytes(result.image_data)

    # Update DB
    now = datetime.now(timezone.utc).isoformat()
    db.set_avatar_identity(agent_name, identity_prompt, now)

    logger.info(f"Generated avatar for agent {agent_name}: {len(result.image_data)} bytes")

    return {
        "agent_name": agent_name,
        "identity_prompt": identity_prompt,
        "refined_prompt": result.refined_prompt,
        "updated_at": now,
    }


@router.delete("/{agent_name}/avatar")
async def delete_avatar(
    agent_name: str,
    current_user: User = Depends(get_current_user),
):
    """Remove avatar file and clear DB fields."""
    owner = db.get_agent_owner(agent_name)
    if not owner:
        raise HTTPException(status_code=404, detail="Agent not found")

    is_admin = current_user.role == "admin"
    is_owner = owner["owner_username"] == current_user.username
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Only the agent owner can remove avatars")

    # Delete file
    avatar_path = AVATAR_DIR / f"{agent_name}.png"
    if avatar_path.exists():
        avatar_path.unlink()

    # Clear DB
    db.clear_avatar_identity(agent_name)

    logger.info(f"Deleted avatar for agent {agent_name}")

    return {"message": f"Avatar removed for {agent_name}"}
