# Feature: Agent Info Display

## Overview
Displays template metadata (capabilities, commands, sub-agents, platforms, resources) in an "Info" tab on the agent detail page, exposing what an agent can do and how it is configured.

## User Story
As a platform user, I want to see what an agent is capable of so that I understand its purpose and available commands before interacting with it.

## Entry Points
- **UI**: `src/frontend/src/views/AgentDetail.vue:279-281` - Info tab is the default active tab
- **API**: `GET /api/agents/{name}/info`

---

## Frontend Layer

### Components

#### AgentDetail.vue:179-189
Tab button for Info panel:
```vue
<button
  @click="activeTab = 'info'"
  :class="[
    'px-6 py-3 border-b-2 font-medium text-sm transition-colors',
    activeTab === 'info'
      ? 'border-indigo-500 text-indigo-600'
      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
  ]"
>
  Info
</button>
```

#### AgentDetail.vue:279-281
Info tab content rendering:
```vue
<div v-if="activeTab === 'info'" class="p-6">
  <InfoPanel :agent-name="agent.name" :agent-status="agent.status" />
</div>
```

#### InfoPanel.vue:1-257
The complete Info Panel component displaying template metadata.

**Key sections displayed:**
| Section | Lines | Data Field | Visual Style |
|---------|-------|------------|--------------|
| Header (name, version, author) | 27-63 | `display_name`, `version`, `author`, `type` | Gradient header box |
| Resources (CPU, Memory) | 66-83 | `resources.cpu`, `resources.memory` | White card with icon |
| Capabilities | 86-102 | `capabilities[]` | Green pills |
| Slash Commands | 105-121 | `commands[]` | Purple mono pills |
| Sub-Agents | 124-141 | `sub_agents[]` | Blue grid cards |
| Platforms | 144-160 | `platforms[]` | Gray pills |
| MCP Servers | 163-179 | `mcp_servers[]` | Yellow mono pills |
| Enabled Tools | 182-199 | `tools[]` | Orange pills |

**Component script (lines 204-257):**
```javascript
const props = defineProps({
  agentName: { type: String, required: true },
  agentStatus: { type: String, default: 'stopped' }
})

const loadTemplateInfo = async () => {
  loading.value = true
  try {
    const response = await agentsStore.getAgentInfo(props.agentName)
    templateInfo.value = response
  } catch (error) {
    templateInfo.value = {
      has_template: false,
      message: 'Failed to load template information'
    }
  } finally {
    loading.value = false
  }
}

// Reload when agent status changes to running (to get full info)
watch(() => props.agentStatus, (newStatus) => {
  if (newStatus === 'running') {
    loadTemplateInfo()
  }
})

onMounted(() => {
  loadTemplateInfo()
})
```

### State Management

#### stores/agents.js:191-197
```javascript
async getAgentInfo(name) {
  const authStore = useAuthStore()
  const response = await axios.get(`/api/agents/${name}/info`, {
    headers: authStore.authHeader
  })
  return response.data
}
```

### API Calls
```javascript
GET /api/agents/{agent_name}/info
Headers: Authorization: Bearer {token}
```

---

## Backend Layer

### Endpoint

#### src/backend/routers/agents.py:625-705
```python
@router.get("/{agent_name}/info")
async def get_agent_info_endpoint(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
```

### Business Logic

**Decision tree:**
```
1. Check user has access to agent
   |
   +-> NO  --> 403 Forbidden
   |
   +-> YES --> Check if agent exists
               |
               +-> NO  --> 404 Not Found
               |
               +-> YES --> Check container status
                           |
                           +-> STOPPED --> Return basic info from Docker labels
                           |
                           +-> RUNNING --> Proxy to agent container API
```

**When agent is STOPPED (lines 651-664):**
Returns limited info from Docker container labels:
```python
labels = container.labels
return {
    "has_template": bool(labels.get("trinity.template")),
    "agent_name": agent_name,
    "template_name": labels.get("trinity.template", ""),
    "type": labels.get("trinity.agent-type", ""),
    "resources": {
        "cpu": labels.get("trinity.cpu", ""),
        "memory": labels.get("trinity.memory", "")
    },
    "status": "stopped",
    "message": "Agent is stopped. Start the agent to see full template info."
}
```

**When agent is RUNNING (lines 667-689):**
Proxies request to agent container:
```python
agent_url = f"http://agent-{agent_name}:8000/api/template/info"
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.get(agent_url)
    if response.status_code == 200:
        data = response.json()
        data["status"] = "running"
        return data
```

### Docker Operations
- `get_agent_container(agent_name)` - Retrieves container by name
- `container.reload()` - Refreshes container state
- `container.labels` - Reads Docker labels for basic info

---

## Agent Layer

### Agent Server Endpoint

#### docker/base-image/agent-server.py:1504-1565
```python
@app.get("/api/template/info")
async def get_template_info():
    """
    Get template metadata from template.yaml if available.
    Returns information about what this agent is, its capabilities, commands, etc.
    """
```

### Template Discovery
Searches for `template.yaml` in multiple locations (lines 1513-1531):
```python
template_paths = [
    home_dir / "template.yaml",
    home_dir / "workspace" / "template.yaml",
    Path("/template") / "template.yaml",
]
```

### Response Schema

**When template exists (lines 1543-1565):**
```python
return {
    "has_template": True,
    "template_path": str(template_path),
    "agent_name": agent_state.agent_name,
    # Core metadata
    "name": template_data.get("name", ""),
    "display_name": template_data.get("display_name", template_data.get("name", "")),
    "description": template_data.get("description", ""),
    "version": template_data.get("version", ""),
    "author": template_data.get("author", ""),
    "updated": template_data.get("updated", ""),
    # Type and resources
    "type": template_data.get("type", ""),
    "resources": template_data.get("resources", {}),
    # Capabilities and features
    "capabilities": template_data.get("capabilities", []),
    "sub_agents": template_data.get("sub_agents", []),
    "commands": template_data.get("commands", []),
    "platforms": template_data.get("platforms", []),
    "tools": template_data.get("tools", []),
    # MCP servers (just the names, not credentials)
    "mcp_servers": list(template_data.get("credentials", {}).get("mcp_servers", {}).keys()),
}
```

**When no template (lines 1535-1540):**
```python
return {
    "has_template": False,
    "agent_name": agent_state.agent_name,
    "template_name": os.getenv("TEMPLATE_NAME", ""),
    "message": "No template.yaml found - this agent was created without a template"
}
```

---

## Template Schema

### Example: ruby-social-media-agent/template.yaml

**Location**: `config/agent-templates/ruby-social-media-agent/template.yaml`

```yaml
name: ruby-social-media-agent
display_name: "Ruby - Social Media Content Manager"
description: |
  Multi-platform content production and distribution agent...
version: "1.3"
author: "Eugene Vyborov"
updated: "2025-11-25"

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
        - TWITTER_ACCESS_TOKEN
        - TWITTER_ACCESS_TOKEN_SECRET
    # ... more servers

capabilities:
  - multi_platform_posting
  - video_generation
  - media_management
  - content_scheduling
  - analytics_tracking
  - ai_image_generation
  - gif_management

sub_agents:
  - ai-ruminator
  - gemini-agent
  - giphy-manager
  - metricool-manager
  - social-media-manager
  - video-editor
  - video-generator
  - video-repurposer

commands:
  - clip-video
  - create-article
  - create-video
  - generate-image
  - get-perspective
  - post-now
  - schedule-post
  - schedule-prepared-content
  - upload-media

platforms:
  - twitter
  - linkedin
  - instagram
  - tiktok
  - youtube
  - threads
  - bluesky
  - facebook
  - pinterest
```

---

## Data Flow Diagram

```
+------------------+     +------------------+     +------------------+
|  InfoPanel.vue   |     |   agents.js      |     |   Backend API    |
|                  |     |   (Store)        |     |                  |
|  onMounted() ----+---->| getAgentInfo() --+---->| GET /agents/     |
|                  |     |                  |     |   {name}/info    |
+------------------+     +------------------+     +--------+---------+
                                                          |
                              +---------------------------+
                              |
                              v
              +---------------+---------------+
              |                               |
              v                               v
    +------------------+            +------------------+
    | Agent STOPPED    |            | Agent RUNNING    |
    |                  |            |                  |
    | Return Docker    |            | Proxy to agent:  |
    | container labels |            | http://{name}:   |
    | (basic info)     |            | 8000/api/        |
    +------------------+            | template/info    |
                                    +--------+---------+
                                             |
                                             v
                                    +------------------+
                                    | Agent Container  |
                                    |                  |
                                    | Read template.   |
                                    | yaml from disk   |
                                    | Parse YAML       |
                                    | Return metadata  |
                                    +------------------+
```

---

## Side Effects

- **WebSocket**: None
- **Audit Log**: None (read-only operation)
- **Redis**: None

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Agent not found | 404 | "Agent not found" |
| Access denied | 403 | "You don't have permission to access this agent" |
| Agent starting up | 504 | "Agent is starting up, please try again" |
| Container proxy failure | 200 | Returns fallback with container labels |
| No template.yaml | 200 | `{"has_template": false, "message": "..."}` |

---

## Security Considerations

- **Authorization**: User must have access to the agent (owner, shared, or admin)
- **No credentials exposed**: MCP servers list contains only names, not secrets
- **Container isolation**: Backend proxies request, frontend never talks to agent directly
- **Docker network**: Agent container only accessible via internal Docker network

---

## UI States

### Loading State
```vue
<div v-if="loading" class="flex items-center justify-center py-8">
  <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
</div>
```

### No Template State
```vue
<div v-else-if="!templateInfo?.has_template" class="text-center py-8">
  <h3>No Template Information</h3>
  <p>{{ templateInfo?.message || 'This agent was created without a template.' }}</p>
</div>
```

### Full Template Display
Renders all metadata sections when `templateInfo.has_template === true`

---

## Helper Function

### formatCapability (InfoPanel.vue:239-245)
Converts snake_case capability names to Title Case:
```javascript
const formatCapability = (capability) => {
  return capability
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
```

---

## Related Flows

- **Upstream**:
  - [Agent Lifecycle](agent-lifecycle.md) - Agent must exist to display info
  - [Template Processing](template-processing.md) - Template must be parsed at agent creation
- **Downstream**:
  - [Agent Chat](agent-chat.md) - User understands commands before chatting
  - [Credential Injection](credential-injection.md) - User sees required MCP servers

---

## Testing Notes

1. **Test with stopped agent**: Should show basic info from Docker labels
2. **Test with running agent**: Should show full template metadata
3. **Test without template**: Should show "No Template Information" message
4. **Test status change**: Reload should trigger when agent starts

---

## Status
✅ **Working** - Verified implementation, all line numbers accurate as of 2025-12-02
