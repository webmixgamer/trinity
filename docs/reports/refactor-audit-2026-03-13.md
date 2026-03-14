# Refactor Audit Report

**Generated**: 2026-03-13
**Scope**: Full codebase (`src/`, `docker/base-image/`)
**Tools**: radon (cyclomatic complexity), vulture (dead code), wc/custom scripts (file/function length)

## Summary

| Severity | Count | Description |
|----------|-------|-------------|
| Critical | 15 | Must fix — blocks AI maintenance (files >1000 lines, functions >200 lines, CC >30) |
| High | 14 | Strongly recommended (files 800-1000 lines, functions 100-200 lines, CC 20-30) |
| Medium | 18 | Recommended (files 500-800 lines, CC 15-20, functions 50-100 lines) |
| Low | 11 | Nice to have (dead code, minor complexity) |

**Total issues**: 58
**AI-Refactorable**: ~45/58 (78%) — Issues that AI can safely fix with tests

---

## Critical Issues

### Backend Files >1000 Lines

| File | Lines | Issue | Recommendation |
|------|-------|-------|----------------|
| `src/backend/routers/agents.py` | 1777 | Monolith router | Split: SSH → `routers/ssh.py`, rename → `routers/agent_rename.py`, resource config → `routers/agent_config.py` |
| `src/backend/routers/chat.py` | 1458 | 3 mega-functions + SSE proxy | Extract `chat_with_agent` (CC=34), `execute_parallel_task` (CC=33), `_execute_task_background` (CC=31) into `services/chat_service.py` |
| `src/backend/database.py` | 1270 | Delegation facade | Already refactored agents into mixins (#102). Continue: split remaining delegation groups into focused facades |
| `src/backend/db/schedules.py` | 1092 | Large DB operations class | Split: execution queries → `db/executions.py`, stats → `db/execution_stats.py` |
| `src/backend/services/process_engine/engine/execution_engine.py` | 1085 | Monolith engine | Extract step handlers into separate handler classes |
| `src/backend/routers/processes.py` | 1018 | Large router | Split CRUD vs execution vs monitoring endpoints |
| `src/backend/routers/ops.py` | 1011 | Many operational endpoints | Split fleet management vs cost reporting vs auth |
| `src/backend/db_models.py` | 1002 | All Pydantic models in one file | Split by domain: agent models, execution models, process models |

### Frontend Files >1000 Lines

| File | Lines | Issue | Recommendation |
|------|-------|-------|----------------|
| `src/frontend/src/views/Settings.vue` | 1999 | Massive settings page | Extract tab sections into `SettingsGeneral.vue`, `SettingsSlack.vue`, `SettingsGithub.vue`, etc. |
| `src/frontend/src/stores/network.js` | 1635 | Giant store | Split WebSocket logic, graph layout, data management |
| `src/frontend/src/views/ProcessEditor.vue` | 1594 | Complex editor | Extract YAML editor, step form, validation into composables/components |
| `src/frontend/src/components/ReplayTimeline.vue` | 1211 | Large component | Extract timeline rendering, zoom controls, data processing |
| `src/frontend/src/views/Agents.vue` | 1174 | Agent list + filtering | Extract filter bar, agent card rendering into sub-components |
| `src/frontend/src/components/TasksPanel.vue` | 1167 | Complex panel | Extract task form, execution list, status rendering |
| `src/frontend/src/views/AgentDetail.vue` | 1062 | Tab container | Extract tab content into dedicated panel components |

### Agent Server >1000 Lines

| File | Lines | Issue | Recommendation |
|------|-------|-------|----------------|
| `docker/base-image/agent_server/services/claude_code.py` | 1003 | Runtime service | Extract headless execution, subprocess management, output parsing |

### Functions with Extreme Complexity (CC >30)

| File | Function | CC | Lines | Recommendation |
|------|----------|----|-------|----------------|
| `src/backend/services/system_service.py:565` | `export_manifest` | 39 | ~190 | Extract per-agent export, permission mapping |
| `src/backend/services/system_service.py:93` | `validate_manifest` | 35 | ~165 | Extract validation rules into validators |
| `src/backend/routers/chat.py:59` | `chat_with_agent` | 34 | 320 | Extract auth, model resolution, execution into service |
| `src/backend/routers/chat.py:575` | `execute_parallel_task` | 33 | 260 | Extract validation, slot management, execution |
| `src/backend/routers/chat.py:379` | `_execute_task_background` | 31 | 196 | Extract metric collection, error handling |

### Functions >200 Lines

| File:Line | Function | Lines | Recommendation |
|-----------|----------|-------|----------------|
| `src/backend/services/agent_service/crud.py:51` | `create_agent_internal` | 482 | Extract: template processing, env setup, container creation, post-create hooks |
| `src/backend/services/task_execution_service.py:60` | `agent_post_with_retry` | 338 | Extract: retry logic, response parsing, error handling |
| `src/backend/routers/chat.py:59` | `chat_with_agent` | 320 | See CC>30 above |
| `docker/base-image/agent_server/services/claude_code.py:695` | `execute_headless_task` | 303 | Extract: command building, output parsing, metric extraction |
| `src/backend/services/task_execution_service.py:112` | `execute_task` | 286 | Extract: slot management, command building, cleanup |
| `src/backend/routers/system_agent.py:270` | `system_agent_terminal` | 266 | Extract WebSocket handling into terminal service |
| `src/backend/services/agent_service/terminal.py:58` | `handle_terminal_session` | 263 | Extract message routing, process management |
| `src/backend/services/agent_service/deploy.py:184` | `deploy_local_agent_logic` | 260 | Extract: validation, file ops, container setup |
| `src/backend/routers/chat.py:575` | `execute_parallel_task` | 260 | See CC>30 above |
| `docker/base-image/agent_server/routers/git.py:143` | `sync_to_github` | 252 | Extract: branch detection, conflict resolution, push logic |

---

## High Priority Issues

### Files 800-1000 Lines

| File | Lines | Notes |
|------|-------|-------|
| `src/backend/routers/settings.py` | 942 | Many settings categories — split by domain |
| `src/backend/routers/executions.py` | 898 | Could split SSE streaming from CRUD |
| `src/backend/services/process_engine/services/validator.py` | 750 | Large validation class |
| `src/backend/db/migrations.py` | 740 | Growing migration file |
| `src/backend/db/schema.py` | 738 | Schema definitions |
| `src/backend/services/system_service.py` | 713 | Contains 2 CC>30 functions |
| `src/backend/services/monitoring_service.py` | 705 | Health check logic |
| `src/frontend/src/views/Dashboard.vue` | 990 | Near-critical |
| `src/frontend/src/components/SchedulesPanel.vue` | 973 | Near-critical |
| `docker/base-image/agent_server/services/gemini_runtime.py` | 672 | 3 long functions |

### Complexity CC 20-30

| File | Function | CC |
|------|----------|----|
| `routers/agents.py:1416` | `rename_agent_endpoint` | 24 |
| `routers/observability.py:23` | `parse_prometheus_metrics` | 24 |
| `services/operator_queue_service.py:102` | `_sync_agent` | 23 |
| `routers/system_agent.py:270` | `system_agent_terminal` | 23 |
| `services/system_service.py:258` | `configure_permissions` | 23 |
| `routers/agents.py:348` | `delete_agent_endpoint` | 21 |
| `routers/systems.py:35` | `deploy_system` | 20 |

---

## Medium Priority Issues

### Files 500-800 Lines

| File | Lines |
|------|-------|
| `src/backend/routers/public.py` | 764 |
| `src/backend/services/process_engine/domain/aggregates.py` | 661 |
| `src/backend/services/process_engine/domain/events.py` | 624 |
| `src/backend/services/process_engine/domain/value_objects.py` | 612 |
| `src/backend/services/ssh_service.py` | 590 |
| `src/backend/main.py` | 590 |
| `src/backend/services/agent_client.py` | 588 |
| `src/backend/services/process_engine/services/alerts.py` | 581 |
| `src/backend/services/template_service.py` | 572 |
| `src/backend/services/process_engine/domain/step_configs.py` | 546 |
| `src/backend/routers/slack.py` | 539 |
| `src/backend/routers/system_agent.py` | 535 |
| `src/backend/services/agent_service/crud.py` | 532 |
| `src/backend/routers/avatar.py` | 523 |
| `src/backend/routers/schedules.py` | 520 |
| `src/backend/routers/monitoring.py` | 509 |
| `src/backend/services/process_engine/services/analytics.py` | 500 |
| `docker/base-image/agent_server/routers/git.py` | 643 |

### Complexity CC 15-20

| File | Function | CC |
|------|----------|----|
| `routers/executions.py:760` | `_to_detail` | 19 |
| `routers/public.py:219` | `public_chat` | 19 |
| `routers/git.py:252` | `initialize_github_sync` | 19 |
| `routers/ops.py:600` | `emergency_stop` | 18 |
| `db/schedules.py:278` | `update_schedule` | 18 |
| `routers/ops.py:430` | `list_all_schedules` | 17 |
| `routers/ops.py:43` | `get_fleet_status` | 16 |
| `routers/avatar.py:85` | `generate_default_avatars` | 15 |
| `main.py:380` | `websocket_endpoint` | 15 |

---

## Low Priority Issues

### Dead Code (vulture, 80%+ confidence)

| File | Issue |
|------|-------|
| `src/backend/database.py:29` | Unused imports: `AgentOwnership`, `AgentPermissionInfo`, `EmailWhitelistEntry`, `HealthCheckRecord`, `HealthCheckType`, `McpAgentKeyCreate`, `SharedFolderConfigUpdate`, `SharedFolderInfo` |
| `src/backend/routers/monitoring.py:18` | Unused import: `HealthCheckRecord` |
| `src/backend/services/monitoring_service.py:23` | Unused import: `HealthCheckType` |
| `src/backend/services/process_engine/events/websocket_publisher.py:10` | Unused import: `asdict` |

**Note**: `database.py` unused imports may be re-exports consumed by other modules. Verify before removing.

### MCP Server (TypeScript)

| File | Lines | Notes |
|------|-------|-------|
| `src/mcp-server/src/client.ts` | 1152 | HTTP client — large but contains many methods |
| `src/mcp-server/src/tools/agents.ts` | 735 | Agent tool definitions |
| `src/mcp-server/src/tools/schedules.ts` | 563 | Schedule tool definitions |

---

## Hotspots (Files with Multiple Issues)

Files appearing multiple times — prioritize these:

| File | Issues | Types |
|------|--------|-------|
| `src/backend/routers/chat.py` | 6 | File size (1458), 3 functions CC>30, 3 functions >200 lines |
| `src/backend/routers/agents.py` | 4 | File size (1777), 2 functions CC>20, 1 function >100 lines |
| `src/backend/services/system_service.py` | 3 | 2 functions CC>30, file 713 lines |
| `src/backend/services/agent_service/crud.py` | 2 | File 532 lines, 1 function 482 lines |
| `src/backend/services/task_execution_service.py` | 2 | 2 functions >250 lines |
| `src/frontend/src/views/Settings.vue` | 1 | 1999 lines — single largest frontend file |
| `src/frontend/src/stores/network.js` | 1 | 1635 lines — largest store |
| `docker/base-image/agent_server/services/claude_code.py` | 2 | File 1003 lines, 1 function 303 lines |

---

## Recommendations

### Quick Wins (Low Risk, High Impact)

1. **Remove dead imports** — `database.py`, `monitoring.py`, `monitoring_service.py`, `websocket_publisher.py` (verify re-exports first)
2. **Split `routers/agents.py`** (1777 lines) — SSH endpoints → `routers/ssh.py`, rename → `routers/agent_rename.py` (~300 lines each, clean separation)
3. **Split `routers/ops.py`** (1011 lines) — Already has clear sections: fleet, schedules, costs, auth report
4. **Split `Settings.vue`** (1999 lines) — Each tab section is already logically separated in the template
5. **Split `db_models.py`** (1002 lines) — Group by domain: `models/agent.py`, `models/execution.py`, `models/process.py`

### Requires Tests First

1. **Extract `chat_with_agent`** (CC=34, 320 lines) — Core execution path, needs comprehensive tests before refactoring
2. **Extract `create_agent_internal`** (482 lines) — Critical creation flow, already partially tested
3. **Refactor `system_service.py`** — `export_manifest` (CC=39) and `validate_manifest` (CC=35) need unit tests
4. **Split `task_execution_service.py`** — Both functions >250 lines, core execution path

### Architectural Changes

1. **Extract a `ChatService`** from `routers/chat.py` — Move all business logic out of route handlers into `services/chat_service.py`
2. **Split `database.py` delegation** — Continue the mixin pattern from #102 for remaining operation groups
3. **Frontend composables** — Extract shared logic from large Vue files into composables (`useTimeline`, `useAgentFilters`, `useWebSocket`)
4. **Agent server `claude_code.py`** — Split into `subprocess_manager.py`, `output_parser.py`, `headless_executor.py`

---

## Comparison with Previous Audit (2026-02-22)

| Metric | Feb 22 | Mar 13 | Trend |
|--------|--------|--------|-------|
| Critical issues | ~12 | 15 | +3 (new features added files) |
| Files >1000 lines | ~10 | 15 | +5 |
| Max file size (backend) | agents.py 1600 | agents.py 1777 | Growing |
| Max CC | chat_with_agent 30 | export_manifest 39 | Worse |
| Dead code findings | 8 | 11 | +3 |

**Notable improvements since Feb:**
- `db/agents.py` was split into 6 focused mixins (#102) — reduced from ~1000 to ~160 lines
- New services follow smaller file conventions (cleanup_service, slot_service)

**New hotspots since Feb:**
- `routers/ops.py` crossed 1000 lines (Operating Room feature)
- `system_service.py` added `export_manifest` (CC=39)
- `Settings.vue` grew to 1999 lines (Slack, GitHub template config)

---

## Next Steps

1. Run `/refactor-audit --quick` after fixes to verify improvement
2. Prioritize `routers/chat.py` — highest complexity hotspot (3 functions CC>30)
3. Add tests for `system_service.py` before splitting (CC=39 and CC=35)
4. Use small, incremental PRs for each split (one file per PR)
