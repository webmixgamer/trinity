# Feature: Model Selection

## Overview

Model selection allows users to view and change the LLM model used by an agent. Each agent can be configured to use different model variants (e.g., Claude Sonnet, Opus, Haiku or Gemini Flash, Pro) for subsequent executions. The model setting persists until explicitly changed, even across session resets.

## User Stories

| ID | Story |
|----|-------|
| CFG-005 | As a user, I want to view the current model so that I know which LLM is being used |
| CFG-006 | As a user, I want to change the model so that I can use different LLM variants |

## Entry Points

- **UI**: `src/frontend/src/views/AgentDetail.vue:107-108` - Model passed to TerminalPanelContent component
- **API (GET)**: `GET /api/agents/{name}/model` - Retrieve current model
- **API (PUT)**: `PUT /api/agents/{name}/model` - Update model selection
- **WebSocket**: Model passed as query parameter when connecting to terminal

## Frontend Layer

### Components

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| AgentDetail | `src/frontend/src/views/AgentDetail.vue` | 107-108 | Passes `currentModel` to TerminalPanelContent |
| TerminalPanelContent | `src/frontend/src/components/TerminalPanelContent.vue` | 33, 119-122 | Forwards model prop to AgentTerminal |
| AgentTerminal | `src/frontend/src/components/AgentTerminal.vue` | 123-127, 331-332 | Includes model in WebSocket connection URL |

### Data Flow

```
AgentDetail.vue
    |-- currentModel (from useAgentSettings composable)
    |
    v
TerminalPanelContent.vue (props.model)
    |
    v
AgentTerminal.vue
    |-- Adds model to WebSocket URL: ?mode=claude&model={model}
    v
WebSocket /api/agents/{name}/terminal?mode=claude&model={model}
```

### Composable

**File**: `src/frontend/src/composables/useAgentSettings.js`

| Method | Lines | Purpose |
|--------|-------|---------|
| `currentModel` | 13 | Reactive ref storing selected model |
| `loadModelInfo()` | 52-60 | Fetches current model from agent (unused - see Note) |
| `changeModel()` | 62-76 | Updates model via API (unused - see Note) |

**Note**: Model changes are primarily handled via the agent-server state, not frontend API calls. The Terminal connects with a model parameter, and the agent-server sets the model on that session.

### Store Actions

**File**: `src/frontend/src/stores/agents.js`

| Action | Lines | Purpose |
|--------|-------|---------|
| `getAgentModel(name)` | 292-298 | GET /api/agents/{name}/model |
| `setAgentModel(name, model)` | 300-307 | PUT /api/agents/{name}/model |

```javascript
// Get current model
async getAgentModel(name) {
  const response = await axios.get(`/api/agents/${name}/model`, {
    headers: authStore.authHeader
  })
  return response.data
}

// Set model
async setAgentModel(name, model) {
  const response = await axios.put(`/api/agents/${name}/model`,
    { model: model || '' },
    { headers: authStore.authHeader }
  )
  return response.data
}
```

## Backend Layer

### Endpoints

**File**: `src/backend/routers/chat.py`

| Endpoint | Lines | Purpose |
|----------|-------|---------|
| `GET /api/agents/{name}/model` | 852-884 | Get current model and available models |
| `PUT /api/agents/{name}/model` | 887-920 | Set model for subsequent messages |

### Request/Response Models

**File**: `src/backend/models.py:101-103`

```python
class ModelChangeRequest(BaseModel):
    """Request model for changing agent's model."""
    model: str  # Model alias: sonnet, opus, haiku, or full model name
```

### GET Model Response

```json
{
  "model": "sonnet",
  "runtime": "claude-code",
  "available_models": ["sonnet", "opus", "haiku"],
  "note": "Claude model aliases: sonnet (Sonnet 4.5), opus (Opus 4.5), haiku. Add [1m] suffix for 1M context."
}
```

### PUT Model Request/Response

```json
// Request
{ "model": "opus" }

// Response
{
  "status": "success",
  "model": "opus",
  "note": "Model will be used for subsequent messages"
}
```

### Business Logic

1. Validate agent exists and is running
2. Forward request to agent-server (`http://agent-{name}:8000/api/model`)
3. Return agent-server response

```python
# GET /api/agents/{name}/model
async with httpx.AsyncClient() as client:
    response = await client.get(
        f"http://agent-{name}:8000/api/model",
        timeout=10.0
    )
    return response.json()

# PUT /api/agents/{name}/model
async with httpx.AsyncClient() as client:
    response = await client.put(
        f"http://agent-{name}:8000/api/model",
        json={"model": request.model},
        timeout=10.0
    )
    return response.json()
```

### Terminal WebSocket Endpoint

**File**: `src/backend/routers/agents.py:1174-1188`

```python
@router.websocket("/{agent_name}/terminal")
async def agent_terminal(
    websocket: WebSocket,
    agent_name: str,
    mode: str = Query(default="claude"),
    model: str = Query(default=None)  # Model parameter from WebSocket URL
):
    await _terminal_manager.handle_terminal_session(
        websocket=websocket,
        agent_name=agent_name,
        mode=mode,
        decode_token_fn=decode_token,
        model=model  # Passed to terminal session
    )
```

## Agent Server Layer

### State Management

**File**: `docker/base-image/agent_server/state.py`

| Property | Lines | Purpose |
|----------|-------|---------|
| `current_model` | 36 | Stores selected model (persists across session reset) |
| `agent_runtime` | 24 | Runtime type: "claude-code" or "gemini-cli" |

```python
class AgentState:
    def __init__(self):
        # Model selection (persists across session)
        self.current_model: Optional[str] = os.getenv("AGENT_RUNTIME_MODEL", None) or os.getenv("CLAUDE_MODEL", None)

    def reset_session(self):
        # Note: current_model is NOT reset - it persists until explicitly changed
```

### Agent Model Endpoints

**File**: `docker/base-image/agent_server/routers/chat.py`

| Endpoint | Lines | Purpose |
|----------|-------|---------|
| `GET /api/model` | 162-180 | Get current model and available models |
| `PUT /api/model` | 183-221 | Set model with validation |

### Model Validation

**Claude Code (lines 206-221)**:
- Valid aliases: `sonnet`, `opus`, `haiku`, `sonnet[1m]`, `opus[1m]`, `haiku[1m]`
- Also accepts full model names starting with `claude-`

**Gemini CLI (lines 191-205)**:
- Valid models: `gemini-3-pro`, `gemini-3-flash`, `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-pro`, `gemini-1.5-flash`
- Also accepts any model starting with `gemini-`

### Model Application

**File**: `docker/base-image/agent_server/services/claude_code.py`

```python
# Line 421: Set model on agent state
agent_state.current_model = model

# Lines 434-436: Apply model to Claude command
if agent_state.current_model:
    cmd.extend(["--model", agent_state.current_model])
    logger.info(f"Using model: {agent_state.current_model}")
```

### Chat Integration

**File**: `docker/base-image/agent_server/routers/chat.py:43-44`

```python
# Use request.model if provided, otherwise use the model set via /api/model endpoint
effective_model = request.model or agent_state.current_model
```

## Data Flow Diagram

```
User selects model in UI
         |
         v
AgentDetail.vue (currentModel state)
         |
         v
TerminalPanelContent.vue (model prop)
         |
         v
AgentTerminal.vue
         |-- Builds WebSocket URL with model param
         v
/api/agents/{name}/terminal?mode=claude&model=opus
         |
         v
Backend Terminal WebSocket Handler
         |-- Spawns PTY with model flag
         v
Agent Container: claude --model opus
         |
         v
Claude Code CLI uses specified model
```

## Default Model Logic

**File**: `src/frontend/src/views/AgentDetail.vue:361-367`

```javascript
const defaultModel = computed(() => {
  const runtime = agent.value?.runtime || 'claude-code'
  if (runtime === 'gemini-cli' || runtime === 'gemini') {
    return 'gemini-2.5-flash'
  }
  return 'sonnet' // Claude default
})
```

**File**: `docker/base-image/agent_server/state.py:36`

```python
# Environment variable defaults
self.current_model: Optional[str] = os.getenv("AGENT_RUNTIME_MODEL", None) or os.getenv("CLAUDE_MODEL", None)
```

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Agent not found | 404 | "Agent not found" |
| Agent not running | 400 | "Agent is not running" |
| Invalid Claude model | 400 | "Invalid Claude model: {model}. Use aliases (sonnet, opus, haiku) or full model names." |
| Invalid Gemini model | 400 | "Invalid Gemini model: {model}. Use: gemini-2.5-pro, gemini-2.5-flash, etc." |
| Agent server unreachable | 503 | "Failed to get/set model" |

## Available Models

### Claude Code Runtime

| Alias | Full Name | Notes |
|-------|-----------|-------|
| `sonnet` | Claude Sonnet 4.5 | Default, balanced |
| `opus` | Claude Opus 4.5 | Highest capability |
| `haiku` | Claude Haiku | Fastest, cheapest |
| `sonnet[1m]` | Claude Sonnet (1M) | Extended context |
| `opus[1m]` | Claude Opus (1M) | Extended context |
| `haiku[1m]` | Claude Haiku (1M) | Extended context |

### Gemini Runtime

| Model | Notes |
|-------|-------|
| `gemini-2.5-pro` | Latest pro model, 1M context |
| `gemini-2.5-flash` | Default, fast and capable |
| `gemini-2.0-flash` | Previous generation |
| `gemini-1.5-pro` | Legacy pro |
| `gemini-1.5-flash` | Legacy flash |

## Testing

### Prerequisites
- Agent must be running
- User must have access to the agent

### Test Steps

1. **View Current Model**
   - Action: Navigate to agent detail page, switch to Terminal tab
   - Expected: Terminal connects with current model
   - Verify: `GET /api/agents/{name}/model` returns model info

2. **Change Model via API**
   - Action: `PUT /api/agents/{name}/model` with `{"model": "opus"}`
   - Expected: 200 response with success status
   - Verify: Subsequent `/api/model` returns new model

3. **Model Validation - Valid**
   - Action: Set model to "sonnet", "opus", "haiku"
   - Expected: Each succeeds with 200

4. **Model Validation - Invalid**
   - Action: Set model to "invalid-model"
   - Expected: 400 error with validation message

5. **Model Persistence**
   - Action: Set model, clear session, check model
   - Expected: Model persists after session reset

6. **Terminal Model Parameter**
   - Action: Connect terminal WebSocket with model param
   - Expected: Terminal uses specified model for Claude commands

### Edge Cases

- Setting model on stopped agent returns 400
- Gemini runtime rejects Claude model names
- Claude runtime rejects Gemini model names
- Empty model string clears to default

### Status

- [x] CFG-005: View current model - Implemented
- [x] CFG-006: Change model - Implemented

## Related Flows

- **Upstream**: [Agent Terminal](agent-terminal.md) - Terminal uses model for CLI commands
- **Downstream**: [Execution Queue](execution-queue.md) - Model applied during task execution
- **Related**: [Agent Lifecycle](agent-lifecycle.md) - Model persists while agent runs

## Revision History

| Date | Change |
|------|--------|
| 2026-01-13 | Initial documentation created |
