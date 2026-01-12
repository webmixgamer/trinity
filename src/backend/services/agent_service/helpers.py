"""
Agent Service Helpers - Shared utility functions.

Contains functions used across multiple agent operations.
"""
import logging
import asyncio
from typing import Optional, List, Callable, Any

import httpx

from models import User, AgentStatus
from database import db
from services.docker_service import (
    docker_client,
    list_all_agents,
    get_agent_container,
)
from services.settings_service import get_anthropic_api_key, get_agent_full_capabilities
from utils.helpers import sanitize_agent_name

logger = logging.getLogger(__name__)


async def agent_http_request(
    agent_name: str,
    method: str,
    path: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    timeout: float = 30.0,
    **kwargs
) -> httpx.Response:
    """
    Make an HTTP request to an agent's internal server with retry logic.

    This handles the common case where an agent container is running but
    its internal HTTP server is not yet ready to accept connections.

    Args:
        agent_name: Name of the agent
        method: HTTP method (GET, POST, etc.)
        path: URL path (e.g., /api/files)
        max_retries: Number of retry attempts
        retry_delay: Seconds between retries (doubles each retry)
        timeout: Request timeout in seconds
        **kwargs: Additional arguments passed to httpx request

    Returns:
        httpx.Response object

    Raises:
        httpx.ConnectError: If all connection attempts fail
        httpx.TimeoutException: If request times out
    """
    agent_url = f"http://agent-{agent_name}:8000{path}"

    last_error = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, agent_url, **kwargs)
                return response
        except httpx.ConnectError as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.debug(
                    f"Agent {agent_name} connection failed (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.warning(
                    f"Agent {agent_name} connection failed after {max_retries} attempts: {e}"
                )

    # All retries exhausted
    raise last_error or httpx.ConnectError(f"Failed to connect to agent {agent_name}")


def get_accessible_agents(current_user: User) -> list:
    """
    Get list of all agents accessible to the current user.

    Helper function for use by other routers that need agent access control.
    Returns list of agent dictionaries with ownership metadata.
    """
    all_agents = list_all_agents()
    user_data = db.get_user_by_username(current_user.username)
    is_admin = user_data and user_data["role"] == "admin"

    accessible_agents = []
    for agent in all_agents:
        agent_dict = agent.dict() if hasattr(agent, 'dict') else dict(agent)
        agent_name = agent_dict.get("name")

        if not db.can_user_access_agent(current_user.username, agent_name):
            continue

        owner = db.get_agent_owner(agent_name)
        agent_dict["owner"] = owner["owner_username"] if owner else None
        agent_dict["is_owner"] = owner and owner["owner_username"] == current_user.username
        agent_dict["is_shared"] = not agent_dict["is_owner"] and not is_admin and \
                                   db.is_agent_shared_with_user(agent_name, current_user.username)
        # Add is_system flag for system agents (deletion-protected)
        agent_dict["is_system"] = owner.get("is_system", False) if owner else False

        # Add autonomy_enabled flag for autonomous scheduled operations
        agent_dict["autonomy_enabled"] = db.get_autonomy_enabled(agent_name)

        # Add GitHub repo info if agent was created from GitHub template
        git_config = db.get_git_config(agent_name)
        if git_config:
            agent_dict["github_repo"] = git_config.github_repo
        else:
            agent_dict["github_repo"] = None

        # Add resource limits for dashboard display
        resource_limits = db.get_resource_limits(agent_name)
        agent_dict["memory_limit"] = resource_limits.get("memory_limit") if resource_limits else None
        agent_dict["cpu_limit"] = resource_limits.get("cpu_limit") if resource_limits else None

        accessible_agents.append(agent_dict)

    return accessible_agents


def sanitize_and_validate_name(name: str) -> str:
    """
    Sanitize and validate an agent name.

    Args:
        name: Raw agent name

    Returns:
        Sanitized agent name

    Raises:
        ValueError: If name is invalid after sanitization
    """
    sanitized = sanitize_agent_name(name)
    if not sanitized:
        raise ValueError("Invalid agent name - must contain at least one alphanumeric character")
    return sanitized


def get_agents_by_prefix(prefix: str) -> List[AgentStatus]:
    """
    Get all agents that match a base name prefix.

    Matches:
    - Exact name (e.g., "my-agent")
    - Versioned names (e.g., "my-agent-2", "my-agent-3")

    Args:
        prefix: Base agent name to match

    Returns:
        List of matching AgentStatus objects
    """
    all_agents = list_all_agents()
    matching = []

    for agent in all_agents:
        name = agent.name
        if name == prefix:
            matching.append(agent)
        elif name.startswith(f"{prefix}-"):
            # Check if suffix is a version number
            suffix = name[len(prefix) + 1:]
            if suffix.isdigit():
                matching.append(agent)

    return matching


def get_next_version_name(base_name: str) -> str:
    """
    Get next available version name for an agent.

    Pattern: {base-name} -> {base-name}-2 -> {base-name}-3

    Args:
        base_name: Base agent name

    Returns:
        Next available version name
    """
    existing = get_agents_by_prefix(base_name)

    if not existing:
        return base_name

    # Find highest version number
    max_version = 1
    for agent in existing:
        if agent.name == base_name:
            max_version = max(max_version, 1)
        elif agent.name.startswith(f"{base_name}-"):
            suffix = agent.name[len(base_name) + 1:]
            try:
                v = int(suffix)
                max_version = max(max_version, v)
            except ValueError:
                pass

    return f"{base_name}-{max_version + 1}"


def get_latest_version(base_name: str) -> Optional[AgentStatus]:
    """
    Get the most recent version of an agent.

    Args:
        base_name: Base agent name

    Returns:
        Most recent AgentStatus or None if no versions exist
    """
    existing = get_agents_by_prefix(base_name)
    if not existing:
        return None

    # Sort by version number (highest first)
    def get_version(agent):
        if agent.name == base_name:
            return 1
        suffix = agent.name[len(base_name) + 1:]
        try:
            return int(suffix)
        except ValueError:
            return 0

    return max(existing, key=get_version)


def check_shared_folder_mounts_match(container, agent_name: str) -> bool:
    """
    Check if container's shared folder mounts match the current config.
    Returns True if mounts are correct, False if recreation needed.
    """
    config = db.get_shared_folder_config(agent_name)
    if not config:
        # No config - check that no shared mounts exist
        mounts = container.attrs.get("Mounts", [])
        for m in mounts:
            dest = m.get("Destination", "")
            if dest == "/home/developer/shared-out" or dest.startswith("/home/developer/shared-in/"):
                return False  # Has mounts but no config - needs recreation to remove
        return True

    mounts = container.attrs.get("Mounts", [])
    mount_dests = {m.get("Destination") for m in mounts}

    # Check expose mount
    if config.expose_enabled:
        if "/home/developer/shared-out" not in mount_dests:
            return False  # Config says expose, but mount missing
    else:
        if "/home/developer/shared-out" in mount_dests:
            return False  # Config says no expose, but mount exists

    # Check consume mounts
    if config.consume_enabled:
        available = db.get_available_shared_folders(agent_name)
        for source_agent in available:
            mount_path = db.get_shared_mount_path(source_agent)
            source_volume = db.get_shared_volume_name(source_agent)
            # Check if volume exists
            try:
                docker_client.volumes.get(source_volume)
                if mount_path not in mount_dests:
                    return False  # Should be mounted but isn't
            except Exception:
                pass  # Volume doesn't exist yet, OK to skip

    return True


def check_api_key_env_matches(container, agent_name: str) -> bool:
    """
    Check if container's ANTHROPIC_API_KEY env var matches the current setting.
    Returns True if env matches config, False if recreation needed.
    """
    use_platform_key = db.get_use_platform_api_key(agent_name)

    # Get current env vars from container
    env_list = container.attrs.get("Config", {}).get("Env", [])
    env_dict = {e.split("=", 1)[0]: e.split("=", 1)[1] for e in env_list if "=" in e}

    has_api_key = "ANTHROPIC_API_KEY" in env_dict and env_dict["ANTHROPIC_API_KEY"]

    if use_platform_key:
        # Should have the platform key - check if it's current
        expected_key = get_anthropic_api_key()
        current_key = env_dict.get("ANTHROPIC_API_KEY", "")
        return current_key == expected_key
    else:
        # Should NOT have the key
        return not has_api_key


def check_resource_limits_match(container, agent_name: str) -> bool:
    """
    Check if container's resource limits match the current database settings.
    Returns True if resources match, False if recreation needed.
    """
    # Get DB settings (may be None if using template defaults)
    db_limits = db.get_resource_limits(agent_name)

    # Get current container limits from labels (stored during creation)
    labels = container.attrs.get("Config", {}).get("Labels", {})
    current_memory = labels.get("trinity.memory", "4g")
    current_cpu = labels.get("trinity.cpu", "2")

    if db_limits is None:
        # No custom limits set in DB - container should use template defaults
        # Don't trigger recreation just because DB is empty
        return True

    # Compare DB limits with current container limits
    expected_memory = db_limits.get("memory") or current_memory
    expected_cpu = db_limits.get("cpu") or current_cpu

    if expected_memory != current_memory:
        logger.info(f"Resource mismatch for {agent_name}: memory {current_memory} -> {expected_memory}")
        return False

    if expected_cpu != current_cpu:
        logger.info(f"Resource mismatch for {agent_name}: cpu {current_cpu} -> {expected_cpu}")
        return False

    return True


def check_full_capabilities_match(container, agent_name: str) -> bool:
    """
    Check if container's full_capabilities setting matches the current system-wide setting.
    Returns True if capabilities match, False if recreation needed.

    When full_capabilities=True:
    - Container runs with Docker default capabilities
    - Can install packages with apt-get, use sudo

    When full_capabilities=False:
    - Container runs with restricted capabilities
    - More secure but cannot install packages

    Note: This is now a system-wide setting, not per-agent.
    """
    # Get system-wide setting
    system_full_caps = get_agent_full_capabilities()

    # Get current container setting from labels
    labels = container.attrs.get("Config", {}).get("Labels", {})
    current_full_caps = labels.get("trinity.full-capabilities", "false").lower() == "true"

    if system_full_caps != current_full_caps:
        logger.info(f"Capabilities mismatch for {agent_name}: container={current_full_caps} -> system={system_full_caps}")
        return False

    return True
