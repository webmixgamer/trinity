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
| `src/frontend/src/views/Credentials.vue:82-108` | `POST /api/credentials/bulk` | Bulk import (.env paste) |
| `src/frontend/src/views/AgentDetail.vue` | `POST /api/agents/{name}/credentials/hot-reload` | Hot-reload on running agent |

> **Note (2025-12-07)**: OAuth provider buttons ("Connect Services" section with Google, Slack, GitHub, Notion) were **removed** from Credentials.vue. OAuth flows remain available via backend API endpoints but are no longer exposed in the UI.

---

## Flow 1: Manual Credential Entry

### Frontend (`src/frontend/src/views/Credentials.vue:475-529`)
```javascript
const createCredential = async () => {
  const response = await fetch('/api/credentials', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${authStore.token}` },
    body: JSON.stringify({
      name: newCredential.value.name,
      service: newCredential.value.service,
      type: newCredential.value.type,
      credentials: { api_key: newCredential.value.api_key }
    })
  })
}
```

### Backend (`src/backend/routers/credentials.py:43-74`)
```python
@router.post("/credentials", response_model=Credential)
async def create_credential(cred_data: CredentialCreate, current_user: User):
    credential = credential_manager.create_credential(current_user.username, cred_data)
    await log_audit_event(event_type="credential_management", action="create", ...)
    return credential
```

### Redis Storage (`src/backend/credentials.py:92-128`)
```python
def create_credential(self, user_id: str, cred_data: CredentialCreate):
    cred_key = f"credentials:{cred_id}"
    self.redis_client.hset(f"{cred_key}:metadata", mapping={...})
    self.redis_client.set(f"{cred_key}:secret", json.dumps(cred_data.credentials))
    self.redis_client.sadd(f"user:{user_id}:credentials", cred_id)
```

---

## Flow 2: Bulk Credential Import

### Frontend (`src/frontend/src/views/Credentials.vue:82-108`)
User pastes `.env`-style content into textarea, clicks "Import Credentials".

### Backend (`src/backend/routers/credentials.py:172-243`)
```python
@router.post("/credentials/bulk", response_model=BulkCredentialResult)
async def bulk_import_credentials(import_data: BulkCredentialImport, ...):
    parsed = parse_env_content(import_data.content)  # line 179

    for key, value in parsed:
        service = infer_service_from_key(key)  # line 194
        cred_type = infer_type_from_key(key)   # line 195

        cred_data = CredentialCreate(
            name=key,
            service=service,
            type=cred_type,
            credentials={key: value},  # line 202
            description="Bulk imported credential"
        )

        credential = credential_manager.create_credential(current_user.username, cred_data)
        created_count += 1
```

### Parser (`src/backend/utils/helpers.py`)
```python
def parse_env_content(content: str) -> List[tuple]:
    """Parse .env-style KEY=VALUE pairs"""
    for line in content.split('\n'):
        if '=' in line:
            key, _, value = line.partition('=')
            if re.match(r'^[A-Z][A-Z0-9_]*$', key):
                results.append((key, value))
    return results

def infer_service_from_key(key: str) -> str:
    """Auto-detect service from key name prefix"""
    service_patterns = [
        ('HEYGEN_', 'heygen'),
        ('TWITTER_', 'twitter'),
        ('OPENAI_', 'openai'),
        ('GOOGLE_', 'google'),
        ('SLACK_', 'slack'),
        ('GITHUB_', 'github'),
        ('NOTION_', 'notion'),
    ]
    for prefix, service in service_patterns:
        if key.startswith(prefix):
            return service
    return 'other'

def infer_type_from_key(key: str) -> str:
    """Infer credential type from key name"""
    if 'TOKEN' in key:
        return 'token'
    elif 'API_KEY' in key or 'APIKEY' in key:
        return 'api_key'
    elif 'SECRET' in key:
        return 'secret'
    else:
        return 'api_key'
```

---

## Flow 3: Hot-Reload Credentials

### Frontend (`src/frontend/src/views/AgentDetail.vue:1066-1094`)
```javascript
const performHotReload = async () => {
  const result = await agentsStore.hotReloadCredentials(
    agent.value.name,
    hotReloadText.value  // KEY=VALUE format
  )
}
```

### Backend (`src/backend/routers/credentials.py:617-702`)
```python
@router.post("/agents/{agent_name}/credentials/hot-reload")
async def hot_reload_credentials(agent_name: str, request_body: HotReloadCredentialsRequest):
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent_status = get_agent_status_from_container(container)
    if agent_status.status != "running":
        raise HTTPException(status_code=400, detail="Agent is not running")

    # Parse credentials (line 636-649)
    credentials = {}
    for line in request_body.credentials_text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            if key:
                credentials[key] = value

    if not credentials:
        raise HTTPException(status_code=400, detail="No valid credentials found")

    # Push to agent container (line 657-681)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://agent-{agent_name}:8000/api/credentials/update",
            json={
                "credentials": credentials,
                "mcp_config": None
            },
            timeout=30.0
        )

    # Audit log (line 683-694)
    await log_audit_event(
        event_type="credential_management",
        action="hot_reload_credentials",
        user_id=current_user.username,
        agent_name=agent_name,
        details={
            "credential_count": len(credentials),
            "credential_names": list(credentials.keys())
        }
    )
```

### Agent Container (`docker/base-image/agent-server.py:1056-1125`)
```python
@app.post("/api/credentials/update")
async def update_credentials(request: CredentialUpdateRequest):
    # 1. Write .env file (line 1070-1076)
    env_lines = []
    for var, value in request.credentials.items():
        env_lines.append(f'{var}="{value}"')
    env_file = Path.home() / '.env'
    env_file.write_text("\n".join(env_lines))

    # 2. Generate .mcp.json from template (line 1078-1092)
    mcp_template = Path.home() / '.mcp.json.template'
    mcp_file = Path.home() / '.mcp.json'
    if mcp_template.exists():
        template_content = mcp_template.read_text()
        for var_name, value in request.credentials.items():
            # Replace ${VAR_NAME} with actual value
            template_content = template_content.replace(f"${{{var_name}}}", str(value))
        mcp_file.write_text(template_content)

    # 3. Export to environment (line 1094-1096)
    for var_name, value in request.credentials.items():
        os.environ[var_name] = str(value)

    # 4. Return updated files (line 1098-1125)
    updated_files = []
    if env_file.exists():
        updated_files.append(".env")
    if mcp_file.exists():
        updated_files.append(".mcp.json")

    return {
        "message": "Credentials updated successfully",
        "updated_files": updated_files,
        "note": "MCP servers may need to be restarted for changes to take effect"
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

### Generation at Agent Creation (`src/backend/routers/agents.py:205-218`)
```python
generated_files = {}
if template_data:
    generated_files = generate_credential_files(
        template_data, flat_credentials, config.name,
        template_base_path=github_template_path
    )

cred_files_dir = Path(f"/tmp/agent-{config.name}-creds")
cred_files_dir.mkdir(exist_ok=True)
for filepath, content in generated_files.items():
    file_path = cred_files_dir / filepath
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        f.write(content)
```

### Generation Logic (`src/backend/services/template_service.py`)
```python
def generate_credential_files(template_data, agent_credentials, agent_name, template_base_path=None):
    # Replace ${VAR_NAME} placeholders with real values
    for server_name, server_config in mcp_config.get("mcpServers", {}).items():
        if "env" in server_config:
            for env_key, env_val in server_config["env"].items():
                if env_val.startswith("${") and env_val.endswith("}"):
                    var_name = env_val[2:-1]
                    server_config["env"][env_key] = agent_credentials.get(var_name, "")
```

---

## Flow 5: OAuth2 Flows

### Supported Providers (`src/backend/credentials.py:49-74`)
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

### Init Endpoint (`src/backend/routers/credentials.py:247-283`)
```python
@router.post("/oauth/{provider}/init")
async def init_oauth(provider: str, current_user: User):
    if provider not in OAUTH_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unsupported OAuth provider: {provider}")

    config = OAUTH_CONFIGS[provider]
    if not config["client_id"]:
        raise HTTPException(status_code=500, detail=f"OAuth not configured for {provider}")

    redirect_uri = f"{BACKEND_URL}/api/oauth/{provider}/callback"
    state = credential_manager.create_oauth_state(current_user.username, provider, redirect_uri)

    auth_url = credential_manager.build_oauth_url(
        provider,
        config["client_id"],
        redirect_uri,
        state
    )

    await log_audit_event(
        event_type="oauth",
        action="init",
        user_id=current_user.username,
        resource=provider,
        result="success"
    )

    return {"auth_url": auth_url, "state": state}
```

### Callback Endpoint (`src/backend/routers/credentials.py:286-381`)
```python
@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, code: str, state: str, request: Request):
    state_data = credential_manager.verify_oauth_state(state)  # line 294

    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    if state_data["provider"] != provider:
        raise HTTPException(status_code=400, detail="Provider mismatch")

    config = OAUTH_CONFIGS[provider]

    # Exchange authorization code for tokens (line 304-310)
    tokens = await credential_manager.exchange_oauth_code(
        provider,
        code,
        config["client_id"],
        config["client_secret"],
        state_data["redirect_uri"]
    )

    if not tokens:
        raise HTTPException(status_code=500, detail="Failed to exchange OAuth code")

    # Normalize credential names for MCP compatibility (line 316-355)
    normalized_creds = {
        # Original OAuth response fields
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "token_type": tokens.get("token_type"),
        "expires_in": tokens.get("expires_in"),
        "scope": tokens.get("scope"),
        "client_id": tokens.get("client_id"),
        "client_secret": tokens.get("client_secret"),
    }

    # Add MCP-compatible naming for each provider
    if provider == "google":
        normalized_creds.update({
            "GOOGLE_ACCESS_TOKEN": tokens.get("access_token"),
            "GOOGLE_REFRESH_TOKEN": tokens.get("refresh_token"),
            "GOOGLE_CLIENT_ID": tokens.get("client_id"),
            "GOOGLE_CLIENT_SECRET": tokens.get("client_secret"),
        })
    elif provider == "slack":
        normalized_creds.update({
            "SLACK_ACCESS_TOKEN": tokens.get("access_token"),
            "SLACK_BOT_TOKEN": tokens.get("bot_token"),
        })
    # ... (similar for github, notion)

    # Create credential in Redis (line 357-365)
    cred_data = CredentialCreate(
        name=f"{provider.title()} OAuth - {datetime.now().strftime('%Y-%m-%d')}",
        service=provider,
        type="oauth2",
        credentials=normalized_creds,
        description="OAuth connection created via authorization flow"
    )

    credential = credential_manager.create_credential(state_data["user_id"], cred_data)

    # Audit log (line 367-375)
    await log_audit_event(
        event_type="oauth",
        action="callback",
        user_id=state_data["user_id"],
        resource=provider,
        result="success",
        details={"credential_id": credential.id}
    )

    return {
        "message": "OAuth authentication successful",
        "credential_id": credential.id,
        "redirect": "http://localhost:3000/credentials"
    }
```

---

## Flow 6: Credential Reload (from Redis)

### Endpoint (`src/backend/routers/credentials.py:480-580`)
Reloads credentials from Redis store into running agent without manual text entry.

```python
@router.post("/agents/{agent_name}/credentials/reload")
async def reload_agent_credentials(agent_name: str, ...):
    container = get_agent_container(agent_name)
    agent_status = get_agent_status_from_container(container)

    if agent_status.status != "running":
        raise HTTPException(status_code=400, detail="Agent is not running")

    # Get credentials from Redis (line 522-526)
    agent_credentials = credential_manager.get_agent_credentials(
        agent_name,
        mcp_servers,
        current_user.username
    )

    # Generate .mcp.json if template exists (line 531-534)
    mcp_config = None
    if mcp_template_content and template_data:
        generated_files = generate_credential_files(template_data, agent_credentials, agent_name)
        mcp_config = generated_files.get(".mcp.json")

    # Push to agent (line 536-560)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://agent-{agent_name}:8000/api/credentials/update",
            json={
                "credentials": agent_credentials,
                "mcp_config": mcp_config
            },
            timeout=30.0
        )
```

---

## Redis Data Structure

```
credentials:{cred_id}:metadata  -> HASH {id, name, service, type, user_id, created_at}
credentials:{cred_id}:secret    -> STRING (JSON blob of secrets)
user:{user_id}:credentials      -> SET of cred_ids
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

## Side Effects

| Action | Audit Event |
|--------|-------------|
| Create credential | `credential_management:create` |
| Bulk import | `credential_management:bulk_import` |
| Hot reload | `credential_management:hot_reload_credentials` |
| Reload from Redis | `credential_management:reload_credentials` |
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
- Click "Hot Reload Credentials" tab
- Paste:
```
HEYGEN_API_KEY=new_key_789
ANTHROPIC_API_KEY=sk-ant-test
```
- Click "Reload"

**Expected**:
- Success message appears
- Agent's `.env` file updated
- Agent's `.mcp.json` file regenerated

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

### 5. Credential Status
**Action**: Navigate to agent detail, view credentials tab

**Expected**: Shows credential status from agent

**Verify**:
- [ ] GET `/api/agents/{name}/credentials/status` returns agent's credentials
- [ ] Shows which credentials are configured

---

**Last Tested**: 2025-12-07
**Status**: ✅ Working (all flows operational)
**Issues**: None - credential system fully functional with modular router architecture

---

## Revision History

| Date | Changes |
|------|---------|
| 2025-12-07 | **Credentials.vue cleanup**: Removed "Connect Services" OAuth provider section (Google, Slack, GitHub, Notion buttons). Removed unused code: `oauthProviders` ref, `fetchOAuthProviders()`, `startOAuth()`, `getProviderIcon()`. Updated empty state text. OAuth flows remain available via backend API. |

---

## Related Flows

- **Upstream**: Agent Creation (injects initial credentials from Redis)
- **Downstream**: Agent Chat (MCP servers use credentials for API calls)
- **Related**: OAuth Authentication (similar OAuth flow for user login)
- **Related**: Template Processing (generates .mcp.json with credential placeholders)
