# Feature: Web Terminal for System Agent

## Overview

Browser-based interactive terminal for the System Agent using xterm.js with full Claude Code TUI support. The terminal is embedded directly on the System Agent page with fullscreen capability. Provides admin-only access to the System Agent container via WebSocket-based PTY forwarding.

## User Story

As an **admin**, I want to access an interactive terminal for the System Agent directly from my browser so that I can run Claude Code or bash commands without SSH port exposure.

## Entry Points

- **UI**: `src/frontend/src/views/SystemAgent.vue:300-370` - Embedded terminal panel (admin-only, auto-connects when agent running)
- **API**: `WS /api/system-agent/terminal?mode=claude|bash`

---

## Frontend Layer

### Components

#### SystemAgent.vue (Parent)
- **File**: `src/frontend/src/views/SystemAgent.vue`
- **Terminal Panel**: Lines 300-370 - Embedded terminal with fullscreen support
- **State**:
  - `isFullscreen` ref controls fullscreen mode
  - `terminalRef` ref for calling terminal methods
- **Event Handlers**:
  - `onTerminalConnected()` - Shows success notification
  - `onTerminalDisconnected()` - Shows info notification
  - `onTerminalError()` - Shows error notification
  - `toggleFullscreen()` - Toggles fullscreen mode, refits terminal
  - `handleKeydown()` - ESC key exits fullscreen

```vue
<!-- Terminal Panel (lines 300-370) -->
<div
  :class="[
    'bg-gray-900 rounded-lg shadow overflow-hidden flex flex-col transition-all duration-300',
    isFullscreen
      ? 'fixed inset-0 z-50 rounded-none'
      : 'lg:col-span-2'
  ]"
  :style="isFullscreen ? {} : { height: '500px' }"
>
  <!-- Header with fullscreen toggle -->
  <div class="flex items-center justify-between px-3 py-2 bg-gray-800 border-b border-gray-700">
    <span class="text-sm font-medium text-gray-300">System Terminal</span>
    <button @click="toggleFullscreen" title="Fullscreen (Esc to exit)">
      <!-- Expand/Collapse icon -->
    </button>
  </div>
  <!-- Terminal Content -->
  <div class="flex-1 min-h-0">
    <SystemAgentTerminal v-if="systemAgent?.status === 'running' && isAdmin" ... />
  </div>
</div>
```

**Fullscreen Toggle** (lines 704-720):
```javascript
// Fullscreen toggle
function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
  // Refit terminal after layout change
  nextTick(() => {
    if (terminalRef.value?.fit) {
      terminalRef.value.fit()
    }
  })
}

// ESC key handler for fullscreen
function handleKeydown(event) {
  if (event.key === 'Escape' && isFullscreen.value) {
    toggleFullscreen()
  }
}
```

#### SystemAgentTerminal.vue (Terminal Component)
- **File**: `src/frontend/src/components/SystemAgentTerminal.vue`
- **Props**:
  - `autoConnect: Boolean` (default: true) - Auto-connect on mount
- **Emits**: `connected`, `disconnected`, `error`
- **Exposes**: `connect()`, `disconnect()`, `focus()`, `fit()`

**Key References**:
| Ref | Type | Purpose |
|-----|------|---------|
| `terminalContainer` | HTMLElement | xterm.js mount point |
| `selectedMode` | 'claude' \| 'bash' | Terminal mode |
| `connectionStatus` | 'connected' \| 'connecting' \| 'disconnected' | WebSocket state |
| `errorMessage` | string | Error display |

**Terminal Initialization** (lines 113-188):
```javascript
terminal = new Terminal({
  cursorBlink: true,
  fontSize: 14,
  fontFamily: 'Menlo, Monaco, "Courier New", monospace',
  theme: { /* VS Code dark theme colors */ },
  allowProposedApi: true,
  scrollback: 10000
})

fitAddon = new FitAddon()
terminal.loadAddon(fitAddon)
terminal.loadAddon(new WebLinksAddon())
```

**WebSocket Connection** (lines 191-278):
```javascript
// Build WebSocket URL
const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
const wsUrl = `${protocol}//${location.host}/api/system-agent/terminal?mode=${selectedMode.value}`

ws = new WebSocket(wsUrl)
ws.binaryType = 'arraybuffer'

// First message is JWT auth
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'auth', token }))
}
```

**Message Handling**:
| Message Type | Direction | Content |
|--------------|-----------|---------|
| `auth` | Client -> Server | `{type: "auth", token: "<jwt>"}` |
| `auth_success` | Server -> Client | `{type: "auth_success"}` |
| `error` | Server -> Client | `{type: "error", message: "...", close?: true}` |
| `resize` | Client -> Server | `{type: "resize", cols: 80, rows: 24}` |
| Binary | Both | Raw terminal I/O |

**Resize Handling** (lines 174-188):
```javascript
resizeObserver = new ResizeObserver(() => {
  fitAddon.fit()
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'resize',
      cols: terminal.cols,
      rows: terminal.rows
    }))
  }
})
resizeObserver.observe(terminalContainer.value)
```

### State Management

- **Admin Check**: `src/frontend/src/views/SystemAgent.vue:569`
  ```javascript
  const userRole = ref(null)
  const isAdmin = computed(() => userRole.value === 'admin')
  ```
- **Role Fetch**: `GET /api/users/me` on mount (lines 893-897)

### Dependencies

```json
{
  "@xterm/xterm": "^5.5.0",
  "@xterm/addon-fit": "^0.10.0",
  "@xterm/addon-web-links": "^0.11.0"
}
```

---

## Backend Layer

### WebSocket Endpoint

- **File**: `src/backend/routers/system_agent.py:315-614`
- **Endpoint**: `@router.websocket("/terminal")`
- **Query Params**: `mode: str` (default: "claude") - Either "claude" or "bash"

### Authentication Flow (lines 343-405)

```python
# Step 1: Wait for auth message (10 second timeout)
auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
auth_data = json.loads(auth_msg)

if auth_data.get("type") != "auth":
    # Send error, close connection
    return

token = auth_data.get("token")

# Step 2: Decode and validate JWT
user = decode_token(token)  # From dependencies.py

# Step 3: Check admin role
if user.get("role") != "admin":
    # Send error with code 4003
    return
```

### Token Decoding Helper

- **File**: `src/backend/dependencies.py:72-102`
- **Function**: `decode_token(token: str) -> Optional[dict]`

```python
def decode_token(token: str) -> Optional[dict]:
    """
    Decode JWT without FastAPI dependency.
    Returns: {sub, email, role, exp, mode} or None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user = db.get_user_by_username(username)
        return {
            "sub": username,
            "email": user.get("email"),
            "role": user.get("role"),
            "exp": payload.get("exp"),
            "mode": payload.get("mode")
        }
    except JWTError:
        return None
```

### Session Limiting (lines 407-425)

```python
# Track active sessions (1 per user, 5-minute stale cleanup)
_active_terminal_sessions: dict = {}  # user_id -> session_info
_terminal_lock = threading.Lock()
SESSION_TIMEOUT_SECONDS = 300

with _terminal_lock:
    if user_email in _active_terminal_sessions:
        session_info = _active_terminal_sessions[user_email]
        session_age = (datetime.utcnow() - session_info["started_at"]).total_seconds()
        if session_age < SESSION_TIMEOUT_SECONDS:
            # Reject: existing active session
            return
        else:
            # Clean up stale session
            logger.warning(f"Cleaning up stale session for {user_email}")
    _active_terminal_sessions[user_email] = {"started_at": datetime.utcnow()}
```

### Docker Exec Creation (lines 462-488)

```python
# Build command based on mode
cmd = ["claude"] if mode == "claude" else ["/bin/bash"]

# Create exec instance with TTY
exec_instance = docker_client.api.exec_create(
    container.id,
    cmd,
    stdin=True,
    tty=True,
    stdout=True,
    stderr=True,
    user="developer",
    workdir="/home/developer",
    environment={"TERM": "xterm-256color", "COLORTERM": "truecolor"}
)
exec_id = exec_instance["Id"]

# Start exec and get raw socket
exec_output = docker_client.api.exec_start(exec_id, socket=True, tty=True)
docker_socket = exec_output._sock
docker_socket.setblocking(False)
```

### Bidirectional Forwarding (lines 493-568)

```python
async def read_from_docker():
    """Read from Docker socket, send to WebSocket."""
    while True:
        ready = await loop.run_in_executor(
            None,
            lambda: select.select([docker_socket], [], [], 0.1)
        )
        if ready[0]:
            data = await loop.run_in_executor(
                None,
                lambda: docker_socket.recv(4096)
            )
            if not data:
                break
            await websocket.send_bytes(data)

async def read_from_websocket():
    """Read from WebSocket, send to Docker socket."""
    while True:
        message = await websocket.receive()
        if "text" in message:
            # Check for resize control message
            try:
                ctrl = json.loads(message["text"])
                if ctrl.get("type") == "resize":
                    docker_client.api.exec_resize(
                        exec_id,
                        height=ctrl.get("rows", 24),
                        width=ctrl.get("cols", 80)
                    )
                    continue
            except json.JSONDecodeError:
                pass
            # Plain text input
            docker_socket.sendall(message["text"].encode())
        elif "bytes" in message:
            docker_socket.sendall(message["bytes"])

# Run both concurrently
await asyncio.gather(read_from_docker(), read_from_websocket())
```

---

## Side Effects

### Audit Logging

Session start (line 454-460):
```python
await log_audit_event(
    event_type="terminal_session",
    action="start",
    user_id=user_email,
    agent_name=SYSTEM_AGENT_NAME,
    details={"mode": mode}
)
```

Session end (lines 596-611):
```python
session_duration = (datetime.utcnow() - session_start).total_seconds()

await log_audit_event(
    event_type="terminal_session",
    action="end",
    user_id=user_email,
    agent_name=SYSTEM_AGENT_NAME,
    details={
        "mode": mode,
        "duration_seconds": session_duration
    }
)
```

### Session Cleanup

On disconnect (lines 581-593):
```python
finally:
    if docker_socket:
        docker_socket.close()

    if user_email:
        with _terminal_lock:
            _active_terminal_sessions.pop(user_email, None)
```

---

## Error Handling

| Error Case | WebSocket Code | Message |
|------------|----------------|---------|
| Missing auth message | 4001 | "Expected auth message" |
| Missing token | 4001 | "Token required" |
| Invalid token | 4001 | "Invalid token" |
| Not admin | 4003 | "Admin access required" |
| Auth timeout (10s) | 4001 | "Authentication timeout" |
| Invalid auth JSON | 4001 | "Invalid auth format" |
| Existing session | 4002 | "You already have an active terminal session" |
| Container not found | 4004 | "System agent container not found" |
| Container not running | 4004 | "System agent is not running" |

Frontend error display (line 69-73):
```vue
<div v-if="errorMessage" class="px-4 py-2 bg-red-900/50 ...">
  {{ errorMessage }}
</div>
```

---

## Security Considerations

1. **Admin-Only Access**: Role check happens after JWT validation, before any container interaction
2. **Session Limit**: One terminal per user prevents resource exhaustion
3. **Stale Session Cleanup**: 5-minute timeout prevents orphaned session blocking
4. **No SSH Exposure**: Uses internal Docker network, no port forwarding to host
5. **Audit Trail**: Full session logging with duration tracking
6. **Binary Transport**: Raw PTY data sent as binary WebSocket frames
7. **TERM Environment**: Sets `TERM=xterm-256color` for proper TUI rendering

---

## Data Flow Diagram

```
User Click          WebSocket          Backend           Docker
    |                   |                 |                 |
    | Click Terminal    |                 |                 |
    |------------------>|                 |                 |
    |                   | WS Connect      |                 |
    |                   |---------------->|                 |
    |                   |                 | Accept          |
    |                   |<----------------|                 |
    |                   | Auth Message    |                 |
    |                   |---------------->|                 |
    |                   |                 | decode_token()  |
    |                   |                 | Check admin     |
    |                   |                 | Session limit   |
    |                   |                 |                 |
    |                   |                 | exec_create()   |
    |                   |                 |---------------->|
    |                   |                 | exec_start()    |
    |                   |                 |---------------->|
    |                   |                 |<----------------|
    |                   | auth_success    |                 |
    |                   |<----------------|                 |
    |                   |                 |                 |
    | Type command      |                 |                 |
    |------------------>| Text/Binary     |                 |
    |                   |---------------->|                 |
    |                   |                 | socket.send()   |
    |                   |                 |---------------->|
    |                   |                 |<----------------| Output
    |                   | Binary          |                 |
    |                   |<----------------|                 |
    | xterm.write()     |                 |                 |
    |<------------------|                 |                 |
    |                   |                 |                 |
    | Resize window     |                 |                 |
    |------------------>| resize JSON     |                 |
    |                   |---------------->|                 |
    |                   |                 | exec_resize()   |
    |                   |                 |---------------->|
```

---

## Related Flows

- **Upstream**: [internal-system-agent.md](internal-system-agent.md) - System agent deployment and status
- **Upstream**: [auth0-authentication.md](auth0-authentication.md) - JWT token creation and admin role
- **Related**: [agent-chat.md](agent-chat.md) - Alternative chat interface via HTTP API

---

## Testing

### Prerequisites
- Backend and frontend running
- Admin user logged in
- System agent container running (`trinity-system` status: running)

### Test Steps

1. **Admin Access**
   - Action: Login as admin, navigate to `/system-agent`
   - Expected: Terminal panel visible on right side of page
   - Verify: Terminal auto-connects, shows "Connected!" message

2. **Terminal Auto-Connection**
   - Action: Navigate to `/system-agent` with agent running
   - Expected: Terminal shows "Connecting..." then "Connected!" automatically
   - Verify: Green status dot, connection status text

3. **Fullscreen Toggle**
   - Action: Click the fullscreen button (expand icon) in terminal header
   - Expected: Terminal expands to fill entire viewport
   - Verify: Terminal refits to new size, content preserved

4. **ESC to Exit Fullscreen**
   - Action: Press ESC key while in fullscreen mode
   - Expected: Terminal returns to embedded panel size
   - Verify: Layout returns to normal, terminal refits

5. **Claude Code Mode (Default)**
   - Action: Type `/help` and press Enter
   - Expected: Claude Code help menu displays with colors
   - Verify: Full TUI preserved, colors render correctly

6. **Keyboard Shortcuts**
   - Action: Press Ctrl+C during operation
   - Expected: Operation cancelled, prompt returns
   - Verify: Interrupt signal processed correctly

7. **Terminal Resize**
   - Action: Resize browser window while connected
   - Expected: Terminal content reflows to fit
   - Verify: No content truncation, prompt intact

8. **Bash Mode**
   - Action: Disconnect, switch to Bash mode, reconnect
   - Expected: Bash shell prompt appears
   - Verify: Can run `ls`, `pwd`, `whoami` commands

9. **Session Limit**
   - Action: Open second browser tab, try to connect
   - Expected: Error "You already have an active terminal session"
   - Verify: First session remains connected

10. **Disconnect/Cleanup**
    - Action: Click Disconnect button
    - Expected: Session terminates cleanly
    - Verify: Can reconnect immediately after

### Edge Cases

- **Non-admin User**: Terminal panel shows "Admin access required" message
- **Stopped Agent**: Terminal panel shows "System agent must be running" with Start button
- **Network Interruption**: Terminal shows disconnection, allows reconnect via Connect button
- **Token Expiry**: Auth error displayed, prompt to refresh page
- **Fullscreen in Small Window**: Terminal should still fit properly

### Cleanup
No cleanup required - sessions terminate automatically on disconnect.

### Status
**Testing Status**: Not Tested

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-25 | Embedded terminal directly on page, removed modal - Terminal now auto-connects when agent running |
| 2025-12-25 | Added fullscreen toggle with ESC key to exit |
| 2025-12-25 | Initial implementation (Req 11.5) |
