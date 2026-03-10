# Trinity Security Analysis Report

**Date:** 2026-03-09
**Scope:** Full codebase (backend, frontend, Docker, infrastructure)
**Methodology:** OWASP Top 10 (2021) with additional container security review
**Analyzer:** Claude Opus 4

---

## Executive Summary

| Severity | Count |
|----------|-------|
| **CRITICAL** | 3 |
| **HIGH** | 6 |
| **MEDIUM** | 8 |
| **LOW** | 5 |
| **INFO** | 4 |
| **Total** | 26 |

The Trinity platform demonstrates mature security practices in several areas (bcrypt password hashing, parameterized SQL queries, RBAC with agent-level ACLs, container hardening with cap_drop/no-new-privileges, credential sanitization). However, several critical and high-severity findings require attention, particularly around unauthenticated WebSocket access, encryption key exposure via API, and internal endpoint access control.

---

## Findings

### CRITICAL Findings

#### C-001: Encryption Key Exposed via Authenticated API Endpoint

**File:** `/src/backend/routers/credentials.py` (lines 298-319)
**Category:** A02 - Cryptographic Failures

The `GET /credentials/encryption-key` endpoint returns the platform's AES-256-GCM credential encryption key to any authenticated user. This key is used to encrypt/decrypt all `.credentials.enc` files across all agents.

```python
@router.get("/credentials/encryption-key")
async def get_encryption_key(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    key = os.getenv("CREDENTIAL_ENCRYPTION_KEY")
    ...
    return {
        "key": key,
        "algorithm": "AES-256-GCM",
        ...
    }
```

**Impact:** Any authenticated user (including non-admin email-authenticated users) can retrieve the master encryption key, which can decrypt credentials for ALL agents on the platform, not just their own.

**Recommendation:** Restrict this endpoint to admin-only access using `require_admin` dependency. Consider per-agent encryption keys instead of a single platform-wide key.

---

#### C-002: WebSocket /ws Endpoint Allows Unauthenticated Read Access to All Events

**File:** `/src/backend/main.py` (lines 361-417)
**Category:** A01 - Broken Access Control

The primary WebSocket endpoint `/ws` accepts connections without authentication and broadcasts ALL platform events (agent started/stopped, chat activity, collaboration events, schedule executions) to all connected clients regardless of authentication status.

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    # ... token validation is OPTIONAL
    if token:
        try:
            # validates but failure just means unauthenticated
            pass
    # Unauthenticated connections receive ALL events
    await manager.connect(websocket)
```

The code comments explicitly note: "SECURITY: Authentication is optional for read-only updates, but should be enforced in production for sensitive data."

**Impact:** Any client connecting to `ws://host:8000/ws` receives all platform events including agent names, activity details, execution metadata, user IDs, collaboration patterns, and operational intelligence. No agent-level filtering is applied.

**Recommendation:** Require authentication on the `/ws` endpoint or, at minimum, reject connections without valid tokens. The filtered `/ws/events` endpoint already demonstrates the correct pattern.

---

#### C-003: Internal API Endpoints Accessible from Docker Network Without Authentication

**File:** `/src/backend/routers/internal.py` (lines 1-140)
**Category:** A01 - Broken Access Control

The `/api/internal/` endpoints have NO authentication and are accessible to any container on the `trinity-agent-network` Docker bridge network. Since agent containers are user-controlled environments where arbitrary code can run, any compromised or malicious agent can:

1. Create fake activity records for any agent via `POST /api/internal/activities/track`
2. Complete/modify activity records via `POST /api/internal/activities/{id}/complete`
3. Inject arbitrary data into the activity stream and WebSocket broadcasts

```python
router = APIRouter(
    prefix="/api/internal",
    tags=["internal"],
    # No authentication dependency
)
```

**Impact:** A compromised agent container can spoof activity data, inject misleading events into the WebSocket stream seen by all users, and manipulate the audit trail. The network is flat -- all agent containers share the same Docker bridge network.

**Recommendation:** Add shared-secret or mutual TLS authentication for internal endpoints. At minimum, validate requests come from known agent container IPs or include a rotating internal API key.

---

### HIGH Findings

#### H-001: API Keys Stored in Plaintext in SQLite Database

**File:** `/src/backend/routers/settings.py` (lines 142-174, 264-296)
**Category:** A02 - Cryptographic Failures

Anthropic API keys, GitHub PATs, Slack secrets, and other sensitive API keys are stored directly in the `system_settings` SQLite table as plaintext values:

```python
db.set_setting('anthropic_api_key', key)
db.set_setting('github_pat', key)
db.set_setting('slack_client_id', body.client_id.strip())
db.set_setting('slack_client_secret', body.client_secret.strip())
```

The SQLite database file is a Docker volume (`trinity-data:/data/trinity.db`) accessible from the backend container and the scheduler container.

**Impact:** Anyone with access to the SQLite database file or a database dump can read all API keys in cleartext. The database is shared across multiple containers.

**Recommendation:** Encrypt sensitive settings before storage using the existing credential encryption infrastructure. Use Redis (which is already in the stack) for ephemeral secrets, or implement application-level encryption for the settings table.

---

#### H-002: Default Admin Password "changeme" in Production Compose

**File:** `/docker-compose.prod.yml` (line 24)
**Category:** A07 - Identification and Authentication Failures

The production Docker Compose file sets a weak default admin password:

```yaml
- ADMIN_PASSWORD=${ADMIN_PASSWORD:-changeme}
```

While using an environment variable override, the fallback value "changeme" means that if the operator forgets to set `ADMIN_PASSWORD`, the system starts with a trivially guessable password.

**Impact:** If deployed without setting `ADMIN_PASSWORD`, the admin account is immediately compromisable.

**Recommendation:** Remove the default fallback value in the production compose file. Require `ADMIN_PASSWORD` to be set explicitly (fail startup if not set, like the `SECRET_KEY` handling in config.py).

---

#### H-003: Docker Socket Mounted Read-Only but Grants Significant Capability

**File:** `/docker-compose.yml` (line 44), `/docker-compose.prod.yml` (line 56)
**Category:** A04 - Insecure Design

The Docker socket is mounted into the backend container:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

While read-only, the Docker socket still allows:
- Listing all containers on the host (not just Trinity)
- Reading container configurations, environment variables, labels
- Inspecting volume mounts and network configurations

Combined with the fact that the backend creates agent containers programmatically, a vulnerability in the backend could be exploited to create privileged containers or escape the Docker isolation.

**Impact:** Backend compromise could lead to container escape. The read-only flag does NOT prevent container creation, image pulling, or exec operations through the Docker API -- those are API calls, not file writes.

**Recommendation:** Use Docker socket proxy (e.g., Tecnativa/docker-socket-proxy) to restrict Docker API operations to only the endpoints needed. Consider enabling Docker TLS authentication.

---

#### H-004: JWT Tokens in localStorage Vulnerable to XSS

**File:** `/src/frontend/src/api.js` (line 18), multiple Vue components
**Category:** A02 - Cryptographic Failures / A03 - Injection

JWT tokens are stored in `localStorage` and retrieved across the frontend:

```javascript
const token = localStorage.getItem('token')
```

Combined with finding H-005 (v-html usage), any XSS vulnerability would allow token exfiltration.

**Impact:** If XSS is achieved (see H-005), the attacker gains full access to the user's JWT, which is valid for 7 days.

**Recommendation:** Use `httpOnly` cookies for JWT storage instead of localStorage. If localStorage must be used, implement Content-Security-Policy headers and sanitize all rendered content.

---

#### H-005: Multiple v-html Usages Rendering Potentially Untrusted Content

**Files:** Multiple Vue components (ChatBubble.vue, ExecutionDetail.vue, DashboardPanel.vue, ProcessChatAssistant.vue, QueueCard.vue, QueueItemDetail.vue, ProcessDocs.vue)
**Category:** A03 - Injection (XSS)

At least 9 instances of `v-html` render content that originates from agent responses, execution logs, dashboard widgets, or operator queue items:

```html
<div v-html="renderedContent" />
<div v-html="renderMarkdown(msg.content)" />
<div v-html="renderMarkdown(item.question)" />
```

Agent responses and dashboard content are user/agent-controlled. If the markdown rendering does not properly sanitize HTML, this creates XSS vectors.

**Impact:** Agents can inject arbitrary HTML/JavaScript into the Trinity UI, potentially exfiltrating JWT tokens from localStorage, performing actions on behalf of the user, or redirecting to phishing pages.

**Recommendation:** Ensure all markdown rendering uses a sanitizer (e.g., DOMPurify) that strips script tags, event handlers, and dangerous HTML. Audit each `v-html` usage to confirm the content passes through sanitization.

---

#### H-006: Redis Running Without Authentication in Development

**File:** `/docker-compose.yml` (lines 101-121)
**Category:** A05 - Security Misconfiguration

The development Docker Compose conditionally enables Redis authentication:

```yaml
command: >
  sh -c '
    if [ -n "$REDIS_PASSWORD" ]; then
      redis-server --appendonly yes --requirepass "$REDIS_PASSWORD"
    else
      echo "WARNING: Redis running without authentication"
      redis-server --appendonly yes
    fi
  '
```

And Redis port 6379 is exposed to the host. In development, `REDIS_PASSWORD` is typically not set.

**Impact:** Any process on the host network can connect to Redis and read/write data including MCP API key metadata, rate limiting counters, SSH credential metadata, and slot management data.

**Recommendation:** Always require Redis authentication, even in development. The production compose already uses `expose` instead of `ports`, which is correct -- apply the same in development.

---

### MEDIUM Findings

#### M-001: Token Accepted via URL Query Parameter

**File:** `/src/backend/routers/auth.py` (lines 192-227)
**Category:** A07 - Authentication Failures

The `/api/auth/validate` endpoint accepts tokens via query parameter:

```python
if not token:
    token = request.query_params.get("token")
```

Similarly, the WebSocket endpoints accept tokens via `?token=` query parameters.

**Impact:** Tokens in URLs are logged in web server access logs, browser history, proxy logs, and referrer headers. This increases the risk of token leakage.

**Recommendation:** Remove query parameter token acceptance for REST endpoints. For WebSocket connections (where headers are limited), consider using a short-lived token exchange pattern.

---

#### M-002: Rate Limiting Falls Open When Redis Is Unavailable

**File:** `/src/backend/routers/auth.py` (lines 44-55)
**Category:** A07 - Authentication Failures

When Redis is unavailable, login rate limiting is silently disabled:

```python
def check_login_rate_limit(client_ip: str) -> bool:
    r = get_redis_client()
    if r is None:
        logger.warning("Rate limiting unavailable - Redis not connected")
        return True  # Allow login
```

**Impact:** If Redis goes down, brute force protection for admin login is completely bypassed.

**Recommendation:** Implement a fallback rate limiting mechanism (e.g., in-memory with `collections.Counter` and TTL) when Redis is unavailable.

---

#### M-003: 7-Day JWT Token Lifetime

**File:** `/src/backend/config.py` (line 26)
**Category:** A07 - Authentication Failures

JWT tokens are valid for 7 days:

```python
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # 7 days
```

There is no token revocation mechanism (tokens are stateless JWTs). The only way to invalidate tokens is to change the `SECRET_KEY`, which invalidates ALL sessions.

**Impact:** Stolen tokens remain valid for up to 7 days. There is no way to revoke a specific token.

**Recommendation:** Implement refresh token rotation with shorter access token lifetime (15-60 minutes). Add a token revocation mechanism (e.g., Redis-backed token blacklist).

---

#### M-004: Missing Agent Access Control on Several Chat Router Endpoints

**File:** `/src/backend/routers/chat.py`
**Category:** A01 - Broken Access Control

The chat router uses `Depends(get_current_user)` but does NOT use the `AuthorizedAgent` dependency for most endpoints. The `{name}` path parameter is used directly without verifying the user has access to that agent:

```python
@router.post("/{name}/chat")
async def chat_with_agent(
    name: str,
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),  # Auth but no agent access check
    ...
```

While a container existence check is performed, there is no call to `db.can_user_access_agent()` for the chat, task, model, and activity endpoints.

**Impact:** An authenticated user may be able to chat with, execute tasks on, and view activity for agents they do not own and that are not shared with them.

**Recommendation:** Add the `AuthorizedAgent` or `get_authorized_agent` dependency to all agent-specific endpoints in the chat router.

---

#### M-005: Agent Container Has Passwordless Sudo Access

**File:** `/docker/base-image/Dockerfile` (lines 52-55)
**Category:** A05 - Security Misconfiguration

The agent base image grants the `developer` user passwordless sudo:

```dockerfile
RUN useradd -m -s /bin/bash -u 1000 developer && \
    echo "developer:developer" | chpasswd && \
    usermod -aG sudo developer && \
    echo "developer ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
```

**Impact:** Any code running as the `developer` user inside an agent container has full root access within that container. Combined with Docker socket access (if granted) or kernel exploits, this could enable container escape.

**Recommendation:** Remove passwordless sudo. Use specific capabilities or run required root operations through a controlled entrypoint script instead.

---

#### M-006: Credential Injection Has No Per-Agent Authorization Check

**File:** `/src/backend/routers/credentials.py` (lines 150-209)
**Category:** A01 - Broken Access Control

The credential injection endpoint verifies the user is authenticated but does not verify they have access to the target agent:

```python
@router.post("/agents/{agent_name}/credentials/inject")
async def inject_credentials(
    agent_name: str,
    request_body: CredentialInjectRequest,
    request: Request,
    current_user: User = Depends(get_current_user)  # No agent access check
):
```

**Impact:** Any authenticated user can inject credential files into any agent container.

**Recommendation:** Add `AuthorizedAgentByName` or `OwnedAgentByName` dependency to credential injection, export, and import endpoints.

---

#### M-007: Setup Endpoint Allows Password Reset Without Authentication

**File:** `/src/backend/routers/setup.py` (lines 37-81)
**Category:** A07 - Authentication Failures

The `POST /api/setup/admin-password` endpoint has no authentication and is guarded only by a `setup_completed` flag in the database:

```python
if db.get_setting_value('setup_completed', 'false') == 'true':
    raise HTTPException(status_code=403, ...)
```

If an attacker can modify the `setup_completed` setting (e.g., via SQL injection in another part of the system, or direct database access), they can reset the admin password.

**Impact:** If the `setup_completed` flag is bypassed, full admin takeover is possible without authentication.

**Recommendation:** Add IP-based restrictions (localhost only) or time-based lockout for the setup endpoint. Consider requiring the existing admin password for password changes after initial setup.

---

#### M-008: CORS Configuration Allows Dynamic Origins via Environment Variable

**File:** `/src/backend/config.py` (lines 88-100)
**Category:** A05 - Security Misconfiguration

The CORS configuration allows arbitrary additional origins via `EXTRA_CORS_ORIGINS`:

```python
_extra_origins = os.getenv("EXTRA_CORS_ORIGINS", "").split(",")
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
] + _extra_origins
```

Additionally, `PUBLIC_CHAT_URL` is automatically added to CORS origins. The `allow_credentials=True` combined with potentially broad origins is dangerous.

**Impact:** If `EXTRA_CORS_ORIGINS` is misconfigured (e.g., set to `*`), cross-origin requests with credentials become possible.

**Recommendation:** Validate that extra origins are well-formed URLs. Never allow wildcard (`*`) when `allow_credentials=True`. Log the final CORS origins list at startup for audit purposes.

---

### LOW Findings

#### L-001: Broad Exception Catching in WebSocket Broadcast

**File:** `/src/backend/main.py` (lines 113-114)
**Category:** A09 - Security Logging and Monitoring Failures

```python
async def broadcast(self, message: str):
    for connection in self.active_connections:
        try:
            await connection.send_text(message)
        except:
            pass  # Silent exception swallowing
```

**Impact:** Errors during WebSocket broadcast are silently ignored, hindering debugging and potentially masking issues.

**Recommendation:** Log the exception at debug level.

---

#### L-002: Developer Password "developer" Set in Dockerfile

**File:** `/docker/base-image/Dockerfile` (line 53)
**Category:** A07 - Authentication Failures

```dockerfile
echo "developer:developer" | chpasswd
```

While SSH password authentication is disabled by default, the container has a known password for the developer user.

**Impact:** If SSH password authentication is re-enabled (which the SSH access feature does for the "password" auth method), the well-known default password is a risk.

**Recommendation:** Do not set a default password. The SSH access feature already generates ephemeral passwords.

---

#### L-003: No CSRF Protection for Form-Encoded Login

**File:** `/src/backend/routers/auth.py` (lines 127-172)
**Category:** A01 - Broken Access Control

The `/token` and `/api/token` endpoints accept `application/x-www-form-urlencoded` data (OAuth2 form format) without CSRF tokens.

**Impact:** A cross-origin form submission could potentially trigger a login and obtain a token if the attacker knows credentials. However, the token is returned in the response body (not set as a cookie), limiting the attack surface.

**Recommendation:** Consider adding CSRF tokens for form-encoded endpoints, or switch to JSON-only endpoints.

---

#### L-004: Email Verification Code Timing Attack

**File:** `/src/backend/db/email_auth.py` (via `db.verify_login_code`)
**Category:** A02 - Cryptographic Failures

Email verification codes are 6-digit numeric codes. If the comparison is not constant-time, timing attacks could be used to determine individual digits.

**Impact:** Theoretical timing attack on 6-digit codes. Practical exploitation is difficult due to network latency.

**Recommendation:** Use `hmac.compare_digest()` or similar constant-time comparison for code verification.

---

#### L-005: No Security Headers in Backend Responses

**File:** `/src/backend/main.py`
**Category:** A05 - Security Misconfiguration

The FastAPI application does not set security headers such as:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security` (HSTS)
- `Content-Security-Policy`

**Impact:** Missing defense-in-depth headers that protect against clickjacking, MIME sniffing, and other browser-based attacks.

**Recommendation:** Add a middleware to set standard security headers on all responses.

---

### INFO Findings

#### I-001: Production Redis Lacks Password Authentication

**File:** `/docker-compose.prod.yml` (line 132)
**Category:** A05 - Security Misconfiguration

Production Redis runs without `--requirepass`:

```yaml
command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
```

While Redis is not exposed externally (`expose` instead of `ports`), internal services can access it without authentication.

**Recommendation:** Add password authentication for defense in depth.

---

#### I-002: SQLite Database Shared Between Backend and Scheduler

**File:** `/docker-compose.yml`, `/docker-compose.prod.yml`
**Category:** A04 - Insecure Design

Both the backend and scheduler mount the same SQLite database file. SQLite has limited concurrent write support.

**Recommendation:** Consider migrating to PostgreSQL for production deployments, or ensure WAL mode is enabled for better concurrent access.

---

#### I-003: Credential Sanitizer May Miss Novel Secret Formats

**File:** `/src/backend/utils/credential_sanitizer.py`
**Category:** A02 - Cryptographic Failures

The credential sanitizer uses regex patterns for known secret formats. Novel or custom secret formats (e.g., Nevermined API keys, custom OAuth tokens) may not be caught.

**Recommendation:** Regularly update sanitizer patterns. Consider an allowlist approach where only known-safe content is passed through, rather than a denylist approach.

---

#### I-004: Agent Templates Cloned via Git Without Integrity Verification

**File:** `/src/backend/services/template_service.py`
**Category:** A04 - Insecure Design

Agent templates are cloned from GitHub repositories using `git clone` with a PAT. There is no commit signature verification or hash pinning.

**Recommendation:** Pin templates to specific commit SHAs or tags. Consider verifying GPG signatures on template commits.

---

## Positive Security Observations

The following security practices are already well-implemented:

1. **Password hashing:** bcrypt via passlib with plaintext fallback removed (M-003 fix).
2. **SQL parameterization:** All SQL queries use parameterized queries with `?` placeholders. The dynamic SQL in `operator_queue.py` uses parameterized values (not string interpolation for values).
3. **Agent-level RBAC:** Comprehensive access control system with owner/shared/admin roles via `AuthorizedAgent` dependencies.
4. **Container hardening:** `no-new-privileges`, `cap_drop: ALL`, memory limits, CPU limits in both dev and prod compose files.
5. **Rate limiting:** Login rate limiting (5 attempts/10 min), email verification rate limiting, public chat rate limiting.
6. **Credential sanitization:** Defense-in-depth sanitization layer that catches known secret patterns in execution logs before database persistence.
7. **Docker bridge network isolation:** Agent containers run on a dedicated Docker bridge network.
8. **SSH security:** SSH key-based auth by default, password auth disabled, ephemeral keys with TTL.
9. **Secret-free configuration:** `.env` file pattern with `${VAR}` placeholders, no hardcoded secrets in source.
10. **Filtered WebSocket for external clients:** The `/ws/events` endpoint properly validates MCP API keys and filters events to accessible agents only.

---

## Top 3 Most Urgent Actions

1. **Restrict `/credentials/encryption-key` to admin-only** (C-001) -- A single-line fix (`require_admin`) that prevents non-admin users from exfiltrating the master encryption key.

2. **Require authentication on `/ws` WebSocket endpoint** (C-002) -- Reject unauthenticated WebSocket connections to prevent unauthorized monitoring of all platform events.

3. **Add agent access control to chat/credential routers** (M-004, M-006) -- Several endpoints allow any authenticated user to interact with any agent. Add `AuthorizedAgent` dependencies consistently.

---

## Methodology Notes

- Analyzed source files: ~40 backend Python files, ~15 Vue/JS frontend files, 4 Docker configuration files
- Static analysis only (no runtime testing)
- Focused on code-level vulnerabilities, not infrastructure hardening beyond Docker
- SQLite query patterns verified for parameterization
- All findings verified by reading actual source code, not inferred
