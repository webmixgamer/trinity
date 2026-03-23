<template>
  <!-- User message (plain text) -->
  <div
    v-if="role === 'user'"
    class="max-w-[85%] ml-auto"
  >
    <div class="rounded-xl px-4 py-3 bg-indigo-600 text-white">
      <div v-if="source === 'voice'" class="flex items-center gap-1.5 mb-1 opacity-75">
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4M12 15a3 3 0 003-3V5a3 3 0 00-6 0v7a3 3 0 003 3z" /></svg>
        <span class="text-[10px] uppercase tracking-wide">Voice</span>
      </div>
      <p class="whitespace-pre-wrap">{{ content }}</p>
    </div>
    <p v-if="formattedTime" class="text-xs text-gray-400 dark:text-gray-500 mt-1 text-right">{{ formattedTime }}</p>
  </div>
  <!-- Assistant message (markdown rendered) -->
  <div
    v-else
    class="max-w-[85%]"
  >
    <div class="rounded-xl px-4 py-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm">
      <div v-if="source === 'voice'" class="flex items-center gap-1.5 mb-1 text-gray-400 dark:text-gray-500">
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072M18.364 5.636a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" /></svg>
        <span class="text-[10px] uppercase tracking-wide">Voice</span>
      </div>
      <div
        class="prose prose-sm dark:prose-invert max-w-none prose-p:my-2 prose-headings:my-3 prose-ul:my-2 prose-ol:my-2 prose-li:my-0 prose-pre:my-2 prose-code:text-indigo-600 dark:prose-code:text-indigo-400 prose-code:bg-gray-100 dark:prose-code:bg-gray-700 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none"
        v-html="renderedContent"
      ></div>
    </div>
    <p v-if="formattedTime" class="text-xs text-gray-400 dark:text-gray-500 mt-1">{{ formattedTime }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { renderMarkdown } from '../../utils/markdown'

const props = defineProps({
  role: {
    type: String,
    required: true,
    validator: (value) => ['user', 'assistant'].includes(value)
  },
  content: {
    type: String,
    required: true
  },
  timestamp: {
    type: String,
    default: null
  },
  source: {
    type: String,
    default: 'text'
  }
})

const renderedContent = computed(() => {
  return renderMarkdown(props.content)
})

const formattedTime = computed(() => {
  if (!props.timestamp) return null
  const date = new Date(props.timestamp)
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()
  const time = date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
  if (isToday) return time
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ', ' + time
})
</script>
