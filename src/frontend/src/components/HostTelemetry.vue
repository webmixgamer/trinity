<script setup>
import { ref, toRaw, onMounted, onUnmounted, nextTick, watch } from 'vue'
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'

const API_BASE = import.meta.env.VITE_API_BASE || ''

// Chart containers
const cpuChartEl = ref(null)
const memChartEl = ref(null)
const containerCpuChartEl = ref(null)

// uPlot instances
let cpuChart = null
let memChart = null
let containerCpuChart = null

// History data (last 60 samples = 5 minutes at 5s intervals)
const MAX_POINTS = 60
const timestamps = ref([])
const cpuHistory = ref([])
const memHistory = ref([])
const containerCpuHistory = ref([])

// Current stats
const hostStats = ref(null)
const containerStats = ref(null)
const loading = ref(true)
const error = ref(null)

let pollInterval = null

// Initialize with empty data
function initHistory() {
  const now = Date.now() / 1000
  for (let i = MAX_POINTS - 1; i >= 0; i--) {
    timestamps.value.push(now - (i * 5))
    cpuHistory.value.push(null)
    memHistory.value.push(null)
    containerCpuHistory.value.push(null)
  }
}

// Minimal chart options - small sparkline style (compact for inline display)
function createChartOpts(color, yMax = 100) {
  return {
    width: 60,
    height: 20,
    padding: [2, 0, 2, 0],
    cursor: { show: false },
    legend: { show: false },
    select: { show: false },
    scales: {
      x: { time: false },
      y: { min: 0, max: yMax, range: [0, yMax] }
    },
    axes: [
      { show: false },
      { show: false }
    ],
    series: [
      {},
      {
        stroke: color,
        width: 1.5,
        fill: color + '30',
        spanGaps: true,
        points: { show: false }
      }
    ]
  }
}

function initCharts() {
  if (!cpuChartEl.value || !memChartEl.value) return

  // Clear any existing content
  cpuChartEl.value.innerHTML = ''
  memChartEl.value.innerHTML = ''
  if (containerCpuChartEl.value) containerCpuChartEl.value.innerHTML = ''

  // Convert Vue reactive arrays to raw arrays for uPlot
  const data = [toRaw(timestamps.value), toRaw(cpuHistory.value)]
  cpuChart = new uPlot(createChartOpts('#3b82f6', 100), data, cpuChartEl.value)

  const memData = [toRaw(timestamps.value), toRaw(memHistory.value)]
  memChart = new uPlot(createChartOpts('#a855f7', 100), memData, memChartEl.value)

  if (containerCpuChartEl.value) {
    const containerData = [toRaw(timestamps.value), toRaw(containerCpuHistory.value)]
    containerCpuChart = new uPlot(createChartOpts('#f97316', 200), containerData, containerCpuChartEl.value)
  }
}

function updateCharts() {
  if (cpuChart) cpuChart.setData([toRaw(timestamps.value), toRaw(cpuHistory.value)])
  if (memChart) memChart.setData([toRaw(timestamps.value), toRaw(memHistory.value)])
  if (containerCpuChart) containerCpuChart.setData([toRaw(timestamps.value), toRaw(containerCpuHistory.value)])
}

async function fetchStats() {
  try {
    // Fetch host stats
    const hostRes = await fetch(`${API_BASE}/api/telemetry/host`, {
      signal: AbortSignal.timeout(3000)
    }).catch(() => null)

    if (hostRes?.ok) {
      hostStats.value = await hostRes.json()

      const now = Date.now() / 1000
      timestamps.value.push(now)
      cpuHistory.value.push(hostStats.value.cpu?.percent ?? null)
      memHistory.value.push(hostStats.value.memory?.percent ?? null)

      if (timestamps.value.length > MAX_POINTS) {
        timestamps.value.shift()
        cpuHistory.value.shift()
        memHistory.value.shift()
      }
    }

    // Fetch container stats
    const containerRes = await fetch(`${API_BASE}/api/telemetry/containers`, {
      signal: AbortSignal.timeout(5000)
    }).catch(() => null)

    if (containerRes?.ok) {
      containerStats.value = await containerRes.json()

      containerCpuHistory.value.push(containerStats.value.total_cpu_percent ?? null)
      if (containerCpuHistory.value.length > MAX_POINTS) {
        containerCpuHistory.value.shift()
      }
    }

    updateCharts()
    loading.value = false
    error.value = null
  } catch (e) {
    loading.value = false
    error.value = e.message
  }
}

function formatPercent(pct) {
  return pct?.toFixed(0) || '0'
}

function formatMemory(usedGb, totalGb) {
  if (!usedGb || !totalGb) return '0/0G'
  return `${usedGb.toFixed(1)}/${totalGb.toFixed(0)}G`
}

function getColorClass(percent) {
  if (percent === null || percent === undefined) return 'text-gray-400'
  if (percent < 50) return 'text-green-500 dark:text-green-400'
  if (percent < 75) return 'text-yellow-500 dark:text-yellow-400'
  if (percent < 90) return 'text-orange-500 dark:text-orange-400'
  return 'text-red-500 dark:text-red-400'
}

// Watch for loading to become false, then init charts
watch(loading, async (newVal, oldVal) => {
  if (oldVal === true && newVal === false) {
    await nextTick()
    initCharts()
  }
})

onMounted(async () => {
  initHistory()
  await fetchStats()
  pollInterval = setInterval(fetchStats, 5000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
  if (cpuChart) cpuChart.destroy()
  if (memChart) memChart.destroy()
  if (containerCpuChart) containerCpuChart.destroy()
})
</script>

<template>
  <div class="host-telemetry">
    <template v-if="!loading">
      <!-- CPU -->
      <span class="stat-item">
        <span class="dot bg-blue-500"></span>
        <span class="stat-label">CPU</span>
        <span ref="cpuChartEl" class="chart-box"></span>
        <span class="stat-value" :class="getColorClass(hostStats?.cpu?.percent)">{{ formatPercent(hostStats?.cpu?.percent) }}%</span>
      </span>

      <span class="text-gray-300 dark:text-gray-600">·</span>

      <!-- Memory -->
      <span class="stat-item">
        <span class="dot bg-purple-500"></span>
        <span class="stat-label">Mem</span>
        <span ref="memChartEl" class="chart-box"></span>
        <span class="stat-value" :class="getColorClass(hostStats?.memory?.percent)">{{ formatMemory(hostStats?.memory?.used_gb, hostStats?.memory?.total_gb) }}</span>
      </span>

      <span class="text-gray-300 dark:text-gray-600">·</span>

      <!-- Disk -->
      <span class="stat-item">
        <span class="dot bg-green-500"></span>
        <span class="stat-label">Disk</span>
        <span class="disk-bar">
          <span
            class="disk-fill"
            :style="{ width: `${hostStats?.disk?.percent || 0}%` }"
            :class="hostStats?.disk?.percent > 90 ? 'bg-red-500' : hostStats?.disk?.percent > 75 ? 'bg-orange-500' : 'bg-green-500'"
          ></span>
        </span>
        <span class="stat-value" :class="getColorClass(hostStats?.disk?.percent)">{{ formatPercent(hostStats?.disk?.percent) }}%</span>
      </span>
    </template>
  </div>
</template>

<style scoped>
.host-telemetry {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
}

.stat-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.stat-label {
  color: #6b7280;
}

.dark .stat-label {
  color: #9ca3af;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.chart-box {
  display: inline-block;
  width: 60px;
  height: 20px;
  background: rgba(107, 114, 128, 0.1);
  border-radius: 2px;
  overflow: hidden;
  vertical-align: middle;
}

.stat-value {
  font-weight: 600;
  font-family: ui-monospace, monospace;
  font-size: 12px;
}

.disk-bar {
  display: inline-block;
  width: 50px;
  height: 6px;
  background: rgba(107, 114, 128, 0.2);
  border-radius: 3px;
  overflow: hidden;
  vertical-align: middle;
}

.disk-fill {
  display: block;
  height: 100%;
  transition: width 0.3s ease;
}

/* uPlot canvas styling */
:deep(.uplot) {
  width: 100% !important;
}

:deep(.u-wrap) {
  width: 100% !important;
}

:deep(.u-over),
:deep(.u-under) {
  width: 100% !important;
}

/* Dark mode adjustments */
.dark .chart-box {
  background: rgba(55, 65, 81, 0.5);
}

.dark .disk-bar {
  background: rgba(55, 65, 81, 0.5);
}
</style>
