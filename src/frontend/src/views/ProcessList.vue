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

        <!-- Header -->
        <div class="flex justify-between items-center mb-8">
          <div>
            <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Processes</h1>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Create and manage automated process workflows
            </p>
          </div>

          <div class="flex items-center space-x-4">
            <!-- Status filter -->
            <select
              v-model="statusFilter"
              class="block rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm py-2 px-3 bg-white dark:bg-gray-700 dark:text-gray-200 border"
            >
              <option value="">All Status</option>
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="archived">Archived</option>
            </select>

            <!-- Sort dropdown -->
            <select
              v-model="processesStore.sortBy"
              class="block rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm py-2 px-3 bg-white dark:bg-gray-700 dark:text-gray-200 border"
            >
              <option value="created_desc">Newest First</option>
              <option value="created_asc">Oldest First</option>
              <option value="name_asc">Name (A-Z)</option>
              <option value="name_desc">Name (Z-A)</option>
              <option value="status">Status</option>
            </select>

            <router-link
              to="/processes/new"
              class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded inline-flex items-center"
            >
              <PlusIcon class="h-5 w-5 mr-1" />
              Create Process
            </router-link>
          </div>
        </div>

        <!-- Loading state -->
        <div v-if="processesStore.loading && displayProcesses.length === 0" class="flex justify-center py-12">
          <div class="flex items-center gap-3 text-gray-500 dark:text-gray-400">
            <svg class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Loading processes...</span>
          </div>
        </div>

        <!-- Error state -->
        <div v-else-if="processesStore.error" class="text-center py-12 bg-white dark:bg-gray-800 rounded-xl shadow">
          <ExclamationCircleIcon class="mx-auto h-12 w-12 text-red-400" />
          <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">Error loading processes</h3>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">{{ processesStore.error }}</p>
          <div class="mt-6">
            <button
              @click="processesStore.fetchProcesses()"
              class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
            >
              Try again
            </button>
          </div>
        </div>

        <!-- Processes Grid -->
        <div v-else-if="displayProcesses.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="process in displayProcesses"
            :key="process.id"
            :class="[
              'bg-white dark:bg-gray-800 rounded-xl border shadow-lg p-5',
              'transition-all duration-200 hover:shadow-xl',
              'flex flex-col',
              process.status === 'published'
                ? 'border-green-200 dark:border-green-800/50'
                : process.status === 'archived'
                  ? 'border-gray-300 dark:border-gray-600 opacity-75'
                  : 'border-gray-200 dark:border-gray-700'
            ]"
          >
            <!-- Header: Name and Status -->
            <div class="flex items-center justify-between mb-2">
              <router-link
                :to="`/processes/${process.id}`"
                class="text-gray-900 dark:text-white font-bold text-base truncate hover:text-indigo-600 dark:hover:text-indigo-400 flex-1 mr-2"
                :title="process.name"
              >
                {{ process.name }}
              </router-link>

              <!-- Status badge -->
              <span :class="[
                'px-2 py-1 text-xs font-semibold rounded-full flex-shrink-0',
                process.status === 'published'
                  ? 'bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300'
                  : process.status === 'archived'
                    ? 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                    : 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-300'
              ]">
                {{ process.status }}
              </span>
            </div>

            <!-- Version and description -->
            <div class="text-xs text-gray-500 dark:text-gray-400 mb-2">
              Version {{ process.version }}
            </div>

            <p class="text-sm text-gray-600 dark:text-gray-300 mb-3 line-clamp-2 flex-grow">
              {{ process.description || 'No description' }}
            </p>

            <!-- Steps count and schedule info -->
            <div class="flex flex-col gap-2 text-xs text-gray-500 dark:text-gray-400 mb-3">
              <div class="flex items-center gap-4">
                <span class="flex items-center">
                  <CubeIcon class="w-4 h-4 mr-1" />
                  {{ process.step_count || 0 }} steps
                </span>
                <span v-if="process.last_run_at" class="flex items-center">
                  <ClockIcon class="w-4 h-4 mr-1" />
                  {{ formatRelativeTime(process.last_run_at) }}
                </span>
              </div>
              <!-- Schedule info -->
              <div v-if="scheduleInfo[process.id]?.next_run_at" class="flex items-center gap-1 text-purple-600 dark:text-purple-400">
                <CalendarIcon class="w-4 h-4" />
                <span>Next: {{ formatNextRunTime(scheduleInfo[process.id].next_run_at) }}</span>
              </div>
            </div>

            <!-- Action buttons -->
            <div class="flex items-center justify-between mt-auto pt-3 border-t border-gray-100 dark:border-gray-700/50">
              <span class="text-xs text-gray-400 dark:text-gray-500">
                {{ formatDate(process.created_at) }}
              </span>

              <div class="flex items-center space-x-2">
                <!-- Execute button (only for published) -->
                <button
                  v-if="process.status === 'published'"
                  @click="handleExecute(process)"
                  :disabled="actionInProgress === process.id"
                  class="p-1.5 rounded-lg bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/50 disabled:opacity-50 transition-colors"
                  title="Execute process"
                >
                  <PlayIcon class="h-5 w-5" />
                </button>

                <!-- Edit button -->
                <router-link
                  :to="`/processes/${process.id}`"
                  class="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
                  :title="process.status === 'draft' ? 'Edit process' : 'View process'"
                >
                  <PencilIcon v-if="process.status === 'draft'" class="h-5 w-5" />
                  <EyeIcon v-else class="h-5 w-5" />
                </router-link>

                <!-- Delete button -->
                <button
                  @click="handleDelete(process)"
                  :disabled="actionInProgress === process.id"
                  class="p-1.5 rounded-lg bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/50 disabled:opacity-50 transition-colors"
                  title="Delete process"
                >
                  <TrashIcon class="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty state -->
        <div v-else class="text-center py-12 bg-white dark:bg-gray-800 rounded-xl shadow">
          <CubeTransparentIcon class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />
          <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">No processes</h3>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">Get started by creating a new process workflow.</p>
          <div class="mt-6">
            <router-link
              to="/processes/new"
              class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
            >
              <PlusIcon class="h-5 w-5 mr-1" />
              Create Process
            </router-link>
          </div>
        </div>

        <!-- Confirm Delete Modal -->
        <ConfirmDialog
          v-if="deleteTarget"
          :visible="true"
          title="Delete Process"
          :message="`Are you sure you want to delete '${deleteTarget.name}'? This action cannot be undone.`"
          confirm-text="Delete"
          @confirm="confirmDelete"
          @cancel="deleteTarget = null"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useProcessesStore } from '../stores/processes'
import NavBar from '../components/NavBar.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import {
  PlusIcon,
  PlayIcon,
  PencilIcon,
  EyeIcon,
  TrashIcon,
  CubeIcon,
  ClockIcon,
  CalendarIcon,
  CubeTransparentIcon,
  ExclamationCircleIcon,
} from '@heroicons/vue/24/outline'
import api from '../api'

const processesStore = useProcessesStore()
const notification = ref(null)
const actionInProgress = ref(null)
const deleteTarget = ref(null)
const statusFilter = ref('')
const scheduleInfo = ref({})

// Computed
const displayProcesses = computed(() => {
  let list = processesStore.sortedProcesses

  if (statusFilter.value) {
    list = list.filter(p => p.status === statusFilter.value)
  }

  return list
})

// Lifecycle
onMounted(async () => {
  await processesStore.fetchProcesses()
  await loadScheduleInfo()
})

async function loadScheduleInfo() {
  try {
    const response = await api.get('/api/triggers/schedules')
    // Build a map by process_id for easy lookup
    const infoMap = {}
    for (const schedule of response.data) {
      // Use the first schedule for each process (or the one with earliest next_run)
      if (!infoMap[schedule.process_id] ||
          (schedule.next_run_at && (!infoMap[schedule.process_id].next_run_at ||
           schedule.next_run_at < infoMap[schedule.process_id].next_run_at))) {
        infoMap[schedule.process_id] = schedule
      }
    }
    scheduleInfo.value = infoMap
  } catch (error) {
    // Silently fail - schedule info is optional
    console.warn('Failed to load schedule info:', error)
  }
}

// Methods
const showNotification = (message, type = 'success') => {
  notification.value = { message, type }
  setTimeout(() => {
    notification.value = null
  }, 3000)
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString()
}

const formatRelativeTime = (dateStr) => {
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
  return `${diffDays}d ago`
}

const formatNextRunTime = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = date - now
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMs < 0) return 'overdue'
  if (diffMins < 1) return 'now'
  if (diffMins < 60) return `in ${diffMins}m`
  if (diffHours < 24) return `in ${diffHours}h`
  if (diffDays < 7) return `in ${diffDays}d`
  return date.toLocaleDateString()
}

const handleExecute = async (process) => {
  actionInProgress.value = process.id
  try {
    await processesStore.executeProcess(process.id)
    showNotification(`Started execution of '${process.name}'`, 'success')
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to execute process', 'error')
  } finally {
    actionInProgress.value = null
  }
}

const handleDelete = (process) => {
  deleteTarget.value = process
}

const confirmDelete = async () => {
  if (!deleteTarget.value) return

  actionInProgress.value = deleteTarget.value.id
  try {
    await processesStore.deleteProcess(deleteTarget.value.id)
    showNotification(`Deleted '${deleteTarget.value.name}'`, 'success')
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to delete process', 'error')
  } finally {
    actionInProgress.value = null
    deleteTarget.value = null
  }
}
</script>
