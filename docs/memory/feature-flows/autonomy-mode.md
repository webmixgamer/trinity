# Feature: Autonomy Mode

## Overview
Autonomy Mode enables or disables all scheduled tasks for an agent with a single toggle. When autonomy is enabled, all schedules run automatically. When disabled, all schedules are paused.

## User Story
As an agent owner, I want to toggle autonomous operation for my agent so that I can quickly enable or disable all scheduled tasks without managing each schedule individually.

## Entry Points
- **Dashboard UI**: `src/frontend/src/components/AgentNode.vue:62-96` - Toggle switch with "AUTO/Manual" label
- **Agent Detail UI**: `src/frontend/src/views/AgentDetail.vue:137-160` - AUTO/Manual toggle button in header
- **API**: `GET /api/agents/autonomy-status` - Bulk status for dashboard
- **API**: `GET /api/agents/{name}/autonomy` - Per-agent status with schedule counts
- **API**: `PUT /api/agents/{name}/autonomy` - Toggle autonomy on/off

---

## Frontend Layer

### Dashboard View (AgentNode.vue)

**File**: `src/frontend/src/components/AgentNode.vue`

#### Toggle Switch (lines 62-96)
The Dashboard agent tiles include an inline toggle switch for quick autonomy control:
```vue
<!-- Autonomy toggle switch with label (not for system agent) -->
<div v-if="!isSystemAgent" class="flex items-center gap-1.5">
  <span :class="autonomyEnabled ? 'text-amber-600' : 'text-gray-400'">
    {{ autonomyEnabled ? 'AUTO' : 'Manual' }}
  </span>
  <button
    @click="handleAutonomyToggle"
    :disabled="autonomyLoading"
    :class="autonomyEnabled ? 'bg-amber-500' : 'bg-gray-200'"
    role="switch"
    :aria-checked="autonomyEnabled"
  >
    <span :class="autonomyEnabled ? 'translate-x-4' : 'translate-x-0'" />
  </button>
</div>
```

**Visual Design**:
- Toggle switch (36x20px) with sliding knob
- Label shows "AUTO" (amber) or "Manual" (gray)
- Disabled state with opacity when API call in progress
- Tooltips explain the current state and action

#### Toggle Handler (lines 317-330)
```javascript
async function handleAutonomyToggle(event) {
  event.stopPropagation() // Prevent card drag
  if (autonomyLoading.value || isSystemAgent.value) return

  autonomyLoading.value = true
  try {
    await networkStore.toggleAutonomy(props.data.label)
  } finally {
    autonomyLoading.value = false
  }
}
```

#### Computed Property (lines 189-191)
```javascript
const autonomyEnabled = computed(() => {
  return props.data.autonomy_enabled === true
})
```

### Network Store (network.js)

**File**: `src/frontend/src/stores/network.js`

#### Toggle Autonomy Action (lines 993-1030)
```javascript
async function toggleAutonomy(agentName) {
  const node = nodes.value.find(n => n.id === agentName)
  if (!node) return { success: false, error: 'Agent not found' }

  const newState = !node.data.autonomy_enabled

  try {
    const response = await axios.put(
      `/api/agents/${agentName}/autonomy`,
      { enabled: newState },
      { headers: { Authorization: `Bearer ${token}` } }
    )

    // Update the node data reactively
    node.data.autonomy_enabled = newState

    return {
      success: true,
      enabled: newState,
      schedulesUpdated: response.data.schedules_updated
    }
  } catch (error) {
    return { success: false, error: error.response?.data?.detail }
  }
}
```

#### Node Conversion (lines 305-327)
The store passes `autonomy_enabled` from agent data to dashboard nodes:
```javascript
regularAgents.forEach((agent, index) => {
  result.push({
    id: agent.name,
    type: 'agent',
    data: {
      // ... other fields
      autonomy_enabled: agent.autonomy_enabled || false,
      // ...
    }
  })
})
```

### Agent Detail View (AgentDetail.vue)

**File**: `src/frontend/src/views/AgentDetail.vue`

#### Toggle Button (lines 137-160)
```vue
<template v-if="!agent.is_system && agent.can_share">
  <button
    @click="toggleAutonomy"
    :disabled="autonomyLoading"
    :class="[
      'inline-flex items-center text-sm font-medium py-1.5 px-3 rounded transition-colors',
      agent.autonomy_enabled
        ? 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 hover:bg-amber-200 dark:hover:bg-amber-900/70'
        : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
    ]"
    :title="agent.autonomy_enabled ? 'Autonomy Mode ON - Scheduled tasks are running' : 'Autonomy Mode OFF - Click to enable scheduled tasks'"
  >
    {{ agent.autonomy_enabled ? 'AUTO' : 'Manual' }}
  </button>
</template>
```

#### Toggle Handler (lines 1401-1441)
```javascript
const autonomyLoading = ref(false)

async function toggleAutonomy() {
  if (!agent.value || autonomyLoading.value) return

  autonomyLoading.value = true
  const newState = !agent.value.autonomy_enabled

  try {
    const response = await fetch(`/api/agents/${agent.value.name}/autonomy`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ enabled: newState })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to update autonomy mode')
    }

    const result = await response.json()

    // Update local state
    agent.value.autonomy_enabled = newState

    showNotification(
      newState
        ? `Autonomy enabled. ${result.schedules_updated} schedule(s) activated.`
        : `Autonomy disabled. ${result.schedules_updated} schedule(s) paused.`,
      'success'
    )
  } catch (error) {
    console.error('Failed to toggle autonomy:', error)
    showNotification(error.message || 'Failed to update autonomy mode', 'error')
  } finally {
    autonomyLoading.value = false
  }
}
```

---

## Backend Layer

### Router Endpoints

**File**: `src/backend/routers/agents.py`

#### Bulk Status Endpoint (lines 168-174)
```python
@router.get("/autonomy-status")
async def get_all_autonomy_status(
    current_user: User = Depends(get_current_user)
):
    """Get autonomy status for all accessible agents (for dashboard display)."""
    return await get_all_autonomy_status_logic(current_user)
```

#### Per-Agent Status Endpoint (lines 766-773)
```python
@router.get("/{agent_name}/autonomy")
async def get_agent_autonomy_status(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get the autonomy status for an agent."""
    return await get_autonomy_status_logic(agent_name, current_user)
```

#### Toggle Endpoint (lines 775-791)
```python
@router.put("/{agent_name}/autonomy")
async def set_agent_autonomy_status(
    agent_name: str,
    body: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Set the autonomy status for an agent.

    Body:
    - enabled: True to enable autonomy, False to disable

    When autonomy is enabled, all schedules for the agent are enabled.
    When disabled, all schedules are paused.
    """
    return await set_autonomy_status_logic(agent_name, body, current_user)
```

### Service Layer

**File**: `src/backend/services/agent_service/autonomy.py`

#### Get Status Logic (lines 20-49)
```python
async def get_autonomy_status_logic(
    agent_name: str,
    current_user: User
) -> dict:
    """Get the autonomy status for an agent."""
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to access this agent")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    autonomy_enabled = db.get_autonomy_enabled(agent_name)

    # Get schedule counts
    schedules = db.list_agent_schedules(agent_name)
    total_schedules = len(schedules)
    enabled_schedules = sum(1 for s in schedules if s.enabled)

    return {
        "agent_name": agent_name,
        "autonomy_enabled": autonomy_enabled,
        "total_schedules": total_schedules,
        "enabled_schedules": enabled_schedules,
        "status": container.status
    }
```

#### Set Status Logic (lines 52-117)
```python
async def set_autonomy_status_logic(
    agent_name: str,
    body: dict,
    current_user: User
) -> dict:
    """Set the autonomy status for an agent."""
    # Only owner can modify autonomy
    if not db.can_user_share_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Only the owner can modify autonomy settings")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Don't allow autonomy for system agent
    if db.is_system_agent(agent_name):
        raise HTTPException(status_code=403, detail="Cannot modify autonomy for system agent")

    enabled = body.get("enabled")
    if enabled is None:
        raise HTTPException(status_code=400, detail="enabled is required")

    enabled = bool(enabled)

    # Update the autonomy flag
    db.set_autonomy_enabled(agent_name, enabled)

    # Enable/disable all schedules for this agent
    # IMPORTANT: Use scheduler_service methods to sync both database AND APScheduler
    schedules = db.list_agent_schedules(agent_name)
    updated_count = 0
    for schedule in schedules:
        schedule_id = schedule.id
        if schedule_id:
            if enabled:
                scheduler_service.enable_schedule(schedule_id)
            else:
                scheduler_service.disable_schedule(schedule_id)
            updated_count += 1

    logger.info(
        f"Autonomy {'enabled' if enabled else 'disabled'} for agent {agent_name} "
        f"by {current_user.username}. Updated {updated_count} schedules."
    )

    return {
        "status": "updated",
        "agent_name": agent_name,
        "autonomy_enabled": enabled,
        "schedules_updated": updated_count,
        "message": f"Autonomy {'enabled' if enabled else 'disabled'}. {updated_count} schedule(s) updated."
    }
```

> **Note**: The service uses `scheduler_service.enable_schedule()` and `scheduler_service.disable_schedule()` (not `db.set_schedule_enabled()` directly) to ensure schedules are synced to APScheduler immediately. This was fixed in 2026-01-11.

#### Bulk Status Logic (lines 115-138)
```python
async def get_all_autonomy_status_logic(
    current_user: User
) -> Dict[str, dict]:
    """Get autonomy status for all agents accessible to the user."""
    all_status = db.get_all_agents_autonomy_status()

    result = {}
    for agent_name, autonomy_enabled in all_status.items():
        if db.can_user_access_agent(current_user.username, agent_name):
            # Skip system agent
            if db.is_system_agent(agent_name):
                continue
            result[agent_name] = {
                "autonomy_enabled": autonomy_enabled
            }

    return result
```

---

## Data Layer

### Database Schema

**File**: `src/backend/database.py`

#### agent_ownership Table (lines 294-302)
```sql
CREATE TABLE agent_ownership (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT UNIQUE NOT NULL,
    owner_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    is_system INTEGER DEFAULT 0,
    use_platform_api_key INTEGER DEFAULT 1,
    autonomy_enabled INTEGER DEFAULT 0,
    FOREIGN KEY (owner_id) REFERENCES users(id)
)
```

#### Migration (lines 219-227)
```python
def _migrate_agent_ownership_autonomy(cursor, conn):
    """Add autonomy_enabled column to agent_ownership table."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    if "autonomy_enabled" not in columns:
        print("Adding autonomy_enabled column to agent_ownership...")
        cursor.execute("ALTER TABLE agent_ownership ADD COLUMN autonomy_enabled INTEGER DEFAULT 0")
        conn.commit()
```

### Database Operations

**File**: `src/backend/db/agents.py`

#### get_autonomy_enabled (lines 325-336)
```python
def get_autonomy_enabled(self, agent_name: str) -> bool:
    """Check if autonomy mode is enabled for agent."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(autonomy_enabled, 0) as autonomy_enabled
            FROM agent_ownership WHERE agent_name = ?
        """, (agent_name,))
        row = cursor.fetchone()
        if row:
            return bool(row["autonomy_enabled"])
        return False  # Default to disabled
```

#### set_autonomy_enabled (lines 338-347)
```python
def set_autonomy_enabled(self, agent_name: str, enabled: bool) -> bool:
    """Set whether autonomy mode is enabled for agent."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE agent_ownership SET autonomy_enabled = ?
            WHERE agent_name = ?
        """, (1 if enabled else 0, agent_name))
        conn.commit()
        return cursor.rowcount > 0
```

#### get_all_agents_autonomy_status (lines 349-357)
```python
def get_all_agents_autonomy_status(self) -> Dict[str, bool]:
    """Get autonomy status for all agents (for dashboard display)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT agent_name, COALESCE(autonomy_enabled, 0) as autonomy_enabled
            FROM agent_ownership
        """)
        return {row["agent_name"]: bool(row["autonomy_enabled"]) for row in cursor.fetchall()}
```

---

## Side Effects

### Schedule Toggling
When autonomy is toggled, all schedules for the agent are enabled/disabled:
```python
schedules = db.list_agent_schedules(agent_name)
for schedule in schedules:
    db.set_schedule_enabled(schedule.id, enabled)
```

### Scheduler Enforcement
The scheduler service double-checks autonomy before executing any schedule:

**File**: `src/backend/services/scheduler_service.py`

```python
async def _execute_schedule(self, schedule_id: str):
    # ... get schedule ...

    if not schedule.enabled:
        logger.info(f"Schedule {schedule_id} is disabled, skipping")
        return

    # Check if agent has autonomy enabled (master switch for all schedules)
    if not db.get_autonomy_enabled(schedule.agent_name):
        logger.info(f"Schedule {schedule_id} skipped: agent {schedule.agent_name} autonomy is disabled")
        return

    # ... execute schedule ...
```

This provides defense-in-depth: even if a schedule is somehow enabled in the database, it won't execute unless the agent's autonomy is also enabled.

### Logging
Server-side logging when autonomy state changes:
```python
logger.info(
    f"Autonomy {'enabled' if enabled else 'disabled'} for agent {agent_name} "
    f"by {current_user.username}. Updated {updated_count} schedules."
)
```

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| No access to agent | 403 | "You don't have permission to access this agent" |
| Not owner (for toggle) | 403 | "Only the owner can modify autonomy settings" |
| Agent not found | 404 | "Agent not found" |
| System agent toggle | 403 | "Cannot modify autonomy for system agent" |
| Missing `enabled` field | 400 | "enabled is required" |

---

## Security Considerations

1. **Access Control**: Only users with access to an agent can view its autonomy status
2. **Owner-Only Toggle**: Only the agent owner (or admin) can modify autonomy settings (uses `can_user_share_agent` permission)
3. **System Agent Protection**: System agents are excluded from autonomy controls entirely
4. **Dashboard Filtering**: Bulk status endpoint only returns agents the user can access, excluding system agents

---

## API Response Examples

### GET /api/agents/autonomy-status
```json
{
  "my-agent": { "autonomy_enabled": true },
  "another-agent": { "autonomy_enabled": false }
}
```

### GET /api/agents/{name}/autonomy
```json
{
  "agent_name": "my-agent",
  "autonomy_enabled": true,
  "total_schedules": 3,
  "enabled_schedules": 3,
  "status": "running"
}
```

### PUT /api/agents/{name}/autonomy
Request:
```json
{ "enabled": true }
```

Response:
```json
{
  "status": "updated",
  "agent_name": "my-agent",
  "autonomy_enabled": true,
  "schedules_updated": 3,
  "message": "Autonomy enabled. 3 schedule(s) updated."
}
```

---

## Testing

### Prerequisites
- Trinity platform running (`./scripts/deploy/start.sh`)
- At least one agent created
- At least one schedule configured for the agent

### Test Steps

1. **Dashboard Toggle Switch**
   - Action: Open Dashboard (/)
   - Expected: Agent cards show toggle switch with "Manual" label (gray)
   - Verify: Click toggle - switch slides right, label changes to "AUTO" (amber)
   - Verify: Click again - switch slides left, returns to "Manual"

2. **Dashboard Toggle Immediate Effect**
   - Action: Toggle autonomy on an agent with schedules
   - Expected: Schedules are immediately enabled/disabled in the backend
   - Verify: Open Agent Detail → Schedules tab, confirm schedule states match

3. **Toggle from Agent Detail**
   - Action: Open agent detail page, click "Manual" button
   - Expected: Button changes to "AUTO", success notification shows schedule count
   - Verify: Refresh page - state persists

3. **Disable Autonomy**
   - Action: Click "AUTO" button on an agent with autonomy enabled
   - Expected: Button changes to "Manual", schedules paused notification
   - Verify: Check Schedules tab - all schedules should be disabled

4. **System Agent Exclusion**
   - Action: Navigate to trinity-system agent
   - Expected: No autonomy toggle button visible
   - Verify: API call returns 403 for system agent

5. **Non-Owner Access**
   - Action: As non-owner, try to toggle autonomy on shared agent
   - Expected: Toggle button not visible (only visible if can_share)
   - Verify: Direct API call returns 403

### Status
- Working (2026-01-03)

---

## Related Flows

- **Upstream**: [Scheduling](scheduling.md) - Autonomy controls schedule enabled/disabled state
- **Related**: [Agent Lifecycle](agent-lifecycle.md) - Agent must exist for autonomy to apply
- **Related**: [Agent Sharing](agent-sharing.md) - Shares `can_share` permission check for toggle access

---

## Revision History

| Date | Change |
|------|--------|
| 2026-01-03 | **Dashboard Toggle Switch**: Replaced static "AUTO" badge with interactive toggle switch. Users can now enable/disable autonomy directly from Dashboard agent tiles. Added `toggleAutonomy()` action to network.js store (lines 993-1030). Toggle includes "AUTO/Manual" label with amber/gray styling. |
| 2026-01-03 | Added scheduler enforcement section - scheduler now double-checks autonomy before executing |
| 2026-01-01 | Initial documentation of Autonomy Mode feature |
