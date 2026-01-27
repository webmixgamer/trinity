"""
Agent management routes for the Trinity backend.

This module provides a thin router layer over the agent service.
All business logic has been moved to services/agent_service/.
"""
import os
import json
import docker
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, WebSocket
from pydantic import BaseModel

from models import AgentConfig, AgentStatus, User, DeployLocalRequest
from database import db
from dependencies import get_current_user, decode_token, AuthorizedAgentByName, CurrentUser
from services.docker_service import (
    docker_client,
    get_agent_container,
    get_agent_by_name,
)
from services.scheduler_service import scheduler_service
from services import git_service
from credentials import CredentialManager

# Import service layer functions
from services.agent_service import (
    # Helpers - re-exported for external modules
    get_accessible_agents,
    get_agents_by_prefix,
    get_next_version_name,
    get_latest_version,
    check_shared_folder_mounts_match,
    check_api_key_env_matches,
    # Lifecycle
    inject_trinity_meta_prompt,
    start_agent_internal,
    recreate_container_with_updated_config,
    # CRUD
    create_agent_internal as _create_agent_internal,
    # Deploy
    deploy_local_agent_logic,
    # Terminal
    TerminalSessionManager,
    # Permissions
    get_agent_permissions_logic,
    set_agent_permissions_logic,
    add_agent_permission_logic,
    remove_agent_permission_logic,
    # Folders
    get_agent_folders_logic,
    update_agent_folders_logic,
    get_available_shared_folders_logic,
    get_folder_consumers_logic,
    # Files
    list_agent_files_logic,
    download_agent_file_logic,
    delete_agent_file_logic,
    preview_agent_file_logic,
    update_agent_file_logic,
    # Queue
    get_agent_queue_status_logic,
    clear_agent_queue_logic,
    force_release_agent_logic,
    # Metrics
    get_agent_metrics_logic,
    # Stats
    get_agents_context_stats_logic,
    get_agent_stats_logic,
    # API Key
    get_agent_api_key_setting_logic,
    update_agent_api_key_setting_logic,
    # Autonomy
    get_autonomy_status_logic,
    set_autonomy_status_logic,
    get_all_autonomy_status_logic,
)

router = APIRouter(prefix="/api/agents", tags=["agents"])

# Initialize credential manager
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
credential_manager = CredentialManager(REDIS_URL)

# WebSocket manager will be injected from main.py
manager = None

# Logger for terminal sessions
logger = logging.getLogger(__name__)

# Terminal session manager
_terminal_manager = TerminalSessionManager()


def set_websocket_manager(ws_manager):
    """Set the WebSocket manager for broadcasting events."""
    global manager
    manager = ws_manager


# ============================================================================
# Facade function for create_agent_internal
# Passes module-level dependencies to service layer
# ============================================================================

async def create_agent_internal(
    config: AgentConfig,
    current_user: User,
    request: Request,
    skip_name_sanitization: bool = False
) -> AgentStatus:
    """
    Internal function to create an agent.

    Facade that delegates to service layer with module-level dependencies.
    """
    return await _create_agent_internal(
        config=config,
        current_user=current_user,
        request=request,
        skip_name_sanitization=skip_name_sanitization,
        credential_manager=credential_manager,
        ws_manager=manager
    )


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.get("")
async def list_agents_endpoint(request: Request, current_user: User = Depends(get_current_user)):
    """List all agents accessible to the current user."""
    return get_accessible_agents(current_user)


@router.get("/context-stats")
async def get_agents_context_stats(current_user: User = Depends(get_current_user)):
    """Get context window stats and activity state for all accessible agents."""
    return await get_agents_context_stats_logic(current_user)


@router.get("/execution-stats")
async def get_agents_execution_stats(
    hours: int = 24,
    current_user: User = Depends(get_current_user)
):
    """Get execution statistics for all accessible agents.

    Returns task counts, success rates, costs, and last execution times
    for all agents the user can access within the specified time window.
    """
    # Get all stats from database
    all_stats = db.get_all_agents_execution_stats(hours=hours)

    # Filter to only agents the user can access
    accessible_agents = {a['name'] for a in get_accessible_agents(current_user)}

    filtered_stats = [
        stat for stat in all_stats
        if stat["name"] in accessible_agents
    ]

    return {"agents": filtered_stats}


@router.get("/autonomy-status")
async def get_all_autonomy_status(
    current_user: User = Depends(get_current_user)
):
    """Get autonomy status for all accessible agents (for dashboard display)."""
    return await get_all_autonomy_status_logic(current_user)


@router.get("/{agent_name}")
async def get_agent_endpoint(agent_name: AuthorizedAgentByName, request: Request, current_user: CurrentUser):
    """Get details of a specific agent."""
    agent = get_agent_by_name(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent_dict = agent.dict() if hasattr(agent, 'dict') else dict(agent)
    user_data = db.get_user_by_username(current_user.username)
    is_admin = user_data and user_data["role"] == "admin"

    owner = db.get_agent_owner(agent_name)
    agent_dict["owner"] = owner["owner_username"] if owner else None
    agent_dict["is_owner"] = owner and owner["owner_username"] == current_user.username
    agent_dict["is_shared"] = not agent_dict["is_owner"] and not is_admin and \
                               db.is_agent_shared_with_user(agent_name, current_user.username)
    agent_dict["is_system"] = owner.get("is_system", False) if owner else False
    agent_dict["can_share"] = db.can_user_share_agent(current_user.username, agent_name)
    agent_dict["can_delete"] = db.can_user_delete_agent(current_user.username, agent_name)
    agent_dict["autonomy_enabled"] = db.get_autonomy_enabled(agent_name)

    if agent_dict["can_share"]:
        shares = db.get_agent_shares(agent_name)
        agent_dict["shares"] = [s.dict() for s in shares]
    else:
        agent_dict["shares"] = []

    return agent_dict


@router.post("")
async def create_agent_endpoint(config: AgentConfig, request: Request, current_user: User = Depends(get_current_user)):
    """Create a new agent."""
    return await create_agent_internal(config, current_user, request, skip_name_sanitization=False)


@router.post("/deploy-local")
async def deploy_local_agent(
    body: DeployLocalRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Deploy a Trinity-compatible local agent."""
    return await deploy_local_agent_logic(
        body=body,
        current_user=current_user,
        request=request,
        create_agent_fn=create_agent_internal,
        credential_manager=credential_manager
    )


@router.delete("/{agent_name}")
async def delete_agent_endpoint(agent_name: str, request: Request, current_user: User = Depends(get_current_user)):
    """Delete an agent."""
    # Check for system agent first - no one can delete these
    if db.is_system_agent(agent_name):
        raise HTTPException(
            status_code=403,
            detail="System agents cannot be deleted. Use re-initialization to reset to clean state."
        )

    if not db.can_user_delete_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to delete this agent")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        container.stop()
        container.remove()
    except Exception as e:
        logger.warning(f"Error stopping/removing container: {e}")

    # Delete per-agent persistent volume
    try:
        agent_volume_name = f"agent-{agent_name}-workspace"
        volume = docker_client.volumes.get(agent_volume_name)
        volume.remove()
    except docker.errors.NotFound:
        pass
    except Exception as e:
        logger.warning(f"Failed to delete workspace volume for agent {agent_name}: {e}")

    # Delete all schedules for this agent
    schedules = db.list_agent_schedules(agent_name)
    for schedule in schedules:
        scheduler_service.remove_schedule(schedule.id)
    db.delete_agent_schedules(agent_name)

    # Delete git config if exists
    git_service.delete_agent_git_config(agent_name)

    # Delete agent's MCP API key
    try:
        db.delete_agent_mcp_api_key(agent_name)
    except Exception as e:
        logger.warning(f"Failed to delete MCP API key for agent {agent_name}: {e}")

    # Delete agent permissions
    try:
        db.delete_agent_permissions(agent_name)
    except Exception as e:
        logger.warning(f"Failed to delete permissions for agent {agent_name}: {e}")

    # Delete agent skills
    try:
        db.delete_agent_skills(agent_name)
    except Exception as e:
        logger.warning(f"Failed to delete skills for agent {agent_name}: {e}")

    # Delete shared folder config and shared volume
    try:
        db.delete_shared_folder_config(agent_name)
        shared_volume_name = db.get_shared_volume_name(agent_name)
        try:
            shared_volume = docker_client.volumes.get(shared_volume_name)
            shared_volume.remove()
        except docker.errors.NotFound:
            pass
    except Exception as e:
        logger.warning(f"Failed to delete shared folder config for agent {agent_name}: {e}")

    # Delete credential assignments for this agent
    try:
        credential_manager.cleanup_agent_credentials(agent_name)
    except Exception as e:
        logger.warning(f"Failed to delete credential assignments for agent {agent_name}: {e}")

    db.delete_agent_ownership(agent_name)

    if manager:
        await manager.broadcast(json.dumps({
            "event": "agent_deleted",
            "data": {"name": agent_name}
        }))

    return {"message": f"Agent {agent_name} deleted"}


# ============================================================================
# Lifecycle Endpoints
# ============================================================================

@router.post("/{agent_name}/start")
async def start_agent_endpoint(agent_name: AuthorizedAgentByName, request: Request, current_user: CurrentUser):
    """Start an agent."""
    try:
        result = await start_agent_internal(agent_name)
        trinity_status = result.get("trinity_injection", "unknown")
        credentials_status = result.get("credentials_injection", "unknown")
        credentials_result = result.get("credentials_result", {})

        if manager:
            await manager.broadcast(json.dumps({
                "event": "agent_started",
                "data": {"name": agent_name, "trinity_injection": trinity_status, "credentials_injection": credentials_status}
            }))

        return {
            "message": f"Agent {agent_name} started",
            "trinity_injection": trinity_status,
            "credentials_injection": credentials_status,
            "credentials_result": credentials_result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start agent: {str(e)}")


@router.post("/{agent_name}/stop")
async def stop_agent_endpoint(agent_name: AuthorizedAgentByName, request: Request, current_user: CurrentUser):
    """Stop an agent."""
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        container.stop()

        if manager:
            await manager.broadcast(json.dumps({
                "event": "agent_stopped",
                "data": {"name": agent_name}
            }))

        return {"message": f"Agent {agent_name} stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop agent: {str(e)}")


# ============================================================================
# Logs and Stats Endpoints
# ============================================================================

@router.get("/{agent_name}/logs")
async def get_agent_logs_endpoint(
    agent_name: AuthorizedAgentByName,
    request: Request,
    tail: int = 100
):
    """Get agent container logs."""
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        logs = container.logs(tail=tail).decode('utf-8')

        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")


@router.get("/{agent_name}/stats")
async def get_agent_stats_endpoint(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get live container stats (CPU, memory, network) for an agent."""
    return await get_agent_stats_logic(agent_name, current_user)


# ============================================================================
# Queue Endpoints
# ============================================================================

@router.get("/{agent_name}/queue")
async def get_agent_queue_status(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get execution queue status for an agent."""
    return await get_agent_queue_status_logic(agent_name, current_user)


@router.post("/{agent_name}/queue/clear")
async def clear_agent_queue(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """Clear all queued executions for an agent."""
    return await clear_agent_queue_logic(agent_name, current_user)


@router.post("/{agent_name}/queue/release")
async def force_release_agent(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """Force release an agent from its running state."""
    return await force_release_agent_logic(agent_name, current_user)


# ============================================================================
# Info and Files Endpoints
# ============================================================================

@router.get("/{agent_name}/info")
async def get_agent_info_endpoint(
    agent_name: AuthorizedAgentByName,
    request: Request
):
    """Get template info and metadata for an agent."""
    import httpx

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    container.reload()

    if container.status != "running":
        labels = container.labels
        return {
            "has_template": bool(labels.get("trinity.template")),
            "agent_name": agent_name,
            "template_name": labels.get("trinity.template", ""),
            "type": labels.get("trinity.agent-type", ""),
            "resources": {
                "cpu": labels.get("trinity.cpu", ""),
                "memory": labels.get("trinity.memory", "")
            },
            "status": "stopped",
            "message": "Agent is stopped. Start the agent to see full template info."
        }

    try:
        agent_url = f"http://agent-{agent_name}:8000/api/template/info"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(agent_url)
            if response.status_code == 200:
                data = response.json()
                data["status"] = "running"
                return data
            else:
                labels = container.labels
                return {
                    "has_template": bool(labels.get("trinity.template")),
                    "agent_name": agent_name,
                    "template_name": labels.get("trinity.template", ""),
                    "type": labels.get("trinity.agent-type", ""),
                    "resources": {
                        "cpu": labels.get("trinity.cpu", ""),
                        "memory": labels.get("trinity.memory", "")
                    },
                    "status": "running",
                    "message": "Template info endpoint not available in this agent version"
                }
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Agent is starting up, please try again")
    except Exception as e:
        labels = container.labels
        return {
            "has_template": bool(labels.get("trinity.template")),
            "agent_name": agent_name,
            "template_name": labels.get("trinity.template", ""),
            "type": labels.get("trinity.agent-type", ""),
            "resources": {
                "cpu": labels.get("trinity.cpu", ""),
                "memory": labels.get("trinity.memory", "")
            },
            "status": "running",
            "message": f"Could not fetch template info: {str(e)}"
        }


@router.get("/{agent_name}/files")
async def list_agent_files_endpoint(
    agent_name: str,
    request: Request,
    path: str = "/home/developer",
    show_hidden: bool = False,
    current_user: User = Depends(get_current_user)
):
    """List files in the agent's workspace directory.

    Args:
        path: Directory path to list (default: /home/developer)
        show_hidden: If True, include hidden files (starting with .)
    """
    return await list_agent_files_logic(agent_name, path, current_user, request, show_hidden)


@router.get("/{agent_name}/files/download")
async def download_agent_file_endpoint(
    agent_name: str,
    request: Request,
    path: str,
    current_user: User = Depends(get_current_user)
):
    """Download a file from the agent's workspace."""
    return await download_agent_file_logic(agent_name, path, current_user, request)


@router.get("/{agent_name}/files/preview")
async def preview_agent_file_endpoint(
    agent_name: str,
    request: Request,
    path: str,
    current_user: User = Depends(get_current_user)
):
    """Get file with proper MIME type for preview (images, video, audio, etc.)."""
    return await preview_agent_file_logic(agent_name, path, current_user, request)


@router.delete("/{agent_name}/files")
async def delete_agent_file_endpoint(
    agent_name: str,
    request: Request,
    path: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a file or directory from the agent's workspace."""
    return await delete_agent_file_logic(agent_name, path, current_user, request)


class FileUpdateRequest(BaseModel):
    """Request body for file updates."""
    content: str


@router.put("/{agent_name}/files")
async def update_agent_file_endpoint(
    agent_name: str,
    request: Request,
    path: str,
    body: FileUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """Update a file's content in the agent's workspace.

    Args:
        path: File path to update
        body: Request body with content
    """
    return await update_agent_file_logic(agent_name, path, body.content, current_user, request)


# ============================================================================
# Activity Stream Endpoints
# ============================================================================

@router.get("/{agent_name}/activities")
async def get_agent_activities(
    agent_name: AuthorizedAgentByName,
    activity_type: Optional[str] = None,
    activity_state: Optional[str] = None,
    limit: int = 100
):
    """Get activity history for a specific agent."""
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    activities = db.get_agent_activities(
        agent_name=agent_name,
        activity_type=activity_type,
        activity_state=activity_state,
        limit=limit
    )

    return {
        "agent_name": agent_name,
        "count": len(activities),
        "activities": activities
    }


@router.get("/activities/timeline")
async def get_activity_timeline(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    activity_types: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get cross-agent activity timeline."""
    types_list = activity_types.split(",") if activity_types else None

    all_activities = db.get_activities_in_range(
        start_time=start_time,
        end_time=end_time,
        activity_types=types_list,
        limit=limit * 2
    )

    filtered_activities = []
    for activity in all_activities:
        agent_name = activity.get("agent_name")
        if db.can_user_access_agent(current_user.username, agent_name):
            filtered_activities.append(activity)
            if len(filtered_activities) >= limit:
                break

    return {
        "count": len(filtered_activities),
        "start_time": start_time,
        "end_time": end_time,
        "activity_types": types_list,
        "activities": filtered_activities  # Frontend expects "activities" (fixed 2026-01-15)
    }


# ============================================================================
# Agent Permissions Endpoints
# ============================================================================

@router.get("/{agent_name}/permissions")
async def get_agent_permissions(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get permissions for an agent."""
    return await get_agent_permissions_logic(agent_name, current_user)


@router.put("/{agent_name}/permissions")
async def set_agent_permissions(
    agent_name: str,
    request: Request,
    body: dict,
    current_user: User = Depends(get_current_user)
):
    """Set permissions for an agent (full replacement)."""
    return await set_agent_permissions_logic(agent_name, body, current_user, request)


@router.post("/{agent_name}/permissions/{target_agent}")
async def add_agent_permission(
    agent_name: str,
    target_agent: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Add permission for an agent to communicate with another agent."""
    return await add_agent_permission_logic(agent_name, target_agent, current_user, request)


@router.delete("/{agent_name}/permissions/{target_agent}")
async def remove_agent_permission(
    agent_name: str,
    target_agent: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Remove permission for an agent to communicate with another agent."""
    return await remove_agent_permission_logic(agent_name, target_agent, current_user, request)


# ============================================================================
# Custom Metrics Endpoints
# ============================================================================

@router.get("/{agent_name}/metrics")
async def get_agent_metrics(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get agent custom metrics."""
    return await get_agent_metrics_logic(agent_name, current_user)


# ============================================================================
# Shared Folders Endpoints
# ============================================================================

@router.get("/{agent_name}/folders")
async def get_agent_folders(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get shared folder configuration for an agent."""
    return await get_agent_folders_logic(agent_name, current_user)


@router.put("/{agent_name}/folders")
async def update_agent_folders(
    agent_name: str,
    request: Request,
    body: dict,
    current_user: User = Depends(get_current_user)
):
    """Update shared folder configuration for an agent."""
    return await update_agent_folders_logic(agent_name, body, current_user, request)


@router.get("/{agent_name}/folders/available")
async def get_available_shared_folders(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get list of shared folders available for this agent to mount."""
    return await get_available_shared_folders_logic(agent_name, current_user)


@router.get("/{agent_name}/folders/consumers")
async def get_folder_consumers(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get list of agents that can consume this agent's shared folder."""
    return await get_folder_consumers_logic(agent_name, current_user)


# ============================================================================
# API Key Settings Endpoints
# ============================================================================

@router.get("/{agent_name}/api-key-setting")
async def get_agent_api_key_setting(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get the API key setting for an agent."""
    return await get_agent_api_key_setting_logic(agent_name, current_user)


@router.put("/{agent_name}/api-key-setting")
async def update_agent_api_key_setting(
    agent_name: str,
    request: Request,
    body: dict,
    current_user: User = Depends(get_current_user)
):
    """Update the API key setting for an agent."""
    return await update_agent_api_key_setting_logic(agent_name, body, current_user, request)


# ============================================================================
# Autonomy Mode Endpoints (per-agent)
# ============================================================================

@router.get("/{agent_name}/autonomy")
async def get_agent_autonomy_status(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get the autonomy status for an agent."""
    return await get_autonomy_status_logic(agent_name, current_user)


@router.put("/{agent_name}/autonomy")
async def set_agent_autonomy_status(
    agent_name: str,
    body: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Set the autonomy status for an agent.

    Body:
    - enabled: True to enable autonomy, False to disable

    When autonomy is enabled, all schedules for the agent are enabled.
    When disabled, all schedules are paused.
    """
    return await set_autonomy_status_logic(agent_name, body, current_user)


# ============================================================================
# Resource Limits Endpoints
# ============================================================================

@router.get("/{agent_name}/resources")
async def get_agent_resources(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the resource limits for an agent.

    Returns:
    - memory: Memory limit (e.g., "4g", "8g", "16g") or null if using template default
    - cpu: CPU limit (e.g., "2", "4", "8") or null if using template default
    - current_memory: Current container memory limit
    - current_cpu: Current container CPU limit
    """
    # Check access
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get DB limits (may be None)
    db_limits = db.get_resource_limits(agent_name)

    # Get current container limits from labels
    labels = container.attrs.get("Config", {}).get("Labels", {})
    current_memory = labels.get("trinity.memory", "4g")
    current_cpu = labels.get("trinity.cpu", "2")

    return {
        "memory": db_limits.get("memory") if db_limits else None,
        "cpu": db_limits.get("cpu") if db_limits else None,
        "current_memory": current_memory,
        "current_cpu": current_cpu
    }


@router.put("/{agent_name}/resources")
async def set_agent_resources(
    agent_name: str,
    body: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Set the resource limits for an agent.

    Body:
    - memory: Memory limit (e.g., "4g", "8g", "16g") or null to use template default
    - cpu: CPU limit (e.g., "2", "4", "8") or null to use template default

    Changes take effect on next agent restart.

    Valid memory values: 1g, 2g, 4g, 8g, 16g, 32g
    Valid CPU values: 1, 2, 4, 8, 16
    """
    # Only owners can change resources
    if not db.can_user_share_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Only owners can change resource limits")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    memory = body.get("memory")
    cpu = body.get("cpu")

    # Validate memory format
    valid_memory = ["1g", "2g", "4g", "8g", "16g", "32g", "64g"]
    if memory and memory not in valid_memory:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid memory value. Must be one of: {', '.join(valid_memory)}"
        )

    # Validate CPU format
    valid_cpu = ["1", "2", "4", "8", "16"]
    if cpu and cpu not in valid_cpu:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CPU value. Must be one of: {', '.join(valid_cpu)}"
        )

    # Update database
    db.set_resource_limits(agent_name, memory=memory, cpu=cpu)

    # Check if restart is needed
    labels = container.attrs.get("Config", {}).get("Labels", {})
    current_memory = labels.get("trinity.memory", "4g")
    current_cpu = labels.get("trinity.cpu", "2")

    restart_needed = (
        (memory and memory != current_memory) or
        (cpu and cpu != current_cpu)
    )

    return {
        "message": "Resource limits updated",
        "memory": memory,
        "cpu": cpu,
        "restart_needed": restart_needed
    }


# ============================================================================
# Full Capabilities Endpoints (Container Security)
# ============================================================================

@router.get("/{agent_name}/capabilities")
async def get_agent_capabilities(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the capabilities setting for an agent.

    Returns:
    - full_capabilities: True if agent has full Docker capabilities (apt-get works)
    - current_full_capabilities: Current container setting

    When full_capabilities=True:
    - Container runs with Docker default capabilities
    - Can install packages with apt-get
    - Can use sudo

    When full_capabilities=False (default):
    - Container runs with restricted capabilities
    - More secure but cannot install packages
    """
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get DB setting
    db_full_caps = db.get_full_capabilities(agent_name)

    # Get current container setting from labels
    labels = container.attrs.get("Config", {}).get("Labels", {})
    current_full_caps = labels.get("trinity.full-capabilities", "false").lower() == "true"

    return {
        "full_capabilities": db_full_caps,
        "current_full_capabilities": current_full_caps
    }


@router.put("/{agent_name}/capabilities")
async def set_agent_capabilities(
    agent_name: str,
    body: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Set the capabilities for an agent.

    Body:
    - full_capabilities: True for full Docker capabilities, False for restricted (secure)

    Note: Agent must be restarted for changes to take effect.
    The container label is updated on restart.
    """
    # Only owners can change capabilities
    if not db.can_user_share_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Only owners can change capabilities")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    full_caps = body.get("full_capabilities")
    if full_caps is None:
        raise HTTPException(status_code=400, detail="full_capabilities is required")

    if not isinstance(full_caps, bool):
        raise HTTPException(status_code=400, detail="full_capabilities must be a boolean")

    # Update database
    db.set_full_capabilities(agent_name, full_caps)

    # Update container label (will be applied on restart/recreate)
    labels = container.attrs.get("Config", {}).get("Labels", {})
    current_full_caps = labels.get("trinity.full-capabilities", "false").lower() == "true"

    restart_needed = full_caps != current_full_caps

    return {
        "message": "Capabilities updated",
        "full_capabilities": full_caps,
        "restart_needed": restart_needed
    }


# ============================================================================
# SSH Access Endpoint
# ============================================================================

class SshAccessRequest(BaseModel):
    """Request body for SSH access."""
    ttl_hours: float = 4.0
    auth_method: str = "key"  # "key" for SSH key, "password" for ephemeral password


@router.post("/{agent_name}/ssh-access")
async def create_ssh_access(
    agent_name: str,
    body: SshAccessRequest = SshAccessRequest(),
    current_user: User = Depends(get_current_user)
):
    """
    Generate ephemeral SSH credentials for direct agent access.

    Supports two authentication methods:
    - "key": Generate ED25519 key pair (save locally, more secure)
    - "password": Generate ephemeral password (one-liner with sshpass)

    Keys/passwords expire automatically after the specified TTL.

    Args:
        agent_name: Name of the agent to access
        body: Request body with ttl_hours (0.1-24 hours, default: 4) and auth_method

    Returns:
        SSH connection details
    """
    from services.ssh_service import get_ssh_service, get_ssh_host, SSH_ACCESS_MAX_TTL_HOURS
    from services.settings_service import get_ops_setting
    import time

    # Check if SSH access is enabled system-wide
    if not get_ops_setting("ssh_access_enabled", as_type=bool):
        raise HTTPException(
            status_code=403,
            detail="SSH access is disabled. Enable it in Settings → Ops Settings → ssh_access_enabled"
        )

    # Check access
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Verify agent is running
    container.reload()
    if container.status != "running":
        raise HTTPException(
            status_code=400,
            detail="Agent must be running to generate SSH access. Start the agent first."
        )

    # Validate TTL
    ttl_hours = body.ttl_hours
    if ttl_hours < 0.1:  # Minimum 6 minutes
        ttl_hours = 0.1
    if ttl_hours > SSH_ACCESS_MAX_TTL_HOURS:
        ttl_hours = SSH_ACCESS_MAX_TTL_HOURS

    # Validate auth method
    auth_method = body.auth_method.lower()
    if auth_method not in ("key", "password"):
        raise HTTPException(status_code=400, detail="auth_method must be 'key' or 'password'")

    # Get SSH port from container labels
    labels = container.attrs.get("Config", {}).get("Labels", {})
    ssh_port = int(labels.get("trinity.ssh-port", "2222"))

    # Get host for SSH connection
    host = get_ssh_host()

    ssh_service = get_ssh_service()

    # Calculate expiry
    from datetime import datetime, timedelta
    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)

    if auth_method == "password":
        # Generate ephemeral password
        password = ssh_service.generate_password()

        # Set password in container
        if not ssh_service.set_container_password(agent_name, password):
            raise HTTPException(
                status_code=500,
                detail="Failed to set SSH password in agent container"
            )

        # Store metadata
        credential_id = f"pwd-{agent_name}-{int(time.time())}"
        ssh_service.store_credential_metadata(
            agent_name=agent_name,
            credential_id=credential_id,
            auth_type="password",
            created_by=current_user.username,
            ttl_hours=ttl_hours
        )

        # Build one-liner command
        ssh_command = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -p {ssh_port} developer@{host}"

        return {
            "status": "success",
            "agent": agent_name,
            "auth_method": "password",
            "connection": {
                "command": ssh_command,
                "host": host,
                "port": ssh_port,
                "user": "developer",
                "password": password
            },
            "expires_at": expires_at.isoformat() + "Z",
            "expires_in_hours": ttl_hours,
            "instructions": [
                "Install sshpass if needed: brew install sshpass (macOS) or apt install sshpass (Linux)",
                f"Connect: {ssh_command}",
                f"Password expires in {ttl_hours} hours"
            ]
        }

    else:
        # Key-based authentication (original behavior)
        keypair = ssh_service.generate_ssh_keypair(agent_name)

        # Inject public key into container
        if not ssh_service.inject_ssh_key(agent_name, keypair["public_key"]):
            raise HTTPException(
                status_code=500,
                detail="Failed to inject SSH key into agent container"
            )

        # Store metadata in Redis with TTL
        ssh_service.store_key_metadata(
            agent_name=agent_name,
            comment=keypair["comment"],
            public_key=keypair["public_key"],
            created_by=current_user.username,
            ttl_hours=ttl_hours
        )

        # Build SSH command
        key_filename = f"~/.trinity/keys/{agent_name}.key"
        ssh_command = f"ssh -p {ssh_port} -i {key_filename} developer@{host}"

        return {
            "status": "success",
            "agent": agent_name,
            "auth_method": "key",
            "connection": {
                "command": ssh_command,
                "host": host,
                "port": ssh_port,
                "user": "developer"
            },
            "private_key": keypair["private_key"],
            "expires_at": expires_at.isoformat() + "Z",
            "expires_in_hours": ttl_hours,
            "instructions": [
                f"Save the private key to a file: {key_filename}",
                f"Set permissions: chmod 600 {key_filename}",
                f"Connect: {ssh_command}",
                f"Key expires in {ttl_hours} hours"
            ]
        }


# ============================================================================
# Terminal WebSocket Endpoint
# ============================================================================

@router.websocket("/{agent_name}/terminal")
async def agent_terminal(
    websocket: WebSocket,
    agent_name: str,
    mode: str = Query(default="claude"),
    model: str = Query(default=None)
):
    """Interactive terminal WebSocket for any agent."""
    await _terminal_manager.handle_terminal_session(
        websocket=websocket,
        agent_name=agent_name,
        mode=mode,
        decode_token_fn=decode_token,
        model=model
    )
