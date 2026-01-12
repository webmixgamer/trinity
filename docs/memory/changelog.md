### 2026-01-12 20:10:00
⚡ **Performance: Docker Stats Optimization - Fast Agent List**

**Problem**: The `/api/agents` endpoint was slow (~2-3s with multiple agents) due to Docker API calls for container metadata.

**Solution**: Added `list_all_agents_fast()` function that extracts agent info ONLY from container labels, avoiding slow operations like:
- `container.attrs` (full Docker inspect API call)
- `container.image` (image metadata lookup)
- `container.stats()` (CPU sampling - 2+ seconds per container)

**Result**: Response time reduced from ~2-3s to **<50ms** for agent list endpoints.

**Files Modified**:
- `src/backend/services/docker_service.py:101-159` - Added `list_all_agents_fast()` function
- `src/backend/services/agent_service/helpers.py:14-17,92` - Use fast version in `get_accessible_agents()`
- `src/backend/main.py:26,177` - Use fast version at startup
- `src/backend/routers/ops.py:22,54,132,239,343,558,620` - Use fast version in ops endpoints
- `src/backend/routers/telemetry.py:16,126` - Use fast version in telemetry

**Note**: Per-agent stats (CPU, memory) still available via `/api/agents/{name}/stats` (~1s due to Docker sampling).

---

### 2026-01-12 18:15:00
🐛 **Fix: Credential Injection Bug - Passing Dict Instead of Username**

**Problem**: Credentials assigned to agents were not being injected on restart despite the previous fix. The `.env` file was not being created.

**Root Cause**: In `inject_assigned_credentials()`, the code was passing the entire `owner` dict from `db.get_agent_owner()` to `credential_manager.get_assigned_credential_values()` and `get_assigned_file_credentials()`. However, these methods expect `user_id` as a string (e.g., "admin"), not a dict. The ownership verification in `get_credential()` was comparing strings to dicts, which always failed silently, resulting in empty credentials being returned.

```python
# BROKEN - owner is a dict like {"owner_username": "admin", ...}
credentials = credential_manager.get_assigned_credential_values(agent_name, owner)

# FIXED - extract the username string
owner_username = owner.get("owner_username")
credentials = credential_manager.get_assigned_credential_values(agent_name, owner_username)
```

**Solution**:
1. Extract `owner_username` from the dict before passing to credential methods
2. Add validation in case `owner_username` is missing
3. Add logging to show owner username in credential injection messages
4. Fix import of `CredentialManager` (was trying to import non-existent `credential_manager` singleton)
5. Update `/api/agents/{name}/start` endpoint to include `credentials_injection` and `credentials_result` in response

**Files Modified**:
- `src/backend/services/agent_service/lifecycle.py:69-92` - Fix owner_username extraction and import
- `src/backend/routers/agents.py:315-335` - Include credential injection status in start response

**Verification**:
```bash
# Stop agent and start via API
curl -X POST /api/agents/demo-fleet-ruby/start
# Response includes: "credentials_injection": "success", "credentials_result": {"status": "success", "credential_count": 2}

# Check agent .env file
docker exec agent-demo-fleet-ruby cat /home/developer/.env
# Shows: API_KEY="value1"
```

---

### 2026-01-12 18:00:00
📚 **Docs: Expanded Custom Metrics Documentation**

Significantly expanded the Custom Metrics section in `TRINITY_COMPATIBLE_AGENT_GUIDE.md`:

**Added**:
- File locations: where agent server looks for `template.yaml` and `metrics.json`
- Complete template.yaml examples for all 6 metric types (counter, gauge, percentage, status, duration, bytes)
- `percentage` type with `warning_threshold` and `critical_threshold` fields
- `status` type with `values` array showing value/color/label structure
- Available colors for status badges: green, red, yellow, gray, blue, orange
- `metrics.json` format with `last_updated` optional field
- Complete working example showing template.yaml → metrics.json → CLAUDE.md integration
- Note that agent must be running for metrics to be visible
- Note about auto-refresh every 30 seconds

**Updated**:
- Removed unused `icon` field from schema (not implemented in frontend)
- Added cross-reference to detailed Custom Metrics section from schema

**Files Modified**:
- `docs/TRINITY_COMPATIBLE_AGENT_GUIDE.md` - Expanded Custom Metrics section

---

### 2026-01-12 17:30:00
🐛 **Fix: Credential Injection on Agent Restart**

**Problem**: Credentials assigned via the Credentials tab were NOT being injected when an agent was restarted. Credentials were only injected at agent creation time.

**Root Cause**:
1. `start_agent_internal()` only started the container and injected the Trinity meta-prompt - it did NOT fetch or inject assigned credentials
2. The "Apply to Agent" button was only visible when `hasChanges` was true, which reset on page refresh

**Solution**:
1. Added `inject_assigned_credentials()` function to `lifecycle.py` that:
   - Gets the agent owner from the database
   - Fetches assigned credentials from Redis via credential_manager
   - Pushes credentials to the running agent via internal API
   - Includes retry logic for agent startup delays

2. Modified `start_agent_internal()` to call `inject_assigned_credentials()` after starting the container

3. Fixed the "Apply to Agent" button visibility in `CredentialsPanel.vue`:
   - Changed from `v-if="hasChanges && agentStatus === 'running'"`
   - To `v-if="agentStatus === 'running' && assignedCredentials.length > 0"`
   - Added "Start agent to apply" hint when agent is stopped

**Files Modified**:
- `src/backend/services/agent_service/lifecycle.py:54-121` - Added `inject_assigned_credentials()` function
- `src/backend/services/agent_service/lifecycle.py:165-167` - Call credential injection in `start_agent_internal()`
- `src/backend/services/agent_service/__init__.py` - Export new function
- `src/frontend/src/components/CredentialsPanel.vue:27-44` - Fix button visibility logic

**Verification**:
1. Create credentials in the Credentials page
2. Assign them to an agent via Agent Detail → Credentials tab
3. Stop and restart the agent
4. Credentials are now automatically injected on start

---

### 2026-01-12 16:00:00
📦 **Feature: Package Persistence & Version Tracking**

**Problem**: When agent containers are recreated (due to base image updates or config changes), system packages installed via `apt-get` or `npm install -g` are lost. Users had to manually reinstall packages each time.

**Solution**: Added `~/.trinity/setup.sh` convention - a persistent setup script that runs on container start to reinstall packages.

**Package Persistence**:
1. `startup.sh` now runs `~/.trinity/setup.sh` if it exists
2. Agents are instructed (via Trinity CLAUDE.md injection) to append install commands to this script
3. Templates can ship with pre-defined `setup.sh` for known dependencies
4. Documented in `TRINITY_COMPATIBLE_AGENT_GUIDE.md`

**Version Tracking**:
1. Base image Dockerfile now includes `trinity.base-image-version` label
2. Container labels store version at creation time
3. `AgentStatus` model includes `base_image_version` field
4. Frontend can compare agent version vs current platform version

**Files Modified**:
- `docker/base-image/startup.sh` - Run setup.sh on start
- `docker/base-image/Dockerfile` - Add VERSION arg and label
- `docker/base-image/agent_server/routers/trinity.py` - Inject package persistence instructions
- `src/backend/models.py` - Add base_image_version to AgentStatus
- `src/backend/services/docker_service.py` - Extract version from container/image labels
- `src/backend/services/agent_service/crud.py` - Add version label, get_platform_version helper
- `src/backend/main.py` - Fix version endpoint path resolution
- `docker-compose.yml` - Mount VERSION file into backend container
- `docs/TRINITY_COMPATIBLE_AGENT_GUIDE.md` - Added Package Persistence section

**Usage**:
```bash
# In agent terminal - install and persist
sudo apt-get install -y ffmpeg
mkdir -p ~/.trinity
echo "sudo apt-get install -y ffmpeg" >> ~/.trinity/setup.sh
```

---

### 2026-01-12 14:30:00
🔐 **Feature: Full Capabilities Mode for Container Software Installation**

**Problem**: Claude Code agents in containers couldn't install software via `apt-get` or `sudo` commands because security capabilities were too restricted (`cap_drop=['ALL']`).

**Solution**: Added configurable `full_capabilities` option that enables Docker default capabilities when True, allowing `apt-get`, `sudo`, and other system commands to work while maintaining container isolation.

**Changes**:
1. Added `full_capabilities: Optional[bool] = False` to AgentConfig model
2. Container creation respects this setting:
   - `full_capabilities=False` (default): Restricted mode with `cap_drop=['ALL']`, `apparmor:docker-default`, `noexec` on `/tmp`
   - `full_capabilities=True`: Docker defaults (no capability restrictions, no AppArmor, executable `/tmp`)
3. Setting persisted in database (`agent_ownership.full_capabilities` column)
4. Setting preserved in container labels for recreation
5. Template support via `full_capabilities: true` or `security: {full_capabilities: true}` in template.yaml

**Files Modified**:
- `src/backend/models.py:31` - Added full_capabilities field to AgentConfig
- `src/backend/services/agent_service/crud.py:158-164,435-443,467-473` - Container creation, template parsing, DB storage
- `src/backend/services/agent_service/lifecycle.py:140-141,222-228` - Container recreation preserves setting
- `src/backend/database.py:248-256,308-311,860-864` - Migration and wrapper methods
- `src/backend/db/agents.py:416-461` - get/set_full_capabilities methods

**Usage** (template.yaml):
```yaml
name: my-agent
full_capabilities: true  # Enables apt-get, sudo, etc.
resources:
  cpu: "2"
  memory: "4g"
```

**Security Note**: Only enable for agents that genuinely need system-level access. Default (restricted) mode is recommended for most use cases.

---

### 2026-01-12 12:55:00
🔧 **Fix: OpenTelemetry Prometheus Export - Delta to Cumulative Conversion**

**Problem**: Claude Code SDK exports metrics with delta temporality, but the Prometheus exporter requires cumulative temporality. Metrics were being received by the collector but not exposed on the Prometheus endpoint.

**Root Cause**: The base OTel Collector image (`otel/opentelemetry-collector:0.91.0`) doesn't include the `deltatocumulative` processor needed to convert delta metrics.

**Solution**:
1. Switched to contrib image: `otel/opentelemetry-collector-contrib:0.120.0`
2. Updated config mount path to `/etc/otelcol-contrib/config.yaml` (contrib uses different path)
3. Added `deltatocumulative` processor to the metrics pipeline
4. Removed `const_labels` from Prometheus exporter (conflicts with `resource_to_telemetry_conversion`)

**Files Modified**:
- `docker-compose.yml:167-176` - Changed image and config mount path
- `config/otel-collector.yaml` - Added deltatocumulative processor, fixed exporter config
- `docs/memory/feature-flows/opentelemetry-integration.md` - Updated with critical configuration notes

**Verification**: Metrics now appear correctly in Prometheus endpoint at `http://localhost:8889/metrics`:
- `trinity_claude_code_cost_usage_USD_total` - Cost per model
- `trinity_claude_code_token_usage_tokens_total` - Tokens by type (input, output, cacheRead, cacheCreation)

---

### 2026-01-12 11:30:00
🛡️ **Feature: max_turns Parameter for Runaway Prevention**

**Problem**: Headless task execution could run indefinitely if an agent got stuck in an infinite loop or continued executing far beyond expected scope.

**Solution**: Added optional `max_turns` parameter to the `/api/task` endpoint. When specified, it adds `--max-turns N` to the Claude Code or Gemini CLI command, limiting the number of agentic turns before the CLI exits.

**Files Modified**:
- `docker/base-image/agent_server/models.py:221` - Added `max_turns: Optional[int] = None` to ParallelTaskRequest
- `docker/base-image/agent_server/services/runtime_adapter.py:106` - Added max_turns to execute_headless interface
- `docker/base-image/agent_server/services/claude_code.py:604-606` - Pass --max-turns to Claude Code
- `docker/base-image/agent_server/services/gemini_runtime.py:542-544` - Pass --max-turns to Gemini CLI
- `docker/base-image/agent_server/routers/chat.py:120` - Pass max_turns to runtime
- `src/backend/models.py:110` - Added max_turns to backend ParallelTaskRequest

**Usage**:
```json
POST /api/task
{
  "message": "Analyze this codebase",
  "max_turns": 50,
  "timeout_seconds": 900
}
```

**Documentation**: Updated `docs/memory/feature-flows/parallel-headless-execution.md`

---

### 2026-01-12 10:15:00
🔧 **UI: Git Buttons Renamed and Enhanced**

**Changes**:
1. **Renamed "Sync" to "Push"**: Consistent Pull/Push terminology
2. **Pull button now shows commits behind**: Displays "Pull (N)" when remote has N commits to fetch
3. **Dynamic button colors**:
   - Pull: Blue when behind, gray when up to date
   - Push: Orange when local changes, gray when clean

**Files Modified**:
- `src/frontend/src/components/AgentHeader.vue` - Button labels, colors, and props
- `src/frontend/src/composables/useGitSync.js` - Added `gitBehind` computed property
- `src/frontend/src/views/AgentDetail.vue` - Pass `gitBehind` prop, handle `git-push` event
- `docs/memory/feature-flows/github-sync.md` - Updated documentation

---

### 2026-01-11 21:44:00
🐛 **Fix: Autonomy Toggle Not Syncing Schedules to APScheduler**

**Problem**: When autonomy was toggled via the UI or API, schedules were enabled/disabled in the database but APScheduler was never updated. This caused schedules to stop running after autonomy was re-enabled until the backend was restarted.

**Root Cause**: `autonomy.py` was calling `db.set_schedule_enabled()` directly, which only updates the database. It should use `scheduler_service.enable_schedule()` and `scheduler_service.disable_schedule()` which update both the database AND APScheduler.

**Fix**: Updated `services/agent_service/autonomy.py` to use scheduler_service methods:
```python
# Before (broken):
db.set_schedule_enabled(schedule_id, enabled)

# After (fixed):
if enabled:
    scheduler_service.enable_schedule(schedule_id)
else:
    scheduler_service.disable_schedule(schedule_id)
```

**Files Modified**:
- `src/backend/services/agent_service/autonomy.py` - Import scheduler_service, use enable/disable methods

**Testing**:
1. Disabled autonomy → Jobs removed from APScheduler
2. Re-enabled autonomy → Jobs re-added to APScheduler
3. Schedule executed on next cron trigger ✅

---

### 2026-01-11 21:30:00
📚 **Docs: Archive Deprecated Feature Flows**

Cleaned up feature-flows index by archiving 4 deprecated/removed feature flows:

| Flow | Status | Reason |
|------|--------|--------|
| auth0-authentication.md | REMOVED | Auth0 deleted (2026-01-01), replaced by email auth |
| agent-chat.md | DEPRECATED | UI replaced by Web Terminal (2025-12-25) |
| vector-memory.md | REMOVED | Platform-injected memory removed (2025-12-24) |
| agent-network-replay-mode.md | SUPERSEDED | Replaced by Dashboard Timeline View (2026-01-04) |

**Changes**:
- Created `docs/memory/feature-flows/archive/` directory
- Moved 4 obsolete flow documents to archive
- Updated feature-flows.md index: removed struck-through entries, added "Archived Flows" section

---

### 2026-01-11 13:30:00
🐛 **Fix: Frontend Timeline Execution ID Extraction**

**Problem**: Dashboard Timeline couldn't navigate to Execution Detail pages because the frontend was looking for execution ID in the wrong place.

**Root Cause**: `network.js` was only checking `details.execution_id` and `details.related_execution_id` (inside the details JSON), but the backend now stores `related_execution_id` as a **top-level field** on the activity record.

**Fix**: Updated `network.js` line 176 to prioritize top-level field:
```javascript
// Before (broken):
execution_id: details.execution_id || details.related_execution_id || null

// After (fixed):
execution_id: activity.related_execution_id || details.execution_id || details.related_execution_id || null
```

**Files Modified**:
- `src/frontend/src/stores/network.js` - Extract execution_id from activity.related_execution_id

**Impact**: Timeline clicks now correctly navigate to Execution Detail page with proper database ID.

---

### 2026-01-11 12:15:00
🔧 **Refactor: Consistent Execution ID Tracking Across All Entry Points**

**Problem**: Execution tracking had multiple inconsistencies:
1. Activities only stored execution ID in `details` dict, not in `related_execution_id` field
2. Tool call activities had no link to parent execution
3. Chat response returned queue ID (transient) instead of database ID (permanent)
4. Manual trigger executions had no activity tracking
5. Schedule activities were created BEFORE execution record (no ID to link)

**Solution**: Comprehensive fix to ensure all execution types use consistent ID tracking:

**chat.py Changes**:
1. Collaboration activity: Added `related_execution_id=task_execution_id` (line 201)
2. Chat start activity: Added `related_execution_id=task_execution_id` (line 224)
3. Tool call activities: Added `related_execution_id=task_execution_id` (line 302)
4. Chat response: Now includes both `id` (queue) and `task_execution_id` (database) (line 357-361)
5. Parallel task activity: Added `related_execution_id=execution_id` (line 462)

**scheduler_service.py Changes**:
1. Reordered operations: Create execution record BEFORE activity tracking
2. Schedule activity: Added `related_execution_id=execution.id` (line 222)
3. Manual trigger: Added full activity tracking with `related_execution_id` (lines 431-446)
4. Manual trigger: Added activity completion for success/failure paths

**ID System Clarification**:
| ID Type | Format | Storage | Purpose |
|---------|--------|---------|---------|
| Queue ID | UUID | Redis (10m TTL) | Internal queue management |
| Database ID | token_urlsafe(16) | SQLite (permanent) | API access, UI navigation |

**Files Modified**:
- `src/backend/routers/chat.py` - 5 activity tracking calls + response format
- `src/backend/services/scheduler_service.py` - Reordered + added activity tracking

**Impact**: Timeline clicks now correctly navigate to Execution Detail page. All execution types (chat, parallel task, scheduled, manual trigger) now have consistent activity linkage.

---

### 2026-01-11 10:31:00
🐛 **Fix: Agent Authorization Dependencies Return 404 for Non-Existent Agents**

**Problem**: API endpoints using `AuthorizedAgent`, `AuthorizedAgentByName`, `OwnedAgent`, and `OwnedAgentByName` dependencies returned incorrect responses for non-existent agents:
- Admin users: 200 OK with empty data (admin bypass skipped existence check)
- Non-admin users: 403 Forbidden (permission check failed before existence check)

**Expected**: All users should receive 404 Not Found for non-existent agents.

**Fix**: Updated all four authorization dependency functions to check agent existence before checking permissions:
1. `get_authorized_agent()` - Lines 183-188
2. `get_authorized_agent_by_name()` - Lines 235-240
3. `get_owned_agent()` - Lines 213-218
4. `get_owned_agent_by_name()` - Lines 273-278

Each function now:
1. First checks if agent exists via `db.get_agent_owner()`
2. Returns 404 if agent doesn't exist
3. Then checks user permissions
4. Returns 403 if user lacks access

**Files Modified**:
- `src/backend/dependencies.py` - All 4 agent authorization dependencies

**Test**: `test_get_executions_nonexistent_agent_returns_404` now passes

---

### 2026-01-11 10:18:00
🐛 **Fix: Timeline Execution Links Not Finding Executions**

**Problem**: Clicking on execution bars in the Dashboard Timeline opened the Execution Detail page, but it showed "Execution not found" even though executions existed in the database.

**Root Cause**: ID mismatch between two different execution tracking systems:
- **Queue execution ID** (UUID format): `4df12ce0-742b-4671-b9ae-ad024ba7c595`
- **Database execution ID** (base64 format): `lxTrun4spCbAtlMUHh748w`

Activities were storing `execution.id` (queue UUID) instead of `task_execution_id` (database ID).

**Fix**: Changed all activity tracking calls to use `task_execution_id` instead of `execution.id`:
- Line 205: collaboration_activity details
- Line 227: chat_start activity details
- Line 320: chat_activity completion details
- Line 333: collaboration_activity completion details

**Files Modified**:
- `src/backend/routers/chat.py` - 4 locations fixed

**Note**: Existing activities have wrong execution_id. New executions will work correctly.

---

### 2026-01-11 09:15:00
✨ **UX: Timeline Execution Click Opens New Tab**

Changed the Dashboard Timeline behavior when clicking on execution bars:
- **Before**: Same-tab navigation to Execution Detail page
- **After**: Opens Execution Detail page in a new browser tab

This allows users to explore execution details without losing their place on the Dashboard.

**Files Modified**:
- `src/frontend/src/components/ReplayTimeline.vue` - Changed `router.push()` to `window.open(route.href, '_blank')`

**Docs Updated**:
- `docs/memory/feature-flows/dashboard-timeline-view.md`
- `docs/memory/feature-flows/execution-detail-page.md`

---

### 2026-01-10 13:30:00
🐛 **Fix: Execution Transcripts Not Showing for Chat-Based Executions**

**Problem**: Execution transcripts were not displaying for some executions (especially MCP and chat-based ones). The frontend's `parseExecutionLog()` expects raw Claude Code stream-json format, but `/api/chat` was returning a simplified `ExecutionLogEntry` format.

**Root Cause**:
- Agent `/api/task` returns raw Claude Code format → ✅ Works
- Agent `/api/chat` returns simplified `ExecutionLogEntry[]` format → ❌ Broken

**Solution**: Unified both endpoints to return raw Claude Code stream-json format:

1. **Agent Server Changes** (`docker/base-image/agent_server/`):
   - `services/claude_code.py`: Updated `execute_claude_code()` to capture raw_messages
   - `services/gemini_runtime.py`: Updated `execute()` to capture raw_messages
   - `services/runtime_adapter.py`: Updated abstract interface signature
   - `routers/chat.py`: Now returns `raw_messages` as `execution_log`

2. **Backend Changes** (`src/backend/routers/chat.py`):
   - Extracts both `execution_log` (raw) and `execution_log_simplified`
   - Uses simplified format for activity tracking
   - Stores raw format in database for UI display

**Files Modified**:
- `docker/base-image/agent_server/services/claude_code.py`
- `docker/base-image/agent_server/services/gemini_runtime.py`
- `docker/base-image/agent_server/services/runtime_adapter.py`
- `docker/base-image/agent_server/routers/chat.py`
- `src/backend/routers/chat.py`

**Rebuild Required**: Base image (`./scripts/deploy/build-base-image.sh`) + backend

---

### 2026-01-10 12:00:00
✨ **Feature: Execution Detail Page**

**Goal**: Provide a dedicated page for viewing comprehensive execution details instead of just a modal.

**Changes**:

1. **New Page** (`ExecutionDetail.vue`):
   - Route: `/agents/:name/executions/:executionId`
   - Header with back button, agent name breadcrumb, status badge
   - Metadata cards: Duration, Cost, Context, Trigger
   - Timestamps row: Started, Completed, Execution ID
   - Task Input panel with full message
   - Error panel (conditional, for failed executions)
   - Response Summary panel
   - Full Execution Transcript (reuses parseExecutionLog logic)

2. **Navigation from TasksPanel** (`TasksPanel.vue:207-217`):
   - New external link icon before the log modal icon
   - Links to ExecutionDetail page for the execution
   - Only shown for server-persisted tasks (not local-)

3. **Navigation from Timeline** (`ReplayTimeline.vue:767-785`):
   - Updated `navigateToExecution()` to open ExecutionDetail page
   - Previously navigated to Tasks tab with highlight
   - Now opens dedicated page for better UX

4. **Router** (`router/index.js:41-46`):
   - Added route: `/agents/:name/executions/:executionId`
   - Named route: `ExecutionDetail`
   - Requires authentication

**Files Modified**:
- `src/frontend/src/views/ExecutionDetail.vue` - New page component
- `src/frontend/src/router/index.js` - New route
- `src/frontend/src/components/TasksPanel.vue` - External link icon
- `src/frontend/src/components/ReplayTimeline.vue` - Updated navigation
- `docs/memory/feature-flows/execution-detail-page.md` - New feature flow

---

### 2026-01-10 11:15:00
✨ **Feature: Timeline Click-to-Navigate to Execution Details**

**Goal**: Allow users to click on execution bars in the Dashboard Timeline to view full execution details in the Tasks tab.

**Changes**:

1. **Execution ID Tracking** (`network.js`):
   - Now extracts `execution_id` from activity details
   - Available via `details.execution_id` or `details.related_execution_id`
   - Passed through to Timeline events for navigation

2. **Click Handler** (`ReplayTimeline.vue`):
   - Added `@click="navigateToExecution(activity)"` on execution bars
   - Navigates to `/agents/{name}?tab=tasks&execution={id}`
   - Tooltip updated: "(Click to view details)"
   - Visual feedback: hover adds white stroke outline

3. **Tab Query Param** (`AgentDetail.vue`):
   - Now reads `tab` query param on mount
   - Auto-selects requested tab (tasks, terminal, etc.)
   - Passes `highlightExecutionId` prop to TasksPanel

4. **Execution Highlighting** (`TasksPanel.vue`):
   - New prop: `highlightExecutionId`
   - Highlighted execution has indigo ring border
   - Auto-expands the highlighted execution
   - Scrolls to highlighted execution on load

**Files Modified**:
- `src/frontend/src/stores/network.js` - Extract execution_id from details
- `src/frontend/src/components/ReplayTimeline.vue` - Click handler, navigation
- `src/frontend/src/views/AgentDetail.vue` - Tab query param, pass highlight prop
- `src/frontend/src/components/TasksPanel.vue` - Highlight styling, auto-scroll
- `docs/memory/feature-flows/dashboard-timeline-view.md` - Updated documentation

---

### 2026-01-10 10:30:00
✨ **Feature: Timeline All Executions Display**

**Goal**: Show ALL executions on Dashboard Timeline (scheduled, manual, collaboration) - not just agent-to-agent collaborations.

**Changes**:

1. **Expanded Activity Query** (`network.js`):
   - Now fetches: `agent_collaboration,schedule_start,schedule_end,chat_start,chat_end`
   - Filters out regular user chat sessions (keeps automated executions only)
   - Parses `activity_type`, `triggered_by`, `schedule_name` for color coding

2. **Activity Type Color Coding** (`ReplayTimeline.vue`):
   | Type | Color | Use Case |
   |------|-------|----------|
   | Cyan `#06b6d4` | Agent-to-agent calls | `agent_collaboration` |
   | Purple `#8b5cf6` | Scheduled tasks | `schedule_start/end` |
   | Green `#22c55e` | Manual/automated tasks | `chat_start/end` (non-user) |
   | Red `#ef4444` | Errors | Any failed execution |
   | Amber `#f59e0b` | In progress | Currently running |

3. **Legend Display**:
   - Color legend added to Timeline header
   - Shows: Collaboration (cyan), Scheduled (purple), Task (green)
   - Hidden on small screens for space

4. **Enhanced Tooltips**:
   - Now shows execution type prefix: "Agent Call", "Scheduled: {name}", "Manual Task", "Task"
   - Status indicator: "(Error)", "(In Progress)"
   - Duration with estimated marker when needed

5. **Arrows Only for Collaborations**:
   - Non-collaboration events render bars only (no target_agent)
   - Communication arrows only shown for `agent_collaboration` events

**Files Modified**:
- `src/frontend/src/stores/network.js` - Expanded query, filter logic, new fields
- `src/frontend/src/components/ReplayTimeline.vue` - Color coding, legend, tooltips
- `docs/memory/feature-flows/dashboard-timeline-view.md` - Updated documentation
- `docs/requirements/TIMELINE_ALL_EXECUTIONS.md` - Requirements (completed)

**Backend**: No changes needed - API already supports all activity types.

---

### 2026-01-10 09:45:00
🔧 **Fix: Dashboard Timeline View Improvements**

**Goal**: Address user feedback to improve Timeline view usability and feature parity with Graph view.

**Changes**:

1. **Graph Hidden in Timeline Mode**:
   - Graph canvas now completely hidden when Timeline is active
   - Views are mutually exclusive - no overlay issues

2. **Default Zoom to Last 2 Hours**:
   - On page load, zoom defaults to `timeRangeHours / 2`
   - For 24h range, zoom is 12x (shows ~2 hours of activity)
   - Auto-scrolls to "Now" position on mount

3. **Rich Agent Tiles** (expanded from 220px to 280px):
   - Now matches Graph tile layout exactly:
   - Row 1: Agent name, runtime badge (Claude/Gemini), system badge, status dot
   - Row 2: Activity state (Active/Idle/Offline) + Autonomy toggle (AUTO/Manual)
   - Row 3: GitHub repo or "Local agent"
   - Row 4: Context progress bar with percentage
   - Row 5: Execution stats (tasks, success rate, cost, last execution)
   - Row 6: Resource info (memory, CPU cores)
   - Row 7: View Details button (or System Dashboard link for system agent)

4. **Autonomy Toggle**:
   - Added `@toggle-autonomy` event emission
   - Wired to Dashboard's `handleToggleAutonomy()` handler
   - Toggle works directly from Timeline view

5. **New Props**:
   - `nodes` - Full node data for tile information
   - `timeRangeHours` - For default zoom calculation

**Files Modified**:
- `src/frontend/src/views/Dashboard.vue` - Hide Graph in Timeline, pass nodes prop
- `src/frontend/src/components/ReplayTimeline.vue` - Rich tiles, default zoom, autonomy toggle
- `docs/memory/feature-flows/dashboard-timeline-view.md` - Updated documentation

---

### 2026-01-10 09:22:00
✨ **Feature: Dashboard Timeline View**

**Goal**: Transform Dashboard to offer two views - Graph (node-based) and Timeline (waterfall activity view) with live event streaming and rich agent labels.

**Changes**:

1. **Renamed Mode Toggle**: "Live/Replay" → "Graph/Timeline"
   - Graph view shows the VueFlow node visualization (unchanged)
   - Timeline view shows waterfall activity timeline

2. **Live Event Streaming in Timeline**:
   - WebSocket stays connected in Timeline view (previously disconnected)
   - New events appear at right edge in real-time
   - "Now" marker updates continuously every second
   - Auto-scroll to latest events (disables when user scrolls back)
   - "Jump to Now" button appears when scrolled away

3. **Rich Agent Labels** (expanded from 150px to 220px):
   - Status dot (green pulsing = active, green = running, gray = stopped)
   - Agent name with click-to-navigate to AgentDetail
   - Context percentage with color coding (red ≥80%, yellow ≥60%)
   - Mini progress bar showing context usage
   - Execution stats row: tasks count, success rate, cost, last execution time

4. **Improved Layout**:
   - Row height increased from 32px to 64px for rich labels
   - Timeline max-height increased from 320px to 400px
   - Playback controls hidden in live mode (shown only when replaying)
   - Stopped agents display grayed out with "Stopped" label

5. **State Persistence**:
   - View preference saved to `trinity-dashboard-view` localStorage key

**Files Modified**:
- `src/frontend/src/views/Dashboard.vue` - Toggle labels, stats props
- `src/frontend/src/components/ReplayTimeline.vue` - Rich labels, live mode
- `src/frontend/src/stores/network.js` - `setViewMode()`, keep WebSocket connected

---

### 2026-01-09 21:30:00
✨ **Feature: System Agent Schedule & Execution Management**

**Goal**: Enable System Agent to manage schedules and monitor executions via slash commands and REST API.

**Backend Changes**:
- Added `GET /api/ops/schedules` endpoint for listing all schedules with filters and execution history
- Added `list_all_schedules()` method to `db/schedules.py`
- Exposed method via `database.py` DatabaseManager

**System Agent Slash Commands**:
| Command | Purpose |
|---------|---------|
| `/ops/schedules` | Quick schedule overview |
| `/ops/schedules/list` | Detailed schedule listing with history |
| `/ops/schedules/pause [agent]` | Pause schedules (all or per-agent) |
| `/ops/schedules/resume [agent]` | Resume paused schedules |
| `/ops/executions/list [agent]` | List recent task executions |
| `/ops/executions/status <id>` | Get execution details |

**Files Created**:
- `config/agent-templates/trinity-system/.claude/commands/ops/schedules/list.md`
- `config/agent-templates/trinity-system/.claude/commands/ops/schedules/pause.md`
- `config/agent-templates/trinity-system/.claude/commands/ops/schedules/resume.md`
- `config/agent-templates/trinity-system/.claude/commands/ops/executions/list.md`
- `config/agent-templates/trinity-system/.claude/commands/ops/executions/status.md`

**Files Modified**:
- `src/backend/routers/ops.py` - New `/api/ops/schedules` endpoint
- `src/backend/db/schedules.py` - `list_all_schedules()` method
- `src/backend/database.py` - Exposed method
- `config/agent-templates/trinity-system/CLAUDE.md` - Schedule management docs
- `config/agent-templates/trinity-system/template.yaml` - New slash commands
- `config/agent-templates/trinity-system/.claude/commands/ops/schedules.md` - Updated overview

---

### 2026-01-09 19:45:00
🔧 **Refactor: AgentDetail.vue Modularization**

**Goal**: Split monolithic AgentDetail.vue (~1860 lines) into modular, maintainable components.

**Results**:
- **AgentDetail.vue**: Reduced from ~1860 lines to **603 lines** (68% reduction)
- **9 new components extracted** totaling ~1500 lines (focused, reusable)

**Components Created**:
| Component | Lines | Purpose |
|-----------|-------|---------|
| `AgentHeader.vue` | 316 | Agent header with stats, controls, git sync |
| `CredentialsPanel.vue` | 296 | Credential management (assign, quick-add) |
| `TerminalPanelContent.vue` | 165 | Terminal tab inner content |
| `PermissionsPanel.vue` | 147 | Agent collaboration permissions |
| `FileTreeNode.vue` | 140 | Recursive file tree (render function) |
| `FilesPanel.vue` | 129 | Files tab with tree browser |
| `SharingPanel.vue` | 125 | Share agent with team members |
| `ResourceModal.vue` | 109 | Memory/CPU configuration modal |
| `LogsPanel.vue` | 73 | Container logs viewer |

**Key Improvements**:
- Each component is self-contained with its own composable initialization
- Terminal KeepAlive behavior preserved (v-show pattern maintained)
- Tab navigation simplified with computed `visibleTabs` array
- All existing functionality preserved (zero behavioral changes)

**Pattern**: Components receive `agent-name` and `agent-status` props, initialize their own composables internally. This follows the pattern established by existing panels (`InfoPanel`, `SchedulesPanel`, etc.).

**Modified Files**:
- `src/frontend/src/views/AgentDetail.vue` - Lean orchestrator
- `src/frontend/src/components/` - 9 new component files

---

### 2026-01-09 18:30:00
🐛 **Fix: System Agent Not Visually Distinct on Dashboard**

**Issue**: Trinity System Agent displayed as a regular agent instead of using the distinct purple `SystemAgentNode` component.

**Root Cause**: `register_agent_owner()` silently failed on `IntegrityError` when the ownership record already existed, without updating the `is_system` flag. If the system agent was created before the `is_system` feature, or if the container was recreated, the flag stayed `0` (false).

**Fix**:
1. Modified `register_agent_owner()` to update `is_system=1` when record exists and `is_system=True` is passed
2. Added call in `ensure_deployed()` to always ensure database record has correct flag

**Modified Files**:
- `src/backend/db/agents.py` - Update is_system on conflict
- `src/backend/services/system_agent_service.py` - Ensure flag on startup

---

### 2026-01-09 17:00:00
🐛 **Fix: GitHub PAT Lookup for Dynamic Templates**

**Issue**: MCP `create_agent` with `github:owner/repo` templates failed with "GitHub PAT not configured" even when PAT was set via Settings or env var.

**Root Cause**: Code inconsistency - Settings page stored PAT in SQLite `system_settings` table, but agent creation looked in Redis credential store (legacy location).

**Fix**: Updated `crud.py` to use `get_github_pat()` from `settings_service.py` which checks SQLite first, then falls back to `GITHUB_PAT` env var.

**Modified Files**:
- `src/backend/services/agent_service/crud.py` - Use settings_service instead of credential_manager

---

### 2026-01-09 16:45:00
🐛 **Fix: MCP Configuration Modal - Missing `type` and Port**

**Issues Fixed**:
1. Missing `"type": "http"` in generated MCP config - required by Claude Code
2. Production URL missing port 8080 (was `https://{host}/mcp`, now `http://{host}:8080/mcp`)

**Before** (broken):
```json
{
  "mcpServers": {
    "trinity": {
      "url": "https://example.com/mcp",
      "headers": { "Authorization": "Bearer ..." }
    }
  }
}
```

**After** (correct):
```json
{
  "mcpServers": {
    "trinity": {
      "type": "http",
      "url": "http://example.com:8080/mcp",
      "headers": { "Authorization": "Bearer ..." }
    }
  }
}
```

**Modified Files**:
- `src/frontend/src/views/ApiKeys.vue` - Fixed `getMcpConfig()` and `mcpServerUrl` computed property

---

### 2026-01-09 16:15:00
📋 **Roadmap: Phase 15 - Compliance-Ready Development Methodology**

**Addition**: Added Phase 15 to roadmap for SOC-2 and ISO 27001-compatible development practices.

**Scope**: Extend `dev-methodology-template/` to produce audit-ready artifacts:
- SOC-2 Control Mapping (Trust Service Criteria)
- ISO 27001:2022 Alignment (ISMS controls)
- Change Management Controls (CC8.1)
- Access Control Documentation
- Security Review Gates (mandatory `/security-check`)
- Audit Trail Requirements
- Incident Response Procedures
- Compliance Evidence Generation

**Reference**: Template at `dev-methodology-template/` contains reusable slash commands, sub-agents, and memory file structure that maps naturally to compliance controls.

**Modified Files**:
- `docs/memory/roadmap.md` - Added Phase 15, backlog entry, decision log

---

### 2026-01-09 15:45:00
🔧 **Infrastructure: Production Port Remapping**

**Change**: Simplified production port configuration to use standard ports.

**Port Changes**:
| Service | Before | After |
|---------|--------|-------|
| Frontend (nginx) | 3005 | **80** |
| Backend (FastAPI) | 8005 | **8000** |
| MCP Server | 8007 | **8080** |
| Agent SSH Start | 2223 | **2222** |

**Rationale**:
- Port 80: Standard HTTP, no port needed in URLs
- Port 8000: De facto Python API standard
- Port 8080: Common HTTP alternative, intuitive for MCP
- Port 2222: Memorable SSH sequence

**Modified Files**:
- `docker-compose.prod.yml` - Updated port mappings and internal references
- `deploy.config.example` - Updated default ports
- `src/frontend/nginx.conf` - Updated backend proxy URLs
- `src/backend/services/docker_service.py` - SSH port range now starts at 2222
- `scripts/deploy/gcp-deploy.sh` - Updated default ports and display URLs
- `scripts/deploy/gcp-firewall.sh` - Updated firewall port list
- `CLAUDE.local.md.example` - Updated port documentation
- `docs/memory/architecture.md` - Updated port allocation table

**Migration Notes**:
- Update firewall rules to allow 80/tcp, 8000/tcp, 8080/tcp
- No data migration required - purely port mapping change
- Development ports unchanged (3000, 8000, 8080)

---

### 2026-01-09 14:30:00
✨ **Feature: Agents Page UI Overhaul - Dashboard Parity**

**Enhancement**: Completely redesigned the Agents page (`/agents`) to match the Dashboard tile design, providing consistent UX across the platform.

**What Changed**:

1. **Grid Layout** - Changed from vertical list to responsive 3-column grid (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3`)

2. **Autonomy Toggle** - Added interactive AUTO/Manual toggle switch matching Dashboard tiles
   - Amber color when enabled, gray when disabled
   - Calls `PUT /api/agents/{name}/autonomy` to toggle all schedules
   - Loading state during API calls

3. **Execution Stats Row** - New compact stats display:
   - Task count (24h): "12 tasks"
   - Success rate with color coding: green (≥80%), yellow (50-79%), red (<50%)
   - Total cost: "$0.45"
   - Last execution: "2m ago"

4. **Context Progress Bar** - Now always visible (not just for running agents)
   - Color coded: green → yellow → orange → red based on usage

5. **Card Styling** - Matching AgentNode.vue design with shadows, rounded corners, hover effects

**Modified Files**:
- `src/frontend/src/stores/agents.js` - Added `executionStats` state, `fetchExecutionStats()`, `toggleAutonomy()` actions
- `src/frontend/src/views/Agents.vue` - Complete rewrite with grid layout and new features
- `docs/memory/feature-flows/agents-page-ui-improvements.md` - Added Enhancement section

**Visual Comparison**:
| Feature | Before | After |
|---------|--------|-------|
| Layout | Vertical list | 3-column grid |
| Autonomy | Not shown | Toggle switch |
| Execution Stats | Not shown | Tasks · Rate · Cost · Time |
| Context Bar | Running only | All agents |

---

### 2026-01-06 18:30:00
♻️ **Refactor: Sovereign Archive Storage Architecture**

**Refactoring**: Removed external S3 dependency and implemented pluggable storage interface with local-only default for sovereign deployments.

**Motivation**: Following architectural feedback to maintain full data sovereignty - no system logs or archives should leave the company's infrastructure. The platform now stores all data locally within mounted volumes, giving operators full control over backup strategies.

**What Changed**:
1. **New Storage Interface** - Abstract `ArchiveStorage` base class with pluggable backend support
2. **Local Storage Default** - `LocalArchiveStorage` implementation stores archives in mounted Docker volume
3. **S3 Code Removed** - Deleted S3-specific code (`s3_storage.py`), boto3 dependency, and S3 env vars
4. **Sovereign Backup Strategies** - Documentation now covers Docker volume backups, NAS/NFS mounts, rsync, cross-instance copies

**New Files**:
- `src/backend/services/archive_storage.py` - Storage abstraction layer

**Deleted Files**:
- `src/backend/services/s3_storage.py` - S3 integration (removed)

**Modified Files**:
- `src/backend/services/log_archive_service.py` - Uses storage interface instead of S3 directly
- `docker/backend/Dockerfile` - Removed boto3 dependency
- `docker-compose.yml` - Removed S3 env vars, added `LOG_ARCHIVE_PATH`
- `docs/memory/feature-flows/vector-logging.md` - Replaced S3 docs with sovereign backup strategies
- `tests/test_log_archive.py` - Removed S3 tests, updated to use storage interface

**Configuration Changes**:
```bash
# Removed:
LOG_S3_ENABLED, LOG_S3_BUCKET, LOG_S3_ACCESS_KEY, LOG_S3_SECRET_KEY,
LOG_S3_ENDPOINT, LOG_S3_REGION

# Added:
LOG_ARCHIVE_PATH=/data/archives  # Local path for archived logs
```

**Backup Strategies** (Sovereign):
- Mount NAS/NFS to archives volume
- rsync to backup server via cron
- Docker volume backup/restore
- Cross-instance volume copy

**Impact**:
- **Breaking**: S3 configuration no longer supported (by design)
- **Non-Breaking**: Archives still stored in `trinity-archives` volume
- **Benefit**: Full data sovereignty - no external dependencies
- **Extensible**: Storage interface allows future backends (NFS, SFTP, etc.) without S3

**Architecture Philosophy**: Keep all data (logs, archives, backups) within operator-controlled infrastructure. External storage can be implemented via volume mounts or custom scripts, not hardcoded cloud dependencies.

---

### 2026-01-06 15:45:00
📋 **Docs: Process-Driven Multi-Agent Systems Vision (Refined)**

Refined the concept document based on design review discussion.

**Key Design Decisions**:

1. **Simplified Role Model** (dropped RACI complexity):
   - **Executor**: Does the work, saves outputs
   - **Monitor**: Watches for failures, handles escalations
   - **Informed**: Learns from events, builds situational awareness
   - Dropped "Consulted" (just an agent-to-agent call)

2. **Stateful Agents as Core Principle**:
   - Agents build memory, beliefs, and judgment over time
   - "Informed" role enables situational awareness
   - Informed agents can proactively trigger actions based on observed events

3. **Output Storage**:
   - Agent responsibility (not platform-managed)
   - Executors save to shared folders or external systems (CRM, Google Drive, etc.)
   - Next step's agent ingests from designated location

4. **Human Approval Steps** (critical feature):
   - Dedicated `type: human_approval` step type
   - Separate approval interface for human operators
   - Timeout, escalation, delegation support
   - Mobile-friendly with email/Slack action links

5. **System Agent Role** (unchanged):
   - Stays focused on platform operations
   - Does NOT orchestrate business processes
   - Process orchestration handled by Process Execution Engine + Monitor agents

**Updated Files**:
- `docs/drafts/PROCESS_DRIVEN_AGENTS.md` - Full concept with refined roles, human approval section, approval interface mockup
- `docs/memory/requirements.md` - Updated 14.1, 14.2, added 14.3 for human-in-the-loop

---

### 2026-01-06 14:30:00
📋 **Docs: Process-Driven Multi-Agent Systems Vision**

Added comprehensive documentation for the strategic evolution of Trinity into a business process orchestration platform.

**New Concept Document**: `docs/drafts/PROCESS_DRIVEN_AGENTS.md`
- Business processes as first-class entities that orchestrate agent collaboration
- Simplified role model: Executor, Monitor, Informed
- Process lifecycle: Design → Configure → Test → Production → Improvement
- Human-in-the-loop improvement cycles with feedback collection
- UI vision: Process Designer, Process Dashboard, Execution View, Human Approval Interface

**New Requirements Added** (requirements.md):
- **13.1 Horizontal Agent Scalability**: Agent pools with N instances, load balancing, auto-scaling
- **13.2 Event Bus Infrastructure**: Redis Streams pub/sub with permission-gated subscriptions
- **13.3 Event Handlers & Reactions**: Automatic agent reactions to events from permitted agents
- **14.1 Business Process Definitions**: Role-based orchestration, triggers, policies
- **14.2 Process Execution & Human Approval**: Execution engine, approval interface
- **14.3 Human-in-the-Loop Improvement**: Feedback collection, quality tracking

**Roadmap Updates**:
- Phase 13: Agent Scalability & Event-Driven Architecture
- Phase 14: Process-Driven Multi-Agent Systems (Future Vision)
- Updated backlog with new high-priority items
- Added 3 decision log entries

**Key Insight**: Business processes should drive agent design, not the other way around. Start with "what outcome do we want?" and derive the agents needed to achieve it.

---

### 2026-01-05 18:30:00
✨ **Feature: Vector Log Retention and Archival**

**New Feature**: Automated log retention, rotation, and archival system for Vector logs with local storage.

**Compliance Gap Addressed**: Vector logging lacked retention policy and archival capabilities required for SOC2/ISO27001 compliance.

**What Was Added**:
1. **Daily Log Rotation** - Vector now writes to date-stamped files (`platform-2026-01-05.json`)
2. **Automated Archival** - Nightly job compresses and archives logs older than retention period
3. **Local Storage** - Archives stored in mounted Docker volume (`trinity-archives`)
4. **API Endpoints** - Admin-only endpoints for stats, config, and manual archival
5. **Integrity Verification** - SHA256 checksums ensure archive integrity

**New Files**:
- `src/backend/services/log_archive_service.py` - Archival logic + APScheduler
- `src/backend/routers/logs.py` - Log management API endpoints
- `tests/test_log_archive.py` - Comprehensive test coverage

**Modified Files**:
- `config/vector.yaml` - Date-based file paths for daily rotation
- `src/backend/main.py` - Register logs router, start archive scheduler
- `docker-compose.yml` - Add log retention env vars, trinity-archives volume
- `docs/memory/feature-flows/vector-logging.md` - Document retention features

**Configuration**:
```bash
LOG_RETENTION_DAYS=90       # Days to keep logs
LOG_ARCHIVE_ENABLED=true    # Enable automated archival
LOG_CLEANUP_HOUR=3          # Hour (UTC) to run nightly job
LOG_ARCHIVE_PATH=/data/archives  # Local path for archived logs
```

**API Endpoints**:
- `GET /api/logs/stats` - Log file statistics
- `GET /api/logs/retention` - Retention configuration
- `PUT /api/logs/retention` - Update retention (runtime)
- `POST /api/logs/archive` - Manual archival trigger
- `GET /api/logs/health` - Service health check

**Impact**:
- No breaking changes to existing Vector functionality
- Existing single-file logs (`platform.json`, `agents.json`) can be manually archived
- New date-based files start after Vector restart
- Disk space remains stable after retention period

**Compliance**: Addresses SOC2/ISO27001 requirement for log retention policy and secure archival.

---

### 2026-01-05 10:15:00
🐛 **Fix: ReplayTimeline infinite loop causing browser hang**

Fixed critical bug where switching to Replay mode caused the browser to freeze.

**Root Cause**: The `timeTicks` computed property in ReplayTimeline.vue generates grid lines every 15 minutes. When `timelineStart` is `null` (no historical events), `startTime` computed to 0 (epoch 1970). The for loop then ran from epoch to current time (2026), creating ~2 million tick iterations and hanging the browser.

**Fix**: Added guards to all computed properties that rely on timeline bounds:
- `timeTicks`: Early return if `!startTime.value` or `!endTime.value`, plus safety limit of 700 max ticks
- `agentRows`: Early return if timeline data is missing
- `communicationArrows`: Early return if timeline data is missing
- `currentTimeX`: Early return if timeline data is missing

**Files Changed**:
- `src/frontend/src/components/ReplayTimeline.vue`: Lines 411-445, 448-450, 520-522, 557-560

**Behavior Now**:
- Switching to Replay mode with no historical data shows empty timeline (no hang)
- Timeline safely handles edge cases with missing data

---

### 2026-01-03 21:45:00
🎬 **Enhancement: Replay Mode Activity & Context Simulation**

Enhanced replay mode to simulate agent activity states and context changes during playback.

**What Was Missing**: After the edge animation fix, replay only showed animated arrows but:
1. Agent activity state (green blinking "Active" indicator) wasn't updating
2. Context progress bars remained static during replay

**Solution**: Added simulation functions to `network.js`:
- `setNodeActivityState()` - Updates agent activity state with Vue reactivity
- `simulateContextChange()` - Adjusts context percentage with bounds (0-100%)
- `simulateAgentActivity()` - Orchestrates the full activity simulation:
  - Source agent becomes active immediately (initiating collaboration)
  - Target agent becomes active after 300ms (processing request)
  - Context bars increase: source +1-3%, target +2-5%
  - Both return to idle after 2-3 seconds

**Files Changed**:
- `src/frontend/src/stores/network.js`:
  - Added `activityTimeouts` ref to track pending timeouts
  - Added `setNodeActivityState()`, `simulateContextChange()`, `simulateAgentActivity()`
  - `scheduleNextEvent()` now calls `simulateAgentActivity()` for each event
  - `startReplay()` initializes context percentages (5-15%) for running agents
  - `stopReplay()` clears activity timeouts and resets all agents to idle

**Behavior Now**:
- During replay, agents show green pulsing "Active" state when involved in collaboration
- Context bars grow incrementally as events play back
- All states reset properly when replay stops
- Switching to Live mode resumes real context polling

---

### 2026-01-03 21:15:00
🐛 **Fix: Dashboard Replay Mode Now Works**

Fixed critical bug where replay mode visuals weren't updating on the Dashboard.

**Root Cause**: The `edges` variable is a computed property that merges `collaborationEdges` and `permissionEdges`. All edge manipulation functions (`animateEdge`, `createHistoricalEdges`, `resetAllEdges`, etc.) were trying to modify `edges.value` directly. Since computed properties return new arrays each time, modifications were being lost.

**Fix**: Updated all edge manipulation functions to work with `collaborationEdges.value` instead of `edges.value`. Added Vue reactivity triggers (`collaborationEdges.value = [...collaborationEdges.value]`) after modifications to ensure the computed `edges` recalculates.

**Files Changed**:
- `src/frontend/src/stores/network.js`:
  - `createHistoricalEdges()` - Push to `collaborationEdges.value` (line 217)
  - `animateEdge()` - Find/push in `collaborationEdges.value` (lines 455, 486)
  - `fadeEdgeAnimation()` - Find in `collaborationEdges.value` (line 554)
  - `clearEdgeAnimation()` - Find in `collaborationEdges.value` (line 573)
  - `resetAllEdges()` - Iterate over `collaborationEdges.value` (line 946)
  - `handleAgentDeleted()` - Filter `collaborationEdges.value` (line 434)
  - Added reactivity triggers after all edge modifications

**Behavior Now**:
- Replay mode properly animates edges when playing back historical events
- Edges turn blue/animated during replay, then fade back to gray
- Play/Pause/Stop controls work correctly
- Timeline scrubber and event markers function as expected

---

### 2026-01-03 19:30:00
🎛️ **Dashboard Autonomy Toggle Switch**

Added interactive toggle switch to Dashboard agent tiles for quick autonomy mode control.

**Visual Design**:
- Toggle switch (36x20px) with smooth sliding animation
- Label shows "AUTO" (amber) or "Manual" (gray) next to switch
- Disabled state with opacity during API call
- Tooltips explain current state and action

**Files Changed**:
- `src/frontend/src/components/AgentNode.vue:62-96` - Toggle switch UI and handler
- `src/frontend/src/stores/network.js:993-1030` - `toggleAutonomy()` action

**Behavior**:
- Click toggle to enable/disable all schedules for the agent
- Node data updates reactively (no page refresh needed)
- System agents do not show the toggle (autonomy N/A)

**Documentation Updated**:
- `docs/memory/feature-flows/autonomy-mode.md` - Full toggle documentation
- `docs/memory/feature-flows/agent-network.md` - AgentNode toggle reference

---

### 2026-01-03 17:55:00
🐛 **Fix: Scheduler now respects Autonomy Mode**

Fixed bug where scheduled tasks would execute even when agent's Autonomy Mode was disabled (Manual mode).

**Root Cause**: `scheduler_service._execute_schedule()` only checked `schedule.enabled` but not the agent's `autonomy_enabled` flag.

**Fix**: Added autonomy check in `_execute_schedule()` before task execution:
```python
if not db.get_autonomy_enabled(schedule.agent_name):
    logger.info(f"Schedule skipped: agent autonomy is disabled")
    return
```

**Files Changed**: `src/backend/services/scheduler_service.py:186-189`

**Behavior Now**:
- Manual mode (autonomy disabled) = no schedules run
- AUTO mode (autonomy enabled) = schedules run as configured

---

### 2026-01-03 14:15:00
🔧 **GitHub Agent Templates - Updated for Trinity Compatibility**

Updated all three GitHub demo agent templates (Cornelius, Corbin, Ruby) to match TRINITY_COMPATIBLE_AGENT_GUIDE.md.

**Changes pushed to GitHub:**

| Repository | Commit | Changes |
|------------|--------|---------|
| `abilityai/agent-cornelius` | `043d24a` | +.gitignore updates, +memory/, +outputs/, template.yaml commit_paths |
| `abilityai/agent-corbin` | `481bf59` | +.gitignore updates, +outputs/, template.yaml commit_paths |
| `abilityai/agent-ruby` | `b946886` | +.gitignore updates, +memory/, +outputs/ |

**Common .gitignore additions:**
- `.trinity/` - Platform-managed directory (injected at startup)
- `.claude/commands/trinity/` - Platform-injected slash commands
- `content/` - Large generated assets (videos, audio, images)

**Directory structure updates:**
- Added `memory/` directory with .gitkeep (Cornelius, Ruby)
- Added `outputs/` directory with .gitkeep (all three)
- Updated `git.commit_paths` to include new directories

**Note**: These agents already had comprehensive template.yaml files with tagline, use_cases, capabilities, metrics, etc. The updates focused on .gitignore and directory structure per the guide.

---

### 2026-01-03 13:30:00
📚 **Demo Agent Templates - Updated for Flexibility & Best Practices**

Updated local demo templates (demo-researcher, demo-analyst) to follow TRINITY_COMPATIBLE_AGENT_GUIDE.md and improved `/create-demo-agent-fleet` command.

**Command Updates** (`.claude/commands/create-demo-agent-fleet.md`):
- Added Option A (Recommended): Local Research Network using system manifest deployment
- Option B: GitHub Templates (Cornelius, Corbin, Ruby) kept for reference
- Added complete system manifest example with permissions and shared folders
- Added test collaboration examples showing inter-agent communication

**Template Improvements** (`config/agent-templates/demo-*`):
- Added `tagline` and `use_cases` fields to template.yaml files
- Added `memory/` directories with .gitkeep files
- Added `outputs/` directory to demo-analyst for generated briefings
- Updated all slash commands to use dynamic agent/path discovery instead of hardcoded names
- Added Bash tool to allowed-tools for filesystem discovery

**Key Changes**:
- demo-analyst CLAUDE.md: Instructions for dynamic shared folder discovery
- briefing.md: Discovers researcher folder dynamically
- opportunities.md, ask.md: Dynamic path resolution
- request-research.md: Lists agents first, then calls researcher

**Files Changed**:
- `.claude/commands/create-demo-agent-fleet.md` - Complete rewrite with 2 deployment options
- `config/agent-templates/demo-researcher/template.yaml` - Added tagline, use_cases
- `config/agent-templates/demo-analyst/template.yaml` - Added tagline, use_cases
- `config/agent-templates/demo-analyst/CLAUDE.md` - Dynamic agent naming instructions
- `config/agent-templates/demo-analyst/.claude/commands/*.md` - All updated for dynamic paths

---

### 2026-01-03 11:45:00
🔧 **MCP Tool: get_agent_info - Agent Template Metadata Access**

New MCP tool allowing agents to discover detailed information about other agents they have permission to access.

**New Tool**: `get_agent_info(name)`

Returns full template.yaml metadata including:
- Display name, description, tagline, version, author
- Capabilities (e.g., `["synthesis", "strategic-analysis"]`)
- Available slash commands with descriptions
- MCP servers the agent uses
- Tools, skills, and example use cases
- Resource allocation (CPU/memory)
- Current status (running/stopped)

**Access Control**:
- Agent-scoped keys: Can only access self + permitted agents
- System agents: Full access to all agents
- User-scoped keys: Access to all accessible agents

**Use Case**: Enables orchestrator agents to understand worker capabilities before delegating tasks.

**Files Changed**:
- `src/mcp-server/src/types.ts` - Added `AgentTemplateInfo` and `AgentCommand` types
- `src/mcp-server/src/client.ts` - Added `getAgentInfo()` method
- `src/mcp-server/src/tools/agents.ts` - Added `get_agent_info` tool with access control
- `src/mcp-server/src/server.ts` - Registered new tool

---

### 2026-01-03 10:30:00
🎨 **Dashboard Agent Cards - Enhanced Styling & Resource Indicators**

Improved agent cards on the Dashboard with a more refined look and resource information display.

**Visual Changes**:
- Increased card width from 280px to 320px for better readability
- Added backdrop-blur and semi-transparent backgrounds for a modern glass effect
- Softer border styling (removed double border, adjusted opacity)
- Minimum height increased to 180px for consistent layout

**New Features**:
- Added resource indicators row showing Memory and CPU limits
- Displays configured limits (e.g., "4g", "2 cores") or defaults
- Subtle separator line between execution stats and resources
- Tooltips show full resource details on hover

**Files Changed**:
- `src/frontend/src/components/AgentNode.vue` - Styling and resource display
- `src/frontend/src/stores/network.js` - Pass memoryLimit/cpuLimit to node data
- `src/backend/services/agent_service/helpers.py` - Include resource limits in agent data

---

### 2026-01-02 18:15:00
🐛 **Fix SSH Privilege Separation Directory**

Fixed SSH failing to start due to missing privilege separation directory.

**Issue**: `/var/run/sshd` created in Dockerfile, but `/var/run` is often a tmpfs that gets wiped on container restart.

**Fix**: Added `mkdir -p /var/run/sshd` in startup.sh before starting sshd.

**Files Changed**:
- `docker/base-image/startup.sh` - Ensure `/var/run/sshd` exists before sshd start

**Note**: Requires base image rebuild: `./scripts/deploy/build-base-image.sh`

---

### 2026-01-02 18:00:00
🐛 **Fix SSH Password Authentication & Host Detection**

Fixed two critical bugs in the SSH ephemeral password system:

**Bug 1: Password Not Being Set (sed escaping)**
- SHA-512 password hashes contain `$` characters (e.g., `$6$salt$hash`)
- The `$` was not escaped in sed, causing the replacement to fail
- **Fix**: Use `usermod -p` with single-quoted password instead of sed
- **Fallback**: If usermod fails, try `chpasswd` with plaintext password

**Bug 2: Host Detection Returns Docker IP**
- `get_ssh_host()` runs inside the backend container
- Socket-based detection returned container's Docker network IP (172.28.x.x)
- **Fix**: Improved detection priority:
  1. SSH_HOST env var (explicit config)
  2. Tailscale IP detection
  3. `host.docker.internal` (Docker Desktop Mac/Windows)
  4. Default gateway IP (Linux Docker host)
  5. Fallback to localhost with warning

**Files Changed**:
- `src/backend/services/ssh_service.py` - `set_container_password()` and `get_ssh_host()`

---

### 2026-01-02 17:15:00
🔧 **SSH Access Toggle in Settings UI**

Added UI toggle for `ssh_access_enabled` in the Settings page.

**Location**: Settings → SSH Access section → Enable SSH Access toggle

**Files Changed**:
- `src/frontend/src/views/Settings.vue` - Added SSH Access section with toggle switch

---

### 2026-01-02 16:30:00
🔐 **MCP SSH Access Tool - Password Auth & System Setting**

Enhanced SSH access with password-based authentication and system-wide enable/disable setting.

**New Features**:
- Password-based auth: `auth_method: "password"` returns sshpass one-liner command
- System setting `ssh_access_enabled` (default: false) - must be enabled in Settings → Ops Settings
- Password set directly in container's `/etc/shadow` (bypasses PAM issues)

**Container Security Updates** (required for SSH):
- Added capabilities: `SETGID`, `SETUID`, `CHOWN`, `SYS_CHROOT`, `AUDIT_WRITE`
- Removed `no-new-privileges:true` (blocks SSH privilege separation)
- **Note**: Existing agents must be deleted and recreated to get new settings

**Files Changed**:
- `src/backend/services/ssh_service.py` - Password generation, shadow file editing
- `src/backend/services/settings_service.py` - `ssh_access_enabled` ops setting
- `src/backend/services/agent_service/crud.py` - Container capabilities
- `src/backend/services/agent_service/lifecycle.py` - Container capabilities

---

### 2026-01-02 15:48:00
🔐 **MCP SSH Access Tool - Ephemeral SSH Credentials**

Added new MCP tool `get_agent_ssh_access` to generate ephemeral SSH credentials for direct terminal access to agent containers. Designed for Tailscale/VPN environments.

**Features**:
- Generate ED25519 key pairs on demand
- Auto-inject public key into agent's `~/.ssh/authorized_keys`
- Configurable TTL (0.1-24 hours, default: 4 hours)
- Keys auto-expire via Redis TTL
- Returns SSH command, private key, and connection instructions
- Host auto-detection (SSH_HOST env → Tailscale IP → localhost)

**MCP Tool**:
- `get_agent_ssh_access(agent_name, ttl_hours, auth_method)` - Returns credentials and connection command

**Backend API**:
- `POST /api/agents/{name}/ssh-access` - Generate ephemeral SSH credentials

**Security**:
- Private key shown once, never stored on server
- Credentials automatically removed from containers on expiry
- User must have access to agent
- Agent must be running
- Controlled by `ssh_access_enabled` system setting (default: disabled)

**Files Created**:
- `src/backend/services/ssh_service.py` - SSH key generation, password management, injection, cleanup

**Files Changed**:
- `src/backend/routers/agents.py` - SSH access endpoint
- `src/mcp-server/src/tools/agents.ts` - `getAgentSshAccess` tool
- `src/mcp-server/src/client.ts` - `createSshAccess()` method
- `src/mcp-server/src/types.ts` - `SshAccessResponse` type
- `src/mcp-server/src/server.ts` - Register new tool

---

### 2026-01-02 15:00:00
⚙️ **Per-Agent Resource Limits Configuration**

Added ability to configure memory and CPU allocation for individual agents. Changes take effect on agent restart.

**Features**:
- Memory options: 1g, 2g, 4g, 8g, 16g, 32g, 64g
- CPU options: 1, 2, 4, 8, 16 cores
- UI in **Metrics tab** - "Resource Allocation" card with "Configure" button
- Modal dialog with warning: "Changes require an agent restart to take effect"
- Works regardless of agent state (running or stopped)
- Container is automatically recreated with new limits on next start

**Backend**:
- New columns in `agent_ownership`: `memory_limit`, `cpu_limit`
- `GET /api/agents/{name}/resources` - Get current and configured limits
- `PUT /api/agents/{name}/resources` - Set new limits (owner-only)
- `check_resource_limits_match()` helper triggers container recreation on start

**Files Changed**:
- `src/backend/database.py` - Migration + delegate methods
- `src/backend/db/agents.py` - `get_resource_limits()`, `set_resource_limits()`
- `src/backend/services/agent_service/helpers.py` - `check_resource_limits_match()`
- `src/backend/services/agent_service/lifecycle.py` - Resource check on start
- `src/backend/routers/agents.py` - API endpoints
- `src/frontend/src/composables/useAgentSettings.js` - Resource limits state
- `src/frontend/src/stores/agents.js` - Store methods
- `src/frontend/src/views/AgentDetail.vue` - Resource Allocation UI panel

---

### 2026-01-02 13:15:00
📝 **Fix MCP Config Examples - Add Missing `type: http`**

Fixed MCP configuration examples that were missing the required `"type": "http"` field for HTTP transport.

**Issue**: Claude Code requires explicit `"type": "http"` for URL-based MCP servers. Without it, config validation fails with "Invalid MCP configuration".

**Files Fixed**:
- `src/frontend/src/views/ApiKeys.vue` - API Keys page example config
- `src/mcp-server/README.md` - MCP server documentation
- `docs/memory/architecture.md` - Architecture docs
- `docs/memory/feature-flows/mcp-orchestration.md` - MCP orchestration flow

**Note**: The agent injection code (`docker/base-image/agent_server/services/trinity_mcp.py`) has been correct since Dec 12, 2025. If agents have incorrect config, rebuild the base image with `./scripts/deploy/build-base-image.sh`.

---

### 2026-01-02 12:45:00
🐛 **Fix Execution Log Viewer for Scheduled Tasks**

Fixed bug where execution logs from scheduled/triggered tasks wouldn't display in the Tasks panel log viewer.

**Root Cause**:
- Two different log formats: raw Claude Code stream-json (`/api/task`) vs simplified ExecutionLogEntry (`/api/chat`)
- Scheduled executions were using `/api/chat` which returns simplified format
- `parseExecutionLog()` expected raw Claude Code format

**Fix (Standardization)**:
- Added `AgentClient.task()` method that calls `/api/task` for stateless execution
- Changed scheduler to use `client.task()` instead of `client.chat()`
- All scheduled/triggered executions now return raw Claude Code format
- No frontend changes needed - format is now consistent

**Files Changed**:
- `src/backend/services/agent_client.py` - Added `task()` method + `_parse_task_response()`
- `src/backend/services/scheduler_service.py` - Use `client.task()` for scheduled executions

---

### 2026-01-02 11:30:00
📈 **Agent Container Telemetry with Sparkline Charts**

Added sparkline charts for CPU and memory on Agent Detail page, matching Dashboard telemetry style.

**Reusable Component**:
- Created `SparklineChart.vue` - configurable uPlot-based sparkline (color, yMax, width, height)
- Used by both `HostTelemetry.vue` (Dashboard) and `AgentDetail.vue` (Agent page)

**Agent Detail Stats**:
- Replaced progress bars with sparkline charts for CPU and memory
- 60-sample rolling history (5-minute window at 5s intervals)
- Color-coded percentage values (green/yellow/red thresholds)
- Consistent styling with Dashboard telemetry

**Files Created**:
- `src/frontend/src/components/SparklineChart.vue` - Reusable sparkline component

**Files Changed**:
- `src/frontend/src/composables/useAgentStats.js` - Added cpuHistory/memoryHistory tracking
- `src/frontend/src/views/AgentDetail.vue` - Use SparklineChart for stats display
- `src/frontend/src/components/HostTelemetry.vue` - Refactored to use SparklineChart

---

### 2026-01-02 10:10:00
📊 **Host & Container Telemetry Dashboard**

Added real-time system metrics display to Dashboard header with sparkline charts.

**Features**:
- CPU usage with rolling 60-sample sparkline (5-minute history)
- Memory usage with sparkline and formatted value (used/total GB)
- Disk usage with progress bar and percentage
- Container stats: aggregate CPU/memory across all running agents (shown when agents running)
- 5-second polling interval
- Color-coded values (green < 50%, yellow 50-75%, orange 75-90%, red > 90%)
- Dark/light theme support

**Backend Endpoints**:
- `GET /api/telemetry/host` - Host CPU, memory, disk stats via psutil
- `GET /api/telemetry/containers` - Aggregate stats across agent containers

**Files Created**:
- `src/backend/routers/telemetry.py` - New telemetry router
- `src/frontend/src/components/HostTelemetry.vue` - Sparkline component using uPlot

**Files Changed**:
- `src/backend/main.py` - Mount telemetry router
- `docker/backend/Dockerfile` - Add psutil dependency
- `docker/frontend/Dockerfile` - Use npm ci with lock file
- `src/frontend/package.json` - Add uplot dependency
- `src/frontend/src/views/Dashboard.vue` - Import and render HostTelemetry

---

### 2026-01-01 18:45:00
🔄 **Autonomy Mode Toggle**

Implemented master switch for agent autonomous operation:

**Dashboard**:
- "AUTO" badge (amber) shown on agents with autonomy enabled
- Badge excluded for system agent

**Agent Detail Page**:
- AUTO/Manual toggle button in header (next to Delete button)
- Owners only can toggle (uses `can_share` permission)
- Real-time UI update on toggle

**Backend**:
- `autonomy_enabled` column added to `agent_ownership` table
- `GET /api/agents/{name}/autonomy` - Get autonomy status with schedule counts
- `PUT /api/agents/{name}/autonomy` - Enable/disable autonomy (bulk toggles all schedules)
- `GET /api/agents/autonomy-status` - Dashboard overview for all accessible agents
- New service module: `services/agent_service/autonomy.py`

**Behavior**:
- Enabling autonomy enables ALL schedules for the agent
- Disabling autonomy disables ALL schedules for the agent
- System agent excluded from autonomy controls

**Files Changed**:
- `src/backend/database.py` - Migration + delegate methods
- `src/backend/db/agents.py` - CRUD for autonomy_enabled
- `src/backend/services/agent_service/autonomy.py` (new)
- `src/backend/services/agent_service/__init__.py` - Exports
- `src/backend/routers/agents.py` - API endpoints + agent detail response
- `src/backend/services/agent_service/helpers.py` - get_accessible_agents
- `src/frontend/src/components/AgentNode.vue` - AUTO badge
- `src/frontend/src/stores/network.js` - Pass autonomy_enabled to nodes
- `src/frontend/src/views/AgentDetail.vue` - Toggle button

---

### 2026-01-01 12:30:00
🤖 **Implement Research Network Demo**

Created and validated two-agent autonomous research system demo:

**Templates Created**:
- `demo-researcher` - Autonomous web researcher with `/research` and `/status` commands
- `demo-analyst` - Strategic analyst with `/briefing`, `/opportunities`, `/ask`, `/request-research` commands

**System Manifest**:
- `config/manifests/research-network.yaml` - Full system recipe with shared folders, schedules, permissions

**Validation Results**:
- Both agents deployed and running via system manifest
- Shared folder collaboration working (researcher exposes, analyst consumes)
- Schedules configured: researcher every 4h, analyst daily at 9 AM
- File sharing verified: test findings file written by researcher, readable by analyst

**Files Created**:
- `config/agent-templates/demo-researcher/` (template.yaml, CLAUDE.md, commands/, .gitignore)
- `config/agent-templates/demo-analyst/` (template.yaml, CLAUDE.md, commands/, .gitignore)
- `config/manifests/research-network.yaml`

**Docs Updated**:
- `docs/memory/autonomous-agent-demos.md` - Added validation log and success criteria

---

### 2026-01-01 08:20:00
🎨 **Simplify System Agent UI - Terminal-Centric Layout**

Redesigned `/system-agent` page to give the terminal central prominence:

**Layout Changes**:
- **Terminal**: Now full width (was 2/3), increased height to 600px, central focus on page
- **Quick Actions**: Moved to compact icon buttons in terminal header bar (was separate card with large buttons)
- **OpenTelemetry**: Collapsible section, only shown when data available, collapsed by default

**Quick Actions (now in terminal header)**:
- Emergency Stop (red icon with tooltip)
- Restart All Agents
- Pause Schedules
- Resume Schedules
- Fullscreen toggle (separated by divider)

**Files Changed**:
- `src/frontend/src/views/SystemAgent.vue` - Complete layout restructure

---

### 2026-01-01 03:00:00
📖 **Add Autonomy Section to Main Agent Guide**

Updated `docs/TRINITY_COMPATIBLE_AGENT_GUIDE.md` with compact autonomy section covering:
- Three-phase lifecycle: Develop → Package → Schedule
- Design principles table (self-contained, deterministic, graceful degradation, bounded, idempotent)
- Quick example showing template.yaml schedule and slash command
- Reference to detailed AUTONOMOUS_AGENT_DESIGN.md

Maintains single source of truth principle - main guide has overview, detailed guide has depth.

---

### 2026-01-01 02:30:00
📖 **Add Autonomous Agent Design Guide**

Created `docs/AUTONOMOUS_AGENT_DESIGN.md` - focused guide on designing Trinity agents that run autonomously via scheduled commands.

**Key concepts documented**:
- **Autonomy lifecycle**: Develop interactively → Package as slash command → Schedule via Trinity
- **Command design principles**: Self-contained, deterministic output, graceful degradation, bounded scope, idempotent
- **Template configuration**: `schedules` block in template.yaml with cron expressions
- **Best practices**: Focused commands, structured output, execution time bounds, error handling

**Example patterns**:
- Complete autonomous agent template with health checks and cost reports
- Slash command structure with frontmatter (`description`, `allowed-tools`)
- Cron expression reference

This guide complements the comprehensive TRINITY_COMPATIBLE_AGENT_GUIDE.md by focusing specifically on the scheduled automation use case.

---

### 2026-01-01 01:00:00
🗑️ **Remove Auth0 from Frontend and Backend - Fix HTTP Access on LAN**

**Problem**: Auth0 SDK threw errors when accessing Trinity via HTTP on local network IPs (e.g., `http://192.168.1.127:3000`), causing a blank white page. Auth0 SDK requires "secure origins" (HTTPS or localhost).

**Solution**: Since Auth0 login was already disabled and email authentication is the primary method, removed all Auth0 code from both frontend and backend.

**Frontend Files Removed**:
- `src/frontend/src/config/auth0.js` - Deleted

**Frontend Files Changed**:
- `src/frontend/src/main.js` - Removed Auth0 import, createAuth0(), app.use(auth0), secure origin checks
- `src/frontend/src/components/NavBar.vue` - Removed useAuth0 import and usage
- `src/frontend/src/stores/auth.js` - Removed setAuth0Instance(), handleAuth0Callback(), ALLOWED_DOMAIN import
- `src/frontend/package.json` - Removed `@auth0/auth0-vue` dependency

**Backend Files Changed**:
- `src/backend/routers/auth.py` - Removed `/api/auth/exchange` endpoint, Auth0 imports
- `src/backend/models.py` - Removed `Auth0TokenExchange` model
- `src/backend/config.py` - Removed `AUTH0_DOMAIN`, `AUTH0_ALLOWED_DOMAIN` config vars

**Kept for backward compatibility** (no DB migration needed):
- `auth0_sub` column in users table
- `get_user_by_auth0_sub()`, `get_or_create_auth0_user()` methods in database layer

**Result**: Trinity now works on any HTTP origin. Email authentication and admin password login remain fully functional.

---

### 2026-01-01 00:15:00
📊 **Dashboard Execution Stats - Agent Cards Show Task Metrics**

Added execution statistics to each agent card on the Dashboard, providing at-a-glance visibility into agent workload and performance.

**Display Format** (on each AgentNode):
```
12 tasks · 92% · $0.45 · 2m ago
```

**Backend Changes**:
- `db/schedules.py`: Added `get_all_agents_execution_stats(hours=24)` - single query aggregating stats per agent
- `database.py`: Added delegate method
- `routers/agents.py`: Added `GET /api/agents/execution-stats` endpoint (returns stats for accessible agents only)

**Frontend Changes**:
- `stores/network.js`: Added `executionStats` state and `fetchExecutionStats()` (polls every 5s with context stats)
- `components/AgentNode.vue`: Added compact stats row with task count, success rate (color-coded), cost, and relative time

**Stats Shown**:
| Metric | Description |
|--------|-------------|
| Task count | Executions in last 24h |
| Success rate | % with status='success' (green >80%, yellow 50-80%, red <50%) |
| Total cost | Sum of execution costs |
| Last run | Relative time since last execution |

**Files Changed**:
- `src/backend/db/schedules.py` - Added aggregation query
- `src/backend/database.py` - Delegate method
- `src/backend/routers/agents.py` - New endpoint
- `src/frontend/src/stores/network.js` - State and polling
- `src/frontend/src/components/AgentNode.vue` - UI display

---

### 2025-12-31 23:15:00
🐛 **Test Suite Fixes - 6 Tests Fixed**

Fixed issues identified in test report:

**1. Scheduler Status Endpoint Route Ordering (4 tests)**
- `schedules.py`: Moved `/scheduler/status` endpoint BEFORE `/{name}/schedules` routes
- **Root cause**: FastAPI was matching "scheduler" as an agent name due to route ordering
- **Fix**: Static routes must be defined before dynamic `/{name}/*` routes
- **Tests fixed**: `test_get_scheduler_status`, `test_scheduler_status_structure`, `test_scheduler_status_includes_jobs`, `test_scheduler_status_requires_auth`

**2. API Client Header Merging Bug (2 tests)**
- `tests/utils/api_client.py`: Fixed header conflict when caller passes custom headers
- **Root cause**: `headers` was passed both via `kwargs` and as explicit parameter
- **Fix**: Pop headers from kwargs and merge with default headers
- **Tests fixed**: `test_task_with_source_agent_header`, `test_agent_task_has_agent_trigger`

**3. Session List Access (Already Fixed)**
- Verified `test_agent_chat.py` already handles empty session lists properly
- Tests skip gracefully when no sessions available

---

### 2025-12-31 22:30:00
🧪 **Expanded API Test Coverage**

Added 23 new tests to cover previously untested API endpoints:

**test_agent_chat.py** - Chat Session Lifecycle (6 tests)
- `test_list_chat_sessions_structure` - Verifies session list response structure
- `test_get_session_details` - GET /api/agents/{name}/chat/sessions/{id}
- `test_get_session_details_nonexistent_returns_404` - 404 for missing session
- `test_close_session` - POST /api/agents/{name}/chat/sessions/{id}/close
- `test_close_session_nonexistent_returns_404` - 404 for closing missing session
- `test_close_session_requires_auth` - Auth required for close

**test_schedules.py** - Scheduler Status (4 tests)
- `test_get_scheduler_status` - GET /api/agents/scheduler/status
- `test_scheduler_status_structure` - Validates running, job_count fields
- `test_scheduler_status_includes_jobs` - Verifies jobs/job_count present
- `test_scheduler_status_requires_auth` - Auth required for status

**test_ops.py** - Context Stats (5 tests)
- `test_get_context_stats` - GET /api/agents/context-stats
- `test_context_stats_structure` - Validates agent stats structure
- `test_context_stats_entries_have_valid_structure` - All entries have required fields
- `test_context_stats_requires_auth` - Auth required
- `test_context_stats_returns_valid_response` - Valid response structure

**test_executions.py** - Execution Logs & Details (8 tests)
- `test_get_execution_log_nonexistent_returns_404` - 404 for missing log
- `test_get_execution_log_nonexistent_agent_returns_404` - 404 for missing agent
- `test_get_execution_log_requires_auth` - Auth required
- `test_get_execution_log_returns_log` - GET /api/agents/{name}/executions/{id}/log
- `test_execution_log_content_structure` - Log content validation
- `test_get_execution_details` - GET /api/agents/{name}/executions/{id}
- `test_get_execution_details_nonexistent_returns_404` - 404 handling
- `test_get_execution_details_requires_auth` - Auth required

**Test Suite Summary**: ~515 tests total (up from ~373), 97.8% pass rate

---

### 2025-12-31 18:45:00
📝 **Updated Agent Scheduling Feature Flow Documentation**

- Updated `docs/memory/feature-flows/scheduling.md` to reflect Plan 02/03 refactoring
- **Access Control Dependencies**: Documented `AuthorizedAgent`, `OwnedAgent`, `CurrentUser` usage in schedules router
  - Added "Access" column to API endpoints table
  - Added "Access Control Pattern" section showing dependency usage
  - Updated flow diagrams to show which endpoints use which dependencies
- **AgentClient Service**: Documented new centralized HTTP client for agent communication
  - Added "Agent HTTP Client Service" section with full API reference
  - Documented `AgentChatResponse` and `AgentChatMetrics` dataclasses
  - Added exception handling patterns: `AgentNotReachableError`, `AgentRequestError`
  - Updated execution flow diagrams to show `client.chat()` instead of raw `httpx.post()`
- Updated all line number references for: schedules.py, scheduler_service.py, agent_client.py, dependencies.py
- Added new files to Related Files table: `agent_client.py`, `dependencies.py`

---

### 2025-12-31 18:15:00
📝 **Updated Agent Permissions Feature Flow Documentation**

- Updated `docs/memory/feature-flows/agent-permissions.md` to document access control dependencies
- Added new section on `dependencies.py` type aliases: `AuthorizedAgent`, `OwnedAgent`, `CurrentUser`, etc.
- Documented dependency pattern benefits: consistent 403 messages, OpenAPI visibility, automatic enforcement
- Noted that permissions endpoints currently use inline checks but can migrate to dependency pattern
- Verified and updated all line number references for router (598-638) and service (18-168) files
- Updated lifecycle integration line numbers: crud.py:474-480, agents.py:239-243
- Updated database delegation line numbers: database.py:964-986

---

### 2025-12-31 17:30:00
🐙 **GitHub API Service Extraction - Architecture Refactoring**

**Problem Solved**: `routers/git.py` `initialize_github_sync` endpoint contained ~280 lines of GitHub API business logic that should be in service layer:
- GitHub PAT validation
- Repository existence check (GitHub API call)
- Organization vs user detection (GitHub API call)
- Repository creation (GitHub API call)
- Git initialization commands (container exec calls)
- Working branch creation

This violated separation of concerns, made the logic unreusable, and hard to unit test.

**Solution**: Created `services/github_service.py` with `GitHubService` class:
- `validate_token()` → Tuple[bool, Optional[str]]
- `get_owner_type(owner)` → OwnerType (USER or ORGANIZATION)
- `check_repo_exists(owner, name)` → GitHubRepoInfo
- `create_repository(owner, name, private, description)` → GitHubCreateResult
- Structured exceptions: `GitHubError`, `GitHubAuthError`, `GitHubPermissionError`
- Response models: `GitHubRepoInfo`, `GitHubCreateResult`, `OwnerType`

**Also added to `services/git_service.py`**:
- `GitInitResult` dataclass for initialization results
- `initialize_git_in_container(agent_name, repo, pat)` - handles all git init steps
- `check_git_initialized(agent_name)` - verify git is set up in container

**Files Changed**:
- **Added**: `services/github_service.py` (~280 lines)
- **Updated**: `services/git_service.py` - added init helpers (~180 lines)
- **Updated**: `routers/git.py` - endpoint reduced from ~280 lines to ~115 lines

**Benefits**:
- Separation of concerns: Router handles HTTP, services handle logic
- Reusability: `GitHubService` can be used elsewhere
- Testability: Can unit test GitHub logic without FastAPI
- Maintainability: ~165 lines removed from router
- Error handling: Structured exceptions instead of inline checks
- Type safety: Dataclasses for responses

---

### 2025-12-31 16:20:00
🔌 **Agent HTTP Client Service - DRY Refactoring**

**Problem Solved**: HTTP client code for agent container communication duplicated across multiple files:
- `scheduler_service.py` - 2 places with chat execution + response parsing (~70 lines each)
- `ops.py` - 2 places with context stats fetching
- `lifecycle.py` - Trinity injection with retry logic

This violated DRY, had inconsistent timeout handling, and duplicated response parsing logic.

**Solution**: Created `services/agent_client.py` with `AgentClient` class:
- `chat(message, stream)` → `AgentChatResponse` with parsed metrics
- `get_session()` → `AgentSessionInfo` with context stats
- `inject_trinity_prompt()` → handles retries internally
- `health_check()` → simple boolean health check
- Structured exceptions: `AgentClientError`, `AgentNotReachableError`, `AgentRequestError`
- Response models: `AgentChatMetrics`, `AgentChatResponse`, `AgentSessionInfo`

**Files Changed**:
- **Added**: `services/agent_client.py` (~320 lines)
- **Updated**: `services/scheduler_service.py` - replaced 2 HTTP blocks + parsing (~90 lines removed)
- **Updated**: `routers/ops.py` - replaced 2 context fetch blocks (~30 lines removed)
- **Updated**: `services/agent_service/lifecycle.py` - replaced injection (~40 lines removed)

**Benefits**:
- ~180 lines of duplicated code removed
- Standardized timeouts (CHAT: 300s, SESSION: 5s, INJECT: 10s)
- Type-safe response parsing with dataclasses
- Centralized error handling prevents context% calculation bugs
- Easy to mock for testing

---

### 2025-12-31 16:05:00
🔒 **Access Control Dependencies - DRY Refactoring**

**Problem Solved**: Same access control pattern repeated 50+ times across routers:
```python
if not db.can_user_access_agent(current_user.username, name):
    raise HTTPException(status_code=403, detail="Access denied")
```

This violated DRY principle, caused inconsistent error messages, and was error-prone.

**Solution**: Created FastAPI dependencies in `dependencies.py`:
- `get_authorized_agent(name)` - validates read access, for `{name}` path param
- `get_owned_agent(name)` - validates owner access, for `{name}` path param
- `get_authorized_agent_by_name(agent_name)` - for `{agent_name}` path param
- `get_owned_agent_by_name(agent_name)` - for `{agent_name}` path param
- Type aliases: `AuthorizedAgent`, `OwnedAgent`, `AuthorizedAgentByName`, `OwnedAgentByName`, `CurrentUser`

**Usage Example** (before → after):
```python
# Before
@router.get("/{name}/schedules")
async def list_schedules(name: str, current_user: User = Depends(get_current_user)):
    if not db.can_user_access_agent(current_user.username, name):
        raise HTTPException(status_code=403, detail="Access denied")
    return db.list_schedules(name)

# After
@router.get("/{name}/schedules")
async def list_schedules(name: AuthorizedAgent):
    return db.list_schedules(name)
```

**Files Changed**:
- `dependencies.py` - Added 4 dependency functions + 5 type aliases
- `routers/schedules.py` - Replaced 10 access checks with `AuthorizedAgent`
- `routers/git.py` - Replaced 6 access checks with `AuthorizedAgentByName`/`OwnedAgentByName`
- `routers/sharing.py` - Replaced 3 access checks with `OwnedAgentByName`
- `routers/public_links.py` - Replaced 5 access checks with `OwnedAgentByName`
- `routers/agents.py` - Replaced 3 access checks with `AuthorizedAgentByName`

**Benefits**:
- ~50 lines of duplicated access control code removed
- Consistent 403 error messages across all endpoints
- New endpoints automatically get proper authorization
- OpenAPI schema shows authorization requirements
- Single point of change for access control logic

---

### 2025-12-31 07:40:00
🏗️ **Settings Service - Architecture Fix**

**Problem Solved**: Services were importing from routers (architectural violation):
- `services/agent_service/crud.py` → `routers/settings.py`
- `services/agent_service/lifecycle.py` → `routers/settings.py`
- `services/agent_service/helpers.py` → `routers/settings.py`
- `services/system_agent_service.py` → `routers/settings.py`
- `routers/git.py` → `routers/settings.py`

This inverted the dependency direction (services should never depend on routers) and created circular dependency risk.

**Solution**: Created `services/settings_service.py` with:
- `get_anthropic_api_key()` - Anthropic API key with env fallback
- `get_github_pat()` - GitHub PAT with env fallback
- `get_google_api_key()` - Google API key with env fallback
- `get_ops_setting()` - Ops settings with type conversion
- `OPS_SETTINGS_DEFAULTS` / `OPS_SETTINGS_DESCRIPTIONS` - Moved from router

**Files Changed**:
- **Added**: `src/backend/services/settings_service.py`
- **Updated**: `services/agent_service/crud.py` - Import from service
- **Updated**: `services/agent_service/lifecycle.py` - Import from service
- **Updated**: `services/agent_service/helpers.py` - Import from service
- **Updated**: `services/system_agent_service.py` - Import from service
- **Updated**: `routers/git.py` - Import from service
- **Updated**: `routers/settings.py` - Re-exports from service for backward compatibility
- **Updated**: `docs/memory/architecture.md` - Added settings_service to services list

**Benefits**:
- Clean architecture: Services no longer depend on routers
- Testability: Easy to mock settings in unit tests
- Single source of truth: All settings logic in one place

---

### 2025-12-31 03:00:00
🔄 **Vector Log Aggregation Migration**

**Major Change**: Replaced unreliable audit-logger with Vector for centralized, reliable log aggregation.

**Why**:
- Audit-logger used fire-and-forget HTTP with 2s timeout (silently dropped events)
- 173+ manual call sites meant incomplete coverage and maintenance burden
- No retry/fallback meant single failures = events lost forever

**What Changed**:
- **Added**: Vector service (timberio/vector:0.43.1-alpine) that captures ALL container stdout/stderr via Docker socket
- **Added**: `config/vector.yaml` - Routes logs to `/data/logs/platform.json` and `/data/logs/agents.json`
- **Added**: `src/backend/logging_config.py` - Structured JSON logging for Python backend
- **Removed**: `src/audit-logger/` directory and `docker/audit-logger/` Dockerfile
- **Removed**: `src/backend/services/audit_service.py` and all 173+ `log_audit_event()` calls across 24 files
- **Removed**: `/api/audit/logs` endpoint
- **Updated**: docker-compose.yml and docker-compose.prod.yml
- **Updated**: CLAUDE.md, DEPLOYMENT.md with new architecture
- **Added**: `docs/QUERYING_LOGS.md` - Guide for querying logs with jq/grep

**Benefits**:
- **Reliable**: Never drops logs - captures everything Docker sees
- **Complete**: ALL containers automatically (no manual call sites)
- **Zero maintenance**: No application changes needed after migration
- **Queryable**: JSON files searchable with grep/jq

**Files Removed** (24 files cleaned):
- All routers: agents.py, credentials.py, settings.py, auth.py, mcp_keys.py, ops.py, chat.py, system_agent.py, schedules.py, public_links.py, public.py, systems.py, sharing.py, git.py, setup.py
- All services: files.py, permissions.py, crud.py, queue.py, terminal.py, deploy.py, folders.py, api_key.py
- dependencies.py, main.py, config.py, services/__init__.py

---

### 2025-12-31 01:30:00
👁️ **Execution Log Viewer in Tasks Tab**

**Feature**: View full execution logs for completed tasks via popup modal.

**Implementation**:
- "View Log" button (document icon) appears on completed tasks in Tasks tab
- Clicking opens modal with full Claude Code execution transcript
- Uses existing `GET /api/agents/{name}/executions/{execution_id}/log` endpoint
- Log displayed as formatted JSON in monospace font
- Modal shows status, timestamp, and scrollable log content
- Graceful handling of tasks without logs

**Files Modified**:
- `src/frontend/src/components/TasksPanel.vue` - Added log modal, view button, and related state/functions

---

### 2025-12-31 01:05:00
🔧 **All MCP Chat Calls Now Tracked in Tasks Tab**

**Feature**: ALL MCP `chat_with_agent` calls now create execution records, appearing in the Tasks tab.

**Problem Solved**: Initial fix only tracked agent-to-agent calls (when `X-Source-Agent` header present). User MCP calls (user-scoped keys via Claude Code) were still not tracked.

**Implementation**:
- MCP client now sends `X-Via-MCP: true` header on all chat calls
- Backend checks for either `X-Via-MCP` or `X-Source-Agent` header
- `triggered_by` values: "agent" (agent-to-agent), "mcp" (user MCP calls)
- All MCP executions now visible in Tasks tab

**Files Modified**:
- `src/mcp-server/src/client.ts` - Added `X-Via-MCP: true` header to chat method
- `src/backend/routers/chat.py` - Check for `X-Via-MCP` header in addition to `X-Source-Agent`

---

### 2025-12-31 00:25:00
🔧 **Agent-to-Agent Chat Tracking in Tasks Tab**

**Feature**: MCP `chat_with_agent` calls (non-parallel mode) now create execution records, appearing in the Tasks tab alongside scheduled and manual tasks.

**Problem Solved**: Previously, only `/task` endpoint created `schedule_executions` records. Agent-to-agent chat via `/chat` endpoint (when `parallel=false`, the default) was not tracked in the Tasks tab. This meant MCP orchestration calls weren't visible in the unified execution history.

**Implementation**:
- When `/chat` endpoint receives `X-Source-Agent` header (agent-to-agent call):
  - Creates `schedule_executions` record with `triggered_by="agent"`
  - Updates record on success with response, cost, context, tool_calls
  - Updates record on failure with error message
- All headless executions now visible in Tasks tab: manual, scheduled, and agent-to-agent

**Files Modified**:
- `src/backend/routers/chat.py` - Added execution record creation for agent-to-agent calls
- `docs/memory/feature-flows/execution-queue.md` - Updated with agent-to-agent tracking
- `docs/memory/feature-flows/tasks-tab.md` - Added `/chat` endpoint as entry point
- `docs/memory/feature-flows/mcp-orchestration.md` - Updated parallel/non-parallel mode docs

---

### 2025-12-30 23:50:00
🐛 **Bug Fixes: File Credential Injection & Mixed Credential Types**

**Fix 1: File Credential Injection Not Working**

- **Root Cause**: Running agent containers had outdated base image without file-handling code
- **Solution**: Rebuild base image with `./scripts/deploy/build-base-image.sh` and restart agents
- **Change**: Added INFO-level logging to `get_assigned_file_credentials()` for production debugging

**Fix 2: TypeError on Mixed Credential Types**

- **Error**: `TypeError: string indices must be integers, not 'str'` at `crud.py:331`
- **Root Cause**: `get_agent_credentials()` returns mixed dict where explicit assignments have dict values but bulk-imported credentials have string values
- **Solution**: Added `isinstance()` check in `crud.py` to handle both types

**Files Modified**:
- `src/backend/credentials.py` - Changed debug logs to info level
- `src/backend/services/agent_service/crud.py` - Handle string vs dict credentials

---

### 2025-12-30 22:20:00
🔐 **Agent-Specific Credential Assignment**

**Feature**: Fine-grained control over which credentials are injected into each agent. Credentials must now be explicitly assigned before injection.

**Problem Solved**: Previously all credentials were auto-injected into all agents. Users had no control over credential scope, leading to security concerns and unnecessary credential exposure.

**Key Changes**:
- No credentials assigned by default (explicit user action required)
- Redis SET storage: `agent:{name}:credentials` for credential IDs
- Filter input for searching credentials by name or service
- Scrollable credential lists with max-height
- "Apply to Agent" button to inject assigned credentials into running agent
- Credential count badge on Credentials tab

**Backend API**:
- `GET /api/agents/{name}/credentials/assignments` - List assigned credential IDs
- `POST /api/agents/{name}/credentials/assign` - Assign a credential
- `DELETE /api/agents/{name}/credentials/assign/{cred_id}` - Unassign
- `POST /api/agents/{name}/credentials/assign/bulk` - Bulk assign
- `POST /api/agents/{name}/credentials/apply` - Inject into running agent

**Files Modified**:
- `src/backend/credentials.py` - 7 new methods for assignment management
- `src/backend/models.py` - CredentialAssignRequest, CredentialBulkAssignRequest
- `src/backend/routers/credentials.py` - 5 new endpoints, route ordering fix
- `src/backend/services/agent_service/crud.py` - Use assigned credentials only
- `src/backend/routers/agents.py` - Cleanup assignments on agent deletion
- `src/frontend/src/stores/agents.js` - 4 new store actions
- `src/frontend/src/composables/useAgentCredentials.js` - Complete rewrite
- `src/frontend/src/views/AgentDetail.vue` - Filter input, scroll, filtered lists

---

### 2025-12-30 18:30:00
🔀 **Git Conflict Resolution**

**Feature**: Basic GitHub workflow with conflict detection and resolution strategies for pull and sync operations.

**Problem Solved**: Pull/sync operations would fail silently on conflicts. Users had no way to choose how to resolve conflicts (stash changes, force replace, etc.).

**Pull Strategies**:
- `clean` (default): Simple pull with rebase, fails on conflicts
- `stash_reapply`: Stash local changes, pull, reapply stash
- `force_reset`: Hard reset to remote, discard local changes

**Sync Strategies**:
- `normal` (default): Stage, commit, push - fails if remote has changes
- `pull_first`: Pull latest, then stage, commit, push
- `force_push`: Force push, overwriting remote

**UI**: GitConflictModal shows resolution options when 409 conflict detected. Destructive options shown in red with warnings.

**API Changes**:
- `POST /api/agents/{name}/git/pull` accepts `{strategy: "clean"|"stash_reapply"|"force_reset"}`
- `POST /api/agents/{name}/git/sync` accepts `{strategy: "normal"|"pull_first"|"force_push"}`
- Conflict responses return HTTP 409 with `X-Conflict-Type` header

**Files Modified**:
- `docker/base-image/agent_server/routers/git.py` - Pull/sync strategies
- `docker/base-image/agent_server/models.py` - Added GitPullRequest model
- `src/backend/routers/git.py` - Strategy parameters, conflict handling
- `src/backend/services/git_service.py` - Proxy with conflict detection
- `src/backend/db_models.py` - Added conflict_type to GitSyncResult
- `src/frontend/src/stores/agents.js` - Strategy parameters
- `src/frontend/src/composables/useGitSync.js` - Conflict state management
- `src/frontend/src/components/GitConflictModal.vue` - New conflict resolution UI
- `src/frontend/src/views/AgentDetail.vue` - Modal integration

---

### 2025-12-30 15:00:00
📁 **File-Type Credentials**

**Feature**: Inject entire credential files (JSON, YAML, PEM, etc.) into agents at specified paths.

**Problem Solved**: Service account JSON files and other file-based credentials couldn't be injected directly. Users had to break them into individual environment variables.

**Implementation**:
- New credential type: `file` with `file_path` field
- Files stored in Redis: `{content: "...file content..."}`
- Injected at agent creation via `/generated-creds/credential-files/`
- Hot-reload support via agent-server endpoint
- Frontend UI with file upload or paste

**Example - Google Service Account**:
```
Name: GCP Service Account
Type: File (JSON, etc.)
Service: google
File Path: .config/gcloud/application_default_credentials.json
Content: {"type": "service_account", "project_id": "...", ...}
```

**Agent Usage**:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/home/developer/.config/gcloud/application_default_credentials.json"
```

**Files Modified**:
- `src/backend/credentials.py` - Added `file` type, `file_path` field, `get_file_credentials()`
- `src/backend/services/agent_service/crud.py` - Write file credentials at agent creation
- `src/backend/routers/credentials.py` - Include files in hot-reload
- `docker/base-image/startup.sh` - Copy credential files to target paths
- `docker/base-image/agent_server/models.py` - Added `files` field to request model
- `docker/base-image/agent_server/routers/credentials.py` - Write files on hot-reload
- `src/frontend/src/views/Credentials.vue` - UI for file-type credentials
- `docs/memory/feature-flows/credential-injection.md` - Flow 7 documentation

---

### 2025-12-30 13:30:00
🔗 **Dynamic GitHub Templates via MCP**

**Feature**: Create agents from ANY GitHub repository via MCP - not just pre-defined templates.

**Problem Solved**: Previously, MCP `create_agent` only worked with templates pre-defined in `config.py`. Users wanted to create agents from arbitrary GitHub repos on the fly.

**Implementation**:
- `create_agent` tool now accepts `template: "github:owner/repo"` for any repository
- If template is not in pre-defined list, uses system GITHUB_PAT for access
- Repository must be accessible by the configured PAT (public or private with access)

**Example**:
```typescript
create_agent({
  name: "my-custom-agent",
  template: "github:myorg/my-private-agent"
})
```

**Requirements**:
- System GitHub PAT configured in Settings or via GITHUB_PAT env var
- PAT must have `repo` scope and access to target repository

**Files Modified**:
- `src/backend/services/agent_service/crud.py` - Support dynamic GitHub repos
- `src/mcp-server/src/tools/agents.ts` - Updated tool description
- `docs/memory/feature-flows/mcp-orchestration.md` - Added documentation

---

### 2025-12-30 12:00:00
🔄 **GitHub Source Mode - Unidirectional Pull Flow**

**Feature**: Agents can now track a GitHub source branch directly and pull updates on demand.

**Problem Solved**: Users developing agents locally wanted to push to GitHub and have Trinity pull updates, without dealing with bidirectional sync conflicts.

**Implementation**:
- **New Fields**: `source_branch` (default: "main") and `source_mode` (default: true) in agent git config
- **Source Mode**: Agent stays on source branch, pulls only (no working branch created)
- **Pull Button**: Added "Pull" button next to "Sync" in Agent Detail UI

**Flow**:
1. Develop locally → push to GitHub (main branch)
2. Create agent in Trinity from GitHub template
3. Click "Pull" button to fetch latest changes
4. Agent's `content/` folder (gitignored) stores large files separately

**Files Modified**:
- `src/backend/db_models.py` - Added `source_branch`, `source_mode` to AgentGitConfig
- `src/backend/database.py` - Migration and schema update
- `src/backend/db/schedules.py` - Updated create_git_config with new params
- `src/backend/models.py` - Added source_branch/source_mode to AgentConfig
- `src/backend/services/agent_service/crud.py` - Pass env vars to container
- `src/backend/routers/git.py` - Include new fields in /git/config response
- `docker/base-image/startup.sh` - Support GIT_SOURCE_MODE and GIT_SOURCE_BRANCH
- `src/frontend/src/composables/useGitSync.js` - Added pullFromGithub function
- `src/frontend/src/views/AgentDetail.vue` - Added Pull button

**API**:
- `POST /api/agents/{name}/git/pull` - Pull latest from source branch

---

### 2025-12-30 10:30:00
🔗 **Dashboard Permissions Integration**

**Feature**: Visual permission management on Dashboard via edge connections.

**Two Edge Types**:
- **Permission edges** (dashed blue): Show which agents CAN communicate - created by dragging between nodes
- **Collaboration edges** (solid animated): Show actual message flow - created automatically from agent activity

**Edge Creation**:
- Drag from source agent handle → target agent handle
- Immediately calls `POST /api/agents/{source}/permissions/{target}`
- Toast notification: "Permission granted: A → B"

**Edge Deletion**:
- Click to select edge → Press Delete/Backspace key
- Immediately calls `DELETE /api/agents/{source}/permissions/{target}`
- Toast notification: "Permission revoked: A → B"

**Files Modified**:
- `src/frontend/src/stores/network.js` - Added `permissionEdges`, `fetchPermissions()`, `createPermissionEdge()`, `deletePermissionEdge()`
- `src/frontend/src/stores/agents.js` - Added `addAgentPermission()`, `removeAgentPermission()` API methods
- `src/frontend/src/views/Dashboard.vue` - Added `@connect`, `@edges-change` handlers, toast notifications
- `src/frontend/src/components/AgentNode.vue` - Styled handles (blue, hover effects, glow)

**UX**:
- No confirmation dialogs - direct manipulation for fast workflow
- Permission edges show as dashed blue lines with arrow
- Node handles highlight blue on hover with glow effect
- Toast notifications for all permission operations

---

### 2025-12-29 16:45:00
🧹 **Removed DEV_MODE_ENABLED from Codebase**

**Complete Removal**:
- Removed `DEV_MODE_ENABLED` environment variable and all references
- Removed `devModeEnabled` state from frontend auth store
- Removed `dev_mode_enabled` from API response (`/api/auth/mode`)
- Updated all documentation, tests, and config files

**Simplified Auth API**:
- `GET /api/auth/mode` now returns `{email_auth_enabled, setup_completed}`
- `POST /api/token` always available for admin login (no mode gating)
- Token mode: `admin` for password login, `email` for email login

---

### 2025-12-29 16:30:00
🔐 **Login Page Simplification**

**Changes**:
- Removed Google OAuth and Developer Mode options from login page
- Login now offers two methods only:
  1. **Email with code** (primary) - For whitelisted users
  2. **Admin Login** (secondary) - Fixed username 'admin', password only
- Token mode changed from `dev` to `admin` for password-based login
- Audit log action changed from `dev_login` to `admin_login`

**Files Modified**:
- `src/frontend/src/views/Login.vue` - Simplified to email + admin login only
- `src/backend/routers/auth.py` - Updated token mode
- `src/frontend/src/stores/auth.js` - Simplified auth methods

---

### 2025-12-29 15:30:00
🗂️ **File Manager: Hidden Files Toggle + Inline Editing**

**New Features**:
1. **Show Hidden Files Toggle**: Checkbox in header to show/hide dotfiles (persisted to localStorage)
2. **Inline Text File Editing**: Edit button for text files, textarea editor, Save/Cancel buttons
3. **Unsaved Changes Warning**: Confirmation prompt when switching files or canceling with changes

**Backend Changes**:
- `docker/base-image/agent_server/routers/files.py`: Added `show_hidden` query param, `PUT /api/files` endpoint
- `src/backend/services/agent_service/files.py`: Updated `list_agent_files_logic` with `show_hidden`, added `update_agent_file_logic`
- `src/backend/routers/agents.py`: Added `show_hidden` param, `PUT /{agent_name}/files` endpoint

**Frontend Changes**:
- `FileManager.vue`: Hidden toggle, edit state, startEdit/cancelEdit/saveFile methods
- `FilePreview.vue`: Edit mode with textarea, `isEditing` and `editContent` props
- `stores/agents.js`: `listAgentFiles` accepts `showHidden`, new `updateAgentFile` action

**Protection Policy**:
- **Cannot delete**: CLAUDE.md, .trinity, .git, .gitignore, .env, .mcp.json, .mcp.json.template
- **Cannot edit**: .trinity, .git, .gitignore, .env, .mcp.json.template
- **CAN edit**: CLAUDE.md, .mcp.json (users need to modify agent instructions and MCP config)

---

### 2025-12-29 14:15:00
📚 **Feature Flows Audit and Update**

**Verified and Updated**:
- `tasks-tab.md` - Updated line numbers for TasksPanel.vue (264-475, 329-433), AgentDetail.vue (201, 884-885), and added service layer references for queue.py
- `scheduling.md` - Updated API endpoint line numbers to match current schedules.py after refactoring (GET/PUT/DELETE endpoints shifted)
- `execution-queue.md` - Updated chat.py line numbers (106-356) to reflect retry helper addition

**No Changes Needed** (already accurate):
- `agent-lifecycle.md` - Service layer references correct (updated 2025-12-27)
- `agent-terminal.md` - Service layer references correct (updated 2025-12-27)
- `agent-network.md` - Workplan removal noted in revision history
- `testing-agents.md` - Plans router removal noted in revision history

**Index Updated**: `feature-flows.md` now reflects 2025-12-29 audit with summary of changes.

---

### 2025-12-29 13:30:00
🧪 **Add Missing Execution and Queue Tests**

**New Tests Added**: Comprehensive test coverage for task executions and queue management.

**test_executions.py** (new file - 15 tests):
- `TestExecutionsEndpoint` - GET /api/agents/{name}/executions endpoint tests
- `TestExecutionFields` - Verify execution records have required fields
- `TestTaskPersistence` - Tasks saved to DB, manual trigger, duration, cost tracking
- `TestAgentToAgentTask` - X-Source-Agent header and triggered_by='agent'
- `TestExecutionOrdering` - Executions returned in descending time order
- `TestExecutionFiltering` - Filter by status and triggered_by

**test_execution_queue.py** (expanded from 6 to 24 tests):
- `TestQueueStatus` - Queue status fields, agent name, busy state, queued executions
- `TestQueueStatusDuringExecution` - Queue busy during chat execution
- `TestClearQueue` - Clear queue, cleared count, auth, 404 handling
- `TestForceRelease` - Release, was_running, warning message, auth
- `TestQueueAfterOperations` - Queue state after clear/release
- `TestQueueWithParallelTasks` - Verify /task bypasses queue

**Coverage Gaps Addressed**:
1. GET /api/agents/{name}/executions endpoint (was untested)
2. Task persistence to database
3. Agent-to-agent execution via X-Source-Agent header
4. Queue endpoint authentication tests
5. Queue state verification after operations

---

### 2025-12-29 13:00:00
🔧 **Fix Agent Server Connectivity Race Condition**

**Problem**: Test suite showed 7/441 failures due to agent file server connectivity issues. When an agent container starts, the internal HTTP server takes a moment to initialize. Requests made during this window would fail with "All connection attempts failed".

**Root Cause**: No retry logic when communicating with agent containers - single connection failure caused immediate HTTP 500 error.

**Solution**: Added retry logic with exponential backoff for all agent communication:
- File operations (list, download, preview, delete)
- Chat endpoint
- Parallel task endpoint

**Changes**:
- `src/backend/services/agent_service/helpers.py` - Added `agent_http_request()` helper with retry logic
- `src/backend/services/agent_service/files.py` - Uses retry helper, returns 503 for connection failures
- `src/backend/routers/chat.py` - Added `agent_post_with_retry()` for chat/task endpoints

**Retry Logic**:
- 3 attempts with exponential backoff (1s, 2s, 4s)
- Returns 503 "Agent server not ready" for connection failures
- Tests can skip on 503 vs failing on 500

**Impact**: Fixes test_agent_files.py failures (7 tests), improves stability for test_activities.py chat tests.

---

### 2025-12-28 23:15:00
🔧 **Manual Tasks Now Persisted to Database**

**Fix**: Manual tasks triggered via Tasks tab are now saved to database and persist across page reloads.

**Backend Changes**:
- Added `create_task_execution()` method to `db/schedules.py` for manual task creation
- Uses `schedule_id = "__manual__"` as marker for non-scheduled tasks
- Updated `/api/agents/{name}/task` endpoint to save execution records
- Execution status (success/failed), response, cost, context, tool_calls all saved

**Modified Files**:
- `src/backend/db/schedules.py` - Added `create_task_execution()` method
- `src/backend/database.py` - Exposed `create_task_execution()` on Database class
- `src/backend/routers/chat.py` - Updated `/task` endpoint to persist executions

**Flow**:
1. Task submitted → execution record created with status "running"
2. Task completes → execution updated with status "success"/"failed" + metadata
3. Page reload → task appears in history from database

---

### 2025-12-28 22:45:00
✨ **Added Tasks Tab to Agent Detail Page (v2)**

**New Feature**: Tasks tab provides a unified view for all headless agent executions with inline task execution and monitoring.

**Key Capabilities**:
1. **Inline Task Execution**: Submit task → immediately appears as "running" in list → updates in place when done
2. **Lightweight UI**: No modals or notifications - everything happens on the task row itself
3. **Expandable Details**: Click task to expand and see response/error inline
4. **Re-run Tasks**: One-click to re-run any previous task
5. **Queue Status**: Shows busy/idle indicator and queue management options

**UX Flow**:
1. Enter task message in input field
2. Click "Run" or Cmd+Enter
3. Task immediately appears at top of list with yellow "running" status
4. When complete, status changes to green "success" or red "failed"
5. Click to expand and see response, click again to collapse

**New Files**:
- `src/frontend/src/components/TasksPanel.vue` - Lightweight task management panel

**Modified Files**:
- `src/frontend/src/views/AgentDetail.vue` - Added Tasks tab

**Technical Details**:
- Uses `/api/agents/{name}/task` endpoint (parallel mode, no queue blocking)
- Local state for pending tasks merged with server executions
- Real-time queue status polling every 5s
- Cmd+Enter / Ctrl+Enter keyboard shortcut to submit

---

### 2025-12-28 21:50:00
🧪 **Tested Scheduling and Execution Queue Functionality**

**Tested Features**:
- Schedule CRUD operations (create, list, get, update, delete)
- Schedule enable/disable with APScheduler sync
- Manual schedule trigger with execution tracking
- Execution queue status, clear, and force release
- WebSocket broadcast implementation verification

**Results**: All tests PASS

**Key Findings**:
1. **Session State Issue**: Scheduled executions fail with exit code 1 if agent's Claude Code session state is corrupted (e.g., from direct testing in container). Fix: restart agent.
2. **MCP Integration Works**: Scheduled tasks can use Trinity MCP tools (agent-to-agent communication)
3. **Observability Captured**: Executions record cost, context tokens, tool calls

**Execution Test Data**:
- Duration: ~25s
- Cost: ~$0.055
- Context: 3,702 / 200,000 tokens
- Tools used: Bash, Read, mcp__trinity__list_agents

**Note**: Feature flow docs (`scheduling.md`, `execution-queue.md`) have outdated line numbers but architecture is accurate.

---

### 2025-12-28 18:30:00
📚 **Documentation - Delegation Best Practices**

Added comprehensive delegation best practices to the Multi-Agent System Guide, covering the hybrid delegation strategy for Trinity.

**New Documentation** (`docs/MULTI_AGENT_SYSTEM_GUIDE.md`):
- **MCP vs Runtime Sub-Agents**: When to use each delegation type
- **Decision Matrix**: Clear guidance for choosing delegation method
- **Anti-Patterns**: Common mistakes to avoid
- **Architecture Diagram**: Visual overview of delegation layers

**Key Concepts Documented**:
- MCP delegation for cross-agent, audited, persistent work
- Runtime sub-agents (Gemini's `codebase_investigator`, Claude's `--agents`) for ephemeral parallelism
- Don't reinvent Trinity's orchestration inside containers

---

### 2025-12-28 18:15:00
🐛 **Fixed Credential Hot-Reload Not Saving to Redis**

**Problem**: When using the "Hot Reload Credentials" feature in AgentDetail, credentials were pushed to the running agent's `.env` file but were NOT persisted to Redis. This meant:
- Credentials were lost when the agent restarted
- "Reload from Redis" wouldn't include hot-reloaded credentials
- No permanent storage of credentials added via hot-reload

**Root Cause**: The `/api/agents/{name}/credentials/hot-reload` endpoint only pushed credentials to the agent container, skipping Redis storage entirely.

**Solution**: Modified the hot-reload endpoint to:
1. Parse credentials from the text input (unchanged)
2. **NEW**: Save each credential to Redis using `import_credential_with_conflict_resolution()`
3. Push credentials to the running agent (unchanged)

The conflict resolution handles duplicates intelligently:
- Same name + same value → reuse existing credential
- Same name + different value → create with suffix (e.g., `API_KEY_2`)
- New name → create new credential

**API Response Enhancement**: Now includes `saved_to_redis` array showing each credential's status:
```json
{
  "saved_to_redis": [
    {"name": "MY_API_KEY", "status": "created", "original": null},
    {"name": "EXISTING_KEY", "status": "reused", "original": null},
    {"name": "CONFLICT_KEY_2", "status": "renamed", "original": "CONFLICT_KEY"}
  ]
}
```

**Files Changed**:
- `src/backend/routers/credentials.py:617-727` - Added Redis persistence to hot-reload endpoint
- `docs/memory/feature-flows/credential-injection.md` - Updated Flow 3 documentation

**Testing**: Verified hot-reload → Redis → agent restart → reload from Redis works end-to-end.

---

### 2025-12-28 15:30:00
🐛 **Fixed File Manager Page Issues**

**Bug #1: Missing Navigation Menu**
- **Problem**: File Manager page (`/files`) didn't show the top navigation bar
- **Fix**: Added `<NavBar />` component to `FileManager.vue`

**Bug #2: Vue Runtime Compiler Warning**
- **Problem**: Console warning "Component provided template option but runtime compilation is not supported"
- **Cause**: `FileTreeNode.vue` used template strings for icon components which require Vue's runtime compiler
- **Fix**: Converted all icon components to use `h()` render functions instead of template strings

**Files Changed**:
- `src/frontend/src/views/FileManager.vue` - Added NavBar import and usage
- `src/frontend/src/components/file-manager/FileTreeNode.vue` - Render functions for icons

**Note on 404 Preview Errors**: Agents created before 2025-12-27 don't have the `/api/files/preview` endpoint. To fix, **recreate** the agent (not just restart). This applies to all agents created before the File Manager feature was implemented.

---

### 2025-12-28 15:00:00
🚀 **Multi-Runtime Support - Gemini CLI Integration**

Added support for Google's Gemini CLI as an alternative agent runtime, enabling cost optimization and 1M token context windows.

**New Features**:
- **Runtime Adapter Pattern**: Abstract interface for swapping execution engines
- **Gemini CLI Support**: Full integration with Google's free-tier AI
- **Per-Agent Runtime Selection**: Choose Claude Code or Gemini CLI per agent
- **Template Configuration**: New `runtime:` field in template.yaml

**Key Benefits**:
- **Cost Savings**: Gemini free tier (60 req/min, 1K/day)
- **5x Context Window**: 1M tokens vs 200K for Claude
- **Provider Flexibility**: Mix runtimes based on task complexity

**Files Added**:
- `docker/base-image/agent_server/services/runtime_adapter.py` - Abstract interface
- `docker/base-image/agent_server/services/gemini_runtime.py` - Gemini implementation
- `config/agent-templates/test-gemini/` - Test template
- `docs/GEMINI_SUPPORT.md` - User guide

**Files Modified**:
- `docker/base-image/Dockerfile` - Added Gemini CLI installation
- `docker/base-image/agent_server/services/claude_code.py` - Wrapped in ClaudeCodeRuntime
- `docker/base-image/agent_server/state.py` - Runtime-aware availability checks
- `docker/base-image/agent_server/routers/chat.py` - Uses runtime adapter
- `src/backend/models.py` - Added runtime fields to AgentConfig
- `src/backend/routers/agents.py` - Runtime env var injection
- `docker-compose.yml` - GOOGLE_API_KEY support

**Documentation Updated**:
- `README.md` - Multi-runtime feature mention
- `docs/DEPLOYMENT.md` - GOOGLE_API_KEY instructions
- `docs/TRINITY_COMPATIBLE_AGENT_GUIDE.md` - Runtime Options section

**Backward Compatibility**: ✅ All existing agents continue using Claude Code by default.

---

### 2025-12-28 12:28:00
⚡ **Fixed Terminal Thread Pool Exhaustion (v2)**

**Problem**: App became unresponsive after opening multiple web terminals. Navigation would hang, API calls would timeout, and audit logging would fail.

**Root Cause**: Terminal implementation used a tight polling loop with `run_in_executor`:
- 5ms `select()` timeout → 200 thread pool calls/second per terminal
- Default thread pool has only 18 workers
- Multiple terminals saturated the pool, blocking all async operations

**Solution (Final)**: Use proper asyncio socket coroutines:
```python
# Correct approach - proper async coroutines
data = await loop.sock_recv(docker_socket, 16384)
await loop.sock_sendall(docker_socket, message.encode())
```

**Why not `add_reader`?** First attempt used `loop.add_reader()` with callback + Event signaling. This was overly complex and caused slow terminal response. The `sock_recv()`/`sock_sendall()` approach is simpler and faster - they are true coroutines that integrate naturally with async/await.

**Files Changed**:
- `src/backend/services/agent_service/terminal.py:221-280` - asyncio socket coroutines
- `src/backend/routers/system_agent.py:491-550` - Same for System Agent

**Investigation**: `docs/investigations/terminal-hanging-investigation.md`

| Metric | Before | After |
|--------|--------|-------|
| Thread pool calls/sec | 200+ per terminal | 0 |
| Max concurrent terminals | ~2-3 | Unlimited |
| Latency | 5ms polling | Near-instant |

---

### 2025-12-27 22:45:00
🐛 **Fixed Two Critical Bugs**

**Bug #1: Terminal Session Loss on Tab Switch**
- **Problem**: When switching from Terminal tab to another tab, the WebSocket connection was destroyed (using `v-if`), causing session loss and "session limit reached" errors when returning
- **Fix**: Changed `v-if="activeTab === 'terminal'"` to `v-show` in `AgentDetail.vue` (line 357) to keep the terminal component mounted
- **Result**: Terminal session persists when switching between tabs

**Bug #2: MCP Agent Import Only Copied CLAUDE.md**
- **Problem**: When deploying a local agent via MCP `deploy_local_agent` tool, only hardcoded files (CLAUDE.md, .claude/, README.md, resources/, scripts/, memory/) were copied
- **Root cause**: `startup.sh` had an explicit list of files instead of copying all template files
- **Fix**: Updated `startup.sh` to copy ALL files from `/template` (including `template.yaml` - required Trinity file)
- **Also added**: `.trinity-initialized` marker to prevent re-copying on container restart

**Files Changed**:
- `src/frontend/src/views/AgentDetail.vue` - Line 357: `v-if` → `v-show` for terminal tab
- `docker/base-image/startup.sh` - Lines 113-142: Replaced hardcoded file list with generic copy

**Note**: Base image rebuilt. New agents will get all files from templates. Existing agents unaffected.

---

### 2025-12-27 21:30:00
✅ **Implemented File Manager Page (Req 12.2)**

Added a dedicated File Manager page with two-panel layout for browsing and managing agent workspace files.

**New Files**:
- `src/frontend/src/views/FileManager.vue` - Main page with agent selector, file tree, preview panel
- `src/frontend/src/components/file-manager/FileTreeNode.vue` - Recursive tree component with icons
- `src/frontend/src/components/file-manager/FilePreview.vue` - Multi-format preview (image, video, audio, text, PDF)

**Backend Changes**:
- `docker/base-image/agent_server/routers/files.py` - DELETE endpoint, preview endpoint with MIME detection
- `src/backend/services/agent_service/files.py` - Proxy functions for delete and preview
- `src/backend/routers/agents.py` - New routes: DELETE `/{name}/files`, GET `/{name}/files/preview`

**Frontend Changes**:
- `src/frontend/src/stores/agents.js` - `deleteAgentFile()`, `getFilePreviewBlob()` methods
- `src/frontend/src/router/index.js` - `/files` route
- `src/frontend/src/components/NavBar.vue` - "Files" navigation link

**Features**:
- Agent selector dropdown with localStorage persistence
- Collapsible file tree with search/filter
- File preview: images, video, audio, text/code, PDF
- Delete with confirmation modal
- Protected file warnings (CLAUDE.md, .trinity/, .git/, .env, etc.)
- Inline notification system

**Note**: Existing agents need recreation (not restart) to get new preview/delete endpoints.

---

### 2025-12-27 18:00:00
✅ **Implemented Content Folder Convention (Req 12.1)**

Implemented the content folder convention for managing large generated assets (videos, audio, images, exports) that should NOT be synced to GitHub.

**Changes**:
- `docker/base-image/startup.sh` - Creates `content/{videos,audio,images,exports}` directories on startup
- `docker/base-image/startup.sh` - Adds `content/` to `.gitignore` automatically
- `docs/TRINITY_COMPATIBLE_AGENT_GUIDE.md` - Added Content Folder Convention section with usage examples

**How it works**:
- All agents now get a `content/` directory at `/home/developer/content/`
- Files in `content/` persist across container restarts (same Docker volume)
- Files in `content/` are NOT synced to GitHub (added to `.gitignore`)
- Standard subdirectories: `videos/`, `audio/`, `images/`, `exports/`

**Testing**:
1. Rebuild base image: `./scripts/deploy/build-base-image.sh`
2. Restart any agent
3. Verify `content/` directory exists
4. Verify `.gitignore` contains `content/`

---

### 2025-12-27 17:30:00
📋 **Added Content Management & File Operations Requirements (Phase 11.5)**

Added comprehensive requirements for managing large generated assets (videos, audio, exports) in agent workspaces.

**Requirement 12.1: Content Folder Convention**
- `content/` directory auto-created and gitignored by default
- Prevents large files from bloating Git repositories
- Same persistent volume - survives container restarts
- Convention documented for template authors

**Requirement 12.2: File Manager Page**
- Dedicated `/files` route with agent selector dropdown
- Two-panel layout: tree (left) + preview (right)
- Preview support: images, video, audio, text/code, PDF
- Delete file/folder with confirmation
- Create new folders
- Protected file warnings (CLAUDE.md, .trinity/, etc.)

**Files Changed**:
- `docs/memory/requirements.md` - Added Section 12 (Content Management)
- `docs/memory/roadmap.md` - Added Phase 11.5

---

### 2025-12-27 15:45:00
🔧 **Refactored AgentDetail.vue (2,193 → 1,386 lines)**

Major refactoring of `views/AgentDetail.vue` using Vue 3 Composition API composables. Extracted 12 domain-specific composables to improve maintainability and reusability.

**Before**: Single 2,193-line component with all business logic inline
**After**: 1,386-line component + 12 composables (~1,000 lines total)

**New Composables Structure** (`composables/`):
| Module | Lines | Purpose |
|--------|-------|---------|
| useNotification.js | 20 | Toast notification management |
| useFormatters.js | 110 | Shared formatting utilities |
| useAgentLifecycle.js | 65 | Start/stop/delete operations |
| useAgentStats.js | 55 | Container stats polling |
| useAgentLogs.js | 65 | Log fetching with auto-refresh |
| useAgentTerminal.js | 45 | Terminal fullscreen/keyboard |
| useAgentCredentials.js | 70 | Credential loading & hot reload |
| useAgentSharing.js | 60 | Agent sharing with users |
| useAgentPermissions.js | 80 | Agent-to-agent permissions |
| useGitSync.js | 90 | Git status and sync operations |
| useFileBrowser.js | 95 | File tree loading/download |
| useAgentSettings.js | 70 | API key and model settings |
| useSessionActivity.js | 100 | Session info and activity polling |

**Benefits**:
- Each composable handles single concern with proper cleanup
- Composables can be reused in other components
- Better testability with isolated logic
- ~37% reduction in main component size

---

### 2025-12-27 12:15:00
📝 **Updated Feature Flow Documentation for Service Layer Refactoring**

Updated all feature flows affected by the agents.py refactoring to reflect new file paths and module locations.

**Updated Flows** (8 documents):
- `agent-lifecycle.md` - References to lifecycle.py, crud.py, helpers.py
- `agent-terminal.md` - References to terminal.py, api_key.py
- `agent-permissions.md` - References to permissions.py
- `agent-shared-folders.md` - References to folders.py, helpers.py
- `file-browser.md` - References to files.py
- `agent-custom-metrics.md` - References to metrics.py
- `execution-queue.md` - References to queue.py
- `local-agent-deploy.md` - References to deploy.py

**Each Updated Flow Includes**:
- "Updated 2025-12-27" note at top explaining refactoring
- Architecture table showing Router vs Service layer split
- Correct file paths and line numbers
- Revision history entry

**Index Updated**:
- `feature-flows.md` - Added refactoring summary and updated all affected flow entries

---

### 2025-12-27 10:30:00
🔧 **Refactored agents.py Router (2928 → 785 lines)**

Major non-breaking refactoring of `routers/agents.py` to improve maintainability. Business logic extracted to dedicated service modules while preserving all API signatures and external interfaces.

**Before**: Single 2,928-line file handling 25+ endpoints and 15 distinct concerns
**After**: 785-line thin router + 12 focused service modules (~2,735 lines total)

**New Service Module Structure** (`services/agent_service/`):
| Module | Lines | Purpose |
|--------|-------|---------|
| helpers.py | 233 | Shared utilities (get_accessible_agents, versioning) |
| lifecycle.py | 251 | Agent start/stop, Trinity injection |
| crud.py | 447 | Agent creation logic |
| deploy.py | 306 | Local agent deployment via MCP |
| terminal.py | 345 | WebSocket PTY terminal handling |
| permissions.py | 197 | Agent-to-agent permissions |
| folders.py | 231 | Shared folder configuration |
| files.py | 137 | File browser proxy |
| queue.py | 124 | Execution queue operations |
| metrics.py | 92 | Custom metrics proxy |
| stats.py | 162 | Container/context statistics |
| api_key.py | 97 | API key settings |

**Preserved Interfaces** (no changes needed in consuming modules):
- `main.py`: `router`, `set_websocket_manager`, `inject_trinity_meta_prompt`
- `systems.py`: `create_agent_internal`, `get_accessible_agents`, `start_agent_internal`
- `activities.py`: `get_accessible_agents`
- `system_service.py`: `start_agent_internal`

**Testing**:
- All 24 agent lifecycle tests pass
- All 56 permissions/folders/api_key tests pass
- All systems integration tests pass

**Files Changed**:
- Backend: `routers/agents.py` - Refactored to thin wrapper (2928 → 785 lines)
- Backend: `services/agent_service/__init__.py` - New module exports
- Backend: `services/agent_service/*.py` - 12 new focused modules

---

### 2025-12-26 18:30:00
🐛 **Fixed Email Whitelist 404 Error**

Fixed email whitelist endpoints returning 404 due to FastAPI route matching order issue.

**Root Cause**: The generic `GET /api/settings/{key}` catch-all route was defined BEFORE the specific `GET /api/settings/email-whitelist` route in settings.py. FastAPI matches routes in order, so it was hitting the generic route and treating "email-whitelist" as a setting key, returning "Setting 'email-whitelist' not found" instead of the actual whitelist data.

**Solution**:
- Reordered routes in `settings.py` - moved email-whitelist routes (lines 544-658) BEFORE the generic `/{key}` catch-all route (line 660+)
- Now FastAPI correctly matches the specific route first
- Email whitelist table now loads and displays whitelisted emails

**Files Changed**:
- Backend: `routers/settings.py` - Reordered routes (email-whitelist section moved from line 823 to line 544)

**Testing**:
1. Navigate to Settings page
2. Scroll to Email Whitelist section
3. Verify table loads and shows any whitelisted emails
4. Add a new email - should show "already whitelisted" if duplicate or add successfully
5. Remove button should work

---

### 2025-12-26 18:15:00
🐛 **Fixed Agents Page Render Error**

Fixed critical bug preventing Agents page from loading. Agents were not displaying due to missing function references from deleted Task DAG system.

**Root Cause**: Task DAG system (Req 9.8) was removed on 2025-12-23, but Agents.vue template still referenced deleted functions `hasActivePlan()`, `getTaskProgress()`, and `getCurrentTask()` at lines 93-101. This caused Vue render error: "Property 'hasActivePlan' was accessed during render but is not defined on instance."

**Solution**:
- Removed obsolete task progress section from Agents.vue template (lines 92-101)
- Removed unused `ClipboardDocumentCheckIcon` import
- Agents page now renders correctly without task progress display

**Files Changed**:
- Frontend: `views/Agents.vue:92-101` - Removed task progress section
- Frontend: `views/Agents.vue:160` - Removed unused icon import

**Testing**:
1. Navigate to /agents page
2. Verify agents list displays correctly
3. Verify no console errors
4. Verify agent cards show name, status, activity state, and context progress (but not task progress)

---

### 2025-12-26 18:00:00
🐛 **Fixed GitHub Initialization UI Timeout**

Fixed UI stuck in "Initializing..." state even after successful repository creation.

**Root Cause**: Git initialization can take 30-60 seconds for agents with large `.claude/` directories, but the frontend axios request had no explicit timeout (defaulted to browser's 60s limit). In some cases, the request would timeout before backend completed, leaving modal stuck.

**Solution**:
- Added explicit 120-second timeout to `initializeGitHub()` axios request
- Added user feedback in modal: "This may take 10-60 seconds depending on the size of your agent's files"
- Added console logging for debugging initialization flow
- Logs now show: Starting → Success → Reloading status → Closing modal

**Files Changed**:
- Frontend: `stores/agents.js:366` - Added `timeout: 120000`
- Frontend: `components/GitPanel.vue:132-134` - Added timing note
- Frontend: `components/GitPanel.vue:356-383` - Added console logging

**Testing**:
1. Initialize git for agent with large `.claude/` directory (100+ MB)
2. Modal should show "Initializing..." with spinner
3. Wait up to 60 seconds
4. Modal should close automatically after success
5. Git tab should display repository info
6. Check browser console for initialization logs

---

### 2025-12-26 17:45:00
🐛 **Fixed GitHub Repository Initialization - Four Issues**

Fixed four critical issues preventing GitHub repository initialization from working correctly:

**Issue 1: ImportError causing 500 status**
- **Root Cause**: The git router was importing `execute_command_in_container` from `services.docker_service`, but this function didn't exist
- **Solution**: Added the missing function to `docker_service.py` (lines 122-155)
- **Files**: `services/docker_service.py`

**Issue 2: Workspace directory not found**
- **Root Cause**: Git commands assumed `/home/developer/workspace` always exists, but some agents (test agents, agents created without templates) don't have this directory
- **Solution**: Added workspace detection and automatic creation:
  - Check if workspace directory exists before git operations
  - Create directory if missing
  - Use detected directory path for all git commands
  - Log which directory is being used for debugging
- **Files**: `routers/git.py:428-454` (workspace detection), `482, 505` (use detected path)

**Issue 3: Orphaned database records**
- **Root Cause**: If initialization partially failed (repo created but git init failed), database record was created but agent had no `.git` directory, causing "already configured" error but UI showing nothing
- **Solution**: Added verification and cleanup:
  - Before rejecting re-initialization, verify `.git` directory actually exists in container
  - If database record exists but git not initialized, auto-cleanup orphaned record
  - Verify git initialization succeeded before creating database record
  - Added `git rev-parse --git-dir` check before database insert
- **Files**: `routers/git.py:322-342` (orphaned record cleanup), `512-525` (verification before DB insert)

**Issue 4: Empty repository - no agent files pushed** ⚠️ **CRITICAL**
- **Root Cause**: Git was initialized in empty `/home/developer/workspace/` directory, but agent's actual files (CLAUDE.md, .claude/, .trinity/, .mcp.json, etc.) live in `/home/developer/`. Result: Empty GitHub repository with no agent content!
- **Solution**: Intelligent directory detection:
  - Check if `/home/developer/workspace/` exists AND has content → use workspace
  - Otherwise → use `/home/developer/` (where agent files actually are)
  - Create `.gitignore` to exclude system files (.bash_logout, .bashrc, .cache/, .ssh/, etc.)
  - Keep important agent files (CLAUDE.md, .claude/, .trinity/, .mcp.json, .claude.json)
  - Check both locations when verifying existing git configuration
- **Files**: `routers/git.py:442-476` (smart directory detection + .gitignore), `326-330` (check both locations)
- **Impact**: Agent files now correctly pushed to GitHub! Repository will contain the agent's configuration, prompts, and working files.

**Result**:
- Repository creation now works for both personal and organization accounts ✅
- Supports both fine-grained and classic PATs ✅
- Works with agents that have or don't have workspace directories ✅
- Handles partial failures gracefully with automatic cleanup ✅
- UI correctly displays git status after successful initialization ✅
- **Agent files are pushed to GitHub repository** ✅ (CRITICAL FIX!)

**Testing**:
1. Navigate to agent detail → Git tab
2. Click "Initialize GitHub Sync"
3. Enter repository owner (personal or organization) and name
4. Wait for initialization to complete (~10-30 seconds)
5. **Verify repository on GitHub has agent files:**
   - Visit `https://github.com/{owner}/{repo}`
   - Check files exist: CLAUDE.md, .claude/, .trinity/, .mcp.json, etc.
   - Verify `main` branch has initial commit
   - Verify `trinity/{agent}/{id}` working branch exists
6. Verify UI shows git sync status with remote URL and branch
7. Check logs show: "Using home directory (agent's files are here): /home/developer" or "Using workspace directory with existing content"
8. Check logs show: "Git initialization verified successfully"

---

### 2025-12-26 17:00:00
🔧 **Fixed GitPanel Vue Render Error**

Fixed "Cannot read properties of null (reading 'remote_url')" error when navigating to the Git tab on agent detail pages.

**Root Cause**: GitPanel template at line 182 had `<div v-else>` which would show the Git Status Display section when git was enabled and agent was running, BUT it didn't check if `gitStatus` object had complete data. When the API call returned, `gitStatus` could be temporarily set to an incomplete object, causing Vue to try rendering `gitStatus.remote_url` on line 191 before the property existed.

**Solution**: Changed line 182 from `<div v-else>` to `<div v-else-if="gitStatus?.remote_url && gitStatus?.branch">` to ensure the Git Status Display only renders when `gitStatus` has complete data.

**Files Changed**:
- Frontend: `components/GitPanel.vue:182` - Added guard for gitStatus properties

**Testing**:
1. Navigate to agent detail page
2. Click Git tab
3. Verify no console errors
4. Verify git status displays correctly (or "not enabled" message)

---

### 2025-12-26 16:30:00
🔧 **Fixed Fine-Grained PAT Support**

Fixed GitHub Personal Access Token validation to properly support fine-grained PATs (starting with `github_pat_`).

**Issue**: Fine-grained PATs were incorrectly showing "Missing repo scope" because they don't expose scopes via `X-OAuth-Scopes` header like classic PATs.

**Solution**:
- Backend now detects token type (fine-grained vs classic)
- Fine-grained PATs: Tests actual permissions by calling `GET /user/repos`
- Classic PATs: Checks `X-OAuth-Scopes` header for `repo` or `public_repo`
- Returns `token_type` and `has_repo_access` fields
- Frontend displays appropriate messages:
  - Fine-grained: "✓ Fine-grained PAT with repository permissions" or "⚠️ Missing repository permissions (need Administration + Contents)"
  - Classic: "✓ Has repo scope" or "⚠️ Missing repo scope"

**Files Changed**:
- Backend: `routers/settings.py` - Updated `test_github_pat` endpoint
- Frontend: `views/Settings.vue` - Updated test result display logic

---

### 2025-12-26 16:00:00
🔀 **GitHub Repository Initialization**

Added ability to initialize GitHub synchronization for any agent, pushing it to a new or existing GitHub repository with one click.

**Features**:
- **Settings Configuration**: GitHub Personal Access Token (PAT) management
  - Admin can configure GitHub PAT in Settings page
  - Test button validates token and checks scopes
  - Stored securely in system settings
- **One-Click Initialization**: Initialize GitHub sync from Agent Git tab
  - Modal form for repository owner and name
  - Option to create repository automatically
  - Private/public repository selection
  - Repository description (optional)
- **Automated Setup**: Backend handles complete initialization
  - Creates GitHub repository via GitHub API (if requested)
  - Initializes git in agent workspace
  - Commits current agent state
  - Pushes to main branch
  - Creates working branch (trinity/{agent-name}/{instance-id})
  - Stores configuration in database
- **MCP Tool**: `initialize_github_sync` for programmatic access

**Backend Changes**:
- **API Endpoints**:
  - `GET /api/settings/api-keys` - Returns both Anthropic and GitHub PAT status
  - `PUT /api/settings/api-keys/github` - Save GitHub PAT
  - `DELETE /api/settings/api-keys/github` - Delete GitHub PAT
  - `POST /api/settings/api-keys/github/test` - Test GitHub PAT validity
  - `POST /api/agents/{name}/git/initialize` - Initialize GitHub sync for agent
- **Helper Functions**:
  - `get_github_pat()` in `routers/settings.py` - Get GitHub PAT from settings or env
- **GitHub Integration**:
  - Repository creation via GitHub REST API
  - Git commands executed in agent container via Docker exec
  - PAT embedded in git remote URL for authentication

**Frontend Changes**:
- **Settings Page** (`src/frontend/src/views/Settings.vue`):
  - GitHub PAT input field with show/hide toggle
  - Test and Save buttons
  - Status indicators (configured/not configured, source)
  - Scope validation (checks for repo access)
  - Link to GitHub token settings
- **Git Tab** (`src/frontend/src/components/GitPanel.vue`):
  - "Initialize GitHub Sync" button when git not enabled
  - Modal form with repository configuration
  - Real-time feedback and error handling
  - Success triggers git status reload
- **Agents Store** (`src/frontend/src/stores/agents.js`):
  - `initializeGitHub(name, config)` method

**MCP Server Changes**:
- **New Tool**: `initialize_github_sync` (`src/mcp-server/src/tools/agents.ts`)
  - Parameters: agent_name, repo_owner, repo_name, create_repo, private, description
  - Enables agents to programmatically initialize GitHub sync

**Required Permissions**:
- GitHub PAT must have `repo` scope (full control of private repositories)
- Or `public_repo` scope (for public repositories only)

**User Workflow**:
1. Admin configures GitHub PAT in Settings → API Keys
2. User opens agent → Git tab
3. Clicks "Initialize GitHub Sync"
4. Enters repository owner and name
5. Selects options (create repo, private/public)
6. Click Initialize
7. Agent workspace is pushed to GitHub and sync is enabled

**Files Changed**:
- Backend: `routers/settings.py`, `routers/git.py` (new initialize endpoint)
- Frontend: `views/Settings.vue`, `components/GitPanel.vue`, `stores/agents.js`
- MCP Server: `src/tools/agents.ts`, `server.ts`

---

### 2025-12-26 14:00:00
📧 **Email-Based Authentication** (Phase 12.4)

Implemented passwordless email authentication as the new default login method. Users enter email → receive 6-digit code → login. Includes admin-managed whitelist and automatic whitelist addition when agents are shared.

**Features**:
- **Passwordless Login**: 2-step email verification (request code → verify code)
- **Email Whitelist**: Admin-managed whitelist controls who can login
- **Auto-Whitelist**: Sharing an agent automatically adds recipient to whitelist
- **Security**: Rate limiting (3 requests/10 min), email enumeration prevention, audit logging
- **Email Providers**: Support for console, SMTP, SendGrid, Resend

**Backend Changes**:
- **Database**: New tables `email_whitelist` and `email_login_codes`
- **API Endpoints**:
  - `POST /api/auth/email/request` - Request verification code
  - `POST /api/auth/email/verify` - Verify code and login
  - `GET /api/settings/email-whitelist` - List whitelist (admin)
  - `POST /api/settings/email-whitelist` - Add email (admin)
  - `DELETE /api/settings/email-whitelist/{email}` - Remove email (admin)
- **Operations**: `src/backend/db/email_auth.py` - EmailAuthOperations class
- **Models**: `src/backend/db_models.py` - EmailWhitelistEntry, EmailLoginRequest, etc.
- **Config**: `EMAIL_AUTH_ENABLED=true` by default, can override via system_settings
- **Integration**: `src/backend/routers/sharing.py` - Auto-whitelist on agent sharing

**Frontend Changes**:
- **Login Page**: `src/frontend/src/views/Login.vue` - Email auth shown by default
  - Step 1: Enter email, request code
  - Step 2: Enter 6-digit code with countdown timer
  - Fallback buttons for Dev mode and Auth0 if enabled
- **Auth Store**: `src/frontend/src/stores/auth.js` - Added email auth methods
  - `requestEmailCode(email)` - Request verification code
  - `verifyEmailCode(email, code)` - Verify and login
  - `emailAuthEnabled` state tracking
- **Settings Page**: `src/frontend/src/views/Settings.vue` - Email Whitelist section
  - Table view with email, source, added date
  - Add/remove emails
  - Source badges: "Manual" vs "Auto (Agent Sharing)"

**Security Features**:
- Rate limiting: 3 code requests per 10 minutes per email
- Code expiration: 10-minute lifetime
- Single-use codes: Marked as verified after use
- Email enumeration prevention: Generic success messages
- Audit logging: Complete event trail for all auth operations

**Configuration**:
- Environment variable: `EMAIL_AUTH_ENABLED=true` (default)
- Runtime toggle: System settings key `email_auth_enabled`
- Detection endpoint: `GET /api/auth/mode` includes `email_auth_enabled` flag

**Documentation**:
- Feature flow: `docs/memory/feature-flows/email-authentication.md` (1200+ lines)
- Comprehensive documentation of architecture, security, testing

**User Experience**:
- Default login: Email with verification code
- Seamless onboarding: Sharing agent auto-whitelists recipient
- Alternative methods: Dev mode and Auth0 still available if configured

**Use Cases**:
- Share agents with external collaborators via email
- No need to pre-configure Auth0 or manage OAuth
- Simple onboarding for new users
- Admin controls access via whitelist

**Files Changed**:
- Backend: 11 files (database, routers, config, models, operations)
- Frontend: 3 files (Login.vue, Settings.vue, auth.js)
- Documentation: 1 feature flow (1200+ lines)

---

### 2025-12-26 12:15:00
🔐 **Automatic Logout on Session Expiration**

Fixed UX issue where expired JWT tokens resulted in empty interface instead of redirecting to login.

**Problem**:
- When JWT token expired, API calls failed with 401
- Frontend showed empty interface (no agents, no data)
- User remained on dashboard with broken state
- Had to manually navigate to /login

**Solution**:
- Added axios response interceptor in `main.js`
- Automatically detects 401 responses (expired/invalid token)
- Clears auth state and redirects to login page
- Console logs: "🔐 Session expired - redirecting to login"

**Changes**:
- `src/frontend/src/main.js`: Added axios interceptor for 401 handling

**User Experience**:
- Token expires → automatic redirect to login screen
- Clear indication session has ended
- No more confusing empty interface

**Combined with previous fix**: 7-day token lifetime + automatic logout = smooth auth experience.

---

### 2025-12-26 12:00:00
⏱️ **Extended JWT Token Lifetime**

Increased JWT token expiration from 30 minutes to 7 days to reduce re-login frequency.

**Changes**:
- `src/backend/config.py`: Changed `ACCESS_TOKEN_EXPIRE_MINUTES` from 30 to 10080 (7 days)

**Impact**:
- Users stay logged in for 7 days instead of 30 minutes
- No more frequent re-logins when walking away from browser
- Still need to re-login after backend redeployments (expected behavior)

**Note**: For even longer sessions, increase `ACCESS_TOKEN_EXPIRE_MINUTES` in config.py (e.g., 43200 = 30 days).

---

### 2025-12-26 11:30:00
📊 **OpenTelemetry Enabled by Default**

Changed OTEL_ENABLED default from `0` (disabled) to `1` (enabled). New Trinity installations will now have metrics export enabled out of the box.

**Changes**:
- `.env.example`: Default `OTEL_ENABLED=1`
- `src/backend/routers/agents.py`: Default to enabled
- `src/backend/routers/observability.py`: Default to enabled
- `src/backend/routers/ops.py`: Default to enabled
- `src/backend/services/system_agent_service.py`: Default to enabled
- `docs/memory/feature-flows/opentelemetry-integration.md`: Updated documentation

**Rationale**: OTel provides valuable cost and productivity insights. Having it on by default ensures users get observability from the start. Set `OTEL_ENABLED=0` to disable.

---

### 2025-12-26 10:00:00
🔐 **Per-Agent API Key Control**

Added ability for agents to use either platform API key or user's own Claude subscription via terminal authentication.

**Changes**:
- Database: Added `use_platform_api_key` column to `agent_ownership` table (default: true)
- Backend: Container recreation on start if API key setting changed
- Backend: API endpoints `GET/PUT /api/agents/{name}/api-key-setting`
- Frontend: Radio toggle in Terminal tab when agent is stopped
- Agents can now run `claude login` in terminal to use personal subscription

**User Flow**:
1. Create agent (uses platform key by default)
2. Go to Terminal tab when agent is stopped
3. Select "Authenticate in Terminal" option
4. Start agent → run `claude login` to authenticate
5. Agent now uses user's subscription instead of platform key

**Files changed**:
- `src/backend/database.py` - Migration for new column
- `src/backend/db/agents.py` - get/set methods for setting
- `src/backend/routers/agents.py` - API endpoints, container recreation logic
- `src/frontend/src/stores/agents.js` - Store methods
- `src/frontend/src/views/AgentDetail.vue` - UI toggle

---

### 2025-12-25 19:30:00
✨ **Agent Terminal: Replaced Chat with Terminal**

Replaced the Chat tab on Agent Detail page with a full Web Terminal (xterm.js), matching System Agent functionality.

**Changes**:
- Created `AgentTerminal.vue` component (generalized from SystemAgentTerminal)
- Added WebSocket terminal endpoint at `/api/agents/{name}/terminal`
- Replaced Chat tab with Terminal tab on Agent Detail page
- Terminal auto-connects when agent is running
- Fullscreen support with ESC key to exit
- Mode toggle: Claude Code (default) or Bash shell
- Access control: User must have access to agent (owner, shared, or admin)
- Session limit: 1 terminal per user per agent (prevents resource exhaustion)
- Audit logging for terminal sessions with duration tracking

**Files changed**:
- `src/frontend/src/components/AgentTerminal.vue` - New terminal component
- `src/frontend/src/views/AgentDetail.vue` - Terminal tab replaces Chat tab
- `src/backend/routers/agents.py` - WebSocket terminal endpoint
- `docs/memory/feature-flows/agent-terminal.md` - New feature flow
- `docs/memory/feature-flows.md` - Updated index, deprecated agent-chat

**Deprecation**: Agent Chat feature (`agent-chat.md`) is deprecated in favor of direct terminal access.

---

### 2025-12-25 18:00:00
✨ **Web Terminal: Embedded with Fullscreen**

Refactored Web Terminal from modal to embedded panel on System Agent page with fullscreen support.

**Changes**:
- Terminal now embedded directly on System Agent page (replaces Operations Console chat)
- Auto-connects when page loads (if agent running and user is admin)
- Added fullscreen toggle button in terminal header
- ESC key exits fullscreen mode
- Terminal refits automatically on fullscreen toggle
- Removed Terminal button from header (no longer modal-based)
- Cleaned up all unused chat-related code (marked library, sendMessage, etc.)

**Files changed**:
- `src/frontend/src/views/SystemAgent.vue` - Embedded terminal, fullscreen, removed chat code
- `docs/memory/feature-flows/web-terminal.md` - Updated documentation

---

### 2025-12-25 17:30:00
🐛 **Web Terminal Bug Fixes**

Fixed several issues discovered during local testing of the Web Terminal feature.

**Fixes**:
- Fixed localStorage key mismatch: Changed `trinity_token` to `token` to match auth store
- Fixed user_email extraction: Handle `None` database values with `or` fallback chain
- Added session timeout (5 min) to auto-cleanup stale sessions from failed connections
- Added WebSocket support (`ws: true`) to Vite proxy for `/api` endpoint
- Made `connectionStatusText` reactive using Vue `computed()` instead of static object

**Files changed**:
- `src/frontend/src/components/SystemAgentTerminal.vue` - localStorage key, computed status
- `src/frontend/vite.config.js` - Added `ws: true` to `/api` proxy
- `src/backend/routers/system_agent.py` - Session timeout, user_email fallback

---

### 2025-12-25 10:30:00
✨ **Web Terminal for System Agent (11.5)**

Implemented browser-based interactive terminal for System Agent with full Claude Code TUI support.

**Features**:
- xterm.js terminal emulator in modal (v5.5.0)
- WebSocket PTY forwarding via Docker exec
- Mode toggle: Claude Code or Bash shell
- Terminal resize follows browser window
- Admin-only access (button hidden for non-admins)
- Session limit: 1 terminal per user
- Audit logging for session start/end with duration

**Architecture**:
- Frontend: `SystemAgentTerminal.vue` with xterm.js + addons (fit, web-links)
- Backend: WebSocket endpoint at `WS /api/system-agent/terminal?mode=claude|bash`
- PTY allocation via Docker SDK `exec_create(tty=True)` + `exec_start(socket=True)`
- Bidirectional socket forwarding with `select()` for non-blocking I/O
- `decode_token()` helper for WebSocket authentication

**Files changed**:
- `src/frontend/package.json` - Added @xterm/xterm, @xterm/addon-fit, @xterm/addon-web-links
- `src/frontend/src/components/SystemAgentTerminal.vue` - New terminal component
- `src/frontend/src/views/SystemAgent.vue` - Added Terminal button and modal
- `src/backend/routers/system_agent.py` - Added WebSocket terminal endpoint
- `src/backend/dependencies.py` - Added `decode_token()` helper function

---

### 2025-12-24 12:30:00
❌ **Removed Platform Chroma Vector Store Injection**

Removed all platform-level vector memory injection for development workflow parity.

**Reason**: Local dev should equal production. Platform-injected capabilities create mismatches between local Claude Code development and Trinity deployment. Templates should be self-contained.

**What was removed**:
- `chromadb`, `sentence-transformers`, `chroma-mcp` from base image (~800MB savings)
- Vector store directory creation during Trinity injection
- Chroma MCP config injection into agent .mcp.json
- `vector-memory.md` documentation file from trinity-meta-prompt
- Vector memory section in injected CLAUDE.md
- `vector_memory` status field from Trinity status API
- `VECTOR_STORE_DIR` constant from agent server config

**Alternative**: Templates that need vector memory should include dependencies and configuration themselves. This ensures local development matches production exactly.

**Files changed**:
- `docker/base-image/Dockerfile` - Removed packages and model download
- `docker/base-image/agent_server/config.py` - Removed VECTOR_STORE_DIR
- `docker/base-image/agent_server/models.py` - Removed vector_memory field
- `docker/base-image/agent_server/routers/trinity.py` - Removed injection logic
- `config/trinity-meta-prompt/vector-memory.md` - Deleted
- `config/trinity-meta-prompt/prompt.md` - Removed vector memory references
- `docs/memory/requirements.md` - Updated 10.4, 10.5 to REMOVED
- `docs/memory/feature-flows/vector-memory.md` - Marked as removed
- `docs/memory/roadmap.md` - Updated Phase 10
- `docs/MULTI_AGENT_SYSTEM_GUIDE.md` - Removed vector memory sections
- `docs/TRINITY_COMPATIBLE_AGENT_GUIDE.md` - Removed vector memory sections
- `docs/requirements/CHROMA_MCP_SERVER.md` - Deleted

---

### 2025-12-24 11:30:00
🔧 **deploy_local_agent MCP Tool - Architecture Fix**

Fixed fundamental architecture issue where MCP tool tried to access local filesystem (impossible since MCP server runs remotely).

**Problem**: The `deploy_local_agent` MCP tool was using `fs.existsSync()` and `tar` commands to package a local directory. Since the MCP server runs on the remote Trinity server, it cannot access the calling agent's local filesystem.

**Solution**: Changed the tool to accept a pre-packaged base64 archive from the calling agent.

**New Parameters**:
```typescript
{
  archive: string,                    // Base64-encoded tar.gz (REQUIRED)
  credentials?: Record<string, string>, // Key-value pairs from .env
  name?: string                       // Override agent name
}
```

**Calling Agent Responsibility**:
1. Create tar.gz archive locally: `tar -czf agent.tar.gz --exclude='.git' ...`
2. Base64 encode: `base64 -i agent.tar.gz`
3. Parse .env file for credentials
4. Call `deploy_local_agent` with archive and credentials

**Files Changed**:
- `src/mcp-server/src/tools/agents.ts` - Replaced path-based logic with archive-based
- `docs/memory/feature-flows/local-agent-deploy.md` - Updated architecture and usage docs

**Backend API Unchanged**: `POST /api/agents/deploy-local` still accepts same parameters.
