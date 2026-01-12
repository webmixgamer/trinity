"""
Agent Service Lifecycle - Agent start/stop and configuration management.

Contains functions for starting, stopping, and reconfiguring agents.
"""
import logging
import docker
import httpx

from fastapi import HTTPException

from database import db
from services.docker_service import (
    docker_client,
    get_agent_container,
)
from services.settings_service import get_anthropic_api_key, get_agent_full_capabilities
from services.agent_client import get_agent_client
from .helpers import check_shared_folder_mounts_match, check_api_key_env_matches, check_resource_limits_match, check_full_capabilities_match

logger = logging.getLogger(__name__)


async def inject_trinity_meta_prompt(agent_name: str, max_retries: int = 5, retry_delay: float = 2.0) -> dict:
    """
    Inject Trinity meta-prompt into an agent via its internal API.

    This is called after agent startup to inject planning commands
    and create the necessary directory structure.

    Args:
        agent_name: Name of the agent
        max_retries: Number of retries for connection
        retry_delay: Seconds between retries

    Returns:
        dict with injection status or error info
    """
    # Fetch system-wide custom prompt setting
    custom_prompt = db.get_setting_value("trinity_prompt", default=None)
    if custom_prompt:
        logger.info(f"Found trinity_prompt setting ({len(custom_prompt)} chars), will inject into {agent_name}")

    # Use AgentClient for injection (handles retries internally)
    client = get_agent_client(agent_name)
    return await client.inject_trinity_prompt(
        custom_prompt=custom_prompt,
        force=False,
        max_retries=max_retries,
        retry_delay=retry_delay
    )


async def inject_assigned_credentials(agent_name: str, max_retries: int = 3, retry_delay: float = 2.0) -> dict:
    """
    Inject assigned credentials into a running agent.

    This is called after agent startup to push any credentials that were
    assigned to this agent in the Credentials tab.

    Args:
        agent_name: Name of the agent
        max_retries: Number of retries for connection
        retry_delay: Seconds between retries

    Returns:
        dict with injection status
    """
    import asyncio
    from credentials import credential_manager

    # Get the agent owner from database
    owner = db.get_agent_owner(agent_name)
    if not owner:
        logger.warning(f"No owner found for agent {agent_name}, skipping credential injection")
        return {"status": "skipped", "reason": "no_owner"}

    # Get assigned credentials
    credentials = credential_manager.get_assigned_credential_values(agent_name, owner)
    file_credentials = credential_manager.get_assigned_file_credentials(agent_name, owner)

    if not credentials and not file_credentials:
        logger.debug(f"No assigned credentials for agent {agent_name}")
        return {"status": "skipped", "reason": "no_credentials"}

    logger.info(f"Injecting {len(credentials)} credentials and {len(file_credentials)} files into agent {agent_name}")

    # Push to agent with retries
    last_error = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://agent-{agent_name}:8000/api/credentials/update",
                    json={
                        "credentials": credentials,
                        "mcp_config": None,
                        "files": file_credentials if file_credentials else None
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    return {
                        "status": "success",
                        "credential_count": len(credentials),
                        "file_count": len(file_credentials)
                    }
                else:
                    last_error = f"Agent returned status {response.status_code}"
                    logger.warning(f"Credential injection attempt {attempt + 1} failed: {last_error}")

        except httpx.RequestError as e:
            last_error = str(e)
            logger.warning(f"Credential injection attempt {attempt + 1} failed: {last_error}")

        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)

    logger.error(f"Failed to inject credentials into agent {agent_name} after {max_retries} attempts: {last_error}")
    return {"status": "failed", "error": last_error}


async def start_agent_internal(agent_name: str) -> dict:
    """
    Internal function to start an agent.

    Used by both the API endpoint and system deployment.
    Triggers Trinity meta-prompt injection.

    Args:
        agent_name: Name of the agent to start

    Returns:
        dict with start status and trinity_injection result

    Raises:
        HTTPException: If agent not found or start fails
    """
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if container needs recreation for shared folders, API key, resource limits, or capabilities
    container.reload()
    needs_recreation = (
        not check_shared_folder_mounts_match(container, agent_name) or
        not check_api_key_env_matches(container, agent_name) or
        not check_resource_limits_match(container, agent_name) or
        not check_full_capabilities_match(container, agent_name)
    )

    if needs_recreation:
        # Recreate container with updated config
        # Use system user for internal operations
        await recreate_container_with_updated_config(agent_name, container, "system")
        container = get_agent_container(agent_name)

    container.start()

    # Inject Trinity meta-prompt
    trinity_result = await inject_trinity_meta_prompt(agent_name)
    trinity_status = trinity_result.get("status", "unknown")

    # Inject assigned credentials from the Credentials page
    credentials_result = await inject_assigned_credentials(agent_name)
    credentials_status = credentials_result.get("status", "unknown")

    return {
        "message": f"Agent {agent_name} started",
        "trinity_injection": trinity_status,
        "trinity_result": trinity_result,
        "credentials_injection": credentials_status,
        "credentials_result": credentials_result
    }


async def recreate_container_with_updated_config(agent_name: str, old_container, owner_username: str):
    """
    Recreate an agent container with updated configuration.
    Handles shared folder mounts and API key settings.
    Preserves the agent's workspace volume and other configuration.
    """
    # Extract configuration from old container
    old_config = old_container.attrs.get("Config", {})
    old_host_config = old_container.attrs.get("HostConfig", {})

    # Get key settings
    image = old_config.get("Image", "trinity-agent:latest")
    env_vars = {e.split("=", 1)[0]: e.split("=", 1)[1] for e in old_config.get("Env", []) if "=" in e}
    labels = old_config.get("Labels", {})

    # Update ANTHROPIC_API_KEY based on current setting
    use_platform_key = db.get_use_platform_api_key(agent_name)
    if use_platform_key:
        # Use platform API key
        env_vars['ANTHROPIC_API_KEY'] = get_anthropic_api_key()
    else:
        # Remove platform key - user will auth in terminal
        env_vars.pop('ANTHROPIC_API_KEY', None)

    # Get port from labels
    ssh_port = int(labels.get("trinity.ssh-port", 2222))

    # Get resource limits - check DB for overrides, fallback to labels/defaults
    db_limits = db.get_resource_limits(agent_name)
    if db_limits:
        cpu = db_limits.get("cpu") or labels.get("trinity.cpu", "2")
        memory = db_limits.get("memory") or labels.get("trinity.memory", "4g")
    else:
        cpu = labels.get("trinity.cpu", "2")
        memory = labels.get("trinity.memory", "4g")

    # Update labels with new resource limits for future reference
    labels["trinity.cpu"] = cpu
    labels["trinity.memory"] = memory

    # Get full_capabilities from system-wide setting (not per-agent)
    full_capabilities = get_agent_full_capabilities()

    # Update label to reflect current setting
    labels["trinity.full-capabilities"] = str(full_capabilities).lower()

    # Stop and remove old container
    try:
        old_container.stop()
    except Exception:
        pass
    old_container.remove()

    # Build new volume configuration
    agent_volume_name = f"agent-{agent_name}-workspace"

    # Start with base volumes - get existing bind mounts
    old_mounts = old_container.attrs.get("Mounts", [])
    volumes = {}

    for m in old_mounts:
        dest = m.get("Destination", "")
        # Skip shared folder mounts - we'll add the correct ones
        if dest == "/home/developer/shared-out" or dest.startswith("/home/developer/shared-in/"):
            continue
        # Keep other mounts
        if m.get("Type") == "bind":
            volumes[m.get("Source")] = {"bind": dest, "mode": "rw" if m.get("RW", True) else "ro"}
        elif m.get("Type") == "volume":
            vol_name = m.get("Name")
            if vol_name:
                volumes[vol_name] = {"bind": dest, "mode": "rw" if m.get("RW", True) else "ro"}

    # Add shared folder mounts based on current config
    shared_config = db.get_shared_folder_config(agent_name)
    if shared_config:
        if shared_config.expose_enabled:
            shared_volume_name = db.get_shared_volume_name(agent_name)
            volume_created = False
            try:
                docker_client.volumes.get(shared_volume_name)
            except docker.errors.NotFound:
                docker_client.volumes.create(
                    name=shared_volume_name,
                    labels={
                        'trinity.platform': 'agent-shared',
                        'trinity.agent-name': agent_name
                    }
                )
                volume_created = True

            # Fix ownership of new volumes (Docker creates them as root)
            if volume_created:
                try:
                    docker_client.containers.run(
                        'alpine',
                        command='chown 1000:1000 /shared',
                        volumes={shared_volume_name: {'bind': '/shared', 'mode': 'rw'}},
                        remove=True
                    )
                except Exception as e:
                    logger.warning(f"Could not fix shared volume ownership: {e}")

            volumes[shared_volume_name] = {'bind': '/home/developer/shared-out', 'mode': 'rw'}

        if shared_config.consume_enabled:
            available_folders = db.get_available_shared_folders(agent_name)
            for source_agent in available_folders:
                source_volume = db.get_shared_volume_name(source_agent)
                mount_path = db.get_shared_mount_path(source_agent)
                try:
                    docker_client.volumes.get(source_volume)
                    volumes[source_volume] = {'bind': mount_path, 'mode': 'rw'}
                except docker.errors.NotFound:
                    pass

    # Create new container
    # Security: If full_capabilities=True, use Docker defaults (apt-get works)
    # Otherwise use restricted mode (secure default)
    new_container = docker_client.containers.run(
        image,
        detach=True,
        name=f"agent-{agent_name}",
        ports={'22/tcp': ssh_port},
        volumes=volumes,
        environment=env_vars,
        labels=labels,
        security_opt=['apparmor:docker-default'] if not full_capabilities else [],
        cap_drop=[] if full_capabilities else ['ALL'],
        cap_add=[] if full_capabilities else ['NET_BIND_SERVICE', 'SETGID', 'SETUID', 'CHOWN', 'SYS_CHROOT', 'AUDIT_WRITE'],
        read_only=False,
        tmpfs={'/tmp': 'size=100m'} if full_capabilities else {'/tmp': 'noexec,nosuid,size=100m'},
        network='trinity-agent-network',
        mem_limit=memory,
        cpu_count=int(cpu)
    )

    logger.info(f"Recreated container for agent {agent_name} with updated configuration")
    return new_container
