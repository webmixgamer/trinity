# Feature: Agent-to-Agent Permissions System

## Overview

Fine-grained permission control for agent-to-agent communication. Allows owners to specify which agents their agents can collaborate with via Trinity MCP tools (`list_agents`, `chat_with_agent`). Enforced at the MCP server layer.

**Requirement**: 9.10 - Agent-to-Agent Collaboration Permissions
**Phase**: 9.10
**Implemented**: 2025-12-10

## User Story

As an agent owner, I want to control which other agents my agent can communicate with, so that I can prevent unintended agent collaboration and maintain security boundaries between agent workloads.

## Access Control Model

### Default Behavior (Option B: Same-Owner Agents)
When an agent is created, it automatically receives **bidirectional permissions** with all other agents owned by the same user.

### Permission Rules
1. **Self-call**: Always allowed (agent can call itself)
2. **Permitted list**: Agent can only communicate with agents in its permission list
3. **Explicit only**: Even same-owner agents need explicit permission (after initial grant)
4. **Unidirectional**: Permissions are directional (A->B does not imply B->A)

## Entry Points

### User Configuration (UI)
- **UI**: `src/frontend/src/views/AgentDetail.vue:255-267` - Permissions tab button
- **Tab Content**: `src/frontend/src/views/AgentDetail.vue:795-891` - Checkbox list UI

### MCP Tool Enforcement
- **list_agents**: `src/mcp-server/src/tools/agents.ts:50-71` - Filters visible agents
- **chat_with_agent**: `src/mcp-server/src/tools/chat.ts:26-90` - Blocks unauthorized calls

### Backend API
- `GET /api/agents/{name}/permissions` - List permitted agents
- `PUT /api/agents/{name}/permissions` - Bulk set permissions
- `POST /api/agents/{name}/permissions/{target}` - Add single permission
- `DELETE /api/agents/{name}/permissions/{target}` - Remove permission

---

## Frontend Layer

### Components

#### AgentDetail.vue:255-267 - Permissions Tab Button
```vue
<button
  v-if="agent.can_share"
  @click="activeTab = 'permissions'"
  :class="[...]"
>
  Permissions
  <span v-if="permittedAgentsCount > 0" class="...bg-purple-100...">
    {{ permittedAgentsCount }}
  </span>
</button>
```

#### AgentDetail.vue:795-891 - Permissions Tab Content
- Checkbox list of all other accessible agents
- "Allow All" / "Allow None" bulk actions
- Save button with dirty state tracking
- Success/error message display

### State Management

#### `src/frontend/src/stores/agents.js:269-285`

```javascript
// Get permissions for an agent
async getAgentPermissions(name) {
  const authStore = useAuthStore()
  const response = await axios.get(`/api/agents/${name}/permissions`, {
    headers: authStore.authHeader
  })
  return response.data
}

// Set permissions (full replacement)
async setAgentPermissions(name, permittedAgents) {
  const authStore = useAuthStore()
  const response = await axios.put(`/api/agents/${name}/permissions`,
    { permitted_agents: permittedAgents },
    { headers: authStore.authHeader }
  )
  return response.data
}
```

### Component Methods

#### AgentDetail.vue:1797-1855 - Permission Methods

```javascript
// Load permissions from backend
const loadPermissions = async () => {
  permissionsLoading.value = true
  const response = await agentsStore.getAgentPermissions(agent.value.name)
  availableAgents.value = response.available_agents || []
  permissionsDirty.value = false
  permissionsLoading.value = false
}

// Save permissions to backend
const savePermissions = async () => {
  permissionsSaving.value = true
  const permittedAgentNames = availableAgents.value
    .filter(a => a.permitted)
    .map(a => a.name)
  await agentsStore.setAgentPermissions(agent.value.name, permittedAgentNames)
  permissionsDirty.value = false
  permissionsSaving.value = false
}

// Bulk actions
const allowAllAgents = () => {
  availableAgents.value.forEach(a => { a.permitted = true })
  permissionsDirty.value = true
}

const allowNoAgents = () => {
  availableAgents.value.forEach(a => { a.permitted = false })
  permissionsDirty.value = true
}
```

---

## Backend Layer

### Endpoint: GET /api/agents/{name}/permissions

**File**: `src/backend/routers/agents.py:1743-1793`

```python
@router.get("/{agent_name}/permissions")
async def get_agent_permissions(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get permissions for an agent."""
    # Check access
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403)

    # Get permitted agents
    permitted_list = db.get_permitted_agents(agent_name)

    # Get all accessible agents for UI
    accessible_agents = get_accessible_agents(current_user)

    # Build response with permission status
    available_agents = []
    for agent in accessible_agents:
        if agent["name"] != agent_name:  # Skip self
            available_agents.append({
                "name": agent["name"],
                "status": agent["status"],
                "type": agent.get("type", ""),
                "permitted": agent["name"] in permitted_list
            })

    return {
        "source_agent": agent_name,
        "permitted_agents": [a for a in available_agents if a["permitted"]],
        "available_agents": available_agents
    }
```

### Endpoint: PUT /api/agents/{name}/permissions

**File**: `src/backend/routers/agents.py:1796-1844`

```python
@router.put("/{agent_name}/permissions")
async def set_agent_permissions(
    agent_name: str,
    request: Request,
    body: dict,
    current_user: User = Depends(get_current_user)
):
    """Set permissions for an agent (full replacement)."""
    # Only owner or admin
    if not db.can_user_share_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403)

    permitted_agents = body.get("permitted_agents", [])

    # Validate all targets exist and are accessible
    for target in permitted_agents:
        if not db.can_user_access_agent(current_user.username, target):
            raise HTTPException(status_code=400, detail=f"Agent '{target}' not accessible")

    # Set permissions (replaces all existing)
    db.set_agent_permissions(agent_name, permitted_agents, current_user.username)

    await log_audit_event(
        event_type="agent_permissions",
        action="set_permissions",
        user_id=current_user.username,
        agent_name=agent_name,
        details={"permitted_count": len(permitted_agents)}
    )

    return {"status": "updated", "permitted_count": len(permitted_agents)}
```

### Endpoint: POST /api/agents/{name}/permissions/{target}

**File**: `src/backend/routers/agents.py:1847-1889`

Adds a single permission. Returns `{status: "added"}` or `{status: "already_exists"}`.

### Endpoint: DELETE /api/agents/{name}/permissions/{target}

**File**: `src/backend/routers/agents.py:1892-1926`

Removes a single permission. Returns `{status: "removed"}` or `{status: "not_found"}`.

---

## Data Layer

### Database Table

**File**: `src/backend/database.py:358-368`

```sql
CREATE TABLE IF NOT EXISTS agent_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_agent TEXT NOT NULL,
    target_agent TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    UNIQUE(source_agent, target_agent)
)
```

**Indexes** (`src/backend/database.py:403-405`):
```sql
CREATE INDEX IF NOT EXISTS idx_permissions_source ON agent_permissions(source_agent)
CREATE INDEX IF NOT EXISTS idx_permissions_target ON agent_permissions(target_agent)
```

### Database Operations

**File**: `src/backend/db/permissions.py`

#### PermissionOperations Class

| Method | Line | Description |
|--------|------|-------------|
| `get_permitted_agents(source)` | 39-52 | Returns list of target agent names |
| `get_permission_details(source)` | 54-68 | Returns full AgentPermission objects |
| `is_permitted(source, target)` | 70-82 | Boolean permission check |
| `add_permission(source, target, by)` | 84-110 | Add single permission (idempotent) |
| `remove_permission(source, target)` | 112-125 | Remove single permission |
| `set_permissions(source, targets, by)` | 127-155 | Full replacement (delete + insert) |
| `delete_agent_permissions(agent)` | 157-180 | Cleanup when agent deleted |
| `grant_default_permissions(agent, owner)` | 182-222 | Bidirectional with same-owner agents |

### Database Manager Delegation

**File**: `src/backend/database.py:698-724`

```python
def get_permitted_agents(self, source_agent: str):
    return self._permission_ops.get_permitted_agents(source_agent)

def is_agent_permitted(self, source_agent: str, target_agent: str):
    return self._permission_ops.is_permitted(source_agent, target_agent)

def set_agent_permissions(self, source_agent: str, target_agents: list, created_by: str):
    return self._permission_ops.set_permissions(source_agent, target_agents, created_by)

def grant_default_permissions(self, agent_name: str, owner_username: str):
    return self._permission_ops.grant_default_permissions(agent_name, owner_username)
```

---

## MCP Server Layer (Enforcement)

### TrinityClient Methods

**File**: `src/mcp-server/src/client.ts:172-191`

```typescript
// Get permitted agents for a source agent
async getPermittedAgents(sourceAgent: string): Promise<string[]> {
  const response = await this.request<{ permitted_agents: Array<{ name: string }> }>(
    "GET",
    `/api/agents/${encodeURIComponent(sourceAgent)}/permissions`
  );
  return response.permitted_agents.map((a) => a.name);
}

// Check if source is permitted to call target
async isAgentPermitted(sourceAgent: string, targetAgent: string): Promise<boolean> {
  const permitted = await this.getPermittedAgents(sourceAgent);
  return permitted.includes(targetAgent);
}
```

### list_agents Filtering

**File**: `src/mcp-server/src/tools/agents.ts:50-71`

```typescript
// Phase 9.10: Filter agents for agent-scoped keys
if (authContext?.scope === "agent" && authContext?.agentName) {
  const callerAgentName = authContext.agentName;
  const permittedAgents = await apiClient.getPermittedAgents(callerAgentName);

  // Include self and permitted agents
  const allowedNames = new Set([callerAgentName, ...permittedAgents]);
  const filteredAgents = agents.filter((a) => allowedNames.has(a.name));

  console.log(`[list_agents] Agent '${callerAgentName}' filtered: ${filteredAgents.length}/${agents.length} agents visible`);

  return JSON.stringify(filteredAgents, null, 2);
}
```

### chat_with_agent Permission Check

**File**: `src/mcp-server/src/tools/chat.ts:26-90`

```typescript
async function checkAgentAccess(
  client: TrinityClient,
  authContext: McpAuthContext | undefined,
  targetAgentName: string
): Promise<AgentAccessCheckResult> {
  // If no auth context, allow (auth may be disabled)
  if (!authContext) {
    return { allowed: true };
  }

  // Phase 9.10: Agent-scoped keys use permission system
  if (authContext.scope === "agent" && authContext.agentName) {
    const callerAgentName = authContext.agentName;

    // Self-call is always allowed
    if (callerAgentName === targetAgentName) {
      return { allowed: true };
    }

    // Check if target is in permitted list
    const isPermitted = await client.isAgentPermitted(callerAgentName, targetAgentName);
    if (isPermitted) {
      return { allowed: true };
    }

    // Not permitted
    return {
      allowed: false,
      reason: `Permission denied: Agent '${callerAgentName}' is not permitted to communicate with '${targetAgentName}'. Configure permissions in the Trinity UI.`
    };
  }

  // User-scoped keys: use existing ownership/sharing rules
  // ... (lines 59-90)
}
```

---

## Agent Container Layer

### CLAUDE.md Injection

**File**: `docker/base-image/agent_server/routers/trinity.py:125-163`

When Trinity is injected into an agent, the CLAUDE.md file is updated with an "Agent Collaboration" section:

```markdown
### Agent Collaboration

You can collaborate with other agents using the Trinity MCP tools:

- `mcp__trinity__list_agents()` - See agents you can communicate with
- `mcp__trinity__chat_with_agent(agent_name, message)` - Delegate tasks to other agents

**Note**: You can only communicate with agents you have been granted permission to access.
Use `list_agents` to discover your available collaborators.
```

---

## Agent Lifecycle Integration

### Agent Creation

**File**: `src/backend/routers/agents.py:544-550`

```python
# Phase 9.10: Grant default permissions (Option B - same-owner agents)
try:
    permissions_count = db.grant_default_permissions(config.name, current_user.username)
    if permissions_count > 0:
        print(f"Granted {permissions_count} default permissions for agent {config.name}")
except Exception as e:
    print(f"Warning: Failed to grant default permissions for {config.name}: {e}")
```

### Agent Deletion

**File**: `src/backend/routers/agents.py:652-656`

```python
# Phase 9.10: Delete agent permissions (both as source and target)
try:
    db.delete_agent_permissions(agent_name)
except Exception as e:
    print(f"Warning: Failed to delete permissions for agent {agent_name}: {e}")
```

---

## Side Effects

### Audit Logging

Events logged to audit service:

| Event Type | Action | Details |
|------------|--------|---------|
| `agent_permissions` | `set_permissions` | `{permitted_count: N}` |
| `agent_permissions` | `add_permission` | `{target_agent: name}` |
| `agent_permissions` | `remove_permission` | `{target_agent: name}` |

### MCP Console Logging

```
[list_agents] Agent 'agent-a' filtered: 3/10 agents visible
[Agent Collaboration] agent-a -> agent-b
[Access Denied] agent-a -> agent-c: Permission denied: Agent 'agent-a' is not permitted to communicate with 'agent-c'. Configure permissions in the Trinity UI.
```

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Agent not found | 404 | "Agent not found" |
| No access to source agent | 403 | "You don't have permission to access this agent" |
| Not owner (modify) | 403 | "Only the owner can modify agent permissions" |
| Target not accessible | 400 | "Agent '{name}' does not exist or is not accessible" |
| Self-permission | 400 | "Agent cannot be permitted to call itself" |
| MCP permission denied | 200* | JSON with `{error: "Access denied", reason: "..."}` |

*MCP tools return error in response body, not HTTP status

---

## Security Considerations

1. **Authorization**: Only agent owners (or admins) can modify permissions
2. **Validation**: All target agents must be accessible to the user setting permissions
3. **No self-permission**: Agents cannot grant themselves permission to call themselves
4. **Cascading delete**: When an agent is deleted, all related permissions are removed
5. **MCP enforcement**: Permissions checked at MCP server, not just UI
6. **Audit trail**: All permission changes logged

---

## Testing

### Automated Tests

**File**: `tests/test_agent_permissions.py` (16 tests, all passing)

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestGetPermissions` | 3 | GET endpoint, response structure, field validation |
| `TestSetPermissions` | 3 | Bulk set, empty list, edge cases |
| `TestAddPermission` | 4 | Add single permission, idempotency, self/nonexistent |
| `TestRemovePermission` | 2 | Remove permission, nonexistent handling |
| `TestDefaultPermissions` | 1 | New agent gets bidirectional permissions |
| `TestPermissionCascadeDelete` | 1 | Permissions removed when agent deleted |
| `TestPermissionAuthorization` | 2 | Unauthenticated access rejected |

**Run tests**:
```bash
cd /Users/eugene/Dropbox/Coding/N8N_Main_repos/project_trinity/tests
source .venv/bin/activate
python -m pytest test_agent_permissions.py -v
```

### Manual Test Steps

**Prerequisites**:
- Trinity platform running (`./scripts/deploy/start.sh`)
- At least 2 agents created by same user

1. **View Permissions Tab**
   - Action: Navigate to Agent Detail > Permissions tab
   - Expected: List of other agents with checkboxes
   - Verify: Badge shows count of permitted agents

2. **Grant Permission**
   - Action: Check checkbox for another agent, click Save
   - Expected: "Permissions saved" message
   - Verify: Agent can now call `list_agents` and see the target

3. **Revoke Permission**
   - Action: Uncheck checkbox, click Save
   - Expected: "Permissions saved" message
   - Verify: Agent's `list_agents` no longer shows the target

4. **MCP Enforcement**
   - Action: Agent calls `chat_with_agent(non_permitted_agent, "hello")`
   - Expected: Error response with "Permission denied"
   - Verify: Target agent does not receive message

5. **Bulk Actions**
   - Action: Click "Allow All", then "Allow None"
   - Expected: All checkboxes toggle, dirty state shown
   - Verify: Save reflects the bulk change

6. **Default Permissions on Create**
   - Action: Create new agent
   - Expected: Bidirectional permissions with all same-owner agents
   - Verify: Check database `agent_permissions` table

### Edge Cases
- Agent with no other agents (empty list shown)
- Deleting permitted agent (cascade delete works)
- Non-owner trying to modify permissions (403)

### Status: ✅ API Tests Passing (16/16)

---

## Related Flows

| Flow | Relationship |
|------|--------------|
| [agent-to-agent-collaboration.md](agent-to-agent-collaboration.md) | **Upstream** - Permission system gates collaboration |
| [agent-lifecycle.md](agent-lifecycle.md) | **Lifecycle** - Permissions granted on create, deleted on delete |
| [mcp-orchestration.md](mcp-orchestration.md) | **Enforcement** - MCP tools check permissions |
| [agent-sharing.md](agent-sharing.md) | **Related** - Sharing controls user access, permissions control agent access |
