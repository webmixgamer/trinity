# Feature: Credential Injection

## Overview
Multi-layer credential management system enabling secure storage, injection, and hot-reload of API keys and OAuth tokens into running agent containers. Credentials flow from user input through Redis storage to agent container files (.env, .mcp.json).

## User Story
As a platform user, I want to configure API credentials for my agents so that MCP servers and tools can authenticate with external services without exposing secrets.

---

## Entry Points

| UI Location | API Endpoint | Purpose |
|-------------|--------------|---------|
| `src/frontend/src/views/Credentials.vue` | `POST /api/credentials` | Single credential entry |
| `src/frontend/src/views/Credentials.vue:96-107` | `POST /api/credentials/bulk` | Bulk import (.env paste) |
| `src/frontend/src/views/AgentDetail.vue` | `GET /api/agents/{name}/credentials/assignments` | List assigned/available credentials |
| `src/frontend/src/views/AgentDetail.vue` | `POST /api/agents/{name}/credentials/assign` | Assign credential to agent |
| `src/frontend/src/views/AgentDetail.vue` | `DELETE /api/agents/{name}/credentials/assign/{id}` | Unassign credential from agent |
| `src/frontend/src/views/AgentDetail.vue` | `POST /api/agents/{name}/credentials/apply` | Apply assigned credentials to running agent |
| `src/frontend/src/views/AgentDetail.vue` | `POST /api/agents/{name}/credentials/hot-reload` | Quick-add: create, assign, and apply |

> **Note (2025-12-07)**: OAuth provider buttons ("Connect Services" section with Google, Slack, GitHub, Notion) were **removed** from Credentials.vue. OAuth flows remain available via backend API endpoints but are no longer exposed in the UI.

> **Note (2025-12-30)**: Credential injection is now **assignment-based**. No credentials are injected by default - users must explicitly assign credentials to each agent via the Credentials tab in Agent Detail.

---

## Flow 1: Manual Credential Entry

### Frontend (`src/frontend/src/views/Credentials.vue:501-569`)
```javascript
const createCredential = async () => {
  let credentials_data = {}
  let file_path = null

  if (newCredential.value.type === 'api_key') {
    credentials_data = { api_key: newCredential.value.api_key }
  } else if (newCredential.value.type === 'file') {
    credentials_data = { content: newCredential.value.file_content }
    file_path = newCredential.value.file_path
  }
  // ...

  const response = await fetch('/api/credentials', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${authStore.token}` },
    body: JSON.stringify({
      name: newCredential.value.name,
      service: newCredential.value.service,
      type: newCredential.value.type,
      credentials: credentials_data,
      description: newCredential.value.description,
      file_path: file_path  // For file-type credentials
    })
  })
}
```

### Backend (`src/backend/routers/credentials.py:44-56`)
```python
@router.post("/credentials", response_model=Credential)
async def create_credential(
    cred_data: CredentialCreate,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    credential = credential_manager.create_credential(current_user.username, cred_data)
    return credential
```

### Redis Storage (`src/backend/credentials.py:98-136`)
```python
def create_credential(self, user_id: str, cred_data: CredentialCreate) -> Credential:
    cred_id = self._generate_id()
    now = datetime.utcnow()

    cred_key = f"{self.credentials_prefix}{cred_id}"
    metadata_key = f"{cred_key}:metadata"
    secret_key = f"{cred_key}:secret"
    user_creds_key = f"user:{user_id}:credentials"

    self.redis_client.hset(metadata_key, mapping={
        "id": cred_id,
        "name": cred_data.name,
        "service": cred_data.service,
        "type": cred_data.type,
        "file_path": cred_data.file_path or "",  # For file-type credentials
        # ...
    })

    self.redis_client.set(secret_key, json.dumps(cred_data.credentials))
    self.redis_client.sadd(user_creds_key, cred_id)

    return credential
```

---

## Flow 2: Bulk Credential Import

### Frontend (`src/frontend/src/views/Credentials.vue:82-107`)
User pastes `.env`-style content into textarea, clicks "Import Credentials" (line 98).

### Backend (`src/backend/routers/credentials.py:119-177`)
```python
@router.post("/credentials/bulk", response_model=BulkCredentialResult)
async def bulk_import_credentials(
    import_data: BulkCredentialImport,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    parsed = parse_env_content(import_data.content)  # line 126

    for key, value in parsed:
        service = infer_service_from_key(key)  # line 141
        cred_type = infer_type_from_key(key)   # line 142

        cred_data = CredentialCreate(
            name=key,
            service=service,
            type=cred_type,
            credentials={key: value},  # line 149
            description="Bulk imported credential"
        )

        credential = credential_manager.create_credential(current_user.username, cred_data)
        created_count += 1
```

### Parser (`src/backend/utils/helpers.py:96-200`)
```python
def parse_env_content(content: str) -> List[Tuple[str, str]]:
    """Parse .env-style KEY=VALUE pairs"""
    for line in content.split('\n'):
        if '=' in line:
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip()
            # Remove surrounding quotes
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            # Validate key format (must be uppercase with underscores)
            if re.match(r'^[A-Z][A-Z0-9_]*$', key):
                results.append((key, value))
    return results

def infer_service_from_key(key: str) -> str:
    """Auto-detect service from key name prefix"""
    service_patterns = [
        ('HEYGEN_', 'heygen'),
        ('TWITTER_', 'twitter'),
        ('OPENAI_', 'openai'),
        ('ANTHROPIC_', 'anthropic'),
        ('CLOUDINARY_', 'cloudinary'),
        ('GOOGLE_', 'google'),
        ('SLACK_', 'slack'),
        ('GITHUB_', 'github'),
        ('NOTION_', 'notion'),
        # ... 20+ more patterns
    ]
    for prefix, service in service_patterns:
        if key_upper.startswith(prefix):
            return service
    return 'custom'

def infer_type_from_key(key: str) -> str:
    """Infer credential type from key name"""
    if '_API_KEY' in key_upper or key_upper.endswith('_KEY'):
        return 'api_key'
    elif '_TOKEN' in key_upper:
        return 'token'
    elif '_SECRET' in key_upper:
        return 'api_key'
    elif '_PASSWORD' in key_upper:
        return 'basic_auth'
    else:
        return 'api_key'
```

---

## Flow 3: Hot-Reload Credentials

> **Updated 2025-12-28**: Hot-reload now persists credentials to Redis with conflict resolution. Credentials survive agent restarts.

### Frontend (`src/frontend/src/composables/useAgentCredentials.js:141-171`)
```javascript
const quickAddCredentials = async () => {
  if (!agentRef.value || agentRef.value.status !== 'running') return
  if (!quickAddText.value.trim()) return

  quickAddLoading.value = true
  const result = await agentsStore.hotReloadCredentials(
    agentRef.value.name,
    quickAddText.value  // KEY=VALUE format
  )
  // Result includes saved_to_redis with status: created/reused/renamed
}
```

### Store Action (`src/frontend/src/stores/agents.js:232-239`)
```javascript
async hotReloadCredentials(name, credentialsText) {
  const authStore = useAuthStore()
  const response = await axios.post(`/api/agents/${name}/credentials/hot-reload`,
    { credentials_text: credentialsText },
    { headers: authStore.authHeader }
  )
  return response.data
}
```

### Backend (`src/backend/routers/credentials.py:508-614`)
```python
@router.post("/agents/{agent_name}/credentials/hot-reload")
async def hot_reload_credentials(agent_name: str, request_body: HotReloadCredentialsRequest,
                                  request: Request, current_user: User = Depends(get_current_user)):
    """Hot-reload credentials on a running agent by parsing .env-style text.

    This endpoint:
    1. Parses .env-style KEY=VALUE text
    2. Saves each credential to Redis (with conflict resolution)
    3. Assigns credentials to this agent
    4. Pushes credentials to the running agent's .env file

    Credentials are persisted in Redis so they survive agent restarts.
    """
    container = get_agent_container(agent_name)
    # ... validation ...

    # Parse credentials from text
    credentials = {}
    for line in request_body.credentials_text.splitlines():
        # ... parse KEY=VALUE pairs ...

    # Save credentials to Redis with conflict resolution AND assign to agent
    saved_credentials = []
    for key, value in credentials.items():
        result = credential_manager.import_credential_with_conflict_resolution(
            key, value, current_user.username
        )
        saved_credentials.append({
            "name": result["name"],
            "status": result["status"],  # created/reused/renamed
            "original": result.get("original")
        })

        # Also assign the credential to this agent
        cred = credential_manager.get_credential_by_name(result["name"], current_user.username)
        if cred:
            credential_manager.assign_credential(agent_name, cred.id, current_user.username)

    # Push credentials to the running agent
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://agent-{agent_name}:8000/api/credentials/update",
            json={"credentials": credentials, "mcp_config": None},
            timeout=30.0
        )

    return {
        "credential_names": list(credentials.keys()),
        "saved_to_redis": saved_credentials,  # Shows Redis persistence status
        "updated_files": agent_response.get("updated_files", []),
        "note": "MCP servers may need to be restarted..."
    }
```

### Agent Container (`docker/base-image/agent_server/routers/credentials.py:19-121`)

> **Updated 2025-12-19**: Agent-server refactored from monolithic `agent-server.py` to modular package at `docker/base-image/agent_server/`.

> **Updated 2026-01-13**: After writing `.mcp.json`, the endpoint now calls `inject_trinity_mcp_if_configured()` to re-inject Trinity MCP. This ensures agents with `.mcp.json.template` don't lose Trinity MCP on credential reload.

```python
@router.post("/api/credentials/update")
async def update_credentials(request: CredentialUpdateRequest):
    home_dir = Path("/home/developer")
    env_file = home_dir / ".env"
    mcp_file = home_dir / ".mcp.json"
    mcp_template = home_dir / ".mcp.json.template"

    # 1. Write .env file (line 40-49)
    env_lines = ["# Generated by Trinity - Agent credentials", ""]
    for var_name, value in request.credentials.items():
        escaped_value = str(value).replace('"', '\\"')
        env_lines.append(f'{var_name}="{escaped_value}"')
    env_file.write_text("\n".join(env_lines) + "\n")

    # 2. Handle .mcp.json generation (line 52-80)
    if request.mcp_config:
        # Use pre-generated config from backend
        mcp_file.write_text(request.mcp_config)
        # Re-inject Trinity MCP after updating
        inject_trinity_mcp_if_configured()
    elif mcp_template.exists():
        # Generate from template using envsubst-style substitution
        template_content = mcp_template.read_text()
        for var_name, value in request.credentials.items():
            placeholder = f"${{{var_name}}}"
            template_content = template_content.replace(placeholder, str(value))
        mcp_file.write_text(template_content)
        # Re-inject Trinity MCP after regenerating from template
        inject_trinity_mcp_if_configured()

    # 3. Write file-type credentials (line 87-109)
    if request.files:
        for file_path, content in request.files.items():
            target_path = home_dir / file_path.lstrip("/")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content)
            target_path.chmod(0o600)  # Owner read/write only

    # 4. Export to environment
    for var_name, value in request.credentials.items():
        os.environ[var_name] = str(value)

    return {
        "status": "success",
        "updated_files": [str(env_file), str(mcp_file)],
        "credential_count": len(request.credentials),
        "note": "MCP servers may need to be restarted to pick up new credentials"
    }
```

---

## Flow 4: .mcp.json Template Generation

### Template Format
```json
{
  "mcpServers": {
    "heygen": {
      "command": "uvx",
      "args": ["heygen-mcp"],
      "env": {
        "HEYGEN_API_KEY": "${HEYGEN_API_KEY}"
      }
    }
  }
}
```

### Generation at Agent Creation (`src/backend/services/agent_service/crud.py:187-207`)
```python
# Get assigned credential values
flat_credentials = credential_manager.get_assigned_credential_values(config.name, current_user.username)

# Also get legacy credentials for backward compatibility
agent_credentials = credential_manager.get_agent_credentials(config.name, config.mcp_servers, current_user.username)

# Generate credential files
generated_files = generate_credential_files(
    template_data, flat_credentials, config.name,
    template_base_path=github_template_path
)

# Get file-type credentials
file_credentials = credential_manager.get_assigned_file_credentials(config.name, current_user.username)
```

### Generation Logic (`src/backend/services/template_service.py:228-299`)
```python
def generate_credential_files(
    template_data: dict,
    agent_credentials: dict,
    agent_name: str,
    template_base_path: Optional[Path] = None
) -> dict:
    """Generate credential files (.mcp.json, .env, config files) with real values."""
    files = {}

    # Generate .mcp.json with real credentials
    for server_name, server_config in mcp_config.get("mcpServers", {}).items():
        if "env" in server_config:
            for env_key, env_val in server_config["env"].items():
                if isinstance(env_val, str) and env_val.startswith("${") and env_val.endswith("}"):
                    var_name = env_val[2:-1]
                    server_config["env"][env_key] = agent_credentials.get(var_name, "")

    files[".mcp.json"] = json.dumps(mcp_config, indent=2)
    return files
```

---

## Flow 5: OAuth2 Flows

### Supported Providers (`src/backend/credentials.py:54-80`)
- **Google** (Workspace, Drive, Gmail access)
- **Slack** (Bot/User tokens)
- **GitHub** (PAT for repos)
- **Notion** (API access)

### OAuth Configuration (`src/backend/config.py`)
```python
OAUTH_CONFIGS = {
    "google": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
    },
    "slack": {...},
    "github": {...},
    "notion": {...},
}
```

### Init Endpoint (`src/backend/routers/credentials.py:181-208`)

> **Note**: OAuth provider buttons were removed from the Credentials.vue UI on 2025-12-07. OAuth flows remain available via these backend API endpoints.

```python
@router.post("/oauth/{provider}/init")
async def init_oauth(provider: str, request: Request, current_user: User = Depends(get_current_user)):
    if provider not in OAUTH_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unsupported OAuth provider: {provider}")

    config = OAUTH_CONFIGS[provider]
    if not config["client_id"]:
        raise HTTPException(status_code=500, detail=f"OAuth not configured for {provider}")

    redirect_uri = f"{BACKEND_URL}/api/oauth/{provider}/callback"
    state = credential_manager.create_oauth_state(current_user.username, provider, redirect_uri)

    auth_url = credential_manager.build_oauth_url(provider, config["client_id"], redirect_uri, state)

    return {"auth_url": auth_url, "state": state}
```

### Callback Endpoint (`src/backend/routers/credentials.py:211-296`)
```python
@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, code: str, state: str, request: Request):
    state_data = credential_manager.verify_oauth_state(state)

    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    if state_data["provider"] != provider:
        raise HTTPException(status_code=400, detail="Provider mismatch")

    config = OAUTH_CONFIGS[provider]

    # Exchange authorization code for tokens (line 229-235)
    tokens = await credential_manager.exchange_oauth_code(
        provider, code, config["client_id"], config["client_secret"], state_data["redirect_uri"]
    )

    # Normalize credential names for MCP compatibility (line 240-280)
    normalized_creds = {
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        # ...
    }

    # Add MCP-compatible naming (e.g., GOOGLE_ACCESS_TOKEN, SLACK_BOT_TOKEN)
    if provider == "google":
        normalized_creds.update({
            "GOOGLE_ACCESS_TOKEN": tokens.get("access_token"),
            "GOOGLE_REFRESH_TOKEN": tokens.get("refresh_token"),
        })
    # ... (slack, github, notion have similar patterns)

    # Create credential in Redis (line 282-290)
    cred_data = CredentialCreate(
        name=f"{provider.title()} OAuth - {datetime.now().strftime('%Y-%m-%d')}",
        service=provider,
        type="oauth2",
        credentials=normalized_creds,
        description=f"OAuth connection created via authorization flow"
    )

    credential = credential_manager.create_credential(state_data["user_id"], cred_data)

    return {"message": "OAuth authentication successful", "credential_id": credential.id}
```

---

## Flow 6: Credential Reload (from Redis)

### Endpoint (`src/backend/routers/credentials.py:386-471`)
Reloads credentials from Redis store into running agent without manual text entry.

```python
@router.post("/agents/{agent_name}/credentials/reload")
async def reload_agent_credentials(agent_name: str, request: Request,
                                   current_user: User = Depends(get_current_user)):
    container = get_agent_container(agent_name)
    agent_status = get_agent_status_from_container(container)

    if agent_status.status != "running":
        raise HTTPException(status_code=400, detail=f"Agent is not running (status: {agent_status.status})")

    # Get only assigned credentials from Redis (line 429)
    agent_credentials = credential_manager.get_assigned_credential_values(agent_name, current_user.username)

    # Generate .mcp.json if template exists (line 431-434)
    mcp_config = None
    if mcp_template_content and template_data:
        generated_files = generate_credential_files(template_data, agent_credentials, agent_name)
        mcp_config = generated_files.get(".mcp.json")

    # Get file credentials (line 437)
    file_credentials = credential_manager.get_assigned_file_credentials(agent_name, current_user.username)

    # Push to agent (line 439-464)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://agent-{agent_name}:8000/api/credentials/update",
            json={"credentials": agent_credentials, "mcp_config": mcp_config, "files": file_credentials},
            timeout=30.0
        )
```

---

## Redis Data Structure

```
credentials:{cred_id}:metadata  -> HASH {id, name, service, type, user_id, file_path, created_at}
credentials:{cred_id}:secret    -> STRING (JSON blob of secrets)
user:{user_id}:credentials      -> SET of cred_ids
agent:{agent_name}:credentials  -> SET of cred_ids (assigned credentials)
oauth_state:{state_token}       -> STRING (JSON, TTL: 600s)
```

**Example:**
```
redis> HGETALL credentials:abc123:metadata
1) "id"
2) "abc123"
3) "name"
4) "HEYGEN_API_KEY"
5) "service"
6) "heygen"
7) "type"
8) "api_key"
9) "user_id"
10) "admin"

redis> GET credentials:abc123:secret
"{\"api_key\": \"sk_test_123\", \"HEYGEN_API_KEY\": \"sk_test_123\"}"
```

---

## Agent Container File Structure

```
/home/developer/
├── .env                    # Generated from credentials
├── .mcp.json              # Generated from .mcp.json.template
├── .mcp.json.template     # Contains ${VAR} placeholders
└── .env.example           # Documentation
```

**Example .env:**
```bash
HEYGEN_API_KEY="sk_test_123"
TWITTER_API_KEY="abc123"
GOOGLE_ACCESS_TOKEN="ya29...."
```

**Example .mcp.json.template:**
```json
{
  "mcpServers": {
    "heygen": {
      "command": "uvx",
      "args": ["heygen-mcp"],
      "env": {
        "HEYGEN_API_KEY": "${HEYGEN_API_KEY}"
      }
    }
  }
}
```

**Generated .mcp.json:**
```json
{
  "mcpServers": {
    "heygen": {
      "command": "uvx",
      "args": ["heygen-mcp"],
      "env": {
        "HEYGEN_API_KEY": "sk_test_123"
      }
    }
  }
}
```

---

## Flow 7: File-Type Credentials

> **Added 2025-12-30**: Support for injecting entire files (e.g., service account JSON) into agents at specified paths.

### Overview

File-type credentials allow injecting entire files (JSON, YAML, PEM, etc.) into agents at specific paths. This is useful for:
- Google Cloud service account JSON files
- AWS credentials files
- SSL/TLS certificates and keys
- Custom configuration files

### Frontend (`src/frontend/src/views/Credentials.vue:287-331`)

```javascript
// Type selector includes "file" option
<option value="file">File (JSON, etc.)</option>

// File-specific fields
newCredential = {
  type: 'file',
  file_path: '.config/gcloud/service-account.json',  // Target path in agent
  file_content: '{"type": "service_account", ...}'   // File content
}

// createCredential sends file_path separately (line 517-520)
const requestBody = {
  name: 'GCP Service Account',
  service: 'google',
  type: 'file',
  credentials: { content: fileContent },
  file_path: '.config/gcloud/service-account.json'
}
```

### Backend Model (`src/backend/credentials.py:30-36`)

```python
class CredentialCreate(BaseModel):
    name: str
    service: str
    type: str  # Now includes "file"
    credentials: Dict  # For files: {"content": "...file content..."}
    file_path: Optional[str] = None  # Target path relative to /home/developer/

class CredentialType(str):
    FILE = "file"  # File-based credential (e.g., service account JSON)
```

### Redis Storage

```
credentials:{id}:metadata  -> HASH {
    ...,
    type: "file",
    file_path: ".config/gcloud/service-account.json"
}
credentials:{id}:secret    -> STRING '{"content": "...entire file content..."}'
```

### Retrieval (`src/backend/credentials.py:270-304`)

```python
def get_file_credentials(self, user_id: str) -> Dict[str, str]:
    """Get all file-type credentials for a user.
    Returns: {"file_path": "file_content", ...}
    """
    file_credentials = {}
    for cred_id in user_credentials:
        if metadata.get("type") == "file" and metadata.get("file_path"):
            secret = get_credential_secret(cred_id)
            file_credentials[file_path] = secret.get("content", "")
    return file_credentials
```

### Agent Creation Injection (`src/backend/services/agent_service/crud.py:207`)

```python
# Get file credentials during agent creation
file_credentials = credential_manager.get_assigned_file_credentials(config.name, current_user.username)

# Write to credential-files subdirectory
for filepath, content in file_credentials.items():
    file_path = cred_files_dir / "credential-files" / filepath
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
```

### Startup Script (`docker/base-image/startup.sh`)

```bash
# Copy credential files from credential-files/ subdirectory
if [ -d "/generated-creds/credential-files" ]; then
    for file in $(find /generated-creds/credential-files -type f); do
        rel_path="${file#/generated-creds/credential-files/}"
        mkdir -p "/home/developer/$(dirname $rel_path)"
        cp "$file" "/home/developer/$rel_path"
        chmod 600 "/home/developer/$rel_path"  # Restrictive permissions
    done
fi
```

### Hot-Reload (`src/backend/routers/credentials.py:577`)

```python
# Get file credentials and send to agent
file_credentials = credential_manager.get_assigned_file_credentials(agent_name, current_user.username)

response = await client.post(
    f"http://agent-{agent_name}:8000/api/credentials/update",
    json={
        "credentials": credentials,
        "mcp_config": mcp_config,
        "files": file_credentials  # New field
    }
)
```

### Agent-Server Handler (`docker/base-image/agent_server/routers/credentials.py:87-109`)

```python
class CredentialUpdateRequest(BaseModel):
    credentials: dict
    mcp_config: Optional[str] = None
    files: Optional[Dict[str, str]] = None  # New: {path: content}

@router.post("/api/credentials/update")
async def update_credentials(request: CredentialUpdateRequest):
    # ... existing .env and .mcp.json handling ...

    # Write file credentials
    if request.files:
        for file_path, content in request.files.items():
            target_path = Path("/home/developer") / file_path.lstrip("/")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content)
            target_path.chmod(0o600)  # Owner read/write only
```

### Example: Google Service Account

1. **Create credential** via UI:
   - Name: `GCP Service Account`
   - Service: `google`
   - Type: `File (JSON, etc.)`
   - File Path: `.config/gcloud/application_default_credentials.json`
   - File Content: `{"type": "service_account", "project_id": "...", ...}`

2. **Result**: File injected at `/home/developer/.config/gcloud/application_default_credentials.json`

3. **Agent can use**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/home/developer/.config/gcloud/application_default_credentials.json"
   gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS
   ```

---

## Flow 8: Agent Credential Assignment

> **Added 2025-12-30**: Credential injection is now assignment-based. No credentials are injected by default.

### Overview

Users must explicitly assign credentials to each agent. This provides fine-grained control over which credentials are available to which agents.

### Redis Data Structure

```
agent:{agent_name}:credentials -> SET of credential IDs
```

### Backend Methods (`src/backend/credentials.py:310-461`)

```python
def assign_credential(self, agent_name: str, cred_id: str, user_id: str) -> bool:
    """Assign a credential to an agent."""
    cred = self.get_credential(cred_id, user_id)
    if not cred:
        return False
    agent_creds_key = f"agent:{agent_name}:credentials"
    self.redis_client.sadd(agent_creds_key, cred_id)
    return True

def unassign_credential(self, agent_name: str, cred_id: str) -> bool:
    """Unassign a credential from an agent."""
    agent_creds_key = f"agent:{agent_name}:credentials"
    return self.redis_client.srem(agent_creds_key, cred_id) > 0

def get_assigned_credentials(self, agent_name: str, user_id: str) -> List[Credential]:
    """Get credentials assigned to an agent."""
    ...

def get_assigned_credential_values(self, agent_name: str, user_id: str) -> Dict[str, str]:
    """Get key-value pairs for assigned credentials (excludes file-type)."""
    ...

def get_assigned_file_credentials(self, agent_name: str, user_id: str) -> Dict[str, str]:
    """Get file credentials assigned to an agent. Returns {path: content}."""
    ...

def cleanup_agent_credentials(self, agent_name: str) -> int:
    """Remove all credential assignments when agent is deleted."""
    ...
```

### API Endpoints (`src/backend/routers/credentials.py:621-834`)

```python
@router.get("/agents/{agent_name}/credentials/assignments")
# Returns: {"assigned": [...], "available": [...]}

@router.post("/agents/{agent_name}/credentials/assign")
# Body: {"credential_id": "abc123"}

@router.delete("/agents/{agent_name}/credentials/assign/{cred_id}")

@router.post("/agents/{agent_name}/credentials/assign/bulk")
# Body: {"credential_ids": ["abc123", "def456"]}

@router.post("/agents/{agent_name}/credentials/apply")
# Pushes all assigned credentials to running agent
```

### Frontend UI (`src/frontend/src/views/AgentDetail.vue`)

The Credentials tab shows:
1. **Filter input** - search credentials by name or service
2. **Assigned Credentials** - credentials currently assigned to this agent (scrollable list)
3. **Available Credentials** - user's credentials not yet assigned (scrollable list)
4. **Quick Add** - paste KEY=VALUE to create, assign, and apply in one step

**UI Features**:
- Filter input at top filters both assigned and available lists
- Scrollable lists with `max-h-64 overflow-y-auto`
- Credential count badge on Credentials tab
- "+ Add" / "Remove" buttons for each credential
- "Apply to Agent" button to push assigned credentials to running agent

### Composable (`src/frontend/src/composables/useAgentCredentials.js:1-215`)

```javascript
// Returns
{
  assignedCredentials,      // Credentials assigned to this agent
  availableCredentials,     // User's credentials not assigned to this agent
  loading,
  applying,
  hasChanges,
  loadCredentials,          // Fetch assigned/available from API
  assignCredential,         // Assign a credential to agent
  unassignCredential,       // Remove assignment
  applyToAgent,             // Push all assigned to running agent
  quickAddCredentials,      // Create, assign, and apply in one step
}
```

### Store Actions (`src/frontend/src/stores/agents.js:242-274`)

```javascript
async getCredentialAssignments(name) {
  const response = await axios.get(`/api/agents/${name}/credentials/assignments`, ...)
  return response.data
}

async assignCredential(name, credentialId) {
  const response = await axios.post(`/api/agents/${name}/credentials/assign`,
    { credential_id: credentialId }, ...)
  return response.data
}

async unassignCredential(name, credentialId) {
  const response = await axios.delete(`/api/agents/${name}/credentials/assign/${credentialId}`, ...)
  return response.data
}

async applyCredentials(name) {
  const response = await axios.post(`/api/agents/${name}/credentials/apply`, {}, ...)
  return response.data
}
```

### Workflow

1. User creates credentials in the Credentials page
2. User goes to Agent Detail -> Credentials tab
3. User clicks "+ Add" on desired credentials
4. User clicks "Apply to Agent" to push to running agent
5. On agent restart, only assigned credentials are injected

---

## Side Effects

| Action | Audit Event |
|--------|-------------|
| Create credential | `credential_management:create` |
| Bulk import | `credential_management:bulk_import` |
| Hot reload | `credential_management:hot_reload_credentials` |
| Reload from Redis | `credential_management:reload_credentials` |
| Assign credential | `credential_management:assign_credential` |
| Unassign credential | `credential_management:unassign_credential` |
| Apply credentials | `credential_management:apply_credentials` |
| OAuth init | `oauth:init` |
| OAuth callback | `oauth:callback` |

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Agent not running (hot-reload) | 400 | "Agent is not running (status: {status}). Start the agent first." |
| No valid credentials in text | 400 | "No valid credentials found in the provided text" |
| OAuth state expired | 400 | "Invalid or expired OAuth state" |
| OAuth provider not configured | 500 | "OAuth not configured for {provider}. Set {PROVIDER}_CLIENT_ID environment variable." |
| Agent unreachable | 503 | "Failed to connect to agent: {error}" |
| Agent rejected update | varies | "Agent rejected credential update: {detail}" |

---

## Security Considerations

1. **Credential Isolation**: Each user can only access their own credentials via Redis `user:{user_id}:credentials` set
2. **No Secret Logging**: Actual credential values never logged, only credential names/IDs
3. **Redis Secrets**: Stored separately from metadata at `credentials:{id}:secret`
4. **Agent Internal API**: Only accessible via Docker internal network (`http://agent-{name}:8000`)
5. **OAuth State Tokens**: Cryptographic random with 10-minute TTL
6. **Input Validation**: Keys must match `^[A-Z][A-Z0-9_]*$` pattern
7. **Normalized Credentials**: OAuth tokens stored with both standard and MCP-compatible names
8. **File Permissions**: File-type credentials written with 600 permissions (owner read/write only)

---

## Testing

**Prerequisites**:
- [ ] Backend running at http://localhost:8000
- [ ] Frontend running at http://localhost:3000
- [ ] Redis running at redis://redis:6379
- [ ] Test agent created and running
- [ ] Logged in as test user

**Test Steps**:

### 1. Manual Credential Entry
**Action**:
- Navigate to http://localhost:3000/credentials
- Click "Add Credential"
- Enter name: "HEYGEN_API_KEY"
- Enter service: "heygen"
- Enter type: "api_key"
- Enter value: "test_key_123"
- Click "Save"

**Verify**:
- [ ] Credential appears in credential list
- [ ] Redis has `credentials:{id}:metadata` hash
- [ ] Redis has `credentials:{id}:secret` string
- [ ] Audit log shows `credential_management:create`

### 2. Bulk Import
**Action**:
- Paste into bulk import textarea:
```
HEYGEN_API_KEY=sk_test_heygen
TWITTER_API_KEY=twitter_123
OPENAI_API_KEY=sk-openai-456
```
- Click "Import Credentials"

**Verify**:
- [ ] All 3 credentials created
- [ ] Services auto-detected (heygen, twitter, openai)
- [ ] Types inferred (api_key, api_key, api_key)
- [ ] Audit log shows `credential_management:bulk_import` with count=3

### 3. Hot-Reload Credentials
**Action**:
- Navigate to agent detail page
- Click "Credentials" tab
- Use "Quick Add" section
- Paste:
```
HEYGEN_API_KEY=new_key_789
ANTHROPIC_API_KEY=sk-ant-test
```
- Click "Add & Apply"

**Expected**:
- Success message appears
- Agent's `.env` file updated
- Agent's `.mcp.json` file regenerated
- Credentials assigned to agent

**Verify**:
- [ ] Agent detail shows success toast
- [ ] Audit log shows `credential_management:hot_reload_credentials`
- [ ] Inside agent container: `cat ~/.env` shows new values
- [ ] Inside agent container: `cat ~/.mcp.json` has replaced placeholders

### 4. OAuth Flow (Google) - **UI REMOVED 2025-12-07**
> **Note**: OAuth provider buttons were removed from the Credentials page UI. OAuth flows are still available via backend API but require direct API calls.

**API-based Testing** (if needed):
```bash
# Initiate OAuth flow via API
curl -X POST http://localhost:8000/api/oauth/google/init \
  -H "Authorization: Bearer $TOKEN"
# Returns: {"auth_url": "https://accounts.google.com/...", "state": "..."}
```

**Expected** (via API):
- Redirect to Google OAuth consent screen
- After approval, redirect to callback
- Credential created with normalized fields

**Verify**:
- [ ] Credential named "Google OAuth - YYYY-MM-DD"
- [ ] Service: "google", Type: "oauth2"
- [ ] Has both `access_token` and `GOOGLE_ACCESS_TOKEN`
- [ ] Has both `refresh_token` and `GOOGLE_REFRESH_TOKEN`
- [ ] Audit log shows `oauth:init` and `oauth:callback`

### 5. Credential Assignment
**Action**:
- Navigate to agent detail page
- Click "Credentials" tab
- Type "google" in filter input
- Click "+ Add" on a Google credential
- Click "Apply to Agent"

**Expected**:
- Filter shows only google-related credentials
- Credential moves from "Available" to "Assigned" section
- Tab badge shows "1"
- Success notification appears

**Verify**:
- [ ] Filter filters both assigned and available lists
- [ ] Assigned count increases, available count decreases
- [ ] Redis has `agent:{name}:credentials` SET with credential ID
- [ ] GET `/api/agents/{name}/credentials/assignments` returns correct lists
- [ ] Agent receives credentials via internal API
- [ ] Audit log shows `credential_management:assign_credential`

### 6. Credential Status
**Action**: Navigate to agent detail, view credentials tab

**Expected**: Shows credential status from agent

**Verify**:
- [ ] GET `/api/agents/{name}/credentials/status` returns agent's credentials
- [ ] Shows which credentials are configured

---

**Last Updated**: 2026-01-23
**Status**: Verified - All file paths and line numbers confirmed accurate
**Issues**: None - credential system fully functional with Redis persistence and centralized settings service

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-01-23 | **Line number verification**: Updated all file paths and line numbers to match current codebase. `credentials.py` methods: `create_credential` at 98-136, `assign_credential` at 310-328, `get_assigned_credential_values` at 379-406, `get_assigned_file_credentials` at 408-445. Router endpoints: bulk import at 119-177, OAuth init at 181-208, OAuth callback at 211-296, hot-reload at 508-614, assignment endpoints at 621-834. Agent-server credentials router at 19-121. Store actions at 232-274. Composable at 1-215. |
| 2025-12-31 | **Settings Service refactor**: API key retrieval functions (`get_anthropic_api_key()`, `get_github_pat()`, `get_google_api_key()`) moved from `routers/settings.py` to `services/settings_service.py`. Router re-exports for backward compatibility. Agent creation now imports from `services.settings_service`. Documented settings retrieval hierarchy. |
| 2025-12-30 | **Bug fixes**: (1) File credential injection not working - agent containers needed base image rebuild. Added INFO logging to `get_assigned_file_credentials()`. (2) TypeError on mixed credential types - `get_agent_credentials()` returns mixed dict (string for bulk imports, dict for explicit assignments). Added `isinstance()` check in `crud.py`. Added Troubleshooting section. |
| 2025-12-30 | **Agent credential assignment with filter UI**: Major refactor - credentials now require explicit assignment to agents. No credentials injected by default. New Redis structure `agent:{name}:credentials` stores assignments. New API endpoints: `/assignments` (GET), `/assign` (POST/DELETE), `/apply` (POST). New UI in AgentDetail.vue Credentials tab with Assigned/Available lists, **filter input for search**, **scrollable lists** (max-h-64), credential count badge on tab, and Quick Add. Hot-reload now also assigns credentials. Cleanup on agent deletion. Fixed route ordering conflict (moved legacy MCP route to end of file). |
| 2025-12-30 | **File-type credentials**: Added support for injecting entire files (JSON, YAML, PEM, etc.) into agents at specified paths. New credential type "file" with file_path field. Files injected at agent creation and via hot-reload. Use cases: GCP service accounts, AWS credentials, SSL certificates. |
| 2025-12-28 | **Bug fix: Hot-reload now saves to Redis**. Previously, hot-reload only pushed credentials to the agent's .env file but did NOT persist them to Redis. Credentials were lost on agent restart. Now hot-reload uses `import_credential_with_conflict_resolution()` to save each credential to Redis before pushing to the agent. Response includes `saved_to_redis` array with status (created/reused/renamed). |
| 2025-12-19 | **Path/line number updates**: Updated all file references for modular architecture. Agent-server now at `docker/base-image/agent_server/routers/credentials.py`. Backend routers at `src/backend/routers/credentials.py`. Updated helpers to `src/backend/utils/helpers.py`. Added store action documentation. Verified all line numbers. |
| 2025-12-07 | **Credentials.vue cleanup**: Removed "Connect Services" OAuth provider section (Google, Slack, GitHub, Notion buttons). Removed unused code: `oauthProviders` ref, `fetchOAuthProviders()`, `startOAuth()`, `getProviderIcon()`. Updated empty state text. OAuth flows remain available via backend API. |

---

## Troubleshooting

### File Credentials Not Being Written

**Symptom**: `POST /api/agents/{name}/credentials/apply` returns success with `file_count: 1` but file doesn't exist in agent.

**Root Cause**: Agent container is running an outdated base image that doesn't have the file-handling code.

**Solution**:
```bash
# 1. Rebuild base image
./scripts/deploy/build-base-image.sh

# 2. Restart the agent (stop + start via UI or API)
# The new container will use the updated base image
```

**Verification**:
```bash
# Check if agent has file handling code
docker exec agent-{name} grep -A 5 "Write file-type" /app/agent_server/routers/credentials.py
```

### TypeError: string indices must be integers

**Symptom**: Error at `crud.py:331` when starting agent with credentials.

**Root Cause**: `get_agent_credentials()` returns a mixed dict:
- Explicitly assigned credentials -> dict values like `{'api_key': 'xxx'}`
- Bulk-imported credentials -> string values like `'sk-xxx'`

**Fix**: Applied in commit `6d0d559`. Update backend code and restart.

---

## Settings Service Architecture

> **Added 2025-12-31**: Centralized settings retrieval with database-first hierarchy.

### Overview

API key retrieval functions are now centralized in `src/backend/services/settings_service.py`. This breaks the circular dependency where services were importing from routers.

### Key Files

| File | Purpose |
|------|---------|
| `src/backend/services/settings_service.py:1-139` | **Primary** - SettingsService class and convenience functions |
| `src/backend/routers/settings.py:17-26` | Re-exports functions for backward compatibility |
| `src/backend/services/agent_service/crud.py:29` | Uses `get_anthropic_api_key()` from settings_service |
| `src/backend/db/settings.py:1-124` | Database operations for `system_settings` table |

### Settings Retrieval Hierarchy

The `SettingsService` class implements a three-tier fallback hierarchy:

```
1. Database setting (if exists) - system_settings table
       | (fallback if not found)
2. Environment variable
       | (fallback if not set)
3. Default value (if provided)
```

### API Key Functions (`src/backend/services/settings_service.py:64-83`)

```python
def get_anthropic_api_key(self) -> str:
    """Get Anthropic API key from settings, fallback to env var."""
    key = self.get_setting('anthropic_api_key')
    if key:
        return key
    return os.getenv('ANTHROPIC_API_KEY', '')

def get_github_pat(self) -> str:
    """Get GitHub PAT from settings, fallback to env var."""
    key = self.get_setting('github_pat')
    if key:
        return key
    return os.getenv('GITHUB_PAT', '')

def get_google_api_key(self) -> str:
    """Get Google API key from settings, fallback to env var."""
    key = self.get_setting('google_api_key')
    if key:
        return key
    return os.getenv('GOOGLE_API_KEY', '')
```

### Convenience Functions (`src/backend/services/settings_service.py:107-125`)

Module-level functions for backward compatibility:

```python
# Singleton instance
settings_service = SettingsService()

# Convenience functions
def get_anthropic_api_key() -> str:
    return settings_service.get_anthropic_api_key()

def get_github_pat() -> str:
    return settings_service.get_github_pat()

def get_google_api_key() -> str:
    return settings_service.get_google_api_key()
```

### Database Table (`system_settings`)

```sql
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

### Admin Configuration

API keys can be configured via:
1. **Settings UI**: Settings page -> API Keys section (stored in database)
2. **Environment variables**: `ANTHROPIC_API_KEY`, `GITHUB_PAT`, `GOOGLE_API_KEY` in `.env`

Database settings take precedence over environment variables, allowing runtime configuration without container restarts.

---

## Related Flows

- **Upstream**: Agent Creation (injects initial credentials from Redis)
- **Downstream**: Agent Chat (MCP servers use credentials for API calls)
- **Related**: OAuth Authentication (similar OAuth flow for user login)
- **Related**: Template Processing (generates .mcp.json with credential placeholders)
- **Related**: Settings Management (API keys stored in system_settings table)
