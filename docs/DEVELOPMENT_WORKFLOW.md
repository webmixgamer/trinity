# Trinity Development Workflow

> **For developers and AI assistants** working on the Trinity platform.
> This guide explains how to use the project's tools, agents, and documentation effectively.

---

## The Development Cycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                     TRINITY DEVELOPMENT CYCLE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   1. CONTEXT LOADING                                                │
│      ↓                                                              │
│   /read-docs → Load requirements, architecture, roadmap             │
│      ↓                                                              │
│   Read relevant feature-flows/* for the area you'll work on         │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   2. DEVELOPMENT                                                    │
│      ↓                                                              │
│   Implement changes following existing patterns                     │
│      ↓                                                              │
│   Reference feature flows for data flow understanding               │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   3. TESTING                                                        │
│      ↓                                                              │
│   test-runner agent → API tests (required)                          │
│      ↓                                                              │
│   ui-integration-tester agent → UI tests (recommended)              │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   4. DOCUMENTATION                                                  │
│      ↓                                                              │
│   feature-flow-analyzer agent → Create/update feature flows         │
│      ↓                                                              │
│   /update-docs → Update changelog, architecture, requirements       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Context Loading

**Always start a development session by loading context.**

### Option A: Full Context Load (New Session)

Use the `/read-docs` command:

```
/read-docs
```

This loads:
- `docs/memory/requirements.md` - Feature requirements (source of truth)
- `docs/memory/architecture.md` - System design
- `docs/memory/roadmap.md` - Current priorities
- `docs/memory/changelog.md` - Recent changes (last 150 lines)
- `docs/TESTING_GUIDE.md` - Testing approach

### Option B: Targeted Context (Specific Feature Work)

If you know what you're working on, load the relevant feature flow directly:

```
# Example: Working on agent chat
@docs/memory/feature-flows/agent-chat.md

# Example: Working on credentials
@docs/memory/feature-flows/credential-injection.md
```

Or ask Claude Code to read specific flows:

```
Read the feature flow for workplan-system before we start
```

### Available Feature Flows

| Feature Area | Flow Document |
|--------------|---------------|
| Agent CRUD | `agent-lifecycle.md` |
| Chat/Messaging | `agent-chat.md` |
| Credentials | `credential-injection.md` |
| Authentication | `auth0-authentication.md` |
| Agent Network | `agent-network.md` |
| Workplans | `workplan-system.md`, `workplan-ui.md` |
| Scheduling | `scheduling.md` |
| Execution Queue | `execution-queue.md` |
| File Browser | `file-browser.md` |
| Activity Stream | `activity-stream.md` |
| MCP Tools | `mcp-orchestration.md` |
| Agent Sharing | `agent-sharing.md` |
| Templates | `template-processing.md` |
| Collaboration | `agent-to-agent-collaboration.md` |

See `docs/memory/feature-flows.md` for the complete index.

---

## Phase 2: Development

### Before Writing Code

1. **Check requirements**: Does `requirements.md` cover this feature?
2. **Check roadmap**: Is this the current priority?
3. **Read feature flow**: Understand existing data flow before modifying

### During Development

- Follow patterns established in existing code
- Reference feature flows for:
  - API endpoint locations
  - Database operations
  - WebSocket events
  - Error handling patterns
- Use the TodoWrite tool to track multi-step tasks

### Key Files Reference

| Layer | Key Files |
|-------|-----------|
| Frontend | `src/frontend/src/views/*.vue`, `src/frontend/src/stores/*.js` |
| Backend | `src/backend/main.py`, `src/backend/database.py` |
| Agent | `docker/base-image/agent-server.py` |
| MCP | `src/mcp-server/src/index.ts` |

---

## Phase 3: Testing

**Every development session must end with testing.**

### Minimum: API Tests

Use the `test-runner` agent:

```
Run the API tests
```

This runs the pytest suite at `tests/` and reports:
- Pass/fail counts
- Failure analysis
- Recommendations

**Test Tiers:**
- **Smoke tests** (~30s): Quick validation - `pytest -m smoke`
- **Core tests** (~3-5min): Standard validation - `pytest -m "not slow"` (default)
- **Full suite** (~5-8min): Comprehensive - `pytest -v`

### Recommended: UI Integration Tests

Use the `ui-integration-tester` agent:

```
Run UI integration test phase 2 (agent creation)
```

Phases 0-12 cover the full platform. See `docs/testing/phases/INDEX.md`.

### Manual Verification

For quick checks during development:

```bash
# Backend running?
curl http://localhost:8000/api/health

# Frontend running?
curl http://localhost:3000

# Test specific endpoint
curl http://localhost:8000/api/agents
```

---

## Phase 4: Documentation

**After tests pass, update documentation.**

### If You Modified Feature Behavior

**Use the `feature-flow-analyzer` agent:**

```
Analyze and update the feature flow for agent-chat
```

Or use the command:

```
/feature-flow-analysis agent-chat
```

This will:
1. Trace the feature from UI → Backend → Agent
2. Update or create `docs/memory/feature-flows/{feature}.md`
3. Update the feature flows index

### For All Changes

**Use the `/update-docs` command:**

```
/update-docs
```

Claude Code will determine which documents need updates:

| Document | When to Update |
|----------|----------------|
| `changelog.md` | Always - add timestamped entry |
| `architecture.md` | API changes, schema changes, new integrations |
| `requirements.md` | New features, scope changes |
| `roadmap.md` | Task completion, new discoveries |
| `feature-flows/*.md` | Behavior changes (use analyzer) |

---

## Sub-Agents Reference

### When to Use Each Agent

| Agent | Use When |
|-------|----------|
| `test-runner` | After development to validate changes |
| `ui-integration-tester` | For comprehensive UI/UX validation |
| `feature-flow-analyzer` | After modifying feature behavior |
| `agent-template-validator` | When creating/modifying agent templates |
| `security-analyzer` | Before commits touching auth, credentials, or APIs |

### Invoking Agents

Agents are invoked automatically by Claude Code when appropriate, or you can request them:

```
# Run tests
Use the test-runner agent to run the API tests

# Analyze a feature
Use the feature-flow-analyzer to document the scheduling feature

# UI testing
Run phase 3 of the UI integration tests
```

---

## Slash Commands Reference

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/read-docs` | Load project context | Start of session |
| `/update-docs` | Update documentation | After changes |
| `/feature-flow-analysis <feature>` | Document feature flow | After modifying features |
| `/security-check` | Validate no secrets in staged files | Before every commit |
| `/agent-status` | Check agent states | Debugging |
| `/deploy-status` | Check deployment | Before/after deploy |
| `/add-testing` | Add tests for a feature | Improving coverage |

---

## Memory Files Explained

The `.claude/memory/` and `docs/memory/` directories contain persistent project state:

```
docs/memory/
├── requirements.md      ← SINGLE SOURCE OF TRUTH for features
├── architecture.md      ← Current system design (~1000 lines max)
├── roadmap.md           ← Prioritized task queue
├── changelog.md         ← Timestamped history (~500 lines)
├── feature-flows.md     ← Index of all feature flow documents
└── feature-flows/       ← Individual feature documentation
    ├── agent-lifecycle.md
    ├── agent-chat.md
    ├── credential-injection.md
    └── ... (25+ flows)
```

### How They Work Together

```
requirements.md  ──defines──►  What features exist
       │
       ▼
roadmap.md       ──prioritizes──►  What to work on next
       │
       ▼
feature-flows/*  ──documents──►  How features work
       │
       ▼
changelog.md     ──records──►  What changed and when
       │
       ▼
architecture.md  ──maintains──►  Current system state
```

---

## Example Development Session

### Scenario: Add a new field to agent chat

```
# 1. CONTEXT LOADING
You: /read-docs
You: Also read the agent-chat feature flow

# 2. DEVELOPMENT
You: Add a "priority" field to chat messages that shows in the UI

Claude: [Reads feature flow, implements changes across frontend/backend]

# 3. TESTING
You: Run the API tests to make sure nothing broke

Claude: [Invokes test-runner agent, reports results]

# 4. DOCUMENTATION
You: Update the feature flow for agent-chat and update docs

Claude: [Invokes feature-flow-analyzer, then /update-docs]
```

### Scenario: Fix a bug in credential injection

```
# 1. CONTEXT LOADING
You: @docs/memory/feature-flows/credential-injection.md
You: The hot-reload isn't working for .env changes

# 2. DEVELOPMENT
Claude: [Reads flow, traces issue, implements fix]

# 3. TESTING
You: Test it

Claude: [Runs relevant tests, verifies fix]

# 4. DOCUMENTATION
You: Update the docs

Claude: [Updates changelog, possibly updates feature flow if behavior changed]
```

---

## Best Practices

### DO

- ✅ Always load context before starting work
- ✅ Read feature flows before modifying features
- ✅ Run tests after every significant change
- ✅ Update feature flows when behavior changes
- ✅ Use sub-agents for specialized tasks
- ✅ Keep changelog entries concise but informative

### DON'T

- ❌ Skip context loading ("I remember from last time")
- ❌ Modify features without reading their flow
- ❌ Commit without running tests
- ❌ Leave feature flows outdated after changes
- ❌ Write new documentation files without being asked
- ❌ Over-document - keep it minimal and useful

---

## Quick Start Checklist

For every development session:

- [ ] Load context (`/read-docs` or read relevant feature flows)
- [ ] Understand what you're modifying (read the feature flow)
- [ ] Implement changes
- [ ] Run API tests (`test-runner` agent)
- [ ] Run UI tests if applicable (`ui-integration-tester` agent)
- [ ] Update feature flow if behavior changed (`feature-flow-analyzer` agent)
- [ ] Update documentation (`/update-docs`)
- [ ] Run security check before commit (`/security-check`)

---

## See Also

- `CONTRIBUTING.md` - How to contribute (PRs, commits, code standards)
- `CLAUDE.md` - Project overview and rules
- `docs/TESTING_GUIDE.md` - Detailed testing approach
- `docs/memory/feature-flows.md` - Feature flow index
- `docs/testing/phases/INDEX.md` - UI test phases
