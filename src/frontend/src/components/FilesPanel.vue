<template>
  <div class="p-6">
    <div v-if="agentStatus !== 'running'" class="text-center py-12">
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
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useAgentsStore } from '../stores/agents'
import { useFileBrowser } from '../composables/useFileBrowser'
import { useNotification } from '../composables'
import FileTreeNode from './FileTreeNode.vue'

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
const { showNotification } = useNotification()

// Create agent ref for composable
const agent = computed(() => ({
  name: props.agentName,
  status: props.agentStatus
}))

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

// Load files when agent is running
onMounted(() => {
  if (props.agentStatus === 'running') {
    loadFiles()
  }
})

// Reload when agent status changes to running
watch(() => props.agentStatus, (newStatus) => {
  if (newStatus === 'running') {
    loadFiles()
  }
})

// Reload when agent name changes
watch(() => props.agentName, () => {
  if (props.agentStatus === 'running') {
    loadFiles()
  }
})
</script>
