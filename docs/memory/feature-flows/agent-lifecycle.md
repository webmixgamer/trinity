# Feature: Agent Lifecycle

## Overview
Complete lifecycle management for Trinity agents: create, start, stop, and delete Docker containers with credential injection, network isolation, Trinity meta-prompt injection, and WebSocket broadcasts.

## User Story
As a Trinity platform user, I want to create, start, stop, and delete agents so that I can manage isolated Claude Code execution environments with custom configurations, credentials, and Trinity planning capabilities.

---

## Entry Points

### Create Agent
- **UI**: `src/frontend/src/views/Agents.vue:19-24` - "Create Agent" button
- **API**: `POST /api/agents`

### Start Agent
- **UI**: `src/frontend/src/views/AgentDetail.vue:44-55` - Start button (when stopped)
- **API**: `POST /api/agents/{agent_name}/start`

### Stop Agent
- **UI**: `src/frontend/src/views/AgentDetail.vue:56-67` - Stop button (when running)
- **API**: `POST /api/agents/{agent_name}/stop`

### Delete Agent
- **UI**: `src/frontend/src/views/AgentDetail.vue:68-77` - Delete button (trash icon)
- **API**: `DELETE /api/agents/{agent_name}`

---

## Frontend Layer

### Components

**Agents List View** - `src/frontend/src/views/Agents.vue`
- Line 19-24: Create Agent button opens modal
- Line 56-67: Start agent inline button with spinner
- Line 68-79: Stop agent inline button with spinner
- Line 117-128: `startAgent()` method
- Line 130-141: `stopAgent()` method

**Agent Detail View** - `src/frontend/src/views/AgentDetail.vue`
- Line 44-55: Start button (conditional on `agent.status === 'stopped'`)
- Line 56-67: Stop button (conditional on `agent.status === 'running'`)
- Line 68-77: Delete button (conditional on `agent.can_delete`)
- Line 825-837: `startAgent()` method
- Line 839-851: `stopAgent()` method
- Line 853-862: `deleteAgent()` method

**Create Agent Modal** - `src/frontend/src/components/CreateAgentModal.vue` (Updated 2025-12-07)
- Line 9: Form submit calls `createAgent()`
- Line 15-22: Agent name input
- Line 26-133: Template selection (blank, GitHub, local)
- Lines 173-178: **NEW** `initialTemplate` prop - Pre-selects template when modal opens
- Line 180: **NEW** `emit('created', agent)` - Emits created agent for navigation
- Lines 189-192: Watch for `initialTemplate` prop changes
- Lines 238-260: `createAgent()` method - emits `created` event on success

### State Management (`src/frontend/src/stores/agents.js`)

```javascript
// Line 58-74: Create agent
async createAgent(config) {
  const response = await axios.post('/api/agents', config, {
    headers: authStore.authHeader
  })
  this.agents.push(response.data)
  return response.data
}

// Line 76-91: Delete agent
async deleteAgent(name) {
  await axios.delete(`/api/agents/${name}`, {
    headers: authStore.authHeader
  })
  this.agents = this.agents.filter(agent => agent.name !== name)
}

// Line 93-107: Start agent
async startAgent(name) {
  const response = await axios.post(`/api/agents/${name}/start`, {}, {
    headers: authStore.authHeader
  })
  const agent = this.agents.find(a => a.name === name)
  if (agent) agent.status = 'running'
  return { success: true, message: response.data?.message }
}

// Line 109-123: Stop agent
async stopAgent(name) {
  const response = await axios.post(`/api/agents/${name}/stop`, {}, {
    headers: authStore.authHeader
  })
  const agent = this.agents.find(a => a.name === name)
  if (agent) agent.status = 'stopped'
  return { success: true, message: response.data?.message }
}
```

---

## Backend Layer

### Router Module
All agent endpoints are now in **modular router**: `src/backend/routers/agents.py`

The router is registered in `src/backend/main.py` with prefix `/api/agents`.

### Pydantic Models (`src/backend/models.py:9-39`)

```python
class AgentConfig(BaseModel):
    name: str
    type: Optional[str] = "business-assistant"
    base_image: str = "trinity-agent-base:latest"
    resources: Optional[dict] = {"cpu": "2", "memory": "4g"}
    tools: Optional[List[str]] = ["filesystem", "web_search"]
    mcp_servers: Optional[List[str]] = []
    custom_instructions: Optional[str] = None
    port: Optional[int] = None  # SSH port (auto-assigned)
    template: Optional[str] = None
    github_repo: Optional[str] = None  # GitHub-native agent support
    github_credential_id: Optional[str] = None

class AgentStatus(BaseModel):
    name: str
    type: str
    status: str  # "running" | "stopped"
    port: int    # SSH port only
    created: datetime
    resources: dict
    container_id: Optional[str] = None
    template: Optional[str] = None
```

### Endpoints

#### Create Agent (`src/backend/routers/agents.py:272-571`)
```python
@router.post("")
async def create_agent_endpoint(config: AgentConfig, request: Request, current_user: User = Depends(get_current_user)):
```

**Business Logic:**
1. **Sanitize name** (line 275-279): Lowercase, replace special chars with hyphens via `sanitize_agent_name()`
2. **Check existence** (line 281-282): Query Docker for existing container via `get_agent_by_name()`
3. **Load template** (line 290-339): GitHub or local template processing
4. **Auto-assign port** (line 341-342): Find next available SSH port (2290+) via `get_next_available_port()`
5. **Get credentials** (line 344): `credential_manager.get_agent_credentials()`
6. **Generate credential files** (line 354-367): Process template placeholders via `generate_credential_files()`
7. **Create MCP API key** (line 406-419): Generate agent-scoped Trinity MCP access key
8. **Build env vars** (line 421-456): ANTHROPIC_API_KEY, MCP server credentials, GitHub repo/PAT
9. **Mount Trinity meta-prompt** (line 472-477): Mount `/trinity-meta-prompt` volume for planning commands
10. **Create container** (line 479-504): Docker SDK `containers.run()` with security options
11. **Register ownership** (line 522): `db.register_agent_owner(current_user.username)`
12. **Create git config** (line 524-534): For GitHub-native agents (Phase 7)
13. **Broadcast WebSocket** (line 508-520): `agent_created` event
14. **Audit log** (line 536-551): `event_type="agent_management", action="create"`

#### Delete Agent (`src/backend/routers/agents.py:574-631`)
```python
@router.delete("/{agent_name}")
async def delete_agent_endpoint(agent_name: str, ...):
    # Authorization check: owner or admin (line 577-587)
    if not db.can_user_delete_agent(current_user.username, agent_name):
        raise HTTPException(403, "Permission denied")

    container = get_agent_container(agent_name)
    container.stop()
    container.remove()

    # Delete schedules (line 599-603)
    schedules = db.list_agent_schedules(agent_name)
    for schedule in schedules:
        scheduler_service.remove_schedule(schedule.id)
    db.delete_agent_schedules(agent_name)

    # Delete git config (line 605-606)
    git_service.delete_agent_git_config(agent_name)

    # Delete MCP API key (line 608-612)
    db.delete_agent_mcp_api_key(agent_name)

    # Delete ownership (line 614) - cascades to shares
    db.delete_agent_ownership(agent_name)

    # Broadcast WebSocket (line 616-620), audit log (line 622-629)
```

#### Start Agent (`src/backend/routers/agents.py:634-678`)
```python
@router.post("/{agent_name}/start")
async def start_agent_endpoint(agent_name: str, ...):
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    container.start()

    # NEW: Trinity meta-prompt injection (line 644-648)
    # Injects planning commands and creates directory structure
    trinity_result = await inject_trinity_meta_prompt(agent_name)
    trinity_status = trinity_result.get("status", "unknown")

    # Broadcast WebSocket with injection status (line 650-654)
    if manager:
        await manager.broadcast(json.dumps({
            "event": "agent_started",
            "data": {"name": agent_name, "trinity_injection": trinity_status}
        }))

    # Audit log with injection status (line 656-664)
    await log_audit_event(..., details={"trinity_injection": trinity_status})
```

**Trinity Meta-Prompt Injection Helper** (`src/backend/routers/agents.py:49-97`)
```python
async def inject_trinity_meta_prompt(agent_name: str, max_retries: int = 5, retry_delay: float = 2.0) -> dict:
    """
    Inject Trinity meta-prompt into an agent via its internal API.
    Called after agent startup to inject planning commands.

    - Retries up to 5 times with 2s delay (agent server startup)
    - Calls agent's POST /api/trinity/inject endpoint
    - Returns {"status": "success|error", ...}
    """
    agent_url = f"http://agent-{agent_name}:8000"
    # ... retry logic with httpx.AsyncClient
    response = await client.post(f"{agent_url}/api/trinity/inject")
```

#### Stop Agent (`src/backend/routers/agents.py:681-718`)
```python
@router.post("/{agent_name}/stop")
async def stop_agent_endpoint(agent_name: str, ...):
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    container.stop()

    # Broadcast WebSocket (line 691-695), audit log (line 697-704)
```

### Docker Service (`src/backend/services/docker_service.py`)

**Key Functions:**

| Function | Line | Purpose |
|----------|------|---------|
| `get_agent_container()` | 18-28 | Get container by name from Docker API |
| `get_agent_status_from_container()` | 31-58 | Convert Docker container to AgentStatus model |
| `list_all_agents()` | 61-73 | List all containers with `trinity.platform=agent` label |
| `get_agent_by_name()` | 76-81 | Get specific agent status |
| `get_next_available_port()` | 84-88 | Find next SSH port (2290+) |

**Status Normalization (line 38-44):**
```python
# Docker statuses: created, running, paused, restarting, removing, exited, dead
docker_status = container.status
if docker_status in ("exited", "dead", "created"):
    normalized_status = "stopped"
elif docker_status == "running":
    normalized_status = "running"
else:
    normalized_status = docker_status  # paused, restarting, etc.
```

---

## Database Layer (`src/backend/database.py`)

### Tables

**agent_ownership**
```sql
CREATE TABLE agent_ownership (
    id INTEGER PRIMARY KEY,
    agent_name TEXT UNIQUE,
    owner_id INTEGER REFERENCES users(id),
    created_at TEXT
)
```

**agent_schedules** (for scheduled tasks)
```sql
CREATE TABLE agent_schedules (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    schedule_type TEXT NOT NULL,
    cron_expression TEXT,
    ...
)
```

**agent_git_configs** (Phase 7 - GitHub-native agents)
```sql
CREATE TABLE agent_git_configs (
    agent_name TEXT PRIMARY KEY,
    github_repo TEXT NOT NULL,
    working_branch TEXT NOT NULL,
    instance_id TEXT NOT NULL,
    ...
)
```

**agent_mcp_api_keys** (Agent-to-Agent collaboration)
```sql
CREATE TABLE agent_mcp_api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT UNIQUE NOT NULL,
    api_key TEXT UNIQUE NOT NULL,
    ...
)
```

### Operations

| Method | Line | Purpose |
|--------|------|---------|
| `register_agent_owner()` | 479-496 | Record owner on creation |
| `delete_agent_ownership()` | 526-535 | Delete ownership + cascade shares |
| `can_user_delete_agent()` | 558-572 | Authorization check (owner or admin) |
| `get_agent_owner()` | 498-524 | Get owner info |
| `can_user_access_agent()` | 537-556 | Check if user can view agent |

---

## Docker Configuration

### Container Labels (`src/backend/routers/agents.py:486-495`)
| Label | Purpose |
|-------|---------|
| `trinity.platform=agent` | Identifies Trinity agents |
| `trinity.agent-name` | Agent name |
| `trinity.agent-type` | Type (business-assistant, etc.) |
| `trinity.ssh-port` | SSH port number |
| `trinity.cpu` | CPU allocation |
| `trinity.memory` | Memory limit |
| `trinity.created` | Creation timestamp (ISO format) |
| `trinity.template` | Template used (empty string if none) |

### Security Options (line 496-500)
```python
security_opt=['no-new-privileges:true', 'apparmor:docker-default'],
cap_drop=['ALL'],
cap_add=['NET_BIND_SERVICE'],
read_only=False,
tmpfs={'/tmp': 'noexec,nosuid,size=100m'}
```

### Network Isolation (line 501)
- Network: `trinity-agent-network` (Docker network)
- Only SSH port (22) mapped externally via `ports={'22/tcp': config.port}`
- UI port (8000) NOT exposed - accessed via backend proxy at `/api/agents/{name}/ui/`

### Resource Limits (line 502-503)
```python
mem_limit=config.resources.get('memory', '4Gi'),
cpu_count=int(config.resources.get('cpu', '2'))
```

### Trinity Meta-Prompt Volume (line 472-477)
```python
# Mount Trinity meta-prompt for task DAG planning (Phase 9)
container_meta_prompt_path = Path("/trinity-meta-prompt")
host_meta_prompt_path = os.getenv("HOST_META_PROMPT_PATH", "./config/trinity-meta-prompt")
if container_meta_prompt_path.exists():
    volumes[host_meta_prompt_path] = {'bind': '/trinity-meta-prompt', 'mode': 'ro'}
```

---

## Side Effects

### WebSocket Broadcasts
| Event | Payload | Trigger |
|-------|---------|---------|
| `agent_created` | `{name, type, status, port, created, resources, container_id}` | After container.run() (line 508-520) |
| `agent_started` | `{name, trinity_injection}` | After container.start() + Trinity injection (line 650-654) |
| `agent_stopped` | `{name}` | After container.stop() (line 691-695) |
| `agent_deleted` | `{name}` | After container.remove() (line 616-620) |

### Audit Logging
```python
await log_audit_event(
    event_type="agent_management",
    action="create|start|stop|delete",
    user_id=current_user.username,
    agent_name=config.name,
    resource=f"agent-{config.name}",
    ip_address=request.client.host if request.client else None,
    result="success|failed|unauthorized",
    details={...}
)
```

### Cascading Deletes (on agent deletion)
1. **Schedules**: All scheduled tasks removed from scheduler and database
2. **Git Config**: GitHub sync configuration deleted
3. **MCP API Key**: Agent's Trinity MCP access key revoked
4. **Ownership**: Ownership record deleted
5. **Shares**: All shares cascade deleted via foreign key constraint

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Invalid agent name | 400 | "Invalid agent name - must contain at least one alphanumeric character" |
| Agent already exists | 400 | "Agent already exists" |
| Agent not found | 404 | "Agent not found" |
| Permission denied (delete) | 403 | "You don't have permission to delete this agent" |
| Docker error | 500 | "Failed to create/start/stop agent: {error}" |
| Docker unavailable | 503 | "Docker not available - cannot create agents in demo mode" |

---

## Security Considerations

1. **Authentication**: All endpoints require `Depends(get_current_user)`
2. **Authorization**:
   - Delete requires `can_user_delete_agent()` (owner or admin)
   - Access requires `can_user_access_agent()` (owner, shared user, or admin)
3. **Container Security**: CAP_DROP ALL, no-new-privileges, AppArmor
4. **Network Isolation**: Agent UI not exposed externally, accessed via backend proxy
5. **Credential Protection**: Never logged, injected at runtime via environment variables
6. **Agent-scoped MCP Keys**: Each agent gets unique API key for Trinity MCP access

---

## Testing

**Prerequisites**:
- [ ] Backend running at http://localhost:8000
- [ ] Frontend running at http://localhost:3000
- [ ] Docker daemon running
- [ ] Logged in as test@example.com

**Test Steps**:

### 1. Create Agent
**Action**:
- Navigate to http://localhost:3000
- Click "Create Agent" button
- Enter name: "test-lifecycle"
- Select template: "local:default"
- Click "Create"

**Expected**:
- Agent appears in agent list
- Status shows "running"
- SSH port assigned (2290+)
- WebSocket broadcast received

**Verify**:
- [ ] UI shows agent card with name "test-lifecycle"
- [ ] API: `curl http://localhost:8000/api/agents` includes agent
- [ ] Docker: `docker ps | grep test-lifecycle` shows container
- [ ] Database: Query agent_ownership for record
- [ ] Container has correct labels: `docker inspect agent-test-lifecycle | grep trinity`

### 2. Start Agent
**Action**: Click "Start" button on stopped agent

**Expected**:
- Button shows loading spinner
- Status changes to "running"
- Toast notification appears
- WebSocket broadcast received with `trinity_injection` status
- Trinity meta-prompt injected into agent

**Verify**:
- [ ] UI shows "running" badge
- [ ] Docker: `docker inspect agent-test-lifecycle | grep '"Running": true'`
- [ ] Container accessible on internal network
- [ ] Audit log has `agent_management:start` event with `trinity_injection` in details
- [ ] Trinity injection: Agent has `/home/developer/.trinity/` directory structure
- [ ] Trinity injection: Agent has planning commands available (check via chat)

### 3. Stop Agent
**Action**: Click "Stop" button

**Expected**:
- Status changes to "stopped"
- Container stops but remains
- WebSocket broadcast received

**Verify**:
- [ ] UI shows "stopped" status
- [ ] Docker: Container exists but not running
- [ ] Can start again without recreating
- [ ] Audit log has `agent_management:stop` event

### 4. Delete Agent
**Action**: Click trash icon, confirm deletion

**Expected**:
- Agent removed
- Container deleted
- All associated resources cleaned up
- Redirected to dashboard

**Verify**:
- [ ] UI: Agent not in list
- [ ] Docker: `docker ps -a | grep test-lifecycle` returns nothing
- [ ] Database: No ownership record
- [ ] Sharing records cascade deleted
- [ ] Schedules deleted
- [ ] MCP API key deleted
- [ ] Audit log has `agent_management:delete` event

**Edge Cases**:
- [ ] Duplicate name: Try creating "test-lifecycle" twice (should fail with 400)
- [ ] Unauthorized delete: Login as different user, try to delete (should fail with 403)
- [ ] Start running agent: Already running agent start should be idempotent
- [ ] Invalid template: Create with "github:invalid/repo" (should fail gracefully)
- [ ] Name sanitization: Create agent with name "Test Agent!" (should become "test-agent")

**Cleanup**:
- [ ] Delete any remaining test agents
- [ ] `docker ps -a | grep test-` - verify no orphans

---

**Last Tested**: 2025-12-07
**Status**: Working (all CRUD operations functional with Trinity injection)
**Issues**: None - agent lifecycle fully operational with modular router architecture and Trinity meta-prompt injection

---

## Revision History

| Date | Changes |
|------|---------|
| 2025-12-09 | **Critical Bug Fix - File Persistence**: Added checks in `startup.sh` to skip re-cloning if repo already exists. Git-sync agents check for `.git` directory; non-git-sync agents check for `.trinity-initialized` marker. Files now persist across container restarts (Pillar III compliance). |
| 2025-12-07 | **CreateAgentModal enhancements**: Added `initialTemplate` prop for pre-selection, `created` event for navigation after success. Used by Templates.vue to open modal with template pre-selected and navigate to new agent's detail page. |

---

## Agent Container Startup Flow

### Container Initialization (`docker/base-image/startup.sh`)

When an agent container starts, it follows this initialization flow:

1. **GitHub Repository Handling** (if `GITHUB_REPO` and `GITHUB_PAT` are set):
   - **Git-Sync Enabled** (`GIT_SYNC_ENABLED=true`):
     - Checks if `/home/developer/.git` directory exists (persistent volume)
     - If exists: Skips cloning, runs `git fetch origin` to sync with remote
     - If not exists: Clones full repo, creates working branch, configures git user
     - Restores infrastructure files from base image backup
   - **Git-Sync Disabled**:
     - Checks if `/home/developer/.trinity-initialized` marker exists
     - If exists: Skips cloning, preserves user files on persistent volume
     - If not exists: Shallow clones repo, copies files, creates `.trinity-initialized` marker

2. **Local Template Handling** (if `TEMPLATE_NAME` and `/template` exists):
   - Copies `.claude/`, `CLAUDE.md`, `README.md`, `resources/`, `scripts/`, `memory/`

3. **Credential File Injection** (from `/generated-creds` volume):
   - Copies `.mcp.json`, `.env`, and other generated config files

4. **Service Startup**:
   - SSH server (if `ENABLE_SSH=true`)
   - Agent Web Server on port 8000 (if `ENABLE_AGENT_UI=true`)

### File Persistence (Bug Fix 2025-12-09)

**Problem**: Files created by agents were lost on container restart because `startup.sh` unconditionally re-cloned repositories, overwriting all user-created files.

**Solution**: Added persistence checks before cloning:

```bash
# For git-sync agents: Check for existing .git directory
if [ -d "/home/developer/.git" ]; then
    echo "Repository already exists on persistent volume - skipping clone"
    # Just fetch from remote, don't re-clone
fi

# For non-git-sync agents: Check for initialization marker
if [ -f "/home/developer/.trinity-initialized" ]; then
    echo "Agent workspace already initialized - preserving user files"
    # Skip cloning entirely
fi
```

**Key Files**:
- `docker/base-image/startup.sh:14-124` - Repository initialization with persistence checks
- `.trinity-initialized` - Marker file created after first-time initialization
- Per-agent Docker volume `agent-{name}-workspace` mounted to `/home/developer`

**Pillar III Compliance**: Agent workspace now survives restarts as required by Deep Agency spec (Persistent Memory pillar).

---

## Related Flows

- **Upstream**: Authentication Flow (JWT required via `get_current_user`)
- **Downstream**: Agent Chat, Credential Injection, Activity Monitoring, Trinity Injection
- **Related**: Agent Sharing (ownership and access control)
- **Related**: Git Sync (GitHub-native agents)
- **Related**: Agent Scheduling (scheduled task management)
- **Related**: Task DAG Planning (Trinity meta-prompt provides planning commands - Phase 9)
