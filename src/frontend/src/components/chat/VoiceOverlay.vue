<template>
  <Transition
    enter-active-class="transition ease-out duration-200"
    enter-from-class="opacity-0 translate-y-4"
    enter-to-class="opacity-100 translate-y-0"
    leave-active-class="transition ease-in duration-150"
    leave-from-class="opacity-100 translate-y-0"
    leave-to-class="opacity-0 translate-y-4"
  >
    <div
      v-if="voice.isActive.value"
      class="absolute inset-0 z-30 flex flex-col items-center justify-center bg-gray-900/95 backdrop-blur-sm rounded-lg"
    >
      <!-- Status indicator -->
      <div class="mb-8 flex flex-col items-center">
        <!-- Pulsing circle -->
        <div class="relative w-28 h-28 mb-4">
          <!-- Outer pulse ring (when listening or speaking) -->
          <div
            v-if="voice.isListening.value || voice.isSpeaking.value"
            :class="[
              'absolute inset-0 rounded-full animate-ping',
              voice.isSpeaking.value ? 'bg-indigo-500/30' : 'bg-green-500/20'
            ]"
            style="animation-duration: 1.5s"
          ></div>

          <!-- Inner circle -->
          <div
            :class="[
              'absolute inset-2 rounded-full flex items-center justify-center transition-colors duration-300',
              statusColor
            ]"
          >
            <!-- Mic icon (listening) -->
            <svg v-if="voice.isListening.value && !voice.muted.value" class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4M12 15a3 3 0 003-3V5a3 3 0 00-6 0v7a3 3 0 003 3z" />
            </svg>

            <!-- Muted icon -->
            <svg v-else-if="voice.muted.value" class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
            </svg>

            <!-- Speaking icon (sound waves) -->
            <svg v-else-if="voice.isSpeaking.value" class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15.536 8.464a5 5 0 010 7.072M18.364 5.636a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
            </svg>

            <!-- Connecting spinner -->
            <svg v-else-if="voice.isConnecting.value" class="w-10 h-10 text-white animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
        </div>

        <!-- Status text -->
        <p class="text-white text-lg font-medium">{{ statusLabel }}</p>
        <p v-if="voice.muted.value" class="text-yellow-400 text-sm mt-1">Microphone muted</p>
      </div>

      <!-- Live transcript -->
      <div
        v-if="voice.transcriptEntries.value.length > 0"
        class="w-full max-w-md max-h-32 overflow-y-auto px-6 mb-6 space-y-1"
      >
        <div
          v-for="(entry, i) in recentTranscript"
          :key="i"
          :class="[
            'text-sm px-3 py-1 rounded-lg',
            entry.role === 'user'
              ? 'text-gray-300 bg-gray-800/50 text-right'
              : 'text-indigo-300 bg-indigo-900/30'
          ]"
        >
          {{ entry.text }}
        </div>
      </div>

      <!-- Error message -->
      <div v-if="voice.error.value" class="mb-4 px-4 py-2 bg-red-900/50 border border-red-700 rounded-lg">
        <p class="text-red-300 text-sm">{{ voice.error.value }}</p>
      </div>

      <!-- Controls -->
      <div class="flex items-center space-x-6">
        <!-- Mute button -->
        <button
          @click="voice.toggleMute()"
          :class="[
            'w-12 h-12 rounded-full flex items-center justify-center transition-colors',
            voice.muted.value
              ? 'bg-yellow-600 hover:bg-yellow-500'
              : 'bg-gray-700 hover:bg-gray-600'
          ]"
          :title="voice.muted.value ? 'Unmute' : 'Mute'"
        >
          <svg v-if="!voice.muted.value" class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4M12 15a3 3 0 003-3V5a3 3 0 00-6 0v7a3 3 0 003 3z" />
          </svg>
          <svg v-else class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
          </svg>
        </button>

        <!-- End call button -->
        <button
          @click="$emit('end')"
          class="w-14 h-14 rounded-full bg-red-600 hover:bg-red-500 flex items-center justify-center transition-colors shadow-lg"
          title="End voice session"
        >
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.279 3H5z" />
          </svg>
        </button>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  voice: {
    type: Object,
    required: true,
  }
})

defineEmits(['end'])

const statusColor = computed(() => {
  switch (props.voice.status.value) {
    case 'connecting': return 'bg-gray-600'
    case 'listening': return 'bg-green-600'
    case 'speaking': return 'bg-indigo-600'
    default: return 'bg-gray-700'
  }
})

const statusLabel = computed(() => {
  if (props.voice.muted.value && props.voice.isListening.value) return 'Muted'
  switch (props.voice.status.value) {
    case 'connecting': return 'Connecting...'
    case 'listening': return 'Listening...'
    case 'speaking': return 'Speaking...'
    default: return 'Voice Chat'
  }
})

// Show last 4 transcript entries
const recentTranscript = computed(() => {
  return props.voice.transcriptEntries.value.slice(-4)
})
</script>
