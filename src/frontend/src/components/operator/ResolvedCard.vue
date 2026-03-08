<template>
  <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-4 opacity-80">
    <div class="flex items-start gap-3">
      <!-- Agent Avatar -->
      <div
        class="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-semibold"
        :class="profile.color"
      >
        {{ profile.initials }}
      </div>

      <!-- Content -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-0.5">
          <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ item.agent_name }}</span>
          <span class="text-xs text-gray-400 dark:text-gray-500">&middot;</span>
          <span class="text-xs text-gray-400 dark:text-gray-500">{{ timeAgo(item.created_at) }}</span>
        </div>

        <p class="text-sm text-gray-600 dark:text-gray-400">{{ item.title }}</p>

        <!-- Response -->
        <div class="mt-2 flex items-center gap-2">
          <span class="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            {{ item.response }}
          </span>
          <span v-if="item.response_text" class="text-xs text-gray-400 dark:text-gray-500">
            &mdash; {{ item.response_text }}
          </span>
          <span class="text-xs text-gray-400 dark:text-gray-500 ml-auto">
            {{ timeAgo(item.responded_at) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useOperatorQueueStore } from '../../stores/operatorQueue'

const props = defineProps({
  item: { type: Object, required: true }
})

const store = useOperatorQueueStore()
const profile = computed(() => store.getProfile(props.item.agent_name))

function timeAgo(isoString) {
  if (!isoString) return ''
  const now = new Date()
  const then = new Date(isoString)
  const diffMs = now - then
  const diffMin = Math.floor(diffMs / 60000)
  const diffHr = Math.floor(diffMs / 3600000)
  const diffDay = Math.floor(diffMs / 86400000)

  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHr < 24) return `${diffHr}h ago`
  return `${diffDay}d ago`
}
</script>
