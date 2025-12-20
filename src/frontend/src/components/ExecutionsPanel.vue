<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <div>
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">Execution History</h3>
        <p class="text-sm text-gray-500 dark:text-gray-400">All scheduled and manual executions for this agent</p>
      </div>
      <button
        @click="loadExecutions"
        :disabled="loading"
        class="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
      >
        <svg v-if="loading" class="animate-spin -ml-0.5 mr-1.5 h-3 w-3" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <svg v-else class="w-3 h-3 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Refresh
      </button>
    </div>

    <!-- Summary Stats -->
    <div v-if="executions.length > 0" class="grid grid-cols-4 gap-4">
      <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Total Executions</p>
        <p class="text-2xl font-semibold text-gray-900 dark:text-white">{{ executions.length }}</p>
      </div>
      <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Success Rate</p>
        <p class="text-2xl font-semibold" :class="successRate >= 90 ? 'text-green-600' : successRate >= 70 ? 'text-yellow-600' : 'text-red-600'">
          {{ successRate }}%
        </p>
      </div>
      <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Total Cost</p>
        <p class="text-2xl font-semibold text-gray-900 dark:text-white font-mono">${{ totalCost.toFixed(4) }}</p>
      </div>
      <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Avg Duration</p>
        <p class="text-2xl font-semibold text-gray-900 dark:text-white">{{ formatDuration(avgDuration) }}</p>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && executions.length === 0" class="text-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mx-auto"></div>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">Loading executions...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="executions.length === 0" class="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <svg class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
      <p class="mt-2 text-gray-500 dark:text-gray-400">No executions yet</p>
      <p class="text-sm text-gray-400 dark:text-gray-500">Configure schedules to automate agent tasks</p>
    </div>

    <!-- Executions Table -->
    <div v-else class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead class="bg-gray-50 dark:bg-gray-800/50">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Started</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Duration</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Context</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Cost</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Trigger</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Message</th>
          </tr>
        </thead>
        <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
          <tr
            v-for="exec in executions"
            :key="exec.id"
            @click="viewExecutionDetail(exec)"
            class="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
          >
            <td class="px-4 py-3 whitespace-nowrap">
              <span
                :class="[
                  'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                  exec.status === 'success' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' :
                  exec.status === 'failed' ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300' :
                  exec.status === 'running' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300' :
                  'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300'
                ]"
              >
                <span
                  :class="[
                    'w-1.5 h-1.5 mr-1.5 rounded-full',
                    exec.status === 'success' ? 'bg-green-500' :
                    exec.status === 'failed' ? 'bg-red-500' :
                    exec.status === 'running' ? 'bg-yellow-500 animate-pulse' :
                    'bg-gray-500'
                  ]"
                ></span>
                {{ exec.status }}
              </span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
              {{ formatDateTime(exec.started_at) }}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400 font-mono">
              {{ formatDuration(exec.duration_ms) || '-' }}
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
              <div v-if="exec.context_used && exec.context_max" class="flex items-center space-x-2">
                <div class="w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full"
                    :class="getContextBarColor(exec.context_used, exec.context_max)"
                    :style="{ width: Math.min(100, (exec.context_used / exec.context_max) * 100) + '%' }"
                  ></div>
                </div>
                <span class="text-xs text-gray-500 dark:text-gray-400">{{ formatContextPercent(exec.context_used, exec.context_max) }}</span>
              </div>
              <span v-else class="text-xs text-gray-400 dark:text-gray-500">-</span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm font-mono text-gray-600 dark:text-gray-400">
              {{ exec.cost ? '$' + exec.cost.toFixed(4) : '-' }}
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
              <span
                :class="[
                  'px-1.5 py-0.5 rounded text-xs',
                  exec.triggered_by === 'manual' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                ]"
              >
                {{ exec.triggered_by }}
              </span>
            </td>
            <td class="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 max-w-xs truncate">
              {{ exec.message.substring(0, 50) }}{{ exec.message.length > 50 ? '...' : '' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Execution Detail Modal -->
    <div v-if="selectedExecution" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="selectedExecution = null"></div>
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full relative z-10 max-h-[85vh] overflow-hidden flex flex-col">
          <!-- Header -->
          <div class="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-start">
            <div>
              <h3 class="text-lg font-medium text-gray-900 dark:text-white">Execution Details</h3>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ formatDateTime(selectedExecution.started_at) }}</p>
            </div>
            <div class="flex items-center space-x-3">
              <span
                :class="[
                  'px-2 py-1 rounded-full text-xs font-medium',
                  selectedExecution.status === 'success' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' :
                  selectedExecution.status === 'failed' ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300' :
                  'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300'
                ]"
              >
                {{ selectedExecution.status }}
              </span>
              <button @click="selectedExecution = null" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          <!-- Stats Row -->
          <div class="p-4 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700 grid grid-cols-5 gap-4">
            <div>
              <p class="text-xs text-gray-500 dark:text-gray-400">Duration</p>
              <p class="text-sm font-medium dark:text-white">{{ formatDuration(selectedExecution.duration_ms) || '-' }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-500 dark:text-gray-400">Cost</p>
              <p class="text-sm font-medium font-mono dark:text-white">${{ selectedExecution.cost?.toFixed(4) || '0.0000' }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-500 dark:text-gray-400">Context Used</p>
              <div class="flex items-center space-x-2">
                <p class="text-sm font-medium dark:text-white">{{ formatTokens(selectedExecution.context_used) }}</p>
                <div v-if="selectedExecution.context_max" class="w-12 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full"
                    :class="getContextBarColor(selectedExecution.context_used, selectedExecution.context_max)"
                    :style="{ width: Math.min(100, (selectedExecution.context_used / selectedExecution.context_max) * 100) + '%' }"
                  ></div>
                </div>
              </div>
            </div>
            <div>
              <p class="text-xs text-gray-500 dark:text-gray-400">Context Max</p>
              <p class="text-sm font-medium dark:text-white">{{ formatTokens(selectedExecution.context_max) }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-500 dark:text-gray-400">Triggered By</p>
              <p class="text-sm font-medium capitalize dark:text-white">{{ selectedExecution.triggered_by }}</p>
            </div>
          </div>

          <!-- Content -->
          <div class="flex-1 overflow-y-auto p-4 space-y-4">
            <!-- Message Sent -->
            <div>
              <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Message Sent</h4>
              <div class="bg-gray-100 dark:bg-gray-700 rounded p-3 text-sm font-mono whitespace-pre-wrap dark:text-gray-300">{{ selectedExecution.message }}</div>
            </div>

            <!-- Error (if any) -->
            <div v-if="selectedExecution.error">
              <h4 class="text-sm font-medium text-red-700 dark:text-red-400 mb-2">Error</h4>
              <div class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded p-3 text-sm text-red-700 dark:text-red-300 whitespace-pre-wrap">{{ selectedExecution.error }}</div>
            </div>

            <!-- Tool Calls -->
            <div v-if="parsedToolCalls.length > 0">
              <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Tool Calls ({{ parsedToolCalls.length }})</h4>
              <div class="space-y-1 max-h-48 overflow-y-auto">
                <div
                  v-for="(tool, idx) in parsedToolCalls"
                  :key="idx"
                  class="flex items-center justify-between text-xs bg-gray-100 dark:bg-gray-700 rounded px-2 py-1.5"
                >
                  <div class="flex items-center space-x-2">
                    <span class="font-medium text-indigo-600 dark:text-indigo-400">{{ tool.tool }}</span>
                    <span v-if="tool.input" class="text-gray-500 dark:text-gray-400 truncate max-w-md">
                      {{ summarizeToolInput(tool) }}
                    </span>
                  </div>
                  <div class="flex items-center space-x-2">
                    <span v-if="tool.duration_ms" class="text-gray-400 dark:text-gray-500">{{ formatDuration(tool.duration_ms) }}</span>
                    <span v-if="tool.success !== undefined" :class="tool.success ? 'text-green-600' : 'text-red-600'">
                      {{ tool.success ? '✓' : '✗' }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Response -->
            <div v-if="selectedExecution.response">
              <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Response</h4>
              <div class="bg-gray-100 dark:bg-gray-700 rounded p-3 text-sm whitespace-pre-wrap max-h-64 overflow-y-auto dark:text-gray-300">{{ selectedExecution.response }}</div>
            </div>
          </div>

          <!-- Footer -->
          <div class="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
            <button
              @click="selectedExecution = null"
              class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  agentName: {
    type: String,
    required: true
  }
})

const authStore = useAuthStore()

// State
const executions = ref([])
const loading = ref(true)
const selectedExecution = ref(null)

// Computed stats
const successRate = computed(() => {
  if (executions.value.length === 0) return 0
  const successful = executions.value.filter(e => e.status === 'success').length
  return Math.round((successful / executions.value.length) * 100)
})

const totalCost = computed(() => {
  return executions.value.reduce((sum, e) => sum + (e.cost || 0), 0)
})

const avgDuration = computed(() => {
  const withDuration = executions.value.filter(e => e.duration_ms)
  if (withDuration.length === 0) return 0
  return Math.round(withDuration.reduce((sum, e) => sum + e.duration_ms, 0) / withDuration.length)
})

// Parse tool calls from selected execution
const parsedToolCalls = computed(() => {
  if (!selectedExecution.value?.tool_calls) return []
  try {
    const calls = JSON.parse(selectedExecution.value.tool_calls)
    return calls.filter(c => c.type === 'tool_use')
  } catch {
    return []
  }
})

// Load executions
async function loadExecutions() {
  loading.value = true
  try {
    const response = await axios.get(`/api/agents/${props.agentName}/executions?limit=100`, {
      headers: authStore.authHeader
    })
    executions.value = response.data
  } catch (error) {
    console.error('Failed to load executions:', error)
  } finally {
    loading.value = false
  }
}

// Format helpers
function formatDateTime(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}

function formatDuration(ms) {
  if (!ms) return ''
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

function formatTokens(tokens) {
  if (!tokens) return '-'
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}K`
  return tokens.toString()
}

function formatContextPercent(used, max) {
  if (!used || !max) return ''
  return `${Math.round((used / max) * 100)}%`
}

function getContextBarColor(used, max) {
  if (!used || !max) return 'bg-gray-400'
  const percent = (used / max) * 100
  if (percent < 50) return 'bg-green-500'
  if (percent < 75) return 'bg-yellow-500'
  if (percent < 90) return 'bg-orange-500'
  return 'bg-red-500'
}

function viewExecutionDetail(exec) {
  selectedExecution.value = exec
}

function summarizeToolInput(tool) {
  if (!tool.input) return ''
  const input = tool.input

  if (input.file_path) {
    const parts = input.file_path.split('/')
    return parts.slice(-2).join('/')
  }
  if (input.pattern) return input.pattern
  if (input.command) return input.command.substring(0, 50) + (input.command.length > 50 ? '...' : '')
  if (input.query) return input.query.substring(0, 50)
  if (input.url) return input.url.substring(0, 50)

  for (const [key, value] of Object.entries(input)) {
    if (typeof value === 'string' && value.length < 60) {
      return `${key}: ${value}`
    }
  }
  return ''
}

// Watch for agent name changes
watch(() => props.agentName, () => {
  loadExecutions()
})

onMounted(() => {
  loadExecutions()
})
</script>
