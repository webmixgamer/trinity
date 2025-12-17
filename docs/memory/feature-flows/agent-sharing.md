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

### State Management (`src/frontend/src/stores/agents.js:209-231`)
```javascript
async shareAgent(name, email) {
  const response = await axios.post(`/api/agents/${name}/share`,
    { email },
    { headers: authStore.authHeader }
  )
  return response.data
}

async unshareAgent(name, email) {
  const response = await axios.delete(`/api/agents/${name}/share/${email}`, {
    headers: authStore.authHeader
  })
  return response.data
}

async getAgentShares(name) {
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
| 24-74 | `/api/agents/{name}/share` | POST | Share agent with email |
| 77-122 | `/api/agents/{name}/share/{email}` | DELETE | Remove share |
| 125-140 | `/api/agents/{name}/shares` | GET | List shares |

### Share Agent (`routers/sharing.py:24-74`)
```python
@router.post("/{agent_name}/share", response_model=AgentShare)
async def share_agent_endpoint(agent_name: str, share_request: AgentShareRequest, current_user: User):
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

    # Broadcast WebSocket event
    await manager.broadcast({
        "event": "agent_shared",
        "data": {"name": agent_name, "shared_with": share_request.email}
    })

    # Audit log
    await log_audit_event(
        event_type="agent_sharing",
        action="share",
        user_id=current_user.username,
        agent_name=agent_name,
        result="success",
        details={"shared_with": share_request.email}
    )
```

### Remove Share (`routers/sharing.py:77-122`)
```python
@router.delete("/{agent_name}/share/{email}")
async def unshare_agent_endpoint(agent_name: str, email: str, current_user: User):
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
```

### Access Control in List Agents (`routers/agents.py:47-78`)
```python
@router.get("")
async def list_agents_endpoint(current_user: User):
    all_agents = list_all_agents()

    for agent in all_agents:
        owner = db.get_agent_owner(agent.name)

        # Determine access level
        is_owner = owner and owner["owner_username"] == current_user.username
        is_admin = user_data and user_data["role"] == "admin"
        is_shared = db.is_agent_shared_with_user(agent_name, current_user.username)

        agent_dict["can_delete"] = db.can_user_delete_agent(current_user.username, agent_name)
        agent_dict["can_share"] = db.can_user_share_agent(current_user.username, agent_name)
        agent_dict["is_shared"] = not is_owner and not is_admin and is_shared
```

---

## Database Layer (`src/backend/database.py`)

### Schema
```sql
CREATE TABLE IF NOT EXISTS agent_sharing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    shared_with_email TEXT NOT NULL,
    shared_by_user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(agent_name, shared_with_email),
    FOREIGN KEY (shared_by_user_id) REFERENCES users(id)
)
```

### Operations

| Method | Line | Purpose |
|--------|------|---------|
| `share_agent()` | 937-980 | Create share record |
| `unshare_agent()` | 982-995 | Remove share record |
| `get_agent_shares()` | 997-1026 | List shares for agent |
| `is_agent_shared_with_user()` | 1028-1044 | Access check |
| `can_user_share_agent()` | 1046-1064 | Authorization check |

### Share Agent (`database.py:937-980`)
```python
def share_agent(self, agent_name: str, owner_username: str, share_with_email: str) -> Optional[AgentShare]:
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get owner user ID
        user = self.get_user_by_username(owner_username)

        # Check if already shared
        cursor.execute("""
            SELECT * FROM agent_sharing
            WHERE agent_name = ? AND shared_with_email = ?
        """, (agent_name, share_with_email))

        if cursor.fetchone():
            return None  # Already shared

        # Insert share record
        cursor.execute("""
            INSERT INTO agent_sharing (agent_name, shared_with_email, shared_by_user_id, created_at)
            VALUES (?, ?, ?, ?)
        """, (agent_name, share_with_email, user["id"], datetime.now().isoformat()))

        conn.commit()
        return self._row_to_agent_share(cursor.execute(...).fetchone())
```

### Cascade Delete
When an agent is deleted, all sharing records are removed:
```python
def delete_agent_ownership(self, agent_name: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Delete sharing records first
        cursor.execute("DELETE FROM agent_sharing WHERE agent_name = ?", (agent_name,))
        # Then delete ownership
        cursor.execute("DELETE FROM agent_ownership WHERE agent_name = ?", (agent_name,))
        conn.commit()
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
✅ **Working** - Agent sharing fully functional with email-based collaboration

---

## Related Flows

- **Upstream**: Authentication (user identity)
- **Related**: Agent Lifecycle (delete cascades shares), MCP Orchestration (agent-to-agent access control)
