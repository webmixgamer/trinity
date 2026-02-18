# Feature: Agents Page UI Improvements

> **Status**: Implemented (2025-12-07, Enhanced 2026-01-09, System Agent Consolidation 2026-01-13, Toggle UX 2026-01-26, Component Standardization 2026-02-12)
> **Tested**: All features verified working
> **Last Updated**: 2026-02-12 - UI Standardization: AutonomyToggle component used instead of inline implementation. Running and Autonomy toggles now on same row (lines 108-123).
>
> **Previous (2026-01-26)** - UX: Unified Start/Stop Toggle: Replaced separate Start/Stop buttons with `RunningStateToggle.vue` component. Shows "Running" (green) or "Stopped" (gray) state. Uses `toggleAgentRunning()` from agents.js store.
>
> **Previous (2026-01-13)** - System Agent Display: System agent now visible on Agents page for admin users only. Pinned at top with purple ring and "SYSTEM" badge. Uses standard AgentDetail.vue with tab filtering instead of dedicated SystemAgent.vue. Added `systemAgent`, `sortedAgentsWithSystem` getters and `displayAgents` computed to conditionally show system agent.

## Overview

Enhance the Agents list page (`/agents`) with status indicators, context stats, and sorting capabilities by reusing existing APIs and components from the Collaboration Dashboard.

## Current State Analysis

### Agents Page (Agents.vue) - Current
- Simple list view with server icon
- Shows: agent name, type, port, RuntimeBadge (Claude/Gemini)
- **Running State Toggle** (2026-01-26): `RunningStateToggle.vue` component with "Running/Stopped" label, green/gray styling, loading spinner
- "Shared by X" badge for shared agents
- Activity state indicators, context stats, sorting (implemented 2025-12-07)

### Collaboration Dashboard (AgentNode.vue) - Already Has
- Activity state (Active/Idle/Offline) with pulsing green dot
- Context progress bar with color coding (green → yellow → orange → red)
- GitHub repo display
- Status dot with pulse animation

### Existing APIs to Reuse
| Endpoint | Purpose | Used By |
|----------|---------|---------|
| `GET /api/agents/context-stats` | Context % + activity state for all agents | network.js, agents.js |
| `GET /api/agents` | Base agent list | agents.js, network.js |

---

## Proposed Improvements

### 1. Activity State Indicator
**Description**: Add a status indicator showing Active/Idle/Offline state for each agent

**Visual Design** (matches AgentNode.vue):
- **Active**: Green pulsing dot (`#10b981`) + "Active" label
- **Idle**: Green static dot (`#10b981`) + "Idle" label
- **Offline**: Gray dot (`#9ca3af`) + "Offline" label

**Implementation**:
- Call `GET /api/agents/context-stats` on mount and poll every 10 seconds
- Parse `activityState` field from response
- Reuse CSS animation from AgentNode.vue:
```css
.active-pulse {
  animation: active-pulse-animation 0.8s ease-in-out infinite;
  box-shadow: 0 0 8px 2px rgba(16, 185, 129, 0.6);
}
```

### 2. Context Progress Bar
**Description**: Show context window usage as a progress bar with color coding

**Visual Design**:
- Mini progress bar under agent name
- Color coding by percentage:
  - 0-49%: Green (`bg-green-500`)
  - 50-74%: Yellow (`bg-yellow-500`)
  - 75-89%: Orange (`bg-orange-500`)
  - 90-100%: Red (`bg-red-500`)
- Text: "Context: XX%"
- Only shown for running agents (hide for stopped/offline)

**Data Source**: `GET /api/agents/context-stats`
- `contextPercent`: Number (0-100)
- `contextUsed`: Number (tokens used)
- `contextMax`: Number (max tokens)

### 3. Sorting & Filtering
**Description**: Add sort controls to organize agent list

**Sort Options**:
- **Default**: Creation date (newest first) - `agent.created`
- Name (A-Z, Z-A)
- Status (running first, stopped first)
- Context usage (highest first) - needs context stats

**UI**: Dropdown select in header area, next to "Create Agent" button

**Implementation**:
```javascript
const sortedAgents = computed(() => {
  const sorted = [...agents]
  switch (sortBy.value) {
    case 'created_desc':
      return sorted.sort((a, b) => new Date(b.created) - new Date(a.created))
    case 'name_asc':
      return sorted.sort((a, b) => a.name.localeCompare(b.name))
    case 'status':
      return sorted.sort((a, b) => (b.status === 'running' ? 1 : 0) - (a.status === 'running' ? 1 : 0))
    // ... etc
  }
})
```

---

## Technical Implementation

### Option A: Extend agents.js Store (Recommended)
Add context stats fetching to existing agents store:

```javascript
// agents.js - New state
contextStats: {},  // Map of agent name -> stats
contextPollingInterval: null,

// New actions
async fetchContextStats() {
  const response = await axios.get('/api/agents/context-stats', {
    headers: authStore.authHeader
  })
  this.contextStats = {}
  response.data.agents.forEach(stat => {
    this.contextStats[stat.name] = stat
  })
},

startContextPolling() {
  this.fetchContextStats()
  this.contextPollingInterval = setInterval(() => {
    this.fetchContextStats()
  }, 10000)  // Every 10 seconds
},

stopContextPolling() {
  if (this.contextPollingInterval) {
    clearInterval(this.contextPollingInterval)
  }
}
```

### Option B: Reuse network.js Store
Import and use existing store (less code, but adds Vue Flow dependency to simple page):

```javascript
import { useNetworkStore } from '../stores/network'

const networkStore = useNetworkStore()

onMounted(() => {
  // Only start context polling, not full collaboration features
  networkStore.fetchContextStats()
  networkStore.startContextPolling()
})

onUnmounted(() => {
  networkStore.stopContextPolling()
})
```

### Recommended: Option A
Keep agents.js self-contained. Extract shared logic into a composable if needed later.

---

## Updated Agents.vue Component Structure

```vue
<template>
  <div class="min-h-screen bg-gray-100">
    <NavBar />

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <!-- Notification Toast (existing) -->

        <div class="flex justify-between items-center mb-8">
          <h1 class="text-3xl font-bold text-gray-900">Agents</h1>

          <div class="flex items-center space-x-4">
            <!-- NEW: Sort dropdown -->
            <select v-model="sortBy" class="...">
              <option value="created_desc">Newest First</option>
              <option value="created_asc">Oldest First</option>
              <option value="name_asc">Name (A-Z)</option>
              <option value="status">Running First</option>
              <option value="context_desc">Context Usage</option>
            </select>

            <button @click="showCreateModal = true" class="...">
              Create Agent
            </button>
          </div>
        </div>

        <!-- Agents List -->
        <div class="bg-white shadow overflow-hidden sm:rounded-md">
          <ul class="divide-y divide-gray-200">
            <li v-for="agent in sortedAgents" :key="agent.name">
              <div class="px-4 py-4 sm:px-6">
                <div class="flex items-center justify-between">
                  <router-link :to="`/agents/${agent.name}`" class="flex-1">
                    <div class="flex items-center">
                      <!-- Agent Icon -->
                      <div class="flex-shrink-0 relative">
                        <ServerIcon class="h-10 w-10 text-gray-400" />
                        <!-- NEW: Activity state indicator dot -->
                        <div
                          :class="[
                            'absolute -bottom-1 -right-1 w-3 h-3 rounded-full border-2 border-white',
                            getActivityDotClass(agent.name)
                          ]"
                        ></div>
                      </div>

                      <div class="ml-4 flex-1">
                        <div class="flex items-center space-x-2">
                          <p class="text-sm font-medium text-indigo-600">{{ agent.name }}</p>
                          <span v-if="agent.is_shared" class="px-2 py-0.5 text-xs ...">
                            Shared by {{ agent.owner }}
                          </span>
                          <!-- NEW: Activity state label -->
                          <span :class="getActivityLabelClass(agent.name)">
                            {{ getActivityState(agent.name) }}
                          </span>
                        </div>

                        <p class="text-sm text-gray-500">Type: {{ agent.type }}</p>

                        <!-- NEW: Context progress bar (only for running) -->
                        <div v-if="agent.status === 'running'" class="mt-2 max-w-xs">
                          <div class="flex items-center justify-between text-xs text-gray-500 mb-1">
                            <span>Context</span>
                            <span>{{ getContextPercent(agent.name) }}%</span>
                          </div>
                          <div class="w-full bg-gray-200 rounded-full h-1.5">
                            <div
                              :class="getProgressBarColor(agent.name)"
                              :style="{ width: getContextPercent(agent.name) + '%' }"
                              class="h-full rounded-full transition-all duration-500"
                            ></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </router-link>

                  <!-- Status badge and controls (existing) -->
                  <div class="flex items-center space-x-2">
                    <!-- ... existing status badge and buttons ... -->
                  </div>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </main>
  </div>
</template>
```

---

## Helper Functions

```javascript
// Activity state helpers (reuse logic from AgentNode.vue)
const getActivityState = (agentName) => {
  const stats = agentsStore.contextStats[agentName]
  if (!stats) return 'Offline'
  return stats.activityState === 'active' ? 'Active'
       : stats.activityState === 'idle' ? 'Idle'
       : 'Offline'
}

const getActivityDotClass = (agentName) => {
  const state = getActivityState(agentName)
  const baseClasses = 'w-3 h-3 rounded-full'
  if (state === 'Active') return `${baseClasses} bg-green-500 active-pulse`
  if (state === 'Idle') return `${baseClasses} bg-green-500`
  return `${baseClasses} bg-gray-400`
}

const getActivityLabelClass = (agentName) => {
  const state = getActivityState(agentName)
  if (state === 'Active' || state === 'Idle') return 'text-xs text-green-600'
  return 'text-xs text-gray-500'
}

// Context helpers
const getContextPercent = (agentName) => {
  const stats = agentsStore.contextStats[agentName]
  return stats ? Math.round(stats.contextPercent || 0) : 0
}

const getProgressBarColor = (agentName) => {
  const percent = getContextPercent(agentName)
  if (percent >= 90) return 'bg-red-500'
  if (percent >= 75) return 'bg-orange-500'
  if (percent >= 50) return 'bg-yellow-500'
  return 'bg-green-500'
}
```

---

## Changes Summary

### Files to Modify
1. **`src/frontend/src/stores/agents.js`**
   - Add `contextStats` state
   - Add `fetchContextStats()` actions
   - Add `startContextPolling()` and `stopContextPolling()` actions

2. **`src/frontend/src/views/Agents.vue`**
   - Add sort dropdown and sorting logic
   - Add activity state indicator (dot + label)
   - Add context progress bar for running agents
   - Add CSS for pulse animation
   - Call polling on mount/unmount

### New Code Reuse
- **API**: `GET /api/agents/context-stats` (already exists)
- **CSS**: Pulse animation from AgentNode.vue
- **Logic**: Progress bar color coding from AgentNode.vue
- **Logic**: Activity state detection from network.js

---

## Implementation Order

1. **Phase 1: Sorting**
   - Add sort dropdown
   - Implement sorting computed property
   - Default to newest first

2. **Phase 2: Context Stats**
   - Add store methods for context stats polling
   - Add activity state indicator (dot + label)
   - Add context progress bar

3. **Phase 3: Polish**
   - Add loading states
   - Test with various agent states
   - Ensure polling stops on unmount

---

## Testing

### Prerequisites
- Backend running with at least 2 agents
- One agent running, one stopped
- Optionally: agent with active plan

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Load `/agents` page | Agents sorted by creation date (newest first) |
| 2 | Check running agent | Shows activity state (Active/Idle), context progress bar |
| 3 | Check stopped agent | Shows "Offline" state, no progress bar |
| 4 | Chat with agent | Activity state changes to "Active" within 5s |
| 5 | Wait 60s after chat | Activity state returns to "Idle" |
| 6 | Change sort to "Name (A-Z)" | Agents reorder alphabetically |
| 7 | Navigate away and back | Polling restarts, data fresh |

---

## Future Enhancements

1. **Search/Filter**: Text search by agent name
2. **Grid View**: Toggle between list and card grid
3. **Bulk Actions**: Start/stop multiple agents
4. **Quick Stats**: Summary bar (X running, Y stopped, Z% avg context)

---

## Enhancement: Dashboard Parity (2026-01-09)

### Overview

Major UI overhaul to align Agents page with Dashboard (AgentNode.vue) tiles. Changed from list view to responsive grid layout with card-based design.

### Changes Made

#### Layout
- **Grid Layout**: Changed from vertical list to responsive 3-column grid (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3`)
- **Card Design**: Each agent displayed in a card matching AgentNode.vue styling (320px width concept, shadow, rounded corners)
- **Stopped Agent Styling**: Cards for stopped agents have reduced opacity (`opacity-75`) for visual distinction

#### New Features Added

1. **Autonomy Toggle** (`Agents.vue` lines 98-133)
   - Interactive toggle switch with AUTO/Manual label
   - Amber color (`bg-amber-500`) when enabled, gray (`bg-gray-200`) when disabled
   - Calls `agentsStore.toggleAutonomy()` via `handleAutonomyToggle()` (line 354-364)
   - Loading state with `autonomyLoading` ref during API call
   - ARIA support with `role="switch"` and `aria-checked`

2. **Execution Stats Row** (`Agents.vue` lines 155-172)
   - Task count (24h): `{{ getExecutionStats(agent.name).taskCount }}`
   - Success rate with color coding:
     - Green (`text-green-600`) for ≥80%
     - Yellow (`text-yellow-600`) for 50-79%
     - Red (`text-red-600`) for <50%
   - Total cost in dollars (conditionally shown if > 0)
   - Last execution time (relative display: "just now", "2m ago", "1h ago", "1d ago")
   - Fallback: "No tasks (24h)" when no execution data

3. **Context Progress Bar Always Visible** (`Agents.vue` lines 140-153)
   - Shows for all agents (not just running ones)
   - Color coded by percentage:
     - Green (`bg-green-500`) for 0-49%
     - Yellow (`bg-yellow-500`) for 50-74%
     - Orange (`bg-orange-500`) for 75-89%
     - Red (`bg-red-500`) for 90-100%
   - Smooth transition: `transition-all duration-500`

4. **RuntimeBadge Integration** (`Agents.vue` line 68)
   - Shows Claude/Gemini icon next to agent name
   - Uses existing `RuntimeBadge` component with `show-label="false"`

#### Store Changes (`agents.js`)

1. **New State** (line 14):
   ```javascript
   executionStats: {},  // Map of agent name -> execution stats
   ```

2. **New Actions**:
   - `fetchExecutionStats()` (lines 523-547): Fetches from `GET /api/agents/execution-stats`
     - Maps response to: `taskCount`, `successCount`, `failedCount`, `runningCount`, `successRate`, `totalCost`, `lastExecutionAt`
   - `toggleAutonomy(agentName)` (lines 550-576): Calls `PUT /api/agents/{name}/autonomy`
     - Toggles `agent.autonomy_enabled` locally after successful API call
     - Returns `{ success, enabled, schedulesUpdated }`

3. **Updated Polling** (lines 578-594):
   - `startContextPolling()` now also calls `fetchExecutionStats()` on mount and every 10 seconds
   - Both `fetchContextStats()` and `fetchExecutionStats()` run in parallel

#### Helper Functions (`Agents.vue` script section)

| Function | Lines | Purpose |
|----------|-------|---------|
| `getActivityState(agentName)` | 279-286 | Returns 'Active', 'Idle', or 'Offline' |
| `isActive(agentName)` | 288-290 | Returns true if agent is actively processing |
| `getStatusDotColor(agentName)` | 292-297 | Returns hex color for status dot |
| `getActivityLabelClass(agentName)` | 299-303 | Returns Tailwind classes for activity label |
| `getContextPercent(agentName)` | 306-309 | Returns rounded context percentage (0-100) |
| `getProgressBarColor(agentName)` | 311-317 | Returns Tailwind bg class based on percentage |
| `getExecutionStats(agentName)` | 320-322 | Returns execution stats object or null |
| `hasExecutionStats(agentName)` | 324-327 | Returns true if taskCount > 0 |
| `getSuccessRateColorClass(agentName)` | 329-336 | Returns color class for success rate |
| `getLastExecutionDisplay(agentName)` | 338-351 | Returns relative time string |
| `handleAutonomyToggle(agent)` | 354-364 | Handles autonomy toggle with loading state |

### Backend Endpoints

1. **GET /api/agents/execution-stats** (`agents.py` lines 144-165)
   - Returns task counts, success rates, costs for all accessible agents
   - Query param: `hours` (default: 24)
   - Response: `{ agents: [{ name, task_count_24h, success_count, failed_count, running_count, success_rate, total_cost, last_execution_at }] }`

2. **PUT /api/agents/{name}/autonomy** (`agents.py` lines 775-790)
   - Body: `{ enabled: boolean }`
   - When enabled: activates all schedules for the agent
   - When disabled: pauses all schedules
   - Response: `{ enabled, schedules_updated }`

3. **GET /api/agents/context-stats** (`agents.py` lines 138-141)
   - Returns context window usage and activity state for all agents
   - Response: `{ agents: [{ name, contextPercent, contextUsed, contextMax, activityState, lastActivityTime }] }`

### Visual Comparison

| Feature | Before | After |
|---------|--------|-------|
| Layout | Vertical list (`<ul>` with `<li>`) | 3-column responsive grid (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3`) |
| Autonomy | Not shown | Toggle switch with AUTO/Manual label |
| Execution Stats | Not shown | Tasks · Success Rate · Cost · Last Run row |
| Context Bar | Only for running agents | All agents (consistent card height) |
| Card Style | Simple table rows | Styled cards with shadow-lg, rounded-xl, hover:shadow-xl |
| Status Indicator | Basic badge | Pulsing dot with activity state label |

### Data Flow

```
User loads /agents page
    └── onMounted() [Agents.vue:269-272]
        ├── agentsStore.fetchAgents() → GET /api/agents
        │   └── Backend: get_accessible_agents() [helpers.py:83-153]
        │       ├── list_all_agents_fast() - Docker labels only (no stats)
        │       └── db.get_all_agent_metadata() - Single JOIN query for all metadata
        │           └── Returns: owner, is_system, autonomy, limits, git config, share access
        └── agentsStore.startContextPolling() [agents.js:578-594]
            ├── fetchContextStats() → GET /api/agents/context-stats
            ├── fetchExecutionStats() → GET /api/agents/execution-stats
            └── setInterval(5000) for continuous updates

User toggles autonomy switch
    └── handleAutonomyToggle(agent) [Agents.vue:354-364]
        └── agentsStore.toggleAutonomy(agentName) [agents.js:550-576]
            └── PUT /api/agents/{name}/autonomy
                └── Updates agent.autonomy_enabled locally
```

### Performance (2026-01-12)

The `/api/agents` endpoint benefits from two optimizations:

1. **Docker Stats Optimization**: `list_all_agents_fast()` (docker_service.py:101-159) extracts data ONLY from container labels, avoiding slow Docker operations (`container.attrs`, `container.stats()`).

2. **Database Batch Queries (N+1 Fix)**: `db.get_all_agent_metadata()` (db/agents.py:467-529) fetches all metadata in a SINGLE JOIN query instead of 8-10 queries per agent.

| Metric | Before | After |
|--------|--------|-------|
| Docker API calls | Full inspect per agent | Labels only |
| Database queries | 160-200 (20 agents) | 2 total |
| Response time | ~2-3 seconds | <50ms |

### Files Modified

1. **`/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/stores/agents.js`** (681 lines total):
   - Line 14: Added `executionStats: {}` state
   - Lines 523-547: Added `fetchExecutionStats()` action
   - Lines 550-576: Added `toggleAutonomy()` action
   - Lines 578-594: Updated `startContextPolling()` to include execution stats

2. **`/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/views/Agents.vue`** (413 lines total):
   - Lines 44-224: Complete rewrite with grid layout and card components
   - Lines 98-133: Autonomy toggle implementation
   - Lines 140-153: Context progress bar (always visible)
   - Lines 155-172: Execution stats row
   - Lines 279-364: Helper functions for stats and autonomy
   - Lines 394-411: CSS for active-pulse animation

### Testing Steps

#### Autonomy Toggle
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Load `/agents` page | See AUTO/Manual label on each agent card |
| 2 | Click toggle on agent | Toggle animates, label changes, API called |
| 3 | Verify in DB | Agent's `autonomy_enabled` field updated |
| 4 | Disable autonomy | All schedules for agent are paused |
| 5 | Re-enable | Schedules resume |

#### Execution Stats
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | View agent with tasks | See "X tasks · Y% · $Z · Nm ago" |
| 2 | View agent without tasks | See "No tasks (24h)" |
| 3 | Verify success rate colors | Green ≥80%, yellow 50-79%, red <50% |
| 4 | Wait 10 seconds | Stats auto-refresh |

#### Context Progress Bar
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | View stopped agent | Context bar shows 0% (gray area visible) |
| 2 | View running agent | Context bar shows actual percentage |
| 3 | Chat with agent | Progress bar fills as context grows |
| 4 | Check color changes | Green → yellow → orange → red as % increases |

### Related Components

- **AgentNode.vue**: Dashboard tiles use same visual design
  - Path: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/components/AgentNode.vue`
  - Lines 52-97: Autonomy toggle (identical implementation)
  - Lines 130-147: Execution stats row
  - Lines 115-128: Context progress bar

---

## Enhancement: System Agent Display (2026-01-13)

### Overview

System agent (`trinity-system`) is now visible on the Agents page for admin users only. Previously, the system agent had a dedicated `/system-agent` page with `SystemAgent.vue`. This has been consolidated - the system agent now uses the standard agent card on the Agents page and `AgentDetail.vue` for the detail view.

### Changes Made

#### Store Changes (`src/frontend/src/stores/agents.js`)

| Getter/Function | Lines | Purpose |
|-----------------|-------|---------|
| `systemAgent` | 25-27 | Returns the agent with `is_system: true` or null |
| `sortedAgentsWithSystem` | 39-41 | Returns sorted agents with system agent pinned at top |
| `_getSortedAgents(includeSystem)` | 43-76 | Helper that conditionally includes system agent |

**Implementation:**
```javascript
// Line 25-27: systemAgent getter
systemAgent() {
  return this.agents.find(agent => agent.is_system) || null
}

// Line 39-41: sortedAgentsWithSystem getter
sortedAgentsWithSystem() {
  return this._getSortedAgents(true)
}

// Lines 70-74: Pin system agent at top
if (includeSystem && this.systemAgent) {
  return [this.systemAgent, ...sorted]
}
```

#### View Changes (`src/frontend/src/views/Agents.vue`)

1. **Admin Check** (lines 271, 288-305):
   - `isAdmin` ref initialized to `false`
   - On mount, fetches `/api/users/me` to check if `role === 'admin'`
   - Used to conditionally show system agent

2. **Display Agents Computed** (lines 274-279):
   ```javascript
   const displayAgents = computed(() => {
     if (isAdmin.value) {
       return agentsStore.sortedAgentsWithSystem
     }
     return agentsStore.sortedAgents
   })
   ```

3. **System Agent Card Styling** (lines 46-57):
   ```vue
   :class="[
     'bg-white dark:bg-gray-800 rounded-xl border shadow-lg p-5',
     agent.is_system
       ? 'ring-2 ring-purple-500/50 border-purple-300 dark:border-purple-700'
       : agent.status === 'running'
         ? 'border-gray-200/60 dark:border-gray-700/50'
         : 'border-gray-200 dark:border-gray-700 opacity-75'
   ]"
   ```

4. **SYSTEM Badge** (lines 69-75):
   ```vue
   <span
     v-if="agent.is_system"
     class="ml-2 px-1.5 py-0.5 text-xs font-semibold bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300 rounded flex-shrink-0"
   >
     SYSTEM
   </span>
   ```

#### Router Changes (`src/frontend/src/router/index.js`)

- Lines 77-81: Legacy `/system-agent` redirects to `/agents/trinity-system`
  ```javascript
  {
    path: '/system-agent',
    redirect: '/agents/trinity-system'
  }
  ```

#### NavBar Changes (`src/frontend/src/components/NavBar.vue`)

- "System" link removed from navigation bar
- System agent accessed via Agents page or direct URL `/agents/trinity-system`

### Visual Design

| Aspect | Regular Agent | System Agent |
|--------|---------------|--------------|
| Border | Gray border | Purple ring + purple border |
| Badge | (none) | "SYSTEM" badge (purple) |
| Position | Sorted by sortBy setting | Always pinned at top |
| Visibility | All users | Admin users only |

### Testing Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as admin user | See system agent at top of Agents page |
| 2 | Login as regular user | System agent NOT visible |
| 3 | Navigate to `/system-agent` | Redirects to `/agents/trinity-system` |
| 4 | Click system agent card | Opens AgentDetail with filtered tabs |
| 5 | Verify system agent styling | Purple ring, "SYSTEM" badge visible |

---

## References

> Line numbers verified 2026-01-09
- **Agents.vue**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/views/Agents.vue` (413 lines total)
- **agents.js store**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/stores/agents.js` (681 lines total)
- **AgentNode.vue**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/components/AgentNode.vue` (393 lines) - Visual design reference
- **Backend agents router**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/routers/agents.py`
  - Lines 138-141: GET /context-stats endpoint
  - Lines 144-165: GET /execution-stats endpoint
  - Lines 775-790: PUT /{name}/autonomy endpoint
- **Backend helpers**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/services/agent_service/helpers.py`
  - Lines 83-153: `get_accessible_agents()` with batch query optimization

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-02-18 | **Read-Only Toggle + Tags Layout Fix**: Added `ReadOnlyToggle` component to toggles row (Agents.vue:248-255) between Running and Autonomy. Fixed tags breaking tile layout by adding fixed height container (`h-6 overflow-hidden`, line 271) and `max-w-20 truncate` on individual tags (line 276). Added `agentReadOnlyStates` state (line 378), `readOnlyLoading` (line 377), `fetchAllReadOnlyStates()` (lines 544-563), `getAgentReadOnlyState()` (lines 540-542), `handleReadOnlyToggle()` (lines 565-594). Import at line 368. Toggle only shown for owned agents (`v-if="!agent.is_system && !agent.is_shared"`). |
| 2026-02-12 | **UI Standardization**: AutonomyToggle now uses reusable `AutonomyToggle.vue` component (151 lines) imported at Agents.vue:367. Running, ReadOnly, and Autonomy toggles positioned on same row (Agents.vue:240-263) for visual consistency with Dashboard. See [autonomy-toggle-component.md](autonomy-toggle-component.md) for component details. |
| 2026-01-26 | **Unified Start/Stop Toggle**: Replaced Start/Stop buttons with `RunningStateToggle.vue` component. |
| 2026-01-13 | **System Agent Display**: System agent now visible on Agents page for admin users only. Added `systemAgent` getter (agents.js:25-27), `sortedAgentsWithSystem` getter (agents.js:39-41), `displayAgents` computed (Agents.vue:391-403), admin check on mount (Agents.vue:427-439). System agent card has purple ring (`ring-2 ring-purple-500/50`) and "SYSTEM" badge (Agents.vue:174-183, 202-208). Legacy `/system-agent` route redirects to `/agents/trinity-system`. Removed "System" link from NavBar. |
| 2026-01-12 | **Polling interval optimization**: Context/execution stats polling changed from 5s to 10s for reduced API load. Updated all polling interval references and test cases. |
| 2026-01-12 | **Database Batch Queries (N+1 Fix)**: Added Performance section documenting `get_accessible_agents()` optimization. Now uses `db.get_all_agent_metadata()` (db/agents.py:467-529) for single JOIN query. Database queries reduced from 160-200 to 2 per request. Combined with Docker stats optimization for <50ms response. Updated Data Flow diagram. |
| 2026-01-09 | **Dashboard Parity**: Major UI overhaul - grid layout, autonomy toggle, execution stats row, context bar always visible. Added `fetchExecutionStats()` and `toggleAutonomy()` to agents.js store. |
| 2025-12-07 | Initial implementation with sorting, activity state indicators, context progress bars. |
