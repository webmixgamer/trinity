# Telegram Bot Integration for Agents (TGRAM-001)

> **Status**: Draft
> **Priority**: P2 (Medium)
> **Author**: Claude + Eugene
> **Created**: 2026-03-09

## Overview

Enable each Trinity agent to have its own Telegram bot account. Users can chat with agents, receive notifications, and approve/reject outputs directly from Telegram. This is a mobile-first interface that lets operators manage agents from their phone.

Inspired by the OpenClaw comparison (2026-02-13 decision log) — Telegram was identified as a gap in Trinity's channel coverage.

## Goals

1. **Per-agent bots**: Each agent gets its own Telegram bot (unique token via BotFather)
2. **Bidirectional chat**: Users send messages to the bot, agent responds via its chat endpoint
3. **Notification bridge**: Agent notifications (NOTIF-001) are forwarded to Telegram
4. **Interactive actions**: Inline keyboards for approve/reject on "question" type notifications
5. **Credential reuse**: Telegram bot tokens use the existing CRED-002 credential injection system
6. **Channel-agnostic architecture**: Design so WhatsApp/Discord/other channels can be added later using the same patterns

## Non-Goals

- Group chat support (Phase 1 is 1:1 DMs only)
- Telegram Payments / Stars integration
- Bot creation automation (users create bots manually via BotFather)
- Telegram Mini Apps or web apps
- Voice/video messages
- Telegram Business account features
- Inline mode (@bot queries from other chats)

---

## Architecture

### Multi-Bot Webhook Model

All agent bots share a single webhook endpoint on the Trinity backend, differentiated by a token-derived path segment:

```
                    Telegram Cloud
                         │
          ┌──────────────┼──────────────┐
          │              │              │
     Bot Agent-A    Bot Agent-B    Bot Agent-N
          │              │              │
          ▼              ▼              ▼
  POST /api/telegram/webhook/{webhook_secret_A}
  POST /api/telegram/webhook/{webhook_secret_B}
  POST /api/telegram/webhook/{webhook_secret_N}
                         │
                         ▼
              ┌─────────────────────┐
              │  Trinity Backend    │
              │  telegram_router.py │
              │                     │
              │  1. Lookup agent    │
              │     by webhook_secret│
              │  2. Parse message   │
              │  3. Route to agent  │
              │     chat endpoint   │
              │  4. Send response   │
              │     via Bot API     │
              └─────────────────────┘
```

**Webhook secret**: A random token (NOT the bot token itself) used in the URL path. The bot token is never exposed in URLs. Stored in `telegram_bindings.webhook_secret`.

### HTTPS Requirements

Telegram webhooks require:
- **TLS 1.2+** (mandatory, no plain HTTP)
- **Ports**: 443, 80, 88, or 8443 only
- **IPv4 only** (IPv6 not supported)
- **Self-signed certs**: Accepted if uploaded during `setWebhook`
- **Let's Encrypt**: Works without certificate upload

**Development**: Use polling mode (no HTTPS needed) or ngrok/Cloudflare Tunnel.
**Production**: Reverse proxy (nginx) with Let's Encrypt.

### Update Modes

| Mode | When | How |
|------|------|-----|
| **Polling** | Development / localhost | Backend polls `getUpdates` per bot on a timer |
| **Webhook** | Production / public URL | Telegram POSTs to `/api/telegram/webhook/{secret}` |

The backend should support both modes, selected via `TELEGRAM_UPDATE_MODE=polling|webhook` env var.

---

## Credential Flow

Telegram bot tokens use the existing CRED-002 system with zero changes:

```
1. User creates bot via @BotFather → gets token (e.g., 123456789:ABCDEFghijklmnop)
2. User injects via Quick Inject UI:
     TELEGRAM_BOT_TOKEN=123456789:ABCDEFghijklmnop
3. Token written to /home/developer/.env (0o600 perms)
4. Credential sanitizer auto-masks token in logs
5. Backend detects TELEGRAM_BOT_TOKEN in agent's .env
6. Backend registers webhook / starts polling for this bot
7. Token exportable via .credentials.enc (encrypted)
```

**No changes to credential system required.**

---

## Database Schema

### New Table: `telegram_bindings`

Maps Telegram bots to agents and tracks connected users.

```sql
CREATE TABLE telegram_bindings (
    id TEXT PRIMARY KEY,                     -- UUID
    agent_name TEXT NOT NULL UNIQUE,         -- One bot per agent
    bot_id TEXT NOT NULL,                    -- Telegram bot user ID (from getMe)
    bot_username TEXT NOT NULL,              -- @username of the bot
    webhook_secret TEXT NOT NULL UNIQUE,     -- Random secret for webhook URL path
    is_active INTEGER DEFAULT 1,            -- 1=active, 0=disabled
    created_at TEXT NOT NULL,               -- ISO timestamp
    updated_at TEXT
);

CREATE INDEX idx_telegram_bindings_agent ON telegram_bindings(agent_name);
CREATE INDEX idx_telegram_bindings_webhook ON telegram_bindings(webhook_secret);
CREATE INDEX idx_telegram_bindings_bot ON telegram_bindings(bot_id);
```

### New Table: `telegram_chat_links`

Maps Telegram users/chats to Trinity users for a specific agent bot.

```sql
CREATE TABLE telegram_chat_links (
    id TEXT PRIMARY KEY,                     -- UUID
    binding_id TEXT NOT NULL,                -- FK to telegram_bindings
    telegram_chat_id INTEGER NOT NULL,       -- Telegram chat ID
    telegram_user_id INTEGER NOT NULL,       -- Telegram user ID
    telegram_username TEXT,                  -- @username (may be NULL)
    telegram_first_name TEXT,               -- Display name
    trinity_user_id TEXT,                   -- FK to users (NULL if unlinked)
    is_verified INTEGER DEFAULT 0,          -- 1=verified Trinity user
    created_at TEXT NOT NULL,
    last_message_at TEXT,

    FOREIGN KEY (binding_id) REFERENCES telegram_bindings(id) ON DELETE CASCADE,
    UNIQUE(binding_id, telegram_chat_id)
);

CREATE INDEX idx_telegram_chats_binding ON telegram_chat_links(binding_id);
CREATE INDEX idx_telegram_chats_chat ON telegram_chat_links(telegram_chat_id);
```

---

## API Endpoints

### Public Endpoints (Webhook Receiver)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/telegram/webhook/{webhook_secret}` | POST | None (secret in URL) | Receive Telegram updates |

### Authenticated Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/agents/{name}/telegram` | GET | JWT | Get Telegram bot status |
| `/api/agents/{name}/telegram/register` | POST | JWT | Register bot (calls getMe, sets webhook) |
| `/api/agents/{name}/telegram/unregister` | DELETE | JWT | Unregister bot (removes webhook) |
| `/api/agents/{name}/telegram/test` | POST | JWT | Send test message to a chat |
| `/api/telegram/bindings` | GET | JWT | List all registered Telegram bots |

---

## API Specifications

### POST /api/agents/{name}/telegram/register

Registers the agent's Telegram bot. Reads `TELEGRAM_BOT_TOKEN` from agent's `.env`, calls Telegram `getMe` to validate, and sets up webhook or polling.

**Request Body:** (none - reads token from agent credentials)

**Response (Success):**
```json
{
  "status": "registered",
  "bot_id": "123456789",
  "bot_username": "my_agent_bot",
  "bot_link": "https://t.me/my_agent_bot",
  "update_mode": "webhook"
}
```

**Error Responses:**

| Status | Reason |
|--------|--------|
| 400 | `TELEGRAM_BOT_TOKEN` not found in agent credentials |
| 400 | Invalid bot token (getMe failed) |
| 409 | Bot already registered for this agent |

### GET /api/agents/{name}/telegram

**Response (Registered):**
```json
{
  "registered": true,
  "bot_id": "123456789",
  "bot_username": "my_agent_bot",
  "bot_link": "https://t.me/my_agent_bot",
  "is_active": true,
  "update_mode": "webhook",
  "connected_users": 3,
  "created_at": "2026-03-09T10:00:00Z"
}
```

**Response (Not Registered):**
```json
{
  "registered": false,
  "has_token": true
}
```

### POST /api/telegram/webhook/{webhook_secret}

Receives updates from Telegram. Handles:

1. **Text messages**: Routes to agent chat endpoint, sends response back
2. **Callback queries**: Handles inline keyboard button presses (approve/reject)
3. **`/start` command**: Sends welcome message with agent description
4. **`/help` command**: Lists available commands

**Response:** Always `200 OK` (Telegram retries on non-200)

---

## Message Flow

### Inbound (Telegram → Agent)

```
Telegram User sends message
    │
    ▼
POST /api/telegram/webhook/{secret}
    │
    ├─ 1. Lookup agent by webhook_secret
    ├─ 2. Get/create telegram_chat_link for this user
    ├─ 3. Build context (last N messages from conversation)
    ├─ 4. POST to agent's /api/task endpoint
    │     (same as web UI chat)
    ├─ 5. Wait for agent response
    └─ 6. Call Telegram sendMessage with response
         (parse markdown → Telegram MarkdownV2)
```

### Outbound (Notification → Telegram)

```
Agent sends notification via MCP send_notification tool
    │
    ▼
notifications.py → _broadcast_notification()
    │
    ├─ Existing: WebSocket broadcast to UI
    └─ NEW: telegram_service.forward_notification()
         │
         ├─ 1. Lookup telegram_binding for agent
         ├─ 2. Get all telegram_chat_links for this binding
         ├─ 3. For "question" type: add inline keyboard
         │     [Approve ✓] [Reject ✗]
         └─ 4. Call sendMessage to each linked chat
```

### Interactive (Inline Keyboard Callbacks)

```
User taps [Approve] button on notification
    │
    ▼
POST /api/telegram/webhook/{secret}
    update.callback_query.data = "approve:{notification_id}"
    │
    ├─ 1. Parse callback data
    ├─ 2. Call POST /api/notifications/{id}/acknowledge
    ├─ 3. Edit message: remove keyboard, add "✓ Approved" text
    └─ 4. Answer callback query (removes loading spinner)
```

---

## Notification Formatting

Map notification types to Telegram message formats:

| Type | Telegram Format |
|------|----------------|
| `alert` | `🚨 *Alert*: {title}\n{message}` |
| `info` | `ℹ️ *Info*: {title}\n{message}` |
| `status` | `📊 *Status*: {title}\n{message}` |
| `completion` | `✅ *Completed*: {title}\n{message}` |
| `question` | `❓ *Action Required*: {title}\n{message}` + inline keyboard |

Priority affects delivery:

| Priority | Behavior |
|----------|----------|
| `low` | Normal message, no notification sound |
| `normal` | Normal message |
| `high` | Normal message (Telegram handles notification) |
| `urgent` | Message + `disable_notification=false` (always alert) |

---

## Configuration

### Environment Variables (Backend)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_UPDATE_MODE` | No | `polling` | `polling` or `webhook` |
| `TELEGRAM_WEBHOOK_BASE_URL` | If webhook | - | Public HTTPS URL (e.g., `https://your-domain.com`) |
| `TELEGRAM_POLLING_INTERVAL` | No | `2` | Seconds between polling requests |

### Per-Agent Credential (in agent .env)

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather |

---

## Frontend UI

### Agent Detail → Telegram Panel

New section in Agent Detail page (either as a tab or within an existing integrations section):

```
┌─────────────────────────────────────────────────────────────┐
│ Telegram Bot                                                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Status: 🟢 Connected as @my_agent_bot                        │
│ Bot Link: https://t.me/my_agent_bot  [Copy] [Open]          │
│ Connected Users: 3                                            │
│ Update Mode: Webhook                                          │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ QR Code                                                  │  │
│ │ (links to https://t.me/my_agent_bot)                    │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ Notification Forwarding: ☑ Enabled                           │
│ Forward priorities: ☑ urgent ☑ high ☐ normal ☐ low          │
│                                                               │
│ [Test Message] [Unregister Bot]                              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**When no token configured:**
```
┌─────────────────────────────────────────────────────────────┐
│ Telegram Bot                                                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ No Telegram bot configured for this agent.                   │
│                                                               │
│ To set up:                                                    │
│ 1. Open Telegram and message @BotFather                      │
│ 2. Send /newbot and follow the prompts                       │
│ 3. Copy the bot token                                        │
│ 4. Add TELEGRAM_BOT_TOKEN=<token> to agent credentials       │
│ 5. Click "Register Bot" below                                │
│                                                               │
│ [Register Bot] (disabled until token detected)               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

### Bot Token Protection
- Bot tokens stored only in agent `.env` files (0o600 permissions)
- Never stored in database (only bot_id and bot_username)
- Credential sanitizer masks tokens in all logs
- Webhook URLs use random secrets, not bot tokens
- Tokens encrypted in `.credentials.enc` for git storage

### Webhook Validation
- Webhook secret is a 32-byte random hex string, unique per agent
- Telegram sends from known IP ranges: `149.154.160.0/20` and `91.108.4.0/22`
- Optional: Validate source IPs in production

### Rate Limiting

| Limit | Value | Scope |
|-------|-------|-------|
| Inbound messages | 30/minute | Per Telegram user per bot |
| Outbound messages | 30/second | Per bot (Telegram limit) |
| Paid broadcasts | 1000/second | Per bot (requires Stars) |
| Notification forwarding | 10/minute | Per agent |

### User Binding
- Phase 1: Any Telegram user can message the bot (open access)
- Phase 2: Optional verification linking Telegram user to Trinity user
- Agent owners can see Telegram usernames of connected users (not phone numbers)

---

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `aiogram` | 3.x | Async Telegram Bot API framework (Python 3.10+, asyncio-native) |

**Why aiogram over python-telegram-bot**: Fully async with native asyncio, lighter weight, aligns with FastAPI's async architecture. Supports Bot API 9.4+.

---

## Implementation Phases

### Phase 1: Core Infrastructure (MVP)
- [ ] Database migrations (2 new tables)
- [ ] `telegram_service.py` — Bot validation (getMe), webhook/polling management
- [ ] `routers/telegram.py` — Webhook receiver, registration endpoints
- [ ] Inbound message routing: Telegram message → agent `/api/task` → Telegram response
- [ ] `/start` and `/help` command handlers
- [ ] Polling mode for development
- [ ] Agent Detail UI: Telegram status panel

### Phase 2: Notification Bridge
- [ ] Hook into `_broadcast_notification()` in `notifications.py`
- [ ] Forward notifications to all linked Telegram chats
- [ ] Notification type → message formatting
- [ ] Priority-based filtering (configurable per agent)

### Phase 3: Interactive Features
- [ ] Inline keyboards for "question" type notifications (approve/reject)
- [ ] Callback query handling → notification acknowledge/dismiss
- [ ] Message editing after action taken

### Phase 4: Webhook Mode (Production)
- [ ] Webhook registration with `setWebhook`
- [ ] Webhook secret generation and validation
- [ ] Auto-switch between polling/webhook based on config
- [ ] Health check endpoint for monitoring webhook status

### Phase 5: Polish & UX
- [ ] QR code generation for bot link
- [ ] Markdown → Telegram MarkdownV2 conversion
- [ ] Conversation context (last N messages) for multi-turn chat
- [ ] "Test Message" button in UI
- [ ] Error message templates (agent unavailable, rate limited)

### Future (Not in Scope)
- Group chat support
- User verification / Trinity user binding
- WhatsApp / Discord channels (same architecture, different adapter)
- Telegram Mini Apps
- Voice message transcription
- File/image upload forwarding

---

## Files to Create

| File | Description |
|------|-------------|
| `src/backend/routers/telegram.py` | Webhook receiver, registration, status endpoints |
| `src/backend/services/telegram_service.py` | Bot lifecycle, message sending, polling, webhook management |
| `src/backend/db/telegram.py` | Database operations for telegram tables |

## Files to Modify

| File | Changes |
|------|---------|
| `src/backend/db/schema.py` | Add 2 new tables |
| `src/backend/db/migrations.py` | Migration for Telegram tables |
| `src/backend/database.py` | Delegation methods for Telegram DB ops |
| `src/backend/main.py` | Mount Telegram router, start polling on startup |
| `src/backend/routers/notifications.py` | Hook `_broadcast_notification()` to forward to Telegram |
| `src/frontend/src/views/AgentDetail.vue` | Add Telegram panel/section |
| `requirements.txt` or `pyproject.toml` | Add `aiogram` dependency |

---

## Relationship to Other Features

| Feature | Relationship |
|---------|-------------|
| **NOTIF-001 (Notifications)** | Upstream — Telegram forwards notifications |
| **CRED-002 (Credentials)** | Reuses — Bot token injected via existing system |
| **SLACK-001 (Slack Integration)** | Sibling — Same channel pattern, different adapter |
| **Public Chat Sessions** | Pattern reference — Similar session/context management |

---

## Open Questions

1. **Open vs restricted access**: Should any Telegram user be able to message any bot, or should there be an allowlist?
   - *Current decision*: Open access in Phase 1, optional verification in future phase

2. **Conversation persistence**: Should Telegram conversations be stored in Trinity's DB for history/audit?
   - *Current decision*: Phase 1 is stateless (context from last N messages only). Full persistence in future phase.

3. **Multi-user notifications**: When an agent sends a notification, should ALL linked Telegram users receive it, or only the agent owner?
   - *Current decision*: All linked users receive it. Configurable filtering in future.

4. **Bot naming convention**: Should bot usernames follow a convention (e.g., `trinity_{agent_name}_bot`)?
   - *Current decision*: No enforcement — users create bots with any name via BotFather.

---

## References

- [Telegram Bot API](https://core.telegram.org/bots/api) (v9.4)
- [Telegram Bot Tutorial](https://core.telegram.org/bots/tutorial)
- [Telegram Webhook Guide](https://core.telegram.org/bots/webhooks)
- [aiogram Framework](https://aiogram.dev/)
- [Trinity Notification System (NOTIF-001)](./AGENT_NOTIFICATIONS.md)
- [Trinity Slack Integration (SLACK-001)](./SLACK_INTEGRATION.md)
- [OpenClaw Comparison](../research/openclaw-comparison.md)

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-03-09 | Claude + Eugene | Initial draft |
