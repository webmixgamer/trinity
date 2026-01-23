# Process Engine Feature Flows

> **Status**: Implemented (Sprints 12-16)
> **Location**: `src/backend/services/process_engine/`
> **Frontend**: `src/frontend/src/views/Process*.vue`

---

## Overview

The Process Engine is a workflow orchestration layer built on top of Trinity's agent infrastructure. It enables declarative process definitions (YAML) that orchestrate agents, handle approvals, manage branching logic, and track execution state.

**Key Differentiator**: Unlike traditional workflow engines (Temporal, Airflow), the Process Engine treats agents as stateful entities that learn and adapt, implementing the EMI (Executor/Monitor/Informed) role pattern.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (Vue.js)                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐  │
│  │ ProcessList.vue│  │ProcessEditor.vue│  │ProcessDashboard│  │ProcessExecution│ │
│  │ List processes │  │ YAML + Preview │  │ Analytics      │  │Detail.vue     │  │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘  └───────┬───────┘  │
└──────────┼───────────────────┼───────────────────┼───────────────────┼──────────┘
           │                   │                   │                   │
           ▼                   ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Backend (FastAPI)                                   │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │  routers/processes.py          routers/executions.py                       │ │
│  │  - CRUD for definitions        - Start, cancel, retry executions           │ │
│  │  - Validate, publish, archive  - Get status, list by process               │ │
│  │  - Analytics endpoints         - Approval management                       │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                             │
│                                    ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                        services/process_engine/                            │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐│ │
│  │  │   domain/   │  │   engine/   │  │ repositories│  │     services/       ││ │
│  │  │ - aggregates│  │ - execution │  │ - sqlite_*  │  │ - validator         ││ │
│  │  │ - entities  │  │   _engine   │  │ - interfaces│  │ - analytics         ││ │
│  │  │ - events    │  │ - handlers/ │  └─────────────┘  │ - alerts            ││ │
│  │  │ - enums     │  │ - dependency│                   │ - informed_notifier ││ │
│  │  │ - value_obj │  │   _resolver │                   │ - output_storage    ││ │
│  │  └─────────────┘  └─────────────┘                   └─────────────────────┘│ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                             │
│  ┌─────────────────────────────────┼─────────────────────────────────────────┐  │
│  │                         events/ │                                          │  │
│  │  ┌─────────────┐  ┌─────────────┴───┐  ┌─────────────────┐                │  │
│  │  │    bus.py   │  │websocket_pub.py │  │ webhook_pub.py  │                │  │
│  │  │ InMemory    │  │ Real-time UI    │  │ External notify │                │  │
│  │  └─────────────┘  └─────────────────┘  └─────────────────┘                │  │
│  └────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Agent Containers                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Agent A    │  │  Agent B    │  │  Agent C    │  │  Agent N    │            │
│  │ (Executor)  │  │ (Executor)  │  │ (Informed)  │  │ (Monitor)   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Concepts

### Domain-Driven Design (DDD)

The Process Engine follows DDD principles:

| Concept | Implementation | Purpose |
|---------|----------------|---------|
| **Aggregates** | `ProcessDefinition`, `ProcessExecution` | Consistency boundaries, root entities |
| **Entities** | `StepDefinition`, `StepExecution`, `ApprovalRequest` | Objects with identity within aggregates |
| **Value Objects** | `ProcessId`, `ExecutionId`, `StepId`, `Money`, `Duration` | Immutable, identity-less objects |
| **Domain Events** | `ProcessStarted`, `StepCompleted`, `ProcessFailed` | Record state changes |
| **Repositories** | `SqliteProcessDefinitionRepository`, `SqliteProcessExecutionRepository` | Persistence abstraction |

### Step Types

| Type | Handler | Description |
|------|---------|-------------|
| `agent_task` | `AgentTaskHandler` | Execute task via Trinity agent |
| `human_approval` | `HumanApprovalHandler` | Gate requiring human decision |
| `gateway` | `GatewayHandler` | Conditional branching (exclusive/parallel) |
| `timer` | `TimerHandler` | Wait for duration or until timestamp |
| `notification` | `NotificationHandler` | Send Slack/webhook notifications |
| `sub_process` | `SubProcessHandler` | Call another process as a step |

### Template Variables

All step handlers support template variable substitution in their configuration fields. Variables are evaluated at runtime using `ExpressionEvaluator`.

**Supported Patterns:**
- `{{input.X}}` - Process input data field
- `{{steps.X.output}}` - Full step output
- `{{steps.X.output.Y}}` - Nested field in step output
- `{{execution.id}}` - Execution ID
- `{{process.name}}` - Process name

See [process-execution.md](./process-execution.md) for handler template field support.

### EMI Role Pattern

Each step can have role assignments:

| Role | Purpose | Behavior |
|------|---------|----------|
| **Executor** | Performs the work | Required, exactly one agent |
| **Monitor** | Owns outcome | Can intervene, receives alerts |
| **Informed** | Learns from events | Receives notifications to agent memory |

---

## Feature Flow Index

| Document | Priority | Description |
|----------|----------|-------------|
| [process-definition.md](./process-definition.md) | High | YAML schema, validation, versioning |
| [process-execution.md](./process-execution.md) | High | Engine, step handlers, state machine |
| [process-monitoring.md](./process-monitoring.md) | High | UI views, WebSocket events, dashboards |
| [human-approval.md](./human-approval.md) | Medium | Approval gates, inbox, timeout handling |
| [process-scheduling.md](./process-scheduling.md) | Medium | Cron triggers, timer steps |
| [process-analytics.md](./process-analytics.md) | Medium | Cost tracking, alerts, metrics |
| [sub-processes.md](./sub-processes.md) | Medium | Parent-child linking, breadcrumbs |
| [agent-roles-emi.md](./agent-roles-emi.md) | Medium | EMI pattern, InformedNotifier |
| [process-templates.md](./process-templates.md) | Low | Bundled templates, management |

---

## Key Files Reference

### Backend

| File | Purpose |
|------|---------|
| `routers/processes.py` | Process definition CRUD, validation, publish/archive |
| `routers/executions.py` | Execution start, cancel, retry, status |
| `domain/aggregates.py` | `ProcessDefinition`, `ProcessExecution` aggregates |
| `domain/entities.py` | `StepDefinition`, `StepExecution`, `StepRoles`, `ApprovalRequest` |
| `domain/events.py` | Domain events (ProcessStarted, StepCompleted, etc.) |
| `domain/value_objects.py` | `ProcessId`, `ExecutionId`, `Money`, `Duration`, `RetryPolicy` |
| `domain/enums.py` | `StepType`, `StepStatus`, `ExecutionStatus`, `AgentRole` |
| `engine/execution_engine.py` | Core orchestrator, retry logic, event publishing |
| `engine/dependency_resolver.py` | Topological sort, parallel step detection |
| `engine/handlers/*.py` | Step-type-specific execution logic |
| `services/validator.py` | YAML validation, schema checking |
| `services/analytics.py` | Metrics calculation, trend data |
| `services/alerts.py` | Cost threshold monitoring |
| `services/informed_notifier.py` | EMI pattern notification delivery |
| `repositories/sqlite_*.py` | SQLite persistence for definitions, executions, events |

### Frontend

| File | Purpose |
|------|---------|
| `views/ProcessList.vue` | Grid view of all processes with status filter |
| `views/ProcessEditor.vue` | YAML editor with live preview and flow visualization |
| `views/ProcessDashboard.vue` | Analytics, metrics, trend charts |
| `views/ProcessExecutionDetail.vue` | Execution timeline, step status, breadcrumbs |
| `views/Approvals.vue` | Approval inbox for human approval steps |
| `views/Alerts.vue` | Cost alert management |
| `components/process/RoleMatrix.vue` | EMI role assignment UI |
| `components/process/TemplateSelector.vue` | Process template picker |
| `components/process/TrendChart.vue` | Analytics visualization |

### Configuration

| File | Purpose |
|------|---------|
| `schemas/process-definition.schema.json` | JSON Schema for YAML validation |
| `config/process-templates/*/` | Bundled process templates |

---

## Database Schema

### Process Definitions Database (`trinity_processes.db`)

```sql
-- Process definition storage
CREATE TABLE process_definitions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    version TEXT NOT NULL,
    status TEXT NOT NULL,           -- draft, published, archived
    yaml_content TEXT NOT NULL,
    steps_json TEXT,                -- Serialized steps
    outputs_json TEXT,              -- Serialized outputs
    triggers_json TEXT,             -- Serialized triggers
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    published_at TEXT
);
```

### Process Executions Database (`trinity_executions.db`)

```sql
-- Execution state tracking
CREATE TABLE process_executions (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL,
    process_name TEXT NOT NULL,
    process_version TEXT NOT NULL,
    status TEXT NOT NULL,           -- pending, running, completed, failed, cancelled, paused
    input_data TEXT,                -- JSON
    output_data TEXT,               -- JSON
    step_executions TEXT,           -- JSON map of step_id -> StepExecution
    triggered_by TEXT,
    started_at TEXT,
    completed_at TEXT,
    total_cost TEXT,
    retry_of TEXT,                  -- Original execution if retry
    parent_execution_id TEXT,       -- For sub-processes
    parent_step_id TEXT,
    child_execution_ids TEXT        -- JSON array
);

-- Approval requests
CREATE TABLE approval_requests (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    assignees TEXT,                 -- JSON array
    status TEXT NOT NULL,           -- pending, approved, rejected, expired
    deadline TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT,
    decided_by TEXT,
    decision_comment TEXT
);
```

---

## Related Flows (Outside This Folder)

| Flow | Relation |
|------|----------|
| [scheduling.md](../scheduling.md) | Process triggers use scheduler infrastructure |
| [agent-terminal.md](../agent-terminal.md) | Agent task steps communicate via same AgentClient |
| [execution-queue.md](../execution-queue.md) | Agent tasks respect queue system |
| [mcp-orchestration.md](../mcp-orchestration.md) | EMI notifications use MCP for agent communication |

---

## Implementation References

| Document | Purpose |
|----------|---------|
| `docs/PROCESS_DRIVEN_PLATFORM/PROCESS_DRIVEN_THINKING_IT1.md` | Initial analysis |
| `docs/PROCESS_DRIVEN_PLATFORM/PROCESS_DRIVEN_THINKING_IT2.md` | Step types design |
| `docs/PROCESS_DRIVEN_PLATFORM/PROCESS_DRIVEN_THINKING_IT3.md` | DDD architecture |
| `docs/PROCESS_DRIVEN_PLATFORM/PROCESS_DRIVEN_THINKING_IT4.md` | UI/UX design |
| `docs/PROCESS_DRIVEN_PLATFORM/BACKLOG_*.md` | Epic/story breakdown |

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-23 | Added Template Variables section documenting expression evaluator support |
| 2026-01-16 | Initial creation with architecture overview |
