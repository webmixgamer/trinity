# Feature: Credentials Page

## Overview
Global credential management page (`/credentials`) for creating, viewing, and deleting platform-wide credentials stored in Redis. Credentials created here can later be assigned to specific agents for injection.

> **Note**: This feature flow documents the Credentials Page UI at `/credentials`. For credential injection into agents, see [credential-injection.md](credential-injection.md).

## User Story
As a platform user, I want to manage my API keys and tokens in a central location so that I can easily assign them to multiple agents without re-entering credentials.

---

## Entry Points

| Entry Point | Location | Description |
|-------------|----------|-------------|
| **NavBar Link** | `src/frontend/src/components/NavBar.vue:32-38` | "Credentials" navigation link |
| **Route** | `src/frontend/src/router/index.js:54-58` | `/credentials` route definition |

### Route Definition
```javascript
// src/frontend/src/router/index.js:54-58
{
  path: '/credentials',
  name: 'Credentials',
  component: () => import('../views/Credentials.vue'),
  meta: { requiresAuth: true }
}
```

---

## Frontend Layer

### Component: `Credentials.vue`
**File**: `src/frontend/src/views/Credentials.vue` (673 lines)

#### State Management
```javascript
// Lines 384-412: Reactive state
const credentials = ref([])
const loading = ref(true)
const showCreateModal = ref(false)
const creating = ref(false)
const showBulkImport = ref(false)
const bulkImportContent = ref('')
const bulkImporting = ref(false)
const bulkImportResult = ref(null)
const templates = ref([])
const selectedTemplateForEnv = ref('')

// New credential form state (lines 401-412)
const newCredential = ref({
  name: '',
  service: '',
  type: 'api_key',  // Default type
  api_key: '',
  token: '',
  username: '',
  password: '',
  file_path: '',
  file_content: '',
  description: ''
})
```

#### Component Structure

| Section | Lines | Description |
|---------|-------|-------------|
| Page Header | 7-18 | Title + "Add Credential" button |
| Bulk Import Panel | 20-136 | Expandable panel with template selector and textarea |
| Credentials List | 138-198 | Card list with view/delete actions |
| Create Modal | 202-362 | Form for adding single credential |
| Confirm Dialog | 364-372 | Delete confirmation |

#### UI Features

**1. Bulk Import Section (Lines 20-136)**
- Template selector dropdown to get `.env` template for a specific agent template
- Textarea for pasting `.env` format content (`KEY=VALUE` pairs)
- Auto-detection of service and type from key names
- Import results display (created, skipped, errors)

**2. Template Selector for Bulk Import (Lines 41-77)**
```javascript
// Copy .env template from agent template
const copyEnvTemplate = async () => {
  const response = await fetch(
    `/api/templates/env-template?template_id=${encodeURIComponent(selectedTemplateForEnv.value)}`,
    { headers: { 'Authorization': `Bearer ${authStore.token}` } }
  )
  const data = await response.json()
  await navigator.clipboard.writeText(data.content)
}
```

**3. Credentials List (Lines 138-198)**
- Icon based on service type (getServiceIcon function)
- Type badge (api_key, token, basic_auth, file)
- Service badge (openai, anthropic, google, etc.)
- File path display for file-type credentials
- View and Delete action buttons

**4. Create Credential Modal (Lines 202-362)**
Dynamic form fields based on credential type:

| Type | Fields |
|------|--------|
| `api_key` | API Key (password input) |
| `token` | Token (password input) |
| `basic_auth` | Username + Password |
| `file` | File Path + File Content (upload or paste) |

---

## Backend Layer

### Router: `credentials.py`
**File**: `src/backend/routers/credentials.py`
**Prefix**: `/api`

#### Endpoints

| Method | Endpoint | Lines | Description |
|--------|----------|-------|-------------|
| `POST` | `/credentials` | 44-56 | Create single credential |
| `GET` | `/credentials` | 59-70 | List all user credentials |
| `GET` | `/credentials/{cred_id}` | 73-85 | Get single credential |
| `PUT` | `/credentials/{cred_id}` | 88-101 | Update credential |
| `DELETE` | `/credentials/{cred_id}` | 104-116 | Delete credential |
| `POST` | `/credentials/bulk` | 119-177 | Bulk import from .env text |

#### Create Credential Endpoint
```python
# src/backend/routers/credentials.py:44-56
@router.post("/credentials", response_model=Credential)
async def create_credential(
    cred_data: CredentialCreate,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Create a new credential."""
    try:
        credential = credential_manager.create_credential(current_user.username, cred_data)
        return credential
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create credential: {str(e)}")
```

#### Bulk Import Endpoint
```python
# src/backend/routers/credentials.py:119-177
@router.post("/credentials/bulk", response_model=BulkCredentialResult)
async def bulk_import_credentials(
    import_data: BulkCredentialImport,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Bulk import credentials from .env-style text content."""
    parsed = parse_env_content(import_data.content)

    for key, value in parsed:
        service = infer_service_from_key(key)
        cred_type = infer_type_from_key(key)
        # ... create credential
```

---

## Data Layer

### Credential Manager
**File**: `src/backend/credentials.py`

#### Class: `CredentialManager`
Redis-backed credential storage with user isolation.

```python
# src/backend/credentials.py:82-91
class CredentialManager:
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.credentials_prefix = "credentials:"
        self.oauth_state_prefix = "oauth_state:"
```

#### Redis Key Structure

| Key Pattern | Purpose |
|-------------|---------|
| `credentials:{cred_id}:metadata` | Hash with name, service, type, description, file_path, timestamps |
| `credentials:{cred_id}:secret` | JSON string with actual credential values |
| `user:{user_id}:credentials` | Set of credential IDs owned by user |

#### Methods

| Method | Lines | Description |
|--------|-------|-------------|
| `create_credential()` | 98-136 | Create new credential with metadata and secret |
| `get_credential()` | 138-155 | Retrieve credential metadata (not secrets) |
| `get_credential_secret()` | 157-169 | Retrieve actual credential values |
| `list_credentials()` | 171-181 | List all credentials for a user |
| `update_credential()` | 183-203 | Update credential name/description/values |
| `delete_credential()` | 205-218 | Remove credential from Redis |

#### Create Credential Implementation
```python
# src/backend/credentials.py:98-136
def create_credential(self, user_id: str, cred_data: CredentialCreate) -> Credential:
    cred_id = self._generate_id()
    now = datetime.utcnow()

    # Store metadata (public info)
    cred_key = f"{self.credentials_prefix}{cred_id}"
    metadata_key = f"{cred_key}:metadata"
    self.redis_client.hset(metadata_key, mapping={
        "id": cred_id,
        "name": cred_data.name,
        "service": cred_data.service,
        "type": cred_data.type,
        "description": cred_data.description or "",
        "file_path": cred_data.file_path or "",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "status": "active",
        "user_id": user_id
    })

    # Store secret separately
    secret_key = f"{cred_key}:secret"
    self.redis_client.set(secret_key, json.dumps(cred_data.credentials))

    # Track ownership
    user_creds_key = f"user:{user_id}:credentials"
    self.redis_client.sadd(user_creds_key, cred_id)

    return credential
```

---

## Credential Types

### Type Definitions
**File**: `src/backend/credentials.py:13-18`

| Type | Storage Key | Usage |
|------|-------------|-------|
| `api_key` | `api_key` | Standard API keys (OpenAI, Anthropic, etc.) |
| `token` | `token` | OAuth tokens, PATs |
| `basic_auth` | `username`, `password` | HTTP Basic Auth |
| `oauth2` | `access_token`, `refresh_token` | OAuth 2.0 tokens |
| `file` | `content` + `file_path` | JSON/YAML files (service accounts) |

### File-Type Credentials
For file-based credentials (e.g., GCP service accounts):

```javascript
// Frontend (Credentials.vue:517-521)
if (newCredential.value.type === 'file') {
  credentials_data = { content: newCredential.value.file_content }
  file_path = newCredential.value.file_path  // e.g., ".config/gcloud/sa.json"
}
```

```python
# Backend storage (credentials.py:108)
file_path=cred_data.file_path  # Stored in metadata, not secret
```

---

## Service Detection

### Service Inference from Key Names
**File**: `src/backend/utils/helpers.py:137-184`

```python
def infer_service_from_key(key: str) -> str:
    """Infer service name from environment variable name."""
    service_patterns = [
        ('HEYGEN_', 'heygen'),
        ('OPENAI_', 'openai'),
        ('ANTHROPIC_', 'anthropic'),
        ('GOOGLE_', 'google'),
        ('GITHUB_', 'github'),
        ('SLACK_', 'slack'),
        ('NOTION_', 'notion'),
        # ... more patterns
    ]
    # Returns 'custom' if no match
```

### Type Inference
**File**: `src/backend/utils/helpers.py:187-200`

```python
def infer_type_from_key(key: str) -> str:
    """Infer credential type from environment variable name."""
    if '_API_KEY' in key_upper or key_upper.endswith('_KEY'):
        return 'api_key'
    elif '_TOKEN' in key_upper:
        return 'token'
    elif '_SECRET' in key_upper:
        return 'api_key'
    elif '_PASSWORD' in key_upper:
        return 'basic_auth'
    return 'api_key'
```

---

## Service Icons

### Icon Mapping
**File**: `src/frontend/src/views/Credentials.vue:651-662`

```javascript
const getServiceIcon = (service) => {
  const icons = {
    openai: '...',      // Robot
    anthropic: '...',   // Brain
    google: '...',      // Magnifying glass
    slack: '...',       // Speech bubble
    github: '...',      // Octopus
    notion: '...',      // Memo
    custom: '...'       // Wrench
  }
  return icons[service] || '...'  // Key (default)
}
```

---

## API Calls

### Frontend API Methods

| Action | Method | Endpoint | Lines |
|--------|--------|----------|-------|
| Fetch all | `fetchCredentials()` | `GET /api/credentials` | 424-438 |
| Fetch templates | `fetchTemplates()` | `GET /api/templates` | 441-454 |
| Copy env template | `copyEnvTemplate()` | `GET /api/templates/env-template` | 456-488 |
| Create | `createCredential()` | `POST /api/credentials` | 501-569 |
| Delete | `deleteCredential()` | `DELETE /api/credentials/{id}` | 572-594 |
| Bulk import | `bulkImportCredentials()` | `POST /api/credentials/bulk` | 596-644 |

### View Credential (Simple Alert)
```javascript
// src/frontend/src/views/Credentials.vue:647-649
const viewCredential = (cred) => {
  alert(`Credential: ${cred.name}\nService: ${cred.service}\nType: ${cred.type}`)
}
```

> **Note**: The View button shows a simple alert with metadata. Actual secrets are not displayed in the UI for security.

---

## Bulk Import Flow

### Parse .env Content
**File**: `src/backend/utils/helpers.py:96-134`

```python
def parse_env_content(content: str) -> List[Tuple[str, str]]:
    """
    Parse .env-style content into list of (key, value) tuples.

    Handles:
    - KEY=VALUE
    - KEY="VALUE WITH SPACES"
    - KEY='VALUE WITH SPACES'
    - # comments (ignored)
    - Empty lines (ignored)
    """
    # Key must match: ^[A-Z][A-Z0-9_]*$
```

### Bulk Import Sequence

```
User pastes .env content
        |
        v
POST /api/credentials/bulk
        |
        v
parse_env_content() -> [(key, value), ...]
        |
        v
For each (key, value):
  - infer_service_from_key(key)
  - infer_type_from_key(key)
  - create_credential()
        |
        v
Return BulkCredentialResult:
  - created: count
  - skipped: count
  - errors: [messages]
  - credentials: [{id, name, service, type}]
```

---

## Templates Integration

### Get .env Template for Agent Template
**File**: `src/backend/routers/templates.py:62-130`

```python
@router.get("/env-template")
async def get_template_env_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get a .env template file with all required credential keys for a template.
    Returns text content that can be copied/downloaded and filled in.
    """
    # 1. Load template (GitHub or local)
    # 2. Extract required_credentials from template.yaml
    # 3. Group by service
    # 4. Format as .env template with placeholders
```

This helps users know exactly which credentials are needed for a specific agent template.

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Invalid JSON | 422 | Validation error |
| Create failed | 500 | `Failed to create credential: {error}` |
| Not found | 404 | `Credential not found` |
| No valid pairs | 400 | `No valid KEY=VALUE pairs found in content` |
| Template not found | 404 | `Template not found` |

---

## Security Considerations

1. **User Isolation**: Credentials are stored per-user via `user:{user_id}:credentials` set
2. **Secrets Separated**: Metadata and secrets stored in separate Redis keys
3. **No Secret Display**: View button only shows metadata, not actual values
4. **Auth Required**: All endpoints require JWT authentication
5. **Owner Verification**: `get_credential()` verifies `user_id` matches owner

---

## Pydantic Models

### Request Models
**File**: `src/backend/credentials.py:30-42`

```python
class CredentialCreate(BaseModel):
    name: str
    service: str
    type: str
    credentials: Dict
    description: Optional[str] = None
    file_path: Optional[str] = None  # For file-type credentials
```

### Response Models
**File**: `src/backend/credentials.py:43-52`

```python
class Credential(BaseModel):
    id: str
    name: str
    service: str
    type: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    status: str = "active"
```

### Bulk Import Models
**File**: `src/backend/models.py:70-81`

```python
class BulkCredentialImport(BaseModel):
    content: str  # .env-style content

class BulkCredentialResult(BaseModel):
    created: int
    skipped: int
    errors: List[str]
    credentials: List[dict]
```

---

## Related Flows

| Flow | Relationship |
|------|--------------|
| [credential-injection.md](credential-injection.md) | **Downstream** - Assign credentials to agents and inject into containers |
| [template-processing.md](template-processing.md) | **Upstream** - Templates define required credentials |
| [agent-lifecycle.md](agent-lifecycle.md) | Credentials injected on agent start |

---

## Testing

### Prerequisites
- Trinity platform running (`./scripts/deploy/start.sh`)
- User logged in

### Test Steps

1. **Navigate to Credentials Page**
   - Action: Click "Credentials" in NavBar
   - Expected: `/credentials` page loads with empty or existing credentials list

2. **Add Single Credential**
   - Action: Click "Add Credential" button
   - Fill form: Name="TEST_KEY", Service="custom", Type="api_key", Value="test123"
   - Click "Create"
   - Expected: Modal closes, new credential appears in list

3. **Bulk Import**
   - Action: Click "Show import" in Bulk Import section
   - Paste: `OPENAI_API_KEY=sk-test123\nGITHUB_TOKEN=ghp_test456`
   - Click "Import Credentials"
   - Expected: Shows "Created 2 credential(s)", credentials appear in list with correct services

4. **Delete Credential**
   - Action: Click "Delete" on a credential
   - Confirm in dialog
   - Expected: Credential removed from list

5. **Copy Template**
   - Action: Select template in "Get credential template for:" dropdown
   - Click "Copy Template"
   - Expected: `.env` template copied to clipboard with placeholder values

### Edge Cases
- Empty bulk import content -> No credentials created
- Invalid KEY format (lowercase) -> Skipped with error
- Duplicate key names -> Each creates separate credential

---

## Revision History

| Date | Change |
|------|--------|
| 2026-01-21 | Initial documentation |
