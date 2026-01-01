<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />

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
          <!-- Agent Header - Compact -->
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
              </div>
              <div class="flex items-center space-x-2">
                <button
                  v-if="agent.status === 'stopped'"
                  @click="startAgent"
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
                  @click="stopAgent"
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
                    @click="pullFromGithub()"
                    :disabled="gitPulling || gitSyncing"
                    class="inline-flex items-center text-sm font-medium py-1.5 px-3 rounded transition-colors bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white"
                    title="Pull latest changes from GitHub"
                  >
                    <svg v-if="gitPulling" class="animate-spin -ml-0.5 mr-1.5 h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <svg v-else class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    {{ gitPulling ? 'Pulling...' : 'Pull' }}
                  </button>
                  <!-- Sync (Push) button -->
                  <button
                    @click="syncToGithub()"
                    :disabled="gitSyncing || gitPulling"
                    class="inline-flex items-center text-sm font-medium py-1.5 px-3 rounded transition-colors"
                    :class="gitHasChanges
                      ? 'bg-orange-600 hover:bg-orange-700 disabled:bg-orange-400 text-white'
                      : 'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 disabled:bg-gray-100 dark:disabled:bg-gray-800 text-gray-600 dark:text-gray-300'"
                    :title="gitHasChanges ? 'Push changes to GitHub' : 'No changes to sync'"
                  >
                    <svg v-if="gitSyncing" class="animate-spin -ml-0.5 mr-1.5 h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <svg v-else class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                    {{ gitSyncing ? 'Syncing...' : (gitHasChanges ? `Sync (${gitChangesCount})` : 'Synced') }}
                  </button>
                  <button
                    @click="refreshGitStatus"
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
                    @click="toggleAutonomy"
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
                  @click="deleteAgent"
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
                  <div class="w-20 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all duration-500 animate-progress-pulse"
                      :class="agentStats.cpu_percent > 80 ? 'bg-red-500' : agentStats.cpu_percent > 50 ? 'bg-yellow-500' : 'bg-green-500'"
                      :style="{ width: `${Math.min(100, agentStats.cpu_percent)}%` }"
                    ></div>
                  </div>
                  <span class="text-gray-600 dark:text-gray-400 font-mono w-12 text-right">{{ agentStats.cpu_percent }}%</span>
                </div>
                <!-- Memory -->
                <div class="flex items-center space-x-2">
                  <span class="text-gray-400 dark:text-gray-500 w-8">MEM</span>
                  <div class="w-20 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all duration-500 animate-progress-pulse"
                      :class="agentStats.memory_percent > 80 ? 'bg-red-500' : agentStats.memory_percent > 50 ? 'bg-yellow-500' : 'bg-green-500'"
                      :style="{ width: `${Math.min(100, agentStats.memory_percent)}%` }"
                    ></div>
                  </div>
                  <span class="text-gray-600 dark:text-gray-400 font-mono w-20 text-right">{{ formatBytes(agentStats.memory_used_bytes) }}</span>
                </div>
                <!-- Network -->
                <div class="flex items-center space-x-1.5 text-gray-500 dark:text-gray-400">
                  <span class="text-gray-400 dark:text-gray-500">NET</span>
                  <span class="text-green-600 dark:text-green-400">↓{{ formatBytes(agentStats.network_rx_bytes) }}</span>
                  <span class="text-blue-600 dark:text-blue-400">↑{{ formatBytes(agentStats.network_tx_bytes) }}</span>
                </div>
                <!-- Uptime -->
                <div class="flex items-center space-x-1.5 text-gray-500 dark:text-gray-400">
                  <span class="text-gray-400 dark:text-gray-500">UP</span>
                  <span class="font-mono">{{ formatUptime(agentStats.uptime_seconds) }}</span>
                </div>
              </div>
              <div v-else class="text-xs text-gray-400 dark:text-gray-500">Stats unavailable</div>
            </div>

            <!-- Stopped state info -->
            <div v-else class="mt-2 text-xs text-gray-400 dark:text-gray-500">
              Created {{ formatRelativeTime(agent.created) }}
            </div>
          </div>

          <!-- Tabs -->
          <div class="bg-white dark:bg-gray-800 shadow dark:shadow-gray-900 rounded-lg">
            <div class="border-b border-gray-200 dark:border-gray-700 overflow-x-auto overflow-y-hidden">
              <nav class="-mb-px flex whitespace-nowrap">
                <button
                  @click="activeTab = 'info'"
                  :class="[
                    'px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                    activeTab === 'info'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Info
                </button>
                <button
                  @click="activeTab = 'tasks'"
                  :class="[
                    'px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                    activeTab === 'tasks'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Tasks
                </button>
                <button
                  @click="activeTab = 'metrics'"
                  :class="[
                    'px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                    activeTab === 'metrics'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                  title="Agent-specific KPIs and stats"
                >
                  Metrics
                </button>
                <button
                  @click="activeTab = 'terminal'"
                  :class="[
                    'px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                    activeTab === 'terminal'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Terminal
                </button>
                <button
                  @click="activeTab = 'logs'"
                  :class="[
                    'px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                    activeTab === 'logs'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Logs
                </button>
                <button
                  @click="activeTab = 'credentials'"
                  :class="[
                    'inline-flex items-center px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                    activeTab === 'credentials'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Credentials
                  <span v-if="assignedCredentials.length > 0" class="ml-1.5 px-1.5 py-0.5 text-[10px] font-semibold bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300 rounded-full leading-none">
                    {{ assignedCredentials.length }}
                  </span>
                </button>
                <button
                  v-if="agent.can_share"
                  @click="activeTab = 'sharing'"
                  :class="[
                    'inline-flex items-center px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                    activeTab === 'sharing'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Sharing
                </button>
                <button
                  v-if="agent.can_share"
                  @click="activeTab = 'permissions'"
                  :class="[
                    'inline-flex items-center px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                    activeTab === 'permissions'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Permissions
                </button>
                <button
                  @click="activeTab = 'schedules'"
                  :class="[
                    'px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                    activeTab === 'schedules'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Schedules
                </button>
                <button
                  v-if="hasGitSync"
                  @click="activeTab = 'git'"
                  :class="[
                    'px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                    activeTab === 'git'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Git
                </button>
                <button
                  @click="activeTab = 'files'"
                  :class="[
                    'px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                    activeTab === 'files'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Files
                </button>
                <button
                  v-if="agent.can_share"
                  @click="activeTab = 'folders'"
                  :class="[
                    'px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                    activeTab === 'folders'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                  title="Shared folders for file-based collaboration"
                >
                  Folders
                </button>
                <button
                  v-if="agent.can_share"
                  @click="activeTab = 'public-links'"
                  :class="[
                    'px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                    activeTab === 'public-links'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                  title="Generate public shareable links"
                >
                  Public Links
                </button>
              </nav>
            </div>

            <!-- Info Tab Content -->
            <div v-if="activeTab === 'info'" class="p-6">
              <InfoPanel :agent-name="agent.name" :agent-status="agent.status" @use-case-click="handleUseCaseClick" />
            </div>

            <!-- Metrics Tab Content -->
            <div v-if="activeTab === 'metrics'" class="p-6">
              <MetricsPanel :agent-name="agent.name" :agent-status="agent.status" />
            </div>

            <!-- Terminal Tab Content -->
            <!-- Using v-show instead of v-if to keep terminal mounted and WebSocket connected when switching tabs -->
            <div
              v-show="activeTab === 'terminal'"
              :class="[
                'transition-all duration-300',
                isTerminalFullscreen
                  ? 'fixed inset-0 z-50 bg-gray-900'
                  : ''
              ]"
              @keydown="handleTerminalKeydown"
            >
              <!--
                NOTE: Model Selector Bar was removed - model selection now happens in CLI.
                To reintroduce, uncomment and restore the model selector UI:
                - availableModels computed property provides model options
                - currentModel ref tracks selected model
                - changeModel() handles model switching
                - See useAgentSettings.js composable for implementation
              -->

              <!-- Terminal Panel -->
              <div
                :class="[
                  'bg-gray-900 overflow-hidden flex flex-col',
                  isTerminalFullscreen ? 'h-full' : 'rounded-b-lg'
                ]"
                :style="isTerminalFullscreen ? {} : { height: '600px' }"
              >
                <!-- Fullscreen Header (only in fullscreen mode) -->
                <div
                  v-if="isTerminalFullscreen"
                  class="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700"
                >
                  <span class="text-sm font-medium text-gray-300">{{ agent.name }} - Terminal</span>
                  <button
                    @click="toggleTerminalFullscreen"
                    class="p-1.5 text-gray-400 hover:text-gray-200 rounded transition-colors"
                    title="Exit Fullscreen (Esc)"
                  >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
                    </svg>
                  </button>
                </div>

                <!-- Terminal Content -->
                <div class="flex-1 min-h-0">
                  <AgentTerminal
                    v-if="agent.status === 'running'"
                    ref="terminalRef"
                    :agent-name="agent.name"
                    :runtime="agent.runtime || 'claude-code'"
                    :model="currentModel"
                    :auto-connect="true"
                    :show-fullscreen-toggle="!isTerminalFullscreen"
                    :is-fullscreen="isTerminalFullscreen"
                    @connected="onTerminalConnected"
                    @disconnected="onTerminalDisconnected"
                    @error="onTerminalError"
                    @toggle-fullscreen="toggleTerminalFullscreen"
                  />
                  <div
                    v-else
                    class="flex items-center justify-center h-full text-gray-400"
                  >
                    <div class="text-center max-w-md">
                      <svg class="w-12 h-12 mx-auto mb-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      <p class="text-lg font-medium mb-2">Agent is not running</p>
                      <p class="text-sm text-gray-500 mb-4">Start the agent to access the terminal</p>

                      <!-- API Key Setting -->
                      <div v-if="agent.can_share" class="mb-4 p-4 bg-gray-800 rounded-lg text-left">
                        <div class="flex items-center justify-between mb-2">
                          <span class="text-sm font-medium text-gray-300">Authentication</span>
                          <span v-if="apiKeySetting.restart_required" class="text-xs text-yellow-400">Restart required</span>
                        </div>
                        <div class="space-y-2">
                          <label class="flex items-center space-x-3 cursor-pointer">
                            <input
                              type="radio"
                              :checked="apiKeySetting.use_platform_api_key"
                              @change="updateApiKeySetting(true)"
                              :disabled="apiKeySettingLoading"
                              class="text-indigo-500 focus:ring-indigo-500"
                            />
                            <div>
                              <span class="text-sm text-gray-200">Use Platform API Key</span>
                              <p class="text-xs text-gray-500">Claude uses Trinity's configured Anthropic API key</p>
                            </div>
                          </label>
                          <label class="flex items-center space-x-3 cursor-pointer">
                            <input
                              type="radio"
                              :checked="!apiKeySetting.use_platform_api_key"
                              @change="updateApiKeySetting(false)"
                              :disabled="apiKeySettingLoading"
                              class="text-indigo-500 focus:ring-indigo-500"
                            />
                            <div>
                              <span class="text-sm text-gray-200">Authenticate in Terminal</span>
                              <p class="text-xs text-gray-500">Run "claude login" after starting to use your own subscription</p>
                            </div>
                          </label>
                        </div>
                      </div>

                      <button
                        @click="startAgent"
                        :disabled="actionLoading"
                        class="bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white text-sm font-medium py-2 px-4 rounded-lg"
                      >
                        {{ actionLoading ? 'Starting...' : 'Start Agent' }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Logs Tab Content -->
            <div v-if="activeTab === 'logs'" class="p-6">
              <div
                ref="logsContainer"
                @scroll="handleLogsScroll"
                class="bg-gray-900 text-gray-300 p-4 rounded-lg h-96 overflow-auto mb-4"
              >
                <pre class="text-sm font-mono whitespace-pre-wrap">{{ logs || 'No logs available' }}</pre>
              </div>
              <div class="flex justify-between items-center">
                <div class="flex items-center space-x-4">
                  <button
                    @click="refreshLogs"
                    class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
                  >
                    Refresh Logs
                  </button>
                  <label class="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                    <input type="checkbox" v-model="autoRefreshLogs" class="rounded border-gray-300 dark:border-gray-600 dark:bg-gray-700" />
                    <span>Auto-refresh (10s)</span>
                  </label>
                </div>
                <div class="flex items-center space-x-2">
                  <label class="text-sm text-gray-600 dark:text-gray-400">Lines:</label>
                  <select v-model="logLines" @change="refreshLogs" class="border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm bg-white dark:bg-gray-800 dark:text-gray-200">
                    <option value="50">50</option>
                    <option value="100">100</option>
                    <option value="200">200</option>
                    <option value="500">500</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- Credentials Tab Content -->
            <div v-if="activeTab === 'credentials'" class="p-6 space-y-6">

              <!-- Loading State -->
              <div v-if="assignmentsLoading" class="text-center py-8">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mx-auto"></div>
                <p class="text-gray-500 dark:text-gray-400 mt-2">Loading credentials...</p>
              </div>

              <template v-else>
                <!-- Filter Input -->
                <div class="mb-4">
                  <input
                    v-model="credentialFilter"
                    type="text"
                    placeholder="Filter credentials..."
                    class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <!-- Assigned Credentials Section -->
                <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white">
                      Assigned Credentials
                      <span class="ml-2 text-sm font-normal text-gray-500">({{ filteredAssignedCredentials.length }})</span>
                    </h3>
                    <button
                      v-if="hasChanges && agent.status === 'running'"
                      @click="applyToAgent"
                      :disabled="applying"
                      class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <svg v-if="applying" class="animate-spin -ml-0.5 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      {{ applying ? 'Applying...' : 'Apply to Agent' }}
                    </button>
                  </div>

                  <div v-if="filteredAssignedCredentials.length === 0" class="p-6 text-center text-gray-500 dark:text-gray-400">
                    <svg class="w-12 h-12 mx-auto mb-3 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                    </svg>
                    <p v-if="credentialFilter">No matching credentials.</p>
                    <p v-else>No credentials assigned to this agent.</p>
                    <p v-if="!credentialFilter" class="text-sm mt-1">Add credentials from the list below.</p>
                  </div>

                  <div v-else class="divide-y divide-gray-200 dark:divide-gray-700 max-h-64 overflow-y-auto">
                    <div
                      v-for="cred in filteredAssignedCredentials"
                      :key="cred.id"
                      class="px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50"
                    >
                      <div class="flex items-center space-x-3">
                        <div class="flex-shrink-0">
                          <span v-if="cred.type === 'file'" class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-purple-100 dark:bg-purple-900/50 text-purple-600 dark:text-purple-400">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                          </span>
                          <span v-else class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-green-100 dark:bg-green-900/50 text-green-600 dark:text-green-400">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                            </svg>
                          </span>
                        </div>
                        <div>
                          <p class="font-medium text-gray-900 dark:text-white">{{ cred.name }}</p>
                          <p class="text-sm text-gray-500 dark:text-gray-400">
                            {{ cred.service }} &middot; {{ cred.type }}
                            <span v-if="cred.file_path" class="ml-1 font-mono text-xs bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">
                              &rarr; {{ cred.file_path }}
                            </span>
                          </p>
                        </div>
                      </div>
                      <button
                        @click="unassignCredential(cred.id)"
                        class="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 text-sm font-medium"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                </div>

                <!-- Available Credentials Section -->
                <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white">
                      Available Credentials
                      <span class="ml-2 text-sm font-normal text-gray-500">({{ filteredAvailableCredentials.length }})</span>
                    </h3>
                  </div>

                  <div v-if="filteredAvailableCredentials.length === 0" class="p-6 text-center text-gray-500 dark:text-gray-400">
                    <p v-if="credentialFilter">No matching credentials.</p>
                    <p v-else>All your credentials are assigned.</p>
                    <router-link v-if="!credentialFilter" to="/credentials" class="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 text-sm mt-1 inline-block">
                      Create more credentials &rarr;
                    </router-link>
                  </div>

                  <div v-else class="divide-y divide-gray-200 dark:divide-gray-700 max-h-64 overflow-y-auto">
                    <div
                      v-for="cred in filteredAvailableCredentials"
                      :key="cred.id"
                      class="px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50"
                    >
                      <div class="flex items-center space-x-3">
                        <div class="flex-shrink-0">
                          <span v-if="cred.type === 'file'" class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                          </span>
                          <span v-else class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                            </svg>
                          </span>
                        </div>
                        <div>
                          <p class="font-medium text-gray-900 dark:text-white">{{ cred.name }}</p>
                          <p class="text-sm text-gray-500 dark:text-gray-400">
                            {{ cred.service }} &middot; {{ cred.type }}
                            <span v-if="cred.file_path" class="ml-1 font-mono text-xs bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">
                              &rarr; {{ cred.file_path }}
                            </span>
                          </p>
                        </div>
                      </div>
                      <button
                        @click="assignCredential(cred.id)"
                        class="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 text-sm font-medium"
                      >
                        + Add
                      </button>
                    </div>
                  </div>
                </div>

                <!-- Quick Add Section -->
                <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white">Quick Add</h3>
                    <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      Paste KEY=VALUE pairs to create, assign, and apply credentials in one step
                    </p>
                  </div>

                  <div class="p-4 space-y-4">
                    <div class="relative">
                      <textarea
                        v-model="quickAddText"
                        :disabled="agent.status !== 'running' || quickAddLoading"
                        rows="5"
                        placeholder="OPENAI_API_KEY=sk-...&#10;ANTHROPIC_API_KEY=sk-ant-...&#10;&#10;# Lines starting with # are ignored"
                        class="w-full font-mono text-sm border border-gray-300 dark:border-gray-600 rounded-lg p-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:cursor-not-allowed"
                      ></textarea>
                      <span
                        v-if="agent.status !== 'running'"
                        class="absolute top-2 right-2 px-2 py-1 text-xs bg-yellow-100 dark:bg-yellow-900/50 text-yellow-700 dark:text-yellow-300 rounded"
                      >
                        Agent must be running
                      </span>
                    </div>

                    <div class="flex items-center justify-between">
                      <span class="text-sm text-gray-500 dark:text-gray-400">
                        {{ quickAddText ? countCredentials(quickAddText) : 0 }} credential(s) detected
                      </span>
                      <button
                        @click="quickAddCredentials"
                        :disabled="agent.status !== 'running' || quickAddLoading || !quickAddText.trim()"
                        class="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                      >
                        <svg v-if="quickAddLoading" class="animate-spin -ml-0.5 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        {{ quickAddLoading ? 'Adding...' : 'Add & Apply' }}
                      </button>
                    </div>

                    <!-- Quick add result -->
                    <div
                      v-if="quickAddResult"
                      :class="[
                        'p-4 rounded-lg',
                        quickAddResult.success ? 'bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800' : 'bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800'
                      ]"
                    >
                      <div class="flex items-start">
                        <svg v-if="quickAddResult.success" class="w-5 h-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                        </svg>
                        <svg v-else class="w-5 h-5 text-red-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                        </svg>
                        <div>
                          <p :class="quickAddResult.success ? 'text-green-800 dark:text-green-300' : 'text-red-800 dark:text-red-300'" class="font-medium">
                            {{ quickAddResult.message }}
                          </p>
                          <p v-if="quickAddResult.credentials && quickAddResult.credentials.length" class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                            Added: {{ quickAddResult.credentials.join(', ') }}
                          </p>
                          <p v-if="quickAddResult.note" class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            {{ quickAddResult.note }}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>

            </div>

            <!-- Sharing Tab Content -->
            <div v-if="activeTab === 'sharing' && agent.can_share" class="p-6">
              <div class="mb-6">
                <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Share Agent</h3>
                <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
                  Share this agent with other team members by entering their email address.
                </p>

                <!-- Share Form -->
                <form @submit.prevent="shareWithUser" class="flex items-center space-x-3">
                  <input
                    v-model="shareEmail"
                    type="email"
                    placeholder="user@ability.ai"
                    :disabled="shareLoading"
                    class="flex-1 max-w-md px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-100 dark:disabled:bg-gray-900"
                  />
                  <button
                    type="submit"
                    :disabled="shareLoading || !shareEmail.trim()"
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-800 disabled:bg-gray-400 dark:disabled:bg-gray-600 disabled:cursor-not-allowed"
                  >
                    <svg v-if="shareLoading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {{ shareLoading ? 'Sharing...' : 'Share' }}
                  </button>
                </form>

                <!-- Share Error/Success Message -->
                <div v-if="shareMessage" :class="[
                  'mt-3 p-3 rounded-lg text-sm',
                  shareMessage.type === 'success' ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300' : 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                ]">
                  {{ shareMessage.text }}
                </div>
              </div>

              <!-- Shared Users List -->
              <div>
                <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Shared With</h3>

                <div v-if="!agent.shares || agent.shares.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400">
                  <svg class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  <p class="mt-2">Not shared with anyone</p>
                </div>

                <ul v-else class="divide-y divide-gray-200 dark:divide-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg">
                  <li v-for="share in agent.shares" :key="share.id" class="px-4 py-3 flex items-center justify-between">
                    <div class="flex items-center space-x-3">
                      <div class="flex-shrink-0 h-8 w-8 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
                        <span class="text-sm font-medium text-gray-600 dark:text-gray-300">
                          {{ (share.shared_with_name || share.shared_with_email || '?')[0].toUpperCase() }}
                        </span>
                      </div>
                      <div>
                        <p class="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {{ share.shared_with_name || share.shared_with_email }}
                        </p>
                        <p v-if="share.shared_with_name" class="text-xs text-gray-500 dark:text-gray-400">
                          {{ share.shared_with_email }}
                        </p>
                      </div>
                    </div>
                    <button
                      @click="removeShare(share.shared_with_email)"
                      :disabled="unshareLoading === share.shared_with_email"
                      class="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 text-sm font-medium disabled:opacity-50"
                    >
                      <span v-if="unshareLoading === share.shared_with_email">Removing...</span>
                      <span v-else>Remove</span>
                    </button>
                  </li>
                </ul>
              </div>
            </div>

            <!-- Permissions Tab Content (Phase 9.10) -->
            <div v-if="activeTab === 'permissions' && agent.can_share" class="p-6">
              <div class="mb-6">
                <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Agent Collaboration Permissions</h3>
                <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
                  Control which other agents this agent can communicate with via the Trinity MCP tools.
                </p>

                <!-- Loading State -->
                <div v-if="permissionsLoading" class="text-center py-4">
                  <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mx-auto"></div>
                  <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">Loading permissions...</p>
                </div>

                <!-- Permissions List -->
                <div v-else-if="availableAgents.length > 0">
                  <!-- Bulk Actions -->
                  <div class="flex items-center space-x-3 mb-4">
                    <button
                      @click="allowAllAgents"
                      :disabled="permissionsSaving"
                      class="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 font-medium disabled:opacity-50"
                    >
                      Allow All
                    </button>
                    <span class="text-gray-300 dark:text-gray-600">|</span>
                    <button
                      @click="allowNoAgents"
                      :disabled="permissionsSaving"
                      class="text-sm text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 font-medium disabled:opacity-50"
                    >
                      Allow None
                    </button>
                    <span v-if="permissionsDirty" class="text-amber-600 dark:text-amber-400 text-xs ml-4">
                      Unsaved changes
                    </span>
                  </div>

                  <!-- Agent Checkboxes -->
                  <ul class="divide-y divide-gray-200 dark:divide-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg mb-4">
                    <li v-for="targetAgent in availableAgents" :key="targetAgent.name" class="px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700">
                      <label :for="'perm-' + targetAgent.name" class="flex items-center space-x-3 cursor-pointer flex-1">
                        <input
                          :id="'perm-' + targetAgent.name"
                          type="checkbox"
                          v-model="targetAgent.permitted"
                          @change="markDirty"
                          :disabled="permissionsSaving"
                          class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 dark:border-gray-600 rounded dark:bg-gray-700"
                        />
                        <div class="flex-1">
                          <span class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ targetAgent.name }}</span>
                          <span v-if="targetAgent.type" class="ml-2 text-xs text-gray-500 dark:text-gray-400">[{{ targetAgent.type }}]</span>
                        </div>
                        <span :class="[
                          'px-2 py-0.5 text-xs font-medium rounded-full',
                          targetAgent.status === 'running' ? 'bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                        ]">
                          {{ targetAgent.status }}
                        </span>
                      </label>
                    </li>
                  </ul>

                  <!-- Save Button -->
                  <div class="flex items-center space-x-3">
                    <button
                      @click="savePermissions"
                      :disabled="permissionsSaving || !permissionsDirty"
                      class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-800 disabled:bg-gray-400 dark:disabled:bg-gray-600 disabled:cursor-not-allowed"
                    >
                      <svg v-if="permissionsSaving" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      {{ permissionsSaving ? 'Saving...' : 'Save Permissions' }}
                    </button>

                    <!-- Status Message -->
                    <div v-if="permissionsMessage" :class="[
                      'text-sm',
                      permissionsMessage.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                    ]">
                      {{ permissionsMessage.text }}
                    </div>
                  </div>
                </div>

                <!-- No Other Agents -->
                <div v-else class="text-center py-8 text-gray-500 dark:text-gray-400">
                  <svg class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  <p class="mt-2">No other agents available</p>
                  <p class="text-xs">Create more agents to enable collaboration permissions.</p>
                </div>
              </div>
            </div>

            <!-- Schedules Tab Content -->
            <div v-if="activeTab === 'schedules'" class="p-6">
              <SchedulesPanel :agent-name="agent.name" />
            </div>

            <!-- Tasks Tab Content -->
            <div v-if="activeTab === 'tasks'" class="p-6">
              <TasksPanel v-if="agent" :agent-name="agent.name" :agent-status="agent.status" />
              <div v-else class="text-center py-8">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mx-auto"></div>
                <p class="text-gray-500 dark:text-gray-400 mt-2">Loading agent...</p>
              </div>
            </div>

            <!-- Git Tab Content -->
            <div v-if="activeTab === 'git'" class="p-6">
              <GitPanel v-if="agent" :agent-name="agent.name" :agent-status="agent.status" />
              <div v-else class="text-center py-8">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mx-auto"></div>
                <p class="text-gray-500 dark:text-gray-400 mt-2">Loading agent...</p>
              </div>
            </div>

            <!-- Files Tab Content -->
            <div v-if="activeTab === 'files'" class="p-6">
              <div v-if="agent.status !== 'running'" class="text-center py-12">
                <svg class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p class="mt-4 text-gray-500 dark:text-gray-400">Agent must be running to browse files</p>
              </div>
              <div v-else>
                <!-- Search Box -->
                <div class="mb-4">
                  <input
                    v-model="fileSearchQuery"
                    type="text"
                    placeholder="Search files by name..."
                    class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <!-- File Tree -->
                <div v-if="filesLoading" class="text-center py-8">
                  <svg class="animate-spin h-8 w-8 mx-auto text-indigo-600" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <p class="mt-2 text-gray-500 dark:text-gray-400">Loading files...</p>
                </div>

                <div v-else-if="filesError" class="text-center py-8">
                  <p class="text-red-600 dark:text-red-400">{{ filesError }}</p>
                  <button @click="loadFiles" class="mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
                    Retry
                  </button>
                </div>

                <div v-else-if="fileTree.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400">
                  <p>No files found in workspace</p>
                </div>

                <div v-else>
                  <div class="flex items-center justify-between mb-4 text-sm text-gray-600 dark:text-gray-400">
                    <span>{{ totalFileCount }} file(s)</span>
                    <button @click="loadFiles" class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300">
                      <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      Refresh
                    </button>
                  </div>

                  <!-- Recursive File Tree Component -->
                  <div class="space-y-1">
                    <FileTreeNode
                      v-for="item in filteredFileTree"
                      :key="item.path"
                      :item="item"
                      :depth="0"
                      :search-query="fileSearchQuery"
                      :expanded-folders="expandedFolders"
                      @toggle-folder="toggleFolder"
                      @download="downloadFile"
                    />
                  </div>
                </div>
              </div>
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
import { ref, computed, onMounted, onUnmounted, onActivated, onDeactivated, watch, nextTick, defineComponent, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAgentsStore } from '../stores/agents'
import NavBar from '../components/NavBar.vue'

// Component name for KeepAlive matching
defineOptions({
  name: 'AgentDetail'
})
import ConfirmDialog from '../components/ConfirmDialog.vue'
import SchedulesPanel from '../components/SchedulesPanel.vue'
import TasksPanel from '../components/TasksPanel.vue'
import GitPanel from '../components/GitPanel.vue'
import InfoPanel from '../components/InfoPanel.vue'
import MetricsPanel from '../components/MetricsPanel.vue'
import FoldersPanel from '../components/FoldersPanel.vue'
import PublicLinksPanel from '../components/PublicLinksPanel.vue'
import AgentTerminal from '../components/AgentTerminal.vue'
import RuntimeBadge from '../components/RuntimeBadge.vue'
import GitConflictModal from '../components/GitConflictModal.vue'

// Import composables
import { useNotification, useFormatters } from '../composables'
import { useAgentLifecycle } from '../composables/useAgentLifecycle'
import { useAgentStats } from '../composables/useAgentStats'
import { useAgentLogs } from '../composables/useAgentLogs'
import { useAgentTerminal } from '../composables/useAgentTerminal'
import { useAgentCredentials } from '../composables/useAgentCredentials'
import { useAgentSharing } from '../composables/useAgentSharing'
import { useAgentPermissions } from '../composables/useAgentPermissions'
import { useGitSync } from '../composables/useGitSync'
import { useFileBrowser } from '../composables/useFileBrowser'
import { useAgentSettings } from '../composables/useAgentSettings'
import { useSessionActivity } from '../composables/useSessionActivity'

// Helper function for file sizes (used by FileTreeNode)
const formatFileSizeHelper = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

// NOTE: formatTokens helper function was removed from here.
// For token formatting, use this pattern: tokens < 1000 ? tokens : (tokens/1000).toFixed(1) + 'K'
// See useSessionActivity.js for full documentation on cost/context tracking data.

// File Tree Node Component (Recursive)
const FileTreeNode = defineComponent({
  name: 'FileTreeNode',
  props: {
    item: Object,
    depth: Number,
    searchQuery: String,
    expandedFolders: Set
  },
  emits: ['toggle-folder', 'download'],
  setup(props, { emit }) {
    const isExpanded = () => props.expandedFolders.has(props.item.path)
    const indent = props.depth * 20

    const toggleFolder = () => {
      emit('toggle-folder', props.item.path)
    }

    const downloadFile = () => {
      emit('download', props.item.path, props.item.name)
    }

    return () => {
      if (props.item.type === 'directory') {
        return h('div', [
          // Folder row
          h('div', {
            class: 'flex items-center py-1.5 px-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded cursor-pointer group',
            style: { paddingLeft: `${indent}px` },
            onClick: toggleFolder
          }, [
            // Expand/collapse icon
            h('svg', {
              class: `w-4 h-4 mr-1 text-gray-500 dark:text-gray-400 transition-transform ${isExpanded() ? 'rotate-90' : ''}`,
              fill: 'currentColor',
              viewBox: '0 0 20 20'
            }, [
              h('path', {
                'fill-rule': 'evenodd',
                d: 'M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z',
                'clip-rule': 'evenodd'
              })
            ]),
            // Folder icon
            h('svg', {
              class: `w-5 h-5 mr-2 ${isExpanded() ? 'text-indigo-500 dark:text-indigo-400' : 'text-gray-400 dark:text-gray-500'}`,
              fill: 'currentColor',
              viewBox: '0 0 20 20'
            }, [
              h('path', {
                d: 'M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z'
              })
            ]),
            // Folder name
            h('span', {
              class: 'font-medium text-gray-700 dark:text-gray-200 flex-1'
            }, props.item.name),
            // File count badge
            h('span', {
              class: 'text-xs text-gray-500 dark:text-gray-400 mr-2'
            }, `${props.item.file_count}`)
          ]),
          // Children (when expanded)
          isExpanded() && props.item.children && props.item.children.length > 0
            ? h('div', props.item.children.map(child =>
                h(FileTreeNode, {
                  key: child.path,
                  item: child,
                  depth: props.depth + 1,
                  searchQuery: props.searchQuery,
                  expandedFolders: props.expandedFolders,
                  onToggleFolder: (path) => emit('toggle-folder', path),
                  onDownload: (path, name) => emit('download', path, name)
                })
              ))
            : null
        ])
      } else {
        // File row
        return h('div', {
          class: 'flex items-center py-1.5 px-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded group',
          style: { paddingLeft: `${indent + 20}px` }
        }, [
          // File icon
          h('svg', {
            class: 'w-4 h-4 mr-2 text-gray-400 dark:text-gray-500',
            fill: 'currentColor',
            viewBox: '0 0 20 20'
          }, [
            h('path', {
              'fill-rule': 'evenodd',
              d: 'M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z',
              'clip-rule': 'evenodd'
            })
          ]),
          // File name
          h('span', {
            class: 'text-gray-700 dark:text-gray-200 flex-1 truncate'
          }, props.item.name),
          // File size
          h('span', {
            class: 'text-xs text-gray-500 dark:text-gray-400 mr-4'
          }, formatFileSizeHelper(props.item.size)),
          // Download button
          h('button', {
            class: 'p-1 text-indigo-600 dark:text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded',
            title: 'Download file',
            onClick: downloadFile
          }, [
            h('svg', {
              class: 'w-4 h-4',
              fill: 'none',
              stroke: 'currentColor',
              viewBox: '0 0 24 24'
            }, [
              h('path', {
                'stroke-linecap': 'round',
                'stroke-linejoin': 'round',
                'stroke-width': '2',
                d: 'M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
              })
            ])
          ])
        ])
      }
    }
  }
})

// Setup
const route = useRoute()
const router = useRouter()
const agentsStore = useAgentsStore()

// Minimal local state
const agent = ref(null)
const loading = ref(true)
const error = ref('')
const activeTab = ref('info')
const credentialFilter = ref('')

// Initialize composables
const { notification, showNotification } = useNotification()
const { formatBytes, formatUptime, formatRelativeTime, formatSource } = useFormatters()

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
  startStatsPolling,
  stopStatsPolling
} = useAgentStats(agent, agentsStore)

// Logs composable
const {
  logs,
  logLines,
  autoRefreshLogs,
  logsContainer,
  refreshLogs,
  handleLogsScroll
} = useAgentLogs(agent, agentsStore)

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

// Credentials composable
const {
  // New assignment-based API
  assignedCredentials,
  availableCredentials,
  loading: assignmentsLoading,
  applying,
  hasChanges,
  quickAddText,
  quickAddLoading,
  quickAddResult,
  loadCredentials,
  assignCredential,
  unassignCredential,
  applyToAgent,
  quickAddCredentials,
  countCredentials,
  // Legacy API (kept for backward compatibility)
  credentialsData,
  credentialsLoading,
  hotReloadText,
  hotReloadLoading,
  hotReloadResult,
  performHotReload
} = useAgentCredentials(agent, agentsStore, showNotification)

// Filtered credentials for search
const filteredAssignedCredentials = computed(() => {
  if (!credentialFilter.value) return assignedCredentials.value
  const filter = credentialFilter.value.toLowerCase()
  return assignedCredentials.value.filter(cred =>
    cred.name.toLowerCase().includes(filter) ||
    cred.service.toLowerCase().includes(filter)
  )
})

const filteredAvailableCredentials = computed(() => {
  if (!credentialFilter.value) return availableCredentials.value
  const filter = credentialFilter.value.toLowerCase()
  return availableCredentials.value.filter(cred =>
    cred.name.toLowerCase().includes(filter) ||
    cred.service.toLowerCase().includes(filter)
  )
})

// Sharing composable
const {
  shareEmail,
  shareLoading,
  shareMessage,
  unshareLoading,
  shareWithUser,
  removeShare
} = useAgentSharing(agent, agentsStore, loadAgent, showNotification)

// Permissions composable
const {
  availableAgents,
  permissionsLoading,
  permissionsSaving,
  permissionsDirty,
  permissionsMessage,
  loadPermissions,
  savePermissions,
  allowAllAgents,
  allowNoAgents,
  markDirty
} = useAgentPermissions(agent, agentsStore)

// Git sync composable
const {
  hasGitSync,
  gitStatus,
  gitLoading,
  gitSyncing,
  gitPulling,
  gitHasChanges,
  gitChangesCount,
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

// File browser composable
const {
  fileTree,
  filesLoading,
  filesError,
  fileSearchQuery,
  expandedFolders,
  totalFileCount,
  filteredFileTree,
  loadFiles,
  toggleFolder,
  downloadFile
} = useFileBrowser(agent, agentsStore, showNotification)

// Model options based on agent runtime (Multi-runtime support)
const availableModels = computed(() => {
  const runtime = agent.value?.runtime || 'claude-code'

  if (runtime === 'gemini-cli' || runtime === 'gemini') {
    return [
      { value: 'gemini-3-flash', label: 'Gemini 3 Flash' },
      { value: 'gemini-3-pro', label: 'Gemini 3 Pro' },
      { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
      { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
      { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
      { value: 'gemini-2.0-flash-lite', label: 'Gemini 2.0 Flash Lite' }
    ]
  }

  // Default: Claude Code models (Sonnet is the default)
  return [
    { value: 'sonnet', label: 'Sonnet 4.5' },
    { value: 'opus', label: 'Opus 4.5' },
    { value: 'haiku', label: 'Haiku' },
    { value: 'sonnet[1m]', label: 'Sonnet 4.5 (1M)' },
    { value: 'opus[1m]', label: 'Opus 4.5 (1M)' }
  ]
})

const modelSelectorTitle = computed(() => {
  const runtime = agent.value?.runtime || 'claude-code'
  return runtime === 'gemini-cli' || runtime === 'gemini' ? 'Select Gemini model' : 'Select Claude model'
})

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
  modelLoading,
  changeModel
} = useAgentSettings(agent, agentsStore, showNotification)

// Session activity composable
// NOTE: sessionInfo contains cost/context tracking data (total_cost_usd, context_tokens, etc.)
// This data is still fetched but not currently displayed in Terminal tab.
// See useSessionActivity.js for documentation on reusing this data in other UI components.
const {
  sessionInfo,  // Available: context_tokens, context_window, context_percent, total_cost_usd, message_count
  sessionActivity,
  loadSessionInfo,
  startActivityPolling,
  stopActivityPolling,
  resetSessionActivity
} = useSessionActivity(agent, agentsStore)

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
    await refreshLogs()
    await loadCredentials()
    await loadSessionInfo()
    await loadApiKeySetting()
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

// Watch for Files tab activation to load files
watch(activeTab, (newTab) => {
  if (newTab === 'files' && agent.value?.status === 'running') {
    loadFiles()
  }
  // Load permissions when permissions tab is selected (Phase 9.10)
  if (newTab === 'permissions' && agent.value?.can_share) {
    loadPermissions()
  }
})

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
  await refreshLogs()
  await loadCredentials()
  await loadSessionInfo()
  await loadApiKeySetting()
  startAllPolling()
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

// Handle use case click from Info tab - switch to terminal tab
const handleUseCaseClick = (text) => {
  activeTab.value = 'terminal'
  // Focus the terminal after switching tabs
  nextTick(() => {
    if (terminalRef.value?.focus) {
      terminalRef.value.focus()
    }
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
