<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <!-- Loading state -->
        <div v-if="loading" class="flex justify-center py-12">
          <div class="flex items-center gap-3 text-gray-500 dark:text-gray-400">
            <svg class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Loading execution...</span>
          </div>
        </div>

        <template v-else-if="execution">
          <!-- Header -->
          <div class="flex justify-between items-start mb-6">
            <div class="flex items-center gap-4">
              <router-link
                to="/executions"
                class="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title="Back to executions"
              >
                <ArrowLeftIcon class="h-5 w-5" />
              </router-link>
              <div>
                <div class="flex items-center gap-3">
                  <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
                    {{ execution.process_name }}
                  </h1>
                  <span :class="getStatusClasses(execution.status)" class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium">
                    <span>{{ getStatusIcon(execution.status) }}</span>
                    <span class="capitalize">{{ execution.status }}</span>
                  </span>
                </div>
                <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Execution ID: <code class="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded text-xs">{{ execution.id }}</code>
                </p>
              </div>
            </div>

            <div class="flex items-center gap-3">
              <!-- Cancel button (for running/pending) -->
              <button
                v-if="execution.status === 'running' || execution.status === 'pending'"
                @click="handleCancel"
                :disabled="actionInProgress"
                class="px-4 py-2 text-sm font-medium text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/50 disabled:opacity-50 transition-colors"
              >
                Cancel Execution
              </button>

              <!-- Retry button (for failed) -->
              <button
                v-if="execution.status === 'failed'"
                @click="handleRetry"
                :disabled="actionInProgress"
                class="px-4 py-2 text-sm font-medium text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg hover:bg-amber-100 dark:hover:bg-amber-900/50 disabled:opacity-50 transition-colors"
              >
                Retry Execution
              </button>

              <!-- Refresh button -->
              <button
                @click="loadExecution"
                :disabled="loading"
                class="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title="Refresh"
              >
                <ArrowPathIcon class="w-5 h-5" :class="{ 'animate-spin': loading }" />
              </button>
            </div>
          </div>

          <!-- Info cards -->
          <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">Triggered By</div>
              <div class="text-sm font-medium text-gray-900 dark:text-white capitalize">{{ execution.triggered_by }}</div>
            </div>
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">Started</div>
              <div class="text-sm font-medium text-gray-900 dark:text-white">
                {{ execution.started_at ? formatDateTime(execution.started_at) : '-' }}
              </div>
            </div>
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">Completed</div>
              <div class="text-sm font-medium text-gray-900 dark:text-white">
                {{ execution.completed_at ? formatDateTime(execution.completed_at) : '-' }}
              </div>
            </div>
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">Duration</div>
              <div class="text-sm font-medium text-gray-900 dark:text-white">
                {{ formatDuration(execution.duration_seconds) }}
              </div>
            </div>
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">Total Cost</div>
              <div class="text-sm font-medium text-gray-900 dark:text-white">
                {{ execution.total_cost || '-' }}
              </div>
            </div>
          </div>

          <!-- Tabs -->
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <div class="border-b border-gray-200 dark:border-gray-700">
              <nav class="flex -mb-px">
                <button
                  @click="activeTab = 'timeline'"
                  :class="[
                    'px-6 py-3 text-sm font-medium border-b-2 transition-colors',
                    activeTab === 'timeline'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Timeline
                </button>
                <button
                  @click="activeTab = 'input'"
                  :class="[
                    'px-6 py-3 text-sm font-medium border-b-2 transition-colors',
                    activeTab === 'input'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Input Data
                </button>
                <button
                  @click="activeTab = 'output'"
                  :class="[
                    'px-6 py-3 text-sm font-medium border-b-2 transition-colors',
                    activeTab === 'output'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Output Data
                </button>
              </nav>
            </div>

            <div class="p-6">
              <!-- Timeline tab -->
              <div v-if="activeTab === 'timeline'">
                <ExecutionTimeline
                  :execution-id="execution.id"
                  :steps="execution.steps || []"
                />
              </div>

              <!-- Input data tab -->
              <div v-else-if="activeTab === 'input'">
                <div v-if="Object.keys(execution.input_data || {}).length > 0">
                  <div class="flex justify-end mb-2">
                    <button
                      @click="copyToClipboard(JSON.stringify(execution.input_data, null, 2))"
                      class="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
                    >
                      Copy JSON
                    </button>
                  </div>
                  <pre class="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 text-sm text-gray-700 dark:text-gray-300 overflow-auto max-h-96 font-mono">{{ JSON.stringify(execution.input_data, null, 2) }}</pre>
                </div>
                <div v-else class="text-center py-8 text-gray-500 dark:text-gray-400">
                  No input data
                </div>
              </div>

              <!-- Output data tab -->
              <div v-else-if="activeTab === 'output'">
                <div v-if="Object.keys(execution.output_data || {}).length > 0">
                  <div class="flex justify-end mb-2">
                    <button
                      @click="copyToClipboard(JSON.stringify(execution.output_data, null, 2))"
                      class="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
                    >
                      Copy JSON
                    </button>
                  </div>
                  <pre class="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 text-sm text-gray-700 dark:text-gray-300 overflow-auto max-h-96 font-mono">{{ JSON.stringify(execution.output_data, null, 2) }}</pre>
                </div>
                <div v-else class="text-center py-8 text-gray-500 dark:text-gray-400">
                  {{ execution.status === 'completed' ? 'No output data' : 'Execution not yet completed' }}
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- Error state -->
        <div v-else class="text-center py-12 bg-white dark:bg-gray-800 rounded-xl shadow">
          <ExclamationCircleIcon class="mx-auto h-12 w-12 text-red-400" />
          <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">Execution not found</h3>
          <div class="mt-6">
            <router-link
              to="/executions"
              class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
            >
              Back to executions
            </router-link>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useExecutionsStore } from '../stores/executions'
import NavBar from '../components/NavBar.vue'
import ExecutionTimeline from '../components/ExecutionTimeline.vue'
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  ExclamationCircleIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const executionsStore = useExecutionsStore()

// State
const loading = ref(false)
const execution = ref(null)
const activeTab = ref('timeline')
const actionInProgress = ref(false)

// Auto-refresh interval
let refreshInterval = null

// Lifecycle
onMounted(() => {
  loadExecution()
  
  // Auto-refresh for running executions
  refreshInterval = setInterval(() => {
    if (execution.value && (execution.value.status === 'running' || execution.value.status === 'pending')) {
      loadExecution()
    }
  }, 5000) // Refresh every 5 seconds for active executions
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

// Methods
async function loadExecution() {
  loading.value = true
  try {
    execution.value = await executionsStore.getExecution(route.params.id)
  } catch (error) {
    console.error('Failed to load execution:', error)
    execution.value = null
  } finally {
    loading.value = false
  }
}

async function handleCancel() {
  actionInProgress.value = true
  try {
    await executionsStore.cancelExecution(execution.value.id)
    await loadExecution()
  } catch (error) {
    console.error('Failed to cancel execution:', error)
  } finally {
    actionInProgress.value = false
  }
}

async function handleRetry() {
  actionInProgress.value = true
  try {
    const newExecution = await executionsStore.retryExecution(execution.value.id)
    // Navigate to new execution
    router.push(`/executions/${newExecution.id}`)
  } catch (error) {
    console.error('Failed to retry execution:', error)
  } finally {
    actionInProgress.value = false
  }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text)
}

// Formatters
function getStatusIcon(status) {
  const icons = {
    pending: '⏳',
    running: '🔄',
    completed: '✅',
    failed: '❌',
    cancelled: '⛔',
    paused: '⏸️',
  }
  return icons[status] || '❓'
}

function getStatusClasses(status) {
  const classes = {
    pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300',
    running: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300',
    completed: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300',
    failed: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300',
    cancelled: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300',
    paused: 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300',
  }
  return classes[status] || 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${mins}m`
}
</script>
