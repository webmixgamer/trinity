# Channel Transport Architecture — Design Notes

**Date**: 2026-03-20
**Context**: Discussion during #63/#64 implementation planning
**Status**: Decision needed before implementation

---

## The Problem

Every messaging channel has two transport modes:

| Channel | Outbound (Trinity connects out) | Inbound (Service pushes to Trinity) |
|---------|--------------------------------|-------------------------------------|
| **Slack** | Socket Mode (WebSocket) | HTTP webhooks (Events API) |
| **Telegram** | Long polling (`getUpdates`) | HTTP webhooks |
| **Discord** | Gateway (WebSocket) | HTTP interactions |
| **WhatsApp** | — | HTTP webhooks |

The current Slack implementation only supports HTTP webhooks, which requires a public URL (ngrok/Tailscale/production domain). This is painful for local dev and was never a deliberate design choice.

**Outbound transports are universally easier for development** — no public URL, no tunnel, no firewall config. Production can optionally use webhooks for scale, but Trinity's volume doesn't require it.

---

## Proposed Architecture

### Layer Separation

```
┌─────────────────────────────────────────────────────────┐
│                    Channel Transports                     │
│  (how events arrive — one per channel per mode)          │
│                                                           │
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │ SlackSocketMode   │  │ SlackWebhook                 │ │
│  │ (WebSocket out)   │  │ (HTTP POST in)               │ │
│  └────────┬──────────┘  └────────────┬─────────────────┘ │
│           │                          │                    │
│           └──────────┬───────────────┘                    │
│                      ▼                                    │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              raw Slack event dict                     │ │
│  └──────────────────────┬───────────────────────────────┘ │
├─────────────────────────┼─────────────────────────────────┤
│                         ▼                                  │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              SlackAdapter                             │ │
│  │  parse_message(event) → NormalizedMessage            │ │
│  │  send_response(channel, response) → Slack API        │ │
│  │  handle_verification(message) → state machine        │ │
│  │  get_agent_name(message) → agent lookup              │ │
│  └──────────────────────┬───────────────────────────────┘ │
│                         ▼                                  │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              ChannelMessageRouter                     │ │
│  │  resolve agent → build context → execute → respond   │ │
│  │  (channel-agnostic, shared across all channels)      │ │
│  └──────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

**Key insight**: The transport only determines how raw events arrive. Once you have the raw event dict, everything downstream (parsing, routing, responding) is identical regardless of transport.

### What Each Layer Owns

**Transport** (per-channel, per-mode):
- Connecting/listening for events
- Authentication specific to that mode (HMAC signatures for webhooks, token for Socket Mode)
- Passing raw event dicts to the adapter
- Lifecycle (start, stop, reconnect)

**Adapter** (per-channel, transport-agnostic):
- `parse_message(raw_event)` → `NormalizedMessage`
- `send_response(channel_id, response)` → channel API call
- `handle_verification(message)` → channel-specific verification flow
- `get_agent_name(message)` → resolve which agent handles this
- `resolve_user(message)` → map channel user to Trinity identity

**MessageRouter** (shared, channel-agnostic):
- Get/create session
- Build context prompt
- Execute agent task (via TaskExecutionService)
- Persist messages
- Return response to adapter

---

## Slack Socket Mode — What's Needed

### How It Works

1. Trinity creates a `SocketModeClient` with an **App-Level Token** (`xapp-...`)
2. Client connects outbound to Slack via WebSocket
3. Slack pushes events through the WebSocket
4. Events have the same structure as webhook events (`event_callback`, `message.im`, etc.)
5. Client acknowledges each event (built into SDK)

### Requirements

**New dependency**: `slack_sdk` (specifically `slack_sdk[socket-mode]`)
- Provides `SocketModeClient` for WebSocket connection
- Also provides `WebClient` for API calls (replaces our raw httpx calls to Slack API)
- Well-maintained, official Slack SDK

**New credential**: App-Level Token (`xapp-...`)
- Generated in Slack App → Basic Information → App-Level Tokens
- Needs `connections:write` scope
- Stored in Settings DB (like signing_secret today)

**Slack App change**: Enable Socket Mode in the app settings
- Event Subscriptions still needed (subscribe to `message.im`)
- But no Request URL needed

### What DOESN'T Change

- OAuth flow (still needed to get bot token for sending messages)
- `chat.postMessage` for responses (same API)
- Verification flow (same state machine)
- Session management (same `public_chat_sessions`)
- All adapter logic (parsing events, formatting responses)

---

## Settings & Configuration

### New Settings (via Settings UI + DB)

| Setting | Value | Required For |
|---------|-------|-------------|
| `slack_transport_mode` | `"socket"` or `"webhook"` | Both (determines which transport runs) |
| `slack_app_token` | `xapp-...` | Socket Mode only |
| `slack_signing_secret` | `7d2b...` | Webhook mode only |
| `slack_client_id` | `6723...` | Both (OAuth) |
| `slack_client_secret` | `c115...` | Both (OAuth) |

### Decision Logic

```python
transport_mode = get_setting("slack_transport_mode", default="socket")

if transport_mode == "socket":
    # Need: slack_app_token + client_id + client_secret
    # Don't need: signing_secret, PUBLIC_CHAT_URL
    transport = SlackSocketTransport(app_token=get_setting("slack_app_token"))

elif transport_mode == "webhook":
    # Need: signing_secret + client_id + client_secret + PUBLIC_CHAT_URL
    # Don't need: slack_app_token
    transport = SlackWebhookTransport(signing_secret=get_setting("slack_signing_secret"))
```

### Default: Socket Mode

Socket Mode should be the default because:
- No public URL needed (works immediately for local dev)
- No signature verification complexity
- No 3-second webhook timeout concern
- Simpler Slack App setup

Webhook mode is available for production deployments that prefer it (higher throughput, no persistent connection).

---

## Implementation Plan

### Transport Base Class

```python
# adapters/transports/base.py

class ChannelTransport(ABC):
    """Handles how events arrive from a channel."""

    def __init__(self, adapter: ChannelAdapter, router: ChannelMessageRouter):
        self.adapter = adapter
        self.router = router

    @abstractmethod
    async def start(self) -> None:
        """Start listening for events."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop listening, cleanup connections."""

    async def on_event(self, raw_event: dict) -> None:
        """Called when a raw event arrives (from any transport mode)."""
        message = self.adapter.parse_message(raw_event)
        if message:
            await self.router.handle_message(self.adapter, message)
```

### Slack Socket Transport

```python
# adapters/transports/slack_socket.py

from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

class SlackSocketTransport(ChannelTransport):
    """Slack Socket Mode — outbound WebSocket connection."""

    def __init__(self, app_token: str, adapter, router):
        super().__init__(adapter, router)
        self.client = SocketModeClient(app_token=app_token)

    async def start(self):
        self.client.socket_mode_request_listeners.append(self._handle_request)
        await self.client.connect()
        logger.info("Slack Socket Mode connected")

    async def stop(self):
        await self.client.disconnect()

    async def _handle_request(self, client: SocketModeClient, req: SocketModeRequest):
        # Acknowledge immediately (no 3-second timeout!)
        response = SocketModeResponse(envelope_id=req.envelope_id)
        await client.send_socket_mode_response(response)

        # Process the event
        if req.type == "events_api":
            await self.on_event(req.payload)
```

### Slack Webhook Transport

```python
# adapters/transports/slack_webhook.py

class SlackWebhookTransport(ChannelTransport):
    """Slack HTTP webhooks — inbound POST from Slack."""

    def __init__(self, signing_secret: str, adapter, router):
        super().__init__(adapter, router)
        self.signing_secret = signing_secret

    async def start(self):
        # No-op: webhook transport is passive (FastAPI endpoint handles requests)
        logger.info("Slack webhook transport ready")

    async def stop(self):
        pass

    async def handle_http_request(self, request: Request) -> dict:
        """Called by the FastAPI endpoint."""
        body = await request.body()

        # Verify signature
        if not self._verify_signature(request, body):
            return {"ok": False}

        event_data = json.loads(body)

        # Handle URL verification challenge
        if event_data.get("type") == "url_verification":
            return {"ok": True, "challenge": event_data.get("challenge")}

        # Process async
        asyncio.create_task(self.on_event(event_data))
        return {"ok": True}
```

### FastAPI Router (thin)

```python
# routers/slack.py — stays thin

@public_router.post("/events")
async def handle_slack_event(request: Request):
    """Receive Slack webhook events. Only used in webhook transport mode."""
    transport = get_slack_transport()
    if isinstance(transport, SlackWebhookTransport):
        result = await transport.handle_http_request(request)
        return SlackEventResponse(**result)
    return SlackEventResponse(ok=False)  # Socket mode doesn't use this endpoint
```

### Startup Wiring

```python
# In main.py or a dedicated startup module

async def start_channel_transports():
    """Start configured channel transports on app startup."""
    mode = get_setting("slack_transport_mode", "socket")

    if mode == "socket":
        app_token = get_setting("slack_app_token")
        if app_token:
            transport = SlackSocketTransport(app_token, slack_adapter, message_router)
            await transport.start()
    elif mode == "webhook":
        signing_secret = get_slack_signing_secret()
        if signing_secret:
            transport = SlackWebhookTransport(signing_secret, slack_adapter, message_router)
            await transport.start()
```

---

## How This Generalizes to Telegram

```python
# Future: adapters/transports/telegram_polling.py

class TelegramPollingTransport(ChannelTransport):
    """Telegram long polling — outbound HTTP requests."""

    async def start(self):
        self._running = True
        asyncio.create_task(self._poll_loop())

    async def _poll_loop(self):
        while self._running:
            updates = await self._get_updates(offset=self._last_update_id + 1)
            for update in updates:
                self._last_update_id = update["update_id"]
                await self.on_event(update)

# Future: adapters/transports/telegram_webhook.py

class TelegramWebhookTransport(ChannelTransport):
    """Telegram webhooks — inbound POST from Telegram."""

    async def handle_http_request(self, request: Request) -> dict:
        update = await request.json()
        asyncio.create_task(self.on_event(update))
        return {"ok": True}
```

Same pattern: transport handles arrival, adapter handles parsing, router handles dispatch.

---

## File Structure

```
src/backend/adapters/
├── __init__.py
├── base.py                    # ChannelAdapter, NormalizedMessage, ChannelResponse
├── message_router.py          # ChannelMessageRouter (shared dispatch)
├── slack_adapter.py           # SlackAdapter (parse, format, verify, resolve)
├── slack_formatter.py         # Markdown → Block Kit (Phase 2)
└── transports/
    ├── __init__.py
    ├── base.py                # ChannelTransport base class
    ├── slack_socket.py        # Slack Socket Mode (WebSocket)
    └── slack_webhook.py       # Slack HTTP webhooks
```

---

## Dependencies

| Package | Version | Purpose | Required For |
|---------|---------|---------|-------------|
| `slack_sdk[socket-mode]` | >=3.27 | Socket Mode client + Web API | Socket Mode transport |
| `aiohttp` | >=3.9 | Async HTTP for slack_sdk | Socket Mode transport |
| `httpx` | (existing) | HTTP calls | Webhook transport (current) |

Add to `docker/backend/Dockerfile`:
```
slack_sdk[socket-mode]==3.33.4
```

---

## Migration Path

1. **Phase 1**: Implement both transports, default to webhook (backward compatible)
2. **Phase 1.5**: Test Socket Mode locally, flip default to socket
3. **Phase 2**: Socket Mode is default, webhook is fallback for production
4. **Settings UI**: Add transport mode toggle + app token field

---

## Open Questions

1. **Should Socket Mode run in the backend process or a separate service?**
   - Backend process (simpler, one fewer container)
   - Separate service (like scheduler — isolated failure, independent restart)
   - **Recommendation**: Backend process, started on `app.startup`. If it disconnects, auto-reconnect (slack_sdk handles this).

2. **What happens when settings change?**
   - Changing transport mode requires restarting the transport
   - Could listen for settings changes via WebSocket and hot-swap
   - **Recommendation**: Require backend restart for transport mode changes (simple, rare operation)

3. **Can both transports run simultaneously?**
   - Technically yes, but would cause duplicate message processing
   - **Recommendation**: One transport at a time per channel, selected by setting
