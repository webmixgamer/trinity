# Feature Flow Analysis

Create or update a feature flow document for end-to-end understanding.

## Arguments

- `$ARGUMENTS` - Feature name (e.g., "agent-chat", "credential-injection")

## Instructions

1. If no feature name provided, ask:
   ```
   Which feature would you like to analyze?
   Available options (from feature-flows.md pending list):
   - Agent Lifecycle
   - Credential Injection
   - Auth0 Authentication
   - Agent Chat
   - MCP Orchestration
   - Agent Sharing
   - Activity Monitoring
   - Template Processing
   ```

2. Trace the feature execution path:

   **Frontend (UI → Store → API)**
   - Find UI entry point (Vue component, button/action)
   - Trace to store action (Pinia)
   - Document API call made

   **Backend (Endpoint → Logic → Docker/DB)**
   - Find FastAPI endpoint in `src/backend/main.py`
   - Trace business logic
   - Document Docker SDK calls or database operations

   **Agent (if applicable)**
   - Find agent-server.py endpoint
   - Document Claude Code invocation
   - Note file operations

3. Document side effects:
   - WebSocket broadcasts
   - Audit log events
   - State changes

4. Document error handling:
   - What can fail?
   - HTTP status codes returned
   - Error messages shown to user

5. Save flow document:
   - Path: `docs/memory/feature-flows/{feature-name}.md`
   - Use template from feature-flows.md

6. Update index:
   - Add entry to `docs/memory/feature-flows.md`
   - Mark as documented with components list

## Output Format

Use the feature flow template:

```markdown
# Feature: {Feature Name}

## Overview
Brief description.

## User Story
As a [user], I want to [action] so that [benefit].

## Entry Points
- **UI**: `path/to/Component.vue` - Action trigger
- **API**: `METHOD /api/endpoint`

## Frontend Layer
### Components
- `Component.vue:line` - handler()

### State Management
- `stores/store.js` - actionName

### API Calls
await api.method(`/api/endpoint`)

## Backend Layer
### Endpoints
- `src/backend/main.py:line` - handler()

### Business Logic
1. Step one
2. Step two

## Data Layer
### Database Operations
- Query: description
- Update: description

## Side Effects
- WebSocket: `{type, data}`
- Audit: event logged

## Error Handling
- Case → HTTP status

## Security Considerations
- Auth checks
- Rate limiting

## Related Flows
- Upstream: flow
- Downstream: flow
```

## Principle

Information density over completeness. Think debugging notes, not comprehensive docs.
