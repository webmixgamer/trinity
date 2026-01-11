# Feature Flow: Dashboard Timeline View

> **Last Updated**: 2026-01-11 (Fixed execution ID extraction from activity.related_execution_id)
> **Status**: Implemented
> **Requirements Doc**: `docs/requirements/DASHBOARD_TIMELINE_VIEW.md`, `docs/requirements/TIMELINE_ALL_EXECUTIONS.md`

## Overview

The Dashboard offers two views for monitoring the agent fleet:
- **Graph View**: Node-based visualization showing agents as nodes with collaboration edges (VueFlow)
- **Timeline View**: Waterfall-style activity timeline with rich agent tiles and live event streaming

**Key Feature**: Views are mutually exclusive - Graph is hidden when Timeline is active.

**All Executions**: Timeline shows ALL execution types - scheduled tasks, manual tasks, and agent-triggered tasks. Collaboration events only create arrows (not boxes).

## User Journey

### Switching Views

1. User navigates to Dashboard (`/`)
2. Toggle buttons in header: `[Graph] [Timeline]`
3. Click "Timeline" to switch to Timeline view
4. **Graph canvas is hidden** - only Timeline shows
5. View preference persisted in localStorage (`trinity-dashboard-view`)

### Timeline View Features

1. **Default Zoom: Last 2 Hours**
   - On page load, zoom defaults to `timeRangeHours / 2`
   - For 24h range, zoom is 12x (shows ~2 hours of activity)
   - Auto-scrolls to "Now" position

2. **Rich Agent Tiles** (left column, 240px):
   - Row 1: Agent name, system badge (SYS), status dot with active pulse
   - Row 2: Autonomy toggle (AUTO/Manual switch)
   - Row 3: Context progress bar with percentage
   - Row 4: Execution stats (tasks, success rate, cost) or "No tasks"
   - Row 5: Memory limit display

3. **Live Event Streaming**
   - WebSocket remains connected (unlike old Replay mode)
   - New collaboration events appear at right edge
   - "Now" marker updates every second
   - Auto-scroll keeps latest events visible

4. **Timeline Grid** (right area)
   - 15-minute interval time ticks
   - Activity bars showing execution duration
   - Communication arrows between agents (only when both have boxes)
   - "Now" vertical line (green, updates continuously)

5. **Controls**
   - Zoom: +/- buttons and slider (0.5x to 20x)
   - "Active only" toggle: Hide agents with no activity
   - "Jump to Now" button: Re-enables auto-scroll when scrolled away

6. **NOW Marker Positioning**
   - NOW marker positioned at 90% of viewport width (not at far right edge)
   - 10% empty space to the right of NOW for visual breathing room
   - Users cannot scroll past the NOW position into the future
   - Auto-scroll positions NOW at the 90% mark

7. **Click to View Execution Details**
   - Hover over execution bar shows tooltip with type, status, duration
   - Click on execution bar opens Execution Detail page in a new tab
   - Navigation uses **Database Execution ID** (from `related_execution_id` field), not Queue ID
   - Fallback to Tasks tab if no execution ID available

## Data Flow

```
+-------------------+    +------------------+    +-------------------+
|   Dashboard.vue   |----| network.js store |----| ReplayTimeline.vue|
|   (Parent)        |    |                  |    | (Component)       |
+-------------------+    +------------------+    +-------------------+
        |                        |                        |
        |                        |                        v
        |                        |              +-------------------+
        |                        |              | Compact Agent     |
        |                        |              | Tiles (240px)     |
        |                        |              +-------------------+
        |                        v
        |              +------------------+
        |              | WebSocket        |
        |              | (Live events)    |
        |              +------------------+
        |                        |
        v                        v
+-------------------+    +------------------+
| setViewMode()     |    | contextStats     |
| - graph           |    | executionStats   |
| - timeline        |    | (5s polling)     |
+-------------------+    +------------------+
```

### Execution ID Handling

**Two ID Systems** (documented 2026-01-11):

| ID Type | Format | Source | Purpose |
|---------|--------|--------|---------|
| Queue Execution ID | UUID v4 | Redis queue | Internal queue management, 10-min TTL |
| Database Execution ID | `token_urlsafe(16)` | `schedule_executions.id` | API access, UI navigation, permanent |

**Timeline uses Database Execution ID** for navigation:
- Activities have `related_execution_id` field linking to `schedule_executions.id`
- Click on execution bar navigates to `/agents/{name}/executions/{database_id}`
- The `details.execution_id` in WebSocket events also contains the Database ID

### Props Passed to ReplayTimeline

| Prop | Source | Purpose |
|------|--------|---------|
| `agents` | `networkStore.agents` | Agent list with status |
| `nodes` | VueFlow nodes array | Full node data for tiles |
| `events` | `networkStore.historicalCollaborations` | Timeline events (executions + collaborations) |
| `contextStats` | `networkStore.contextStats` | Context usage per agent |
| `executionStats` | `networkStore.executionStats` | Task stats per agent |
| `isLiveMode` | Hardcoded `true` | Enables live features |
| `timeRangeHours` | `selectedTimeRange` | For default zoom calculation |

### Events Emitted by ReplayTimeline

| Event | Payload | Purpose |
|-------|---------|---------|
| `toggle-autonomy` | `agentName` | Toggle autonomy mode for agent |

## Key Implementation Details

### 1. Graph Hidden in Timeline Mode

```vue
<!-- Dashboard.vue:142-167 -->
<ReplayTimeline v-if="isTimelineMode" ... />
<div v-if="!isTimelineMode" class="...">
  <!-- VueFlow Graph -->
</div>
```

### 2. Execution Events vs Collaboration Events

**Critical Distinction**: Only execution events create boxes on the timeline. Collaboration events only create arrows.

```javascript
// ReplayTimeline.vue:543-579
props.events.forEach((event, index) => {
  // Skip collaboration events for boxes - they only create arrows
  // The target agent will have its own chat_start event with triggered_by='agent'
  if (event.activity_type === 'agent_collaboration') {
    return
  }

  // Add activity box for the executing agent
  agentActivityMap.get(event.source_agent).push({
    time: new Date(event.timestamp).getTime(),
    type: 'execution',
    activityType: event.activity_type,
    triggeredBy: event.triggered_by,
    scheduleName: event.schedule_name
  })
})
```

### 3. Source Agent Mapping (network.js)

**Key Fix**: The `source_agent` field is mapped differently for execution vs collaboration events.

```javascript
// network.js:161-171
const isCollaboration = activity.activity_type === 'agent_collaboration'

return {
  // For execution events (chat_start, schedule_start): use agent_name (the executor)
  // For collaboration events: use details.source_agent (the caller) for arrows
  source_agent: isCollaboration ? (details.source_agent || activity.agent_name) : activity.agent_name,
  target_agent: details.target_agent || null,  // null for non-collaboration events
  // ...
}
```

**Why This Matters**:
- When Agent A calls Agent B:
  - Agent A's execution shows on A's row (source_agent = A)
  - The collaboration arrow goes from A to B (source_agent = A, target_agent = B)
  - Agent B's triggered execution shows on B's row (source_agent = B, triggered_by = 'agent')

### 4. Trigger-Based Color Coding

Activity bars are colored by what triggered them, not the activity type:

| Trigger | Color | Active | Inactive | Description |
|---------|-------|--------|----------|-------------|
| Error | Red | `#ef4444` | - | Any failed execution |
| In Progress | Amber | `#f59e0b` | - | Currently running |
| `schedule` | Purple | `#8b5cf6` | `#c4b5fd` | Scheduled executions |
| `agent` | Cyan | `#06b6d4` | `#67e8f9` | Agent-triggered (called by another agent) |
| `manual`/`user` | Green | `#22c55e` | `#86efac` | Manual task executions |
| Default | Blue | `#3b82f6` | `#93c5fd` | Unknown trigger type |

```javascript
// ReplayTimeline.vue:841-868
function getBarColor(activity) {
  if (activity.hasError) return '#ef4444'  // Red for errors
  if (activity.isInProgress) return '#f59e0b'  // Amber for in-progress

  // Color by trigger type (not activity type)
  const triggeredBy = activity.triggeredBy
  const activityType = activity.activityType

  // Scheduled executions -> Purple
  if (activityType?.startsWith('schedule_') || triggeredBy === 'schedule') {
    return activity.active ? '#8b5cf6' : '#c4b5fd'
  }

  // Agent-triggered executions (called by another agent) -> Cyan
  if (triggeredBy === 'agent') {
    return activity.active ? '#06b6d4' : '#67e8f9'
  }

  // Manual/user executions -> Green
  if (triggeredBy === 'manual' || triggeredBy === 'user' || activityType?.startsWith('chat_')) {
    return activity.active ? '#22c55e' : '#86efac'
  }

  // Default blue for unknown types
  return activity.active ? '#3b82f6' : '#93c5fd'
}
```

### 5. Arrow Drawing with Box Validation

Arrows are only drawn when the target agent has an execution box within 30 seconds of the collaboration event. This prevents "floating arrows" that point to nothing.

```javascript
// ReplayTimeline.vue:661-753
const communicationArrows = computed(() => {
  // Build a map of which agents have activity boxes and their time ranges
  const agentActivityTimeRanges = new Map()
  filteredAgentRows.value.forEach(row => {
    if (row.activities && row.activities.length > 0) {
      const ranges = row.activities.map(act => ({
        startTime: startTime.value + (act.x / actualGridWidth.value) * duration.value,
        endTime: startTime.value + ((act.x + act.width) / actualGridWidth.value) * duration.value
      }))
      agentActivityTimeRanges.set(row.name, ranges)
    }
  })

  return chronoEvents.map((event, chronoIndex) => {
    // Only process collaboration events (those with target_agent)
    if (!event.target_agent) return null

    const time = new Date(event.timestamp).getTime()

    // Check if target agent has an activity box near this time
    const targetRanges = agentActivityTimeRanges.get(event.target_agent)
    if (!targetRanges || targetRanges.length === 0) {
      return null  // Target has no activity boxes at all
    }

    // Find if there's a box on target agent that could be the triggered execution
    // Look for boxes that start within ~30 seconds of the collaboration event
    const toleranceMs = 30000  // 30 second window
    const hasMatchingTargetBox = targetRanges.some(range => {
      return Math.abs(range.startTime - time) < toleranceMs
    })

    if (!hasMatchingTargetBox) {
      return null  // No matching target box - don't draw a floating arrow
    }

    // ... create arrow with validated endpoints
  }).filter(a => a !== null)
})
```

### 6. Legend Display

The legend shows the three execution trigger types:

```html
<!-- ReplayTimeline.vue:68-81 -->
<div class="hidden sm:flex items-center space-x-3">
  <span title="Manual task executions">
    <span class="w-2 h-2 rounded" style="background-color: #22c55e"></span>
    <span>Manual</span>
  </span>
  <span title="Scheduled task executions">
    <span class="w-2 h-2 rounded" style="background-color: #8b5cf6"></span>
    <span>Scheduled</span>
  </span>
  <span title="Agent-triggered executions (called by another agent)">
    <span class="w-2 h-2 rounded" style="background-color: #06b6d4"></span>
    <span>Agent-Triggered</span>
  </span>
</div>
```

### 7. Fetching All Execution Types

The timeline fetches ALL execution types from the backend:

```javascript
// network.js:127-135
const params = {
  activity_types: 'agent_collaboration,schedule_start,schedule_end,chat_start,chat_end',
  start_time: startTime.toISOString(),
  limit: 500
}
```

**Filtering Logic**:
- Keep: `agent_collaboration` - all (for arrows only)
- Keep: `schedule_start` / `schedule_end` - all
- Keep: `chat_start` / `chat_end` where `triggered_by != 'user'` (agent-initiated)
- Keep: `chat_start` / `chat_end` where `details.parallel_mode == true` (manual tasks)
- Skip: `chat_start` / `chat_end` where `triggered_by == 'user'` AND NOT `parallel_mode` (regular user chats)

### 8. Duration-Based Activity Bar Widths

Activity bars show width proportional to execution duration:

```javascript
// ReplayTimeline.vue:595-607
const durationMs = event.duration_ms || 30000  // Default 30s when null
const minBarWidth = 12  // Minimum width for visibility

let barWidth = minBarWidth
if (act.durationMs > 0) {
  // Convert duration to pixels: (durationMs / totalMs) * gridWidth
  barWidth = Math.max(minBarWidth, (act.durationMs / duration.value) * actualGridWidth.value)
}
```

### 9. NOW Marker at 90% Viewport Position

```javascript
// ReplayTimeline.vue:420-428
function scrollToNow() {
  const container = timelineContainer.value
  const viewportWidth = container.clientWidth - labelWidth
  const nowPosition = labelWidth + nowX.value
  const targetScroll = nowPosition - (viewportWidth * 0.9)
  container.scrollLeft = Math.max(0, targetScroll)
}
```

### 10. Future Scroll Prevention

```javascript
// ReplayTimeline.vue:435-455
function handleScroll() {
  const container = timelineContainer.value
  const viewportWidth = container.clientWidth - labelWidth
  const nowPosition = labelWidth + nowX.value
  const maxAllowedScroll = Math.max(0, nowPosition - (viewportWidth * 0.9))

  // Clamp scroll to prevent scrolling into the future
  if (container.scrollLeft > maxAllowedScroll + 10) {
    container.scrollLeft = maxAllowedScroll
  }
}
```

### 11. Future Padding for 90% Positioning

```javascript
// ReplayTimeline.vue:464-467
const actualGridWidth = computed(() => baseGridWidth * zoomLevel.value)
// In live mode, add ~11% padding after NOW so it appears at ~90% of viewport
const futurePadding = computed(() => props.isLiveMode ? Math.max(150, actualGridWidth.value * 0.11) : 0)
const timelineWidth = computed(() => labelWidth + actualGridWidth.value + futurePadding.value)
```

### 12. Enhanced Tooltips

```javascript
// ReplayTimeline.vue:870-900
function getBarTooltip(activity) {
  let prefix = ''
  const activityType = activity.activityType
  const triggeredBy = activity.triggeredBy

  if (activityType?.startsWith('schedule_') || triggeredBy === 'schedule') {
    prefix = activity.scheduleName ? `Scheduled: ${activity.scheduleName}` : 'Scheduled Task'
  } else if (triggeredBy === 'agent') {
    prefix = 'Agent-Triggered Task'
  } else if (triggeredBy === 'manual') {
    prefix = 'Manual Task'
  } else if (triggeredBy === 'user' || activityType?.startsWith('chat_')) {
    prefix = 'Task'
  } else {
    prefix = 'Execution'
  }

  // Status suffix
  let status = ''
  if (activity.hasError) status = '(Error)'
  else if (activity.isInProgress) status = '(In Progress)'

  const duration = activity.isEstimated
    ? `~${formatDuration(activity.durationMs)}`
    : formatDuration(activity.durationMs)

  return `${prefix} ${status} - ${duration}`
}
```

## Testing

### Prerequisites
- [x] Backend running at http://localhost:8000
- [x] Frontend running at http://localhost
- [x] At least 2 agents created
- [x] Some execution history (scheduled, manual, or agent-triggered)

### Test Steps

#### 1. Toggle Between Views
**Action**: Click "Graph" and "Timeline" buttons
**Expected**:
- Graph view shows VueFlow node visualization
- Timeline view shows waterfall timeline **without Graph overlay**
- Toggle state reflects current view

**Verify**:
- [x] Button highlighting updates correctly
- [x] Graph canvas completely hidden in Timeline mode
- [x] localStorage key `trinity-dashboard-view` updates

#### 2. Execution Box Color Coding
**Action**: Trigger different execution types and view in Timeline
**Expected**:
- Manual tasks show as **green** boxes
- Scheduled tasks show as **purple** boxes
- Agent-triggered tasks show as **cyan** boxes
- Errors show as **red** boxes
- In-progress show as **amber** boxes

**Verify**:
- [x] Colors match the legend in header
- [x] Legend shows "Manual", "Scheduled", "Agent-Triggered"
- [x] Tooltips show correct execution type

#### 3. Collaboration Arrows
**Action**: Have Agent A call Agent B via MCP
**Expected**:
- Agent A's execution appears as a box on A's row
- Cyan arrow drawn from A to B
- Agent B's triggered execution appears as cyan box on B's row
- Arrow connects the two boxes

**Verify**:
- [x] Arrow only appears if both agents have execution boxes
- [x] No "floating arrows" pointing to empty space
- [x] Arrow timestamp aligns with collaboration event

#### 4. No Floating Arrows
**Action**: Create collaboration event where target has no execution
**Expected**:
- Arrow should NOT be drawn
- Only collaboration events with matching target execution boxes get arrows

**Verify**:
- [x] 30-second tolerance window for matching
- [x] Arrows filtered out when target has no boxes
- [x] Console shows filtered collaboration count

#### 5. Source Agent Attribution
**Action**: Agent A triggers Agent B, verify both rows
**Expected**:
- A's execution box on A's row (green or purple depending on trigger)
- Arrow from A to B
- B's execution box on B's row (cyan = agent-triggered)

**Verify**:
- [x] Execution events use `activity.agent_name` as source
- [x] Collaboration events use `details.source_agent` for arrow origin
- [x] B's box shows `triggered_by: 'agent'`

#### 6. Live Event Streaming
**Action**: Trigger new executions while viewing Timeline
**Expected**:
- New execution boxes appear at right edge
- Collaboration arrows appear when applicable
- Timeline auto-scrolls to show new events

**Verify**:
- [x] WebSocket connection indicator stays green
- [x] New events appear without page refresh
- [x] Colors applied correctly to new events

#### 7. Now Marker Positioning
**Action**: Wait and observe "Now" marker
**Expected**:
- "NOW" label positioned at 90% of viewport width
- 10% empty space visible to the right
- Green vertical line updates every second

**Verify**:
- [x] Cannot scroll past NOW into the future
- [x] "Jump to Now" button appears when scrolled away
- [x] Auto-scroll keeps NOW at 90% position

#### 8. Click to View Execution Details
**Action**: Click on an execution bar in the timeline
**Expected**:
- Opens Execution Detail page in a new browser tab
- URL is `/agents/{agent_name}/executions/{execution_id}`
- Full execution metadata, transcript, and response visible

**Verify**:
- [x] Hover shows tooltip with "(Click to open in new tab)"
- [x] Click opens new tab (not same-tab navigation)
- [x] Execution Detail page loads with correct data
- [x] For executions without ID, opens Tasks tab in new tab

### Edge Cases
- [x] 0 agents: Empty timeline with just "Now" marker
- [x] Agent with no executions: Row visible but no boxes
- [x] Collaboration without target execution: Arrow not drawn
- [x] Multiple rapid collaborations: Each gets own arrow if box exists
- [x] Agent calls itself: Arrow from row to same row (if box exists)

**Last Tested**: 2026-01-11
**Status**: Fully implemented and tested

## Backend Bug Fixes

### Collaboration Activity Completion on Error (2026-01-10)

**Issue**: Collaboration activities were stuck in "started" state when chat requests failed with HTTP errors.

**Root Cause**: The HTTP error handler in `routers/chat.py` was missing the `complete_activity()` call for `collaboration_activity_id`.

**Fix Location**: `src/backend/routers/chat.py:386-392`

```python
# Complete collaboration activity on failure
if collaboration_activity_id:
    await activity_service.complete_activity(
        activity_id=collaboration_activity_id,
        status="failed",
        error=error_msg
    )
```

**Impact**: Collaboration activities now properly show "failed" status with `duration_ms` calculated.

## Revision History

| Date | Change |
|------|--------|
| 2026-01-11 | **Fix**: Frontend network.js now correctly reads `related_execution_id` from top-level activity field (was only checking details) |
| 2026-01-11 | **Docs**: Clarified execution ID handling - navigation uses Database ID (from `related_execution_id`), not Queue ID |
| 2026-01-11 | **UX**: Click opens Execution Detail page in new tab instead of same-tab navigation |
| 2026-01-10 | **Feature**: Click-to-navigate - Click execution bar to view details |
| 2026-01-10 | **Major**: Execution-only boxes - collaboration events only create arrows, not boxes |
| 2026-01-10 | **Major**: Trigger-based color coding - Green=Manual, Purple=Scheduled, Cyan=Agent-Triggered |
| 2026-01-10 | **Major**: Arrow validation - 30-second tolerance window, prevents floating arrows |
| 2026-01-10 | **Fix**: Source agent mapping - execution events use `agent_name`, collaboration events use `details.source_agent` |
| 2026-01-10 | Updated legend to show "Manual", "Scheduled", "Agent-Triggered" |
| 2026-01-10 | NOW marker at 90% viewport: positioned at 90% width with 10% padding on right |
| 2026-01-10 | Future scroll prevention: users cannot scroll past NOW into the future |
| 2026-01-10 | Added `futurePadding` computed property (~11% padding in live mode) |
| 2026-01-10 | All Executions: Timeline now shows scheduled, manual, and collaboration events |
| 2026-01-10 | Added duration-based bar widths, enhanced tooltips, visual improvements |
| 2026-01-10 | Fixed collaboration activity completion bug in HTTP error handler |
| 2026-01-10 | Initial documentation
