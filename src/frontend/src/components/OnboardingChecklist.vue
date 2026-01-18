<template>
  <!-- Notification Toast using Teleport -->
  <Teleport to="body">
    <div
      v-if="showHint"
      class="fixed bottom-24 right-4 z-[9998] w-80 bg-indigo-600 text-white rounded-lg shadow-2xl p-4 flex items-start gap-3 transition-all duration-300"
      style="animation: slideIn 0.3s ease-out;"
    >
      <div class="flex-shrink-0">
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <div class="flex-1">
        <p class="text-sm font-medium">You're already here!</p>
        <p class="text-xs mt-1 opacity-90">{{ hintMessage }}</p>
      </div>
      <button @click="showHint = false" class="flex-shrink-0 opacity-70 hover:opacity-100">
        <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  </Teleport>

  <div
    v-if="showChecklist"
    class="fixed bottom-4 right-4 z-[9999] w-80 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden transition-all duration-300"
    :class="{ 'h-auto': !isMinimized, 'h-14': isMinimized }"
  >
    <!-- Header -->
    <div
      class="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-indigo-500 to-purple-500 text-white cursor-pointer"
      @click="toggleMinimized"
    >
      <div class="flex items-center gap-2">
        <SparklesIcon class="h-5 w-5" />
        <span class="font-semibold text-sm">Getting Started</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-xs bg-white/20 rounded-full px-2 py-0.5">
          {{ progress.completed }}/{{ progress.total }}
        </span>
        <ChevronDownIcon
          class="h-4 w-4 transition-transform duration-200"
          :class="{ 'rotate-180': isMinimized }"
        />
      </div>
    </div>

    <!-- Content -->
    <div v-if="!isMinimized" class="p-4">
      <!-- Progress bar -->
      <div class="mb-4">
        <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            class="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500"
            :style="{ width: `${progressPercent}%` }"
          />
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {{ progress.requiredCompleted >= progress.required ? 'All required steps complete!' : `${progress.required - progress.requiredCompleted} required steps remaining` }}
        </p>
      </div>

      <!-- Checklist items -->
      <ul class="space-y-2">
        <!-- Required items -->
        <li
          v-for="item in requiredItems"
          :key="item.id"
          class="flex items-start gap-3 p-2 rounded-lg transition-colors"
          :class="[
            item.completed ? 'bg-green-50 dark:bg-green-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-700/50',
            !item.completed && item.link ? 'cursor-pointer' : ''
          ]"
          @click="handleItemClick(item)"
        >
          <div
            class="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center mt-0.5"
            :class="item.completed
              ? 'bg-green-500 text-white'
              : 'border-2 border-gray-300 dark:border-gray-600'"
          >
            <CheckIcon v-if="item.completed" class="h-3 w-3" />
          </div>
          <div class="flex-1 min-w-0">
            <p
              class="text-sm font-medium"
              :class="item.completed
                ? 'text-green-700 dark:text-green-400 line-through'
                : 'text-gray-900 dark:text-white'"
            >
              {{ item.label }}
            </p>
            <p class="text-xs text-gray-500 dark:text-gray-400">{{ item.description }}</p>
          </div>
          <span
            v-if="!item.completed && item.link"
            class="flex-shrink-0 text-xs"
            :class="isOnTargetPage(item)
              ? 'text-amber-600 dark:text-amber-400'
              : 'text-indigo-600 dark:text-indigo-400'"
          >
            {{ isOnTargetPage(item) ? 'See above ↑' : 'Start →' }}
          </span>
        </li>

        <!-- Divider -->
        <li class="border-t border-gray-200 dark:border-gray-700 my-2"></li>

        <!-- Optional items label -->
        <li class="text-xs text-gray-500 dark:text-gray-400 px-2">Optional</li>

        <!-- Optional items -->
        <li
          v-for="item in optionalItems"
          :key="item.id"
          class="flex items-start gap-3 p-2 rounded-lg transition-colors"
          :class="item.completed ? 'bg-green-50 dark:bg-green-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'"
        >
          <div
            class="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center mt-0.5"
            :class="item.completed
              ? 'bg-green-500 text-white'
              : 'border-2 border-gray-300 dark:border-gray-600'"
          >
            <CheckIcon v-if="item.completed" class="h-3 w-3" />
          </div>
          <div class="flex-1 min-w-0">
            <p
              class="text-sm font-medium"
              :class="item.completed
                ? 'text-green-700 dark:text-green-400 line-through'
                : 'text-gray-900 dark:text-white'"
            >
              {{ item.label }}
            </p>
            <p class="text-xs text-gray-500 dark:text-gray-400">{{ item.description }}</p>
          </div>
        </li>
      </ul>

      <!-- Dismiss button -->
      <div class="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
        <button
          @click="dismiss"
          class="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
        >
          Dismiss checklist
        </button>
        <button
          @click.stop.prevent="navigateTo('/processes/docs')"
          type="button"
          class="text-xs text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer pointer-events-auto"
        >
          View all docs →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOnboarding } from '../composables/useOnboarding'
import {
  CheckIcon,
  ChevronDownIcon,
  SparklesIcon
} from '@heroicons/vue/24/solid'

const router = useRouter()
const showHint = ref(false)
const hintMessage = ref('')
let hintTimeout = null

const {
  state,
  checklistProgress,
  isChecklistComplete,
  dismissOnboarding,
  toggleChecklistMinimized
} = useOnboarding()

onUnmounted(() => {
  if (hintTimeout) {
    clearTimeout(hintTimeout)
  }
})

// Show checklist only if not dismissed
const showChecklist = computed(() => {
  return state.value && !state.value.dismissed
})

const isMinimized = computed(() => {
  return state.value?.checklistMinimized || false
})

const progress = computed(() => checklistProgress.value)

const progressPercent = computed(() => {
  return Math.round((progress.value.completed / progress.value.total) * 100)
})

// Checklist item definitions
const requiredItems = computed(() => [
  {
    id: 'createProcess',
    label: 'Create your first process',
    description: 'Define a workflow with steps and agents',
    completed: state.value?.checklist.createProcess || false,
    link: '/processes/new'
  },
  {
    id: 'runExecution',
    label: 'Run a process execution',
    description: 'Execute your process and see it in action',
    completed: state.value?.checklist.runExecution || false,
    link: '/processes'
  },
  {
    id: 'monitorExecution',
    label: 'Monitor an execution',
    description: 'View progress and step outputs',
    completed: state.value?.checklist.monitorExecution || false,
    link: '/executions'
  }
])

const optionalItems = computed(() => [
  {
    id: 'setupSchedule',
    label: 'Set up a schedule',
    description: 'Automate recurring process runs',
    completed: state.value?.checklist.setupSchedule || false
  },
  {
    id: 'configureApproval',
    label: 'Configure human approval',
    description: 'Add approval gates to your workflow',
    completed: state.value?.checklist.configureApproval || false
  }
])

const toggleMinimized = () => {
  toggleChecklistMinimized()
}

const dismiss = () => {
  dismissOnboarding()
}

const isOnTargetPage = (item) => {
  return item.link && router.currentRoute.value.path === item.link
}

const navigateTo = (path) => {
  router.push(path)
}

const showHintToast = (message) => {
  hintMessage.value = message
  showHint.value = true

  // Clear any existing timeout
  if (hintTimeout) {
    clearTimeout(hintTimeout)
  }

  // Auto-hide after 5 seconds
  hintTimeout = setTimeout(() => {
    showHint.value = false
  }, 5000)
}

const handleItemClick = (item) => {
  if (item.completed) {
    return // Already completed, no action needed
  }

  if (!item.link) {
    return // No link defined
  }

  // If already on the target page, provide feedback
  if (router.currentRoute.value.path === item.link) {
    // Show helpful hints based on the item
    if (item.id === 'runExecution') {
      showHintToast('Click the Play button (▶️) on a published process to execute it!')
    } else if (item.id === 'createProcess') {
      showHintToast('Click the "Create Process" button above to start creating your process!')
    } else if (item.id === 'monitorExecution') {
      showHintToast('View your running executions and monitor their progress here!')
    }
    return
  }

  navigateTo(item.link)
}
</script>

<style scoped>
@keyframes slideIn {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}
</style>
