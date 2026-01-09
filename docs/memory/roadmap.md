# Trinity Roadmap

> **Purpose**: Phased implementation plan derived from requirements.
> Work topmost incomplete items. All items must trace to `requirements.md`.
>
> **Vision**: Trinity implements the Four Pillars of Deep Agency for System 2 AI.

---

## Current Priority Queue

### 🐛 Bug Fixes (Priority)

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ⏳ | Executions 404 for Non-Existent Agent | `GET /api/agents/{name}/executions` returns `200 + []` instead of `404` for non-existent agents. Should add agent existence check before returning empty list. | LOW |
| ⏳ | Test Client Headers Bug | `TrinityApiClient.post()` in `tests/utils/api_client.py` passes `headers` param twice to httpx when caller also provides headers. Fix: merge headers instead of passing separately. | LOW |
| ⏳ | Emergency Stop Test Timeout | `test_emergency_stop_returns_structure` times out (>2 min) with multiple agents. Increase test timeout to 180s or mock the operation. | LOW |
| ✅ | Context % Calculation Bug | **Fixed 2025-12-12**: Main bug was in agent_server/routers/chat.py incorrectly summing input_tokens + cache_creation_tokens + cache_read_tokens, causing >100% display (130%, 289%). cache_creation and cache_read are billing SUBSETS, not additional tokens. Now uses metadata.input_tokens directly (authoritative total from modelUsage). Also fixed in scheduler_service.py (2 locations, 2025-12-06) and claude_code.py logging. | HIGH |
| ✅ | Template Detail Endpoint 404 | **Fixed 2025-12-22**: `GET /api/templates/{id}` returned 404 for GitHub templates like `github:org/repo`. Root cause: The `/` in the template ID was interpreted as path separator. Fix: Changed route from `{template_id}` to `{template_id:path}` to capture full path including slashes. | MEDIUM |
| ✅ | .env Template Endpoint Bug | **Verified 2025-12-22**: Endpoint works correctly. Code at lines 110-130 already handles both string credentials (GitHub templates) and dict credentials (local templates). Tested all GitHub templates + local templates - all pass. | MEDIUM |

---

### Phase 9: Deep Agent Core Infrastructure (Pillar I - Explicit Planning)
🚧 **In Progress** — *Critical for Deep Agent positioning*

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ✅ | Task DAG Engine (Backend) | External task graph representation - API + storage | HIGH |
| ✅ | Task State Tracking | pending → active → completed → failed state machine | HIGH |
| ✅ | Plan Persistence | Store/restore task DAGs across sessions | HIGH |
| ✅ | Trinity Meta-Prompt Injection | Platform injects planning commands at startup | HIGH |
| ✅ | Task DAG Visualization (Dashboard) | AgentNode shows current task + progress bar in Collaboration Dashboard | HIGH |
| ✅ | **AgentDetail Plans UI** | Plans tab showing plan list, task details, status badges (2025-12-07) | HIGH |
| ✅ | **Agent Permissions (9.10)** | Permission grants control which agents can call each other (2025-12-13) | HIGH |
| ✅ | **Agent Shared Folders (9.11)** | File-based collaboration via shared Docker volumes (2025-12-13) | HIGH |
| ⏳ | Task Actions UI | Manual complete/fail/re-run buttons for tasks | LOW |
| ⏳ | Failure Recovery | Plan restructuring when steps fail (add debug nodes) | MEDIUM |
| ⏳ | Sentinel/Watchdog Agents | Low-cost monitors detecting infinite loops, human escalation | MEDIUM |
| ⏳ | Thinking Budget | Cost limits per reasoning task ($X max spend) | MEDIUM |

### Phase 10: Deep Agent Memory & Observability (Pillar III Enhancement)
🚧 **In Progress**

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ❌ | ~~Agent Vector Memory (Chroma)~~ | REMOVED (2025-12-24) - Templates should define their own memory | ~~MEDIUM~~ |
| ❌ | ~~Chroma MCP Server~~ | REMOVED (2025-12-24) - Platform should not inject agent capabilities | ~~HIGH~~ |
| ⏳ | Memory Folding | Periodic context compression to summary files | HIGH |
| ⏳ | Reasoning Chain Logs | Capture "why" decisions, not just tool calls | MEDIUM |
| ⏳ | Cognitive Rollback | Git-based agent state restoration | MEDIUM |
| ⏳ | Vectorized Episodic Memory | Auto-store conversations for "Have I solved this before?" | LOW |

### Phase 11: Ecosystem & Enterprise
🚧 **In Progress**

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ✅ | **System Manifest (10.7)** | Recipe-based multi-agent deployment via YAML - complete (agent creation, conflict resolution, trinity_prompt, folders, schedules, permissions, auto-start). Completed 2025-12-18. | HIGH |
| ✅ | **OpenTelemetry Integration** | OTel Collector + env var injection for Claude Code metrics export. Completed 2025-12-20. | HIGH |
| ✅ | **OpenTelemetry UI (10.8)** | Display OTel metrics in Dashboard - cost, tokens, productivity. Backend API + header summary + panel detail. Completed 2025-12-20. | HIGH |
| ✅ | **Internal System Agent (11.1)** | Auto-deployed platform orchestrator (`trinity-system`) with deletion protection, system-scoped MCP key, permission bypass. Completed 2025-12-20. | HIGH |
| ✅ | **Parallel Headless Execution (12.1)** | Stateless parallel task execution - enables orchestrator to spawn N worker tasks simultaneously. `POST /api/agents/{name}/task` bypasses queue. MCP `chat_with_agent(parallel=true)`. Completed 2025-12-22. | **HIGH** |
| ✅ | **OWASP Security Hardening** | Fixed 7/14 OWASP Top 10:2025 issues - SECRET_KEY, password hashing, Redis auth, WebSocket auth, CORS, error sanitization. Completed 2025-12-23. | **HIGH** |
| ✅ | **Web Terminal for System Agent (11.5)** | Browser-based xterm.js terminal with PTY forwarding via Docker exec. Full Claude Code TUI. Admin-only, no SSH exposure. Completed 2025-12-25. | **HIGH** |
| ⏳ | System Manifest UI | Upload YAML, view deployment results, group agents by system prefix | MEDIUM |
| ⏳ | A2A Protocol Support | Agent discovery and negotiation across boundaries | LOW |
| ⏳ | Agent collaboration execution tracking | Extend schedule_executions | LOW |
| ⏳ | Automated sync modes (scheduled, on-stop) | GitOps enhancement | LOW |
| ⏳ | Automated secret rotation | Security enhancement | LOW |

### Phase 11.5: Content Management & File Operations
🚧 **In Progress** — *Essential for agents generating large assets (video, audio, exports)*

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ✅ | **Content Folder Convention (12.1)** | `content/` directory gitignored by default, persists across restarts. Implemented 2025-12-27. | **HIGH** |
| ✅ | **File Manager Page (12.2)** | Dedicated `/files` page with agent selector, two-panel layout (tree + preview), delete operations. Implemented 2025-12-27. | **HIGH** |
| ✅ | File Preview Support | Preview images, video, audio, text/code, PDF in right panel. Implemented 2025-12-27. | HIGH |
| ✅ | Delete Operations | Delete file/folder with confirmation, protected file warnings. Implemented 2025-12-27. | HIGH |
| ⏳ | Create Folder | Create new directories in agent workspace | MEDIUM |

**Content Convention**:
```
/home/developer/
├── [workspace files]     # Synced to Git
├── content/              # NOT synced - videos, audio, exports
│   ├── videos/
│   ├── audio/
│   └── exports/
└── .gitignore            # Includes: content/
```

### Phase 12: Agent Perception & Attention (Cognitive Patterns)
⏳ **Pending** — *Emergent coordination via event-driven cognition*

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ⏳ | **Event Bus Infrastructure** | Platform-wide pub/sub system for agent event broadcasting and subscription | HIGH |
| ⏳ | Event Types & Schema | Define standard event types (task_completed, anomaly_detected, resource_available, attention_required) | HIGH |
| ⏳ | Agent Event Subscriptions | Agents declare interest in event types via template.yaml or runtime API | MEDIUM |
| ⏳ | Event Persistence & Replay | Store events for late-joining agents and debugging | MEDIUM |
| ⏳ | **Attention Amplification Pattern** | Cognitive pattern: agents select salient events from perception and amplify to others | HIGH |
| ⏳ | Salience Scoring | Agents assign importance scores to perceived events based on relevance to their goals | MEDIUM |
| ⏳ | Broadcast Amplification | High-salience events re-broadcast with amplification metadata (source_agent, salience_score, reasoning) | MEDIUM |
| ⏳ | Attention Cascade Detection | Platform detects when multiple agents amplify same event (emergent consensus) | LOW |
| ⏳ | Attention Dashboard | Visualize event flow and amplification patterns in Collaboration Dashboard | LOW |

**Cognitive Pattern: Attention Amplification**
```
1. Agent perceives events from subscribed channels
2. Agent evaluates salience: "Does this require attention?"
3. High-salience events are re-broadcast with amplification:
   {
     "type": "attention_required",
     "original_event": {...},
     "amplified_by": "agent-name",
     "salience_score": 0.92,
     "reasoning": "Anomaly in data pipeline may affect downstream agents"
   }
4. Other agents see amplified events with social proof
5. Platform tracks amplification cascades for emergent coordination
```

---

## Completed Phases

### Phase 7: GitHub Sync (Source Mode + Working Branch Mode)
✅ **Completed: 2025-11-29, Updated: 2025-12-30**

**Architecture Document**: `docs/GITHUB_NATIVE_AGENTS.md`

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Database schema: `agent_git_config` table | 2025-11-29 |
| ✅ | Working branch mode: Create branch on GitHub-template creation | 2025-11-29 |
| ✅ | Store repo URL, branch name, instance ID in database | 2025-11-29 |
| ✅ | POST `/api/agents/{name}/git/sync` endpoint (push) | 2025-11-29 |
| ✅ | POST `/api/agents/{name}/git/pull` endpoint | 2025-11-29 |
| ✅ | Git operations: stage, commit, force push | 2025-11-29 |
| ✅ | "Sync to GitHub" button in agent detail UI | 2025-11-29 |
| ✅ | Track last commit SHA and push timestamp | 2025-11-29 |
| ✅ | "Git" tab in agent detail page | 2025-11-29 |
| ✅ | Show repo, branch, last sync, commit history | 2025-11-29 |
| ✅ | Sync status indicator | 2025-11-29 |
| ✅ | **Source mode (default)**: Track source branch, pull-only | 2025-12-30 |
| ✅ | **Pull button**: Blue "Pull" button in agent header | 2025-12-30 |
| ✅ | **source_branch/source_mode fields**: DB schema update | 2025-12-30 |
| ✅ | **Content folder convention**: `content/` gitignored for large files | 2025-12-30 |

### Phase 6: Agent Scheduling & Autonomy
✅ **Completed: 2025-11-28**

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Platform scheduler service (APScheduler) | 2025-11-28 |
| ✅ | Schedule CRUD API endpoints | 2025-11-28 |
| ✅ | Cron-style scheduling support | 2025-11-28 |
| ✅ | Schedule UI on agent detail page | 2025-11-28 |
| ✅ | Scheduled executions list & logs | 2025-11-28 |
| ✅ | Enable/disable & manual trigger | 2025-11-28 |
| ✅ | Timezone support | 2025-11-28 |
| ✅ | WebSocket broadcast for execution events | 2025-11-28 |

### Phase 5: Agent Sharing & Observability
✅ **Completed: 2025-11-28**

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Agent sharing (Owner/Shared/Admin access) | 2025-11-28 |
| ✅ | Context window tracking in chat header | 2025-11-28 |
| ✅ | Agent live telemetry (CPU, memory, network, uptime) | 2025-11-28 |
| ✅ | Unified activity panel for tool calls | 2025-11-28 |
| ✅ | Session cost tracking | 2025-11-28 |
| ✅ | New session reset button | 2025-11-28 |
| ✅ | Markdown rendering in chat | 2025-11-28 |

### Phase 4: Multi-Agent Support
✅ **Completed: 2025-11-27**

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Trinity MCP server (12 tools) | 2025-11-27 |
| ✅ | MCP API key authentication | 2025-11-27 |
| ✅ | Per-user API keys | 2025-11-27 |
| ✅ | Inter-agent chat via MCP | 2025-11-27 |
| ✅ | MCP usage statistics | 2025-11-27 |
| ✅ | Credential hot-reload | 2025-11-28 |
| ✅ | Bulk credential import | 2025-11-27 |
| ✅ | Credential requirements visibility | 2025-11-27 |

### Phase 3.5: Credential Management
✅ **Completed: 2025-11-27**

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Redis-backed credential storage | 2025-11-25 |
| ✅ | OAuth2 flows (Google, Slack, GitHub, Notion) | 2025-11-25 |
| ✅ | Credential injection at agent creation | 2025-11-25 |
| ✅ | Manual credential entry | 2025-11-25 |
| ✅ | SQLite data persistence (users, ownership, API keys) | 2025-11-27 |

### Phase 3: Enhanced Security
✅ **Completed: 2025-11-27**

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Auth0 + Google OAuth integration | 2025-11-27 |
| ✅ | Domain restriction (@ability.ai) | 2025-11-27 |
| ✅ | Container security (non-root, cap-drop) | 2025-11-26 |
| ✅ | Audit logging service | 2025-11-26 |
| ✅ | Network isolation | 2025-11-26 |
| ✅ | Development mode bypass | 2025-11-27 |

### Phase 2: Web Management Interface
✅ **Completed: 2025-11-25**

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Vue.js frontend with Tailwind | 2025-11-22 |
| ✅ | Agent list dashboard | 2025-11-22 |
| ✅ | Agent creation UI | 2025-11-22 |
| ✅ | Agent start/stop controls | 2025-11-22 |
| ✅ | Real-time WebSocket updates | 2025-11-22 |
| ✅ | GCP production deployment | 2025-11-25 |
| ✅ | SSL/TLS via Let's Encrypt | 2025-11-25 |

### Phase 1: Base Infrastructure
✅ **Completed: 2025-11-22**

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Universal agent base image | 2025-11-20 |
| ✅ | Multi-runtime support (Python, Node, Go) | 2025-11-20 |
| ✅ | Claude Code installation | 2025-11-20 |
| ✅ | FastAPI backend | 2025-11-21 |
| ✅ | Docker SDK integration | 2025-11-21 |
| ✅ | Agent creation/deletion | 2025-11-21 |
| ✅ | Chat via backend API | 2025-11-22 |
| ✅ | Template system (GitHub + local) | 2025-11-22 |

---

### Phase 13: Agent Scalability & Event-Driven Architecture
⏳ **Pending** — *Foundation for process-driven systems*

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ⏳ | **Horizontal Agent Scalability (13.1)** | Agent pools with N instances, load balancing, auto-scaling based on queue depth | HIGH |
| ⏳ | **Event Bus Infrastructure (13.2)** | Redis Streams pub/sub, permission-gated subscriptions, event persistence | HIGH |
| ⏳ | **Event Handlers & Reactions (13.3)** | Configure automatic agent reactions to events from permitted agents | HIGH |

### Phase 14: Process-Driven Multi-Agent Systems (Future Vision)
⏳ **Pending** — *Business process orchestration platform*

> **Concept Document**: `docs/drafts/PROCESS_DRIVEN_AGENTS.md`

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ⏳ | **Business Process Definitions (14.1)** | Processes as first-class entities with RACI matrix, triggers, policies | Future |
| ⏳ | **System Agent as Orchestrator (14.2)** | Conversational process design, testing, and monitoring via System Agent | Future |
| ⏳ | **Human-in-the-Loop Improvement** | Feedback collection, agent instruction updates, quality tracking | Future |
| ⏳ | **Process Designer UI** | Visual process builder with RACI matrix editor | Future |
| ⏳ | **Process Dashboard** | Process monitoring, execution history, metrics | Future |

### Phase 15: Compliance-Ready Development Methodology
⏳ **Pending** — *SOC-2 and ISO-compatible AI development practices*

> **Template Location**: `dev-methodology-template/`

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ⏳ | **SOC-2 Control Mapping** | Map methodology components to SOC-2 Trust Service Criteria (Security, Availability, Confidentiality) | HIGH |
| ⏳ | **ISO 27001 Alignment** | Align with ISO 27001:2022 controls for ISMS (A.8 Asset Management, A.14 System Dev) | HIGH |
| ⏳ | **Change Management Controls** | Formalize changelog, approval workflows, rollback procedures per SOC-2 CC8.1 | HIGH |
| ⏳ | **Access Control Documentation** | Document RBAC model, credential handling, audit trail requirements | MEDIUM |
| ⏳ | **Security Review Gates** | Mandatory `/security-check` before commits, OWASP compliance verification | MEDIUM |
| ⏳ | **Audit Trail Requirements** | Structured logging, immutable changelog, evidence retention policies | MEDIUM |
| ⏳ | **Incident Response Procedures** | Add `incidents.md` memory file, response playbooks, escalation paths | MEDIUM |
| ⏳ | **Compliance Evidence Generation** | Automated report generation for auditors (changelog → evidence, test runs → attestation) | LOW |

**Scope**: Extend `dev-methodology-template/` to produce development artifacts that satisfy:
- **SOC-2 Type II**: Trust Service Criteria for service organizations
- **ISO 27001**: Information Security Management System requirements
- **ISO 27701**: Privacy extension (GDPR alignment)

**Deliverables**:
- Control mapping documents (SOC-2, ISO 27001)
- Enhanced security-analyzer agent with compliance checks
- Audit-ready documentation templates
- Compliance dashboard/report generation

---

## Backlog

Items not yet scheduled. Will be prioritized as needed.

| Priority | Item | Requirement |
|----------|------|-------------|
| **High** | **Horizontal Agent Scalability** | 13.1 - Agent pools with multiple instances for parallel workloads |
| **High** | **Event Bus Infrastructure** | 13.2 - Platform-wide pub/sub for agent event broadcasting/subscription |
| **High** | **Event Handlers & Reactions** | 13.3 - Automatic agent reactions to events from permitted agents |
| **High** | **Attention Amplification Pattern** | Phase 12 - Cognitive pattern for salience-based event amplification |
| Medium | **Process-Driven Systems** | 14.1, 14.2 - Business process orchestration (see concept doc) |
| Medium | **SOC-2/ISO Compliance Methodology** | 15.* - Extend dev-methodology-template for audit-ready practices |
| Low | Task DAG Graph Visualization | 9.8 - Visual dependency graph (Vue Flow) - backend ready, UI nice-to-have |
| Medium | Kubernetes deployment scripts | 10.3 Kubernetes Deployment |
| Medium | Helm charts | 10.3 Kubernetes Deployment |
| Low | Automated testing pipeline | Non-functional |
| Low | Performance monitoring dashboard | Non-functional |
| Low | Agent resource usage alerts | Non-functional |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-09 | Compliance-Ready Development Methodology (Phase 15) | Extend `dev-methodology-template/` to produce SOC-2 and ISO 27001-compatible development artifacts. The existing methodology (slash commands, memory files, security-check, changelog) maps naturally to compliance controls. Formalizing this enables enterprise adoption and audit-ready AI development practices. |
| 2026-01-06 | Process-Driven Multi-Agent Vision | Evolution from agent management to business process orchestration. Processes define agents (not vice versa). RACI matrix for role assignment. System Agent as primary interface for design/test/monitor. Human-in-the-loop improvement cycles. See `docs/drafts/PROCESS_DRIVEN_AGENTS.md`. |
| 2026-01-06 | Event Bus with Permission-Gated Subscriptions | Agents subscribe to events from permitted agents only (reuses agent_permissions). Event handlers trigger agent execution like schedules but event-driven. Foundation for process-driven systems. |
| 2026-01-06 | Horizontal Agent Scalability | Agent pools with N instances for parallel task processing. Load balancing, auto-scaling, shared credentials. Enables high-throughput workflows. |
| 2025-12-22 | Parallel Headless Execution (12.1) | Two execution modes: Sequential Chat (maintains context with --continue) and Parallel Task (stateless, no lock). Enables orchestrators to spawn N parallel worker tasks. Based on Claude Code headless mode research. |
| 2025-12-20 | Internal System Agent (11.1) | Platform needs a privileged orchestrator that auto-deploys on startup, executes system-level user requests, and cannot be deleted. Enables unified multi-agent coordination. |
| 2025-12-08 | Deprioritize Task DAG Graph Viz | Backend workplan system complete; text-based UI sufficient for now; graph viz is nice-to-have |
| 2025-12-05 | Deep Agent positioning | Trinity = "Four Pillars of Deep Agency" platform. Pillar I (Explicit Planning) is the priority gap. |
| 2025-11-26 | Docker as source of truth | Eliminates in-memory registry issues with multiple workers |
| 2025-11-27 | SQLite + Redis hybrid | SQLite for relations, Redis for secrets - survives restarts |
| 2025-11-27 | No external agent UI ports | Security - all access via authenticated backend API |
| 2025-11-28 | Auth0 domain restriction | Enterprise security - @ability.ai only |

---

## How to Use This Document

1. **Check current phase** - Work on items in "Current Priority Queue"
2. **Pick topmost ⏳** - Start with first incomplete item
3. **Update on completion** - Change ⏳ to ✅, add date
4. **Move to completed** - Once all items done, move phase to "Completed Phases"
5. **Add new items** - Must trace to `requirements.md` requirement ID
