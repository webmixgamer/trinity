# Demo Agent Fleet - Trinity Platform Showcase

Demonstrate Trinity Deep Agent Orchestration Platform using the demo fleet (Cornelius, Corbin, Ruby).

## Safety Guarantees

**This demo will NOT:**
- Post to social media (Twitter, LinkedIn, etc.)
- Send emails or messages externally
- Make external API calls
- Execute destructive operations

**This demo WILL:**
- Have agents communicate via Trinity MCP
- Show real-time Dashboard visualization
- Demonstrate meaningful multi-agent collaboration
- Create and track workplans (Pillar I - Explicit Planning)
- Update custom metrics per agent

---

## The Demo Fleet

| Agent | Role | Collaboration Pattern |
|-------|------|----------------------|
| **Cornelius** | Knowledge Brain | Provides insights, perspectives, synthesizes ideas from Obsidian vault |
| **Ruby** | Content Producer | Creates content strategy, asks Cornelius for intellectual depth |
| **Corbin** | Business Coordinator | Manages tasks, delegates work, coordinates the team |

**Natural Information Flow:**
```
Corbin (coordinator) ─────┬────────► Ruby (producer)
         │                │              │
         │                │              │
         ▼                │              ▼
    Delegates work        │        Requests insights
         │                │              │
         └────────────────┴──────► Cornelius (brain)
```

---

## EXECUTION INSTRUCTIONS

Run this demo by executing each section in order. Use the MCP tools and bash commands as specified.

---

## STEP 1: Prerequisites Check

### 1.1: Verify Demo Fleet Exists

```
mcp__trinity__list_agents()
```

**Check for agents:** `cornelius`, `corbin`, `ruby`

- **If ANY are missing:** Run `/create-demo-agent-fleet` first, then return here.
- **If agents exist but are stopped:** Start them with `mcp__trinity__start_agent(name="<name>")`

### 1.2: Browser Setup

Use Chrome DevTools MCP to navigate and authenticate:

```
mcp__chrome-devtools__navigate_page(url="http://localhost:3000/")
```

If page shows login form, authenticate:
```
mcp__chrome-devtools__fill(uid="<username-field>", value="admin")
mcp__chrome-devtools__fill(uid="<password-field>", value="password")
mcp__chrome-devtools__click(uid="<sign-in-button>")
```

Take a snapshot to verify dashboard shows 3 agents:
```
mcp__chrome-devtools__take_snapshot()
```

**If "No agents" shown:** Sign out and re-login (stale session).

---

## STEP 2: Initialize Demo State

This step creates initial workplans and metrics so the demo has context.

### 2.1: Create Cornelius's Workplan (Knowledge Synthesis)

```bash
docker exec agent-cornelius mkdir -p /home/developer/plans/active && docker exec agent-cornelius tee /home/developer/plans/active/plan-insight-synthesis.yaml << 'EOF'
id: plan-insight-synthesis
name: "Deep Agent Thought Leadership"
status: active
created: "2025-12-11T09:00:00Z"
description: "Synthesize insights on AI agents from knowledge base for content creation"
tasks:
  - id: task-1
    name: "Search knowledge base for AI agent insights"
    status: completed
    completed_at: "2025-12-11T09:15:00Z"
    result: "Found 23 relevant notes on agent architectures, autonomy patterns"
  - id: task-2
    name: "Extract Eugene's unique perspective on deep agents"
    status: completed
    completed_at: "2025-12-11T09:30:00Z"
    result: "Key thesis: Four Pillars framework differentiates reactive chatbots from autonomous agents"
  - id: task-3
    name: "Identify cross-domain connections"
    status: active
    depends_on: [task-1, task-2]
  - id: task-4
    name: "Generate synthesis report for content team"
    status: pending
    depends_on: [task-3]
EOF
```

### 2.2: Create Ruby's Workplan (Content Strategy)

```bash
docker exec agent-ruby mkdir -p /home/developer/plans/active && docker exec agent-ruby tee /home/developer/plans/active/plan-content-campaign.yaml << 'EOF'
id: plan-content-campaign
name: "AI Agents Content Campaign"
status: active
created: "2025-12-11T10:00:00Z"
description: "Create multi-platform content campaign on AI agents topic"
tasks:
  - id: task-1
    name: "Request insights from Cornelius"
    status: completed
    completed_at: "2025-12-11T10:15:00Z"
    result: "Received Four Pillars framework and key differentiators"
  - id: task-2
    name: "Draft LinkedIn thought leadership post"
    status: active
    depends_on: [task-1]
  - id: task-3
    name: "Create Twitter thread outline"
    status: pending
    depends_on: [task-1]
  - id: task-4
    name: "Design infographic concepts"
    status: pending
    depends_on: [task-2]
  - id: task-5
    name: "Prepare content calendar"
    status: pending
    depends_on: [task-3, task-4]
EOF
```

### 2.3: Create Corbin's Workplan (Campaign Coordination)

```bash
docker exec agent-corbin mkdir -p /home/developer/plans/active && docker exec agent-corbin tee /home/developer/plans/active/plan-campaign-coordination.yaml << 'EOF'
id: plan-campaign-coordination
name: "Q1 Thought Leadership Campaign"
status: active
created: "2025-12-11T08:00:00Z"
description: "Coordinate cross-agent thought leadership campaign on AI agents"
tasks:
  - id: task-1
    name: "Define campaign objectives"
    status: completed
    completed_at: "2025-12-11T08:30:00Z"
    result: "Goal: Establish Eugene as Deep Agent thought leader"
  - id: task-2
    name: "Assign knowledge synthesis to Cornelius"
    status: completed
    completed_at: "2025-12-11T08:45:00Z"
    result: "Delegated via Trinity MCP"
  - id: task-3
    name: "Assign content creation to Ruby"
    status: completed
    completed_at: "2025-12-11T09:00:00Z"
    result: "Delegated via Trinity MCP"
  - id: task-4
    name: "Monitor agent progress"
    status: active
    depends_on: [task-2, task-3]
  - id: task-5
    name: "Compile campaign status report"
    status: pending
    depends_on: [task-4]
  - id: task-6
    name: "Schedule stakeholder review"
    status: pending
    depends_on: [task-5]
EOF
```

### 2.4: Create Metrics Files

```bash
docker exec agent-cornelius tee /home/developer/metrics.json << 'EOF'
{
  "notes_searched": 47,
  "insights_extracted": 12,
  "articles_generated": 3,
  "connections_mapped": 28,
  "synthesis_requests": 8,
  "agent_state": "researching"
}
EOF
```

```bash
docker exec agent-ruby tee /home/developer/metrics.json << 'EOF'
{
  "posts_published": 0,
  "videos_generated": 0,
  "platforms_active": 0,
  "content_scheduled": 0,
  "collaborations": 2,
  "agent_state": "active"
}
EOF
```

```bash
docker exec agent-corbin tee /home/developer/metrics.json << 'EOF'
{
  "emails_processed": 0,
  "meetings_scheduled": 0,
  "tasks_created": 6,
  "delegations_sent": 2,
  "contacts_searched": 0,
  "agent_state": "coordinating"
}
EOF
```

---

## STEP 3: Verify Dashboard State

```
mcp__chrome-devtools__navigate_page(url="http://localhost:3000/")
mcp__chrome-devtools__take_screenshot()
```

**Expected Dashboard State:**
- Header: "3 agents - 3 running - 3 plans"
- Cornelius: Tasks 2/4 (50%), State: Researching
- Ruby: Tasks 1/5 (20%), State: Active
- Corbin: Tasks 3/6 (50%), State: Coordinating

---

## STEP 4: Scenario A - Knowledge Request Flow

**Story:** Ruby needs intellectual depth for content creation. She asks Cornelius for Eugene's unique perspective on AI agents.

### 4.1: Ruby Requests Insight from Cornelius

```
mcp__trinity__chat_with_agent(
  agent_name="ruby",
  message="You're working on the AI Agents Content Campaign. You need intellectual depth for your LinkedIn post. Use the Trinity MCP to message Cornelius with this request: 'I'm drafting a thought leadership post about AI agents. What is Eugene's unique perspective on what differentiates true AI agents from simple chatbots? I need 2-3 key insights I can build content around.' Then report what Cornelius shares with you."
)
```

**Dashboard shows:** Edge from ruby → cornelius (animated)

### 4.2: Verify Collaboration in Dashboard

```
mcp__chrome-devtools__navigate_page(url="http://localhost:3000/")
mcp__chrome-devtools__take_screenshot()
```

**Expected:** Message count increased, edge visible between Ruby and Cornelius

---

## STEP 5: Scenario B - Coordinator Delegation Flow

**Story:** Corbin is coordinating the campaign. He checks in with both agents to monitor progress and requests updates.

### 5.1: Corbin Checks Campaign Status

```
mcp__trinity__chat_with_agent(
  agent_name="corbin",
  message="You're coordinating the Q1 Thought Leadership Campaign. Use the Trinity MCP to check on your team:

1. First, list available agents to see who's online
2. Message Cornelius: 'Campaign status check - what insights have you synthesized so far for the AI agents thought leadership piece?'
3. Message Ruby: 'Campaign status check - how is the content creation progressing? What do you need from the team?'

Summarize the status you receive from each agent in a brief coordination report."
)
```

**Dashboard shows:**
- Edge from corbin → cornelius
- Edge from corbin → ruby
- All 3 agents show recent activity

### 5.2: Screenshot Multi-Agent Activity

```
mcp__chrome-devtools__navigate_page(url="http://localhost:3000/")
mcp__chrome-devtools__take_screenshot()
```

---

## STEP 6: Scenario C - Cross-Pollination Flow

**Story:** Cornelius discovers a connection that's relevant to Ruby's content strategy. He proactively shares it.

### 6.1: Cornelius Shares Discovery

```
mcp__trinity__chat_with_agent(
  agent_name="cornelius",
  message="You've been synthesizing insights on AI agents and discovered a compelling connection between agent autonomy and the Buddhist concept of 'skillful means' (upaya). This cross-domain insight could make for unique content. Use the Trinity MCP to message Ruby: 'I found an interesting angle for your content - there's a parallel between agent autonomy levels and the Buddhist concept of skillful means. Agents that adapt their approach based on context (like upaya) are more effective than rigid rule-followers. This could differentiate Eugene's perspective from typical AI agent content.' Share this insight and ask if she wants you to develop it further."
)
```

**Dashboard shows:** Edge from cornelius → ruby (note: reverse direction from earlier)

### 6.2: Ruby Responds and Requests Elaboration

```
mcp__trinity__chat_with_agent(
  agent_name="ruby",
  message="You just received an interesting insight from Cornelius about Buddhist concepts and AI agents. This is exactly the kind of unique angle that makes thought leadership stand out. Use the Trinity MCP to respond to Cornelius: 'This is great! The skillful means angle is unique - no one else is making this connection. Can you give me 2-3 bullet points explaining this parallel that I can use in a LinkedIn post? Keep it accessible for a business audience.' Then report what additional detail he provides."
)
```

**Dashboard shows:** Bidirectional communication between Ruby and Cornelius

---

## STEP 7: Scenario D - Full Coordination Loop

**Story:** Corbin brings everyone together for a final sync before the campaign launches.

### 7.1: Corbin Orchestrates Team Sync

```
mcp__trinity__chat_with_agent(
  agent_name="corbin",
  message="Time for a final campaign sync. As the coordinator, use the Trinity MCP to:

1. Message Cornelius: 'Final sync - please provide your top 3 synthesized insights for the campaign, ranked by uniqueness'
2. Message Ruby: 'Final sync - what content pieces are ready? What's still in progress?'

Then create a brief campaign readiness report that includes:
- Knowledge assets ready (from Cornelius)
- Content pieces status (from Ruby)
- Overall campaign readiness percentage
- Any blockers or dependencies

This report will be shared with Eugene for final approval."
)
```

**Dashboard shows:** All edges active, demonstrating full coordination

---

## STEP 8: Update Workplan Progress

After the collaboration, update task progress to reflect the work done.

### 8.1: Update Cornelius's Plan

```bash
docker exec agent-cornelius tee /home/developer/plans/active/plan-insight-synthesis.yaml << 'EOF'
id: plan-insight-synthesis
name: "Deep Agent Thought Leadership"
status: active
created: "2025-12-11T09:00:00Z"
description: "Synthesize insights on AI agents from knowledge base for content creation"
tasks:
  - id: task-1
    name: "Search knowledge base for AI agent insights"
    status: completed
    completed_at: "2025-12-11T09:15:00Z"
    result: "Found 23 relevant notes on agent architectures, autonomy patterns"
  - id: task-2
    name: "Extract Eugene's unique perspective on deep agents"
    status: completed
    completed_at: "2025-12-11T09:30:00Z"
    result: "Key thesis: Four Pillars framework differentiates reactive chatbots from autonomous agents"
  - id: task-3
    name: "Identify cross-domain connections"
    status: completed
    completed_at: "2025-12-11T11:00:00Z"
    result: "Connected agent autonomy to Buddhist skillful means (upaya) concept"
  - id: task-4
    name: "Generate synthesis report for content team"
    status: completed
    completed_at: "2025-12-11T11:30:00Z"
    result: "Delivered 3 ranked insights to Ruby for content creation"
EOF
```

### 8.2: Update Ruby's Plan

```bash
docker exec agent-ruby tee /home/developer/plans/active/plan-content-campaign.yaml << 'EOF'
id: plan-content-campaign
name: "AI Agents Content Campaign"
status: active
created: "2025-12-11T10:00:00Z"
description: "Create multi-platform content campaign on AI agents topic"
tasks:
  - id: task-1
    name: "Request insights from Cornelius"
    status: completed
    completed_at: "2025-12-11T10:15:00Z"
    result: "Received Four Pillars framework and skillful means angle"
  - id: task-2
    name: "Draft LinkedIn thought leadership post"
    status: completed
    completed_at: "2025-12-11T11:45:00Z"
    result: "Draft ready with unique Buddhist-AI connection angle"
  - id: task-3
    name: "Create Twitter thread outline"
    status: active
    depends_on: [task-1]
  - id: task-4
    name: "Design infographic concepts"
    status: pending
    depends_on: [task-2]
  - id: task-5
    name: "Prepare content calendar"
    status: pending
    depends_on: [task-3, task-4]
EOF
```

### 8.3: Update Corbin's Plan

```bash
docker exec agent-corbin tee /home/developer/plans/active/plan-campaign-coordination.yaml << 'EOF'
id: plan-campaign-coordination
name: "Q1 Thought Leadership Campaign"
status: active
created: "2025-12-11T08:00:00Z"
description: "Coordinate cross-agent thought leadership campaign on AI agents"
tasks:
  - id: task-1
    name: "Define campaign objectives"
    status: completed
    completed_at: "2025-12-11T08:30:00Z"
    result: "Goal: Establish Eugene as Deep Agent thought leader"
  - id: task-2
    name: "Assign knowledge synthesis to Cornelius"
    status: completed
    completed_at: "2025-12-11T08:45:00Z"
    result: "Delegated via Trinity MCP - completed successfully"
  - id: task-3
    name: "Assign content creation to Ruby"
    status: completed
    completed_at: "2025-12-11T09:00:00Z"
    result: "Delegated via Trinity MCP - LinkedIn draft ready"
  - id: task-4
    name: "Monitor agent progress"
    status: completed
    completed_at: "2025-12-11T12:00:00Z"
    result: "Both agents on track, unique angle discovered"
  - id: task-5
    name: "Compile campaign status report"
    status: active
    depends_on: [task-4]
  - id: task-6
    name: "Schedule stakeholder review"
    status: pending
    depends_on: [task-5]
EOF
```

### 8.4: Update Metrics

```bash
docker exec agent-cornelius tee /home/developer/metrics.json << 'EOF'
{
  "notes_searched": 89,
  "insights_extracted": 23,
  "articles_generated": 3,
  "connections_mapped": 45,
  "synthesis_requests": 14,
  "agent_state": "active"
}
EOF
```

```bash
docker exec agent-ruby tee /home/developer/metrics.json << 'EOF'
{
  "posts_published": 0,
  "videos_generated": 0,
  "platforms_active": 0,
  "content_scheduled": 1,
  "collaborations": 6,
  "agent_state": "active"
}
EOF
```

```bash
docker exec agent-corbin tee /home/developer/metrics.json << 'EOF'
{
  "emails_processed": 0,
  "meetings_scheduled": 0,
  "tasks_created": 6,
  "delegations_sent": 4,
  "contacts_searched": 0,
  "agent_state": "active"
}
EOF
```

---

## STEP 9: Final Dashboard Verification

### 9.1: Dashboard Screenshot

```
mcp__chrome-devtools__navigate_page(url="http://localhost:3000/")
mcp__chrome-devtools__take_screenshot()
```

**Expected Final State:**
- Multiple message edges visible between all agents
- Task progress updated on all agent cards
- All agents showing "Active" state

### 9.2: Check Individual Agent Details

**Cornelius - Workplan Tab:**
```
mcp__chrome-devtools__navigate_page(url="http://localhost:3000/agents/cornelius")
mcp__chrome-devtools__click(uid="<workplan-tab>")
mcp__chrome-devtools__take_snapshot()
```
Expected: 4/4 tasks completed (100%)

**Ruby - Workplan Tab:**
```
mcp__chrome-devtools__navigate_page(url="http://localhost:3000/agents/ruby")
mcp__chrome-devtools__click(uid="<workplan-tab>")
mcp__chrome-devtools__take_snapshot()
```
Expected: 2/5 tasks completed (40%)

**Corbin - Workplan Tab:**
```
mcp__chrome-devtools__navigate_page(url="http://localhost:3000/agents/corbin")
mcp__chrome-devtools__click(uid="<workplan-tab>")
mcp__chrome-devtools__take_snapshot()
```
Expected: 4/6 tasks completed (67%)

---

## Demo Results Summary

Report these results to the user:

```markdown
## Demo Fleet Results

**Timestamp**: [current time]
**Environment**: Local (localhost:3000)
**Agents**: cornelius, corbin, ruby

### Four Pillars Demonstrated

| Pillar | Feature | Status |
|--------|---------|--------|
| I. Explicit Planning | Workplans with task dependencies | ✅ |
| II. Hierarchical Delegation | Corbin coordinates, delegates to others | ✅ |
| III. Persistent Memory | Metrics, workplan state survive | ✅ |
| IV. Context Engineering | Each agent has specialized CLAUDE.md | ✅ |

### Collaboration Patterns Shown

| Scenario | Flow | Purpose |
|----------|------|---------|
| A. Knowledge Request | Ruby → Cornelius | Content creator seeks intellectual depth |
| B. Coordinator Check-in | Corbin → Both | Manager monitors team progress |
| C. Cross-Pollination | Cornelius → Ruby | Knowledge worker shares discovery |
| D. Full Coordination | Corbin → Both → Back | End-to-end campaign sync |

### Agent Final Status

| Agent | Role | Tasks | Key Metric |
|-------|------|-------|------------|
| Cornelius | Knowledge Brain | 4/4 (100%) | 45 connections mapped |
| Ruby | Content Producer | 2/5 (40%) | 6 collaborations |
| Corbin | Coordinator | 4/6 (67%) | 4 delegations sent |

### Messages Exchanged
- Ruby → Cornelius: 2
- Corbin → Cornelius: 2
- Corbin → Ruby: 2
- Cornelius → Ruby: 1
- **Total**: 7+ inter-agent messages

**Demo Status**: Complete
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No agents" on Dashboard | Re-login: sign out, refresh, login again |
| Agent shows "Offline" | `mcp__trinity__start_agent(name="<name>")` |
| Login fails | Check password in docker-compose.yml (default: `password`) |
| Metrics not showing | Re-run Step 2.4 to create metrics.json files |
| Workplans not showing | Re-run Steps 2.1-2.3 to create workplan files |
| Fleet doesn't exist | Run `/create-demo-agent-fleet` first |
| Agent can't see other agents | Check permissions in AgentDetail → Permissions tab |

---

## Notes

- Agent names are lowercase: cornelius, corbin, ruby
- Agents have Trinity MCP auto-injected for collaboration
- No external credentials needed for basic demo
- Demo creates real message history in the database
- Safe to run multiple times - adds to collaboration history
- Do NOT delete agents after demo - preserves state for future demos
