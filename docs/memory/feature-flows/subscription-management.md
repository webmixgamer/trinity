# Feature: Subscription Management (SUB-001)

## Overview

Centralized management of Claude Max/Pro subscription credentials. Enables registering OAuth credentials once and assigning them to multiple agents, with automatic injection on agent start and hot-injection to running agents.

## User Story

As a Trinity platform admin, I want to register my Claude Max/Pro subscription credentials centrally so that I can assign them to multiple agents without re-entering credentials, reducing cost by using subscription instead of API billing.

---

## Key Concepts

### Authentication Hierarchy

When an agent authenticates with Claude Code, credentials are checked in this order:

1. **Subscription OAuth** (`~/.claude/.credentials.json`) - Claude Max/Pro OAuth tokens
2. **API Key** (`ANTHROPIC_API_KEY` env var) - Platform API key

Subscription takes precedence if both exist. This allows cost-effective operation using Claude Max/Pro subscriptions instead of per-token API billing.

### Data Model

```
subscription_credentials          agent_ownership
+------------------------+        +------------------------+
| id (PK, UUID)          |        | agent_name (PK)        |
| name (UNIQUE)          |        | owner_id (FK)          |
| encrypted_credentials  |<-------| subscription_id (FK)   |
| subscription_type      |        | ...                    |
| rate_limit_tier        |        +------------------------+
| owner_id (FK users)    |
| created_at, updated_at |
+------------------------+
```

### Credential Flow

```
User's Machine                  Trinity Backend                    Agent Container
+----------------+              +-------------------+               +------------------+
| ~/.claude/     |  register    | subscription_     |   inject      | ~/.claude/       |
| .credentials   | -----------> | credentials       | ------------> | .credentials     |
| .json          |  (encrypt)   | (encrypted AES)   |  (decrypt)    | .json            |
+----------------+              +-------------------+               +------------------+
```

---

## Entry Points

| UI Location | API Endpoint | Purpose |
|-------------|--------------|---------|
| **Settings Page: Claude Subscriptions** | `GET /api/subscriptions` | List subscriptions (Settings UI) |
| **Settings Page: Add Subscription** | `POST /api/subscriptions` | Register via file upload |
| **Settings Page: Delete Button** | `DELETE /api/subscriptions/{id}` | Delete with cascade confirmation |
| MCP Tool: `register_subscription` | `POST /api/subscriptions` | Register new subscription |
| MCP Tool: `list_subscriptions` | `GET /api/subscriptions` | List all subscriptions with agents |
| MCP Tool: `assign_subscription` | `PUT /api/subscriptions/agents/{agent_name}` | Assign subscription to agent |
| MCP Tool: `clear_agent_subscription` | `DELETE /api/subscriptions/agents/{agent_name}` | Clear subscription from agent |
| MCP Tool: `get_agent_auth` | `GET /api/subscriptions/agents/{agent_name}/auth` | Get agent auth status |
| MCP Tool: `delete_subscription` | `DELETE /api/subscriptions/{subscription_id}` | Delete subscription |
| Fleet Dashboard | `GET /api/ops/auth-report` | Fleet-wide auth status report |

---

## Frontend UI (Settings Page)

### Overview

The Settings page (`/settings`) includes a "Claude Subscriptions" section for managing subscription credentials through a web UI. This provides an alternative to MCP tools for subscription management.

### Location

- **File**: `src/frontend/src/views/Settings.vue`
- **Template**: Lines 223-435 (Claude Subscriptions section)
- **State**: Lines 872-883
- **Methods**: Lines 1268-1387

### UI Components

#### 1. Add Subscription Form (`Settings.vue:234-329`)

Form fields:
- **Name** (`v-model="newSubscription.name"`) - Unique identifier (e.g., "eugene-max")
- **Type** (`v-model="newSubscription.type"`) - Dropdown: Max / Pro / Unknown
- **Credentials File Upload** - Drag-and-drop or click-to-browse for `.credentials.json`

```html
<input
  type="file"
  accept=".json,application/json"
  @change="handleCredentialFileUpload"
  ref="credentialFileInput"
/>
```

Buttons:
- **Clear** - Reset form (visible when form has data)
- **Register Subscription** - Submit (disabled until name + credentials provided)

#### 2. Subscriptions Table (`Settings.vue:331-431`)

Columns:
| Column | Data |
|--------|------|
| Name | Subscription name with expand chevron |
| Type | Badge: purple (Max) or blue (Pro) |
| Agents | Count badge: "N agent(s)" |
| Created | Formatted date |
| Actions | Delete button |

Features:
- **Loading spinner** when `loadingSubscriptions` is true
- **Empty state** when no subscriptions registered
- **Expandable rows** showing owner, rate limit tier, assigned agents
- **Delete confirmation** with cascade warning (agent count)

#### 3. Expanded Details Row (`Settings.vue:399-427`)

Shows when row is clicked (`expandedSubscriptions.has(sub.id)`):
- Owner email
- Rate limit tier (if set)
- Assigned agents list (badges with agent icons)
- Hint about `assign_subscription` MCP tool if no agents assigned

### State Variables (`Settings.vue:872-883`)

```javascript
const subscriptions = ref([])              // List of SubscriptionWithAgents
const loadingSubscriptions = ref(false)    // Loading state
const addingSubscription = ref(false)      // Adding in progress
const deletingSubscription = ref(null)     // ID of subscription being deleted
const expandedSubscriptions = ref(new Set()) // Set of expanded row IDs
const credentialFileInput = ref(null)      // File input ref for clearing
const newSubscription = ref({
  name: '',
  type: 'max',
  credentials: null                        // Raw JSON string
})
```

### Methods

#### `loadSubscriptions()` (`Settings.vue:1269-1285`)

Fetches all subscriptions on page load.

```javascript
async function loadSubscriptions() {
  loadingSubscriptions.value = true
  try {
    const response = await axios.get('/api/subscriptions', {
      headers: authStore.authHeader
    })
    subscriptions.value = response.data || []
  } catch (e) {
    // 403 for non-admin is expected - silently hide section
    if (e.response?.status !== 403) {
      error.value = e.response?.data?.detail || 'Failed to load subscriptions'
    }
  } finally {
    loadingSubscriptions.value = false
  }
}
```

#### `handleCredentialFileUpload(event)` (`Settings.vue:1287-1306`)

Handles file selection and validates JSON.

```javascript
function handleCredentialFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      JSON.parse(e.target.result)  // Validate JSON
      newSubscription.value.credentials = e.target.result
    } catch (parseError) {
      error.value = 'Invalid JSON file. Please upload a valid .credentials.json file.'
      newSubscription.value.credentials = null
    }
  }
  reader.readAsText(file)
}
```

#### `clearNewSubscription()` (`Settings.vue:1308-1317`)

Resets the add form.

```javascript
function clearNewSubscription() {
  newSubscription.value = { name: '', type: 'max', credentials: null }
  if (credentialFileInput.value) {
    credentialFileInput.value.value = ''  // Clear file input
  }
}
```

#### `addSubscription()` (`Settings.vue:1319-1347`)

Registers a new subscription via API.

```javascript
async function addSubscription() {
  if (!newSubscription.value.name || !newSubscription.value.credentials) return

  addingSubscription.value = true
  try {
    await axios.post('/api/subscriptions', {
      name: newSubscription.value.name,
      credentials_json: newSubscription.value.credentials,
      subscription_type: newSubscription.value.type || null
    }, { headers: authStore.authHeader })

    clearNewSubscription()
    await loadSubscriptions()
    // Show success toast
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to register subscription'
  } finally {
    addingSubscription.value = false
  }
}
```

#### `deleteSubscription(subscription)` (`Settings.vue:1349-1377`)

Deletes subscription with cascade confirmation.

```javascript
async function deleteSubscription(subscription) {
  if (!confirm(`Delete subscription "${subscription.name}"?\n\nThis will clear the subscription from all ${subscription.agent_count || 0} assigned agent(s).`)) {
    return
  }

  deletingSubscription.value = subscription.id
  try {
    await axios.delete(`/api/subscriptions/${subscription.id}`, {
      headers: authStore.authHeader
    })
    expandedSubscriptions.value.delete(subscription.id)
    await loadSubscriptions()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to delete subscription'
  } finally {
    deletingSubscription.value = null
  }
}
```

#### `toggleSubscriptionDetails(subscriptionId)` (`Settings.vue:1379-1387`)

Toggles row expansion.

```javascript
function toggleSubscriptionDetails(subscriptionId) {
  if (expandedSubscriptions.value.has(subscriptionId)) {
    expandedSubscriptions.value.delete(subscriptionId)
  } else {
    expandedSubscriptions.value.add(subscriptionId)
  }
  expandedSubscriptions.value = new Set(expandedSubscriptions.value)  // Force reactivity
}
```

### Data Flow

```
User Action                Frontend                      Backend
    |                         |                             |
    | Upload .credentials.json|                             |
    |------------------------>|                             |
    |                         | FileReader.readAsText()     |
    |                         | JSON.parse() validate       |
    |                         |                             |
    | Click "Register"        |                             |
    |------------------------>|                             |
    |                         | POST /api/subscriptions     |
    |                         |----------------------------->|
    |                         |                             | Validate JSON
    |                         |                             | Encrypt (AES-256-GCM)
    |                         |                             | Insert to DB
    |                         |<-----------------------------|
    |                         | loadSubscriptions()         |
    |                         | GET /api/subscriptions      |
    |                         |----------------------------->|
    |                         |<-----------------------------|
    | See new subscription    |                             |
    |<------------------------|                             |
```

---

## Flow 1: Register Subscription

### Overview

Admin registers Claude Max/Pro OAuth credentials from their local machine. Credentials are encrypted using AES-256-GCM and stored in the database.

### Sequence Diagram

```
Admin             MCP/Claude Code          Backend                     Database
  |                    |                      |                            |
  | cat ~/.claude/     |                      |                            |
  | .credentials.json  |                      |                            |
  |-------pbcopy------>|                      |                            |
  |                    |                      |                            |
  | register_          |                      |                            |
  | subscription       |                      |                            |
  |------------------->|                      |                            |
  |                    | POST /api/           |                            |
  |                    | subscriptions        |                            |
  |                    |--------------------->|                            |
  |                    |                      | Validate JSON              |
  |                    |                      | Encrypt (AES-256-GCM)      |
  |                    |                      | Upsert by name             |
  |                    |                      |--------------------------->|
  |                    |                      |<---------------------------|
  |                    |<---------------------|                            |
  |<-------------------|                      |                            |
  | "Subscription      |                      |                            |
  |  registered"       |                      |                            |
```

### MCP Tool (`src/mcp-server/src/tools/subscriptions.ts:42-85`)

```typescript
registerSubscription: {
  name: "register_subscription",
  description: "Register a Claude Max/Pro subscription credential...",
  parameters: z.object({
    name: z.string().describe("Unique name for the subscription (e.g., 'eugene-max')"),
    credentials_json: z.string().describe("Raw JSON from ~/.claude/.credentials.json"),
    subscription_type: z.string().optional().describe("Type: 'max' or 'pro'"),
    rate_limit_tier: z.string().optional().describe("Rate limit tier if known"),
  }),
  execute: async (params, context) => {
    const apiClient = getClient(context?.session);
    const result = await apiClient.registerSubscription(
      params.name,
      params.credentials_json,
      params.subscription_type,
      params.rate_limit_tier
    );
    return JSON.stringify({ success: true, subscription: result }, null, 2);
  },
}
```

### MCP Client (`src/mcp-server/src/client.ts:830-852`)

```typescript
async registerSubscription(
  name: string,
  credentialsJson: string,
  subscriptionType?: string,
  rateLimitTier?: string
): Promise<{id: string; name: string; ...}> {
  return this.request(
    "POST",
    "/api/subscriptions",
    {
      name,
      credentials_json: credentialsJson,
      subscription_type: subscriptionType,
      rate_limit_tier: rateLimitTier,
    }
  );
}
```

### Backend Endpoint (`src/backend/routers/subscriptions.py:40-89`)

```python
@router.post("", response_model=SubscriptionCredential)
async def register_subscription(
    request: SubscriptionCredentialCreate,
    current_user: User = Depends(get_current_user)
):
    """Register a new subscription credential. Admin-only."""
    require_admin(current_user)

    # Validate JSON
    try:
        json.loads(request.credentials_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="credentials_json must be valid JSON")

    user = db.get_user_by_username(current_user.username)
    subscription = db.create_subscription(
        name=request.name,
        credentials_json=request.credentials_json,
        owner_id=user["id"],
        subscription_type=request.subscription_type,
        rate_limit_tier=request.rate_limit_tier,
    )

    logger.info(f"Registered subscription '{request.name}' by {current_user.username}")
    return subscription
```

### Database Operations (`src/backend/db/subscriptions.py:62-134`)

```python
def create_subscription(
    self,
    name: str,
    credentials_json: str,
    owner_id: int,
    subscription_type: Optional[str] = None,
    rate_limit_tier: Optional[str] = None,
) -> SubscriptionCredential:
    """Create or update (upsert by name) a subscription credential."""

    # Encrypt the credentials using AES-256-GCM
    encryption_service = self._get_encryption_service()
    encrypted = encryption_service.encrypt({".credentials.json": credentials_json})

    # Check for existing subscription with same name
    cursor.execute("SELECT id FROM subscription_credentials WHERE name = ?", (name,))
    existing = cursor.fetchone()

    if existing:
        # Update existing
        cursor.execute("""
            UPDATE subscription_credentials
            SET encrypted_credentials = ?, subscription_type = ?, ...
            WHERE id = ?
        """, (encrypted, subscription_type, ..., existing["id"]))
    else:
        # Insert new
        subscription_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO subscription_credentials
            (id, name, encrypted_credentials, ...) VALUES (?, ?, ?, ...)
        """, (subscription_id, name, encrypted, ...))
```

### Encryption (`src/backend/services/credential_encryption.py`)

Credentials are encrypted using the same AES-256-GCM encryption service as other credentials:

- Key derived from `CREDENTIAL_ENCRYPTION_KEY` env var or JWT secret
- 12-byte random nonce per encryption
- Ciphertext + nonce stored as JSON

---

## Flow 2: Assign Subscription to Agent

### Overview

Admin assigns a registered subscription to an agent. If the agent is running, credentials are immediately injected (hot-injection).

### Sequence Diagram

```
Admin            MCP/Claude Code        Backend                   Agent
  |                   |                    |                        |
  | assign_           |                    |                        |
  | subscription      |                    |                        |
  |------------------>|                    |                        |
  |                   | PUT /api/sub/      |                        |
  |                   | agents/{name}      |                        |
  |                   | ?sub_name=xxx      |                        |
  |                   |------------------>|                        |
  |                   |                    | Check access (owner)   |
  |                   |                    | Get subscription ID    |
  |                   |                    | Update agent_ownership |
  |                   |                    |                        |
  |                   |                    | If agent running:      |
  |                   |                    | inject_subscription()  |
  |                   |                    |----------------------->|
  |                   |                    | POST /api/credentials/ |
  |                   |                    | inject                 |
  |                   |                    |                        |
  |                   |                    | Write to ~/.claude/    |
  |                   |                    | .credentials.json      |
  |                   |                    |<-----------------------|
  |                   |<-------------------|                        |
  |<------------------|                    |                        |
  | "Assigned +       |                    |                        |
  |  injected"        |                    |                        |
```

### Backend Endpoint (`src/backend/routers/subscriptions.py:180-227`)

```python
@router.put("/agents/{agent_name}")
async def assign_subscription_to_agent(
    agent_name: str,
    subscription_name: str = Query(..., description="Name of subscription to assign"),
    current_user: User = Depends(get_current_user)
):
    """Assign a subscription to an agent. Owner access required."""

    # Authorization check
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied to this agent")

    # Get subscription by name
    subscription = db.get_subscription_by_name(subscription_name)
    if not subscription:
        raise HTTPException(status_code=404, detail=f"Subscription '{subscription_name}' not found")

    # Update database
    db.assign_subscription_to_agent(agent_name, subscription.id)

    # Hot-inject if agent is running
    injection_result = None
    try:
        from services.subscription_service import inject_subscription_to_agent
        injection_result = await inject_subscription_to_agent(agent_name, subscription.id)
    except Exception as e:
        logger.warning(f"Could not inject subscription to running agent: {e}")

    return {
        "success": True,
        "message": f"Subscription '{subscription_name}' assigned to agent '{agent_name}'",
        "injection_result": injection_result
    }
```

### Subscription Service (`src/backend/services/subscription_service.py:24-111`)

```python
async def inject_subscription_to_agent(
    agent_name: str,
    subscription_id: str,
    max_retries: int = 3,
    retry_delay: float = 2.0
) -> dict:
    """Inject subscription credentials into a running agent."""

    # Get decrypted credentials
    credentials_json = db.get_subscription_credentials(subscription_id)
    if not credentials_json:
        return {"status": "failed", "error": "Subscription credentials not found"}

    # Check if agent is running
    container = get_agent_container(agent_name)
    if not container or get_agent_status_from_container(container).status != "running":
        return {"status": "skipped", "reason": "agent_not_running"}

    # Inject via agent HTTP API with retries
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://agent-{agent_name}:8000/api/credentials/inject",
                    json={
                        "files": {
                            ".claude/.credentials.json": credentials_json
                        }
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    return {"status": "success", "files_written": [".claude/.credentials.json"]}
        except httpx.RequestError as e:
            logger.warning(f"Injection attempt {attempt + 1} failed: {e}")

        await asyncio.sleep(retry_delay)

    return {"status": "failed", "error": last_error}
```

---

## Flow 3: Agent Start with Subscription Injection

### Overview

When an agent starts, the lifecycle service checks for an assigned subscription and injects credentials automatically.

### Sequence Diagram

```
API Request        lifecycle.py                subscription_service.py        Agent
     |                  |                              |                         |
     | start_agent()    |                              |                         |
     |----------------->|                              |                         |
     |                  | container.start()            |                         |
     |                  |----------------------------->|                         |
     |                  |                              |                         |
     |                  | inject_trinity_meta_prompt() |                         |
     |                  |                              |                         |
     |                  | inject_assigned_credentials()|                         |
     |                  |                              |                         |
     |                  | inject_subscription_on_start |                         |
     |                  |---------------------------->|                         |
     |                  |                              | db.get_agent_sub_id()   |
     |                  |                              |                         |
     |                  |                              | If subscription_id:     |
     |                  |                              | inject_subscription()   |
     |                  |                              |------------------------>|
     |                  |                              | POST /api/credentials/  |
     |                  |                              | inject                  |
     |                  |                              |<------------------------|
     |                  |<-----------------------------|                         |
     |<-----------------|                              |                         |
```

### Lifecycle Integration (`src/backend/services/agent_service/lifecycle.py:239-243`)

```python
async def start_agent_internal(agent_name: str) -> dict:
    container = get_agent_container(agent_name)
    # ... recreation check, container.start() ...

    # 1. Inject Trinity meta-prompt
    trinity_result = await inject_trinity_meta_prompt(agent_name)

    # 2. Inject credentials from .credentials.enc (CRED-002)
    credentials_result = await inject_assigned_credentials(agent_name)

    # 3. Inject subscription credentials if assigned (SUB-001)
    from services.subscription_service import inject_subscription_on_start
    subscription_result = await inject_subscription_on_start(agent_name)

    # 4. Inject assigned skills
    skills_result = await inject_assigned_skills(agent_name)

    return {
        "message": f"Agent {agent_name} started",
        "subscription_injection": subscription_result.get("status", "unknown"),
        "subscription_result": subscription_result,
        # ... other injection results ...
    }
```

### Startup Injection (`src/backend/services/subscription_service.py:114-149`)

```python
async def inject_subscription_on_start(agent_name: str) -> dict:
    """Inject subscription credentials on agent startup if assigned."""

    # Check if agent has a subscription assigned
    subscription_id = db.get_agent_subscription_id(agent_name)
    if not subscription_id:
        return {"status": "skipped", "reason": "no_subscription_assigned"}

    subscription = db.get_subscription(subscription_id)
    if not subscription:
        return {"status": "failed", "error": "assigned_subscription_not_found"}

    logger.info(f"Injecting subscription '{subscription.name}' into agent {agent_name} on startup")

    return await inject_subscription_to_agent(agent_name, subscription_id)
```

---

## Flow 4: Auth Status Detection

### Overview

Determines how an agent is authenticated (subscription, API key, or not configured) by checking database assignments and optionally verifying with the running agent.

### Backend Endpoint (`src/backend/routers/subscriptions.py:262-283`)

```python
@router.get("/agents/{agent_name}/auth", response_model=AgentAuthStatus)
async def get_agent_auth_status(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get the authentication status for an agent."""

    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied to this agent")

    from services.subscription_service import get_agent_auth_mode
    return await get_agent_auth_mode(agent_name)
```

### Auth Mode Detection (`src/backend/services/subscription_service.py:152-218`)

```python
async def get_agent_auth_mode(agent_name: str) -> AgentAuthStatus:
    """Detect the authentication mode for an agent."""

    # Check for subscription assignment
    subscription = db.get_agent_subscription(agent_name)
    has_subscription = subscription is not None

    # Check for platform API key setting
    has_api_key = db.get_use_platform_api_key(agent_name) or False

    # Determine auth mode (subscription takes precedence)
    if has_subscription:
        auth_mode = "subscription"
    elif has_api_key:
        auth_mode = "api_key"
    else:
        auth_mode = "not_configured"

    # For running agents, verify actual credential presence
    container = get_agent_container(agent_name)
    if container and get_agent_status_from_container(container).status == "running":
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://agent-{agent_name}:8000/api/credentials/status",
                    timeout=10.0
                )
                # Verify .credentials.json exists if subscription mode
        except Exception:
            pass  # Continue with DB-based status

    return AgentAuthStatus(
        agent_name=agent_name,
        auth_mode=auth_mode,
        subscription_name=subscription.name if subscription else None,
        subscription_id=subscription.id if subscription else None,
        has_api_key=has_api_key,
    )
```

---

## Flow 5: Fleet Auth Report

### Overview

Admin views fleet-wide authentication status report showing how many agents use each authentication method.

### Backend Endpoint (`src/backend/routers/ops.py:933-1010`)

```python
@router.get("/auth-report")
async def get_auth_report(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get authentication status report for all agents."""
    agents = list_all_agents_fast()

    subscription_agents = []
    api_key_agents = []
    not_configured_agents = []

    for agent in agents:
        # Skip system agent
        owner = db.get_agent_owner(agent.name)
        if owner and owner.get("is_system"):
            continue

        subscription = db.get_agent_subscription(agent.name)
        has_api_key = db.get_use_platform_api_key(agent.name) or False

        agent_info = {
            "name": agent.name,
            "status": agent.status,
            "type": agent.type,
        }

        if subscription:
            agent_info["subscription_name"] = subscription.name
            subscription_agents.append(agent_info)
        elif has_api_key:
            api_key_agents.append(agent_info)
        else:
            not_configured_agents.append(agent_info)

    return {
        "summary": {
            "using_subscription": len(subscription_agents),
            "using_api_key": len(api_key_agents),
            "not_configured": len(not_configured_agents),
        },
        "by_auth_mode": {...},
        "subscriptions": [...],  # Subscription usage summary
    }
```

---

## Database Schema

### Table: subscription_credentials (`src/backend/database.py:383-404`)

```sql
CREATE TABLE IF NOT EXISTS subscription_credentials (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    encrypted_credentials TEXT NOT NULL,  -- AES-256-GCM encrypted JSON
    subscription_type TEXT,                -- "max", "pro", etc.
    rate_limit_tier TEXT,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_name ON subscription_credentials(name);
CREATE INDEX IF NOT EXISTS idx_subscriptions_owner ON subscription_credentials(owner_id);
```

### Column: agent_ownership.subscription_id (`src/backend/database.py:407-419`)

```sql
ALTER TABLE agent_ownership ADD COLUMN subscription_id TEXT REFERENCES subscription_credentials(id);
```

---

## Pydantic Models (`src/backend/db_models.py:616-649`)

```python
class SubscriptionCredentialCreate(BaseModel):
    """Request model for registering a subscription."""
    name: str                              # Unique name (e.g., "eugene-max")
    credentials_json: str                  # Raw JSON from ~/.claude/.credentials.json
    subscription_type: Optional[str] = None  # "max", "pro"
    rate_limit_tier: Optional[str] = None

class SubscriptionCredential(BaseModel):
    """A registered Claude subscription credential."""
    id: str
    name: str
    subscription_type: Optional[str] = None
    rate_limit_tier: Optional[str] = None
    owner_id: int
    owner_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    agent_count: int = 0

class SubscriptionWithAgents(SubscriptionCredential):
    """Subscription with list of assigned agents."""
    agents: List[str] = []

class AgentAuthStatus(BaseModel):
    """Auth status for an agent."""
    agent_name: str
    auth_mode: str  # "subscription", "api_key", "not_configured"
    subscription_name: Optional[str] = None
    subscription_id: Optional[str] = None
    has_api_key: bool = False
```

---

## TypeScript Types (`src/mcp-server/src/types.ts:204-228`)

```typescript
export interface Subscription {
  id: string;
  name: string;
  subscription_type?: string;
  rate_limit_tier?: string;
  owner_id: number;
  owner_email?: string;
  created_at: string;
  updated_at: string;
  agent_count: number;
}

export interface SubscriptionWithAgents extends Subscription {
  agents: string[];
}

export interface AgentAuthStatus {
  agent_name: string;
  auth_mode: "subscription" | "api_key" | "not_configured";
  subscription_name?: string;
  subscription_id?: string;
  has_api_key: boolean;
}
```

---

## MCP Tools Summary

All 6 subscription tools defined in `src/mcp-server/src/tools/subscriptions.ts`:

| Tool | Description | Parameters | Access |
|------|-------------|------------|--------|
| `register_subscription` | Register Claude Max/Pro credentials | `name`, `credentials_json`, `subscription_type?`, `rate_limit_tier?` | Admin |
| `list_subscriptions` | List all subscriptions with assigned agents | (none) | Admin |
| `assign_subscription` | Assign subscription to agent (hot-injects if running) | `agent_name`, `subscription_name` | Owner |
| `clear_agent_subscription` | Clear subscription from agent | `agent_name` | Owner |
| `get_agent_auth` | Get auth status for an agent | `agent_name` | Owner |
| `delete_subscription` | Delete subscription (cascades to clear agent assignments) | `subscription_name` | Admin |

Tools registered in `src/mcp-server/src/server.ts`.

---

## Security Considerations

1. **Encryption at Rest**: Credentials encrypted with AES-256-GCM before database storage
2. **Admin-Only Registration**: Only admins can register new subscriptions
3. **Owner Access for Assignment**: Users can only assign subscriptions to agents they own
4. **No Credential Exposure**: API never returns decrypted credentials - only metadata
5. **Audit Logging**: Subscription operations logged via structured logging
6. **Cascade Delete**: Deleting subscription clears all agent assignments

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Not admin (register/delete) | 403 | "Admin access required" |
| Not owner (assign) | 403 | "Access denied to this agent" |
| Invalid JSON | 400 | "credentials_json must be valid JSON" |
| Subscription not found | 404 | "Subscription '{name}' not found" |
| Agent not found | 400 | "Agent {name} not found in ownership table" |

---

## Testing

### Prerequisites
- Trinity platform running
- Admin user logged in
- At least one agent created
- Claude Max/Pro subscription with valid `~/.claude/.credentials.json`

---

### UI Testing (Settings Page)

#### Test: View Subscriptions List
1. Navigate to Settings page (`/settings`)
2. Scroll to "Claude Subscriptions" section
3. Verify: Table shows loading spinner briefly, then list (or empty state)
4. Verify: Non-admin users see empty section (403 handled gracefully)

#### Test: Register via File Upload
1. Navigate to Settings page
2. In "Add Subscription" form:
   - Enter name: "test-subscription"
   - Select type: "Max"
   - Click file upload area or drag `.credentials.json` file
3. Verify: Upload area shows green checkmark and "Credentials loaded"
4. Click "Register Subscription"
5. Verify: Loading spinner on button
6. Verify: New subscription appears in table with correct name, type, "0 agents"
7. Verify: Form is cleared after success

#### Test: Invalid JSON File
1. Create a file with invalid JSON content
2. Attempt to upload it
3. Verify: Error message "Invalid JSON file. Please upload a valid .credentials.json file."
4. Verify: Upload area does NOT show green checkmark

#### Test: Expand Subscription Row
1. Click on a subscription row in the table
2. Verify: Chevron rotates 90 degrees
3. Verify: Details row expands showing owner, rate limit tier (if set), assigned agents
4. Click row again
5. Verify: Row collapses

#### Test: Delete Subscription
1. Click "Delete" button on a subscription row
2. Verify: Confirmation dialog shows subscription name and agent count
3. Click OK
4. Verify: Button shows "Deleting..."
5. Verify: Subscription removed from list after delete completes
6. Verify: Success indicator shown

#### Test: Delete Cancellation
1. Click "Delete" button on a subscription
2. Click Cancel on confirmation dialog
3. Verify: Subscription remains in list, no changes

#### Test: Clear Form
1. Enter a name in the form
2. Upload a credentials file
3. Click "Clear" button
4. Verify: Name field is empty
5. Verify: Upload area shows upload icon (not checkmark)

---

### MCP Testing

#### Test: Register Subscription
1. Copy credentials: `cat ~/.claude/.credentials.json | pbcopy`
2. Via MCP: `register_subscription(name: "test-max", credentials_json: <paste>, subscription_type: "max")`
3. Verify: `list_subscriptions()` shows new subscription

#### Test: Assign to Agent
1. Start an agent
2. Via MCP: `assign_subscription(agent_name: "my-agent", subscription_name: "test-max")`
3. Verify: Response includes `injection_status: "success"`
4. Verify: Agent can execute without `ANTHROPIC_API_KEY`

#### Test: Agent Start Injection
1. Assign subscription to stopped agent
2. Start agent via UI or API
3. Verify: Start response includes `subscription_injection: "success"`

#### Test: Auth Report
1. Via API: `GET /api/ops/auth-report`
2. Verify: Agent shows under `by_auth_mode.subscription`

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-02-23 | Added Frontend UI section for Settings page integration (lines 223-435, 872-883, 1268-1387) |
| 2026-02-22 | Initial documentation for SUB-001 implementation |

---

## Related Flows

- **Credential Injection** (`credential-injection.md`) - General credential system (CRED-002)
- **Agent Lifecycle** (`agent-lifecycle.md`) - Subscription injection on agent start
- **MCP Orchestration** (`mcp-orchestration.md`) - MCP tools including subscription management
- **Settings Management** (`platform-settings.md`) - Platform API key configuration
