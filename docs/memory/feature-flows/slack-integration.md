# Slack Integration for Public Links (SLACK-001)

> **Status**: Complete
> **Created**: 2026-02-25
> **Spec**: `docs/requirements/SLACK_INTEGRATION.md`

## Overview

Enables Slack as a delivery channel for public agent links. Users can chat with Trinity agents via DMs to a Slack bot, using the same security model as web-based public links.

## User Stories

1. **As an agent owner**, I want to connect my Slack workspace to a public link so users can chat with my agent via DM.
2. **As a Slack user**, I want to DM a bot to interact with a Trinity agent without leaving Slack.
3. **As an admin**, I want email verification for Slack users to track who uses my agent.

## Architecture

### Deployment Model

```
Environment Variables (src/backend/config.py:57-62):
- SLACK_SIGNING_SECRET    # From Slack App settings (line 59)
- SLACK_CLIENT_ID         # For OAuth flow (line 60)
- SLACK_CLIENT_SECRET     # For OAuth flow (line 61)
- SLACK_AUTO_VERIFY_EMAIL # Auto-verify via Slack profile email (line 62)
- PUBLIC_CHAT_URL         # Public-facing URL for Slack callbacks (line 45)
- FRONTEND_URL            # Admin UI URL for OAuth redirects (line 41)
```

### Data Flow (DM-Only)

```
User sends DM to bot
       |
       v
Slack API (message.im event)
       |
       v
POST ${PUBLIC_CHAT_URL}/api/public/slack/events
       |
       +-> 1. Verify Slack signature (routers/slack.py:69-76)
       +-> 2. Lookup link by team_id (routers/slack.py:132)
       +-> 3. Check user verification (routers/slack.py:152-157)
       +-> 4. Get/create session (routers/slack.py:299)
       +-> 5. Forward to agent via /api/task (routers/slack.py:306-316)
       +-> 6. Send response via chat.postMessage (routers/slack.py:166)
```

Key simplification: One Slack workspace = One public link = One agent

## Entry Points

### Owner Interface
- **UI**: `src/frontend/src/components/PublicLinksPanel.vue:125-181` - Slack section within link card
- **API**: `POST /api/agents/{name}/public-links/{id}/slack/connect` - Initiates OAuth

### Public Interface (Slack Events)
- **API**: `POST /api/public/slack/events` - Receives all Slack events
- **API**: `GET /api/public/slack/oauth/callback` - OAuth completion redirect

## Database Schema

### Tables

Defined in `src/backend/db/schema.py:476-521`:

**slack_link_connections** (lines 479-492):
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | Connection UUID |
| link_id | TEXT FK | Public link (UNIQUE) |
| slack_team_id | TEXT | Slack workspace ID (UNIQUE) |
| slack_team_name | TEXT | Display name |
| slack_bot_token | TEXT | OAuth access token |
| connected_by | TEXT FK | User who connected |
| connected_at | TEXT | ISO timestamp |
| enabled | INTEGER | 1=active, 0=disabled |

**slack_user_verifications** (lines 494-506):
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | Verification UUID |
| link_id | TEXT FK | Public link |
| slack_user_id | TEXT | Slack user ID |
| slack_team_id | TEXT | Slack workspace |
| verified_email | TEXT | Verified email address |
| verification_method | TEXT | 'slack_profile' or 'email_code' |
| verified_at | TEXT | ISO timestamp |

**slack_pending_verifications** (lines 508-521):
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | Pending verification UUID |
| link_id | TEXT FK | Public link |
| slack_user_id | TEXT | Slack user ID |
| slack_team_id | TEXT | Slack workspace |
| email | TEXT | Email being verified |
| code | TEXT | 6-digit verification code |
| created_at | TEXT | ISO timestamp |
| expires_at | TEXT | Expiration (10 minutes) |
| state | TEXT | 'awaiting_email' or 'awaiting_code' |

### Session Reuse

Slack sessions use the existing `public_chat_sessions` table with:
- `identifier_type = 'slack'`
- `session_identifier = '{team_id}:{user_id}'`

## API Endpoints

### Public Endpoints (No Auth)

| Endpoint | Method | File:Line | Handler |
|----------|--------|-----------|---------|
| `/api/public/slack/events` | POST | `routers/slack.py:53` | `handle_slack_event()` |
| `/api/public/slack/oauth/callback` | GET | `routers/slack.py:349` | `slack_oauth_callback()` |

### Authenticated Endpoints

| Endpoint | Method | File:Line | Handler |
|----------|--------|-----------|---------|
| `/api/agents/{name}/public-links/{id}/slack` | GET | `routers/slack.py:417` | `get_slack_connection_status()` |
| `/api/agents/{name}/public-links/{id}/slack` | PUT | `routers/slack.py:516` | `update_slack_connection()` |
| `/api/agents/{name}/public-links/{id}/slack` | DELETE | `routers/slack.py:489` | `disconnect_slack()` |
| `/api/agents/{name}/public-links/{id}/slack/connect` | POST | `routers/slack.py:453` | `initiate_slack_oauth()` |

## Implementation Files

### Backend

| File | Line Range | Description |
|------|------------|-------------|
| `src/backend/config.py` | 57-62 | `SLACK_SIGNING_SECRET`, `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_AUTO_VERIFY_EMAIL` |
| `src/backend/db/schema.py` | 476-521 | 3 table definitions |
| `src/backend/db/migrations.py` | 57, 490-527 | Migration #20 `_migrate_slack_integration_tables()` |
| `src/backend/db/slack.py` | 1-371 | `SlackOperations` class (371 lines) |
| `src/backend/services/slack_service.py` | 1-314 | `SlackService` class (314 lines) |
| `src/backend/routers/slack.py` | 1-543 | Public + auth routers (543 lines) |
| `src/backend/db_models.py` | 810-890 | 8 Pydantic models |
| `src/backend/database.py` | 125, 250, 1060-1113 | Import, init, delegation methods |
| `src/backend/main.py` | 65, 327-328 | Import and router mounting |

### Frontend

| File | Line Range | Description |
|------|------------|-------------|
| `src/frontend/src/components/PublicLinksPanel.vue` | 125-181, 377, 407-408, 533-601, 660-675 | Slack UI section |

## Backend Layer

### SlackOperations Class (`src/backend/db/slack.py`)

| Method | Line | Description |
|--------|------|-------------|
| `create_slack_connection()` | 24-45 | Create new workspace connection |
| `get_slack_connection()` | 47-62 | Get by connection ID |
| `get_slack_connection_by_link()` | 64-79 | Get by public link ID |
| `get_slack_connection_by_team()` | 81-101 | Get by Slack team ID (joins link data) |
| `update_slack_connection()` | 103-134 | Update enabled/team_name |
| `delete_slack_connection()` | 136-151 | Delete with cascade cleanup |
| `delete_slack_connection_by_link()` | 153-163 | Delete by link ID |
| `get_user_verification()` | 182-210 | Check if user is verified |
| `create_user_verification()` | 212-234 | Create verification record (upsert) |
| `get_pending_verification()` | 240-260 | Get active pending verification |
| `create_pending_verification()` | 262-291 | Start verification flow |
| `update_pending_verification()` | 293-330 | Transition state machine |
| `delete_pending_verification()` | 332-345 | Remove after success |
| `cleanup_expired_pending_verifications()` | 347-356 | Cleanup job |

### SlackService Class (`src/backend/services/slack_service.py`)

| Method | Line | Description |
|--------|------|-------------|
| `verify_slack_signature()` | 52-86 | HMAC-SHA256 signature verification |
| `get_oauth_url()` | 92-106 | Generate OAuth URL with scopes |
| `exchange_oauth_code()` | 108-146 | Exchange code for access token |
| `encode_oauth_state()` | 148-170 | Create signed state token |
| `decode_oauth_state()` | 172-200 | Verify and decode state token |
| `send_message()` | 206-237 | Send via chat.postMessage |
| `get_user_email()` | 239-268 | Get email from Slack profile |
| `open_dm_channel()` | 270-296 | Open DM channel with user |
| `get_oauth_callback_redirect()` | 298-309 | Build redirect URL |

### Router Handlers (`src/backend/routers/slack.py`)

**Public Router** (prefix `/api/public/slack`):

| Handler | Line | Description |
|---------|------|-------------|
| `handle_slack_event()` | 53-105 | Main event handler |
| `_handle_slack_dm()` | 108-173 | Process DM messages |
| `_handle_slack_verification()` | 176-280 | Verification state machine |
| `_forward_to_agent()` | 283-327 | Forward to agent, get response |
| `slack_oauth_callback()` | 349-407 | OAuth completion handler |

**Auth Router** (prefix `/api/agents`):

| Handler | Line | Description |
|---------|------|-------------|
| `get_slack_connection_status()` | 417-450 | Get connection status |
| `initiate_slack_oauth()` | 453-486 | Start OAuth flow |
| `disconnect_slack()` | 489-513 | Disconnect workspace |
| `update_slack_connection()` | 516-542 | Update settings |

### Database Delegation (`src/backend/database.py:1060-1113`)

```python
# Line 1063-1067
def create_slack_connection(self, link_id, slack_team_id, slack_team_name,
                            slack_bot_token, connected_by):
    return self._slack_ops.create_slack_connection(...)

# Line 1087-1088
def get_slack_user_verification(self, link_id, slack_user_id, slack_team_id):
    return self._slack_ops.get_user_verification(...)
```

## Frontend Layer

### PublicLinksPanel.vue

**State** (lines 407-408):
```javascript
const slackConnections = ref({})  // { linkId: { connected, team_name, enabled, ... } }
const slackLoading = ref({})      // { linkId: true/false }
```

**Methods**:

| Method | Line | Description |
|--------|------|-------------|
| `fetchSlackStatus()` | 529-543 | Load connection status for a link |
| `connectSlack()` | 549-567 | Initiate OAuth flow (opens popup) |
| `toggleSlackEnabled()` | 569-586 | Enable/disable connection |
| `disconnectSlack()` | 588-605 | Remove Slack connection |

**Template** (lines 125-181):
- Line 127-131: Slack icon and label
- Line 135-143: "Connect Slack" button (not connected state)
- Line 147-175: Connected state (team badge, toggle, disconnect)
- Line 178-180: "Connected by X on Y" info line

**URL Parameter Handling** (lines 660-675):
```javascript
const slackStatus = urlParams.get('slack')
if (slackStatus === 'connected') {
  copyNotification.value = 'slack-connected'
  // ...
}
```

## Pydantic Models (`src/backend/db_models.py:810-890`)

| Model | Line | Description |
|-------|------|-------------|
| `SlackConnectionCreate` | 814-820 | Internal create request |
| `SlackConnection` | 823-831 | Connection record |
| `SlackConnectionStatus` | 834-841 | API response (no token) |
| `SlackOAuthInitResponse` | 844-846 | OAuth URL response |
| `SlackUserVerification` | 849-857 | Verified user record |
| `SlackPendingVerification` | 860-870 | In-progress verification |
| `SlackEvent` | 873-881 | Incoming Slack event |
| `SlackOAuthState` | 884-889 | OAuth state token fields |

## Verification Flow

```
User sends first DM
       |
       v
Link requires email? (routers/slack.py:152)
       |
   +---+---+
   | NO    | YES
   v       v
[Chat]  User already verified? (routers/slack.py:191-192)
            |
        +---+---+
        | NO    | YES
        v       v
    SLACK_AUTO_VERIFY_EMAIL? (routers/slack.py:201)
        |       [Chat]
    +---+---+
    | YES   | NO
    v       v
  Auto-    "Reply with your email" (routers/slack.py:211-215)
  verify       |
    |          v
    v     Send code to email (routers/slack.py:237-242)
[Chat]         |
               v
          "Enter 6-digit code" (routers/slack.py:254-265)
               |
               v
          Verify -> [Chat] (routers/slack.py:267-278)
```

### Verification Messages

Defined in `routers/slack.py`:

**Initial prompt** (lines 211-215):
```
Hi! Before we chat, I need to verify your email address.
Please reply with your email address to continue.
```

**Code sent** (lines 239-242):
```
I've sent a 6-digit verification code to {email}.
Reply with the code to complete verification. The code expires in 10 minutes.
```

**Verification complete** (lines 273-277):
```
Verified! You can now chat with me.
What would you like to know?
```

## OAuth Flow

**Step-by-step**:

1. **User clicks "Connect Slack"** (`PublicLinksPanel.vue:549`)
2. **Frontend calls** `POST /api/agents/{name}/public-links/{id}/slack/connect` (line 553)
3. **Backend generates signed state** (`slack_service.py:148-170`)
4. **Backend returns OAuth URL** (`slack_service.py:92-106`)
   - Scopes: `im:history,chat:write,users:read.email`
5. **Frontend opens Slack OAuth** (`PublicLinksPanel.vue:560`)
6. **User authorizes in Slack**
7. **Slack redirects to** `/api/public/slack/oauth/callback` (line 349)
8. **Backend validates state** (`routers/slack.py:370-374`)
9. **Backend exchanges code for token** (`slack_service.py:108-146`)
10. **Backend creates connection** (`routers/slack.py:388-395`)
11. **Redirect to frontend with** `?slack=connected` (`slack_service.py:307`)
12. **Frontend shows success notification** (`PublicLinksPanel.vue:662-667`)

## Security

### Request Verification (`slack_service.py:52-86`)

```python
# Line 75-80
sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
expected_signature = 'v0=' + hmac.new(
    SLACK_SIGNING_SECRET.encode('utf-8'),
    sig_basestring.encode('utf-8'),
    hashlib.sha256
).hexdigest()
```

- 5-minute timestamp tolerance (line 69)
- Constant-time comparison (line 83)

### OAuth State Token (`slack_service.py:148-200`)

- Encodes `link_id`, `agent_name`, `user_id`, `timestamp`
- HMAC-SHA256 signed with `SECRET_KEY`
- 15-minute expiry (line 193)

### Authorization Checks

| Endpoint | Check | File:Line |
|----------|-------|-----------|
| Connect Slack | Owner or admin | `routers/slack.py:461-463` |
| Disconnect | Owner or admin | `routers/slack.py:497-499` |
| Update | Owner or admin | `routers/slack.py:525-527` |
| Get status | Any access level | `routers/slack.py:425-427` |

## Error Handling

| Error Case | HTTP Status | Handler Location |
|------------|-------------|------------------|
| Signature verification failed | 200* | `routers/slack.py:73-76` |
| Invalid OAuth state | Redirect | `routers/slack.py:372-374` |
| OAuth token exchange failed | Redirect | `routers/slack.py:382-385` |
| Link not found | 404 | `routers/slack.py:431-432` |
| Access denied | 403 | `routers/slack.py:427-428` |
| Already connected | 400 | `routers/slack.py:472-473` |
| Slack not configured | 400 | `routers/slack.py:475-476` |

*Slack events always return 200 to prevent retries

## Frontend UI

### PublicLinksPanel Integration (lines 125-181)

```
+---------------------------------------------------------------+
| Public Link: "Customer Support"                                |
+---------------------------------------------------------------+
| ... existing link content (URL, copy buttons, etc.) ...        |
|                                                                |
| -----------------------------------------------------------   |
| [Slack icon] Slack              [Connect Slack]     <- Line 136-143
|                                                                |
| -- OR (when connected) ----------------------------------      |
|                                                                |
| [Slack icon] Slack    [* Acme Corp] [toggle] [x]   <- Line 147-175
| Connected by admin@example.com on Feb 25, 2026     <- Line 178-180
+---------------------------------------------------------------+
```

### UI States

| State | Elements Shown |
|-------|----------------|
| Not connected | "Connect Slack" button |
| Loading | "Connecting..." text |
| Connected + Enabled | Green badge, disable toggle, disconnect button |
| Connected + Disabled | Green badge, enable toggle, disconnect button |

## Session Persistence

Slack sessions reuse the existing public chat session infrastructure:

```python
# routers/slack.py:296
session_identifier = f"{team_id}:{user_id}"

# routers/slack.py:299
session = db.get_or_create_public_chat_session(link_id, session_identifier, "slack")
```

Context is built using `db.build_public_chat_context()` (line 302), same as web public links.

## Testing

### Unit Tests

- `test_slack_signature_verification` - Valid/invalid/expired signatures
- `test_url_verification_challenge` - Returns challenge for Slack setup
- `test_lookup_link_by_team` - Finds correct link for workspace
- `test_user_verification_flow` - Email code state machine
- `test_auto_verify_with_email_scope` - Auto-verifies via Slack profile

### Integration Tests

- `test_oauth_flow_complete` - Full OAuth -> token storage -> redirect
- `test_dm_to_response` - Slack DM event -> agent call -> response
- `test_session_persistence` - Multiple messages maintain context

### Manual Tests

1. Connect Slack -> DM bot -> receive response
2. Enable "require email" -> DM bot -> enter email -> enter code -> chat
3. Disconnect -> verify DMs no longer work
4. Re-connect -> verify previous sessions are cleared

## Related

- **[Public Agent Links](public-agent-links.md)** (15.1) - Base infrastructure, session persistence (PUB-005)
- **Email Verification** - Reused for Slack user verification (`email_service.send_verification_code()`)
- **Session Persistence** - `public_chat_sessions` with `identifier_type='slack'`

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-02-25 | Claude | Initial implementation |
| 2026-02-25 | Claude | Enhanced with exact line numbers and code references |
