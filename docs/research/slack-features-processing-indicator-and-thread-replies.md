# Slack Features: Processing Indicator & Thread Replies Without @Mention

**Date**: 2026-03-23
**Status**: Implemented, needs testing
**Related Issues**: #63 (Channel Adapter), #64 (Slack Hardening)

---

## Feature 1: Processing Indicator (Reaction Emoji)

### What It Does

When a user sends a message to the bot, the bot immediately adds a ⏳ reaction to the user's message. This gives instant visual feedback that the message was received and is being processed. When the agent finishes (success or error), the ⏳ is replaced with ✅.

### User Experience

```
User sends: @mcp-bot what's the weather?
  → ⏳ appears on user's message (instant)
  → Agent processes (5-30 seconds)
  → ⏳ removed, ✅ appears
  → Bot sends response in thread
```

### Why Reaction Emoji (Not Other Options)

| Option | Available? | Notes |
|--------|-----------|-------|
| **Typing indicator** | No | Slack API has no typing indicator for bots — only human users |
| **Reaction emoji** | Yes | Instant, visual, non-intrusive |
| **Placeholder message + edit** | Yes | More visible but clutters the conversation |
| **Ephemeral "processing" message** | Yes | Only visible to sender, disappears — but can't be removed on completion |

Reaction emoji was chosen because:
- Zero latency — added before any processing starts
- Non-intrusive — doesn't create extra messages
- Clear lifecycle — ⏳ (processing) → ✅ (done)
- Works for both success and error cases

### Technical Implementation

**Abstraction** (`adapters/base.py`):
```python
class ChannelAdapter(ABC):
    async def indicate_processing(self, message) -> None:
        """Show processing indicator. Default: no-op."""
        pass

    async def indicate_done(self, message) -> None:
        """Show completion indicator. Default: no-op."""
        pass
```

These are optional hooks with default no-op — future adapters (Telegram, Discord) override them with their own indicators:
- Telegram: `sendChatAction(action="typing")`
- Discord: `triggerTypingIndicator()`

**Slack implementation** (`adapters/slack_adapter.py`):
```python
async def indicate_processing(self, message):
    await slack_service.add_reaction(bot_token, channel, timestamp, "hourglass_flowing_sand")

async def indicate_done(self, message):
    await slack_service.remove_reaction(bot_token, channel, timestamp, "hourglass_flowing_sand")
    await slack_service.add_reaction(bot_token, channel, timestamp, "white_check_mark")
```

**Slack Service** (`services/slack_service.py`):
- `add_reaction(bot_token, channel, timestamp, emoji)` — calls `reactions.add` API
- `remove_reaction(bot_token, channel, timestamp, emoji)` — calls `reactions.remove` API
- Both handle `already_reacted` and `no_reaction` errors gracefully (not fatal)

**Router** (`adapters/message_router.py`):
```python
# Step 8: Before agent execution
await adapter.indicate_processing(message)

# Step 10: After execution completes (success or error)
await adapter.indicate_done(message)
```

### Required Slack Configuration

- **OAuth scope**: `reactions:write` (added to OAuth scope string)
- **No event subscription changes** needed

### Trade-offs

| Trade-off | Decision |
|-----------|----------|
| Extra API calls (2 per message) | Acceptable — reactions API is fast and cheap |
| Rate limiting on reactions API | Tier 3 (50+ per minute) — not a concern |
| Emoji not visible in threads | Reactions are visible on the parent message, not thread replies — works fine since we react to the user's message |
| Error on failed reaction | Logged as warning, doesn't block message processing |

---

## Feature 2: Thread Replies Without @Mention

### What It Does

When a user @mentions the bot and the bot responds in a thread, subsequent replies in that same thread **don't need** the @mention. The bot automatically picks up thread replies and responds.

### User Experience

```
User: @mcp-bot explain kubernetes           ← needs @mention (starts thread)
Bot:  Kubernetes is a container...          ← responds in thread

User: what about pods?                      ← no @mention needed!
Bot:  Pods are the smallest...              ← responds in same thread

User: and services?                         ← still no @mention
Bot:  Services provide...                   ← continues conversation
```

### How It Works

**Two safety checks** ensure the bot only responds in the right context:

1. **Channel binding check**: Is this channel in `slack_channel_agents` table? (Only Trinity-created agent channels)
2. **Active thread check**: Is this thread in `slack_active_threads` table? (Only threads where bot already responded)

```
Message arrives with thread_ts
  ├─ Channel ID in slack_channel_agents?
  │   ├─ NO → ignore (not a bot channel)
  │   └─ YES → Thread_ts in slack_active_threads?
  │       ├─ NO → ignore (bot didn't start this thread)
  │       └─ YES → respond (bot-initiated thread in bot channel)
  │
  └─ No thread_ts → handled by @mention or DM logic (existing)
```

This guarantees:
- ✅ Only in Trinity-created agent channels
- ✅ Only in threads the bot started via @mention
- ✅ Random threads by humans in the channel are ignored
- ✅ Bot in #general (if invited) ignores all non-@mention messages

### Technical Implementation

**Database table** (`slack_active_threads`):
```sql
CREATE TABLE slack_active_threads (
    team_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    thread_ts TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (team_id, channel_id, thread_ts)
);
```

Indexed by `(team_id, channel_id, thread_ts)` for fast lookup on every thread message.

**Registration** — when bot sends a response in a thread, the adapter registers it:

Abstraction (`adapters/base.py`):
```python
class ChannelAdapter(ABC):
    async def on_response_sent(self, message, agent_name) -> None:
        """Post-response hook. Default: no-op."""
        pass
```

Slack implementation (`adapters/slack_adapter.py`):
```python
async def on_response_sent(self, message, agent_name):
    if message.thread_id and message.metadata.get("team_id"):
        db.register_slack_active_thread(
            team_id=message.metadata["team_id"],
            channel_id=message.channel_id,
            thread_ts=message.thread_id,
            agent_name=agent_name,
        )
```

**Parsing** — thread replies checked in `parse_message()`:

```python
def parse_message(self, raw_event):
    # ... existing DM and @mention handlers ...

    # Thread reply in bot channel (no @mention needed)
    if event_type == "message" and event.get("thread_ts"):
        return self._parse_thread_reply(event, team_id)
```

`_parse_thread_reply()` checks:
1. `db.get_slack_agent_name_for_channel(team_id, channel_id)` — is this a bot channel?
2. `db.is_slack_active_thread(team_id, channel_id, thread_ts)` — did bot respond here?
3. Both must pass → process message

### Required Slack Configuration

- **Bot event subscription**: `message.channels` — required to receive regular channel messages (not just @mentions)
- This is in addition to `app_mention` (which handles the initial @mention)
- Without `message.channels`, Slack only sends `app_mention` events

### Data Growth & Cleanup

| Time | Rows (1000 msg/day) | Size |
|------|---------------------|------|
| 1 week | ~7,000 | ~1.4 MB |
| 1 month | ~30,000 | ~6 MB |
| 1 year | ~365,000 | ~73 MB |

**TODO**: Implement cleanup job to delete threads older than 7 days. Pattern: same as `cleanup_service.py` with configurable retention. After expiry, users just @mention again to restart the thread.

This is documented as a required follow-up in:
- `db/migrations.py` — TODO comment on the table creation
- `docs/research/slack-implementation-questions.md` — Q10 (concurrent requests) references cleanup

### Trade-offs

| Trade-off | Decision |
|-----------|----------|
| DB lookup on every thread message | Fast — indexed primary key lookup, <1ms |
| `message.channels` receives ALL channel messages | Filtered immediately: non-bot-channel messages are discarded in `parse_message()` before any processing |
| No cleanup job yet | Acceptable for POC — table grows slowly, cleanup documented as follow-up |
| Thread ownership by channel_id not message content | Simple and reliable — we check the exact channel ID we created, not names or content |
| Bot might respond to thread replies from other bots | Filtered: `bot_id` and `subtype` checks reject bot messages |

### Security Considerations

- Thread replies go through the same security pipeline: `TaskExecutionService`, `allowed_tools`, rate limiting
- Thread replies in non-bot-channels are silently ignored (no error response that would leak info)
- Active thread tracking is per-workspace — no cross-workspace data leakage

---

## Summary of Changes

### New Slack API Usage

| API Method | Purpose | Required Scope |
|-----------|---------|----------------|
| `reactions.add` | Add ⏳/✅ emoji to messages | `reactions:write` |
| `reactions.remove` | Remove ⏳ emoji after processing | `reactions:write` |
| (receives `message` events) | Thread replies without @mention | `message.channels` bot event |

### New Database

| Table | Purpose | Size Impact |
|-------|---------|-------------|
| `slack_active_threads` | Track bot-initiated threads | ~73 MB/year at 1000 msg/day (cleanup TODO) |

### New Abstractions in `ChannelAdapter`

| Method | Purpose | Slack | Telegram (future) |
|--------|---------|-------|-------------------|
| `indicate_processing()` | Show "working on it" | ⏳ reaction | `sendChatAction(typing)` |
| `indicate_done()` | Show "finished" | ⏳→✅ | no-op (auto-expires) |
| `on_response_sent()` | Post-response hook | Register active thread | no-op |

All three are optional (default no-op) — adapters override only what they need.
