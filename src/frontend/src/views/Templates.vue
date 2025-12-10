<template>
  <div class="min-h-screen bg-gray-100">
    <NavBar />

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <div class="flex justify-between items-center mb-8">
          <div>
            <h1 class="text-3xl font-bold text-gray-900">Agent Templates</h1>
            <p class="mt-1 text-sm text-gray-500">
              Pre-configured agent templates with MCP servers and credentials
            </p>
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="fetchTemplates"
              class="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
              title="Refresh templates"
            >
              <svg class="w-5 h-5" :class="{ 'animate-spin': loading }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Loading state -->
        <div v-if="loading && templates.length === 0" class="flex justify-center py-12">
          <div class="flex items-center gap-3 text-gray-500">
            <svg class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Loading templates...</span>
          </div>
        </div>

        <!-- Error state -->
        <div v-else-if="error" class="text-center py-12">
          <div class="text-red-500 mb-4">
            <svg class="w-12 h-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p class="text-gray-600">{{ error }}</p>
          <button @click="fetchTemplates" class="mt-4 text-indigo-600 hover:text-indigo-800">
            Try again
          </button>
        </div>

        <!-- Templates grid -->
        <div v-else>
          <!-- GitHub Templates Section -->
          <div v-if="githubTemplates.length > 0" class="mb-8">
            <h2 class="text-lg font-semibold text-gray-800 mb-4 flex items-center">
              <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
              GitHub Templates
              <span class="ml-2 text-sm font-normal text-gray-500">({{ githubTemplates.length }})</span>
            </h2>
            <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              <div
                v-for="template in githubTemplates"
                :key="template.id"
                class="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow flex flex-col"
              >
                <div class="flex items-start justify-between mb-3">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 w-10 h-10 rounded-full bg-gray-900 flex items-center justify-center">
                      <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                      </svg>
                    </div>
                    <div class="ml-3">
                      <h3 class="text-lg font-medium text-gray-900">{{ getDisplayName(template) }}</h3>
                      <p class="text-xs text-gray-500">{{ template.github_repo }}</p>
                    </div>
                  </div>
                </div>

                <!-- Content area that grows -->
                <div class="flex-grow">
                  <p class="text-gray-600 text-sm mb-4 line-clamp-3">
                    {{ template.description || 'No description available' }}
                  </p>

                  <!-- MCP Servers -->
                  <div v-if="template.mcp_servers && template.mcp_servers.length > 0" class="mb-4">
                    <p class="text-xs font-medium text-gray-500 mb-1">MCP Servers:</p>
                    <div class="flex flex-wrap gap-1">
                      <span
                        v-for="server in template.mcp_servers.slice(0, 4)"
                        :key="server"
                        class="px-2 py-0.5 text-xs bg-gray-100 text-gray-700 rounded"
                      >
                        {{ server }}
                      </span>
                      <span
                        v-if="template.mcp_servers.length > 4"
                        class="px-2 py-0.5 text-xs bg-gray-100 text-gray-500 rounded"
                      >
                        +{{ template.mcp_servers.length - 4 }} more
                      </span>
                    </div>
                  </div>

                  <!-- Resources & Credentials -->
                  <div class="flex items-center gap-4 text-xs text-gray-500 mb-4">
                    <span class="flex items-center">
                      <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                      </svg>
                      {{ template.resources?.cpu || '2' }} CPU, {{ template.resources?.memory || '4g' }}
                    </span>
                    <span class="flex items-center">
                      <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                      </svg>
                      {{ template.required_credentials?.length || 0 }} credentials
                    </span>
                  </div>
                </div>

                <button
                  @click="useTemplate(template)"
                  class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded transition-colors mt-auto"
                >
                  Use Template
                </button>
              </div>
            </div>
          </div>

          <!-- Local Templates Section -->
          <div v-if="localTemplates.length > 0" class="mb-8">
            <h2 class="text-lg font-semibold text-gray-800 mb-4 flex items-center">
              <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
              </svg>
              Local Templates
              <span class="ml-2 text-sm font-normal text-gray-500">({{ localTemplates.length }})</span>
            </h2>
            <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              <div
                v-for="template in localTemplates"
                :key="template.id"
                class="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow flex flex-col"
              >
                <div class="flex items-start justify-between mb-3">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center">
                      <svg class="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div class="ml-3">
                      <h3 class="text-lg font-medium text-gray-900">{{ template.display_name }}</h3>
                      <p class="text-xs text-gray-500">{{ template.id }}</p>
                    </div>
                  </div>
                </div>

                <!-- Content area that grows -->
                <div class="flex-grow">
                  <p class="text-gray-600 text-sm mb-4 line-clamp-3">
                    {{ template.description || 'No description available' }}
                  </p>

                  <!-- MCP Servers -->
                  <div v-if="template.mcp_servers && template.mcp_servers.length > 0" class="mb-4">
                    <p class="text-xs font-medium text-gray-500 mb-1">MCP Servers:</p>
                    <div class="flex flex-wrap gap-1">
                      <span
                        v-for="server in template.mcp_servers.slice(0, 4)"
                        :key="server"
                        class="px-2 py-0.5 text-xs bg-gray-100 text-gray-700 rounded"
                      >
                        {{ server }}
                      </span>
                      <span
                        v-if="template.mcp_servers.length > 4"
                        class="px-2 py-0.5 text-xs bg-gray-100 text-gray-500 rounded"
                      >
                        +{{ template.mcp_servers.length - 4 }} more
                      </span>
                    </div>
                  </div>

                  <!-- Resources & Credentials -->
                  <div class="flex items-center gap-4 text-xs text-gray-500 mb-4">
                    <span class="flex items-center">
                      <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                      </svg>
                      {{ template.resources?.cpu || '2' }} CPU, {{ template.resources?.memory || '4g' }}
                    </span>
                    <span class="flex items-center">
                      <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                      </svg>
                      {{ template.required_credentials?.length || 0 }} credentials
                    </span>
                  </div>
                </div>

                <button
                  @click="useTemplate(template)"
                  class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded transition-colors mt-auto"
                >
                  Use Template
                </button>
              </div>
            </div>
          </div>

          <!-- Create Custom Agent Card -->
          <div class="mb-8">
            <h2 class="text-lg font-semibold text-gray-800 mb-4 flex items-center">
              <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Custom Agent
            </h2>
            <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              <div class="bg-white shadow rounded-lg p-6 border-2 border-dashed border-gray-300 hover:border-indigo-300 transition-colors">
                <div class="text-center py-4">
                  <div class="mx-auto w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-4">
                    <svg class="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                  </div>
                  <h3 class="text-lg font-medium text-gray-900 mb-2">Blank Agent</h3>
                  <p class="text-gray-600 text-sm mb-6">
                    Start with an empty configuration and customize everything
                  </p>
                  <button
                    @click="useTemplate(null)"
                    class="w-full bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded transition-colors"
                  >
                    Create Blank Agent
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty state -->
          <div v-if="templates.length === 0 && !loading" class="text-center py-12">
            <svg class="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="text-gray-500 text-lg mb-2">No templates configured</p>
            <p class="text-gray-400 text-sm">Configure GitHub templates in config.py or add local templates to config/agent-templates/</p>
          </div>
        </div>
      </div>
    </main>

    <!-- Create Agent Modal -->
    <CreateAgentModal
      v-if="showCreateModal"
      :initial-template="selectedTemplateId"
      @close="showCreateModal = false"
      @created="onAgentCreated"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import NavBar from '../components/NavBar.vue'
import CreateAgentModal from '../components/CreateAgentModal.vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const templates = ref([])
const loading = ref(false)
const error = ref('')
const showCreateModal = ref(false)
const selectedTemplateId = ref('')

// Computed properties to separate GitHub and local templates
const githubTemplates = computed(() => {
  return templates.value.filter(t => t.source === 'github')
})

const localTemplates = computed(() => {
  return templates.value.filter(t => t.source === 'local' || !t.source)
})

// Extract display name without "(GitHub)" suffix for cleaner display
const getDisplayName = (template) => {
  const name = template.display_name || template.id
  return name.replace(' (GitHub)', '')
}

const fetchTemplates = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await axios.get('/api/templates', {
      headers: authStore.authHeader
    })
    templates.value = response.data
  } catch (err) {
    console.error('Failed to fetch templates:', err)
    error.value = err.response?.data?.detail || 'Failed to load templates'
  } finally {
    loading.value = false
  }
}

const useTemplate = (template) => {
  selectedTemplateId.value = template?.id || ''
  showCreateModal.value = true
}

const onAgentCreated = (agent) => {
  // Navigate to the newly created agent's detail page
  if (agent?.name) {
    router.push(`/agents/${agent.name}`)
  } else {
    router.push('/agents')
  }
}

onMounted(() => {
  fetchTemplates()
})
</script>

<style scoped>
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
