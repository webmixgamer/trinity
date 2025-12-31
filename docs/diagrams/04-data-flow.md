# Trinity Data Flow Diagrams

## User Chat Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         USER CHAT WITH AGENT                                    │
│                                                                                 │
│                                                                                 │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐         ┌──────────┐ │
│   │  Browser │         │ Frontend │         │ Backend  │         │  Agent   │ │
│   │          │         │  Vue.js  │         │ FastAPI  │         │Container │ │
│   └────┬─────┘         └────┬─────┘         └────┬─────┘         └────┬─────┘ │
│        │                    │                    │                    │        │
│        │  Type message      │                    │                    │        │
│        │───────────────────►│                    │                    │        │
│        │                    │                    │                    │        │
│        │                    │  POST /api/agents  │                    │        │
│        │                    │  /{name}/chat      │                    │        │
│        │                    │───────────────────►│                    │        │
│        │                    │                    │                    │        │
│        │                    │                    │  Acquire queue     │        │
│        │                    │                    │  lock (Redis)      │        │
│        │                    │                    │                    │        │
│        │                    │                    │  POST /api/chat    │        │
│        │                    │                    │───────────────────►│        │
│        │                    │                    │                    │        │
│        │                    │                    │         ┌──────────┴──────┐│
│        │                    │                    │         │  Claude Code    ││
│        │                    │                    │         │  --print        ││
│        │                    │                    │         │  --output-format││
│        │                    │                    │         │  stream-json    ││
│        │                    │                    │         └──────────┬──────┘│
│        │                    │                    │                    │        │
│        │                    │                    │◄───────────────────│        │
│        │                    │                    │  Stream response   │        │
│        │                    │                    │                    │        │
│        │                    │                    │  Save to database  │        │
│        │                    │                    │  (chat_messages)   │        │
│        │                    │                    │                    │        │
│        │                    │                    │  Broadcast activity│        │
│        │                    │                    │  via WebSocket     │        │
│        │                    │                    │                    │        │
│        │                    │                    │  Release queue     │        │
│        │                    │                    │  lock              │        │
│        │                    │                    │                    │        │
│        │                    │◄───────────────────│                    │        │
│        │                    │  Response + stats  │                    │        │
│        │                    │                    │                    │        │
│        │◄───────────────────│                    │                    │        │
│        │  Display response  │                    │                    │        │
│        │                    │                    │                    │        │
│        │                    │                    │                    │        │
│   └────┴─────┘         └────┴─────┘         └────┴─────┘         └────┴─────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Agent-to-Agent Communication

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    AGENT-TO-AGENT COMMUNICATION                                 │
│                                                                                 │
│                                                                                 │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────────┐│
│   │   Agent A    │     │  MCP Server  │     │   Backend    │     │  Agent B   ││
│   │ (Orchestrator)│     │   FastMCP    │     │   FastAPI    │     │  (Worker)  ││
│   └──────┬───────┘     └──────┬───────┘     └──────┬───────┘     └──────┬─────┘│
│          │                    │                    │                    │      │
│          │                    │                    │                    │      │
│          │  mcp__trinity__    │                    │                    │      │
│          │  chat_with_agent   │                    │                    │      │
│          │  (target="agent-b")│                    │                    │      │
│          │───────────────────►│                    │                    │      │
│          │                    │                    │                    │      │
│          │                    │  Extract agent     │                    │      │
│          │                    │  context from key  │                    │      │
│          │                    │                    │                    │      │
│          │                    │  Check permissions │                    │      │
│          │                    │  (agent_permissions│                    │      │
│          │                    │   table)           │                    │      │
│          │                    │───────────────────►│                    │      │
│          │                    │                    │                    │      │
│          │                    │◄───────────────────│                    │      │
│          │                    │  Permission OK     │                    │      │
│          │                    │                    │                    │      │
│          │                    │  POST /api/agents  │                    │      │
│          │                    │  /agent-b/chat     │                    │      │
│          │                    │  X-Source-Agent:   │                    │      │
│          │                    │  agent-a           │                    │      │
│          │                    │───────────────────►│                    │      │
│          │                    │                    │                    │      │
│          │                    │                    │  POST /api/chat    │      │
│          │                    │                    │───────────────────►│      │
│          │                    │                    │                    │      │
│          │                    │                    │◄───────────────────│      │
│          │                    │                    │  Response          │      │
│          │                    │                    │                    │      │
│          │                    │                    │  Broadcast         │      │
│          │                    │                    │  collaboration     │      │
│          │                    │                    │  event (WebSocket) │      │
│          │                    │                    │                    │      │
│          │                    │                    │  Log activity      │      │
│          │                    │                    │  (agent_activities)│      │
│          │                    │                    │                    │      │
│          │                    │◄───────────────────│                    │      │
│          │◄───────────────────│                    │                    │      │
│          │  Response from B   │                    │                    │      │
│          │                    │                    │                    │      │
│   └──────┴───────┘     └──────┴───────┘     └──────┴───────┘     └──────┴─────┘│
│                                                                                 │
│                                                                                 │
│   Permission Rules:                                                             │
│   ─────────────────                                                             │
│   • Same owner: Allowed by default                                              │
│   • Explicit permission: Check agent_permissions table                          │
│   • Shared agent: Allowed if target is shared with source owner                 │
│   • System agent: Bypasses all permission checks                                │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Credential Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         CREDENTIAL MANAGEMENT FLOW                              │
│                                                                                 │
│                                                                                 │
│   ┌──────────────────────────────────────────────────────────────────────────┐ │
│   │                        CREDENTIAL STORAGE                                 │ │
│   │                                                                           │ │
│   │   User Input                   OAuth Flow                                 │ │
│   │   (KEY=VALUE)                  (Google, Slack, GitHub, Notion)            │ │
│   │       │                              │                                    │ │
│   │       │                              │                                    │ │
│   │       ▼                              ▼                                    │ │
│   │   ┌───────────────────────────────────────────────────────────┐          │ │
│   │   │                       REDIS                                │          │ │
│   │   │                                                            │          │ │
│   │   │   credentials:{id} = {                                     │          │ │
│   │   │     name: "ANTHROPIC_API_KEY",                             │          │ │
│   │   │     value: "sk-ant-...",                                   │          │ │
│   │   │     service: "anthropic",                                  │          │ │
│   │   │     owner_id: "user-123"                                   │          │ │
│   │   │   }                                                        │          │ │
│   │   │                                                            │          │ │
│   │   └───────────────────────────────────────────────────────────┘          │ │
│   │                                                                           │ │
│   └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│                                      │                                          │
│                                      │ Agent Creation                           │
│                                      │ or Hot-Reload                            │
│                                      ▼                                          │
│                                                                                 │
│   ┌──────────────────────────────────────────────────────────────────────────┐ │
│   │                        CREDENTIAL INJECTION                               │ │
│   │                                                                           │ │
│   │                                                                           │ │
│   │   ┌─────────────────────┐      ┌─────────────────────────────────────┐   │ │
│   │   │ .mcp.json.template  │      │              .mcp.json              │   │ │
│   │   │                     │      │                                     │   │ │
│   │   │ {                   │      │ {                                   │   │ │
│   │   │   "mcpServers": {   │ ───► │   "mcpServers": {                   │   │ │
│   │   │     "google": {     │      │     "google": {                     │   │ │
│   │   │       "env": {      │      │       "env": {                      │   │ │
│   │   │         "TOKEN":    │      │         "TOKEN":                    │   │ │
│   │   │         "${GOOGLE_  │      │         "ya29.actual-token..."      │   │ │
│   │   │          TOKEN}"    │      │       }                             │   │ │
│   │   │       }             │      │     }                               │   │ │
│   │   │     }               │      │   }                                 │   │ │
│   │   │   }                 │      │ }                                   │   │ │
│   │   │ }                   │      │                                     │   │ │
│   │   └─────────────────────┘      └─────────────────────────────────────┘   │ │
│   │                                                                           │ │
│   │                                                                           │ │
│   │   Credentials also written to .env file:                                  │ │
│   │                                                                           │ │
│   │   ANTHROPIC_API_KEY=sk-ant-...                                            │ │
│   │   GOOGLE_TOKEN=ya29.actual-token...                                       │ │
│   │   TRINITY_MCP_API_KEY=trinity_mcp_...                                     │ │
│   │                                                                           │ │
│   └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Scheduled Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      SCHEDULED EXECUTION FLOW                                   │
│                                                                                 │
│                                                                                 │
│   ┌──────────────────────────────────────────────────────────────────────────┐ │
│   │                       SCHEDULER SERVICE                                   │ │
│   │                        (APScheduler)                                      │ │
│   │                                                                           │ │
│   │   ┌─────────────────────────────────────────────────────────────────┐    │ │
│   │   │  agent_schedules table                                           │    │ │
│   │   │                                                                  │    │ │
│   │   │  id: sched-123                                                   │    │ │
│   │   │  agent_name: research-agent                                      │    │ │
│   │   │  cron_expression: "0 9 * * *"  (9 AM daily)                      │    │ │
│   │   │  message: "Generate daily report"                                │    │ │
│   │   │  enabled: true                                                   │    │ │
│   │   │  timezone: "America/New_York"                                    │    │ │
│   │   └─────────────────────────────────────────────────────────────────┘    │ │
│   │                                                                           │ │
│   └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│                                      │                                          │
│                                      │ Cron trigger                             │
│                                      ▼                                          │
│                                                                                 │
│   ┌──────────────────────────────────────────────────────────────────────────┐ │
│   │                       EXECUTION FLOW                                      │ │
│   │                                                                           │ │
│   │   1. Check if agent is running                                            │ │
│   │      └── If not, start agent first                                        │ │
│   │                                                                           │ │
│   │   2. Create execution record                                              │ │
│   │      └── schedule_executions table                                        │ │
│   │                                                                           │ │
│   │   3. Acquire queue lock                                                   │ │
│   │      └── Redis: agent:{name}:queue                                        │ │
│   │                                                                           │ │
│   │   4. Send message to agent                                                │ │
│   │      └── POST /api/chat                                                   │ │
│   │                                                                           │ │
│   │   5. Capture response                                                     │ │
│   │      └── Parse Claude Code output                                         │ │
│   │                                                                           │ │
│   │   6. Update execution record                                              │ │
│   │      └── status, response, duration, cost                                 │ │
│   │                                                                           │ │
│   │   7. Release queue lock                                                   │ │
│   │                                                                           │ │
│   │   8. Broadcast WebSocket event                                            │ │
│   │      └── schedule_execution_completed                                     │ │
│   │                                                                           │ │
│   └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```
