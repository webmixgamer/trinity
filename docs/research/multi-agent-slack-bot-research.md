# Multi-Agent Slack Bot Research

> **Date**: 2026-03-20
> **Status**: Research Complete
> **Author**: Claude (research) + Eugene (review)
> **Context**: Trinity platform with N agents, users need to reach specific agents via Slack

---

## Table of Contents

1. [Slack API Limitations for Our Use Case](#1-slack-api-limitations)
2. [Patterns Used by Other Multi-Agent Platforms](#2-multi-agent-platform-patterns)
3. [Routing Patterns for Single App + Multiple Agents](#3-routing-patterns)
4. [Technical Deep Dive on Promising Patterns](#4-technical-deep-dive)
5. [Practical UX Considerations](#5-practical-ux-considerations)
6. [Recommendation for Trinity](#6-recommendation)

---

## 1. Slack API Limitations

### 1.1 Can One Slack App Have Multiple Bot Identities/Personalities?

**No, not natively.** A Slack App has exactly one bot user with one display name and one avatar configured in the app settings. However, there is a powerful workaround:

**`chat:write.customize` scope** allows per-message identity override:
- `username` parameter: Override the displayed bot name per message
- `icon_url` parameter: Override the avatar per message
- `icon_emoji` parameter: Use an emoji as avatar per message

These require the `chat:write.customize` OAuth scope. The message still comes from the same bot user, but it **visually appears** as a different entity. This is the key mechanism for simulating multiple agent identities from one app.

**DM-specific limitations**: In DMs, the identity overrides work but Slack may show additional context (like "via AppName") to ensure users know which app sent the message. The bot's actual identity is always discoverable.

**Source**: [chat.postMessage docs](https://docs.slack.dev/reference/methods/chat.postMessage/), [chat:write.customize scope](https://docs.slack.dev/reference/scopes/chat.write.customize/)

### 1.2 Can You Programmatically Create Slack Apps?

**Yes.** The `apps.manifest.create` API method creates a fully functional Slack App from a JSON/YAML manifest. It returns `client_id`, `client_secret`, `verification_token`, and `signing_secret` -- a complete, deployable app.

**Requirements**:
- An **App Configuration Token** (not a regular bot/user token)
- Generated at `api.slack.com/apps` under "Your App Configuration Tokens"
- Tokens expire after 12 hours (refresh tokens provided)
- One config token can manage multiple apps within a workspace
- Rate limit: Tier 1 (1+ per minute)

**No documented limit** on how many apps can be created via this API.

This means Trinity **could** auto-provision a Slack App per agent, though this adds management complexity (each app needs separate OAuth installation).

**Source**: [apps.manifest.create](https://docs.slack.dev/reference/methods/apps.manifest.create/), [Configuring apps with app manifests](https://docs.slack.dev/app-manifests/configuring-apps-with-app-manifests/)

### 1.3 Can One Bot Respond Differently Based on Channel/Thread?

**Yes, fully supported.** Every incoming event includes:
- `team_id` (workspace)
- `channel` (channel ID)
- `thread_ts` (thread timestamp, if in a thread)
- `user` (who sent it)

The backend can use any of these to determine routing. The bot can respond with different content, personality, or agent backend based on which channel or thread the message is in. Combined with `username`/`icon_url` overrides, each channel can feel like a different agent.

### 1.4 What Are Slack's Limits on Apps per Workspace?

| Plan | App Install Limit |
|------|------------------|
| **Free** | 10 third-party or custom apps |
| **Pro** | Unlimited |
| **Business+** | Unlimited |
| **Enterprise Grid** | Unlimited (with governance controls) |

For the "one app per agent" approach, Free plan workspaces would hit the 10-app cap quickly if they have many agents. The single-app approach avoids this entirely.

**Source**: [Usage limits for free workspaces](https://slack.com/help/articles/115002422943-Usage-limits-for-free-workspaces), [Slack plans and features](https://slack.com/help/articles/115003205446-Slack-plans-and-features)

### 1.5 Can You Change a Bot's Display Name Per-Message or Per-Channel?

**Per-message: Yes** (with `chat:write.customize` scope). Each call to `chat.postMessage` can specify a different `username` and `icon_url`. This is the primary mechanism used by platforms like Dust.tt to simulate multiple agent identities.

**Per-channel: No native mechanism.** There's no Slack feature to say "in channel #sales, this bot should appear as Sales Agent." You must implement this in your backend and pass the appropriate `username`/`icon_url` with each message.

### 1.6 How Does `chat.postMessage` Work with `username` and `icon_url` Overrides?

```python
# Example: Post as "Sales Agent" with custom avatar
response = client.chat_postMessage(
    channel="C1234567890",
    text="Here's the Q4 forecast...",
    username="Sales Agent",           # Override display name
    icon_url="https://example.com/sales-avatar.png",  # Override avatar
    # OR: icon_emoji=":briefcase:"    # Use emoji as avatar
)
```

**Key rules**:
1. Requires `chat:write` + `chat:write.customize` scopes
2. The `as_user` parameter is legacy (classic apps only) -- modern apps don't use it
3. In DMs, the override works but Slack may add attribution context
4. Messages posted with custom identity cannot be edited/deleted by the "fake" identity -- only by the actual app
5. The message metadata still records the real app as sender

**Source**: [chat.postMessage reference](https://docs.slack.dev/reference/methods/chat.postMessage/)

---

## 2. Multi-Agent Platform Patterns

### 2.1 Slack's Workflow Builder

Slack's native Workflow Builder supports **conditional branching** (up to 15 conditions, with nested 5-condition branches). It can route messages to different channels and trigger different automations based on:
- Keywords in messages
- Form field values
- Channel where triggered

However, it's designed for **simple linear automations**, not AI agent routing. It breaks down with external system calls, complex context, or long-running operations.

**Relevance to Trinity**: Minimal. Workflow Builder is for simple automations, not agent orchestration.

**Source**: [Slack Workflow Builder](https://slack.com/features/workflow-automation), [Conditional branching](https://slack.com/blog/news/conditional-branching-workflow-builder)

### 2.2 Slack's "Agents & AI Apps" Feature (New)

Slack has introduced a first-party **Agents & AI Apps** developer feature with:
- **Split view surface**: Users can chat with AI apps in a side panel within channels
- **App threads**: Conversations auto-grouped into threads with title support
- **Suggested prompts**: Up to 4 preset prompts to guide users
- **Chat + History tabs**: Replaces the standard Messages tab in App Home
- **Context awareness**: Apps receive `channel_id` context when opened from a channel
- **Loading states**: Built-in indicators during AI processing

**Required scope**: `assistant:write` (auto-added when feature is enabled)
**Required events**: `assistant_thread_started`, `assistant_thread_context_changed`, `message.im`

**Limitation**: Marketplace submission with this feature is currently **reserved for select partners only**. However, the feature can be used in custom apps installed to your own workspace.

**Multi-agent gap**: The documentation does not address how multiple AI apps coexist or how to route between them. Each AI app is independent.

**Source**: [AI in Slack apps](https://docs.slack.dev/ai/), [Developing AI apps](https://docs.slack.dev/ai/developing-ai-apps/), [Split view](https://docs.slack.dev/surfaces/split-view/)

### 2.3 Dust.tt -- Single App, Multi-Agent via Syntax

Dust uses a **single Slack app** with a clever routing syntax:

| Pattern | Behavior |
|---------|----------|
| `@dust question` | Routes to default agent |
| `@dust ~sales_writer question` | Routes to named agent |
| `@dust +code_reviewer question` | Alternative syntax for named agent |

**Channel-level binding**: Admins can bind a specific agent to a channel. When `@dust` is mentioned in that channel, the bound agent responds instead of the default.

**Architecture**: One Slack app, one bot token, backend parses the `+agent_name` or `~agent_name` prefix from the message text to determine routing. Channel bindings stored in Dust's backend database.

**Source**: [Dust Slack docs](https://docs.dust.tt/docs/slack), [Dust Slack integration](https://dust.tt/home/slack/slack-integration)

### 2.4 Relevance AI -- Single App, Keyword Triggers

Relevance AI uses a **single Slack app** with keyword-based routing:

- Each agent is configured with trigger keywords
- If a message @mentions `@Relevance AI` with a matching keyword, the appropriate agent responds
- Leaving the keyword blank makes the agent respond to all messages
- Supports triggering multi-agent **Workforces** (complex workflows with multiple agents)

**Source**: [Relevance AI Slack docs](https://relevanceai.com/docs/integrations/popular-integrations/slack)

### 2.5 OpenClaw -- One App Per Agent (Multi-App)

OpenClaw takes the **opposite approach**: one Slack app/bot per agent identity.

- Each agent gets its own Slack bot with unique name, avatar, and token
- `bindings` in config map Slack account IDs to agent IDs
- Each agent has true independent DMs and channel presence
- One primary agent can delegate to specialists via agent-to-agent tools

**Tradeoffs**:
- **Pro**: True separate identities, independent DM conversations, natural @mention routing
- **Con**: Multiple Slack apps to create/manage, hits Free plan limits, complex OAuth per agent

**Source**: [OpenClaw multi-agent docs](https://gist.github.com/rafaelquintanilha/9ca5ae6173cd0682026754cfefe26d3f)

### 2.6 Salesforce Agentforce in Slack

Salesforce's Agentforce agents run directly in Slack via the Salesforce integration:
- Agents operate in channels, threads, and DMs
- Users @mention agents like team members
- Each agent is registered as a separate Slack app identity via the Salesforce platform

**Source**: [Agentforce in Slack](https://slack.com/ai-agents), [Salesforce Agentforce](https://www.salesforce.com/slack/agentforce/)

### 2.7 Microsoft Teams Comparison

Teams has a similar constraint: one bot per app manifest entry. For multi-agent scenarios:
- Regional routing must happen at the **backend level**, not the Teams manifest
- A single Teams app can contain one bot registration
- The backend determines which agent logic handles the request
- Teams does not support per-message identity override like Slack's `chat:write.customize`

**Source**: [Teams bot configuration](https://learn.microsoft.com/en-us/microsoftteams/platform/toolkit/configure-bot-capability)

### 2.8 Customer Support Platforms (Intercom, Zendesk, Freshdesk)

These platforms take a fundamentally different approach -- they route **human agents**, not AI agents:
- **Zendesk**: Skills-based routing across channels based on expertise and workload
- **Intercom**: Round-robin assignment with capacity-based routing
- **Freshdesk**: Ticket management from Slack with routing rules

Their Slack integrations focus on notification/ticket management, not multi-bot identity. They use a single Slack app that posts on behalf of the platform, not individual agents.

---

## 3. Routing Patterns for Single App + Multiple Agents

### 3.1 Channel-Based Routing

**Pattern**: Each Slack channel maps to a specific agent.

```
#sales-agent     -> routes to Sales Agent
#support-agent   -> routes to Support Agent
#engineering     -> routes to Engineering Agent
```

**Implementation**:
- Store channel-to-agent mapping in database (`channel_bindings` table)
- On `message` event, look up `channel_id` -> `agent_name`
- Respond with agent-specific `username` + `icon_url`
- Admin configures bindings via Trinity UI or slash command

**Pros**:
- Clear context -- everyone in the channel talks to the same agent
- Easy to understand for users
- Agent's conversation history stays in one place

**Cons**:
- Channel proliferation (one channel per agent)
- Less natural for ad-hoc "let me ask a different agent"
- Requires channel creation/management

**Best for**: Teams with dedicated agent roles (support, sales, engineering)

### 3.2 Thread-Based Routing

**Pattern**: Each thread can be with a different agent.

```
Channel #ai-agents:
  Thread 1: "Sales Agent, what's our Q4 pipeline?" -> Sales Agent
  Thread 2: "Support Agent, customer #123 has an issue" -> Support Agent
```

**Implementation**:
- Store `thread_ts` -> `agent_name` mapping
- First message in thread determines the agent (via @mention, prefix, or selection)
- All replies in thread route to same agent
- Use `thread_ts` in `chat.postMessage` to keep responses in-thread

**Pros**:
- Multiple agents in one channel
- Clean conversation separation
- Natural Slack UX (threads are familiar)

**Cons**:
- Need a mechanism to select agent at thread start
- Thread routing state must be persisted
- Users might forget which agent they're in

**Best for**: Shared channels where multiple agents are needed

### 3.3 DM Routing

**Pattern**: Users DM the bot and select/switch agents.

**Option A: Session-based (current Trinity model)**
- One agent per DM session (workspace -> agent mapping)
- Simple, no ambiguity

**Option B: Command-based switching**
- User sends `/switch sales-agent` or types `@bot switch to Sales Agent`
- Bot acknowledges and routes subsequent messages

**Option C: Selection prompt**
- On first DM, bot presents Block Kit buttons for agent selection
- Subsequent messages route to selected agent
- "Switch agent" button always available

**Pros** (Option C):
- No channel clutter
- Private conversations
- Clear agent selection UX

**Cons**:
- Only one conversation stream per DM (unless using threads)
- Switching agents mid-conversation may lose context
- Less discoverable than channels

### 3.4 Slash Command Routing

**Pattern**: `/ask <agent-name> <question>`

```
/ask sales-agent What's our Q4 pipeline?
/ask support-agent Customer #123 has an issue
/trinity list-agents
/trinity talk sales-agent
```

**Implementation**:
- Register one slash command (e.g., `/trinity` or `/ask`)
- Parse first word as agent name, rest as message
- Route to agent, post response as ephemeral or regular message
- Optionally start a thread for follow-ups

**Pros**:
- Explicit routing, no ambiguity
- Works in any channel
- No channel/thread management needed
- Easy to discover via `/trinity help`

**Cons**:
- Slash command responses have a 3-second acknowledgment timeout (must use `response_url` for async)
- Less conversational, more transactional
- Users must remember agent names (mitigated with autocomplete)
- Only one slash command per command name across all apps in workspace

### 3.5 App Home Tab as Agent Directory

**Pattern**: The App Home tab serves as an agent launcher/directory.

**Implementation**:
- `app_home_opened` event triggers `views.publish`
- Home tab shows list of available agents with descriptions
- Each agent has a "Start Chat" button
- Button click opens a modal or starts a DM thread with that agent
- Home tab can show recent conversations per agent
- Up to 100 blocks in Home tab (plenty for agent listing)

**Pros**:
- Central directory of all agents
- Rich UI with descriptions, avatars, status
- Discoverable -- users can browse agents
- Can show agent status (online/offline)

**Cons**:
- Requires users to navigate to App Home (not inline)
- Starting a conversation requires an extra step
- Cannot be the primary interaction surface

**Best for**: Discovery and navigation, complementing other patterns

### 3.6 Interactive Messages (Block Kit)

**Pattern**: Agent selection via buttons, dropdowns, or overflow menus.

```
Bot: "Which agent would you like to talk to?"
[Sales Agent] [Support Agent] [Engineering Agent]
-- or --
[Select an agent v]  (dropdown with all agents)
```

**Implementation**:
- Post Block Kit message with `static_select` or `button` elements
- Handle `block_actions` interaction payload
- Route subsequent messages based on selection
- Can include agent descriptions in the selection UI

**Pros**:
- Visual, user-friendly
- No need to remember agent names
- Can be embedded in any message or thread
- Supports rich agent info (description, avatar)

**Cons**:
- Extra interaction step before chatting
- Selection UI takes space in the conversation
- Must handle the interaction endpoint

---

## 4. Technical Deep Dive

### 4.1 Per-Message Identity via `chat:write.customize`

This is the **most important finding** for Trinity's use case.

**How it works**: With the `chat:write.customize` scope, every `chat.postMessage` call can include:

```python
await client.chat_postMessage(
    channel=channel_id,
    text=response_text,
    username=agent.display_name,      # "Sales Agent"
    icon_url=agent.avatar_url,        # "https://trinity.example.com/agents/sales/avatar.png"
    thread_ts=thread_ts,              # Keep in thread if applicable
    blocks=formatted_blocks           # Rich Block Kit content
)
```

**Behavior**:
- In channels: Message appears with custom name and avatar, no "via App" attribution visible
- In DMs: Message appears with custom name/avatar but the app attribution is visible in the conversation header
- The actual app identity is always discoverable by clicking the bot name
- Messages are editable/deletable only by the real app, not the "fake" identity

**This means Trinity can**: Use one Slack App, but make each agent's responses appear with that agent's name and avatar. From the user's perspective, it looks like different bots are responding.

### 4.2 App Home as Agent Directory

The App Home `views.publish` API supports:
- `header` blocks for titles
- `section` blocks with text + accessory (buttons, images)
- `actions` blocks with buttons, select menus, overflow menus
- `divider` blocks
- `image` blocks
- `context` blocks for metadata
- Up to 100 blocks total
- Dynamic per-user personalization
- Interactive elements that trigger modals or actions

**Example agent directory layout**:
```
[Header] Trinity Agents
[Divider]
[Section] Sales Agent - Handles sales inquiries     [Start Chat]
[Context] Online | 42 conversations today
[Section] Support Agent - Customer support           [Start Chat]
[Context] Online | 18 conversations today
[Divider]
[Section] Settings
[Button] Default Agent: [Sales Agent v]
```

This is a viable agent discovery and launch surface.

### 4.3 Slack's "Agents & AI Apps" Feature

This newer Slack feature provides a purpose-built surface for AI agent interactions:

- **Split view**: AI chat panel alongside the main channel
- **Threaded conversations**: Auto-organized with titles
- **Suggested prompts**: Up to 4 starter prompts
- **Context passing**: App knows which channel the user opened it from
- **Chat + History tabs**: Purpose-built navigation

**Key events**:
- `assistant_thread_started`: User opens the AI surface
- `assistant_thread_context_changed`: User switches channels
- `message.im`: Regular DM messages

**Limitation**: This creates one AI surface per app. For multiple agents, you'd need either:
- One app per agent (using this feature), or
- One app that internally routes (using suggested prompts like "Talk to Sales Agent")

**Current restriction**: Marketplace distribution requires partner status, but custom workspace installs work.

### 4.4 Slack Bookmarks and Canvas for Agent Binding

**Bookmarks API**: Channels can have up to 100 bookmarks. While primarily for links, a bookmark could theoretically mark a channel's bound agent (readable via `bookmarks.list`). However, this is hacky and not the intended use.

**Canvas API**: Channel canvases can display agent configuration info, but they're not machine-readable configuration -- they're rich-text documents.

**Verdict**: Neither is suitable for agent-to-channel binding. Use a database table.

### 4.5 Slack Connect for External Agent Access

Slack Connect allows sharing channels between organizations. Key facts for Trinity:

- **Bot access**: Bots are accessible to all users in shared channels where the bot is present
- **DMs**: Bots can DM external users who share a common channel
- **Slash commands**: NOT shared -- each org must install the app independently
- **Custom apps**: Your org's apps post messages visible to everyone, but only your org can use the app's shortcuts/commands

**Relevance to Trinity**: An organization could install the Trinity Slack app and invite external users to shared channels. The bot would respond to both internal and external users. However, external users cannot install the app or access slash commands -- they can only interact via @mentions and DMs in shared channels.

---

## 5. Practical UX Considerations

### 5.1 Best UX for Reaching Specific Agents

Based on the research, the optimal UX combines multiple patterns:

| Need | Best Pattern |
|------|-------------|
| "I want to browse available agents" | App Home tab with agent directory |
| "I want to ask Sales Agent a question" | @mention or `/ask sales-agent question` |
| "I want ongoing support conversation" | Dedicated channel #support-agent or DM thread |
| "I want to quickly switch agents" | Block Kit selection or prefix syntax |

### 5.2 How Other Platforms Handle "Which Agent Am I Talking To"

| Platform | Approach |
|----------|----------|
| **Dust.tt** | Prefix syntax (`@dust ~agent_name`), channel binding |
| **Relevance AI** | Keyword triggers, single bot identity |
| **OpenClaw** | Separate bot per agent (different Slack apps) |
| **Salesforce Agentforce** | Separate app per agent, @mention by agent name |
| **Intercom/Zendesk** | Single bot, routing is internal/invisible to user |

### 5.3 Agent Switching Mid-Conversation

**Challenge**: Users may want to switch agents within the same channel or thread.

**Approaches**:
- **Thread isolation**: Start a new thread for a new agent. Previous thread keeps its agent context.
- **Explicit switch command**: `switch to Support Agent` changes routing for subsequent messages
- **Prefix per message**: Every message includes the agent target (Dust.tt approach)
- **Selection after inactivity**: After 30min idle, prompt "Continue with Sales Agent or switch?"

**Recommendation**: Thread isolation is the cleanest -- each thread = one agent conversation. Users start a new thread to talk to a different agent.

### 5.4 Showing Which Agent Is Responding

**With `chat:write.customize`**:
- Agent name as `username` (e.g., "Sales Agent")
- Agent avatar as `icon_url`
- Optional: Prefix response with agent identity in text
- Optional: Use Block Kit context block showing agent name + badge

**Visual result**: Each message in the channel shows the agent's name and avatar, making it clear who is responding. Different agents in different threads will have different names/avatars.

---

## 6. Recommendation for Trinity

### Recommended Architecture: Single App + Hybrid Routing

Trinity should use **one Slack App** with:

1. **`chat:write.customize` for per-agent identity** (display name + avatar per message)
2. **Channel-based routing** as the primary pattern
3. **Thread-based routing** for multi-agent channels
4. **App Home** as agent directory/launcher
5. **Slash command** for quick agent interactions

### Why Single App (Not One App Per Agent)

| Factor | Single App | App Per Agent |
|--------|-----------|---------------|
| Setup complexity | One OAuth install | N OAuth installs |
| Free plan compatibility | 1 of 10 slots | N of 10 slots |
| Identity customization | Via `chat:write.customize` | Native (true separate bots) |
| DM experience | One DM channel, routing needed | True separate DMs per agent |
| Channel presence | One bot invited, multiple identities | N bots to invite |
| Management overhead | Low | High (N apps to maintain) |
| Auto-provisioning | Not needed | Need manifest API automation |
| User discoverability | One app to find, directory inside | Find each agent separately |

**The single-app approach wins on simplicity and scalability.** The `chat:write.customize` scope provides sufficient identity differentiation. Only if true separate DM conversations per agent are critical should the multi-app approach be considered.

### Proposed Implementation Layers

```
Layer 1: Slack App (single)
  - OAuth scopes: chat:write, chat:write.customize, im:history,
    app_mentions:read, channels:history, users:read.email
  - Events: message.im, app_mention, app_home_opened
  - Slash command: /trinity
  - App Home: Agent directory with interactive buttons

Layer 2: Routing Engine (backend)
  - Channel bindings table: channel_id -> agent_name
  - Thread bindings table: thread_ts -> agent_name
  - DM session state: user_id -> current_agent
  - Slash command parser: /trinity ask <agent> <question>
  - @mention parser: @Trinity ~agent_name question

Layer 3: Agent Identity (per message)
  - Each agent has: display_name, avatar_url, description
  - Every chat.postMessage includes username + icon_url
  - Block Kit formatting with agent context blocks

Layer 4: Agent Directory (App Home)
  - List all agents with status, description, avatar
  - "Start Chat" buttons per agent
  - "Set as channel default" dropdown
  - Recent conversations list
```

### Required OAuth Scopes

| Scope | Purpose |
|-------|---------|
| `chat:write` | Send messages |
| `chat:write.customize` | Override bot name/avatar per message |
| `im:history` | Read DM messages |
| `app_mentions:read` | Respond to @mentions in channels |
| `channels:history` | Read channel messages (for thread context) |
| `users:read.email` | Auto-verify users via Slack profile |
| `commands` | Slash command support |
| `assistant:write` | (Optional) Enable Agents & AI Apps split view |

### Routing Priority

When a message arrives, determine the target agent in this order:

1. **Thread binding**: If message is in a thread with an existing agent binding, route to that agent
2. **Channel binding**: If channel has a default agent, route to that agent
3. **Prefix parsing**: Check for `~agent_name` or `+agent_name` prefix in message text
4. **Slash command**: Parse `/trinity ask <agent> <question>`
5. **DM session**: If in DM, use the user's current agent selection
6. **Default agent**: Fall back to workspace default agent (configurable)

### Migration Path from Current Implementation

Trinity's current Slack integration (SLACK-001) uses:
- One workspace = one public link = one agent
- DM-only routing
- HTTP webhooks

The migration to multi-agent would:
1. Add `chat:write.customize` scope to existing OAuth flow
2. Add `app_mentions:read` + `channels:history` scopes for channel support
3. Extend `slack_link_connections` or add `channel_bindings` table for per-channel routing
4. Store agent `display_name` + `avatar_url` for identity override
5. Update `chat.postMessage` calls to include `username` + `icon_url`
6. Add App Home with agent directory
7. Add slash command for quick interactions

This can be done incrementally without breaking the existing single-agent DM flow.

### Future Considerations

- **Slack's Agents & AI Apps feature**: As this matures and opens beyond select partners, Trinity should adopt the split view surface for a more native AI chat experience
- **App-per-agent option**: Offer as an advanced configuration for users who need true separate DM conversations (using `apps.manifest.create` for auto-provisioning)
- **Slack Connect**: Document how external organizations can interact with Trinity agents via shared channels

---

## Sources

### Slack Official Documentation
- [chat.postMessage method](https://docs.slack.dev/reference/methods/chat.postMessage/)
- [chat:write.customize scope](https://docs.slack.dev/reference/scopes/chat.write.customize/)
- [apps.manifest.create method](https://docs.slack.dev/reference/methods/apps.manifest.create/)
- [Configuring apps with app manifests](https://docs.slack.dev/app-manifests/configuring-apps-with-app-manifests/)
- [App Home](https://docs.slack.dev/surfaces/app-home/)
- [AI in Slack apps overview](https://docs.slack.dev/ai/)
- [Developing AI apps](https://docs.slack.dev/ai/developing-ai-apps/)
- [Split view](https://docs.slack.dev/surfaces/split-view/)
- [Block Kit](https://docs.slack.dev/block-kit/)
- [Implementing slash commands](https://docs.slack.dev/interactivity/implementing-slash-commands/)
- [Understanding Slack Connect](https://docs.slack.dev/apis/slack-connect/)
- [Rate limits](https://docs.slack.dev/apis/web-api/rate-limits/)
- [Usage limits for free workspaces](https://slack.com/help/articles/115002422943-Usage-limits-for-free-workspaces)
- [Slack plans and features](https://slack.com/help/articles/115003205446-Slack-plans-and-features)
- [Workflow Builder conditional branching](https://slack.com/blog/news/conditional-branching-workflow-builder)
- [Handling user interaction](https://docs.slack.dev/interactivity/handling-user-interaction/)

### Multi-Agent Platform References
- [Dust.tt Slack Integration](https://dust.tt/home/slack/slack-integration)
- [Dust Slack docs](https://docs.dust.tt/docs/slack)
- [Dust blog: Slack AI agents](https://dust.tt/blog/slack-ai-agents)
- [Relevance AI Slack integration](https://relevanceai.com/docs/integrations/popular-integrations/slack)
- [OpenClaw multi-agent Slack setup](https://gist.github.com/rafaelquintanilha/9ca5ae6173cd0682026754cfefe26d3f)
- [OpenClaw multi-agent routing](https://docs.openclaw.ai/concepts/multi-agent)
- [Salesforce Agentforce in Slack](https://slack.com/ai-agents)
- [Salesforce Agentforce](https://www.salesforce.com/slack/agentforce/)

### Microsoft Teams
- [Teams bot configuration](https://learn.microsoft.com/en-us/microsoftteams/platform/toolkit/configure-bot-capability)
- [Single Teams app routing to different bots](https://learn.microsoft.com/en-us/answers/questions/1611031/how-to-use-a-single-custom-teams-app-that-points-t)

### Other References
- [LangChain Slack agent integration](https://docs.langchain.com/langsmith/agent-builder-slack-app)
- [Cloudflare Slack agent guide](https://developers.cloudflare.com/agents/guides/slack-agent/)
- [Vercel Slack Agents Academy](https://vercel.com/academy/slack-agents/views-and-app-home)
