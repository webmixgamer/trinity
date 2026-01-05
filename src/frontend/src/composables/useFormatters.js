/**
 * Composable for shared formatting functions
 * Used across agent-related components
 */
export function useFormatters() {
  /**
   * Format bytes to human readable (e.g., 1024 -> "1.0 KB")
   */
  const formatBytes = (bytes) => {
    if (!bytes && bytes !== 0) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB']
    let value = bytes
    let unitIndex = 0
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024
      unitIndex++
    }
    return `${value.toFixed(unitIndex > 0 ? 1 : 0)} ${units[unitIndex]}`
  }

  /**
   * Format uptime to human readable (e.g., 3661 -> "1h 1m")
   */
  const formatUptime = (seconds) => {
    if (!seconds && seconds !== 0) return '0s'
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
    if (seconds < 86400) {
      const hours = Math.floor(seconds / 3600)
      const mins = Math.floor((seconds % 3600) / 60)
      return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
    }
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    return hours > 0 ? `${days}d ${hours}h` : `${days}d`
  }

  /**
   * Format relative time (e.g., "2 hours ago")
   */
  const formatRelativeTime = (dateString) => {
    if (!dateString) return 'Unknown'
    const date = new Date(dateString)
    const now = new Date()
    const diffSeconds = Math.floor((now - date) / 1000)

    if (diffSeconds < 60) return 'just now'
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} minutes ago`
    if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)} hours ago`
    if (diffSeconds < 604800) return `${Math.floor(diffSeconds / 86400)} days ago`
    return date.toLocaleDateString()
  }

  /**
   * Format token count for display (e.g., 45000 -> "45K")
   */
  const formatTokenCount = (count) => {
    if (!count && count !== 0) return '0'
    if (count < 1000) return count.toString()
    if (count < 1000000) return `${(count / 1000).toFixed(1)}K`
    return `${(count / 1000000).toFixed(2)}M`
  }

  /**
   * Format file size (same as formatBytes but using different precision)
   */
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
  }

  /**
   * Format duration for display (e.g., 1500 -> "1.5s")
   */
  const formatDuration = (ms) => {
    if (!ms && ms !== 0) return ''
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
  }

  /**
   * Format date with relative time (e.g., "5m ago")
   */
  const formatDate = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  /**
   * Format credential source for display
   */
  const formatSource = (source) => {
    if (!source) return 'Unknown source'

    if (source.startsWith('mcp:')) {
      const mcpServer = source.replace('mcp:', '')
      return `MCP Server: ${mcpServer}`
    }

    if (source === 'env_file' || source === 'template:env_file') {
      return 'Environment variable'
    }

    if (source.startsWith('template:mcp:')) {
      const mcpServer = source.replace('template:mcp:', '')
      return `MCP Server: ${mcpServer}`
    }

    return source
  }

  /**
   * Get context bar color based on percentage
   */
  const getContextBarColor = (percent) => {
    if (percent >= 90) return 'bg-red-500'
    if (percent >= 70) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  return {
    formatBytes,
    formatUptime,
    formatRelativeTime,
    formatTokenCount,
    formatFileSize,
    formatDuration,
    formatDate,
    formatSource,
    getContextBarColor
  }
}
