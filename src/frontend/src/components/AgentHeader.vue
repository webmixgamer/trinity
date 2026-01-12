<template>
  <div class="bg-white dark:bg-gray-800 shadow dark:shadow-gray-900 rounded-lg p-4 mb-4">
    <!-- Top row: Name, status, and actions -->
    <div class="flex justify-between items-center">
      <div class="flex items-center space-x-3">
        <h1 class="text-xl font-bold text-gray-900 dark:text-white">{{ agent.name }}</h1>
        <span :class="[
          'px-2 py-0.5 text-xs font-medium rounded-full',
          agent.status === 'running' ? 'bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300'
        ]">
          {{ agent.status }}
        </span>
        <!-- Runtime badge (Claude/Gemini) -->
        <RuntimeBadge :runtime="agent.runtime" />
        <!-- System agent badge -->
        <span
          v-if="agent.is_system"
          class="px-2 py-0.5 text-xs font-semibold rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300"
          title="System Agent - Platform Orchestrator with full access"
        >
          SYSTEM
        </span>
        <span v-if="agent.is_shared" class="px-2 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded-full">
          Shared by {{ agent.owner }}
        </span>
        <span class="text-xs text-gray-400 dark:text-gray-500">{{ agent.type }}</span>
        <!-- Git repo link and commit hash -->
        <template v-if="gitStatus?.remote_url">
          <a
            :href="gitStatus.remote_url"
            target="_blank"
            rel="noopener noreferrer"
            class="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            title="Open GitHub repository"
          >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
          </a>
          <span
            v-if="gitStatus.last_commit?.short_sha"
            class="text-xs font-mono text-gray-400 dark:text-gray-500"
            :title="`Commit: ${gitStatus.last_commit.message}\nAuthor: ${gitStatus.last_commit.author}\nDate: ${gitStatus.last_commit.date}`"
          >{{ gitStatus.last_commit.short_sha }}</span>
        </template>
      </div>
      <div class="flex items-center space-x-2">
        <button
          v-if="agent.status === 'stopped'"
          @click="$emit('start')"
          :disabled="actionLoading"
          class="bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white text-sm font-medium py-1.5 px-3 rounded flex items-center"
        >
          <svg v-if="actionLoading" class="animate-spin -ml-1 mr-1.5 h-3 w-3 text-white" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ actionLoading ? 'Starting...' : 'Start' }}
        </button>
        <button
          v-else
          @click="$emit('stop')"
          :disabled="actionLoading"
          class="bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white text-sm font-medium py-1.5 px-3 rounded flex items-center"
        >
          <svg v-if="actionLoading" class="animate-spin -ml-1 mr-1.5 h-3 w-3 text-white" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ actionLoading ? 'Stopping...' : 'Stop' }}
        </button>
        <!-- Git Sync Controls (only for GitHub-native agents when running) -->
        <template v-if="hasGitSync && agent.status === 'running'">
          <div class="h-4 w-px bg-gray-300 dark:bg-gray-600 mx-1"></div>
          <!-- Pull Latest button -->
          <button
            @click="$emit('git-pull')"
            :disabled="gitPulling || gitSyncing"
            class="inline-flex items-center text-sm font-medium py-1.5 px-3 rounded transition-colors"
            :class="gitBehind > 0
              ? 'bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white'
              : 'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 disabled:bg-gray-100 dark:disabled:bg-gray-800 text-gray-600 dark:text-gray-300'"
            :title="gitBehind > 0 ? `Pull ${gitBehind} commit(s) from GitHub` : 'Already up to date'"
          >
            <svg v-if="gitPulling" class="animate-spin -ml-0.5 mr-1.5 h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <svg v-else class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {{ gitPulling ? 'Pulling...' : (gitBehind > 0 ? `Pull (${gitBehind})` : 'Pull') }}
          </button>
          <!-- Push button -->
          <button
            @click="$emit('git-push')"
            :disabled="gitSyncing || gitPulling"
            class="inline-flex items-center text-sm font-medium py-1.5 px-3 rounded transition-colors"
            :class="gitHasChanges
              ? 'bg-orange-600 hover:bg-orange-700 disabled:bg-orange-400 text-white'
              : 'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 disabled:bg-gray-100 dark:disabled:bg-gray-800 text-gray-600 dark:text-gray-300'"
            :title="gitHasChanges ? 'Push changes to GitHub' : 'No changes to push'"
          >
            <svg v-if="gitSyncing" class="animate-spin -ml-0.5 mr-1.5 h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <svg v-else class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            {{ gitSyncing ? 'Pushing...' : (gitHasChanges ? `Push (${gitChangesCount})` : 'Push') }}
          </button>
          <button
            @click="$emit('git-refresh')"
            :disabled="gitLoading"
            class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
            title="Refresh git status"
          >
            <svg :class="['w-4 h-4', gitLoading ? 'animate-spin' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </template>
        <!-- Git status indicator (when stopped but has git) -->
        <template v-else-if="hasGitSync && agent.status === 'stopped'">
          <div class="h-4 w-px bg-gray-300 dark:bg-gray-600 mx-1"></div>
          <span class="text-xs text-gray-400 dark:text-gray-500 flex items-center">
            <svg class="w-3.5 h-3.5 mr-1" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
            Git enabled
          </span>
        </template>
        <!-- Autonomy Mode Toggle (not for system agents) -->
        <template v-if="!agent.is_system && agent.can_share">
          <div class="h-4 w-px bg-gray-300 dark:bg-gray-600 mx-1"></div>
          <button
            @click="$emit('toggle-autonomy')"
            :disabled="autonomyLoading"
            :class="[
              'inline-flex items-center text-sm font-medium py-1.5 px-3 rounded transition-colors',
              agent.autonomy_enabled
                ? 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 hover:bg-amber-200 dark:hover:bg-amber-900/70'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
            ]"
            :title="agent.autonomy_enabled ? 'Autonomy Mode ON - Scheduled tasks are running' : 'Autonomy Mode OFF - Click to enable scheduled tasks'"
          >
            <svg v-if="autonomyLoading" class="animate-spin -ml-0.5 mr-1.5 h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <svg v-else class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {{ agent.autonomy_enabled ? 'AUTO' : 'Manual' }}
          </button>
        </template>
        <button
          v-if="agent.can_delete"
          @click="$emit('delete')"
          class="text-gray-400 dark:text-gray-500 hover:text-red-600 dark:hover:text-red-400 p-1.5 rounded"
          title="Delete agent"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Live Stats Row (only when running) -->
    <div v-if="agent.status === 'running'" class="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
      <div v-if="statsLoading && !agentStats" class="flex items-center space-x-2 text-xs text-gray-400 dark:text-gray-500">
        <div class="animate-spin h-3 w-3 border border-gray-300 dark:border-gray-600 border-t-gray-600 dark:border-t-gray-300 rounded-full"></div>
        <span>Loading stats...</span>
      </div>
      <div v-else-if="agentStats" class="flex items-center space-x-6 text-xs">
        <!-- CPU -->
        <div class="flex items-center space-x-2">
          <span class="text-gray-400 dark:text-gray-500 w-8">CPU</span>
          <SparklineChart
            :data="cpuHistory"
            color="#3b82f6"
            :y-max="100"
            :width="60"
            :height="20"
          />
          <span
            class="font-mono text-right min-w-[2.5rem]"
            :class="agentStats.cpu_percent > 80 ? 'text-red-500' : agentStats.cpu_percent > 50 ? 'text-yellow-500' : 'text-green-500'"
          >{{ agentStats.cpu_percent }}%</span>
          <span class="text-gray-400 dark:text-gray-500 font-mono">/ {{ resourceLimits.current_cpu || '2' }}</span>
        </div>
        <!-- Memory -->
        <div class="flex items-center space-x-2">
          <span class="text-gray-400 dark:text-gray-500 w-8">MEM</span>
          <SparklineChart
            :data="memoryHistory"
            color="#a855f7"
            :y-max="100"
            :width="60"
            :height="20"
          />
          <span
            class="font-mono text-right min-w-[4rem]"
            :class="agentStats.memory_percent > 80 ? 'text-red-500' : agentStats.memory_percent > 50 ? 'text-yellow-500' : 'text-green-500'"
          >{{ formatBytes(agentStats.memory_used_bytes) }}</span>
          <span class="text-gray-400 dark:text-gray-500 font-mono">/ {{ (resourceLimits.current_memory || '4g').toUpperCase() }}</span>
        </div>
        <!-- Network -->
        <div class="flex items-center space-x-1.5 text-gray-500 dark:text-gray-400">
          <span class="text-gray-400 dark:text-gray-500">NET</span>
          <span class="text-green-600 dark:text-green-400 font-mono min-w-[4.5rem]">↓{{ formatBytes(agentStats.network_rx_bytes) }}</span>
          <span class="text-blue-600 dark:text-blue-400 font-mono min-w-[4.5rem]">↑{{ formatBytes(agentStats.network_tx_bytes) }}</span>
        </div>
        <!-- Uptime -->
        <div class="flex items-center space-x-1.5 text-gray-500 dark:text-gray-400">
          <span class="text-gray-400 dark:text-gray-500">UP</span>
          <span class="font-mono min-w-[3.5rem]">{{ formatUptime(agentStats.uptime_seconds) }}</span>
        </div>
        <!-- Resource Config Button -->
        <button
          v-if="agent.can_share"
          @click="$emit('open-resource-modal')"
          class="ml-4 p-1 text-gray-400 dark:text-gray-500 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          title="Configure resources (Memory/CPU)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
      <div v-else class="text-xs text-gray-400 dark:text-gray-500">Stats unavailable</div>
    </div>

    <!-- Stopped state info -->
    <div v-else class="mt-2 flex items-center justify-between text-xs text-gray-400 dark:text-gray-500">
      <div class="flex items-center space-x-4">
        <span>Created {{ formatRelativeTime(agent.created) }}</span>
        <span class="text-gray-300 dark:text-gray-600">|</span>
        <span class="font-mono">{{ resourceLimits.current_cpu || '2' }} CPU</span>
        <span class="font-mono">{{ (resourceLimits.current_memory || '4g').toUpperCase() }} RAM</span>
      </div>
      <button
        v-if="agent.can_share"
        @click="$emit('open-resource-modal')"
        class="p-1 text-gray-400 dark:text-gray-500 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
        title="Configure resources (Memory/CPU)"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import RuntimeBadge from './RuntimeBadge.vue'
import SparklineChart from './SparklineChart.vue'
import { useFormatters } from '../composables'

const props = defineProps({
  agent: {
    type: Object,
    required: true
  },
  actionLoading: {
    type: Boolean,
    default: false
  },
  autonomyLoading: {
    type: Boolean,
    default: false
  },
  // Stats props
  agentStats: {
    type: Object,
    default: null
  },
  statsLoading: {
    type: Boolean,
    default: false
  },
  cpuHistory: {
    type: Array,
    default: () => []
  },
  memoryHistory: {
    type: Array,
    default: () => []
  },
  resourceLimits: {
    type: Object,
    default: () => ({})
  },
  // Git props
  gitStatus: {
    type: Object,
    default: null
  },
  hasGitSync: {
    type: Boolean,
    default: false
  },
  gitLoading: {
    type: Boolean,
    default: false
  },
  gitSyncing: {
    type: Boolean,
    default: false
  },
  gitPulling: {
    type: Boolean,
    default: false
  },
  gitHasChanges: {
    type: Boolean,
    default: false
  },
  gitChangesCount: {
    type: Number,
    default: 0
  },
  gitBehind: {
    type: Number,
    default: 0
  }
})

defineEmits([
  'start',
  'stop',
  'delete',
  'toggle-autonomy',
  'open-resource-modal',
  'git-pull',
  'git-push',
  'git-refresh'
])

const { formatBytes, formatUptime, formatRelativeTime } = useFormatters()
</script>
