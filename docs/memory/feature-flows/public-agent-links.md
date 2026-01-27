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
| `src/frontend/src/views/PublicChat.vue` | 1-441 | Public chat interface |

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
| `loadLinkInfo()` | 257 | Validate link token |
| `requestCode()` | 295 | Request verification email |
| `verifyCode()` | 318 | Confirm 6-digit code |
| `sendMessage()` | 355 | Send chat message |

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
| `POST /api/agents/{name}/public-links` | `public_links.py:56` | `create_public_link()` |
| `GET /api/agents/{name}/public-links` | `public_links.py:92` | `list_public_links()` |
| `GET /api/agents/{name}/public-links/{id}` | `public_links.py:107` | `get_public_link()` |
| `PUT /api/agents/{name}/public-links/{id}` | `public_links.py:126` | `update_public_link()` |
| `DELETE /api/agents/{name}/public-links/{id}` | `public_links.py:167` | `delete_public_link()` |

### Public Endpoints (Unauthenticated)

| Endpoint | File:Line | Handler |
|----------|-----------|---------|
| `GET /api/public/link/{token}` | `public.py:43` | `get_public_link_info()` |
| `POST /api/public/verify/request` | `public.py:73` | `request_verification_code()` |
| `POST /api/public/verify/confirm` | `public.py:130` | `confirm_verification_code()` |
| `POST /api/public/chat/{token}` | `public.py:166` | `public_chat()` |

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
| `PublicLinkInfo` | `db_models.py:335` | Public-facing link info |
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

# Frontend URL (for link generation)
# Default: http://localhost (port 80, Docker deployment)
# For Vite dev server: http://localhost:5173
FRONTEND_URL=http://localhost
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
| `src/backend/db/public_links.py` | Database operations class (439 lines) |
| `src/backend/routers/public_links.py` | Owner CRUD endpoints (198 lines) |
| `src/backend/routers/public.py` | Public endpoints (265 lines) |
| `src/backend/services/email_service.py` | Email sending service |
| `src/backend/db_models.py:301-374` | Pydantic models |
| `src/backend/database.py` | Schema, imports, delegation |
| `src/backend/config.py` | Email configuration |
| `src/backend/main.py:44-45,112,292-293` | Router registration |

### Frontend

| File | Description |
|------|-------------|
| `src/frontend/src/views/PublicChat.vue` | Public chat page (441 lines) |
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

## Revision History

| Date | Changes |
|------|---------|
| 2025-12-22 | Initial documentation |
| 2025-12-30 | Verified line numbers, updated file references, added detailed method tables, expanded testing section |
| 2026-01-23 | Refreshed line numbers for all backend files: public_links.py endpoints (56, 92, 107, 126, 167), public.py endpoints (43, 73, 130, 166), db_models.py models (301-374). Updated AgentDetail.vue references (167, 169, 230, 443-446). Added delete_agent_public_links() at db/public_links.py:156. Updated main.py references (44-45, 112, 292-293). Corrected file line counts. |
