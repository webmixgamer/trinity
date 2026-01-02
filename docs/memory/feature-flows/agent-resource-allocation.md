# Feature: Agent Resource Allocation

## Overview
Allows users to configure memory and CPU limits for Docker agent containers. Resources are stored in the database and applied when containers are created or recreated.

## User Story
As an agent owner, I want to configure memory and CPU allocation for my agents so that I can balance performance and resource usage across my fleet.

## Revision History
| Date | Change |
|------|--------|
| 2026-01-02 | Initial documentation |

---

## Entry Points

- **UI**: `src/frontend/src/views/AgentDetail.vue:225,243` - Gear icon button in agent header (shown when agent.can_share)
- **API GET**: `GET /api/agents/{name}/resources` - Fetch current limits
- **API PUT**: `PUT /api/agents/{name}/resources` - Update limits

---

## Frontend Layer

### Components

**AgentDetail.vue** (`src/frontend/src/views/AgentDetail.vue`)

| Line | Element | Description |
|------|---------|-------------|
| 225 | `@click="showResourceModal = true"` | Gear button (running state, next to sparklines) |
| 243 | `@click="showResourceModal = true"` | Gear button (stopped state) |
| 427-518 | Resource Modal | Full modal component with form |
| 467 | Memory dropdown | `v-model="resourceLimits.memory"` |
| 484 | CPU dropdown | `v-model="resourceLimits.cpu"` |
| 502 | Save button | `@click="saveResourceLimits"` |
| 1392 | `showResourceModal` | Ref for modal visibility |
| 1639-1658 | `saveResourceLimits()` | Handler that saves and auto-restarts |

**Modal UI Features:**
- Warning banner: "If the agent is running, it will be automatically restarted to apply changes"
- Memory options: 1g, 2g, 4g, 8g, 16g, 32g, 64g (or Default)
- CPU options: 1, 2, 4, 8, 16 cores (or Default)
- Default option shows current container value (e.g., "Default (4g)")

### Composable

**useAgentSettings.js** (`src/frontend/src/composables/useAgentSettings.js:78-110`)

```javascript
// State
const resourceLimits = ref({
  memory: null,      // Selected value (null = use default)
  cpu: null,         // Selected value (null = use default)
  current_memory: '4g',  // Current container limit
  current_cpu: '2',      // Current container limit
  restart_needed: false  // Set by backend response
})

// Methods
const loadResourceLimits = async () => {
  const result = await agentsStore.getResourceLimits(agentRef.value.name)
  resourceLimits.value = { ... }
}

const updateResourceLimits = async () => {
  const result = await agentsStore.setResourceLimits(
    agentRef.value.name,
    resourceLimits.value.memory,
    resourceLimits.value.cpu
  )
}
```

### Store Actions

**agents.js** (`src/frontend/src/stores/agents.js:601-618`)

```javascript
// GET /api/agents/{name}/resources
async getResourceLimits(name) {
  const response = await axios.get(`/api/agents/${name}/resources`, {
    headers: authStore.authHeader
  })
  return response.data
}

// PUT /api/agents/{name}/resources
async setResourceLimits(name, memory, cpu) {
  const response = await axios.put(`/api/agents/${name}/resources`, {
    memory: memory,
    cpu: cpu
  }, { headers: authStore.authHeader })
  return response.data
}
```

### Auto-Restart Logic

**AgentDetail.vue:1639-1658** - `saveResourceLimits()`:

```javascript
async function saveResourceLimits() {
  // Check if values actually changed
  const newMemory = resourceLimits.value.memory || resourceLimits.value.current_memory
  const newCpu = resourceLimits.value.cpu || resourceLimits.value.current_cpu
  const oldMemory = resourceLimits.value.current_memory
  const oldCpu = resourceLimits.value.current_cpu
  const valuesChanged = newMemory !== oldMemory || newCpu !== oldCpu

  await updateResourceLimits()
  showResourceModal.value = false

  // If values changed and agent is running, restart it
  if (valuesChanged && agent.value?.status === 'running') {
    showNotification('Restarting agent to apply new resource limits...', 'info')
    await stopAgent()
    await new Promise(resolve => setTimeout(resolve, 1000))
    await startAgent()
  }
}
```

---

## Backend Layer

### Endpoints

**agents.py** (`src/backend/routers/agents.py:797-898`)

#### GET /api/agents/{name}/resources (Line 797)

```python
@router.get("/{agent_name}/resources")
async def get_agent_resources(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    # Check access
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get DB limits (may be None)
    db_limits = db.get_resource_limits(agent_name)

    # Get current container limits from labels
    labels = container.attrs.get("Config", {}).get("Labels", {})
    current_memory = labels.get("trinity.memory", "4g")
    current_cpu = labels.get("trinity.cpu", "2")

    return {
        "memory": db_limits.get("memory") if db_limits else None,
        "cpu": db_limits.get("cpu") if db_limits else None,
        "current_memory": current_memory,
        "current_cpu": current_cpu
    }
```

#### PUT /api/agents/{name}/resources (Line 835)

```python
@router.put("/{agent_name}/resources")
async def set_agent_resources(
    agent_name: str,
    body: dict,
    current_user: User = Depends(get_current_user)
):
    # Only owners can change resources
    if not db.can_user_share_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Only owners can change resource limits")

    # Validate memory format
    valid_memory = ["1g", "2g", "4g", "8g", "16g", "32g", "64g"]
    if memory and memory not in valid_memory:
        raise HTTPException(status_code=400, detail=f"Invalid memory value")

    # Validate CPU format
    valid_cpu = ["1", "2", "4", "8", "16"]
    if cpu and cpu not in valid_cpu:
        raise HTTPException(status_code=400, detail=f"Invalid CPU value")

    # Update database
    db.set_resource_limits(agent_name, memory=memory, cpu=cpu)

    # Check if restart is needed
    labels = container.attrs.get("Config", {}).get("Labels", {})
    current_memory = labels.get("trinity.memory", "4g")
    current_cpu = labels.get("trinity.cpu", "2")
    restart_needed = (memory and memory != current_memory) or (cpu and cpu != current_cpu)

    return {
        "message": "Resource limits updated",
        "memory": memory,
        "cpu": cpu,
        "restart_needed": restart_needed
    }
```

### Mismatch Check at Start

**helpers.py** (`src/backend/services/agent_service/helpers.py:299-329`)

```python
def check_resource_limits_match(container, agent_name: str) -> bool:
    """
    Check if container's resource limits match the current database settings.
    Returns True if resources match, False if recreation needed.
    """
    # Get DB settings (may be None if using template defaults)
    db_limits = db.get_resource_limits(agent_name)

    # Get current container limits from labels
    labels = container.attrs.get("Config", {}).get("Labels", {})
    current_memory = labels.get("trinity.memory", "4g")
    current_cpu = labels.get("trinity.cpu", "2")

    if db_limits is None:
        # No custom limits set - container uses template defaults
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
```

### Container Recreation

**lifecycle.py** (`src/backend/services/agent_service/lifecycle.py:53-97`)

```python
async def start_agent_internal(agent_name: str) -> dict:
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if container needs recreation
    container.reload()
    needs_recreation = (
        not check_shared_folder_mounts_match(container, agent_name) or
        not check_api_key_env_matches(container, agent_name) or
        not check_resource_limits_match(container, agent_name)  # <-- Resource check
    )

    if needs_recreation:
        await recreate_container_with_updated_config(agent_name, container, "system")
        container = get_agent_container(agent_name)

    container.start()
    # ... trinity prompt injection
```

**lifecycle.py:100-231** - `recreate_container_with_updated_config()`:

```python
async def recreate_container_with_updated_config(agent_name, old_container, owner_username):
    # ... extract old config ...

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

    # ... stop and remove old container ...

    # Create new container with new limits
    new_container = docker_client.containers.run(
        image,
        # ... other config ...
        mem_limit=memory,    # e.g., "8g"
        cpu_count=int(cpu)   # e.g., 4
    )
```

---

## Data Layer

### Database Schema

**database.py** (`src/backend/database.py:230-240`) - Migration:

```python
def _migrate_agent_ownership_resource_limits(cursor, conn):
    """Add memory_limit and cpu_limit columns to agent_ownership table."""
    new_columns = [
        ("memory_limit", "TEXT"),  # e.g., "4g", "8g", "16g"
        ("cpu_limit", "TEXT")      # e.g., "2", "4", "8"
    ]
    for col_name, col_type in new_columns:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE agent_ownership ADD COLUMN {col_name} {col_type}")
```

**database.py:321-326** - Table schema:

```sql
CREATE TABLE IF NOT EXISTS agent_ownership (
    -- ... other columns ...
    memory_limit TEXT,
    cpu_limit TEXT,
    FOREIGN KEY (owner_id) REFERENCES users(id)
)
```

### CRUD Operations

**db/agents.py** (`src/backend/db/agents.py:363-409`)

```python
def get_resource_limits(self, agent_name: str) -> Optional[Dict[str, str]]:
    """Get per-agent resource limits (memory and CPU)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT memory_limit, cpu_limit
            FROM agent_ownership WHERE agent_name = ?
        """, (agent_name,))
        row = cursor.fetchone()
        if row:
            memory = row["memory_limit"]
            cpu = row["cpu_limit"]
            if memory is None and cpu is None:
                return None
            return {"memory": memory, "cpu": cpu}
        return None

def set_resource_limits(self, agent_name: str, memory: Optional[str] = None, cpu: Optional[str] = None) -> bool:
    """Set per-agent resource limits."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE agent_ownership SET memory_limit = ?, cpu_limit = ?
            WHERE agent_name = ?
        """, (memory, cpu, agent_name))
        conn.commit()
        return cursor.rowcount > 0
```

### Container Labels

Resource limits are stored in Docker container labels for reference:
- `trinity.memory`: Current memory limit (e.g., "8g")
- `trinity.cpu`: Current CPU limit (e.g., "4")

These labels are read to determine current container resources and compared against DB values to detect mismatches.

---

## Complete Flow

```
1. User clicks gear icon in AgentDetail header
   ├─ AgentDetail.vue:225 or :243 → showResourceModal = true

2. Modal opens, shows current limits from composable
   ├─ loadResourceLimits() called on component mount
   └─ GET /api/agents/{name}/resources
       ├─ Check user access (can_user_access_agent)
       ├─ Get DB limits (may be null)
       ├─ Get container labels (trinity.memory, trinity.cpu)
       └─ Return { memory, cpu, current_memory, current_cpu }

3. User selects new values and clicks Save
   ├─ saveResourceLimits() in AgentDetail.vue:1639
   ├─ Calculates if values actually changed
   └─ Calls updateResourceLimits()
       └─ PUT /api/agents/{name}/resources { memory, cpu }
           ├─ Validate ownership (can_user_share_agent)
           ├─ Validate memory in [1g, 2g, 4g, 8g, 16g, 32g, 64g]
           ├─ Validate CPU in [1, 2, 4, 8, 16]
           ├─ UPDATE agent_ownership SET memory_limit, cpu_limit
           └─ Return { message, memory, cpu, restart_needed }

4. Frontend auto-restarts if needed
   ├─ If valuesChanged && agent.status === 'running':
   │   ├─ showNotification("Restarting agent...")
   │   ├─ await stopAgent()
   │   ├─ wait 1 second
   │   └─ await startAgent()

5. On agent start, backend checks for mismatches
   ├─ start_agent_internal() in lifecycle.py:53
   ├─ check_resource_limits_match() returns False if DB != container
   └─ If mismatch:
       └─ recreate_container_with_updated_config()
           ├─ Stop and remove old container
           ├─ Read new limits from DB
           ├─ Update trinity.* labels
           └─ Create new container with mem_limit and cpu_count
```

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Agent not found | 404 | "Agent not found" |
| Access denied (not accessible) | 403 | "Access denied" |
| Not owner (trying to change) | 403 | "Only owners can change resource limits" |
| Invalid memory value | 400 | "Invalid memory value. Must be one of: 1g, 2g, 4g, 8g, 16g, 32g, 64g" |
| Invalid CPU value | 400 | "Invalid CPU value. Must be one of: 1, 2, 4, 8, 16" |

---

## Security Considerations

1. **Ownership Check**: Only agent owners can modify resource limits (`can_user_share_agent`)
2. **Access Check**: Reading limits requires agent access (`can_user_access_agent`)
3. **Input Validation**: Strict validation of memory and CPU values against allowlists
4. **Docker Security**: Recreated containers maintain security options (no-new-privileges, apparmor, cap_drop)

---

## Related Flows

- **Upstream**: [agent-lifecycle.md](agent-lifecycle.md) - Container start/stop/recreate logic
- **Downstream**: None (terminal operation)
- **Similar**: [agent-shared-folders.md](agent-shared-folders.md) - Also triggers container recreation on start

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- Frontend running at localhost:3000
- At least one agent created and owned by test user

### Test Steps

1. **View Resource Settings (Running Agent)**
   - Action: Navigate to agent detail page for a running agent
   - Expected: Gear icon visible next to CPU/MEM sparklines
   - Verify: Click opens modal with current values

2. **View Resource Settings (Stopped Agent)**
   - Action: Navigate to agent detail page for a stopped agent
   - Expected: Gear icon visible in "Created X ago" row
   - Verify: Click opens modal with current values

3. **Change Memory Limit**
   - Action: Select "8 GB" from memory dropdown, click Save
   - Expected: Success notification, modal closes
   - Verify: Reopen modal - "8g" should be selected
   - If running: Agent should restart automatically

4. **Change CPU Limit**
   - Action: Select "4 Cores" from CPU dropdown, click Save
   - Expected: Success notification, agent restarts if running
   - Verify: Check container with `docker inspect` - `CpuCount: 4`

5. **Reset to Default**
   - Action: Select "Default" for both fields, click Save
   - Expected: Success, values stored as null in DB
   - Verify: Container uses template defaults on next start

6. **Non-Owner Access**
   - Action: Share agent with another user, log in as that user
   - Expected: Gear icon should NOT be visible
   - Verify: API returns 403 if called directly

### Edge Cases
- Invalid memory value via API: 400 error with validation message
- Invalid CPU value via API: 400 error with validation message
- Agent deleted while modal open: Error on save
- Rapid clicking Save: Loading state prevents double-submit

### Status
:construction: Not Tested
