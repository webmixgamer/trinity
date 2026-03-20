"""SSH access endpoints for Trinity agents."""
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from models import User
from database import db
from dependencies import get_current_user
from services.docker_service import get_agent_container
from services.docker_utils import container_reload

router = APIRouter(prefix="/api/agents", tags=["agents"])


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
    await container_reload(container)
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
    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)

    if auth_method == "password":
        # Generate ephemeral password
        password = ssh_service.generate_password()

        # Set password in container (async to avoid blocking)
        if not await ssh_service.set_container_password(agent_name, password):
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

        # Inject public key into container (async to avoid blocking)
        if not await ssh_service.inject_ssh_key(agent_name, keypair["public_key"]):
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
