<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <NavBar />

    <main class="max-w-3xl mx-auto py-6 px-4 sm:px-6">
      <!-- Page Header -->
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Operating Room</h1>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Your agents need your input on {{ store.pendingCount }} {{ store.pendingCount === 1 ? 'item' : 'items' }}
        </p>
      </div>

      <!-- Tabs: Open / Resolved -->
      <div class="flex items-center gap-1 mb-6 border-b border-gray-200 dark:border-gray-700">
        <button
          @click="store.activeTab = 'open'"
          class="px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px"
          :class="store.activeTab === 'open'
            ? 'border-blue-500 text-blue-600 dark:text-blue-400'
            : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'"
        >
          Open
          <span
            v-if="store.pendingCount > 0"
            class="ml-1.5 px-1.5 py-0.5 text-xs font-medium rounded-full"
            :class="store.activeTab === 'open'
              ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
              : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'"
          >
            {{ store.pendingCount }}
          </span>
        </button>
        <button
          @click="store.activeTab = 'resolved'"
          class="px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px"
          :class="store.activeTab === 'resolved'
            ? 'border-blue-500 text-blue-600 dark:text-blue-400'
            : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'"
        >
          Resolved
        </button>
      </div>

      <!-- Open Items Tab -->
      <div v-if="store.activeTab === 'open'">
        <!-- Empty state -->
        <div v-if="store.openItems.length === 0" class="text-center py-16">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/20 mb-4">
            <svg class="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">All caught up</h3>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">Your agents are working independently. Nice.</p>
        </div>

        <!-- Card feed -->
        <div v-else class="space-y-3">
          <QueueCard
            v-for="item in store.openItems"
            :key="item.id"
            :item="item"
          />
        </div>
      </div>

      <!-- Resolved Items Tab -->
      <div v-if="store.activeTab === 'resolved'">
        <div v-if="store.resolvedItems.length === 0" class="text-center py-16">
          <p class="text-sm text-gray-500 dark:text-gray-400">No resolved items yet</p>
        </div>

        <div v-else class="space-y-2">
          <ResolvedCard
            v-for="item in store.resolvedItems"
            :key="item.id"
            :item="item"
          />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, watch } from 'vue'
import NavBar from '../components/NavBar.vue'
import QueueCard from '../components/operator/QueueCard.vue'
import ResolvedCard from '../components/operator/ResolvedCard.vue'
import { useOperatorQueueStore } from '../stores/operatorQueue'

const store = useOperatorQueueStore()

onMounted(() => {
  store.startPolling(10000) // Poll every 10 seconds
})

onUnmounted(() => {
  store.stopPolling()
})

// Auto-expand first item when items arrive
watch(() => store.openItems.length, (len) => {
  if (len > 0 && !store.expandedItemId) {
    store.toggleExpand(store.openItems[0].id)
  }
})
</script>
