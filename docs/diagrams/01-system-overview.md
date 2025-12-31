# Trinity System Overview

## What is Trinity?

Trinity is a **Deep Agent Orchestration Platform** — infrastructure for deploying, orchestrating, and governing autonomous AI agents that plan, reason, and execute independently.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│                         TRINITY PLATFORM                                        │
│                    "Deep Agent Orchestration"                                   │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                         WEB INTERFACE                                    │  │
│   │                                                                          │  │
│   │   Dashboard    Agent Details    File Manager    System Agent    Settings │  │
│   │      │              │               │               │             │      │  │
│   └──────┼──────────────┼───────────────┼───────────────┼─────────────┼──────┘  │
│          │              │               │               │             │         │
│          └──────────────┴───────────────┴───────────────┴─────────────┘         │
│                                      │                                          │
│                                      ▼                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                         PLATFORM SERVICES                                │  │
│   │                                                                          │  │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│   │  │ Backend  │  │   MCP    │  │  Audit   │  │  Redis   │  │  SQLite  │  │  │
│   │  │ FastAPI  │  │  Server  │  │  Logger  │  │ Secrets  │  │   Data   │  │  │
│   │  │  :8000   │  │  :8080   │  │  :8001   │  │  :6379   │  │          │  │  │
│   │  └────┬─────┘  └────┬─────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│   │       │             │                                                    │  │
│   └───────┼─────────────┼────────────────────────────────────────────────────┘  │
│           │             │                                                       │
│           ▼             ▼                                                       │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                         AGENT RUNTIME                                    │  │
│   │                                                                          │  │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  │
│   │   │   Agent 1   │  │   Agent 2   │  │   Agent 3   │  │   Agent N   │   │  │
│   │   │             │  │             │  │             │  │             │   │  │
│   │   │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │   │  │
│   │   │ │ Claude  │ │  │ │ Claude  │ │  │ │ Claude  │ │  │ │ Claude  │ │   │  │
│   │   │ │  Code   │ │  │ │  Code   │ │  │ │  Code   │ │  │ │  Code   │ │   │  │
│   │   │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │   │  │
│   │   │             │  │             │  │             │  │             │   │  │
│   │   │ MCP Tools   │  │ MCP Tools   │  │ MCP Tools   │  │ MCP Tools   │   │  │
│   │   │ Workspace   │  │ Workspace   │  │ Workspace   │  │ Workspace   │   │  │
│   │   │ Credentials │  │ Credentials │  │ Credentials │  │ Credentials │   │  │
│   │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │  │
│   │                                                                          │  │
│   │                    Agent Network (172.28.0.0/16)                        │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## The Four Pillars of Deep Agency

Trinity implements infrastructure for "System 2" AI — agents that think deliberately rather than react.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│                    THE FOUR PILLARS OF DEEP AGENCY                              │
│                                                                                 │
├─────────────────────┬─────────────────────┬─────────────────────┬───────────────┤
│                     │                     │                     │               │
│   I. HIERARCHICAL   │  II. PERSISTENT     │  III. EXTREME       │  IV. AUTO-    │
│      DELEGATION     │      MEMORY         │      CONTEXT        │     NOMOUS    │
│                     │                     │      ENGINEERING    │     OPS       │
│                     │                     │                     │               │
│  ┌───────────────┐  │  ┌───────────────┐  │  ┌───────────────┐  │  ┌─────────┐  │
│  │  Orchestrator │  │  │   Database    │  │  │   CLAUDE.md   │  │  │Schedule │  │
│  │       │       │  │  │   Chat Logs   │  │  │   Templates   │  │  │  Cron   │  │
│  │   ┌───┴───┐   │  │  │   Sessions    │  │  │   Prompts     │  │  │  Jobs   │  │
│  │   ▼       ▼   │  │  └───────────────┘  │  └───────────────┘  │  └─────────┘  │
│  │ Worker Worker │  │                     │                     │               │
│  └───────────────┘  │  ┌───────────────┐  │  ┌───────────────┐  │  ┌─────────┐  │
│                     │  │  File System  │  │  │  Credentials  │  │  │ Health  │  │
│  Agent-to-Agent     │  │  Workspaces   │  │  │  MCP Configs  │  │  │ Monitor │  │
│  via Trinity MCP    │  │  Shared Dirs  │  │  │  Injection    │  │  │ Restart │  │
│                     │  └───────────────┘  │  └───────────────┘  │  └─────────┘  │
│                     │                     │                     │               │
└─────────────────────┴─────────────────────┴─────────────────────┴───────────────┘
```

## Key Differentiators

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│   Traditional Chatbot (System 1)          Trinity Agent (System 2)              │
│   ─────────────────────────────           ─────────────────────────             │
│                                                                                 │
│   User ──► Bot ──► Response               User ──► Agent ──► Plan              │
│       (reactive)                                              │                 │
│                                                               ▼                 │
│   • Single turn                           ┌─────────────────────────┐           │
│   • No memory                             │  1. Decompose goal      │           │
│   • No planning                           │  2. Execute steps       │           │
│   • Human-dependent                       │  3. Delegate to others  │           │
│                                           │  4. Handle failures     │           │
│                                           │  5. Report results      │           │
│                                           └─────────────────────────┘           │
│                                                                                 │
│                                           • Multi-session memory                │
│                                           • Autonomous execution                │
│                                           • Self-healing recovery               │
│                                           • Agent-to-agent collaboration        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```
