/**
 * Audio utilities for voice chat (VOICE-004).
 *
 * Handles microphone capture (PCM 16kHz mono) and audio playback (PCM 24kHz mono)
 * using the Web Audio API.
 */

const INPUT_SAMPLE_RATE = 16000
const OUTPUT_SAMPLE_RATE = 24000

/**
 * Start capturing audio from the microphone.
 * Returns raw PCM 16-bit LE chunks via the onData callback.
 *
 * @param {Function} onData - Called with base64-encoded PCM chunks
 * @returns {{ stop: Function }} Control object
 */
export async function startMicCapture(onData) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      sampleRate: INPUT_SAMPLE_RATE,
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    }
  })

  const audioContext = new AudioContext({ sampleRate: INPUT_SAMPLE_RATE })
  const source = audioContext.createMediaStreamSource(stream)

  // Use ScriptProcessorNode for broad compatibility (AudioWorklet is better but
  // requires a separate file and HTTPS for some browsers)
  const bufferSize = 4096
  const processor = audioContext.createScriptProcessor(bufferSize, 1, 1)

  processor.onaudioprocess = (event) => {
    const float32 = event.inputBuffer.getChannelData(0)
    const pcm16 = float32ToPcm16(float32)
    const base64 = arrayBufferToBase64(pcm16.buffer)
    onData(base64)
  }

  source.connect(processor)
  processor.connect(audioContext.destination) // Required for ScriptProcessor to work

  return {
    stop() {
      processor.disconnect()
      source.disconnect()
      audioContext.close()
      stream.getTracks().forEach(t => t.stop())
    }
  }
}

/**
 * Create an audio player for PCM 24kHz mono output.
 *
 * @returns {{ play: Function, stop: Function }}
 */
export function createAudioPlayer() {
  let audioContext = null
  let nextStartTime = 0

  function ensureContext() {
    if (!audioContext || audioContext.state === 'closed') {
      audioContext = new AudioContext({ sampleRate: OUTPUT_SAMPLE_RATE })
      nextStartTime = 0
    }
    // Resume if suspended (autoplay policy)
    if (audioContext.state === 'suspended') {
      audioContext.resume()
    }
    return audioContext
  }

  return {
    /**
     * Queue a PCM audio chunk for playback.
     * @param {string} base64Data - Base64-encoded PCM 16-bit LE audio
     */
    play(base64Data) {
      const ctx = ensureContext()
      const pcmBytes = base64ToArrayBuffer(base64Data)
      const float32 = pcm16ToFloat32(new Int16Array(pcmBytes))

      const buffer = ctx.createBuffer(1, float32.length, OUTPUT_SAMPLE_RATE)
      buffer.getChannelData(0).set(float32)

      const source = ctx.createBufferSource()
      source.buffer = buffer

      source.connect(ctx.destination)

      // Schedule seamlessly after the last chunk
      const now = ctx.currentTime
      if (nextStartTime < now) {
        nextStartTime = now
      }
      source.start(nextStartTime)
      nextStartTime += buffer.duration
    },

    /**
     * Stop playback and reset.
     */
    stop() {
      if (audioContext) {
        audioContext.close().catch(() => {})
        audioContext = null
        nextStartTime = 0
      }
    }
  }
}

// ── Conversion helpers ──────────────────────────────────────────────────────

/** Convert Float32Array [-1, 1] to Int16Array PCM */
function float32ToPcm16(float32) {
  const pcm16 = new Int16Array(float32.length)
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]))
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
  }
  return pcm16
}

/** Convert Int16Array PCM to Float32Array [-1, 1] */
function pcm16ToFloat32(int16) {
  const float32 = new Float32Array(int16.length)
  for (let i = 0; i < int16.length; i++) {
    float32[i] = int16[i] / (int16[i] < 0 ? 0x8000 : 0x7FFF)
  }
  return float32
}

/** Convert ArrayBuffer to base64 string */
function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

/** Convert base64 string to ArrayBuffer */
function base64ToArrayBuffer(base64) {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}
