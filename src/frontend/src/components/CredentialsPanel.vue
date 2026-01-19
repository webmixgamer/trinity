<template>
  <div class="p-6 space-y-6">
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
            v-if="agentStatus === 'running' && assignedCredentials.length > 0"
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
          <span
            v-else-if="agentStatus !== 'running' && assignedCredentials.length > 0"
            class="text-sm text-yellow-600 dark:text-yellow-400"
          >
            Start agent to apply
          </span>
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
              :disabled="agentStatus !== 'running' || quickAddLoading"
              rows="5"
              placeholder="OPENAI_API_KEY=sk-...&#10;ANTHROPIC_API_KEY=sk-ant-...&#10;&#10;# Lines starting with # are ignored"
              class="w-full font-mono text-sm border border-gray-300 dark:border-gray-600 rounded-lg p-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:cursor-not-allowed"
            ></textarea>
            <span
              v-if="agentStatus !== 'running'"
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
              :disabled="agentStatus !== 'running' || quickAddLoading || !quickAddText.trim()"
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
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAgentsStore } from '../stores/agents'
import { useAgentCredentials } from '../composables/useAgentCredentials'
import { useNotification } from '../composables'

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

// Local state
const credentialFilter = ref('')

// Create agent ref for composable
const agent = computed(() => ({
  name: props.agentName,
  status: props.agentStatus
}))

const {
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
  countCredentials
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

// Load credentials on mount
onMounted(() => {
  loadCredentials()
})

// Reload when agent changes
watch(() => props.agentName, () => {
  loadCredentials()
})
</script>
