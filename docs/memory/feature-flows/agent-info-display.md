# Feature: Agent Info Display

## Overview
Displays template metadata (capabilities, commands, sub-agents, platforms, resources) in an "Info" tab on the agent detail page, exposing what an agent can do and how it is configured.

## User Story
As a platform user, I want to see what an agent is capable of so that I understand its purpose and available commands before interacting with it.

## Entry Points
- **UI**: `src/frontend/src/views/AgentDetail.vue:76-78` - Info tab content rendering
- **API**: `GET /api/agents/{name}/info`

---

## Frontend Layer

### Components

#### AgentDetail.vue:207-216
Tab button for Info panel:
```vue
<button
  @click="activeTab = 'info'"
  :class="[
    'inline-flex items-center px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
    activeTab === 'info'
      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
  ]"
>
  Info
</button>
```

#### AgentDetail.vue:76-78
Info tab content rendering:
```vue
<div v-if="activeTab === 'info'" class="p-6">
  <InfoPanel :agent-name="agent.name" :agent-status="agent.status" @item-click="handleInfoItemClick" />
</div>
```

#### AgentDetail.vue:566-576 - Item Click Handler
Handles clicks from Info tab items (use cases, commands, sub-agents) and redirects to Tasks tab:
```javascript
// Handle item click from Info tab - switch to Tasks tab with prefilled message
const handleInfoItemClick = ({ type, text }) => {
  // Set the prefill message and switch to Tasks tab
  taskPrefillMessage.value = text
  activeTab.value = 'tasks'
  // Clear the prefill after a short delay so it can be used again
  nextTick(() => {
    setTimeout(() => {
      taskPrefillMessage.value = ''
    }, 100)
  })
}
```

#### TasksPanel.vue - Initial Message Prop
```javascript
const props = defineProps({
  agentName: { type: String, required: true },
  agentStatus: { type: String, default: 'stopped' },
  highlightExecutionId: { type: String, default: null },
  initialMessage: { type: String, default: '' }  // NEW: prefilled task message
})

// Watch for initial message changes (from Info tab clicks)
watch(() => props.initialMessage, (newMessage) => {
  if (newMessage) {
    newTaskMessage.value = newMessage
  }
})
```

#### InfoPanel.vue:1-360
The complete Info Panel component displaying template metadata.

**Key sections displayed:**
| Section | Lines | Data Field | Visual Style | Clickable |
|---------|-------|------------|--------------|-----------|
| Header (name, version, author) | 27-67 | `display_name`, `tagline`, `version`, `author`, `type` | Gradient header box | No |
| Use Cases | 70-91 | `use_cases[]` | Clickable prompts grid | ✅ Yes |
| Resources (CPU, Memory) | 93-111 | `resources.cpu`, `resources.memory` | White card with icon | No |
| Sub-Agents | 113-145 | `sub_agents[]` | Blue grid cards | ✅ Yes |
| Slash Commands | 147-172 | `commands[]` | Purple mono pills | ✅ Yes |
| MCP Servers | 174-194 | `mcp_servers[]` | Yellow mono pills | No |
| Skills | 196-216 | `skills[]` | Teal pills | No |
| Capabilities | 218-235 | `capabilities[]` | Green pills | No |
| Platforms | 237-254 | `platforms[]` | Gray pills | No |
| Enabled Tools | 256-274 | `tools[]` | Orange pills | No |

**Click handlers (lines 333-353):**
```javascript
const emit = defineEmits(['item-click'])

const handleItemClick = (type, text) => {
  // Emit event to parent to open Tasks tab with this text
  emit('item-click', { type, text })
}

const handleUseCaseClick = (text) => {
  handleItemClick('use-case', text)
}

const handleCommandClick = (command) => {
  const commandName = getItemName(command)
  handleItemClick('command', `/${commandName}`)
}

const handleSubAgentClick = (subAgent) => {
  const agentName = getItemName(subAgent)
  const description = getItemDescription(subAgent)
  const prompt = description
    ? `Ask ${agentName} to help with: ${description}`
    : `Ask ${agentName} to help with a task`
  handleItemClick('sub-agent', prompt)
}
```

### State Management

#### stores/agents.js:224-230
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

#### src/backend/routers/agents.py:478-549
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

**When agent is STOPPED (lines 496-509):**
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

**When agent is RUNNING (lines 511-532):**
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

#### docker/base-image/agent_server/routers/info.py:81-152
```python
@router.get("/api/template/info")
async def get_template_info():
    """
    Get template metadata from template.yaml if available.
    Returns information about what this agent is, its capabilities, commands, etc.
    """
```

### Template Discovery
Searches for `template.yaml` in multiple locations (lines 87-94):
```python
template_paths = [
    home_dir / "template.yaml",
    home_dir / "workspace" / "template.yaml",
    Path("/template") / "template.yaml",
]
```

### Response Schema

**When template exists (lines 126-152):**
```python
return {
    "has_template": True,
    "template_path": str(template_path),
    "agent_name": agent_state.agent_name,
    # Core metadata
    "name": template_data.get("name", ""),
    "display_name": template_data.get("display_name", template_data.get("name", "")),
    "tagline": template_data.get("tagline", ""),
    "description": template_data.get("description", ""),
    "version": template_data.get("version", ""),
    "author": template_data.get("author", ""),
    "updated": template_data.get("updated", ""),
    # Type and resources
    "type": template_data.get("type", ""),
    "resources": template_data.get("resources", {}),
    # Use cases - example prompts for users
    "use_cases": template_data.get("use_cases", []),
    # Capabilities and features (can be strings or {name, description} objects)
    "capabilities": template_data.get("capabilities", []),
    "sub_agents": template_data.get("sub_agents", []),
    "commands": template_data.get("commands", []),
    "platforms": template_data.get("platforms", []),
    "tools": template_data.get("tools", []),
    "skills": template_data.get("skills", []),
    # MCP servers (can be strings or {name, description} objects)
    "mcp_servers": mcp_servers_raw,
}
```

**When no template (lines 110-117):**
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

## Helper Functions

### formatCapability (InfoPanel.vue:314-320)
Converts snake_case capability names to Title Case:
```javascript
const formatCapability = (capability) => {
  return capability
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
```

### getItemName / getItemDescription (InfoPanel.vue:303-312)
Handle items that can be either strings or {name, description} objects:
```javascript
const getItemName = (item) => {
  if (typeof item === 'string') return item
  return item?.name || ''
}

const getItemDescription = (item) => {
  if (typeof item === 'string') return null
  return item?.description || null
}
```

---

## MCP Tool Access (Added 2026-01-03)

Agents can also retrieve template metadata for other agents via the MCP tool `get_agent_info`:

### MCP Tool: `get_agent_info`

**File**: `src/mcp-server/src/tools/agents.ts:103-145`

```typescript
// Tool usage
get_agent_info({ name: "target-agent" })

// Returns: AgentTemplateInfo with full template.yaml metadata
```

### Access Control

| Key Scope | Access Rule |
|-----------|-------------|
| Agent-scoped | Self + permitted agents only (via `getPermittedAgents()`) |
| System-scoped | Full access to all agents |
| User-scoped | All accessible agents (owned + shared) |

### Client Method

**File**: `src/mcp-server/src/client.ts:184-189`

```typescript
async getAgentInfo(name: string): Promise<AgentTemplateInfo> {
  return this.request<AgentTemplateInfo>(
    "GET",
    `/api/agents/${encodeURIComponent(name)}/info`
  );
}
```

### Types

**File**: `src/mcp-server/src/types.ts:84-114`

```typescript
export interface AgentTemplateInfo {
  has_template: boolean;
  agent_name: string;
  display_name?: string;
  description?: string;
  version?: string;
  capabilities?: string[];
  commands?: AgentCommand[];
  mcp_servers?: string[];
  tools?: string[];
  skills?: string[];
  use_cases?: string[];
  // ... additional fields
}
```

### Use Case

Head agents can inspect sub-agent capabilities before delegating tasks:

```typescript
// Get sub-agent capabilities
const info = await mcp_trinity_get_agent_info({ name: "worker-agent" });
// Check if it has required skills
if (info.capabilities?.includes("code_review")) {
  await mcp_trinity_chat_with_agent({ agent_name: "worker-agent", message: "Review this PR" });
}
```

---

## Related Flows

- **Upstream**:
  - [Agent Lifecycle](agent-lifecycle.md) - Agent must exist to display info
  - [Template Processing](template-processing.md) - Template must be parsed at agent creation
- **Downstream**:
  - [Tasks Tab](tasks-tab.md) - **Click-through destination** for use cases, commands, and sub-agents
  - [Agent Terminal](agent-terminal.md) - User understands commands before interacting
  - [Credential Injection](credential-injection.md) - User sees required MCP servers
- **MCP Integration**:
  - [MCP Orchestration](mcp-orchestration.md) - `get_agent_info` tool (agents.ts:103-145)
  - [Agent Permissions](agent-permissions.md) - Access control for agent-scoped keys

---

## Testing Notes

1. **Test with stopped agent**: Should show basic info from Docker labels
2. **Test with running agent**: Should show full template metadata
3. **Test without template**: Should show "No Template Information" message
4. **Test status change**: Reload should trigger when agent starts
5. **Test use case click**: Should switch to Tasks tab with text prefilled
6. **Test command click**: Should switch to Tasks tab with `/command-name` prefilled
7. **Test sub-agent click**: Should switch to Tasks tab with delegation prompt prefilled

---

## Status
**Working** - Verified implementation, line numbers updated as of 2026-01-12

**Key Changes:**
- **2026-01-12**: **Interactive Items** - Use cases, commands, and sub-agents are now clickable
  - Clicking redirects to Tasks tab with text pre-filled in task input
  - Event changed from `@use-case-click` to `@item-click` with `{type, text}` payload
  - TasksPanel has new `initialMessage` prop for prefilled text
  - Commands prefill as `/command-name`, sub-agents prefill as delegation prompts
- **2026-01-03**: Added MCP tool `get_agent_info` for programmatic access to template metadata
- **2025-12-30**: Line numbers verified for agent server modular package
- **2025-12-06**: Agent server refactored to modular package structure (`docker/base-image/agent_server/`)
- InfoPanel.vue now supports `use_cases`, `skills`, `tagline` fields
- Items can be strings or {name, description} objects for rich display
