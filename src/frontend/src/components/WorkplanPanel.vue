<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <div>
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">Workplan</h3>
        <p class="text-sm text-gray-500 dark:text-gray-400" title="This agent's internal task breakdown. Shows how the agent has organized its work into steps.">Explicit planning with task dependencies and progress tracking</p>
      </div>
      <div class="flex items-center space-x-2">
        <!-- Status Filter -->
        <select
          v-model="statusFilter"
          class="text-sm border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-800 dark:text-gray-200"
        >
          <option value="">All</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="paused">Paused</option>
        </select>
        <button
          @click="loadPlans"
          :disabled="loading"
          class="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
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
    </div>

    <!-- Summary Stats -->
    <div v-if="summary" class="grid grid-cols-5 gap-4">
      <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Total</p>
        <p class="text-2xl font-semibold text-gray-900 dark:text-white">{{ summary.total_plans }}</p>
      </div>
      <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Active</p>
        <p class="text-2xl font-semibold text-blue-600 dark:text-blue-400">{{ summary.active_plans }}</p>
      </div>
      <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Completed</p>
        <p class="text-2xl font-semibold text-green-600 dark:text-green-400">{{ summary.completed_plans }}</p>
      </div>
      <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Tasks</p>
        <p class="text-2xl font-semibold text-gray-900 dark:text-white">{{ summary.total_tasks }}</p>
      </div>
      <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Progress</p>
        <div class="flex items-center space-x-2">
          <p class="text-2xl font-semibold text-indigo-600 dark:text-indigo-400">{{ taskProgressPercent }}%</p>
          <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              class="h-full bg-indigo-500 rounded-full transition-all duration-300"
              :style="{ width: taskProgressPercent + '%' }"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Current Task Banner -->
    <div v-if="summary?.current_task" class="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div class="flex-shrink-0">
            <div class="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
          </div>
          <div>
            <p class="text-sm font-medium text-blue-900 dark:text-blue-100">Currently Active Task</p>
            <p class="text-sm text-blue-700 dark:text-blue-300">
              <span class="font-mono">{{ summary.current_task.task_name }}</span>
              <span class="text-blue-500 dark:text-blue-400 ml-2">in {{ summary.current_task.plan_name }}</span>
            </p>
          </div>
        </div>
        <button
          @click="viewPlan(summary.current_task.plan_id)"
          class="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium"
        >
          View Plan →
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && plans.length === 0" class="text-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mx-auto"></div>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">Loading workplan...</p>
    </div>

    <!-- Agent Not Running State -->
    <div v-else-if="agentNotRunning" class="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <svg class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
      </svg>
      <p class="mt-2 text-gray-500 dark:text-gray-400">Agent must be running to view workplan</p>
      <p class="text-sm text-gray-400 dark:text-gray-500">Start the agent to access its workplan system</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="plans.length === 0" class="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <svg class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
      </svg>
      <p class="mt-2 text-gray-500 dark:text-gray-400">No workplan yet</p>
      <p class="text-sm text-gray-400 dark:text-gray-500">Workplans are created when the agent uses /workplan commands to decompose complex tasks</p>
    </div>

    <!-- Plans List -->
    <div v-else class="space-y-3">
      <div
        v-for="plan in filteredPlans"
        :key="plan.id"
        @click="viewPlan(plan.id)"
        class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:border-indigo-300 dark:hover:border-indigo-600 cursor-pointer transition-colors"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="flex items-center space-x-2">
              <h4 class="text-sm font-medium text-gray-900 dark:text-white">{{ plan.name }}</h4>
              <span :class="getStatusBadgeClass(plan.status)">
                {{ plan.status }}
              </span>
            </div>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {{ plan.task_count }} tasks · {{ plan.completed_count }} completed
            </p>
          </div>
          <div class="text-right">
            <p class="text-xs text-gray-400 dark:text-gray-500">{{ formatRelativeTime(plan.updated || plan.created) }}</p>
            <div class="flex items-center justify-end space-x-1 mt-1">
              <div class="w-20 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-300"
                  :class="getProgressBarClass(plan.status)"
                  :style="{ width: plan.progress_percent + '%' }"
                ></div>
              </div>
              <span class="text-xs text-gray-500 dark:text-gray-400 w-8 text-right">{{ plan.progress_percent }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Plan Detail Modal -->
    <div v-if="selectedPlan" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 dark:bg-black dark:bg-opacity-60" @click="selectedPlan = null"></div>
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full relative z-10 max-h-[85vh] overflow-hidden flex flex-col">
          <!-- Header -->
          <div class="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-start">
            <div>
              <div class="flex items-center space-x-2">
                <h3 class="text-lg font-medium text-gray-900 dark:text-white">{{ selectedPlan.name }}</h3>
                <span :class="getStatusBadgeClass(selectedPlan.status)">
                  {{ selectedPlan.status }}
                </span>
              </div>
              <p v-if="selectedPlan.description" class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ selectedPlan.description }}</p>
              <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
                Created {{ formatDateTime(selectedPlan.created) }}
                <span v-if="selectedPlan.updated"> · Updated {{ formatRelativeTime(selectedPlan.updated) }}</span>
              </p>
            </div>
            <button @click="selectedPlan = null" class="text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Progress Bar -->
          <div class="px-4 py-3 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-200">Overall Progress</span>
              <span class="text-sm text-gray-500 dark:text-gray-400">{{ completedTaskCount }}/{{ selectedPlan.tasks?.length || 0 }} tasks</span>
            </div>
            <div class="w-full h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-300"
                :class="getProgressBarClass(selectedPlan.status)"
                :style="{ width: planProgressPercent + '%' }"
              ></div>
            </div>
          </div>

          <!-- Tasks List -->
          <div class="flex-1 overflow-y-auto p-4">
            <div class="space-y-3">
              <div
                v-for="task in selectedPlan.tasks"
                :key="task.id"
                class="border rounded-lg p-4"
                :class="getTaskBorderClass(task.status)"
              >
                <div class="flex items-start justify-between">
                  <div class="flex items-start space-x-3">
                    <!-- Status Icon -->
                    <div class="flex-shrink-0 mt-0.5">
                      <div v-if="task.status === 'completed'" class="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
                        <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <div v-else-if="task.status === 'active'" class="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                        <div class="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                      </div>
                      <div v-else-if="task.status === 'failed'" class="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center">
                        <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </div>
                      <div v-else-if="task.status === 'blocked'" class="w-5 h-5 rounded-full bg-yellow-500 flex items-center justify-center">
                        <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m0 0v2m0-2h2m-2 0H10m4-6V7a4 4 0 00-8 0v4h8z" />
                        </svg>
                      </div>
                      <div v-else class="w-5 h-5 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center">
                        <div class="w-2 h-2 bg-white rounded-full"></div>
                      </div>
                    </div>

                    <div class="flex-1">
                      <div class="flex items-center space-x-2">
                        <span class="text-sm font-medium text-gray-900 dark:text-white">{{ task.name }}</span>
                        <span class="text-xs font-mono text-gray-400 dark:text-gray-500">{{ task.id }}</span>
                      </div>
                      <p v-if="task.description" class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ task.description }}</p>

                      <!-- Dependencies -->
                      <div v-if="task.dependencies?.length" class="mt-2 flex items-center space-x-1">
                        <span class="text-xs text-gray-400 dark:text-gray-500">Depends on:</span>
                        <span
                          v-for="dep in task.dependencies"
                          :key="dep"
                          class="text-xs font-mono px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
                        >
                          {{ dep }}
                        </span>
                      </div>

                      <!-- Result -->
                      <div v-if="task.result" class="mt-2 bg-gray-50 dark:bg-gray-900 rounded p-2 text-xs font-mono text-gray-600 dark:text-gray-300 max-h-24 overflow-y-auto">
                        {{ task.result }}
                      </div>
                    </div>
                  </div>

                  <div class="text-right text-xs text-gray-400 dark:text-gray-500 space-y-1">
                    <div v-if="task.started_at">
                      Started: {{ formatDateTime(task.started_at) }}
                    </div>
                    <div v-if="task.completed_at">
                      Completed: {{ formatDateTime(task.completed_at) }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
            <div class="flex space-x-2">
              <button
                v-if="selectedPlan.status === 'active'"
                @click="pausePlan"
                class="px-3 py-1.5 text-sm font-medium text-yellow-700 dark:text-yellow-300 bg-yellow-100 dark:bg-yellow-900/50 rounded-md hover:bg-yellow-200 dark:hover:bg-yellow-900"
              >
                Pause Plan
              </button>
              <button
                v-if="selectedPlan.status === 'paused'"
                @click="resumePlan"
                class="px-3 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/50 rounded-md hover:bg-blue-200 dark:hover:bg-blue-900"
              >
                Resume Plan
              </button>
              <button
                @click="deletePlan"
                class="px-3 py-1.5 text-sm font-medium text-red-700 dark:text-red-300 bg-red-100 dark:bg-red-900/50 rounded-md hover:bg-red-200 dark:hover:bg-red-900"
              >
                Delete
              </button>
            </div>
            <button
              @click="selectedPlan = null"
              class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirm Dialog -->
    <ConfirmDialog
      v-model:visible="confirmDialog.visible"
      :title="confirmDialog.title"
      :message="confirmDialog.message"
      :confirm-text="confirmDialog.confirmText"
      :variant="confirmDialog.variant"
      @confirm="confirmDialog.onConfirm"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import ConfirmDialog from './ConfirmDialog.vue'
import { useAgentsStore } from '../stores/agents'

const props = defineProps({
  agentName: {
    type: String,
    required: true
  },
  agentStatus: {
    type: String,
    default: 'stopped'
  }
})

const agentsStore = useAgentsStore()

// State
const plans = ref([])
const summary = ref(null)
const loading = ref(false)
const selectedPlan = ref(null)
const statusFilter = ref('')
const agentNotRunning = ref(false)

// Confirm dialog state
const confirmDialog = reactive({
  visible: false,
  title: '',
  message: '',
  confirmText: 'Delete',
  variant: 'danger',
  onConfirm: () => {}
})

// Computed
const filteredPlans = computed(() => {
  if (!statusFilter.value) return plans.value
  return plans.value.filter(p => p.status === statusFilter.value)
})

const taskProgressPercent = computed(() => {
  if (!summary.value?.total_tasks) return 0
  return Math.round((summary.value.completed_tasks / summary.value.total_tasks) * 100)
})

const completedTaskCount = computed(() => {
  if (!selectedPlan.value?.tasks) return 0
  return selectedPlan.value.tasks.filter(t => t.status === 'completed').length
})

const planProgressPercent = computed(() => {
  if (!selectedPlan.value?.tasks?.length) return 0
  return Math.round((completedTaskCount.value / selectedPlan.value.tasks.length) * 100)
})

// Methods
async function loadPlans() {
  if (props.agentStatus !== 'running') {
    agentNotRunning.value = true
    plans.value = []
    summary.value = null
    return
  }

  agentNotRunning.value = false
  loading.value = true

  try {
    // Load both summary and plans in parallel
    const [summaryData, plansData] = await Promise.all([
      agentsStore.getAgentPlansSummary(props.agentName),
      agentsStore.getAgentPlans(props.agentName, statusFilter.value || null)
    ])

    summary.value = summaryData
    plans.value = plansData.plans || []
  } catch (error) {
    console.error('Failed to load plans:', error)
    if (error.response?.status === 400 || error.response?.status === 504) {
      agentNotRunning.value = true
    }
  } finally {
    loading.value = false
  }
}

async function viewPlan(planId) {
  try {
    const plan = await agentsStore.getAgentPlan(props.agentName, planId)
    selectedPlan.value = plan
  } catch (error) {
    console.error('Failed to load plan:', error)
  }
}

async function pausePlan() {
  if (!selectedPlan.value) return
  try {
    const updated = await agentsStore.updateAgentPlan(
      props.agentName,
      selectedPlan.value.id,
      { status: 'paused' }
    )
    selectedPlan.value = updated
    loadPlans()
  } catch (error) {
    console.error('Failed to pause plan:', error)
  }
}

async function resumePlan() {
  if (!selectedPlan.value) return
  try {
    const updated = await agentsStore.updateAgentPlan(
      props.agentName,
      selectedPlan.value.id,
      { status: 'active' }
    )
    selectedPlan.value = updated
    loadPlans()
  } catch (error) {
    console.error('Failed to resume plan:', error)
  }
}

function deletePlan() {
  if (!selectedPlan.value) return

  confirmDialog.title = 'Delete Plan'
  confirmDialog.message = `Delete plan "${selectedPlan.value.name}"? This cannot be undone.`
  confirmDialog.confirmText = 'Delete'
  confirmDialog.variant = 'danger'
  confirmDialog.onConfirm = async () => {
    try {
      await agentsStore.deleteAgentPlan(props.agentName, selectedPlan.value.id)
      selectedPlan.value = null
      loadPlans()
    } catch (error) {
      console.error('Failed to delete plan:', error)
    }
  }
  confirmDialog.visible = true
}

// Styling helpers
function getStatusBadgeClass(status) {
  const base = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium'
  switch (status) {
    case 'active': return `${base} bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300`
    case 'completed': return `${base} bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300`
    case 'failed': return `${base} bg-red-100 dark:bg-red-900/50 text-red-800 dark:text-red-300`
    case 'paused': return `${base} bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-300`
    default: return `${base} bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300`
  }
}

function getProgressBarClass(status) {
  switch (status) {
    case 'active': return 'bg-blue-500'
    case 'completed': return 'bg-green-500'
    case 'failed': return 'bg-red-500'
    case 'paused': return 'bg-yellow-500'
    default: return 'bg-gray-400'
  }
}

function getTaskBorderClass(status) {
  switch (status) {
    case 'completed': return 'border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-900/20'
    case 'active': return 'border-blue-300 dark:border-blue-700 bg-blue-50/50 dark:bg-blue-900/20'
    case 'failed': return 'border-red-200 dark:border-red-800 bg-red-50/50 dark:bg-red-900/20'
    case 'blocked': return 'border-yellow-200 dark:border-yellow-800 bg-yellow-50/50 dark:bg-yellow-900/20'
    default: return 'border-gray-200 dark:border-gray-700'
  }
}

// Format helpers
function formatDateTime(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}

function formatRelativeTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

// Watch for changes
watch(() => props.agentName, () => {
  selectedPlan.value = null
  loadPlans()
})

watch(() => props.agentStatus, () => {
  loadPlans()
})

watch(statusFilter, () => {
  loadPlans()
})

onMounted(() => {
  loadPlans()
})
</script>
