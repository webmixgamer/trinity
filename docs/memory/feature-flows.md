# Feature Flows Index

> **Purpose**: Maps features to detailed vertical slice documentation.
> Each flow documents the complete path from UI → API → Database → Side Effects.

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
> - Agent defines `dashboard.yaml` in `~/` or `~/workspace/` with declarative layout
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
> **Updated (2026-01-02)**: Agent Resource Allocation feature documented:
> - **agent-resource-allocation.md**: New feature flow for per-agent memory and CPU configuration
> - Frontend: Gear button in AgentDetail.vue header (lines 225, 243) opens modal dialog
> - Composable: `useAgentSettings.js` manages `resourceLimits` state and API calls
> - Store: `agents.js` - `getResourceLimits()` and `setResourceLimits()` actions (lines 601-618)
> - API: `GET/PUT /api/agents/{name}/resources` (agents.py:797-898)
> - Database: `memory_limit` and `cpu_limit` columns in `agent_ownership` table (db/agents.py:363-409)
> - Lifecycle: `check_resource_limits_match()` in helpers.py triggers container recreation on start
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
| Agent Lifecycle | High | [agent-lifecycle.md](feature-flows/agent-lifecycle.md) | Create, start, stop, delete Docker containers - **service layer: lifecycle.py, crud.py**, docker_service: `list_all_agents_fast()`, db: `get_all_agent_metadata()` batch query (Updated 2026-01-12) |
| **Agent Terminal** | High | [agent-terminal.md](feature-flows/agent-terminal.md) | Browser-based xterm.js terminal - **service layer: terminal.py, api_key.py** - Claude/Gemini/Bash modes, per-agent API key control (Updated 2025-12-30) |
| Credential Injection | High | [credential-injection.md](feature-flows/credential-injection.md) | Redis storage, hot-reload, OAuth2 flows (Updated 2025-12-19) |
| Agent Scheduling | High | [scheduling.md](feature-flows/scheduling.md) | Cron-based automation, APScheduler, execution tracking - uses AgentClient.task() for raw log format, **Make Repeatable** flow for creating schedules from tasks (Updated 2026-01-12) |
| Activity Monitoring | Medium | [activity-monitoring.md](feature-flows/activity-monitoring.md) | Real-time tool execution tracking |
| Agent Logs & Telemetry | Medium | [agent-logs-telemetry.md](feature-flows/agent-logs-telemetry.md) | Container logs viewing and live metrics |
| Template Processing | Medium | [template-processing.md](feature-flows/template-processing.md) | GitHub and local template handling |
| Agent Sharing | Medium | [agent-sharing.md](feature-flows/agent-sharing.md) | Email-based sharing, access levels |
| MCP Orchestration | Medium | [mcp-orchestration.md](feature-flows/mcp-orchestration.md) | 21 MCP tools for external agent management, including `get_agent_info` for template metadata access (Updated 2026-01-03) |
| GitHub Sync | Medium | [github-sync.md](feature-flows/github-sync.md) | GitHub sync for agents - Source mode (pull-only, default) or Working Branch mode (legacy bidirectional) (Updated 2025-12-30) |
| **GitHub Repository Initialization** | High | [github-repo-initialization.md](feature-flows/github-repo-initialization.md) | Initialize GitHub sync for existing agents - **refactored**: GitHubService class, git_service.initialize_git_in_container(), OwnedAgentByName dependency (Updated 2025-12-31) |
| Agent Info Display | Medium | [agent-info-display.md](feature-flows/agent-info-display.md) | Template metadata display in Info tab (Req 9.3) - also accessible via MCP `get_agent_info` tool (Updated 2026-01-03) |
| Agent-to-Agent Collaboration | High | [agent-to-agent-collaboration.md](feature-flows/agent-to-agent-collaboration.md) | Inter-agent communication via Trinity MCP (Implemented 2025-11-29) |
| Persistent Chat Tracking | High | [persistent-chat-tracking.md](feature-flows/persistent-chat-tracking.md) | Database-backed chat persistence with full observability (Implemented 2025-12-01) |
| File Browser | Medium | [file-browser.md](feature-flows/file-browser.md) | Browse and download workspace files in AgentDetail Files tab - **service layer: files.py** (Updated 2025-12-27) |
| **File Manager** | High | [file-manager.md](feature-flows/file-manager.md) | Standalone `/files` page with two-panel layout, agent selector, rich media preview (image/video/audio/PDF/text), delete with protected path warnings - **Phase 11.5, Req 12.2** (Created 2025-12-27) |
| Agent Network (Dashboard) | High | [agent-network.md](feature-flows/agent-network.md) | Real-time visual graph showing agents and messages - **now integrated into Dashboard.vue at `/`** - uses `list_all_agents_fast()` + `get_all_agent_metadata()` batch query (Updated 2026-01-12) |
| **Dashboard Timeline View** | High | [dashboard-timeline-view.md](feature-flows/dashboard-timeline-view.md) | Graph/Timeline mode toggle - execution boxes (Green=Manual, Purple=Scheduled, Cyan=Agent-Triggered), collaboration arrows with box validation, live streaming, NOW at 90% viewport (Updated 2026-01-10) |
| **Replay Timeline Component** | High | [replay-timeline.md](feature-flows/replay-timeline.md) | Waterfall-style timeline - execution-only boxes (collaborations = arrows only), trigger-based colors (Green=Manual, Purple=Scheduled, Cyan=Agent), 30s arrow validation window - see dashboard-timeline-view.md (Updated 2026-01-10) |
| Unified Activity Stream | High | [activity-stream.md](feature-flows/activity-stream.md) | Centralized persistent activity tracking with WebSocket broadcasting (Updated 2025-12-30, Req 9.7) |
| Activity Stream Collaboration Tracking | High | [activity-stream-collaboration-tracking.md](feature-flows/activity-stream-collaboration-tracking.md) | Complete vertical slice: MCP → Database → Dashboard visualization (Implemented 2025-12-02, Req 9.7) |
| **Execution Queue** | Critical | [execution-queue.md](feature-flows/execution-queue.md) | Parallel execution prevention via Redis queue - **service layer: queue.py** - scheduler uses AgentClient.task() for raw log format (Updated 2026-01-12: termination section) |
| **Execution Termination** | High | [execution-termination.md](feature-flows/execution-termination.md) | Stop running executions via process registry - SIGINT/SIGKILL, queue release, activity tracking (Created 2026-01-12) |
| **Agents Page UI Improvements** | Medium | [agents-page-ui-improvements.md](feature-flows/agents-page-ui-improvements.md) | Grid layout, autonomy toggle, execution stats, context bar - Dashboard parity with AgentNode.vue design, batch query optimization (Updated 2026-01-12) |
| **Testing Agents Suite** | High | [testing-agents.md](feature-flows/testing-agents.md) | Automated pytest suite (474+ tests) + 8 local test agents for manual verification - agent-server refactored to modular package (Updated 2025-12-30) |
| **Agent Custom Metrics** | High | [agent-custom-metrics.md](feature-flows/agent-custom-metrics.md) | Agent-defined custom metrics - **service layer: metrics.py** (Updated 2025-12-30) |
| **Agent-to-Agent Permissions** | High | [agent-permissions.md](feature-flows/agent-permissions.md) | Agent communication permissions - **service layer: permissions.py** + **composable: useAgentPermissions.js** - enforced by `list_agents`, `get_agent_info`, `chat_with_agent` (Updated 2026-01-03) |
| **Agent Shared Folders** | High | [agent-shared-folders.md](feature-flows/agent-shared-folders.md) | File collaboration via shared volumes - **service layer: folders.py** (Updated 2025-12-27) |
| **System-Wide Trinity Prompt** | High | [system-wide-trinity-prompt.md](feature-flows/system-wide-trinity-prompt.md) | Admin-configurable custom instructions injected into all agents' CLAUDE.md at startup (Updated 2025-12-19) |
| **Dark Mode / Theme Switching** | Low | [dark-mode-theme.md](feature-flows/dark-mode-theme.md) | Client-side theme system with Light/Dark/System modes, localStorage persistence, Tailwind class strategy (Implemented 2025-12-14) |
| **System Manifest Deployment** | High | [system-manifest.md](feature-flows/system-manifest.md) | Recipe-based multi-agent deployment via YAML manifest - complete with permissions, folders, schedules, auto-start (Completed 2025-12-18, Req 10.7) |
| **OpenTelemetry Integration** | Medium | [opentelemetry-integration.md](feature-flows/opentelemetry-integration.md) | OTel metrics export from Claude Code agents to Prometheus via OTEL Collector - cost, tokens, productivity metrics with Dashboard UI (Phase 2.5 UI completed 2025-12-20) |
| **Internal System Agent** | High | [internal-system-agent.md](feature-flows/internal-system-agent.md) | Platform operations manager (trinity-system) with fleet ops API, health monitoring, schedule control, and emergency stop. Ops-only scope. **2026-01-12**: Fleet ops uses `list_all_agents_fast()`. **2026-01-09**: Schedule & Execution Management. **2025-12-31**: AgentClient service pattern. (Req 11.1, 11.2) |
| **System Agent UI** | High | [system-agent-ui.md](feature-flows/system-agent-ui.md) | Admin-only `/system-agent` page with fleet overview cards, quick actions (Emergency Stop, Restart All, Pause/Resume Schedules), and Operations Console chat interface (Req 11.3 - Created 2025-12-20) |
| **Local Agent Deployment** | High | [local-agent-deploy.md](feature-flows/local-agent-deploy.md) | Deploy local agents via MCP - **service layer: deploy.py** (Updated 2025-12-27) |
| **Parallel Headless Execution** | High | [parallel-headless-execution.md](feature-flows/parallel-headless-execution.md) | Stateless parallel task execution via `POST /task` endpoint - bypasses queue, enables orchestrator-worker patterns - now with execution_log persistence (Updated 2025-12-31, Req 12.1) |
| **Public Agent Links** | Medium | [public-agent-links.md](feature-flows/public-agent-links.md) | Shareable public links for unauthenticated agent access with optional email verification, usage tracking, and rate limiting (Implemented 2025-12-22, Req 12.2) |
| **First-Time Setup** | High | [first-time-setup.md](feature-flows/first-time-setup.md) | Admin password wizard on fresh install, bcrypt hashing, API key configuration in Settings, login block until setup complete (Implemented 2025-12-23, Req 11.4 / Phase 12.3) |
| **Web Terminal** | High | [web-terminal.md](feature-flows/web-terminal.md) | Browser-based xterm.js terminal for System Agent with Claude Code TUI, PTY forwarding via Docker exec, admin-only access (Implemented 2025-12-25, Req 11.5) |
| **Email-Based Authentication** | High | [email-authentication.md](feature-flows/email-authentication.md) | Passwordless email login with 6-digit verification codes, 2-step UI with countdown timer, admin-managed whitelist, auto-whitelist on agent sharing, rate limiting and email enumeration prevention (Fully Implemented 2025-12-26, Phase 12.4) |
| **Tasks Tab** | High | [tasks-tab.md](feature-flows/tasks-tab.md) | Unified task execution UI in Agent Detail - trigger manual tasks, monitor queue, view history, **Stop button** for running tasks, **Make Repeatable** for schedules (Updated 2026-01-12) |
| **Execution Log Viewer** | Medium | [execution-log-viewer.md](feature-flows/execution-log-viewer.md) | Tasks panel modal for viewing Claude Code execution transcripts - all execution types (scheduled/manual/user/MCP) now produce parseable logs (Updated 2026-01-10) |
| **Execution Detail Page** | High | [execution-detail-page.md](feature-flows/execution-detail-page.md) | Dedicated page for execution details - metadata cards, timestamps, task input, response, full transcript. Entry points: TasksPanel icon, Timeline click (Implemented 2026-01-10) |
| **Vector Logging** | Medium | [vector-logging.md](feature-flows/vector-logging.md) | Centralized log aggregation via Vector - captures all container stdout/stderr, routes to platform.json/agents.json, replaces audit-logger (Implemented 2025-12-31) |
| **Autonomy Mode** | High | [autonomy-mode.md](feature-flows/autonomy-mode.md) | Agent autonomous operation toggle - enables/disables all schedules with single click - **service layer: autonomy.py**, dashboard toggle switch with "AUTO/Manual" label, owner-only access (Updated 2026-01-03) |
| **Agent Resource Allocation** | Medium | [agent-resource-allocation.md](feature-flows/agent-resource-allocation.md) | Per-agent memory/CPU limits - gear button in header opens modal, values stored in DB, auto-restart if running, container recreation on start if mismatch (Created 2026-01-02) |
| **SSH Access** | Medium | [ssh-access.md](feature-flows/ssh-access.md) | Ephemeral SSH credentials via MCP tool - ED25519 keys or passwords, configurable TTL, Tailscale-aware host detection, Redis metadata with auto-expiry - **service layer: ssh_service.py** (Created 2026-01-02) |
| **Agent Dashboard** | Medium | [agent-dashboard.md](feature-flows/agent-dashboard.md) | Agent-defined dashboard via `dashboard.yaml` - 11 widget types (metric, status, progress, text, markdown, table, list, link, image, divider, spacer), auto-refresh, YAML validation - replaces Metrics tab (Created 2026-01-12) |

---

## Archived Flows

> **Note**: These flows document features that have been removed, deprecated, or superseded. They are preserved in `feature-flows/archive/` for historical reference.

| Flow | Status | Document | Reason |
|------|--------|----------|--------|
| Authentication Mode System | REMOVED | [archive/auth0-authentication.md](feature-flows/archive/auth0-authentication.md) | Auth0 deleted (2026-01-01) - replaced by email-authentication.md |
| Agent Chat | DEPRECATED | [archive/agent-chat.md](feature-flows/archive/agent-chat.md) | UI replaced by Agent Terminal (2025-12-25) - API docs merged into execution-queue.md |
| Agent Vector Memory | REMOVED | [archive/vector-memory.md](feature-flows/archive/vector-memory.md) | Platform-injected vector memory removed (2025-12-24) - templates should define their own |
| Agent Network Replay Mode | SUPERSEDED | [archive/agent-network-replay-mode.md](feature-flows/archive/agent-network-replay-mode.md) | VCR-style replay replaced by Dashboard Timeline View and replay-timeline.md (2026-01-04) |

---

## Core Specifications

| Document | Purpose |
|----------|---------|
| [TRINITY_COMPATIBLE_AGENT_GUIDE.md](../TRINITY_COMPATIBLE_AGENT_GUIDE.md) | **Single-agent guide** — Creating Trinity-compatible agents, template structure, Four Pillars, planning system |
| [MULTI_AGENT_SYSTEM_GUIDE.md](../MULTI_AGENT_SYSTEM_GUIDE.md) | **Multi-agent guide** — Building coordinated multi-agent systems, architecture patterns, shared folders, deployment |

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
