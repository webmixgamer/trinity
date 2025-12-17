# Feature: Testing Agents Suite

> **Status**: Implemented and Tested
> **Created**: 2025-12-07
> **Last Tested**: 2025-12-08
> **Purpose**: Systematic verification of Trinity platform functionality using predictable test agents

---

## Overview

Trinity includes a suite of **8 testing agents** designed for systematic platform verification. Each agent performs ONE function well with predictable, deterministic behavior - making them ideal for testing specific Trinity features.

## User Story

As a Trinity developer, I want predictable test agents so that I can systematically verify platform functionality without complex AI behavior interfering with test results.

---

## Test Agent Suite

| Agent | Repository | Tests | Priority | Status |
|-------|------------|-------|----------|--------|
| **test-echo** | `github:abilityai/test-agent-echo` | Basic chat, streaming | HIGH | PASSED |
| **test-counter** | `github:abilityai/test-agent-counter` | File persistence, state | MEDIUM | PASSED |
| **test-worker** | `github:abilityai/test-agent-worker` | Workplan system (Pillar I) | HIGH | PARTIAL |
| **test-delegator** | `github:abilityai/test-agent-delegator` | Agent-to-agent (Pillar II) | HIGH | PASSED |
| **test-scheduler** | `github:abilityai/test-agent-scheduler` | Cron execution | HIGH | Configured |
| **test-queue** | `github:abilityai/test-agent-queue` | Execution queue, 429 | HIGH | Configured |
| **test-files** | `github:abilityai/test-agent-files` | File browser API | MEDIUM | Configured |
| **test-error** | `github:abilityai/test-agent-error` | Error handling | MEDIUM | Configured |

---

## Test Results (2025-12-08)

### Full System Test Session (14:00 UTC)

**Environment**: Local development (localhost:3000 + localhost:8000)
**Auth**: Dev mode with admin/trinity2024

| Step | Action | Result |
|------|--------|--------|
| 1 | Clean up existing test agents | ✅ Removed 4 containers |
| 2 | Verify Templates page | ✅ All 8 test agents displayed |
| 3 | Create test-echo via API | ✅ Agent created and running |
| 4 | Create test-counter via API | ✅ Agent created and running |
| 5 | Create test-delegator via API | ✅ Agent created and running |
| 6 | Dashboard visualization | ✅ 3 agents, all showing "Idle" |
| 7 | test-echo chat test | ✅ PASSED |
| 8 | test-counter persistence test | ✅ PASSED |
| 9 | test-delegator collaboration test | ✅ PASSED |
| 10 | Dashboard collaboration edges | ✅ "6x" edge visible |

### Verified Working

| Agent | Test | Result | Notes |
|-------|------|--------|-------|
| **test-echo** | Basic chat | ✅ PASSED | "Hello World" → "Echo: Hello World\nWords: 2\nCharacters: 11" |
| **test-counter** | State persistence | ✅ PASSED | Reset → 0, Increment → 1 |
| **test-counter** | File persistence | ✅ PASSED | counter.txt maintained, Read/Write tool calls visible |
| **test-delegator** | Trinity MCP | ✅ PASSED | Connected to Trinity MCP server |
| **test-delegator** | list_agents | ✅ PASSED | Listed all 3 test agents |
| **test-delegator** | chat_with_agent | ✅ PASSED | Delegated to test-echo, 2.2s response time |
| **Dashboard** | Agent network | ✅ PASSED | Vue Flow nodes with status indicators |
| **Dashboard** | Collaboration edges | ✅ PASSED | Edge with "6x" message count label |

### Key Findings

1. **test-echo**: Fully functional. Returns predictable echo with word/character count.

2. **test-counter**: Fully functional. State persists in `counter.txt` file. Activity panel shows Read/Write tool calls.

3. **test-delegator**: Trinity MCP integration works correctly. The agent successfully:
   - Connected to Trinity MCP server
   - Listed available agents via `mcp__trinity__list_agents`
   - Delegated messages to test-echo via `mcp__trinity__chat_with_agent`
   - Response time: 2.2 seconds for full delegation round-trip

4. **Dashboard Visualization**: Agent network shows collaboration edges with message counts. "6x" label indicates 6 messages exchanged between test-delegator and test-echo.

5. **Known Issue - Template Pre-selection**: CreateAgentModal shows "Blank Agent" when opened from Templates page "Use Template" button. The `initial-template` prop isn't being applied. **Workaround**: Create agents via API.

6. **Known Issue - Session Expiration**: After backend activity (agent creation), frontend sessions may expire. **Workaround**: Re-login with admin/trinity2024.

---

## Entry Points

### UI
- **Templates Page** (`/templates`): Test agents appear in GitHub templates section
- **Create Agent Modal**: Select any test agent template
- **Agent Detail Page**: Test via chat, verify features

### API
- `GET /api/templates` - Returns all templates including test agents
- `POST /api/agents` - Create agent from test template
- Template ID format: `github:abilityai/test-agent-{name}`

---

## Configuration

### Backend (`src/backend/config.py`)

All 8 test agents are defined in `TEST_AGENT_TEMPLATES` (lines 168-268):

```python
TEST_AGENT_TEMPLATES = [
    {
        "id": "github:abilityai/test-agent-echo",
        "display_name": "Test: Echo (GitHub)",
        "description": "Simple echo agent for testing basic chat functionality...",
        "github_repo": "abilityai/test-agent-echo",
        "github_credential_id": "4g4p363VFbI4JJqp98Yr0Q",
        "source": "github",
        "resources": {"cpu": "1", "memory": "2g"},
        "mcp_servers": [],
        "required_credentials": [],
        "category": "testing"
    },
    # ... test-counter, test-worker, test-delegator
    # ... test-scheduler, test-queue, test-files, test-error
]

# Combined with production templates
ALL_GITHUB_TEMPLATES = GITHUB_TEMPLATES + TEST_AGENT_TEMPLATES
```

### Template Files Updated

| File | Change |
|------|--------|
| `config.py` | Added `TEST_AGENT_TEMPLATES` (8 agents) and `ALL_GITHUB_TEMPLATES` |
| `routers/templates.py` | Import `ALL_GITHUB_TEMPLATES` instead of `GITHUB_TEMPLATES` |
| `services/template_service.py` | Use `ALL_GITHUB_TEMPLATES` in `get_github_template()` |
| `routers/agents.py` | Removed unused `GITHUB_TEMPLATES` import |

### Local Repository Structure

All 8 test agent repositories exist locally in `repositories/`:

```
repositories/
  test-agent-echo/
  test-agent-counter/
  test-agent-worker/
  test-agent-delegator/
  test-agent-scheduler/
  test-agent-queue/
  test-agent-files/
  test-agent-error/
```

Each repository contains:
```
test-agent-{name}/
  template.yaml      # Trinity metadata
  CLAUDE.md          # Agent instructions
  README.md          # Human documentation
  .gitignore         # Ignore .env, .mcp.json
```

> **Note**: GitHub repositories need to be created and pushed. Currently only local repos exist in `repositories/` folder.

---

## Agent Specifications

### 1. test-echo - Basic Chat Testing

**Commands**: Any text
**Response Format**:
```
Echo: [original message]
Words: [word count]
Characters: [character count]
```

**Tests**:
- Agent creation/start/stop
- Basic chat API
- Response streaming
- WebSocket status updates

### 2. test-counter - State Persistence

**Commands**: `get`, `increment`, `decrement`, `add N`, `subtract N`, `reset`
**Response Format**: `Counter: [value] (previous: [old_value])`

**Tests**:
- File read/write operations
- State persistence across messages
- Context window growth
- File browser API

### 3. test-worker - Workplan System

**Commands**: `create plan: [desc]`, `complete task: [id]`, `fail task: [id]`, `plan status`, `complete plan`

**Tests**:
- Workplan creation API
- Task dependencies (blocked -> pending)
- Plan completion/archiving
- Dashboard visibility
- Trinity command injection

> **Note**: Workplan slash commands not yet implemented in GitHub repo CLAUDE.md

### 4. test-delegator - Agent-to-Agent Communication

**Commands**: `list agents`, `delegate to [agent]: [message]`, `ping [agent]`, `chain [a1] [a2]: [msg]`, `broadcast: [msg]`

**Tests**:
- Trinity MCP injection
- Agent-scoped API keys
- `chat_with_agent` tool
- Access control (same owner)
- Collaboration events
- 429 handling for busy agents

### 5. test-scheduler - Scheduling System

**Commands**: `get log`, `clear log`, `log message: [text]`, `status`
**Log Format**: `[timestamp] [SCHEDULED|MANUAL] [message]`

**Tests**:
- Schedule creation
- Cron execution
- Execution history
- Manual trigger
- Source differentiation

### 6. test-queue - Execution Queue

**Commands**: `delay [N]`, `quick`, `status`, `busy [N]`

**Tests**:
- Serial execution
- Queue position tracking
- 429 when queue full
- Queue status API
- Defense-in-depth

### 7. test-files - File Browser

**Commands**: `create [file]: [content]`, `read [file]`, `list`, `create-tree`, `delete [file]`, `large [N]`, `hidden`

**Tests**:
- File listing API
- File download API
- Directory traversal
- Hidden file filtering
- File size limits (100MB)

### 8. test-error - Error Handling

**Commands**: `normal`, `fail`, `exception`, `slow [N]`, `empty`, `large`, `malformed`

**Tests**:
- Failed execution tracking
- Activity state (failed)
- Response truncation
- Timeout handling
- Error recovery

---

## Multi-Agent Test Scenarios

### Scenario 1: Basic Collaboration (VERIFIED 2025-12-08)
```
Setup: test-delegator + test-echo

1. Start both agents
2. Send to delegator: "delegate to test-echo: Hello World"
3. Verify: Echo response received, Dashboard shows collaboration event
```

### Scenario 2: Queue Under Load
```
Setup: test-queue

1. Send 5 simultaneous "delay 30" requests
2. Expected:
   - 1 request runs immediately
   - 3 requests queue (queue size = 3)
   - 1 request returns 429
3. Verify via GET /api/agents/test-queue/queue
```

### Scenario 3: Workplan Lifecycle
```
Setup: test-worker

1. "create plan: Integration Test" -> Plan created with 3 tasks
2. Dashboard shows plan visibility
3. "complete task: task-1" -> task-2 unblocks
4. Complete remaining tasks -> Plan archives
```

### Scenario 4: Scheduled Delegation
```
Setup: test-delegator + test-counter

1. Reset counter in test-counter
2. Create schedule: "delegate to test-counter: increment" every minute
3. Wait 3 minutes
4. Verify counter = 3, collaboration events logged
```

---

## Testing

### Prerequisites
- [x] Backend running at http://localhost:8000
- [x] Frontend running at http://localhost:3000
- [x] Docker daemon running
- [x] GitHub PAT configured for private repos

### Test: Template Discovery

1. Navigate to Templates page (`/templates`)
2. **Expected**: 8 test agents appear in GitHub templates section
3. **Verify**: Each shows "Test:" prefix in display name

### Test: Create Test Agent

1. Click "Use Template" on test-echo
2. Enter name: "my-test-echo"
3. Click "Create"
4. **Expected**: Agent created and starts automatically
5. **Verify**: Agent appears in agents list with "running" status

### Test: Echo Response (PASSED 2025-12-08)

1. Navigate to my-test-echo detail page
2. Send message: "Hello World"
3. **Expected Response**:
   ```
   Echo: Hello World
   Words: 2
   Characters: 11
   ```

### Test: Counter Persistence (PASSED 2025-12-08)

1. Create test-counter agent
2. Send: "reset" -> Counter: 0
3. Send: "increment" -> Counter: 1
4. Send: "add 10" -> Counter: 11
5. **Verify**: File browser shows counter.txt

### Test: Workplan Creation (PARTIAL)

1. Create test-worker agent
2. Send: "create plan: Test"
3. **Verify**: Plans tab shows new plan with 3 tasks
4. Dashboard shows plan in AgentNode

> **Note**: Slash command parsing not yet in test-worker CLAUDE.md

### Test: Agent Collaboration (PASSED 2025-12-08)

1. Create test-delegator and test-echo
2. Ensure both running
3. Send to delegator: "delegate to test-echo: ping"
4. **Verify**:
   - Response includes echo output
   - Dashboard shows collaboration edge animation

### Edge Cases

- [ ] Create agent when GitHub repo unavailable
- [ ] Delegate to stopped agent (should fail gracefully)
- [ ] Queue full (send 5+ "delay 60" to test-queue)
- [ ] Access denied (delegate to agent owned by different user)

### Cleanup

```bash
# Delete all test agents
docker rm -f $(docker ps -a --filter "name=test-" --format "{{.Names}}")
```

---

## Repository Structure

Each test agent repository:
```
test-agent-{name}/
  template.yaml      # Trinity metadata
  CLAUDE.md          # Agent instructions
  README.md          # Human documentation
  .gitignore         # Ignore .env, .mcp.json
```

### GitHub Repositories

| Agent | URL | Status |
|-------|-----|--------|
| test-echo | https://github.com/Abilityai/test-agent-echo | Local only |
| test-counter | https://github.com/Abilityai/test-agent-counter | Local only |
| test-worker | https://github.com/Abilityai/test-agent-worker | Local only |
| test-delegator | https://github.com/Abilityai/test-agent-delegator | Local only |
| test-scheduler | https://github.com/Abilityai/test-agent-scheduler | Local only |
| test-queue | https://github.com/Abilityai/test-agent-queue | Local only |
| test-files | https://github.com/Abilityai/test-agent-files | Local only |
| test-error | https://github.com/Abilityai/test-agent-error | Local only |

> **Action Required**: Push local repositories to GitHub to enable GitHub-based template cloning.

---

## Related Documentation

- **Design Document**: `docs/TESTING_AGENTS_DESIGN.md`
- **Testing Guide**: `docs/TESTING_GUIDE.md`
- **Agent Lifecycle**: `feature-flows/agent-lifecycle.md`
- **Workplan System**: `feature-flows/workplan-system.md`
- **Agent Network**: `feature-flows/agent-network.md`

---

## Revision History

| Date | Changes |
|------|---------|
| 2025-12-07 | Initial implementation - 8 test agents designed and 4 configured |
| 2025-12-08 | All 8 test agents configured in `config.py` (added test-scheduler, test-queue, test-files, test-error) |
| 2025-12-08 | Test results: test-echo PASSED, test-counter PASSED, test-worker PARTIAL, test-delegator PASSED |
| 2025-12-08 | Verified Trinity MCP integration with test-delegator successfully delegating to test-echo |
| 2025-12-08 | All 8 local repositories created in `repositories/` folder |
| 2025-12-08 | Full system test via UI - test-echo, test-counter, test-delegator all PASSED |
| 2025-12-08 | Dashboard collaboration edges verified - "6x" message count label visible |
| 2025-12-08 | Documented known issues: Template pre-selection bug, session expiration |
