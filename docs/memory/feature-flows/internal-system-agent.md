# Feature Flow: Internal System Agent

> **Phase 11.1 & 11.2** - Platform operations manager with privileged access

## Overview

The Internal System Agent (`trinity-system`) is an auto-deployed, deletion-protected agent that serves as the **platform operations manager**. It focuses exclusively on infrastructure concerns: agent health, lifecycle management, resource governance, and schedule control.

> **Guiding Principle**: "The system agent manages the orchestra, not the music."

## Operational Scope

### In Scope (Operations)

| Area | Responsibilities |
|------|------------------|
| **Health Monitoring** | Detect stuck agents, high context usage, container failures |
| **Lifecycle Management** | Start, stop, restart agents based on health |
| **Resource Governance** | Monitor cost, context thresholds, memory bounds |
| **Schedule Control** | Enable/disable schedules, trigger manual runs, pause automation |
| **Validation** | Pre-flight checks before agent operations |
| **Alerting** | Notify on anomalies, failures, threshold breaches |
| **Cleanup** | Reset stuck sessions, archive old plans |
| **Reporting** | Fleet status, cost summaries, health reports |

### Out of Scope (Not Ops)

| NOT Responsible For | Why |
|---------------------|-----|
| Task orchestration | Agents coordinate themselves via MCP |
| Content/output review | Domain-specific, not infrastructure |
| Workflow design | User/developer responsibility |
| Agent-to-agent messaging | Agents handle directly |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Trinity Platform Startup                        │
├─────────────────────────────────────────────────────────────────────┤
│  1. Backend starts                                                  │
│  2. Database migrations run (is_system column)                      │
│  3. system_agent_service.ensure_deployed() called                   │
│  4. If trinity-system doesn't exist → create from template          │
│  5. If exists but stopped → start it                                │
│  6. If running → no action                                          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    System Agent Container                            │
├─────────────────────────────────────────────────────────────────────┤
│  Name: agent-trinity-system                                         │
│  Template: local:trinity-system                                      │
│  Resources: 4 CPU, 8GB RAM                                          │
│  MCP Key: scope="system" (bypasses all permissions)                 │
│  Labels: trinity.is-system=true                                      │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  CLAUDE.md                                                    │   │
│  │  - Operations-only scope                                      │   │
│  │  - Available MCP tools                                        │   │
│  │  - Health monitoring guidelines                               │   │
│  │  - Alerting and reporting                                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Slash Commands (/ops/*)                                      │   │
│  │  - /ops/status - Fleet status report                         │   │
│  │  - /ops/health - Health check all agents                     │   │
│  │  - /ops/restart <agent> - Restart specific agent             │   │
│  │  - /ops/restart-all - Restart entire fleet                   │   │
│  │  - /ops/stop <agent> - Stop specific agent                   │   │
│  │  - /ops/schedules - Schedule overview                        │   │
│  │  - /ops/costs - Cost report from OTel                        │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `config/agent-templates/trinity-system/template.yaml` | Template configuration |
| `config/agent-templates/trinity-system/CLAUDE.md` | Operations instructions |
| `config/agent-templates/trinity-system/commands/ops/*.md` | Slash commands |
| `src/backend/services/system_agent_service.py` | Auto-deployment logic |
| `src/backend/routers/system_agent.py` | Admin management endpoints |
| `src/backend/routers/ops.py` | Fleet operations endpoints |
| `src/backend/routers/settings.py` | Ops settings (OPS_SETTINGS_DEFAULTS) |
| `src/backend/db/agents.py` | SYSTEM_AGENT_NAME constant, is_system checks |
| `src/frontend/src/views/SystemAgent.vue` | **System Agent UI** - dedicated ops interface |
| `src/frontend/src/components/NavBar.vue` | System link in navbar (admin-only) |
| `src/frontend/src/router/index.js` | `/system-agent` route |

## Frontend UI

### Route
- **Path**: `/system-agent`
- **Access**: Admin-only (requires `role: "admin"`)
- **NavBar**: Purple "System" link with CPU icon (visible to admins)

### Components

The `SystemAgent.vue` view provides a dedicated, ops-focused interface:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    System Agent Header                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  [CPU Icon]  System Agent                    [running] [Restart]│  │
│  │              Platform Operations Manager                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                       │
│  │ Total  │ │Running │ │Stopped │ │ Issues │  <- Fleet Overview    │
│  │   12   │ │   8    │ │   4    │ │   1    │                       │
│  └────────┘ └────────┘ └────────┘ └────────┘                       │
│                                                                      │
│  ┌──────────────────┐  ┌────────────────────────────────────────┐  │
│  │  Quick Actions   │  │     Operations Console                  │  │
│  │                  │  │  ┌──────────────────────────────────┐   │  │
│  │ [Emergency Stop] │  │  │ [/ops/status] [/ops/health] [...] │   │  │
│  │ [Restart All]    │  │  └──────────────────────────────────┘   │  │
│  │ [Pause Scheds]   │  │                                         │  │
│  │ [Resume Scheds]  │  │  Chat messages appear here...           │  │
│  │ [Refresh Status] │  │                                         │  │
│  │                  │  │  [Enter command...              ] [Send]│  │
│  └──────────────────┘  └────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Features

| Feature | Description |
|---------|-------------|
| **Purple Header** | Gradient header with system agent branding |
| **Fleet Overview Cards** | Total, Running, Stopped, Issues counts |
| **Quick Actions** | Emergency Stop, Restart All, Pause/Resume Schedules |
| **Operations Console** | Chat interface for ops commands |
| **Quick Command Buttons** | One-click `/ops/status`, `/ops/health`, `/ops/schedules` |
| **Auto-refresh** | Polls status every 10 seconds |

### Design Decisions

1. **Simplified Layout**: Unlike regular `AgentDetail.vue` with many tabs, this is a single-page ops dashboard
2. **Purple Branding**: Distinguishes from regular agents (which use blue/green)
3. **Quick Actions**: One-click buttons for common operations (no need to type commands)
4. **Fleet Focus**: Shows aggregate stats, not individual agent details
5. **Admin-Only**: Protected route - only admins can access

## API Endpoints

### System Agent Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/system-agent/status` | GET | Get system agent status |
| `/api/system-agent/restart` | POST | Restart system agent (admin) |
| `/api/system-agent/reinitialize` | POST | Reset to clean state (admin) |

### Fleet Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ops/fleet/status` | GET | All agents with status, context, activity |
| `/api/ops/fleet/health` | GET | Health summary with critical/warning issues |
| `/api/ops/fleet/restart` | POST | Restart all/filtered agents |
| `/api/ops/fleet/stop` | POST | Stop all/filtered agents |

### Schedule Control

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ops/schedules/pause` | POST | Pause all schedules |
| `/api/ops/schedules/resume` | POST | Resume all schedules |
| `/api/ops/emergency-stop` | POST | Halt all executions immediately |

### Ops Settings

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/settings/ops/config` | GET | Get all ops settings with defaults |
| `/api/settings/ops/config` | PUT | Update multiple ops settings |
| `/api/settings/ops/reset` | POST | Reset all ops settings to defaults |

## Ops Settings

Stored in `system_settings` table with these defaults:

| Key | Default | Description |
|-----|---------|-------------|
| `ops_context_warning_threshold` | 75 | Context % to trigger warning |
| `ops_context_critical_threshold` | 90 | Context % to trigger critical |
| `ops_idle_timeout_minutes` | 30 | Minutes before stuck detection |
| `ops_cost_limit_daily_usd` | 50.0 | Daily cost limit (0 = unlimited) |
| `ops_max_execution_minutes` | 10 | Max chat execution time |
| `ops_alert_suppression_minutes` | 15 | Suppress duplicate alerts |
| `ops_log_retention_days` | 7 | Days to keep container logs |
| `ops_health_check_interval` | 60 | Seconds between health checks |

## MCP Scope Types

| Scope | Description | Permission Check |
|-------|-------------|------------------|
| `user` | Human user via Claude Code client | Owner/admin/shared |
| `agent` | Regular agent | Explicit permission list |
| `system` | System agent | **Bypasses all checks** |

## Slash Commands

Commands are located in `config/agent-templates/trinity-system/commands/ops/`:

| Command | File | Description |
|---------|------|-------------|
| `/ops/status` | `status.md` | Fleet status with context usage |
| `/ops/health` | `health.md` | Health check with issues and recommendations |
| `/ops/restart <agent>` | `restart.md` | Restart specific agent |
| `/ops/restart-all` | `restart-all.md` | Restart entire fleet |
| `/ops/stop <agent>` | `stop.md` | Stop specific agent |
| `/ops/schedules` | `schedules.md` | Schedule overview with next runs |
| `/ops/costs` | `costs.md` | Cost report from OTel metrics |

## Data Flow

### 1. Auto-Deployment on Startup

```
Backend Startup
       │
       ▼
┌──────────────────┐
│ lifespan()       │
│ handler          │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────┐
│ system_agent_service.            │
│ ensure_deployed()                │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────┐    Yes    ┌──────────────────┐
│ Container        ├──────────►│ Already running? │
│ exists?          │           │ → No action      │
└────────┬─────────┘           └──────────────────┘
         │ No
         ▼
┌──────────────────────────────────┐
│ _create_system_agent()           │
│ 1. Load template                 │
│ 2. Create MCP key (scope=system) │
│ 3. Start container               │
│ 4. Register ownership (is_system)│
└──────────────────────────────────┘
```

### 2. Fleet Health Check Flow

```
User: /ops/health
       │
       ▼
┌──────────────────────────────────┐
│ System Agent receives command    │
│ Reads health.md instructions     │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ mcp__trinity__list_agents        │
│ Get all agents                   │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ For each running agent:          │
│ - Check container status         │
│ - Check context usage            │
│ - Check last activity            │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Classify health:                 │
│ - Critical: >90% context, down   │
│ - Warning: >75% context, idle    │
│ - Healthy: Normal operation      │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Generate health report           │
│ with recommendations             │
└──────────────────────────────────┘
```

### 3. Emergency Stop Flow

```
POST /api/ops/emergency-stop
       │
       ▼
┌──────────────────────────────────┐
│ 1. Pause all enabled schedules   │
│    - Set enabled=false in DB     │
│    - Remove from APScheduler     │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ 2. Stop all non-system agents    │
│    - Skip trinity-system         │
│    - container.stop(timeout=10)  │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ 3. Audit log with results        │
│    - schedules_paused: N         │
│    - agents_stopped: N           │
│    - errors: [...]               │
└──────────────────────────────────┘
```

## Testing

### 1. Auto-Deployment
```bash
# Restart backend
docker-compose restart backend

# Check logs for system agent deployment
docker-compose logs backend | grep "System agent"
# Expected: "System agent: created - System agent created and started"
```

### 2. Deletion Protection
```bash
# Try to delete via API
curl -X DELETE http://localhost:8000/api/agents/trinity-system \
  -H "Authorization: Bearer $TOKEN"

# Expected: 403 with message about system agents
```

### 3. Fleet Status API
```bash
curl http://localhost:8000/api/ops/fleet/status \
  -H "Authorization: Bearer $TOKEN"

# Expected: List of all agents with status, context, activity
```

### 4. Health Check API
```bash
curl http://localhost:8000/api/ops/fleet/health \
  -H "Authorization: Bearer $TOKEN"

# Expected: Health summary with critical_issues, warnings, healthy_count
```

### 5. Emergency Stop
```bash
curl -X POST http://localhost:8000/api/ops/emergency-stop \
  -H "Authorization: Bearer $TOKEN"

# Expected: All schedules paused, all non-system agents stopped
```

### 6. Ops Commands (via Chat)
```bash
# Connect to system agent and run:
# /ops/status
# /ops/health
# /ops/restart <agent-name>
```

### 7. Ops Settings
```bash
# Get current settings
curl http://localhost:8000/api/settings/ops/config \
  -H "Authorization: Bearer $TOKEN"

# Update settings
curl -X PUT http://localhost:8000/api/settings/ops/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"settings": {"ops_context_warning_threshold": "80"}}'
```

## Troubleshooting

### System Agent Not Deploying
1. Check admin user exists in database
2. Verify template exists at `config/agent-templates/trinity-system/`
3. Check backend logs for deployment errors
4. Verify Docker is accessible

### System Agent Can't Access Other Agents
1. Verify MCP key was created with `scope: "system"`
2. Check MCP server logs for authentication
3. Verify key is passed correctly to agent container

### Re-initialization Fails
1. Verify user is admin
2. Check container is accessible
3. Review workspace cleanup errors in response

### Ops Commands Not Working
1. Verify slash commands exist at `config/agent-templates/trinity-system/commands/ops/`
2. Check agent has been re-initialized after template update
3. Verify agent can access MCP tools

## Related Documents

- `docs/drafts/SYSTEM_AGENT_OPS_REQUIREMENTS.md` - Full ops requirements
- `docs/memory/requirements.md` - Requirements 11.1 and 11.2
- `docs/memory/feature-flows/agent-lifecycle.md` - Agent lifecycle operations
