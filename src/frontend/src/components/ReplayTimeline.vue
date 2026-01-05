<template>
  <div class="replay-timeline bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
    <!-- Header with playback controls -->
    <div class="flex items-center justify-between px-4 py-2 border-b border-gray-100 dark:border-gray-700">
      <!-- Playback Controls -->
      <div class="flex items-center space-x-3">
        <button
          @click="$emit('play')"
          :disabled="isPlaying || totalEvents === 0"
          class="p-1.5 rounded hover:bg-green-100 dark:hover:bg-green-900/30 disabled:opacity-40"
          title="Play"
        >
          <svg class="w-4 h-4 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
            <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
          </svg>
        </button>
        <button
          @click="$emit('pause')"
          :disabled="!isPlaying"
          class="p-1.5 rounded hover:bg-yellow-100 dark:hover:bg-yellow-900/30 disabled:opacity-40"
          title="Pause"
        >
          <svg class="w-4 h-4 text-yellow-600 dark:text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
            <path d="M5.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75A.75.75 0 007.25 3h-1.5zM12.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75a.75.75 0 00-.75-.75h-1.5z" />
          </svg>
        </button>
        <button
          @click="$emit('stop')"
          class="p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30"
          title="Stop"
        >
          <svg class="w-4 h-4 text-red-600 dark:text-red-400" fill="currentColor" viewBox="0 0 20 20">
            <path d="M5.25 3A2.25 2.25 0 003 5.25v9.5A2.25 2.25 0 005.25 17h9.5A2.25 2.25 0 0017 14.75v-9.5A2.25 2.25 0 0014.75 3h-9.5z" />
          </svg>
        </button>

        <select
          :value="replaySpeed"
          @change="$emit('speed-change', $event)"
          class="text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 dark:text-gray-200"
        >
          <option :value="1">1x</option>
          <option :value="2">2x</option>
          <option :value="5">5x</option>
          <option :value="10">10x</option>
          <option :value="20">20x</option>
          <option :value="50">50x</option>
        </select>

        <!-- Zoom Controls -->
        <div class="flex items-center space-x-1 ml-4 border-l border-gray-300 dark:border-gray-600 pl-4">
          <button
            @click="zoomOut"
            class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400"
            title="Zoom out"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
            </svg>
          </button>
          <input
            type="range"
            :value="zoomLevel"
            @input="zoomLevel = parseFloat($event.target.value)"
            min="0.5"
            max="20"
            step="0.5"
            class="w-20 h-1 accent-blue-500"
            title="Zoom level"
          />
          <button
            @click="zoomIn"
            class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400"
            title="Zoom in"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
          </button>
          <span class="text-xs text-gray-400 dark:text-gray-500 ml-1 w-8">{{ Math.round(zoomLevel * 100) }}%</span>
        </div>

        <!-- Hide inactive toggle -->
        <div class="flex items-center space-x-1 ml-4 border-l border-gray-300 dark:border-gray-600 pl-4">
          <label class="flex items-center space-x-1.5 text-xs text-gray-500 dark:text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              v-model="hideInactiveAgents"
              class="w-3 h-3 rounded border-gray-300 dark:border-gray-600 text-blue-500 focus:ring-blue-500"
            />
            <span>Active only</span>
          </label>
        </div>
      </div>

      <!-- Stats -->
      <div class="flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
        <span>{{ currentEventIndex }}/{{ totalEvents }} events</span>
        <span>{{ formatDuration(replayElapsedMs) }} / {{ formatDuration(totalDuration) }}</span>
      </div>
    </div>

    <!-- Timeline Grid with scroll -->
    <div
      class="timeline-scroll-container overflow-auto"
      ref="timelineContainer"
      @wheel="handleWheel"
    >
      <div class="relative" :style="{ width: timelineWidth + 'px', height: timelineHeight + 'px' }">
        <!-- Time scale header (sticky) -->
        <div
          class="sticky top-0 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 z-20"
          :style="{ height: headerHeight + 'px' }"
        >
          <div class="flex">
            <!-- Label spacer -->
            <div :style="{ width: labelWidth + 'px', flexShrink: 0 }" class="bg-gray-50 dark:bg-gray-800"></div>
            <!-- Time header -->
            <svg :width="actualGridWidth" :height="headerHeight" class="overflow-visible">
              <g v-for="(tick, i) in timeTicks" :key="'tick-' + i">
                <line
                  :x1="tick.x"
                  y1="0"
                  :x2="tick.x"
                  :y2="headerHeight"
                  stroke="#e5e7eb"
                  stroke-width="1"
                  class="dark:stroke-gray-600"
                />
                <text
                  :x="tick.x"
                  :y="headerHeight - 4"
                  text-anchor="middle"
                  class="fill-gray-500 dark:fill-gray-400"
                  font-size="10"
                >
                  {{ tick.label }}
                </text>
              </g>
              <!-- "Now" marker in header -->
              <g v-if="nowX >= 0">
                <line
                  :x1="nowX"
                  y1="0"
                  :x2="nowX"
                  :y2="headerHeight"
                  stroke="#10b981"
                  stroke-width="1"
                  stroke-dasharray="2,2"
                />
                <text
                  :x="nowX"
                  :y="10"
                  text-anchor="middle"
                  class="fill-emerald-500"
                  font-size="8"
                >
                  now
                </text>
              </g>
            </svg>
          </div>
        </div>

        <!-- Agent rows -->
        <div class="relative flex">
          <!-- Sticky agent labels -->
          <div
            class="sticky left-0 z-10 bg-white dark:bg-gray-800"
            :style="{ width: labelWidth + 'px', flexShrink: 0 }"
          >
            <div
              v-for="(row, i) in filteredAgentRows"
              :key="'label-' + i"
              class="flex items-center px-2 text-xs font-medium truncate border-b border-gray-100 dark:border-gray-700"
              :style="{ height: rowHeight + 'px' }"
            >
              <span
                class="w-2 h-2 rounded-full mr-2 flex-shrink-0"
                :class="[
                  row.isExecuting ? 'bg-green-500 animate-pulse' : (row.status === 'running' ? 'bg-green-700 opacity-60' : 'bg-gray-400')
                ]"
              ></span>
              <span class="truncate text-gray-700 dark:text-gray-300" :title="row.name">
                {{ row.name }}
              </span>
            </div>
          </div>

          <!-- Grid content -->
          <svg
            :width="actualGridWidth"
            :height="filteredAgentRows.length * rowHeight"
          >
            <!-- Vertical grid lines -->
            <g v-for="(tick, i) in timeTicks" :key="'grid-' + i">
              <line
                :x1="tick.x"
                y1="0"
                :x2="tick.x"
                :y2="filteredAgentRows.length * rowHeight"
                :stroke="tick.major ? '#d1d5db' : '#e5e7eb'"
                :stroke-width="tick.major ? 1 : 0.5"
                class="dark:stroke-gray-600"
                :stroke-dasharray="tick.major ? '0' : '2,2'"
              />
            </g>

            <!-- Horizontal row separators -->
            <g v-for="(row, i) in filteredAgentRows" :key="'row-line-' + i">
              <line
                x1="0"
                :y1="(i + 1) * rowHeight"
                :x2="actualGridWidth"
                :y2="(i + 1) * rowHeight"
                stroke="#f3f4f6"
                stroke-width="1"
                class="dark:stroke-gray-700"
              />
            </g>

            <!-- Activity bars for each agent -->
            <g v-for="(row, rowIndex) in filteredAgentRows" :key="'activities-' + rowIndex">
              <rect
                v-for="(activity, actIndex) in row.activities"
                :key="'act-' + rowIndex + '-' + actIndex"
                :x="activity.x"
                :y="rowIndex * rowHeight + (rowHeight - barHeight) / 2"
                :width="Math.max(activity.width, 4)"
                :height="barHeight"
                :fill="activity.active ? '#3b82f6' : '#93c5fd'"
                :opacity="activity.active ? 1 : 0.7"
                rx="2"
                class="transition-all duration-300"
              />
            </g>

            <!-- Communication arrows -->
            <g v-for="(arrow, i) in communicationArrows" :key="'arrow-' + i">
              <line
                :x1="arrow.x"
                :y1="arrow.y1"
                :x2="arrow.x"
                :y2="arrow.y2"
                :stroke="arrow.active ? '#06b6d4' : '#67e8f9'"
                :stroke-width="arrow.active ? 1.5 : 1"
                :opacity="arrow.active ? 1 : 0.6"
                class="transition-all duration-300"
              />
              <!-- Smaller arrow head -->
              <polygon
                :points="getArrowHead(arrow)"
                :fill="arrow.active ? '#06b6d4' : '#67e8f9'"
                :opacity="arrow.active ? 1 : 0.6"
              />
            </g>

            <!-- "Now" vertical line -->
            <line
              v-if="nowX >= 0"
              :x1="nowX"
              y1="0"
              :x2="nowX"
              :y2="filteredAgentRows.length * rowHeight"
              stroke="#10b981"
              stroke-width="1"
              stroke-dasharray="4,4"
              opacity="0.6"
            />

            <!-- Current time cursor (playback position) -->
            <line
              v-if="currentTimeX >= 0"
              :x1="currentTimeX"
              y1="0"
              :x2="currentTimeX"
              :y2="filteredAgentRows.length * rowHeight"
              stroke="#ef4444"
              stroke-width="2"
              class="transition-all duration-100"
            />
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'

const props = defineProps({
  agents: { type: Array, default: () => [] },
  events: { type: Array, default: () => [] },
  timelineStart: { type: String, default: null },
  timelineEnd: { type: String, default: null },
  currentEventIndex: { type: Number, default: 0 },
  totalEvents: { type: Number, default: 0 },
  totalDuration: { type: Number, default: 0 },
  replayElapsedMs: { type: Number, default: 0 },
  replaySpeed: { type: Number, default: 10 },
  isPlaying: { type: Boolean, default: false }
})

defineEmits(['play', 'pause', 'stop', 'speed-change', 'seek'])

const timelineContainer = ref(null)
const zoomLevel = ref(1)
const hideInactiveAgents = ref(false)

// Smooth playback cursor tracking
const localElapsedMs = ref(0)
const playbackStartTime = ref(0)
const playbackStartElapsed = ref(0)
let animationFrame = null

function updateCursor() {
  if (props.isPlaying && playbackStartTime.value > 0) {
    const wallClockElapsed = Date.now() - playbackStartTime.value
    localElapsedMs.value = playbackStartElapsed.value + wallClockElapsed
    animationFrame = requestAnimationFrame(updateCursor)
  }
}

watch(() => props.isPlaying, (playing) => {
  if (playing) {
    // Store when we started and the elapsed value at that time
    playbackStartTime.value = Date.now()
    playbackStartElapsed.value = props.replayElapsedMs
    localElapsedMs.value = props.replayElapsedMs
    updateCursor()
  } else {
    if (animationFrame) {
      cancelAnimationFrame(animationFrame)
      animationFrame = null
    }
    // Sync to actual elapsed when paused
    localElapsedMs.value = props.replayElapsedMs
  }
})

// Sync when replayElapsedMs changes externally (e.g., stop/reset)
watch(() => props.replayElapsedMs, (newVal) => {
  if (!props.isPlaying) {
    localElapsedMs.value = newVal
  }
})

onUnmounted(() => {
  if (animationFrame) {
    cancelAnimationFrame(animationFrame)
  }
})

// Layout constants
const labelWidth = 150
const headerHeight = 24
const rowHeight = 32
const barHeight = 16
const baseGridWidth = 800

// Computed grid width based on zoom
const actualGridWidth = computed(() => baseGridWidth * zoomLevel.value)

const timelineWidth = computed(() => labelWidth + actualGridWidth.value)
// Note: timelineHeight will be recalculated after filteredAgentRows is defined
const timelineHeight = computed(() => headerHeight + (filteredAgentRows.value.length * rowHeight))

// Zoom controls
function zoomIn() {
  const current = parseFloat(zoomLevel.value) || 1
  zoomLevel.value = Math.min(20, current + 0.5)
}

function zoomOut() {
  const current = parseFloat(zoomLevel.value) || 1
  zoomLevel.value = Math.max(0.5, current - 0.5)
}

function handleWheel(event) {
  // Ctrl+wheel for zoom
  if (event.ctrlKey || event.metaKey) {
    event.preventDefault()
    if (event.deltaY < 0) {
      zoomIn()
    } else {
      zoomOut()
    }
  }
}

// Parse timeline bounds - extend to "now" if needed
const startTime = computed(() => props.timelineStart ? new Date(props.timelineStart).getTime() : 0)
const endTime = computed(() => {
  const eventEnd = props.timelineEnd ? new Date(props.timelineEnd).getTime() : 0
  const now = Date.now()
  // Use whichever is later: last event or now
  return Math.max(eventEnd, now)
})
const duration = computed(() => endTime.value - startTime.value)

// Position of "now" on the timeline
const nowX = computed(() => {
  if (!duration.value || !startTime.value) return -1
  const now = Date.now()
  if (now < startTime.value || now > endTime.value) return -1
  return ((now - startTime.value) / duration.value) * actualGridWidth.value
})

// Generate time ticks (15 min intervals)
const timeTicks = computed(() => {
  // Guard: Need valid timeline bounds to generate ticks
  // If startTime is 0 (no timelineStart prop), the loop would run from epoch to now = millions of iterations!
  if (!duration.value || !startTime.value || !endTime.value) return []

  const ticks = []
  const intervalMs = 15 * 60 * 1000 // 15 minutes
  const start = startTime.value
  const end = endTime.value

  // Safety: Limit to reasonable number of ticks (max 7 days = 672 ticks)
  const maxTicks = 700
  let tickCount = 0

  // Round start to nearest 15 min
  const firstTick = Math.ceil(start / intervalMs) * intervalMs

  for (let time = firstTick; time <= end && tickCount < maxTicks; time += intervalMs) {
    const x = ((time - start) / duration.value) * actualGridWidth.value
    const date = new Date(time)
    const hours = date.getHours()
    const minutes = date.getMinutes()
    const major = minutes === 0 // Major tick at hour marks

    ticks.push({
      x,
      time,
      label: `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`,
      major
    })
    tickCount++
  }

  return ticks
})

// Create agent rows with activity data
const agentRows = computed(() => {
  // Guard: Need valid timeline data
  if (!props.agents.length || !startTime.value || !duration.value) return []

  // Group events by agent
  const agentActivityMap = new Map()

  props.events.forEach((event, index) => {
    // Source agent activity
    if (!agentActivityMap.has(event.source_agent)) {
      agentActivityMap.set(event.source_agent, [])
    }
    agentActivityMap.get(event.source_agent).push({
      time: new Date(event.timestamp).getTime(),
      type: 'send',
      eventIndex: index
    })

    // Target agent activity
    if (!agentActivityMap.has(event.target_agent)) {
      agentActivityMap.set(event.target_agent, [])
    }
    agentActivityMap.get(event.target_agent).push({
      time: new Date(event.timestamp).getTime(),
      type: 'receive',
      eventIndex: index
    })
  })

  return props.agents.map(agent => {
    const activities = agentActivityMap.get(agent.name) || []

    // Convert activities to bars
    const bars = activities.map(act => {
      const x = ((act.time - startTime.value) / duration.value) * actualGridWidth.value
      // Check if this activity is at or before current playback position
      const chronoIndex = props.events.length - 1 - act.eventIndex
      const active = chronoIndex < props.currentEventIndex

      return {
        x: Math.max(0, x - 2), // Center the bar on the time
        width: 8, // Fixed width bar
        active,
        type: act.type
      }
    })

    // Check if agent has any activity
    const hasActivity = bars.length > 0

    // Check if agent is currently executing (has activity around current playback position)
    const isExecuting = bars.some(bar => bar.active) && props.isPlaying

    return {
      name: agent.name,
      status: agent.status,
      activities: bars,
      hasActivity,
      isExecuting
    }
  })
})

// Filtered agent rows based on hideInactiveAgents toggle
const filteredAgentRows = computed(() => {
  if (!hideInactiveAgents.value) {
    return agentRows.value
  }
  return agentRows.value.filter(row => row.hasActivity)
})

// Create communication arrows based on filtered agent rows
const communicationArrows = computed(() => {
  // Guard: Need valid timeline data
  if (!props.events.length || !filteredAgentRows.value.length || !startTime.value || !duration.value) return []

  // Build index map from filtered rows
  const agentIndexMap = new Map()
  filteredAgentRows.value.forEach((row, i) => {
    agentIndexMap.set(row.name, i)
  })

  // Reverse to get chronological order
  const chronoEvents = [...props.events].reverse()

  return chronoEvents.map((event, chronoIndex) => {
    const sourceIndex = agentIndexMap.get(event.source_agent)
    const targetIndex = agentIndexMap.get(event.target_agent)

    if (sourceIndex === undefined || targetIndex === undefined) return null

    const time = new Date(event.timestamp).getTime()
    const x = ((time - startTime.value) / duration.value) * actualGridWidth.value

    const y1 = sourceIndex * rowHeight + rowHeight / 2
    const y2 = targetIndex * rowHeight + rowHeight / 2

    // Check if this event is at or before current playback position
    const active = chronoIndex < props.currentEventIndex

    return {
      x,
      y1,
      y2,
      active,
      direction: targetIndex > sourceIndex ? 'down' : 'up'
    }
  }).filter(a => a !== null)
})

// Current time cursor position - smooth interpolation based on elapsed time
const currentTimeX = computed(() => {
  // Guard: Need valid timeline data
  if (!props.events.length || !duration.value || !startTime.value) return -1

  // Get the first event time as the replay start reference
  const chronoEvents = [...props.events].reverse()
  const firstEventTime = new Date(chronoEvents[0].timestamp).getTime()

  // Calculate current simulated time: wall-clock elapsed * replay speed = simulated elapsed
  const simulatedElapsedMs = localElapsedMs.value * props.replaySpeed
  const currentSimulatedTime = firstEventTime + simulatedElapsedMs

  // Clamp to timeline bounds
  if (currentSimulatedTime < startTime.value) return -1

  return ((currentSimulatedTime - startTime.value) / duration.value) * actualGridWidth.value
})

// Smaller arrow head
function getArrowHead(arrow) {
  const size = 2 // Reduced from 4
  const x = arrow.x
  const y = arrow.y2

  if (arrow.direction === 'down') {
    return `${x},${y} ${x-size},${y-size*2} ${x+size},${y-size*2}`
  } else {
    return `${x},${y} ${x-size},${y+size*2} ${x+size},${y+size*2}`
  }
}

function formatDuration(ms) {
  if (!ms) return '00:00'
  const minutes = Math.floor(ms / 60000)
  const seconds = Math.floor((ms % 60000) / 1000)
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
}
</script>

<style scoped>
.replay-timeline {
  max-height: 320px;
}

.timeline-scroll-container {
  max-height: 280px;
}

/* Scrollbar styling for both axes */
.timeline-scroll-container::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.timeline-scroll-container::-webkit-scrollbar-track {
  background: #f1f5f9;
}

.dark .timeline-scroll-container::-webkit-scrollbar-track {
  background: #374151;
}

.timeline-scroll-container::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

.dark .timeline-scroll-container::-webkit-scrollbar-thumb {
  background: #4b5563;
}

.timeline-scroll-container::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.dark .timeline-scroll-container::-webkit-scrollbar-thumb:hover {
  background: #6b7280;
}

.timeline-scroll-container::-webkit-scrollbar-corner {
  background: #f1f5f9;
}

.dark .timeline-scroll-container::-webkit-scrollbar-corner {
  background: #374151;
}

/* Zoom slider styling */
input[type="range"] {
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
  cursor: pointer;
}

input[type="range"]::-webkit-slider-runnable-track {
  background: #e5e7eb;
  height: 4px;
  border-radius: 2px;
}

.dark input[type="range"]::-webkit-slider-runnable-track {
  background: #4b5563;
}

input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  margin-top: -4px;
  background-color: #3b82f6;
  height: 12px;
  width: 12px;
  border-radius: 50%;
}
</style>
