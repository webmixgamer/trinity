# Feature: Agent Sharing

## Overview
Collaboration feature enabling agent owners to share agents with team members via email. Supports three access levels: Owner (full control), Shared (limited access), and Admin (full control over all agents).

## User Story
As an agent owner, I want to share my agents with team members so that they can use the agents without having full ownership permissions.

## Entry Points
- **UI**: `src/frontend/src/views/AgentDetail.vue` - Sharing tab (owners only)
- **API**: `POST /api/agents/{name}/share` - Share agent
- **API**: `DELETE /api/agents/{name}/share/{email}` - Remove share
- **API**: `GET /api/agents/{name}/shares` - List shares

---

## Frontend Layer

### AgentDetail.vue (`src/frontend/src/views/AgentDetail.vue`)

**Sharing Tab**:
```vue
<button
  v-if="agent.can_share"
  @click="activeTab = 'sharing'"
  :class="[activeTab === 'sharing' ? 'border-indigo-500' : 'border-transparent']"
>
  Sharing
</button>
```

**Share Form**:
```vue
<input
  v-model="shareEmail"
  type="email"
  placeholder="Enter email address"
/>
<button @click="shareAgent">Share</button>

<!-- Shared Users List -->
<div v-for="share in agentShares" :key="share.email">
  <span>{{ share.email }}</span>
  <button @click="removeShare(share.email)">Remove</button>
</div>
```

**Methods**:
```javascript
const shareAgent = async () => {
  await agentsStore.shareAgent(agent.value.name, shareEmail.value)
  shareEmail.value = ''
  await loadAgentShares()
}

const removeShare = async (email) => {
  await agentsStore.unshareAgent(agent.value.name, email)
  await loadAgentShares()
}
```

### State Management (`src/frontend/src/stores/agents.js:249-272`)
```javascript
// Agent Sharing Actions
async shareAgent(name, email) {
  const authStore = useAuthStore()
  const response = await axios.post(`/api/agents/${name}/share`,
    { email },
    { headers: authStore.authHeader }
  )
  return response.data
}

async unshareAgent(name, email) {
  const authStore = useAuthStore()
  await axios.delete(`/api/agents/${name}/share/${encodeURIComponent(email)}`, {
    headers: authStore.authHeader
  })
}

async getAgentShares(name) {
  const authStore = useAuthStore()
  const response = await axios.get(`/api/agents/${name}/shares`, {
    headers: authStore.authHeader
  })
  return response.data
}
```

---

## Backend Layer

### Endpoints (`src/backend/routers/sharing.py`)

| Line | Endpoint | Method | Purpose |
|------|----------|--------|---------|
| 24-88 | `/api/agents/{name}/share` | POST | Share agent with email |
| 91-136 | `/api/agents/{name}/share/{email}` | DELETE | Remove share |
| 139-155 | `/api/agents/{name}/shares` | GET | List shares |

### Share Agent (`routers/sharing.py:24-88`)
```python
@router.post("/{agent_name}/share", response_model=AgentShare)
async def share_agent_endpoint(agent_name: str, share_request: AgentShareRequest, current_user: User):
    # Check agent exists
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check authorization (must be owner or admin)
    if not db.can_user_share_agent(current_user.username, agent_name):
        raise HTTPException(403, "You don't have permission to share this agent")

    # Prevent self-sharing
    if current_user_email.lower() == share_request.email.lower():
        raise HTTPException(400, "Cannot share an agent with yourself")

    # Create share record
    share = db.share_agent(agent_name, current_user.username, share_request.email)
    if not share:
        raise HTTPException(409, f"Agent is already shared with {share_request.email}")

    # Auto-add email to whitelist if email auth is enabled (Phase 12.4)
    if email_auth_enabled:
        db.add_to_whitelist(share_request.email, current_user.username, source="agent_sharing")

    # Audit log
    await log_audit_event(
        event_type="agent_sharing",
        action="share",
        user_id=current_user.username,
        agent_name=agent_name,
        result="success",
        details={"shared_with": share_request.email}
    )

    # Broadcast WebSocket event
    await manager.broadcast(json.dumps({
        "event": "agent_shared",
        "data": {"name": agent_name, "shared_with": share_request.email}
    }))
```

### Remove Share (`routers/sharing.py:91-136`)
```python
@router.delete("/{agent_name}/share/{email}")
async def unshare_agent_endpoint(agent_name: str, email: str, current_user: User):
    # Check agent exists
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if not db.can_user_share_agent(current_user.username, agent_name):
        raise HTTPException(403, "You don't have permission to modify sharing for this agent")

    success = db.unshare_agent(agent_name, current_user.username, email)
    if not success:
        raise HTTPException(404, f"No sharing found for {email}")

    # Audit log
    await log_audit_event(
        event_type="agent_sharing",
        action="unshare",
        user_id=current_user.username,
        agent_name=agent_name,
        result="success",
        details={"removed_user": email}
    )

    # Broadcast WebSocket event
    await manager.broadcast(json.dumps({
        "event": "agent_unshared",
        "data": {"name": agent_name, "removed_user": email}
    }))
```

### Access Control in List Agents (`routers/agents.py:129-140`)

Agent access control is handled by `services/agent_service/helpers.py:get_accessible_agents()`:

```python
@router.get("")
async def list_agents_endpoint(request: Request, current_user: User = Depends(get_current_user)):
    """List all agents accessible to the current user."""
    await log_audit_event(
        event_type="agent_access",
        action="list",
        user_id=current_user.username,
        ip_address=request.client.host if request.client else None,
        result="success"
    )
    return get_accessible_agents(current_user)
```

Access levels are determined in `get_accessible_agents()`:
- `is_owner`: Owner of the agent
- `is_admin`: User has admin role
- `is_shared`: Agent shared with user via email
- `can_delete`: Owner or admin (not system agents)
- `can_share`: Owner or admin

---

## Database Layer (`src/backend/db/agents.py`)

Database operations are delegated from `database.py` to `db/agents.py`.

### Schema
```sql
CREATE TABLE IF NOT EXISTS agent_sharing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    shared_with_email TEXT NOT NULL,
    shared_by_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(agent_name, shared_with_email),
    FOREIGN KEY (shared_by_id) REFERENCES users(id)
)
```

### Operations (`db/agents.py`)

| Method | Line | Purpose |
|--------|------|---------|
| `share_agent()` | 164-207 | Create share record |
| `unshare_agent()` | 209-222 | Remove share record |
| `get_agent_shares()` | 224-236 | List shares for agent |
| `get_shared_agents()` | 238-253 | Get agents shared with user |
| `is_agent_shared_with_user()` | 255-271 | Access check |
| `can_user_share_agent()` | 273-283 | Authorization check |
| `delete_agent_shares()` | 285-290 | Cascade delete shares |

### Share Agent (`db/agents.py:164-207`)
```python
def share_agent(self, agent_name: str, owner_username: str, share_with_email: str) -> Optional[AgentShare]:
    # Get owner and validate permission
    owner = self._user_ops.get_user_by_username(owner_username)
    if not owner:
        return None

    # Check if user can share (owner or admin)
    if not self.can_user_share_agent(owner_username, agent_name):
        return None

    # Prevent self-sharing
    if owner.get("email", "").lower() == share_with_email.lower():
        return None

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO agent_sharing (agent_name, shared_with_email, shared_by_id, created_at)
                VALUES (?, ?, ?, ?)
            """, (agent_name, share_with_email.lower(), owner["id"], now))
            conn.commit()
            return AgentShare(...)
        except sqlite3.IntegrityError:
            return None  # Already shared
```

### Cascade Delete (`db/agents.py:285-290`)
When an agent is deleted, all sharing records are removed:
```python
def delete_agent_shares(self, agent_name: str) -> int:
    """Delete all sharing records for an agent (when agent is deleted)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM agent_sharing WHERE agent_name = ?", (agent_name,))
        conn.commit()
        return cursor.rowcount
```

---

## Access Levels

| Level | View | Start/Stop | Delete | Share |
|-------|------|------------|--------|-------|
| Owner | Yes | Yes | Yes | Yes |
| Shared | Yes | Yes | No | No |
| Admin | Yes | Yes | Yes | Yes |

---

## Side Effects

### WebSocket Broadcasts
| Event | Payload |
|-------|---------|
| `agent_shared` | `{name, shared_with}` |
| `agent_unshared` | `{name, removed_user}` |

### Audit Logging
```python
await log_audit_event(
    event_type="agent_sharing",
    action="share|unshare",
    user_id=current_user.username,
    agent_name=agent_name,
    details={"shared_with": email},
    result="success",
    ip_address=request.client.host
)
```

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Agent not found | 404 | "Agent not found" |
| Not authorized to share | 403 | "You don't have permission to share this agent" |
| Share not found | 404 | "No sharing found for {email}" |
| Already shared | 409 | "Agent is already shared with this email" |
| Self-sharing | 400 | "Cannot share an agent with yourself" |

---

## Security Considerations

1. **Email-Based Sharing**: Shares with users who haven't registered yet
2. **Owner-Only Sharing**: Only owners and admins can share
3. **Cascade Delete**: Shares removed when agent deleted
4. **Access Validation**: Every endpoint checks authorization via `can_user_share_agent()`
5. **Audit Trail**: All sharing actions logged with IP address
6. **Auto-Whitelist**: When email auth is enabled, shared emails are auto-added to whitelist (Phase 12.4)

---

## Testing

### Manual Testing
```bash
# Share an agent
curl -X POST http://localhost:8000/api/agents/my-agent/share \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "colleague@example.com"}'

# List shares
curl http://localhost:8000/api/agents/my-agent/shares \
  -H "Authorization: Bearer $TOKEN"

# Remove share
curl -X DELETE http://localhost:8000/api/agents/my-agent/share/colleague@example.com \
  -H "Authorization: Bearer $TOKEN"

# Verify shared user can see agent
curl http://localhost:8000/api/agents \
  -H "Authorization: Bearer $SHARED_USER_TOKEN"
```

---

## Status
Working - Agent sharing fully functional with email-based collaboration

---

## Revision History

| Date | Changes |
|------|---------|
| 2025-12-30 | **Flow verification**: Updated line numbers for routers/sharing.py (24-88, 91-136, 139-155). Updated database layer to reference db/agents.py. Updated store action line numbers. Added auto-whitelist feature note. |

---

## Related Flows

- **Upstream**: Authentication (user identity)
- **Related**: Agent Lifecycle (delete cascades shares), MCP Orchestration (agent-to-agent access control), Email Authentication (auto-whitelist)
