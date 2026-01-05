# Trinity Authentication Architecture

## Authentication Layers Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      TRINITY AUTHENTICATION LAYERS                              │
│                                                                                 │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                        LAYER 1: USER AUTHENTICATION                      │  │
│   │                        (Human → Platform)                                │  │
│   │                                                                          │  │
│   │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │  │
│   │   │  Dev Mode   │    │ Email Auth  │    │   Auth0     │                 │  │
│   │   │  (local)    │    │ (default)   │    │  (OAuth)    │                 │  │
│   │   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                 │  │
│   │          │                  │                  │                         │  │
│   │          └──────────────────┼──────────────────┘                         │  │
│   │                             │                                            │  │
│   │                             ▼                                            │  │
│   │                     ┌──────────────┐                                     │  │
│   │                     │  JWT Token   │                                     │  │
│   │                     │  mode claim  │                                     │  │
│   │                     └──────────────┘                                     │  │
│   │                                                                          │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                        LAYER 2: MCP API KEYS                             │  │
│   │                        (Claude Code Client → MCP Server)                 │  │
│   │                                                                          │  │
│   │   ┌─────────────────┐                    ┌─────────────────┐            │  │
│   │   │  User API Key   │                    │  Agent API Key  │            │  │
│   │   │  scope: "user"  │                    │  scope: "agent" │            │  │
│   │   │                 │                    │  agent_name set │            │  │
│   │   └────────┬────────┘                    └────────┬────────┘            │  │
│   │            │                                      │                      │  │
│   │            └──────────────┬───────────────────────┘                      │  │
│   │                           │                                              │  │
│   │                           ▼                                              │  │
│   │                  ┌──────────────────┐                                    │  │
│   │                  │ Authorization:   │                                    │  │
│   │                  │ Bearer trinity_  │                                    │  │
│   │                  │ mcp_xxxxx        │                                    │  │
│   │                  └──────────────────┘                                    │  │
│   │                                                                          │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                        LAYER 3: AGENT PERMISSIONS                        │  │
│   │                        (Agent → Agent)                                   │  │
│   │                                                                          │  │
│   │   ┌────────────────────────────────────────────────────────────────┐    │  │
│   │   │                    agent_permissions table                      │    │  │
│   │   │                                                                 │    │  │
│   │   │   source_agent    │  target_agent    │  granted_by             │    │  │
│   │   │   ───────────────────────────────────────────────────          │    │  │
│   │   │   orchestrator    │  worker-1        │  user-123               │    │  │
│   │   │   orchestrator    │  worker-2        │  user-123               │    │  │
│   │   │   worker-1        │  orchestrator    │  user-123               │    │  │
│   │   │                                                                 │    │  │
│   │   └────────────────────────────────────────────────────────────────┘    │  │
│   │                                                                          │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                        LAYER 4: SYSTEM AGENT                             │  │
│   │                        (Privileged Access)                               │  │
│   │                                                                          │  │
│   │   ┌────────────────────────────────────────────────────────────────┐    │  │
│   │   │                                                                 │    │  │
│   │   │   trinity-system agent                                          │    │  │
│   │   │   scope: "system"                                               │    │  │
│   │   │                                                                 │    │  │
│   │   │   • Bypasses ALL permission checks                              │    │  │
│   │   │   • Can communicate with any agent                              │    │  │
│   │   │   • Cannot be deleted                                           │    │  │
│   │   │   • Auto-deployed on startup                                    │    │  │
│   │   │                                                                 │    │  │
│   │   └────────────────────────────────────────────────────────────────┘    │  │
│   │                                                                          │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Email Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      EMAIL AUTHENTICATION FLOW                                  │
│                                                                                 │
│                                                                                 │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐         ┌──────────┐ │
│   │  Browser │         │ Frontend │         │ Backend  │         │  Email   │ │
│   │          │         │  Vue.js  │         │ FastAPI  │         │ Provider │ │
│   └────┬─────┘         └────┬─────┘         └────┬─────┘         └────┬─────┘ │
│        │                    │                    │                    │        │
│        │  Enter email       │                    │                    │        │
│        │───────────────────►│                    │                    │        │
│        │                    │                    │                    │        │
│        │                    │  POST /api/auth/   │                    │        │
│        │                    │  email/request     │                    │        │
│        │                    │  {email}           │                    │        │
│        │                    │───────────────────►│                    │        │
│        │                    │                    │                    │        │
│        │                    │                    │  Check whitelist   │        │
│        │                    │                    │  (email_whitelist) │        │
│        │                    │                    │                    │        │
│        │                    │                    │  Rate limit check  │        │
│        │                    │                    │  (3 per 10 min)    │        │
│        │                    │                    │                    │        │
│        │                    │                    │  Generate 6-digit  │        │
│        │                    │                    │  code              │        │
│        │                    │                    │                    │        │
│        │                    │                    │  Store in          │        │
│        │                    │                    │  email_login_codes │        │
│        │                    │                    │                    │        │
│        │                    │                    │  Send email        │        │
│        │                    │                    │───────────────────►│        │
│        │                    │                    │                    │        │
│        │                    │◄───────────────────│                    │        │
│        │                    │  {success, expires}│                    │        │
│        │                    │                    │                    │        │
│        │◄───────────────────│                    │                    │        │
│        │  Show code input   │                    │                    │        │
│        │  + countdown timer │                    │                    │        │
│        │                    │                    │                    │        │
│        │                    │                    │                    │        │
│        │  Enter 6-digit code│                    │                    │        │
│        │───────────────────►│                    │                    │        │
│        │                    │                    │                    │        │
│        │                    │  POST /api/auth/   │                    │        │
│        │                    │  email/verify      │                    │        │
│        │                    │  {email, code}     │                    │        │
│        │                    │───────────────────►│                    │        │
│        │                    │                    │                    │        │
│        │                    │                    │  Validate code     │        │
│        │                    │                    │  (not expired,     │        │
│        │                    │                    │   not used)        │        │
│        │                    │                    │                    │        │
│        │                    │                    │  Create/get user   │        │
│        │                    │                    │                    │        │
│        │                    │                    │  Generate JWT      │        │
│        │                    │                    │                    │        │
│        │                    │◄───────────────────│                    │        │
│        │                    │  {token, user}     │                    │        │
│        │                    │                    │                    │        │
│        │◄───────────────────│                    │                    │        │
│        │  Redirect to       │                    │                    │        │
│        │  dashboard         │                    │                    │        │
│        │                    │                    │                    │        │
│   └────┴─────┘         └────┴─────┘         └────┴─────┘         └────┴─────┘ │
│                                                                                 │
│                                                                                 │
│   Whitelist Auto-Population:                                                    │
│   ──────────────────────────                                                    │
│   When user A shares an agent with user B (email):                              │
│   └── User B automatically added to email_whitelist                             │
│       └── source: "agent_sharing"                                               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## MCP Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      MCP SERVER AUTHENTICATION                                  │
│                                                                                 │
│                                                                                 │
│   ┌──────────────┐              ┌──────────────┐              ┌──────────────┐ │
│   │ Claude Code  │              │  MCP Server  │              │   Backend    │ │
│   │   Client     │              │   FastMCP    │              │   FastAPI    │ │
│   └──────┬───────┘              └──────┬───────┘              └──────┬───────┘ │
│          │                             │                             │          │
│          │                             │                             │          │
│          │  MCP Request                │                             │          │
│          │  Authorization: Bearer      │                             │          │
│          │  trinity_mcp_xxxxx          │                             │          │
│          │────────────────────────────►│                             │          │
│          │                             │                             │          │
│          │                             │  POST /api/mcp/validate     │          │
│          │                             │  {api_key}                  │          │
│          │                             │────────────────────────────►│          │
│          │                             │                             │          │
│          │                             │                             │  Hash    │
│          │                             │                             │  key     │
│          │                             │                             │          │
│          │                             │                             │  Lookup  │
│          │                             │                             │  in DB   │
│          │                             │                             │          │
│          │                             │◄────────────────────────────│          │
│          │                             │  {                          │          │
│          │                             │    valid: true,             │          │
│          │                             │    user_id: "user-123",     │          │
│          │                             │    email: "user@domain.com",│          │
│          │                             │    agent_name: null,        │          │
│          │                             │    scope: "user"            │          │
│          │                             │  }                          │          │
│          │                             │                             │          │
│          │                             │  Create McpAuthContext      │          │
│          │                             │  Store in session           │          │
│          │                             │                             │          │
│          │                             │  Execute tool with          │          │
│          │                             │  auth context               │          │
│          │                             │                             │          │
│          │◄────────────────────────────│                             │          │
│          │  Tool result                │                             │          │
│          │                             │                             │          │
│   └──────┴───────┘              └──────┴───────┘              └──────┴───────┘ │
│                                                                                 │
│                                                                                 │
│   MCP Auth Context Structure:                                                   │
│   ───────────────────────────                                                   │
│   {                                                                             │
│     userId: "user-123",           # User who owns the key                       │
│     userEmail: "user@domain.com", # User's email                                │
│     keyName: "my-key",            # Name given to the key                       │
│     agentName: "agent-a",         # Only set for agent-scoped keys              │
│     scope: "user"|"agent"|"system"# Permission level                            │
│   }                                                                             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```
