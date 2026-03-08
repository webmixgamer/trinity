<template>
  <div>
    <!-- Header with filter -->
    <div class="flex items-center gap-3 mb-6">
      <select
        v-model="statusFilter"
        @change="fetchAlerts"
        class="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200"
      >
        <option value="">All Alerts</option>
        <option value="active">Active</option>
        <option value="dismissed">Dismissed</option>
      </select>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-2 gap-4 mb-6">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div class="text-3xl font-bold text-red-600 dark:text-red-400">{{ alertsStore.activeCount }}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400">Active Alerts</div>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div class="text-3xl font-bold text-gray-900 dark:text-white">{{ alertsStore.alerts.length }}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400">Total Shown</div>
      </div>
    </div>

    <!-- Alerts List -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h2 class="text-lg font-medium text-gray-900 dark:text-white">Alert History</h2>
      </div>

      <div class="divide-y divide-gray-200 dark:divide-gray-700">
        <div
          v-for="alert in alertsStore.alerts"
          :key="alert.id"
          class="px-6 py-4"
          :class="{ 'bg-red-50 dark:bg-red-900/10': alert.status === 'active' }"
        >
          <div class="flex items-start justify-between">
            <div class="flex items-start gap-3">
              <!-- Severity Icon -->
              <div
                class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
                :class="alert.severity === 'critical' ? 'bg-red-100 dark:bg-red-900/30' : 'bg-yellow-100 dark:bg-yellow-900/30'"
              >
                <ExclamationTriangleIcon
                  class="w-5 h-5"
                  :class="alert.severity === 'critical' ? 'text-red-600 dark:text-red-400' : 'text-yellow-600 dark:text-yellow-400'"
                />
              </div>

              <div>
                <div class="flex items-center gap-2">
                  <span class="font-medium text-gray-900 dark:text-white">{{ alert.process_name }}</span>
                  <span
                    class="px-2 py-0.5 text-xs font-medium rounded capitalize"
                    :class="getThresholdTypeBadge(alert.threshold_type)"
                  >
                    {{ formatThresholdType(alert.threshold_type) }}
                  </span>
                </div>
                <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">{{ alert.message }}</p>
                <div class="flex items-center gap-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
                  <span>Threshold: ${{ alert.threshold_amount.toFixed(2) }}</span>
                  <span>Actual: ${{ alert.actual_amount.toFixed(2) }}</span>
                  <span>{{ formatRelativeTime(alert.created_at) }}</span>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <span
                class="px-2 py-1 text-xs font-medium rounded capitalize"
                :class="alert.status === 'active' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'"
              >
                {{ alert.status }}
              </span>

              <button
                v-if="alert.status === 'active'"
                @click="dismissAlert(alert.id)"
                class="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-600"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>

        <div v-if="alertsStore.alerts.length === 0" class="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
          <BellSlashIcon class="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
          <p class="text-lg font-medium">No alerts</p>
          <p class="text-sm mt-1">Cost alerts will appear here when thresholds are exceeded</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAlertsStore } from '../../stores/alerts'
import {
  ExclamationTriangleIcon,
  BellSlashIcon,
} from '@heroicons/vue/24/outline'

const alertsStore = useAlertsStore()

// State
const loading = ref(false)
const statusFilter = ref('')

// Lifecycle
onMounted(() => {
  fetchAlerts()
})

// Methods
async function fetchAlerts() {
  loading.value = true
  try {
    await alertsStore.fetchAlerts({
      status: statusFilter.value || undefined,
    })
  } finally {
    loading.value = false
  }
}

async function dismissAlert(alertId) {
  try {
    await alertsStore.dismissAlert(alertId)
  } catch (err) {
    console.error('Failed to dismiss alert:', err)
  }
}

function getThresholdTypeBadge(type) {
  const badges = {
    per_execution: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
    daily: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
    weekly: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300',
  }
  return badges[type] || 'bg-gray-100 text-gray-700'
}

function formatThresholdType(type) {
  const labels = {
    per_execution: 'Per Execution',
    daily: 'Daily',
    weekly: 'Weekly',
  }
  return labels[type] || type
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
  return `${diffDays}d ago`
}
</script>
