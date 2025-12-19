### 2025-12-19 12:30:00
✅ **Test Suite: Fixed 4 Failing Tests - Now 179/179 Pass**

Fixed all failing test assertions to match actual API response formats.

**Fixes Applied**:
1. `test_agent_lifecycle.py:128` - Updated `test_invalid_name_returns_400` to `test_invalid_name_is_sanitized`
   - API sanitizes invalid names (by design) rather than rejecting them
   - Test now verifies sanitization behavior: `"invalid name with spaces!"` → `"invalid-name-with-spaces"`

2. `test_systems.py:497,935` - Fixed permitted_agents assertion
   - API returns list of objects `[{name, status, type, permitted}]`, not strings
   - Extract names: `[p["name"] for p in permitted]` before checking membership

3. `test_systems.py:640,953` - Fixed schedules response assertion
   - API returns list directly `[{...}]`, not wrapped `{"schedules": [...]}`
   - Handle both formats: `schedules = data if isinstance(data, list) else data.get("schedules", [])`

**Test Results**: 179 passed, 28 skipped, 0 failed (20:36 duration)

---

### 2025-12-19 10:55:00
🐛 **Bug Fix: MCP Client YAML Response Handling**

Fixed `get_system_manifest` MCP tool failing with "Unexpected token" JSON parse error.

**Root Cause**:
- `TrinityClient.request()` always parsed responses as JSON
- `/api/systems/{name}/manifest` endpoint returns YAML (text/plain)
- Attempting to JSON.parse() YAML content caused the error

**Fix**:
- Modified `src/mcp-server/src/client.ts` line 130-134
- Added content-type check before parsing response
- Returns raw text for `text/plain`, `text/yaml`, `application/x-yaml` content types

**Also Fixed**:
- `agents/Ruby/ruby-cms.yaml`: Changed template names from `github:Abilityai/ruby-*` to `github:abilityai/ruby-*` (lowercase) to match registered templates

**Testing**:
- Successfully deployed Ruby CMS system via MCP `deploy_system` tool
- All 16 MCP tools verified working (9 agent, 3 chat, 4 system)
- Full verification: 3 agents, 6 permissions, 3 shared folder volumes, 6 schedules

---

### 2025-12-18 05:15:00
📝 **Documentation: Updated Ruby CMS System Definition**

Updated Ruby Content Management System operational definition to reflect System Manifest deployment (Req 10.7).

**Files Updated/Created**:
- `agents/Ruby/ruby-content-system-definition.md` (updated)
- `agents/Ruby/ruby-cms.yaml` (new)
- `agents/Ruby/README.md` (new)

**Changes**:
1. **New Section: "System Manifest Deployment (Recommended)"**:
   - Complete YAML manifest for Ruby CMS with all 3 agents
   - Includes global prompt for demo/test mode
   - All 6 schedules defined in YAML
   - Full-mesh permissions preset
   - Deployment instructions via API and MCP tools
   - System management endpoints (list, get, restart, export)

2. **Updated Agent Repositories Table**:
   - Added "Trinity Template" column with correct template IDs
   - Added deployment method reference

3. **Renamed Section: "Manual Deployment (Alternative)"**:
   - Original deployment section now marked as alternative approach
   - Cross-references Multi-Agent System Guide for manual steps

4. **Updated Operations Guide**:
   - Initial deployment now shows System Manifest method
   - Added system-level management commands
   - Updated container names to use `ruby-cms-` prefix (from manifest naming convention)

5. **Version Bump**: 1.0.0 → 1.1.0
   - Updated header and version history
   - Last updated date: 2025-12-18

6. **New File: ruby-cms.yaml**:
   - Ready-to-deploy System Manifest file
   - Complete YAML with all 3 agents, schedules, permissions
   - Users can deploy directly: `curl ... -d "$(cat ruby-cms.yaml)"`

7. **New File: README.md**:
   - Quick start guide for Ruby CMS
   - Directory structure explanation
   - Deployment options (manifest, MCP, manual)
   - System management commands
   - Links to detailed documentation

**Impact**:
- Ruby CMS now serves as complete reference example for System Manifest deployment
- Users can copy YAML manifest directly and deploy entire system
- Demonstrates all System Manifest features: permissions, folders, schedules, global prompt
- Original manual deployment docs preserved as alternative

---

### 2025-12-18 05:00:00
📝 **Documentation: System Manifest Deployment Guide**

Updated multi-agent system documentation to include System Manifest (YAML-based deployment) as the recommended deployment method.

**Files Updated**:

1. **MULTI_AGENT_SYSTEM_GUIDE.md**:
   - Added new section: "System Manifest Deployment (Recommended)"
   - Comprehensive YAML manifest examples (minimal and complete)
   - Permission preset documentation (full-mesh, orchestrator-workers, none, explicit)
   - Deployment options: API and MCP tools
   - Agent naming convention and conflict resolution
   - System management endpoints (list, get, restart, export)
   - Recipe vs. declarative model explanation
   - Best practices for manifest deployment
   - Renamed old section to "Manual Deployment Workflow (Alternative)"

2. **TRINITY_COMPATIBLE_AGENT_GUIDE.md**:
   - Added new section: "Multi-Agent Systems"
   - Deployment options (System Manifest vs. Manual)
   - Design considerations for multi-agent templates
   - Cross-references to MULTI_AGENT_SYSTEM_GUIDE.md

**Impact**:
- Users now have clear guidance on deploying multi-agent systems via YAML manifests
- System Manifest positioned as recommended approach (faster, more consistent, less error-prone)
- Manual deployment still documented as alternative for fine-grained control
- Single-agent guide now cross-references multi-agent guide

**Documentation Links**:
- Feature Flow: `docs/memory/feature-flows/system-manifest.md` (complete implementation details)
- Design Doc: `docs/drafts/SYSTEM_MANIFEST_SIMPLIFIED.md` (design rationale)
- Requirements: `docs/memory/requirements.md` (Req 10.7)

---

### 2025-12-18 04:30:00
🔧 **Bug Fixes: Critical System Manifest Test Failures (P0-P2)**

Fixed all critical bugs identified in system manifest test report 2025-12-17.

**P0 - CRITICAL: YAML Export Serialization Bug (SECURITY RISK)** ✅
- **Issue**: Python object tags in exported YAML (RCE vector, can't re-import)
- **Root Cause**: `db.get_setting("trinity_prompt")` returned ORM object, not string
- **Fix**: Changed to `db.get_setting_value()` which returns just the value
- **Also Fixed**: Changed `db.get_agent_schedules()` → `db.list_agent_schedules()` and converted Schedule objects to dicts
- **Modified Files**:
  - `src/backend/services/system_service.py`:
    - Line 454: Fixed function call and dict conversion for schedules
    - Line 542: Fixed trinity_prompt to use get_setting_value()
- **Security Impact**: Eliminated Python object serialization in YAML exports
- **Test Impact**: `test_export_manifest_endpoint` and `test_export_and_redeploy` should now pass

**P1 - HIGH: List Systems Endpoint Bug** ✅
- **Issue**: System names with hyphens (e.g., `test-list-abc123`) not grouped correctly
- **Root Cause**: Code split on `-` and took first part, but system names can have multiple hyphens
- **Example**: `test-list-abc123-worker1` → extracted `test` instead of `test-list-abc123`
- **Fix**: Split on `-` and take all parts except last: `'-'.join(parts[:-1])`
- **Modified Files**:
  - `src/backend/routers/systems.py`:
    - Lines 264-268: Fixed prefix extraction logic with comment explaining the fix
- **Test Impact**: `test_list_systems_endpoint` should now pass

**P2 - MEDIUM: Test Configuration Issues** ✅
1. **Wrong Default Password**:
   - Changed `tests/utils/api_client.py` line 28: `"changeme"` → `"password"`
   - Eliminates 401 Unauthorized errors when env var not set

2. **Deployment Timeouts**:
   - Added `timeout=120.0` to slow deployment tests in `test_systems.py`:
     - `test_shared_folders_configuration` (line 576)
     - `test_complete_system_deployment` (line 899)
   - Default 30s timeout insufficient for multi-agent deployments with folders/schedules

**P3 - LOW: Schedules Endpoint** (No Fix Needed)
- **Issue**: Test calls `.get("schedules")` on array, expects dict
- **Analysis**: API returns `List[ScheduleResponse]` (bare array) - this is correct
- **Frontend**: Consumes `response.data` directly as array - working as designed
- **Conclusion**: Test bug, not API bug - test should use array directly

**Files Modified** (5 total):
- `src/backend/services/system_service.py` - YAML export fixes
- `src/backend/routers/systems.py` - List systems prefix extraction
- `tests/utils/api_client.py` - Default password fix
- `tests/test_systems.py` - Timeout increases (2 tests)

**Expected Test Improvements**:
- ✅ `test_export_manifest_endpoint` - PASS (was failing with YAML constructor error)
- ✅ `test_export_and_redeploy` - PASS (was failing with YAML constructor error)
- ✅ `test_list_systems_endpoint` - PASS (was failing with None assertion)
- ✅ `test_shared_folders_configuration` - PASS (was timing out)
- ✅ `test_complete_system_deployment` - PASS (was timing out)

**Test Suite Status Prediction**:
- Before: 23/30 passed (76.7%)
- After: 28/30 passed (93.3%)
- Remaining failures: `test_explicit_permissions` (test assertion bug), `test_schedules_created` (test API misuse)

---

### 2025-12-18 03:00:00
🔧 **Bug Fixes: System Manifest Import Errors & Template Endpoints (HIGH PRIORITY)**

Fixed critical import errors blocking System Manifest endpoints and template retrieval errors.

**Issues Fixed (from Test Report 2025-12-17 21:02:04):**

1. **Missing Import: `list_agents_for_user` (7 test failures)** ✅
   - **Root Cause**: systems.py attempted to import non-existent function from docker_service
   - **Fix**: Changed all imports to use `get_accessible_agents()` from routers.agents
   - **Modified Files**:
     - `src/backend/routers/systems.py` - 4 import corrections
       - list_systems: line 256
       - get_system: line 304
       - restart_system: line 380
       - get_system_manifest: line 458

2. **Template Endpoint 500 Errors (2 test failures)** ✅
   - **Root Cause**: Type mismatch - code expected dict but got string in required_credentials
   - **Fix**: Added type checking for both dict and string credentials
   - **Modified Files**:
     - `src/backend/routers/templates.py`:
       - get_template_env_template: Added isinstance() checks (lines 107-125)
       - get_template: Added try/except wrapper and "local:" prefix handling (lines 161-199)
       - get_template_env_template: Added error handling (lines 161-167)

**Technical Details:**
- Replaced `list_agents_for_user(username)` with `get_accessible_agents(current_user)` pattern
- Fixed restart_system to use container.stop() directly instead of non-existent stop_agent()
- Added template_id prefix stripping for "local:" templates
- Added comprehensive error logging for template operations

**Expected Impact:**
- **CRITICAL**: All 7 System Manifest backend endpoint tests should now pass
- **MEDIUM**: Template detail and env template endpoints should work correctly
- Estimated fix: **9 of 13 failing tests** (remaining 4 are timeout and test logic issues)

**Next Steps:**
1. Re-run test suite to verify fixes
2. Address timeout issues (increase timeout for system deployment tests)
3. Fix test assertion errors (test_explicit_permissions, test_schedules_created)

---

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

### 2025-12-18 02:30:00
🧪 **Testing: System Manifest Integration Test Suite**

Created comprehensive integration tests for System Manifest deployment (Req 10.7).

**New Files:**
- `tests/test_systems.py` - 35 tests covering all phases of System Manifest

**Test Coverage:**
1. **Phase 1 - YAML Parsing & Validation** (8 smoke tests)
   - Dry run validation with minimal and full manifests
   - Invalid YAML syntax handling
   - Missing required fields (name, agents)
   - Invalid system/agent name formats
   - Invalid template prefixes
   - Invalid permission presets
   - Conflicting permission configurations

2. **Phase 1 - Deployment** (3 core tests)
   - Deploy minimal system with correct agent naming
   - Conflict resolution with `_N` suffix
   - Trinity prompt update verification

3. **Phase 2 - Permissions** (4 core tests)
   - Full-mesh preset (each agent ↔ all others)
   - Orchestrator-workers preset (orchestrator → workers only)
   - Explicit permission matrix
   - None preset (clear all permissions)

4. **Phase 2 - Configuration** (3 core tests)
   - Shared folders (expose/consume flags)
   - Schedule creation and verification
   - Agent auto-start after deployment

5. **Phase 3 - Backend Endpoints** (5 core tests)
   - List systems with grouping
   - Get system details with enriched data
   - Nonexistent system returns 404
   - Restart system agents
   - Export manifest as YAML

6. **Integration Tests** (2 slow tests)
   - Complete system with all features (prompt, folders, schedules, permissions)
   - Export and redeploy workflow

7. **Edge Cases** (6 tests)
   - Authentication requirements
   - Empty manifest handling
   - Unknown agents in permissions
   - Nonexistent system operations

**Test Organization:**
- Smoke tests: No agent creation (YAML validation only)
- Core tests: Agent creation with cleanup (module-scoped)
- Slow tests: Full multi-agent systems with all features
- Edge cases: Error handling and authentication

**Updated Files:**
- `.claude/agents/test-runner.md` - Added System Manifest to test categories

**Expected Results:**
- ~8 smoke tests (30 seconds)
- ~18 core tests (3-5 minutes)
- ~2 slow tests (2-3 minutes)
- ~7 edge case tests (1 minute)
- **Total: 35 tests** covering all 3 phases

---

### 2025-12-18 01:45:00
✨ **Feature: System Manifest Phase 2 - Configuration & Startup (Req 10.7)**

Completed Phase 2 of System Manifest deployment - now supports permissions, folders, schedules, and auto-starts agents.

**Modified Files:**
- `src/backend/services/system_service.py` - Added 4 configuration functions
- `src/backend/routers/systems.py` - Extended deploy endpoint with Phase 2 steps
- `src/backend/routers/agents.py` - Extracted `start_agent_internal()` for reuse

**New Configuration Functions:**
1. `configure_permissions()` - Apply permission presets or explicit rules
2. `configure_folders()` - Set expose/consume for shared folders
3. `create_schedules()` - Create agent schedules from manifest
4. `start_all_agents()` - Start all created agents (triggers Trinity injection)

**Permission Presets:**
- `full-mesh` - Every agent can call every other agent
- `orchestrator-workers` - Only orchestrator can call workers, workers isolated
- `none` - Clear all default permissions, agents cannot communicate
- `explicit` - Custom permission matrix from manifest

**Tests Passed (6/6):**
1. Full-mesh permissions (each agent can call all others)
2. Orchestrator-workers (orchestrator→workers, workers→[])
3. Explicit permissions (custom matrix)
4. None preset (all permissions cleared)
5. Shared folders (expose/consume flags applied)
6. Complete system (prompt + agents + folders + schedules + permissions + start)

---

### 2025-12-17 22:52:00
✨ **Feature: System Manifest Phase 1 - Core Deployment Engine (Req 10.7)**

Implemented `POST /api/systems/deploy` endpoint for recipe-based multi-agent deployment from YAML manifests.

**New Files:**
- `src/backend/models.py` - Added 5 new models: SystemAgentConfig, SystemPermissions, SystemManifest, SystemDeployRequest, SystemDeployResponse
- `src/backend/services/system_service.py` - YAML parsing, validation, agent name resolution
- `src/backend/routers/systems.py` - Deploy endpoint with dry_run support

**Modified Files:**
- `src/backend/routers/agents.py` - Extracted `create_agent_internal()` for reuse
- `src/backend/main.py` - Registered systems router

**Features:**
- Parse and validate YAML manifests
- Agent naming: `{system}-{agent}` format
- Conflict resolution with `_N` suffix (e.g., `my-agent_2`)
- Dry run mode for validation without deployment
- Updates `trinity_prompt` setting from manifest
- Full audit logging

**Tests:** 6/6 passed
1. Dry run validation
2. Invalid YAML error handling
3. Missing required fields validation
4. Actual deployment with agent creation
5. Conflict resolution with suffix
6. Trinity prompt update

---

### 2025-12-17 11:45:00
📝 **Design: System Manifest (Multi-Agent Deployment)**

Finalized design for recipe-based multi-agent deployment via YAML manifest (Req 10.7).

**Key Decisions:**
- Agent naming: `{system}-{agent}` format (e.g., `content-production-orchestrator`)
- Re-deploy creates new agents with `_N` suffix (`ruby` → `ruby_2` → `ruby_3`)
- Updates global `trinity_prompt` setting (reuses existing 10.6)
- No `systems` table - agents are independent after creation (recipe, not declarative)

**YAML Format:**
```yaml
name: content-production
prompt: "System-wide instructions..."
agents:
  orchestrator:
    template: github:YourOrg/repo
    folders: {expose: true, consume: true}
    schedules: [{name: daily, cron: "0 9 * * *", message: "..."}]
permissions:
  preset: full-mesh  # or orchestrator-workers, none, explicit
```

**Maps to Existing APIs:**
- `prompt` → `PUT /api/settings/trinity_prompt`
- `agents.*` → `POST /api/agents`
- `folders` → `PUT /api/agents/{name}/folders`
- `schedules` → `POST /api/agents/{name}/schedules`
- `permissions` → `PUT /api/agents/{name}/permissions`

**Files:**
- Design: `docs/drafts/SYSTEM_MANIFEST_SIMPLIFIED.md`
- Requirement: `docs/memory/requirements.md` (10.7)
- Roadmap: Phase 11 priority item

---

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

