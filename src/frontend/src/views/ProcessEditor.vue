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
        <div class="flex justify-between items-center mb-6">
          <div class="flex items-center gap-4">
            <router-link
              to="/processes"
              class="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Back to processes"
            >
              <ArrowLeftIcon class="h-5 w-5" />
            </router-link>
            <div>
              <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
                {{ isNew ? 'Create Process' : 'Edit Process' }}
              </h1>
              <p v-if="!isNew && process" class="text-sm text-gray-500 dark:text-gray-400">
                {{ process.name }} v{{ process.version }}
                <span v-if="process.status" :class="[
                  'ml-2 px-2 py-0.5 text-xs font-medium rounded-full',
                  process.status === 'published' 
                    ? 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300'
                    : process.status === 'archived'
                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                      : 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-700 dark:text-yellow-300'
                ]">
                  {{ process.status }}
                </span>
              </p>
            </div>
          </div>

          <div class="flex items-center gap-3">
            <!-- Validate button -->
            <button
              @click="validateProcess"
              :disabled="saving || validating"
              class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
            >
              <span v-if="validating" class="flex items-center gap-2">
                <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Validating...
              </span>
              <span v-else class="flex items-center gap-2">
                <CheckCircleIcon class="h-4 w-4" />
                Validate
              </span>
            </button>

            <!-- Save button -->
            <button
              @click="saveProcess"
              :disabled="saving || hasErrors"
              class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <span v-if="saving" class="flex items-center gap-2">
                <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Saving...
              </span>
              <span v-else>Save</span>
            </button>

            <!-- Publish button (only for draft) -->
            <button
              v-if="!isNew && process?.status === 'draft'"
              @click="publishProcess"
              :disabled="saving || hasErrors"
              class="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Publish
            </button>

            <!-- Execute button (only for published) -->
            <button
              v-if="!isNew && process?.status === 'published'"
              @click="executeProcess"
              :disabled="saving"
              class="px-4 py-2 text-sm font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              <PlayIcon class="h-4 w-4" />
              Execute
            </button>
          </div>
        </div>

        <!-- Loading state -->
        <div v-if="loading" class="flex justify-center py-12">
          <div class="flex items-center gap-3 text-gray-500 dark:text-gray-400">
            <svg class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Loading process...</span>
          </div>
        </div>

        <!-- Editor -->
        <div v-else class="space-y-4">
          <!-- Split view: Editor + Preview -->
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- YAML Editor -->
            <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
              <div class="px-4 py-2 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
                <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">YAML Definition</h3>
              </div>
              <div class="p-4">
                <YamlEditor
                  v-model="yamlContent"
                  :validation-errors="validationErrors"
                  height="450px"
                  @save="saveProcess"
                  @change="handleChange"
                />
              </div>
            </div>

            <!-- Flow Preview -->
            <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
              <ProcessFlowPreview
                :yaml-content="yamlContent"
                :validation-errors="validationErrors"
                height="450px"
              />
            </div>
          </div>

          <!-- Help text -->
          <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
            <div class="p-4">
              <div class="flex items-start gap-2 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/50">
                <InformationCircleIcon class="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
                <div class="text-sm text-blue-700 dark:text-blue-300">
                  <p class="font-medium mb-1">YAML Process Definition</p>
                  <p class="text-xs text-blue-600 dark:text-blue-400">
                    Define your process with steps, dependencies, and configurations. 
                    Press <kbd class="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-800 rounded text-xs">Cmd+S</kbd> to save.
                    The flow preview updates as you type.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Unsaved changes warning modal -->
        <ConfirmDialog
          v-if="showUnsavedWarning"
          :visible="true"
          title="Unsaved Changes"
          message="You have unsaved changes. Are you sure you want to leave?"
          confirm-text="Leave"
          @confirm="confirmLeave"
          @cancel="showUnsavedWarning = false"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { useProcessesStore } from '../stores/processes'
import NavBar from '../components/NavBar.vue'
import YamlEditor from '../components/YamlEditor.vue'
import ProcessFlowPreview from '../components/ProcessFlowPreview.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  InformationCircleIcon,
  PlayIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const processesStore = useProcessesStore()

// State
const loading = ref(false)
const saving = ref(false)
const validating = ref(false)
const process = ref(null)
const yamlContent = ref(defaultYamlTemplate())
const validationErrors = ref([])
const notification = ref(null)
const hasUnsavedChanges = ref(false)
const showUnsavedWarning = ref(false)
const pendingNavigation = ref(null)

// Computed
const isNew = computed(() => route.name === 'ProcessNew')

const hasErrors = computed(() => 
  validationErrors.value.some(e => e.level === 'error' || !e.level)
)

// Default template for new processes
function defaultYamlTemplate() {
  return `# Process Definition
name: my-process
version: 1
description: Describe what this process does

steps:
  - id: step-1
    name: First Step
    type: agent_task
    agent: your-agent-name
    message: |
      Your message to the agent.
      Use {{input.variable}} to reference input data.
    timeout: 5m

# Define outputs to collect from steps
outputs:
  - name: result
    source: "{{steps.step-1.output}}"
`
}

// Lifecycle
onMounted(async () => {
  if (!isNew.value) {
    await loadProcess()
  }
})

// Navigation guard for unsaved changes
onBeforeRouteLeave((to, from, next) => {
  if (hasUnsavedChanges.value) {
    pendingNavigation.value = to
    showUnsavedWarning.value = true
    next(false)
  } else {
    next()
  }
})

// Methods
async function loadProcess() {
  loading.value = true
  try {
    const id = route.params.id
    const data = await processesStore.getProcess(id)
    process.value = data
    yamlContent.value = data.yaml_content || defaultYamlTemplate()
    hasUnsavedChanges.value = false
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to load process', 'error')
    router.push('/processes')
  } finally {
    loading.value = false
  }
}

function handleChange() {
  hasUnsavedChanges.value = true
  // Clear validation on edit
  validationErrors.value = []
}

async function validateProcess() {
  validating.value = true
  try {
    const result = await processesStore.validateYaml(yamlContent.value)
    validationErrors.value = result.errors || []
    
    if (result.is_valid) {
      showNotification('Validation passed!', 'success')
    } else {
      showNotification(`Found ${validationErrors.value.length} issue(s)`, 'error')
    }
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Validation failed', 'error')
  } finally {
    validating.value = false
  }
}

async function saveProcess() {
  // Validate first
  validating.value = true
  try {
    const result = await processesStore.validateYaml(yamlContent.value)
    validationErrors.value = result.errors || []
    
    if (!result.is_valid && validationErrors.value.some(e => e.level === 'error' || !e.level)) {
      showNotification('Please fix validation errors before saving', 'error')
      validating.value = false
      return
    }
  } catch (error) {
    showNotification('Validation failed', 'error')
    validating.value = false
    return
  }
  validating.value = false
  
  saving.value = true
  try {
    if (isNew.value) {
      const created = await processesStore.createProcess(yamlContent.value)
      showNotification('Process created successfully!', 'success')
      hasUnsavedChanges.value = false
      router.push(`/processes/${created.id}`)
    } else {
      await processesStore.updateProcess(route.params.id, yamlContent.value)
      showNotification('Process saved successfully!', 'success')
      hasUnsavedChanges.value = false
      await loadProcess()
    }
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to save process', 'error')
  } finally {
    saving.value = false
  }
}

async function publishProcess() {
  saving.value = true
  try {
    await processesStore.publishProcess(route.params.id)
    showNotification('Process published!', 'success')
    await loadProcess()
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to publish', 'error')
  } finally {
    saving.value = false
  }
}

async function executeProcess() {
  try {
    await processesStore.executeProcess(route.params.id)
    showNotification('Execution started!', 'success')
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to execute', 'error')
  }
}

function confirmLeave() {
  hasUnsavedChanges.value = false
  showUnsavedWarning.value = false
  if (pendingNavigation.value) {
    router.push(pendingNavigation.value)
  }
}

function showNotification(message, type = 'success') {
  notification.value = { message, type }
  setTimeout(() => {
    notification.value = null
  }, 3000)
}
</script>
