# Plan: Consolidate Ops / Events / Cost Alerts into Operating Room

## Goal

Merge three separate sections (Operating Room, Events, Cost Alerts) into a single unified Operating Room view with tabs. Remove two nav items and two bell icons. Users get one place for all agent-to-operator communication.

**Before:** Ops | Health | [Events bell] | [Alerts bell] (4 concepts, confusing)
**After:** Ops | Health (2 concepts, clear)

---

## Design

### New Operating Room Tab Structure

```
Operating Room
┌─────────────────┬────────────────┬──────────────────┬─────────────┐
│ Needs Response   │ Notifications  │ Cost Alerts      │ Resolved    │
│ (3)             │ (12)           │ (2)              │             │
└─────────────────┴────────────────┴──────────────────┴─────────────┘
```

- **Needs Response** (was: Open tab) - Queue items needing operator action (approvals, questions, alerts). Uses existing QueueCard component.
- **Notifications** (was: Events page) - Read-only agent notifications (info, status, completion, question, alert). Uses adapted Events content.
- **Cost Alerts** (was: Alerts page) - Cost threshold alerts. Uses adapted Alerts content.
- **Resolved** (was: Resolved tab) - Completed operator queue items. Uses existing ResolvedCard component.

### Unified Badge in NavBar

Single "Ops" nav item with combined badge count:
- Badge number = operator queue pending + notification pending + active cost alerts
- Badge turns red if any critical/urgent items exist across any source

### What Stays Unchanged

- **Health** (`/monitoring`) - remains separate, admin-only
- **All backend APIs** - no changes to `/api/operator-queue`, `/api/notifications`, `/api/alerts`
- **All stores** - keep `operatorQueue`, `notifications`, `alerts` as separate stores (they each manage their own data well)
- **QueueCard.vue** and **ResolvedCard.vue** - reused as-is

---

## Implementation Steps

### Step 1: Update OperatingRoom.vue - Add Tab Structure

**File:** `src/frontend/src/views/OperatingRoom.vue`

Replace the current 2-tab layout (Open / Resolved) with 4 tabs:

1. **Needs Response** - current Open tab content (QueueCard feed), badge shows `operatorQueueStore.pendingCount`
2. **Notifications** - embed the Events.vue content (notification list with filters), badge shows `notificationsStore.pendingCount`
3. **Cost Alerts** - embed the Alerts.vue content (alert list with filters), badge shows `alertsStore.activeCount`
4. **Resolved** - current Resolved tab content (ResolvedCard feed), no badge

Import and use all three stores (`operatorQueue`, `notifications`, `alerts`). Start/stop polling for all three on mount/unmount.

The filter UI for Notifications and Cost Alerts tabs should be kept but moved inline within their respective tab panels (no separate page chrome/headers needed).

### Step 2: Extract Reusable Content from Events.vue

**File:** `src/frontend/src/components/operator/NotificationsPanel.vue` (new)

Extract the notification list + filters + bulk actions from Events.vue into a standalone panel component that can be embedded in the Operating Room. This is essentially Events.vue without the NavBar and page wrapper.

Content to move:
- Filter bar (agent, type, priority, status, show dismissed)
- Stats row (pending, acknowledged, total, agents)
- Notification card list with expand/collapse
- Bulk actions (acknowledge/dismiss selected)
- Empty state

### Step 3: Extract Reusable Content from Alerts.vue

**File:** `src/frontend/src/components/operator/CostAlertsPanel.vue` (new)

Extract the alert list + filter from Alerts.vue into a standalone panel component.

Content to move:
- Status filter (active/dismissed/all)
- Stats row (active count, total)
- Alert card list with dismiss action
- Empty state

### Step 4: Update NavBar.vue - Remove Bells, Update Badge

**File:** `src/frontend/src/components/NavBar.vue`

Changes:
- **Remove** the Events bell icon + badge (lines ~75-90)
- **Remove** the Alerts bell icon + badge (lines ~93-107)
- **Update** Ops badge to show combined count: `operatorQueueStore.pendingCount + notificationsStore.pendingCount + alertsStore.activeCount`
- **Update** badge color logic: red if any critical queue items OR any urgent notifications OR any active cost alerts
- Keep polling for all three stores (already started in NavBar)

### Step 5: Update Router - Redirect Old Routes

**File:** `src/frontend/src/router/index.js`

- Keep `/operating-room` route as-is
- Change `/events` to redirect to `/operating-room?tab=notifications`
- Change `/alerts` to redirect to `/operating-room?tab=cost-alerts`
- Add query param support to OperatingRoom.vue so `?tab=notifications` opens the right tab

This preserves any existing bookmarks or links.

### Step 6: Delete Standalone Pages

**Files to delete:**
- `src/frontend/src/views/Events.vue` - replaced by NotificationsPanel embedded in Operating Room
- `src/frontend/src/views/Alerts.vue` - replaced by CostAlertsPanel embedded in Operating Room

### Step 7: Update Page Header / Subtitle

**File:** `src/frontend/src/views/OperatingRoom.vue`

Update the subtitle from the current "Your agents need your input on X items" to show a combined summary, e.g.:
- "X pending responses, Y notifications, Z cost alerts" (when there are items)
- "All clear - your agents are working independently" (when empty across all tabs)

---

## Files Changed Summary

| File | Change |
|------|--------|
| `src/frontend/src/views/OperatingRoom.vue` | Major: 4-tab layout, import 3 stores, query param support |
| `src/frontend/src/components/operator/NotificationsPanel.vue` | **New**: Extracted from Events.vue |
| `src/frontend/src/components/operator/CostAlertsPanel.vue` | **New**: Extracted from Alerts.vue |
| `src/frontend/src/components/NavBar.vue` | Remove 2 bell icons, update Ops badge |
| `src/frontend/src/router/index.js` | Redirect `/events` and `/alerts` to `/operating-room` |
| `src/frontend/src/views/Events.vue` | **Delete** |
| `src/frontend/src/views/Alerts.vue` | **Delete** |

## Files NOT Changed

| File | Reason |
|------|--------|
| All backend files | No API changes needed |
| `operatorQueue.js` store | Keeps working as-is |
| `notifications.js` store | Keeps working as-is |
| `alerts.js` store | Keeps working as-is |
| `QueueCard.vue` | Reused as-is in Needs Response tab |
| `ResolvedCard.vue` | Reused as-is in Resolved tab |
| `Monitoring.vue` | Health stays separate |

---

## Risk Assessment

- **Low risk**: No backend changes, no data model changes, no store logic changes
- **Routing**: Old URLs redirect cleanly via router
- **Stores**: All three stores already initialize polling in NavBar, so Operating Room just needs to call their fetch methods on tab switch
- **Mobile**: Tab bar with 4 tabs may need horizontal scroll on small screens - use compact labels ("Queue", "Notifs", "Costs", "Done")
