<template>
  <div class="flex flex-col h-[600px]">
    <!-- Header with session selector -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
      <div class="flex items-center space-x-3">
        <!-- Session selector dropdown -->
        <div class="relative" ref="dropdownRef">
          <button
            @click="showSessionDropdown = !showSessionDropdown"
            class="flex items-center space-x-2 px-3 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
          >
            <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            <span class="max-w-32 truncate">{{ currentSessionLabel }}</span>
            <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          <!-- Dropdown menu -->
          <div
            v-if="showSessionDropdown"
            class="absolute left-0 mt-2 w-72 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20"
          >
            <div class="py-2 max-h-64 overflow-y-auto">
              <div v-if="sessionsLoading" class="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                Loading sessions...
              </div>
              <div v-else-if="sessions.length === 0" class="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                No previous sessions
              </div>
              <button
                v-else
                v-for="session in sessions"
                :key="session.id"
                @click="selectSession(session)"
                class="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                :class="{ 'bg-indigo-50 dark:bg-indigo-900/30': currentSessionId === session.id }"
              >
                <div class="flex items-center justify-between">
                  <span class="text-sm font-medium text-gray-700 dark:text-gray-200">
                    {{ formatSessionDate(session.started_at) }}
                  </span>
                  <span class="text-xs text-gray-400">
                    {{ session.message_count }} msg{{ session.message_count !== 1 ? 's' : '' }}
                  </span>
                </div>
                <p v-if="session.last_message" class="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                  {{ session.last_message }}
                </p>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- New Chat button -->
      <button
        @click="startNewChat"
        :disabled="loading"
        class="inline-flex items-center px-3 py-1.5 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded-lg transition-colors"
      >
        <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        New Chat
      </button>
    </div>

    <!-- Agent not running message -->
    <div v-if="agentStatus !== 'running'" class="flex-1 flex items-center justify-center">
      <div class="text-center p-8">
        <div class="w-16 h-16 bg-yellow-100 dark:bg-yellow-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Agent Not Running</h3>
        <p class="text-gray-500 dark:text-gray-400 text-sm">
          Start the agent to begin chatting.
        </p>
      </div>
    </div>

    <!-- Chat interface -->
    <template v-else>
      <!-- Messages area -->
      <ChatMessages
        ref="messagesRef"
        :messages="messages"
        :loading="loading"
        loading-text="Thinking..."
        class="flex-1 px-2"
      >
        <template #empty>
          <div class="text-center py-12">
            <div class="w-16 h-16 bg-indigo-100 dark:bg-indigo-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg class="w-8 h-8 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Start a Conversation</h3>
            <p class="text-gray-500 dark:text-gray-400 text-sm max-w-md mx-auto">
              Chat with your agent using a simple interface. All activity is tracked in the Dashboard timeline.
            </p>
          </div>
        </template>
      </ChatMessages>

      <!-- Error message -->
      <div v-if="error" class="mx-4 mb-2 p-3 bg-red-100 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
        <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
      </div>

      <!-- Input area -->
      <div class="px-4 pb-4">
        <ChatInput
          v-model="message"
          :disabled="loading"
          placeholder="Type your message..."
          @submit="sendMessage"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { ChatMessages, ChatInput } from './chat'

const props = defineProps({
  agentName: {
    type: String,
    required: true
  },
  agentStatus: {
    type: String,
    default: 'stopped'
  }
})

const authStore = useAuthStore()

// State
const message = ref('')
const messages = ref([])
const loading = ref(false)
const error = ref(null)
const messagesRef = ref(null)

// Sessions
const sessions = ref([])
const sessionsLoading = ref(false)
const currentSessionId = ref(null)
const showSessionDropdown = ref(false)
const dropdownRef = ref(null)

// Computed
const currentSessionLabel = computed(() => {
  if (!currentSessionId.value) return 'New Conversation'
  const session = sessions.value.find(s => s.id === currentSessionId.value)
  if (session) {
    return formatSessionDate(session.started_at)
  }
  return 'Current Session'
})

// Format session date
const formatSessionDate = (dateStr) => {
  if (!dateStr) return 'Unknown'
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  })
}

// Load sessions
const loadSessions = async () => {
  sessionsLoading.value = true
  try {
    const response = await axios.get(`/api/agents/${props.agentName}/chat/sessions`, {
      headers: authStore.authHeader
    })
    sessions.value = response.data.sessions || []

    // If we have sessions and no current session, select the most recent active one
    if (sessions.value.length > 0 && !currentSessionId.value) {
      const activeSession = sessions.value.find(s => s.status === 'active')
      if (activeSession) {
        await selectSession(activeSession, false)
      }
    }
  } catch (err) {
    console.error('Failed to load sessions:', err)
  } finally {
    sessionsLoading.value = false
  }
}

// Select a session and load its messages
const selectSession = async (session, closeDropdown = true) => {
  if (closeDropdown) {
    showSessionDropdown.value = false
  }

  if (currentSessionId.value === session.id) return

  currentSessionId.value = session.id
  loading.value = true
  error.value = null

  try {
    const response = await axios.get(`/api/agents/${props.agentName}/chat/sessions/${session.id}`, {
      headers: authStore.authHeader
    })

    // Load messages from session
    messages.value = (response.data.messages || []).map(msg => ({
      role: msg.role,
      content: msg.content
    }))
  } catch (err) {
    console.error('Failed to load session:', err)
    error.value = 'Failed to load conversation history'
  } finally {
    loading.value = false
  }
}

// Start a new chat
const startNewChat = () => {
  currentSessionId.value = null
  messages.value = []
  error.value = null
  showSessionDropdown.value = false
}

// Build context from conversation history
const buildContextPrompt = (userMessage) => {
  if (messages.value.length === 0) {
    return userMessage
  }

  // Build conversation context (last 10 exchanges)
  const recentMessages = messages.value.slice(-20) // Last 20 messages (10 exchanges)
  let context = '### Previous conversation:\n\n'

  for (const msg of recentMessages) {
    const role = msg.role === 'user' ? 'User' : 'Assistant'
    context += `${role}: ${msg.content}\n\n`
  }

  context += `### Current message:\n\nUser: ${userMessage}`

  return context
}

// Send message
const sendMessage = async (userMessage) => {
  if (!userMessage || loading.value || props.agentStatus !== 'running') return

  error.value = null

  // Add user message to chat immediately
  messages.value.push({
    role: 'user',
    content: userMessage
  })

  // Clear input
  message.value = ''

  loading.value = true

  try {
    // Build context with conversation history
    const contextPrompt = buildContextPrompt(userMessage)

    // Send via task endpoint (headless execution for Dashboard tracking)
    const response = await axios.post(`/api/agents/${props.agentName}/task`, {
      message: contextPrompt
    }, {
      headers: authStore.authHeader
    })

    // Add assistant response
    if (response.data.response) {
      messages.value.push({
        role: 'assistant',
        content: response.data.response
      })
    }

    // Update current session if we got one in response
    if (response.data.task_execution_id && !currentSessionId.value) {
      // Refresh sessions to get the new one
      await loadSessions()
    }
  } catch (err) {
    console.error('Chat error:', err)
    error.value = err.response?.data?.detail || 'Failed to send message. Please try again.'
    // Remove the user message if send failed
    messages.value.pop()
  } finally {
    loading.value = false
  }
}

// Click outside to close dropdown
const handleClickOutside = (event) => {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target)) {
    showSessionDropdown.value = false
  }
}

// Watch for agent becoming available
watch(() => props.agentStatus, (newStatus) => {
  if (newStatus === 'running') {
    loadSessions()
  }
})

// Watch for agent name change
watch(() => props.agentName, () => {
  messages.value = []
  currentSessionId.value = null
  error.value = null
  if (props.agentStatus === 'running') {
    loadSessions()
  }
})

// Initialize
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  if (props.agentStatus === 'running') {
    loadSessions()
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
