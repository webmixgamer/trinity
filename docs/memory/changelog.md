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
