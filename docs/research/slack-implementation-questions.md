# Slack Implementation — Open Questions

**Date**: 2026-03-21
**Context**: Questions arising during #63/#64 implementation
**Status**: Open for discussion

---

## Q1: Channel Listening Mode — @mention vs All Messages

### Current Behavior
Bot only responds when explicitly @mentioned (`app_mention` event). Users must type `@mcp-bot hello` every time.

### Proposed Behavior
In Trinity-created agent channels (e.g., `#dummy-gummy`), listen to ALL messages — no @mention needed. The channel IS the agent's space.

### Implementation
Subscribe to `message.channels` event in addition to `app_mention`. In `SlackAdapter.parse_message()`:

```python
# Channel message (not @mention)
if event_type == "message" and event.get("channel_type") == "channel":
    channel_id = event.get("channel")
    # Only respond if this channel is bound to an agent
    agent = db.get_slack_agent_name_for_channel(team_id, channel_id)
    if agent:
        return self._parse_channel_message(event, team_id)
    # Not a Trinity channel — ignore
    return None
```

### Smart Filtering Logic

```
Message arrives in a channel
  │
  ├─ Is this channel in slack_channel_agents table?
  │   ├─ YES → This is a Trinity agent channel
  │   │   └─ Respond to ALL messages (no @mention needed)
  │   │
  │   └─ NO → This is a regular channel (e.g., #general)
  │       └─ Only respond to @mentions (app_mention events)
  │
  └─ Is this a DM?
      └─ Respond (existing behavior)
```

### Benefits
- Seamless UX in agent channels — feels like chatting with a person
- No @mention friction for the primary use case
- Safe: only listens to channels Trinity created and bound to an agent
- General channels still require @mention — no spam

### Concerns
- What if someone manually adds the bot to a channel and names it the same as an agent?
  - **Mitigation**: Only respond if channel ID matches `slack_channel_agents.slack_channel_id` (not by name)
- What about bot's own messages creating echo loops?
  - **Mitigation**: Already filtering `bot_id` and `subtype` in `parse_message()`
- What about threads vs top-level messages?
  - Could respond to top-level and threads in agent channels
  - Or only top-level, with threads as follow-ups

### Required Changes
1. Slack App → Event Subscriptions → add `message.channels` to bot events
2. Slack App → OAuth scopes → `channels:history` (already added)
3. `SlackAdapter.parse_message()` — handle channel messages by checking binding table
4. No other changes needed — routing, execution, response all stay the same

---

## Q2: Who Responds — Bot Identity vs Agent Identity

### Current Behavior
Responses show the Slack app name ("mcp-bot") as sender, with `chat:write.customize` overriding to agent name.

### Questions
- Should the bot appear as "mcp-bot" or as the agent name (e.g., "dummy-gummy")?
- If `chat:write.customize` works, does the Slack app name matter?
- Should each agent channel show the agent's Trinity avatar as the bot icon?

### Status
`chat:write.customize` is in the OAuth scope. Implementation passes `username=agent_name` in `send_response()`. Need to verify it's working visually in Slack.

---

## Q3: Channel Lifecycle — What Happens When Agent Is Deleted/Renamed?

### Questions
- When an agent is deleted, should the Slack channel be archived/deleted?
- When an agent is renamed, should the channel be renamed?
- Who cleans up the `slack_channel_agents` binding?

### Current State
No cleanup logic exists. If agent `dummy-gummy` is deleted, channel `#dummy-gummy` stays in Slack and the binding stays in DB. Messages would fail with "agent not available."

### Proposed
- Agent delete → archive Slack channel + remove binding
- Agent rename → rename Slack channel + update binding
- Add to agent lifecycle hooks in `services/agent_service/crud.py`

---

## Q4: Multiple Users in Agent Channel — Session Isolation

### Current Behavior
Session identifier is `{team_id}:{user_id}:{channel_id}` — each user gets their own session even in the same channel.

### Questions
- Is this correct? Should all users in `#sales-bot` share one conversation context?
- Or should each user have their own "thread" with the agent?
- What happens when User A asks a question and User B sees the response — is the context confused?

### Options
| Option | Session Key | Behavior |
|--------|-----------|----------|
| Per-user per-channel | `team:user:channel` (current) | Each user has isolated context |
| Per-channel shared | `team:channel` | Everyone shares context (group chat) |
| Per-thread | `team:user:thread_ts` | Each thread is a separate session |

### Recommendation
Keep per-user per-channel for now. Group chat context (shared session) is a future enhancement. Thread-based sessions are in the #64 hardening plan.

---

## Q5: DM Behavior — Which Agent Responds?

### Current Behavior
DMs check: default agent → single connected agent → legacy `slack_link_connections` fallback.

### Questions
- When multiple agents are connected, what should DMs do?
- Show agent picker (Block Kit buttons)?
- Route to the last agent the user interacted with?
- Always use the "default" agent?

### Current Status
Deferred to #64 (Slack Hardening). For now, single agent or dm_default works.

---

## Q6: Should We Listen to `message.channels` Everywhere or Only Trinity Channels?

### The Concern
If we subscribe to `message.channels`, the bot receives ALL messages in ALL channels it's a member of. This includes:
- Trinity-created agent channels (intended) ✅
- Channels where someone manually invited the bot (unintended) ⚠️

### Proposed Solution
**Only respond in channels registered in `slack_channel_agents` table.** The check is by `channel_id`, not channel name — so even if someone creates a channel with the same name as an agent, we won't respond unless it's the exact channel we created and registered.

```python
# In SlackAdapter.parse_message():
if event_type == "message" and channel_type == "channel":
    # Only respond in Trinity-registered channels
    binding = db.get_slack_channel_agent(team_id, channel_id)
    if not binding:
        return None  # Ignore — not our channel
    # This is a Trinity agent channel — process the message
    return self._parse_channel_message(event, team_id)
```

This means:
- `#dummy-gummy` (created by Trinity, ID in DB) → ✅ responds to all messages
- `#general` (bot invited manually, ID NOT in DB) → ❌ ignores regular messages, only responds to @mentions
- `#dummy-gummy` (created by someone else, different channel ID) → ❌ ignored

### Required Slack App Config
- Subscribe to **both** `message.channels` AND `app_mention`
- `message.channels` for Trinity-created agent channels (all messages)
- `app_mention` for any other channel (explicit @mention only)

---

## Q7: Platform Prompt for Public Users

### The Problem
The Trinity platform prompt (`--append-system-prompt`) is injected on every execution. It contains fleet management instructions, operator queue protocol, and internal architecture details. Public Slack users see responses informed by this prompt.

### Questions
- Should public executions receive a different (minimal) system prompt?
- Or should the platform prompt be stripped entirely for public users?
- Does the web public chat have the same issue? (Yes — same prompt)

### Related
See `docs/research/slack-security-findings.md` for full analysis.

---

## Q8: Rate Limiting Granularity

### Current
30 messages per 60 seconds per Slack user (in-memory, not persistent).

### Questions
- Should rate limits be per-agent or per-workspace?
- Should they survive backend restarts? (Currently lost on restart)
- Should admins be able to configure limits per channel/agent?
- Should rate-limited users get a specific Slack message?

---

## Q9: Error Messages — Agent Identity

### Current
Error messages (agent unavailable, rate limited, execution error) are sent as plain text with no agent identity.

### Questions
- Should errors show the agent name/avatar via `chat:write.customize`?
- Should errors be ephemeral (only visible to the user who triggered them)?
- Slack supports `chat.postEphemeral` for this — should we use it?

---

## Q10: Concurrent Requests from Same User

### Scenario
User sends 3 messages rapidly before the first one gets a response.

### Current Behavior
All 3 are processed in parallel (separate `asyncio.create_task` calls). Agent gets 3 concurrent `/api/task` requests. Slot management limits this to `max_parallel_tasks` (default 3).

### Questions
- Should we queue messages per user and process sequentially?
- Or is parallel processing fine (agent handles its own state)?
- What if the user sends message 2 while message 1 is still processing — does message 2 have the context from message 1?
  - No — message 2 builds context from persisted messages only, and message 1 hasn't been persisted yet
