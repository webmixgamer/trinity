<template>
  <div class="process-flow-preview bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-2 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">Process Flow</h3>
      <div class="flex items-center gap-2">
        <button
          @click="orientation = orientation === 'horizontal' ? 'vertical' : 'horizontal'"
          class="p-1 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 rounded"
          :title="orientation === 'horizontal' ? 'Switch to vertical' : 'Switch to horizontal'"
        >
          <component :is="orientation === 'horizontal' ? ArrowsUpDownIcon : ArrowsRightLeftIcon" class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Flow diagram -->
    <div class="p-4 overflow-auto" :style="{ maxHeight: height }">
      <!-- Error state -->
      <div v-if="parseError" class="flex items-center gap-2 text-red-600 dark:text-red-400 text-sm">
        <ExclamationCircleIcon class="w-5 h-5 flex-shrink-0" />
        <span>{{ parseError }}</span>
      </div>

      <!-- Empty state -->
      <div v-else-if="!steps.length" class="text-center text-gray-500 dark:text-gray-400 text-sm py-8">
        Add steps to see the flow diagram
      </div>

      <!-- Flow diagram -->
      <div v-else :class="containerClasses">
        <!-- Start node -->
        <div class="flex-shrink-0">
          <div class="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/30 border-2 border-green-500 flex items-center justify-center">
            <PlayIcon class="w-5 h-5 text-green-600 dark:text-green-400" />
          </div>
        </div>

        <!-- Arrow -->
        <div :class="arrowClasses">
          <div :class="arrowLineClasses"></div>
          <div :class="arrowHeadClasses"></div>
        </div>

        <!-- Steps -->
        <template v-for="(step, index) in steps" :key="step.id">
          <!-- Step node -->
          <div 
            class="flex-shrink-0 group relative"
            :class="{ 'ring-2 ring-red-400 rounded-lg': hasError(step.id) }"
          >
            <div 
              class="px-4 py-3 rounded-lg border-2 min-w-[120px] text-center transition-colors"
              :class="getStepClasses(step)"
            >
              <!-- Step icon -->
              <div class="flex items-center justify-center gap-2 mb-1">
                <component :is="getStepIcon(step.type)" class="w-4 h-4" />
                <span class="text-xs font-medium uppercase opacity-60">{{ step.type }}</span>
              </div>
              <!-- Step name -->
              <div class="text-sm font-medium truncate max-w-[150px]" :title="step.id">
                {{ step.id }}
              </div>
              <!-- Dependencies badge -->
              <div v-if="step.depends_on?.length" class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                depends on: {{ step.depends_on.join(', ') }}
              </div>
            </div>

            <!-- Error tooltip -->
            <div
              v-if="hasError(step.id)"
              class="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-red-600 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10"
            >
              {{ getError(step.id) }}
            </div>
          </div>

          <!-- Arrow between steps -->
          <div v-if="index < steps.length - 1" :class="arrowClasses">
            <div :class="arrowLineClasses"></div>
            <div :class="arrowHeadClasses"></div>
          </div>
        </template>

        <!-- Arrow to end -->
        <div :class="arrowClasses">
          <div :class="arrowLineClasses"></div>
          <div :class="arrowHeadClasses"></div>
        </div>

        <!-- End node -->
        <div class="flex-shrink-0">
          <div class="w-10 h-10 rounded-full bg-gray-100 dark:bg-gray-700 border-2 border-gray-400 dark:border-gray-500 flex items-center justify-center">
            <StopIcon class="w-5 h-5 text-gray-500 dark:text-gray-400" />
          </div>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div class="px-4 py-2 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
      <div class="flex items-center gap-1">
        <div class="w-3 h-3 rounded border-2 border-blue-500 bg-blue-50 dark:bg-blue-900/30"></div>
        <span>Agent Task</span>
      </div>
      <div class="flex items-center gap-1">
        <div class="w-3 h-3 rounded border-2 border-purple-500 bg-purple-50 dark:bg-purple-900/30"></div>
        <span>Human Approval</span>
      </div>
      <div class="flex items-center gap-1">
        <div class="w-3 h-3 rounded border-2 border-amber-500 bg-amber-50 dark:bg-amber-900/30"></div>
        <span>Gateway</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  PlayIcon,
  StopIcon,
  CpuChipIcon,
  UserIcon,
  ArrowsRightLeftIcon,
  ArrowsUpDownIcon,
  ExclamationCircleIcon,
  ClockIcon,
} from '@heroicons/vue/24/outline'
import yaml from 'js-yaml'

const props = defineProps({
  yamlContent: {
    type: String,
    default: ''
  },
  validationErrors: {
    type: Array,
    default: () => []
  },
  height: {
    type: String,
    default: '300px'
  }
})

// State
const orientation = ref('horizontal')
const parseError = ref(null)
const steps = ref([])

// Parse YAML to extract steps
watch(() => props.yamlContent, (newContent) => {
  parseYaml(newContent)
}, { immediate: true })

function parseYaml(content) {
  if (!content?.trim()) {
    steps.value = []
    parseError.value = null
    return
  }

  try {
    const parsed = yaml.load(content)
    if (parsed?.steps && Array.isArray(parsed.steps)) {
      steps.value = parsed.steps.map(step => ({
        id: step.id || 'unnamed',
        type: step.type || 'unknown',
        depends_on: step.depends_on || [],
      }))
      parseError.value = null
    } else if (parsed?.steps && typeof parsed.steps === 'object') {
      // Handle object-style steps
      steps.value = Object.entries(parsed.steps).map(([id, config]) => ({
        id,
        type: config?.type || 'unknown',
        depends_on: config?.depends_on || [],
      }))
      parseError.value = null
    } else {
      steps.value = []
      parseError.value = null
    }
  } catch (e) {
    parseError.value = e.message
    steps.value = []
  }
}

// Computed classes
const containerClasses = computed(() => [
  'flex items-center gap-2',
  orientation.value === 'vertical' ? 'flex-col' : 'flex-row flex-wrap',
])

const arrowClasses = computed(() => [
  'flex items-center',
  orientation.value === 'vertical' ? 'flex-col' : 'flex-row',
])

const arrowLineClasses = computed(() => [
  'bg-gray-300 dark:bg-gray-600',
  orientation.value === 'vertical' ? 'w-0.5 h-6' : 'w-6 h-0.5',
])

const arrowHeadClasses = computed(() => [
  'w-0 h-0 border-solid',
  orientation.value === 'vertical'
    ? 'border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-gray-300 dark:border-t-gray-600'
    : 'border-t-4 border-b-4 border-l-4 border-t-transparent border-b-transparent border-l-gray-300 dark:border-l-gray-600',
])

// Helper functions
function getStepClasses(step) {
  const typeClasses = {
    agent_task: 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
    human_approval: 'border-purple-500 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
    gateway: 'border-amber-500 bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
    timer: 'border-gray-500 bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300',
  }
  return typeClasses[step.type] || 'border-gray-400 bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
}

function getStepIcon(type) {
  const icons = {
    agent_task: CpuChipIcon,
    human_approval: UserIcon,
    gateway: ArrowsRightLeftIcon,
    timer: ClockIcon,
  }
  return icons[type] || CpuChipIcon
}

function hasError(stepId) {
  return props.validationErrors.some(e => 
    e.message?.includes(stepId) || e.path?.includes(stepId)
  )
}

function getError(stepId) {
  const error = props.validationErrors.find(e => 
    e.message?.includes(stepId) || e.path?.includes(stepId)
  )
  return error?.message || 'Validation error'
}
</script>

<style scoped>
.process-flow-preview {
  min-height: 200px;
}
</style>
