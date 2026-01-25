<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />
    <AgentSubNav />

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <div v-if="loading" class="text-center py-8">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto"></div>
        </div>

        <!-- Notification Toast -->
        <div v-if="notification"
          :class="[
            'fixed top-20 right-4 z-50 px-4 py-3 rounded-lg shadow-lg transition-all duration-300',
            notification.type === 'success' ? 'bg-green-100 dark:bg-green-900/50 border border-green-400 dark:border-green-700 text-green-700 dark:text-green-300' : 'bg-red-100 dark:bg-red-900/50 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-300'
          ]"
        >
          {{ notification.message }}
        </div>

        <div v-if="error && !agent" class="bg-red-100 dark:bg-red-900/50 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded mb-4">
          {{ error }}
        </div>

        <div v-if="agent">
          <!-- Agent Header Component -->
          <AgentHeader
            :agent="agent"
            :action-loading="actionLoading"
            :autonomy-loading="autonomyLoading"
            :agent-stats="agentStats"
            :stats-loading="statsLoading"
            :cpu-history="cpuHistory"
            :memory-history="memoryHistory"
            :resource-limits="resourceLimits"
            :has-git-sync="hasGitSync"
            :git-status="gitStatus"
            :git-loading="gitLoading"
            :git-syncing="gitSyncing"
            :git-pulling="gitPulling"
            :git-has-changes="gitHasChanges"
            :git-changes-count="gitChangesCount"
            :git-behind="gitBehind"
            @start="startAgent"
            @stop="stopAgent"
            @delete="deleteAgent"
            @toggle-autonomy="toggleAutonomy"
            @open-resource-modal="showResourceModal = true"
            @git-pull="pullFromGithub"
            @git-push="syncToGithub"
            @git-refresh="refreshGitStatus"
          />

          <!-- Tabs -->
          <div class="bg-white dark:bg-gray-800 shadow dark:shadow-gray-900 rounded-lg">
            <div class="border-b border-gray-200 dark:border-gray-700 overflow-x-auto overflow-y-hidden">
              <nav class="-mb-px flex whitespace-nowrap">
                <button
                  v-for="tab in visibleTabs"
                  :key="tab.id"
                  @click="activeTab = tab.id"
                  :class="[
                    'px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                    activeTab === tab.id
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  {{ tab.label }}
                  <span v-if="tab.badge" class="ml-1.5 px-1.5 py-0.5 text-[10px] font-semibold bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300 rounded-full leading-none">
                    {{ tab.badge }}
                  </span>
                </button>
              </nav>
            </div>

            <!-- Info Tab Content -->
            <div v-if="activeTab === 'info'" class="p-6">
              <InfoPanel :agent-name="agent.name" :agent-status="agent.status" @item-click="handleInfoItemClick" />
            </div>

            <!-- Tasks Tab Content -->
            <div v-if="activeTab === 'tasks'" class="p-6">
              <TasksPanel :agent-name="agent.name" :agent-status="agent.status" :highlight-execution-id="route.query.execution" :initial-message="taskPrefillMessage" @create-schedule="handleCreateSchedule" />
            </div>

            <!-- Dashboard Tab Content -->
            <div v-if="activeTab === 'dashboard'" class="p-6">
              <DashboardPanel :agent-name="agent.name" :agent-status="agent.status" />
            </div>

            <!-- Terminal Tab Content -->
            <!-- Using v-show instead of v-if to keep terminal mounted and WebSocket connected when switching tabs -->
            <div
              v-show="activeTab === 'terminal'"
              :class="[
                'transition-all duration-300',
                isTerminalFullscreen ? 'fixed inset-0 z-50 bg-gray-900' : ''
              ]"
              @keydown="handleTerminalKeydown"
            >
              <TerminalPanelContent
                ref="terminalRef"
                :agent-name="agent.name"
                :agent-status="agent.status"
                :runtime="agent.runtime || 'claude-code'"
                :model="currentModel"
                :is-fullscreen="isTerminalFullscreen"
                :can-share="agent.can_share"
                :api-key-setting="apiKeySetting"
                :api-key-setting-loading="apiKeySettingLoading"
                :action-loading="actionLoading"
                @toggle-fullscreen="toggleTerminalFullscreen"
                @connected="onTerminalConnected"
                @disconnected="onTerminalDisconnected"
                @error="onTerminalError"
                @start-agent="startAgent"
                @update-api-key-setting="updateApiKeySetting"
              />
            </div>

            <!-- Logs Tab Content -->
            <div v-if="activeTab === 'logs'">
              <LogsPanel :agent-name="agent.name" :agent-status="agent.status" />
            </div>

            <!-- Credentials Tab Content -->
            <div v-if="activeTab === 'credentials'">
              <CredentialsPanel :agent-name="agent.name" :agent-status="agent.status" />
            </div>

            <!-- Sharing Tab Content -->
            <div v-if="activeTab === 'sharing' && agent.can_share">
              <SharingPanel
                :agent-name="agent.name"
                :shares="agent.shares"
                @agent-updated="loadAgent"
              />
            </div>

            <!-- Permissions Tab Content -->
            <div v-if="activeTab === 'permissions' && agent.can_share">
              <PermissionsPanel :agent-name="agent.name" :agent-status="agent.status" />
            </div>

            <!-- Schedules Tab Content -->
            <div v-if="activeTab === 'schedules'" class="p-6">
              <SchedulesPanel :agent-name="agent.name" :initial-message="schedulePrefillMessage" />
            </div>

            <!-- Git Tab Content -->
            <div v-if="activeTab === 'git'" class="p-6">
              <GitPanel :agent-name="agent.name" :agent-status="agent.status" />
            </div>

            <!-- Files Tab Content -->
            <div v-if="activeTab === 'files'">
              <FilesPanel :agent-name="agent.name" :agent-status="agent.status" />
            </div>

            <!-- Skills Tab Content -->
            <div v-if="activeTab === 'skills'">
              <SkillsPanel :agent-name="agent.name" :agent-status="agent.status" />
            </div>

            <!-- Shared Folders Tab Content -->
            <div v-if="activeTab === 'folders'" class="p-6">
              <FoldersPanel :agent-name="agent.name" :agent-status="agent.status" :can-share="agent.can_share" />
            </div>

            <!-- Public Links Tab Content -->
            <div v-if="activeTab === 'public-links'" class="p-6">
              <PublicLinksPanel :agent-name="agent.name" />
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Resource Modal -->
    <ResourceModal
      :show="showResourceModal"
      :resource-limits="resourceLimits"
      :loading="resourceLimitsLoading"
      @update:show="showResourceModal = $event"
      @update:memory="resourceLimits.memory = $event"
      @update:cpu="resourceLimits.cpu = $event"
      @save="saveResourceLimits"
    />

    <!-- Confirm Dialog -->
    <ConfirmDialog
      v-model:visible="confirmDialog.visible"
      :title="confirmDialog.title"
      :message="confirmDialog.message"
      :confirm-text="confirmDialog.confirmText"
      :variant="confirmDialog.variant"
      @confirm="confirmDialog.onConfirm"
    />

    <!-- Git Conflict Resolution Modal -->
    <GitConflictModal
      :show="showConflictModal"
      :conflict="gitConflict"
      @resolve="resolveConflict"
      @dismiss="dismissConflict"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, onDeactivated, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAgentsStore } from '../stores/agents'
import NavBar from '../components/NavBar.vue'
import AgentSubNav from '../components/AgentSubNav.vue'

// Component name for KeepAlive matching
defineOptions({
  name: 'AgentDetail'
})

// UI Components
import ConfirmDialog from '../components/ConfirmDialog.vue'
import GitConflictModal from '../components/GitConflictModal.vue'

// Panel Components (existing)
import SchedulesPanel from '../components/SchedulesPanel.vue'
import TasksPanel from '../components/TasksPanel.vue'
import GitPanel from '../components/GitPanel.vue'
import InfoPanel from '../components/InfoPanel.vue'
import DashboardPanel from '../components/DashboardPanel.vue'
import FoldersPanel from '../components/FoldersPanel.vue'
import PublicLinksPanel from '../components/PublicLinksPanel.vue'

// Panel Components (newly extracted)
import AgentHeader from '../components/AgentHeader.vue'
import ResourceModal from '../components/ResourceModal.vue'
import LogsPanel from '../components/LogsPanel.vue'
import CredentialsPanel from '../components/CredentialsPanel.vue'
import SharingPanel from '../components/SharingPanel.vue'
import PermissionsPanel from '../components/PermissionsPanel.vue'
import FilesPanel from '../components/FilesPanel.vue'
import TerminalPanelContent from '../components/TerminalPanelContent.vue'
import SkillsPanel from '../components/SkillsPanel.vue'

// Import composables
import { useNotification } from '../composables'
import { useAgentLifecycle } from '../composables/useAgentLifecycle'
import { useAgentStats } from '../composables/useAgentStats'
import { useAgentTerminal } from '../composables/useAgentTerminal'
import { useGitSync } from '../composables/useGitSync'
import { useAgentSettings } from '../composables/useAgentSettings'
import { useSessionActivity } from '../composables/useSessionActivity'

// Setup
const route = useRoute()
const router = useRouter()
const agentsStore = useAgentsStore()

// Minimal local state
const agent = ref(null)
const loading = ref(true)
const error = ref('')
const activeTab = ref('info')
const showResourceModal = ref(false)
const taskPrefillMessage = ref('')
const schedulePrefillMessage = ref('')

// Initialize composables
const { notification, showNotification } = useNotification()

// Agent lifecycle composable
const {
  actionLoading,
  confirmDialog,
  startAgent,
  stopAgent,
  deleteAgent
} = useAgentLifecycle(agent, agentsStore, router, showNotification)

// Stats composable
const {
  agentStats,
  statsLoading,
  cpuHistory,
  memoryHistory,
  startStatsPolling,
  stopStatsPolling
} = useAgentStats(agent, agentsStore)

// Terminal composable
const {
  isTerminalFullscreen,
  terminalRef,
  toggleTerminalFullscreen,
  handleTerminalKeydown,
  onTerminalConnected,
  onTerminalDisconnected,
  onTerminalError
} = useAgentTerminal(showNotification)

// Git sync composable
const {
  hasGitSync,
  gitStatus,
  gitLoading,
  gitSyncing,
  gitPulling,
  gitHasChanges,
  gitChangesCount,
  gitBehind,
  gitConflict,
  showConflictModal,
  refreshGitStatus,
  syncToGithub,
  pullFromGithub,
  resolveConflict,
  dismissConflict,
  startGitStatusPolling,
  stopGitStatusPolling
} = useGitSync(agent, agentsStore, showNotification)

// Autonomy mode state
const autonomyLoading = ref(false)

async function toggleAutonomy() {
  if (!agent.value || autonomyLoading.value) return

  autonomyLoading.value = true
  const newState = !agent.value.autonomy_enabled

  try {
    const response = await fetch(`/api/agents/${agent.value.name}/autonomy`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ enabled: newState })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to update autonomy mode')
    }

    const result = await response.json()

    // Update local state
    agent.value.autonomy_enabled = newState

    showNotification(
      newState
        ? `Autonomy enabled. ${result.schedules_updated} schedule(s) activated.`
        : `Autonomy disabled. ${result.schedules_updated} schedule(s) paused.`,
      'success'
    )
  } catch (error) {
    console.error('Failed to toggle autonomy:', error)
    showNotification(error.message || 'Failed to update autonomy mode', 'error')
  } finally {
    autonomyLoading.value = false
  }
}

// Default model based on runtime
const defaultModel = computed(() => {
  const runtime = agent.value?.runtime || 'claude-code'
  if (runtime === 'gemini-cli' || runtime === 'gemini') {
    return 'gemini-2.5-flash'
  }
  return 'sonnet' // Claude default
})

// Agent settings composable
const {
  apiKeySetting,
  apiKeySettingLoading,
  loadApiKeySetting,
  updateApiKeySetting,
  currentModel,
  resourceLimits,
  resourceLimitsLoading,
  loadResourceLimits,
  updateResourceLimits
} = useAgentSettings(agent, agentsStore, showNotification)

// Save resource limits and restart agent if needed
async function saveResourceLimits() {
  // Check if values actually changed
  const newMemory = resourceLimits.value.memory || resourceLimits.value.current_memory
  const newCpu = resourceLimits.value.cpu || resourceLimits.value.current_cpu
  const oldMemory = resourceLimits.value.current_memory
  const oldCpu = resourceLimits.value.current_cpu
  const valuesChanged = newMemory !== oldMemory || newCpu !== oldCpu

  await updateResourceLimits()
  showResourceModal.value = false

  // If values changed and agent is running, restart it
  if (valuesChanged && agent.value?.status === 'running') {
    showNotification('Restarting agent to apply new resource limits...', 'info')
    await stopAgent()
    // Wait a moment for container to fully stop
    await new Promise(resolve => setTimeout(resolve, 1000))
    await startAgent()
  }
}

// Session activity composable
const {
  sessionInfo,
  startActivityPolling,
  stopActivityPolling,
  loadSessionInfo,
  resetSessionActivity
} = useSessionActivity(agent, agentsStore)

// Computed tabs based on agent permissions and system agent status
const visibleTabs = computed(() => {
  const isSystem = agent.value?.is_system

  const tabs = [
    { id: 'info', label: 'Info' },
    { id: 'tasks', label: 'Tasks' },
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'terminal', label: 'Terminal' },
    { id: 'logs', label: 'Logs' },
    { id: 'credentials', label: 'Credentials' },
    { id: 'skills', label: 'Skills' }
  ]

  // Sharing/Permissions - hide for system agent (system agent has full access)
  if (agent.value?.can_share && !isSystem) {
    tabs.push({ id: 'sharing', label: 'Sharing' })
    tabs.push({ id: 'permissions', label: 'Permissions' })
  }

  // Schedules - show for all agents including system
  tabs.push({ id: 'schedules', label: 'Schedules' })

  if (hasGitSync.value) {
    tabs.push({ id: 'git', label: 'Git' })
  }

  tabs.push({ id: 'files', label: 'Files' })

  // Folders and Public Links - hide for system agent
  if (agent.value?.can_share && !isSystem) {
    tabs.push({ id: 'folders', label: 'Folders' })
    tabs.push({ id: 'public-links', label: 'Public Links' })
  }

  return tabs
})

// Load agent
async function loadAgent() {
  loading.value = true
  error.value = ''
  try {
    agent.value = await agentsStore.fetchAgent(route.params.name)
  } catch (err) {
    error.value = 'Failed to load agent details'
  } finally {
    loading.value = false
  }
}

// Watch for route changes (when navigating to a different agent)
watch(() => route.params.name, async (newName, oldName) => {
  if (newName && newName !== oldName) {
    // Stop polling for old agent
    stopAllPolling()
    // Disconnect terminal from old agent
    if (terminalRef.value?.disconnect) {
      terminalRef.value.disconnect()
    }
    // Load new agent data
    await loadAgent()
    await loadSessionInfo()
    await loadApiKeySetting()
    await loadResourceLimits()
    startAllPolling()
    // Connect terminal to new agent if on terminal tab and agent is running
    if (activeTab.value === 'terminal' && agent.value?.status === 'running') {
      nextTick(() => {
        if (terminalRef.value?.connect) {
          terminalRef.value.connect()
        }
      })
    }
  }
})

// Watch agent status for stats, activity, and git polling
watch(() => agent.value?.status, (newStatus) => {
  if (newStatus === 'running') {
    startStatsPolling()
    startActivityPolling()
    if (hasGitSync.value) {
      startGitStatusPolling()
    }
  } else {
    stopStatsPolling()
    stopActivityPolling()
    stopGitStatusPolling()
    resetSessionActivity()
  }
})

// Initialize model to default when agent is loaded and model is not set
watch(() => agent.value?.runtime, (newRuntime) => {
  if (newRuntime && !currentModel.value) {
    currentModel.value = defaultModel.value
  }
}, { immediate: true })

// Start all polling (used on mount and activation)
function startAllPolling() {
  if (agent.value?.status === 'running') {
    startStatsPolling()
    startActivityPolling()
    if (hasGitSync.value) {
      startGitStatusPolling()
    }
  }
}

// Stop all polling (used on deactivation and unmount)
function stopAllPolling() {
  stopStatsPolling()
  stopActivityPolling()
  stopGitStatusPolling()
}

// Initialize on mount
onMounted(async () => {
  await loadAgent()
  await loadSessionInfo()
  await loadApiKeySetting()
  await loadResourceLimits()
  startAllPolling()

  // Handle tab query param (from Timeline click navigation)
  if (route.query.tab) {
    const requestedTab = route.query.tab
    const validTabs = ['info', 'tasks', 'metrics', 'terminal', 'logs', 'credentials', 'sharing', 'permissions', 'schedules', 'git', 'files', 'folders', 'public-links']
    if (validTabs.includes(requestedTab)) {
      activeTab.value = requestedTab
    }
  }
})

// onActivated fires when component is shown (after being cached by KeepAlive)
onActivated(() => {
  // Restart polling when returning to this view
  startAllPolling()
  // Refresh agent data
  loadAgent()
  // Refit terminal if on terminal tab
  if (activeTab.value === 'terminal') {
    nextTick(() => {
      if (terminalRef.value?.fit) {
        terminalRef.value.fit()
      }
    })
  }
})

// onDeactivated fires when navigating away (component is cached, not destroyed)
onDeactivated(() => {
  // Stop polling when navigating away (but keep WebSocket connection alive)
  stopAllPolling()
})

// onUnmounted fires when component is actually destroyed
onUnmounted(() => {
  stopAllPolling()
})

// Handle item click from Info tab - switch to Tasks tab with prefilled message
const handleInfoItemClick = ({ type, text }) => {
  // Set the prefill message and switch to Tasks tab
  taskPrefillMessage.value = text
  activeTab.value = 'tasks'
  // Clear the prefill after a short delay so it can be used again
  nextTick(() => {
    setTimeout(() => {
      taskPrefillMessage.value = ''
    }, 100)
  })
}

// Handle create schedule from Tasks tab - switch to Schedules tab with prefilled message
const handleCreateSchedule = (message) => {
  // Set the prefill message and switch to Schedules tab
  schedulePrefillMessage.value = message
  activeTab.value = 'schedules'
  // Clear the prefill after a short delay so it can be used again
  nextTick(() => {
    setTimeout(() => {
      schedulePrefillMessage.value = ''
    }, 100)
  })
}
</script>

<style scoped>
/* Animated progress bar pulse effect */
@keyframes progress-pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.animate-progress-pulse {
  animation: progress-pulse 2s ease-in-out infinite;
}

/* Shimmer effect for progress bars */
@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

.animate-shimmer {
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.3) 50%,
    transparent 100%
  );
  background-size: 200% 100%;
  animation: shimmer 2s ease-in-out infinite;
}
</style>
