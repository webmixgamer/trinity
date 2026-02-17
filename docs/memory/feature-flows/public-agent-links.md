# Feature Flow: Public Agent Links (12.2)

## Overview

Public Agent Links allow agent owners to generate shareable URLs that enable unauthenticated users to chat with their agents. This feature supports optional email verification, usage tracking, and rate limiting.

## User Stories

1. **As an agent owner**, I want to create public links so prospects can demo my agent without logging in.
2. **As an agent owner**, I want to require email verification to track who uses my agent.
3. **As an agent owner**, I want to see usage statistics for each public link.
4. **As a public user**, I want to chat with an agent using just a URL.
5. **As a public user**, I want a simple verification flow if required.

## Architecture

```
+-------------------------------------------------------------------+
|                         Frontend                                   |
+-------------------------------------------------------------------+
|  PublicLinksPanel.vue          PublicChat.vue                     |
|  (Owner management)            (Public chat interface)            |
|                                                                    |
|  - Create/edit/delete links    - Email verification flow          |
|  - Copy link URL               - Chat interface                   |
|  - View usage stats            - Session management               |
|  - Enable/disable              - Error handling                   |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                         Backend API                                |
+-------------------------------------------------------------------+
|  routers/public_links.py       routers/public.py                  |
|  (Authenticated)               (Unauthenticated)                  |
|                                                                    |
|  - CRUD endpoints              - Link validation                  |
|  - Owner verification          - Email verification               |
|  - Usage stats                 - Public chat                      |
+-------------------------------------------------------------------+
                                  |
         +------------------------+------------------------+
         v                        v                        v
+------------------+  +----------------------+  +------------------+
|   SQLite DB      |  |   Email Service      |  |   Agent Server   |
+------------------+  +----------------------+  +------------------+
| agent_public_    |  | Console (dev)        |  | /api/task        |
|   links          |  | SMTP                 |  | (parallel exec)  |
| public_link_     |  | SendGrid             |  |                  |
|   verifications  |  |                      |  |                  |
| public_link_     |  |                      |  |                  |
|   usage          |  |                      |  |                  |
+------------------+  +----------------------+  +------------------+
```

## Entry Points

### Owner Interface
- **UI**: `src/frontend/src/views/AgentDetail.vue:167` - "Public Links" tab content
- **Component**: `src/frontend/src/components/PublicLinksPanel.vue` - Full management panel

### Public Interface
- **UI**: `src/frontend/src/views/PublicChat.vue` - Public chat page
- **Route**: `/chat/:token` defined in `src/frontend/src/router/index.js:18-22`

## Data Flow

### 1. Create Public Link (Owner)

```
Owner (AgentDetail) -> POST /api/agents/{name}/public-links
                    -> Backend validates ownership
                    -> Generate unique token (secrets.token_urlsafe(24))
                    -> Insert into agent_public_links
                    -> Return link with URL
```

### 2. Public Chat (No Email Required)

```
Public User -> GET /api/public/link/{token}
            -> Backend returns {valid: true, require_email: false}

Public User -> POST /api/public/chat/{token}
            -> Backend validates token
            -> Check rate limit (30/min per IP)
            -> Record usage
            -> Proxy to agent's /api/task endpoint
            -> Return response
```

### 3. Public Chat (Email Required)

```
Public User -> GET /api/public/link/{token}
            -> Backend returns {valid: true, require_email: true}

Public User -> POST /api/public/verify/request
            -> Backend generates 6-digit code
            -> Email service sends code
            -> Return {expires_in_seconds: 600}

Public User -> POST /api/public/verify/confirm
            -> Backend validates code
            -> Generate session_token (24h validity)
            -> Return {session_token: "..."}

Public User -> POST /api/public/chat/{token}
              {message: "...", session_token: "..."}
            -> Backend validates session
            -> Chat proceeds as normal
```

## Frontend Layer

### Components

| File | Line | Description |
|------|------|-------------|
| `src/frontend/src/views/AgentDetail.vue` | 167 | Public Links tab content |
| `src/frontend/src/views/AgentDetail.vue` | 169 | PublicLinksPanel component usage |
| `src/frontend/src/views/AgentDetail.vue` | 230 | Import statement |
| `src/frontend/src/views/AgentDetail.vue` | 443-446 | Tab configuration logic |
| `src/frontend/src/components/PublicLinksPanel.vue` | 1-503 | Owner management panel |
| `src/frontend/src/views/PublicChat.vue` | 1-538 | Public chat interface (PUB-003 intro, PUB-004 header metadata) |

### PublicLinksPanel.vue Methods

| Method | Line | Description |
|--------|------|-------------|
| `loadLinks()` | 345 | Fetch all links for agent |
| `saveLink()` | 360 | Create or update link |
| `toggleLink()` | 400 | Enable/disable link |
| `editLink()` | 417 | Open edit modal |
| `deleteLink()` | 433 | Delete with confirmation |
| `copyLink()` | 452 | Copy URL to clipboard |

### PublicChat.vue Methods

| Method | Line | Description |
|--------|------|-------------|
| `loadLinkInfo()` | 306 | Validate link token, receives agent metadata |
| `requestCode()` | 344 | Request verification email |
| `verifyCode()` | 367 | Confirm 6-digit code, calls `fetchIntro()` |
| `fetchIntro()` | 406 | Fetch agent introduction (PUB-003) |
| `sendMessage()` | 441 | Send chat message |

### Router Configuration

```javascript
// src/frontend/src/router/index.js:18-22
{
  path: '/chat/:token',
  name: 'PublicChat',
  component: () => import('../views/PublicChat.vue'),
  meta: { requiresAuth: false }
}
```

## Backend Layer

### Owner Endpoints (Authenticated)

| Endpoint | File:Line | Handler |
|----------|-----------|---------|
| `POST /api/agents/{name}/public-links` | `public_links.py:64` | `create_public_link()` |
| `GET /api/agents/{name}/public-links` | `public_links.py:100` | `list_public_links()` |
| `GET /api/agents/{name}/public-links/{id}` | `public_links.py:115` | `get_public_link()` |
| `PUT /api/agents/{name}/public-links/{id}` | `public_links.py:134` | `update_public_link()` |
| `DELETE /api/agents/{name}/public-links/{id}` | `public_links.py:175` | `delete_public_link()` |

### Public Endpoints (Unauthenticated)

| Endpoint | File:Line | Handler |
|----------|-----------|---------|
| `GET /api/public/link/{token}` | `public.py:43` | `get_public_link_info()` |
| `POST /api/public/verify/request` | `public.py:73` | `request_verification_code()` |
| `POST /api/public/verify/confirm` | `public.py:130` | `confirm_verification_code()` |
| `POST /api/public/chat/{token}` | `public.py:166` | `public_chat()` |
| `GET /api/public/intro/{token}` | `public.py:276` | `get_agent_intro()` |

### Database Operations

| Method | File:Line | Description |
|--------|-----------|-------------|
| `create_public_link()` | `db/public_links.py:28` | Create new link with token |
| `get_public_link()` | `db/public_links.py:52` | Get link by ID |
| `get_public_link_by_token()` | `db/public_links.py:69` | Get link by URL token |
| `list_agent_public_links()` | `db/public_links.py:86` | List all links for agent |
| `update_public_link()` | `db/public_links.py:101` | Update link properties |
| `delete_public_link()` | `db/public_links.py:142` | Delete link and related data |
| `delete_agent_public_links()` | `db/public_links.py:156` | Cascade delete for agent |
| `is_link_valid()` | `db/public_links.py:176` | Validate token (enabled, not expired) |
| `create_verification()` | `db/public_links.py:200` | Create 6-digit verification code |
| `verify_code()` | `db/public_links.py:235` | Verify code, create session |
| `validate_session()` | `db/public_links.py:281` | Validate session token |
| `count_recent_verification_requests()` | `db/public_links.py:305` | Verification rate limit |
| `record_usage()` | `db/public_links.py:324` | Record chat message usage |
| `get_link_usage_stats()` | `db/public_links.py:363` | Get usage statistics |
| `count_recent_messages_by_ip()` | `db/public_links.py:407` | Rate limit check |

### Pydantic Models

| Model | File:Line | Description |
|-------|-----------|-------------|
| `PublicLinkCreate` | `db_models.py:301` | Create link request |
| `PublicLinkUpdate` | `db_models.py:308` | Update link request |
| `PublicLink` | `db_models.py:316` | Base link model |
| `PublicLinkWithUrl` | `db_models.py:329` | Link with generated URL |
| `PublicLinkInfo` | `db_models.py:336` | Public-facing link info (includes agent metadata) |
| `VerificationRequest` | `db_models.py:343` | Request verification code |
| `VerificationConfirm` | `db_models.py:349` | Confirm verification code |
| `VerificationResponse` | `db_models.py:356` | Verification result |
| `PublicChatRequest` | `db_models.py:364` | Chat message request |
| `PublicChatResponse` | `db_models.py:370` | Chat message response |

## Database Schema

### agent_public_links

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | Unique link ID |
| agent_name | TEXT FK | Target agent |
| token | TEXT UNIQUE | URL-safe token for link |
| created_by | TEXT FK | Owner user ID |
| created_at | TEXT | ISO timestamp |
| expires_at | TEXT | Optional expiration |
| enabled | INTEGER | 1=active, 0=disabled |
| name | TEXT | Optional friendly name |
| require_email | INTEGER | 1=yes, 0=no |

### public_link_verifications

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | Verification ID |
| link_id | TEXT FK | Parent link |
| email | TEXT | User's email |
| code | TEXT | 6-digit code |
| created_at | TEXT | Request time |
| expires_at | TEXT | Code expiration |
| verified | INTEGER | 0=pending, 1=verified, -1=invalidated |
| session_token | TEXT | Session after verification |
| session_expires_at | TEXT | Session expiration |

### public_link_usage

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | Usage record ID |
| link_id | TEXT FK | Parent link |
| email | TEXT | Verified email (if any) |
| ip_address | TEXT | Client IP |
| message_count | INTEGER | Messages sent |
| created_at | TEXT | First message time |
| last_used_at | TEXT | Most recent message |

## Side Effects

### WebSocket Broadcasts

```javascript
// Link created
{ "event": "public_link_created", "data": { "agent_name": "...", "link_id": "...", "require_email": true/false } }

// Link updated
{ "event": "public_link_updated", "data": { "agent_name": "...", "link_id": "...", "enabled": true/false } }

// Link deleted
{ "event": "public_link_deleted", "data": { "agent_name": "...", "link_id": "..." } }
```

### Audit Logging

| Event Type | Action | Trigger |
|------------|--------|---------|
| `public_link` | `create` | Owner creates link |
| `public_link` | `update` | Owner modifies link |
| `public_link` | `delete` | Owner deletes link |
| `public_verification` | `request_code` | User requests email code |
| `public_verification` | `confirm_code` | User confirms code |
| `public_chat` | `message` | User sends chat message |

## Security Considerations

1. **Rate Limiting**: 30 messages/minute per IP prevents abuse
2. **Email Verification**: Optional but recommended for tracking
3. **Session Tokens**: 24-hour validity, tied to link+email
4. **Verification Codes**: 10-minute expiry, 3 requests/10 min per email
5. **Audit Logging**: All public access logged
6. **No Sensitive Data**: Public endpoints don't expose link IDs or agent details
7. **Owner-Only Management**: Only agent owners with `can_share` can create/manage links

## Configuration

### Environment Variables

```bash
# Email Provider
EMAIL_PROVIDER=console  # console, smtp, sendgrid

# SMTP Settings
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=secret
SMTP_FROM=noreply@example.com

# SendGrid
SENDGRID_API_KEY=SG.xxx

# Frontend URL (for internal link generation)
# Default: http://localhost (port 80, Docker deployment)
# For Vite dev server: http://localhost:5173
FRONTEND_URL=http://localhost

# External URL for public chat links (PUB-002)
# Set when you want to share links with users outside VPN
# Examples: Tailscale Funnel, GCP Load Balancer, Cloudflare Tunnel
# When set, enables "Copy External Link" button in PublicLinksPanel
PUBLIC_CHAT_URL=
```

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Link not found | 200* | `{valid: false, reason: "not_found"}` |
| Link disabled | 200* | `{valid: false, reason: "disabled"}` |
| Link expired | 200* | `{valid: false, reason: "expired"}` |
| Agent not found | 404 | Agent not found |
| Permission denied | 403 | Only the agent owner can... |
| Session required | 401 | Session token required for this link |
| Session expired | 401 | Invalid or expired session |
| Rate limited | 429 | Too many requests |
| Agent unavailable | 503 | Agent is not available |
| Agent timeout | 504 | Request timed out |
| Agent error | 502 | Failed to process your request |

*Note: Public link info endpoint returns 200 with valid=false for invalid links (not 404)

## Files

### Backend

| File | Description |
|------|-------------|
| `src/backend/db/public_links.py` | Database operations class |
| `src/backend/routers/public_links.py` | Owner CRUD endpoints (206 lines) |
| `src/backend/routers/public_links.py:30-39` | URL builders: `_build_public_url()`, `_build_external_url()` |
| `src/backend/routers/public_links.py:42-61` | `_link_to_response()` - converts DB dict to API model |
| `src/backend/routers/public.py` | Public endpoints |
| `src/backend/services/email_service.py` | Email sending service |
| `src/backend/db_models.py:301-374` | Pydantic models |
| `src/backend/db_models.py:329-333` | `PublicLinkWithUrl` with `external_url` field |
| `src/backend/database.py` | Schema, imports, delegation |
| `src/backend/config.py:43-45` | `PUBLIC_CHAT_URL` environment variable |
| `src/backend/config.py:86-88` | Auto-add `PUBLIC_CHAT_URL` to CORS origins |
| `src/backend/main.py:44-45,112,292-293` | Router registration |

### Frontend

| File | Description |
|------|-------------|
| `src/frontend/src/views/PublicChat.vue` | Public chat page (538 lines) |
| `src/frontend/src/components/PublicLinksPanel.vue` | Owner panel (503 lines) |
| `src/frontend/src/views/AgentDetail.vue` | Public Links tab integration |
| `src/frontend/src/router/index.js:18-22` | Route definition |

### Tests

| File | Description |
|------|-------------|
| `tests/test_public_links.py` | Comprehensive test suite |

## Testing

### Prerequisites

- Backend running on `localhost:8000`
- Frontend running on `localhost:3000`
- At least one running agent with the updated base image (must have `/api/task` endpoint)

**Note**: Agents created before the Parallel Headless Execution feature (Phase 12.1) need to be recreated with the updated base image for public chat to work. The `/api/task` endpoint is required for stateless parallel execution.

### Test File

`tests/test_public_links.py` - Comprehensive test suite

### Test Classes

| Class | Description |
|-------|-------------|
| `TestPublicLinkDatabase` | Verify database tables exist |
| `TestPublicEndpoints` | Test unauthenticated endpoints |
| `TestOwnerEndpointsNoAuth` | Verify auth is required |
| `TestOwnerEndpointsWithAuth` | Test authenticated CRUD |
| `TestPublicLinkLifecycle` | Full create/update/delete cycle |
| `TestEmailVerification` | Email verification flow |
| `TestPublicChat` | Public chat functionality |

### Test Results (2025-12-22)

| Test | Status | Notes |
|------|--------|-------|
| Database tables exist | Pass | 3 tables created |
| Public endpoint - invalid link | Pass | Returns `{valid: false, reason: "not_found"}` |
| Public endpoint - verification request (invalid) | Pass | Returns 404 |
| Public endpoint - verification confirm (invalid) | Pass | Returns 404 |
| Public endpoint - chat (invalid link) | Pass | Returns 404 |
| Owner endpoints require auth | Pass | Returns 401 without token |
| Create public link | Pass | Returns link with ID, token, URL |
| List owner links | Pass | Returns array with usage stats |
| Update link | Pass | Name and enabled state updated |
| Disable link - public sees disabled | Pass | Returns `{valid: false, reason: "disabled"}` |
| Re-enable link | Pass | Link becomes valid again |
| Delete link | Pass | Link removed from database |
| Public chat (no email required) | Skip | Requires agent with updated base image |
| Email verification flow | Pass | Codes sent (console mode) |

### How to Run Tests

```bash
# API tests via pytest
pytest tests/test_public_links.py -v

# Inside docker container
docker-compose exec backend python -m pytest tests/test_public_links.py -v
```

## Related Flows

- **Upstream**: Agent Lifecycle (agent must exist and be running)
- **Downstream**: Agent Chat (uses same `/api/task` endpoint)
- **Related**: Agent Sharing (manages `can_share` permission)

## External Public URL (PUB-002)

**Status**: Implemented (2026-02-16)
**Spec**: `docs/requirements/EXTERNAL_PUBLIC_URL.md`

Support for an external (internet-accessible) URL for public links, enabling sharing with users outside the Tailscale VPN.

### Data Flow

```
+-----------------------------+     +----------------------------------+
|  PublicLinksPanel.vue       |     |  Backend API                     |
+-----------------------------+     +----------------------------------+
|                             |     |                                  |
|  1. User clicks copy button |     |  GET /api/agents/{name}/public-links
|     - Internal (clipboard)  | <-- |  Returns: {url, external_url, ...}
|     - External (globe icon) |     |                                  |
|                             |     +----------------------------------+
|  2. copyLink(link, external)|                    |
|     - external=false: link.url                   |
|     - external=true: link.external_url           v
|                             |     +----------------------------------+
|  3. Notification:           |     |  config.py                       |
|     - "Internal link copied!"|     +----------------------------------+
|     - "External link copied!"|     |  PUBLIC_CHAT_URL env var        |
+-----------------------------+     |  (loaded at startup)             |
                                    +----------------------------------+
                                                   |
                                                   v
                                    +----------------------------------+
                                    |  public_links.py                 |
                                    +----------------------------------+
                                    |  _build_external_url(token)      |
                                    |    if PUBLIC_CHAT_URL:           |
                                    |      return f"{URL}/chat/{token}"|
                                    |    return None                   |
                                    +----------------------------------+
```

### Configuration

Set `PUBLIC_CHAT_URL` environment variable to your external URL:

```bash
# .env or docker-compose.yml
PUBLIC_CHAT_URL=https://public.example.com
```

When set:
1. The API returns `external_url` field in all public link responses
2. The UI shows a globe icon button to copy the external link
3. CORS is automatically configured to allow the external origin

### Backend Implementation

**Config (`src/backend/config.py:43-45`)**:
```python
# External URL for public chat links (Tailscale Funnel, Cloudflare Tunnel, etc.)
# When set, enables "Copy External Link" button in PublicLinksPanel
PUBLIC_CHAT_URL = os.getenv("PUBLIC_CHAT_URL", "")
```

**CORS Auto-Configuration (`src/backend/config.py:86-88`)**:
```python
# Automatically add PUBLIC_CHAT_URL to CORS if set
if PUBLIC_CHAT_URL:
    _extra_origins.append(PUBLIC_CHAT_URL)
```

**URL Builder (`src/backend/routers/public_links.py:35-39`)**:
```python
def _build_external_url(token: str) -> str | None:
    """Build the external public URL for a link token (if configured)."""
    if PUBLIC_CHAT_URL:
        return f"{PUBLIC_CHAT_URL}/chat/{token}"
    return None
```

**Response Assembly (`src/backend/routers/public_links.py:42-61`)**:
```python
def _link_to_response(link: dict, include_usage: bool = True) -> PublicLinkWithUrl:
    # ...
    return PublicLinkWithUrl(
        # ... other fields ...
        url=_build_public_url(link["token"]),        # Line 58: Internal URL
        external_url=_build_external_url(link["token"]),  # Line 59: External URL
        usage_stats=usage_stats
    )
```

**Model (`src/backend/db_models.py:329-333`)**:
```python
class PublicLinkWithUrl(PublicLink):
    """Public link with generated URL."""
    url: str  # Internal URL (VPN/tailnet)
    external_url: Optional[str] = None  # External URL (public internet via Funnel/Tunnel)
    usage_stats: Optional[dict] = None
```

### Frontend Implementation

**URL Preview (`src/frontend/src/components/PublicLinksPanel.vue:79-102`)**:
- Line 81: Displays `external_url` if available, otherwise `url`
- Lines 83-90: Internal copy button (clipboard icon)
- Lines 92-101: External copy button (globe icon, conditionally rendered)

```vue
<!-- URL preview - shows external URL if available -->
<code class="...">{{ link.external_url || link.url }}</code>

<!-- Internal link copy -->
<button @click="copyLink(link, false)" title="Copy internal link">
  <!-- clipboard icon -->
</button>

<!-- External link copy (only if external_url exists) -->
<button v-if="link.external_url" @click="copyLink(link, true)"
        title="Copy external link (public internet)">
  <!-- globe icon -->
</button>
```

**Copy Method (`src/frontend/src/components/PublicLinksPanel.vue:461-473`)**:
```javascript
const copyLink = async (link, external = false) => {
  try {
    const url = external && link.external_url ? link.external_url : link.url
    await navigator.clipboard.writeText(url)
    copyNotification.value = external ? 'external' : 'internal'
    setTimeout(() => {
      copyNotification.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy link:', err)
  }
}
```

**Notification (`src/frontend/src/components/PublicLinksPanel.vue:311-317`)**:
```vue
<div v-if="copyNotification" class="...">
  {{ copyNotification === 'external' ? 'External link copied!' : 'Internal link copied!' }}
</div>
```

### UI Behavior

| Scenario | Copy Icon | Globe Icon | URL Displayed |
|----------|-----------|------------|---------------|
| `PUBLIC_CHAT_URL` not set | Visible | Hidden | Internal URL (`FRONTEND_URL/chat/{token}`) |
| `PUBLIC_CHAT_URL` set | Visible | Visible | External URL (`PUBLIC_CHAT_URL/chat/{token}`) |

### Example API Response

```json
{
  "id": "link_abc123",
  "agent_name": "my-agent",
  "token": "xyz789...",
  "url": "http://localhost/chat/xyz789...",
  "external_url": "https://public.example.com/chat/xyz789...",
  "enabled": true,
  "require_email": false,
  "usage_stats": { "total_messages": 42, "unique_users": 5 }
}
```

### Infrastructure Requirements

The external URL requires separate infrastructure setup. Options:
- **Tailscale Funnel**: `tailscale funnel 80` (simplest)
- **GCP Load Balancer**: External IP with SSL termination
- **Cloudflare Tunnel**: `cloudflared tunnel`
- **ngrok**: `ngrok http 80`

See `docs/requirements/PUBLIC_EXTERNAL_ACCESS_SETUP.md` for setup guides.

---

## Agent Introduction (PUB-003)

**Status**: Implemented (2026-02-17)

When users access a public chat link, the agent automatically introduces itself before they start chatting.

### Data Flow

```
User opens /chat/{token}
        ↓
loadLinkInfo() - validate link
        ↓
Email verification (if required)
        ↓
fetchIntro() called
        ↓
GET /api/public/intro/{token}?session_token=...
        ↓
Backend sends INTRO_PROMPT to agent via /api/task
        ↓
Agent responds with 2-paragraph introduction
        ↓
Response displayed as first assistant message
```

### Backend Implementation

**Intro Prompt** (`public.py:267-273`):
```python
INTRO_PROMPT = """Provide a brief 2-paragraph introduction of yourself.

First paragraph: Who you are and what you do.
Second paragraph: Your purpose and how you can help the user.

Be concise, welcoming, and conversational. Do not use headers, bullet points, or markdown formatting."""
```

**Endpoint** (`public.py:276-356`):
- Validates link token and session (if email required)
- Sends intro prompt to agent via `/api/task`
- Returns `{"intro": "..."}`
- 60-second timeout for generation

### Frontend Implementation

**State** (`PublicChat.vue:270-273`):
```javascript
const introLoading = ref(false)
const introError = ref(null)
const introFetched = ref(false)
```

**fetchIntro()** (`PublicChat.vue:376-408`):
- Builds URL with session token if needed
- Adds response as first assistant message
- Sets `introFetched = true` on success or error

**Trigger Points**:
1. After email verification succeeds (`verifyCode()`)
2. On mount if no email needed or already verified (`onMounted()`)

**UI States**:
- Loading: "Getting ready..." with spinner
- Success: Intro message displayed in chat
- Error: Falls back to generic "Start a Conversation"

### User Experience

| Before | After |
|--------|-------|
| Generic "Start a Conversation" | Personalized agent introduction |
| User must ask what agent does | Agent proactively explains purpose |
| Cold start | Warm, welcoming interaction |

---

## Public Chat Header Metadata (PUB-004)

**Status**: Implemented (2026-02-17)

The public chat page header now displays agent metadata to provide users with context about who they are chatting with.

### Data Flow

```
User opens /chat/{token}
        |
        v
GET /api/public/link/{token}
        |
        v
Backend validates link token
        |
        v
Backend fetches agent metadata:
  1. AgentsDB.get_autonomy_enabled(agent_name) -> is_autonomous
  2. AgentsDB.get_read_only_mode(agent_name) -> is_read_only
  3. GET http://agent-{name}:8000/api/template/info -> display_name, description
        |
        v
Returns PublicLinkInfo with metadata fields
        |
        v
PublicChat.vue header displays:
  - Agent display name (or fallback to agent name)
  - Agent description (if available)
  - AUTO badge (amber) if is_autonomous
  - READ-ONLY badge (rose with lock icon) if is_read_only
```

### Backend Implementation

**Endpoint** (`public.py:44-103`):
```python
@router.get("/link/{token}", response_model=PublicLinkInfo)
async def get_public_link_info(token: str, request: Request):
    # ... validation ...

    # Get agent metadata from database
    agents_db = AgentsDB()
    is_autonomous = agents_db.get_autonomy_enabled(agent_name)
    read_only_data = agents_db.get_read_only_mode(agent_name)
    is_read_only = read_only_data.get("enabled", False)

    # Get display name and description from template.yaml (if agent running)
    if agent_available:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://agent-{agent_name}:8000/api/template/info")
            if response.status_code == 200:
                info = response.json()
                agent_display_name = info.get("name") or info.get("display_name") or agent_name
                agent_description = info.get("description")

    return PublicLinkInfo(
        valid=True,
        # ... other fields ...
        agent_display_name=agent_display_name,
        agent_description=agent_description,
        is_autonomous=is_autonomous,
        is_read_only=is_read_only
    )
```

**Model** (`db_models.py:336-346`):
```python
class PublicLinkInfo(BaseModel):
    """Public-facing link information (no sensitive data)."""
    valid: bool
    require_email: bool = False
    agent_available: bool = True
    reason: Optional[str] = None
    # Agent metadata (only populated when valid)
    agent_display_name: Optional[str] = None
    agent_description: Optional[str] = None
    is_autonomous: bool = False
    is_read_only: bool = False
```

### Frontend Implementation

**Header Template** (`PublicChat.vue:4-46`):
```vue
<header class="bg-white dark:bg-gray-800 shadow-sm py-3 px-4">
  <div class="max-w-3xl mx-auto">
    <div v-if="linkInfo && linkInfo.valid" class="space-y-1">
      <!-- Top row: Status dot, name, badges -->
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
          <span class="font-semibold text-gray-900 dark:text-white">
            {{ linkInfo.agent_display_name || 'Agent' }}
          </span>
        </div>
        <!-- Status badges -->
        <div class="flex items-center space-x-2">
          <span v-if="linkInfo.is_autonomous"
            class="... bg-amber-100 text-amber-800 ...">
            AUTO
          </span>
          <span v-if="linkInfo.is_read_only"
            class="... bg-rose-100 text-rose-800 ...">
            <svg><!-- lock icon --></svg>
            READ-ONLY
          </span>
        </div>
      </div>
      <!-- Description row -->
      <p v-if="linkInfo.agent_description"
        class="text-sm text-gray-500 dark:text-gray-400 line-clamp-2">
        {{ linkInfo.agent_description }}
      </p>
    </div>
  </div>
</header>
```

### API Response Example

```json
{
  "valid": true,
  "require_email": false,
  "agent_available": true,
  "reason": null,
  "agent_display_name": "Sales Assistant",
  "agent_description": "I help answer questions about our products and services.",
  "is_autonomous": true,
  "is_read_only": false
}
```

### UI Behavior

| Field | Display |
|-------|---------|
| `agent_display_name` | Header title (fallback: "Agent") |
| `agent_description` | Subtitle below name (truncated to 2 lines) |
| `is_autonomous` | Amber "AUTO" badge |
| `is_read_only` | Rose "READ-ONLY" badge with lock icon |

### Status Badges

| Badge | Color | Icon | Meaning |
|-------|-------|------|---------|
| AUTO | Amber (`bg-amber-100 text-amber-800`) | None | Agent runs autonomous scheduled executions |
| READ-ONLY | Rose (`bg-rose-100 text-rose-800`) | Lock | Agent cannot modify filesystem outside `.trinity` |

### Metadata Sources

| Field | Primary Source | Fallback |
|-------|---------------|----------|
| `agent_display_name` | `template.yaml` via `/api/template/info` | Container label `trinity.agent-type`, then agent name |
| `agent_description` | `template.yaml` via `/api/template/info` | None |
| `is_autonomous` | `agents` table `autonomy_enabled` column | `false` |
| `is_read_only` | `agents` table `read_only_enabled` column | `false` |

---

## Revision History

| Date | Changes |
|------|---------|
| 2025-12-22 | Initial documentation |
| 2025-12-30 | Verified line numbers, updated file references, added detailed method tables, expanded testing section |
| 2026-01-23 | Refreshed line numbers for all backend files: public_links.py endpoints (56, 92, 107, 126, 167), public.py endpoints (43, 73, 130, 166), db_models.py models (301-374). Updated AgentDetail.vue references (167, 169, 230, 443-446). Added delete_agent_public_links() at db/public_links.py:156. Updated main.py references (44-45, 112, 292-293). Corrected file line counts. |
| 2026-02-16 | **Implemented PUB-002 External Public URL**: Added `PUBLIC_CHAT_URL` env var, `external_url` field in API response, globe icon button in UI for copying external links. Configuration section updated. |
| 2026-02-17 | **Expanded PUB-002 documentation**: Added detailed data flow diagram, CORS auto-configuration, complete code snippets with exact line numbers (config.py:43-45,86-88; public_links.py:35-39,42-61,58-59; db_models.py:329-333; PublicLinksPanel.vue:79-102,311-317,461-473). Added API response example and infrastructure options. |
| 2026-02-17 | **Implemented PUB-003 Agent Introduction**: New `GET /api/public/intro/{token}` endpoint sends intro prompt to agent. Frontend `fetchIntro()` displays response as first chat message. Added Agent Introduction section with full implementation details. |
| 2026-02-17 | **Updated for PUB-003**: Refreshed PublicChat.vue method line numbers (276, 314, 337, 376, 411), added `fetchIntro()` to methods table, updated file line count (508 lines), corrected PUB-003 section line number (376-408). |
| 2026-02-17 | **Implemented PUB-004 Public Chat Header Metadata**: `GET /api/public/link/{token}` now returns `agent_display_name`, `agent_description`, `is_autonomous`, `is_read_only`. PublicChat.vue header displays agent name, description, and status badges (AUTO amber, READ-ONLY rose with lock). Updated PublicLinkInfo model (db_models.py:336-346), public.py endpoint (lines 44-103), PublicChat.vue header (lines 4-46). Refreshed method line numbers (306, 344, 367, 406, 441). File now 538 lines. |
