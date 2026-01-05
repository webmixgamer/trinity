import { ref } from 'vue'

/**
 * Composable for agent credential management
 * Handles credential assignment, loading, and application to running agents
 */
export function useAgentCredentials(agentRef, agentsStore, showNotification) {
  // Credential lists
  const assignedCredentials = ref([])
  const availableCredentials = ref([])

  // Loading states
  const loading = ref(false)
  const applying = ref(false)
  const hasChanges = ref(false)

  // Quick-add functionality (formerly hot-reload)
  const quickAddText = ref('')
  const quickAddLoading = ref(false)
  const quickAddResult = ref(null)

  // Legacy support - kept for backward compatibility with existing UI
  const credentialsData = ref(null)
  const credentialsLoading = ref(false)
  const hotReloadText = ref('')
  const hotReloadLoading = ref(false)
  const hotReloadResult = ref(null)

  /**
   * Load credential assignments for the agent
   */
  const loadCredentials = async () => {
    if (!agentRef.value) return
    loading.value = true
    credentialsLoading.value = true
    try {
      const data = await agentsStore.getCredentialAssignments(agentRef.value.name)
      assignedCredentials.value = data.assigned || []
      availableCredentials.value = data.available || []

      // Also load legacy data for backward compatibility
      try {
        credentialsData.value = await agentsStore.getAgentCredentials(agentRef.value.name)
      } catch (err) {
        // Ignore - legacy endpoint may not exist
        credentialsData.value = null
      }
    } catch (err) {
      console.error('Failed to load credentials:', err)
      assignedCredentials.value = []
      availableCredentials.value = []
    } finally {
      loading.value = false
      credentialsLoading.value = false
    }
  }

  /**
   * Assign a credential to the agent
   */
  const assignCredential = async (credentialId) => {
    if (!agentRef.value) return
    try {
      await agentsStore.assignCredential(agentRef.value.name, credentialId)
      hasChanges.value = true
      await loadCredentials()
      if (showNotification) {
        showNotification('Credential assigned', 'success')
      }
    } catch (err) {
      console.error('Failed to assign credential:', err)
      if (showNotification) {
        showNotification(err.response?.data?.detail || 'Failed to assign credential', 'error')
      }
    }
  }

  /**
   * Unassign a credential from the agent
   */
  const unassignCredential = async (credentialId) => {
    if (!agentRef.value) return
    try {
      await agentsStore.unassignCredential(agentRef.value.name, credentialId)
      hasChanges.value = true
      await loadCredentials()
      if (showNotification) {
        showNotification('Credential removed', 'success')
      }
    } catch (err) {
      console.error('Failed to unassign credential:', err)
      if (showNotification) {
        showNotification(err.response?.data?.detail || 'Failed to remove credential', 'error')
      }
    }
  }

  /**
   * Apply assigned credentials to the running agent
   */
  const applyToAgent = async () => {
    if (!agentRef.value || agentRef.value.status !== 'running') return
    applying.value = true
    try {
      const result = await agentsStore.applyCredentials(agentRef.value.name)
      hasChanges.value = false
      if (showNotification) {
        showNotification(`Applied ${result.credential_count} credentials to agent`, 'success')
      }
      return result
    } catch (err) {
      console.error('Failed to apply credentials:', err)
      if (showNotification) {
        showNotification(err.response?.data?.detail || 'Failed to apply credentials', 'error')
      }
      throw err
    } finally {
      applying.value = false
    }
  }

  /**
   * Count credentials in .env-style text
   */
  const countCredentials = (text) => {
    if (!text) return 0
    let count = 0
    for (const line of text.split('\n')) {
      const trimmed = line.trim()
      if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
        count++
      }
    }
    return count
  }

  /**
   * Quick-add credentials (create, assign, and apply in one step)
   * Uses existing hot-reload endpoint which now also assigns credentials
   */
  const quickAddCredentials = async () => {
    if (!agentRef.value || agentRef.value.status !== 'running') return
    if (!quickAddText.value.trim()) return

    quickAddLoading.value = true
    quickAddResult.value = null

    try {
      const result = await agentsStore.hotReloadCredentials(agentRef.value.name, quickAddText.value)
      quickAddResult.value = {
        success: true,
        message: result.message,
        credentials: result.credential_names,
        note: result.note
      }
      quickAddText.value = ''
      hasChanges.value = false
      await loadCredentials()
      if (showNotification) {
        showNotification('Credentials added and applied', 'success')
      }
    } catch (err) {
      console.error('Quick add failed:', err)
      quickAddResult.value = {
        success: false,
        message: err.response?.data?.detail || err.message || 'Failed to add credentials'
      }
    } finally {
      quickAddLoading.value = false
    }
  }

  /**
   * Legacy: Perform hot reload (alias for quickAddCredentials)
   */
  const performHotReload = async () => {
    hotReloadText.value = quickAddText.value
    hotReloadLoading.value = true
    hotReloadResult.value = null

    try {
      await quickAddCredentials()
      hotReloadResult.value = quickAddResult.value
      hotReloadText.value = ''
    } finally {
      hotReloadLoading.value = false
    }
  }

  return {
    // New assignment-based API
    assignedCredentials,
    availableCredentials,
    loading,
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

    // Legacy API for backward compatibility
    credentialsData,
    credentialsLoading,
    hotReloadText,
    hotReloadLoading,
    hotReloadResult,
    performHotReload
  }
}
