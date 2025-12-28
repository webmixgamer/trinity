import { ref } from 'vue'

/**
 * Composable for agent credential loading and hot reload
 * Manages credential data and live credential updates
 */
export function useAgentCredentials(agentRef, agentsStore, showNotification) {
  const credentialsData = ref(null)
  const credentialsLoading = ref(false)
  const hotReloadText = ref('')
  const hotReloadLoading = ref(false)
  const hotReloadResult = ref(null)

  const loadCredentials = async () => {
    if (!agentRef.value) return
    credentialsLoading.value = true
    try {
      credentialsData.value = await agentsStore.getAgentCredentials(agentRef.value.name)
    } catch (err) {
      console.error('Failed to load credentials:', err)
      credentialsData.value = null
    } finally {
      credentialsLoading.value = false
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
   * Perform hot reload of credentials
   */
  const performHotReload = async () => {
    if (!agentRef.value || agentRef.value.status !== 'running') return
    if (!hotReloadText.value.trim()) return

    hotReloadLoading.value = true
    hotReloadResult.value = null

    try {
      const result = await agentsStore.hotReloadCredentials(agentRef.value.name, hotReloadText.value)
      hotReloadResult.value = {
        success: true,
        message: result.message,
        credentials: result.credential_names,
        note: result.note
      }
      // Clear the textarea on success
      hotReloadText.value = ''
      // Refresh credentials list
      await loadCredentials()
    } catch (err) {
      console.error('Hot reload failed:', err)
      hotReloadResult.value = {
        success: false,
        message: err.response?.data?.detail || err.message || 'Failed to hot-reload credentials'
      }
    } finally {
      hotReloadLoading.value = false
    }
  }

  return {
    credentialsData,
    credentialsLoading,
    hotReloadText,
    hotReloadLoading,
    hotReloadResult,
    loadCredentials,
    countCredentials,
    performHotReload
  }
}
