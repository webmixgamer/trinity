# Feature: Process Scheduling

> Cron-based schedule triggers for automated process execution and timer steps for delays within processes

---

## Overview

Process Scheduling provides two complementary features:
1. **Schedule Triggers** - Automatically start processes on a cron schedule
2. **Timer Steps** - Add delays within a process workflow

**Key Capabilities:**
- Cron expression support with presets (daily, hourly, etc.)
- Timezone-aware scheduling
- Timer steps for in-process delays
- Integration with existing Trinity scheduler infrastructure

---

## Entry Points

- **UI**: `ProcessEditor.vue` -> triggers section in YAML
- **Backend**: Process publish registers schedules in scheduler
- **Scheduler**: Background service checks and triggers processes
- **Timer step**: Inline delay during process execution

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Process Definition                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  YAML with triggers                                                      │    │
│  │  triggers:                                                               │    │
│  │    - id: daily-run                                                       │    │
│  │      type: schedule                                                      │    │
│  │      cron: "0 9 * * *"                                                  │    │
│  │      timezone: America/New_York                                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ Publish process
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Backend                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  routers/processes.py - publish_process()                                │    │
│  │  └── _register_process_schedules()                                       │    │
│  │      ├── Filter ScheduleTriggerConfig from triggers                      │    │
│  │      ├── Expand cron presets (daily → "0 0 * * *")                       │    │
│  │      ├── Validate cron expression with croniter                          │    │
│  │      ├── Calculate next_run_at                                           │    │
│  │      └── INSERT into process_schedules table                             │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Database: process_schedules table                                       │    │
│  │  ├── id                          - Schedule ID                           │    │
│  │  ├── process_id                  - Process to execute                    │    │
│  │  ├── trigger_id                  - Trigger within process                │    │
│  │  ├── cron_expression             - Cron expression                       │    │
│  │  ├── timezone                    - IANA timezone                         │    │
│  │  ├── enabled                     - Active flag                           │    │
│  │  └── next_run_at                 - Next scheduled execution              │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      │ Scheduler reads                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  services/scheduler.py (Existing Trinity Scheduler)                      │    │
│  │  ├── _check_process_schedules()  - Called periodically                   │    │
│  │  │   ├── Query schedules where next_run_at <= now                        │    │
│  │  │   ├── Start execution via ExecutionEngine                             │    │
│  │  │   └── Update next_run_at                                              │    │
│  │  └── Process runs with triggered_by="schedule"                           │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Schedule Triggers

### YAML Configuration

```yaml
name: daily-report
version: 1
description: Generate daily report

triggers:
  - id: morning-run
    type: schedule
    cron: "0 9 * * *"        # 9 AM daily
    timezone: America/New_York
    enabled: true
    description: "Generate report at 9 AM EST"

  - id: evening-backup
    type: schedule
    cron: "0 18 * * 1-5"     # 6 PM weekdays
    timezone: UTC
    enabled: true

steps:
  - id: generate
    type: agent_task
    agent: report-agent
    message: Generate the daily report
```

### Cron Presets

Common presets are supported for convenience:

| Preset | Cron Expression | Description |
|--------|-----------------|-------------|
| `daily` | `0 0 * * *` | Midnight daily |
| `hourly` | `0 * * * *` | Every hour |
| `weekly` | `0 0 * * 0` | Sunday midnight |
| `monthly` | `0 0 1 * *` | First of month |
| `every_5min` | `*/5 * * * *` | Every 5 minutes |
| `every_15min` | `*/15 * * * *` | Every 15 minutes |

```yaml
triggers:
  - id: daily-check
    type: schedule
    cron: daily           # Uses preset
    timezone: UTC
```

### ScheduleTriggerConfig

```python
# step_configs.py

@dataclass(frozen=True)
class ScheduleTriggerConfig(TriggerConfig):
    """Configuration for schedule-based triggers."""
    cron: str                    # Cron expression or preset
    timezone: str = "UTC"        # IANA timezone
    enabled: bool = True
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> ScheduleTriggerConfig:
        return cls(
            id=data["id"],
            cron=data["cron"],
            timezone=data.get("timezone", "UTC"),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
        )
```

### Schedule Registration

When a process is published, schedules are registered:

```python
# processes.py:639-731 (_register_process_schedules)

def _register_process_schedules(definition: ProcessDefinition) -> int:
    # Filter for schedule triggers
    schedule_triggers = [
        t for t in definition.triggers
        if isinstance(t, ScheduleTriggerConfig)
    ]

    if not schedule_triggers:
        return 0

    for trigger in schedule_triggers:
        if not trigger.enabled:
            continue

        # Expand cron preset if needed
        cron_expr = expand_cron_preset(trigger.cron)

        # Calculate next run time
        tz = pytz.timezone(trigger.timezone)
        cron = croniter(cron_expr, datetime.now(tz))
        next_run = cron.get_next(datetime)

        # Insert into database
        cursor.execute("""
            INSERT OR REPLACE INTO process_schedules (
                id, process_id, process_name, trigger_id, cron_expression,
                enabled, timezone, description, next_run_at, ...
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ...)
        """, ...)

    return count
```

### Cron Validation

```python
# validator.py:592-622 (_validate_cron_expression)

def _validate_cron_expression(self, cron: str) -> Optional[str]:
    """Validate a cron expression or preset."""
    # Check if it's a valid preset
    if cron in CRON_PRESETS:
        return None

    # Expand preset and validate
    cron_expr = expand_cron_preset(cron)

    # Basic format check (5 fields)
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return f"Invalid cron: expected 5 fields (minute hour day month day_of_week)"

    # Use croniter for detailed validation
    if CRONITER_AVAILABLE:
        try:
            croniter(cron_expr, datetime.now())
        except (ValueError, KeyError) as e:
            return f"Invalid cron expression: {str(e)}"

    return None
```

---

## Timer Steps

Timer steps add delays within a process workflow.

### YAML Configuration

```yaml
steps:
  - id: start-task
    type: agent_task
    agent: task-agent
    message: Start the task

  - id: wait-5min
    type: timer
    delay: 5m
    depends_on: [start-task]

  - id: check-result
    type: agent_task
    agent: check-agent
    message: Check if task completed
    depends_on: [wait-5min]
```

### Duration Format

| Format | Example | Seconds |
|--------|---------|---------|
| Seconds | `30s` | 30 |
| Minutes | `5m` | 300 |
| Hours | `1h` | 3600 |
| Days | `1d` | 86400 |

### TimerConfig

```python
# step_configs.py:141-170

@dataclass(frozen=True)
class TimerConfig:
    """Configuration for timer step type."""
    delay: Duration = field(default_factory=lambda: Duration.from_minutes(1))

    @classmethod
    def from_dict(cls, data: dict) -> TimerConfig:
        delay = data.get("delay", "1m")
        if isinstance(delay, str):
            delay = Duration.from_string(delay)
        elif isinstance(delay, int):
            delay = Duration.from_seconds(delay)

        return cls(delay=delay)

    def to_dict(self) -> dict:
        return {"delay": str(self.delay)}
```

### TimerHandler

```python
# handlers/timer.py:20-75

class TimerHandler(StepHandler):
    """Handler for timer step type - pauses execution for a duration."""

    @property
    def step_type(self) -> StepType:
        return StepType.TIMER

    async def execute(self, context: StepContext, config: StepConfig) -> StepResult:
        if not isinstance(config, TimerConfig):
            return StepResult.fail("Invalid config type", error_code="INVALID_CONFIG")

        delay_seconds = config.delay.seconds

        logger.info(f"Timer step starting: waiting {delay_seconds}s")

        # Wait for the specified duration
        await asyncio.sleep(delay_seconds)

        logger.info(f"Timer step completed: waited {delay_seconds}s")

        return StepResult.ok({
            "waited_seconds": delay_seconds,
            "delay_formatted": str(config.delay),
        })
```

---

## Database Schema

### process_schedules Table

```sql
CREATE TABLE IF NOT EXISTS process_schedules (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL,
    process_name TEXT NOT NULL,
    trigger_id TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    timezone TEXT DEFAULT 'UTC',
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_run_at TEXT,
    next_run_at TEXT,
    UNIQUE(process_id, trigger_id)
);
```

---

## Flow Details

### 1. Schedule Trigger Flow

```
Process Published                Scheduler Service              ExecutionEngine
-----------------                -----------------              ---------------
publish_process()
_register_process_schedules()
INSERT process_schedules
                                 _check_process_schedules()
                                 (runs every minute)
                                 SELECT where next_run_at <= now
                                 For each schedule:
                                     Get ProcessDefinition
                                     engine.start(definition, triggered_by="schedule")
                                                               → start()
                                                                 ProcessExecution.create()
                                                                 _run()
                                     Update next_run_at
```

### 2. Timer Step Flow

```
ExecutionEngine                  TimerHandler
---------------                  ------------
_execute_step()
  Get handler for TIMER
  handler.execute(context, config)
                                → execute()
                                  delay_seconds = config.delay.seconds
                                  await asyncio.sleep(delay_seconds)
                                ← StepResult.ok({waited_seconds: N})
  _handle_step_success()
  Continue to next step
```

---

## Timezone Support

### IANA Timezone Names

Use standard IANA timezone names:

```yaml
triggers:
  - id: tokyo-morning
    type: schedule
    cron: "0 9 * * *"
    timezone: Asia/Tokyo

  - id: london-evening
    type: schedule
    cron: "0 18 * * *"
    timezone: Europe/London
```

### Timezone Validation

```python
# validator.py:580-590

timezone = trigger.get("timezone", "UTC")
if timezone:
    try:
        import pytz
        pytz.timezone(timezone)
    except Exception:
        result.add_warning(
            message=f"Unknown timezone '{timezone}', will use UTC",
            path=f"{path_prefix}.timezone",
        )
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/schedules` | List all schedules |
| GET | `/api/schedules/{id}` | Get schedule detail |
| POST | `/api/schedules/{id}/enable` | Enable schedule |
| POST | `/api/schedules/{id}/disable` | Disable schedule |
| POST | `/api/schedules/{id}/trigger` | Manually trigger now |

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| Invalid cron expression | Malformed cron syntax | Use preset or valid 5-field cron |
| Unknown timezone | Invalid IANA timezone | Check timezone name |
| Schedule not firing | Process not published | Publish the process |
| Timer too long | Delay exceeds timeout | Adjust step timeout |

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- Process with schedule trigger or timer step

### Test Cases

1. **Schedule registration on publish**
   - Action: Publish process with schedule trigger
   - Expected: Entry appears in process_schedules table

2. **Cron preset expansion**
   - Action: Use preset like "daily"
   - Expected: Expands to "0 0 * * *"

3. **Timezone calculation**
   - Action: Schedule at 9 AM Tokyo time
   - Expected: Runs at correct UTC equivalent

4. **Timer step execution**
   - Action: Run process with 30s timer step
   - Expected: Step waits 30s, outputs waited_seconds

5. **Archive removes schedules**
   - Action: Archive a published process
   - Expected: Schedule entries deleted

---

## Related Flows

- [process-definition.md](./process-definition.md) - Trigger configuration
- [process-execution.md](./process-execution.md) - How scheduled executions run

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-16 | Initial creation |
