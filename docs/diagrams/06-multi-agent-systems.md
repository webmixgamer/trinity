# Trinity Multi-Agent System Architecture

## System Manifest Deployment

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      SYSTEM MANIFEST DEPLOYMENT                                 │
│                                                                                 │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                        system.yaml                                       │  │
│   │                                                                          │  │
│   │   name: content-production                                               │  │
│   │   description: Autonomous content pipeline                               │  │
│   │                                                                          │  │
│   │   prompt: |                                                              │  │
│   │     You are part of the Content Production system.                       │  │
│   │     Coordinate with other agents via Trinity MCP.                        │  │
│   │                                                                          │  │
│   │   agents:                                                                │  │
│   │     orchestrator:                                                        │  │
│   │       template: github:YourOrg/orchestrator-template                     │  │
│   │       resources: {cpu: "2", memory: "4g"}                                │  │
│   │       folders: {expose: true, consume: true}                             │  │
│   │                                                                          │  │
│   │     researcher:                                                          │  │
│   │       template: local:research-agent                                     │  │
│   │       folders: {expose: true}                                            │  │
│   │                                                                          │  │
│   │     writer:                                                              │  │
│   │       template: local:writer-agent                                       │  │
│   │       folders: {consume: true}                                           │  │
│   │       schedules:                                                         │  │
│   │         - name: daily-draft                                              │  │
│   │           cron: "0 9 * * *"                                              │  │
│   │           message: "Write daily content draft"                           │  │
│   │                                                                          │  │
│   │   permissions:                                                           │  │
│   │     preset: orchestrator-workers                                         │  │
│   │                                                                          │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│                                      │                                          │
│                                      │ POST /api/systems/deploy                 │
│                                      ▼                                          │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                        DEPLOYMENT RESULT                                 │  │
│   │                                                                          │  │
│   │   Created Agents:                                                        │  │
│   │   ├── content-production-orchestrator                                    │  │
│   │   ├── content-production-researcher                                      │  │
│   │   └── content-production-writer                                          │  │
│   │                                                                          │  │
│   │   Permissions (orchestrator-workers preset):                             │  │
│   │   ├── orchestrator → researcher ✓                                        │  │
│   │   ├── orchestrator → writer ✓                                            │  │
│   │   ├── researcher → orchestrator ✓                                        │  │
│   │   └── writer → orchestrator ✓                                            │  │
│   │                                                                          │  │
│   │   Shared Folders:                                                        │  │
│   │   ├── orchestrator: expose + consume                                     │  │
│   │   ├── researcher: expose only                                            │  │
│   │   └── writer: consume only                                               │  │
│   │                                                                          │  │
│   │   Schedules:                                                             │  │
│   │   └── writer: daily-draft @ 9 AM                                         │  │
│   │                                                                          │  │
│   │   Trinity Prompt: Updated globally                                       │  │
│   │                                                                          │  │
│   │   All agents started: ✓                                                  │  │
│   │                                                                          │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Permission Presets

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PERMISSION PRESETS                                      │
│                                                                                 │
│                                                                                 │
│   ┌─────────────────────────────┐    ┌─────────────────────────────┐           │
│   │      FULL-MESH              │    │    ORCHESTRATOR-WORKERS     │           │
│   │                             │    │                             │           │
│   │   Every agent can           │    │   First agent is            │           │
│   │   call every other          │    │   orchestrator, others      │           │
│   │                             │    │   are workers                │           │
│   │                             │    │                             │           │
│   │      ┌───┐                  │    │         ┌───┐               │           │
│   │      │ A │◄────────┐        │    │         │ O │               │           │
│   │      └─┬─┘         │        │    │         └─┬─┘               │           │
│   │        │           │        │    │       ┌───┴───┐             │           │
│   │        ▼           │        │    │       ▼       ▼             │           │
│   │      ┌───┐       ┌─┴─┐      │    │     ┌───┐   ┌───┐           │           │
│   │      │ B │◄─────►│ C │      │    │     │W1 │   │W2 │           │           │
│   │      └───┘       └───┘      │    │     └─┬─┘   └─┬─┘           │           │
│   │                             │    │       │       │             │           │
│   │   A↔B, A↔C, B↔C             │    │       └───┬───┘             │           │
│   │                             │    │           ▼                 │           │
│   │                             │    │         ┌───┐               │           │
│   │                             │    │         │ O │               │           │
│   │                             │    │         └───┘               │           │
│   │                             │    │                             │           │
│   │                             │    │   O→W1, O→W2                │           │
│   │                             │    │   W1→O, W2→O                │           │
│   │                             │    │   (workers can't call       │           │
│   │                             │    │    each other)              │           │
│   │                             │    │                             │           │
│   └─────────────────────────────┘    └─────────────────────────────┘           │
│                                                                                 │
│   ┌─────────────────────────────┐    ┌─────────────────────────────┐           │
│   │         NONE                │    │        EXPLICIT             │           │
│   │                             │    │                             │           │
│   │   No permissions            │    │   Custom permission         │           │
│   │   granted                   │    │   matrix                    │           │
│   │                             │    │                             │           │
│   │      ┌───┐                  │    │   permissions:              │           │
│   │      │ A │                  │    │     explicit:               │           │
│   │      └───┘                  │    │       orchestrator:         │           │
│   │                             │    │         - researcher        │           │
│   │      ┌───┐                  │    │         - writer            │           │
│   │      │ B │                  │    │       researcher:           │           │
│   │      └───┘                  │    │         - writer            │           │
│   │                             │    │                             │           │
│   │      ┌───┐                  │    │   O→R, O→W, R→W             │           │
│   │      │ C │                  │    │                             │           │
│   │      └───┘                  │    │                             │           │
│   │                             │    │                             │           │
│   │   (isolated agents)         │    │                             │           │
│   │                             │    │                             │           │
│   └─────────────────────────────┘    └─────────────────────────────┘           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Shared Folder Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      SHARED FOLDER ARCHITECTURE                                 │
│                                                                                 │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                        DOCKER VOLUMES                                    │  │
│   │                                                                          │  │
│   │   agent-researcher-shared (Docker Volume)                                │  │
│   │   agent-writer-shared (Docker Volume)                                    │  │
│   │                                                                          │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│                                                                                 │
│   ┌──────────────────────────────┐    ┌──────────────────────────────┐         │
│   │      RESEARCHER AGENT        │    │       WRITER AGENT           │         │
│   │      (expose: true)          │    │       (consume: true)        │         │
│   │                              │    │                              │         │
│   │   /home/developer/           │    │   /home/developer/           │         │
│   │   ├── workspace/             │    │   ├── workspace/             │         │
│   │   │   └── [code]             │    │   │   └── [code]             │         │
│   │   │                          │    │   │                          │         │
│   │   ├── shared-out/ ◄──────────┼────┼───┤                          │         │
│   │   │   └── research-data.json │    │   │                          │         │
│   │   │       (written here)     │    │   │                          │         │
│   │   │                          │    │   │                          │         │
│   │   └── shared-in/             │    │   └── shared-in/             │         │
│   │       (empty - not consuming)│    │       └── researcher/ ◄──────┼─────┐   │
│   │                              │    │           └── research-      │     │   │
│   │                              │    │               data.json      │     │   │
│   │                              │    │               (mounted here) │     │   │
│   │                              │    │                              │     │   │
│   └──────────────────────────────┘    └──────────────────────────────┘     │   │
│                                                                             │   │
│                                                                             │   │
│   ┌─────────────────────────────────────────────────────────────────────────┘   │
│   │                                                                             │
│   │   Volume Mount:                                                             │
│   │   agent-researcher-shared:/home/developer/shared-out (in researcher)        │
│   │   agent-researcher-shared:/home/developer/shared-in/researcher (in writer)  │
│   │                                                                             │
│   │   Permission Required:                                                      │
│   │   Writer must have permission to call Researcher                            │
│   │   (same permission as for chat_with_agent)                                  │
│   │                                                                             │
│   └─────────────────────────────────────────────────────────────────────────────┘
│                                                                                 │
│                                                                                 │
│   Data Flow:                                                                    │
│   ──────────                                                                    │
│                                                                                 │
│   1. Researcher writes to /home/developer/shared-out/research-data.json         │
│   2. Docker volume persists the file                                            │
│   3. Writer reads from /home/developer/shared-in/researcher/research-data.json  │
│   4. No network communication needed - pure file-based collaboration            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Orchestrator-Worker Pattern

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR-WORKER PATTERN                                │
│                                                                                 │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                        ORCHESTRATOR AGENT                                │  │
│   │                                                                          │  │
│   │   Role: Decompose complex tasks, delegate to workers, aggregate results │  │
│   │                                                                          │  │
│   │   Capabilities:                                                          │  │
│   │   • mcp__trinity__list_agents() - See available workers                  │  │
│   │   • mcp__trinity__chat_with_agent(parallel=true) - Parallel execution   │  │
│   │   • Read shared-in folders for worker outputs                            │  │
│   │   • Write instructions to shared-out for workers                         │  │
│   │                                                                          │  │
│   │   ┌─────────────────────────────────────────────────────────────────┐   │  │
│   │   │                    TASK DECOMPOSITION                            │   │  │
│   │   │                                                                  │   │  │
│   │   │   User Request: "Create a market analysis report"               │   │  │
│   │   │                                                                  │   │  │
│   │   │   ┌──────────────┐                                               │   │  │
│   │   │   │  Orchestrator │                                              │   │  │
│   │   │   │   analyzes    │                                              │   │  │
│   │   │   │   request     │                                              │   │  │
│   │   │   └──────┬───────┘                                               │   │  │
│   │   │          │                                                       │   │  │
│   │   │          ▼                                                       │   │  │
│   │   │   ┌──────────────────────────────────────────────────────────┐  │   │  │
│   │   │   │              PARALLEL TASK DISPATCH                       │  │   │  │
│   │   │   │                                                           │  │   │  │
│   │   │   │   chat_with_agent(      chat_with_agent(                  │  │   │  │
│   │   │   │     target="researcher",  target="analyst",               │  │   │  │
│   │   │   │     message="Research     message="Analyze                │  │   │  │
│   │   │   │       competitors",        market trends",                │  │   │  │
│   │   │   │     parallel=true)        parallel=true)                  │  │   │  │
│   │   │   │          │                     │                          │  │   │  │
│   │   │   │          ▼                     ▼                          │  │   │  │
│   │   │   │   ┌────────────┐        ┌────────────┐                    │  │   │  │
│   │   │   │   │ Researcher │        │  Analyst   │                    │  │   │  │
│   │   │   │   │  (worker)  │        │  (worker)  │                    │  │   │  │
│   │   │   │   └─────┬──────┘        └─────┬──────┘                    │  │   │  │
│   │   │   │         │                     │                          │  │   │  │
│   │   │   │         │  Writes to          │  Writes to               │  │   │  │
│   │   │   │         │  shared-out         │  shared-out              │  │   │  │
│   │   │   │         │                     │                          │  │   │  │
│   │   │   │         ▼                     ▼                          │  │   │  │
│   │   │   │   ┌────────────────────────────────────────┐             │  │   │  │
│   │   │   │   │        ORCHESTRATOR AGGREGATES          │             │  │   │  │
│   │   │   │   │                                         │             │  │   │  │
│   │   │   │   │  Reads from shared-in/researcher/       │             │  │   │  │
│   │   │   │   │  Reads from shared-in/analyst/          │             │  │   │  │
│   │   │   │   │  Combines into final report             │             │  │   │  │
│   │   │   │   │                                         │             │  │   │  │
│   │   │   │   └────────────────────────────────────────┘             │  │   │  │
│   │   │   │                                                           │  │   │  │
│   │   │   └───────────────────────────────────────────────────────────┘  │   │  │
│   │   │                                                                  │   │  │
│   │   └─────────────────────────────────────────────────────────────────┘   │  │
│   │                                                                          │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```
