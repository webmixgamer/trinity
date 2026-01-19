# Implementation Plan: Frontend Polling Optimization

> **Priority**: MEDIUM
> **Estimated Impact**: ~50 req/min → ~20 req/min per agent page
> **Dependencies**: None (can be done independently)
> **Related Issue**: Aggressive frontend polling overwhelming backend

---

## Problem Summary

Multiple concurrent polling loops run from a single `AgentDetail.vue` page:

| Composable | Current Interval | Requests/min |
|------------|------------------|--------------|
| `useSessionActivity.js` | **2 seconds** | 30 |
| `useAgentStats.js` | 5 seconds | 12 |
| `useAgentLogs.js` | 10 seconds | 6 |
| `useGitSync.js` | 30 seconds | 2 |
| **TOTAL** | - | **~50** |

With multiple users or browser tabs, this load multiplies significantly.

---

## Solution: Reduce Polling Intervals

Increase intervals to more reasonable values while maintaining acceptable UX.

| Composable | Current | Recommended | Change |
|------------|---------|-------------|--------|
| `useSessionActivity.js` | 2s | 5s | -60% |
| `useAgentStats.js` | 5s | 10s | -50% |
| `useAgentLogs.js` | 10s | 15s | -33% |
| `useGitSync.js` | 30s | 60s | -50% |
| **TOTAL** | ~50/min | **~20/min** | -60% |

---

## Implementation Steps

### Step 1: Update useSessionActivity.js

**File**: `src/frontend/src/composables/useSessionActivity.js`

**Line 117** - Change from 2000ms to 5000ms:

```javascript
// Before:
activityRefreshInterval = setInterval(loadSessionActivity, 2000) // Every 2 seconds

// After:
activityRefreshInterval = setInterval(loadSessionActivity, 5000) // Every 5 seconds
```

**Rationale**: Activity status updates (active/idle/processing) don't need sub-second precision. 5 seconds is responsive enough for users to notice state changes.

---

### Step 2: Update useAgentStats.js

**File**: `src/frontend/src/composables/useAgentStats.js`

**Line 59** - Change from 5000ms to 10000ms:

```javascript
// Before:
statsRefreshInterval = setInterval(loadStats, 5000) // Then every 5 seconds

// After:
statsRefreshInterval = setInterval(loadStats, 10000) // Then every 10 seconds
```

**Also update Line 4** - Adjust history configuration for new interval:

```javascript
// Before:
// History configuration: 60 samples at 5s intervals = 5 minutes
const MAX_POINTS = 60

// After:
// History configuration: 30 samples at 10s intervals = 5 minutes
const MAX_POINTS = 30
```

**Rationale**: CPU/memory stats don't change rapidly. 10-second updates are sufficient for monitoring. The sparkline history still covers 5 minutes.

---

### Step 3: Update useAgentLogs.js

**File**: `src/frontend/src/composables/useAgentLogs.js`

**Line 45** - Change from 10000ms to 15000ms:

```javascript
// Before:
logsRefreshInterval = setInterval(refreshLogs, 10000)

// After:
logsRefreshInterval = setInterval(refreshLogs, 15000)
```

**Rationale**: Log auto-refresh is opt-in (toggle). Users actively watching logs can click "Refresh" if needed. 15 seconds is reasonable for background updates.

---

### Step 4: Update useGitSync.js

**File**: `src/frontend/src/composables/useGitSync.js`

**Line 164** - Change from 30000ms to 60000ms:

```javascript
// Before:
gitStatusInterval = setInterval(loadGitStatus, 30000) // Then every 30 seconds

// After:
gitStatusInterval = setInterval(loadGitStatus, 60000) // Then every 60 seconds
```

**Rationale**: Git status rarely changes. Users typically trigger manual syncs. 60 seconds is sufficient for showing "X changes pending" badge.

---

## Files to Modify

| File | Line | Change |
|------|------|--------|
| `src/frontend/src/composables/useSessionActivity.js` | 117 | 2000 → 5000 |
| `src/frontend/src/composables/useAgentStats.js` | 4, 59 | MAX_POINTS 60→30, 5000→10000 |
| `src/frontend/src/composables/useAgentLogs.js` | 45 | 10000 → 15000 |
| `src/frontend/src/composables/useGitSync.js` | 164 | 30000 → 60000 |

---

## Code Changes Summary

### useSessionActivity.js
```diff
  const startActivityPolling = () => {
    loadSessionActivity() // Load immediately
-   activityRefreshInterval = setInterval(loadSessionActivity, 2000) // Then every 2 seconds
+   activityRefreshInterval = setInterval(loadSessionActivity, 5000) // Then every 5 seconds
  }
```

### useAgentStats.js
```diff
- // History configuration: 60 samples at 5s intervals = 5 minutes
- const MAX_POINTS = 60
+ // History configuration: 30 samples at 10s intervals = 5 minutes
+ const MAX_POINTS = 30

  const startStatsPolling = () => {
    initHistory() // Reset history on start
    loadStats() // Load immediately
-   statsRefreshInterval = setInterval(loadStats, 5000) // Then every 5 seconds
+   statsRefreshInterval = setInterval(loadStats, 10000) // Then every 10 seconds
  }
```

### useAgentLogs.js
```diff
  // Watch for auto-refresh toggle
  watch(autoRefreshLogs, (enabled) => {
    if (enabled) {
-     logsRefreshInterval = setInterval(refreshLogs, 10000)
+     logsRefreshInterval = setInterval(refreshLogs, 15000)
    } else {
```

### useGitSync.js
```diff
  const startGitStatusPolling = () => {
    if (!hasGitSync.value) return
    loadGitStatus() // Load immediately
-   gitStatusInterval = setInterval(loadGitStatus, 30000) // Then every 30 seconds
+   gitStatusInterval = setInterval(loadGitStatus, 60000) // Then every 60 seconds
  }
```

---

## Testing Plan

### Request Volume Verification

1. Open browser DevTools → Network tab
2. Navigate to an agent detail page
3. Wait 2 minutes
4. Count API requests

**Before**:
- Session activity: ~60 requests (30/min × 2)
- Stats: ~24 requests (12/min × 2)
- Logs: ~12 requests (6/min × 2)
- Git: ~4 requests (2/min × 2)
- **Total: ~100 requests in 2 minutes**

**After**:
- Session activity: ~24 requests (12/min × 2)
- Stats: ~12 requests (6/min × 2)
- Logs: ~8 requests (4/min × 2)
- Git: ~2 requests (1/min × 2)
- **Total: ~46 requests in 2 minutes**

### UX Verification

1. **Activity Status**: Start a task in terminal
   - Verify status updates within 5 seconds (not instant, but acceptable)

2. **Stats Sparklines**: Watch CPU/memory charts
   - Verify updates every 10 seconds
   - Verify chart still shows 5 minutes of history

3. **Logs Auto-Refresh**: Enable auto-refresh toggle
   - Verify logs update every 15 seconds
   - Manual refresh button still works instantly

4. **Git Status**: Make changes in agent workspace
   - Verify "X changes" badge updates within 60 seconds
   - Manual refresh button still works instantly

---

## Rollback Plan

If users complain about slow updates, revert individual composables:

```bash
# Revert specific file
git checkout HEAD -- src/frontend/src/composables/useSessionActivity.js
```

Or implement per-user configurable intervals (future enhancement).

---

## Future Enhancement: WebSocket Push

Replace polling entirely with WebSocket push notifications:

**Backend** (in agent activity handlers):
```python
# When agent state changes
await ws_manager.broadcast(json.dumps({
    "event": "agent_activity",
    "agent_name": agent_name,
    "data": {"status": "active", "tool": "Bash"}
}))
```

**Frontend** (in composable):
```javascript
// Replace setInterval with WebSocket listener
const startActivityTracking = () => {
    loadSessionActivity() // Initial load

    // Listen for WebSocket events instead of polling
    websocket.addEventListener('message', (event) => {
        const data = JSON.parse(event.data)
        if (data.event === 'agent_activity' && data.agent_name === agentRef.value.name) {
            sessionActivity.value = data.data
        }
    })
}
```

This eliminates polling entirely and provides real-time updates.

---

## Alternative: Conditional Polling

Only poll when the tab is visible:

```javascript
// Add to composables
const startSmartPolling = (loadFn, interval) => {
    let intervalId = null

    const startPolling = () => {
        loadFn()
        intervalId = setInterval(loadFn, interval)
    }

    const stopPolling = () => {
        if (intervalId) {
            clearInterval(intervalId)
            intervalId = null
        }
    }

    // Visibility-based polling
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stopPolling()
        } else {
            startPolling()
        }
    })

    // Start if visible
    if (!document.hidden) {
        startPolling()
    }

    return { stopPolling }
}
```

This stops polling when the browser tab is in the background.

---

## Request Reduction Summary

| State | Requests/min | Reduction |
|-------|--------------|-----------|
| Before (per agent page) | ~50 | - |
| After (per agent page) | ~20 | -60% |
| 5 users with 2 tabs each | 500 → 200 | -300 req/min |

---

## Completion Checklist

- [ ] Update `useSessionActivity.js` (2s → 5s)
- [ ] Update `useAgentStats.js` (5s → 10s, adjust MAX_POINTS)
- [ ] Update `useAgentLogs.js` (10s → 15s)
- [ ] Update `useGitSync.js` (30s → 60s)
- [ ] Test activity status update latency
- [ ] Test stats sparkline display
- [ ] Test logs auto-refresh
- [ ] Test git status badge
- [ ] Verify request count reduced (DevTools)
- [ ] Update changelog.md
