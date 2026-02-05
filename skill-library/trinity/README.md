# Trinity Skills Library

Canonical skills for Trinity-compatible agents. These skills enable any Claude Code agent to integrate with the Trinity Deep Agent Orchestration Platform.

## Available Skills

| Skill | Description | Invocation |
|-------|-------------|------------|
| [trinity-adopt](./trinity-adopt/) | Convert any agent to Trinity-compatible format | `/trinity-adopt` |
| [trinity-compatibility](./trinity-compatibility/) | Audit agent structure for Trinity requirements | `/trinity-compatibility` |
| [trinity-remote](./trinity-remote/) | Remote agent operations (execute, deploy-run) | `/trinity-remote` |
| [trinity-sync](./trinity-sync/) | Git-based synchronization with remote agent | `/trinity-sync` |
| [trinity-schedules](./trinity-schedules/) | Manage scheduled autonomous executions | `/trinity-schedules` |

## Skill Workflow

```
ADOPT → DEVELOP → DEPLOY → RUN → MONITOR
  │        │        │       │       │
  │        │        │       │       └─ /trinity-schedules status
  │        │        │       └─ /trinity-remote exec <prompt>
  │        │        └─ /trinity-sync push
  │        └─ Local development
  └─ /trinity-adopt
```

## Installation

### Via Plugin (Recommended)

The Trinity Onboard plugin installs these skills automatically:

```bash
# Add marketplace
/plugin marketplace add abilityai/trinity

# Install onboard plugin
/plugin install trinity-onboard@abilityai-trinity

# Run onboarding
/trinity-onboard:onboard
```

### Manual Installation

Copy skills to your agent's `.claude/skills/` directory:

```bash
# Copy individual skill
cp -r skill-library/trinity/trinity-adopt ~/.claude/skills/

# Or copy all Trinity skills
cp -r skill-library/trinity/trinity-* ~/.claude/skills/
```

## Skill Details

### trinity-adopt

Converts any Claude Code agent directory to Trinity-compatible format by:
- Creating required files (template.yaml, .env.example, .gitignore)
- Setting up directory structure
- Creating initial policy documents
- Configuring MCP server templates

### trinity-compatibility

Read-only audit that checks:
- Required files exist (template.yaml, CLAUDE.md, .mcp.json.template, etc.)
- Directory structure is correct
- Security requirements are met (.gitignore excludes credentials)
- No hardcoded secrets present

### trinity-remote

Interact with the remote Trinity agent:
- `status` - Check remote agent status
- `exec <prompt>` - Execute prompt on remote without syncing
- `run <prompt>` - Sync local changes then execute (deploy-run)
- `notify` - Configure notification settings

### trinity-sync

Git-based synchronization between local and remote:
- `status` - Compare local and remote state
- `push` - Push local changes to remote
- `pull` - Pull remote changes to local
- `deploy <branch>` - Deploy specific branch to remote
- `branches` - List available branches

### trinity-schedules

Manage scheduled autonomous executions:
- `status` - View all schedules and their state
- `schedule <skill> <cron>` - Create/update a schedule
- `trigger <skill>` - Manually trigger execution
- `history` - View execution history
- `pause/resume` - Control schedule state

## Agent Name Detection

Skills detect the agent name in this order:
1. `name` field in `template.yaml`
2. Current directory name
3. `TRINITY_AGENT_NAME` environment variable

## Requirements

- Claude Code with skill support
- Git repository (for sync functionality)
- Trinity MCP server connection (for remote operations)

## See Also

- [Trinity Documentation](https://trinity.abilityai.dev/docs)
- [Trinity Onboard Plugin](../plugins/trinity-onboard/)
- [Agent Template Specification](../../docs/AGENT_TEMPLATE_SPEC.md)
