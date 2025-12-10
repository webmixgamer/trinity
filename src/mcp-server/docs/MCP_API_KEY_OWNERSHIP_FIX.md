# MCP API Key Ownership Bug Fix

**Date**: 2025-12-02
**Priority**: Critical
**Status**: ✅ Code Fixed | ⚠️ Configuration Required

---

## Issue Summary

When creating agents via Trinity MCP tools (`mcp__trinity__create_agent`), agents are incorrectly owned by **admin** instead of the user who owns the MCP API key.

### Example:
- User: `eugene@ability.ai` creates MCP API key in UI
- User calls `mcp__trinity__create_agent` via Claude Code
- **Expected**: Agent owned by `eugene@ability.ai`
- **Actual**: Agent owned by `admin` ❌

---

## Root Cause Analysis

### Problem Flow:

```
1. User creates MCP API key (eugene@ability.ai) ✅ Correct
   └─> Stored in database with user_id linking to eugene@ability.ai

2. User calls mcp__trinity__create_agent from Claude Code
   └─> MCP server receives request

3. MCP server authentication flow:
   ├─> MCP_REQUIRE_API_KEY = false (dev mode)
   ├─> NO API key validation performed
   ├─> MCP server authenticates to Trinity backend as "admin"
   └─> Uses admin token for all Trinity API calls ❌

4. Trinity backend receives create_agent request:
   ├─> Sees Authorization: Bearer <admin-token>
   ├─> Extracts user from token → "admin"
   └─> Creates agent owned by admin ❌
```

### Key Files Involved:

| File | Issue | Line |
|------|-------|------|
| `src/mcp-server/src/server.ts` | MCP_REQUIRE_API_KEY defaults to false | 76 |
| `src/mcp-server/src/server.ts` | Authenticates as admin user | 87-90 |
| `src/mcp-server/src/client.ts` | Uses admin token for API calls | 89-90 |
| `src/mcp-server/src/tools/agents.ts` | createAgent uses admin client | 122 (old code) |

---

## Fix Implemented

### Code Changes (Completed ✅):

#### 1. **Modified `src/mcp-server/src/types.ts`**
Added `mcpApiKey` field to `McpAuthContext`:
```typescript
export interface McpAuthContext {
  userId: string;
  userEmail?: string;
  keyName: string;
  agentName?: string;
  scope: "user" | "agent";
  mcpApiKey?: string;  // NEW: Store actual MCP API key
}
```

#### 2. **Modified `src/mcp-server/src/server.ts`**
Store MCP API key in auth context (Line 136):
```typescript
currentAuthContext = {
  userId: result.user_id || "unknown",
  userEmail: result.user_email,
  keyName: result.key_name || "unknown",
  agentName: result.agent_name,
  scope: scope as "user" | "agent",
  mcpApiKey: apiKey,  // NEW: Store for user-scoped requests
};
```

Pass auth context to agent tools (Line 161):
```typescript
const agentTools = createAgentTools(client, requireApiKey ? getAuthContext : undefined);
```

#### 3. **Modified `src/mcp-server/src/client.ts`**
Added `getBaseUrl()` method (Line 82-84):
```typescript
getBaseUrl(): string {
  return this.baseUrl;
}
```

#### 4. **Modified `src/mcp-server/src/tools/agents.ts`**
Accept auth context and create user-scoped client (Lines 16-34):
```typescript
export function createAgentTools(
  client: TrinityClient,
  getAuthContext?: () => McpAuthContext | undefined
) {
  const getClient = (mcpApiKey?: string): TrinityClient => {
    if (mcpApiKey) {
      // Create new client authenticated with user's MCP API key
      const userClient = new TrinityClient(client.getBaseUrl());
      userClient.setToken(mcpApiKey);
      return userClient;
    }
    return client;  // Fall back to admin client
  };
  // ...
}
```

Use user's client in createAgent (Lines 145-148):
```typescript
// Use user-scoped client if MCP API key is available
const authContext = getAuthContext?.();
const apiClient = getClient(authContext?.mcpApiKey);
const agent = await apiClient.createAgent(config);
```

### Build Status:
- ✅ TypeScript compiled successfully
- ✅ MCP server restarted

---

## Configuration Required

The fix is implemented but **requires environment configuration** to activate.

### Steps to Enable:

#### Option 1: Production Mode (Recommended)

**1. Set environment variable on MCP server container:**

Edit the container environment or docker-compose configuration:
```bash
MCP_REQUIRE_API_KEY=true
```

**2. Restart MCP server:**
```bash
docker restart trinity-mcp-server
```

**3. Verify authentication is enabled:**
```bash
docker logs trinity-mcp-server | grep "MCP API Key authentication"
# Should show: "MCP API Key authentication: ENABLED"
```

#### Option 2: Manual Testing (Quick Test)

**1. Get your MCP API key from Trinity UI:**
- Login to `http://localhost:3000` as `eugene@ability.ai`
- Navigate to `/api-keys`
- Copy your API key (starts with `trinity_...`)

**2. Test via curl with your key:**
```bash
curl -X POST http://localhost:8080/mcp/trinity/create_agent \
  -H "Authorization: Bearer YOUR_MCP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-ownership-eugene",
    "type": "business-assistant"
  }'
```

**3. Verify ownership:**
```bash
curl http://localhost:8000/api/agents/test-ownership-eugene | jq '.owner'
# Should show: "eugene@ability.ai" ✅
```

---

## Testing Plan

### Test Case 1: Agent Creation with User MCP Key

**Prerequisites:**
- MCP_REQUIRE_API_KEY=true
- User has MCP API key

**Steps:**
1. Create agent via MCP: `mcp__trinity__create_agent(name="user-owned-test")`
2. Query agent ownership: `GET /api/agents/user-owned-test`
3. Verify: `owner` should be `eugene@ability.ai`, not `admin`

**Expected Result:**
```json
{
  "name": "user-owned-test",
  "owner": "eugene@ability.ai",  ✅
  "is_owner": true,
  "can_delete": true
}
```

### Test Case 2: Multiple Users Creating Agents

**Steps:**
1. User A creates agent via their MCP key → Owned by User A
2. User B creates agent via their MCP key → Owned by User B
3. User A cannot see User B's agent (unless shared)

**Expected Result:**
- Each user sees only their own agents
- Access control enforced correctly

---

## Rollout Plan

### Phase 1: Local Testing (Current)
- ✅ Code fixed and deployed
- ⏳ Enable MCP_REQUIRE_API_KEY=true
- ⏳ Test with eugene@ability.ai MCP key
- ⏳ Verify ownership is correct

### Phase 2: Production Deployment
- Update production environment variables
- Restart MCP server
- Monitor logs for authentication success
- Test with multiple users

### Phase 3: Cleanup
- Delete all admin-owned test agents
- Update documentation
- Add to changelog

---

## Backwards Compatibility

### Dev Mode (MCP_REQUIRE_API_KEY=false):
- ❌ Fix does NOT activate
- Uses admin client (existing behavior)
- No breaking changes

### Production Mode (MCP_REQUIRE_API_KEY=true):
- ✅ Fix activates automatically
- Uses user's MCP API key
- Agents owned by correct user

---

## Known Limitations

1. **Existing admin-owned agents**: Will remain owned by admin. No automatic migration.
2. **Dev mode**: Fix only works when MCP API key auth is enabled
3. **Shared agents**: Ownership doesn't change when agent is shared (by design)

---

## Cleanup Checklist

After fix is verified:
- [ ] Delete test agents: `collab-test-alpha-1764712899`, `collab-test-beta-1764712899`, `collab-test-gamma-1764712899`
- [ ] Update `.claude/memory/changelog.md`
- [ ] Update `.claude/memory/architecture.md` (MCP authentication flow)
- [ ] Add test case to `docs/TESTING_GUIDE.md`
- [ ] Update `docs/MCP_TROUBLESHOOTING.md` with this issue

---

## References

### Modified Files:
- `src/mcp-server/src/types.ts` - Added mcpApiKey to McpAuthContext
- `src/mcp-server/src/server.ts` - Store and pass MCP API key
- `src/mcp-server/src/client.ts` - Added getBaseUrl() method
- `src/mcp-server/src/tools/agents.ts` - Use user-scoped client for createAgent

### Related Documentation:
- `.claude/memory/feature-flows/agent-to-agent-collaboration.md` - MCP authentication
- `docs/AGENT_TEMPLATE_SPEC.md` - Agent ownership model
- `.claude/memory/requirements.md` - REQ-4.2: Per-User API Keys

---

## Next Steps

**Immediate:**
1. Enable MCP_REQUIRE_API_KEY=true in environment
2. Restart MCP server
3. Test agent creation with user's MCP API key
4. Verify ownership shows `eugene@ability.ai`

**If Issues:**
- Check MCP server logs: `docker logs trinity-mcp-server`
- Verify API key is valid: `curl -X POST http://localhost:8000/api/mcp/validate -H "Authorization: Bearer YOUR_KEY"`
- Check Trinity backend logs: `docker logs trinity-backend`

**Questions?**
Contact Eugene or refer to Trinity documentation.
