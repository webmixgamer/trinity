# Create Demo Agent Fleet

Create a demo agent fleet to showcase Trinity's capabilities. Three options available:

- **Option A (Recommended)**: Acme Consulting - 3-agent team with business processes
- **Option B**: Research Network - 2-agent system with shared folders
- **Option C**: GitHub Templates (Cornelius, Corbin, Ruby) - requires GitHub PAT

---

## Option A: Acme Consulting (Recommended)

A business-focused 3-agent consulting team demonstrating:
- Agent-to-agent collaboration via MCP
- File-based collaboration via shared folders
- Business process orchestration (Process Engine)

| Agent | Template | Role |
|-------|----------|------|
| **acme-scout** | `local:scout` | Market Research Analyst - finds trends, competitors, opportunities |
| **acme-sage** | `local:sage` | Strategic Advisor - synthesizes research, develops strategy |
| **acme-scribe** | `local:scribe` | Content Writer - creates reports, proposals, deliverables |

### Business Processes

| Process | Steps | Description |
|---------|-------|-------------|
| **client-onboarding** | 4 | Research → Strategy → Human Approval → Proposal |
| **market-analysis** | 4 | Research → Synthesis → Human Review → Report |
| **weekly-brief** | 3 | Intelligence → Commentary → Executive Brief |

### Prerequisites

1. **Trinity platform running** - `./scripts/deploy/start.sh`
2. No external credentials required

### Deploy via System Manifest (Recommended)

Deploy all 3 agents with permissions and shared folders:

```
mcp__trinity__deploy_system(manifest="""
name: acme
description: Acme Consulting AI Team - Scout (Research), Sage (Strategy), Scribe (Content)

agents:
  scout:
    template: local:scout
    folders:
      expose: true
      consume: false

  sage:
    template: local:sage
    folders:
      expose: true
      consume: true

  scribe:
    template: local:scribe
    folders:
      expose: true
      consume: true

permissions:
  preset: full-mesh

auto_start: true
""")
```

This creates:
- `acme-scout` - exposes research at `/home/developer/shared-out`
- `acme-sage` - reads Scout's research, exposes strategy
- `acme-scribe` - reads both, creates deliverables

### Or Deploy Individually

```
mcp__trinity__create_agent(name="acme-scout", template="local:scout")
mcp__trinity__create_agent(name="acme-sage", template="local:sage")
mcp__trinity__create_agent(name="acme-scribe", template="local:scribe")
```

Then configure shared folders and permissions manually via the UI.

### Test Agent Collaboration

1. **Ask Scout to research a topic:**
   ```
   mcp__trinity__chat_with_agent(agent_name="acme-scout", message="/research AI agent platforms")
   ```

2. **Ask Sage to analyze and strategize:**
   ```
   mcp__trinity__chat_with_agent(agent_name="acme-sage", message="/briefing AI agents")
   ```

3. **Ask Scribe to create a deliverable:**
   ```
   mcp__trinity__chat_with_agent(agent_name="acme-scribe", message="/report AI agent market executive")
   ```

### Test Process Execution

Execute a business process via UI:
1. Navigate to http://localhost/processes
2. Click the play button on **weekly-brief**
3. Enter input: `{"topics": "AI agents, automation"}`
4. Watch execution progress on Dashboard Timeline

### Cleanup (Option A)

```
mcp__trinity__delete_agent(name="acme-scout")
mcp__trinity__delete_agent(name="acme-sage")
mcp__trinity__delete_agent(name="acme-scribe")
```

---

## Option B: Research Network

A simpler 2-agent system demonstrating shared folders and inter-agent collaboration.

| Agent | Template | Role |
|-------|----------|------|
| **researcher** | `local:demo-researcher` | Autonomous researcher - discovers trends, writes findings |
| **analyst** | `local:demo-analyst` | Strategic analyst - synthesizes research, generates briefings |

### Prerequisites

1. **Trinity platform running** - `./scripts/deploy/start.sh`
2. No external credentials required

### Deploy via System Manifest

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

### Test the Collaboration

1. **Run research cycle:**
   ```
   mcp__trinity__chat_with_agent(agent_name="research-network-researcher", message="/research")
   ```

2. **Generate briefing:**
   ```
   mcp__trinity__chat_with_agent(agent_name="research-network-analyst", message="/briefing")
   ```

### Cleanup (Option B)

```
mcp__trinity__delete_agent(name="research-network-researcher")
mcp__trinity__delete_agent(name="research-network-analyst")
```

---

## Option C: GitHub Templates (Cornelius, Corbin, Ruby)

Production-style agents from GitHub repositories. Demonstrates GitHub template cloning and source mode sync.

| Agent | Template | Role |
|-------|----------|------|
| **Cornelius** | `github:abilityai/agent-cornelius` | Knowledge Base Manager - Obsidian vault, insights |
| **Corbin** | `github:abilityai/agent-corbin` | Business Assistant - Google Workspace, contacts |
| **Ruby** | `github:abilityai/agent-ruby` | Content Creator - Content strategy, publishing |

### Prerequisites

1. **GitHub PAT must be configured** - Set `GITHUB_PAT` in `.env` and restart backend
2. **Trinity platform running** - `./scripts/deploy/start.sh`

### Step 1: Verify GitHub PAT

```
mcp__trinity__list_templates()
```

If GitHub templates show errors, check `.env` has `GITHUB_PAT=github_pat_xxx`.

### Step 2: Create Agents

```
mcp__trinity__create_agent(name="cornelius", template="github:abilityai/agent-cornelius")
mcp__trinity__create_agent(name="corbin", template="github:abilityai/agent-corbin")
mcp__trinity__create_agent(name="ruby", template="github:abilityai/agent-ruby")
```

### Cleanup (Option C)

```
mcp__trinity__delete_agent(name="cornelius")
mcp__trinity__delete_agent(name="corbin")
mcp__trinity__delete_agent(name="ruby")
```

---

## Post-Creation (All Options)

After creating the fleet:
1. Navigate to http://localhost to see agents on Dashboard
2. Each agent has Trinity MCP auto-injected for agent-to-agent communication
3. Agents can communicate with each other immediately (same-owner permissions are auto-granted)
4. Agents created via system manifest have shared folders pre-configured

## Demo Screenshots

See `docs/demo-screenshots/` for example screenshots of:
- Dashboard Timeline and Graph views
- Agents list and detail pages
- Process list and editor
- Process execution flow

## Notes

- **Local templates** (`local:*`) require no external dependencies
- **GitHub templates** require a valid GitHub PAT with repo access
- Source mode (default): Agents track the `main` branch and can pull updates
- Run `/agent-status` to check fleet health after creation
