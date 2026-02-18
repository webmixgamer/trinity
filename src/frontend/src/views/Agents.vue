<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />
    <AgentSubNav />

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 sm:px-0">
        <!-- Notification Toast -->
        <div v-if="notification"
          :class="[
            'fixed top-20 right-4 z-50 px-4 py-3 rounded-lg shadow-lg transition-all duration-300',
            notification.type === 'success' ? 'bg-green-100 dark:bg-green-900/50 border border-green-400 dark:border-green-700 text-green-700 dark:text-green-300' : 'bg-red-100 dark:bg-red-900/50 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-300'
          ]"
        >
          {{ notification.message }}
        </div>

        <div class="flex justify-between items-center mb-4">
          <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Agents</h1>

          <div class="flex items-center space-x-4">
            <!-- Tag Filter -->
            <div v-if="availableTags.length > 0" class="flex items-center space-x-2">
              <select
                v-model="selectedFilterTag"
                class="block rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm py-2 px-3 bg-white dark:bg-gray-700 dark:text-gray-200 border"
              >
                <option value="">All Tags</option>
                <option v-for="tagInfo in availableTags" :key="tagInfo.tag" :value="tagInfo.tag">
                  #{{ tagInfo.tag }} ({{ tagInfo.count }})
                </option>
              </select>
            </div>

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

        <!-- Bulk Actions Toolbar -->
        <div
          v-if="selectedAgents.length > 0"
          class="mb-4 p-3 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg flex items-center justify-between"
        >
          <div class="flex items-center space-x-3">
            <span class="text-sm font-medium text-blue-700 dark:text-blue-300">
              {{ selectedAgents.length }} agent{{ selectedAgents.length > 1 ? 's' : '' }} selected
            </span>
            <button
              @click="clearSelection"
              class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
            >
              Clear
            </button>
          </div>
          <div class="flex items-center space-x-2">
            <!-- Add Tag -->
            <div class="relative">
              <button
                @click="showBulkAddTag = !showBulkAddTag"
                class="px-3 py-1.5 bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300 rounded text-sm font-medium hover:bg-green-200 dark:hover:bg-green-900 transition-colors"
              >
                + Add Tag
              </button>
              <div
                v-if="showBulkAddTag"
                class="absolute right-0 top-full mt-1 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-3 z-50 min-w-64"
              >
                <div class="mb-2">
                  <input
                    v-model="bulkTagInput"
                    @keyup.enter="applyBulkTag"
                    type="text"
                    placeholder="Enter tag name..."
                    class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 dark:text-gray-200 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div v-if="availableTags.length > 0" class="mb-2 max-h-32 overflow-y-auto">
                  <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">Or select existing:</div>
                  <div class="flex flex-wrap gap-1">
                    <button
                      v-for="tagInfo in availableTags"
                      :key="tagInfo.tag"
                      @click="bulkTagInput = tagInfo.tag"
                      :class="[
                        'px-2 py-0.5 rounded-full text-xs transition-colors',
                        bulkTagInput === tagInfo.tag
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                      ]"
                    >
                      #{{ tagInfo.tag }}
                    </button>
                  </div>
                </div>
                <div class="flex justify-end space-x-2">
                  <button
                    @click="showBulkAddTag = false; bulkTagInput = ''"
                    class="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    @click="applyBulkTag"
                    :disabled="!bulkTagInput.trim()"
                    class="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Apply
                  </button>
                </div>
              </div>
            </div>
            <!-- Remove Tag -->
            <div class="relative">
              <button
                @click="showBulkRemoveTag = !showBulkRemoveTag"
                class="px-3 py-1.5 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 rounded text-sm font-medium hover:bg-red-200 dark:hover:bg-red-900 transition-colors"
              >
                - Remove Tag
              </button>
              <div
                v-if="showBulkRemoveTag"
                class="absolute right-0 top-full mt-1 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-3 z-50 min-w-48"
              >
                <div v-if="commonTagsInSelection.length > 0">
                  <div class="text-xs text-gray-500 dark:text-gray-400 mb-2">Tags in selected agents:</div>
                  <div class="flex flex-wrap gap-1 mb-2">
                    <button
                      v-for="tag in commonTagsInSelection"
                      :key="tag"
                      @click="removeBulkTag(tag)"
                      class="px-2 py-0.5 rounded-full text-xs bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-900 transition-colors"
                    >
                      #{{ tag }} ×
                    </button>
                  </div>
                </div>
                <div v-else class="text-xs text-gray-500 dark:text-gray-400">
                  No tags found on selected agents
                </div>
                <button
                  @click="showBulkRemoveTag = false"
                  class="mt-2 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
                >
                  Close
                </button>
              </div>
            </div>
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
              'flex flex-col relative',
              agent.is_system
                ? 'ring-2 ring-purple-500/50 border-purple-300 dark:border-purple-700'
                : agent.status === 'running'
                  ? 'border-gray-200/60 dark:border-gray-700/50'
                  : 'border-gray-200 dark:border-gray-700 opacity-75'
            ]"
          >
            <!-- Header: Checkbox, Name, Runtime Badge, Status Dot -->
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center flex-1 mr-2 min-w-0">
                <!-- Selection checkbox -->
                <input
                  type="checkbox"
                  :checked="selectedAgents.includes(agent.name)"
                  @change="toggleSelection(agent.name)"
                  class="w-4 h-4 mr-2 text-blue-600 bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500 cursor-pointer flex-shrink-0"
                />
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

            <!-- Activity state -->
            <div
              :class="[
                'text-xs font-medium capitalize mb-2',
                getActivityLabelClass(agent.name)
              ]"
            >
              {{ getActivityState(agent.name) }}
            </div>

            <!-- Running, Read-Only, and Autonomy toggles (same row) -->
            <div class="flex items-center justify-between mb-2">
              <RunningStateToggle
                :model-value="agent.status === 'running'"
                :loading="actionInProgress === agent.name"
                size="sm"
                @toggle="toggleAgentRunning(agent)"
              />
              <ReadOnlyToggle
                v-if="!agent.is_system && !agent.is_shared"
                :model-value="getAgentReadOnlyState(agent.name)"
                :loading="readOnlyLoading === agent.name"
                size="sm"
                :show-label="false"
                @toggle="handleReadOnlyToggle(agent)"
              />
              <AutonomyToggle
                v-if="!agent.is_system"
                :model-value="agent.autonomy_enabled"
                :loading="autonomyLoading === agent.name"
                size="sm"
                @toggle="handleAutonomyToggle(agent)"
              />
            </div>

            <!-- Type display -->
            <div class="text-xs text-gray-500 dark:text-gray-400 mb-2">
              Type: {{ agent.type }}
            </div>

            <!-- Tags display (fixed height for consistent layout) -->
            <div class="h-6 mb-2 overflow-hidden">
              <div v-if="getAgentTags(agent.name).length > 0" class="flex flex-wrap gap-1">
                <span
                  v-for="tag in getAgentTags(agent.name).slice(0, 3)"
                  :key="tag"
                  class="px-1.5 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 truncate max-w-20"
                  :title="'#' + tag"
                >
                  #{{ tag }}
                </span>
                <span
                  v-if="getAgentTags(agent.name).length > 3"
                  class="px-1.5 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-500"
                >
                  +{{ getAgentTags(agent.name).length - 3 }}
                </span>
              </div>
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
            <div class="flex items-center justify-end mt-auto pt-3 border-t border-gray-100 dark:border-gray-700/50">
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
import AgentSubNav from '../components/AgentSubNav.vue'
import CreateAgentModal from '../components/CreateAgentModal.vue'
import RuntimeBadge from '../components/RuntimeBadge.vue'
import RunningStateToggle from '../components/RunningStateToggle.vue'
import AutonomyToggle from '../components/AutonomyToggle.vue'
import ReadOnlyToggle from '../components/ReadOnlyToggle.vue'
import { ServerIcon } from '@heroicons/vue/24/outline'
import axios from 'axios'

const agentsStore = useAgentsStore()
const showCreateModal = ref(false)
const notification = ref(null)
const actionInProgress = ref(null)
const autonomyLoading = ref(null)
const readOnlyLoading = ref(null)
const agentReadOnlyStates = ref({}) // Map of agent_name -> boolean
const isAdmin = ref(false)

// Tag-related state
const availableTags = ref([])
const agentTags = ref({}) // Map of agent_name -> tags[]
const selectedFilterTag = ref('')
const selectedAgents = ref([])
const showBulkAddTag = ref(false)
const showBulkRemoveTag = ref(false)
const bulkTagInput = ref('')

// Computed to show system agent for admins, with optional tag filtering
const displayAgents = computed(() => {
  let agents = isAdmin.value ? agentsStore.sortedAgentsWithSystem : agentsStore.sortedAgents

  // Apply tag filter if selected
  if (selectedFilterTag.value) {
    agents = agents.filter(agent => {
      const tags = agentTags.value[agent.name] || []
      return tags.includes(selectedFilterTag.value)
    })
  }

  return agents
})

// Get common tags across all selected agents (for removal)
const commonTagsInSelection = computed(() => {
  if (selectedAgents.value.length === 0) return []
  const allTags = new Set()
  selectedAgents.value.forEach(agentName => {
    const tags = agentTags.value[agentName] || []
    tags.forEach(tag => allTags.add(tag))
  })
  return Array.from(allTags).sort()
})

const showNotification = (message, type = 'success') => {
  notification.value = { message, type }
  setTimeout(() => {
    notification.value = null
  }, 3000)
}

onMounted(async () => {
  await agentsStore.fetchAgents()
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

  // Fetch tags and read-only states
  await fetchAvailableTags()
  await fetchAllAgentTags()
  await fetchAllReadOnlyStates()
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

// Read-only mode functions
function getAgentReadOnlyState(agentName) {
  return agentReadOnlyStates.value[agentName] || false
}

async function fetchAllReadOnlyStates() {
  const agents = isAdmin.value ? agentsStore.sortedAgentsWithSystem : agentsStore.sortedAgents
  const states = {}

  await Promise.all(
    agents.filter(a => !a.is_system && !a.is_shared).map(async (agent) => {
      try {
        const token = localStorage.getItem('token')
        const response = await axios.get(`/api/agents/${agent.name}/read-only`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        states[agent.name] = response.data.enabled || false
      } catch (err) {
        states[agent.name] = false
      }
    })
  )

  agentReadOnlyStates.value = states
}

async function handleReadOnlyToggle(agent) {
  if (readOnlyLoading.value === agent.name) return
  readOnlyLoading.value = agent.name

  const newState = !getAgentReadOnlyState(agent.name)

  try {
    const token = localStorage.getItem('token')
    const response = await axios.put(`/api/agents/${agent.name}/read-only`, {
      enabled: newState
    }, {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (response.data) {
      agentReadOnlyStates.value[agent.name] = newState
      showNotification(
        newState
          ? `Read-only mode enabled for ${agent.name}`
          : `Read-only mode disabled for ${agent.name}`,
        'success'
      )
    }
  } catch (error) {
    console.error('Failed to toggle read-only mode:', error)
    showNotification('Failed to toggle read-only mode', 'error')
  } finally {
    readOnlyLoading.value = null
  }
}

const toggleAgentRunning = async (agent) => {
  if (actionInProgress.value === agent.name) return
  actionInProgress.value = agent.name

  try {
    const result = await agentsStore.toggleAgentRunning(agent.name)
    if (result.success) {
      const action = result.status === 'running' ? 'started' : 'stopped'
      showNotification(`Agent ${agent.name} ${action}`, 'success')
    } else {
      showNotification(result.error || 'Failed to toggle agent', 'error')
    }
  } catch (error) {
    showNotification(error.message || 'Failed to toggle agent', 'error')
  } finally {
    actionInProgress.value = null
  }
}

// Tag-related functions
async function fetchAvailableTags() {
  try {
    const response = await axios.get('/api/tags')
    availableTags.value = response.data.tags || []
  } catch (err) {
    console.error('Failed to fetch tags:', err)
    availableTags.value = []
  }
}

async function fetchAllAgentTags() {
  // Fetch tags for all agents
  const agents = isAdmin.value ? agentsStore.sortedAgentsWithSystem : agentsStore.sortedAgents
  const tagsMap = {}

  await Promise.all(
    agents.map(async (agent) => {
      try {
        const response = await axios.get(`/api/agents/${agent.name}/tags`)
        tagsMap[agent.name] = response.data.tags || []
      } catch (err) {
        tagsMap[agent.name] = []
      }
    })
  )

  agentTags.value = tagsMap
}

function getAgentTags(agentName) {
  return agentTags.value[agentName] || []
}

function toggleSelection(agentName) {
  const index = selectedAgents.value.indexOf(agentName)
  if (index === -1) {
    selectedAgents.value.push(agentName)
  } else {
    selectedAgents.value.splice(index, 1)
  }
}

function clearSelection() {
  selectedAgents.value = []
  showBulkAddTag.value = false
  showBulkRemoveTag.value = false
}

async function applyBulkTag() {
  const tag = bulkTagInput.value.toLowerCase().trim()
  if (!tag) return

  // Validate tag format
  if (!/^[a-z0-9-]+$/.test(tag) || tag.length > 50) {
    showNotification('Invalid tag format. Use lowercase letters, numbers, and hyphens only.', 'error')
    return
  }

  try {
    await Promise.all(
      selectedAgents.value.map(agentName =>
        axios.post(`/api/agents/${agentName}/tags/${tag}`)
      )
    )
    showNotification(`Added tag "${tag}" to ${selectedAgents.value.length} agent(s)`, 'success')
    bulkTagInput.value = ''
    showBulkAddTag.value = false
    await fetchAllAgentTags()
    await fetchAvailableTags()
  } catch (err) {
    console.error('Failed to add tag:', err)
    showNotification('Failed to add tag to some agents', 'error')
  }
}

async function removeBulkTag(tag) {
  try {
    await Promise.all(
      selectedAgents.value.map(agentName =>
        axios.delete(`/api/agents/${agentName}/tags/${tag}`)
      )
    )
    showNotification(`Removed tag "${tag}" from ${selectedAgents.value.length} agent(s)`, 'success')
    showBulkRemoveTag.value = false
    await fetchAllAgentTags()
    await fetchAvailableTags()
  } catch (err) {
    console.error('Failed to remove tag:', err)
    showNotification('Failed to remove tag from some agents', 'error')
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
