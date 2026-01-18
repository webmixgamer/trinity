import { ref, computed, watch } from 'vue'
import { useAuthStore } from '../stores/auth'

const STORAGE_KEY = 'trinity_onboarding'

// Shared state across all component instances
const state = ref(null)
const initialized = ref(false)

export function useOnboarding() {
  const authStore = useAuthStore()

  // Get storage key based on user
  const getStorageKey = () => `${STORAGE_KEY}_${authStore.user?.id || 'anon'}`

  // Initialize state from localStorage
  const initState = () => {
    if (initialized.value) return

    try {
      const stored = localStorage.getItem(getStorageKey())
      if (stored) {
        state.value = JSON.parse(stored)
      } else {
        state.value = getDefaultState()
      }
    } catch (e) {
      console.warn('Failed to load onboarding state:', e)
      state.value = getDefaultState()
    }
    initialized.value = true
  }

  // Default state structure
  const getDefaultState = () => ({
    dismissed: false,
    tourCompleted: false,
    checklistMinimized: false,
    checklist: {
      createProcess: false,
      runExecution: false,
      monitorExecution: false,
      setupSchedule: false,
      configureApproval: false
    }
  })

  // Save state to localStorage
  const saveState = () => {
    if (!state.value) return
    try {
      localStorage.setItem(getStorageKey(), JSON.stringify(state.value))
    } catch (e) {
      console.warn('Failed to save onboarding state:', e)
    }
  }

  // Watch for changes and persist
  watch(state, () => {
    saveState()
  }, { deep: true })

  // Computed properties
  const isFirstRun = computed(() => {
    if (!state.value) return false
    return !state.value.dismissed
  })

  const checklistProgress = computed(() => {
    if (!state.value) return { completed: 0, total: 5, required: 3 }

    const requiredItems = ['createProcess', 'runExecution', 'monitorExecution']
    const optionalItems = ['setupSchedule', 'configureApproval']

    const requiredCompleted = requiredItems.filter(item => state.value.checklist[item]).length
    const optionalCompleted = optionalItems.filter(item => state.value.checklist[item]).length

    return {
      completed: requiredCompleted + optionalCompleted,
      total: 5,
      required: 3,
      requiredCompleted
    }
  })

  const isChecklistComplete = computed(() => {
    return checklistProgress.value.requiredCompleted >= checklistProgress.value.required
  })

  // Methods
  const markChecklistItem = (item) => {
    if (!state.value) return
    if (item in state.value.checklist) {
      state.value.checklist[item] = true
      saveState()
    }
  }

  const dismissOnboarding = () => {
    if (!state.value) return
    state.value.dismissed = true
    saveState()
  }

  const markTourCompleted = () => {
    if (!state.value) return
    state.value.tourCompleted = true
    saveState()
  }

  const toggleChecklistMinimized = () => {
    if (!state.value) return
    state.value.checklistMinimized = !state.value.checklistMinimized
    saveState()
  }

  const resetOnboarding = () => {
    state.value = getDefaultState()
    saveState()
  }

  // Auto-detect completion based on API data
  const syncWithData = ({ processCount = 0, executionCount = 0, hasSchedule = false, hasApproval = false }) => {
    if (!state.value) return

    if (processCount > 0 && !state.value.checklist.createProcess) {
      state.value.checklist.createProcess = true
    }
    if (executionCount > 0 && !state.value.checklist.runExecution) {
      state.value.checklist.runExecution = true
    }
    if (executionCount > 0 && !state.value.checklist.monitorExecution) {
      // If they've run an execution, they've likely monitored it too
      state.value.checklist.monitorExecution = true
    }
    if (hasSchedule && !state.value.checklist.setupSchedule) {
      state.value.checklist.setupSchedule = true
    }
    if (hasApproval && !state.value.checklist.configureApproval) {
      state.value.checklist.configureApproval = true
    }

    saveState()
  }

  // Initialize on first use
  initState()

  return {
    state: computed(() => state.value),
    isFirstRun,
    checklistProgress,
    isChecklistComplete,
    markChecklistItem,
    dismissOnboarding,
    markTourCompleted,
    toggleChecklistMinimized,
    resetOnboarding,
    syncWithData
  }
}
