# Channel Adapter Abstraction & Slack Improvements Plan

**Date**: 2026-03-20 (focused revision)
**Status**: Ready to implement
**Branch**: `slack-improvements`
**Issues**: #63 (Channel Adapter Abstraction), #64 (Slack Adapter Hardening)
**Assignee**: pavshulin
**Research**: `docs/research/multi-agent-slack-bot-research.md`, `docs/plans/channel-transport-architecture.md`

---

## Goal

1. **Solid abstraction** for channel message transport (reusable for Telegram, Discord later)
2. **Working Slack POC** — single app, single agent, Socket Mode + webhook support, `chat:write.customize` for agent identity

Multi-agent routing, Block Kit formatting, thread sessions, and channel bindings are **deferred** — researched and documented but not in this release.

---

## Architecture

```
Transport (how events arrive)  →  Adapter (parse & format)  →  Router (dispatch to agent)
```

### Base Abstraction (channel-agnostic)

```python
# adapters/base.py — minimal, no Slack leakage

class NormalizedMessage(BaseModel):
    sender_id: str
    text: str
    channel_id: str
    thread_id: Optional[str] = None
    timestamp: str
    metadata: dict = {}             # Channel-specific extras

class ChannelResponse(BaseModel):
    text: str
    metadata: dict = {}             # Agent name, cost, etc.

class ChannelAdapter(ABC):
    @abstractmethod
    def parse_message(self, raw_event: dict) -> Optional[NormalizedMessage]: ...

    @abstractmethod
    async def send_response(self, channel_id: str, response: ChannelResponse,
                            thread_id: Optional[str] = None) -> None: ...

    @abstractmethod
    async def get_agent_name(self, message: NormalizedMessage) -> Optional[str]: ...

class ChannelTransport(ABC):
    def __init__(self, adapter: ChannelAdapter, router): ...

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    async def on_event(self, raw_event: dict) -> None:
        message = self.adapter.parse_message(raw_event)
        if message:
            await self.router.handle_message(self.adapter, message)
```

That's it for the abstraction. No `AgentIdentity`, no `prompt_agent_selection`, no verification in the interface. Those are Slack-specific and live in `SlackAdapter`.

### Slack Layer (Slack-specific, all of it)

- `SlackAdapter` — parse Slack events, send via `chat:write.customize`, verification state machine, agent lookup
- `SlackSocketTransport` — Socket Mode (default)
- `SlackWebhookTransport` — HTTP webhooks (fallback)
- `SlackService` — Slack API calls (existing, enhanced)

### Message Router (channel-agnostic)

- Get agent name from adapter
- Check agent availability
- Get/create session
- Build context, execute agent task, persist messages
- Return response through adapter

---

## What's In This Release

### Phase 1: Abstraction + Slack POC (#63)

| Step | What | Files |
|------|------|-------|
| 1.1 | Base classes: `ChannelAdapter`, `ChannelTransport`, `NormalizedMessage`, `ChannelResponse` | `adapters/base.py`, `adapters/transports/base.py` |
| 1.2 | `SlackSocketTransport` (Socket Mode) | `adapters/transports/slack_socket.py` |
| 1.3 | `SlackWebhookTransport` (HTTP, existing behavior) | `adapters/transports/slack_webhook.py` |
| 1.4 | `SlackAdapter` — parse, send (with `chat:write.customize`), verification, agent lookup | `adapters/slack_adapter.py` |
| 1.5 | `ChannelMessageRouter` — shared dispatch logic | `adapters/message_router.py` |
| 1.6 | Refactor `routers/slack.py` to use adapter + transport | `routers/slack.py` |
| 1.7 | OAuth scope update: add `chat:write.customize` | `services/slack_service.py` |
| 1.8 | Settings: `slack_transport_mode`, `slack_app_token` | `services/settings_service.py`, `routers/settings.py` |
| 1.9 | Startup hook: start transport on backend boot | `main.py` |
| 1.10 | Add `slack_sdk[socket-mode]` dependency | `docker/backend/Dockerfile` |
| 1.11 | Doc updates | changelog, architecture, requirements |

### What's NOT in this release

- Multi-agent routing (single agent per workspace, same as today)
- `slack_agent_connections` / `slack_agent_bindings` tables (deferred)
- `channel_bindings` table (deferred)
- Block Kit formatting (plain text + `chat:write.customize` for name/avatar)
- Thread-based sessions
- Agent picker / Block Kit buttons
- App Home directory
- Slash commands
- Token-aware context injection
- Typing indicator
- Retry logic

All researched and documented — just not in scope for this PR.

---

## Detailed Steps

### 1.1 Base Classes (~60 lines)

**`src/backend/adapters/__init__.py`** — empty
**`src/backend/adapters/base.py`**:

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from pydantic import BaseModel

class NormalizedMessage(BaseModel):
    sender_id: str
    text: str
    channel_id: str
    thread_id: Optional[str] = None
    timestamp: str
    metadata: dict = {}

class ChannelResponse(BaseModel):
    text: str
    metadata: dict = {}

class ChannelAdapter(ABC):
    @abstractmethod
    def parse_message(self, raw_event: dict) -> Optional[NormalizedMessage]: ...

    @abstractmethod
    async def send_response(self, channel_id: str, response: ChannelResponse,
                            thread_id: Optional[str] = None) -> None: ...

    @abstractmethod
    async def get_agent_name(self, message: NormalizedMessage) -> Optional[str]: ...
```

**`src/backend/adapters/transports/__init__.py`** — empty
**`src/backend/adapters/transports/base.py`**:

```python
from abc import ABC, abstractmethod

class ChannelTransport(ABC):
    def __init__(self, adapter, router):
        self.adapter = adapter
        self.router = router

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    async def on_event(self, raw_event: dict) -> None:
        message = self.adapter.parse_message(raw_event)
        if message:
            await self.router.handle_message(self.adapter, message)
```

### 1.2-1.3 Slack Transports (~150 lines total)

**Socket Mode** (`adapters/transports/slack_socket.py`):
- Uses `slack_sdk.socket_mode.aiohttp.SocketModeClient`
- Acknowledges events immediately (no timeout)
- Passes `req.payload` to `on_event()`

**Webhook** (`adapters/transports/slack_webhook.py`):
- Signature verification (moved from `slack.py`)
- URL verification challenge handling
- `asyncio.create_task(on_event())` for async processing

### 1.4 SlackAdapter (~200 lines)

**`adapters/slack_adapter.py`** — all Slack-specific logic:

- `parse_message()` — extract from Slack event (user, text, channel, thread_ts, team_id in metadata)
- `send_response()` — `chat.postMessage` with `username` + `icon_url` from agent (chat:write.customize)
- `get_agent_name()` — lookup via `db.get_slack_connection_by_team()` (current 1:1 model)
- `handle_verification()` — existing state machine (moved from slack.py)
- `get_bot_token()` — get from workspace connection
- `is_bot_message()` — filter out bot's own messages

Verification is a method on `SlackAdapter`, NOT on the base `ChannelAdapter`.

### 1.5 Message Router (~150 lines)

**`adapters/message_router.py`**:

```python
class ChannelMessageRouter:
    async def handle_message(self, adapter, message):
        agent_name = await adapter.get_agent_name(message)
        if not agent_name:
            return

        # Check availability
        container = get_agent_container(agent_name)
        if not container or container.status != "running":
            await adapter.send_response(message.channel_id,
                ChannelResponse(text="Sorry, I'm not available right now."))
            return

        # Slack-specific: verification (duck-type check)
        if hasattr(adapter, 'handle_verification'):
            verified = await adapter.handle_verification(message)
            if not verified:
                return

        # Session + context + execute
        session = self._get_or_create_session(agent_name, message)
        context = self._build_context(session, message.text)
        response_text = await self._execute_agent_task(agent_name, context)
        self._persist_messages(session, message.text, response_text)

        await adapter.send_response(
            message.channel_id,
            ChannelResponse(text=response_text),
            thread_id=message.thread_id
        )
```

Uses `TaskExecutionService` for agent dispatch (activity tracking, execution records).

### 1.6 Router Refactor

**`routers/slack.py`** — slimmed to ~250 lines:
- Webhook endpoint delegates to `SlackWebhookTransport`
- OAuth endpoints stay (connect, callback, disconnect, status)
- Verification messages and `_forward_to_agent` removed (moved to adapter + router)

### 1.7 OAuth Scope

In `services/slack_service.py` → `get_oauth_url()`:
```python
# Add chat:write.customize for agent identity
"scope": "im:history,im:read,im:write,chat:write,chat:write.customize,users:read,users:read.email"
```

Note: Existing workspaces need to re-authorize to get the new scope.

### 1.8 Settings

Add to `settings_service.py` (same DB-first + env fallback pattern):
- `get_slack_transport_mode()` → `"socket"` (default) or `"webhook"`
- `get_slack_app_token()` → App-Level Token (`xapp-...`) for Socket Mode

### 1.9 Startup Hook

In `main.py`:
```python
@app.on_event("startup")
async def start_channel_transports():
    mode = get_slack_transport_mode() or "socket"
    if mode == "socket":
        app_token = get_slack_app_token()
        if app_token:
            transport = SlackSocketTransport(app_token, slack_adapter, message_router)
            await transport.start()
    # Webhook mode: passive (FastAPI endpoint handles it)
```

### 1.10 Dependency

Add to `docker/backend/Dockerfile`:
```
slack_sdk[socket-mode]==3.33.4
```

---

## Line Estimates

| Component | Lines |
|-----------|-------|
| `adapters/base.py` | ~40 |
| `adapters/transports/base.py` | ~30 |
| `adapters/transports/slack_socket.py` | ~70 |
| `adapters/transports/slack_webhook.py` | ~80 |
| `adapters/slack_adapter.py` | ~200 |
| `adapters/message_router.py` | ~150 |
| `routers/slack.py` refactor | 540 → ~250 (net -290) |
| Settings + startup | ~60 |
| Dockerfile | +1 line |
| **Total** | **~630 new, ~290 removed** |

---

## Acceptance Criteria

- [ ] `ChannelAdapter` and `ChannelTransport` base classes — minimal, no Slack leakage
- [ ] `SlackAdapter` implements adapter (parse, send with agent identity, verification)
- [ ] Socket Mode transport working (no public URL needed)
- [ ] Webhook transport working (backward compatible)
- [ ] `chat:write.customize` — agent name + avatar shown on responses
- [ ] Message router dispatches to agent, persists session
- [ ] Settings UI for transport mode + app token
- [ ] Existing Slack functionality preserved (OAuth, DM routing, verification)
- [ ] No regressions

---

## What's Deferred (documented, not implemented)

| Feature | Where it's documented | Why deferred |
|---------|----------------------|-------------|
| Multi-agent per workspace | `docs/research/multi-agent-slack-bot-research.md` | Needs agent picker UI, routing tables |
| Block Kit formatting | Plan Phase 2 section (removed) | Markdown works for POC |
| Thread-based sessions | Plan Phase 2 section (removed) | DM sessions work for POC |
| Token-aware context | Plan Phase 2 section (removed) | Fixed 10-turn works for POC |
| Typing indicator | Plan Phase 2 section (removed) | Nice-to-have, not blocking |
| Channel binding routing | Research doc §3.1 | Needs multi-agent first |
| App Home directory | Research doc §3.5 | Needs multi-agent first |
| Slash commands | Research doc §3.4 | Future enhancement |
| Retry logic | Plan Phase 2 section (removed) | Slack SDK has built-in retries |

All of these go into #64 (Slack Adapter Hardening) which remains a separate issue.

---

## Implementation Order

```
Phase 0: ✅ Done
  0.1  PUBLIC_CHAT_URL → Settings DB
  0.2  Fixed PublicChatSession subscriptable bug
  0.3  Fixed prompt vs message field name

Phase 1: Abstraction + Slack POC (#63)
  1.1  adapters/base.py + adapters/transports/base.py
  1.2  adapters/transports/slack_socket.py
  1.3  adapters/transports/slack_webhook.py
  1.4  adapters/slack_adapter.py
  1.5  adapters/message_router.py
  1.6  Refactor routers/slack.py
  1.7  OAuth scope: add chat:write.customize
  1.8  Settings: transport_mode + app_token
  1.9  main.py startup hook
  1.10 Dockerfile: slack_sdk[socket-mode]
  1.11 Docs: changelog + architecture + requirements
  ── test Socket Mode (no Tailscale) ──
  ── test webhook (backward compat) ──
  ── commit, PR for #63 ──
```

---

## Pre-implementation Doc Fixes (bundle with PR)

| Document | Fix |
|----------|-----|
| `docs/memory/feature-flows/slack-integration.md` | PUBLIC_CHAT_URL: Settings DB, not env-only |
| `docs/requirements/SLACK_INTEGRATION.md` | Architecture diagram: Settings DB |
| `.env.example` | PUBLIC_CHAT_URL comment: Settings UI note |
| `docs/memory/changelog.md` | Phase 0 + Phase 1 entries |
| `docs/memory/architecture.md` | Channel Adapter section |
| `docs/memory/requirements.md` | Update §15.1b |

---

## Patterns to Follow

- **DatabaseManager facade**: new ops classes wired via delegation
- **DB operations**: `secrets.token_urlsafe(16)`, `datetime.utcnow().isoformat()`, `get_db_connection()` context manager
- **Settings**: DB-first + env fallback (same as Slack credentials)
- **Existing tables**: `slack_link_connections`, `slack_user_verifications`, `slack_pending_verifications`, `public_chat_sessions` — don't break
- **Security**: never log tokens, return 200 to Slack webhooks
