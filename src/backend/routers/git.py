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


class GitInitializeRequest(BaseModel):
    """Request body for git initialization."""
    repo_owner: str  # GitHub username or organization
    repo_name: str  # Repository name
    create_repo: bool = True  # Whether to create the repository if it doesn't exist
    private: bool = True  # Whether the new repository should be private
    description: Optional[str] = None  # Repository description


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


@router.post("/{agent_name}/git/initialize")
async def initialize_github_sync(
    agent_name: str,
    body: GitInitializeRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Initialize GitHub synchronization for an agent.

    This endpoint:
    1. Creates a GitHub repository (if requested)
    2. Initializes git in the agent workspace
    3. Commits the current state
    4. Pushes to GitHub
    5. Creates a working branch
    6. Stores configuration in the database

    Requires:
    - GitHub PAT configured in system settings
    - Agent must be running
    - User must be agent owner
    """
    import httpx
    from services.docker_service import get_agent_container, execute_command_in_container
    from routers.settings import get_github_pat

    # Check if agent exists
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if agent is running
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent must be running to initialize Git sync")

    # Check access (owners and admins only)
    if not db.can_user_share_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Only agent owners can initialize GitHub sync")

    # Check if already configured
    existing_config = git_service.get_agent_git_config(agent_name)
    if existing_config:
        # Verify git is actually initialized in the container (check both possible locations)
        check_git = execute_command_in_container(
            container_name=f"agent-{agent_name}",
            command='bash -c "[ -d /home/developer/workspace/.git ] && echo workspace || ([ -d /home/developer/.git ] && echo home || echo notexists)"',
            timeout=5
        )

        if "workspace" in check_git.get("output", "") or "home" in check_git.get("output", ""):
            # Git is properly initialized, prevent re-initialization
            raise HTTPException(
                status_code=409,
                detail=f"Git sync already configured for this agent. Repository: {existing_config.github_repo}"
            )
        else:
            # Database record exists but git not initialized - clean up orphaned record
            print(f"Warning: Found orphaned git config for {agent_name}. Cleaning up and allowing re-initialization.")
            db.execute_query("DELETE FROM agent_git_config WHERE agent_name = ?", (agent_name,))
            # Continue with initialization

    # Get GitHub PAT from settings
    github_pat = get_github_pat()
    if not github_pat:
        raise HTTPException(
            status_code=400,
            detail="GitHub Personal Access Token not configured. Please add it in Settings."
        )

    try:
        repo_full_name = f"{body.repo_owner}/{body.repo_name}"

        # Step 1: Create repository if requested
        if body.create_repo:
            async with httpx.AsyncClient() as client:
                # Check if repository already exists
                check_response = await client.get(
                    f"https://api.github.com/repos/{repo_full_name}",
                    headers={
                        "Authorization": f"Bearer {github_pat}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28"
                    },
                    timeout=10.0
                )

                if check_response.status_code == 404:
                    # Repository doesn't exist, check if owner is an org or user
                    owner_response = await client.get(
                        f"https://api.github.com/users/{body.repo_owner}",
                        headers={
                            "Authorization": f"Bearer {github_pat}",
                            "Accept": "application/vnd.github+json",
                            "X-GitHub-Api-Version": "2022-11-28"
                        },
                        timeout=10.0
                    )

                    is_org = False
                    if owner_response.status_code == 200:
                        owner_data = owner_response.json()
                        is_org = owner_data.get("type") == "Organization"

                    # Create repository
                    create_payload = {
                        "name": body.repo_name,
                        "private": body.private,
                        "auto_init": False  # We'll initialize ourselves
                    }
                    if body.description:
                        create_payload["description"] = body.description

                    # Use different endpoint for orgs vs personal repos
                    if is_org:
                        create_url = f"https://api.github.com/orgs/{body.repo_owner}/repos"
                    else:
                        create_url = "https://api.github.com/user/repos"

                    create_response = await client.post(
                        create_url,
                        headers={
                            "Authorization": f"Bearer {github_pat}",
                            "Accept": "application/vnd.github+json",
                            "X-GitHub-Api-Version": "2022-11-28"
                        },
                        json=create_payload,
                        timeout=30.0
                    )

                    if create_response.status_code != 201:
                        error_data = create_response.json()
                        error_msg = error_data.get('message', 'Unknown error')

                        # Log full error for debugging
                        print(f"GitHub API Error: Status={create_response.status_code}")
                        print(f"Response: {error_data}")
                        print(f"Is Organization: {is_org}")
                        print(f"Endpoint used: {create_url}")

                        # Add helpful context
                        if is_org:
                            error_msg += f" (Organization: {body.repo_owner}. Ensure PAT has 'repo' scope and admin access to this organization)"
                        else:
                            error_msg += " (For personal repos, PAT needs 'repo' or 'public_repo' scope)"

                        raise HTTPException(
                            status_code=400,
                            detail=f"Failed to create GitHub repository: {error_msg}"
                        )
                elif check_response.status_code == 200:
                    # Repository already exists, that's fine
                    pass
                else:
                    # Other error
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to check repository: {check_response.status_code}"
                    )

        # Step 2: Determine git directory
        # Check if workspace exists and has content
        check_workspace = execute_command_in_container(
            container_name=f"agent-{agent_name}",
            command='bash -c "[ -d /home/developer/workspace ] && find /home/developer/workspace -mindepth 1 -maxdepth 1 | head -1 | wc -l"',
            timeout=5
        )

        workspace_has_content = check_workspace.get("exit_code") == 0 and "1" in check_workspace.get("output", "")

        if workspace_has_content:
            # Use workspace if it exists and has content
            git_dir = "/home/developer/workspace"
            print(f"Using workspace directory with existing content: {git_dir}")
        else:
            # Use home directory where agent's files actually live
            git_dir = "/home/developer"
            print(f"Using home directory (agent's files are here): {git_dir}")

            # Create .gitignore to exclude certain files from git
            gitignore_content = """# Exclude sensitive and temporary files
.bash_logout
.bashrc
.profile
.bash_history
.cache/
.local/
.npm/
.ssh/
"""
            execute_command_in_container(
                container_name=f"agent-{agent_name}",
                command=f'bash -c "cat > {git_dir}/.gitignore << \'GITIGNORE_EOF\'\n{gitignore_content}\nGITIGNORE_EOF\n"',
                timeout=5
            )

        # Step 3: Initialize git in agent workspace
        commands = [
            # Configure git
            'git config --global user.email "trinity@agent.local"',
            'git config --global user.name "Trinity Agent"',
            'git config --global init.defaultBranch main',

            # Initialize repository
            'git init',

            # Add remote (use PAT in URL for authentication)
            f'git remote add origin https://oauth2:{github_pat}@github.com/{repo_full_name}.git',

            # Stage all files
            'git add .',

            # Create initial commit
            'git commit -m "Initial commit from Trinity Agent" || echo "Nothing to commit"',

            # Push to main branch
            'git push -u origin main --force'
        ]

        for cmd in commands:
            result = execute_command_in_container(
                container_name=f"agent-{agent_name}",
                command=f'bash -c "cd {git_dir} && {cmd}"',
                timeout=60
            )
            if "error" in result.get("output", "").lower() and "Nothing to commit" not in result.get("output", ""):
                # Don't fail on "Nothing to commit" message
                if result.get("exit_code", 0) != 0:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Git command failed: {cmd}\nOutput: {result.get('output', '')}"
                    )

        # Step 4: Create working branch
        instance_id = git_service.generate_instance_id()
        working_branch = git_service.generate_working_branch(agent_name, instance_id)

        branch_commands = [
            f'git checkout -b {working_branch}',
            f'git push -u origin {working_branch}'
        ]

        for cmd in branch_commands:
            result = execute_command_in_container(
                container_name=f"agent-{agent_name}",
                command=f'bash -c "cd {git_dir} && {cmd}"',
                timeout=60
            )
            if result.get("exit_code", 0) != 0:
                # Working branch creation is optional - log but don't fail
                print(f"Warning: Failed to create working branch: {result.get('output', '')}")

        # Step 5: Verify git was initialized successfully
        verify_result = execute_command_in_container(
            container_name=f"agent-{agent_name}",
            command=f'bash -c "cd {git_dir} && git rev-parse --git-dir"',
            timeout=5
        )

        if verify_result.get("exit_code", 0) != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Git initialization verification failed. Git directory not found: {verify_result.get('output', '')}"
            )

        print(f"Git initialization verified successfully in {git_dir}")

        # Step 6: Store configuration in database
        config = await git_service.create_git_config_for_agent(
            agent_name=agent_name,
            github_repo=repo_full_name,
            instance_id=instance_id
        )

        # Log the initialization
        await log_audit_event(
            event_type="git_operation",
            action="initialize",
            user_id=current_user.username,
            agent_name=agent_name,
            ip_address=request.client.host if request.client else None,
            result="success",
            details={
                "github_repo": repo_full_name,
                "working_branch": working_branch,
                "created_repo": body.create_repo
            }
        )

        return {
            "success": True,
            "message": "GitHub sync initialized successfully",
            "github_repo": repo_full_name,
            "working_branch": working_branch,
            "instance_id": instance_id,
            "repo_url": f"https://github.com/{repo_full_name}"
        }

    except HTTPException:
        raise
    except Exception as e:
        await log_audit_event(
            event_type="git_operation",
            action="initialize",
            user_id=current_user.username,
            agent_name=agent_name,
            ip_address=request.client.host if request.client else None,
            result="failed",
            severity="error",
            details={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Failed to initialize GitHub sync: {str(e)}")
