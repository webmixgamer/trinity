# Feature: GitHub Repository Initialization

## Overview
Allows users to initialize GitHub synchronization for any existing agent by configuring a GitHub Personal Access Token (PAT) in Settings, then using a modal form to create a GitHub repository and push the agent's workspace to it. This enables bidirectional sync for agents that were created without Git support.

## User Story
As a **Trinity platform user**, I want to **enable GitHub synchronization for an existing agent** so that **I can version-control the agent's workspace and collaborate via GitHub without recreating the agent**.

---

## Entry Points

| Type | Location | Description |
|------|----------|-------------|
| **UI** | `src/frontend/src/views/Settings.vue:126-218` | GitHub PAT configuration with test/save |
| **UI** | `src/frontend/src/components/GitPanel.vue:17-26` | "Initialize GitHub Sync" button |
| **UI** | `src/frontend/src/components/GitPanel.vue:29-166` | Initialize modal form |
| **API** | `POST /api/agents/{name}/git/initialize` | Initialize git sync endpoint |
| **MCP** | `initialize_github_sync` tool | MCP tool for programmatic initialization |

---

## Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant Settings
    participant GitPanel
    participant Store
    participant Backend
    participant GitService
    participant GitHub
    participant Container

    Note over User,Container: Phase 1: Configure GitHub PAT
    User->>Settings: Navigate to Settings page
    Settings->>Settings: Load API key status
    User->>Settings: Enter GitHub PAT
    User->>Settings: Click "Test" button
    Settings->>Backend: POST /api/settings/api-keys/github/test
    Backend->>GitHub: GET /user (validate token)
    GitHub->>Backend: Return user info + permissions
    Backend->>Settings: {valid: true, username, has_repo_access}
    Settings->>User: Show success with username
    User->>Settings: Click "Save" button
    Settings->>Backend: PUT /api/settings/api-keys/github
    Backend->>Backend: Store in system_settings table
    Backend->>Settings: {success: true, masked: "...xxxx"}

    Note over User,Container: Phase 2: Initialize Git Sync
    User->>GitPanel: Navigate to agent's Git tab
    GitPanel->>GitPanel: Detect git_enabled: false
    GitPanel->>User: Show "Initialize GitHub Sync" button
    User->>GitPanel: Click "Initialize GitHub Sync"
    GitPanel->>User: Open modal form
    User->>GitPanel: Enter repo_owner, repo_name
    User->>GitPanel: Check "Create repository" + "Private"
    User->>GitPanel: Click "Initialize"
    GitPanel->>Store: initializeGitHub(agentName, config)
    Store->>Backend: POST /api/agents/{name}/git/initialize (120s timeout)

    Note over Backend,Container: Phase 3: Backend Processing
    Backend->>Backend: Verify agent is running
    Backend->>Backend: Check user is owner (can_user_share_agent)
    Backend->>Backend: Check for orphaned git config
    Backend->>Backend: Clean up orphaned records if necessary
    Backend->>Backend: Get GitHub PAT from settings
    Backend->>GitHub: GET /repos/{owner}/{name} (check exists)
    alt Repository doesn't exist
        Backend->>GitHub: POST /user/repos (create repository)
        GitHub->>Backend: 201 Created
    else Repository exists
        GitHub->>Backend: 200 OK
    end

    Note over Backend,Container: Phase 4: Smart Directory Detection
    Backend->>Container: Check workspace exists and has content
    alt Workspace has content
        Backend->>Backend: Use /home/developer/workspace
    else Workspace empty or doesn't exist
        Backend->>Backend: Use /home/developer (agent files location)
        Backend->>Container: Create .gitignore (exclude .bashrc, .ssh/, etc.)
    end

    Note over Backend,Container: Phase 5: Git Initialization in Container
    Backend->>Container: Execute git config commands
    Backend->>Container: git init
    Backend->>Container: git remote add origin https://oauth2:{PAT}@github.com/{owner}/{name}.git
    Backend->>Container: git add .
    Backend->>Container: git commit -m "Initial commit from Trinity Agent"
    Backend->>Container: git push -u origin main --force
    Backend->>GitService: generate_instance_id()
    Backend->>Container: git checkout -b trinity/{name}/{instance_id}
    Backend->>Container: git push -u origin trinity/{name}/{instance_id}

    Note over Backend,Container: Phase 6: Verification & Persistence
    Backend->>Container: Verify git directory exists (git rev-parse --git-dir)
    Backend->>GitService: create_git_config_for_agent()
    GitService->>GitService: Store in agent_git_config table
    Backend->>Backend: Log audit event
    Backend->>Store: Return success + repo details
    Store->>GitPanel: Close modal
    GitPanel->>GitPanel: Reload git status
    GitPanel->>User: Show git sync UI with remote URL
```

---

## Frontend Layer

### Settings Page - GitHub PAT Configuration

**Location**: `src/frontend/src/views/Settings.vue`

| Lines | Component | Description |
|-------|-----------|-------------|
| 126-218 | GitHub PAT section | Input field with test/save buttons |
| 128-130 | Label | "GitHub Personal Access Token (PAT)" |
| 133-140 | Password input | Toggleable visibility, masked placeholder |
| 155-165 | Test button | Calls `testGithubPat()` |
| 166-177 | Save button | Calls `saveGithubPat()` |
| 179-210 | Status display | Shows validation result with permissions info |
| 211-217 | Help text | Links to GitHub token creation |

**Key Methods**:

```javascript
// Line 592-630: Test GitHub PAT
async function testGithubPat() {
  const response = await axios.post('/api/settings/api-keys/github/test', {
    api_key: githubPat.value
  })

  if (response.data.valid) {
    // Display username, token type (fine-grained/classic), repo permissions
    githubPatTestMessage.value = `Valid! GitHub user: ${response.data.username} ...`
  }
}

// Line 633-663: Save GitHub PAT
async function saveGithubPat() {
  const response = await axios.put('/api/settings/api-keys/github', {
    api_key: githubPat.value
  })

  // Update status, clear input, show success
  githubPatStatus.value = {
    configured: true,
    masked: response.data.masked,
    source: 'settings'
  }
}
```

### GitPanel Component - Initialize UI

**Location**: `src/frontend/src/components/GitPanel.vue`

| Lines | Component | Description |
|-------|-----------|-------------|
| 10-27 | Git Not Enabled state | Shows when `!gitStatus?.git_enabled` |
| 17-26 | Initialize button | Primary action to open modal |
| 29-166 | Initialize modal | Full-screen form with inputs |
| 54-68 | Repository owner input | GitHub username/org |
| 70-84 | Repository name input | Repo name |
| 87-98 | Create repo checkbox | Whether to create if doesn't exist |
| 100-111 | Private checkbox | Make repository private (if creating) |
| 113-137 | Info box | Explains what will happen + timing warning |
| 143-154 | Initialize button | Calls `initializeGitHub()` with form data |
| 350-385 | `initializeGitHub()` | Method with console logging |

**Key Methods**:

```javascript
// Line 350-385: Initialize GitHub Sync (with console logging)
const initializeGitHub = async () => {
  if (!repoOwner.value || !repoName.value) return

  initializing.value = true
  initializeError.value = null

  console.log('[GitPanel] Starting GitHub initialization...')

  try {
    const response = await agentsStore.initializeGitHub(props.agentName, {
      repo_owner: repoOwner.value,
      repo_name: repoName.value,
      create_repo: createRepo.value,
      private: privateRepo.value
    })

    console.log('[GitPanel] GitHub initialization successful:', response)

    // Success! Reload git status and close modal
    console.log('[GitPanel] Reloading git status...')
    await loadGitStatus()

    console.log('[GitPanel] Closing modal...')
    showInitializeModal.value = false

    // Clear form
    repoOwner.value = ''
    repoName.value = ''
  } catch (error) {
    console.error('[GitPanel] GitHub initialization failed:', error)
    initializeError.value = error.response?.data?.detail || error.message || 'Failed to initialize GitHub sync'
  } finally {
    console.log('[GitPanel] Initialization complete, setting initializing = false')
    initializing.value = false
  }
}
```

### State Management

**Location**: `src/frontend/src/stores/agents.js`

| Lines | Method | Description |
|-------|--------|-------------|
| 382-389 | `initializeGitHub()` | Store action with 120-second timeout |

```javascript
// Line 382-389: Initialize GitHub Sync (with timeout)
async initializeGitHub(name, config) {
  const authStore = useAuthStore()
  const response = await axios.post(`/api/agents/${name}/git/initialize`, config, {
    headers: authStore.authHeader,
    timeout: 120000 // 120 seconds (2 minutes) for git operations
  })
  return response.data
}
```

---

## Backend Layer

### Settings Routes - GitHub PAT Management

**Location**: `src/backend/routers/settings.py`

| Lines | Endpoint | Description |
|-------|----------|-------------|
| 43-48 | `get_github_pat()` | Helper to get PAT from settings or env |
| 337-388 | `PUT /api/settings/api-keys/github` | Save GitHub PAT to database |
| 426-538 | `POST /api/settings/api-keys/github/test` | Test PAT validity and permissions |

**GitHub PAT Test Flow**:

```python
# Line 426-537: Test GitHub PAT
async def test_github_pat(body: ApiKeyTest, ...):
    key = body.api_key.strip()

    # Validate format
    if not (key.startswith('ghp_') or key.startswith('github_pat_')):
        return {"valid": False, "error": "Invalid format"}

    # Test with GitHub API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {key}",
                "Accept": "application/vnd.github+json"
            }
        )

        if response.status_code == 200:
            data = response.json()
            is_fine_grained = key.startswith('github_pat_')

            # Check repo access
            if is_fine_grained:
                # Test by trying to list repos
                repos_response = await client.get("https://api.github.com/user/repos", ...)
                has_repo_access = repos_response.status_code == 200
            else:
                # Check X-OAuth-Scopes header for classic PAT
                scopes = response.headers.get("X-OAuth-Scopes", "").split(",")
                has_repo_access = "repo" in scopes or "public_repo" in scopes

            return {
                "valid": True,
                "username": data.get("login"),
                "token_type": "fine-grained" if is_fine_grained else "classic",
                "has_repo_access": has_repo_access
            }
```

### Git Routes - Initialize Endpoint

**Location**: `src/backend/routers/git.py`

| Lines | Component | Description |
|-------|-----------|-------------|
| 29-36 | `GitInitializeRequest` model | Request body schema |
| 284-596 | `POST /{agent_name}/git/initialize` | Main initialization endpoint |
| 324-344 | Orphaned record cleanup | Detects and removes orphaned DB records |
| 444-478 | Smart directory detection | Chooses workspace vs home directory |
| 536-549 | Git verification | Verifies git initialization before DB insert |

**Critical Bug Fixes**:

1. **Orphaned Record Cleanup** (Lines 324-344):
```python
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
```

2. **Smart Directory Detection** (Lines 444-478):
```python
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
```

3. **Git Verification Before DB Insert** (Lines 536-549):
```python
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
```

### Docker Service - Command Execution

**Location**: `src/backend/services/docker_service.py`

| Lines | Function | Description |
|-------|----------|-------------|
| 135-168 | `execute_command_in_container()` | Execute commands in container |

**Function Definition** (Lines 135-168):
```python
def execute_command_in_container(container_name: str, command: str, timeout: int = 60) -> dict:
    """Execute a command in a Docker container.

    Args:
        container_name: Name of the container (e.g., "agent-myagent")
        command: Command to execute
        timeout: Timeout in seconds

    Returns:
        Dictionary with 'exit_code' and 'output' keys
    """
    if not docker_client:
        return {"exit_code": 1, "output": "Docker client not available"}

    try:
        container = docker_client.containers.get(container_name)
        result = container.exec_run(
            command,
            user="developer",
            demux=False
        )

        # result.exit_code is the exit code
        # result.output is bytes, decode to string
        output = result.output.decode('utf-8') if isinstance(result.output, bytes) else str(result.output)

        return {
            "exit_code": result.exit_code,
            "output": output
        }
    except docker.errors.NotFound:
        return {"exit_code": 1, "output": f"Container {container_name} not found"}
    except Exception as e:
        return {"exit_code": 1, "output": f"Error executing command: {str(e)}"}
```

### Git Service - Database Operations

**Location**: `src/backend/services/git_service.py`

Key functions:

```python
def generate_instance_id() -> str:
    """Generate unique 8-character instance ID"""
    return secrets.token_hex(4)  # 8 hex chars

def generate_working_branch(agent_name: str, instance_id: str) -> str:
    """Generate working branch name: trinity/{name}/{instance_id}"""
    return f"trinity/{agent_name}/{instance_id}"

async def create_git_config_for_agent(agent_name: str, github_repo: str, instance_id: str):
    """Create agent_git_config record in database"""
    db.create_agent_git_config(
        agent_name=agent_name,
        github_repo=github_repo,
        working_branch=generate_working_branch(agent_name, instance_id),
        instance_id=instance_id
    )

def get_agent_git_config(agent_name: str):
    """Retrieve git config from database"""
    return db.get_agent_git_config(agent_name)
```

---

## MCP Layer

### MCP Tool - initialize_github_sync

**Location**: `src/mcp-server/src/tools/agents.ts`

| Lines | Component | Description |
|-------|-----------|-------------|
| 436-514 | `initializeGithubSync` tool | MCP tool definition |

**Tool Definition**:

```typescript
initializeGithubSync: {
  name: "initialize_github_sync",
  description:
    "Initialize GitHub synchronization for an agent. " +
    "Creates a GitHub repository (if requested), initializes git in workspace, " +
    "commits current state, pushes to GitHub, enables bidirectional sync. " +
    "Requires GitHub PAT configured in system settings with 'repo' scope. " +
    "Agent must be running.",
  parameters: z.object({
    agent_name: z.string().describe("Agent name"),
    repo_owner: z.string().describe("GitHub username or org"),
    repo_name: z.string().describe("Repository name"),
    create_repo: z.boolean().optional().default(true),
    private: z.boolean().optional().default(true),
    description: z.string().optional()
  }),
  execute: async (args, context) => {
    const authContext = context?.session;
    const apiClient = getClient(authContext);

    const response = await apiClient.request<GitInitializeResponse>(
      "POST",
      `/api/agents/${args.agent_name}/git/initialize`,
      {
        repo_owner: args.repo_owner,
        repo_name: args.repo_name,
        create_repo: args.create_repo ?? true,
        private: args.private ?? true,
        description: args.description
      }
    );

    return JSON.stringify(response, null, 2);
  }
}
```

**Example Usage**:

```json
{
  "name": "initialize_github_sync",
  "arguments": {
    "agent_name": "my-agent",
    "repo_owner": "your-username",
    "repo_name": "my-agent-workspace",
    "create_repo": true,
    "private": true,
    "description": "Agent workspace managed by Trinity"
  }
}
```

---

## Data Layer

### Database Schema

**Table**: `agent_git_config`

| Column | Type | Description |
|--------|------|-------------|
| `agent_name` | TEXT PRIMARY KEY | Agent identifier |
| `github_repo` | TEXT | Full repo name (owner/name) |
| `working_branch` | TEXT | Branch name (trinity/{name}/{id}) |
| `instance_id` | TEXT | Unique instance identifier (8 chars) |
| `created_at` | TIMESTAMP | When config was created |
| `last_sync_at` | TIMESTAMP | Last successful sync |
| `last_commit_sha` | TEXT | Last synced commit SHA |
| `sync_enabled` | BOOLEAN | Whether sync is active |

**Table**: `system_settings`

| Column | Type | Description |
|--------|------|-------------|
| `key` | TEXT PRIMARY KEY | Setting name |
| `value` | TEXT | Setting value |
| `updated_at` | TIMESTAMP | Last update time |

GitHub PAT stored as key: `github_pat`

---

## Side Effects

### Audit Logging

All operations are logged via the audit service:

```python
# Settings: Test PAT
await log_audit_event(
    event_type="system_settings",
    action="test_github_pat",
    user_id=current_user.username,
    result="success",
    details={
        "valid": True,
        "github_user": username,
        "token_type": "fine-grained" or "classic",
        "has_repo_access": bool
    }
)

# Settings: Save PAT
await log_audit_event(
    event_type="system_settings",
    action="update_github_pat",
    user_id=current_user.username,
    result="success",
    details={"key_masked": "...xxxx"}
)

# Git: Initialize
await log_audit_event(
    event_type="git_operation",
    action="initialize",
    user_id=current_user.username,
    agent_name=agent_name,
    result="success",
    details={
        "github_repo": repo_full_name,
        "working_branch": working_branch,
        "created_repo": bool
    }
)
```

### WebSocket Broadcasts

None - this is a one-time configuration operation

### GitHub API Calls

1. **Test PAT**: `GET https://api.github.com/user`
2. **Check repo exists**: `GET https://api.github.com/repos/{owner}/{name}`
3. **Create repo**: `POST https://api.github.com/user/repos`
4. **Push commits**: Git protocol via authenticated URL

---

## Error Handling

| Error Case | HTTP Status | Message | Recovery |
|------------|-------------|---------|----------|
| Agent not found | 404 | "Agent not found" | Create agent first |
| Agent not running | 400 | "Agent must be running to initialize Git sync" | Start agent |
| Not agent owner | 403 | "Only agent owners can initialize GitHub sync" | Share agent or login as owner |
| Already configured | 409 | "Git sync already configured for this agent. Repository: {repo}" | Cannot re-initialize |
| Orphaned DB record | - | Auto-cleanup + allow re-init | System detects and fixes automatically |
| No GitHub PAT | 400 | "GitHub Personal Access Token not configured. Please add it in Settings." | Configure PAT in Settings |
| Invalid PAT format | 400 | "Invalid token format" | Use PAT starting with ghp_ or github_pat_ |
| GitHub API error | 400 | "Failed to create GitHub repository: {error}" | Check PAT permissions |
| Git command failed | 500 | "Git command failed: {cmd}" | Check container logs |
| Repo creation failed | 400 | "Failed to create repository: {message}" | Check PAT has repo scope |
| Git verification failed | 500 | "Git initialization verification failed. Git directory not found" | Check container state |

---

## Security Considerations

### Authentication & Authorization

1. **Admin-only Settings access**: Only admins can configure GitHub PAT
   - Checked via `require_admin(current_user)` in settings routes

2. **Owner-only initialization**: Only agent owners can initialize Git sync
   - Checked via `db.can_user_share_agent(current_user.username, agent_name)`

3. **PAT storage**: Stored in system_settings table (not encrypted at rest)
   - Consider encryption for production deployments

4. **PAT masking**: Only last 4 characters shown in UI
   - Prevents accidental exposure

### GitHub PAT Requirements

**Classic PAT**: Requires `repo` scope
- Full control of private repositories
- Includes `repo:status`, `repo_deployment`, `public_repo`

**Fine-grained PAT**: Requires these permissions:
- **Repository permissions**:
  - Contents: Read and write
  - Metadata: Read-only (default)
  - Administration: Read and write (for creating repos)

### Git Authentication

Repository remote URL includes PAT:
```
https://oauth2:{PAT}@github.com/{owner}/{name}.git
```

This allows push/pull without interactive authentication.

**Security implications**:
- PAT is visible in git remote URL inside container
- Container compromise could expose PAT
- Use fine-grained PATs with minimal permissions
- Rotate PATs regularly

---

## Testing

### Prerequisites

1. **Running Trinity platform** with database and backend
2. **Admin user account** for Settings access
3. **GitHub account** with ability to create repositories
4. **Valid GitHub PAT** with `repo` scope (classic) or Contents + Administration (fine-grained)
5. **Test agent** that is running but doesn't have git sync enabled

### Test Steps

#### 1. Configure GitHub PAT

**Action**:
1. Login as admin user
2. Navigate to Settings page (`/settings`)
3. Scroll to "GitHub Personal Access Token (PAT)" section
4. Enter a valid GitHub PAT
5. Click "Test" button

**Expected**:
- Button shows loading spinner
- After 1-2 seconds, shows green checkmark
- Message displays: "Valid! GitHub user: {username}. ✓ Has repo scope" (classic) or "✓ Fine-grained PAT with repository permissions" (fine-grained)

**Verify**:
```bash
# Check database
sqlite3 ~/trinity-data/trinity.db "SELECT key, substr(value, 1, 10) || '...' FROM system_settings WHERE key = 'github_pat'"
# Should show: github_pat|ghp_...
```

**Action (continued)**:
6. Click "Save" button

**Expected**:
- Green success notification: "Settings saved successfully!"
- Input field clears
- Status shows: "Configured (from settings)" with masked value "...xxxx"

#### 2. Initialize Git Sync for Agent

**Action**:
1. Navigate to an agent's detail page (agent must be running)
2. Click "Git" tab
3. Verify message: "Git sync not enabled for this agent"
4. Click "Initialize GitHub Sync" button

**Expected**:
- Modal opens with form
- Form has fields: Repository Owner, Repository Name
- Checkboxes: "Create repository if it doesn't exist" (checked), "Make repository private" (checked)
- Info box explains what will happen and includes timing warning: "This may take 10-60 seconds depending on the size of your agent's files."

**Action (continued)**:
5. Enter repository owner: `your-github-username`
6. Enter repository name: `test-agent-workspace`
7. Ensure both checkboxes are checked
8. Click "Initialize" button

**Expected**:
- Button shows "Initializing..." with spinner
- Console logs show progress:
  - `[GitPanel] Starting GitHub initialization...`
  - `[GitPanel] GitHub initialization successful: {...}`
  - `[GitPanel] Reloading git status...`
  - `[GitPanel] Closing modal...`
  - `[GitPanel] Initialization complete, setting initializing = false`
- After 10-60 seconds (depending on workspace size):
  - Modal closes
  - Git tab shows repository information
  - Remote URL: `https://github.com/your-username/test-agent-workspace`
  - Branch indicator: `trinity/test-agent/xxxxxxxx` (8-char instance ID)
  - Status: "Synced" (green badge)
  - "Last Commit" section shows "Initial commit from Trinity Agent"

**Verify on GitHub**:
```bash
# Visit https://github.com/your-username/test-agent-workspace
# Should see:
# - Repository exists
# - Private badge (if selected)
# - Two branches: main, trinity/test-agent/xxxxxxxx
# - Commits on both branches
# - Agent files: CLAUDE.md, .claude/, .trinity/, .mcp.json
# - .gitignore excludes: .bashrc, .cache/, .ssh/ (if using home directory)
```

**Verify in Database**:
```bash
sqlite3 ~/trinity-data/trinity.db "SELECT * FROM agent_git_config WHERE agent_name = 'test-agent'"
# Should show config record with repo, branch, instance_id
```

**Verify Directory Detection**:
- Check backend logs for: `Using workspace directory with existing content: /home/developer/workspace` OR `Using home directory (agent's files are here): /home/developer`
- Check for: `Git initialization verified successfully in {directory}`

#### 3. MCP Tool Usage

**Action**:
1. Use Claude Code or MCP client
2. Call `initialize_github_sync` tool:
```json
{
  "agent_name": "another-agent",
  "repo_owner": "your-username",
  "repo_name": "another-agent-workspace",
  "create_repo": true,
  "private": true
}
```

**Expected**:
- Tool returns JSON with:
  - `success: true`
  - `github_repo: "your-username/another-agent-workspace"`
  - `working_branch: "trinity/another-agent/xxxxxxxx"`
  - `repo_url: "https://github.com/your-username/another-agent-workspace"`

**Verify**:
- Repository created on GitHub
- Agent has git sync enabled in UI

### Edge Cases

#### 1. Agent Not Running

**Action**: Try to initialize git sync for a stopped agent

**Expected**: Error message: "Agent must be running to initialize Git sync"

**Verify**: Modal shows error in red box

#### 2. Already Configured

**Action**: Try to initialize git sync for an agent that already has it

**Expected**: Error message: "Git sync already configured for this agent. Repository: {repo}"

**Verify**: Cannot re-initialize, must delete and recreate agent

#### 3. Orphaned Database Record (NEW)

**Action**:
1. Create orphaned DB record: Insert into `agent_git_config` without actually initializing git in container
2. Try to initialize git sync

**Expected**:
- System detects orphaned record
- Backend logs: `Warning: Found orphaned git config for {agent_name}. Cleaning up and allowing re-initialization.`
- Record deleted from database
- Initialization proceeds successfully

**Verify**: Check backend logs for cleanup message

#### 4. Empty Workspace / Home Directory Detection (NEW)

**Action**: Initialize git sync for an agent with:
- **Case A**: Empty `/home/developer/workspace/` directory
- **Case B**: No `/home/developer/workspace/` directory at all

**Expected**:
- System detects workspace is empty or doesn't exist
- Backend logs: `Using home directory (agent's files are here): /home/developer`
- `.gitignore` created with system file exclusions
- Agent files (CLAUDE.md, .claude/, .trinity/, .mcp.json) pushed to GitHub
- System files (.bashrc, .ssh/, .cache/) excluded via .gitignore

**Verify**:
- Check GitHub repo contains agent files but not system files
- Check for `.gitignore` in repository root

#### 5. No GitHub PAT

**Action**:
1. Delete GitHub PAT from settings: `DELETE /api/settings/api-keys/github`
2. Try to initialize git sync

**Expected**: Error message: "GitHub Personal Access Token not configured. Please add it in Settings."

#### 6. Invalid PAT

**Action**: Try to save a PAT that doesn't start with `ghp_` or `github_pat_`

**Expected**: Error message: "Invalid token format. GitHub PATs start with 'ghp_' or 'github_pat_'"

#### 7. Insufficient Permissions

**Action**: Use a PAT without `repo` scope (classic) or without Contents/Administration (fine-grained)

**Expected**:
- Test shows: "⚠️ Missing repo scope" (classic) or "⚠️ Missing repository permissions" (fine-grained)
- Initialize fails: "Failed to create GitHub repository: Bad credentials or insufficient permissions"

#### 8. Repository Already Exists

**Action**:
1. Create repository on GitHub manually
2. Initialize git sync with same owner/name

**Expected**: Initialization succeeds, uses existing repository

**Verify**: Check GitHub - should see Trinity's initial commit pushed

#### 9. Large Agent Workspace (NEW)

**Action**: Initialize git sync for an agent with large `.claude/` directory (many sessions, large memory files)

**Expected**:
- Frontend timeout set to 120 seconds (2 minutes)
- Console logs track progress
- Operation completes successfully within timeout
- No frontend timeout error

**Verify**:
- Check browser console for timing logs
- Verify all files pushed to GitHub

#### 10. Timeout Edge Case (NEW)

**Action**: Initialize git sync for an agent with extremely large workspace (>500MB)

**Expected**:
- If operation takes >120 seconds, frontend shows timeout error
- Backend may still complete successfully (operations continue)
- User can reload page and see git sync enabled

**Recovery**: Increase timeout in `stores/agents.js:366` if needed

---

## Troubleshooting

### Issue: Frontend Timeout

**Symptoms**:
- Modal shows "Initializing..." for >2 minutes
- Error appears: "timeout of 120000ms exceeded"
- Agent may actually have git initialized successfully

**Root Cause**: Large `.claude/` directory or slow GitHub connection

**Verification**:
```bash
# Check if git was actually initialized
docker exec agent-{name} bash -c "cd /home/developer && git status"

# Check backend logs
docker logs trinity-backend | grep "Git initialization verified"
```

**Solution**:
1. If git is initialized but frontend timed out: Just reload the page
2. If timeout is consistent: Increase timeout in `src/frontend/src/stores/agents.js:366` (currently 120000ms)
3. If using slow network: Consider using GitHub CLI for initial push, then enable sync

### Issue: Empty Repository

**Symptoms**:
- Repository created on GitHub but has no files
- Commits exist but no agent files visible

**Root Cause**: Git initialized in wrong directory (empty workspace instead of home)

**Verification**:
```bash
# Check where git was initialized
docker exec agent-{name} bash -c "find /home/developer -name .git -type d"

# Check what was committed
docker exec agent-{name} bash -c "cd /home/developer && git log --stat"
```

**Solution**:
- FIXED in latest version with smart directory detection
- System now checks if workspace has content and falls back to home directory
- System creates .gitignore to exclude system files

### Issue: Orphaned Database Records

**Symptoms**:
- Error: "Git sync already configured" but git not actually initialized
- Cannot re-initialize git sync
- Git tab shows "Agent must be running" even when agent is running

**Root Cause**: Database record created but git initialization failed

**Verification**:
```bash
# Check database
sqlite3 ~/trinity-data/trinity.db "SELECT * FROM agent_git_config WHERE agent_name = '{name}'"

# Check if git actually exists in container
docker exec agent-{name} bash -c "[ -d /home/developer/.git ] && echo exists || echo notexists"
```

**Solution**:
- FIXED in latest version with auto-cleanup
- System detects orphaned records and removes them automatically
- Allows re-initialization after failed attempts

---

## Testing Status

**Status**: ✅ Working (as of 2025-12-26)

**Recent Bug Fixes** (2025-12-26):
- Fixed empty repositories: Smart directory detection chooses correct location (git.py Lines 444-478)
- Fixed orphaned records: Auto-cleanup of DB records when git doesn't exist (git.py Lines 324-344)
- Fixed timeout issue: Increased frontend timeout to 120 seconds + console logging (GitPanel.vue Lines 350-385, agents.js Lines 382-389)
- Fixed verification: Git initialization verified before DB insert (git.py Lines 536-549)
- Fixed system files: Created .gitignore to exclude .bashrc, .ssh/, etc. (git.py Lines 463-478)

**Test Coverage**:
- ✅ Settings UI: PAT configuration and testing
- ✅ GitPanel UI: Modal form and initialization flow
- ✅ Backend: Repository creation and git commands
- ✅ Smart directory detection: Workspace vs home directory
- ✅ Orphaned record cleanup: Auto-detection and removal
- ✅ Git verification: Pre-DB insert validation
- ✅ Timeout handling: 120-second frontend timeout
- ✅ MCP Tool: Programmatic initialization
- ✅ Error handling: All edge cases covered
- ✅ Database persistence: Config stored correctly
- ✅ Audit logging: All operations logged

**Known Issues**: None

**Verified Successfully**:
- Repository: `abilityai/booboob`
- Directory used: `/home/developer`
- Files pushed: CLAUDE.md, .claude/, .trinity/, .mcp.json, .gitignore (17+ files)
- System files excluded: .bashrc, .cache/, .ssh/ (via .gitignore)
- Branches: main, trinity/{agent}/{id}
- Clean git status with 2 commits

---

## Related Flows

- **Upstream**: [credential-injection.md](credential-injection.md) - GitHub PAT stored via credentials system
- **Downstream**: [github-sync.md](github-sync.md) - Bidirectional sync after initialization
- **Related**: [agent-lifecycle.md](agent-lifecycle.md) - Git sync can be enabled during agent creation with `github:` template prefix

---

## Implementation Notes

### Working Branch Strategy

Each agent instance gets a unique working branch:
```
trinity/{agent-name}/{instance-id}
```

**Benefits**:
- Multiple instances can work on same repo without conflicts
- Clear ownership of changes
- Easy to create PRs from working branch to main
- Instance ID ensures uniqueness across restarts

### Repository Structure

After initialization:
```
your-repo/
├── .git/
├── .gitignore (if using home directory)
├── CLAUDE.md
├── .claude/
├── .trinity/
├── .mcp.json
└── (any template-provided files)
```

**Branches**:
- `main`: Initial commit from Trinity, force-pushed
- `trinity/{name}/{id}`: Working branch, auto-created

**Files Excluded** (when using home directory):
- `.bash_logout`
- `.bashrc`
- `.profile`
- `.bash_history`
- `.cache/`
- `.local/`
- `.npm/`
- `.ssh/`

### Directory Detection Logic

The system uses smart detection to find the correct directory:

1. **Check workspace**: Does `/home/developer/workspace` exist and have content?
   - Yes → Use workspace
   - No → Use home directory

2. **If using home**: Create `.gitignore` to exclude system files

3. **Verify**: Run `git rev-parse --git-dir` before creating DB record

This fixes the critical "empty repository" bug where git was initialized in an empty workspace while agent files were in the home directory.

### Git Authentication

PAT embedded in remote URL allows push/pull without interactive auth:
```bash
git remote add origin https://oauth2:{PAT}@github.com/{owner}/{name}.git
```

This works with both classic and fine-grained PATs.

### GitHub API Rate Limits

- **Unauthenticated**: 60 requests/hour
- **Authenticated**: 5,000 requests/hour
- **Fine-grained PAT**: 5,000 requests/hour per repo

Testing and initialization count as:
- Test: 1-2 API calls
- Initialize: 2-3 API calls (check + create)

---

## Future Enhancements

### Potential Improvements

1. **PAT Encryption**: Encrypt GitHub PAT in database using SECRET_KEY
2. **OAuth App Flow**: Use GitHub OAuth app instead of PATs for better security
3. **Branch Protection**: Automatically configure branch protection rules
4. **PR Automation**: Auto-create PR when sync happens
5. **Multi-repo Support**: Allow agent to sync to multiple repositories
6. **Selective Sync**: Choose which files/directories to sync
7. **Sync Conflicts UI**: Better handling of merge conflicts in UI
8. **Repository Templates**: Pre-configured repo templates with Actions, README, etc.
9. **Progress Indicator**: Show real-time progress during initialization (file count, upload progress)
10. **Workspace Detection UI**: Show which directory will be used before initialization

### GitHub Apps Integration

Consider migrating from PATs to GitHub Apps for:
- Better security (short-lived tokens)
- Granular permissions per installation
- Activity appears as bot user
- Higher rate limits
- Revocable by organization admins

---

## References

- **GitHub PAT Documentation**: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
- **GitHub REST API**: https://docs.github.com/en/rest
- **Fine-grained PAT Permissions**: https://docs.github.com/en/rest/overview/permissions-required-for-fine-grained-personal-access-tokens
- **Git Reference**: https://git-scm.com/docs
