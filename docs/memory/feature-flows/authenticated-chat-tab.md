# Feature: Authenticated Chat Tab (CHAT-001)

## Overview

A dedicated **Chat** tab in the Agent Detail page that provides a simple, clean chat interface for authenticated users. This complements the Terminal tab (which provides full Claude Code TUI access) with a simpler chat experience that tracks all activity in the Dashboard timeline.

**Spec**: `docs/requirements/AUTHENTICATED_CHAT_TAB.md`

## User Story

As an authenticated user, I want a simple chat interface with my agents that:
- Has a clean, modern UI (like PublicChat)
- Supports multi-turn conversations with session persistence
- Lets me switch between past sessions
- Shows all activity in the Dashboard (unlike Terminal which is TUI-only)
- Works consistently with how public links work

## Entry Points

- **UI**: `src/frontend/src/views/AgentDetail.vue:498` - Chat tab in tab list (`{ id: 'chat', label: 'Chat' }`)
- **UI**: `src/frontend/src/views/AgentDetail.vue:95-96` - Chat tab content rendering
- **Component**: `src/frontend/src/components/ChatPanel.vue` (363 lines) - Main authenticated chat panel

## Frontend Layer

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `ChatPanel.vue` | `components/ChatPanel.vue` (363 lines) | Main authenticated chat panel with session selector |
| `ChatMessages.vue` | `components/chat/ChatMessages.vue` (87 lines) | Shared message list with bottom-aligned layout |
| `ChatInput.vue` | `components/chat/ChatInput.vue` (83 lines) | Shared input with auto-resize textarea |
| `ChatBubble.vue` | `components/chat/ChatBubble.vue` (56 lines) | Shared message bubble with markdown rendering |
| `ChatLoadingIndicator.vue` | `components/chat/ChatLoadingIndicator.vue` (36 lines) | Bouncing dots "Thinking..." indicator |

### ChatPanel Features

1. **Session Selector** (lines 7-55)
   - Dropdown showing current session date/time
   - List of past sessions with message counts
   - Click to switch sessions and load history

2. **New Chat Button** (lines 59-68)
   - Creates fresh session
   - Clears messages

3. **Agent Not Running State** (lines 72-84)
   - Yellow warning icon
   - Message: "Start the agent to begin chatting."

4. **Message Display** (lines 89-109)
   - Uses shared `ChatMessages` component
   - User messages: indigo bubbles (right-aligned)
   - Assistant messages: white/gray with markdown (left-aligned)
   - Bottom-aligned (iMessage style)
   - Custom empty slot for welcome message

5. **Input Area** (lines 117-124)
   - Uses shared `ChatInput` component
   - Auto-resize textarea
   - Send on Enter or button click

### State Management

```javascript
// ChatPanel.vue state (lines 148-160)
const message = ref('')              // Current input
const messages = ref([])             // Current conversation
const loading = ref(false)           // Send in progress
const error = ref(null)              // Error message

// Sessions
const sessions = ref([])             // List of user's sessions
const sessionsLoading = ref(false)   // Loading sessions
const currentSessionId = ref(null)   // Active session
const showSessionDropdown = ref(false)
```

### ChatPanel.vue Methods

| Method | Line | Description |
|--------|------|-------------|
| `formatSessionDate()` | 173 | Format timestamp as relative time ("2h ago") |
| `loadSessions()` | 196 | Fetch user's chat sessions for this agent |
| `selectSession()` | 219 | Select a session and load its messages |
| `startNewChat()` | 249 | Clear current session, start fresh conversation |
| `buildContextPrompt()` | 257 | Build conversation context from last 20 messages |
| `sendMessage()` | 277 | Send message via `/task` endpoint |

### API Calls

```javascript
// List sessions (line 199)
await axios.get(`/api/agents/${agentName}/chat/sessions`, { headers: authStore.authHeader })

// Get session details with messages (line 231)
await axios.get(`/api/agents/${agentName}/chat/sessions/${sessionId}`, { headers: authStore.authHeader })

// Send message (via task endpoint for Dashboard tracking + session persistence) (line 302)
await axios.post(`/api/agents/${agentName}/task`, {
  message: contextPrompt,          // Full message with conversation context
  save_to_session: true,           // Persist to chat_sessions table
  user_message: userMessage,       // Original message (for session display)
  create_new_session: !sessionId   // Create new session if none active
}, { headers: authStore.authHeader })
```

## Backend Layer

### Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET /api/agents/{name}/chat/sessions` | List user's chat sessions |
| `GET /api/agents/{name}/chat/sessions/{id}` | Get session with messages |
| `POST /api/agents/{name}/task` | Send message (headless execution) |

### Why `/task` not `/chat`?

- `/task` uses headless execution - activities tracked in Dashboard timeline
- `/chat` uses `--continue` flag but doesn't track well in Dashboard
- For Chat tab, we want visibility in Dashboard like Tasks tab

### Context Building

Since `/task` is stateless, ChatPanel builds conversation context:

```javascript
const buildContextPrompt = (userMessage) => {
  if (messages.value.length === 0) return userMessage

  let context = '### Previous conversation:\n\n'
  for (const msg of messages.value.slice(-20)) {
    const role = msg.role === 'user' ? 'User' : 'Assistant'
    context += `${role}: ${msg.content}\n\n`
  }
  context += `### Current message:\n\nUser: ${userMessage}`
  return context
}
```

## Data Flow

```
User types message
    │
    ▼
ChatPanel prepends session history to message
    │
    ▼
POST /api/agents/{name}/task (with save_to_session=true)
    │
    ├─► schedule_executions table (execution record)
    ├─► agent_activities table (Dashboard tracking)
    ├─► chat_sessions table (session created/updated)
    ├─► chat_messages table (user + assistant messages)
    └─► Agent container executes headless
            │
            ▼
        Response returned (with chat_session_id)
            │
            ▼
ChatPanel sets currentSessionId, adds to local messages
    │
    ├─► Session appears in dropdown (survives page refresh)
    └─► Dashboard shows activity in timeline
```

### Session Persistence Parameters

| Parameter | Type | Purpose |
|-----------|------|---------|
| `save_to_session` | bool | When true, persist to `chat_sessions` + `chat_messages` tables |
| `user_message` | string | Original user message (without context prefix) for clean display |
| `create_new_session` | bool | When true, close existing active sessions and create new one |

## Shared Components

The following components are shared between ChatPanel and PublicChat:

```
src/frontend/src/components/chat/
├── index.js                  # Export barrel (5 lines)
├── ChatBubble.vue            # Message bubble with markdown (56 lines)
├── ChatInput.vue             # Auto-resize textarea + send button (83 lines)
├── ChatMessages.vue          # Message list with auto-scroll (87 lines)
└── ChatLoadingIndicator.vue  # "Thinking..." indicator (36 lines)
```

### Component Details

**ChatBubble.vue**
- User messages: indigo background, white text, right-aligned (`bg-indigo-600 text-white ml-auto`)
- Assistant messages: white/gray background, markdown rendered via `marked` library
- Links open in new tab with `target="_blank"`

**ChatMessages.vue**
- Bottom-aligned layout using flexbox spacer technique (line 4: `<div class="flex-1"></div>`)
- Auto-scroll on new messages via `watch` on `messages.length`
- Exposes `scrollToBottom()` method for parent components
- Named slot `#empty` for custom empty state

**ChatInput.vue**
- Auto-resize textarea with max height of 150px
- Enter to submit, supports v-model
- Send button disabled when empty or loading
- Exposes `focus()` method

**ChatLoadingIndicator.vue**
- Three bouncing dots with staggered animation delays
- Customizable text via `text` prop (default: "Thinking...")

## Tab Position

Chat tab appears after Tasks in the tab navigation:

```
Tasks | Chat | Dashboard | Schedules | Credentials | Skills | ...
```

## Differences from Terminal Tab

| Aspect | Chat Tab | Terminal Tab |
|--------|----------|--------------|
| Interface | Simple bubbles | Full TUI (xterm.js) |
| Execution | Headless (`/task`) | Interactive (PTY) |
| Dashboard | ✅ Shows in timeline | ❌ Not tracked |
| Session | Switchable, persistent | Single stream |
| Model | Sonnet (default) | Per-session |
| Power | Basic chat | Full Claude Code |

## Differences from Public Chat

| Aspect | Chat Tab | Public Chat |
|--------|----------|-------------|
| Auth | JWT token | Public link token |
| API | `/api/agents/...` | `/api/public/...` |
| Sessions | Full session list | Single session per link |
| Features | Session switching | Basic only |
| Components | **SHARED** | **SHARED** |

## Testing

### Prerequisites
- Backend running at http://localhost:8000
- Frontend running at http://localhost
- Agent running

### Test Cases

1. **Basic Chat**
   - Navigate to agent detail, click Chat tab
   - Send a message
   - Verify response appears
   - Verify activity in Dashboard timeline

2. **Session Management**
   - Send multiple messages
   - Click session dropdown
   - Verify session appears in list
   - Click New Chat
   - Verify messages cleared

3. **Session Switching**
   - Create messages in one session
   - Start new chat, send messages
   - Switch back to first session
   - Verify history loads correctly

4. **Agent Not Running**
   - Stop agent
   - Navigate to Chat tab
   - Verify "Agent Not Running" message displayed

5. **Component Sharing**
   - Test public chat link
   - Verify same styling as Chat tab

## Files

### Created
- `src/frontend/src/components/chat/ChatBubble.vue`
- `src/frontend/src/components/chat/ChatInput.vue`
- `src/frontend/src/components/chat/ChatMessages.vue`
- `src/frontend/src/components/chat/ChatLoadingIndicator.vue`
- `src/frontend/src/components/chat/index.js`
- `src/frontend/src/components/ChatPanel.vue`

### Modified
- `src/frontend/src/views/AgentDetail.vue` - Added Chat tab
- `src/frontend/src/views/PublicChat.vue` - Refactored to use shared components

## Related Flows

- **[parallel-headless-execution.md](parallel-headless-execution.md)** - Core `/task` endpoint with `save_to_session` parameter documentation
- **[tasks-tab.md](tasks-tab.md)** - Similar headless execution pattern (same `/task` endpoint)
- **[public-agent-links.md](public-agent-links.md)** - Public chat (shares components)
- **[persistent-chat-tracking.md](persistent-chat-tracking.md)** - Session API documentation (`chat_sessions`, `chat_messages` tables)
- **[execution-queue.md](execution-queue.md)** - Task execution flow

## Revision History

| Date | Change |
|------|--------|
| 2026-02-20 | Fixed session persistence - `/task` now saves to `chat_sessions` when `save_to_session=true`. Added `create_new_session` for "New Chat" button. |
| 2026-02-19 | Initial implementation (CHAT-001) |
