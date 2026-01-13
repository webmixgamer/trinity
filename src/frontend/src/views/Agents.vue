<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <!-- Notification Toast -->
        <div v-if="notification"
          :class="[
            'fixed top-20 right-4 z-50 px-4 py-3 rounded-lg shadow-lg transition-all duration-300',
            notification.type === 'success' ? 'bg-green-100 dark:bg-green-900/50 border border-green-400 dark:border-green-700 text-green-700 dark:text-green-300' : 'bg-red-100 dark:bg-red-900/50 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-300'
          ]"
        >
          {{ notification.message }}
        </div>

        <div class="flex justify-between items-center mb-8">
          <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Agents</h1>

          <div class="flex items-center space-x-4">
            <!-- Sort dropdown -->
            <select
              v-model="agentsStore.sortBy"
              class="block rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm py-2 px-3 bg-white dark:bg-gray-700 dark:text-gray-200 border"
            >
              <option value="created_desc">Newest First</option>
              <option value="created_asc">Oldest First</option>
              <option value="name_asc">Name (A-Z)</option>
              <option value="name_desc">Name (Z-A)</option>
              <option value="status">Running First</option>
              <option value="context_desc">Context Usage</option>
            </select>

            <button
              @click="showCreateModal = true"
              class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded"
            >
              Create Agent
            </button>
          </div>
        </div>

        <!-- Agents Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="agent in displayAgents"
            :key="agent.name"
            :class="[
              'bg-white dark:bg-gray-800 rounded-xl border shadow-lg p-5',
              'transition-all duration-200 hover:shadow-xl',
              'flex flex-col',
              agent.is_system
                ? 'ring-2 ring-purple-500/50 border-purple-300 dark:border-purple-700'
                : agent.status === 'running'
                  ? 'border-gray-200/60 dark:border-gray-700/50'
                  : 'border-gray-200 dark:border-gray-700 opacity-75'
            ]"
          >
            <!-- Header: Name, Runtime Badge, Status Dot -->
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center flex-1 mr-2 min-w-0">
                <router-link
                  :to="`/agents/${agent.name}`"
                  class="text-gray-900 dark:text-white font-bold text-base truncate hover:text-indigo-600 dark:hover:text-indigo-400"
                  :title="agent.name"
                >
                  {{ agent.name }}
                </router-link>
                <!-- SYSTEM badge -->
                <span
                  v-if="agent.is_system"
                  class="ml-2 px-1.5 py-0.5 text-xs font-semibold bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300 rounded flex-shrink-0"
                >
                  SYSTEM
                </span>
                <!-- Runtime badge (Claude/Gemini) -->
                <RuntimeBadge :runtime="agent.runtime" :show-label="false" class="ml-2 flex-shrink-0" />
                <!-- Shared badge -->
                <span
                  v-if="agent.is_shared"
                  class="ml-2 px-1.5 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded flex-shrink-0"
                  :title="'Shared by ' + agent.owner"
                >
                  Shared
                </span>
              </div>
              <!-- Status indicator dot -->
              <div
                :class="[
                  'w-3 h-3 rounded-full flex-shrink-0',
                  isActive(agent.name) ? 'active-pulse' : ''
                ]"
                :style="{ backgroundColor: getStatusDotColor(agent.name) }"
              ></div>
            </div>

            <!-- Activity state and Autonomy toggle -->
            <div class="flex items-center justify-between mb-2">
              <div
                :class="[
                  'text-xs font-medium capitalize',
                  getActivityLabelClass(agent.name)
                ]"
              >
                {{ getActivityState(agent.name) }}
              </div>
              <!-- Autonomy toggle switch with label -->
              <div class="flex items-center gap-1.5">
                <span
                  :class="[
                    'text-xs font-medium transition-colors',
                    agent.autonomy_enabled
                      ? 'text-amber-600 dark:text-amber-400'
                      : 'text-gray-400 dark:text-gray-500'
                  ]"
                >
                  {{ agent.autonomy_enabled ? 'AUTO' : 'Manual' }}
                </span>
                <button
                  @click.stop="handleAutonomyToggle(agent)"
                  :disabled="autonomyLoading === agent.name"
                  :class="[
                    'relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2',
                    agent.autonomy_enabled
                      ? 'bg-amber-500 focus:ring-amber-500'
                      : 'bg-gray-200 dark:bg-gray-600 focus:ring-gray-400',
                    autonomyLoading === agent.name ? 'opacity-50 cursor-wait' : ''
                  ]"
                  :title="agent.autonomy_enabled ? 'Autonomy Mode ON - Click to disable' : 'Autonomy Mode OFF - Click to enable'"
                  role="switch"
                  :aria-checked="agent.autonomy_enabled"
                >
                  <span class="sr-only">Toggle autonomy mode</span>
                  <span
                    :class="[
                      'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                      agent.autonomy_enabled ? 'translate-x-4' : 'translate-x-0'
                    ]"
                  />
                </button>
              </div>
            </div>

            <!-- Type display -->
            <div class="text-xs text-gray-500 dark:text-gray-400 mb-3">
              Type: {{ agent.type }}
            </div>

            <!-- Context progress bar -->
            <div class="mb-3">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs text-gray-500 dark:text-gray-400">Context</span>
                <span class="text-xs font-semibold text-gray-700 dark:text-gray-300">{{ getContextPercent(agent.name) }}%</span>
              </div>
              <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :class="getProgressBarColor(agent.name)"
                  :style="{ width: getContextPercent(agent.name) + '%' }"
                ></div>
              </div>
            </div>

            <!-- Execution Stats Row -->
            <div v-if="hasExecutionStats(agent.name)" class="flex items-center flex-wrap text-xs text-gray-500 dark:text-gray-400 gap-x-1.5 gap-y-0.5 mb-3">
              <span class="font-medium text-gray-700 dark:text-gray-300">{{ getExecutionStats(agent.name).taskCount }}</span>
              <span>tasks</span>
              <span class="text-gray-300 dark:text-gray-600">·</span>
              <span :class="getSuccessRateColorClass(agent.name)" class="font-medium">{{ getExecutionStats(agent.name).successRate }}%</span>
              <template v-if="getExecutionStats(agent.name).totalCost > 0">
                <span class="text-gray-300 dark:text-gray-600">·</span>
                <span class="font-medium text-gray-700 dark:text-gray-300">${{ getExecutionStats(agent.name).totalCost.toFixed(2) }}</span>
              </template>
              <template v-if="getLastExecutionDisplay(agent.name)">
                <span class="text-gray-300 dark:text-gray-600">·</span>
                <span>{{ getLastExecutionDisplay(agent.name) }}</span>
              </template>
            </div>
            <div v-else class="text-xs text-gray-400 dark:text-gray-500 mb-3">
              No tasks (24h)
            </div>

            <!-- Action buttons -->
            <div class="flex items-center justify-between mt-auto pt-3 border-t border-gray-100 dark:border-gray-700/50">
              <!-- Status badge -->
              <span :class="[
                'px-2 py-1 text-xs font-semibold rounded-full',
                agent.status === 'running'
                  ? 'bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
              ]">
                {{ agent.status }}
              </span>

              <div class="flex items-center space-x-2">
                <!-- Start/Stop button -->
                <button
                  v-if="agent.status === 'stopped'"
                  @click="startAgent(agent.name)"
                  :disabled="actionInProgress === agent.name"
                  class="p-1.5 rounded-lg bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/50 disabled:opacity-50 transition-colors"
                  title="Start agent"
                >
                  <svg v-if="actionInProgress === agent.name" class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <PlayIcon v-else class="h-5 w-5" />
                </button>
                <button
                  v-else
                  @click="stopAgent(agent.name)"
                  :disabled="actionInProgress === agent.name"
                  class="p-1.5 rounded-lg bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/50 disabled:opacity-50 transition-colors"
                  title="Stop agent"
                >
                  <svg v-if="actionInProgress === agent.name" class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <StopIcon v-else class="h-5 w-5" />
                </button>
                <!-- View Details button -->
                <router-link
                  :to="`/agents/${agent.name}`"
                  class="px-3 py-1.5 bg-blue-50 dark:bg-blue-900/30 hover:bg-blue-100 dark:hover:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded-lg text-xs font-semibold transition-all duration-200 border border-blue-200 dark:border-blue-700"
                >
                  View Details
                </router-link>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="displayAgents.length === 0" class="text-center py-12 bg-white dark:bg-gray-800 rounded-xl shadow">
          <ServerIcon class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />
          <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">No agents</h3>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">Get started by creating a new agent.</p>
          <div class="mt-6">
            <button
              @click="showCreateModal = true"
              class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
            >
              Create Agent
            </button>
          </div>
        </div>

        <!-- Create Agent Modal -->
        <CreateAgentModal v-if="showCreateModal" @close="showCreateModal = false" />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAgentsStore } from '../stores/agents'
import NavBar from '../components/NavBar.vue'
import CreateAgentModal from '../components/CreateAgentModal.vue'
import RuntimeBadge from '../components/RuntimeBadge.vue'
import { ServerIcon, PlayIcon, StopIcon } from '@heroicons/vue/24/outline'
import axios from 'axios'

const agentsStore = useAgentsStore()
const showCreateModal = ref(false)
const notification = ref(null)
const actionInProgress = ref(null)
const autonomyLoading = ref(null)
const isAdmin = ref(false)

// Computed to show system agent for admins
const displayAgents = computed(() => {
  if (isAdmin.value) {
    return agentsStore.sortedAgentsWithSystem
  }
  return agentsStore.sortedAgents
})

const showNotification = (message, type = 'success') => {
  notification.value = { message, type }
  setTimeout(() => {
    notification.value = null
  }, 3000)
}

onMounted(async () => {
  agentsStore.fetchAgents()
  agentsStore.startContextPolling()

  // Check if user is admin
  try {
    const token = localStorage.getItem('token')
    if (token) {
      const response = await axios.get('/api/users/me', {
        headers: { Authorization: `Bearer ${token}` }
      })
      isAdmin.value = response.data.role === 'admin'
    }
  } catch (e) {
    console.warn('Failed to fetch user role:', e)
    isAdmin.value = false
  }
})

onUnmounted(() => {
  agentsStore.stopContextPolling()
})

// Activity state helpers
const getActivityState = (agentName) => {
  const stats = agentsStore.contextStats[agentName]
  if (!stats) return 'Offline'
  const state = stats.activityState
  if (state === 'active') return 'Active'
  if (state === 'idle') return 'Idle'
  return 'Offline'
}

const isActive = (agentName) => {
  return getActivityState(agentName) === 'Active'
}

const getStatusDotColor = (agentName) => {
  const state = getActivityState(agentName)
  if (state === 'Active') return '#10b981' // green-500
  if (state === 'Idle') return '#10b981' // green-500
  return '#9ca3af' // gray-400
}

const getActivityLabelClass = (agentName) => {
  const state = getActivityState(agentName)
  if (state === 'Active' || state === 'Idle') return 'text-green-600 dark:text-green-400'
  return 'text-gray-500 dark:text-gray-400'
}

// Context helpers
const getContextPercent = (agentName) => {
  const stats = agentsStore.contextStats[agentName]
  return stats ? Math.round(stats.contextPercent || 0) : 0
}

const getProgressBarColor = (agentName) => {
  const percent = getContextPercent(agentName)
  if (percent >= 90) return 'bg-red-500'
  if (percent >= 75) return 'bg-orange-500'
  if (percent >= 50) return 'bg-yellow-500'
  return 'bg-green-500'
}

// Execution stats helpers
const getExecutionStats = (agentName) => {
  return agentsStore.executionStats[agentName] || null
}

const hasExecutionStats = (agentName) => {
  const stats = getExecutionStats(agentName)
  return stats && stats.taskCount > 0
}

const getSuccessRateColorClass = (agentName) => {
  const stats = getExecutionStats(agentName)
  if (!stats) return 'text-gray-500 dark:text-gray-400'
  const rate = stats.successRate
  if (rate >= 80) return 'text-green-600 dark:text-green-400'
  if (rate >= 50) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-red-600 dark:text-red-400'
}

const getLastExecutionDisplay = (agentName) => {
  const stats = getExecutionStats(agentName)
  if (!stats?.lastExecutionAt) return null
  const lastTime = new Date(stats.lastExecutionAt)
  const now = new Date()
  const diffMs = now - lastTime
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${Math.floor(diffHours / 24)}d ago`
}

// Autonomy toggle handler
const handleAutonomyToggle = async (agent) => {
  if (autonomyLoading.value === agent.name) return
  autonomyLoading.value = agent.name
  try {
    await agentsStore.toggleAutonomy(agent.name)
  } catch (error) {
    showNotification('Failed to toggle autonomy mode', 'error')
  } finally {
    autonomyLoading.value = null
  }
}

const startAgent = async (name) => {
  if (actionInProgress.value === name) return
  actionInProgress.value = name
  try {
    const result = await agentsStore.startAgent(name)
    showNotification(result.message, 'success')
  } catch (error) {
    showNotification(error.message || 'Failed to start agent', 'error')
  } finally {
    actionInProgress.value = null
  }
}

const stopAgent = async (name) => {
  if (actionInProgress.value === name) return
  actionInProgress.value = name
  try {
    const result = await agentsStore.stopAgent(name)
    showNotification(result.message, 'success')
  } catch (error) {
    showNotification(error.message || 'Failed to stop agent', 'error')
  } finally {
    actionInProgress.value = null
  }
}
</script>

<style scoped>
/* Pulsing animation for active agents */
.active-pulse {
  animation: active-pulse-animation 0.8s ease-in-out infinite;
  box-shadow: 0 0 8px 2px rgba(16, 185, 129, 0.6);
}

@keyframes active-pulse-animation {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
    box-shadow: 0 0 8px 2px rgba(16, 185, 129, 0.6);
  }
  50% {
    transform: scale(1.3);
    opacity: 0.8;
    box-shadow: 0 0 16px 4px rgba(16, 185, 129, 0.9);
  }
}
</style>
