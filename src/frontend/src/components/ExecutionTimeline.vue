<template>
  <div class="execution-timeline">
    <!-- Timeline header -->
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-medium text-gray-900 dark:text-white">Execution Steps</h3>
      <div class="text-sm text-gray-500 dark:text-gray-400">
        {{ completedSteps }}/{{ totalSteps }} completed
      </div>
    </div>

    <!-- Progress bar -->
    <div class="mb-6">
      <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
        <div
          class="h-full rounded-full transition-all duration-500"
          :class="progressBarColor"
          :style="{ width: progressPercent + '%' }"
        ></div>
      </div>
    </div>

    <!-- Steps timeline -->
    <div class="space-y-3">
      <div
        v-for="(step, index) in steps"
        :key="step.step_id"
        :class="[
          'border rounded-lg transition-all duration-200',
          expandedStep === step.step_id 
            ? 'border-indigo-300 dark:border-indigo-700 shadow-md' 
            : 'border-gray-200 dark:border-gray-700',
          step.status === 'running' ? 'ring-2 ring-blue-400 dark:ring-blue-500' : '',
        ]"
      >
        <!-- Step header (clickable) -->
        <div
          @click="toggleStep(step.step_id)"
          class="flex items-center gap-4 p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-lg"
        >
          <!-- Step number -->
          <div class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium"
            :class="getStepNumberClasses(step.status)"
          >
            <span v-if="step.status === 'running'" class="animate-spin">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
            </span>
            <span v-else>{{ getStepIcon(step.status) }}</span>
          </div>

          <!-- Step info -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="font-medium text-gray-900 dark:text-white truncate">{{ step.step_id }}</span>
              <span :class="getStatusBadgeClasses(step.status)" class="px-2 py-0.5 rounded text-xs font-medium capitalize">
                {{ step.status }}
              </span>
              <!-- Parallel execution indicator -->
              <span 
                v-if="isParallelStep(step)"
                class="px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300"
                :title="`Parallel group (level ${step.parallel_level})`"
              >
                ⫘
              </span>
            </div>
            <div class="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 mt-1">
              <span v-if="step.started_at">Started: {{ formatTime(step.started_at) }}</span>
              <span v-if="step.completed_at">Completed: {{ formatTime(step.completed_at) }}</span>
            </div>
          </div>

          <!-- Duration bar -->
          <div class="hidden sm:flex items-center gap-3 flex-shrink-0">
            <div v-if="getDuration(step)" class="text-sm text-gray-600 dark:text-gray-300 font-mono">
              {{ getDuration(step) }}
            </div>
            <div 
              v-if="maxDuration > 0"
              class="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden"
            >
              <div
                class="h-full rounded-full"
                :class="getDurationBarColor(step.status)"
                :style="{ width: getDurationPercent(step) + '%' }"
              ></div>
            </div>
          </div>

          <!-- Expand icon -->
          <ChevronDownIcon 
            class="w-5 h-5 text-gray-400 transition-transform duration-200"
            :class="{ 'rotate-180': expandedStep === step.step_id }"
          />
        </div>

        <!-- Step detail panel (expanded) -->
        <div v-if="expandedStep === step.step_id" class="border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-800/50">
          <!-- Timing info -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <div class="text-xs text-gray-500 dark:text-gray-400">Started</div>
              <div class="text-sm font-medium text-gray-900 dark:text-white">
                {{ step.started_at ? formatDateTime(step.started_at) : '-' }}
              </div>
            </div>
            <div>
              <div class="text-xs text-gray-500 dark:text-gray-400">Completed</div>
              <div class="text-sm font-medium text-gray-900 dark:text-white">
                {{ step.completed_at ? formatDateTime(step.completed_at) : '-' }}
              </div>
            </div>
            <div>
              <div class="text-xs text-gray-500 dark:text-gray-400">Duration</div>
              <div class="text-sm font-medium text-gray-900 dark:text-white">
                {{ getDuration(step) || '-' }}
              </div>
            </div>
            <div>
              <div class="text-xs text-gray-500 dark:text-gray-400">Retries</div>
              <div class="text-sm font-medium text-gray-900 dark:text-white">
                {{ step.retry_count || 0 }}
              </div>
            </div>
          </div>

          <!-- Error display (for failed steps) -->
          <div v-if="step.error" class="mb-4">
            <div class="text-xs font-medium text-red-600 dark:text-red-400 mb-2">Error Details</div>
            <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <!-- Error code badge -->
              <div v-if="step.error.code" class="mb-2">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-red-100 dark:bg-red-900/50 text-red-800 dark:text-red-300">
                  {{ step.error.code }}
                </span>
              </div>
              
              <!-- Error message -->
              <div class="text-sm text-red-700 dark:text-red-300 font-medium mb-2">
                {{ step.error.message || 'Unknown error' }}
              </div>
              
              <!-- Retry info -->
              <div v-if="step.retry_count > 0" class="mt-3 pt-3 border-t border-red-200 dark:border-red-800">
                <div class="flex items-center gap-2 text-xs text-red-600 dark:text-red-400">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  <span>Failed after {{ step.retry_count }} retry attempt{{ step.retry_count > 1 ? 's' : '' }}</span>
                </div>
                <div v-if="step.error.failed_at" class="text-xs text-red-500 dark:text-red-500 mt-1">
                  Last attempt: {{ formatDateTime(step.error.failed_at) }}
                </div>
              </div>

              <!-- Copy button -->
              <div class="mt-3 flex gap-2">
                <button
                  @click="copyToClipboard(JSON.stringify(step.error, null, 2))"
                  class="text-xs text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 flex items-center gap-1"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Copy error details
                </button>
              </div>
            </div>
          </div>

          <!-- Output display (for completed steps) -->
          <div v-if="step.status === 'completed'" class="mb-4">
            <div class="flex items-center justify-between mb-1">
              <div class="text-xs font-medium text-gray-500 dark:text-gray-400">Output</div>
              <button
                @click="loadStepOutput(step.step_id)"
                v-if="!stepOutputs[step.step_id]"
                class="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
              >
                Load output
              </button>
              <button
                v-else
                @click="copyToClipboard(JSON.stringify(stepOutputs[step.step_id], null, 2))"
                class="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
              >
                Copy output
              </button>
            </div>
            <div v-if="loadingOutput === step.step_id" class="text-sm text-gray-500 dark:text-gray-400">
              Loading...
            </div>
            <div v-else-if="stepOutputs[step.step_id]" class="bg-gray-100 dark:bg-gray-900 rounded-lg p-3 max-h-60 overflow-auto">
              <pre class="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono">{{ formatOutput(stepOutputs[step.step_id]) }}</pre>
            </div>
            <div v-else class="text-sm text-gray-500 dark:text-gray-400 italic">
              Click "Load output" to view step output
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="steps.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400">
      No steps in this execution
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useExecutionsStore } from '../stores/executions'
import { ChevronDownIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  executionId: {
    type: String,
    required: true
  },
  steps: {
    type: Array,
    default: () => []
  }
})

const executionsStore = useExecutionsStore()

// State
const expandedStep = ref(null)
const stepOutputs = ref({})
const loadingOutput = ref(null)

// Computed
const totalSteps = computed(() => props.steps.length)

const completedSteps = computed(() => 
  props.steps.filter(s => s.status === 'completed' || s.status === 'skipped').length
)

const progressPercent = computed(() => {
  if (totalSteps.value === 0) return 0
  return Math.round((completedSteps.value / totalSteps.value) * 100)
})

const progressBarColor = computed(() => {
  const hasFailure = props.steps.some(s => s.status === 'failed')
  if (hasFailure) return 'bg-red-500'
  if (progressPercent.value === 100) return 'bg-green-500'
  return 'bg-blue-500'
})

const maxDuration = computed(() => {
  let max = 0
  props.steps.forEach(step => {
    if (step.started_at && step.completed_at) {
      const duration = new Date(step.completed_at) - new Date(step.started_at)
      if (duration > max) max = duration
    }
  })
  return max
})

// Check if step is part of a parallel group (same level as another step)
const parallelLevelCounts = computed(() => {
  const counts = {}
  props.steps.forEach(step => {
    const level = step.parallel_level || 0
    counts[level] = (counts[level] || 0) + 1
  })
  return counts
})

function isParallelStep(step) {
  const level = step.parallel_level || 0
  return parallelLevelCounts.value[level] > 1
}

// Methods
function toggleStep(stepId) {
  expandedStep.value = expandedStep.value === stepId ? null : stepId
}

async function loadStepOutput(stepId) {
  loadingOutput.value = stepId
  try {
    const output = await executionsStore.getStepOutput(props.executionId, stepId)
    stepOutputs.value[stepId] = output
  } catch (error) {
    console.error('Failed to load step output:', error)
    stepOutputs.value[stepId] = { error: 'Failed to load output' }
  } finally {
    loadingOutput.value = null
  }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text)
}

// Formatters
function getStepIcon(status) {
  const icons = {
    pending: '○',
    running: '◐',
    completed: '✓',
    failed: '✗',
    skipped: '–',
  }
  return icons[status] || '?'
}

function getStepNumberClasses(status) {
  const classes = {
    pending: 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400',
    running: 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400',
    completed: 'bg-green-100 dark:bg-green-900/50 text-green-600 dark:text-green-400',
    failed: 'bg-red-100 dark:bg-red-900/50 text-red-600 dark:text-red-400',
    skipped: 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500',
  }
  return classes[status] || 'bg-gray-100 dark:bg-gray-700 text-gray-500'
}

function getStatusBadgeClasses(status) {
  const classes = {
    pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
    running: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
    completed: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
    failed: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
    skipped: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
  }
  return classes[status] || 'bg-gray-100 text-gray-600'
}

function getDurationBarColor(status) {
  const colors = {
    completed: 'bg-green-500',
    failed: 'bg-red-500',
    running: 'bg-blue-500',
  }
  return colors[status] || 'bg-gray-400'
}

function getDuration(step) {
  if (!step.started_at) return null
  
  const start = new Date(step.started_at)
  const end = step.completed_at ? new Date(step.completed_at) : new Date()
  const diffMs = end - start
  const seconds = Math.floor(diffMs / 1000)
  
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}m ${secs}s`
}

function getDurationPercent(step) {
  if (!step.started_at || !step.completed_at || maxDuration.value === 0) return 0
  const duration = new Date(step.completed_at) - new Date(step.started_at)
  return Math.round((duration / maxDuration.value) * 100)
}

function formatTime(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleTimeString()
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

function formatError(error) {
  if (typeof error === 'string') return error
  if (error.message) return error.message
  return JSON.stringify(error, null, 2)
}

function formatOutput(output) {
  if (typeof output === 'string') return output
  return JSON.stringify(output, null, 2)
}
</script>
