# Feature: Process Analytics

> Cost tracking, metrics calculation, trend analysis, and cost threshold alerts

---

## Overview

Process Analytics provides visibility into process execution performance and costs. It includes:
1. **Metrics Calculation** - Success rates, durations, costs per process
2. **Trend Data** - Daily execution counts and costs over time
3. **Cost Alerts** - Threshold-based alerting for cost overruns

**Key Capabilities:**
- Per-process metrics (success rate, avg duration, avg cost)
- Step-level performance analysis (slowest, most expensive steps)
- Daily/weekly trend visualization
- Cost threshold configuration with alert generation

---

## Entry Points

- **UI**: Nav bar "Dashboard" -> `ProcessDashboard.vue`
- **UI**: Process detail -> Analytics tab
- **UI**: Nav bar "Alerts" -> `Alerts.vue`
- **API**: `GET /api/processes/{id}/analytics` - Per-process metrics
- **API**: `GET /api/processes/analytics/trends` - Trend data
- **API**: `GET /api/alerts` - Cost alerts

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  ProcessDashboard.vue                                                    │    │
│  │  ├── Summary cards (total executions, success rate, cost)               │    │
│  │  ├── TrendChart.vue (daily execution/cost charts)                       │    │
│  │  └── Process metrics table                                              │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Alerts.vue                                                              │    │
│  │  ├── Filter by status (active, dismissed)                               │    │
│  │  ├── Alert cards with severity badges                                   │    │
│  │  └── Dismiss action                                                      │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Backend                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  routers/processes.py - Analytics Endpoints                              │    │
│  │  ├── get_process_analytics()    - GET /{id}/analytics                    │    │
│  │  ├── get_process_trends()       - GET /analytics/trends                  │    │
│  │  └── get_all_process_analytics()- GET /analytics/all                     │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  services/analytics.py - ProcessAnalytics                                │    │
│  │  ├── get_process_metrics()      - Calculate metrics for one process     │    │
│  │  ├── get_all_process_metrics()  - Calculate metrics for all processes   │    │
│  │  ├── get_trend_data()           - Daily breakdowns over time            │    │
│  │  └── get_step_performance()     - Slowest/most expensive steps          │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      │ reads from                                │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  services/alerts.py - CostAlertService                                   │    │
│  │  ├── get_thresholds()           - List thresholds for process           │    │
│  │  ├── set_threshold()            - Create/update threshold               │    │
│  │  ├── check_execution_cost()     - Check per-execution threshold         │    │
│  │  ├── check_daily_costs()        - Check daily aggregated cost           │    │
│  │  ├── check_weekly_costs()       - Check weekly aggregated cost          │    │
│  │  └── dismiss_alert()            - Dismiss an alert                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Cost Tracking

### How Costs Are Captured

Costs are extracted from agent task responses:

```python
# execution_engine.py:560-576 (_handle_step_success)

# Extract and store cost from output if available
if output.get("cost"):
    cost = Money.from_string(output["cost"])
    step_exec.cost = cost
    execution.add_cost(cost)  # Adds to execution.total_cost

# Extract and store token usage
if output.get("token_usage"):
    token_usage = TokenUsage.from_dict(output["token_usage"])
    step_exec.token_usage = token_usage
```

### AgentGateway Cost Extraction

```python
# handlers/agent_task.py:73-98 (AgentGateway.send_message)

# Extract cost if available
cost = None
if response.metrics and response.metrics.cost_usd:
    cost = Money.from_float(response.metrics.cost_usd)

# Extract token usage if available
if response.metrics:
    input_tokens = getattr(metrics, 'input_tokens', 0)
    output_tokens = getattr(metrics, 'output_tokens', 0)
    if total_tokens > 0:
        token_usage = TokenUsage(...)

return {
    "response": response.response_text,
    "cost": cost,
    "token_usage": token_usage,
}
```

---

## ProcessAnalytics Service

### ProcessMetrics Dataclass

```python
# analytics.py:32-67

@dataclass
class ProcessMetrics:
    process_id: str
    process_name: str
    execution_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    running_count: int = 0
    success_rate: float = 0.0
    average_duration_seconds: Optional[float] = None
    average_cost: Optional[Decimal] = None
    total_cost: Decimal = Decimal("0")
    min_duration_seconds: Optional[float] = None
    max_duration_seconds: Optional[float] = None
    min_cost: Optional[Decimal] = None
    max_cost: Optional[Decimal] = None
```

### Metrics Calculation

```python
# analytics.py:448-500 (_calculate_metrics)

def _calculate_metrics(self, process_id, process_name, executions) -> ProcessMetrics:
    metrics = ProcessMetrics(process_id=process_id, process_name=process_name)

    durations = []
    costs = []

    for execution in executions:
        metrics.execution_count += 1

        if execution.status == ExecutionStatus.COMPLETED:
            metrics.completed_count += 1
        elif execution.status == ExecutionStatus.FAILED:
            metrics.failed_count += 1

        if execution.duration:
            durations.append(execution.duration.seconds)

        if execution.total_cost and execution.total_cost.amount > 0:
            costs.append(execution.total_cost.amount)
            metrics.total_cost += execution.total_cost.amount

    # Calculate success rate
    finished = metrics.completed_count + metrics.failed_count
    if finished > 0:
        metrics.success_rate = (metrics.completed_count / finished) * 100

    # Calculate averages
    if durations:
        metrics.average_duration_seconds = sum(durations) / len(durations)
        metrics.min_duration_seconds = min(durations)
        metrics.max_duration_seconds = max(durations)

    if costs:
        metrics.average_cost = metrics.total_cost / len(costs)
        metrics.min_cost = min(costs)
        metrics.max_cost = max(costs)

    return metrics
```

### Trend Data

```python
# analytics.py:70-111

@dataclass
class DailyTrend:
    date: str
    execution_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    total_cost: Decimal = Decimal("0")
    success_rate: float = 0.0

@dataclass
class TrendData:
    days: int
    daily_trends: List[DailyTrend]
    total_executions: int = 0
    total_completed: int = 0
    total_failed: int = 0
    overall_success_rate: float = 0.0
    total_cost: Decimal = Decimal("0")
```

---

## Cost Alerts

### Threshold Types

| Type | Description | Check Trigger |
|------|-------------|---------------|
| `per_execution` | Single execution cost | On execution complete |
| `daily` | Aggregated daily cost | Periodic/on execution |
| `weekly` | Aggregated weekly cost | Periodic/on execution |

### Alert Severity

| Level | Condition |
|-------|-----------|
| `warning` | Cost exceeds threshold but < 2x |
| `critical` | Cost exceeds 2x threshold |

### CostAlertService

```python
# alerts.py:137-145

class CostAlertService:
    """Service for managing cost thresholds and alerts."""

    def __init__(self, db_path: Optional[str] = None):
        # Uses separate database: trinity_alerts.db

    def get_thresholds(self, process_id: str) -> List[CostThreshold]
    def set_threshold(self, process_id, threshold_type, amount, enabled) -> CostThreshold
    def delete_threshold(self, process_id, threshold_type) -> bool
    def check_execution_cost(self, process_id, process_name, execution_id, cost) -> Optional[CostAlert]
    def check_daily_costs(self, process_id, process_name, daily_cost) -> Optional[CostAlert]
    def check_weekly_costs(self, process_id, process_name, weekly_cost) -> Optional[CostAlert]
    def get_alerts(self, status, process_id, limit, offset) -> List[CostAlert]
    def dismiss_alert(self, alert_id, dismissed_by) -> bool
```

### Integration with ExecutionEngine

```python
# execution_engine.py:751-788 (_check_cost_thresholds)

async def _check_cost_thresholds(self, execution: ProcessExecution) -> None:
    """Check if execution cost exceeds configured thresholds."""
    if not self.cost_alert_service:
        return

    if not execution.total_cost or execution.total_cost.amount <= 0:
        return

    alert = self.cost_alert_service.check_execution_cost(
        process_id=str(execution.process_id),
        process_name=execution.process_name,
        execution_id=str(execution.id),
        cost=execution.total_cost.amount,
    )

    if alert:
        logger.warning(
            f"Cost alert triggered for execution {execution.id}: "
            f"${execution.total_cost.amount:.2f} exceeded threshold"
        )
```

---

## API Endpoints

### Analytics Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/processes/{id}/analytics` | Metrics for single process |
| GET | `/api/processes/analytics/all` | Metrics for all processes |
| GET | `/api/processes/analytics/trends` | Trend data over time |
| GET | `/api/processes/{id}/cost-stats` | Cost statistics |

### Alert Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/alerts` | List alerts with filters |
| GET | `/api/alerts/{id}` | Get single alert |
| POST | `/api/alerts/{id}/dismiss` | Dismiss an alert |
| GET | `/api/processes/{id}/thresholds` | Get process thresholds |
| POST | `/api/processes/{id}/thresholds` | Set threshold |
| DELETE | `/api/processes/{id}/thresholds/{type}` | Delete threshold |

### Response Examples

**Process Metrics:**

```json
{
  "process_id": "uuid",
  "process_name": "content-pipeline",
  "execution_count": 150,
  "completed_count": 140,
  "failed_count": 10,
  "running_count": 0,
  "success_rate": 93.3,
  "average_duration_seconds": 120.5,
  "average_cost": "$0.35",
  "total_cost": "$52.50",
  "min_duration_seconds": 45.2,
  "max_duration_seconds": 340.8,
  "min_cost": "$0.10",
  "max_cost": "$1.25"
}
```

**Trend Data:**

```json
{
  "days": 30,
  "daily_trends": [
    {
      "date": "2026-01-15",
      "execution_count": 5,
      "completed_count": 4,
      "failed_count": 1,
      "total_cost": 1.75,
      "success_rate": 80.0
    }
  ],
  "total_executions": 150,
  "total_completed": 140,
  "total_failed": 10,
  "overall_success_rate": 93.3,
  "total_cost": "$52.50"
}
```

**Cost Alert:**

```json
{
  "id": "alert-uuid",
  "process_id": "process-uuid",
  "process_name": "content-pipeline",
  "execution_id": "execution-uuid",
  "threshold_type": "per_execution",
  "threshold_amount": 0.50,
  "actual_amount": 1.25,
  "currency": "USD",
  "severity": "critical",
  "status": "active",
  "message": "Execution cost $1.25 exceeded threshold $0.50",
  "created_at": "2026-01-16T10:30:00Z"
}
```

---

## Database Schema

### cost_thresholds Table

```sql
CREATE TABLE cost_thresholds (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL,
    threshold_type TEXT NOT NULL,     -- per_execution, daily, weekly
    threshold_amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(process_id, threshold_type)
);
```

### cost_alerts Table

```sql
CREATE TABLE cost_alerts (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL,
    process_name TEXT NOT NULL,
    execution_id TEXT,                 -- NULL for daily/weekly alerts
    threshold_type TEXT NOT NULL,
    threshold_amount REAL NOT NULL,
    actual_amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    severity TEXT DEFAULT 'warning',   -- warning, critical
    status TEXT DEFAULT 'active',      -- active, dismissed
    message TEXT,
    created_at TEXT NOT NULL,
    dismissed_at TEXT,
    dismissed_by TEXT
);
```

---

## Frontend Components

### ProcessDashboard.vue

Dashboard for viewing analytics across all processes.

| Section | Description |
|---------|-------------|
| Summary Cards | Total executions, overall success rate, total cost |
| Trend Chart | Line chart showing daily executions/costs |
| Process Table | Per-process metrics with sorting |
| Step Performance | Slowest and most expensive steps |

### TrendChart.vue

Chart.js-based visualization component.

```vue
<template>
  <canvas ref="chartCanvas"></canvas>
</template>

<script setup>
const props = defineProps({
  data: Object,
  type: { type: String, default: 'executions' }  // executions | costs
})

function renderChart() {
  // Uses Chart.js to render line/bar chart
  // X-axis: dates
  // Y-axis: count or cost
}
</script>
```

### Alerts.vue

Alert management interface.

| Section | Description |
|---------|-------------|
| Filter | Status dropdown (active/dismissed) |
| Stats | Active alert count |
| Alert List | Cards with severity badge, dismiss button |

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- Processes with completed executions
- Configured cost thresholds

### Test Cases

1. **View process metrics**
   - Action: Open ProcessDashboard
   - Expected: Shows correct counts, rates, costs

2. **View trend chart**
   - Action: Select 30-day period
   - Expected: Chart shows daily data points

3. **Cost alert generation**
   - Action: Run process that exceeds threshold
   - Expected: Alert created, appears in Alerts view

4. **Dismiss alert**
   - Action: Click dismiss on active alert
   - Expected: Status changes to dismissed

5. **Step performance**
   - Action: View step performance section
   - Expected: Shows slowest and most expensive steps

---

## Related Flows

- [process-execution.md](./process-execution.md) - Cost capture during execution
- [process-monitoring.md](./process-monitoring.md) - Dashboard integration

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-16 | Initial creation |
