import { ref, computed, onUnmounted } from 'vue'

/**
 * Composable for git status and sync functionality
 * Manages git sync operations and status polling
 */
export function useGitSync(agentRef, agentsStore, showNotification) {
  // Git sync - show tab for all agents (can initialize GitHub sync for any agent)
  const hasGitSync = computed(() => true)

  const gitStatus = ref(null)
  const gitLoading = ref(false)
  const gitSyncing = ref(false)
  const gitPulling = ref(false)
  const gitSyncResult = ref(null)
  let gitStatusInterval = null

  const gitHasChanges = computed(() => {
    return (gitStatus.value?.changes_count > 0) || (gitStatus.value?.ahead > 0)
  })

  const gitChangesCount = computed(() => {
    return gitStatus.value?.changes_count || 0
  })

  const loadGitStatus = async () => {
    if (!agentRef.value || agentRef.value.status !== 'running' || !hasGitSync.value) return
    gitLoading.value = true
    try {
      gitStatus.value = await agentsStore.getGitStatus(agentRef.value.name)
    } catch (err) {
      console.debug('Failed to load git status:', err)
      gitStatus.value = null
    } finally {
      gitLoading.value = false
    }
  }

  const refreshGitStatus = () => {
    gitSyncResult.value = null
    loadGitStatus()
  }

  const syncToGithub = async () => {
    if (!agentRef.value || gitSyncing.value) return
    gitSyncing.value = true
    gitSyncResult.value = null
    try {
      const result = await agentsStore.syncToGithub(agentRef.value.name)
      gitSyncResult.value = result
      if (result.success) {
        if (result.files_changed > 0) {
          showNotification(`Synced ${result.files_changed} file(s) to GitHub`, 'success')
        } else {
          showNotification(result.message || 'Already up to date', 'success')
        }
      } else {
        showNotification(result.message || 'Sync failed', 'error')
      }
      // Refresh status after sync
      await loadGitStatus()
    } catch (err) {
      console.error('Git sync failed:', err)
      showNotification(err.response?.data?.detail || 'Failed to sync to GitHub', 'error')
    } finally {
      gitSyncing.value = false
    }
  }

  const pullFromGithub = async () => {
    if (!agentRef.value || gitPulling.value) return
    gitPulling.value = true
    try {
      const result = await agentsStore.pullFromGithub(agentRef.value.name)
      if (result.success) {
        showNotification(result.message || 'Pulled latest changes from GitHub', 'success')
      } else {
        showNotification(result.message || 'Pull failed', 'error')
      }
      // Refresh status after pull
      await loadGitStatus()
    } catch (err) {
      console.error('Git pull failed:', err)
      showNotification(err.response?.data?.detail || 'Failed to pull from GitHub', 'error')
    } finally {
      gitPulling.value = false
    }
  }

  const startGitStatusPolling = () => {
    if (!hasGitSync.value) return
    loadGitStatus() // Load immediately
    gitStatusInterval = setInterval(loadGitStatus, 30000) // Then every 30 seconds
  }

  const stopGitStatusPolling = () => {
    if (gitStatusInterval) {
      clearInterval(gitStatusInterval)
      gitStatusInterval = null
    }
  }

  // Cleanup on unmount
  onUnmounted(() => {
    stopGitStatusPolling()
  })

  return {
    hasGitSync,
    gitStatus,
    gitLoading,
    gitSyncing,
    gitPulling,
    gitSyncResult,
    gitHasChanges,
    gitChangesCount,
    loadGitStatus,
    refreshGitStatus,
    syncToGithub,
    pullFromGithub,
    startGitStatusPolling,
    stopGitStatusPolling
  }
}
