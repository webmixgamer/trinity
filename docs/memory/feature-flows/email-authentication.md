# Feature: Email-Based Authentication

## Overview
Passwordless email-based authentication with verification codes. Users enter their email, receive a 6-digit code, and login without passwords. Includes admin-managed email whitelist and automatic whitelist addition when agents are shared. This is the default authentication method for Trinity (Phase 12.4).

## User Story
As a user, I want to login with my email address and a verification code so that I don't need to manage passwords or OAuth providers.

As an admin, I want to control who can access the platform via an email whitelist so that I can manage access control independently of OAuth providers.

## Entry Points
- **UI**: `src/frontend/src/views/Login.vue` - Email login form (TODO - not implemented yet)
- **UI**: `src/frontend/src/views/Settings.vue` - Email Whitelist management tab (TODO - not implemented yet)
- **API**: `POST /api/auth/email/request` - Request verification code
- **API**: `POST /api/auth/email/verify` - Verify code and login
- **API**: `GET /api/settings/email-whitelist` - List whitelisted emails (admin-only)
- **API**: `POST /api/settings/email-whitelist` - Add email to whitelist (admin-only)
- **API**: `DELETE /api/settings/email-whitelist/{email}` - Remove from whitelist (admin-only)

---

## Architecture: Email Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Email Auth Flow                              │
└─────────────────────────────────────────────────────────────────────┘

  User enters email                    Backend checks whitelist
┌────────────────────┐              ┌──────────────────────────┐
│  Login.vue (TODO)  │              │  email_whitelist table   │
│  Email input       │              │  - id                    │
│  "Send Code" btn   │              │  - email                 │
└─────────┬──────────┘              │  - added_by              │
          │                         │  - added_at              │
          │ POST /api/auth/         │  - source (manual|       │
          │      email/request      │    agent_sharing)        │
          │                         └──────────┬───────────────┘
          v                                    │
┌─────────────────────────────────────────┐   │
│  auth.py:request_email_login_code()     │   │
│  1. Check setup_completed               │   │
│  2. Check EMAIL_AUTH_ENABLED            │   │
│  3. Verify email in whitelist  ─────────┼───┘
│  4. Rate limit check (3 per 10 min)     │
│  5. Generate 6-digit code               │
│  6. Store in email_login_codes table    │
│  7. Send email                          │
└─────────┬───────────────────────────────┘
          │
          v
┌─────────────────────────────────────────┐
│  email_service.py                       │
│  - console: Print to console (dev)      │
│  - smtp: Standard SMTP                  │
│  - sendgrid: SendGrid API               │
│  - resend: Resend API                   │
└─────────┬───────────────────────────────┘
          │
          │ User receives email
          v
┌────────────────────┐
│  Email: "Your      │
│  code is: 123456"  │
│  Expires in 10 min │
└─────────┬──────────┘
          │
          │ User enters code
          v
┌────────────────────┐              ┌──────────────────────────┐
│  Login.vue (TODO)  │              │  email_login_codes       │
│  Code input        │              │  - id                    │
│  "Verify" btn      │              │  - email                 │
└─────────┬──────────┘              │  - code (6 digits)       │
          │                         │  - created_at            │
          │ POST /api/auth/         │  - expires_at            │
          │      email/verify       │  - verified (0|1)        │
          │                         │  - used_at               │
          v                         └──────────┬───────────────┘
┌─────────────────────────────────────────┐   │
│  auth.py:verify_email_login_code()      │   │
│  1. Check setup_completed               │   │
│  2. Check EMAIL_AUTH_ENABLED            │   │
│  3. Verify code and expiry  ────────────┼───┘
│  4. Mark code as verified               │
│  5. Get or create user (email = user)   │
│  6. Generate JWT with mode="email"      │
│  7. Audit log                           │
└─────────┬───────────────────────────────┘
          │
          v
┌────────────────────────────────────────┐
│  JWT Token returned                    │
│  {                                     │
│    "access_token": "eyJ...",           │
│    "token_type": "bearer",             │
│    "user": {                           │
│      "username": "user@example.com",   │
│      "email": "user@example.com",      │
│      "role": "user"                    │
│    }                                   │
│  }                                     │
└────────────────────────────────────────┘
```

---

## Auto-Whitelist on Agent Sharing

When an agent is shared with a new email, that email is automatically added to the whitelist:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Agent Sharing → Auto-Whitelist                   │
└─────────────────────────────────────────────────────────────────────┘

  Owner shares agent with email
┌────────────────────────────┐
│  AgentDetail.vue           │
│  "Share Agent" dialog      │
│  Enter email, click Share  │
└─────────┬──────────────────┘
          │
          │ POST /api/agents/{agent_name}/share
          │ { "email": "newuser@example.com" }
          │
          v
┌─────────────────────────────────────────┐
│  sharing.py:share_agent_endpoint()      │
│  1. Validate ownership                  │
│  2. Create share record                 │
│  3. Check if EMAIL_AUTH_ENABLED         │
│  4. If enabled: auto-add to whitelist   │
│     - db.add_to_whitelist()             │
│     - source="agent_sharing"            │
│  5. Audit log                           │
│  6. WebSocket broadcast                 │
└─────────┬───────────────────────────────┘
          │
          v
┌─────────────────────────────────────────┐
│  email_whitelist table updated          │
│  - email: newuser@example.com           │
│  - added_by: owner_id                   │
│  - source: "agent_sharing"              │
│  - added_at: 2025-12-26T10:00:00Z       │
└─────────────────────────────────────────┘

Result: New user can now login with email code
        without admin manually adding them
```

---

## Configuration

### Environment Variables (`src/backend/config.py`)

```python
# Line 11-15: Email Authentication Mode (Phase 12.4)
EMAIL_AUTH_ENABLED = os.getenv("EMAIL_AUTH_ENABLED", "true").lower() == "true"

# Line 52-59: Email Service Configuration
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "resend")  # console|smtp|sendgrid|resend
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@trinity.example.com")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
```

**Setting can also be overridden via system_settings table:**
- Key: `email_auth_enabled`
- Value: `"true"` or `"false"`

---

## Frontend Layer (TODO - Not Implemented Yet)

### State Management (`src/frontend/src/stores/auth.js`)

**Required additions:**
```javascript
// Add to actions section (after line 237)

async requestEmailCode(email) {
  try {
    const response = await axios.post('/api/auth/email/request', { email })
    return { success: true, expiresIn: response.data.expires_in_seconds }
  } catch (error) {
    this.authError = error.response?.data?.detail || 'Failed to send code'
    return { success: false, error: this.authError }
  }
},

async verifyEmailCode(email, code) {
  try {
    const response = await axios.post('/api/auth/email/verify', { email, code })

    this.token = response.data.access_token
    this.user = response.data.user
    this.isAuthenticated = true

    localStorage.setItem('token', this.token)
    localStorage.setItem('auth0_user', JSON.stringify(this.user))
    this.setupAxiosAuth()

    return true
  } catch (error) {
    this.authError = error.response?.data?.detail || 'Invalid code'
    return false
  }
}
```

### Login.vue Additions

Add email auth form to `src/frontend/src/views/Login.vue`:

```vue
<!-- Insert after line 102 (after production mode section) -->

<!-- Email Authentication Mode -->
<div v-else-if="authStore.emailAuthEnabled">
  <!-- Step 1: Request Code -->
  <div v-if="!codeSent">
    <form @submit.prevent="handleRequestCode" class="space-y-4">
      <div>
        <label for="email" class="block text-sm font-medium">Email Address</label>
        <input
          id="email"
          v-model="email"
          type="email"
          required
          class="mt-1 block w-full px-3 py-2 border rounded-lg"
          placeholder="you@example.com"
        />
      </div>
      <button
        type="submit"
        :disabled="loginLoading || !email"
        class="w-full py-3 px-4 rounded-lg bg-blue-600 text-white"
      >
        {{ loginLoading ? 'Sending code...' : 'Send verification code' }}
      </button>
    </form>
  </div>

  <!-- Step 2: Verify Code -->
  <div v-else>
    <p class="text-sm text-gray-600 mb-4">
      We sent a code to <strong>{{ email }}</strong>
    </p>
    <form @submit.prevent="handleVerifyCode" class="space-y-4">
      <div>
        <label for="code" class="block text-sm font-medium">Verification Code</label>
        <input
          id="code"
          v-model="code"
          type="text"
          required
          maxlength="6"
          pattern="[0-9]{6}"
          class="mt-1 block w-full px-3 py-2 border rounded-lg text-center text-2xl tracking-widest"
          placeholder="000000"
        />
      </div>
      <button
        type="submit"
        :disabled="loginLoading || code.length !== 6"
        class="w-full py-3 px-4 rounded-lg bg-blue-600 text-white"
      >
        {{ loginLoading ? 'Verifying...' : 'Verify code' }}
      </button>
      <button
        type="button"
        @click="codeSent = false; code = ''"
        class="w-full py-2 text-sm text-gray-600"
      >
        Use a different email
      </button>
    </form>
  </div>
</div>
```

**Required reactive state:**
```javascript
const email = ref('')
const code = ref('')
const codeSent = ref(false)
```

**Required methods:**
```javascript
const handleRequestCode = async () => {
  loginLoading.value = true
  const result = await authStore.requestEmailCode(email.value)
  if (result.success) {
    codeSent.value = true
  }
  loginLoading.value = false
}

const handleVerifyCode = async () => {
  loginLoading.value = true
  const success = await authStore.verifyEmailCode(email.value, code.value)
  if (success) {
    router.push('/')
  }
  loginLoading.value = false
}
```

### Settings.vue - Email Whitelist Tab (TODO)

Add new tab to Settings page:

```vue
<!-- Add to tabs array -->
<button @click="currentTab = 'email-whitelist'" v-if="isAdmin">
  Email Whitelist
</button>

<!-- Tab content -->
<div v-if="currentTab === 'email-whitelist'" class="space-y-4">
  <div class="flex justify-between items-center">
    <h3 class="text-lg font-semibold">Email Whitelist</h3>
    <button @click="showAddEmailDialog = true" class="btn-primary">
      Add Email
    </button>
  </div>

  <div class="bg-white rounded-lg shadow">
    <table class="min-w-full">
      <thead>
        <tr>
          <th>Email</th>
          <th>Added By</th>
          <th>Source</th>
          <th>Added At</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="entry in emailWhitelist" :key="entry.id">
          <td>{{ entry.email }}</td>
          <td>{{ entry.added_by_username }}</td>
          <td>
            <span v-if="entry.source === 'manual'" class="badge-blue">Manual</span>
            <span v-else-if="entry.source === 'agent_sharing'" class="badge-green">
              Agent Sharing
            </span>
          </td>
          <td>{{ formatDate(entry.added_at) }}</td>
          <td>
            <button @click="removeEmail(entry.email)" class="btn-danger-sm">
              Remove
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
```

---

## Backend Layer

### Database Schema (`src/backend/database.py:500-521`)

**email_whitelist table:**
```sql
CREATE TABLE IF NOT EXISTS email_whitelist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    added_by TEXT NOT NULL,          -- User ID who added this email
    added_at TEXT NOT NULL,          -- ISO timestamp
    source TEXT NOT NULL,            -- "manual" or "agent_sharing"
    FOREIGN KEY (added_by) REFERENCES users(id)
)
```

**email_login_codes table:**
```sql
CREATE TABLE IF NOT EXISTS email_login_codes (
    id TEXT PRIMARY KEY,             -- Random token
    email TEXT NOT NULL,             -- Email address (lowercase)
    code TEXT NOT NULL,              -- 6-digit verification code
    created_at TEXT NOT NULL,        -- ISO timestamp
    expires_at TEXT NOT NULL,        -- ISO timestamp (created_at + 10 min)
    verified INTEGER DEFAULT 0,      -- 0 = unused, 1 = used
    used_at TEXT                     -- ISO timestamp when verified
)
```

**Indexes:**
```sql
CREATE INDEX idx_email_whitelist_email ON email_whitelist(email)
CREATE INDEX idx_email_login_codes_email ON email_login_codes(email)
CREATE INDEX idx_email_login_codes_code ON email_login_codes(code)
```

### Database Operations (`src/backend/db/email_auth.py`)

**EmailAuthOperations class** (injected with UserOperations dependency):

| Method | Line | Purpose |
|--------|------|---------|
| `is_email_whitelisted(email)` | 27-35 | Check if email is in whitelist |
| `add_to_whitelist(email, added_by, source)` | 37-67 | Add email to whitelist |
| `remove_from_whitelist(email)` | 69-83 | Remove email from whitelist |
| `list_whitelist(limit)` | 85-104 | Get all whitelisted emails with metadata |
| `create_login_code(email, expiry_minutes)` | 110-145 | Generate 6-digit code with 10 min expiry |
| `verify_login_code(email, code)` | 147-190 | Verify code, mark as used, return result |
| `count_recent_code_requests(email, minutes)` | 192-205 | Rate limiting check |
| `cleanup_old_codes(days)` | 207-220 | Cleanup expired codes (housekeeping) |
| `get_or_create_email_user(email)` | 226-253 | Create user account from email |

### Authentication Endpoints (`src/backend/routers/auth.py`)

#### POST /api/auth/email/request (Lines 287-375)

**Request verification code - Unauthenticated endpoint**

```python
@router.post("/api/auth/email/request")
async def request_email_login_code(request: Request):
    """
    Request a login code via email.

    Rate limit: 3 requests per 10 minutes per email.
    """
```

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Business Logic:**
1. Check if setup is completed (line 301-305)
2. Check if email auth is enabled (line 308-313)
3. Parse and lowercase email (line 316-318)
4. Check if email is whitelisted (line 321-334)
   - If not whitelisted: Return generic success message (prevent enumeration)
   - Audit log with `result="denied"`, `reason="not_whitelisted"`
5. Check rate limit: 3 requests per 10 minutes (line 337-351)
   - If exceeded: Return 429 with audit log
6. Generate 6-digit code (line 354)
   - `db.create_login_code(email, expiry_minutes=10)`
7. Send email via EmailService (line 357-358)
8. Audit log: `event_type="authentication"`, `action="email_login_code_sent"` (line 361-369)
9. Return success response (line 371-375)

**Response:**
```json
{
  "success": true,
  "message": "Verification code sent to your email",
  "expires_in_seconds": 600
}
```

**Security:** Returns generic success message even if email is not whitelisted (prevents email enumeration).

#### POST /api/auth/email/verify (Lines 378-465)

**Verify code and get JWT - Unauthenticated endpoint**

```python
@router.post("/api/auth/email/verify")
async def verify_email_login_code(request: Request):
    """
    Verify email login code and get JWT token.
    """
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "code": "123456"
}
```

**Business Logic:**
1. Check if setup is completed (line 388-392)
2. Check if email auth is enabled (line 395-400)
3. Parse request (line 403-406)
4. Verify code (line 409)
   - `db.verify_login_code(email, code)`
   - Checks: code exists, not already used, not expired
   - Marks code as verified with `used_at` timestamp
5. If invalid: audit log and return 401 (line 410-424)
6. Get or create user (line 427-432)
   - `db.get_or_create_email_user(email)`
   - Username = email (lowercase)
   - Role = "user"
   - No password set (email auth only)
7. Update last login (line 435)
8. Create JWT token (line 438-443)
   - 7-day expiry (ACCESS_TOKEN_EXPIRE_MINUTES = 10080)
   - Include `mode="email"` claim
9. Audit log: `event_type="authentication"`, `action="email_login"` (line 446-453)
10. Return token and user profile (line 455-465)

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "username": "user@example.com",
    "email": "user@example.com",
    "role": "user",
    "name": null,
    "picture": null
  }
}
```

### Whitelist Management Endpoints (`src/backend/routers/settings.py`)

All whitelist endpoints are **admin-only** (require `role="admin"`).

#### GET /api/settings/email-whitelist (Lines 602-625)

List all whitelisted emails.

**Response:**
```json
{
  "whitelist": [
    {
      "id": 1,
      "email": "admin@example.com",
      "added_by": "1",
      "added_by_username": "admin",
      "added_at": "2025-12-26T10:00:00Z",
      "source": "manual"
    },
    {
      "id": 2,
      "email": "user@example.com",
      "added_by": "1",
      "added_by_username": "admin",
      "added_at": "2025-12-26T11:00:00Z",
      "source": "agent_sharing"
    }
  ]
}
```

#### POST /api/settings/email-whitelist (Lines 628-677)

Add email to whitelist.

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "source": "manual"
}
```

**Business Logic:**
1. Parse request and lowercase email (line 643-645)
2. Add to whitelist (line 648-649)
   - `db.add_to_whitelist(email, current_user.username, source)`
   - Returns `False` if already exists
3. If duplicate: return 409 Conflict (line 651-655)
4. Audit log (line 657-664)
5. Return success (line 666)

**Response:**
```json
{
  "success": true,
  "email": "newuser@example.com"
}
```

#### DELETE /api/settings/email-whitelist/{email} (Lines 680-711)

Remove email from whitelist.

**Response:**
```json
{
  "success": true,
  "email": "user@example.com"
}
```

### Agent Sharing Auto-Whitelist (`src/backend/routers/sharing.py:58-70`)

When an agent is shared, automatically add recipient to whitelist:

```python
# Line 58-70: Auto-add email to whitelist if email auth is enabled
from config import EMAIL_AUTH_ENABLED
email_auth_setting = db.get_setting_value("email_auth_enabled", str(EMAIL_AUTH_ENABLED).lower())
if email_auth_setting.lower() == "true":
    try:
        db.add_to_whitelist(
            share_request.email,
            current_user.username,
            source="agent_sharing"
        )
    except Exception:
        # Already whitelisted or error - continue anyway
        pass
```

**Key behavior:**
- Runs after successful share creation
- Silent failure if email already whitelisted
- Source is marked as `"agent_sharing"` for audit trail
- Does NOT block agent sharing if whitelist add fails

---

## Email Service (`src/backend/services/email_service.py`)

**EmailService class** supports 4 providers:

| Provider | Config | Use Case |
|----------|--------|----------|
| `console` | Default | Development - prints to console/logs |
| `smtp` | SMTP_HOST, SMTP_USER, SMTP_PASSWORD | Standard email server |
| `sendgrid` | SENDGRID_API_KEY | SendGrid API |
| `resend` | RESEND_API_KEY | Resend API (recommended) |

### Key Methods

| Method | Line | Purpose |
|--------|------|---------|
| `send_verification_code(to_email, code)` | 42-56 | Send 6-digit code email |
| `send_email(to_email, subject, body, html_body)` | 58-92 | Generic email sender |
| `_send_console(...)` | 103-114 | Print to console (dev mode) |
| `_send_smtp(...)` | 116-153 | Send via SMTP |
| `_send_sendgrid(...)` | 155-203 | Send via SendGrid API |
| `_send_resend(...)` | 205-253 | Send via Resend API |

### Email Template

```text
Subject: Your verification code

Your verification code is: 123456

This code expires in 10 minutes.

If you didn't request this code, you can safely ignore this email.
```

**Note:** HTML template can be added as optional `html_body` parameter.

---

## Data Models (`src/backend/db_models.py`)

### EmailWhitelistEntry (Lines 376-384)
```python
class EmailWhitelistEntry(BaseModel):
    id: int
    email: str
    added_by: str                    # User ID
    added_by_username: Optional[str] = None
    added_at: datetime
    source: str                      # "manual", "agent_sharing"
```

### EmailWhitelistAdd (Lines 386-389)
```python
class EmailWhitelistAdd(BaseModel):
    email: str
    source: str = "manual"
```

### EmailLoginRequest (Lines 392-394)
```python
class EmailLoginRequest(BaseModel):
    email: str
```

### EmailLoginVerify (Lines 397-400)
```python
class EmailLoginVerify(BaseModel):
    email: str
    code: str  # 6-digit code
```

### EmailLoginResponse (Lines 403-408)
```python
class EmailLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict  # User profile
```

---

## Security Considerations

### Email Enumeration Prevention

The system prevents attackers from discovering which emails are registered:

1. **Generic success message**: `/api/auth/email/request` returns success even for non-whitelisted emails
2. **Audit logging**: Failed attempts are logged with `result="denied"`, `reason="not_whitelisted"`
3. **Rate limiting**: Prevents brute-force enumeration attempts

**Example - Non-whitelisted email:**
```python
# Line 321-334 in auth.py
if not db.is_email_whitelisted(email):
    # Log for security monitoring
    await log_audit_event(
        event_type="authentication",
        action="email_login_request",
        user_id=email,
        result="denied",
        details={"reason": "not_whitelisted"},
        severity="warning"
    )
    # Return success to prevent email enumeration
    return {"success": True, "message": "If your email is registered, you'll receive a code shortly"}
```

### Rate Limiting

**3 code requests per 10 minutes per email:**

```python
# Line 337-351 in auth.py
recent_requests = db.count_recent_code_requests(email, minutes=10)
if recent_requests >= 3:
    await log_audit_event(
        event_type="authentication",
        action="email_login_request",
        user_id=email,
        result="denied",
        details={"reason": "rate_limit"},
        severity="warning"
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests. Please try again in 10 minutes"
    )
```

### Code Expiration

- Codes expire 10 minutes after creation
- Expired codes are rejected during verification
- Old codes are cleaned up by `cleanup_old_codes()` (can be run as scheduled task)

### Single-Use Codes

- Codes marked as `verified=1` after successful use
- `used_at` timestamp recorded
- Subsequent attempts with same code fail

### JWT Token Security

- 7-day expiration (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Tokens include `mode="email"` claim for tracking
- SECRET_KEY must be set in production (auto-generated warning on startup)

### Audit Logging

All operations are logged to audit service:

| Event Type | Action | Details |
|------------|--------|---------|
| `authentication` | `email_login_request` | Code request (success/denied) |
| `authentication` | `email_login_code_sent` | Email sent status |
| `authentication` | `email_login_verify` | Code verification (success/failed) |
| `authentication` | `email_login` | Successful login |
| `email_whitelist` | `list` | List whitelist |
| `email_whitelist` | `add` | Add email to whitelist |
| `email_whitelist` | `remove` | Remove email from whitelist |
| `agent_sharing` | `share` | Agent shared (triggers auto-whitelist) |

---

## Error Handling

| Error Case | HTTP Status | Message | Handling |
|------------|-------------|---------|----------|
| Setup not completed | 403 | `setup_required` | Block login until first-time setup done |
| Email auth disabled | 403 | `Email authentication is disabled` | Check `EMAIL_AUTH_ENABLED` setting |
| Email not whitelisted | 200 | Generic success (prevents enumeration) | Logs audit event with `result="denied"` |
| Rate limit exceeded | 429 | `Too many requests. Please try again in 10 minutes` | 3 requests per 10 min per email |
| Invalid code | 401 | `Invalid or expired verification code` | Code doesn't exist, expired, or already used |
| Code expired | 401 | `Invalid or expired verification code` | Code older than 10 minutes |
| User creation failed | 500 | `Failed to create user account` | Database error |
| Email already whitelisted | 409 | `Email {email} is already whitelisted` | Duplicate email in POST whitelist |
| Email not in whitelist | 404 | `Email {email} not found in whitelist` | DELETE non-existent email |
| User not found (whitelist add) | 400 | `User not found: {username}` | Invalid `added_by` user |

---

## Configuration Examples

### Development Setup (Console Email)

```yaml
# docker-compose.yml
backend:
  environment:
    - EMAIL_AUTH_ENABLED=true
    - EMAIL_PROVIDER=console  # Prints codes to logs
```

**Code appears in console:**
```
[EMAIL to user@example.com] Subject: Your verification code
Body: Your verification code is: 123456

This code expires in 10 minutes.
```

### Production Setup (Resend)

```yaml
# docker-compose.yml
backend:
  environment:
    - EMAIL_AUTH_ENABLED=true
    - EMAIL_PROVIDER=resend
    - RESEND_API_KEY=re_xxxxxxxxxxxxx
    - SMTP_FROM=noreply@yourdomain.com
```

### Production Setup (SMTP)

```yaml
backend:
  environment:
    - EMAIL_AUTH_ENABLED=true
    - EMAIL_PROVIDER=smtp
    - SMTP_HOST=smtp.gmail.com
    - SMTP_PORT=587
    - SMTP_USER=your-email@gmail.com
    - SMTP_PASSWORD=your-app-password
    - SMTP_FROM=noreply@yourdomain.com
```

### Disabling Email Auth

To disable email authentication and use only Auth0 or dev mode:

**Via environment variable:**
```yaml
backend:
  environment:
    - EMAIL_AUTH_ENABLED=false
```

**Via system settings (runtime toggle):**
```bash
# Via API or database
curl -X PUT /api/settings/email_auth_enabled \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"value": "false"}'
```

---

## Related Flows

### Upstream Dependencies
- **First-Time Setup** ([first-time-setup.md](first-time-setup.md)) - Must complete setup before login
- **Auth Mode Detection** ([auth0-authentication.md](auth0-authentication.md)) - Runtime detection of available auth methods

### Downstream Flows
- **Agent Sharing** ([agent-sharing.md](agent-sharing.md)) - Auto-adds emails to whitelist
- **User Management** - Email becomes username for email auth users

### Interaction with Other Auth Methods

Email authentication coexists with other methods:

| Mode | Priority | Use Case |
|------|----------|----------|
| Email Auth | Default | Passwordless login for whitelisted users |
| Auth0 OAuth | Production | Google OAuth for @ability.ai domain |
| Dev Mode | Development | Local username/password for testing |

**Detection endpoint** (`GET /api/auth/mode`) returns all available modes:
```json
{
  "dev_mode_enabled": false,
  "auth0_configured": true,
  "email_auth_enabled": true,
  "allowed_domain": "ability.ai",
  "setup_completed": true
}
```

---

## Testing

### Prerequisites
- Backend running with `EMAIL_AUTH_ENABLED=true`
- Email service configured (use `EMAIL_PROVIDER=console` for dev)
- At least one admin user exists (via first-time setup)

### Manual Testing Steps

#### 1. Admin Adds Email to Whitelist

**Action:**
```bash
# Login as admin first
curl -X POST http://localhost:8000/api/token \
  -d "username=admin&password=your-password"

export TOKEN="<jwt-token>"

# Add email to whitelist
curl -X POST http://localhost:8000/api/settings/email-whitelist \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser@example.com", "source": "manual"}'
```

**Expected:**
```json
{
  "success": true,
  "email": "testuser@example.com"
}
```

**Verify:**
```bash
curl -X GET http://localhost:8000/api/settings/email-whitelist \
  -H "Authorization: Bearer $TOKEN"
```

#### 2. User Requests Login Code

**Action:**
```bash
curl -X POST http://localhost:8000/api/auth/email/request \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser@example.com"}'
```

**Expected:**
```json
{
  "success": true,
  "message": "Verification code sent to your email",
  "expires_in_seconds": 600
}
```

**Verify:**
- Check backend logs (if EMAIL_PROVIDER=console)
- Check email inbox (if using real email provider)
- Code should be 6 digits: `123456`

#### 3. User Verifies Code

**Action:**
```bash
curl -X POST http://localhost:8000/api/auth/email/verify \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser@example.com", "code": "123456"}'
```

**Expected:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "username": "testuser@example.com",
    "email": "testuser@example.com",
    "role": "user",
    "name": null,
    "picture": null
  }
}
```

**Verify:**
```bash
# Use token to access authenticated endpoint
curl -X GET http://localhost:8000/api/agents \
  -H "Authorization: Bearer <access-token>"
```

#### 4. Rate Limiting Test

**Action:**
```bash
# Send 4 code requests within 10 minutes
for i in {1..4}; do
  curl -X POST http://localhost:8000/api/auth/email/request \
    -H "Content-Type: application/json" \
    -d '{"email": "testuser@example.com"}'
  echo ""
done
```

**Expected:**
- First 3 requests: Success
- 4th request: `429 Too Many Requests`

**Verify:**
```json
{
  "detail": "Too many requests. Please try again in 10 minutes"
}
```

#### 5. Email Enumeration Prevention Test

**Action:**
```bash
# Try to request code for non-whitelisted email
curl -X POST http://localhost:8000/api/auth/email/request \
  -H "Content-Type: application/json" \
  -d '{"email": "notwhitelisted@example.com"}'
```

**Expected:**
```json
{
  "success": true,
  "message": "If your email is registered, you'll receive a code shortly"
}
```

**Verify:**
- Response looks the same as whitelisted email (no enumeration)
- Check audit logs for `result="denied"`, `reason="not_whitelisted"`

#### 6. Auto-Whitelist on Agent Share

**Action:**
```bash
# Share agent with new email
curl -X POST http://localhost:8000/api/agents/test-agent/share \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com"}'
```

**Expected:**
```json
{
  "id": 2,
  "agent_name": "test-agent",
  "shared_with_email": "newuser@example.com",
  "shared_by_id": 1,
  "shared_by_email": "admin@example.com",
  "created_at": "2025-12-26T12:00:00Z"
}
```

**Verify:**
```bash
# Check whitelist - newuser@example.com should be added
curl -X GET http://localhost:8000/api/settings/email-whitelist \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected whitelist entry:**
```json
{
  "id": 3,
  "email": "newuser@example.com",
  "added_by": "1",
  "added_by_username": "admin",
  "added_at": "2025-12-26T12:00:00Z",
  "source": "agent_sharing"
}
```

#### 7. Code Expiration Test

**Action:**
```bash
# Request code
curl -X POST http://localhost:8000/api/auth/email/request \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser@example.com"}'

# Wait 11 minutes (or modify expires_at in database)

# Try to verify expired code
curl -X POST http://localhost:8000/api/auth/email/verify \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser@example.com", "code": "123456"}'
```

**Expected:**
```json
{
  "detail": "Invalid or expired verification code"
}
```

#### 8. Single-Use Code Test

**Action:**
```bash
# Request and verify code successfully
CODE=$(curl -X POST http://localhost:8000/api/auth/email/request \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser@example.com"}' | grep code)

# Verify once (success)
curl -X POST http://localhost:8000/api/auth/email/verify \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser@example.com", "code": "'$CODE'"}'

# Try to verify same code again (fail)
curl -X POST http://localhost:8000/api/auth/email/verify \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser@example.com", "code": "'$CODE'"}'
```

**Expected on 2nd attempt:**
```json
{
  "detail": "Invalid or expired verification code"
}
```

### Audit Log Verification

Check audit logger for complete event trail:

```bash
# View audit logs
curl -X GET http://localhost:8001/api/audit/events?limit=50

# Filter for email auth events
curl -X GET "http://localhost:8001/api/audit/events?event_type=authentication&action=email_login"
```

**Expected events:**
1. `email_login_request` - Code requested
2. `email_login_code_sent` - Email sent
3. `email_login_verify` - Code verification attempt
4. `email_login` - Successful login
5. `email_whitelist/add` - Email added to whitelist
6. `agent_sharing/share` - Agent shared (if testing auto-whitelist)

### Edge Cases

| Scenario | Expected Behavior |
|----------|------------------|
| Email auth disabled | 403 "Email authentication is disabled" |
| Setup not completed | 403 "setup_required" |
| Invalid email format | 422 Validation error from Pydantic |
| Code with wrong email | 401 "Invalid or expired verification code" |
| Database error during user creation | 500 "Failed to create user account" |
| Email service down | Code created but email fails (audit log shows `email_sent=false`) |

### Status

- **Backend Implementation**: ✅ Complete (Phase 12.4)
- **Frontend Implementation**: 🚧 TODO
  - `src/frontend/src/stores/auth.js` - Add email auth methods
  - `src/frontend/src/views/Login.vue` - Add email login UI
  - `src/frontend/src/views/Settings.vue` - Add Email Whitelist tab
- **Email Service**: ✅ Complete (console, SMTP, SendGrid, Resend)
- **Auto-Whitelist**: ✅ Complete (agent sharing integration)
- **Audit Logging**: ✅ Complete
- **Security**: ✅ Complete (rate limiting, enumeration prevention, code expiration)

---

## Implementation Checklist

### Backend (Completed)
- [x] Database schema (email_whitelist, email_login_codes)
- [x] EmailAuthOperations class
- [x] POST /api/auth/email/request endpoint
- [x] POST /api/auth/email/verify endpoint
- [x] GET /api/settings/email-whitelist endpoint
- [x] POST /api/settings/email-whitelist endpoint
- [x] DELETE /api/settings/email-whitelist/{email} endpoint
- [x] Email service (console, SMTP, SendGrid, Resend)
- [x] Rate limiting (3 per 10 min)
- [x] Email enumeration prevention
- [x] Code expiration (10 minutes)
- [x] Single-use codes
- [x] Audit logging
- [x] Auto-whitelist on agent sharing
- [x] Runtime enable/disable via settings

### Frontend (TODO)
- [ ] Add `emailAuthEnabled` to auth store state
- [ ] Add `requestEmailCode()` method to auth store
- [ ] Add `verifyEmailCode()` method to auth store
- [ ] Update Login.vue with email auth form
  - [ ] Step 1: Email input + "Send code" button
  - [ ] Step 2: Code input (6 digits) + "Verify" button
  - [ ] Error handling and loading states
- [ ] Add Email Whitelist tab to Settings.vue
  - [ ] List whitelist with source badges
  - [ ] Add email dialog
  - [ ] Remove email confirmation
  - [ ] Admin-only access
- [ ] Update GET /api/auth/mode to check `email_auth_enabled`
- [ ] Test complete flow end-to-end

### Documentation (Completed)
- [x] Feature flow document
- [x] Security considerations
- [x] Testing instructions
- [x] Configuration examples

---

## Notes

### Why Email = Username?

Email authentication users have their email as their username for simplicity:
- Username = email (lowercase)
- No password field (email auth only)
- Role defaults to "user"
- Can still be looked up by email or username

This is implemented in `get_or_create_email_user()`:

```python
# Line 243-248 in db/email_auth.py
username = email.lower()

cursor.execute("""
    INSERT INTO users (username, email, role, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?)
""", (username, email.lower(), "user", now, now))
```

### JWT Mode Claim

All email auth JWTs include `mode="email"` for tracking:

```python
# Line 438-443 in routers/auth.py
access_token = create_access_token(
    data={"sub": user["username"]},
    expires_delta=access_token_expires,
    mode="email"  # Mark as email auth token
)
```

This allows distinguishing between:
- `mode="dev"` - Dev mode (username/password)
- `mode="prod"` - Auth0 OAuth
- `mode="email"` - Email verification code

### Source Tracking

The whitelist tracks how emails were added:
- `source="manual"` - Added by admin via Settings page
- `source="agent_sharing"` - Auto-added when agent was shared

This provides an audit trail and helps admins understand whitelist growth.

### Cleanup Strategy

Old verification codes should be cleaned up periodically:

```python
# Can be run as a scheduled task (e.g., daily cron)
db.cleanup_old_codes(days=1)  # Delete codes older than 1 day
```

This is not currently scheduled but can be added to the System Agent or a separate cleanup task.
