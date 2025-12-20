<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />

    <main class="max-w-6xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto"></div>
        <p class="mt-4 text-gray-500 dark:text-gray-400">Loading System Agent...</p>
      </div>

      <!-- Not Found State -->
      <div v-else-if="!systemAgent" class="text-center py-12">
        <div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6 max-w-md mx-auto">
          <svg class="w-12 h-12 text-yellow-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h3 class="text-lg font-medium text-yellow-800 dark:text-yellow-200">System Agent Not Found</h3>
          <p class="mt-2 text-sm text-yellow-700 dark:text-yellow-300">
            The system agent (trinity-system) is not deployed. It should auto-deploy on backend restart.
          </p>
        </div>
      </div>

      <!-- Main Content -->
      <div v-else>
        <!-- Header -->
        <div class="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-lg shadow-lg p-6 mb-6">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-4">
              <div class="bg-white/20 p-3 rounded-lg">
                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                </svg>
              </div>
              <div>
                <h1 class="text-2xl font-bold text-white">System Agent</h1>
                <p class="text-purple-200">Platform Operations Manager</p>
              </div>
            </div>
            <div class="flex items-center space-x-3">
              <span :class="[
                'px-3 py-1 text-sm font-medium rounded-full',
                systemAgent.status === 'running'
                  ? 'bg-green-400/20 text-green-100 border border-green-400/50'
                  : 'bg-gray-400/20 text-gray-200 border border-gray-400/50'
              ]">
                {{ systemAgent.status }}
              </span>
              <button
                v-if="systemAgent.status === 'stopped'"
                @click="startSystemAgent"
                :disabled="actionLoading"
                class="bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-lg font-medium transition-colors"
              >
                {{ actionLoading ? 'Starting...' : 'Start' }}
              </button>
              <button
                v-else
                @click="restartSystemAgent"
                :disabled="actionLoading"
                class="bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-lg font-medium transition-colors"
              >
                {{ actionLoading ? 'Restarting...' : 'Restart' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Fleet Overview Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <!-- Total Agents -->
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-gray-500 dark:text-gray-400">Total Agents</p>
                <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ fleetStatus.total }}</p>
              </div>
              <div class="bg-blue-100 dark:bg-blue-900/50 p-2 rounded-lg">
                <svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
            </div>
          </div>

          <!-- Running -->
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-gray-500 dark:text-gray-400">Running</p>
                <p class="text-2xl font-bold text-green-600 dark:text-green-400">{{ fleetStatus.running }}</p>
              </div>
              <div class="bg-green-100 dark:bg-green-900/50 p-2 rounded-lg">
                <svg class="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>

          <!-- Stopped -->
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-gray-500 dark:text-gray-400">Stopped</p>
                <p class="text-2xl font-bold text-gray-600 dark:text-gray-400">{{ fleetStatus.stopped }}</p>
              </div>
              <div class="bg-gray-100 dark:bg-gray-700 p-2 rounded-lg">
                <svg class="w-6 h-6 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                </svg>
              </div>
            </div>
          </div>

          <!-- Issues -->
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-gray-500 dark:text-gray-400">Issues</p>
                <p :class="[
                  'text-2xl font-bold',
                  fleetStatus.issues > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-600 dark:text-gray-400'
                ]">{{ fleetStatus.issues }}</p>
              </div>
              <div :class="[
                'p-2 rounded-lg',
                fleetStatus.issues > 0 ? 'bg-red-100 dark:bg-red-900/50' : 'bg-gray-100 dark:bg-gray-700'
              ]">
                <svg :class="[
                  'w-6 h-6',
                  fleetStatus.issues > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-600 dark:text-gray-400'
                ]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick Actions and Chat -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- Quick Actions -->
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div class="p-4 border-b border-gray-200 dark:border-gray-700">
              <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Quick Actions</h2>
            </div>
            <div class="p-4 space-y-3">
              <!-- Emergency Stop -->
              <button
                @click="emergencyStop"
                :disabled="emergencyLoading"
                class="w-full flex items-center justify-center space-x-2 bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white font-medium py-3 px-4 rounded-lg transition-colors"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                </svg>
                <span>{{ emergencyLoading ? 'Stopping...' : 'Emergency Stop' }}</span>
              </button>

              <!-- Restart All -->
              <button
                @click="restartAllAgents"
                :disabled="restartAllLoading"
                class="w-full flex items-center justify-center space-x-2 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-400 text-white font-medium py-3 px-4 rounded-lg transition-colors"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>{{ restartAllLoading ? 'Restarting...' : 'Restart All Agents' }}</span>
              </button>

              <!-- Pause Schedules -->
              <button
                @click="pauseAllSchedules"
                :disabled="pauseLoading"
                class="w-full flex items-center justify-center space-x-2 bg-yellow-500 hover:bg-yellow-600 disabled:bg-yellow-400 text-white font-medium py-3 px-4 rounded-lg transition-colors"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{{ pauseLoading ? 'Pausing...' : 'Pause Schedules' }}</span>
              </button>

              <!-- Resume Schedules -->
              <button
                @click="resumeAllSchedules"
                :disabled="resumeLoading"
                class="w-full flex items-center justify-center space-x-2 bg-green-500 hover:bg-green-600 disabled:bg-green-400 text-white font-medium py-3 px-4 rounded-lg transition-colors"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{{ resumeLoading ? 'Resuming...' : 'Resume Schedules' }}</span>
              </button>

              <!-- Refresh Status -->
              <button
                @click="refreshFleetStatus"
                :disabled="fleetLoading"
                class="w-full flex items-center justify-center space-x-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 font-medium py-3 px-4 rounded-lg transition-colors"
              >
                <svg :class="['w-5 h-5', fleetLoading ? 'animate-spin' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>Refresh Status</span>
              </button>
            </div>
          </div>

          <!-- Chat Panel -->
          <div class="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg shadow flex flex-col" style="height: 500px;">
            <div class="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Operations Console</h2>
              <div class="flex items-center space-x-2">
                <!-- Quick Commands -->
                <div class="flex space-x-1">
                  <button
                    @click="sendQuickCommand('/ops/status')"
                    class="text-xs px-2 py-1 bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 rounded hover:bg-purple-200 dark:hover:bg-purple-900"
                  >
                    /ops/status
                  </button>
                  <button
                    @click="sendQuickCommand('/ops/health')"
                    class="text-xs px-2 py-1 bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 rounded hover:bg-purple-200 dark:hover:bg-purple-900"
                  >
                    /ops/health
                  </button>
                  <button
                    @click="sendQuickCommand('/ops/schedules')"
                    class="text-xs px-2 py-1 bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 rounded hover:bg-purple-200 dark:hover:bg-purple-900"
                  >
                    /ops/schedules
                  </button>
                </div>
                <button
                  @click="clearChat"
                  class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                  title="Clear chat"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Messages Area -->
            <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4">
              <div v-if="messages.length === 0" class="text-center py-8">
                <svg class="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <p class="text-gray-500 dark:text-gray-400">Send a command to the System Agent</p>
                <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">Try: /ops/status, /ops/health, or ask questions</p>
              </div>

              <div
                v-for="msg in messages"
                :key="msg.id"
                :class="[
                  'flex',
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                ]"
              >
                <div :class="[
                  'max-w-[85%] rounded-lg px-4 py-2',
                  msg.role === 'user'
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                ]">
                  <div class="whitespace-pre-wrap text-sm" v-html="formatMessage(msg.content)"></div>
                  <div :class="[
                    'text-xs mt-1',
                    msg.role === 'user' ? 'text-purple-200' : 'text-gray-400 dark:text-gray-500'
                  ]">
                    {{ formatTime(msg.timestamp) }}
                  </div>
                </div>
              </div>

              <!-- Typing indicator -->
              <div v-if="isTyping" class="flex justify-start">
                <div class="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-2">
                  <div class="flex space-x-1">
                    <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms;"></div>
                    <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms;"></div>
                    <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms;"></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Input Area -->
            <div class="p-4 border-t border-gray-200 dark:border-gray-700">
              <form @submit.prevent="sendMessage" class="flex space-x-2">
                <input
                  v-model="inputMessage"
                  type="text"
                  placeholder="Enter command or message..."
                  :disabled="isTyping || systemAgent?.status !== 'running'"
                  class="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
                />
                <button
                  type="submit"
                  :disabled="!inputMessage.trim() || isTyping || systemAgent?.status !== 'running'"
                  class="bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                >
                  Send
                </button>
              </form>
              <p v-if="systemAgent?.status !== 'running'" class="text-xs text-yellow-600 dark:text-yellow-400 mt-2">
                System agent must be running to send commands
              </p>
            </div>
          </div>
        </div>

        <!-- Notification Toast -->
        <div
          v-if="notification"
          :class="[
            'fixed bottom-4 right-4 px-4 py-3 rounded-lg shadow-lg transition-all duration-300 z-50',
            notification.type === 'success' ? 'bg-green-500 text-white' :
            notification.type === 'error' ? 'bg-red-500 text-white' :
            'bg-purple-500 text-white'
          ]"
        >
          {{ notification.message }}
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import NavBar from '../components/NavBar.vue'
import { useAuthStore } from '../stores/auth'
import { useAgentsStore } from '../stores/agents'
import { marked } from 'marked'

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true
})

const router = useRouter()
const authStore = useAuthStore()
const agentsStore = useAgentsStore()

// State
const loading = ref(true)
const systemAgent = ref(null)
const actionLoading = ref(false)

// Fleet status
const fleetStatus = ref({
  total: 0,
  running: 0,
  stopped: 0,
  issues: 0
})
const fleetLoading = ref(false)

// Quick action loading states
const emergencyLoading = ref(false)
const restartAllLoading = ref(false)
const pauseLoading = ref(false)
const resumeLoading = ref(false)

// Chat state
const messages = ref([])
const inputMessage = ref('')
const isTyping = ref(false)
const messagesContainer = ref(null)

// Notifications
const notification = ref(null)

// Polling interval
let pollingInterval = null

// Load system agent status
async function loadSystemAgent() {
  try {
    const response = await axios.get('/api/system-agent/status', {
      headers: authStore.authHeader
    })
    systemAgent.value = response.data
  } catch (error) {
    console.error('Failed to load system agent:', error)
    systemAgent.value = null
  } finally {
    loading.value = false
  }
}

// Fetch fleet status from ops API
async function refreshFleetStatus() {
  fleetLoading.value = true
  try {
    const response = await axios.get('/api/ops/fleet/status', {
      headers: authStore.authHeader
    })
    const agents = response.data.agents || []

    // Don't count system agent in stats
    const nonSystemAgents = agents.filter(a => a.name !== 'trinity-system')

    fleetStatus.value = {
      total: nonSystemAgents.length,
      running: nonSystemAgents.filter(a => a.status === 'running').length,
      stopped: nonSystemAgents.filter(a => a.status === 'stopped').length,
      issues: nonSystemAgents.filter(a => a.health_status === 'critical' || a.health_status === 'warning').length
    }
  } catch (error) {
    console.error('Failed to fetch fleet status:', error)
  } finally {
    fleetLoading.value = false
  }
}

// System agent actions
async function startSystemAgent() {
  actionLoading.value = true
  try {
    await axios.post('/api/system-agent/restart', {}, {
      headers: authStore.authHeader
    })
    showNotification('System agent started', 'success')
    await loadSystemAgent()
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to start system agent', 'error')
  } finally {
    actionLoading.value = false
  }
}

async function restartSystemAgent() {
  actionLoading.value = true
  try {
    await axios.post('/api/system-agent/restart', {}, {
      headers: authStore.authHeader
    })
    showNotification('System agent restarted', 'success')
    await loadSystemAgent()
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to restart system agent', 'error')
  } finally {
    actionLoading.value = false
  }
}

// Quick actions
async function emergencyStop() {
  if (!confirm('This will stop ALL agents and pause ALL schedules. Continue?')) return

  emergencyLoading.value = true
  try {
    const response = await axios.post('/api/ops/emergency-stop', {}, {
      headers: authStore.authHeader
    })
    showNotification(`Emergency stop: ${response.data.agents_stopped} agents stopped, ${response.data.schedules_paused} schedules paused`, 'success')
    await refreshFleetStatus()
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Emergency stop failed', 'error')
  } finally {
    emergencyLoading.value = false
  }
}

async function restartAllAgents() {
  if (!confirm('This will restart ALL agents. Continue?')) return

  restartAllLoading.value = true
  try {
    const response = await axios.post('/api/ops/fleet/restart', {}, {
      headers: authStore.authHeader
    })
    showNotification(`Restarted ${response.data.restarted?.length || 0} agents`, 'success')
    await refreshFleetStatus()
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Restart failed', 'error')
  } finally {
    restartAllLoading.value = false
  }
}

async function pauseAllSchedules() {
  pauseLoading.value = true
  try {
    const response = await axios.post('/api/ops/schedules/pause', {}, {
      headers: authStore.authHeader
    })
    showNotification(`Paused ${response.data.paused_count || 0} schedules`, 'success')
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to pause schedules', 'error')
  } finally {
    pauseLoading.value = false
  }
}

async function resumeAllSchedules() {
  resumeLoading.value = true
  try {
    const response = await axios.post('/api/ops/schedules/resume', {}, {
      headers: authStore.authHeader
    })
    showNotification(`Resumed ${response.data.resumed_count || 0} schedules`, 'success')
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to resume schedules', 'error')
  } finally {
    resumeLoading.value = false
  }
}

// Chat functions
async function sendMessage() {
  const message = inputMessage.value.trim()
  if (!message || isTyping.value) return

  // Add user message
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: message,
    timestamp: new Date()
  })
  inputMessage.value = ''
  scrollToBottom()

  isTyping.value = true
  try {
    const response = await axios.post('/api/agents/trinity-system/chat',
      { message },
      { headers: authStore.authHeader }
    )

    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: response.data.response || response.data.message || 'No response',
      timestamp: new Date()
    })
  } catch (error) {
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: `Error: ${error.response?.data?.detail || error.message}`,
      timestamp: new Date()
    })
  } finally {
    isTyping.value = false
    scrollToBottom()
  }
}

function sendQuickCommand(command) {
  inputMessage.value = command
  sendMessage()
}

function clearChat() {
  messages.value = []
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function formatMessage(content) {
  try {
    return marked(content)
  } catch {
    return content
  }
}

function formatTime(date) {
  return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// Notifications
function showNotification(message, type = 'info') {
  notification.value = { message, type }
  setTimeout(() => {
    notification.value = null
  }, 3000)
}

// Lifecycle
onMounted(async () => {
  await loadSystemAgent()
  await refreshFleetStatus()

  // Start polling
  pollingInterval = setInterval(() => {
    loadSystemAgent()
    refreshFleetStatus()
  }, 10000)
})

onUnmounted(() => {
  if (pollingInterval) {
    clearInterval(pollingInterval)
  }
})
</script>
