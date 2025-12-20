<template>
  <div class="space-y-6">
    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mx-auto"></div>
      <p class="text-gray-500 dark:text-gray-400 mt-2">Loading git status...</p>
    </div>

    <!-- Git Not Enabled -->
    <div v-else-if="!gitStatus?.git_enabled" class="text-center py-8 text-gray-500 dark:text-gray-400">
      <svg class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
      <p class="mt-2">Git sync not enabled for this agent</p>
      <p class="text-sm text-gray-400 dark:text-gray-500 mt-1">Only GitHub-native agents support git sync</p>
    </div>

    <!-- Agent Not Running -->
    <div v-else-if="gitStatus?.agent_running === false" class="text-center py-8 text-gray-500 dark:text-gray-400">
      <svg class="mx-auto h-12 w-12 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <p class="mt-2">Agent must be running to view git status</p>
      <div v-if="gitStatus?.config" class="mt-4 text-left max-w-md mx-auto bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
        <p class="text-sm font-medium text-gray-700 dark:text-gray-300">Saved Configuration:</p>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Repo: {{ gitStatus.config.github_repo }}</p>
        <p class="text-sm text-gray-500 dark:text-gray-400">Branch: {{ gitStatus.config.working_branch }}</p>
        <p v-if="gitStatus.config.last_sync_at" class="text-sm text-gray-500 dark:text-gray-400">
          Last sync: {{ formatDate(gitStatus.config.last_sync_at) }}
        </p>
      </div>
    </div>

    <!-- Git Status Display -->
    <div v-else>
      <!-- Repository Info Header -->
      <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <svg class="h-6 w-6 text-gray-600 dark:text-gray-400" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
            <div>
              <a :href="gitStatus.remote_url" target="_blank" class="text-sm font-medium text-indigo-600 hover:text-indigo-800">
                {{ gitStatus.remote_url }}
              </a>
              <div class="flex items-center space-x-2 mt-1">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-300">
                  <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  {{ gitStatus.branch }}
                </span>
                <span v-if="gitStatus.ahead > 0" class="text-xs text-green-600">
                  {{ gitStatus.ahead }} ahead
                </span>
                <span v-if="gitStatus.behind > 0" class="text-xs text-orange-600">
                  {{ gitStatus.behind }} behind
                </span>
              </div>
            </div>
          </div>
          <div class="flex items-center space-x-2">
            <span
              :class="[
                'px-2 py-1 text-xs font-medium rounded-full',
                gitStatus.sync_status === 'up_to_date'
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
                  : 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300'
              ]"
            >
              {{ gitStatus.sync_status === 'up_to_date' ? 'Synced' : 'Changes pending' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Pending Changes -->
      <div v-if="gitStatus.changes && gitStatus.changes.length > 0">
        <h3 class="text-sm font-medium text-gray-900 dark:text-white mb-2">Pending Changes ({{ gitStatus.changes_count }})</h3>
        <div class="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <ul class="divide-y divide-gray-200 dark:divide-gray-700 max-h-48 overflow-y-auto">
            <li v-for="change in gitStatus.changes" :key="change.path" class="px-4 py-2 flex items-center space-x-3 text-sm">
              <span
                :class="[
                  'w-5 h-5 flex items-center justify-center rounded text-xs font-mono font-bold',
                  getChangeStatusClass(change.status)
                ]"
              >
                {{ change.status }}
              </span>
              <span class="font-mono text-gray-700 dark:text-gray-300 truncate">{{ change.path }}</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- Last Commit -->
      <div v-if="gitStatus.last_commit">
        <h3 class="text-sm font-medium text-gray-900 dark:text-white mb-2">Last Commit</h3>
        <div class="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div class="flex items-start space-x-3">
            <div class="flex-shrink-0">
              <div class="w-8 h-8 bg-gray-300 dark:bg-gray-600 rounded-full flex items-center justify-center">
                <span class="text-xs font-medium text-gray-600 dark:text-gray-300">
                  {{ (gitStatus.last_commit.author || '?')[0].toUpperCase() }}
                </span>
              </div>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 dark:text-white">{{ gitStatus.last_commit.message }}</p>
              <div class="flex items-center space-x-2 mt-1 text-xs text-gray-500 dark:text-gray-400">
                <code class="bg-gray-200 dark:bg-gray-700 px-1.5 py-0.5 rounded">{{ gitStatus.last_commit.short_sha }}</code>
                <span>by {{ gitStatus.last_commit.author }}</span>
                <span>&bull;</span>
                <span>{{ formatDate(gitStatus.last_commit.date) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent Commits -->
      <div v-if="gitLog && gitLog.commits && gitLog.commits.length > 1">
        <h3 class="text-sm font-medium text-gray-900 dark:text-white mb-2">Recent Commits</h3>
        <div class="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <ul class="divide-y divide-gray-200 dark:divide-gray-700 max-h-64 overflow-y-auto">
            <li v-for="commit in gitLog.commits.slice(1)" :key="commit.sha" class="px-4 py-3">
              <div class="flex items-start space-x-3">
                <code class="flex-shrink-0 bg-gray-200 dark:bg-gray-700 px-1.5 py-0.5 rounded text-xs">{{ commit.short_sha }}</code>
                <div class="flex-1 min-w-0">
                  <p class="text-sm text-gray-700 dark:text-gray-300 truncate">{{ commit.message }}</p>
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {{ commit.author }} &bull; {{ formatDate(commit.date) }}
                  </p>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>

      <!-- Database Config (if different from live) -->
      <div v-if="gitStatus.db_config" class="text-xs text-gray-500 dark:text-gray-400 border-t dark:border-gray-700 pt-4">
        <p>Last sync: {{ gitStatus.db_config.last_sync_at ? formatDate(gitStatus.db_config.last_sync_at) : 'Never' }}</p>
        <p v-if="gitStatus.db_config.last_commit_sha">
          Last synced commit: <code class="bg-gray-100 dark:bg-gray-700 px-1 rounded">{{ gitStatus.db_config.last_commit_sha.substring(0, 7) }}</code>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
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

const loading = ref(false)
const gitStatus = ref(null)
const gitLog = ref(null)

const loadGitStatus = async () => {
  loading.value = true
  try {
    gitStatus.value = await agentsStore.getGitStatus(props.agentName)
    // Also load git log if status shows git is enabled
    if (gitStatus.value?.git_enabled && gitStatus.value?.branch) {
      gitLog.value = await agentsStore.getGitLog(props.agentName, 10)
    }
  } catch (err) {
    console.error('Failed to load git status:', err)
    gitStatus.value = { git_enabled: false }
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return 'Unknown'
  const date = new Date(dateString)
  const now = new Date()
  const diffSeconds = Math.floor((now - date) / 1000)

  if (diffSeconds < 60) return 'just now'
  if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`
  if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`
  if (diffSeconds < 604800) return `${Math.floor(diffSeconds / 86400)}d ago`
  return date.toLocaleDateString()
}

const getChangeStatusClass = (status) => {
  switch (status) {
    case 'M': return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300'  // Modified
    case 'A': return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'   // Added
    case 'D': return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'       // Deleted
    case '?': return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300'     // Untracked
    case 'R': return 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300' // Renamed
    default: return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300'
  }
}

// Watch for agent status changes
watch(() => props.agentStatus, (newStatus) => {
  if (newStatus === 'running') {
    loadGitStatus()
  }
})

onMounted(() => {
  loadGitStatus()
})
</script>
