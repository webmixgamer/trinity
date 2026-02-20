# Feature Flows Index

> **Purpose**: Maps features to detailed vertical slice documentation.
> Each flow documents the complete path from UI → API → Database → Side Effects.

> **Updated (2026-02-19)**: Authenticated Chat Tab (CHAT-001):
> - **New feature flow**: [authenticated-chat-tab.md](feature-flows/authenticated-chat-tab.md) - Simple chat UI in Agent Detail page
> - **Chat tab** added after Tasks in AgentDetail.vue (line 498)
> - **ChatPanel.vue** (363 lines): Session selector dropdown, "New Chat" button, agent not running state
> - **Shared components** created in `components/chat/`: ChatMessages.vue, ChatInput.vue, ChatBubble.vue, ChatLoadingIndicator.vue
> - **PublicChat.vue refactored** to use the same shared components (now 611 lines)
> - Uses `/api/agents/{name}/task` endpoint for Dashboard activity tracking (not `/chat`)
> - Related flows updated: public-agent-links.md (shared components), tasks-tab.md (same `/task` endpoint pattern)
>
> **Updated (2026-02-18 17:50)**: Toggle Size Consistency Fix:
> - **All toggles now use `size="sm"`** across the system for visual consistency
> - **AgentHeader.vue**: RunningStateToggle (line 41), AutonomyToggle (line 68), ReadOnlyToggle (line 77) all changed to `size="sm"`
> - **RunningStateToggle.vue**: Default size changed from 'md' to 'sm' (line 97)
> - **Agents.vue**: ReadOnlyToggle (line 252) no longer has `:show-label="false"` - now shows labels like other toggles
> - Affected flows: agent-lifecycle.md, agents-page-ui-improvements.md, read-only-mode.md, autonomy-toggle-component.md
>
> **Updated (2026-02-18)**: AgentDetail Tab Restructuring:
> - **Logs tab REMOVED**: No longer visible in AgentDetail.vue. Logs still available via API (`GET /api/agents/{name}/logs`) and MCP tool.
> - **Files tab REMOVED**: No longer visible in AgentDetail.vue. Users should use the standalone File Manager page at `/files`.
> - **Terminal tab repositioned**: Now after Git tab (near end of tab list).
> - **Public Links tab CONSOLIDATED**: No longer a separate tab. Public Links now rendered within "Sharing" tab via SharingPanel.vue embedding PublicLinksPanel.vue.
> - **New tab order** (lines 496-525): Tasks, Dashboard*, Schedules, Credentials, Skills, Sharing* (includes Public Links), Permissions*, Git*, **Terminal**, Folders*, Info (* = conditional)
>
> **Updated (2026-02-18)**: Agents Page Enhancements:
> - **ReadOnlyToggle on Agents Page**: `Agents.vue:248-255` - ReadOnlyToggle component added between Running and Autonomy toggles. Only shown for owned agents (not system, not shared). State: `agentReadOnlyStates` (line 378), `readOnlyLoading` (line 377). Functions: `fetchAllReadOnlyStates()` (544-563), `getAgentReadOnlyState()` (540-542), `handleReadOnlyToggle()` (565-594).
> - **Tags Layout Fix**: `Agents.vue:270-288` - Fixed tags breaking tile layout. Tags now in fixed-height container (`h-6 overflow-hidden`, line 271) with individual tag truncation (`max-w-20 truncate`, line 276). Shows up to 3 tags with "+N" overflow indicator.
>
> **Updated (2026-02-18)**: Agent Detail Page Redesign (UI-001):
> - **AgentHeader.vue**: Restructured into 3 rows for cleaner layout:
>   - Row 1 (lines 4-57): Identity (name, badges) + Primary Action (toggle, delete)
>   - Row 2 (lines 59-163): Settings (toggles, tags) on left + Stats (CPU/MEM sparklines, uptime) on right
>   - Row 3 (lines 165-250): Git controls (conditional, only when hasGitSync)
>   - Stats display: Fixed widths (`w-10` for CPU%, `w-14` for MEM bytes, `w-16` for uptime) prevent layout jumping
>   - Network stats removed from display
> - **AgentDetail.vue**: Default tab changed from 'info' to 'tasks' (line 275: `activeTab = ref('tasks')`)
>   - Tab order reordered (lines 504-529): Tasks first, Info moved to end
>   - **Logs tab removed**, **Files tab removed**, Terminal repositioned after Git
>   - Order: Tasks, Dashboard*, Schedules, Credentials, Skills, Sharing*, Permissions*, Git*, Terminal, Folders*, Public Links*, Info
>   - (*) = conditional tabs
> - **TasksPanel.vue**: Tasks tab layout reordered for better UX:
>   - Section order: Stats (lines 49-69) → Task Input (lines 71-101) → Task History (lines 103-315)
>   - Stats section more compact: smaller padding (`px-3 py-2`), smaller text (`text-base`, `text-[10px]`)
>   - Run button now matches textarea height (uses `items-stretch` on container)
>
> **Updated (2026-02-18)**: Agent Tags Bug Fix:
> - **agent-tags.md**: Fixed tag API authentication in AgentDetail.vue - now uses `axios` + `authStore.authHeader` instead of Pinia store wrapper
> - Tag operations (add, remove, load) now work correctly with proper JWT authentication
> - Updated line numbers: `loadTags()` (548-558), `addTag()` (585-598), `removeTag()` (600-611)
>
> **Updated (2026-02-17)**: Agent Tags & System Views (ORG-001 Phase 1-4 COMPLETE):
> - **Phase 1 (Tags)**: Lightweight agent tagging system for organizational grouping
>   - Backend: `db/tags.py` (TagOperations), `routers/tags.py` (5 endpoints)
>   - Frontend: `TagsEditor.vue` component with inline editing and autocomplete
>   - Integration: Tags row in `AgentHeader.vue`, API calls in `AgentDetail.vue`
>   - Database: `agent_tags` table with composite primary key
>   - API: `GET /api/tags`, `GET/PUT/POST/DELETE /api/agents/{name}/tags`, `GET /api/agents?tags=` filtering
> - **Phase 2 (System Views)**: Saved filters that group agents by tags
>   - Backend: `db/system_views.py` (SystemViewOperations), `routers/system_views.py` (5 endpoints)
>   - Frontend: `SystemViewsSidebar.vue` collapsible sidebar, `SystemViewEditor.vue` modal
>   - Store: `systemViews.js` Pinia store with localStorage persistence
>   - Dashboard: Sidebar integration, filter reactivity via `network.js:setFilterTags()`
>   - Database: `system_views` table with owner_id FK, agent_count computed on fetch
>   - API: `GET/POST /api/system-views`, `GET/PUT/DELETE /api/system-views/{id}`
> - **Phase 3 (Polish)**: MCP tools, quick tag filter, bulk operations
>   - MCP: 5 tools in `tools/tags.ts` (list_tags, get_agent_tags, tag_agent, untag_agent, set_agent_tags)
>   - Dashboard: Quick tag filter pills in header with multi-select support
>   - Agents Page: Bulk tag operations (select multiple agents, add/remove tags), tag filter dropdown
> - **Phase 4 (System Manifest Integration)**: Auto-apply tags and System Views on system deployment
>   - Models: `SystemAgentConfig.tags`, `SystemManifest.default_tags`, `SystemManifest.system_view`, `SystemViewConfig`
>   - Service: `configure_tags()` (lines 429-480), `create_system_view()` (lines 483-534) in `system_service.py`
>   - Router: `deploy_system()` steps 10-11 for tag/view creation, response includes `tags_configured`, `system_view_created`
>   - Migration: `scripts/management/migrate_prefixes_to_tags.py` for existing agent prefixes
> - Spec: `docs/requirements/AGENT_SYSTEMS_AND_TAGS.md`
>
> **Updated (2026-02-17)**: Public Client Mode Awareness (PUB-006) + Bottom-Aligned Chat:
> - **public-agent-links.md**: Agents now know when serving public users via `PUBLIC_LINK_MODE_HEADER` constant
> - Header `"### Trinity: Public Link Access Mode"` prepended to all public chat prompts (`db/public_chat.py:17-18,265-266`)
> - Enables agents to adjust behavior for public vs internal users (formal language, limited internal details)
> - **UI: Bottom-aligned messages**: Chat messages now stack from bottom up like iMessage/Slack
> - Flexbox layout with spacer div pushes content to bottom (`PublicChat.vue:191-193`)
> - New `messagesContainer` ref for scroll handling (`PublicChat.vue:334`)
> - File line count: PublicChat.vue now 684 lines
>
> **Updated (2026-02-17)**: Public Chat Session Persistence (PUB-005):
> - **public-agent-links.md**: Multi-turn conversation persistence with database-backed sessions
> - New tables: `public_chat_sessions` (database.py:662-674), `public_chat_messages` (database.py:678-686)
> - New endpoints: `GET /api/public/history/{token}` (public.py:465), `DELETE /api/public/session/{token}` (public.py:541)
> - Updated: `POST /api/public/chat/{token}` (public.py:214) now persists messages and builds context prompt
> - New backend: `db/public_chat.py` - PublicChatOperations class (307 lines) with session/message management
> - Frontend: `loadHistory()` (PublicChat.vue:456), `confirmNewConversation()` (PublicChat.vue:530), "New" button (lines 17-27)
> - Session strategy: Email links use verified email as identifier, anonymous links use localStorage session_id
> - Context injection: Last 10 exchanges formatted as "### Trinity: Public Link Access Mode\n\nPrevious conversation:\nUser:...\nAssistant:...\n\nCurrent message:\nUser:..."
>
> **Updated (2026-02-17)**: Public Chat Header Metadata (PUB-004):
> - **public-agent-links.md**: `GET /api/public/link/{token}` now returns agent metadata
> - New fields: `agent_display_name`, `agent_description`, `is_autonomous`, `is_read_only`
> - Backend fetches display name/description from agent's `/api/template/info` endpoint
> - Backend fetches autonomy/read-only status from `agents_db`
> - PublicChat.vue header (lines 4-46) displays agent name, description, and status badges
> - Status badges: AUTO (amber) if autonomous, READ-ONLY (rose with lock icon) if read-only
> - Model: `PublicLinkInfo` (db_models.py:336-346) extended with 4 new fields
>
> **Updated (2026-02-17)**: Public Chat Agent Introduction (PUB-003):
> - **public-agent-links.md**: New `GET /api/public/intro/{token}` endpoint sends intro prompt to agent via `/api/task`
> - Frontend `fetchIntro()` (PublicChat.vue:406-438) displays agent introduction as first chat message
> - Backend `INTRO_PROMPT` (public.py:300-306) requests 2-paragraph intro
> - Triggered after email verification or on mount if no verification needed
> - UI shows "Getting ready..." spinner during fetch, falls back to generic welcome on error
>
> **Updated (2026-02-17)**: Read-Only Mode (CFG-007):
> - **read-only-mode.md**: New feature flow for code protection via Claude Code PreToolUse hooks
> - Prevents agents from modifying source files (*.py, *.js, CLAUDE.md, etc.) while allowing output directories (content/, output/, reports/)
> - Frontend: `ReadOnlyToggle.vue` component in AgentHeader.vue with rose/red color scheme
> - Backend: `services/agent_service/read_only.py` for hook injection logic
> - Guard script: `config/hooks/read-only-guard.py` - intercepts Write/Edit/NotebookEdit operations
> - Database: `read_only_mode` and `read_only_config` columns in `agent_ownership` table
> - Hooks auto-injected on agent start via `lifecycle.py:243-256`, immediate injection if agent running
> - Files: `~/.trinity/read-only-config.json`, `~/.trinity/hooks/read-only-guard.py`, merged into `~/.claude/settings.local.json`

> **Updated (2026-02-16)**: Credential Leakage Security Fix - Multi-Layer Sanitization:
> - **Agent-Side Sanitization**: New `credential_sanitizer.py` utility in `docker/base-image/agent_server/utils/` sanitizes subprocess output and response text before storing
> - **Backend-Side Sanitization**: New `credential_sanitizer.py` utility in `src/backend/utils/` provides defense-in-depth sanitization before database persistence
> - **Credential Cache Refresh**: Agent refreshes sanitizer cache after credential injection via `refresh_credential_values()` in `routers/credentials.py`
> - **Updated flows**: **execution-queue.md** (backend sanitization), **parallel-headless-execution.md** (agent+backend sanitization), **credential-injection.md** (cache refresh), **execution-log-viewer.md** (security considerations)
> - **Patterns detected**: API keys (sk-*, ghp_*, trinity_mcp_*), OAuth tokens, Bearer/Basic auth, sensitive env vars (ANTHROPIC_*, OPENAI_*, GITHUB_*, etc.)
>
> **Previous (2026-02-15)**: Claude Max Subscription Support for Headless Calls:
> - Removed mandatory `ANTHROPIC_API_KEY` check from `execute_claude_code()` (line 410-414) and `execute_headless_task()` (line 586-590) in `docker/base-image/agent_server/services/claude_code.py`
> - Claude Code now uses whatever authentication is available: OAuth session from `/login` (Claude Pro/Max) stored in `~/.claude.json`, OR `ANTHROPIC_API_KEY` env var
> - Enables headless calls (schedules, MCP triggers, parallel tasks) to use Claude Max subscription billing
> - Updated flows: **agent-terminal.md** (Claude Max subscription flow, test cases), **scheduling.md** (authentication section), **execution-queue.md** (revision history), **parallel-headless-execution.md** (authentication section + revision history), **agent-lifecycle.md** (authentication model), **credential-injection.md** (Claude Max as alternative)

> **Updated (2026-02-12)**: UI Component Standardization - AutonomyToggle & Dashboard Tab:
> - **NEW: autonomy-toggle-component.md**: Reusable `AutonomyToggle.vue` component (151 lines) used in 4 locations: AgentNode.vue, ReplayTimeline.vue, AgentHeader.vue, Agents.vue
> - **autonomy-mode.md**: Updated entry points section with component table showing 4 UI locations
> - **agent-network.md**: Updated AgentNode.vue toggle documentation, Running + Autonomy toggles now same row (lines 57-86)
> - **agents-page-ui-improvements.md**: Updated revision history, Running + Autonomy toggles now same row (lines 108-123)
> - **replay-timeline.md**: Updated with AutonomyToggle component usage (lines 155-161, no label mode)
> - **agent-dashboard.md**: Dashboard tab now conditionally hidden when agent lacks `dashboard.yaml`. Added `hasDashboard` ref, `checkDashboardExists()` function, conditional tab visibility
> - **Toggle Position Standardization**: Running and Autonomy toggles now on same row in both Dashboard Graph and Agents page

> **Previous (2026-02-12)**: Test Fix - Parallel Task Queue Test:
> - **execution-queue.md**: Added revision history entry for `test_parallel_task_does_not_show_in_queue` fix
> - **parallel-headless-execution.md**: Added revision history entry and Related Tests section
> - **Fix**: Test now uses `async_mode: True` to return immediately instead of timing out after 30s

> **Updated (2026-02-11)**: Scheduler Consolidation - Embedded Scheduler Removed:
> - **scheduling.md**: Major update - all references to `src/backend/services/scheduler_service.py` replaced with dedicated scheduler (`src/scheduler/`). Architecture diagram updated. Create/Enable/Disable/Delete flows now show database-only backend with 60s scheduler sync. Manual trigger flows through dedicated scheduler API.
> - **autonomy-mode.md**: Updated Side Effects section - schedule toggling now database-only, dedicated scheduler syncs changes. Scheduler enforcement section references `src/scheduler/service.py`.
> - **activity-stream.md**: Updated Schedule Integration section - activity tracking now via internal API endpoints called by dedicated scheduler.
> - **execution-queue.md**: Updated Section 2 (Scheduler) to document dedicated scheduler execution flow with distributed locking.
> - **trinity-connect.md**: Updated event source for `schedule_execution_completed` to reference dedicated scheduler.
> - **scheduler-service.md**: Already updated (reference document for the new architecture).
> - Key changes: Embedded scheduler fully removed. Manual triggers route through scheduler API. Activity tracking via internal endpoints. Database sync every 60 seconds.

> **Updated (2026-02-05)**: CRED-002 Credential System Audit - Multiple Feature Flows Updated:
> - **mcp-orchestration.md**: Tool count updated 36 -> 39 (16 agent, 3 chat, 4 system, 1 docs, 7 skills, 8 schedule). Replaced `reload_credentials` with 4 new tools: `inject_credentials`, `export_credentials`, `import_credentials`, `get_credential_encryption_key`
> - **agent-lifecycle.md**: Updated `start_agent_internal()` to document 3-phase startup injection (Trinity, Credentials, Skills). Removed `credential_manager` references. Updated line numbers for lifecycle.py
> - **local-agent-deploy.md**: Removed `credential_manager` parameter. Credentials now injected via `/api/agents/{name}/credentials/inject` endpoint
> - **template-processing.md**: Removed Redis credential_manager references. GitHub PAT now via `get_github_pat()` from SQLite/env. Removed `initialize_github_pat()` documentation
> - All flows now document CRED-002 system: direct file injection, encrypted `.credentials.enc` storage, no Redis

> **Updated (2026-02-05)**: Trinity Connect (Local-Remote Agent Sync):
> - **trinity-connect.md**: New feature flow for real-time event listening from local Claude Code
> - New WebSocket endpoint `/ws/events` with MCP API key authentication
> - Server-side event filtering based on user's accessible agents (owned + shared)
> - New `trinity-listen.sh` blocking script for event-driven local-remote coordination
> - Files: `main.py` (FilteredWebSocketManager, endpoint), `db/agents.py` (get_accessible_agent_names), `activity_service.py`, `scheduler_service.py`, `routers/agents.py` (broadcast hooks)
> - **Updated existing flows** to document Trinity Connect integration:
>   - **activity-stream.md**: Added dual broadcast pattern (main + filtered WebSocket)
>   - **scheduling.md**: Added Trinity Connect section with schedule event broadcasts
>   - **scheduler-service.md**: Added filtered broadcast callback documentation
>   - **agent-lifecycle.md**: Added Trinity Connect filtered broadcasts for agent_started/agent_stopped
>   - **mcp-api-keys.md**: Added WebSocket authentication documentation for `/ws/events`

> **Updated (2026-02-05)**: SSE Streaming Fix for Live Execution Logs:
> - **parallel-headless-execution.md**: Added nginx configuration requirements for SSE streaming (`proxy_buffering off`, `proxy_cache off`, `chunked_transfer_encoding on`). Documented frontend fetch/ReadableStream implementation.
> - **execution-detail-page.md**: Added "Live SSE Streaming" section with nginx config, frontend implementation, and UI indicators.
> - **Fix**: Live execution logs now work on production (nginx was buffering SSE events)
> - Files changed: `src/frontend/nginx.conf` (added SSE directives to `/api/` location)

> **Updated (2026-01-30)**: Git Pull Permission Fix:
> - **github-sync.md**: `POST /api/agents/{name}/git/pull` changed from `OwnedAgentByName` to `AuthorizedAgentByName`
> - Shared users can now pull from GitHub repositories (previously owner/admin only)
> - Updated Access Control Dependencies table, Endpoint Signatures table, and Security Considerations section

> **Updated (2026-01-30)**: Async Mode for Parallel Execution:
> - **parallel-headless-execution.md**: Added comprehensive "Async Mode (Fire-and-Forget)" section with architecture diagram, implementation details, API spec, use cases, and sync vs async comparison table
> - **mcp-orchestration.md**: Added "Async Mode" section documenting `async` parameter for `chat_with_agent` tool, polling endpoint, and use cases
> - **agent-to-agent-collaboration.md**: Added "Async Mode (Fire-and-Forget)" subsection to Parallel Delegation Mode
> - Feature: When `parallel=true` and `async=true`, backend spawns task via `asyncio.create_task()` and returns immediately with `execution_id`
> - Polling: `GET /api/agents/{name}/executions/{execution_id}` for status and results
> - Implementation: `_execute_task_background()` helper in `chat.py:418-525`, `async_mode` field in `ParallelTaskRequest`

> **Updated (2026-01-29)**: Scheduler Sync Bug Fix:
> - **scheduling.md**: Known Issues section marked as FIXED, added fix details for `next_run_at` calculation and periodic sync
> - **scheduler-service.md**: Added Flow 6 "Periodic Schedule Sync" documenting 60-second sync interval, snapshot tracking, job detection
> - **replay-timeline.md**: Updated "Known Issue" to "Scheduler Sync (FIXED)" with fix summary
> - **dashboard-timeline-view.md**: Added revision history entry for scheduler sync fix
> - **Database layer changes** (`src/backend/db/schedules.py`): `create_schedule()`, `update_schedule()`, `set_schedule_enabled()` now calculate `next_run_at` using croniter
> - **Dedicated scheduler changes** (`src/scheduler/service.py`): `_sync_schedules()` method syncs every 60s; new schedules appear in APScheduler without container restart
>
> **Updated (2026-01-29)**: Timeline Schedule Markers (TSM-001):
> - **replay-timeline.md**: Added Section 5a "Schedule Markers" with full implementation details (computed property, SVG rendering, helper functions)
> - **dashboard-timeline-view.md**: Added `schedules` prop to Props table, Test Case 9, edge cases for schedule markers
> - **scheduling.md**: Added Dashboard Timeline to Related Flows for cross-reference
> - Purple triangle markers at `next_run_at` position; hover shows tooltip; click navigates to Schedules tab
> - Data flow: `network.js:fetchSchedules()` -> `GET /api/ops/schedules?enabled_only=true` -> `ReplayTimeline.vue:scheduleMarkers`
> - **Fix**: Timeline extends max 2 hours into future (far-off schedules don't break scale)
>
> **Updated (2026-01-29)**: MCP Schedule Management (MCP-SCHED-001):
> - **mcp-orchestration.md**: Already updated to 36 tools (13 agent, 3 chat, 4 system, 1 docs, 7 skills, 8 schedule)
> - **scheduling.md**: Already has MCP Integration section with 8 schedule tools table
> - **execution-queue.md**: Added `trigger_agent_schedule` to Entry Points, updated Related Flows
> - **agent-to-agent-collaboration.md**: Added System Agent Schedule Management section for system-scoped agents managing schedules across all agents
> - Schedule tools go through existing backend endpoints -> scheduler service -> execution queue (no new queue paths)
>
> **Updated (2026-01-27)**: Bug Fixes:
> - **internal-system-agent.md**: Added `system_prefix` query parameter to `POST /api/ops/emergency-stop` endpoint for targeted emergency stops. Schedule pausing (line 638-639) and agent stopping (line 658-659) now respect prefix filter. Enables safe testing with nonexistent prefix (`routers/ops.py:607-696`)
> - **testing-agents.md**: Fixed AsyncTrinityApiClient header merging - all async methods (get, post, put, delete) now properly merge custom headers with auth headers (`tests/utils/api_client.py:208-280`). Emergency stop test now uses `?system_prefix=nonexistent-test-prefix-xyz` to avoid side effects (`tests/test_ops.py:367-391`)
>
> **Updated (2026-01-26)**: Agent Start/Stop Toggle UX:
> - **agent-lifecycle.md**: Updated Entry Points (unified toggle UI), Frontend Layer (RunningStateToggle component), State Management (`toggleAgentRunning()`)
> - **agent-network.md**: Added RunningStateToggle to AgentNode.vue (lines 57-65), `toggleAgentRunning()` to network.js (lines 1211-1254)
> - **agents-page-ui-improvements.md**: Updated to reflect RunningStateToggle replacing Start/Stop buttons
> - New component: `RunningStateToggle.vue` - reusable toggle with sm/md/lg sizes, loading spinner, dark mode, ARIA support
>
> **Updated (2026-01-25)**: Skills Management System - 5 Dedicated Flows:
> - **skills-management.md**: UI documentation for Skills.vue admin page and SkillsPanel.vue agent tab (grid layout, modals, user flows)
> - **skills-crud.md**: Backend CRUD operations via `/skills` page (`routers/skills.py`, `db/skills.py`)
> - **agent-skill-assignment.md**: Owner assigns skills via SkillsPanel (`routers/agents.py:999-1184`)
> - **skill-injection.md**: Automatic injection to `~/.claude/skills/{name}/SKILL.md` on agent start (`skill_service.py`, `lifecycle.py:219-221`)
> - **mcp-skill-tools.md**: 8 MCP tools for programmatic management (`tools/skills.ts`, `client.ts:500-575`)
>
> **Updated (2026-01-23)**: Shared Folders Template Extraction Fix (SF-H1):
> - **agent-shared-folders.md**: Rewrote "Agent Creation Flow" section with three-phase structure
> - Phase 1: Template Extraction (lines 91-92, 173-179) - extracts `shared_folders` from template.yaml
> - Phase 2: DB Upsert (lines 394-404) - persists config BEFORE container creation
> - Phase 3: Volume Mounting (lines 406-450) - mounts volumes based on DB config
> - Fix ensures templates with `shared_folders: expose: true` get volumes mounted on first creation
> - Added Revision History table, Template-Based Agent Test section, corrected all line numbers
>
> **Updated (2026-01-15)**: Timezone-Aware Timestamp Handling:
> - All feature flows with timestamp handling updated to reference [Timezone Handling Guide](/docs/TIMEZONE_HANDLING.md)
> - Backend: Uses `utc_now_iso()`, `to_utc_iso()`, `parse_iso_timestamp()` from `utils/helpers.py` - timestamps include 'Z' suffix
> - Frontend: Uses `parseUTC()`, `getTimestampMs()` from `@/utils/timestamps.js` - handles missing 'Z' suffix for backward compatibility
> - Updated flows: **activity-stream.md**, **execution-queue.md**, **scheduling.md**, **agent-network.md**
> - Fix: Dashboard Timeline events now display at correct positions regardless of server/client timezone difference
>
> **Updated (2026-01-14)**: Security Bug Fixes (4 HIGH, 1 LOW):
> - **execution-queue.md**: Race Condition Fixes - `submit()` uses atomic `SET NX EX`, `complete()` uses Lua script for atomic pop-and-set, `get_all_busy_agents()` uses `SCAN` instead of blocking `KEYS`
> - **agent-lifecycle.md**: Auth on Lifecycle Endpoints - `start`, `stop`, `logs` endpoints now use `AuthorizedAgentByName` dependency
> - **agent-lifecycle.md + container-capabilities.md**: Container Security Consistency - Added `RESTRICTED_CAPABILITIES` and `FULL_CAPABILITIES` constants, all creation paths now apply baseline security
> - **internal-system-agent.md**: Emergency Stop Parallel Execution - Uses `ThreadPoolExecutor(max_workers=10)` for faster fleet halt (20-30s vs 200+s)
>
> **Previous (2026-01-13)**: Dedicated Scheduler Service:
> - **scheduler-service.md**: New standalone scheduler service replacing embedded backend scheduler
> - Fixes duplicate execution bug in multi-worker deployments (was: each uvicorn worker ran its own APScheduler)
> - Source: `src/scheduler/` (main.py, service.py, config.py, models.py, database.py, agent_client.py, locking.py)
> - Docker: `docker/scheduler/` (Dockerfile, requirements.txt, docker-compose.test.yml)
> - Tests: `tests/scheduler_tests/` (8 test files: config, cron, database, locking, agent_client, service, conftest)
> - Key features: Single-instance design, Redis distributed locks, event publishing, health endpoints
> - Lock pattern: `scheduler:lock:schedule:{schedule_id}` with auto-renewal every 300s (half of 600s TTL)
> - Agent communication: HTTP POST to `/api/task` via AgentClient with 15-min timeout
> - Related: scheduling.md (backend CRUD API), autonomy-mode.md (execution gating)
>
> **Updated (2026-01-13)**: Host Telemetry Monitoring (OBS-011, OBS-012):
> - **host-telemetry.md**: New feature flow for infrastructure health monitoring
> - Host stats: CPU, memory, disk usage via psutil in Dashboard header
> - Container stats: Aggregate CPU/memory across running agents (API only)
> - Frontend: `HostTelemetry.vue` with sparkline charts via uPlot, 5s polling
> - Backend: `routers/telemetry.py` - `/api/telemetry/host`, `/api/telemetry/containers`
> - Performance: Container stats use parallel ThreadPoolExecutor + `list_all_agents_fast()`
> - Files: HostTelemetry.vue (194 lines), SparklineChart.vue (148 lines), telemetry.py (174 lines)
>
> **Updated (2026-01-13)**: Live Button for Running Tasks:
> - **execution-detail-page.md**: Added "Live" button entry point from TasksPanel (lines 213-232)
> - Green badge with animated pulsing dot appears for running tasks
> - Navigates to Execution Detail page for real-time monitoring
> - Explicit ID logic: server executions use `task.id`, local pending tasks use `task.execution_id` from process registry
> - **execution-termination.md**: Added Live button as additional entry point alongside Stop button
> - **LIVE_EXECUTION_STREAMING.md**: Marked FR4 (Entry Point from Running Task) as implemented
> - Files: TasksPanel.vue (213-232)
>
> **Updated (2026-01-13)**: System Agent UI Consolidation:
> - **system-agent-ui.md**: Archived - dedicated `/system-agent` page removed
> - **internal-system-agent.md**: Updated Frontend UI section with new AgentDetail.vue tab filtering, Agents.vue system agent display, and store getters
> - **agents-page-ui-improvements.md**: Added "System Agent Display" enhancement section with store changes, view changes, and testing steps
> - System agent (`trinity-system`) now uses standard `AgentDetail.vue` with full tab access including **Schedules**
> - System agent pinned at top of Agents page (admin-only visibility) with purple ring and "SYSTEM" badge
> - Tabs hidden for system agent: Sharing, Permissions, Folders, Public Links (not applicable)
> - Files deleted: `SystemAgent.vue` (782 lines), `SystemAgentTerminal.vue` (~350 lines)
> - `/system-agent` route now redirects to `/agents/trinity-system`
> - Key line numbers: AgentDetail.vue `visibleTabs` (414-448), Agents.vue admin check (288-305), agents.js getters (25-27, 39-41)
>
> **Updated (2026-01-13)**: System Agent Report Storage:
> - **internal-system-agent.md**: Added Report Storage section documenting organized report directories
> - Reports saved to `~/reports/{fleet,health,costs,compliance,service-checks,schedules,executions}/`
> - Naming convention: `YYYY-MM-DD_HHMM.md` for timestamped reports
> - All `/ops/` slash commands updated with "Save Report" instructions
> - New `.gitignore` in template to exclude `reports/` from sync
>
> **Updated (2026-01-12)**: Execution Termination Feature:
> - **execution-termination.md**: New feature flow for stopping running executions
> - Stop button in Tasks panel (`TasksPanel.vue:239-255`) for running tasks with `execution_id`
> - Process Registry (`agent_server/services/process_registry.py`) - thread-safe subprocess tracking
> - Agent endpoints: `POST /api/executions/{id}/terminate`, `GET /api/executions/running`
> - Backend proxy: `POST /api/agents/{name}/executions/{id}/terminate` with queue release
> - Signal flow: SIGINT (graceful, 5s timeout) -> SIGKILL (force)
> - New `EXECUTION_CANCELLED` activity type for audit trail
> - Process registration in `claude_code.py` for both chat and task executions
> - Updated flows: execution-queue.md, tasks-tab.md
>
> **Updated (2026-01-12)**: Make Repeatable Feature:
> - **tasks-tab.md**: Added "Make Repeatable" button (calendar icon) to create schedule from task execution
> - **scheduling.md**: Added "Make Repeatable" flow (Section 1b) with `initialMessage` prop and pre-fill behavior
> - Frontend files: TasksPanel.vue (251-261, 451, 654-657), AgentDetail.vue (84, 148, 261, 583-594), SchedulesPanel.vue (487-490, 790-802)
> - User flow: Click calendar icon on task -> Tab switches to Schedules -> Create form opens with message pre-filled
>
> **Updated (2026-01-12)**: Frontend Polling Optimization:
> - Reduced polling frequency across all composables to lower API load:
>   - `useSessionActivity.js:117`: Activity polling changed from 2s to 5s
>   - `useAgentStats.js:4,59`: Stats polling changed from 5s to 10s, MAX_POINTS from 60 to 30 (still 5 min of history)
>   - `useAgentLogs.js:45`: Logs auto-refresh changed from 10s to 15s
>   - `useGitSync.js:164`: Git status polling changed from 30s to 60s
> - Feature flows updated: activity-monitoring.md, agent-logs-telemetry.md, github-sync.md, agent-network.md, agents-page-ui-improvements.md, activity-stream-collaboration-tracking.md
>
> **Updated (2026-01-12)**: Database Batch Queries (N+1 Fix):
> - **New method**: `db.get_all_agent_metadata(user_email)` in `db/agents.py:467-529` - single JOIN query across `agent_ownership`, `users`, `agent_git_config`, `agent_sharing` tables
> - **Updated function**: `get_accessible_agents()` in `helpers.py:83-153` - was 8-10 queries per agent, now 2 total queries
> - **Exposed on DatabaseManager**: `database.py:845-850`
> - **Result**: Database queries reduced from 160-200 to 2 per `/api/agents` request
> - **Orphaned agents**: Docker-only containers (no DB record) now only visible to admin
> - **Feature flows updated**: agent-lifecycle.md, agent-network.md, agents-page-ui-improvements.md
>
> **Updated (2026-01-12)**: Docker Stats Optimization:
> - **Performance**: `/api/agents` response time reduced from ~2-3s to <50ms
> - **New function**: `list_all_agents_fast()` in `services/docker_service.py:101-159` - extracts data ONLY from container labels
> - **Avoids slow operations**: `container.attrs`, `container.image`, `container.stats()` (2+ seconds per container)
> - **Updated files**: `helpers.py:17,92,167` (`get_accessible_agents`, `get_agents_by_prefix`), `main.py:26,177` (startup), `ops.py:22` (fleet ops), `telemetry.py:16,126` (container stats)
> - **Feature flows updated**: agent-lifecycle.md, agent-network.md, internal-system-agent.md

> **Updated (2026-01-12)**: Agent Dashboard feature:
> - **agent-dashboard.md**: New feature flow for agent-defined dashboard system replacing Metrics tab
> - Dashboard tab renders `DashboardPanel.vue` component with 11 widget types
> - Agent defines `dashboard.yaml` at `~/dashboard.yaml` (i.e., `/home/developer/dashboard.yaml`)
> - Backend: `/api/agent-dashboard/{name}` (routers/agent_dashboard.py) -> `services/agent_service/dashboard.py`
> - Agent Server: `/api/dashboard` (agent_server/routers/dashboard.py) reads and validates YAML
> - Widget types: metric, status, progress, text, markdown, table, list, link, image, divider, spacer
> - Auto-refresh based on `config.refresh` (default 30s, min 5s)

> **Updated (2026-01-11)**: Execution ID Tracking System:
> - **execution-queue.md**: Documented two ID systems - Queue ID (UUID, Redis, 10-min TTL) vs Database ID (`token_urlsafe(16)`, SQLite, permanent)
> - **execution-detail-page.md**: Clarified navigation uses Database Execution ID from `task_execution_id` in chat response
> - **scheduling.md**: Execution record created BEFORE activity for `related_execution_id` linkage; manual trigger now has full activity tracking
> - **dashboard-timeline-view.md**: Added execution ID handling section - timeline navigation uses Database ID
> - **chat.py**: Activity tracking uses `related_execution_id` as top-level field (not just in details dict)
> - **scheduler_service.py**: Lines 206-231 - execution created first, then activity with `related_execution_id=execution.id`
>
> **Updated (2026-01-10)**: Execution Detail Page:
> - **execution-detail-page.md**: New dedicated page for viewing execution details
> - Route: `/agents/:name/executions/:executionId` with full metadata, timestamps, task input, response, and transcript
> - Entry points: External link icon in TasksPanel (207-217), click on Timeline execution bars (767-785)
> - Backend: `GET /api/agents/{name}/executions/{id}` (schedules.py:319-332), `GET .../log` (schedules.py:335-375)
> - Database: `get_execution()` in db/schedules.py:447-453, `schedule_executions` table
> - Files: `ExecutionDetail.vue` (496 lines), `TasksPanel.vue`, `ReplayTimeline.vue`, router/index.js:41-46
>
> **Previous (2026-01-10)**: Dashboard Timeline View - Execution Boxes & Trigger-Based Colors:
> - **dashboard-timeline-view.md**: Major update - execution-only boxes, trigger-based color coding, arrow validation
> - **Execution-only boxes**: Only `chat_start`/`schedule_start` events create boxes; `agent_collaboration` events only create arrows (not boxes)
> - **Trigger-based color coding**: Green=Manual, Purple=Scheduled, Cyan=Agent-Triggered (based on `triggered_by` field, not activity type)
> - **Arrow validation**: Arrows only drawn when target agent has execution box within 30-second tolerance window (prevents floating arrows)
> - **Source agent mapping fix**: Execution events use `activity.agent_name`, collaboration events use `details.source_agent` for correct row attribution
> - **Legend updated**: Shows "Manual", "Scheduled", "Agent-Triggered" labels with color swatches
> - Files: `ReplayTimeline.vue` (lines 543-579, 661-753, 841-868), `network.js` (lines 161-171)
>
> **Previous (2026-01-10)**: Dashboard Timeline View - Visual Enhancements:
> - Duration-based bar widths proportional to `duration_ms`, NOW marker at 90% viewport, future scroll prevention
> - Bug fix: `routers/chat.py:386-392` - Collaboration activities complete on HTTP errors
>
> **Updated (2026-01-09)**: System Agent Schedule & Execution Management:
> - **internal-system-agent.md**: Added Schedule and Execution Management via slash commands
> - New `GET /api/ops/schedules` endpoint (ops.py:427-495) with `agent_name` and `enabled_only` filters
> - New slash commands: `/ops/schedules/list`, `/ops/schedules/pause`, `/ops/schedules/resume`
> - New execution commands: `/ops/executions/list`, `/ops/executions/status`
> - Backend: `list_all_schedules()` method in db/schedules.py:185-193
> - Template: Updated CLAUDE.md with schedule management section, template.yaml with 6 new commands
> - Files: ops.py, db/schedules.py, database.py, config/agent-templates/trinity-system/*
>
> **Updated (2026-01-09)**: Agents Page Dashboard Parity:
> - **agents-page-ui-improvements.md**: Complete UI overhaul to match Dashboard (AgentNode.vue) tiles
> - Layout: Vertical list replaced with responsive 3-column grid (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3`)
> - Autonomy Toggle: Interactive AUTO/Manual switch with amber/gray styling, calls `PUT /api/agents/{name}/autonomy`
> - Execution Stats: Tasks (24h), success rate (color-coded), cost, last execution time
> - Context Progress Bar: Now always visible for consistent card height
> - Store: Added `executionStats` state, `fetchExecutionStats()`, `toggleAutonomy()` actions to agents.js
> - Files: Agents.vue (413 lines), agents.js (681 lines)
>
> **Updated (2026-01-04)**: ReplayTimeline Component documented:
> - **replay-timeline.md**: New feature flow for Dashboard replay timeline waterfall visualization
> - Waterfall-style timeline with agent rows, activity bars, and communication arrows
> - Zoom controls (50%-2000%), "Active only" toggle, blinking execution indicator
> - Smooth playback cursor using requestAnimationFrame, "Now" marker, 15-minute grid lines
> - Sticky headers for time scale and agent labels
> - Component: `src/frontend/src/components/ReplayTimeline.vue` (664 lines)
>
> **Updated (2026-01-03)**: Dashboard Autonomy Toggle Switch:
> - **autonomy-mode.md**: Replaced static "AUTO" badge with interactive toggle switch on Dashboard agent tiles
> - **agent-network.md**: Added `toggleAutonomy()` action documentation (network.js:993-1030)
> - Dashboard UI: AgentNode.vue toggle switch (lines 62-96) with "AUTO/Manual" label
> - Store: `toggleAutonomy(agentName)` calls API and updates node data reactively
> - Visual: Amber toggle when enabled, gray when disabled, loading state during API call
>
> **Updated (2026-01-03)**: MCP `get_agent_info` tool documented:
> - **mcp-orchestration.md**: Tool count updated to 21 (was 17). Added `get_agent_info` (agents.ts:103-145) and `get_agent_ssh_access` (agents.ts:385-420)
> - **agent-info-display.md**: Added MCP Tool Access section - agents can retrieve template metadata programmatically via `get_agent_info` tool
> - **agent-permissions.md**: Added `get_agent_info` to MCP tool enforcement list - respects permission boundaries for agent-scoped keys
>
> **Updated (2026-01-02)**: SSH Access feature documented:
> - **ssh-access.md**: New feature flow for ephemeral SSH credentials to agent containers
> - MCP Tool: `get_agent_ssh_access` in agents.ts:338-373 with key/password auth methods
> - Backend: `POST /api/agents/{name}/ssh-access` endpoint (agents.py:905-1072)
> - Service: `ssh_service.py` - ED25519 key generation, password hashing, Redis TTL, container exec
> - Settings: `ssh_access_enabled` ops setting (default: false) controls feature availability
> - Container security: Requires SETGID, SETUID, CHOWN, SYS_CHROOT, AUDIT_WRITE capabilities for SSH privilege separation
>
> **Updated (2026-01-23)**: Agent Resource Allocation line numbers refreshed:
> - **agent-resource-allocation.md**: Complete refresh - UI refactored to use separate ResourceModal.vue component
> - Frontend: AgentHeader.vue gear buttons at lines 222-232 (running) and 245-255 (stopped), emits `open-resource-modal`
> - Components: ResourceModal.vue extracted as standalone component with memory/CPU dropdowns
> - Composable: `useAgentSettings.js:17-23` state, `:78-110` methods for load/update
> - Store: `agents.js:693-710` - `getResourceLimits()` and `setResourceLimits()` actions
> - API: `GET/PUT /api/agents/{name}/resources` (agents.py:803-904)
> - Database: `memory_limit` and `cpu_limit` columns in `agent_ownership` table (db/agents.py:368-414)
> - Lifecycle: `check_resource_limits_match()` in helpers.py:333-363, recreation in lifecycle.py:195-200
>
> **Updated (2026-01-10)**: Chat endpoint execution log fix:
> - **execution-log-viewer.md**: Phase 2 fix - `/api/chat` now returns raw Claude Code format like `/api/task`
> - Agent server: `execute_claude_code()` captures `raw_messages`, chat router returns both raw and simplified formats
> - Backend: `chat.py` extracts `execution_log` (raw) and `execution_log_simplified` for activity tracking
> - Fix: MCP calls and chat-based executions now display transcripts in Tasks panel log viewer
>
> **Updated (2025-01-02)**: Scheduler execution log fix:
> - **execution-log-viewer.md**: Documented log format standardization - all execution types now use `/api/task` for raw Claude Code `stream-json` format
> - **execution-queue.md**: Updated scheduler to use `AgentClient.task()` instead of `AgentClient.chat()`
> - **scheduling.md**: Updated execution flow diagrams and AgentClient API table
> - **tasks-tab.md**: Added note about log format standardization
> - New `AgentClient.task()` method and `_parse_task_response()` in `src/backend/services/agent_client.py:194-281`
> - Fix: Scheduled execution logs now display properly in the Tasks panel log viewer
>
> **Updated (2026-01-01)**: Autonomy Mode feature documented:
> - **autonomy-mode.md**: New feature flow for agent autonomous operation toggle
> - Dashboard UI: AgentNode.vue toggle switch (lines 62-96) - see 2026-01-03 update for toggle details
> - Agent Detail UI: AUTO/Manual toggle button in header (AgentDetail.vue:137-160, 1401-1441)
> - Service layer: `services/agent_service/autonomy.py` - business logic for enable/disable
> - Database: `autonomy_enabled` column in `agent_ownership` table (db/agents.py:325-357)
> - API: `GET /api/agents/autonomy-status`, `GET/PUT /api/agents/{name}/autonomy` (agents.py:168-174, 766-791)
>
> **Updated (2026-01-01)**: Auth0 completely removed from codebase:
> - **auth0-authentication.md**: Updated to REMOVED status (was DEPRECATED)
> - Frontend: Deleted `@auth0/auth0-vue` package, `config/auth0.js`, Auth0 SDK initialization
> - Backend: Removed `/api/auth/exchange` endpoint, `Auth0TokenExchange` model, `AUTH0_*` config vars
> - Fix: Trinity now works on HTTP over LAN (Auth0 SDK required "secure origins")
>
> **Updated (2026-01-01)**: Dashboard Execution Stats feature added:
> - **agent-network.md**: Updated with execution stats display on Agent Cards
> - New `GET /api/agents/execution-stats` endpoint documented (agents.py:140-161)
> - Database layer: `get_all_agents_execution_stats()` in db/schedules.py:445-489
> - Frontend: `fetchExecutionStats()` in network.js:622-658, polled every 10s
> - AgentNode.vue: Compact stats row showing "12 tasks - 92% - $0.45 - 2m ago" (lines 86-103)
>
> **Updated (2025-12-31)**: Execution Log Viewer feature flow documented:
> - **execution-log-viewer.md**: New feature flow documenting the Tasks panel log viewer modal
> - Complete vertical slice: View button -> API call -> parseExecutionLog() -> formatted transcript
> - Covers all entry types: init, assistant-text, tool-call, tool-result, result
> - Includes visual styling, truncation logic, error handling
>
> **Updated (2025-12-31)**: Vector Logging feature flow documented:
> - **vector-logging.md**: New infrastructure flow documenting Vector log aggregation replacing audit-logger
> - Complete data flow: Docker socket -> VRL transforms -> platform.json/agents.json
> - Includes structured logging config, query examples, troubleshooting guide
>
> **Updated (2026-01-23)**: Process Engine Template Variable Fix (PE-H1):
> - **human-approval.md**: Documented template variable substitution (`{{input.*}}`, `{{steps.*}}`) in `title` and `description` fields
> - **process-execution.md**: Added "Template Variable Substitution" section with handler support table
> - **process-engine/README.md**: Added Template Variables section
> - Handler now uses `ExpressionEvaluator` to evaluate templates at runtime before creating approval requests
> - Tests: 4 new tests in `test_approval_handler.py` covering variable substitution, missing variables, and output content
>
> **Updated (2025-12-31)**: Execution log storage feature documented:
> - **execution-queue.md**: Added revision history entry for execution_log storage
> - **tasks-tab.md**: Added `GET /api/agents/{name}/executions/{execution_id}/log` endpoint documentation with response examples, added `execution_log` column to database schema
> - **parallel-headless-execution.md**: Added execution log persistence note and new retrieval endpoint documentation
> - New `execution_log TEXT` column in `schedule_executions` table stores full Claude Code execution transcript as JSON

> **Updated (2025-12-30)**: Public Agent Links flow documentation updated:
> - Verified all line numbers for `public_links.py`, `public.py`, `db/public_links.py`, `PublicLinksPanel.vue`, `PublicChat.vue`
> - Added detailed method tables with line references for frontend and backend
> - Added Pydantic model references (`db_models.py:299-372`)
> - Expanded testing section with test class descriptions
> - Added revision history entry

> **Updated (2025-12-30)**: Feature flows line number verification (continued):
> - **Agent Network**: Updated Dashboard.vue line numbers (OTel panel addition shifted lines ~20), updated network.js line numbers (edges now computed property, permission edges added), updated AgentNode.vue line numbers (system agent support added), updated chat.py line numbers
> - **Agent Network Replay Mode**: Updated all Dashboard.vue and network.js replay control line numbers to match current codebase
> - **Activity Stream**: Updated database.py table schema line (421-442, was 341-364), indexes line (574-580, was 424-430)
>
> **Updated (2025-12-30)**: Feature flows line number verification:
> - **Agent Lifecycle**: Updated line numbers after composable refactoring. Frontend lifecycle methods now in `composables/useAgentLifecycle.js`.
> - **Agent Terminal**: Verified line numbers, added Gemini runtime support documentation.
> - **Auth0 Authentication**: Marked as REMOVED (2026-01-01) - all Auth0 code deleted from codebase.
> - **Testing Agents**: Updated test count to 474+ tests (was 179), corrected config.py line numbers.
> - **Agent Custom Metrics**: Corrected router line (743), service lines, frontend/store lines.
> - **Agent Permissions**: Updated router lines (696-736), added composable docs, corrected database table line (444-453).
>
> **Updated (2025-12-29)**: Feature flows audit completed:
> - **Tasks Tab**: Verified tasks-tab.md with correct line numbers for TasksPanel.vue (264-475) and AgentDetail.vue (201, 884-885)
> - **Scheduling**: Updated API endpoint line numbers in scheduling.md to match current schedules.py
> - **Execution Queue**: Updated chat.py line numbers (106-356) to reflect retry helper addition
>
> **Updated (2025-12-27)**: **Service Layer Refactoring** - All agent-related feature flows updated:
> - `routers/agents.py` reduced from 2928 to ~842 lines (thin router layer)
> - Business logic extracted into 12 service modules in `services/agent_service/`
> - Updated flows: agent-lifecycle, agent-terminal, agent-permissions, agent-shared-folders, file-browser, agent-custom-metrics, execution-queue, local-agent-deploy

> **Updated (2025-12-26)**: Feature flows audit completed:
> - **Task DAG Removal**: ✅ All references cleaned up, Agents.vue bug fixed (2025-12-23 Req 9.8 deletion)
> - **GitHub Initialization**: ✅ Four critical bugs fixed - smart directory detection, orphaned record cleanup, agent files pushed (2025-12-26)
> - **Email Authentication**: ✅ Backend complete, route ordering fixed, frontend TODO (Phase 12.4, 2025-12-26)
> - **Agent Terminal**: ✅ Added per-agent API key control documentation (Req 11.7, 2025-12-26)
>
> **Previous Updates (2025-12-23)**:
> - **Workplan/Task DAG Removal**: Removed all references to workplans, plans, task DAGs (Req 9.8 - deleted system)
> - **OWASP Security Hardening**: Added bcrypt password hashing and SECRET_KEY handling documentation to auth0-authentication.md
> - **New Features**: First-Time Setup, Public Agent Links, Parallel Headless Execution flows added
> - **Internal System Agent**: Updated with Cost Monitoring data flow, 5-step reinitialize, OTel access fix

> **Important (2025-12-07)**: The Dashboard page now contains the Agent Network visualization (previously in a separate AgentNetwork.vue). Route `/network` redirects to `/`. See [agent-network.md](feature-flows/agent-network.md) for details.

> **Updated (2025-12-12)**: Critical bug fix:
> - **Agent Chat**: Context percentage >100% bug fixed - was incorrectly summing `input_tokens + cache_creation_tokens + cache_read_tokens`. Cache tokens are billing breakdowns (subsets), not additional tokens. Now uses `metadata.input_tokens` directly (authoritative total from modelUsage). See [agent-chat.md](feature-flows/agent-chat.md) for details.
>
> **Updated (2025-12-09)**: Bug fixes:
> - **Agent Lifecycle**: File persistence fixed - `startup.sh` now checks for existing `.git` or `.trinity-initialized` before re-cloning (Pillar III compliance)
> - **Agent Network**: Initial `activityState` set in `convertAgentsToNodes()` - running agents show "Idle" not "Offline"

> **Updated (2025-12-07)**: Several feature flows updated for recent changes:
> - **Template Processing**: Templates.vue now dynamically fetches from API (was static). CreateAgentModal has new `initialTemplate` prop and `created` event.
> - **Credential Injection**: OAuth provider buttons removed from Credentials.vue UI (backend API still available).
> - **Agent Network**: AgentNode.vue card layout fixes (flex, always-show progress bar, button alignment).
> - **Agent Lifecycle**: CreateAgentModal enhancements documented.

> **Important (2025-12-06)**: The agent-server has been refactored from a monolithic `agent-server.py` file into a modular package at `docker/base-image/agent_server/`. All feature flows referencing agent-server have been updated with new file paths and line numbers.

---

## Documented Flows

| Flow | Priority | Document | Description |
|------|----------|----------|-------------|
| Agent Lifecycle | High | [agent-lifecycle.md](feature-flows/agent-lifecycle.md) | Create, start, stop, delete Docker containers - **2026-02-18 17:50**: All toggles use `size="sm"`, RunningStateToggle default changed. **2026-01-14 Security Fixes**: Auth on lifecycle endpoints (AuthorizedAgentByName), Container security constants (RESTRICTED/FULL_CAPABILITIES). Service layer: lifecycle.py, crud.py, docker_service: `list_all_agents_fast()`, db: `get_all_agent_metadata()` batch query |
| **Agent Terminal** | High | [agent-terminal.md](feature-flows/agent-terminal.md) | Browser-based xterm.js terminal - **2026-02-18**: Tab repositioned after Git. **service layer: terminal.py, api_key.py** - Claude/Gemini/Bash modes, per-agent API key control, WebGL/Canvas renderer |
| Credential Injection | High | [credential-injection.md](feature-flows/credential-injection.md) | **CRED-002 Simplified System** - Direct file injection, encrypted git storage (.credentials.enc), auto-import on startup. **2026-02-16**: Credential sanitizer cache refreshed after injection. MCP tools: inject/export/import_credentials, get_credential_encryption_key (Refactored 2026-02-05) |
| Agent Scheduling | High | [scheduling.md](feature-flows/scheduling.md) | Cron-based automation, APScheduler, execution tracking - uses AgentClient.task() for raw log format, **Make Repeatable** flow for creating schedules from tasks (Updated 2026-01-12) |
| **Scheduler Service** | Critical | [scheduler-service.md](feature-flows/scheduler-service.md) | Standalone scheduler service - fixes duplicate execution bug in multi-worker deployments, Redis distributed locks, single-instance design, health endpoints. Source: `src/scheduler/`, Docker: `docker/scheduler/`, Tests: `tests/scheduler_tests/` (Created 2026-01-13) |
| Activity Monitoring | Medium | [activity-monitoring.md](feature-flows/activity-monitoring.md) | Real-time tool execution tracking |
| Agent Logs & Telemetry | Medium | [agent-logs-telemetry.md](feature-flows/agent-logs-telemetry.md) | Live metrics in AgentHeader - **2026-02-18**: Logs tab REMOVED from UI (API still available). Stats display shows only CPU, Memory, Uptime (network removed from UI) |
| **Host Telemetry** | Medium | [host-telemetry.md](feature-flows/host-telemetry.md) | Host CPU/memory/disk in Dashboard header via psutil, aggregate container stats via Docker API, sparkline charts with uPlot, 5s polling - no auth required (OBS-011, OBS-012) (Created 2026-01-13) |
| Template Processing | Medium | [template-processing.md](feature-flows/template-processing.md) | GitHub and local template handling |
| **Templates Page** | Medium | [templates-page.md](feature-flows/templates-page.md) | `/templates` route for browsing agent templates - GitHub and local template display, metadata cards (MCP servers, credentials, resources), "Use Template" flow to CreateAgentModal (Created 2026-01-21) |
| Agent Sharing | Medium | [agent-sharing.md](feature-flows/agent-sharing.md) | Email-based sharing, access levels - **2026-02-18**: Public Links tab consolidated into Sharing tab (SharingPanel.vue now embeds PublicLinksPanel.vue). **2026-01-30**: Added Git operations to Access Levels table (shared users can pull, not sync/init) |
| MCP Orchestration | Medium | [mcp-orchestration.md](feature-flows/mcp-orchestration.md) | 44 MCP tools: 16 agent (incl. 4 CRED-002 credential tools), 3 chat, 4 system, 1 docs, 7 skills, 8 schedule, 5 tag (ORG-001) (Updated 2026-02-17) |
| **MCP API Keys** | Medium | [mcp-api-keys.md](feature-flows/mcp-api-keys.md) | Create, list, revoke, delete MCP API keys for Claude Code integration - key generation with `trinity_mcp_` prefix, SHA-256 hash storage, usage tracking, scope separation (user/agent/system), auto-created default keys (Created 2026-01-13) |
| **API Keys Page** | Medium | [api-keys-page.md](feature-flows/api-keys-page.md) | Complete UI flow for `/api-keys` page - NavBar entry, page load lifecycle, create/copy/revoke/delete flows, admin vs user views, MCP config generation (Created 2026-01-21) |
| GitHub Sync | Medium | [github-sync.md](feature-flows/github-sync.md) | GitHub sync for agents - Source mode (pull-only, default) or Working Branch mode (legacy bidirectional). **2026-01-30**: Shared users can now git pull (was owner-only) |
| **GitHub Repository Initialization** | High | [github-repo-initialization.md](feature-flows/github-repo-initialization.md) | Initialize GitHub sync for existing agents - GitHubService class, git_service.initialize_git_in_container(), OwnedAgentByName dependency, smart directory detection (Updated 2026-01-23) |
| Agent Info Display | Medium | [agent-info-display.md](feature-flows/agent-info-display.md) | Template metadata display in Info tab (Req 9.3) - also accessible via MCP `get_agent_info` tool (Updated 2026-01-03) |
| Agent-to-Agent Collaboration | High | [agent-to-agent-collaboration.md](feature-flows/agent-to-agent-collaboration.md) | Inter-agent communication via Trinity MCP - X-Source-Agent header, permission system (user/agent/system scopes), collaboration event broadcasting, activity tracking, **system agent schedule management** via 8 MCP schedule tools (Updated 2026-01-29) |
| Persistent Chat Tracking | High | [persistent-chat-tracking.md](feature-flows/persistent-chat-tracking.md) | Database-backed chat persistence with full observability - **Session Management**: list/view/close sessions (EXEC-019, EXEC-020, EXEC-021 - backend API only, no frontend UI) (Updated 2026-01-13) |
| File Browser | Medium | [file-browser.md](feature-flows/file-browser.md) | Browse and download workspace files - **2026-02-18**: Files tab REMOVED from AgentDetail. Use File Manager page at `/files`. **service layer: files.py** |
| **File Manager** | High | [file-manager.md](feature-flows/file-manager.md) | Standalone `/files` page with two-panel layout, agent selector, rich media preview (image/video/audio/PDF/text), delete with protected path warnings - **Phase 11.5, Req 12.2** (Created 2025-12-27) |
| Agent Network (Dashboard) | High | [agent-network.md](feature-flows/agent-network.md) | Real-time visual graph showing agents and messages - **now integrated into Dashboard.vue at `/`** - uses `list_all_agents_fast()` + `get_all_agent_metadata()` batch query (Updated 2026-01-12) |
| **Dashboard Timeline View** | High | [dashboard-timeline-view.md](feature-flows/dashboard-timeline-view.md) | Graph/Timeline mode toggle - execution boxes (Green=Manual, Pink=MCP, Purple=Scheduled, Cyan=Agent-Triggered), collaboration arrows with box validation, live streaming, NOW at 90% viewport, **schedule markers** (TSM-001) (Updated 2026-01-29) |
| **Replay Timeline Component** | High | [replay-timeline.md](feature-flows/replay-timeline.md) | Waterfall-style timeline - execution-only boxes (collaborations = arrows only), trigger-based colors (Green=Manual, Pink=MCP, Purple=Scheduled, Cyan=Agent), 30s arrow validation window, **schedule markers at next_run_at** (TSM-001) - see dashboard-timeline-view.md (Updated 2026-01-29) |
| Unified Activity Stream | High | [activity-stream.md](feature-flows/activity-stream.md) | Centralized persistent activity tracking with WebSocket broadcasting (Updated 2025-12-30, Req 9.7) |
| Activity Stream Collaboration Tracking | High | [activity-stream-collaboration-tracking.md](feature-flows/activity-stream-collaboration-tracking.md) | Complete vertical slice: MCP → Database → Dashboard visualization (Implemented 2025-12-02, Req 9.7) |
| **Execution Queue** | Critical | [execution-queue.md](feature-flows/execution-queue.md) | Parallel execution prevention via Redis queue - **2026-02-16 Credential Sanitization**: Backend sanitizes execution logs before DB persistence. **2026-01-14 Race Condition Fixes**: Atomic Redis operations. Service layer: queue.py |
| **Execution Termination** | High | [execution-termination.md](feature-flows/execution-termination.md) | Stop running executions via process registry - SIGINT/SIGKILL, queue release, activity tracking (Created 2026-01-12) |
| **Agents Page UI Improvements** | Medium | [agents-page-ui-improvements.md](feature-flows/agents-page-ui-improvements.md) | Grid layout, autonomy toggle, execution stats, context bar - Dashboard parity with AgentNode.vue design, batch query optimization. **2026-02-18 17:50**: All toggles now use `size="sm"`, ReadOnlyToggle shows labels. **2026-02-18**: ReadOnlyToggle added (lines 248-255), tags layout fix with fixed-height container (line 271) and truncation (line 276). **2026-01-13**: System agent display for admins (purple ring, SYSTEM badge, pinned at top) |
| **Testing Agents Suite** | High | [testing-agents.md](feature-flows/testing-agents.md) | Automated pytest suite (1460+ tests) + 8 local test agents for manual verification. **2026-01-27**: Fixed AsyncTrinityApiClient header merging in async methods (Updated 2026-01-27) |
| **Agent Custom Metrics** | High | [agent-custom-metrics.md](feature-flows/agent-custom-metrics.md) | Agent-defined custom metrics via `template.yaml` + Dashboard Widget system via `dashboard.yaml` - **service layer: metrics.py, dashboard.py** (Updated 2026-01-23) |
| **Agent-to-Agent Permissions** | High | [agent-permissions.md](feature-flows/agent-permissions.md) | Agent communication permissions - **service layer: permissions.py** + **composable: useAgentPermissions.js** + **PermissionsPanel.vue** - enforced by `list_agents`, `get_agent_info`, `chat_with_agent` (Updated 2026-01-23) |
| **Agent Shared Folders** | High | [agent-shared-folders.md](feature-flows/agent-shared-folders.md) | File collaboration via shared volumes - **service layer: folders.py** (Updated 2025-12-27) |
| **System-Wide Trinity Prompt** | High | [system-wide-trinity-prompt.md](feature-flows/system-wide-trinity-prompt.md) | Admin-configurable custom instructions injected into all agents' CLAUDE.md at startup (Updated 2025-12-19) |
| **Dark Mode / Theme Switching** | Low | [dark-mode-theme.md](feature-flows/dark-mode-theme.md) | Client-side theme system with Light/Dark/System modes, localStorage persistence, Tailwind class strategy (Implemented 2025-12-14) |
| **System Manifest Deployment** | High | [system-manifest.md](feature-flows/system-manifest.md) | Recipe-based multi-agent deployment via YAML manifest - permissions, folders, schedules, auto-start. **ORG-001 Phase 4**: `default_tags`, per-agent `tags`, `system_view` auto-creation. `configure_tags()`, `create_system_view()` in system_service.py. Response: `tags_configured`, `system_view_created` (Updated 2026-02-17) |
| **OpenTelemetry Integration** | Medium | [opentelemetry-integration.md](feature-flows/opentelemetry-integration.md) | OTel metrics export from Claude Code agents to Prometheus via OTEL Collector - cost, tokens, productivity metrics with Dashboard UI (Phase 2.5 UI completed 2025-12-20) |
| **Internal System Agent** | High | [internal-system-agent.md](feature-flows/internal-system-agent.md) | Platform operations manager (trinity-system) with fleet ops API, health monitoring, schedule control, and emergency stop. **2026-01-27**: Emergency stop `system_prefix` query parameter for targeted stops. **2026-01-14**: Parallel `ThreadPoolExecutor(max_workers=10)` for faster fleet halt. **2026-01-13**: UI consolidated + Report Storage. (Req 11.1, 11.2) |
| **Local Agent Deployment** | High | [local-agent-deploy.md](feature-flows/local-agent-deploy.md) | Deploy local agents via MCP - **service layer: deploy.py** - archive validation, safe tar extraction, CLAUDE.md injection (Updated 2026-01-23) |
| **Parallel Headless Execution** | High | [parallel-headless-execution.md](feature-flows/parallel-headless-execution.md) | Stateless parallel task execution via `POST /task` endpoint - bypasses queue, enables orchestrator-worker patterns, **2026-02-16 credential sanitization** at agent+backend layers, max_turns runaway prevention, async mode (Updated 2026-02-16, Req 12.1) |
| **Public Agent Links** | Medium | [public-agent-links.md](feature-flows/public-agent-links.md) | Shareable public links for unauthenticated agent access with optional email verification, usage tracking, rate limiting. **2026-02-19**: Refactored to use shared chat components (ChatMessages, ChatInput, ChatBubble, ChatLoadingIndicator). **2026-02-18**: Consolidated into "Sharing" tab. **PUB-002**: External URL support. **PUB-003**: Agent introduction. **PUB-004**: Header metadata. **PUB-005**: Session persistence. **PUB-006**: Public mode awareness |
| **First-Time Setup** | High | [first-time-setup.md](feature-flows/first-time-setup.md) | Admin password wizard on fresh install, bcrypt hashing, API key configuration in Settings, login block until setup complete (Implemented 2025-12-23, Req 11.4 / Phase 12.3) |
| **Web Terminal** | High | [web-terminal.md](feature-flows/web-terminal.md) | Browser-based xterm.js terminal for System Agent with Claude Code TUI, PTY forwarding via Docker exec, admin-only access (Implemented 2025-12-25, Req 11.5) |
| **Email-Based Authentication** | High | [email-authentication.md](feature-flows/email-authentication.md) | Passwordless email login with 6-digit verification codes, 2-step UI with countdown timer, admin-managed whitelist, auto-whitelist on agent sharing, rate limiting and email enumeration prevention (Fully Implemented 2025-12-26, Phase 12.4) |
| **Admin Login** | High | [admin-login.md](feature-flows/admin-login.md) | Password-based admin authentication - fixed "admin" username, bcrypt password verification, JWT with mode=admin, 7-day token expiry, localStorage persistence, requires setup completion (Created 2026-01-21) |
| **Tasks Tab** | High | [tasks-tab.md](feature-flows/tasks-tab.md) | Unified task execution UI in Agent Detail - trigger manual tasks, monitor queue, view history, **Stop button** for running tasks, **Make Repeatable** for schedules (Updated 2026-01-12) |
| **Execution Log Viewer** | Medium | [execution-log-viewer.md](feature-flows/execution-log-viewer.md) | Tasks panel modal for viewing Claude Code execution transcripts - all execution types (scheduled/manual/user/MCP) now produce parseable logs, **credentials sanitized before storage** (Updated 2026-02-16) |
| **Execution Detail Page** | High | [execution-detail-page.md](feature-flows/execution-detail-page.md) | Dedicated page for execution details - metadata cards, timestamps, task input, response, full transcript. Entry points: TasksPanel **Live button** (running tasks, green pulsing badge) or icon (completed), Timeline click (Updated 2026-01-13) |
| **Container Capabilities** | Medium | [container-capabilities.md](feature-flows/container-capabilities.md) | Full capabilities mode for apt-get package installation - **2026-01-14**: Added RESTRICTED/FULL_CAPABILITIES constants for consistent security across all container creation paths. System-wide setting + per-agent API, automatic recreation on start (CFG-004) |
| **Vector Logging** | Medium | [vector-logging.md](feature-flows/vector-logging.md) | Centralized log aggregation via Vector - captures all container stdout/stderr, routes to platform.json/agents.json, replaces audit-logger (Implemented 2025-12-31) |
| **Autonomy Mode** | High | [autonomy-mode.md](feature-flows/autonomy-mode.md) | Agent autonomous operation toggle - enables/disables all schedules with single click - **service layer: autonomy.py**, uses AutonomyToggle component in 4 locations, owner-only access (Updated 2026-02-12) |
| **AutonomyToggle Component** | Medium | [autonomy-toggle-component.md](feature-flows/autonomy-toggle-component.md) | Reusable Vue toggle component (151 lines) for autonomy mode - used in AgentNode.vue, ReplayTimeline.vue, AgentHeader.vue, Agents.vue - sm/md/lg sizes (all now use 'sm'), v-model support, loading states (Updated 2026-02-18) |
| **Agent Resource Allocation** | Medium | [agent-resource-allocation.md](feature-flows/agent-resource-allocation.md) | Per-agent memory/CPU limits - gear button in AgentHeader.vue opens ResourceModal.vue, values stored in DB, auto-restart if running, container recreation on start if mismatch (Updated 2026-01-23) |
| **SSH Access** | Medium | [ssh-access.md](feature-flows/ssh-access.md) | Ephemeral SSH credentials via MCP tool - ED25519 keys or passwords, configurable TTL, **FRONTEND_URL domain extraction + Tailscale-aware host detection** (priority: SSH_HOST > FRONTEND_URL > Tailscale > host.docker.internal > gateway > localhost), Redis metadata with auto-expiry - **service layer: ssh_service.py** (Updated 2026-02-13: Fixed localhost bug in production) |
| **Agent Dashboard** | Medium | [agent-dashboard.md](feature-flows/agent-dashboard.md) | Agent-defined dashboard via `dashboard.yaml` - 11 widget types (metric, status, progress, text, markdown, table, list, link, image, divider, spacer), auto-refresh, YAML validation - **Dashboard tab now conditionally hidden when agent lacks dashboard.yaml** (Updated 2026-02-12) |
| **Platform Settings** | Medium | [platform-settings.md](feature-flows/platform-settings.md) | Admin settings page - GitHub PAT configuration and testing, ops settings (thresholds, limits), SSH access toggle, email whitelist. DB: `system_settings` table. Service: `settings_service.py` (Created 2026-01-13) |
| **Model Selection** | Medium | [model-selection.md](feature-flows/model-selection.md) | View and change LLM model for agents - Claude (sonnet/opus/haiku) or Gemini variants, persists across session reset, validated per runtime (Created 2026-01-13, CFG-005, CFG-006) |
| **Alerts Page** | Medium | [alerts-page.md](feature-flows/alerts-page.md) | Cost threshold alerts for process executions - NavBar badge with 60s polling, filter by status, dismiss alerts, severity levels (warning/critical), threshold types (per_execution/daily/weekly). Service: CostAlertService, DB: trinity_alerts.db (Created 2026-01-21) |
| **Skills CRUD** | High | [skills-crud.md](feature-flows/skills-crud.md) | Admin CRUD for platform skills via `/skills` page - create, update, delete methodology guides. Types: policy, procedure, methodology. Backend: `routers/skills.py`, `db/skills.py` (Created 2026-01-25) |
| **Skill Assignment** | High | [skill-assignment.md](feature-flows/skill-assignment.md) | Owner assigns skills to agents via SkillsPanel in Agent Detail - checkbox selection, save, inject to running agents. Backend: `routers/skills.py:93-199`, `db/skills.py:35-174` (Updated 2026-01-25) |
| **Skill Injection** | High | [skill-injection.md](feature-flows/skill-injection.md) | Automatic injection of assigned skills into agent containers on start - writes to `~/.claude/skills/{name}/SKILL.md` + updates `CLAUDE.md` with "Platform Skills" section. Service: `skill_service.py:300-435` (inject_skills + _update_claude_md_skills_section), lifecycle: `lifecycle.py:174-212,260-272`, agent files: `agent_server/routers/files.py:112-153,314-371`. AgentClient: `read_file()` (470-506), `write_file()` (508-547) (Updated 2026-01-25) |
| **Skills on Agent Start** | High | [skills-on-agent-start.md](feature-flows/skills-on-agent-start.md) | Detailed vertical slice of automatic skill injection during agent startup - complete flow from UI start button through `start_agent_internal()` -> `inject_assigned_skills()` -> `skill_service.inject_skills()` -> `AgentClient.write_file()` + `_update_claude_md_skills_section()` -> agent container file writes + CLAUDE.md update. Includes return value structure, error handling, testing steps (Updated 2026-01-25) |
| **MCP Skill Tools** | High | [mcp-skill-tools.md](feature-flows/mcp-skill-tools.md) | 8 MCP tools for programmatic skill management - `list_skills`, `get_skill`, `create_skill`, `delete_skill`, `assign_skill_to_agent`, `remove_skill_from_agent`, `sync_agent_skills`, `execute_procedure`. Some require system scope. Files: `tools/skills.ts`, `client.ts:500-575` (Created 2026-01-25) |
| **Skills Management UI** | High | [skills-management.md](feature-flows/skills-management.md) | Frontend UI documentation - Skills.vue admin page (CRUD modals, grid layout, type badges), SkillsPanel.vue agent tab (checkbox assignment, Save/Sync buttons). User flows for create/edit/delete skills and assign/sync to agents (Created 2026-01-25) |
| **Skills Library Sync** | High | [skills-library-sync.md](feature-flows/skills-library-sync.md) | GitHub repository sync for skills library - Settings.vue configuration (URL/branch), git clone/pull operations, GitHub PAT for private repos. Service: `skill_service.py:sync_library()`, Settings: `settings_service.py` (Created 2026-01-25) |
| **Trinity Connect** | High | [trinity-connect.md](feature-flows/trinity-connect.md) | Local-remote agent sync via `/ws/events` WebSocket endpoint. MCP API key auth, server-side event filtering, blocking `trinity-listen.sh` script. Enables real-time coordination between local Claude Code and Trinity agents (Created 2026-02-05) |
| **Read-Only Mode** | Medium | [read-only-mode.md](feature-flows/read-only-mode.md) | Code protection via Claude Code PreToolUse hooks - blocks Write/Edit/NotebookEdit to protected paths (*.py, *.js, CLAUDE.md, etc.), allows output directories (content/, output/, reports/). ReadOnlyToggle in AgentHeader.vue (`size="sm"`) + Agents.vue (lines 248-255, now shows labels), auto-injection on agent start - **service layer: read_only.py** (CFG-007, Updated 2026-02-18 17:50) |
| **Agent Tags & System Views** | Medium | [agent-tags.md](feature-flows/agent-tags.md) | **Phase 1 (Tags)**: TagsEditor.vue with autocomplete, inline editing in AgentHeader, `/api/agents?tags=` filtering (OR logic). **Phase 2 (System Views)**: Saved tag filters in Dashboard sidebar, SystemViewsSidebar.vue + SystemViewEditor.vue, localStorage persistence, shared views. **Phase 3 (Polish)**: 5 MCP tools in `tools/tags.ts`, quick tag filter pills in Dashboard header, bulk tag operations on Agents page, **tags layout fix** (fixed-height container, truncation). **Phase 4**: System manifest integration (default_tags, per-agent tags, system_view auto-creation). **db/tags.py**, **routers/tags.py**, **db/system_views.py**, **routers/system_views.py** - 10 total API endpoints + 5 MCP tools (ORG-001 Complete, Layout Fix 2026-02-18) |
| **Authenticated Chat Tab** | High | [authenticated-chat-tab.md](feature-flows/authenticated-chat-tab.md) | Simple chat UI in Agent Detail (CHAT-001) - bubble messages, session selector dropdown, shared components with PublicChat. Uses `/task` endpoint for Dashboard tracking. **Components**: ChatPanel.vue, ChatMessages.vue, ChatInput.vue, ChatBubble.vue, ChatLoadingIndicator.vue. **Tab position**: after Tasks (Created 2026-02-19) |

---

## Process Engine Flows

> **New (2026-01-16)**: Complete documentation for the Process Engine - BPMN-inspired workflow orchestration with AI agents.

The Process Engine is a major platform feature that enables defining, executing, and monitoring multi-step workflows with AI agents, human approvals, and automated scheduling. See the dedicated documentation folder for comprehensive feature flows:

**Index Document**: [process-engine/README.md](feature-flows/process-engine/README.md)

| Flow | Document | Description |
|------|----------|-------------|
| Process Definition | [process-definition.md](feature-flows/process-engine/process-definition.md) | YAML schema, validation, versioning |
| Process Execution | [process-execution.md](feature-flows/process-engine/process-execution.md) | Execution engine, step handlers, state machine, retry logic, compensation - Rebuilt with accurate line numbers 2026-01-23 |
| Process Monitoring | [process-monitoring.md](feature-flows/process-engine/process-monitoring.md) | Real-time WebSocket events (10 types), ExecutionTimeline, breadcrumbs, polling fallback (Updated 2026-01-23) |
| Human Approval | [human-approval.md](feature-flows/process-engine/human-approval.md) | Approval gates, inbox, timeout handling |
| Process Scheduling | [process-scheduling.md](feature-flows/process-engine/process-scheduling.md) | Cron triggers, timer steps |
| Process Analytics | [process-analytics.md](feature-flows/process-engine/process-analytics.md) | Cost tracking, metrics, trends, threshold alerts - ProcessDashboard.vue, analytics.js store, ProcessAnalytics service, CostAlertService (Rebuilt 2026-01-23) |
| Sub-Processes | [sub-processes.md](feature-flows/process-engine/sub-processes.md) | Parent-child linking, breadcrumbs |
| Agent Roles (EMI) | [agent-roles-emi.md](feature-flows/process-engine/agent-roles-emi.md) | EMI pattern, InformedNotifier |
| Process Templates | [process-templates.md](feature-flows/process-engine/process-templates.md) | Bundled and user templates |
| **Onboarding & Docs** | [onboarding-documentation.md](feature-flows/process-engine/onboarding-documentation.md) | Process Wizard, Docs page, Help panel, Chat assistant, Onboarding checklist |
| **Execution List Page** | [execution-list-page.md](feature-flows/execution-list-page.md) | `/executions` route - list all executions with filters, stats, pagination, auto-refresh (Created 2026-01-21) |
| **Process Dashboard** | [process-dashboard.md](feature-flows/process-dashboard.md) | `/process-dashboard` route - analytics overview with metrics cards, trend charts, process health, step performance (Created 2026-01-21) |

**Key Entry Points:**
- **UI**: Process List (`/processes`), Process Editor, Execution Detail, Approvals
- **API**: `/api/processes/*`, `/api/executions/*`, `/api/approvals/*`, `/api/process-templates/*`
- **Backend**: `src/backend/services/process_engine/`

---

## Archived Flows

> **Note**: These flows document features that have been removed, deprecated, or superseded. They are preserved in `feature-flows/archive/` for historical reference.

| Flow | Status | Document | Reason |
|------|--------|----------|--------|
| Authentication Mode System | REMOVED | [archive/auth0-authentication.md](feature-flows/archive/auth0-authentication.md) | Auth0 deleted (2026-01-01) - replaced by email-authentication.md |
| Agent Chat | DEPRECATED | [archive/agent-chat.md](feature-flows/archive/agent-chat.md) | UI replaced by Agent Terminal (2025-12-25) - API docs merged into execution-queue.md |
| Agent Vector Memory | REMOVED | [archive/vector-memory.md](feature-flows/archive/vector-memory.md) | Platform-injected vector memory removed (2025-12-24) - templates should define their own |
| Agent Network Replay Mode | SUPERSEDED | [archive/agent-network-replay-mode.md](feature-flows/archive/agent-network-replay-mode.md) | VCR-style replay replaced by Dashboard Timeline View and replay-timeline.md (2026-01-04) |
| System Agent UI | CONSOLIDATED | [archive/system-agent-ui.md](feature-flows/archive/system-agent-ui.md) | Dedicated `/system-agent` page removed (2026-01-13) - system agent now uses regular AgentDetail.vue with full tab access including Schedules |
| Skills Management | SPLIT | [archive/skills-management.md](feature-flows/archive/skills-management.md) | Comprehensive skills doc split into 4 dedicated flows (2026-01-25) - see skills-crud.md, agent-skill-assignment.md, skill-injection.md, mcp-skill-tools.md |

---

## Core Specifications

| Document | Purpose |
|----------|---------|
| [TRINITY_COMPATIBLE_AGENT_GUIDE.md](../TRINITY_COMPATIBLE_AGENT_GUIDE.md) | **Single-agent guide** — Creating Trinity-compatible agents, template structure, Four Pillars, planning system |
| [MULTI_AGENT_SYSTEM_GUIDE.md](../MULTI_AGENT_SYSTEM_GUIDE.md) | **Multi-agent guide** — Building coordinated multi-agent systems, architecture patterns, shared folders, deployment |

---

## Requirements Specs (Implemented)

| Document | Priority | Status | Description |
|----------|----------|--------|-------------|
| [DEDICATED_SCHEDULER_SERVICE.md](../requirements/DEDICATED_SCHEDULER_SERVICE.md) | **HIGH** | **IMPLEMENTED** | Standalone scheduler service - fixes duplicate execution bug with multiple workers, Redis distributed locks, single-instance design. See [scheduler-service.md](feature-flows/scheduler-service.md) (Implemented 2026-01-13) |
| [EXTERNAL_PUBLIC_URL.md](../requirements/EXTERNAL_PUBLIC_URL.md) | **MEDIUM** | **IMPLEMENTED** | External URL support for public agent links - enables sharing with users outside VPN. Adds `PUBLIC_CHAT_URL` env var, `external_url` field in API, "Copy External Link" button in UI (Implemented 2026-02-16) |

## Requirements Specs (Pending)

| Document | Priority | Status | Description |
|----------|----------|--------|-------------|
| [AGENT_SYSTEMS_AND_TAGS.md](../requirements/AGENT_SYSTEMS_AND_TAGS.md) | **MEDIUM** | **IMPLEMENTED** | Lightweight agent organization via tags and saved system views. **Phase 1 (Tags)**: `db/tags.py`, `routers/tags.py`, `TagsEditor.vue`, AgentHeader/AgentDetail integration, `/api/agents?tags=` filtering. **Phase 2 (System Views)**: `db/system_views.py`, `routers/system_views.py`, `SystemViewsSidebar.vue`, `SystemViewEditor.vue`, `systemViews.js` store, Dashboard integration with filter reactivity. (Completed 2026-02-17) |
| [PUBLIC_EXTERNAL_ACCESS_SETUP.md](../requirements/PUBLIC_EXTERNAL_ACCESS_SETUP.md) | **MEDIUM** | **NOT STARTED** | Infrastructure setup guide for exposing public endpoints outside VPN - Tailscale Funnel, GCP Load Balancer, or Cloudflare Tunnel options (Created 2026-02-16) |

---

## Flow Document Template

Save flows to: `docs/memory/feature-flows/{feature-name}.md`

```markdown
# Feature: {Feature Name}

## Overview
Brief description of what this feature does.

## User Story
As a [user type], I want to [action] so that [benefit].

## Entry Points
- **UI**: `src/frontend/src/views/Component.vue` - Action trigger
- **API**: `METHOD /api/endpoint`

## Frontend Layer
### Components
- `Component.vue:line` - handler() method

### State Management
- `stores/store.js` - action name

### API Calls
\`\`\`javascript
await api.method(`/api/endpoint`)
\`\`\`

## Backend Layer
### Endpoints
- `src/backend/main.py:line` - endpoint_handler()

### Business Logic
1. Step one
2. Step two
3. Step three

## Data Layer
### Database Operations
- Query: Description
- Update: Description

## Side Effects
- WebSocket broadcast: `{type, data}`
- Audit log entry

## Error Handling
- Error case → HTTP status

## Security Considerations
- Authorization checks
- Rate limiting

## Related Flows
- Upstream: Previous flow
- Downstream: Next flow
```

---

## How to Create a Flow Document

1. Run `/feature-flow-analysis {feature-name}`
2. Or manually:
   - Find UI entry point (grep for button/action)
   - Trace to API call (check store action)
   - Find backend endpoint (grep route)
   - Document database operations
   - Note side effects (WebSocket, audit)
   - **Add Testing section** with step-by-step verification instructions
3. Update this index after creating

## Testing Section Standard

Every feature flow MUST include a Testing section with:
- **Prerequisites**: What needs to be running/configured
- **Test Steps**: Numbered steps with Action → Expected → Verify
- **Edge Cases**: Boundary conditions and error scenarios
- **Cleanup**: How to reset state after testing
- **Status**: ✅ Working / 🚧 Not Tested / ⚠️ Issues / ❌ Broken

See `docs/TESTING_GUIDE.md` for template and examples.
