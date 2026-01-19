# Feature: Process Monitoring

> Real-time monitoring of process executions via UI with WebSocket updates and dashboard analytics

---

## Overview

Process Monitoring provides real-time visibility into process executions through the UI. Users can watch executions progress, view step outputs, track costs, and see analytics across all processes.

**Key Capabilities:**
- Real-time updates via WebSocket connection
- Step-by-step execution timeline
- Output viewer for each step
- Breadcrumb navigation for nested sub-processes
- Analytics dashboard with trends and metrics

---

## Entry Points

- **UI**: `ProcessList.vue` -> Click execution count -> `ExecutionList.vue`
- **UI**: `ExecutionList.vue` -> Click execution -> `ProcessExecutionDetail.vue`
- **UI**: Nav bar "Dashboard" -> `ProcessDashboard.vue`
- **API**: `GET /api/executions` - List executions
- **API**: `GET /api/executions/{id}` - Get execution detail
- **WebSocket**: `/ws` - Real-time event stream

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                            │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  ProcessExecutionDetail.vue                                              │    │
│  │  ├── Header (status, process name, ID, breadcrumbs)                     │    │
│  │  ├── Info cards (triggered_by, started_at, duration, cost)              │    │
│  │  ├── Step timeline (vertical list with status icons)                    │    │
│  │  ├── Step output viewer (expandable per step)                           │    │
│  │  └── WebSocket connection indicator (Live/Polling)                      │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  ProcessDashboard.vue                                                    │    │
│  │  ├── Summary cards (total executions, success rate, avg cost)           │    │
│  │  ├── TrendChart.vue (daily executions, costs over time)                 │    │
│  │  └── Per-process metrics table                                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│                          │ WebSocket                                             │
└──────────────────────────┼──────────────────────────────────────────────────────┘
                           │
                           │ /ws connection
                           ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Backend                                             │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  main.py - WebSocket endpoint                                            │    │
│  │  ├── ConnectionManager                                                   │    │
│  │  │   ├── connect(websocket)                                              │    │
│  │  │   ├── disconnect(websocket)                                           │    │
│  │  │   └── broadcast(message)                                              │    │
│  │  └── /ws endpoint handles connections                                    │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      │ receives events from                      │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  events/websocket_publisher.py - WebSocketEventPublisher                 │    │
│  │  ├── register_with_event_bus()  - Subscribe to domain events            │    │
│  │  ├── handle_event()             - Convert and broadcast                  │    │
│  │  └── _event_to_message()        - Serialize event for WebSocket         │    │
│  └───────────────────────────────────┬─────────────────────────────────────┘    │
│                                      │                                           │
│                                      │ subscribed to                             │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  events/bus.py - InMemoryEventBus                                        │    │
│  │  ├── subscribe(event_type, handler)                                      │    │
│  │  └── publish(event)             - Notify all handlers                    │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                      ▲                                           │
│                                      │ publishes events                          │
│  ┌───────────────────────────────────┴─────────────────────────────────────┐    │
│  │  engine/execution_engine.py - ExecutionEngine                            │    │
│  │  └── _publish_event()           - Emit domain events                     │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## UI Components

### ProcessExecutionDetail.vue

The main view for monitoring a single execution.

**Sections:**

| Section | Lines | Description |
|---------|-------|-------------|
| Breadcrumbs | 8-24 | Navigation for nested sub-process executions |
| Header | 38-145 | Status badge, process name, retry/parent links |
| Info Cards | 147-200 | Triggered by, started, duration, cost |
| Step Timeline | 210-350 | Vertical list of steps with status |
| Step Output | 360-450 | Expandable JSON viewer per step |
| Actions | 115-143 | Cancel, Retry, Refresh buttons |

**Key Features:**

```vue
<!-- Status Badge -->
<span :class="getStatusClasses(execution.status)">
  <span>{{ getStatusIcon(execution.status) }}</span>
  <span class="capitalize">{{ execution.status }}</span>
</span>

<!-- WebSocket indicator -->
<div v-if="execution.status === 'running'">
  <span :class="wsConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'"></span>
  <span>{{ wsConnected ? 'Live' : 'Polling' }}</span>
</div>

<!-- Breadcrumbs for sub-processes -->
<nav v-if="breadcrumbs.length > 1">
  <template v-for="(crumb, index) in breadcrumbs">
    <router-link :to="`/executions/${crumb.id}`">
      {{ crumb.process_name }}
    </router-link>
  </template>
</nav>
```

### ProcessDashboard.vue

Analytics dashboard for all processes.

**Sections:**

| Section | Description |
|---------|-------------|
| Summary Cards | Total executions, success rate, total cost, avg duration |
| Trend Chart | Daily execution counts and costs over selected period |
| Process Table | Per-process metrics with sorting |

**Data Flow:**

```javascript
// Load dashboard data
async function loadDashboard() {
  // Get all process metrics
  const metrics = await api.get('/api/processes/analytics/all')

  // Get trend data
  const trends = await api.get('/api/processes/analytics/trends', {
    params: { days: selectedDays.value }
  })

  allMetrics.value = metrics.processes
  trendData.value = trends
}
```

### TrendChart.vue

Visualization component for execution trends.

```vue
<template>
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script setup>
import { Chart } from 'chart.js/auto'

const props = defineProps({
  data: { type: Object, required: true },
  type: { type: String, default: 'executions' } // executions | costs
})

// Render chart on data change
watch(() => props.data, () => {
  renderChart()
})
</script>
```

---

## WebSocket Events

### Event Flow

```
ExecutionEngine                  EventBus                WebSocketPublisher           Frontend
---------------                  --------                ------------------           --------
_execute_step() completes
publish(StepCompleted)      →    notify handlers    →    handle_event()
                                                         _event_to_message()
                                                         broadcast(json)         →    onmessage()
                                                                                      Update execution state
```

### Event Types

| Event Type | WebSocket Message | UI Behavior |
|------------|-------------------|-------------|
| `process_started` | `{type: "process_event", event_type: "process_started", ...}` | Add to active list |
| `process_completed` | `{..., duration_seconds: N}` | Update status, show completion |
| `process_failed` | `{..., error: "msg", failed_step_id: "id"}` | Show error, highlight step |
| `step_started` | `{..., step_id: "id"}` | Set step to "running" |
| `step_completed` | `{..., step_id: "id", duration_seconds: N}` | Set step to "completed" |
| `step_failed` | `{..., step_id: "id", error: "msg"}` | Set step to "failed", show error |
| `approval_requested` | `{..., step_id: "id", approvers: [...]}` | Show approval indicator |
| `compensation_started` | `{..., compensation_count: N}` | Show rollback progress |

### WebSocket Message Format

```json
{
  "type": "process_event",
  "event_type": "step_completed",
  "timestamp": "2026-01-16T10:30:45.123Z",
  "execution_id": "uuid-of-execution",
  "step_id": "research",
  "duration_seconds": 45
}
```

### Frontend WebSocket Handling

```javascript
// ProcessExecutionDetail.vue

const wsConnected = ref(false)
let ws = null

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${protocol}//${window.location.host}/ws`)

  ws.onopen = () => {
    wsConnected.value = true
  }

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'process_event' && data.execution_id === execution.value.id) {
      handleProcessEvent(data)
    }
  }

  ws.onclose = () => {
    wsConnected.value = false
    // Fallback to polling
    startPolling()
  }
}

function handleProcessEvent(data) {
  switch (data.event_type) {
    case 'step_started':
      updateStepStatus(data.step_id, 'running')
      break
    case 'step_completed':
      updateStepStatus(data.step_id, 'completed')
      break
    case 'step_failed':
      updateStepStatus(data.step_id, 'failed')
      stepErrors.value[data.step_id] = data.error
      break
    case 'process_completed':
    case 'process_failed':
      // Reload full execution for final state
      loadExecution()
      break
  }
}
```

---

## API Endpoints

### Execution Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/executions` | List executions with filters |
| GET | `/api/executions/{id}` | Get execution detail |
| GET | `/api/executions/{id}/steps` | Get step executions |
| GET | `/api/executions/{id}/steps/{step_id}/output` | Get step output |

### Analytics Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/processes/{id}/analytics` | Metrics for single process |
| GET | `/api/processes/analytics/all` | Metrics for all processes |
| GET | `/api/processes/analytics/trends` | Trend data over time |

### Response Formats

**Execution Detail:**

```json
{
  "id": "execution-uuid",
  "process_id": "process-uuid",
  "process_name": "content-pipeline",
  "process_version": "1.0",
  "status": "running",
  "triggered_by": "manual",
  "started_at": "2026-01-16T10:30:00Z",
  "completed_at": null,
  "total_cost": "$0.15",
  "duration_seconds": 45,
  "input_data": {"topic": "AI"},
  "output_data": {},
  "step_executions": {
    "research": {
      "step_id": "research",
      "status": "completed",
      "started_at": "2026-01-16T10:30:05Z",
      "completed_at": "2026-01-16T10:30:45Z",
      "output": {"response": "..."},
      "cost": "$0.10"
    },
    "write": {
      "step_id": "write",
      "status": "running",
      "started_at": "2026-01-16T10:30:46Z"
    }
  },
  "parent_execution_id": null,
  "child_execution_ids": []
}
```

**Analytics Response:**

```json
{
  "process_id": "process-uuid",
  "process_name": "content-pipeline",
  "execution_count": 150,
  "completed_count": 140,
  "failed_count": 10,
  "success_rate": 0.93,
  "total_cost": "$45.00",
  "average_cost": "$0.30",
  "average_duration_seconds": 120,
  "step_performance": {
    "research": {"avg_duration": 45, "success_rate": 0.98},
    "write": {"avg_duration": 60, "success_rate": 0.95}
  }
}
```

---

## Breadcrumb Navigation

For nested sub-process executions, breadcrumbs show the execution hierarchy.

### Building Breadcrumbs

```javascript
// ProcessExecutionDetail.vue

const breadcrumbs = ref([])

async function buildBreadcrumbs(execution) {
  const crumbs = []

  // Start with current execution
  let current = execution
  crumbs.unshift({
    id: current.id,
    process_name: current.process_name
  })

  // Walk up parent chain
  while (current.parent_execution_id) {
    const parent = await api.get(`/api/executions/${current.parent_execution_id}`)
    crumbs.unshift({
      id: parent.id,
      process_name: parent.process_name
    })
    current = parent
  }

  breadcrumbs.value = crumbs
}
```

### Breadcrumb Display

```
Home > parent-process > child-process > current-process (bold)
         ↑ clickable     ↑ clickable    ↑ current page
```

---

## Polling Fallback

When WebSocket connection fails, the UI falls back to polling.

```javascript
const pollingInterval = ref(null)

function startPolling() {
  if (pollingInterval.value) return

  pollingInterval.value = setInterval(async () => {
    if (execution.value?.status === 'running' || execution.value?.status === 'pending') {
      await loadExecution()
    } else {
      // Stop polling when execution is done
      stopPolling()
    }
  }, 3000) // Poll every 3 seconds
}

function stopPolling() {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
    pollingInterval.value = null
  }
}
```

---

## Status Display

### Status Colors

| Status | Background | Text | Icon |
|--------|------------|------|------|
| `pending` | gray-100 | gray-700 | ⏳ |
| `running` | blue-100 | blue-700 | ▶️ |
| `completed` | green-100 | green-700 | ✅ |
| `failed` | red-100 | red-700 | ❌ |
| `cancelled` | gray-100 | gray-700 | 🚫 |
| `paused` | yellow-100 | yellow-700 | ⏸️ |

### Status Helper Functions

```javascript
function getStatusClasses(status) {
  const classes = {
    pending: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300',
    running: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
    completed: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
    failed: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
    cancelled: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300',
    paused: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
  }
  return classes[status] || classes.pending
}

function getStatusIcon(status) {
  const icons = {
    pending: '⏳',
    running: '▶️',
    completed: '✅',
    failed: '❌',
    cancelled: '🚫',
    paused: '⏸️',
  }
  return icons[status] || '❓'
}
```

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- WebSocket endpoint available at /ws
- At least one process execution

### Test Cases

1. **Real-time step updates**
   - Action: Start execution, watch step timeline
   - Expected: Steps update to running/completed in real-time

2. **WebSocket reconnection**
   - Action: Disconnect network, reconnect
   - Expected: Falls back to polling, reconnects when available

3. **Breadcrumb navigation**
   - Action: View sub-process execution
   - Expected: Breadcrumbs show parent chain, links work

4. **Dashboard metrics**
   - Action: View ProcessDashboard
   - Expected: Shows correct counts, rates, charts

5. **Output viewer**
   - Action: Expand step output
   - Expected: Shows formatted JSON response

---

## Related Flows

- [process-execution.md](./process-execution.md) - How events are generated
- [sub-processes.md](./sub-processes.md) - Parent-child execution details
- [process-analytics.md](./process-analytics.md) - Dashboard metrics details

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-16 | Initial creation |
