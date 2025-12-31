# Trinity Agent Container Architecture

## Agent Container Anatomy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         AGENT CONTAINER                                         │
│                      (trinity-agent-base image)                                 │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                          RUNTIMES                                          │ │
│  │                                                                            │ │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                    │ │
│  │   │  Python 3.11 │  │  Node.js 20  │  │   Go 1.21    │                    │ │
│  │   └──────────────┘  └──────────────┘  └──────────────┘                    │ │
│  │                                                                            │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                       AGENT SERVER (FastAPI :8000)                         │ │
│  │                                                                            │ │
│  │   /api/chat          Execute Claude Code commands                         │ │
│  │   /api/chat/session  Get context window stats                             │ │
│  │   /api/task          Stateless parallel execution                         │ │
│  │   /api/files         List workspace files                                 │ │
│  │   /api/files/download Download file content                               │ │
│  │   /api/files/preview  Preview with MIME type                              │ │
│  │   /api/credentials   Hot-reload credentials                               │ │
│  │   /api/trinity       Trinity meta-prompt injection                        │ │
│  │   /api/health        Health check                                         │ │
│  │                                                                            │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                         CLAUDE CODE                                        │ │
│  │                                                                            │ │
│  │   ┌─────────────────────────────────────────────────────────────────────┐ │ │
│  │   │  • AI-powered coding assistant                                       │ │ │
│  │   │  • File operations (read, write, edit)                              │ │ │
│  │   │  • Bash command execution                                           │ │ │
│  │   │  • Web search and fetch                                             │ │ │
│  │   │  • MCP tool integration                                             │ │ │
│  │   │  • Headless mode for automation                                     │ │ │
│  │   └─────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                            │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                      FILE SYSTEM (/home/developer/)                        │ │
│  │                                                                            │ │
│  │   workspace/                 Agent's working directory (from template)    │ │
│  │   ├── CLAUDE.md              Agent instructions + Trinity injection       │ │
│  │   ├── template.yaml          Agent metadata and configuration             │ │
│  │   ├── .claude/commands/      Slash commands                               │ │
│  │   └── [project files]        Template-specific files                      │ │
│  │                                                                            │ │
│  │   content/                   Generated assets (gitignored)                │ │
│  │   ├── videos/                                                             │ │
│  │   ├── audio/                                                              │ │
│  │   ├── images/                                                             │ │
│  │   └── exports/                                                            │ │
│  │                                                                            │ │
│  │   shared-out/                Exposed shared folder (if enabled)           │ │
│  │   shared-in/                 Mounted folders from other agents            │ │
│  │   └── {agent-name}/          Per-agent mount points                       │ │
│  │                                                                            │ │
│  │   .env                       Credentials (KEY=VALUE format)               │ │
│  │   .mcp.json                  Generated MCP configuration                  │ │
│  │   .mcp.json.template         Template with ${VAR} placeholders            │ │
│  │   .trinity/                  Trinity platform files                       │ │
│  │                                                                            │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                         MCP SERVERS                                        │ │
│  │                                                                            │ │
│  │   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐         │ │
│  │   │  Trinity   │  │  Google    │  │   Slack    │  │   GitHub   │         │ │
│  │   │    MCP     │  │ Workspace  │  │    MCP     │  │    MCP     │         │ │
│  │   │ (injected) │  │    MCP     │  │            │  │            │         │ │
│  │   └────────────┘  └────────────┘  └────────────┘  └────────────┘         │ │
│  │                                                                            │ │
│  │   Configured via .mcp.json with credentials from .env                     │ │
│  │                                                                            │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                      SECURITY CONSTRAINTS                                  │ │
│  │                                                                            │ │
│  │   • User: developer (UID 1000) - non-root                                 │ │
│  │   • CAP_DROP: ALL                                                         │ │
│  │   • CAP_ADD: NET_BIND_SERVICE only                                        │ │
│  │   • no-new-privileges: true                                               │ │
│  │   • tmpfs /tmp with noexec, nosuid                                        │ │
│  │   • Isolated network (no external UI ports)                               │ │
│  │                                                                            │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Agent Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          AGENT LIFECYCLE                                        │
│                                                                                 │
│                                                                                 │
│   CREATE                                                                        │
│   ──────                                                                        │
│                                                                                 │
│   ┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│   │ Template │───►│ Clone/Copy   │───►│ Create       │───►│ Start        │    │
│   │ Selected │    │ Workspace    │    │ Container    │    │ Container    │    │
│   └──────────┘    └──────────────┘    └──────────────┘    └──────────────┘    │
│                                               │                    │           │
│                                               │                    ▼           │
│                                               │           ┌──────────────┐     │
│                                               │           │ Inject       │     │
│                                               │           │ Trinity      │     │
│                                               │           │ Meta-Prompt  │     │
│                                               │           └──────────────┘     │
│                                               │                    │           │
│                                               ▼                    ▼           │
│                                        ┌─────────────────────────────────┐     │
│                                        │         AGENT RUNNING           │     │
│                                        │                                 │     │
│                                        │  • Claude Code ready            │     │
│                                        │  • MCP servers connected        │     │
│                                        │  • API endpoints active         │     │
│                                        │  • Credentials loaded           │     │
│                                        └─────────────────────────────────┘     │
│                                                        │                       │
│                         ┌──────────────────────────────┼───────────────┐       │
│                         │                              │               │       │
│                         ▼                              ▼               ▼       │
│                  ┌──────────────┐            ┌──────────────┐  ┌────────────┐ │
│                  │    STOP      │            │   RESTART    │  │   DELETE   │ │
│                  │              │            │              │  │            │ │
│                  │ Container    │            │ Stop + Start │  │ Stop +     │ │
│                  │ preserved    │            │ Workspace    │  │ Remove     │ │
│                  │ Data intact  │            │ preserved    │  │ container  │ │
│                  │              │            │              │  │ + volumes  │ │
│                  └──────────────┘            └──────────────┘  └────────────┘ │
│                         │                                                      │
│                         │                                                      │
│                         ▼                                                      │
│                  ┌──────────────┐                                              │
│                  │    START     │                                              │
│                  │              │                                              │
│                  │ Resume from  │                                              │
│                  │ saved state  │                                              │
│                  └──────────────┘                                              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Template Structure

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         AGENT TEMPLATE STRUCTURE                                │
│                                                                                 │
│   config/agent-templates/{template-name}/                                       │
│   ├── template.yaml              Required: Agent metadata                       │
│   ├── CLAUDE.md                  Required: Agent instructions                   │
│   ├── .mcp.json.template         Optional: MCP config with ${VAR} placeholders │
│   ├── .claude/                   Optional: Claude Code configuration           │
│   │   └── commands/              Optional: Slash commands                       │
│   │       └── {command}.md                                                      │
│   └── [other files]              Project-specific files                         │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                        template.yaml                                     │  │
│   │                                                                          │  │
│   │   name: research-agent                                                   │  │
│   │   display_name: Research Agent                                           │  │
│   │   description: Autonomous research and analysis                          │  │
│   │   version: "1.0.0"                                                       │  │
│   │   author: Trinity Team                                                   │  │
│   │                                                                          │  │
│   │   capabilities:                                                          │  │
│   │     - web-research                                                       │  │
│   │     - document-analysis                                                  │  │
│   │     - report-generation                                                  │  │
│   │                                                                          │  │
│   │   resources:                                                             │  │
│   │     cpu: "2"                                                             │  │
│   │     memory: "4g"                                                         │  │
│   │                                                                          │  │
│   │   credentials:                                                           │  │
│   │     - name: OPENAI_API_KEY                                               │  │
│   │       description: OpenAI API key for embeddings                         │  │
│   │       required: false                                                    │  │
│   │                                                                          │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```
