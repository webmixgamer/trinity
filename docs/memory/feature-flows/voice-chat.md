# Voice Chat — Gemini 2.5 Flash Native Audio

**Status**: 🚧 Phase 1 MVP Implemented
**Date**: 2026-03-23
**Priority**: P1

---

## Problem Statement

Users need a fast, natural way to speak with agents via the browser. Text chat creates friction — typing is slow, reading long responses takes time, and the interaction feels robotic. A voice interface should feel like talking to a person: sub-500ms response time, natural turn-taking, interruption support.

---

## Core Concept

Use **Gemini 2.5 Flash Native Audio** (`gemini-live-2.5-flash-native-audio`) as a real-time voice proxy for the agent. Claude Code remains the agent's brain (generates the system prompt and handles complex tasks), but the voice conversation runs on Gemini's speech-to-speech model for speed (~280ms TTFT).

### Why Not Claude for Voice?

Anthropic has no speech-to-speech or realtime audio API. Any Claude voice pipeline would require STT → Claude text API (~500-800ms TTFT) → TTS, totaling 800ms-1.3s. Gemini's native audio model handles audio in/out natively with ~280ms latency and built-in turn-taking, barge-in, and emotion.

### Why Gemini 2.5 Flash Native Audio?

- Native speech-to-speech (no STT/TTS pipeline)
- ~280ms time-to-first-token
- 30 HD voices, 24 languages
- Supports custom system prompts
- Affective dialog (responds to user's tone)
- Function calling mid-conversation
- GA on Vertex AI
- WebSocket-based Live API

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (Agent Detail)                │
│                                                         │
│  ┌──────────────┐    ┌───────────────────────────────┐  │
│  │  Chat Panel  │    │   Voice Overlay / Panel       │  │
│  │  (existing)  │    │                               │  │
│  │              │    │  [Waveform / Speaking Status]  │  │
│  │  ... msgs    │    │  [Mute] [End Call]             │  │
│  │              │    │                               │  │
│  └──────────────┘    └──────────┬────────────────────┘  │
│                                 │                        │
│                        WebSocket (audio frames)          │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Trinity Backend     │
              │                       │
              │  /api/agents/{name}/  │
              │    voice/start        │
              │    voice/stop         │
              │                       │
              │  WebSocket proxy:     │
              │  Browser ↔ Gemini     │
              │  Live API             │
              │                       │
              │  On session end:      │
              │  - Extract transcript │
              │  - Save to ChatMessage│
              │  - Update ChatSession │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  Gemini Live API      │
              │  (Vertex AI)          │
              │                       │
              │  Model:               │
              │  gemini-live-2.5-     │
              │  flash-native-audio   │
              │                       │
              │  System prompt:       │
              │  agent personality +  │
              │  conversation summary │
              └───────────────────────┘
```

---

## User Flow

### Starting a Voice Session

1. User is on Agent Detail page, Chat tab (authenticated)
2. User clicks **"Talk"** button (microphone icon) next to the chat input
3. Backend receives `POST /api/agents/{name}/voice/start`
4. Backend prepares the voice session:
   a. Loads the agent's **voice system prompt** (pre-created, stored as agent config)
   b. Fetches recent chat history for this session
   c. Summarizes the conversation so far into a concise context block
   d. Combines: `voice_system_prompt + "\n\n## Conversation so far:\n" + summary`
5. Backend opens a WebSocket connection to Gemini Live API with the combined prompt
6. Backend establishes a WebSocket bridge: browser ↔ backend ↔ Gemini
7. Browser captures microphone audio via `getUserMedia()` and streams to backend
8. Gemini responds with audio frames streamed back to the browser
9. Voice overlay appears with speaking indicators

### During the Voice Session

- User speaks naturally; Gemini responds in real-time
- Gemini uses the agent's personality from the system prompt
- Gemini has context of the prior text conversation via the summary
- User can interrupt (barge-in) at any time
- Backend accumulates the transcript (Gemini provides text alongside audio)

### Ending a Voice Session

1. User clicks **"End"** button, or closes the overlay
2. Backend sends session close to Gemini Live API
3. Backend extracts the full transcript from the session
4. Transcript is saved as ChatMessage entries in the existing chat session:
   - Each user utterance → `ChatMessage(role="user", content=text)`
   - Each agent response → `ChatMessage(role="assistant", content=text)`
   - Messages tagged with `source="voice"` for UI differentiation
5. Chat panel refreshes and shows the voice conversation inline with text messages
6. User can continue the conversation via text or start another voice session

### Picking Up Context

When starting a new voice session mid-conversation:
- The summary includes ALL prior messages (both text and previous voice transcripts)
- This means the voice agent knows what was discussed in text AND in previous voice sessions
- Seamless continuity between modalities

---

## Requirements

### VOICE-001: Voice Session Initialization

**Status**: 🚧 Phase 1 Implemented

| Requirement | Detail |
|-------------|--------|
| Backend endpoint | `POST /api/agents/{name}/voice/start` → returns WebSocket URL |
| System prompt source | Agent config field: `voice_system_prompt` (pre-created by agent owner) |
| Context injection | Summarize last N messages of current chat session (truncate to fit Gemini context) |
| Gemini connection | Open WebSocket to `generativelanguage.googleapis.com` Live API |
| Authentication | Vertex AI service account or Gemini API key (platform-level config) |
| Audio format | PCM 16-bit, 16kHz mono (Gemini Live API default) |

### VOICE-002: Audio Streaming Bridge

**Status**: ⏳ Not Started

| Requirement | Detail |
|-------------|--------|
| Browser → Backend | WebSocket carrying raw audio frames from `getUserMedia()` |
| Backend → Gemini | Forward audio frames to Gemini Live API WebSocket |
| Gemini → Backend | Receive audio response frames + transcript text |
| Backend → Browser | Forward audio frames for playback via `AudioContext` |
| Latency target | < 100ms added by the proxy layer |
| Concurrency | One active voice session per user per agent |

### VOICE-003: Transcript Persistence

**Status**: ⏳ Not Started

| Requirement | Detail |
|-------------|--------|
| Transcript extraction | Capture text from Gemini's `serverContent` messages (text alongside audio) |
| Storage | Save as `ChatMessage` rows in existing `chat_messages` table |
| Message metadata | `source` field = `"voice"` to distinguish from text messages |
| Session linkage | Messages belong to the user's current `ChatSession` |
| Timing | Save on session end (batch) AND incrementally during session |
| Cost tracking | Track Gemini API cost per voice session |

### VOICE-004: Frontend Voice UI

**Status**: ⏳ Not Started

| Requirement | Detail |
|-------------|--------|
| Trigger | Microphone icon button next to chat input textarea |
| Voice overlay | Appears over/beside chat panel when voice is active |
| Visual feedback | Waveform or pulsing indicator showing who is speaking |
| Controls | Mute mic toggle, End call button |
| Browser API | `navigator.mediaDevices.getUserMedia({ audio: true })` |
| Audio playback | `AudioContext` + `AudioWorklet` for low-latency playback |
| Permission | Request mic permission on first click, show clear prompt |
| Mobile | Must work on mobile browsers (Safari, Chrome) |

### VOICE-005: Voice System Prompt

**Status**: ⏳ Not Started

| Requirement | Detail |
|-------------|--------|
| Storage | New field on agent: `voice_system_prompt` (text, nullable) |
| Creation | Agent owner writes it manually OR generates from agent's main CLAUDE.md |
| Content | Concise personality description, conversation style, voice-specific instructions |
| Voice-specific rules | E.g., "Keep responses under 2 sentences", "Use casual language", "Don't use markdown" |
| Fallback | If no voice prompt set, derive a basic one from agent name + description |

### VOICE-006: Conversation Summary for Context

**Status**: ⏳ Not Started

| Requirement | Detail |
|-------------|--------|
| Trigger | On voice session start |
| Input | All ChatMessage rows for current session (text + prior voice transcripts) |
| Method | Call Claude (fast model, e.g., Haiku) to summarize OR simple truncation of last N messages |
| Output | Concise summary (< 2000 tokens) injected into Gemini system prompt |
| Fallback | If no prior messages, just use the voice system prompt alone |

---

## API Design

### POST /api/agents/{name}/voice/start

**Request:**
```json
{
  "session_id": "optional - existing chat session to continue"
}
```

**Response:**
```json
{
  "voice_session_id": "vs_abc123",
  "websocket_url": "wss://localhost:8000/ws/voice/vs_abc123",
  "chat_session_id": "cs_xyz789"
}
```

### WebSocket /ws/voice/{voice_session_id}

**Client → Server frames:**
```json
{
  "type": "audio",
  "data": "<base64 PCM audio>"
}
```

**Server → Client frames:**
```json
{
  "type": "audio",
  "data": "<base64 PCM audio>"
}
```
```json
{
  "type": "transcript",
  "role": "user|assistant",
  "text": "what the user/agent said"
}
```
```json
{
  "type": "status",
  "state": "listening|speaking|processing"
}
```

### POST /api/agents/{name}/voice/stop

**Request:**
```json
{
  "voice_session_id": "vs_abc123"
}
```

**Response:**
```json
{
  "transcript": [...],
  "messages_saved": 12,
  "duration_seconds": 45,
  "cost": 0.003
}
```

---

## Configuration

### Platform-Level (Settings)

| Setting | Description |
|---------|-------------|
| `GEMINI_API_KEY` | API key for Gemini Live API (or Vertex AI service account) |
| `VOICE_ENABLED` | Global toggle to enable/disable voice feature |
| `VOICE_MODEL` | Model ID (default: `gemini-2.5-flash-native-audio-preview-12-2025`) |
| `VOICE_MAX_DURATION` | Max voice session duration in seconds (default: 300) |

### Per-Agent

| Setting | Description |
|---------|-------------|
| `voice_system_prompt` | Agent-specific voice personality prompt |
| `voice_enabled` | Per-agent toggle (default: true if platform voice is enabled) |
| `voice_name` | Gemini voice selection (from 30 HD voices) |

---

## Scope & Phasing

### Phase 1: MVP (This Implementation)

- Authenticated chat only (not public links)
- Single agent at a time
- Basic voice overlay UI (no waveform, just status indicators)
- Transcript saved on session end (not incremental)
- Manual voice system prompt (agent owner writes it)
- Gemini API key in platform settings

### Phase 2: Polish

- Real-time waveform visualization
- Incremental transcript display in chat during voice session
- Auto-generate voice prompt from agent's CLAUDE.md
- Voice quality/latency metrics
- Public link voice support

### Phase 3: Advanced

- Function calling (Gemini calls Trinity MCP tools mid-voice-session)
- Multi-language voice with auto-detection
- Voice cloning / custom voice per agent
- Voice-to-voice agent-to-agent communication

---

## Dependencies

| Dependency | Purpose | Status |
|------------|---------|--------|
| Gemini API key | Access to Live API | Need to configure |
| `google-genai` Python SDK | Server-side Gemini Live API client | Need to install |
| Browser `getUserMedia` | Microphone access | Available in all modern browsers |
| Browser `AudioContext` | Audio playback | Available in all modern browsers |
| Existing ChatPanel.vue | Integration point for voice button | ✅ Exists |
| Existing ChatMessage model | Storage for transcripts | ✅ Exists |
| Existing ChatSession model | Session tracking | ✅ Exists |

---

## Key Implementation Files (Planned)

| Layer | File | Purpose |
|-------|------|---------|
| **Backend** | `src/backend/routers/voice.py` | Voice API endpoints + WebSocket handler |
| **Backend** | `src/backend/services/gemini_voice.py` | Gemini Live API client wrapper |
| **Frontend** | `src/frontend/src/components/chat/VoiceOverlay.vue` | Voice session UI overlay |
| **Frontend** | `src/frontend/src/composables/useVoiceSession.js` | Voice session state management |
| **Frontend** | `src/frontend/src/utils/audio.js` | Audio capture and playback utilities |

---

## Related Documentation

- [Authenticated Chat Tab](./authenticated-chat-tab.md) — Existing chat implementation
- [Persistent Chat Tracking](./persistent-chat-tracking.md) — Message storage
- [Gemini Runtime](./gemini-runtime.md) — Existing Gemini integration
- [Gemini Live API Docs](https://ai.google.dev/gemini-api/docs/live-api) — Official API reference
- [Gemini Live API Capabilities](https://ai.google.dev/gemini-api/docs/live-api/capabilities) — Audio features
