#!/bin/bash

echo "Starting Trinity Agent (Secure Mode)..."

# Initialize from GitHub repository if specified
if [ -n "${GITHUB_REPO}" ] && [ -n "${GITHUB_PAT}" ]; then
    echo "Initializing agent from GitHub repository: ${GITHUB_REPO}"
    cd /home/developer

    # Clone the repository using PAT authentication
    CLONE_URL="https://oauth2:${GITHUB_PAT}@github.com/${GITHUB_REPO}.git"

    # Check if GIT_SYNC_ENABLED - if so, keep .git directory for bidirectional sync
    if [ "${GIT_SYNC_ENABLED}" = "true" ]; then
        # Check if repo is already cloned (persistent volume has existing .git)
        if [ -d "/home/developer/.git" ]; then
            echo "Repository already exists on persistent volume - skipping clone"
            echo "Running git fetch to sync with remote..."
            cd /home/developer
            git fetch origin 2>&1 || echo "Note: Could not fetch from remote"

            # Restore infrastructure files from base image (may have been updated)
            cp /home/developer/agent-server.py.base /home/developer/agent-server.py 2>/dev/null || true
            cp -r /home/developer/agent_server.base /home/developer/agent_server 2>/dev/null || true

            echo "Existing repository ready with persisted files"
        else
            echo "Git sync enabled - cloning with full history for bidirectional sync"
            echo "Cloning repository..."

            # Preserve agent-server.py, agent_server/, startup.sh, and Python packages before cloning
            cp /home/developer/agent-server.py /tmp/agent-server.py.bak 2>/dev/null || true
            cp -r /home/developer/agent_server /tmp/agent_server.bak 2>/dev/null || true
            cp /home/developer/startup.sh /tmp/startup.sh.bak 2>/dev/null || true
            cp -r /home/developer/.local /tmp/.local.bak 2>/dev/null || true

            # Clone directly into /home/developer (first time setup on empty volume)
            rm -rf /home/developer/* /home/developer/.[!.]* 2>/dev/null || true

            if git clone "${CLONE_URL}" /home/developer 2>&1; then
            echo "Repository cloned successfully with git history"
            cd /home/developer

            # Configure git user for commits
            git config user.email "trinity-agent@ability.ai"
            git config user.name "Trinity Agent (${AGENT_NAME:-unknown})"

            # Create and checkout working branch if specified
            if [ -n "${GIT_WORKING_BRANCH}" ]; then
                echo "Creating working branch: ${GIT_WORKING_BRANCH}"

                # Check if branch exists on remote
                if git ls-remote --heads origin "${GIT_WORKING_BRANCH}" | grep -q "${GIT_WORKING_BRANCH}"; then
                    echo "Branch exists on remote, checking out..."
                    git checkout "${GIT_WORKING_BRANCH}" || git checkout -b "${GIT_WORKING_BRANCH}" origin/main
                else
                    echo "Creating new branch from main..."
                    git checkout -b "${GIT_WORKING_BRANCH}"
                    # Push the new branch to establish tracking
                    git push -u origin "${GIT_WORKING_BRANCH}" 2>&1 || echo "Note: Could not push new branch (will push on first sync)"
                fi

                echo "Working branch '${GIT_WORKING_BRANCH}' ready"
            fi

            # Store git remote URL with credentials for push operations
            git remote set-url origin "${CLONE_URL}"

            # Restore agent-server.py, agent_server/, startup.sh, and Python packages (these are from the base image, not the repo)
            cp /tmp/agent-server.py.bak /home/developer/agent-server.py 2>/dev/null || true
            cp -r /tmp/agent_server.bak /home/developer/agent_server 2>/dev/null || true
            cp /tmp/startup.sh.bak /home/developer/startup.sh 2>/dev/null || true
            cp -r /tmp/.local.bak /home/developer/.local 2>/dev/null || true
            chmod +x /home/developer/agent-server.py /home/developer/startup.sh 2>/dev/null || true

            # Add infrastructure files to .gitignore (don't sync these to GitHub)
            if [ ! -f /home/developer/.gitignore ]; then
                echo "# Trinity agent infrastructure files" > /home/developer/.gitignore
            fi
            grep -q "agent-server.py" /home/developer/.gitignore || echo "agent-server.py" >> /home/developer/.gitignore
            grep -q "agent_server/" /home/developer/.gitignore || echo "agent_server/" >> /home/developer/.gitignore
            grep -q "startup.sh" /home/developer/.gitignore || echo "startup.sh" >> /home/developer/.gitignore
            grep -q ".local/" /home/developer/.gitignore || echo ".local/" >> /home/developer/.gitignore

            echo "Git sync initialization complete"
            else
                echo "ERROR: Failed to clone GitHub repository: ${GITHUB_REPO}"
            fi
        fi
    else
        # Original behavior: shallow clone without .git for non-sync agents
        # Check if initialization marker exists (persistent volume already has files)
        if [ -f "/home/developer/.trinity-initialized" ]; then
            echo "Agent workspace already initialized on persistent volume - preserving user files"
        else
            echo "Git sync disabled - using shallow clone without git history"

        # Clone into a temp directory first
        if git clone --depth 1 "${CLONE_URL}" /tmp/repo-clone 2>&1; then
            echo "Repository cloned successfully"

            # Copy all files from the cloned repo to the working directory
            # Using rsync-like behavior with cp
            cd /tmp/repo-clone

            # Copy everything except .git directory
            for item in $(ls -A | grep -v "^\.git$"); do
                echo "Copying ${item}..."
                cp -r "${item}" /home/developer/ 2>/dev/null || true
            done

            # Clean up the clone
            rm -rf /tmp/repo-clone

            cd /home/developer

            # Create initialization marker to prevent re-cloning on restart
            touch /home/developer/.trinity-initialized

            echo "GitHub repository initialization complete"
        else
            echo "ERROR: Failed to clone GitHub repository: ${GITHUB_REPO}"
        fi
        fi
    fi

# Initialize from local template if specified (fallback)
elif [ -n "${TEMPLATE_NAME}" ] && [ -d "/template" ]; then
    echo "Initializing agent from local template: ${TEMPLATE_NAME}"
    cd /home/developer

    # Copy template files to workspace, excluding template.yaml
    if [ -d "/template/.claude" ]; then
        echo "Copying .claude directory..."
        cp -r /template/.claude . 2>/dev/null || true
    fi

    if [ -f "/template/CLAUDE.md" ]; then
        echo "Copying CLAUDE.md..."
        cp /template/CLAUDE.md . 2>/dev/null || true
    fi

    if [ -f "/template/README.md" ]; then
        echo "Copying README.md..."
        cp /template/README.md . 2>/dev/null || true
    fi

    if [ -d "/template/resources" ]; then
        echo "Copying resources directory..."
        cp -r /template/resources . 2>/dev/null || true
    fi

    if [ -d "/template/scripts" ]; then
        echo "Copying scripts directory..."
        cp -r /template/scripts . 2>/dev/null || true
        chmod +x scripts/*.sh 2>/dev/null || true
        chmod +x scripts/*.py 2>/dev/null || true
    fi

    if [ -d "/template/memory" ]; then
        echo "Copying memory directory..."
        cp -r /template/memory . 2>/dev/null || true
    fi

    echo "Template initialization complete"
fi

# NOTE: Trinity Meta-Prompt Injection is now handled by agent-server.py
# The backend calls POST /api/trinity/inject after the container starts
# This provides centralized control and better error handling

# Copy generated credential files (with real values, generated by backend)
if [ -d "/generated-creds" ]; then
    echo "Copying generated credential files..."
    cd /home/developer

    # Copy .mcp.json with real credentials
    if [ -f "/generated-creds/.mcp.json" ]; then
        echo "  Copying .mcp.json (with credentials)..."
        cp /generated-creds/.mcp.json . 2>/dev/null || true
    fi

    # Copy .env with real credentials
    if [ -f "/generated-creds/.env" ]; then
        echo "  Copying .env (with credentials)..."
        cp /generated-creds/.env . 2>/dev/null || true
    fi

    # Copy any other generated config files (preserving directory structure)
    for file in $(find /generated-creds -type f ! -name ".mcp.json" ! -name ".env" 2>/dev/null); do
        # Get relative path from /generated-creds
        rel_path="${file#/generated-creds/}"
        target_dir=$(dirname "$rel_path")

        if [ "$target_dir" != "." ]; then
            mkdir -p "/home/developer/$target_dir"
        fi

        echo "  Copying $rel_path..."
        cp "$file" "/home/developer/$rel_path" 2>/dev/null || true
    done

    echo "Credential files copied"
fi

# Start SSH if enabled
if [ "${ENABLE_SSH}" = "true" ]; then
    echo "Starting SSH server..."
    sudo /usr/sbin/sshd -D &
fi

# Load agent configuration
if [ -f "/config/agent-config.yaml" ]; then
    echo "Loading agent configuration..."
    python3 /home/developer/configure_agent.py
fi

# Configure MCP servers
if [ -d "/config/mcp-servers" ]; then
    for mcp in /config/mcp-servers/*.yaml; do
        if [ -f "$mcp" ]; then
            echo "Configuring MCP: $mcp"
            python3 /home/developer/setup_mcp.py "$mcp"
        fi
    done
fi

# Start Agent Web Server (self-contained UI)
if [ "${ENABLE_AGENT_UI}" = "true" ]; then
    echo "Starting Agent Web UI on port ${AGENT_SERVER_PORT:-8000}..."
    python3 /home/developer/agent-server.py &
fi

echo "Agent ready. Keeping container alive..."
tail -f /dev/null

