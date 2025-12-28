import { ref } from 'vue'

/**
 * Composable for agent API key and model settings
 * Manages API key toggle and model selection
 */
export function useAgentSettings(agentRef, agentsStore, showNotification) {
  const apiKeySetting = ref({
    use_platform_api_key: true,
    restart_required: false
  })
  const apiKeySettingLoading = ref(false)
  const currentModel = ref('')
  const modelLoading = ref(false)

  const loadApiKeySetting = async () => {
    if (!agentRef.value) return
    try {
      apiKeySetting.value = await agentsStore.getAgentApiKeySetting(agentRef.value.name)
    } catch (err) {
      console.error('Failed to load API key setting:', err)
    }
  }

  const updateApiKeySetting = async (usePlatformKey) => {
    if (apiKeySettingLoading.value) return
    apiKeySettingLoading.value = true
    try {
      const result = await agentsStore.updateAgentApiKeySetting(agentRef.value.name, usePlatformKey)
      apiKeySetting.value = {
        use_platform_api_key: result.use_platform_api_key,
        restart_required: result.restart_required
      }
      showNotification(result.message, 'success')
    } catch (err) {
      showNotification(err.message || 'Failed to update API key setting', 'error')
    } finally {
      apiKeySettingLoading.value = false
    }
  }

  const loadModelInfo = async () => {
    if (!agentRef.value || agentRef.value.status !== 'running') return
    try {
      const info = await agentsStore.getAgentModel(agentRef.value.name)
      currentModel.value = info.model || ''
    } catch (err) {
      console.error('Failed to load model info:', err)
    }
  }

  const changeModel = async () => {
    if (!agentRef.value || modelLoading.value) return
    modelLoading.value = true
    try {
      await agentsStore.setAgentModel(agentRef.value.name, currentModel.value || null)
      showNotification(`Model changed to ${currentModel.value || 'default'}`, 'success')
    } catch (err) {
      console.error('Failed to change model:', err)
      showNotification('Failed to change model', 'error')
      // Reload to get actual state
      await loadModelInfo()
    } finally {
      modelLoading.value = false
    }
  }

  return {
    apiKeySetting,
    apiKeySettingLoading,
    currentModel,
    modelLoading,
    loadApiKeySetting,
    updateApiKeySetting,
    loadModelInfo,
    changeModel
  }
}
