<template>
  <div class="process-chat-assistant flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
      <div class="flex items-center gap-2">
        <SparklesIcon class="h-5 w-5 text-indigo-500" />
        <span class="font-medium text-gray-900 dark:text-white">Process Assistant</span>
      </div>
      <div class="flex items-center gap-2">
        <span 
          class="text-xs px-2 py-0.5 rounded-full"
          :class="systemAgentStatus === 'running' 
            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400' 
            : 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400'"
        >
          {{ systemAgentStatus === 'running' ? 'Connected' : 'Connecting...' }}
        </span>
      </div>
    </div>

    <!-- Messages area -->
    <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4">
      <!-- Welcome message -->
      <div v-if="messages.length === 0" class="text-center py-8">
        <div class="w-16 h-16 bg-indigo-100 dark:bg-indigo-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
          <SparklesIcon class="w-8 h-8 text-indigo-500" />
        </div>
        <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">
          Let's create your process!
        </h3>
        <p class="text-gray-500 dark:text-gray-400 text-sm max-w-md mx-auto mb-4">
          Describe what you want to automate, and I'll help you build it step by step.
        </p>
        
        <!-- Suggested prompts -->
        <div class="flex flex-wrap justify-center gap-2 mt-4">
          <button
            v-for="prompt in suggestedPrompts"
            :key="prompt"
            @click="sendSuggestedPrompt(prompt)"
            class="text-xs px-3 py-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-full text-gray-600 dark:text-gray-300 hover:border-indigo-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          >
            {{ prompt }}
          </button>
        </div>
      </div>

      <!-- Message list -->
      <div v-for="(msg, index) in messages" :key="index" class="animate-fade-in">
        <!-- User message -->
        <div v-if="msg.role === 'user'" class="flex justify-end">
          <div class="max-w-[85%] bg-indigo-600 text-white rounded-xl rounded-br-sm px-4 py-3">
            <p class="whitespace-pre-wrap text-sm">{{ msg.content }}</p>
          </div>
        </div>
        
        <!-- Assistant message -->
        <div v-else class="flex justify-start">
          <div class="max-w-[85%] bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-xl rounded-bl-sm px-4 py-3 shadow-sm border border-gray-100 dark:border-gray-700">
            <!-- Check for YAML code blocks -->
            <div v-if="hasYamlBlock(msg.content)" class="space-y-3">
              <div v-for="(part, i) in parseMessageParts(msg.content)" :key="i">
                <!-- Text content -->
                <p v-if="part.type === 'text'" class="whitespace-pre-wrap text-sm">{{ part.content }}</p>
                
                <!-- YAML code block -->
                <div v-else-if="part.type === 'yaml'" class="relative">
                  <div class="bg-gray-900 rounded-lg overflow-hidden">
                    <div class="flex items-center justify-between px-3 py-2 bg-gray-800 border-b border-gray-700">
                      <span class="text-xs text-gray-400 font-mono">process.yaml</span>
                      <button
                        @click="applyYaml(part.content)"
                        class="flex items-center gap-1 text-xs px-2 py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded transition-colors"
                      >
                        <ArrowRightIcon class="h-3 w-3" />
                        Apply to Editor
                      </button>
                    </div>
                    <pre class="p-3 text-sm text-gray-100 overflow-x-auto"><code>{{ part.content }}</code></pre>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Plain text message -->
            <p v-else class="whitespace-pre-wrap text-sm">{{ msg.content }}</p>
          </div>
        </div>
      </div>

      <!-- Loading indicator -->
      <div v-if="loading" class="flex justify-start">
        <div class="bg-white dark:bg-gray-800 rounded-xl px-4 py-3 shadow-sm border border-gray-100 dark:border-gray-700">
          <div class="flex items-center gap-2">
            <div class="flex space-x-1">
              <span class="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
              <span class="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
              <span class="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
            </div>
            <span class="text-sm text-gray-500 dark:text-gray-400">Thinking...</span>
          </div>
        </div>
      </div>

      <!-- Error message -->
      <div v-if="error" class="flex justify-center">
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3 text-sm text-red-600 dark:text-red-400">
          {{ error }}
          <button @click="error = null" class="ml-2 underline">Dismiss</button>
        </div>
      </div>
    </div>

    <!-- Input area -->
    <div class="border-t border-gray-200 dark:border-gray-700 p-3 bg-white dark:bg-gray-800">
      <form @submit.prevent="sendMessage" class="flex items-end gap-2">
        <textarea
          ref="inputRef"
          v-model="inputMessage"
          rows="1"
          placeholder="Describe what you want to automate..."
          class="flex-1 resize-none border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
          :disabled="loading"
          @keydown.enter.exact.prevent="sendMessage"
          @input="autoResize"
        ></textarea>
        <button
          type="submit"
          :disabled="loading || !inputMessage.trim()"
          class="p-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
        >
          <PaperAirplaneIcon class="w-5 h-5" />
        </button>
      </form>
      <p class="text-xs text-gray-400 mt-2 text-center">
        Powered by Trinity System Agent
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { SparklesIcon, PaperAirplaneIcon, ArrowRightIcon } from '@heroicons/vue/24/outline'
import api from '../api'

// Props and emits
const emit = defineEmits(['apply-yaml'])

// State
const messages = ref([])
const inputMessage = ref('')
const loading = ref(false)
const error = ref(null)
const systemAgentStatus = ref('connecting')
const messagesContainer = ref(null)
const inputRef = ref(null)

// Suggested prompts for empty state
const suggestedPrompts = [
  "Review content before publishing",
  "Analyze data and generate reports",
  "Route support tickets to agents",
  "Automate approval workflows"
]

// Process creation context - prepended to first message
const PROCESS_ASSISTANT_CONTEXT = `You are helping the user create a process definition for the Trinity Process Engine.

IMPORTANT INSTRUCTIONS:
1. Ask clarifying questions to understand their workflow needs
2. Suggest appropriate patterns (sequential steps, parallel execution, human approvals)
3. When ready, generate valid YAML that follows the process engine schema
4. Always wrap YAML in \`\`\`yaml code blocks
5. Use realistic step names and helpful comments
6. Include appropriate triggers (manual, schedule, or webhook)
7. You can check available agents using your Trinity MCP tools if the user asks

YAML SCHEMA REFERENCE:
- name: string (required, kebab-case)
- version: "1.0" format
- description: string
- trigger: { type: manual|schedule|webhook }
- steps: array of step definitions
- Step types: agent_task, human_approval, gateway, notification, sub_process
- Each step needs: id, name, type, and type-specific config
- Use depends_on: [step_id] for sequential execution

Now, help the user create their process. Start by understanding what they want to automate.

User's request: `

// Check system agent status on mount
onMounted(async () => {
  try {
    const response = await api.get('/api/system-agent/status')
    systemAgentStatus.value = response.data.status === 'running' ? 'running' : 'stopped'
  } catch (e) {
    systemAgentStatus.value = 'unavailable'
    console.error('Failed to check system agent status:', e)
  }
  
  // Focus input
  inputRef.value?.focus()
})

// Send message to system agent
async function sendMessage() {
  if (!inputMessage.value.trim() || loading.value) return
  
  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''
  error.value = null
  
  // Reset textarea height
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
  }
  
  // Add user message to chat
  messages.value.push({
    role: 'user',
    content: userMessage
  })
  
  // Scroll to bottom
  await nextTick()
  scrollToBottom()
  
  loading.value = true
  
  try {
    // Build message with context for first message
    let messageToSend = userMessage
    if (messages.value.length === 1) {
      messageToSend = PROCESS_ASSISTANT_CONTEXT + userMessage
    }
    
    const response = await api.post('/api/agents/trinity-system/chat', {
      message: messageToSend
    })
    
    // Add assistant response
    messages.value.push({
      role: 'assistant',
      content: response.data.response
    })
  } catch (err) {
    console.error('Chat error:', err)
    if (err.response?.status === 503) {
      error.value = 'System agent is not running. Please start it from the Settings page.'
    } else if (err.response?.status === 429) {
      error.value = 'System agent is busy. Please wait a moment.'
    } else {
      error.value = err.response?.data?.detail || 'Failed to get response. Please try again.'
    }
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

// Send suggested prompt
function sendSuggestedPrompt(prompt) {
  inputMessage.value = `I want to ${prompt.toLowerCase()}`
  sendMessage()
}

// Check if message contains YAML code block
function hasYamlBlock(content) {
  return /```ya?ml[\s\S]*?```/i.test(content)
}

// Parse message into text and YAML parts
function parseMessageParts(content) {
  const parts = []
  const regex = /```ya?ml\n?([\s\S]*?)```/gi
  let lastIndex = 0
  let match
  
  while ((match = regex.exec(content)) !== null) {
    // Add text before this match
    if (match.index > lastIndex) {
      const text = content.slice(lastIndex, match.index).trim()
      if (text) {
        parts.push({ type: 'text', content: text })
      }
    }
    
    // Add YAML block
    parts.push({ type: 'yaml', content: match[1].trim() })
    lastIndex = match.index + match[0].length
  }
  
  // Add remaining text
  if (lastIndex < content.length) {
    const text = content.slice(lastIndex).trim()
    if (text) {
      parts.push({ type: 'text', content: text })
    }
  }
  
  return parts
}

// Apply YAML to editor
function applyYaml(yaml) {
  emit('apply-yaml', yaml)
}

// Auto-resize textarea
function autoResize(event) {
  const textarea = event.target
  textarea.style.height = 'auto'
  textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px'
}

// Scroll to bottom of messages
function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// Watch for new messages and auto-scroll
watch(messages, () => {
  nextTick(() => scrollToBottom())
}, { deep: true })
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
