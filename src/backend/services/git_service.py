"""
Git synchronization service for GitHub-native agents (Phase 7).

Handles:
- Creating working branches for new agents
- Syncing agent changes to GitHub
- Managing git configuration in the database
"""
import httpx
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from database import db, AgentGitConfig, GitSyncResult
from services.docker_service import get_agent_container


def generate_instance_id() -> str:
    """Generate a unique instance ID for an agent."""
    return uuid.uuid4().hex[:8]


def generate_working_branch(agent_name: str, instance_id: str) -> str:
    """Generate a working branch name for an agent instance."""
    return f"trinity/{agent_name}/{instance_id}"


async def create_git_config_for_agent(
    agent_name: str,
    github_repo: str,
    instance_id: Optional[str] = None
) -> AgentGitConfig:
    """
    Create git configuration for a new agent.

    Args:
        agent_name: Name of the agent
        github_repo: GitHub repository (e.g., "Abilityai/agent-ruby")
        instance_id: Optional instance ID (generated if not provided)

    Returns:
        AgentGitConfig with the configuration
    """
    if not instance_id:
        instance_id = generate_instance_id()

    working_branch = generate_working_branch(agent_name, instance_id)

    # Create the database record
    config = db.create_git_config(
        agent_name=agent_name,
        github_repo=github_repo,
        working_branch=working_branch,
        instance_id=instance_id
    )

    return config


async def get_git_status(agent_name: str) -> Optional[Dict[str, Any]]:
    """
    Get git status for an agent by calling the agent's internal API.

    Returns git status including branch, changes, and sync state.
    """
    container = get_agent_container(agent_name)
    if not container or container.status != "running":
        return None

    try:
        # Call the agent's internal git status endpoint
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"http://agent-{agent_name}:8000/api/git/status"
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception as e:
        print(f"Error getting git status for {agent_name}: {e}")
        return None


async def sync_to_github(
    agent_name: str,
    message: Optional[str] = None,
    paths: Optional[list] = None
) -> GitSyncResult:
    """
    Sync agent changes to GitHub.

    Calls the agent's internal sync endpoint to stage, commit, and push changes.

    Args:
        agent_name: Name of the agent
        message: Optional custom commit message
        paths: Optional specific paths to sync (default: all)

    Returns:
        GitSyncResult with sync outcome
    """
    container = get_agent_container(agent_name)
    if not container:
        return GitSyncResult(
            success=False,
            message="Agent not found"
        )

    if container.status != "running":
        return GitSyncResult(
            success=False,
            message="Agent must be running to sync"
        )

    try:
        # Call the agent's internal sync endpoint
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {}
            if message:
                payload["message"] = message
            if paths:
                payload["paths"] = paths

            response = await client.post(
                f"http://agent-{agent_name}:8000/api/git/sync",
                json=payload
            )

            if response.status_code == 200:
                data = response.json()

                # Update database with sync result
                if data.get("commit_sha"):
                    db.update_git_sync(agent_name, data["commit_sha"])

                return GitSyncResult(
                    success=data.get("success", False),
                    commit_sha=data.get("commit_sha"),
                    message=data.get("message", "Sync completed"),
                    files_changed=data.get("files_changed", 0),
                    branch=data.get("branch"),
                    sync_time=datetime.fromisoformat(data["sync_time"]) if data.get("sync_time") else datetime.utcnow()
                )
            else:
                error_detail = response.json().get("detail", "Sync failed")
                return GitSyncResult(
                    success=False,
                    message=f"Sync failed: {error_detail}"
                )
    except Exception as e:
        return GitSyncResult(
            success=False,
            message=f"Sync error: {str(e)}"
        )


async def get_git_log(agent_name: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """
    Get recent git commits for an agent.

    Returns list of commits with SHA, message, author, and date.
    """
    container = get_agent_container(agent_name)
    if not container or container.status != "running":
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"http://agent-{agent_name}:8000/api/git/log",
                params={"limit": limit}
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception as e:
        print(f"Error getting git log for {agent_name}: {e}")
        return None


async def pull_from_github(agent_name: str) -> Dict[str, Any]:
    """
    Pull latest changes from GitHub to the agent.

    Use with caution - may cause merge conflicts.
    """
    container = get_agent_container(agent_name)
    if not container:
        return {"success": False, "message": "Agent not found"}

    if container.status != "running":
        return {"success": False, "message": "Agent must be running to pull"}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"http://agent-{agent_name}:8000/api/git/pull"
            )

            if response.status_code == 200:
                return response.json()
            else:
                error_detail = response.json().get("detail", "Pull failed")
                return {"success": False, "message": f"Pull failed: {error_detail}"}
    except Exception as e:
        return {"success": False, "message": f"Pull error: {str(e)}"}


def get_agent_git_config(agent_name: str) -> Optional[AgentGitConfig]:
    """Get git configuration for an agent from the database."""
    return db.get_git_config(agent_name)


def delete_agent_git_config(agent_name: str) -> bool:
    """Delete git configuration when an agent is deleted."""
    return db.delete_git_config(agent_name)
