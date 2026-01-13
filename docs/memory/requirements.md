# Trinity Deep Agent Orchestration Platform - Requirements

> **SINGLE SOURCE OF TRUTH** - All development must trace back to this document.
> Update this file BEFORE implementing any new feature.

## Vision: The Four Pillars of Deep Agency

Trinity implements infrastructure for "System 2" AI — Deep Agents that plan, reason, and execute autonomously.

| Pillar | Description | Implementation Status |
|--------|-------------|----------------------|
| **I. Explicit Planning** | Task DAGs persisting outside context window | ❌ REMOVED (2025-12-23) - Deferred to orchestrator-level |
| **II. Hierarchical Delegation** | Orchestrator-Worker with context quarantine | ✅ Agent-to-Agent via MCP |
| **III. Persistent Memory** | Virtual filesystems, memory folding | ✅ Chat persistence, file browser |
| **IV. Extreme Context Engineering** | High-Order Prompts defining reasoning | ✅ Templates with CLAUDE.md |

## Status Labels
- ⏳ Not Started
- 🚧 In Progress
- ✅ Implemented
- ❌ Removed

---

## 1. Core Agent Management

### 1.1 Agent Creation
- **Status**: ✅ Implemented
- **Description**: Create agents from templates (GitHub or local) or from scratch
- **Key Features**: Web UI, REST API, GitHub templates (`github:Org/repo`), local templates, credential schema auto-detection

### 1.2 Agent Start/Stop
- **Status**: ✅ Implemented
- **Description**: Start and stop agent containers with visual feedback
- **Key Features**: Loading spinners, toast notifications, WebSocket status broadcasts

### 1.3 Agent Deletion
- **Status**: ✅ Implemented
- **Description**: Delete agents and cleanup resources
- **Key Features**: Container cleanup, network cleanup, cascade delete sharing records

### 1.4 Agent Logs Viewing
- **Status**: ✅ Implemented
- **Description**: View container logs for debugging
- **Key Features**: Logs tab, fixed-height scrollable container, auto-refresh, smart auto-scroll

### 1.5 Agent Live Telemetry
- **Status**: ✅ Implemented
- **Description**: Real-time container metrics in agent header
- **Key Features**: CPU/memory usage, network I/O, uptime display, auto-refresh every 10 seconds

---

## 2. Authentication & Authorization

### 2.1 Email-Based Authentication
- **Status**: ✅ Implemented (2025-12-26)
- **Description**: Passwordless email login with 6-digit verification codes
- **Key Features**: 2-step verification, admin-managed whitelist, auto-whitelist on agent sharing, rate limiting
- **Flow**: `docs/memory/feature-flows/email-authentication.md`

### 2.2 Admin Password Login
- **Status**: ✅ Implemented
- **Description**: Password-based fallback for admin user
- **Key Features**: Bcrypt hashing, first-time setup wizard

### 2.3 Session Persistence
- **Status**: ✅ Implemented
- **Description**: User profile survives page refresh via localStorage JWT

### 2.4 Agent Sharing
- **Status**: ✅ Implemented
- **Description**: Share agents with team members
- **Key Features**: Share via email, access levels (Owner/Shared/Admin), sharing tab for owners

### 2.5 Auth0 OAuth
- **Status**: ❌ Removed (2026-01-01)
- **Reason**: Auth0 SDK caused blank pages on HTTP LAN access. Email auth is simpler and works everywhere.

---

## 3. Credential Management

### 3.1 Manual Credential Entry
- **Status**: ✅ Implemented
- **Description**: Add credentials via UI form with name, value, service

### 3.2 OAuth2 Flows
- **Status**: ✅ Implemented
- **Description**: OAuth2 authentication for Google, Slack, GitHub, Notion
- **Key Features**: MCP-compatible credential normalization

### 3.3 Credential Hot-Reload
- **Status**: ✅ Implemented
- **Description**: Update credentials on running agents without restart
- **Key Features**: Hot-reload via UI paste, writes `.env` and regenerates `.mcp.json`

### 3.4 Bulk Credential Import
- **Status**: ✅ Implemented
- **Description**: Paste `.env`-style KEY=VALUE pairs with template selector

### 3.5 Credential Requirements Extraction
- **Status**: ✅ Implemented
- **Description**: Extract from `.mcp.json.template` and show configured vs missing status

---

## 4. Template System

### 4.1 Local Templates
- **Status**: ✅ Implemented
- **Description**: Auto-discovery from `config/agent-templates/`

### 4.2 GitHub Templates
- **Status**: ✅ Implemented
- **Description**: Clone via `github:Org/repo` format with PAT authentication

### 4.3 Template Metadata
- **Status**: ✅ Implemented
- **Description**: Read template.yaml for display name, description, resources, credentials

---

## 5. Agent Chat & Terminal

### 5.1 Agent Terminal
- **Status**: ✅ Implemented (2025-12-25)
- **Description**: Browser-based xterm.js terminal with Claude Code TUI
- **Key Features**: PTY forwarding, mode toggle (Claude/Gemini/Bash), resize support
- **Flow**: `docs/memory/feature-flows/agent-terminal.md`

### 5.2 Chat via Backend API
- **Status**: ✅ Implemented
- **Description**: `/api/agents/{name}/chat` endpoint with stream-json output parsing

### 5.3 Conversation History
- **Status**: ✅ Implemented
- **Description**: Persistent chat history per agent stored in database

### 5.4 Context Window Tracking
- **Status**: ✅ Implemented
- **Description**: Token usage display (e.g., "45.5K / 200K") with color-coded progress bar

### 5.5 Session Cost Tracking
- **Status**: ✅ Implemented
- **Description**: Cumulative cost display across conversation

---

## 6. Activity Monitoring

### 6.1 Unified Activity Panel
- **Status**: ✅ Implemented
- **Description**: Real-time tool execution tracking with `--output-format stream-json --verbose`

### 6.2 Tool Chips with Counts
- **Status**: ✅ Implemented
- **Description**: Visual counts per tool type, sorted by frequency

### 6.3 Expandable Timeline
- **Status**: ✅ Implemented
- **Description**: List of all tool calls with timestamps and durations

### 6.4 Unified Activity Stream
- **Status**: ✅ Implemented (2025-12-02)
- **Description**: Centralized `agent_activities` table for all runtime activities
- **Flow**: `docs/memory/feature-flows/activity-stream.md`

---

## 7. MCP Server

### 7.1 Trinity MCP Server
- **Status**: ✅ Implemented
- **Description**: Agent orchestration via Model Context Protocol
- **Key Features**: FastMCP with Streamable HTTP, 21 tools, API key authentication
- **Flow**: `docs/memory/feature-flows/mcp-orchestration.md`

### 7.2 Per-User API Keys
- **Status**: ✅ Implemented
- **Description**: Generate, revoke, and track usage per key

---

## 8. Infrastructure

### 8.1 Docker as Source of Truth
- **Status**: ✅ Implemented
- **Description**: No in-memory registry; query Docker directly with container labels

### 8.2 SQLite Data Persistence
- **Status**: ✅ Implemented
- **Description**: Users, ownership, API keys, chat sessions via bind mount

### 8.3 Redis for Secrets
- **Status**: ✅ Implemented
- **Description**: Credential storage, OAuth state with AOF persistence

### 8.4 Audit Logging
- **Status**: ✅ Implemented
- **Description**: Security event tracking via Vector log aggregation

### 8.5 Container Security
- **Status**: ✅ Implemented
- **Description**: Non-root execution, CAP_DROP ALL, isolated network
- **Key Features**: Optional full capabilities mode for containers needing system access

### 8.6 GCP Production Deployment
- **Status**: ✅ Implemented
- **Description**: SSL/TLS via Let's Encrypt, nginx reverse proxy

### 8.7 Vector Log Aggregation
- **Status**: ✅ Implemented (2025-12-31)
- **Description**: Centralized log aggregation via Vector replacing audit-logger
- **Key Features**: Docker socket capture, VRL transforms, platform.json/agents.json output
- **Flow**: `docs/memory/feature-flows/vector-logging.md`

---

## 9. Agent Collaboration

### 9.1 Agent-to-Agent Communication
- **Status**: ✅ Implemented (2025-11-29)
- **Description**: Agents communicate via Trinity MCP with agent-scoped API keys
- **Flow**: `docs/memory/feature-flows/agent-to-agent-collaboration.md`

### 9.2 Agent Permissions
- **Status**: ✅ Implemented (2025-12-10)
- **Description**: Explicit permission model controlling which agents can call which
- **Key Features**: Permissions tab in UI, default grant for same-owner agents
- **Flow**: `docs/memory/feature-flows/agent-permissions.md`

### 9.3 Agent Shared Folders
- **Status**: ✅ Implemented (2025-12-13)
- **Description**: File-based collaboration via shared Docker volumes
- **Key Features**: Expose/consume toggles, permission-gated mounting
- **Flow**: `docs/memory/feature-flows/agent-shared-folders.md`

### 9.4 Collaboration Dashboard
- **Status**: ✅ Implemented (2025-12-02)
- **Description**: Real-time visual graph showing agents and animated connections
- **Key Features**: Vue Flow, draggable nodes, context progress bars, replay mode
- **Flow**: `docs/memory/feature-flows/agent-network.md`

### 9.5 Dashboard Timeline View
- **Status**: ✅ Implemented (2026-01-10)
- **Description**: Graph/Timeline mode toggle with execution visualization
- **Key Features**: Execution boxes (color-coded by trigger), collaboration arrows, live streaming
- **Flow**: `docs/memory/feature-flows/dashboard-timeline-view.md`

### 9.6 Replay Timeline Component
- **Status**: ✅ Implemented (2026-01-04)
- **Description**: Waterfall-style timeline visualization of agent activities
- **Key Features**: Zoom controls (50%-2000%), agent rows, activity bars, communication arrows
- **Flow**: `docs/memory/feature-flows/replay-timeline.md`

### 9.7 Task DAG System
- **Status**: ❌ Removed (2025-12-23)
- **Reason**: Individual agent planning deferred to orchestrator-level. Claude Code handles task management internally.

---

## 10. Scheduling & Autonomy

### 10.1 Agent Scheduling
- **Status**: ✅ Implemented (2025-11-28)
- **Description**: Cron-based automation with APScheduler
- **Key Features**: Schedule CRUD, timezone support, execution history, manual trigger
- **Flow**: `docs/memory/feature-flows/scheduling.md`

### 10.2 Autonomy Mode
- **Status**: ✅ Implemented (2026-01-01)
- **Description**: Master toggle for agent autonomous operation
- **Key Features**: Dashboard toggle, enables/disables all schedules
- **Flow**: `docs/memory/feature-flows/autonomy-mode.md`

### 10.3 Execution Queue
- **Status**: ✅ Implemented
- **Description**: Redis-based queue preventing parallel execution conflicts
- **Flow**: `docs/memory/feature-flows/execution-queue.md`

### 10.4 Execution Termination
- **Status**: ✅ Implemented (2026-01-12)
- **Description**: Stop running executions via process registry
- **Key Features**: SIGINT/SIGKILL flow, queue release, activity tracking
- **Flow**: `docs/memory/feature-flows/execution-termination.md`

---

## 11. GitHub Integration

### 11.1 GitHub Sync
- **Status**: ✅ Implemented (2025-11-29, Updated 2025-12-30)
- **Description**: Two sync modes - Source (pull-only, default) and Working Branch (bidirectional)
- **Key Features**: Pull button, sync button, content folder gitignored
- **Flow**: `docs/memory/feature-flows/github-sync.md`

### 11.2 GitHub Repository Initialization
- **Status**: ✅ Implemented
- **Description**: Initialize GitHub sync for existing agents
- **Flow**: `docs/memory/feature-flows/github-repo-initialization.md`

---

## 12. Platform Operations

### 12.1 Internal System Agent
- **Status**: ✅ Implemented (2025-12-20)
- **Description**: Auto-deployed platform orchestrator (`trinity-system`)
- **Key Features**: Deletion-protected, system-scoped MCP key, permission bypass, ops commands
- **Flow**: `docs/memory/feature-flows/internal-system-agent.md`

### 12.2 System Agent Operations Scope
- **Status**: ✅ Implemented (2025-12-20)
- **Description**: Fleet ops, health monitoring, schedule control, emergency stop
- **Key Features**: `/ops/*` slash commands, configurable thresholds
- **Guiding Principle**: "The system agent manages the orchestra, not the music."

### 12.3 Web Terminal for System Agent
- **Status**: ✅ Implemented (2025-12-25)
- **Description**: Admin-only browser terminal for System Agent
- **Flow**: `docs/memory/feature-flows/web-terminal.md`

### 12.4 System Agent UI Page
- **Status**: ✅ Implemented (2025-12-20)
- **Description**: Admin-only `/system-agent` page with fleet overview and operations console
- **Key Features**: Fleet cards, Emergency Stop, Restart All, Pause/Resume Schedules
- **Flow**: `docs/memory/feature-flows/system-agent-ui.md`

### 12.5 OpenTelemetry Integration
- **Status**: ✅ Implemented (2025-12-20)
- **Description**: OTel metrics export from Claude Code agents
- **Key Features**: Cost, tokens, productivity metrics in Dashboard
- **Flow**: `docs/memory/feature-flows/opentelemetry-integration.md`

### 12.6 System-Wide Trinity Prompt
- **Status**: ✅ Implemented (2025-12-14)
- **Description**: Admin-configurable prompt injected into all agents' CLAUDE.md
- **Flow**: `docs/memory/feature-flows/system-wide-trinity-prompt.md`

### 12.7 Vector Memory
- **Status**: ❌ Removed (2025-12-24)
- **Reason**: Templates should define their own memory. Platform should not inject agent capabilities.

---

## 13. Content & File Management

### 13.1 File Browser
- **Status**: ✅ Implemented
- **Description**: Browse and download workspace files in AgentDetail Files tab
- **Flow**: `docs/memory/feature-flows/file-browser.md`

### 13.2 File Manager Page
- **Status**: ✅ Implemented (2025-12-27)
- **Description**: Dedicated `/files` page with two-panel layout and rich previews
- **Key Features**: Agent selector, tree view, image/video/audio/PDF preview, delete with protected path warnings
- **Flow**: `docs/memory/feature-flows/file-manager.md`

### 13.3 Content Folder Convention
- **Status**: ✅ Implemented (2025-12-27)
- **Description**: `content/` directory gitignored by default for large generated assets

### 13.4 Agent Dashboard
- **Status**: ✅ Implemented (2026-01-12)
- **Description**: Agent-defined dashboard via `dashboard.yaml` with widget system
- **Key Features**: 11 widget types (metric, status, progress, table, etc.), auto-refresh
- **Flow**: `docs/memory/feature-flows/agent-dashboard.md`

### 13.5 Tasks Tab
- **Status**: ✅ Implemented
- **Description**: Unified task execution UI in Agent Detail page
- **Key Features**: Trigger manual tasks, monitor queue, view history, stop running tasks, make repeatable
- **Flow**: `docs/memory/feature-flows/tasks-tab.md`

### 13.6 Execution Log Viewer
- **Status**: ✅ Implemented
- **Description**: Modal for viewing Claude Code execution transcripts
- **Flow**: `docs/memory/feature-flows/execution-log-viewer.md`

### 13.7 Execution Detail Page
- **Status**: ✅ Implemented (2026-01-10)
- **Description**: Dedicated page for execution details with metadata, timestamps, transcript
- **Flow**: `docs/memory/feature-flows/execution-detail-page.md`

### 13.8 Live Execution Streaming
- **Status**: ✅ Implemented (2026-01-13)
- **Description**: Real-time streaming of Claude Code execution logs to the Execution Detail page
- **Key Features**:
  - SSE streaming from agent server through backend proxy
  - Live log display with auto-scroll
  - "Live" indicator for running executions
  - Stop button integration
  - Late joiner support (buffered entries)
- **Spec**: `docs/requirements/LIVE_EXECUTION_STREAMING.md`

---

## 14. Multi-Runtime Support

### 14.1 Runtime Adapter Architecture
- **Status**: ✅ Implemented (2025-12-28)
- **Description**: Abstract interface for agent execution engines
- **Key Features**: ClaudeCodeRuntime, GeminiRuntime, factory function

### 14.2 Gemini CLI Integration
- **Status**: ✅ Implemented (2025-12-28)
- **Description**: Google's Gemini CLI as alternative runtime
- **Key Features**: Free tier, 1M token context, native Google Search

### 14.3 Runtime Configuration
- **Status**: ✅ Implemented (2025-12-28)
- **Description**: Runtime selection via `template.yaml` `runtime:` field
- **Schema**: `runtime: {type: claude-code|gemini-cli, model: string}`

---

## 15. Public Access

### 15.1 Public Agent Links
- **Status**: ✅ Implemented (2025-12-22)
- **Description**: Shareable public links for unauthenticated agent access
- **Key Features**: Optional email verification, rate limiting, usage tracking
- **Flow**: `docs/memory/feature-flows/public-agent-links.md`

### 15.2 First-Time Setup
- **Status**: ✅ Implemented (2025-12-23)
- **Description**: Admin password wizard on fresh install
- **Key Features**: Bcrypt hashing, API key configuration in Settings
- **Flow**: `docs/memory/feature-flows/first-time-setup.md`

### 15.3 Per-Agent API Key Control
- **Status**: ✅ Implemented (2025-12-26)
- **Description**: Agents can use platform API key or user's own Claude subscription
- **Key Features**: Toggle in Terminal tab, container recreation on change

---

## 16. Advanced Features

### 16.1 Agent Resource Allocation
- **Status**: ✅ Implemented (2026-01-02)
- **Description**: Per-agent memory and CPU configuration
- **Flow**: `docs/memory/feature-flows/agent-resource-allocation.md`

### 16.2 SSH Access
- **Status**: ✅ Implemented (2026-01-02)
- **Description**: Ephemeral SSH credentials via MCP tool
- **Key Features**: ED25519 keys, configurable TTL, ops setting controlled
- **Flow**: `docs/memory/feature-flows/ssh-access.md`

### 16.3 Agent Info Display
- **Status**: ✅ Implemented
- **Description**: Template metadata display in Info tab
- **Flow**: `docs/memory/feature-flows/agent-info-display.md`

### 16.4 Parallel Headless Execution
- **Status**: ✅ Implemented (2025-12-22)
- **Description**: Stateless parallel task execution via `POST /task` endpoint
- **Key Features**: Bypasses queue, enables orchestrator-worker patterns
- **Flow**: `docs/memory/feature-flows/parallel-headless-execution.md`

### 16.5 System Manifest Deployment
- **Status**: ✅ Implemented (2025-12-18)
- **Description**: Recipe-based multi-agent deployment via YAML manifest
- **Key Features**: Permission presets, shared folders, schedules, auto-start
- **Flow**: `docs/memory/feature-flows/system-manifest.md`

### 16.6 Local Agent Deployment via MCP
- **Status**: ✅ Implemented
- **Description**: Deploy local agents via MCP tool
- **Flow**: `docs/memory/feature-flows/local-agent-deploy.md`

### 16.7 Agents Page UI
- **Status**: ✅ Implemented (2026-01-09)
- **Description**: Grid layout with Dashboard parity for Agents list page
- **Key Features**: 3-column grid, autonomy toggle, execution stats, context bar
- **Flow**: `docs/memory/feature-flows/agents-page-ui-improvements.md`

### 16.8 Dark Mode / Theme Switching
- **Status**: ✅ Implemented (2025-12-14)
- **Description**: Client-side theme system with Light/Dark/System modes
- **Key Features**: localStorage persistence, Tailwind class strategy
- **Flow**: `docs/memory/feature-flows/dark-mode-theme.md`

---

## 17. Planned Features

### 17.1 Horizontal Agent Scalability
- **Status**: ⏳ Not Started
- **Priority**: High
- **Description**: Agent pools with N instances for parallel workloads
- **Key Concepts**: Pool configuration, load balancing, auto-scaling triggers

### 17.2 Event Bus Infrastructure
- **Status**: ⏳ Not Started
- **Priority**: High
- **Description**: Platform-wide pub/sub for agent event broadcasting
- **Key Concepts**: Redis Streams, permission-gated subscriptions, event persistence

### 17.3 Event Handlers & Reactions
- **Status**: ⏳ Not Started
- **Priority**: High
- **Description**: Configure automatic agent reactions to events
- **Key Concepts**: Event matching with filters, debouncing/throttling

### 17.4 Automated Git Sync
- **Status**: ⏳ Not Started
- **Priority**: Medium
- **Description**: Sync modes - Manual / Scheduled / On Stop

### 17.5 Automated Secret Rotation
- **Status**: ⏳ Not Started
- **Priority**: Medium
- **Description**: Automatic credential rotation with notifications

### 17.6 Kubernetes Deployment
- **Status**: ⏳ Not Started
- **Priority**: Low
- **Description**: Helm charts, StatefulSet for agents

---

## 18. Future Vision

### 18.1 Business Process Definitions
- **Status**: ⏳ Concept Phase
- **Description**: Processes as first-class entities orchestrating agent collaboration
- **Design Doc**: `docs/drafts/PROCESS_DRIVEN_AGENTS.md`

### 18.2 Human-in-the-Loop Improvement
- **Status**: ⏳ Concept Phase
- **Description**: Feedback collection and continuous improvement of agent behavior

### 18.3 Compliance-Ready Methodology
- **Status**: ⏳ Concept Phase
- **Description**: SOC-2 and ISO 27001-compatible development practices
- **Location**: `dev-methodology-template/`

---

## Non-Functional Requirements

### Performance
- Agent creation: < 30 seconds
- Chat response: < 5 seconds for simple queries
- UI responsiveness: < 100ms for interactions
- WebSocket latency: < 500ms for status updates

### Security
- All credentials encrypted at rest (Redis)
- HTTPS in production (Let's Encrypt)
- Container isolation (network, filesystem)
- Audit logging for compliance

### Scalability
- Support 50+ concurrent agents
- Multiple backend workers (uvicorn)
- Stateless backend (Docker as truth)

### Reliability
- Agent state survives backend restart
- SQLite persists across container recreation
- Redis AOF for secret durability

### Testing
- Feature flows include Testing sections
- Manual testing before marking complete
- Automated tests for critical paths only

---

## Out of Scope

- Multi-tenant deployment (single org only)
- Mobile application
- Billing/payment integration
- Agent marketplace
