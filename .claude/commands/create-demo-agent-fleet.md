# Create Demo Agent Fleet

Create the demo agent fleet (Cornelius, Corbin, Ruby) from GitHub templates. These agents demonstrate agent-to-agent collaboration without external integrations.

## Demo Fleet Agents

| Agent | Template | Role |
|-------|----------|------|
| **Cornelius** | `github:abilityai/agent-cornelius` | Knowledge Base Manager - Obsidian vault, insights |
| **Corbin** | `github:abilityai/agent-corbin` | Business Assistant - Google Workspace, contacts |
| **Ruby** | `github:abilityai/agent-ruby` | Content Creator - Content strategy, publishing |

## Prerequisites

1. **GitHub PAT must be configured** - The `GITHUB_PAT` environment variable should be set in `.env` and the backend must be running (it auto-uploads to Redis on startup)
2. **Trinity platform running** - `./scripts/deploy/start.sh`

## Execution Steps

### Step 1: Verify GitHub PAT is Available

```
mcp__trinity__list_templates()
```

If GitHub templates show errors, the PAT is not configured. Check:
- `.env` has `GITHUB_PAT=github_pat_xxx`
- Backend was restarted after adding the PAT

### Step 2: Create Each Agent

Create in this order (no dependencies between them):

```
mcp__trinity__create_agent(name="cornelius", template="github:abilityai/agent-cornelius")
mcp__trinity__create_agent(name="corbin", template="github:abilityai/agent-corbin")
mcp__trinity__create_agent(name="ruby", template="github:abilityai/agent-ruby")
```

### Step 3: Start All Agents

```
mcp__trinity__start_agent(name="cornelius")
mcp__trinity__start_agent(name="corbin")
mcp__trinity__start_agent(name="ruby")
```

### Step 4: Verify Fleet Status

```
mcp__trinity__list_agents()
```

**Expected:** All 3 agents show `status: "running"`

## Post-Creation

After creating the fleet:
1. Navigate to http://localhost:3000/ to see agents on Dashboard
2. Each agent will have Trinity MCP auto-injected for agent-to-agent communication
3. Agents can communicate with each other immediately (same-owner permissions are auto-granted)

## Credential Requirements

These agents can demonstrate collaboration without external credentials. For full functionality:

| Agent | Optional Credentials |
|-------|---------------------|
| Cornelius | `SMART_VAULT_PATH`, `GEMINI_API_KEY` |
| Corbin | `GOOGLE_CLOUD_PROJECT_ID`, `LINKEDIN_NETWORK_API_KEY` |
| Ruby | `TWITTER_*`, `CLOUDINARY_*`, `HEYGEN_API_KEY` |

## Notes

- Agents are created from GitHub templates (requires PAT)
- Each agent gets a unique working branch: `trinity/{agent-name}/{instance-id}`
- The demo can run without external credentials - agents will use their base capabilities
- Run `/demo-agent-fleet` after creation to showcase the platform

## Cleanup

To remove the demo fleet:
```
mcp__trinity__delete_agent(name="cornelius")
mcp__trinity__delete_agent(name="corbin")
mcp__trinity__delete_agent(name="ruby")
```
