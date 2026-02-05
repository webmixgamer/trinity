# Trinity Onboard Plugin

Zero-friction onboarding to deploy any Claude Code agent to the Trinity Deep Agent Orchestration Platform.

## Quick Start

```bash
# Add Trinity marketplace
/plugin marketplace add abilityai/trinity

# Install the onboard plugin
/plugin install trinity-onboard@abilityai-trinity

# Run onboarding
/trinity-onboard:onboard
```

## What It Does

The onboard skill guides you through deploying your agent to Trinity:

1. **Analyzes** your current agent structure
2. **Creates** required configuration files (template.yaml, .gitignore, etc.)
3. **Sets up** git repository and pushes to GitHub
4. **Deploys** agent to Trinity platform
5. **Installs** Trinity management skills for ongoing operations

## Requirements

- Claude Code with plugin support
- GitHub repository (created during onboarding if needed)
- Trinity account with API key

## Configuration Files Created

| File | Purpose |
|------|---------|
| `template.yaml` | Agent metadata for Trinity |
| `.gitignore` | Security-critical exclusions |
| `.env.example` | Documents required environment variables |
| `.mcp.json.template` | MCP server config with placeholders |

## Skills Installed

After onboarding, these skills are available:

| Skill | Command | Description |
|-------|---------|-------------|
| trinity-sync | `/trinity-sync` | Synchronize local and remote agent |
| trinity-remote | `/trinity-remote` | Execute tasks on remote agent |
| trinity-schedules | `/trinity-schedules` | Manage scheduled autonomous tasks |
| trinity-compatibility | `/trinity-compatibility` | Audit agent structure |

## Post-Onboarding

### Check Remote Status

```
/trinity-remote
```

### Push Local Changes

```
/trinity-sync push
```

### Execute on Remote

```
/trinity-remote exec "Run my daily tasks"
```

### Schedule a Task

```
/trinity-schedules schedule procedure-my-task "0 9 * * *" "Daily Task"
```

## Manual Installation

If not using the plugin marketplace:

```bash
# Clone Trinity repository
git clone https://github.com/abilityai/trinity.git

# Run Claude Code with plugin directory
claude --plugin-dir /path/to/trinity/plugins/trinity-onboard
```

## Plugin Structure

```
plugins/trinity-onboard/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── skills/
│   └── onboard/
│       └── SKILL.md         # Main onboarding skill
├── templates/
│   ├── template.yaml.example
│   ├── gitignore.example
│   ├── env.example
│   └── mcp-json.template.example
├── .mcp.json                # Trinity MCP server config
└── README.md                # This file
```

## Troubleshooting

### MCP Server Not Connected

Ensure you have the Trinity API key set:

```bash
export TRINITY_API_KEY=your-api-key
```

Or add to your `.env` file.

### Git Push Failed

1. Verify you have push access to the repository
2. Check for uncommitted changes: `git status`
3. Resolve any merge conflicts

### Agent Creation Failed

1. Verify your Trinity API key is valid
2. Check the agent name is unique (lowercase, hyphens only)
3. Ensure the GitHub repository is accessible

## Support

- **Documentation**: https://trinity.abilityai.dev/docs
- **Issues**: https://github.com/abilityai/trinity/issues
- **Email**: support@ability.ai

## License

MIT License - see repository for details.
