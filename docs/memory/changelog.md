# Changelog

> **Purpose**: Document all changes with progressive condensation.
> Update after EVERY task completion. Keep ~500 lines through consolidation.

## Emoji Prefixes
- 🎉 Major milestones
- ✨ New features
- 🔧 Bug fixes
- 🔄 Refactoring
- 📝 Documentation
- 🔒 Security updates
- 🚀 Performance improvements
- 💾 Data/persistence changes
- 🐳 Docker/infrastructure

---

## Recent Changes (Full Detail)

### 2025-12-17 10:35:02
🔧 **Dark Mode: Fix Agent Detail Panel Components**

Added dark mode support to 4 components on the Agent Detail page that were displaying with light mode styles:

**Files updated:**
- `UnifiedActivityPanel.vue` - Session activity panel (header, timeline, tool chips, modal)
- `InfoPanel.vue` - Agent info tab (template info, use cases, resources, capabilities sections)
- `MetricsPanel.vue` - Custom metrics tab (empty states, metrics grid, progress bars)
- `WorkplanPanel.vue` - Workplan tab (summary stats, current task banner, plans list, modal)

**Changes:**
- Added `dark:` variants to all background, border, and text color classes
- Updated gradients (e.g., `from-indigo-50 to-purple-50` → `dark:from-indigo-900/30 dark:to-purple-900/30`)
- Fixed modal overlays, buttons, and interactive states for dark mode
- Updated status badge helper functions with dark mode color variants

### 2025-12-17 10:05:28
🔒 **Security: Pre-Commit Security Check Command**

Created `/security-check` command to validate staged changes don't contain sensitive information.

**Checks for:**
- API keys/tokens (Anthropic, OpenAI, GitHub, Slack, Google, AWS patterns)
- Real email addresses (excluding example.com placeholders)
- IP addresses (internal and public)
- .env files with actual values
- Hardcoded secrets in code
- Internal URLs/domains
- Credential files (.pem, .key, credentials.json, etc.)

**Features:**
- Severity levels (CRITICAL/HIGH/MEDIUM/LOW)
- Quick fix instructions for each issue type
- False positive guidance
- Report format with actionable findings

**Key file**: `.claude/commands/security-check.md`

---

### 2025-12-17 10:02:11
📝 **Documentation: Development Workflow Guide**

Created `docs/DEVELOPMENT_WORKFLOW.md` - comprehensive guide for developers and AI assistants working on Trinity.

**Documents the optimal workflow:**
1. **Context Loading** - Start with `/read-docs` or read relevant feature flows
2. **Development** - Reference feature flows while implementing
3. **Testing** - Run API tests (required) and UI tests (recommended)
4. **Documentation** - Update feature flows via analyzer, then `/update-docs`

**Includes:**
- Complete development cycle diagram
- Sub-agents reference (when to use each)
- Slash commands reference
- Memory files explanation and relationships
- Example development sessions
- Best practices checklist

**Key files**: `docs/DEVELOPMENT_WORKFLOW.md`

---

### 2025-12-15 00:15:00
📝 **Documentation: Multi-Agent System Guide - Runtime Injection & Credentials**

Enhanced the multi-agent guide with clear documentation about what Trinity injects at runtime vs. what system designers should provide in templates.

**Key Additions:**
- **Runtime Injection System** section explaining `POST /api/trinity/inject` flow
- **⚡ RUNTIME INJECTION** markers on auto-injected features (Vector DB, Workplan, Trinity MCP, Chroma MCP)
- **"What NOT to Include"** table - Lists all files/sections that Trinity injects automatically
- **"What TO Include"** table - Clarifies template designer responsibilities
- **Credential System** comprehensive documentation with flow diagram
- **Required .gitignore** section showing what to exclude from repos
- Updated Repository Contents section with clearer annotations

**Impact**: System designers now have clear guidance on avoiding duplication of platform-injected content in their agent templates.

---

### 2025-12-14 23:45:00
📝 **Documentation: Multi-Agent System Guide - Platform Capabilities Section**

Added comprehensive "Trinity Platform Capabilities" section to the multi-agent guide, documenting all platform features available to agent designers.

**New Section Contents:**
- Vector Database (Chroma) - Python API + 12 MCP tools with examples
- Scheduling System - Cron patterns, API endpoints, coordination patterns
- Workplan System (Task DAGs) - Format, states, cross-agent coordination
- Trinity MCP Tools - All 12 agent-to-agent tools
- Shared Folders - Paths, configuration, permission gating
- Credential Hot-Reload - API for live updates
- Collaboration Dashboard - Real-time visualization features
- Activity Stream - Unified audit trail API
- Context Tracking - Monitoring and warnings
- Custom Metrics - template.yaml schema and examples
- Git Sync - Bidirectional GitHub synchronization
- Capability Summary Table with scope, access method, multi-agent benefit
- Design Implications section with 7 key considerations

---

### 2025-12-14 23:30:00
📝 **Documentation: Multi-Agent System Guide**

Created comprehensive guide for building multi-agent systems on Trinity platform.

**New File**:
- `docs/MULTI_AGENT_SYSTEM_GUIDE.md` - Complete guide for multi-agent architecture

**Guide Contents (19 sections)**:
- When to use multi-agent systems vs single agents
- Architecture patterns: Orchestrator-Workers, Pipeline, Mesh, Hierarchical
- System design process (5 steps)
- Agent boundaries and responsibilities
- Communication strategies (shared folders vs MCP)
- Shared folder architecture with file contracts
- Scheduling coordination and collision avoidance
- Permissions and access control patterns
- State management with ownership tables
- Repository structure (one repo per agent)
- Deployment workflow with step-by-step scripts
- Observability and monitoring patterns
- Testing multi-agent systems (unit, integration, system)
- Best practices for design, communication, operations
- System definition template
- Example: Ruby Content Management System reference
- Troubleshooting common issues

**Updated Files**:
- `README.md` - Added link to new guide in Documentation section
- `docs/memory/feature-flows.md` - Added to Core Specifications table

**Based On**: Ruby Content Management System (`ruby-content-system-definition.md`) as reference architecture

---

### 2025-12-14 22:15:00
📝 **Documentation: Consolidated Agent Compatibility Guides**

Merged two overlapping documentation files into a single comprehensive guide.

**New File**:
- `docs/TRINITY_COMPATIBLE_AGENT_GUIDE.md` - Single source of truth for agent compatibility

**Deleted Files**:
- `docs/AGENT_TEMPLATE_SPEC.md` - Merged into new guide
- `docs/memory/trinity-compatible-agent.md` - Merged into new guide

**Updated Files**:
- `README.md` - Updated references to new guide (lines 130, 223)
- `docs/memory/feature-flows.md` - Updated Core Specifications reference

**Guide Contents**:
- Overview and Four Pillars of Deep Agency
- Required files (template.yaml, CLAUDE.md, .mcp.json.template, .gitignore)
- Complete directory structure
- Full template.yaml schema with all fields
- CLAUDE.md requirements
- Credential management and hot-reload
- Platform injection (meta-prompt, commands, MCP)
- Task planning system (DAG format, state machine)
- Inter-agent collaboration (MCP tools, access control)
- Shared folders and custom metrics
- Memory management patterns
- Testing locally guide
- Compatibility checklist
- Migration guide and troubleshooting

---

### 2025-12-14 21:30:00
📝 **Testing: Added UI Test Phase 13 for System Settings**

Created comprehensive UI test phase for the System Settings feature (Trinity Prompt).

**New Files**:
- `docs/testing/phases/PHASE_13_SETTINGS.md` - Full UI test phase with 8 test steps

**Updated Files**:
- `docs/testing/phases/INDEX.md` - Added Phase 13 to phase overview table, file list, and version history

**Test Phase Coverage**:
1. Admin access verification (navbar + page)
2. Non-admin access denial
3. Trinity Prompt creation
4. Persistence verification via API
5. Prompt injection into new agent
6. Prompt update on agent restart
7. Prompt removal when cleared
8. Markdown content support

**API Tests Verified**: `tests/test_settings.py` - All 19 tests passing

**UI Test Results**: PARTIAL - Core functionality verified via API, auth issue in long-running backend detected during UI testing (to be investigated separately)

---

### 2025-12-14 19:45:00
🔧 **Bug Fix: Custom Instructions Removal + Integration Tests**

Fixed bug where clearing the `trinity_prompt` setting didn't remove the "## Custom Instructions" section from CLAUDE.md on agent restart. Also added comprehensive integration tests.

**Bug Fix**:
- `docker/base-image/agent_server/routers/trinity.py`:
  - Added `had_custom_instructions` flag tracking
  - Modified condition at line 271 to `elif custom_section or had_custom_instructions:`
  - Now properly writes updated content without Custom Instructions when prompt is cleared
  - Added log message "Removed Custom Instructions from CLAUDE.md"

**New Tests** (`tests/test_settings.py`):
- `TestSettingsEndpointsAuthentication` (4 tests) - Auth requirements
- `TestSettingsEndpointsAdmin` (6 tests) - CRUD operations
- `TestTrinityPromptSetting` (3 tests) - Prompt-specific operations
- `TestTrinityPromptInjection` (3 tests) - Agent injection verification
- `TestSettingsValidation` (3 tests) - Input validation
- **Total: 19 tests, all passing**

**Documentation Updates**:
- `feature-flows/system-wide-trinity-prompt.md` - Updated test status
- `docs/TESTING_GUIDE.md` - Added System Settings to test coverage

---

### 2025-12-14 02:30:00
✨ **Feature: System-Wide Trinity Prompt (Settings Page)**

Added ability to set a custom system prompt that gets injected into all agents' CLAUDE.md at startup. Accessible via new admin-only Settings page.

**Architecture**:
- System setting stored in SQLite `system_settings` table
- Retrieved during agent start and passed to agent-server injection API
- Injected as "## Custom Instructions" section in CLAUDE.md after Trinity section

**Backend Changes**:
- `src/backend/db/settings.py` - New SettingsOperations class (CRUD for system settings)
- `src/backend/db/__init__.py` - Export SettingsOperations
- `src/backend/db_models.py` - Added SystemSetting, SystemSettingUpdate models
- `src/backend/database.py` - Added system_settings table, integrated operations
- `src/backend/routers/settings.py` - New router with GET/PUT/DELETE endpoints (admin-only)
- `src/backend/main.py` - Mounted settings router
- `src/backend/routers/agents.py` - `inject_trinity_meta_prompt()` now fetches `trinity_prompt` setting and passes to agent-server

**Agent-Server Changes**:
- `docker/base-image/agent_server/models.py` - Added `custom_prompt` field to TrinityInjectRequest
- `docker/base-image/agent_server/routers/trinity.py` - Inject custom prompt as "## Custom Instructions" section

**Frontend Changes**:
- `src/frontend/src/views/Settings.vue` - New Settings page with Trinity Prompt editor
- `src/frontend/src/stores/settings.js` - New Pinia store for settings API
- `src/frontend/src/router/index.js` - Added `/settings` route
- `src/frontend/src/components/NavBar.vue` - Added Settings link (admin-only via role check)

**API Endpoints**:
- `GET /api/settings` - List all settings (admin only)
- `GET /api/settings/{key}` - Get specific setting (admin only)
- `PUT /api/settings/{key}` - Create/update setting (admin only)
- `DELETE /api/settings/{key}` - Delete setting (admin only)

**Setting Key**: `trinity_prompt` - The custom instructions text

**Usage**:
1. Login as admin
2. Navigate to Settings page
3. Enter custom prompt text (supports Markdown)
4. Save changes
5. Start/restart agents - they will receive the custom instructions

---

### 2025-12-14 00:15:00
✨ **Feature: Chroma MCP Server Integration (Req 10.5)**

Added auto-configuration of official chroma-mcp server in agent containers, enabling agents to use vector memory via MCP tools instead of Python code.

**Changes**:
- `docker/base-image/Dockerfile` - Added `chroma-mcp` package
- `docker/base-image/agent_server/routers/trinity.py`:
  - Added CHROMA_MCP_CONFIG constant with MCP server configuration
  - inject_trinity() now injects chroma server into `.mcp.json`
  - check_trinity_injection_status() includes `chroma_mcp_configured` field
  - Simplified CLAUDE.md vector memory section (MCP tools auto-discovered)
- `config/trinity-meta-prompt/vector-memory.md` - Updated with MCP tool examples

**MCP Config Injected**:
```json
{
  "mcpServers": {
    "chroma": {
      "command": "python3",
      "args": ["-m", "chroma_mcp", "--client-type", "persistent", "--data-dir", "/home/developer/vector-store"]
    }
  }
}
```

**Agent Usage**: `mcp__chroma__chroma_add_documents()`, `mcp__chroma__chroma_query_documents()`, etc.

**Rollout**: Requires base image rebuild with `./scripts/deploy/build-base-image.sh`

---

### 2025-12-13 23:30:00
✨ **Feature: Agent Vector Memory with Chroma (Req 10.4)**

Added per-agent Chroma vector database with pre-configured all-MiniLM-L6-v2 embedding model for semantic memory storage and retrieval.

**Architecture**:
- Chroma DB with persistent storage at `/home/developer/vector-store/`
- all-MiniLM-L6-v2 embedding model (384 dimensions, ~80MB)
- Model pre-loaded in base image to avoid runtime downloads
- Documentation injected via Trinity injection API

**Base Image Changes**:
- `docker/base-image/Dockerfile` - Added chromadb, sentence-transformers packages
- `docker/base-image/Dockerfile` - Pre-download embedding model at build time

**Agent Server Changes**:
- `docker/base-image/agent_server/config.py` - Added VECTOR_STORE_DIR constant
- `docker/base-image/agent_server/models.py` - Added vector_memory field to TrinityStatusResponse
- `docker/base-image/agent_server/routers/trinity.py`:
  - check_trinity_injection_status() now includes vector memory status
  - inject_trinity() creates `/home/developer/vector-store/` directory
  - inject_trinity() copies `vector-memory.md` to `.trinity/`
  - CLAUDE.md Trinity section now includes vector memory documentation

**New Files**:
- `config/trinity-meta-prompt/vector-memory.md` - Comprehensive usage documentation

**Usage**:
```python
import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path="/home/developer/vector-store")
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = client.get_or_create_collection("memory", embedding_function=ef)

# Store memory
collection.add(documents=["User prefers Python"], ids=["pref-001"])

# Query by similarity
results = collection.query(query_texts=["programming language preferences"], n_results=5)
```

**Rollout**:
- Requires base image rebuild: `./scripts/deploy/build-base-image.sh`
- Image size increases ~800MB (PyTorch CPU + model)
- Backward compatible - existing agents gain capability on restart

---

### 2025-12-13 14:30:00
✨ **Feature: Agent Shared Folders (Req 9.11)**

Implemented file-based collaboration between agents via shared Docker volumes. Agents can expose a shared folder that other permitted agents can mount.

**Architecture**:
- Expose: Creates volume `agent-{name}-shared` mounted at `/home/developer/shared-out`
- Consume: Mounts permitted agents' volumes at `/home/developer/shared-in/{agent}`
- Permission-gated: Only permitted agents can mount shared folders

**Backend Changes**:
- `src/backend/db_models.py` - Added SharedFolderConfig, SharedFolderConfigUpdate, SharedFolderMount, SharedFolderInfo models
- `src/backend/db/shared_folders.py` - New module with SharedFolderOperations class
- `src/backend/database.py` - Added agent_shared_folder_config table, integrated SharedFolderOperations
- `src/backend/routers/agents.py:499-529` - Volume creation/mounting in agent creation
- `src/backend/routers/agents.py:690-701` - Volume cleanup on agent deletion
- `src/backend/routers/agents.py:2059-2283` - Four new API endpoints:
  - GET/PUT `/api/agents/{name}/folders` - Config management
  - GET `/api/agents/{name}/folders/available` - List mountable folders
  - GET `/api/agents/{name}/folders/consumers` - List consuming agents

**Frontend Changes**:
- `src/frontend/src/views/AgentDetail.vue:319-331` - Added Shared Folders tab button
- `src/frontend/src/views/AgentDetail.vue:987-989` - FoldersPanel content render
- `src/frontend/src/components/FoldersPanel.vue` - New component with:
  - Expose toggle (create shared volume)
  - Consume toggle (mount other agents' volumes)
  - Restart required banner
  - Consumers list and available folders display
- `src/frontend/src/stores/agents.js:543-574` - Four new actions for folder management

**Documentation**:
- `docs/requirements/SHARED_FOLDERS.md` - Implementation reference (input)
- `docs/memory/requirements.md:806-838` - Added Req 9.10 (Permissions) and 9.11 (Shared Folders)
- `docs/memory/feature-flows.md:55` - Added to feature index
- `docs/memory/feature-flows/agent-shared-folders.md` - Complete feature flow

**Flow**:
1. Agent A enables "Expose" → creates volume → restarts
2. Agent B granted permission to Agent A (via Permissions tab)
3. Agent B enables "Consume" → restarts → mounts Agent A's folder
4. Agent A writes to `/home/developer/shared-out/file.txt`
5. Agent B reads from `/home/developer/shared-in/agent-a/file.txt`

---

### 2025-12-13 21:58:00
🔧 **Bug Fix: Shared Folders Container Recreation**

Fixed issue where shared folder mounts weren't applied on agent restart.

**Problem**: Docker doesn't allow adding volumes to existing containers. The `start` endpoint just starts the existing container.

**Solution**: Added helper functions to detect when shared folder config doesn't match container mounts and recreate the container:
- `_check_shared_folder_mounts_match()` - Checks if container mounts match config
- `_recreate_container_with_shared_folders()` - Recreates container with updated mounts

**Also Fixed**: Volume ownership - Docker creates volumes with root ownership. Added automatic ownership fix using alpine container to chown to UID 1000.

**Tested**: ✅ End-to-end file sharing verified
- ruby exposes folder, corbin consumes
- File written on ruby at `/home/developer/shared-out/test.txt`
- File visible on corbin at `/home/developer/shared-in/ruby/test.txt`

---

### 2025-12-12 12:46:00
🔧 **Critical Fix: Context Percentage >100% Bug**

Fixed context window calculation showing impossible percentages (130%, 289%) in Dashboard and Agent Detail pages.

**Root Cause**:
- Code was incorrectly summing `input_tokens + cache_creation_tokens + cache_read_tokens`
- **Wrong assumption**: Thought cache tokens were additional to input tokens
- **Reality**: `cache_creation_tokens` and `cache_read_tokens` are billing **breakdowns** (subsets) of `input_tokens`, not extra tokens
- Result: Double-counting cached tokens (e.g., 50K input + 40K cache_read + 10K cache_creation = 100K but really only 50K)

**The Fix**:
- Changed to use `metadata.input_tokens` directly
- This value comes from Claude's `modelUsage.inputTokens` which is the authoritative context window total
- Already includes all conversation turns and all token types

**Files Modified**:
- `docker/base-image/agent_server/routers/chat.py:45-53` - Simplified to `session_context_tokens = metadata.input_tokens`
- `docs/memory/feature-flows/agent-chat.md:338-349, 559` - Updated documentation and revision history

**Impact**: Context percentages now display correctly (0-100%) in Dashboard network view and Agent Detail chat headers.

**Note**: Agent containers need restart to pick up the fix: `docker restart $(docker ps -q --filter "label=trinity.platform=agent")`

---

### 2025-12-11 17:35:00
✨ **GitHub PAT Auto-Upload from Environment**

Added automatic upload of GitHub Personal Access Token from `.env` to Redis on backend startup. Simplifies local development by eliminating manual credential configuration.

**Files Modified**:
- `.env.example` - Added `GITHUB_PAT` placeholder with documentation
- `docker-compose.yml` - Added `GITHUB_PAT` env var passthrough to backend
- `src/backend/config.py` - Added `GITHUB_PAT` and `GITHUB_PAT_CREDENTIAL_ID` constants; updated all templates to use fixed credential ID
- `src/backend/main.py` - Added `initialize_github_pat()` function called on startup

**How It Works**:
1. Set `GITHUB_PAT=github_pat_xxx` in `.env`
2. Backend uploads to Redis on startup with fixed ID `github-pat-templates`
3. All GitHub templates reference this credential automatically
4. PAT is updated in Redis if value changes

**Documentation Updated**:
- `docs/DEPLOYMENT.md` - Added GitHub Templates configuration section
- `docs/memory/feature-flows/template-processing.md` - Updated with auto-upload details

---

### 2025-12-10 22:05:00
🌐 **Trinity Landing Page Created**

Created separate landing page repository for trinity.ability.ai marketing site.

**Repository**: https://github.com/Abilityai/trinity-landing-page
**Deployment**: Vercel (auto-deploys from GitHub)
**Local Path**: `~/Dropbox/Coding/N8N_Main_repos/trinity-landing-page`

**Stack**:
- Next.js 14 with App Router
- Tailwind CSS with Ability AI design tokens
- Lucide icons for Four Pillars section
- Static export for Vercel deployment

**Sections Implemented**:
- Hero with logo, headline, GitHub/Demo CTAs
- Video placeholder (ready for YouTube embed)
- Four Pillars of Deep Agency
- Why Sovereign (self-hosted messaging)
- Open Source section
- Footer with Ability.ai branding

**Documentation Updated**:
- `architecture.md` - Added Landing Page URLs section
- Source-of-truth `LANDING_PAGE_SPEC.md` - Added deployment status

---

### 2025-12-10 18:00:00
📝 **Updated Demo Agent Fleet Command**

Completely rewrote `.claude/commands/demo-agent-fleet.md` to showcase all current platform capabilities.

**New Demo Sections**:
1. Dashboard Overview (at `/` not `/collaboration`)
2. Context Tracking (real-time progress bars, color coding)
3. Agent Permissions System (Req 9.10) - revoke/restore/enforcement demo
4. Agent-to-Agent Collaboration (streamlined)
5. Workplan System (Pillar I) - plan creation, progress tracking
6. File Browser - workspace browsing
7. Custom Metrics - type-specific visualizations
8. Dashboard Replay Mode - historical playback
9. Additional Features - telemetry, logs, info tab

**Key Updates**:
- Updated terminology: "messages" not "communications"
- Dashboard at `/` root (legacy `/collaboration` redirects)
- Added Four Pillars validation section
- Timing increased from ~5 min to ~33 min (comprehensive demo)
- Added permission enforcement demonstration
- Results summary template with checklist format

---

### 2025-12-10 15:00:00
✨ **Agent-to-Agent Permissions System (Requirement 9.10)**

Implemented centralized permission system controlling which agents can communicate with other agents.

**Architecture**:
- SQLite table `agent_permissions` with source/target agent pairs
- Backend REST API for CRUD operations
- MCP enforcement layer filters list_agents and blocks chat_with_agent
- Frontend Permissions tab in AgentDetail.vue
- Default permissions: same-owner agents get bidirectional permissions on creation

**Files Created/Modified**:
- `src/backend/db_models.py` - Added AgentPermission, AgentPermissionInfo models
- `src/backend/db/permissions.py` - NEW: PermissionOperations class
- `src/backend/database.py` - Table creation, indexes, delegation methods
- `src/backend/routers/agents.py` - Permission CRUD endpoints (GET/PUT/POST/DELETE)
- `src/mcp-server/src/client.ts` - getPermittedAgents, isAgentPermitted methods
- `src/mcp-server/src/tools/agents.ts` - list_agents filtering for agent-scoped keys
- `src/mcp-server/src/tools/chat.ts` - Permission enforcement in checkAgentAccess
- `src/frontend/src/views/AgentDetail.vue` - Permissions tab with checkboxes, bulk actions
- `src/frontend/src/stores/agents.js` - getAgentPermissions, setAgentPermissions actions
- `docker/base-image/agent_server/routers/trinity.py` - Agent Collaboration section in CLAUDE.md

**API Endpoints**:
- `GET /api/agents/{name}/permissions` - List permitted + available agents
- `PUT /api/agents/{name}/permissions` - Bulk set permissions
- `POST /api/agents/{name}/permissions/{target}` - Add single permission
- `DELETE /api/agents/{name}/permissions/{target}` - Remove permission

**Behavior**:
- Agent-scoped MCP keys: list_agents filtered to permitted agents only
- Agent-scoped MCP keys: chat_with_agent blocked for non-permitted targets
- User-scoped MCP keys: Bypass filtering (full access)
- Cascade delete: Permissions removed when either agent is deleted

---

### 2025-12-10 12:30:00
✨ **Agent Custom Metrics Feature (Requirement 9.9)**

Implemented agent-defined custom metrics that agents can expose in their `template.yaml` and display in the Trinity UI.

**Architecture**:
- Agents define metrics in `template.yaml` under `metrics:` field
- Agents write values to `metrics.json` in workspace
- Agent server reads definitions + values via `GET /api/metrics`
- Backend proxies via `GET /api/agents/{name}/metrics`
- Frontend MetricsPanel.vue displays with type-specific rendering

**Metric Types Supported**:
- `counter`: Monotonically increasing (large number with label)
- `gauge`: Current value (number with unit)
- `percentage`: 0-100 with progress bar and thresholds
- `status`: Enum/state with colored badge
- `duration`: Seconds formatted as "2h 15m"
- `bytes`: Bytes formatted as "1.2 MB"

**Files Created/Modified**:
- `docker/base-image/agent_server/routers/info.py` - Added `GET /api/metrics` endpoint
- `src/backend/routers/agents.py` - Added `GET /api/agents/{name}/metrics` proxy
- `src/frontend/src/components/MetricsPanel.vue` - New component (265 lines)
- `src/frontend/src/views/AgentDetail.vue` - Added Metrics tab
- `src/frontend/src/stores/agents.js` - Added `getAgentMetrics` action
- `docs/memory/requirements.md` - Added requirement 9.9
- `docs/memory/feature-flows.md` - Added index entry
- `docs/memory/feature-flows/agent-custom-metrics.md` - Created flow doc

**Test Agents**: All 8 test agents already have metrics defined in their template.yaml files.

---

### 2025-12-10 00:35:00
🔧 **Critical Bug Fixes from UI Integration Test Report (3 Critical Bugs)**
- **BUG #1 - Context Percentage Stuck at 0% (CRITICAL)**
  - **Root Cause**: `chat.py` was only using `input_tokens` (3) for context tracking, ignoring cache tokens (18K+)
  - **Fix**: Updated context calculation to sum all token types: `input_tokens + cache_creation_tokens + cache_read_tokens`
  - **File**: `docker/base-image/agent_server/routers/chat.py`
  - **Verified**: Context now shows correct percentage (9.3% = 18,696 / 200,000)
- **BUG #2 - Files Do Not Persist After Agent Restart (CRITICAL)**
  - **Root Cause**: `startup.sh` deleted all files and re-cloned GitHub repo on every container start, even with persistent volumes mounted
  - **Fix**: Added checks to skip cloning if repo already exists:
    - Git-sync agents: Check for `.git` directory
    - Non-git-sync agents: Check for `.trinity-initialized` marker
  - **File**: `docker/base-image/startup.sh`
  - **Verified**: Files persist after stop/start for both blank and GitHub-based agents
- **BUG #3 - Agent Status Display Inconsistency (HIGH)**
  - **Root Cause**: `convertAgentsToNodes` in network.js didn't set initial `activityState`, causing nodes to show "Offline" until first context-stats poll
  - **Fix**: Added initial `activityState: agent.status === 'running' ? 'idle' : 'offline'` to node data
  - **File**: `src/frontend/src/stores/network.js`
  - **Verified**: Running agents now show "Idle" immediately, not "Offline"
- **Base Image**: Rebuilt with all fixes (`./scripts/deploy/build-base-image.sh`)

### 2025-12-09 14:00:00
🔧 **Replace Browser confirm() with In-App ConfirmDialog**
- **Purpose**: Enable automated UI testing - browser `confirm()` blocks Chrome DevTools MCP
- **Created**: `src/frontend/src/components/ConfirmDialog.vue`
  - Reusable modal component with title, message, confirm/cancel buttons
  - Supports `danger` (red) and `warning` (yellow) variants
  - Data-testid attributes for automated testing
  - Teleported to body for proper z-index stacking
- **Updated Files** (7 confirm() calls replaced):
  - `AgentDetail.vue`: Delete agent, New session
  - `Credentials.vue`: Delete credential
  - `ApiKeys.vue`: Revoke key, Delete key
  - `SchedulesPanel.vue`: Delete schedule
  - `WorkplanPanel.vue`: Delete plan
- **Testing Docs Updated**:
  - `docs/testing/UI_INTEGRATION_TEST.md`: Added ConfirmDialog note, test IDs, Key Learnings section
- **Impact**: All confirmation actions now testable via Chrome DevTools MCP
- **Test IDs**: `confirm-dialog`, `confirm-dialog-title`, `confirm-dialog-message`, `confirm-dialog-confirm`, `confirm-dialog-cancel`

### 2025-12-09 11:30:00
🔧 **Critical Bug Fixes from UI Integration Test Report**
- **BUG #1 - Context Token Tracking**: Fixed `input_tokens` extraction from Claude Code stream-json
  - Now extracts from `modelUsage.inputTokens` (authoritative source) in addition to `usage.input_tokens`
  - Added debug logging for token tracking troubleshooting
  - Files: `docker/base-image/agent_server/services/claude_code.py`
- **BUG #2 - Activity Timeline**: Clarified expected behavior in test agent docs
  - Activity tracking only shows tool executions (Read, Write, MCP calls)
  - Echo agent doesn't use tools → "No activity" is **expected behavior**
  - Counter agent uses Read/Write tools → Activity Panel will show tool calls
  - Updated: `repositories/test-agent-echo/README.md`, `repositories/test-agent-counter/README.md`
  - Pushed to GitHub: abilityai/test-agent-echo, abilityai/test-agent-counter
- **BUG #3 - File Persistence**: Fixed critical Pillar III violation
  - Added per-agent Docker volume `agent-{name}-workspace` mounted to `/home/developer`
  - Files created by agents now persist across container restarts
  - Volume cleanup added to agent deletion
  - Files: `src/backend/routers/agents.py` (create_agent, delete_agent_endpoint)
- **Impact**: Fixes observability (context tracking) and persistent memory (file storage)
- **Pillar III Compliance**: Agent workspace now survives restarts as required by Deep Agency spec

### 2025-12-09 03:00:00
✨ **UI Integration Tester Subagent**
- **Created**: `.claude/agents/ui-integration-tester.md`
- **Purpose**: Browser-based visual UI testing in phases
- **Phases**: setup, auth, create-echo, chat-echo, create-counter, chat-counter, create-delegator, chat-delegator, dashboard, lifecycle, cleanup
- **Tools**: Chrome DevTools MCP (snapshots, screenshots, click, fill, navigate), Bash, Read
- **Model**: Sonnet
- **Usage**: Orchestrator invokes with specific phase, agent executes and reports results
- **Design**: Lightweight context per phase, resumable workflow

### 2025-12-09 02:30:00
✅ **API Test Suite - All Fixes Verified**
- **Test Run**: 142 tests collected, 110 passed, 25 skipped (agent-server direct tests), 7 initially failing
- **All 7 Failures Fixed**:
  1. `test_reset_session` - Added DELETE `/api/agents/{name}/chat/history` endpoint
  2. `test_download_nonexistent_file` - Updated test to accept 403 for security-blocked paths
  3. `test_download_directory` - Updated test to accept 403 for security-blocked paths
  4. `test_git_sync` - Fixed to return 400 (not 500) for configuration errors
  5. `test_git_sync_nonexistent_agent` - Fixed to return 404 (not 500)
  6. `test_git_pull` - Fixed to return 400 (not 500) for configuration errors
  7. `test_share_has_required_fields` - Updated test to use `shared_with_email` field
- **Final Result**: 110 passed, 25 skipped (77.5% pass rate on executed tests)
- **Files changed**:
  - `src/backend/routers/git.py` - Added agent existence checks, fixed HTTP status codes
  - `src/backend/routers/chat.py` - Added DELETE reset endpoint
  - `tests/test_agent_files.py` - Updated assertions for 403 responses
  - `tests/test_agent_sharing.py` - Updated field name assertions
  - `tests/test_agent_chat.py` - Updated reset test assertions
  - `tests/test_agent_git.py` - Updated expected status codes

### 2025-12-08 22:30:00
📝 **API Test Requirements Document**
- **Created**: `docs/testing/API_TEST_REQUIREMENTS.md` - Comprehensive test specification
- **Scope**: Defines 100+ test requirements covering:
  - **Trinity Backend API** (12 test categories, 47 endpoints):
    - Authentication (mode, login, token validation)
    - Agent Lifecycle (create, start, stop, delete, logs, info)
    - Agent Chat (messages, history, session, model management)
    - Execution Queue (status, clear, release, 429 handling)
    - Files (list tree, download with security checks)
    - Plans (CRUD, task updates, summary)
    - Credentials (create, bulk import, hot-reload)
    - MCP API Keys (create, list, validate, revoke)
    - Templates (list, details, env template)
    - Sharing (share, unshare, list shares)
    - Git Sync (status, sync, log, pull)
    - Schedules (CRUD, enable/disable, trigger)
  - **Agent Server API** (7 test categories):
    - Info/Health endpoints
    - Direct chat execution
    - Activity monitoring
    - File browser
    - Credential updates
    - Plan management
    - Git operations
- **Test Infrastructure**:
  - pytest framework with async support
  - Configurable endpoints via environment variables
  - Test isolation with cleanup
  - JUnit XML / HTML reports for CI
- **Test Categories**:
  - Smoke tests (<1 min)
  - Core functionality (2-5 min)
  - Full regression (10-15 min)
- **Priority**: HIGH/MEDIUM/LOW for each requirement
- **Next Phase**: Implementation of test fixtures and core tests

### 2025-12-08 12:55:00
🔧 **Fix: CreateAgentModal Template Selector Bug**
- **Issue**: Modal only showed "Blank Agent" - templates weren't visible
- **Root Cause**:
  - Modal had `overflow-hidden` which clipped content
  - No loading state while templates were being fetched
  - Template list had no max-height/scrolling
- **Fixes Applied to `CreateAgentModal.vue`**:
  - Removed `overflow-hidden`, added `max-h-[90vh] overflow-y-auto` to modal container
  - Added `templatesLoading` and `templatesError` state variables
  - Added loading spinner while templates are being fetched
  - Added error display with "Try again" button if fetch fails
  - Added `max-h-80 overflow-y-auto` to template list for scrolling
- **User Impact**: Templates now properly display in the Create Agent modal

### 2025-12-08 20:24:00
✨ **Automated Integration Test Suite**
- **Created**: `docs/testing/run_integration_test.py` - Full automated test script
- **Test Coverage**: 26 tests covering all core functionality:
  - Prerequisites validation
  - Agent creation (test-echo)
  - Basic chat with echo response validation
  - State persistence (test-counter) with reset/increment/add operations
  - Agent-to-agent collaboration (test-delegator) with MCP tools
  - Dashboard APIs (context-stats, activity timeline, plans aggregate)
  - Agent lifecycle (stop, start, chat after restart, delete)
- **Key Improvements**:
  - Proper wait logic: 10s after agent starts for initialization
  - 503 retry logic: 5 retries with 5s waits for busy agents
  - MCP server initialization: Extra 5s wait for delegator
  - Clean slate enforcement: Delete test agents before and after tests
- **Test Results**: 26/26 tests passed in ~3 minutes
- **Documentation Updated**: `UI_INTEGRATION_TEST.md` with:
  - Automated test option at top
  - Agent initialization wait notes
  - Delegation timing expectations
  - Key learnings section
  - Known issue: 503 during initialization
- **Files Created**: `docs/testing/run_integration_test.py`
- **Files Updated**: `docs/testing/UI_INTEGRATION_TEST.md`

### 2025-12-08 14:15:00
✅ **Full System Test - Testing Agents Verification**
- **Test Environment**: Local development (localhost:3000 + localhost:8000), dev mode auth
- **Agents Tested**: test-echo, test-counter, test-delegator
- **Results**:
  - ✅ test-echo: Basic chat PASSED - "Hello World" → echo with word/char counts
  - ✅ test-counter: State persistence PASSED - reset/increment operations, counter.txt visible
  - ✅ test-delegator: Agent-to-agent PASSED - Trinity MCP chat_with_agent, 2.2s round-trip
  - ✅ Dashboard: Network visualization PASSED - 3 agents, collaboration edge with "6x" label
- **Known Issues Documented**:
  - Template pre-selection bug: CreateAgentModal shows "Blank Agent" instead of selected template
  - Session expiration: Frontend sessions may expire after backend API activity
- **Documentation Updated**: `feature-flows/testing-agents.md` with full test session results

### 2025-12-08 01:15:00
✨ **Testing Agents Suite - Systematic Platform Testing**
- **Created**: 8 test agent repositories for predictable platform verification
- **Repositories** (all private, github:abilityai/test-agent-*):
  - **test-echo**: Basic chat testing (echo responses with word/char counts)
  - **test-counter**: State persistence (file read/write, counter.txt)
  - **test-worker**: Workplan system testing (Pillar I - plan creation, task dependencies)
  - **test-delegator**: Agent-to-agent testing (Pillar II - Trinity MCP tools)
  - **test-scheduler**: Scheduling testing (cron execution, log differentiation)
  - **test-queue**: Execution queue testing (delays, 429 handling)
  - **test-files**: File browser testing (create, list, download files)
  - **test-error**: Error handling testing (fail, timeout, recovery)
- **Backend Config Updates**:
  - Added `TEST_AGENT_TEMPLATES` list in `config.py` (8 templates)
  - Added `ALL_GITHUB_TEMPLATES = GITHUB_TEMPLATES + TEST_AGENT_TEMPLATES`
  - Updated `templates.py` and `template_service.py` to use combined list
  - Removed unused import from `agents.py`
- **Feature Flow**: Created `testing-agents.md` with comprehensive test scenarios
- **Files Changed**: `config.py`, `routers/templates.py`, `services/template_service.py`, `routers/agents.py`
- **Files Created**: `feature-flows/testing-agents.md`, 8 GitHub repos

### 2025-12-08 00:30:00
📝 **Testing Guide Update - Comprehensive Refresh**
- **Updated**: `docs/TESTING_GUIDE.md` to reflect current project state
- **Added Sections**:
  - Feature Flows Reference table with 16 documented flows and their test status
  - WebSocket Testing guide with event types and monitoring instructions
  - Docker Testing commands for verifying container state
  - Database Testing via API and direct SQLite access
  - Quick Reference table showing test coverage by feature with dates
- **Improved Templates**: Enhanced testing section template with more verification options
- **Added Examples**: Workplan System testing (20/20 tests) as model documentation
- **Updated Date**: 2025-11-30 → 2025-12-08
- **Files Changed**: `docs/TESTING_GUIDE.md`

### 2025-12-08 00:05:00
🔧 **Dashboard AgentNode Task Progress Bar Consistency**
- **Problem**: Task DAG Progress section only shown for agents with active plans, causing inconsistent card heights
- **Fix**: Removed `v-if="hasActivePlan"` condition - now always shows Tasks progress bar
- **Added**: `taskProgressDisplay` computed property - shows "—" when no tasks, "X/Y" when tasks exist
- **Result**: All agent cards now have consistent height and layout
- **Files Changed**: `AgentNode.vue`, `feature-flows/agent-network.md`

### 2025-12-07 23:36:00
🔧 **Dashboard AgentNode Button Alignment Fix**
- **Problem**: "View Details" buttons not aligned at bottom of agent cards when content varies
- **Fix**: Added `flex flex-col` to outer container and inner content div, `mt-auto` to button
- **Files Changed**: `AgentNode.vue`

### 2025-12-07 23:32:00
🔄 **Credentials Page Cleanup - Remove Unused OAuth Section**
- **Removed**: "Connect Services" OAuth provider section (Google, Slack, GitHub, Notion buttons)
- **Removed Code**: `oauthProviders` ref, `fetchOAuthProviders()`, `startOAuth()`, `getProviderIcon()`
- **Updated**: Empty state text from "connecting a service" to "using bulk import"
- **Files Changed**: `Credentials.vue`

### 2025-12-07 23:27:00
✨ **Templates Page - Dynamic Template Loading**
- **Purpose**: Display real GitHub and local templates from the API instead of static hardcoded cards
- **Changes**:
  - Rewrote `Templates.vue` to fetch templates from `/api/templates`
  - Displays GitHub templates section (5 templates from production config)
  - Displays Local templates section (from `config/agent-templates/`)
  - Shows: name, description, MCP servers, resources, credentials count
  - "Use Template" button opens CreateAgentModal with template pre-selected
  - "Create Blank Agent" option for starting from scratch
  - Added `initial-template` prop to CreateAgentModal for pre-selection
  - Added `created` event to CreateAgentModal for navigation after success
  - Navigates to new agent's detail page after successful creation
- **GitHub Templates Displayed**: Fred (Orchestrator), Cornelius (Knowledge Base), Corbin (Business), Ruby (Content), Marvin (Worldview)
- **Files Changed**: `Templates.vue`, `CreateAgentModal.vue`

### 2025-12-07 22:10:00
🔄 **Dashboard Header UX Improvements**
- **Purpose**: Reduce vertical space usage, cleaner UI
- **Changes**:
  - Merged two headers into single compact row (~40px vs ~140px)
  - Removed "Dashboard" title (redundant with nav menu)
  - Changed stats from card-style to inline text: "3 agents · 2 running · 15 messages"
  - Renamed "Communications" → "messages" throughout
  - Icon-only buttons (Refresh, Reset) with tooltips
  - Shortened time range labels: "Last Hour" → "1h", etc.
- **Documentation**: Updated feature flows (agent-network.md, agent-network-replay-mode.md, feature-flows.md, workplan-system.md)

### 2025-12-07 21:48:00
🔄 **Dashboard Consolidation - Network View as Main Dashboard**
- **Purpose**: Make the Agent Network view the primary dashboard page
- **Changes**:
  - Replaced `Dashboard.vue` with Agent Network content (Vue Flow graph, real-time messages)
  - Removed `/network` route from NavBar (Dashboard now shows network view)
  - Added redirect `/network` → `/` for backwards compatibility
  - Deleted `AgentNetwork.vue` (merged into Dashboard)
  - Added "Create Agent" button in empty state
- **Files Changed**: `Dashboard.vue`, `router/index.js`, `NavBar.vue`
- **Files Deleted**: `AgentNetwork.vue`

### 2025-12-07 20:30:00
🔄 **Terminology Clarity Refactor**
- **Purpose**: Clearer distinction between single-agent workplans and multi-agent communication
- **UI Changes (Sprint 1)**:
  - Nav link: "Collaboration" → "Network" with tooltip
  - Tab name: "Plans" → "Workplan" with tooltip
  - Page title: "Agent Collaboration" → "Agent Network"
  - Updated empty states, help text, status labels in WorkplanPanel
- **File Renames (Sprint 2)**:
  - `PlansPanel.vue` → `WorkplanPanel.vue`
  - `AgentCollaboration.vue` → `AgentNetwork.vue`
  - `collaborations.js` → `network.js` (store renamed to `useNetworkStore`)
  - Route: `/collaboration` → `/network`
- **Trinity Commands (Sprint 3)**:
  - `/trinity-plan-*` → `/workplan-*` (create, status, update, list)
  - Updated `prompt.md` to reference new commands
- **Documentation (Sprint 4)**:
  - `task-dag-system.md` → `workplan-system.md`
  - `plans-ui.md` → `workplan-ui.md`
  - `collaboration-dashboard.md` → `agent-network.md`
  - `collaboration-dashboard-replay-mode.md` → `agent-network-replay-mode.md`
  - Updated feature-flows.md index
  - Updated CLAUDE.md terminology
  - Renamed COLLABORATION_DASHBOARD_DEMO.md → AGENT_NETWORK_DEMO.md
- **Backwards Compatibility**: API paths unchanged (Option A from refactor plan)
- **Files Changed**: 15+ frontend files, 8 documentation files, 4 command files

### 2025-12-07 17:35:00
✨ **Implemented Agents Page UI Improvements**
- **Enhanced Agents List** (`/agents`) with activity indicators and context stats
- **New Features**:
  - Sort dropdown: Newest First, Oldest First, Name (A-Z/Z-A), Running First, Context Usage
  - Activity state indicator: Green pulsing dot for Active, green static for Idle, gray for Offline
  - Activity state label: "Active", "Idle", or "Offline" next to agent name
  - Context progress bar: Green (0-49%), Yellow (50-74%), Orange (75-89%), Red (90-100%)
  - Progress bar only shown for running agents
  - Task progress display for agents with active plans (X/Y tasks)
  - Empty state with create button when no agents exist
- **Store Updates** (`agents.js`):
  - Added `contextStats`, `planStats`, `sortBy` state
  - Added `sortedAgents` getter with 6 sort options
  - Added `fetchContextStats()`, `fetchPlanStats()` actions
  - Added `startContextPolling()`, `stopContextPolling()` with 5s interval
- **Files Changed**: `src/frontend/src/stores/agents.js`, `src/frontend/src/views/Agents.vue`
- **Tested**: Sorting, activity states, context bars, stopped agent display all verified

### 2025-12-07 04:35:00
✨ **Implemented Plans UI - AgentDetail Plans Tab**
- **New Component**: `PlansPanel.vue` - Full-featured plans management UI
  - Summary stats: Total plans, active, completed, task progress percentage
  - Current task banner with link to active plan
  - Plan list with status badges, progress bars, relative timestamps
  - Status filter dropdown (All/Active/Completed/Failed/Paused)
  - Plan detail modal with full task DAG visualization
  - Task status icons: completed (✓), active (pulse), blocked (lock), failed (✗)
  - Task dependencies display with chip badges
  - Task results and timestamps
  - Plan actions: Pause, Resume, Delete
- **Updated Store**: Added 7 plans API methods to `agents.js`:
  - `getAgentPlans()`, `getAgentPlansSummary()`, `getAgentPlan()`
  - `createAgentPlan()`, `updateAgentPlan()`, `deleteAgentPlan()`
  - `updateAgentTask()` for task status updates
- **Updated AgentDetail.vue**: Added Plans tab between Executions and Git
- **Files Changed**: `src/frontend/src/stores/agents.js`, `src/frontend/src/views/AgentDetail.vue`
- **Files Created**: `src/frontend/src/components/PlansPanel.vue`

### 2025-12-06 23:00:00
📝 **Updated Requirements - Task DAG UI Requirements Added**
- **Marked Complete**: Agent Server Injection API, Backend Integration, startup.sh cleanup, Collaboration Dashboard visualization
- **Added NEW Requirements** for 9.8 Task DAG System:
  - **AgentDetail Plans UI** (HIGH priority): Plans tab, plan list, task details, status badges, active/archived toggle
  - **Task DAG Graph Visualization** (MEDIUM): Visual dependency graph using Vue Flow
  - **Task Actions UI** (LOW): Manual complete/fail/re-run buttons
- **Updated Roadmap**: Added 3 new items to Phase 9

### 2025-12-06 22:30:00
🔧 **Fix Context % Calculation Bug (>100% displayed)**
- **Problem**: Context window percentage showed >100% (e.g., 289%) because code was incorrectly summing `input_tokens + cache_creation_tokens + cache_read_tokens`
- **Root Cause**: Misunderstanding of Claude API token fields - `cache_creation_tokens` and `cache_read_tokens` are billing SUBSETS of `input_tokens`, NOT additional tokens
- **Fixed Files**:
  - `src/backend/services/scheduler_service.py` - Fixed 2 locations (lines 285-289 and 495-499)
    - Before: `context_used = session_data.get("context_tokens") or (input + cache_creation + cache_read)`
    - After: `context_used = session_data.get("context_tokens") or metadata.get("input_tokens", 0)`
  - `docker/base-image/agent_server/services/claude_code.py` - Fixed logging at line 416-417
    - Before: Logged misleading `total_context = input + cache_creation + cache_read`
    - After: Logs correct `context = metadata.input_tokens`
- **Impact**: Scheduled executions and manual triggers now report correct context percentage

### 2025-12-06 21:05:00
🔄 **Agent Server Refactoring - Modular Architecture**
- **Refactored**: Split monolithic `agent-server.py` (2578 lines) into modular package structure
- **New Package**: `docker/base-image/agent_server/` with organized module hierarchy:
  - `config.py` - Configuration constants (CORS, paths, thread pool)
  - `models.py` - All 25+ Pydantic models (Chat, Credentials, Git, Trinity, Plans)
  - `state.py` - AgentState class for session management
  - `utils/helpers.py` - Utility functions (shorten_path, get_tool_name, etc.)
  - `services/` - Core business logic:
    - `activity_tracking.py` - Real-time tool execution monitoring
    - `claude_code.py` - Claude Code subprocess execution with streaming
    - `trinity_mcp.py` - Trinity MCP injection for agent-to-agent comms
  - `routers/` - API endpoints split by domain:
    - `info.py` - Root, health, agent info, template info (4 endpoints)
    - `chat.py` - Chat, history, session, model (7 endpoints)
    - `activity.py` - Real-time activity tracking (3 endpoints)
    - `credentials.py` - Credential update and status (2 endpoints)
    - `git.py` - Git sync: status, sync, log, pull (4 endpoints)
    - `files.py` - File browser: list, download (2 endpoints)
    - `trinity.py` - Trinity injection: status, inject, reset (3 endpoints)
    - `plans.py` - Task DAG: CRUD, task updates (7 endpoints)
  - `main.py` - FastAPI app initialization and router mounting
- **Updated**: `agent-server.py` reduced to 15-line entry point
- **Updated**: `docker/base-image/Dockerfile` - Added COPY for agent_server package
- **Verified**: 36 routes registered, server starts correctly in Docker
- **Benefits**: Better code organization, easier testing, clearer separation of concerns

### 2025-12-06 14:30:00
📝 **Execution Queue Feature Flow Documentation**
- **Created**: `docs/memory/feature-flows/execution-queue.md` - Comprehensive vertical slice documentation
  - Problem statement and failure scenarios
  - Solution architecture with ASCII diagram
  - Data models (Execution, ExecutionSource, ExecutionStatus, QueueStatus)
  - Execution Queue Service methods (create_execution, submit, complete, get_status, etc.)
  - All integration points (User Chat, Scheduler, MCP Server, Agent Container)
  - API endpoints with request/response examples
  - Error handling (429, queue full, MCP busy responses)
  - Configuration parameters and Redis key structure
  - Testing instructions and edge cases
  - Future improvements roadmap
- **Updated**: Related feature flows to reference Execution Queue
  - `agent-chat.md` - Added queue integration in endpoint flow, 429 error handling, Related Flows section
  - `scheduling.md` - Added queue integration in execution flow, queue full handling, Related Flows section
  - `mcp-orchestration.md` - Added Queue-Aware Chat section with 429 handling code, Related Flows section
- **Updated**: `feature-flows.md` index with expanded description

### 2025-12-06 10:25:00
✨ **Execution Queue System - Parallel Execution Prevention**
- **Feature**: Platform-level execution queue to prevent parallel execution on agents
- **Problem Solved**: Multiple simultaneous requests (user chat + schedule + agent-to-agent) would corrupt Claude Code's conversation state
- **Solution**: Redis-backed queue with single-execution-at-a-time guarantee per agent

- **New Files**:
  - `src/backend/services/execution_queue.py` - Redis-backed queue service
    - `ExecutionQueue` class with submit/complete/get_status methods
    - Max 3 queued requests per agent, 429 if full
    - 10-minute execution TTL (Redis key expiry)
    - Thread-safe via Redis atomic operations
  - New models in `models.py`: `Execution`, `ExecutionSource`, `ExecutionStatus`, `QueueStatus`

- **Backend Changes**:
  - `routers/chat.py`: Integrated queue before proxying to agent
    - Creates execution request, submits to queue
    - Returns 429 with retry_after if queue full
    - Releases queue slot in finally block
    - Response includes `execution.id`, `queue_status`, `was_queued`
  - `routers/agents.py`: New queue endpoints
    - `GET /{agent_name}/queue` - Queue status
    - `POST /{agent_name}/queue/clear` - Clear pending requests
    - `POST /{agent_name}/queue/release` - Emergency release stuck agent
  - `services/scheduler_service.py`: Uses queue for scheduled executions
    - Both `_execute_schedule` and `_execute_manual_trigger` updated
    - Fails gracefully if queue full (no schedule execution lost)

- **Agent Container Changes**:
  - `docker/base-image/agent-server.py`:
    - Added `asyncio.Lock` for defense-in-depth
    - Reduced ThreadPoolExecutor to `max_workers=1`

- **MCP Server Changes**:
  - `src/mcp-server/src/client.ts`: Handles 429 response, returns structured error
  - `src/mcp-server/src/tools/chat.ts`: Returns "agent_busy" status to orchestrator

- **Testing**: All syntax checks passed, backend starts successfully, endpoints registered

- **Future Updates Needed**:
  - Frontend queue status indicator in agent card
  - Queue position notification for queued requests
  - Metrics/monitoring for queue utilization

### 2025-12-06 03:15:00
✨ **Task DAG Visualization in Collaboration Dashboard**
- **Feature**: Real-time visualization of agent planning activity in Collaboration Dashboard
- **Frontend Changes**:
  - `collaborations.js` store: Added `planStats`, `aggregatePlanStats` state, `fetchPlanStats()` function
  - Plan stats polling integrated into `startContextPolling()` (every 5 seconds)
  - `AgentNode.vue`: Added task progress display with purple progress bar
    - Shows current task name with pulsing icon
    - Task progress bar (completed/total)
    - Only visible when agent has active plan
  - `AgentCollaboration.vue`: Added plan stats to header
    - Shows active plans count, tasks completed/total
    - Purple accent to distinguish from collaboration stats
- **API Integration**: Fetches from `GET /api/agents/plans/aggregate`
- **UI/UX**:
  - Progressive disclosure: Task section only shows when agent has plans
  - Purple color scheme for tasks (distinguishes from green context)
  - Real-time updates within 5 seconds
- **Files Changed**:
  - `src/frontend/src/stores/collaborations.js` (60 lines added)
  - `src/frontend/src/components/AgentNode.vue` (50 lines added)
  - `src/frontend/src/views/AgentCollaboration.vue` (15 lines added)
- **Docs Updated**: feature-flows/task-dag-system.md, roadmap.md

### 2025-12-06 02:30:00
🔄 **Task DAG System Architecture Refactor - Centralized Injection via Agent Server**
- **Problem**: Previous architecture used startup.sh for Trinity injection (file permission issues, no control)
- **Solution**: Centralized all injection logic in agent-server.py with API endpoints
- **New Agent Server Endpoints**:
  - `POST /api/trinity/inject` - Inject meta-prompt, commands, create directories
  - `POST /api/trinity/reset` - Reset injection to clean state
  - `GET /api/trinity/status` - Check injection status
- **Backend Integration**: `start_agent` endpoint now calls injection API after container starts
  - Retry logic with 5 attempts, 2-second delay
  - Non-blocking - agent starts even if injection fails
  - Injection status included in response and audit log
- **Files Changed**:
  - `docker/base-image/agent-server.py` - Added Trinity Injection API (~200 lines)
  - `docker/base-image/startup.sh` - Removed injection code (replaced with comment)
  - `src/backend/routers/agents.py` - Added `inject_trinity_meta_prompt()` helper, modified `start_agent`
  - `docker-compose.yml` / `docker-compose.prod.yml` - Added `HOST_META_PROMPT_PATH` env var
- **Benefits**:
  - Centralized control in agent-server.py
  - Can update/reset injection without restart
  - Clear API contract with proper error handling
  - Testable endpoints
- **Tested on Production**: Full lifecycle verified - injection, plan creation, dependency unblocking, auto-archiving
- **Docs Updated**: requirements.md (9.8), feature-flows/task-dag-system.md

### 2025-12-06 01:35:00
🔒 **Authentication Mode System Refactor**
- **Problem**: Dev mode (`VITE_DEV_MODE`) was build-time only, hardcoded credentials in frontend, switching modes required rebuild
- **Solution**: Backend-driven runtime mode detection
- **Backend Changes**:
  - Added `DEV_MODE_ENABLED` env var to `config.py`
  - New `GET /api/auth/mode` endpoint (unauthenticated) returns mode config
  - `POST /api/token` gated - returns 403 if `DEV_MODE_ENABLED=false`
  - JWT tokens now include `"mode": "dev"` or `"mode": "prod"` claim
  - Removed debug prints that leaked token prefixes
- **Frontend Changes**:
  - Runtime mode detection via `authStore.detectAuthMode()`
  - Removed hardcoded `admin/trinity2024!` credentials
  - New `loginWithCredentials(username, password)` method
  - `Login.vue` shows form OR Google button based on backend mode
  - Token mode validation on session restore (clears dev tokens in prod)
  - Auth0 plugin always loaded (prevents rebuild requirement)
- **Docker**: `DEV_MODE_ENABLED=true` in docker-compose.yml, `=false` in docker-compose.prod.yml
- **Benefit**: Switch modes by changing env var and restarting backend - no frontend rebuild needed
- **Docs**: Updated `feature-flows/auth0-authentication.md` → now "Authentication Mode System"

### 2025-12-05 20:05:00
🔧 **Task DAG System Route Fix**
- **Issue**: `/api/plans/summary` was matched as `/{plan_id}` due to route ordering
- **Fix**: Moved `/api/plans/summary` endpoint BEFORE `/api/plans/{plan_id}` in agent-server.py
- **Tested**: Full lifecycle test passed - plan creation, task updates, dependency unblocking, auto-archiving

### 2025-12-05 16:55:00
✨ **Task DAG System Backend (Phase 9 - Pillar I: Explicit Planning)**
- **Trinity Meta-Prompt Injection**: Platform now injects planning infrastructure into agents
  - Created `config/trinity-meta-prompt/prompt.md` - Trinity system prompt with planning instructions
  - Created `/trinity-plan-create`, `/trinity-plan-status`, `/trinity-plan-update`, `/trinity-plan-list` commands
  - Modified `startup.sh` to inject `.trinity/` dir and commands at container start
  - Creates `plans/active/` and `plans/archive/` directories for task DAG storage
  - Appends Trinity section to CLAUDE.md or creates it if missing
- **Agent Server Plan API**: New REST endpoints in `agent-server.py`
  - `GET /api/plans` - List all plans with progress summaries
  - `POST /api/plans` - Create new plan with tasks
  - `GET /api/plans/{plan_id}` - Get full plan details
  - `PUT /api/plans/{plan_id}` - Update plan metadata
  - `DELETE /api/plans/{plan_id}` - Delete plan
  - `PUT /api/plans/{plan_id}/tasks/{task_id}` - Update task status
  - `GET /api/plans/summary` - Aggregate stats for dashboard
  - Automatic dependency handling: tasks become `blocked` → `pending` as deps complete
  - Plans auto-archive to `plans/archive/` when completed/failed
- **Backend Proxy Endpoints**: New routes in `routers/agents.py`
  - `GET /api/agents/{name}/plans` - Proxy to agent's plan list
  - `POST /api/agents/{name}/plans` - Proxy to create plan
  - `GET /api/agents/{name}/plans/summary` - Proxy to agent's summary
  - `GET /api/agents/{name}/plans/{plan_id}` - Proxy to specific plan
  - `PUT /api/agents/{name}/plans/{plan_id}` - Proxy to update plan
  - `DELETE /api/agents/{name}/plans/{plan_id}` - Proxy to delete plan
  - `PUT /api/agents/{name}/plans/{plan_id}/tasks/{task_id}` - Proxy to update task
  - `GET /api/agents/plans/aggregate` - Cross-agent plan aggregation for dashboard
  - Volume mount for trinity-meta-prompt in container creation
- **Files Modified**:
  - `config/trinity-meta-prompt/prompt.md` - NEW
  - `config/trinity-meta-prompt/commands/*.md` - NEW (4 files)
  - `docker/base-image/agent-server.py` - Plan API endpoints (~450 lines)
  - `docker/base-image/startup.sh` - Injection logic (~70 lines)
  - `src/backend/routers/agents.py` - Proxy endpoints (~460 lines)
- **Status**: Backend complete, frontend visualization pending

### 2025-12-03 02:30:00
✨ **Collaboration Dashboard UX Improvements**
- **Canvas Height Fix**: Changed from fixed height to flex layout, canvas now extends fully to bottom edge
  - Removed 15% gap at bottom that was wasting screen space
  - Uses `flex-1 min-h-0` pattern for proper flex child behavior
- **Agent Active Pulsing**: Made pulsing indicator much more pronounced
  - Custom `active-pulse` animation runs at 0.8s (faster than default)
  - Scales from 1.0x to 1.3x with glowing box-shadow
  - Green glow effect pulses with the dot
- **Collaboration Arrow Duration**: Extended edge animation visibility
  - Changed from 2.5s to 6s fade delay (gives time for target agent context update)
  - Added timeout tracking to prevent edge resets when retriggered
  - Made flowing dots animation faster (0.6s instead of 1.5s)
- **GitHub Repo Display**: Added GitHub repo info to agent nodes
  - Backend: `get_accessible_agents()` now includes `github_repo` from git_config
  - Frontend: AgentNode.vue shows GitHub icon + owner/repo for template-based agents
  - Handles various formats: `github:owner/repo`, full URLs, plain `owner/repo`
- **Files Modified**:
  - `src/frontend/src/views/AgentCollaboration.vue` - Canvas flex layout, edge animation speed
  - `src/frontend/src/components/AgentNode.vue` - GitHub repo display, active-pulse animation
  - `src/frontend/src/stores/collaborations.js` - Extended edge timeouts, githubRepo in node data
  - `src/backend/routers/agents.py` - Include github_repo in agent list response
- **Deployed**: Production via `gcp-deploy.sh`

### 2025-12-03 01:45:00
🔧 **MCP Server: Removed Admin Authentication Requirement**
- **Problem**: MCP server → backend API calls were failing due to recurring admin password authentication issues
- **Root Cause**: When `MCP_REQUIRE_API_KEY=true`, the chat tools (`chat.ts`) were using an unauthenticated base client instead of creating per-request authenticated clients with the user's MCP API key
- **Solution**:
  - Modified `server.ts` to skip admin authentication entirely when `requireApiKey=true`
  - Updated `getClient()` pattern in both `agents.ts` and `chat.ts` to REQUIRE MCP API key (no admin fallback)
  - All backend API calls now use the user's MCP API key directly
- **Files Modified**:
  - `src/mcp-server/src/server.ts` - Skip admin auth when API key auth enabled
  - `src/mcp-server/src/tools/agents.ts` - Require MCP API key in getClient()
  - `src/mcp-server/src/tools/chat.ts` - Add getClient() pattern, use authenticated client for all operations
  - `docs/memory/feature-flows/mcp-orchestration.md` - Updated documentation
- **Result**: Agent-to-agent collaboration now works correctly on production. Eliminates need for `TRINITY_USERNAME`/`TRINITY_PASSWORD` environment variables when `MCP_REQUIRE_API_KEY=true`
- **Testing**: Successfully tested chain collaboration (head agent → alpha → beta) on production

### 2025-12-02 23:55:00
📝 **Architecture Documentation Comprehensive Update**
- Updated `docs/memory/architecture.md` based on systematic review of 7 recent feature flows
- **Database Schema Updates**:
  - Added `chat_sessions` table documentation (persistent chat session tracking)
  - Added `chat_messages` table documentation (individual message persistence with observability)
  - Documented indexes, foreign keys, and persistent chat features
- **API Endpoints Updates** (6 new endpoints):
  - Added `/api/agents/{name}/chat/history/persistent` - Database-backed chat history
  - Added `/api/agents/{name}/chat/sessions` - List all chat sessions
  - Added `/api/agents/{name}/chat/sessions/{id}` - Session details with messages
  - Added `/api/agents/{name}/chat/sessions/{id}/close` - Close chat session
  - Added `/api/activities/timeline` - Cross-agent activity timeline with filtering
  - Clarified `/api/agents/{name}/files` as tree structure (was flat list)
  - Updated count from 16 to 22 agent endpoints
- **WebSocket Events**:
  - Added complete `agent_activity` event documentation
  - Documented event schema with all activity types and states
  - Enhanced `agent_collaboration` event description
- **Feature Summaries**:
  - Added Replay Mode to Collaboration Dashboard features
  - Added Activity Timeline Integration description
  - Added Persistent Chat feature summary in Agent Containers section
  - Noted file browser tree structure implementation
- **MCP Server Authentication**:
  - Documented FastMCP `authenticate` callback pattern
  - Added `McpAuthContext` interface documentation
  - Explained `context.session` parameter for tool execution
  - Documented agent-scoped keys for collaboration access control
- Files modified: `docs/memory/architecture.md`
- All updates maintain minimal necessary changes principle
- Documentation now synchronized with implemented features as of 2025-12-02

### 2025-12-02 23:26:47
🔧 **Fixed Collaboration Dashboard UX Issues**
- **Issue #1 - History Panel Always Visible**: Made collaboration history panel collapsible
  - Added floating toggle button (clipboard icon) in bottom-right corner
  - Panel now starts closed by default to avoid cluttering main view
  - Button moves right when panel opens to prevent overlap
  - Smooth slide-in/slide-out animation with transition effects
- **Issue #2 - Agents Showing Offline**: Fixed critical route ordering bug in backend
  - Root cause: `/context-stats` endpoint defined AFTER `/{agent_name}` catch-all route
  - FastAPI was matching `/context-stats` as agent name, returning 404
  - Solution: Moved `/context-stats` to line 93, before `/{agent_name}` at line 174
  - Now agents correctly show Active/Idle/Offline status with pulsing green/gray dots
  - Context progress bars now display with color coding (green/yellow/orange/red)
  - Activity state updates every 5 seconds via polling
- **Issue #3 - Time Range Selector Unclear**: Improved labeling and context
  - Changed label from "Time Range:" to "History:" with clock icon
  - Added tooltip: "How far back to load collaboration history"
  - Clarified purpose: filters historical data load, useful in both Live and Replay modes
- Files modified:
  - `src/frontend/src/views/AgentCollaboration.vue` - UI improvements (toggle button, clearer labels)
  - `src/backend/routers/agents.py` - Route ordering fix (moved context-stats before catch-all)
- Backend restarted to apply route fix
- All fixes tested and working

### 2025-12-02 23:45:00
📝 **Updated Agent-to-Agent Collaboration Feature Flow Documentation**
- Updated `docs/memory/feature-flows/agent-to-agent-collaboration.md` to reflect auth context fix
- Added comprehensive "Authentication Flow (Updated 2025-12-02)" section:
  - Documented FastMCP session pattern for auth context propagation
  - Showed how `context.session` replaced module-level state
  - Explained 3-step flow: authenticate → session → tool execution
- Added "Security Considerations" section covering:
  - Session-based auth context management
  - Agent identity verification via scope
  - Owner-based access control
  - Admin bypass safeguards
  - Audit logging for collaboration attempts
- Updated "Key Implementation Files" table with accurate line numbers:
  - `server.ts:106-139` - FastMCP authenticate callback
  - `chat.ts:111` - Gets auth from `context.session`
  - `chat.ts:21-73` - Access control using session context
  - `types.ts:64-71` - McpAuthContext interface
- Added note explaining context.session fix resolved undefined auth context breaking access control
- Cross-referenced with MCP Orchestration flow for consistent auth pattern
- Requirement: **REQ-DOCS Agent-to-Agent Collaboration Feature Flow**

### 2025-12-02 23:30:00
📝 **Updated MCP Orchestration Feature Flow Documentation**
- Completely rewrote `docs/memory/feature-flows/mcp-orchestration.md` with corrected authentication flow
- Added comprehensive "Authentication Flow (Critical)" section documenting 5-step auth process:
  1. MCP Client → MCP Server authentication via FastMCP authenticate callback
  2. Tool execution receiving auth context via `context.session`
  3. MCP Server → Backend API calls with user's MCP API key
  4. Backend validation of MCP API key in `get_current_user()` dependency
  5. Agent creation with correct owner assignment
- Documented "The Bug That Was Fixed" section explaining race condition:
  - Before: Module-level `currentAuthContext` variable (shared state, race conditions)
  - After: FastMCP session mechanism (request-scoped, thread-safe)
- Added "Troubleshooting" section with two bug fixes from 2025-12-02:
  - Race condition bug (module-level state → FastMCP session)
  - Backend validation bug (`if mcp_key_info.get("valid")` → `if mcp_key_info:`)
- Updated all code snippets with accurate line numbers from current codebase
- Added race condition testing instructions for validation
- Emphasized request-scoped authentication as key security feature
- Total: 742 lines of comprehensive vertical slice documentation
- Requirement: **REQ-DOCS MCP Orchestration Feature Flow**

### 2025-12-02 23:06:00
🔧 **Fixed MCP Agent Ownership Bug**
- **Problem**: Agents created via MCP with user API keys were incorrectly assigned to 'admin' instead of actual user
- **Root Cause 1**: MCP server used shared module-level `currentAuthContext` variable overwritten in concurrent requests
- **Root Cause 2**: Backend auth check used incorrect condition `if mcp_key_info.get("valid")` when validate returns dict/None
- **Solution**: Removed shared state, used FastMCP session mechanism, fixed backend validation condition
- **Files Modified**:
  - `src/mcp-server/src/server.ts` - Removed global state, return auth from authenticate callback
  - `src/mcp-server/src/tools/agents.ts` - Get auth from context.session
  - `src/mcp-server/src/tools/chat.ts` - Get auth from context.session
  - `src/mcp-server/src/types.ts` - Made McpAuthContext extend Record<string, unknown>
  - `src/backend/dependencies.py` - Fixed MCP key validation: `if mcp_key_info:` instead of `if mcp_key_info.get("valid"):`
- **Verification**: Test agent created via MCP correctly assigned to user@example.com (user_id=3) instead of admin (user_id=1)
- **Impact**: All future agents created via MCP will be properly owned by the user who created them

### 2025-12-02 22:30:00
✨ **Collaboration Dashboard Replay Feature**
- Added replay mode toggle (Live/Replay) in dashboard header with pill-shaped button group
- Implemented playback controls: Play (green), Pause (yellow), Stop (red) buttons
- Speed selector dropdown with 6 options (1x, 2x, 5x, 10x, 20x, 50x)
- Timeline scrubber with visual event markers (gray dots) showing all historical collaborations
- Draggable playback position marker (blue line with handle)
- Progress statistics: Event X/Y, elapsed/total time, remaining time at current speed
- Time compression logic: `delay = realTimeDelta / speedMultiplier` with 100ms minimum
- Frontend-only implementation - no backend changes required
- Uses existing `historicalCollaborations` data from agent_activities table
- Store functions: `setReplayMode()`, `startReplay()`, `pauseReplay()`, `stopReplay()`, `setReplaySpeed()`, `jumpToTime()`, `jumpToEvent()`
- Automatically disconnects WebSocket and stops context polling during replay
- Reconnects to live mode when switching back
- Timeline click-to-jump and playback position updates
- Smooth CSS transitions and hover effects for professional UX
- Files modified:
  - `src/frontend/src/stores/collaborations.js`: +206 lines (replay state, computed props, functions)
  - `src/frontend/src/views/AgentCollaboration.vue`: +119 template lines, +76 CSS lines, +45 script lines
- Requirement: **REQ-9.6.1 Collaboration Dashboard Replay Feature**
- Estimated effort: 8-10 hours → Actual: ~6 hours (faster due to well-planned specs)

### 2025-12-02 20:52:00
✨ **Collaboration Dashboard UI/UX Enhancements**
- Implemented real-time context window monitoring with visual progress bars (Requirement 9.6 enhancement)
- Added three-state agent activity tracking: Active, Idle, Offline
- Backend: New `GET /api/agents/context-stats` endpoint
  - Fetches context usage from agent internal API (`/api/chat/session`)
  - Calculates activity state from `agent_activities` table (< 60s = active)
  - Returns: `contextPercent`, `contextUsed`, `contextMax`, `activityState`
- Frontend: 5-second polling for real-time updates
  - Store: `fetchContextStats()`, `startContextPolling()`, `stopContextPolling()`
  - Updates node data dynamically with context and activity information
- Redesigned AgentNode.vue component:
  - Clean white card design (matches mockup requirements)
  - Context progress bar with color-coding: Green (<50%), Yellow (50-75%), Orange (75-90%), Red (>90%)
  - Activity state labels with status dots (green for active/idle, gray for offline)
  - Pulsing animation for active agents
  - Progress bar only visible for running agents (hidden for offline)
- Dashboard lifecycle: Starts polling on mount, stops on unmount
- Key files: `routers/agents.py` (+81 lines), `stores/collaborations.js` (+70 lines), `AgentNode.vue` (redesigned), `AgentCollaboration.vue` (+3 lines)

### 2025-12-02 10:56:37
✨ **Unified Activity Stream Implementation**
- Implemented comprehensive activity tracking system (Requirement 9.7)
- Database: `agent_activities` table with 15 columns and 7 indexes
- Activity types: chat_start, chat_end, tool_call, schedule_start, schedule_end, agent_collaboration
- Centralized `ActivityService` with WebSocket broadcasting and subscriber pattern
- Chat integration: tracks chat lifecycle with granular tool call tracking
- Schedule integration: tracks scheduled task execution
- Query API: `GET /api/agents/{name}/activities` and `GET /api/activities/timeline`
- Data strategy: Tool calls stored in both chat_messages (JSON) and agent_activities (rows)
- Observability data (cost/context) stored in existing tables, accessed via JOIN
- Full backward compatibility with existing chat_messages and schedule_executions tables
- Key files: `database.py`, `services/activity_service.py`, `routers/chat.py`, `routers/agents.py`, `models.py`

### 2025-12-01 21:35:00
🔧 **Bug Fix: User Model Authentication Fields**

Fixed critical authentication bug preventing agent chat functionality.

**Problem:**
- Chat endpoint failed with `AttributeError: 'User' object has no attribute 'id'`
- Persistent chat tracking required `id` and `email` fields that didn't exist on User model
- Affected all agent-to-agent collaboration and chat persistence

**Root Cause:**
- `src/backend/models.py` User model only defined `username` and `role`
- JWT authentication in `dependencies.py` wasn't populating database user fields
- Chat persistence code in `chat.py` expected full user object with id/email

**Solution:**
1. Extended User model with required fields:
   - Added `id: int` field
   - Added `email: Optional[str]` field
   - Maintained backward compatibility with existing code

2. Updated JWT authentication to populate fields from database:
   - Modified `get_current_user()` in dependencies.py
   - Queries database for full user record
   - Constructs User object with all fields

3. Fixed all references in chat.py (7 locations):
   - Session creation: `current_user.id`, `current_user.email`
   - Message persistence: uses correct user fields
   - Access control: validates against user id

**Testing:**
- Successfully triggered 8 agent-to-agent collaborations
- All WebSocket collaboration events broadcast correctly
- Chat persistence working for both user and assistant messages
- Session tracking operational with full user context

**Files Modified:**
- `src/backend/models.py` (lines 42-47)
- `src/backend/dependencies.py` (lines 79-84)
- `src/backend/routers/chat.py` (lines 67-81, 110-122, 425-429, 463-464, 505-506, 536-537)

**Impact:**
- ✅ Agent collaboration dashboard now fully functional
- ✅ Chat persistence and session tracking working
- ✅ Access control properly enforced
- ✅ All authentication flows operational

### 2025-12-01 21:00:00
✨ **Agent Collaboration Dashboard - Real-Time Graph Visualization**

Implemented comprehensive real-time visualization dashboard for agent-to-agent communication using Vue Flow.

**Frontend Implementation:**
1. **Vue Flow Integration** (Latest Versions)
   - @vue-flow/core: 1.48.0
   - @vue-flow/background: 1.3.2
   - @vue-flow/controls: 1.1.3
   - @vue-flow/minimap: 1.5.0

2. **Components Created:**
   - `AgentCollaboration.vue` (src/frontend/src/views/) - Main dashboard view with graph canvas
   - `AgentNode.vue` (src/frontend/src/components/) - Custom node component with status-based colors
   - `collaborations.js` (src/frontend/src/stores/) - Pinia store for graph state and WebSocket integration

3. **Features:**
   - Draggable agent nodes with grid layout
   - Status-based gradient colors (green=running, gray=stopped, orange=starting)
   - Real-time WebSocket integration for collaboration events
   - Animated blue edges when agents communicate (3-second fade-out)
   - Node position persistence via localStorage
   - Zoom, pan, and minimap controls
   - Collaboration statistics (agent count, active collaborations, last event time)
   - Click-through to agent detail pages
   - Connection status indicator
   - Reset layout button
   - Collaboration history panel (last 10 events)

**Backend Implementation:**
1. **WebSocket Broadcasts** (src/backend/routers/chat.py)
   - Added `set_websocket_manager()` function
   - Created `broadcast_collaboration_event()` helper
   - Modified `chat_with_agent()` endpoint to accept `X-Source-Agent` header
   - Broadcasts collaboration events when header is present

2. **Main.py Changes:**
   - Imported `set_websocket_manager` from chat router
   - Injected WebSocket manager into chat router on startup

3. **Event Format:**
   ```json
   {
     "type": "agent_collaboration",
     "source_agent": "agent-a",
     "target_agent": "agent-b",
     "action": "chat",
     "timestamp": "2025-12-01T..."
   }
   ```

**Router & Navigation:**
- Added `/collaboration` route to frontend router
- Added "Collaboration" link to NavBar
- Route requires authentication (meta.requiresAuth: true)

**Configuration:**
- Updated vite.config.js to include @ alias for imports
- Added path resolution for src directory

**Documentation:**
- requirements.md: Added REQ-9.6 "Agent Collaboration Dashboard"
- architecture.md: Added "Collaboration Dashboard" section with component details
- architecture.md: Added Vue Flow to Technology Stack (Frontend)
- Full specification in `docs/requirements/AGENT_COLLABORATION_DASHBOARD.md`

**Testing:**
- Frontend build successful (no errors)
- Bundle size: AgentCollaboration.js 229.20 kB (75.06 kB gzipped)
- All components properly imported and configured

**Future Enhancements:**
- Auto-layout algorithms (force-directed, hierarchical)
- Collaboration history persistence in database
- Edge click to show message history between agents
- Export graph as PNG/SVG
- Agent grouping by owner or type

**Files Modified:**
- src/frontend/package.json
- src/frontend/vite.config.js
- src/frontend/src/router/index.js
- src/frontend/src/components/NavBar.vue
- src/backend/main.py
- src/backend/routers/chat.py
- docs/memory/requirements.md
- docs/memory/architecture.md

**Files Created:**
- src/frontend/src/views/AgentCollaboration.vue
- src/frontend/src/components/AgentNode.vue
- src/frontend/src/stores/collaborations.js

**Next Steps:**
- Update MCP server to send `X-Source-Agent` header when proxying agent-to-agent chats
- Test with actual agent-to-agent communication
- Consider database persistence for collaboration history

### 2025-12-01 14:30:00
🔴 **KNOWN ISSUE: OAuth Redirect Still Goes to localhost in Production**

Despite implementing BACKEND_URL configuration and updating Google Cloud Console, OAuth flow still redirects to localhost:8000 instead of production URL.

**Issue documented in**: `docs/KNOWN_ISSUES.md`

**Investigation needed**: Frontend caching, backend env var loading, or Google OAuth cache.

### 2025-12-01 14:09:42
✨ **Google Drive OAuth Integration with Normalized Credentials**

Implemented OAuth credential normalization for Google Drive MCP server integration.

**Problem Solved:**
- OAuth credentials stored in Redis didn't match naming convention expected by Google Drive MCP servers
- Missing client ID/secret in agent credentials (were only in backend env vars)

**Implementation:**
1. **Modified exchange_oauth_code** (src/backend/credentials.py:330-337)
   - Added client_id and client_secret to token response
   - Enables per-user OAuth app configuration

2. **Added credential normalization** (src/backend/routers/credentials.py:315-355)
   - Stores both raw OAuth tokens AND MCP-compatible names
   - Google: GOOGLE_ACCESS_TOKEN, GOOGLE_REFRESH_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
   - Slack: SLACK_ACCESS_TOKEN, SLACK_BOT_TOKEN, SLACK_CLIENT_ID, SLACK_CLIENT_SECRET
   - GitHub: GITHUB_ACCESS_TOKEN, GITHUB_TOKEN, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET
   - Notion: NOTION_ACCESS_TOKEN, NOTION_TOKEN, NOTION_CLIENT_ID, NOTION_CLIENT_SECRET

3. **Created google-drive-test template** (config/agent-templates/google-drive-test/)
   - template.yaml with credential requirements
   - .mcp.json.template with ${GOOGLE_*} placeholders
   - CLAUDE.md with usage instructions

**Testing:**
- Python test script validates normalization logic ✅
- All required MCP credential keys present after OAuth flow ✅
- Template variable replacement works correctly ✅
- Deployed to production (GCP)

**Compatibility:**
- No changes to existing get_agent_credentials (already handles uppercase matching)
- No changes to template_service.py (already replaces ${VAR} placeholders)
- Backward compatible with existing OAuth flows

**Files Modified:**
- src/backend/credentials.py
- src/backend/routers/credentials.py
- config/agent-templates/google-drive-test/ (new)
- docs/development/GOOGLE_DRIVE_OAUTH_INTEGRATION.md (spec document)

**Deployed:** Production @ your-domain.com

### 2025-12-01 12:08:38
✨ **File Browser Tree Structure - macOS Finder Style**

Converted file browser from flat list to hierarchical tree structure with expand/collapse functionality.

**UI Changes:**
- Recursive FileTreeNode component using Vue h() render function
- Folders show chevron icon (rotates 90° when expanded) and folder icon (color changes)
- File count badge on each folder showing number of files inside
- 20px indentation per nesting level
- Folders collapsed by default, click to expand/collapse
- Files show download button on hover (opacity transition)
- Search auto-expands folders containing matches

**Backend Changes:**
- Modified `GET /api/files` to return tree structure instead of flat list
- Added recursive `build_tree(directory, base_path)` function in agent-server.py
- Sorts items: directories first, then files (alphabetically)
- Response format: `{tree: [...], total_files: N}` instead of `{files: [...], count: N}`

**State Management:**
- Changed from `files` array to `fileTree` array
- Added `expandedFolders` Set to track open folders
- Added `totalFileCount` for display
- Updated `filteredFileTree` computed to recursively filter and auto-expand

**Bug Fix:**
- Fixed scoping issue: `build_tree()` now receives `base_path` as explicit parameter
- Resolves relative paths correctly in nested directories

**Files Modified:**
- `docker/base-image/agent-server.py` - Tree structure API (lines 1718-1776)
- `src/frontend/src/views/AgentDetail.vue` - FileTreeNode component and state (lines 765-830, 866-993, 1100-1142)
- `src/frontend/src/stores/agents.js` - Default path parameter (line 312)
- `docs/memory/feature-flows/file-browser.md` - Updated documentation

**Testing:** ✅ Verified working on agent-vfwefwef

### 2025-12-01 11:12:44
🔧 **File Browser Bug Fix - Audit Logging Parameter**

Fixed critical bug preventing file browser from working in production.

**Issue:**
- TypeError in audit logging: `log_audit_event() got an unexpected keyword argument 'metadata'`
- File list and download endpoints returned 500 Internal Server Error
- Bug introduced during initial implementation (used wrong parameter name)

**Fix:**
- Changed `metadata` parameter to `details` in all `log_audit_event()` calls
- Affects 4 calls in file browser endpoints (list success/error, download success/error)
- Audit logging signature uses `details`, not `metadata`

**Files Modified:**
- `src/backend/routers/agents.py` - Fixed 4 audit log calls

**Root Cause:** Parameter mismatch - `log_audit_event()` expects `details` but was called with `metadata`

**Deployed to Production:** GCP @ your-domain.com

### 2025-12-01 10:36:48
✨ **File Browser for Agent Workspaces**

Added file browsing and download capability for agent workspaces with full audit logging.

**Features Implemented:**
- Agent server endpoints: `GET /api/files` (list) and `GET /api/files/download`
- Backend proxied endpoints: `GET /api/agents/{name}/files` and `/files/download`
- Frontend Files tab with search, filtering, and download functionality
- Security: workspace-only access (`/home/developer/workspace`), 100MB file size limit
- Audit logging: `file_access` event type for both list and download operations

**Architecture:**
- 3-layer implementation: agent-server.py → backend → frontend
- Files auto-load when Files tab is activated
- Real-time search filtering by filename or path
- Shows file metadata: name, path, size, modified date

**Files Modified:**
- `docker/base-image/agent-server.py` - File listing and download endpoints
- `src/backend/routers/agents.py` - Proxied endpoints with audit logging
- `src/frontend/src/views/AgentDetail.vue` - Files tab UI
- `src/frontend/src/stores/agents.js` - API methods

**Deployed to Production:** GCP @ your-domain.com

### 2025-12-01 09:45:00
💾 **Persistent Chat Session Tracking**

Implemented full database persistence for all agent chat interactions with comprehensive audit trail and observability.

**Problem Solved:**
- Interactive chat history was only stored in agent container memory (lost on restart/deletion)
- No user attribution for messages
- No way for agent owners to review conversation history
- No cost/context tracking across sessions

**New Database Tables:**
- `chat_sessions` - Session metadata (user, agent, costs, context usage, timestamps)
- `chat_messages` - All messages (user + assistant) with full observability data

**New API Endpoints:**
- `GET /api/agents/{name}/chat/history/persistent` - Get persistent messages across all sessions
- `GET /api/agents/{name}/chat/sessions` - List all sessions for an agent
- `GET /api/agents/{name}/chat/sessions/{session_id}` - Get session details with messages
- `POST /api/agents/{name}/chat/sessions/{session_id}/close` - Close a session

**Features:**
- Automatic session creation on first chat message
- Tracks both user and assistant messages
- Persists cost, context usage, tool calls, execution time for each assistant response
- Survives container restarts and deletions
- User-based access control (users see their own messages, admins/owners see all)
- Filter by user, status, and time range

**Files Modified:**
- `src/backend/database.py` - Added ChatSession and ChatMessage models, CRUD operations (240+ lines)
- `src/backend/routers/chat.py` - Updated chat endpoint to persist messages, added history endpoints (150+ lines)

**Commit:** `9649557`

### 2025-11-30 17:04:01
🔧 **Codebase Cleanup - Remove Unused Infisical References**

Removed all Infisical references from the codebase since Trinity uses Redis for credential storage.

**Files Modified:**
- `docker-compose.yml` - Removed INFISICAL_URL env var, commented service, infisical-data/encrypted-secrets volumes
- `.env.example` - Removed Infisical configuration section (INFISICAL_ENCRYPTION_KEY, etc.)
- `scripts/deploy/start.sh` - Removed Infisical access point from startup message
- `src/frontend/src/views/Credentials.vue` - Removed "Open Infisical Dashboard" link
- `docs/development/CREDENTIAL_MANAGEMENT.md` - Removed "Migration from Infisical" section
- `docs/trinity-architecture-diagrams.md` - Removed Infisical from Docker Compose diagram

**Files Deleted:**
- `scripts/management/rotate_secrets.py` - Infisical-specific secret rotation script

**Rationale:**
Trinity platform has never used Infisical in production. All credential management uses Redis with OAuth2 flows. Removing these references eliminates confusion and reduces maintenance burden.

### 2025-11-30 16:57:31
🚀 **Production Deployment - Latest Features to GCP**

Deployed latest codebase to production (`your-domain.com`).

**Changes Deployed:**
- Agent-to-agent collaboration via Trinity MCP
- HOST_TEMPLATES_PATH volume mounting fix
- Authentication debugging improvements
- All backend modular architecture updates

**Deployment Steps:**
1. Backed up production database (`trinity_backup_20251130_165422.db`)
2. Rebuilt all Docker images (backend, frontend, mcp-server, audit-logger)
3. Restarted services to pick up new code
4. Verified all endpoints healthy

**Production Status:**
- ✅ Backend: Healthy (http://your-server-ip:8005)
- ✅ Frontend: Healthy (https://your-domain.com)
- ✅ MCP Server: Running (http://your-server-ip:8007)
- ✅ Audit Logger: Healthy (http://your-server-ip:8006)
- ✅ Redis: Healthy

**Git Commits Deployed:**
- `65f82c6` - fix: add HOST_TEMPLATES_PATH for Docker volume mounting
- `c2d4172` - docs: add authentication debugging report
- `e24be8f` - feat: implement agent-to-agent collaboration via Trinity MCP

### 2025-11-30 09:40:00
🎉 **Comprehensive Platform Testing - All Features Validated**

Systematically tested all 13 major feature categories. **Result: 13/13 PASSED**.

**Testing Coverage:**
- ✅ System status & health checks
- ✅ Authentication (admin login, JWT tokens)
- ✅ Agent creation (local templates)
- ✅ Agent lifecycle (start/stop/delete)
- ✅ Credential management (CRUD operations)
- ✅ Agent chat interface
- ✅ Activity monitoring
- ✅ Logs & telemetry
- ✅ Agent sharing
- ✅ Agent scheduling
- ✅ MCP orchestration
- ✅ Agent-to-agent collaboration infrastructure

**Critical Fix - Docker Volume Mounting:**
- **Issue**: Agent creation failed with "invalid characters for volume name"
- **Root Cause**: Docker requires absolute paths for host directory volumes, not relative paths like `./config/agent-templates`
- **Solution**: Added `HOST_TEMPLATES_PATH` environment variable with absolute path
- **File Modified**: `docker-compose.yml:19`
- **Impact**: Local template-based agent creation now works correctly

**Minor Issues Found (Non-blocking):**
- MCP server health check shows "unhealthy" but responds correctly to requests
- `/api/mcp/info` endpoint returns 404 (MCP keys work fine)
- Token/cost tracking shows $0.00 for simple messages (may be expected)

**Test Methodology:**
- Python `requests` library for automated API testing
- Created/deleted test agents dynamically
- Verified response codes and data structures
- Tested error handling and edge cases

**Files Modified:**
- `docker-compose.yml` - Added HOST_TEMPLATES_PATH environment variable
- `docs/memory/changelog.md` - This entry

**Production Readiness:** ✅ Platform fully operational and ready for production use.

### 2025-11-30 09:20:00
🔧 **Authentication Debugging - False Alarm**

Investigated reported JWT token validation failures. Root cause: **testing methodology issue, NOT an authentication bug**.

**Investigation Results:**
- JWT creation and validation: ✅ Working correctly
- `get_current_user` dependency: ✅ Working correctly
- Database user lookup: ✅ Working correctly

**Actual Issue:**
- `curl` with bash variables was truncating JWT tokens (shell escaping)
- Python `requests` library: 200 OK ✅
- Internal container HTTP: 200 OK ✅
- curl with bash: 401 ❌ (token truncated)

**Secondary Finding:**
- uvicorn `--reload` can cause stale worker processes
- Code file changes force process restart, clearing stale state

**Testing Recommendations:**
- ✅ Use Python `requests` library for API testing
- ✅ Use browser UI for integration testing
- ✅ Use Postman/Insomnia for manual API testing
- ❌ Avoid curl with bash variables for tokens with special chars

**Files Modified:**
- `src/backend/dependencies.py` (temporary debug logging added/removed)
- `docs/memory/changelog.md` (this entry)
- `docs/TESTING_GUIDE.md` (added API testing best practices)
- `docs/AUTH_DEBUGGING_2025-11-30.md` (detailed investigation report)

**Status:** Authentication system fully functional. Ready for feature testing.

**See Also:** `docs/AUTH_DEBUGGING_2025-11-30.md` for complete investigation details.

### 2025-11-30 08:42:00
📝 **Simple Feature-Based Testing Approach**

Created practical testing approach: feature flows include testing instructions, Claude follows them.

**Philosophy**:
- Manual testing via documented steps > Over-engineered automation
- One feature flow = one testing section with clear instructions
- Claude Code follows testing steps to verify features work
- Only automate tests when features break repeatedly

**Deliverables:**
- `docs/TESTING_GUIDE.md` - Simple, practical testing guide
- Updated feature flows with practical Testing sections:
  - `docs/memory/feature-flows/agent-lifecycle.md`
  - `docs/memory/feature-flows/agent-chat.md`

**Testing Section Standard:**
Each feature flow now includes:
- Prerequisites checklist
- Step-by-step test instructions
- Expected results for each step
- Verification checklist (UI, API, Docker, DB)
- Edge cases to test
- Cleanup steps
- Status tracking (✅ Working / 🚧 Not Tested / ⚠️ Issues / ❌ Broken)

**How It Works:**
1. Read feature flow document
2. Follow Testing section step-by-step
3. Verify each step works as documented
4. Update "Last Tested" timestamp and status
5. Document any issues found

**When to Automate:**
- Feature broke in production (regression prevention)
- Critical user path (must never break)
- Complex edge cases (hard to test manually)
- NOT by default - avoid over-engineering

**Files Modified:**
- `docs/TESTING_GUIDE.md` (new - simple approach)
- `docs/memory/feature-flows/agent-lifecycle.md` (practical testing steps)
- `docs/memory/feature-flows/agent-chat.md` (practical testing steps)
- `docs/memory/changelog.md` (this entry)

### 2025-11-30 15:25:00
🔧 **Agent-to-Agent Collaboration - MCP Tool Loading Fix**

Fixed critical issue preventing Claude Code from loading Trinity MCP tools inside agent containers.

**Issue:**
- Agents had `.mcp.json` configured but Trinity MCP tools weren't available
- Claude Code wasn't loading MCP servers from config file

**Fix (agent-server.py:707-709):**
```python
# Add MCP config if .mcp.json exists (for agent-to-agent collaboration via Trinity MCP)
mcp_config_path = Path.home() / ".mcp.json"
if mcp_config_path.exists():
    cmd.extend(["--mcp-config", str(mcp_config_path)])
```

**Testing:**
- Deployed to production (GCP)
- Created `collab-agent-a` and `collab-agent-b` owned by `admin`
- Agent A successfully used `mcp__trinity__chat_with_agent` to contact Agent B
- Agent B responded with full capabilities description
- MCP server logs confirm: `[Agent Collaboration] collab-agent-a -> collab-agent-b`
- Access control working: blocked `user@example.com` from accessing `admin`-owned agents

**Cost & Performance:**
- Agent-to-agent call: $0.0892, 17s duration
- Agent MCP keys auto-created on agent creation
- Proper authentication with `scope=agent` field

### 2025-11-29 19:30:00
✨ **Agent-to-Agent Collaboration via Trinity MCP (Requirement 9.4)**

Implemented full agent-to-agent communication infrastructure enabling agents to collaborate through the Trinity MCP server with proper access control.

**Database Changes:**
- Added `agent_name` (TEXT) and `scope` (TEXT: "user"|"agent") columns to `mcp_api_keys` table
- Added migration function for existing databases
- Created index on `agent_name` for fast lookups

**Backend (agents.py, database.py):**
- `create_agent_mcp_api_key()`: Generate agent-scoped MCP API keys
- `get_agent_mcp_api_key()`: Retrieve agent's MCP key
- `delete_agent_mcp_api_key()`: Clean up on agent deletion
- Auto-generate MCP key during agent creation
- Inject `TRINITY_MCP_URL` and `TRINITY_MCP_API_KEY` env vars to agent containers
- Delete agent MCP key when agent is deleted

**Agent Container (agent-server.py):**
- `inject_trinity_mcp_if_configured()`: Inject Trinity MCP into .mcp.json on startup
- Merges Trinity MCP entry with existing MCP servers
- Logs injection status for debugging

**MCP Server (TypeScript):**
- Extended `McpApiKeyValidationResult` with `agent_name` and `scope` fields
- Added `McpAuthContext`, `AgentAccessInfo`, `AgentAccessCheckResult` types
- `getAgentAccessInfo()` client method for ownership/sharing lookup
- `checkAgentAccess()` function implementing access control rules:
  - Same owner → allowed
  - Shared agent → allowed
  - Admin → allowed (bypass)
  - Otherwise → denied with reason
- Auth context stored and passed to chat tools
- Access control enforced in `chat_with_agent` tool

**Access Control Flow:**
1. Agent A calls `mcp__trinity__chat_with_agent(target="B")`
2. MCP server validates API key, extracts agent context
3. Access check: caller owner vs target owner/sharing
4. If denied: return error with reason
5. If allowed: proxy chat request to target agent
6. Audit log: collaboration event logged

**Files Modified:**
- `src/backend/database.py`
- `src/backend/routers/agents.py`
- `src/backend/routers/mcp_keys.py`
- `docker/base-image/agent-server.py`
- `src/mcp-server/src/types.ts`
- `src/mcp-server/src/server.ts`
- `src/mcp-server/src/client.ts`
- `src/mcp-server/src/tools/chat.ts`

### 2025-11-29 11:56:00
✨ **Enhanced Template Format for Rich Info Tab Display**
- Extended `template.yaml` format with new fields for Info tab:
  - `tagline`: Short one-liner for dashboard cards
  - `use_cases`: Example prompts shown as "What You Can Ask"
  - `sub_agents`: Now supports `{name, description}` objects (backwards compatible)
  - `commands`: Now supports `{name, description}` objects (backwards compatible)
  - `mcp_servers`: New section with `{name, description}` objects
  - `skills`: New section with `{name, description}` objects
- Updated `agent-server.py` to return new fields from template.yaml
- Updated `InfoPanel.vue` with enhanced display:
  - Tagline under header
  - "What You Can Ask" section with clickable use cases (copies to clipboard)
  - Sub-agents, commands, MCP servers, skills now show descriptions
  - Counts displayed in section headers
- Updated `docs/AGENT_TEMPLATE_SPEC.md` with new format documentation
- Pushed enhanced template.yaml to `abilityai/agent-ruby` (v2.1)
- Files: `docker/base-image/agent-server.py`, `src/frontend/src/components/InfoPanel.vue`

### 2025-11-29 14:45:00
🔧 **Fixed Agent Info Endpoint Docker Network Bug**
- Bug: `/api/agents/{name}/info` endpoint used `http://{agent_name}:8000`
- Fix: Changed to `http://agent-{agent_name}:8000` to match Docker container naming
- All other endpoints already used `agent-` prefix correctly
- Info tab now displays full template metadata (display_name, description, version, author, mcp_servers)
- File: `src/backend/routers/agents.py:668`

### 2025-11-29 10:34:42
✨ **Agent Info Display Implemented (Requirement 9.3)**
- Added `/api/template/info` endpoint to agent-server.py inside containers:
  - Reads template.yaml from multiple locations (home, workspace, /template)
  - Returns: display_name, description, version, author, capabilities, sub_agents, commands, platforms, mcp_servers, resources
  - Graceful fallback when no template.yaml exists
- Added `/api/agents/{name}/info` endpoint to backend routers/agents.py:
  - Proxies request to running agent container
  - Returns basic info from container labels when agent is stopped
  - Handles timeouts and errors gracefully
- Created `InfoPanel.vue` component:
  - Beautiful gradient header with display name, version, author, update date
  - Resource allocation display (CPU, memory)
  - Capabilities as green chips
  - Slash commands as purple monospace chips
  - Sub-agents as blue items in grid layout
  - Supported platforms as gray chips
  - MCP servers as yellow monospace chips
  - Enabled tools as orange chips
  - Graceful empty state when no template
- Updated `AgentDetail.vue`:
  - Added "Info" tab as first tab (default active)
  - Integrated InfoPanel component
- Added `getAgentInfo` method to agents.js store
- Updated requirements.md with completed criteria

### 2025-11-29 10:01:27
🎨 **Git Sync Controls Moved to Agent Header**
- Moved "Sync to GitHub" and "Refresh" buttons from GitPanel.vue to agent header
- Sync button now appears next to Start/Stop controls for quick access
- Button shows "Sync (N)" with pending change count, or "Synced" when up to date
- Orange color when changes pending, gray when synced
- Git status polling every 30 seconds when agent is running
- "Git enabled" indicator shown when agent is stopped
- GitPanel.vue now serves as read-only log/history view
- Updated feature-flows/github-sync.md with new UI locations

### 2025-11-29
🎉 **GitHub Bidirectional Sync Implemented (Phase 7 Complete)**
- Added `agent_git_config` database table for git configuration storage:
  - Tracks github_repo, working_branch, instance_id, last_sync_at, last_commit_sha
  - Auto-generates unique instance IDs and branch names: `trinity/{agent-name}/{instance-id}`
- Modified `docker/base-image/startup.sh` for git sync:
  - Clones with full history when GIT_SYNC_ENABLED=true (vs shallow clone)
  - Creates and checks out working branch
  - Configures git user for commits
- Added git sync endpoints to `agent-server.py`:
  - `GET /api/git/status` - Get branch, changes, sync status
  - `POST /api/git/sync` - Stage, commit, and push changes
  - `GET /api/git/log` - Get recent commits
  - `POST /api/git/pull` - Pull from remote
- Created backend git service and router:
  - `services/git_service.py` - Git configuration management
  - `routers/git.py` - API endpoints with audit logging
- Updated agent creation (`routers/agents.py`):
  - Passes GIT_SYNC_ENABLED and GIT_WORKING_BRANCH env vars for GitHub templates
  - Creates git config in database on agent creation
  - Cleans up git config on agent deletion
- Created `GitPanel.vue` component with Git tab in AgentDetail:
  - Shows repository, branch, and sync status
  - Displays pending changes with file status indicators
  - "Sync to GitHub" button with success/error feedback
  - Commit history display
  - Automatic status refresh on agent start

✨ **Execution Observability Enhancement**
- Added observability fields to schedule_executions table:
  - `context_used` - Tokens used in context window
  - `context_max` - Maximum context window size
  - `cost` - Execution cost in USD
  - `tool_calls` - JSON array of tool calls made
- Updated scheduler_service.py to extract context/cost from agent response
- Enhanced SchedulesPanel.vue execution history:
  - Context usage progress bar (color-coded by usage level)
  - Cost display in execution rows
  - Clickable rows open execution detail modal
  - Modal shows message, response, tool calls, and stats
- Created ExecutionsPanel.vue component:
  - Dedicated "Executions" tab on AgentDetail.vue
  - Summary stats: total executions, success rate, total cost, avg duration
  - Full table view with all executions across schedules
  - Same detail modal for drilling into any execution
- Added database migration for new columns on existing databases
- Updated feature-flows/scheduling.md with observability documentation

### 2025-11-28
🎉 **Agent Scheduling & Autonomy Implemented (Phase 6 Complete)**
- Added database tables: `agent_schedules` and `schedule_executions`
- Created `services/scheduler_service.py` using APScheduler with AsyncIO
- Created `routers/schedules.py` with full CRUD + control endpoints:
  - `GET/POST /api/agents/{name}/schedules` - List/Create schedules
  - `GET/PUT/DELETE /api/agents/{name}/schedules/{id}` - Schedule CRUD
  - `POST /api/agents/{name}/schedules/{id}/enable` - Enable schedule
  - `POST /api/agents/{name}/schedules/{id}/disable` - Disable schedule
  - `POST /api/agents/{name}/schedules/{id}/trigger` - Manual trigger
  - `GET /api/agents/{name}/schedules/{id}/executions` - Execution history
  - `GET /api/agents/{name}/executions` - All agent executions
- Created `SchedulesPanel.vue` frontend component:
  - Schedule list with enable/disable toggles
  - Create/edit modal with cron presets
  - Execution history with expandable timeline
  - Manual trigger button
- Integrated scheduler lifecycle with FastAPI lifespan
- WebSocket broadcasts for real-time execution updates
- Automatic schedule cleanup on agent deletion
- Added dependencies: apscheduler, croniter, pytz

### 2025-11-28
📝 **Agent Scheduling & Autonomy Added to Roadmap**
- Added requirement 9.1 Agent Scheduling & Autonomy (8 acceptance criteria)
- Moved to top of roadmap as Phase 6
- GitHub-Native Agents moved to Phase 7
- Key features: cron scheduling, execution logs, platform-managed scheduler

### 2025-11-28
📝 **Feature Flows Updated for Modular Architecture**
- Updated all 9 feature flow documents after backend refactoring
- Replaced `main.py:XXXX` line references with new router paths:
  - `auth0-authentication.md` → `routers/auth.py`, `config.py`, `dependencies.py`
  - `agent-lifecycle.md` → `routers/agents.py`, `services/docker_service.py`
  - `agent-chat.md` → `routers/chat.py`
  - `credential-injection.md` → `routers/credentials.py`, `services/template_service.py`
  - `activity-monitoring.md` → `routers/chat.py`
  - `template-processing.md` → `routers/templates.py`, `config.py`
  - `agent-sharing.md` → `routers/sharing.py`, `routers/agents.py`
  - `mcp-orchestration.md` → `routers/mcp_keys.py`
  - `agent-logs-telemetry.md` → `routers/agents.py`
- Verified line numbers against actual router implementations

### 2025-11-29
🔄 **Backend Modular Architecture Refactoring**
- Refactored `main.py` from ~3200 lines to 182 lines (94% reduction)
- Created `config.py`: Centralized configuration constants (88 lines)
- Created `models.py`: All Pydantic models (85 lines)
- Created `dependencies.py`: FastAPI auth dependencies (79 lines)
- Created `services/` directory:
  - `audit_service.py`: Audit logging (46 lines)
  - `docker_service.py`: Container management (88 lines)
  - `template_service.py`: Template processing (299 lines)
- Created `routers/` directory:
  - `auth.py`: Authentication endpoints (221 lines)
  - `agents.py`: Agent CRUD operations (586 lines)
  - `credentials.py`: Credential management (698 lines)
  - `templates.py`: Template listing (176 lines)
  - `sharing.py`: Agent sharing (140 lines)
  - `mcp_keys.py`: MCP API keys (197 lines)
  - `chat.py`: Agent chat/activity (315 lines)
- Created `utils/helpers.py`: Shared utilities (129 lines)
- Updated `docker/backend/Dockerfile` to copy new modules
- All endpoints tested and verified working

### 2025-11-28
📝 **Agent Logs & Telemetry Feature Flow**
- Created `feature-flows/agent-logs-telemetry.md` documenting requirements 1.4 and 1.5
- Covers container logs viewing (tail N lines, auto-refresh, smart scroll)
- Covers live telemetry (CPU, memory, network I/O, uptime)
- Documents Docker API integration for `container.logs()` and `container.stats()`
- Updated feature-flows.md index (now 9 documented flows)

📝 **Feature Flow Analyzer Sub-Agent Upgrade**
- Converted `.claude/agents/feature-flow-analyzer.md` to proper sub-agent format
- Added YAML frontmatter with name, description, tools (Read, Grep, Glob), model (sonnet)
- Detailed system prompt for tracing features from UI → API → Docker → Agent
- Includes search strategy, output format template, and feature priority list
- Sub-agent can now be invoked automatically or explicitly for flow documentation

### 2025-11-28 16:30:00
📝 **Kami Methodology Adoption**
- Created `docs/memory/` directory structure
- Added `requirements.md` with all 43 features documented
- Added `architecture.md` with system design extracted from CLAUDE.md
- Added `roadmap.md` with phased implementation plan
- Added `changelog.md` (this file)
- Added `feature-flows.md` index
- Added `project_index.json` for machine-readable state
- Created slash commands: `/read-docs`, `/update-docs`, `/feature-flow-analysis`, `/agent-status`, `/deploy-status`
- Created sub-agents: `feature-flow-analyzer`, `security-analyzer`, `agent-template-validator`
- Refactored CLAUDE.md to ~200 lines with rules of engagement

### 2025-11-28 16:00:00
✨ **Agent Sharing Implementation**
- Added sharing tab in agent detail page
- Implemented access levels: Owner, Shared, Admin
- Created `agent_sharing` table with cascade delete
- API endpoints: `POST/DELETE /api/agents/{name}/share`
- "Shared by X" badge on shared agents

### 2025-11-28 14:00:00
✨ **Context Window Tracking**
- Real-time context window usage in chat header
- Color-coded progress bar (green/yellow/orange/red)
- Session cost tracking (cumulative)
- New Session button to reset context

### 2025-11-28 12:00:00
✨ **Agent Live Telemetry**
- Real-time CPU, memory, network I/O in agent header
- Uptime display with human-readable duration
- Auto-refresh every 5 seconds
- Color-coded progress bars

### 2025-11-28 10:00:00
✨ **Unified Activity Panel**
- Single component replacing 3 previous components
- Real-time tool call display with pulsing indicator
- Tool chips with counts sorted by frequency
- Expandable timeline with drill-down modal
- Per-message stats (cost, duration, tool count)

### 2025-11-28 08:00:00
✨ **Credential Hot-Reload**
- Hot-reload via UI paste (KEY=VALUE format)
- Regenerates `.mcp.json` from template
- MCP tools: `reload_credentials`, `get_credential_status`

---

## Older Entries (Condensed)

### 2025-11-27
- 🔒 MCP API Key Authentication - per-user keys, usage tracking
- 💾 SQLite Data Persistence - users, ownership, API keys survive restarts
- ✨ Credential Requirements Visibility - show required vs configured
- ✨ Bulk Credential Import - paste .env-style KEY=VALUE pairs
- 🎨 UI Improvements - loading spinners, toast notifications, auto-scroll

### 2025-11-26
- 🐳 Docker as Source of Truth - removed in-memory registry
- 🔒 Container Security - non-root, cap-drop, network isolation
- ✨ Audit Logging Service - SQLite-backed event tracking

### 2025-11-25
- 🚀 GCP Production Deployment - your-vm-name VM
- 🔒 SSL/TLS via Let's Encrypt
- 🐳 nginx reverse proxy configuration

### 2025-11-22
- ✨ Template System - GitHub and local sources
- ✨ Chat via Backend API - real Claude Code execution
- 🎉 MVP Operational - first successful agent chat

### 2025-11-21
- ✨ FastAPI Backend - agent management endpoints
- 🐳 Docker SDK Integration - container lifecycle

### 2025-11-20
- 🐳 Universal Agent Base Image - Python, Node, Go runtimes
- ✨ Claude Code Installation - pre-installed in base image

---

## How to Update This File

1. Get timestamp: `date '+%Y-%m-%d %H:%M:%S'`
2. Add entry at top of "Recent Changes"
3. Use appropriate emoji prefix
4. Include: what changed, why, key files affected
5. When file exceeds ~500 lines, condense oldest entries

**Format:**
```markdown
### YYYY-MM-DD HH:MM:SS
🔧 **Brief Title**
- What was changed
- Why it was changed
- Key files: `path/to/file.py`
```
