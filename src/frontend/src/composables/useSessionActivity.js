import { ref, computed, onUnmounted } from 'vue'

/**
 * Composable for session info and activity polling
 * Manages context window, token usage, and activity status
 */
export function useSessionActivity(agentRef, agentsStore) {
  const sessionInfo = ref({
    context_tokens: 0,
    context_window: 200000,
    context_percent: 0,
    total_cost_usd: 0,
    message_count: 0
  })

  const sessionActivity = ref({
    status: 'idle',
    active_tool: null,
    tool_counts: {},
    timeline: [],
    totals: { calls: 0, duration_ms: 0, started_at: null }
  })

  let activityRefreshInterval = null

  const currentToolDisplay = computed(() => {
    if (sessionActivity.value?.active_tool) {
      return `${sessionActivity.value.active_tool.name}...`
    }
    return 'Processing...'
  })

  const loadSessionInfo = async () => {
    if (!agentRef.value || agentRef.value.status !== 'running') return
    try {
      const info = await agentsStore.getSessionInfo(agentRef.value.name)
      sessionInfo.value = {
        context_tokens: info.context_tokens || 0,
        context_window: info.context_window || 200000,
        context_percent: info.context_percent || 0,
        total_cost_usd: info.total_cost_usd || 0,
        message_count: info.message_count || 0
      }
    } catch (err) {
      console.error('Failed to load session info:', err)
    }
  }

  const loadSessionActivity = async () => {
    if (!agentRef.value || agentRef.value.status !== 'running') return
    try {
      sessionActivity.value = await agentsStore.getSessionActivity(agentRef.value.name)
    } catch (err) {
      // Don't log errors - activity endpoint may fail during startup
      console.debug('Failed to load session activity:', err)
    }
  }

  const startActivityPolling = () => {
    loadSessionActivity() // Load immediately
    activityRefreshInterval = setInterval(loadSessionActivity, 2000) // Then every 2 seconds
  }

  const stopActivityPolling = () => {
    if (activityRefreshInterval) {
      clearInterval(activityRefreshInterval)
      activityRefreshInterval = null
    }
  }

  const clearActivity = async () => {
    if (!agentRef.value) return
    try {
      await agentsStore.clearSessionActivity(agentRef.value.name)
      sessionActivity.value = {
        status: 'idle',
        active_tool: null,
        tool_counts: {},
        timeline: [],
        totals: { calls: 0, duration_ms: 0, started_at: null }
      }
    } catch (err) {
      console.error('Failed to clear activity:', err)
    }
  }

  const resetSessionInfo = () => {
    sessionInfo.value = {
      context_tokens: 0,
      context_window: 200000,
      context_percent: 0,
      total_cost_usd: 0,
      message_count: 0
    }
  }

  const resetSessionActivity = () => {
    sessionActivity.value = {
      status: 'idle',
      active_tool: null,
      tool_counts: {},
      timeline: [],
      totals: { calls: 0, duration_ms: 0, started_at: null }
    }
  }

  // Cleanup on unmount
  onUnmounted(() => {
    stopActivityPolling()
  })

  return {
    sessionInfo,
    sessionActivity,
    currentToolDisplay,
    loadSessionInfo,
    loadSessionActivity,
    startActivityPolling,
    stopActivityPolling,
    clearActivity,
    resetSessionInfo,
    resetSessionActivity
  }
}
