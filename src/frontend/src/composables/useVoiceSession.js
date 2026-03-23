/**
 * Voice session composable for Trinity (VOICE-004).
 *
 * Manages the full lifecycle of a voice conversation:
 * 1. POST /voice/start → get voice_session_id + websocket_url
 * 2. Open WebSocket → stream audio bidirectionally
 * 3. POST /voice/stop or WebSocket close → save transcript
 */

import { ref, computed } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { startMicCapture, createAudioPlayer } from '../utils/audio'

/**
 * @param {string} agentName - The agent to voice-chat with
 */
export function useVoiceSession(agentName) {
  const authStore = useAuthStore()

  // State
  const active = ref(false)
  const status = ref('idle') // idle, connecting, listening, speaking, ended, error
  const muted = ref(false)
  const error = ref(null)
  const voiceSessionId = ref(null)
  const chatSessionId = ref(null)
  const transcriptEntries = ref([]) // [{role, text}]

  // Internal
  let ws = null
  let micCapture = null
  let audioPlayer = null

  const isActive = computed(() => active.value)
  const isConnecting = computed(() => status.value === 'connecting')
  const isSpeaking = computed(() => status.value === 'speaking')
  const isListening = computed(() => status.value === 'listening')

  /**
   * Start a voice session.
   * @param {string|null} sessionId - Existing chat session to continue
   */
  async function start(sessionId = null) {
    if (active.value) return
    error.value = null
    transcriptEntries.value = []
    status.value = 'connecting'
    active.value = true

    try {
      // 1. Initialize session on backend
      const response = await axios.post(
        `/api/agents/${agentName}/voice/start`,
        { session_id: sessionId },
        { headers: authStore.authHeader }
      )

      voiceSessionId.value = response.data.voice_session_id
      chatSessionId.value = response.data.chat_session_id
      const wsPath = response.data.websocket_url

      // 2. Open WebSocket with auth token
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${wsProtocol}//${window.location.host}${wsPath}?token=${authStore.token}`
      ws = new WebSocket(wsUrl)

      ws.onopen = async () => {
        // 3. Start microphone capture
        try {
          audioPlayer = createAudioPlayer()
          micCapture = await startMicCapture((base64Audio) => {
            if (ws && ws.readyState === WebSocket.OPEN && !muted.value) {
              ws.send(JSON.stringify({ type: 'audio', data: base64Audio }))
            }
          })
          status.value = 'listening'
        } catch (micError) {
          error.value = 'Microphone access denied. Please allow microphone access and try again.'
          await stop()
        }
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)

          if (msg.type === 'audio' && msg.data) {
            // Play audio from Gemini
            if (audioPlayer) {
              audioPlayer.play(msg.data)
            }
          } else if (msg.type === 'transcript') {
            // Add transcript entry
            transcriptEntries.value.push({
              role: msg.role,
              text: msg.text,
            })
          } else if (msg.type === 'status') {
            if (msg.state === 'ended') {
              _cleanup()
            } else {
              status.value = msg.state
            }
          }
        } catch (e) {
          console.error('Voice WS message parse error:', e)
        }
      }

      ws.onerror = () => {
        error.value = 'Voice connection error'
        _cleanup()
      }

      ws.onclose = () => {
        _cleanup()
      }

    } catch (err) {
      console.error('Voice start error:', err)
      error.value = err.response?.data?.detail || 'Failed to start voice session'
      _cleanup()
    }
  }

  /**
   * Stop the voice session.
   */
  async function stop() {
    if (!active.value) return

    // Send end signal
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({ type: 'end' }))
      } catch (e) {
        // Ignore
      }
    }

    // Also call the stop endpoint to ensure transcript is saved
    if (voiceSessionId.value) {
      try {
        await axios.post(
          `/api/agents/${agentName}/voice/stop`,
          { voice_session_id: voiceSessionId.value },
          { headers: authStore.authHeader }
        )
      } catch (e) {
        // The WebSocket close handler also saves, so this is a fallback
        console.warn('Voice stop API error (transcript may already be saved):', e)
      }
    }

    _cleanup()
  }

  /**
   * Toggle mute.
   */
  function toggleMute() {
    muted.value = !muted.value
  }

  /**
   * Internal cleanup.
   */
  function _cleanup() {
    active.value = false
    status.value = 'idle'

    if (micCapture) {
      micCapture.stop()
      micCapture = null
    }
    if (audioPlayer) {
      audioPlayer.stop()
      audioPlayer = null
    }
    if (ws) {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close()
      }
      ws = null
    }
  }

  return {
    // State
    active,
    isActive,
    status,
    isConnecting,
    isSpeaking,
    isListening,
    muted,
    error,
    voiceSessionId,
    chatSessionId,
    transcriptEntries,

    // Actions
    start,
    stop,
    toggleMute,
  }
}
