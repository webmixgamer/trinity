<template>
  <div
    :class="[
      'rounded-full overflow-hidden flex-shrink-0 flex items-center justify-center',
      sizeClasses
    ]"
    :style="!showImage ? { background: gradientStyle } : {}"
  >
    <img
      v-if="avatarUrl && showImage"
      :src="avatarUrl"
      :alt="name"
      class="w-full h-full object-cover"
      @error="showImage = false"
    />
    <span
      v-else
      :class="['font-bold text-white select-none', textSizeClass]"
    >{{ initials }}</span>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  name: {
    type: String,
    required: true
  },
  avatarUrl: {
    type: String,
    default: null
  },
  size: {
    type: String,
    default: 'md',
    validator: v => ['sm', 'md', 'lg', 'xl', '2xl'].includes(v)
  }
})

const showImage = ref(!!props.avatarUrl)

watch(() => props.avatarUrl, (newVal) => {
  showImage.value = !!newVal
})

const sizeClasses = computed(() => {
  const map = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16',
    '2xl': 'w-24 h-24'
  }
  return map[props.size]
})

const textSizeClass = computed(() => {
  const map = {
    sm: 'text-[10px]',
    md: 'text-xs',
    lg: 'text-sm',
    xl: 'text-base',
    '2xl': 'text-2xl'
  }
  return map[props.size]
})

const initials = computed(() => {
  const parts = props.name.replace(/[^a-zA-Z0-9\s-]/g, '').split(/[\s-]+/).filter(Boolean)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return (props.name.slice(0, 2)).toUpperCase()
})

// Deterministic gradient from agent name
const gradientStyle = computed(() => {
  let hash = 0
  for (let i = 0; i < props.name.length; i++) {
    hash = props.name.charCodeAt(i) + ((hash << 5) - hash)
  }
  const h1 = Math.abs(hash % 360)
  const h2 = (h1 + 40) % 360
  return `linear-gradient(135deg, hsl(${h1}, 65%, 45%), hsl(${h2}, 65%, 55%))`
})
</script>
