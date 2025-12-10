import { ref } from 'vue'
import { useAgentsStore } from '../stores/agents'

const ws = ref(null)
const isConnected = ref(false)

export function useWebSocket() {
  const agentsStore = useAgentsStore()

  const connect = () => {
    if (ws.value) return

    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      isConnected.value = true
      console.log('WebSocket connected')
    }

    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleMessage(data)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.value.onclose = () => {
      isConnected.value = false
      ws.value = null
      console.log('WebSocket disconnected')
      // Attempt to reconnect after 5 seconds
      setTimeout(connect, 5000)
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  const disconnect = () => {
    if (ws.value) {
      ws.value.close()
      ws.value = null
      isConnected.value = false
    }
  }

  const handleMessage = (data) => {
    switch (data.event) {
      case 'agent_created':
        agentsStore.agents.push(data.data)
        break
      case 'agent_deleted':
        agentsStore.agents = agentsStore.agents.filter(a => a.name !== data.data.name)
        break
      case 'agent_started':
        agentsStore.updateAgentStatus(data.data.name, 'running')
        break
      case 'agent_stopped':
        agentsStore.updateAgentStatus(data.data.name, 'stopped')
        break
      default:
        console.log('Unknown WebSocket event:', data.event)
    }
  }

  return {
    connect,
    disconnect,
    isConnected
  }
}
