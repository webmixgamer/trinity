"""
Git synchronization routes for GitHub-native agents (Phase 7).

Provides API endpoints for:
- Getting git status
- Syncing changes to GitHub
- Viewing commit history
- Pulling from GitHub
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from models import User
from database import db
from dependencies import get_current_user
from services.audit_service import log_audit_event
from services import git_service

router = APIRouter(prefix="/api/agents", tags=["git"])


class GitSyncRequest(BaseModel):
    """Request body for git sync operation."""
    message: Optional[str] = None  # Custom commit message
    paths: Optional[List[str]] = None  # Specific paths to sync


@router.get("/{agent_name}/git/status")
async def get_git_status(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get git status for an agent.

    Returns:
    - git_enabled: Whether git sync is enabled
    - branch: Current branch name
    - remote_url: GitHub repository URL
    - last_commit: Last commit info
    - changes: List of modified/untracked files
    - sync_status: "up_to_date" or "pending_sync"
    """
    # Check access
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied")

    # Get database config
    git_config = git_service.get_agent_git_config(agent_name)

    # Get live status from agent
    status = await git_service.get_git_status(agent_name)

    if not status:
        # Agent not running or git not enabled
        if git_config:
            return {
                "git_enabled": True,
                "agent_running": False,
                "message": "Agent must be running to get git status",
                "config": {
                    "github_repo": git_config.github_repo,
                    "working_branch": git_config.working_branch,
                    "last_sync_at": git_config.last_sync_at.isoformat() if git_config.last_sync_at else None,
                    "last_commit_sha": git_config.last_commit_sha
                }
            }
        return {
            "git_enabled": False,
            "message": "Git sync not enabled for this agent"
        }

    # Merge with database info
    if git_config:
        status["db_config"] = {
            "last_sync_at": git_config.last_sync_at.isoformat() if git_config.last_sync_at else None,
            "last_commit_sha": git_config.last_commit_sha,
            "sync_enabled": git_config.sync_enabled
        }

    return status


@router.post("/{agent_name}/git/sync")
async def sync_to_github(
    agent_name: str,
    request: Request,
    body: GitSyncRequest = GitSyncRequest(),
    current_user: User = Depends(get_current_user)
):
    """
    Sync agent changes to GitHub.

    Stages all changes, creates a commit, and pushes to the working branch.

    Request body (optional):
    - message: Custom commit message
    - paths: Specific paths to sync (default: all changes)

    Returns:
    - success: Whether sync succeeded
    - commit_sha: SHA of the created commit
    - files_changed: Number of files changed
    - branch: Branch that was pushed to
    """
    # Import here to avoid circular imports
    from services.docker_service import get_agent_container

    # Check if agent exists first
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check access (owners and admins only)
    if not db.can_user_share_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Only agent owners can sync to GitHub")

    result = await git_service.sync_to_github(
        agent_name=agent_name,
        message=body.message,
        paths=body.paths
    )

    # Log the sync operation
    await log_audit_event(
        event_type="git_operation",
        action="sync",
        user_id=current_user.username,
        agent_name=agent_name,
        ip_address=request.client.host if request.client else None,
        result="success" if result.success else "failed",
        severity="info" if result.success else "warning",
        details={
            "commit_sha": result.commit_sha,
            "files_changed": result.files_changed,
            "message": result.message
        }
    )

    if not result.success:
        # Return 400 for configuration issues, not 500
        raise HTTPException(status_code=400, detail=result.message)

    return {
        "success": result.success,
        "commit_sha": result.commit_sha,
        "files_changed": result.files_changed,
        "branch": result.branch,
        "message": result.message,
        "sync_time": result.sync_time.isoformat() if result.sync_time else None
    }


@router.get("/{agent_name}/git/log")
async def get_git_log(
    agent_name: str,
    request: Request,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """
    Get recent git commits for an agent.

    Returns list of commits with:
    - sha: Full commit SHA
    - short_sha: Abbreviated SHA
    - message: Commit message
    - author: Commit author
    - date: Commit date
    """
    # Check access
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied")

    log = await git_service.get_git_log(agent_name, limit=limit)

    if log is None:
        raise HTTPException(
            status_code=400,
            detail="Agent must be running with git enabled to view log"
        )

    return log


@router.post("/{agent_name}/git/pull")
async def pull_from_github(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Pull latest changes from GitHub to the agent.

    Warning: This may cause merge conflicts if there are local changes.
    Consider syncing first.
    """
    # Import here to avoid circular imports
    from services.docker_service import get_agent_container

    # Check if agent exists first
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check access (owners and admins only)
    if not db.can_user_share_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Only agent owners can pull from GitHub")

    result = await git_service.pull_from_github(agent_name)

    # Log the pull operation
    await log_audit_event(
        event_type="git_operation",
        action="pull",
        user_id=current_user.username,
        agent_name=agent_name,
        ip_address=request.client.host if request.client else None,
        result="success" if result.get("success") else "failed",
        severity="info" if result.get("success") else "warning",
        details={"message": result.get("message")}
    )

    if not result.get("success"):
        # Return 400 for configuration issues, not 500
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result


@router.get("/{agent_name}/git/config")
async def get_git_config(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get git configuration for an agent from the database.

    Returns the stored configuration including:
    - github_repo: Repository name
    - working_branch: Branch name
    - instance_id: Unique instance identifier
    - last_sync_at: Last sync timestamp
    - sync_enabled: Whether sync is enabled
    """
    # Check access
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied")

    config = git_service.get_agent_git_config(agent_name)

    if not config:
        return {
            "git_enabled": False,
            "message": "Git sync not configured for this agent"
        }

    return {
        "git_enabled": True,
        "github_repo": config.github_repo,
        "working_branch": config.working_branch,
        "instance_id": config.instance_id,
        "created_at": config.created_at.isoformat(),
        "last_sync_at": config.last_sync_at.isoformat() if config.last_sync_at else None,
        "last_commit_sha": config.last_commit_sha,
        "sync_enabled": config.sync_enabled
    }
