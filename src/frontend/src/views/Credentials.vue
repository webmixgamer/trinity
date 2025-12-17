<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <div class="flex justify-between items-center mb-8">
          <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Credentials</h1>
          <button
            @click="showCreateModal = true"
            class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
          >
            <svg class="-ml-1 mr-2 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Add Credential
          </button>
        </div>

        <!-- Bulk Import Section -->
        <div class="bg-white dark:bg-gray-800 shadow dark:shadow-gray-900 rounded-lg p-6 mb-6">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-lg font-medium text-gray-900 dark:text-white">Bulk Import Credentials</h2>
            <button
              v-if="!showBulkImport"
              @click="showBulkImport = true"
              class="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
            >
              Show import
            </button>
            <button
              v-else
              @click="showBulkImport = false"
              class="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
            >
              Hide
            </button>
          </div>

          <div v-if="showBulkImport">
            <!-- Template Selector for .env template -->
            <div class="mb-4 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
              <div class="flex items-center justify-between mb-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Get credential template for:</label>
              </div>
              <div class="flex items-center gap-3">
                <select
                  v-model="selectedTemplateForEnv"
                  class="flex-1 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                >
                  <option value="">Select a template...</option>
                  <option v-for="template in templates" :key="template.id" :value="template.id">
                    {{ template.display_name }}
                  </option>
                </select>
                <button
                  @click="copyEnvTemplate"
                  :disabled="!selectedTemplateForEnv || loadingEnvTemplate"
                  class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg v-if="loadingEnvTemplate" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <svg v-else-if="copiedEnvTemplate" class="-ml-1 mr-2 h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                  <svg v-else class="-ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                  </svg>
                  {{ copiedEnvTemplate ? 'Copied!' : 'Copy Template' }}
                </button>
              </div>
              <p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Copy the credential template, fill in values in 1Password or your password manager, then paste below.
              </p>
            </div>

            <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">
              Paste your credentials in .env format (KEY=VALUE pairs, one per line). Comments starting with # are ignored.
            </p>
            <textarea
              v-model="bulkImportContent"
              rows="8"
              class="block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-mono"
              placeholder="HEYGEN_API_KEY=your-key-here
TWITTER_API_KEY=your-twitter-key
TWITTER_API_SECRET=your-twitter-secret
# Comments are ignored
CLOUDINARY_API_KEY=your-cloudinary-key"
            ></textarea>

            <div class="mt-3 flex items-center justify-between">
              <p class="text-xs text-gray-400 dark:text-gray-500">
                Service and type are auto-detected from key names
              </p>
              <button
                @click="bulkImportCredentials"
                :disabled="bulkImporting || !bulkImportContent.trim()"
                class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg v-if="bulkImporting" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {{ bulkImporting ? 'Importing...' : 'Import Credentials' }}
              </button>
            </div>

            <!-- Import Results -->
            <div v-if="bulkImportResult" class="mt-4 p-4 rounded-md" :class="bulkImportResult.errors.length > 0 ? 'bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800' : 'bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800'">
              <div class="flex">
                <div class="flex-shrink-0">
                  <svg v-if="bulkImportResult.errors.length === 0" class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                  </svg>
                  <svg v-else class="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="ml-3">
                  <p class="text-sm font-medium" :class="bulkImportResult.errors.length === 0 ? 'text-green-800 dark:text-green-300' : 'text-yellow-800 dark:text-yellow-300'">
                    Created {{ bulkImportResult.created }} credential(s)
                    <span v-if="bulkImportResult.skipped > 0">, {{ bulkImportResult.skipped }} skipped</span>
                  </p>
                  <div v-if="bulkImportResult.errors.length > 0" class="mt-2 text-sm text-yellow-700 dark:text-yellow-400">
                    <p class="font-medium">Errors:</p>
                    <ul class="list-disc list-inside">
                      <li v-for="(error, idx) in bulkImportResult.errors.slice(0, 5)" :key="idx">{{ error }}</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Credentials List -->
        <div class="bg-white dark:bg-gray-800 shadow dark:shadow-gray-900 rounded-lg overflow-hidden">
          <div v-if="loading" class="p-8 text-center">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
            <p class="mt-4 text-gray-500 dark:text-gray-400">Loading credentials...</p>
          </div>

          <div v-else-if="credentials.length === 0" class="text-center py-12">
            <svg class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">No credentials</h3>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">Get started by adding a credential or using bulk import.</p>
          </div>

          <ul v-else class="divide-y divide-gray-200 dark:divide-gray-700">
            <li v-for="cred in credentials" :key="cred.id" class="p-6 hover:bg-gray-50 dark:hover:bg-gray-700">
              <div class="flex items-center justify-between">
                <div class="flex items-center flex-1">
                  <div class="flex-shrink-0">
                    <div class="h-10 w-10 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center">
                      <span class="text-xl">{{ getServiceIcon(cred.service) }}</span>
                    </div>
                  </div>
                  <div class="ml-4 flex-1">
                    <div class="flex items-center">
                      <h3 class="text-sm font-medium text-gray-900 dark:text-white">{{ cred.name }}</h3>
                      <span class="ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300">
                        {{ cred.type }}
                      </span>
                      <span class="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300">
                        {{ cred.service }}
                      </span>
                    </div>
                    <p v-if="cred.description" class="mt-1 text-sm text-gray-500 dark:text-gray-400">{{ cred.description }}</p>
                    <p class="mt-1 text-xs text-gray-400 dark:text-gray-500">
                      Created {{ formatDate(cred.created_at) }}
                    </p>
                  </div>
                </div>
                <div class="ml-4 flex items-center space-x-2">
                  <button
                    @click="viewCredential(cred)"
                    class="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 shadow-sm text-xs font-medium rounded text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
                  >
                    View
                  </button>
                  <button
                    @click="deleteCredential(cred.id)"
                    class="inline-flex items-center px-3 py-1.5 border border-red-300 dark:border-red-700 shadow-sm text-xs font-medium rounded text-red-700 dark:text-red-400 bg-white dark:bg-gray-800 hover:bg-red-50 dark:hover:bg-red-900/30"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </main>

    <!-- Create Credential Modal -->
    <div v-if="showCreateModal" class="fixed z-10 inset-0 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:p-0">
        <div class="fixed inset-0 bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-80 transition-opacity" @click="showCreateModal = false"></div>

        <div class="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div class="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Add Credential</h3>

            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Name</label>
                <input
                  v-model="newCredential.name"
                  type="text"
                  class="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  placeholder="My API Key"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Service</label>
                <select
                  v-model="newCredential.service"
                  class="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                >
                  <option value="">Select service</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="google">Google</option>
                  <option value="slack">Slack</option>
                  <option value="github">GitHub</option>
                  <option value="notion">Notion</option>
                  <option value="custom">Custom</option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Type</label>
                <select
                  v-model="newCredential.type"
                  class="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                >
                  <option value="api_key">API Key</option>
                  <option value="token">Token</option>
                  <option value="basic_auth">Basic Auth</option>
                </select>
              </div>

              <div v-if="newCredential.type === 'api_key'">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">API Key</label>
                <input
                  v-model="newCredential.api_key"
                  type="password"
                  class="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  placeholder="sk-..."
                />
              </div>

              <div v-if="newCredential.type === 'token'">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Token</label>
                <input
                  v-model="newCredential.token"
                  type="password"
                  class="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  placeholder="xoxb-..."
                />
              </div>

              <div v-if="newCredential.type === 'basic_auth'">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Username</label>
                <input
                  v-model="newCredential.username"
                  type="text"
                  class="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                />
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mt-2">Password</label>
                <input
                  v-model="newCredential.password"
                  type="password"
                  class="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Description (optional)</label>
                <textarea
                  v-model="newCredential.description"
                  rows="2"
                  class="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  placeholder="Additional notes..."
                ></textarea>
              </div>
            </div>
          </div>

          <div class="bg-gray-50 dark:bg-gray-900 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              @click="createCredential"
              :disabled="creating"
              class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50"
            >
              {{ creating ? 'Creating...' : 'Create' }}
            </button>
            <button
              @click="showCreateModal = false"
              class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-800 text-base font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
            >
              Cancel
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
import { ref, reactive, onMounted } from 'vue'
import NavBar from '../components/NavBar.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const credentials = ref([])
const loading = ref(true)
const showCreateModal = ref(false)
const creating = ref(false)

// Bulk import state
const showBulkImport = ref(false)
const bulkImportContent = ref('')
const bulkImporting = ref(false)
const bulkImportResult = ref(null)

// Template env template state
const templates = ref([])
const selectedTemplateForEnv = ref('')
const loadingEnvTemplate = ref(false)
const copiedEnvTemplate = ref(false)

const newCredential = ref({
  name: '',
  service: '',
  type: 'api_key',
  api_key: '',
  token: '',
  username: '',
  password: '',
  description: ''
})

// Confirm dialog state
const confirmDialog = reactive({
  visible: false,
  title: '',
  message: '',
  confirmText: 'Delete',
  variant: 'danger',
  onConfirm: () => {}
})

const fetchCredentials = async () => {
  try {
    const response = await fetch('/api/credentials', {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    if (response.ok) {
      credentials.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to fetch credentials:', error)
  } finally {
    loading.value = false
  }
}

const fetchTemplates = async () => {
  try {
    const response = await fetch('/api/templates', {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    if (response.ok) {
      templates.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to fetch templates:', error)
  }
}

const copyEnvTemplate = async () => {
  if (!selectedTemplateForEnv.value) return

  loadingEnvTemplate.value = true
  copiedEnvTemplate.value = false

  try {
    const response = await fetch(`/api/templates/env-template?template_id=${encodeURIComponent(selectedTemplateForEnv.value)}`, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })

    if (response.ok) {
      const data = await response.json()
      await navigator.clipboard.writeText(data.content)
      copiedEnvTemplate.value = true

      // Reset the copied state after 2 seconds
      setTimeout(() => {
        copiedEnvTemplate.value = false
      }, 2000)
    } else {
      const error = await response.json()
      alert(`Failed to get template: ${error.detail}`)
    }
  } catch (error) {
    console.error('Failed to copy env template:', error)
    alert('Failed to copy template to clipboard')
  } finally {
    loadingEnvTemplate.value = false
  }
}

const createCredential = async () => {
  creating.value = true
  
  try {
    let credentials_data = {}
    
    if (newCredential.value.type === 'api_key') {
      credentials_data = { api_key: newCredential.value.api_key }
    } else if (newCredential.value.type === 'token') {
      credentials_data = { token: newCredential.value.token }
    } else if (newCredential.value.type === 'basic_auth') {
      credentials_data = {
        username: newCredential.value.username,
        password: newCredential.value.password
      }
    }
    
    const response = await fetch('/api/credentials', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify({
        name: newCredential.value.name,
        service: newCredential.value.service,
        type: newCredential.value.type,
        credentials: credentials_data,
        description: newCredential.value.description
      })
    })
    
    if (response.ok) {
      showCreateModal.value = false
      newCredential.value = {
        name: '',
        service: '',
        type: 'api_key',
        api_key: '',
        token: '',
        username: '',
        password: '',
        description: ''
      }
      await fetchCredentials()
    } else {
      const error = await response.json()
      alert(`Failed to create credential: ${error.detail}`)
    }
  } catch (error) {
    console.error('Failed to create credential:', error)
    alert('Failed to create credential')
  } finally {
    creating.value = false
  }
}

const deleteCredential = async (id) => {
  confirmDialog.title = 'Delete Credential'
  confirmDialog.message = 'Are you sure you want to delete this credential?'
  confirmDialog.confirmText = 'Delete'
  confirmDialog.variant = 'danger'
  confirmDialog.onConfirm = async () => {
    try {
      const response = await fetch(`/api/credentials/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authStore.token}`
        }
      })

      if (response.ok) {
        await fetchCredentials()
      }
    } catch (error) {
      console.error('Failed to delete credential:', error)
    }
  }
  confirmDialog.visible = true
}

const bulkImportCredentials = async () => {
  if (!bulkImportContent.value.trim()) {
    return
  }

  bulkImporting.value = true
  bulkImportResult.value = null

  try {
    const response = await fetch('/api/credentials/bulk', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify({
        content: bulkImportContent.value
      })
    })

    if (response.ok) {
      const result = await response.json()
      bulkImportResult.value = result

      // Clear the textarea on success
      if (result.created > 0) {
        bulkImportContent.value = ''
        await fetchCredentials()
      }
    } else {
      const error = await response.json()
      bulkImportResult.value = {
        created: 0,
        skipped: 0,
        errors: [error.detail || 'Failed to import credentials'],
        credentials: []
      }
    }
  } catch (error) {
    console.error('Failed to bulk import credentials:', error)
    bulkImportResult.value = {
      created: 0,
      skipped: 0,
      errors: ['Network error: ' + error.message],
      credentials: []
    }
  } finally {
    bulkImporting.value = false
  }
}

const viewCredential = (cred) => {
  alert(`Credential: ${cred.name}\nService: ${cred.service}\nType: ${cred.type}`)
}

const getServiceIcon = (service) => {
  const icons = {
    openai: '🤖',
    anthropic: '🧠',
    google: '🔍',
    slack: '💬',
    github: '🐙',
    notion: '📝',
    custom: '🔧'
  }
  return icons[service] || '🔑'
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

onMounted(() => {
  fetchCredentials()
  fetchTemplates()
})
</script>
