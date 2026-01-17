<template>
  <div class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 mb-6">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <nav class="-mb-px flex space-x-8">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm transition-colors whitespace-nowrap inline-flex items-center',
            isActive(item.path)
              ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
          ]"
        >
          <component :is="item.icon" class="h-4 w-4 mr-2" />
          {{ item.label }}
        </router-link>
      </nav>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  CpuChipIcon,
  FolderIcon,
  DocumentDuplicateIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()

const navItems = [
  {
    path: '/agents',
    label: 'Agents',
    icon: CpuChipIcon,
  },
  {
    path: '/files',
    label: 'Files',
    icon: FolderIcon,
  },
  {
    path: '/templates',
    label: 'Templates',
    icon: DocumentDuplicateIcon,
  },
]

const isActive = (path) => {
  // Exact match for most routes
  if (route.path === path) return true
  // For agents, also match /agents/:id
  if (path === '/agents' && route.path.startsWith('/agents/')) return true
  return false
}
</script>
