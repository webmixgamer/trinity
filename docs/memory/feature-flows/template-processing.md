# Feature: Template Processing

## Overview
Template processing enables agent creation from pre-configured templates, supporting both local templates (in `config/agent-templates/`) and GitHub-based templates. The system extracts credential requirements, parses template.yaml metadata, processes .mcp.json templates, and initializes agent workspaces.

## User Story
As a platform user, I want to create agents from templates so that I can quickly deploy pre-configured agents with the correct MCP servers and credential requirements.

## Entry Points
- **UI**: `src/frontend/src/views/Templates.vue` - Dedicated templates page (primary)
- **UI**: `src/frontend/src/components/CreateAgentModal.vue` - Create agent form with template selection
- **API**: `GET /api/templates` - List available templates
- **API**: `GET /api/templates/{template_id}` - Get template details
- **API**: `POST /api/agents` - Create agent with template

---

## Frontend Layer

### Templates.vue (`src/frontend/src/views/Templates.vue`) - **UPDATED 2025-12-07**

Dedicated templates page that dynamically loads templates from the API (previously static hardcoded cards).

| Line | Element | Purpose |
|------|---------|---------|
| 16-23 | Refresh button | `@click="fetchTemplates"` with loading spinner |
| 54-133 | GitHub Templates section | Grid of GitHub template cards |
| 136-215 | Local Templates section | Grid of local template cards |
| 217-246 | Custom Agent section | "Blank Agent" card |
| 261-266 | CreateAgentModal | Opens with `initial-template` prop pre-selected |
| 302-316 | `fetchTemplates()` | Fetches from `/api/templates` API |
| 318-321 | `useTemplate()` | Sets `selectedTemplateId` and opens modal |
| 323-330 | `onAgentCreated()` | Navigates to `/agents/{name}` after creation |

**Template Card Display**:
- Name and description (GitHub shows repo, local shows display_name)
- MCP Servers list (shows up to 4, then "+N more")
- Resources: CPU and memory allocation
- Credentials count
- "Use Template" button

**Computed Properties** (Lines 288-294):
```javascript
const githubTemplates = computed(() => {
  return templates.value.filter(t => t.source === 'github')
})

const localTemplates = computed(() => {
  return templates.value.filter(t => t.source === 'local' || !t.source)
})
```

### CreateAgentModal.vue (`src/frontend/src/components/CreateAgentModal.vue`) - **UPDATED 2025-12-07**

| Line | Element | Purpose |
|------|---------|---------|
| 9 | Form submission | `@submit.prevent="createAgent"` |
| 29-50 | Blank agent option | `form.template = ''` selection |
| 52-84 | GitHub templates section | Shows templates from API with `source === 'github'` |
| 86-118 | Local templates section | Shows templates with `source === 'local'` |
| 173-178 | `initialTemplate` prop | **NEW**: Pre-selects template when modal opens |
| 180 | `emit('created', agent)` | **NEW**: Emits created agent data for navigation |
| 189-192 | Watch initialTemplate | Syncs form.template when prop changes |
| 252-254 | createAgent success | Emits `created` event with agent data |

**New Props** (Lines 173-178):
```javascript
const props = defineProps({
  initialTemplate: {
    type: String,
    default: ''
  }
})
```

**New Events** (Line 180):
```javascript
const emit = defineEmits(['close', 'created'])
```

**Watch for initialTemplate** (Lines 189-192):
```javascript
watch(() => props.initialTemplate, (newVal) => {
  form.template = newVal || ''
})
```

### Template Display Logic
```javascript
const githubTemplates = computed(() => {
  return templates.value.filter(t => t.source === 'github')
})

const localTemplates = computed(() => {
  return templates.value.filter(t => t.source === 'local' || !t.source)
})
```

---

## Backend Layer

### Template Endpoints (`src/backend/routers/templates.py`)

| Line | Endpoint | Purpose |
|------|----------|---------|
| 19-55 | `GET /api/templates` | List all templates |
| 58-144 | `GET /api/templates/env-template` | Get .env template |
| 147-176 | `GET /api/templates/{template_id}` | Get template details |

### List Templates (`routers/templates.py:19-55`)
```python
@router.get("")
async def list_templates(current_user: User = Depends(get_current_user)):
    # 1. Load hardcoded GITHUB_TEMPLATES from config.py
    # 2. Scan config/agent-templates/ for local templates
    # 3. Parse template.yaml for each local template
    # 4. Extract credential requirements via extract_agent_credentials()
    # 5. Return merged list
```

### Template Response Schema
```json
{
  "id": "github:Abilityai/agent-ruby",
  "display_name": "Ruby - Social Media Agent",
  "source": "github",
  "resources": {"cpu": "2", "memory": "4g"},
  "mcp_servers": ["heygen", "twitter-mcp"],
  "required_credentials": [
    {"name": "HEYGEN_API_KEY", "source": "mcp:heygen"}
  ]
}
```

---

## Template Processing Logic

### GitHub Templates (`routers/agents.py:142-169`)
```python
if config.template.startswith("github:"):
    gh_template = get_github_template(config.template)
    if not gh_template:
        raise HTTPException(status_code=400, detail="Unknown GitHub template")

    # Get GitHub PAT from credential store
    github_cred = credential_manager.get_credential(github_cred_id, "admin")
    github_secret = credential_manager.get_credential_secret(github_cred_id, "admin")
    github_pat = github_secret.get("token") or github_secret.get("api_key")

    # Store for agent container (clone happens at startup)
    github_repo_for_agent = gh_template["github_repo"]
    github_pat_for_agent = github_pat
    config.resources = gh_template.get("resources", config.resources)
```

### Local Templates (`routers/agents.py:170-191`)
```python
else:
    templates_dir = Path("/agent-configs/templates")
    if not templates_dir.exists():
        templates_dir = Path("./config/agent-templates")

    template_path = templates_dir / config.template
    template_yaml = template_path / "template.yaml"

    if template_yaml.exists():
        with open(template_yaml) as f:
            template_data = yaml.safe_load(f)
            config.type = template_data.get("type", config.type)
            config.resources = template_data.get("resources", config.resources)
            config.tools = template_data.get("tools", config.tools)
```

---

## Credential Extraction

### extract_agent_credentials (`services/template_service.py:143-225`)
```python
def extract_agent_credentials(repo_path: Path) -> Dict:
    """Extract credential requirements from:
    1. .mcp.json or .mcp.json.template (${VAR_NAME} patterns)
    2. template.yaml (credentials schema)
    3. .env.example (env file vars)
    """
    pattern = r'\$\{([A-Z][A-Z0-9_]*)\}'  # Matches ${VAR_NAME}
```

### extract_env_vars_from_mcp_json (`services/template_service.py:64-103`)
```python
def extract_env_vars_from_mcp_json(file_path: Path) -> Dict[str, List[str]]:
    # Searches in env section and args array
    for server_name, server_config in mcp_servers.items():
        if "env" in server_config:
            matches = re.findall(pattern, value)  # ${VAR_NAME}
        if "args" in server_config:
            matches = re.findall(pattern, arg)
```

### generate_credential_files (`services/template_service.py:228-299`)
```python
def generate_credential_files(template_data: dict, agent_credentials: dict, ...):
    """
    Generate credential files (.mcp.json, .env, config files) with real values.
    Returns dict of {filepath: content} to write into container.
    """
    # Replaces ${VAR_NAME} with actual credential values
```

---

## Agent Container Initialization

### startup.sh (`docker/base-image/startup.sh`)

**GitHub Template** (lines 6-35):
```bash
if [ -n "${GITHUB_REPO}" ] && [ -n "${GITHUB_PAT}" ]; then
    CLONE_URL="https://oauth2:${GITHUB_PAT}@github.com/${GITHUB_REPO}.git"
    git clone --depth 1 "${CLONE_URL}" /tmp/repo-clone
    cp -r /tmp/repo-clone/* /home/developer/
fi
```

**Local Template** (lines 38-76):
```bash
elif [ -n "${TEMPLATE_NAME}" ] && [ -d "/template" ]; then
    cp -r /template/.claude . 2>/dev/null || true
    cp /template/CLAUDE.md . 2>/dev/null || true
fi
```

**Credential Files** (lines 78-110):
```bash
if [ -d "/generated-creds" ]; then
    cp /generated-creds/.mcp.json . 2>/dev/null || true
    cp /generated-creds/.env . 2>/dev/null || true
fi
```

---

## Data Structures

### template.yaml Schema
```yaml
name: ruby-social-media-agent
display_name: "Ruby - Social Media Content Manager"
description: |
  Multi-platform content production agent...
version: "1.3"

resources:
  cpu: "2"
  memory: "4g"

credentials:
  mcp_servers:
    heygen:
      env_vars:
        - HEYGEN_API_KEY
    twitter-mcp:
      env_vars:
        - TWITTER_API_KEY
        - TWITTER_API_SECRET_KEY

  env_file:
    - BLOTATO_API_KEY
```

### .mcp.json.template
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

### GITHUB_TEMPLATES Definition (`config.py:60-98`)
```python
# Fixed credential ID for all GitHub templates
GITHUB_PAT_CREDENTIAL_ID = "github-pat-templates"

GITHUB_TEMPLATES = [
    {
        "id": "github:abilityai/agent-ruby",
        "display_name": "Ruby - Content & Publishing",
        "github_repo": "abilityai/agent-ruby",
        "github_credential_id": GITHUB_PAT_CREDENTIAL_ID,  # References fixed ID
        "source": "github",
        "mcp_servers": [],
        "required_credentials": [...]
    }
]
```

### GitHub PAT Auto-Upload (`main.py:86-139`)

On backend startup, the `initialize_github_pat()` function automatically uploads the `GITHUB_PAT` environment variable to Redis:

```python
def initialize_github_pat():
    """Upload GitHub PAT from environment to Redis on startup."""
    if not GITHUB_PAT:
        print("GitHub PAT not configured in environment (GITHUB_PAT)")
        return

    credential_manager = CredentialManager(REDIS_URL)
    # Creates/updates credential with ID "github-pat-templates"
    # Stores: {"token": "<PAT value>"}
```

**Configuration:**
1. Set `GITHUB_PAT` in `.env` file
2. Restart backend to sync to Redis
3. Templates automatically reference credential via `GITHUB_PAT_CREDENTIAL_ID`

---

## Side Effects

### WebSocket Broadcast
```json
{
  "event": "agent_created",
  "data": {
    "name": "agent-name",
    "template": "github:Abilityai/agent-ruby"
  }
}
```

### Docker Labels
```python
labels={
    'trinity.template': config.template or ''
}
```

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Unknown GitHub template | 400 | "Unknown GitHub template" |
| GitHub PAT not found | 500 | "GitHub credential not found" |
| Template not found | 404 | "Template not found" |
| Agent already exists | 400 | "Agent already exists" |

---

## Security Considerations

1. **GitHub PAT Storage**: Stored in Redis with fixed credential ID (`github-pat-templates`)
2. **PAT Auto-Upload**: Backend uploads PAT from `GITHUB_PAT` env var on startup
3. **PAT Injection**: Passed to agent container via `GITHUB_PAT` environment variable
4. **Shallow Clone**: `--depth 1` limits history exposure (when git sync disabled)
5. **Read-Only Mount**: Template volume mounted as `:ro`
6. **Never Logged**: PAT values are never written to logs or API responses

---

## Testing

### Manual Testing
```bash
# List all templates
curl http://localhost:8000/api/templates \
  -H "Authorization: Bearer $TOKEN"

# Get template details
curl http://localhost:8000/api/templates/ruby-social-media-agent \
  -H "Authorization: Bearer $TOKEN"

# Create agent from GitHub template
curl -X POST http://localhost:8000/api/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ruby-test",
    "template": "github:Abilityai/agent-ruby"
  }'

# Create agent from local template
curl -X POST http://localhost:8000/api/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "local-test",
    "template": "ruby-social-media-agent"
  }'
```

---

## Status
✅ **Working** - Template processing fully functional for both GitHub and local templates

---

## Revision History

| Date | Changes |
|------|---------|
| 2025-12-11 | **GitHub PAT Auto-Upload**: Added `GITHUB_PAT` env var support. Backend auto-uploads PAT to Redis on startup with fixed credential ID `github-pat-templates`. All templates now reference `GITHUB_PAT_CREDENTIAL_ID` constant. |
| 2025-12-07 | **Templates.vue rewrite**: Now dynamically fetches templates from `/api/templates` API instead of static hardcoded cards. Added GitHub/Local template sections with full metadata display. CreateAgentModal enhanced with `initialTemplate` prop and `created` event for navigation to new agent. |

---

## Related Flows

- **Upstream**: User authentication
- **Downstream**: Credential Injection (hot-reload), Agent Lifecycle (start after creation)
