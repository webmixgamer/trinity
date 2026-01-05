# Issue: Vue Component Update Error in AgentDetail.vue

## Status
✅ **RESOLVED** (2025-12-26 17:00)

## Summary
After implementing GitHub Repository Initialization feature, the Git tab shows on all agent pages but triggers a Vue component update error when navigating to agent detail pages.

## Error Details

**Error Message:**
```
Uncaught (in promise) TypeError: Cannot read properties of null (reading 'emitsOptions')
```

**Stack Trace:**
```
shouldUpdateComponent @ chunk-JWJ3HAGN.js:6824
loadStats @ AgentDetail.vue:1590
startStatsPolling @ AgentDetail.vue:1606
(anonymous) @ AgentDetail.vue:1365
```

**Vue Warning:**
```
[Vue warn]: Unhandled error during execution of component update
  at <AgentDetail onVnodeUnmounted=fn<onVnodeUnmounted> ref=Ref< Proxy(Object) {__v_skip: true} > >
  at <RouterView>
  at <App>
```

## Root Cause Analysis

The error occurs when:
1. User navigates to agent detail page
2. Component mounts and starts stats polling (line 1365)
3. `startStatsPolling()` is called (line 1606)
4. `loadStats()` runs and sets `statsLoading.value = true` (line 1590)
5. This triggers a Vue reactive update
6. During the update, Vue tries to compare components using `shouldUpdateComponent`
7. Vue encounters a component with `null` emitsOptions

## Changes Made That May Have Caused This

### 1. Changed `hasGitSync` to Always Return True
**File:** `src/frontend/src/views/AgentDetail.vue:1221-1225`

**Before:**
```javascript
const hasGitSync = computed(() => {
  return agent.value?.template?.startsWith('github:')
})
```

**After:**
```javascript
const hasGitSync = computed(() => {
  // Always show Git tab - agents can initialize GitHub sync on demand
  return true
})
```

This change makes the Git tab button always visible, which might be causing Vue to render/update components that weren't previously in the DOM.

### 2. Added Component Guards
**File:** `src/frontend/src/views/AgentDetail.vue:870-881`

Added `v-if="agent"` guards to ExecutionsPanel and GitPanel to prevent rendering before agent data loads.

## Reproduction Steps

1. Clear browser cache completely
2. Navigate to http://localhost:3000
3. Login
4. Click on any agent to view details
5. Error appears in console immediately
6. Git tab shows but is empty/broken

## What Works
- Settings page - GitHub PAT configuration works perfectly
- Other tabs (Overview, Terminal, Files, Logs) work fine
- Agent list page works fine

## What Doesn't Work
- Git tab is empty
- Console shows component update error
- Error repeats every 5 seconds (stats polling interval)

## Attempted Fixes (All Failed)

1. ✗ Added `v-if="agent"` guard to GitPanel component
2. ✗ Added `v-if="agent"` guard to ExecutionsPanel component
3. ✗ Rebuilt frontend container
4. ✗ Cleared browser cache completely
5. ✗ Tested in incognito mode

## Potential Solutions to Try

### Option 1: Revert hasGitSync Change
Revert `hasGitSync` to check for GitHub templates, then add a separate check in GitPanel to show "Initialize" UI for non-git agents.

### Option 2: Lazy Load GitPanel
Use dynamic imports to lazy-load GitPanel only when Git tab is clicked:

```javascript
const GitPanel = defineAsyncComponent(() =>
  import('../components/GitPanel.vue')
)
```

### Option 3: Fix Component Registration
Check if all panel components (SchedulesPanel, ExecutionsPanel, etc.) are properly registered and have correct component options.

### Option 4: Disable Stats Polling During Initial Load
Delay stats polling until after the page is fully mounted:

```javascript
onMounted(async () => {
  await loadAgentData()
  // Wait a tick for all components to be ready
  await nextTick()
  if (hasGitSync.value) {
    startStatsPolling()
  }
})
```

### Option 5: Remove hasGitSync Dependency from Stats
The stats polling shouldn't depend on git sync status. Check line 1365 to see what's triggering startStatsPolling and if it's related to hasGitSync.

## Files Affected

- `src/frontend/src/views/AgentDetail.vue` - Main component with error
- `src/frontend/src/components/GitPanel.vue` - Git tab panel component
- `src/frontend/src/components/ExecutionsPanel.vue` - Executions panel
- `src/frontend/src/components/SchedulesPanel.vue` - Potentially affected

## Environment

- Docker container: `trinity-frontend`
- Framework: Vue 3 + Vite
- Node version: 20-alpine
- Browser: All browsers (tested in Chrome with incognito)

## Next Steps

1. Check line 1365 in AgentDetail.vue to see what's triggering startStatsPolling
2. Add console.log before line 1590 to see what's null
3. Check if GitPanel.vue is properly exported as default export
4. Verify all components have proper defineComponent or <script setup>
5. Try Option 2 (lazy loading) first as it's least invasive

## Impact

- **Severity:** High - Blocks GitHub initialization feature
- **Users Affected:** All users trying to use Git sync
- **Workaround:** None currently available
- **Timeline:** Needs immediate fix before feature can be tested

## Resolution

**Fixed**: 2025-12-26 17:00

**Actual Error**: `GitPanel.vue:191 Uncaught (in promise) TypeError: Cannot read properties of null (reading 'remote_url')`

**Real Root Cause**: GitPanel template at line 182 had `<div v-else>` showing the Git Status Display when git was enabled and agent was running. However, it didn't check if `gitStatus` object had complete data. When `loadGitStatus()` completed, it could set `gitStatus` to an incomplete object temporarily, and Vue would try to render line 191 which accessed `gitStatus.remote_url` before that property existed.

**Solution**: Changed line 182 to add a guard:

```vue
<!-- Before -->
<div v-else>
  <a :href="gitStatus.remote_url" ...>  <!-- Line 191 - crashes if remote_url is null -->

<!-- After -->
<div v-else-if="gitStatus?.remote_url && gitStatus?.branch">
  <a :href="gitStatus.remote_url" ...>  <!-- Only renders when data is complete -->
```

**Why Debugging Was Difficult**:
1. Initial error message was misleading - talked about `emitsOptions` instead of the actual property access
2. Error only occurred on specific tabs (Git, Files, Folders) making it seem like a tab-switching issue
3. Stats polling was a red herring - disabling it didn't fix the issue
4. The error occurred immediately on tab load, not during reactive updates

**Why This Works**: The `v-else-if` guard ensures the Git Status Display section only renders when `gitStatus` has both `remote_url` and `branch` properties, preventing null property access during template rendering.

## Related

- Feature: GitHub Repository Initialization
- PR/Commit: Changes made on 2025-12-26
- Documentation: `docs/memory/feature-flows/github-repo-initialization.md`
- Fix: `src/frontend/src/views/AgentDetail.vue:1370`
