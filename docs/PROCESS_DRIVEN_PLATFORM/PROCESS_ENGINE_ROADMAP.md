# Process Engine Roadmap

> **Purpose**: Test the Process Engine with diverse real-world processes to identify architectural and UX bottlenecks
> **Reference**: `PROCESS_DRIVEN_THINKING_IT5.md` (scale, reliability, enterprise considerations)
> **Date**: 2026-01-16

---

## Strategy

Rather than theoretical improvements, we'll **build real processes** across different domains and patterns to:
1. **Discover architectural limits** — Where does the engine struggle?
2. **Expose UX friction** — Where do users get confused?
3. **Validate assumptions** — Do our step types cover real needs?
4. **Stress test at scale** — What breaks with concurrent execution?

**Each process category tests specific aspects of the platform.**

---

## Phase 1: Foundation Processes (Sequential + Basic)

These processes validate core functionality works correctly before adding complexity.

### P1.1 — Simple Content Pipeline

| Aspect | Value |
|--------|-------|
| **Steps** | 3 sequential agent_task steps |
| **Agents** | 3 different agents |
| **Duration** | ~5-10 minutes |
| **Tests** | Basic orchestration, output passing |

```yaml
name: simple-content-pipeline
steps:
  - id: research
    type: agent_task
    agent: researcher
    message: "Research the topic: {{input.topic}}"

  - id: write
    type: agent_task
    agent: writer
    depends_on: [research]
    message: "Write article using: {{steps.research.output}}"

  - id: review
    type: agent_task
    agent: editor
    depends_on: [write]
    message: "Review and improve: {{steps.write.output}}"
```

**Bottlenecks to Watch**:
- [ ] Output variable passing between steps (template syntax)
- [ ] Error messages when agent is unavailable
- [ ] Progress visibility during long agent tasks

---

### P1.2 — Approval Gate Pipeline

| Aspect | Value |
|--------|-------|
| **Steps** | 2 agent_task + 1 human_approval + 1 conditional |
| **Duration** | Variable (depends on human) |
| **Tests** | Human approval flow, timeout handling, conditional logic |

```yaml
name: content-with-approval
steps:
  - id: draft
    type: agent_task
    agent: writer
    message: "Write first draft about {{input.topic}}"

  - id: review-gate
    type: human_approval
    depends_on: [draft]
    title: "Content Review Required"
    description: "Please review the draft for quality and accuracy"
    timeout: 24h
    approvers: ["editor@company.com"]

  - id: publish
    type: agent_task
    depends_on: [review-gate]
    agent: publisher
    condition: "{{steps.review-gate.decision}} == 'approved'"
    message: "Publish: {{steps.draft.output}}"

  - id: revise
    type: agent_task
    depends_on: [review-gate]
    agent: writer
    condition: "{{steps.review-gate.decision}} == 'rejected'"
    message: "Revise based on feedback: {{steps.review-gate.comment}}"
```

**Bottlenecks to Watch**:
- [ ] Approval notification delivery (how do approvers know?)
- [ ] Timeout behavior (does execution fail gracefully?)
- [ ] Conditional branching UX (is it clear why a step was skipped?)
- [ ] Approval inbox findability

---

### P1.3 — Scheduled Daily Report

| Aspect | Value |
|--------|-------|
| **Trigger** | Cron schedule (daily 9am) |
| **Steps** | 3 sequential |
| **Tests** | Scheduling, timezone handling, unattended execution |

```yaml
name: daily-metrics-report
trigger:
  type: schedule
  cron: "0 9 * * *"
  timezone: "America/New_York"

steps:
  - id: gather
    type: agent_task
    agent: data-collector
    message: "Gather yesterday's metrics from all sources"

  - id: analyze
    type: agent_task
    agent: analyst
    depends_on: [gather]
    message: "Analyze trends and anomalies in: {{steps.gather.output}}"

  - id: report
    type: agent_task
    agent: reporter
    depends_on: [analyze]
    message: "Generate executive summary from: {{steps.analyze.output}}"
```

**Bottlenecks to Watch**:
- [ ] Schedule UI (is cron readable? timezone picker UX?)
- [ ] Unattended failure handling (who gets notified?)
- [ ] Execution history for scheduled processes
- [ ] Disabling/pausing schedules

---

## Phase 2: Parallel & Complex Patterns

Test advanced orchestration capabilities.

### P2.1 — Parallel Research Pipeline

| Aspect | Value |
|--------|-------|
| **Steps** | 4 parallel + 1 aggregation |
| **Agents** | 4 researcher agents running simultaneously |
| **Tests** | Parallel execution, result aggregation, resource contention |

```yaml
name: multi-source-research
steps:
  # These 4 run in parallel (no dependencies)
  - id: research-academic
    type: agent_task
    agent: academic-researcher
    message: "Find academic papers about {{input.topic}}"

  - id: research-news
    type: agent_task
    agent: news-researcher
    message: "Find recent news about {{input.topic}}"

  - id: research-social
    type: agent_task
    agent: social-researcher
    message: "Find social media discussions about {{input.topic}}"

  - id: research-industry
    type: agent_task
    agent: industry-researcher
    message: "Find industry reports about {{input.topic}}"

  # Aggregation step waits for all parallel steps
  - id: synthesize
    type: agent_task
    agent: synthesizer
    depends_on: [research-academic, research-news, research-social, research-industry]
    message: |
      Synthesize findings from:
      - Academic: {{steps.research-academic.output}}
      - News: {{steps.research-news.output}}
      - Social: {{steps.research-social.output}}
      - Industry: {{steps.research-industry.output}}
```

**Bottlenecks to Watch**:
- [ ] UI visualization of parallel branches
- [ ] Progress indication (4 things at once)
- [ ] Memory/resource usage with 4 concurrent agents
- [ ] What happens if 1 of 4 fails? (partial results?)
- [ ] Aggregation step message length limits

---

### P2.2 — Diamond Dependency Pattern

| Aspect | Value |
|--------|-------|
| **Pattern** | Fork → parallel → join |
| **Tests** | Complex dependency resolution, timing |

```yaml
name: diamond-pattern
steps:
  - id: start
    type: agent_task
    agent: coordinator
    message: "Initialize workflow for {{input.request}}"

  # Fork: two parallel paths
  - id: path-a
    type: agent_task
    agent: specialist-a
    depends_on: [start]
    message: "Process via method A: {{steps.start.output}}"

  - id: path-b
    type: agent_task
    agent: specialist-b
    depends_on: [start]
    message: "Process via method B: {{steps.start.output}}"

  # Join: wait for both
  - id: merge
    type: agent_task
    agent: coordinator
    depends_on: [path-a, path-b]
    message: |
      Merge results:
      - Method A: {{steps.path-a.output}}
      - Method B: {{steps.path-b.output}}
```

**Bottlenecks to Watch**:
- [ ] Dependency graph visualization clarity
- [ ] Join timing (what if path-a takes 10x longer than path-b?)
- [ ] UI showing "waiting for other branch"

---

### P2.3 — Nested Sub-Process

| Aspect | Value |
|--------|-------|
| **Depth** | Parent calls child process |
| **Tests** | Sub-process invocation, input/output mapping, breadcrumbs |

**Parent Process:**
```yaml
name: customer-onboarding-main
steps:
  - id: validate-customer
    type: agent_task
    agent: validator
    message: "Validate customer data: {{input.customer_data}}"

  - id: setup-account
    type: sub_process
    depends_on: [validate-customer]
    process: account-setup-subprocess
    input_mapping:
      customer_id: "{{steps.validate-customer.output.customer_id}}"
      tier: "{{input.subscription_tier}}"

  - id: welcome
    type: agent_task
    depends_on: [setup-account]
    agent: communicator
    message: "Send welcome to {{steps.setup-account.output.email}}"
```

**Child Process:**
```yaml
name: account-setup-subprocess
steps:
  - id: create-account
    type: agent_task
    agent: account-creator
    message: "Create account for customer {{input.customer_id}}"

  - id: configure-tier
    type: agent_task
    agent: configurator
    depends_on: [create-account]
    message: "Configure {{input.tier}} tier for {{steps.create-account.output.account_id}}"
```

**Bottlenecks to Watch**:
- [ ] Sub-process discovery (where do I define the child?)
- [ ] Input/output mapping UX (complex template syntax)
- [ ] Breadcrumb navigation clarity
- [ ] Cost aggregation (parent includes child costs?)
- [ ] Error propagation (child fails → parent status?)

---

## Phase 3: Real-World Business Processes

Test realistic scenarios that exercise multiple features simultaneously.

### P3.1 — Marketing Campaign Launch

| Aspect | Value |
|--------|-------|
| **Steps** | 8 steps with mixed types |
| **Duration** | Hours to days |
| **Complexity** | Multiple approvals, conditional branching, notifications |

```yaml
name: marketing-campaign-launch
trigger:
  type: manual

steps:
  - id: brief-analysis
    type: agent_task
    agent: marketing-strategist
    message: "Analyze campaign brief: {{input.brief}}"

  - id: creative-development
    type: agent_task
    agent: creative-director
    depends_on: [brief-analysis]
    message: "Develop creative concepts based on: {{steps.brief-analysis.output}}"
    roles:
      informed: [marketing-manager]

  - id: creative-approval
    type: human_approval
    depends_on: [creative-development]
    title: "Creative Approval"
    description: "Review creative concepts for brand alignment"
    timeout: 48h
    approvers: ["brand-manager@company.com"]

  - id: budget-calculation
    type: agent_task
    depends_on: [creative-approval]
    condition: "{{steps.creative-approval.decision}} == 'approved'"
    agent: financial-analyst
    message: "Calculate budget for campaign"

  - id: budget-approval
    type: human_approval
    depends_on: [budget-calculation]
    title: "Budget Approval - ${{steps.budget-calculation.output.total}}"
    timeout: 24h
    approvers: ["finance-director@company.com"]

  - id: asset-creation
    type: agent_task
    depends_on: [budget-approval]
    condition: "{{steps.budget-approval.decision}} == 'approved'"
    agent: content-creator
    message: "Create campaign assets"
    roles:
      monitors: [quality-reviewer]

  - id: launch-notification
    type: notification
    depends_on: [asset-creation]
    channels: [slack, email]
    message: "Campaign '{{input.campaign_name}}' ready for launch!"
    recipients: ["marketing-team"]

  - id: schedule-posts
    type: agent_task
    depends_on: [asset-creation]
    agent: social-scheduler
    message: "Schedule social media posts for {{input.launch_date}}"
```

**Bottlenecks to Watch**:
- [ ] Long-running process visibility (hours/days)
- [ ] Multiple approval sequence (approval fatigue?)
- [ ] Conditional branching after rejection (restart vs revise)
- [ ] Notification delivery reliability
- [ ] Process cancellation mid-flight
- [ ] Cost tracking across many steps

---

### P3.2 — Customer Support Escalation

| Aspect | Value |
|--------|-------|
| **Pattern** | Event-driven feel, rapid iteration |
| **Complexity** | Gateway conditions, timer delays, multiple outcomes |

```yaml
name: support-ticket-escalation
steps:
  - id: initial-analysis
    type: agent_task
    agent: support-ai
    message: "Analyze support ticket: {{input.ticket}}"

  - id: complexity-check
    type: gateway
    depends_on: [initial-analysis]
    conditions:
      - condition: "{{steps.initial-analysis.output.complexity}} == 'simple'"
        next_step: auto-resolve
      - condition: "{{steps.initial-analysis.output.complexity}} == 'medium'"
        next_step: human-review
      - condition: "{{steps.initial-analysis.output.complexity}} == 'complex'"
        next_step: specialist-escalation

  - id: auto-resolve
    type: agent_task
    agent: support-ai
    message: "Generate and send resolution for: {{input.ticket}}"
    roles:
      informed: [support-lead]

  - id: human-review
    type: human_approval
    title: "Support Ticket Review"
    timeout: 2h
    approvers: ["support-team"]

  - id: specialist-escalation
    type: agent_task
    agent: escalation-coordinator
    message: "Escalate to specialist team: {{input.ticket}}"

  - id: wait-for-resolution
    type: timer
    depends_on: [specialist-escalation]
    duration: 4h

  - id: check-resolution
    type: agent_task
    depends_on: [wait-for-resolution]
    agent: support-ai
    message: "Check if ticket {{input.ticket_id}} has been resolved"

  - id: resolution-gate
    type: gateway
    depends_on: [check-resolution]
    conditions:
      - condition: "{{steps.check-resolution.output.resolved}} == true"
        next_step: close-ticket
      - condition: "{{steps.check-resolution.output.resolved}} == false"
        next_step: manager-escalation

  - id: close-ticket
    type: agent_task
    agent: support-ai
    message: "Close ticket and send satisfaction survey"

  - id: manager-escalation
    type: notification
    channels: [slack, pagerduty]
    message: "URGENT: Ticket {{input.ticket_id}} unresolved after 4 hours"
    recipients: ["support-manager"]
```

**Bottlenecks to Watch**:
- [ ] Gateway visualization (multiple branches)
- [ ] Timer UX (is it clear process is waiting?)
- [ ] Loop detection (what if check-resolution loops?)
- [ ] Short timeout approvals (2h vs 48h)
- [ ] Multiple end points in a process

---

### P3.3 — Financial Report Generation

| Aspect | Value |
|--------|-------|
| **Complexity** | Data-heavy, compliance-sensitive |
| **Tests** | Cost tracking, error handling, audit trail |

```yaml
name: quarterly-financial-report
config:
  data_classification: confidential
  max_cost: 50.00

trigger:
  type: schedule
  cron: "0 6 1 */3 *"  # First day of each quarter at 6am
  timezone: "UTC"

steps:
  - id: data-extraction
    type: agent_task
    agent: data-engineer
    message: "Extract Q{{input.quarter}} financial data from all systems"
    retry:
      max_attempts: 3
      backoff: exponential

  - id: validation
    type: agent_task
    agent: data-validator
    depends_on: [data-extraction]
    message: "Validate data integrity and flag anomalies"
    roles:
      monitors: [finance-lead]

  - id: analysis
    type: agent_task
    agent: financial-analyst
    depends_on: [validation]
    message: "Perform financial analysis and generate insights"

  - id: report-draft
    type: agent_task
    agent: report-writer
    depends_on: [analysis]
    message: "Generate quarterly report draft"

  - id: compliance-review
    type: human_approval
    depends_on: [report-draft]
    title: "Compliance Review - Q{{input.quarter}} Report"
    description: "Verify regulatory compliance of financial statements"
    timeout: 72h
    approvers: ["compliance-officer@company.com"]

  - id: cfo-approval
    type: human_approval
    depends_on: [compliance-review]
    condition: "{{steps.compliance-review.decision}} == 'approved'"
    title: "CFO Final Approval"
    timeout: 48h
    approvers: ["cfo@company.com"]

  - id: publish
    type: agent_task
    depends_on: [cfo-approval]
    condition: "{{steps.cfo-approval.decision}} == 'approved'"
    agent: publisher
    message: "Publish Q{{input.quarter}} report to stakeholders"
    roles:
      informed: [board-members, investors]
```

**Bottlenecks to Watch**:
- [ ] Cost limit enforcement (stops at $50?)
- [ ] Data classification handling (confidential label effects?)
- [ ] Audit trail completeness
- [ ] Retry configuration UX
- [ ] Multi-level approval chain
- [ ] Informed notification to external parties

---

## Phase 4: Stress & Edge Cases

Push the platform to find breaking points.

### P4.1 — High-Concurrency Batch

| Aspect | Value |
|--------|-------|
| **Pattern** | 10 parallel agent tasks |
| **Tests** | Resource limits, queue behavior, UI performance |

```yaml
name: parallel-stress-test
steps:
  # 10 parallel steps using the same agent (queue test)
  - id: task-01
    type: agent_task
    agent: worker
    message: "Process item 1"
  - id: task-02
    type: agent_task
    agent: worker
    message: "Process item 2"
  # ... (8 more identical steps)
  - id: task-10
    type: agent_task
    agent: worker
    message: "Process item 10"

  - id: aggregate
    type: agent_task
    agent: aggregator
    depends_on: [task-01, task-02, task-03, task-04, task-05,
                 task-06, task-07, task-08, task-09, task-10]
    message: "Aggregate all results"
```

**Bottlenecks to Watch**:
- [ ] Agent queue behavior (fairness, ordering)
- [ ] UI performance with 10+ active steps
- [ ] WebSocket event flood
- [ ] Memory usage
- [ ] Timeout handling (what if one hangs?)

---

### P4.2 — Long-Running Timer Process

| Aspect | Value |
|--------|-------|
| **Duration** | 24+ hours |
| **Tests** | Timer reliability, state persistence, recovery |

```yaml
name: long-timer-test
steps:
  - id: start
    type: agent_task
    agent: coordinator
    message: "Initialize long-running process"

  - id: wait-12h
    type: timer
    depends_on: [start]
    duration: 12h

  - id: checkpoint-1
    type: agent_task
    agent: coordinator
    depends_on: [wait-12h]
    message: "12-hour checkpoint"

  - id: wait-12h-more
    type: timer
    depends_on: [checkpoint-1]
    duration: 12h

  - id: final
    type: agent_task
    agent: coordinator
    depends_on: [wait-12h-more]
    message: "Process complete after 24h"
```

**Bottlenecks to Watch**:
- [ ] Timer survives backend restart?
- [ ] UI shows time remaining?
- [ ] Execution list shows "waiting" status clearly?
- [ ] What happens if server clock drifts?

---

### P4.3 — Deep Nesting (3 Levels)

| Aspect | Value |
|--------|-------|
| **Depth** | Parent → Child → Grandchild |
| **Tests** | Deep sub-process navigation, cost roll-up |

**Grandparent:**
```yaml
name: level-1-parent
steps:
  - id: call-child
    type: sub_process
    process: level-2-child
```

**Child:**
```yaml
name: level-2-child
steps:
  - id: work
    type: agent_task
    agent: worker
    message: "Do work at level 2"
  - id: call-grandchild
    type: sub_process
    depends_on: [work]
    process: level-3-grandchild
```

**Grandchild:**
```yaml
name: level-3-grandchild
steps:
  - id: deep-work
    type: agent_task
    agent: worker
    message: "Do work at level 3"
```

**Bottlenecks to Watch**:
- [ ] Breadcrumb navigation at 3 levels
- [ ] Cost aggregation accuracy
- [ ] Error propagation chain
- [ ] Execution list showing hierarchy
- [ ] Performance with nested queries

---

### P4.4 — Error Recovery Test

| Aspect | Value |
|--------|-------|
| **Pattern** | Intentionally failing steps |
| **Tests** | Retry behavior, error UX, recovery options |

```yaml
name: error-recovery-test
steps:
  - id: will-fail
    type: agent_task
    agent: unreliable-agent  # This agent will fail sometimes
    message: "This might fail"
    retry:
      max_attempts: 3
      backoff: exponential
      initial_delay: 5s

  - id: after-failure
    type: agent_task
    agent: worker
    depends_on: [will-fail]
    message: "Continue after failure handling"
```

**Bottlenecks to Watch**:
- [ ] Retry countdown visibility
- [ ] Error message clarity
- [ ] Manual retry option after exhaustion
- [ ] Partial execution state clarity

---

## Phase 5: Multi-Process Scenarios

Test processes running simultaneously and interacting.

### P5.1 — Competing for Same Agent

| Aspect | Value |
|--------|-------|
| **Pattern** | 3 different processes, all need same agent |
| **Tests** | Queue fairness, starvation prevention |

**Run simultaneously:**
1. `simple-content-pipeline` (uses writer agent)
2. `content-with-approval` (uses writer agent)
3. `daily-metrics-report` (uses reporter agent)

**Bottlenecks to Watch**:
- [ ] Does one process starve another?
- [ ] Is queue position visible?
- [ ] Can user prioritize one execution?

---

### P5.2 — Cascading Schedules

| Aspect | Value |
|--------|-------|
| **Pattern** | 5 scheduled processes all trigger at same time |
| **Tests** | Schedule collision handling, resource contention |

Configure 5 different processes all scheduled for "0 9 * * *" (9am daily).

**Bottlenecks to Watch**:
- [ ] Do they all start or queue?
- [ ] Is there schedule jitter option?
- [ ] Dashboard shows schedule collision warning?

---

## Bottleneck Categories

### Architecture Bottlenecks

| ID | Category | Description | Discovered By |
|----|----------|-------------|---------------|
| A1 | Agent Contention | Same agent requested by multiple processes | P4.1, P5.1 |
| A2 | Database Locks | SQLite write contention under load | P4.1 |
| A3 | Memory Usage | Many concurrent executions | P4.1, P5.2 |
| A4 | Timer Reliability | Long timers surviving restarts | P4.2 |
| A5 | Event Storm | WebSocket flood with parallel steps | P4.1 |
| A6 | Nested Queries | Deep sub-process performance | P4.3 |
| A7 | Recovery Gaps | State not properly persisted | P4.2, P4.4 |

### UX Bottlenecks

| ID | Category | Description | Discovered By |
|----|----------|-------------|---------------|
| U1 | Approval Discovery | Users don't know they have approvals | P1.2, P3.1 |
| U2 | Parallel Visualization | Hard to understand concurrent steps | P2.1, P4.1 |
| U3 | Conditional Clarity | Why was a step skipped? | P1.2, P3.2 |
| U4 | Timer Visibility | Is it waiting or stuck? | P3.2, P4.2 |
| U5 | Error Understanding | What went wrong and how to fix? | P4.4 |
| U6 | Sub-process Navigation | Lost in nested executions | P2.3, P4.3 |
| U7 | Long Process Status | Process runs for days, status unclear | P3.1, P4.2 |
| U8 | Cost Awareness | Total cost not visible until done | P3.3 |
| U9 | Template Syntax | Variable interpolation confusing | P2.1, P2.3 |
| U10 | Schedule UX | Cron syntax intimidating | P1.3, P5.2 |

---

## Implementation Tracking

### Phase 1 Status

| Process | Created | Tested | Issues Found |
|---------|---------|--------|--------------|
| P1.1 Simple Content Pipeline | ⏳ | ⏳ | - |
| P1.2 Approval Gate Pipeline | ⏳ | ⏳ | - |
| P1.3 Scheduled Daily Report | ⏳ | ⏳ | - |

### Phase 2 Status

| Process | Created | Tested | Issues Found |
|---------|---------|--------|--------------|
| P2.1 Parallel Research | ⏳ | ⏳ | - |
| P2.2 Diamond Pattern | ⏳ | ⏳ | - |
| P2.3 Nested Sub-Process | ⏳ | ⏳ | - |

### Phase 3 Status

| Process | Created | Tested | Issues Found |
|---------|---------|--------|--------------|
| P3.1 Marketing Campaign | ⏳ | ⏳ | - |
| P3.2 Support Escalation | ⏳ | ⏳ | - |
| P3.3 Financial Report | ⏳ | ⏳ | - |

### Phase 4 Status

| Process | Created | Tested | Issues Found |
|---------|---------|--------|--------------|
| P4.1 High Concurrency | ⏳ | ⏳ | - |
| P4.2 Long Timer | ⏳ | ⏳ | - |
| P4.3 Deep Nesting | ⏳ | ⏳ | - |
| P4.4 Error Recovery | ⏳ | ⏳ | - |

### Phase 5 Status

| Process | Created | Tested | Issues Found |
|---------|---------|--------|--------------|
| P5.1 Agent Competition | ⏳ | ⏳ | - |
| P5.2 Schedule Collision | ⏳ | ⏳ | - |

---

## Issue Log

Track discovered bottlenecks as processes are tested.

| ID | Process | Type | Severity | Description | Status |
|----|---------|------|----------|-------------|--------|
| - | - | - | - | - | - |

**Severity**: Critical / High / Medium / Low
**Type**: Architecture / UX / Bug / Enhancement

---

## Success Criteria

Phase completion requires:

1. **Phase 1**: All 3 processes execute successfully end-to-end
2. **Phase 2**: Parallel execution works, dependencies resolve correctly
3. **Phase 3**: Business processes complete with all step types working
4. **Phase 4**: Stress tests complete, issues documented
5. **Phase 5**: Multi-process scenarios don't deadlock or starve

**Overall Goal**: Identify and document at least 10 actionable bottlenecks for future improvement.

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-16 | Initial roadmap with 5 phases, 14 test processes |
