# Process Engine - Reliability Improvements Backlog

> **Phase**: Reliability
> **Goal**: Application Service Integration Tests for Process Engine
> **Stories**: 10
> **Focus**: Test ExecutionEngine orchestration with real infrastructure, mock only external boundaries
> **Reference**: See [`BACKLOG_INDEX.md`](./BACKLOG_INDEX.md) for conventions

---

## Overview

This backlog implements **Application Service Integration Tests** for the Process Engine module. These tests fill the critical gap in the DDD test pyramid between unit tests (600+) and E2E tests (future).

### Test Scope

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    INTEGRATION TEST SCOPE                                    │
│                                                                              │
│  ┌─ REAL ────────────────────────────────────────────────────────────────┐  │
│  │   ExecutionEngine ──► ProcessExecutionRepository (SQLite :memory:)    │  │
│  │        │          ──► DependencyResolver (real)                       │  │
│  │        │          ──► OutputStorage (real)                            │  │
│  │        │          ──► EventBus (InMemory - capture events)            │  │
│  │        │          ──► StepHandlerRegistry                             │  │
│  │        │                    │                                         │  │
│  │        │                    └──► AgentTaskHandler ──► MockAgentGateway│  │
│  │        │                    └──► GatewayHandler (real)                │  │
│  │        │                    └──► TimerHandler (real, mocked sleep)    │  │
│  └────────┼──────────────────────────────────────────────────────────────┘  │
│           │                                                                  │
│      MOCK ONLY: External HTTP calls to agents                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Sprint Plan

| Sprint | Stories | Focus |
|--------|---------|-------|
| **Sprint 1** | RI-01 | Test Infrastructure (conftest.py) |
| **Sprint 2** | RI-02 | Execution Lifecycle |
| **Sprint 3** | RI-03, RI-04 | Sequential & Parallel Execution |
| **Sprint 4** | RI-05, RI-06 | Error Handling & Gateways |
| **Sprint 5** | RI-07, RI-08, RI-09 | Timer, Events, Output |

---

## Stories

### RI-01: Integration Test Infrastructure

**As a** developer, **I want** shared test fixtures for integration tests, **so that** I can write tests with real infrastructure.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Dependencies | None |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `tests/process_engine/integration/__init__.py` created
- [x] `tests/process_engine/integration/conftest.py` with:
  - [x] `MockAgentGateway` class with configurable responses and call tracking
  - [x] `integration_repos` fixture (real SQLite `:memory:`)
  - [x] `integration_event_bus` fixture with event capture
  - [x] `integration_engine` fixture (fully wired ExecutionEngine)
  - [x] Helper functions for creating test process definitions
- [x] All fixtures can be imported without triggering main app dependencies

**Technical Notes:**
- Reuse patterns from `tests/process_engine/conftest.py`
- MockAgentGateway should implement same interface as real `AgentGateway`
- Event capture should support assertion helpers

---

### RI-02: Execution Lifecycle Tests

**As a** developer, **I want** tests for basic execution lifecycle, **so that** I verify start/complete/fail/cancel flows work end-to-end.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Dependencies | RI-01 |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `test_execution_lifecycle.py` with 4 tests:
  - [x] `test_single_step_completes` - One step process completes
  - [x] `test_execution_persisted_to_database` - State saved to SQLite
  - [x] `test_failed_step_fails_execution` - Agent error fails process
  - [x] `test_cancel_pending_execution` - Cancel before execution

**Technical Notes:**
- Each test should verify both in-memory and persisted state
- Use `integration_engine` fixture

---

### RI-03: Sequential Execution Tests

**As a** developer, **I want** tests for sequential execution, **so that** I verify multi-step chains and output passing work correctly.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Dependencies | RI-02 |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `test_sequential_execution.py` with 4 tests:
  - [x] `test_three_step_sequential_completes` - All steps in order
  - [x] `test_output_passed_between_steps` - `{{steps.X.output}}` works
  - [x] `test_input_data_available_in_first_step` - `{{input.X}}` works
  - [x] `test_middle_step_failure_stops_execution` - Failure stops chain (bonus)

**Technical Notes:**
- Configure MockAgentGateway with step-specific responses
- Verify ExpressionEvaluator substitution works in integration

---

### RI-04: Parallel Execution Tests

**As a** developer, **I want** tests for parallel execution, **so that** I verify fork/join patterns work correctly.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P0 |
| Dependencies | RI-02 |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `test_parallel_execution.py` with 5 tests:
  - [x] `test_parallel_steps_both_complete` - Two independent steps
  - [x] `test_diamond_pattern` - Fork → parallel → join
  - [x] `test_join_waits_for_all_dependencies` - Join doesn't start early
  - [x] `test_one_parallel_failure_behavior` - Configurable stop_on_failure
  - [x] `test_parallel_events_sequence` - Event ordering (bonus)

**Technical Notes:**
- Use `ExecutionConfig(parallel_execution=True)`
- Verify DependencyResolver correctly identifies parallel groups

---

### RI-05: Error Handling & Retry Tests

**As a** developer, **I want** tests for error handling, **so that** I verify retry policies and error boundaries work.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Dependencies | RI-02 |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `test_error_retry.py` with 5 tests:
  - [x] `test_retry_succeeds_on_third_attempt` - Retry policy works
  - [x] `test_retry_exhausted_fails_execution` - Max attempts reached
  - [x] `test_skip_step_on_error_continues` - `on_error: skip_step`
  - [x] `test_retry_count_persisted` - `step_execution.retry_count` saved
  - [x] `test_retry_with_exponential_backoff` - Backoff behavior (bonus)

**Technical Notes:**
- MockAgentGateway needs `fail_count` parameter
- Verify StepRetrying events emitted

---

### RI-06: Gateway Routing Tests

**As a** developer, **I want** tests for gateway routing, **so that** I verify conditional logic works in integration.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Dependencies | RI-02 |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `test_gateway_routing.py` with 4 tests:
  - [x] `test_exclusive_gateway_takes_first_match` - XOR routing
  - [x] `test_gateway_uses_default_route` - Fallback path
  - [x] `test_gateway_routes_based_on_step_output` - Dynamic routing
  - [x] `test_gateway_with_complex_condition` - Boolean logic (bonus)

**Technical Notes:**
- GatewayHandler is used directly (no mock)
- Verify correct branch executed based on conditions

---

### RI-07: Timer Step Tests

**As a** developer, **I want** tests for timer steps, **so that** I verify delay behavior in integration.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P2 |
| Dependencies | RI-02 |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `test_timer_steps.py` with 3 tests:
  - [x] `test_timer_step_completes` - Timer runs (mocked sleep)
  - [x] `test_timer_output_includes_waited_seconds` - Output correct
  - [x] `test_timer_delays_dependent_steps` - Dependency ordering (bonus)

**Technical Notes:**
- Mock `asyncio.sleep` to avoid real delays
- TimerHandler is used directly

---

### RI-08: Event Publishing Tests

**As a** developer, **I want** tests for event publishing, **so that** I verify domain events are emitted correctly.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Dependencies | RI-02 |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `test_event_publishing.py` with 5 tests:
  - [x] `test_event_sequence_for_successful_execution` - All events in order
  - [x] `test_step_failed_event_contains_error` - Error details in event
  - [x] `test_events_contain_execution_context` - IDs, timestamps present
  - [x] `test_failed_sequence_includes_partial_success_events` - Partial events (bonus)
  - [x] `test_events_ordered_by_timestamp` - Monotonic ordering (bonus)

**Technical Notes:**
- Use `integration_event_bus` fixture with event capture
- Create assertion helper: `assert_event_sequence(events, expected_types)`

---

### RI-09: Output Persistence Tests

**As a** developer, **I want** tests for output persistence, **so that** I verify OutputStorage integration.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P2 |
| Dependencies | RI-03 |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `test_output_persistence.py` with 3 tests:
  - [x] `test_step_output_stored_and_retrievable` - OutputStorage works
  - [x] `test_output_available_for_next_step_substitution` - E2E flow
  - [x] `test_multiple_output_references` - Multiple substitutions (bonus)

**Technical Notes:**
- Verify OutputStorage.store() and OutputStorage.retrieve()
- Confirm ExpressionEvaluator can access stored outputs

---

## Running the Tests

```bash
# Run all integration tests
pytest tests/process_engine/integration/ -v

# Run specific test file
pytest tests/process_engine/integration/test_execution_lifecycle.py -v

# Run with coverage
pytest tests/process_engine/integration/ --cov=services.process_engine.engine
```

---

## Success Criteria

| Metric | Target | Actual |
|--------|--------|--------|
| Total tests | 25+ | ✅ 33 |
| Test runtime | < 10 seconds | ⚠️ ~90s (includes real async ops) |
| Test isolation | Each test independent | ✅ Yes |
| Coverage | Critical paths from PROCESS_ENGINE_ROADMAP.md | ✅ Covered |

**Note**: Test runtime is higher than target due to real execution engine orchestration. Tests use mocked `asyncio.sleep` where possible but still exercise full async event dispatch.

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-17 | Initial creation - Application Service Integration Tests |
| 2026-01-17 | All 33 integration tests implemented and passing |
