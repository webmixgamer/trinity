# Create Demo Agent Fleet

Create a demo agent fleet to showcase Trinity's agent-to-agent collaboration capabilities. Two options available:

- **Option A (Recommended)**: Local Research Network - no external dependencies, demonstrates shared folders
- **Option B**: GitHub Templates (Cornelius, Corbin, Ruby) - requires GitHub PAT

---

## Option A: Local Research Network (Recommended)

A self-contained 2-agent system demonstrating shared folders and inter-agent collaboration.

| Agent | Template | Role |
|-------|----------|------|
| **researcher** | `local:demo-researcher` | Autonomous researcher - discovers trends, writes findings |
| **analyst** | `local:demo-analyst` | Strategic analyst - synthesizes research, generates briefings |

### Prerequisites

1. **Trinity platform running** - `./scripts/deploy/start.sh`
2. No external credentials required

### Deploy via System Manifest (Recommended)

Deploy both agents with proper permissions and shared folders in one command:

```
mcp__trinity__deploy_system(manifest="""
name: research-network
description: Research and analysis demo system

agents:
  researcher:
    template: local:demo-researcher
    folders:
      expose: true
      consume: false

  analyst:
    template: local:demo-analyst
    folders:
      expose: false
      consume: true

permissions:
  preset: full-mesh
""")
```

This creates:
- `research-network-researcher` - exposes shared folder at `/home/developer/shared-out`
- `research-network-analyst` - mounts researcher's folder at `/home/developer/shared-in/research-network-researcher`

### Or Deploy Individually

```
mcp__trinity__create_agent(name="researcher", template="local:demo-researcher")
mcp__trinity__create_agent(name="analyst", template="local:demo-analyst")
```

Then configure shared folders and permissions manually via the UI.

### Test the Collaboration

1. **Run research cycle on the researcher:**
   ```
   mcp__trinity__chat_with_agent(agent_name="research-network-researcher", message="/research")
   ```

2. **Generate briefing from the analyst:**
   ```
   mcp__trinity__chat_with_agent(agent_name="research-network-analyst", message="/briefing")
   ```

3. **Ask the analyst to request specific research:**
   ```
   mcp__trinity__chat_with_agent(agent_name="research-network-analyst", message="/request-research AI agent architectures")
   ```

### Cleanup (Option A)

```
mcp__trinity__delete_agent(name="research-network-researcher")
mcp__trinity__delete_agent(name="research-network-analyst")
```

---

## Option B: GitHub Templates (Cornelius, Corbin, Ruby)

Production-style agents from GitHub repositories. Demonstrates GitHub template cloning and source mode sync.

| Agent | Template | Role |
|-------|----------|------|
| **Cornelius** | `github:abilityai/agent-cornelius` | Knowledge Base Manager - Obsidian vault, insights |
| **Corbin** | `github:abilityai/agent-corbin` | Business Assistant - Google Workspace, contacts |
| **Ruby** | `github:abilityai/agent-ruby` | Content Creator - Content strategy, publishing |

### Prerequisites

1. **GitHub PAT must be configured** - The `GITHUB_PAT` environment variable should be set in `.env` and the backend must be running (it auto-uploads to Redis on startup)
2. **Trinity platform running** - `./scripts/deploy/start.sh`

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

### Step 3: Verify Fleet Status

```
mcp__trinity__list_agents()
```

**Expected:** All 3 agents show `status: "running"`

### Credential Requirements (Optional)

These agents can demonstrate collaboration without external credentials. For full functionality:

| Agent | Optional Credentials |
|-------|---------------------|
| Cornelius | `SMART_VAULT_PATH`, `GEMINI_API_KEY` |
| Corbin | `GOOGLE_CLOUD_PROJECT_ID`, `LINKEDIN_API_KEY` |
| Ruby | `TWITTER_*`, `CLOUDINARY_*`, `HEYGEN_API_KEY` |

### Cleanup (Option B)

```
mcp__trinity__delete_agent(name="cornelius")
mcp__trinity__delete_agent(name="corbin")
mcp__trinity__delete_agent(name="ruby")
```

---

## Post-Creation (Both Options)

After creating the fleet:
1. Navigate to http://localhost:3000/ to see agents on Dashboard
2. Each agent has Trinity MCP auto-injected for agent-to-agent communication
3. Agents can communicate with each other immediately (same-owner permissions are auto-granted)
4. Agents created via system manifest have shared folders pre-configured

## Notes

- **Local templates** (`local:demo-*`) require no external dependencies
- **GitHub templates** require a valid GitHub PAT with repo access
- Source mode (default): Agents track the `main` branch and can pull updates
- Run `/agent-status` to check fleet health after creation
