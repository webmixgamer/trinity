# Process-Driven Platform - Onboarding Backlog

> **Phase**: MVP+ / Core
> **Goal**: Premium onboarding experience for new users
> **Epics**: E20, E21, E22, E23, E24
> **Stories**: 21
> **Reference**: See [`BACKLOG_INDEX.md`](./BACKLOG_INDEX.md) for conventions

---

## Sprint Plan

| Sprint | Stories | Focus |
|--------|---------|-------|
| **Sprint 7** | E20-01, E20-02, E21-04 | Quick wins + Getting Started content ✅ |
| **Sprint 8** | E21-01, E21-02, E21-05, E21-06, E20-05 | Docs tab foundation ✅ |
| **Sprint 8.5** | E21-07, E21-08, E21-09 | Pattern docs + Learning path |
| **Sprint 9** | E22-01, E22-03, E20-03, E20-04 | Contextual help |
| **Sprint 10** | E23-01, E23-02, E21-03 | Tours + search |
| **Sprint 11** | E24-01, E24-02, E24-03, E24-04 | First Process Wizard |

---

## Dependency Graph

```
E20-01 (Empty State)
  │
  ├──► E20-03 (Template Cards) ──► E24-01 (Wizard Shell)
  │                                      │
  │                                      └──► E24-02, E24-03, E24-04
  │
  └──► E20-02 (Checklist) ──► E20-04 (First-Run Detection)
                                  │
                                  └──► E20-05 (UX Polish) ✅

E21-04 (Getting Started Content)
  │
  └──► E21-01 (Docs Route) ──► E21-02 (Docs View)
                                    │
                                    ├──► E21-03 (Search)
                                    │
                                    ├──► E21-05, E21-06 (Reference Content) ✅
                                    │         │
                                    │         └──► E21-08 (Missing Step Types)
                                    │
                                    └──► E21-07 (Pattern Docs)
                                              │
                                              └──► E21-09 (Learning Path)

E21-02 (Docs View)
  │
  └──► E22-01 (Editor Help Panel) ──► E22-02 (Tooltips)
                                            │
                                            └──► E22-03 (Status Explainers)

E23-01 (Driver.js Integration)
  │
  └──► E23-02 (First Tour) ──► E23-03 (Mini-Tours)
```

---

## Epic E20: Empty States and Quick Wins

> First impressions matter. Transform generic empty states into helpful onboarding entry points.

---

### E20-01: Enhanced Empty State for Process List

**As a** new user, **I want** a helpful empty state when I have no processes, **so that** I understand what processes are and how to get started.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P0 |
| Phase | MVP+ |
| Dependencies | None |
| Status | done |

**Acceptance Criteria:**
- [ ] Empty state shows welcoming illustration/icon with message
- [ ] Value proposition text: "Processes automate multi-step workflows using your AI agents"
- [ ] Primary CTA "Create Your First Process" button links to `/processes/new`
- [ ] Secondary text "New to Processes?" with link placeholder for docs
- [ ] Design matches existing Trinity aesthetic (indigo accent, dark mode support)
- [ ] Responsive layout for mobile/tablet

**Technical Notes:**
- Location: `src/frontend/src/views/ProcessList.vue` (lines 196-210)
- Reference: PROCESS_ENGINE_ROADMAP.md Phase 6.3
- Replace current generic empty state with enhanced version

---

### E20-02: Onboarding Progress Checklist

**As a** new user, **I want** to see my setup progress, **so that** I know what steps remain to fully utilize the platform.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Phase | MVP+ |
| Dependencies | None |
| Status | done |

**Acceptance Criteria:**
- [ ] Checklist component shows 5 key milestones:
  - [ ] Create your first process
  - [ ] Run a process execution
  - [ ] Monitor an execution
  - [ ] (Optional) Set up a schedule
  - [ ] (Optional) Configure an approval workflow
- [ ] Checklist persists in localStorage (survives refresh)
- [ ] Auto-detects completion (e.g., process count > 0 = first item done)
- [ ] Dismissible after all required items complete
- [ ] Collapsible/expandable UI
- [ ] Progress indicator (e.g., "2 of 3 complete")

**Technical Notes:**
- New composable: `src/frontend/src/composables/useOnboarding.js`
- New component: `src/frontend/src/components/OnboardingChecklist.vue`
- LocalStorage key: `trinity_onboarding_${userId}`
- Auto-detection via API calls to check process/execution counts

---

### E20-03: Template Cards in Empty State

**As a** new user, **I want** quick-start template options, **so that** I can create my first process without starting from scratch.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P1 |
| Phase | MVP+ |
| Dependencies | E20-01 |
| Status | pending |

**Acceptance Criteria:**
- [ ] 3 template cards displayed in empty state:
  - Content Pipeline (research → write → review)
  - Data Report (gather → analyze → report)
  - Support Escalation (triage → route → resolve)
- [ ] Each card shows: name, brief description, step count
- [ ] Click loads template YAML into editor
- [ ] Templates sourced from `config/process-templates/`

**Technical Notes:**
- Leverage existing templates: `content-review/`, `data-analysis/`, `customer-support/`
- API endpoint may be needed: `GET /api/processes/templates`
- Or load client-side from static JSON

---

### E20-04: First-Run Detection Service

**As a** developer, **I want** reliable first-run detection, **so that** onboarding features trigger appropriately.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P1 |
| Phase | MVP+ |
| Dependencies | E20-02 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Composable provides `isFirstRun` computed property
- [ ] Detects: no processes created yet, onboarding not dismissed
- [ ] Exposes methods: `markOnboardingComplete()`, `resetOnboarding()`
- [ ] Works with localStorage + optional API backup

**Technical Notes:**
- Part of `useOnboarding.js` composable
- Can check `processesStore.processes.length === 0` for process detection
- Consider backend flag in `system_settings` for multi-device sync (optional)

---

### E20-05: Onboarding UX Polish

**As a** user, **I want** context-aware checklist guidance and ability to restart onboarding, **so that** I get relevant help without confusion.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P1 |
| Phase | MVP+ |
| Dependencies | E20-02 |
| Status | done |

**Acceptance Criteria:**
- [x] Show inline hint instead of "Start" when already on target page
- [x] "Restart Onboarding" button on Docs page sidebar
- [x] Confirmation dialog before restart
- [x] Remove hidden keyboard shortcut (replaced by UI option)

**Technical Notes:**
- Location: `src/frontend/src/components/OnboardingChecklist.vue`
- Location: `src/frontend/src/views/ProcessDocs.vue`
- Use existing `resetOnboarding()` from `useOnboarding.js` composable
- Show "See above ↑" with amber color when on target page instead of "Start →"

---

## Epic E21: Documentation Tab

> In-app documentation reduces friction and helps users self-serve.

---

### E21-01: Docs Route and Navigation

**As a** user, **I want** a Docs tab in the Processes section, **so that** I can access documentation without leaving the app.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P1 |
| Phase | MVP+ |
| Dependencies | None |
| Status | done |

**Acceptance Criteria:**
- [ ] New route: `/processes/docs` added to router
- [ ] ProcessSubNav shows "Docs" tab with BookOpenIcon
- [ ] Tab positioned between Dashboard and Executions
- [ ] Active state styling when on docs route
- [ ] Route requires authentication

**Technical Notes:**
- Location: `src/frontend/src/router/index.js`
- Location: `src/frontend/src/components/ProcessSubNav.vue`
- Import `BookOpenIcon` from `@heroicons/vue/24/outline`

---

### E21-02: ProcessDocs View with Markdown Rendering

**As a** user, **I want** to browse documentation with a sidebar and content area, **so that** I can easily navigate and read help content.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | MVP+ |
| Dependencies | E21-01 |
| Status | done |

**Acceptance Criteria:**
- [ ] Left sidebar with collapsible navigation tree
- [ ] Main content area renders Markdown
- [ ] Code blocks have syntax highlighting (YAML focus)
- [ ] Copy-to-clipboard button for code snippets
- [ ] Responsive: sidebar collapses on mobile
- [ ] Dark mode support
- [ ] Loading state while fetching content

**Technical Notes:**
- New view: `src/frontend/src/views/ProcessDocs.vue`
- Markdown library: `marked` + `highlight.js` (or `vue-markdown-render`)
- Content loaded from static files or API
- Consider lazy-loading content per section

---

### E21-03: Documentation Search

**As a** user, **I want** to search documentation, **so that** I can quickly find relevant information.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | MVP+ |
| Dependencies | E21-02 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Search input at top of docs sidebar
- [ ] Fuzzy search across all doc titles and content
- [ ] Results show matching doc title + snippet
- [ ] Click result navigates to that doc
- [ ] Keyboard shortcut (Cmd/Ctrl+K) to focus search
- [ ] "No results" state with suggestions

**Technical Notes:**
- Client-side search using pre-built index
- Consider `fuse.js` for fuzzy matching
- Index built at build time or on first load

---

### E21-04: Getting Started Content

**As a** new user, **I want** clear getting started documentation, **so that** I can learn the basics quickly.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Phase | MVP+ |
| Dependencies | None |
| Status | done |

**Acceptance Criteria:**
- [ ] Document: "What are Processes?" (~300 words)
  - Explains process automation concept
  - Shows simple diagram of steps
  - Lists benefits
- [ ] Document: "Your First Process" (~500 words)
  - 5-minute tutorial
  - Step-by-step with screenshots/code
  - Creates a simple 2-step process
- [ ] Documents stored in `config/process-docs/getting-started/`
- [ ] Markdown format with YAML code blocks

**Technical Notes:**
- Files: `what-are-processes.md`, `first-process.md`
- Include copy-paste YAML examples
- Reference actual Trinity UI elements

---

### E21-05: Step Types Reference Content

**As a** process designer, **I want** reference documentation for each step type, **so that** I know how to configure them correctly.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | MVP+ |
| Dependencies | E21-02 |
| Status | done |

**Acceptance Criteria:**
- [ ] Document: "Understanding Step Types" (~400 words)
  - Overview of all step types
  - When to use each
- [ ] Individual reference for each type:
  - `agent_task` - agent execution
  - `human_approval` - approval gates
  - `gateway` - conditional branching
  - `timer` - delays and waits
- [ ] Each reference includes: description, required fields, optional fields, example YAML

**Technical Notes:**
- File: `config/process-docs/getting-started/step-types.md`
- Or split into `config/process-docs/reference/step-types/` folder
- Include validation rules and common errors

---

### E21-06: YAML Schema Reference Content

**As a** process designer, **I want** complete YAML schema documentation, **so that** I can write valid process definitions.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | MVP+ |
| Dependencies | E21-02 |
| Status | done |

**Acceptance Criteria:**
- [ ] Document: "Process Definition Schema" (~800 words)
  - Full schema reference
  - Required vs optional fields
  - Field types and constraints
- [ ] Document: "Variable Interpolation" (~400 words)
  - `{{input.x}}` syntax
  - `{{steps.x.output}}` syntax
  - Available context variables
- [ ] Document: "Triggers" (~300 words)
  - Manual, webhook, schedule triggers
  - Trigger configuration options
- [ ] Document: "Error Handling" (~300 words)
  - Retry configuration
  - Timeout handling
  - Error boundaries

**Technical Notes:**
- Files in `config/process-docs/reference/`
- Cross-link between documents
- Include JSON Schema excerpt where helpful

---

### E21-07: Pattern Documentation

**As a** process designer, **I want** documented common patterns with examples, **so that** I can learn from proven workflow designs.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | MVP+ |
| Dependencies | E21-02 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Document: "Sequential Workflows" (~400 words)
  - Linear step chains with depends_on
  - Data flow between steps
  - Error handling in chains
  - Complete YAML example
- [ ] Document: "Parallel Execution" (~500 words)
  - Fork/join pattern
  - Fan-out / fan-in pattern
  - Diamond pattern with diagram
  - Aggregating results from parallel steps
  - YAML examples for each pattern
- [ ] Document: "Approval Workflows" (~500 words)
  - Single approval gate
  - Multi-level approval chains
  - Conditional paths after approval/rejection
  - Timeout handling strategies
  - Complete content review pipeline example

**Technical Notes:**
- Files in `config/process-docs/patterns/`
- Create directory if missing
- Include ASCII diagrams showing flow
- Cross-link to step-types.md reference

---

### E21-08: Missing Step Types Documentation

**As a** process designer, **I want** documentation for all step types, **so that** I can use the full capability of the process engine.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P1 |
| Phase | MVP+ |
| Dependencies | E21-05 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Add `notification` step type to step-types.md:
  - Purpose: Send alerts/messages to channels
  - Required fields: channels, message, recipients
  - Example: Slack notification on completion
- [ ] Add `sub_process` step type to step-types.md:
  - Purpose: Invoke nested workflows
  - Required fields: process (name), input_mapping
  - Output mapping from child to parent
  - Example: Customer onboarding calling account setup
- [ ] Update step types overview table with new types
- [ ] Add examples showing when to use each

**Technical Notes:**
- Update existing `config/process-docs/getting-started/step-types.md`
- Reference the roadmap (PROCESS_ENGINE_ROADMAP.md) for examples
- Include breadcrumb/navigation concepts for sub_process

---

### E21-09: Progressive Learning Path

**As a** new user, **I want** a structured learning journey, **so that** I can progressively build my process design skills.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P1 |
| Phase | MVP+ |
| Dependencies | E21-07, E21-08 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Define 3-level learning path in docs:
  - Level 1: Getting Started (existing content, reorganized)
  - Level 2: Intermediate (new tutorials)
  - Level 3: Advanced (new tutorials)
- [ ] Create "Second Process" tutorial (~600 words):
  - Builds on first-process.md
  - Teaches parallel execution
  - Introduces variable passing between parallel steps
- [ ] Create "Adding Human Checkpoints" tutorial (~500 words):
  - Takes existing process
  - Adds human_approval step
  - Shows approval decision handling
- [ ] Create "Complex Workflows" tutorial (~600 words):
  - Gateway branching
  - Multiple conditional paths
  - Combining patterns
- [ ] Update docs sidebar to show learning path progression
- [ ] Add "Next Steps" links connecting tutorials

**Technical Notes:**
- Files in `config/process-docs/tutorials/` (new directory)
- Each tutorial should have clear prerequisites
- Include "What You'll Learn" section at start
- End with "What's Next" linking to the next tutorial
- Consider badges/progress indicators in onboarding checklist

---

## Epic E22: Contextual Help

> Help that appears where and when you need it.

---

### E22-01: YAML Editor Help Panel

**As a** process designer, **I want** contextual help while editing YAML, **so that** I get guidance without leaving the editor.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P1 |
| Phase | Core |
| Dependencies | E21-02 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Collapsible help panel on right side of editor
- [ ] Panel shows help for current cursor position
- [ ] Detects YAML key path (e.g., `steps[0].depends_on`)
- [ ] Shows: field description, type, required/optional, example
- [ ] "Learn more" link to full docs
- [ ] Toggle button to show/hide panel
- [ ] Panel state persists in localStorage

**Technical Notes:**
- Location: `src/frontend/src/views/ProcessEditor.vue`
- Parse YAML to determine cursor context
- Help content from `config/process-docs/tooltips.json` or inline
- Consider CodeMirror cursor position API

---

### E22-02: Smart Tooltips Composable

**As a** developer, **I want** a reusable tooltip system, **so that** I can add contextual help throughout the UI.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | Core |
| Dependencies | E22-01 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Composable: `useContextualHelp.js`
- [ ] Method: `registerHelpTrigger(element, helpKey)` - attach help to element
- [ ] Method: `showHelp(helpKey)` - programmatically show help
- [ ] Help content loaded from JSON config
- [ ] Tooltip appears on hover/focus with delay
- [ ] Tooltip dismissible, doesn't block interaction

**Technical Notes:**
- New composable: `src/frontend/src/composables/useContextualHelp.js`
- Content file: `config/process-docs/tooltips.json`
- Consider using existing tooltip library or custom implementation

---

### E22-03: Execution Status Explainers

**As a** user monitoring executions, **I want** explanations for each status, **so that** I understand what's happening and what to do.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P1 |
| Phase | Core |
| Dependencies | None |
| Status | pending |

**Acceptance Criteria:**
- [ ] Each execution status has explanatory text:
  - PENDING: "Waiting to start..."
  - RUNNING: "Execution in progress"
  - PAUSED: "Awaiting human approval" + link to Approvals
  - COMPLETED: "All steps finished successfully"
  - FAILED: "Execution stopped due to error" + error details
  - CANCELLED: "Execution was manually cancelled"
- [ ] Step-level status explanations:
  - WAITING: "Waiting for dependencies: [list]"
  - SKIPPED: "Skipped because: [condition]"
- [ ] Info icon next to status that shows explanation on hover

**Technical Notes:**
- Location: `src/frontend/src/views/ProcessExecutionDetail.vue`
- Location: `src/frontend/src/components/ExecutionTimeline.vue`
- Add `title` attributes or tooltip component

---

## Epic E23: Guided Tours

> Interactive walkthroughs for key user journeys.

---

### E23-01: Tour Library Integration (Driver.js)

**As a** developer, **I want** a tour library integrated, **so that** I can create guided walkthroughs.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P2 |
| Phase | Core |
| Dependencies | None |
| Status | pending |

**Acceptance Criteria:**
- [ ] Driver.js installed and configured
- [ ] Wrapper composable: `useTour.js`
- [ ] Tour styling matches Trinity theme (colors, dark mode)
- [ ] Tours can be triggered programmatically
- [ ] Tour progress saved to prevent repeat showing

**Technical Notes:**
- Install: `npm install driver.js`
- New composable: `src/frontend/src/composables/useTour.js`
- CSS customization for Trinity theme
- LocalStorage for tour completion state

---

### E23-02: First-Time User Tour

**As a** new user, **I want** a guided tour of the Processes section, **so that** I understand the key areas.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | Core |
| Dependencies | E23-01 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Tour triggers on first visit to `/processes` with no processes
- [ ] Tour steps:
  1. Welcome message explaining Processes
  2. Highlight "Create Process" button
  3. Point to Dashboard tab
  4. Point to Executions tab
  5. Point to Approvals tab
  6. Point to Docs tab (if implemented)
- [ ] "Skip tour" option
- [ ] "Don't show again" checkbox
- [ ] Tour completion marked in localStorage

**Technical Notes:**
- Trigger in `ProcessList.vue` on mount
- Check `isFirstRun` from `useOnboarding.js`
- Tour steps reference DOM elements by selector or ref

---

### E23-03: Feature Discovery Mini-Tours

**As a** user exploring features, **I want** contextual mini-tours, **so that** I learn about features when I first encounter them.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P3 |
| Phase | Core |
| Dependencies | E23-02 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Mini-tour: First time opening Process Editor
  - Highlight YAML area
  - Highlight Preview panel
  - Highlight Validate button
- [ ] Mini-tour: First execution completes
  - Highlight timeline view
  - Explain step statuses
- [ ] Mini-tour: First approval pending
  - Highlight Approvals tab badge
  - Explain approval workflow
- [ ] Each mini-tour shows only once

**Technical Notes:**
- Trigger based on user actions + localStorage flags
- Shorter than main tour (2-3 steps max)
- Can be implemented incrementally

---

## Epic E24: First Process Wizard

> Guided wizard for creating first process without YAML knowledge.

---

### E24-01: Wizard Component Shell

**As a** new user, **I want** a step-by-step wizard, **so that** I can create a process without knowing YAML.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | Advanced |
| Dependencies | E20-03 |
| Status | pending |

**Acceptance Criteria:**
- [ ] New view/route: `/processes/wizard`
- [ ] Multi-step wizard shell with:
  - Step indicator (1 of 4)
  - Back/Next navigation
  - Cancel option with confirmation
- [ ] Wizard state managed in component (not persisted)
- [ ] Final step generates YAML and saves process

**Technical Notes:**
- New view: `src/frontend/src/views/ProcessWizard.vue`
- Route: Add to router with requiresAuth
- Consider Vuex/Pinia for complex wizard state

---

### E24-02: Goal Selection Step

**As a** new user, **I want** to choose what I'm automating, **so that** the wizard can suggest appropriate templates.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P2 |
| Phase | Advanced |
| Dependencies | E24-01 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Step 1 shows goal options:
  - Content Creation (research → write → review)
  - Data Processing (collect → analyze → report)
  - Approval Workflow (request → review → notify)
  - Custom (start from scratch)
- [ ] Each option shows brief description and step count
- [ ] Selection stored in wizard state
- [ ] "Custom" skips to minimal template

**Technical Notes:**
- Options map to process templates
- Visual cards for selection (radio-like behavior)

---

### E24-03: Agent Selection Step

**As a** new user, **I want** to assign agents to steps, **so that** my process uses the right agents.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | Advanced |
| Dependencies | E24-02 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Step 2 shows steps from selected template
- [ ] Each step has agent dropdown
- [ ] Dropdown shows available agents with status (running/stopped)
- [ ] Warning if agent is stopped
- [ ] Option to create new agent (links out)
- [ ] Agents stored in wizard state

**Technical Notes:**
- Fetch agents from `/api/agents`
- Show agent status badges
- Consider "Use same agent for all" option

---

### E24-04: Review and Create Step

**As a** new user, **I want** to review and create my process, **so that** I can verify before saving.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | Advanced |
| Dependencies | E24-03 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Step 4 shows:
  - Process name input (editable)
  - Visual workflow diagram
  - Estimated duration (if computable)
  - Generated YAML preview (collapsible)
- [ ] "Create Process" button saves and redirects
- [ ] Option: "Run immediately after creation" checkbox
- [ ] Success message with link to new process

**Technical Notes:**
- Generate YAML from wizard state
- Call `POST /api/processes` to save
- Optionally call execute endpoint if checkbox checked

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-18 | Initial onboarding backlog with 17 stories across 5 epics |
| 2026-01-18 | Sprint 7 implemented: E20-01, E20-02, E21-04 (empty states, checklist, getting started) |
| 2026-01-18 | Sprint 8 implemented: E21-01, E21-02, E21-05, E21-06 (docs tab, reference content) |
| 2026-01-18 | Added E20-05: Onboarding UX Polish (context-aware hints, restart from docs) |
| 2026-01-18 | Added E21-07, E21-08, E21-09: Pattern docs, missing step types, learning path (21 stories total) |
