# Terminology Clarity Refactor (Option A)

> **Created**: 2025-12-07
> **Status**: Planning
> **Purpose**: Rename confusing terminology to make the distinction between single-agent task planning and multi-agent communication clearer to users.

---

## Problem Statement

Users are confused about whether "Task DAG" refers to:
1. **Multi-agent orchestration** - How multiple agents collaborate in a workflow
2. **Single-agent task planning** - How ONE agent breaks down its work internally

**Current Reality**:
- "Task DAG Plans" = Single-agent internal task breakdown (Pillar I: Explicit Planning)
- "Collaboration Dashboard" = Multi-agent communication visualization (who talks to whom)

These are **two separate, unconnected concepts** in the current implementation, but the terminology suggests they might be related.

---

## Proposed Terminology Changes

### Concept 1: Single-Agent Task Planning

| Current Term | New Term | Rationale |
|--------------|----------|-----------|
| "Task DAG" | **"Workplan"** | Clear that it's a plan for work, avoids jargon |
| "Task DAG System" | **"Workplan System"** | Consistent |
| "Task DAG Plans" | **"Agent Workplans"** | Explicitly per-agent |
| "Plans" (tab name) | **"Workplan"** | Singular, cleaner |
| "Plans Panel" | **"Workplan Panel"** | Component name |
| `/trinity-plan-*` commands | **`/workplan-*`** | User-facing commands |

### Concept 2: Multi-Agent Communication

| Current Term | New Term | Rationale |
|--------------|----------|-----------|
| "Collaboration Dashboard" | **"Agent Network"** | Emphasizes connections, not workflows |
| "Collaboration" (nav link) | **"Network"** | Shorter, clearer |
| "collaborations.js" | **"network.js"** | Store name |
| "agent_collaboration" (event type) | **"agent_communication"** | More accurate |
| "collaboration edge" | **"communication edge"** | Edge terminology |

---

## Files to Change

### Phase 1: Frontend UI Text (User-Facing)

These changes affect what users see in the UI.

#### 1.1 Navigation & Tab Labels

| File | Line | Current | New |
|------|------|---------|-----|
| `src/frontend/src/components/NavBar.vue` | ~45 | "Collaboration" | "Network" |
| `src/frontend/src/views/AgentDetail.vue` | 263-273 | "Plans" tab | "Workplan" tab |
| `src/frontend/src/router/index.js` | ~52 | `/collaboration` route name | `/network` route |

#### 1.2 Page Titles & Headers

| File | Location | Current | New |
|------|----------|---------|-----|
| `AgentCollaboration.vue` | Header | "Agent Collaboration" | "Agent Network" |
| `PlansPanel.vue` | Title | "Plans" references | "Workplan" references |

#### 1.3 Empty States & Help Text

| File | Location | Current | New |
|------|----------|---------|-----|
| `PlansPanel.vue` | Empty state | "No plans yet" | "No workplan yet" |
| `PlansPanel.vue` | Help text | "/plan commands" | "/workplan commands" |
| `AgentCollaboration.vue` | Empty state | "collaboration" references | "communication" references |

#### 1.4 Status Labels & Badges

| File | Location | Current | New |
|------|----------|---------|-----|
| `PlansPanel.vue` | Summary stats | "Total Plans", "Active" | "Workplan", "Active Tasks" |
| `AgentNode.vue` | Task display | "Tasks" label | Keep as "Tasks" (fine) |

---

### Phase 2: Frontend Code (Internal)

These changes affect code organization and variable names.

#### 2.1 Store Renaming

| Current File | New File | Changes |
|--------------|----------|---------|
| `stores/collaborations.js` | `stores/network.js` | Rename file |

**Internal Variables to Rename**:
```javascript
// In network.js (was collaborations.js)
collaborationHistory → communicationHistory
activeCollaborations → activeCommunications
totalCollaborationCount → totalCommunicationCount
historicalCollaborations → historicalCommunications
fetchHistoricalCollaborations() → fetchHistoricalCommunications()
handleCollaborationEvent() → handleCommunicationEvent()
```

#### 2.2 Store Imports

Update all files that import the store:
- `AgentCollaboration.vue` → `AgentNetwork.vue`
- `App.vue` (if applicable)
- Any other consumers

#### 2.3 Component Renaming

| Current File | New File |
|--------------|----------|
| `views/AgentCollaboration.vue` | `views/AgentNetwork.vue` |
| `components/PlansPanel.vue` | `components/WorkplanPanel.vue` |

#### 2.4 agents.js Store

```javascript
// Current
planStats → workplanStats
fetchPlanStats() → fetchWorkplanStats()
getAgentPlans() → getAgentWorkplan()
getAgentPlansSummary() → getAgentWorkplanSummary()
// etc.
```

---

### Phase 3: Backend API (Careful - Breaking Change)

**Option A: Keep API paths, change display names only**
- Less work, no API breaking changes
- Frontend just displays different labels
- Recommended for now

**Option B: Full API rename (future)**
- `/api/agents/{name}/plans` → `/api/agents/{name}/workplan`
- `/api/activities` with `activity_type=agent_collaboration` → `agent_communication`
- Requires versioning or migration period

**Recommendation**: Start with Option A (display names only), do Option B in a future release with proper deprecation.

---

### Phase 4: Trinity Meta-Prompt Commands

These are the slash commands agents use to create workplans.

| Current | New | File |
|---------|-----|------|
| `/trinity-plan-create` | `/workplan-create` | `config/trinity-meta-prompt/commands/` |
| `/trinity-plan-status` | `/workplan-status` | |
| `/trinity-plan-update` | `/workplan-update` | |
| `/trinity-plan-list` | `/workplan-list` | |

**Files to Update**:
- `config/trinity-meta-prompt/commands/trinity-plan-create.md` → `workplan-create.md`
- `config/trinity-meta-prompt/commands/trinity-plan-status.md` → `workplan-status.md`
- `config/trinity-meta-prompt/commands/trinity-plan-update.md` → `workplan-update.md`
- `config/trinity-meta-prompt/commands/trinity-plan-list.md` → `workplan-list.md`
- `config/trinity-meta-prompt/prompt.md` - Update references

---

### Phase 5: Documentation Updates

| Document | Changes |
|----------|---------|
| `CLAUDE.md` | Update "Pillar I" description, terminology |
| `requirements.md` | Update all "Task DAG" → "Workplan" references |
| `architecture.md` | Update system design terminology |
| `feature-flows/task-dag-system.md` | Rename to `workplan-system.md`, update content |
| `feature-flows/plans-ui.md` | Rename to `workplan-ui.md`, update content |
| `feature-flows/collaboration-dashboard.md` | Rename to `agent-network.md`, update content |
| `feature-flows.md` | Update index |
| `roadmap.md` | Update task references |
| `changelog.md` | Add entry for terminology refactor |

---

## UI Mockups (Before/After)

### Navigation Bar

**Before**:
```
Trinity | Dashboard | Agents | Credentials | Templates | MCP Keys | Collaboration
```

**After**:
```
Trinity | Dashboard | Agents | Credentials | Templates | MCP Keys | Network
```

### Agent Detail Tabs

**Before**:
```
[ Chat ] [ Activity ] [ Logs ] [ Executions ] [ Plans ] [ Git ] [ Files ] [ Info ]
```

**After**:
```
[ Chat ] [ Activity ] [ Logs ] [ Executions ] [ Workplan ] [ Git ] [ Files ] [ Info ]
```

### Workplan Panel Header

**Before**:
```
Plans
Total Plans: 3 | Active: 1 | Completed: 2 | Total Tasks: 12 | Task Progress: 75%
```

**After**:
```
Workplan
Total: 3 | Active: 1 | Completed: 2 | Tasks: 12 | Progress: 75%
```

### Agent Network Page Header

**Before**:
```
Agent Collaboration
6 agents - 2 active - 15 total (24h)
```

**After**:
```
Agent Network
6 agents - 2 active communications - 15 total (24h)
```

---

## Tooltips & Help Text

Add clarifying tooltips to help users understand each concept:

### Workplan Tab Tooltip
> "This agent's internal task breakdown. Shows how the agent has organized its work into steps."

### Network Page Tooltip
> "Shows when agents communicate with each other. Lines appear when one agent sends a message to another."

### Current Task (in Agents list)
> "The task this agent is currently working on from its workplan."

---

## Implementation Order

### Sprint 1: Quick Wins (UI Labels Only)
1. Change nav link "Collaboration" → "Network"
2. Change tab name "Plans" → "Workplan"
3. Change page title "Agent Collaboration" → "Agent Network"
4. Update empty states and help text
5. Add tooltips for clarity

**Estimated effort**: 1-2 hours
**Risk**: Low (no breaking changes)

### Sprint 2: Component & Store Renaming
1. Rename `PlansPanel.vue` → `WorkplanPanel.vue`
2. Rename `AgentCollaboration.vue` → `AgentNetwork.vue`
3. Rename `collaborations.js` → `network.js`
4. Update all imports and references

**Estimated effort**: 2-3 hours
**Risk**: Medium (file renames, import updates)

### Sprint 3: Command Renaming
1. Rename Trinity meta-prompt commands
2. Update prompt.md references
3. Rebuild base image
4. Test with agents

**Estimated effort**: 1-2 hours
**Risk**: Medium (affects agent behavior)

### Sprint 4: Documentation
1. Update all feature flows
2. Update requirements.md
3. Update architecture.md
4. Update CLAUDE.md

**Estimated effort**: 2-3 hours
**Risk**: Low

### Sprint 5 (Future): API Rename
1. Add new API endpoints with new names
2. Deprecate old endpoints
3. Migration period
4. Remove old endpoints

**Estimated effort**: 4-6 hours
**Risk**: High (breaking change for integrations)

---

## Testing Checklist

### After Sprint 1
- [ ] "Network" link navigates to agent network page
- [ ] "Workplan" tab shows workplan panel
- [ ] Page titles display correctly
- [ ] Tooltips appear on hover

### After Sprint 2
- [ ] All component imports resolve
- [ ] Store actions work correctly
- [ ] No console errors
- [ ] Hot reload works

### After Sprint 3
- [ ] `/workplan-create` command works in agents
- [ ] Old `/trinity-plan-*` commands still work (or show helpful error)
- [ ] Plans/workplans are created correctly

### After Sprint 4
- [ ] Documentation is consistent
- [ ] No references to old terminology
- [ ] Feature flows are updated

---

## Rollback Plan

If issues arise:
1. **Sprint 1**: Revert text changes (simple find/replace)
2. **Sprint 2**: Git revert file renames
3. **Sprint 3**: Restore old command files, rebuild base image
4. **Sprint 4**: Git revert documentation changes

---

## Success Metrics

1. **User Clarity**: Users can explain the difference between Workplan and Network
2. **No Support Questions**: Reduced confusion about what "Task DAG" means
3. **Consistent Terminology**: All UI, docs, and code use same terms

---

## Open Questions

1. Should we keep "DAG" anywhere for technical users? (e.g., in docs only)
2. Should the route be `/network` or `/agent-network`?
3. Should workplan commands be `/workplan-*` or `/plan-*`?
4. Do we need a migration for existing plans stored as `plans/` directory?

---

## Approval

- [ ] Product Owner approval for terminology changes
- [ ] Engineering review of implementation plan
- [ ] Documentation review

---

## References

- Feature Flow: [task-dag-system.md](feature-flows/task-dag-system.md)
- Feature Flow: [plans-ui.md](feature-flows/plans-ui.md)
- Feature Flow: [collaboration-dashboard.md](feature-flows/collaboration-dashboard.md)
- Requirements: [requirements.md](requirements.md) Section 9
