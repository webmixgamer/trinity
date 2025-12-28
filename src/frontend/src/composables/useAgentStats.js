import { ref, onUnmounted } from 'vue'

/**
 * Composable for agent container stats polling
 * Manages CPU, memory, network, uptime metrics with auto-polling
 */
export function useAgentStats(agentRef, agentsStore) {
  const agentStats = ref(null)
  const statsLoading = ref(false)
  let statsRefreshInterval = null

  const loadStats = async () => {
    if (!agentRef.value || agentRef.value.status !== 'running') return
    statsLoading.value = true
    try {
      agentStats.value = await agentsStore.getAgentStats(agentRef.value.name)
    } catch (err) {
      // Don't log 400 errors (agent not running)
      if (err.response?.status !== 400) {
        console.error('Failed to load stats:', err)
      }
      agentStats.value = null
    } finally {
      statsLoading.value = false
    }
  }

  const startStatsPolling = () => {
    loadStats() // Load immediately
    statsRefreshInterval = setInterval(loadStats, 5000) // Then every 5 seconds
  }

  const stopStatsPolling = () => {
    if (statsRefreshInterval) {
      clearInterval(statsRefreshInterval)
      statsRefreshInterval = null
    }
  }

  // Cleanup on unmount
  onUnmounted(() => {
    stopStatsPolling()
  })

  return {
    agentStats,
    statsLoading,
    loadStats,
    startStatsPolling,
    stopStatsPolling
  }
}
