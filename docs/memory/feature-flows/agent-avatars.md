# Feature: Agent Avatars (AVATAR-001)

## Overview
AI-generated circular avatars for agents using Gemini image generation, with fallback to deterministic gradient initials.

## User Story
As an agent owner, I want to generate a custom avatar for my agent from a text description so that my agents are visually distinguishable across the platform.

## Entry Points
- **UI (Generate)**: `src/frontend/src/components/AgentHeader.vue:4-19` - Camera icon overlay on avatar (owner-only, hover-triggered)
- **UI (Display)**: `src/frontend/src/components/AgentAvatar.vue` - Reusable avatar component (5 sizes)
- **API (Generate)**: `POST /api/agents/{agent_name}/avatar/generate`
- **API (Serve)**: `GET /api/agents/{agent_name}/avatar`
- **API (Identity)**: `GET /api/agents/{agent_name}/avatar/identity`
- **API (Delete)**: `DELETE /api/agents/{agent_name}/avatar`

---

## Frontend Layer

### Components

#### AgentAvatar.vue (reusable display component)
- **File**: `src/frontend/src/components/AgentAvatar.vue`
- Props: `name` (required), `avatarUrl` (nullable), `size` (sm/md/lg/xl/2xl)
- Sizes: sm=24px, md=32px, lg=48px, xl=64px, 2xl=96px
- Shows `<img>` when `avatarUrl` is set; on `@error` falls back to initials
- Fallback: deterministic gradient from agent name hash + 2-letter initials
- Gradient uses `hsl(hash%360, 65%, 45%)` to `hsl((hash+40)%360, 65%, 55%)`

#### AvatarGenerateModal.vue (generation modal)
- **File**: `src/frontend/src/components/AvatarGenerateModal.vue`
- Props: `show`, `agentName`, `initialPrompt`, `currentAvatarUrl`
- Emits: `close`, `updated`
- Contains textarea for identity prompt (500 char max)
- "Generate" button (line 49) calls `POST /api/agents/{agentName}/avatar/generate` (line 97)
- "Remove Avatar" button (line 31) calls `DELETE /api/agents/{agentName}/avatar` (line 114)
- Shows spinner during generation, error messages on failure

#### AgentHeader.vue (avatar trigger)
- **File**: `src/frontend/src/components/AgentHeader.vue:4-19`
- Avatar sits on left edge of card at `absolute left-0 top-3 -translate-x-1/2` (50% in, 50% out)
- Wrapped in indigo ring border (`border-[3px] border-indigo-400`)
- Camera icon overlay appears on hover (`group-hover:bg-black/40`)
- Only clickable for owners (`agent.can_share && !agent.is_system`)
- Click emits `open-avatar-modal` (line 5 and line 12)
- Emits declaration at line 438

#### Usage Locations

| Location | File | Line | Size | Context |
|----------|------|------|------|---------|
| Agent Detail Header | `src/frontend/src/components/AgentHeader.vue` | 6 | 2xl | Overlapping left edge of card, ring border, hover camera overlay |
| Dashboard Graph Nodes | `src/frontend/src/components/AgentNode.vue` | 28 | md | In node header, before agent name label |
| Agents List (desktop) | `src/frontend/src/views/Agents.vue` | 272 | sm | In agent row, before name link |
| Agents List (tablet) | `src/frontend/src/views/Agents.vue` | 442 | sm | In agent row, after status dot |
| Agents List (mobile) | `src/frontend/src/views/Agents.vue` | 585 | sm | In agent row, after status dot |

### State Management

No dedicated store. Avatar state is managed locally:

- `AgentDetail.vue:311` - `showAvatarModal = ref(false)`
- `AgentDetail.vue:312` - `avatarIdentityPrompt = ref('')`
- `AgentDetail.vue:844` - `loadAvatarIdentity()` called on mount
- `AgentDetail.vue:60` - `@open-avatar-modal="showAvatarModal = true"` handler on AgentHeader
- `AgentDetail.vue:220-228` - `AvatarGenerateModal` component with props
- `AgentDetail.vue:25` - `ml-14` class on agent content wrapper for avatar offset

### API Calls

```javascript
// Load identity prompt on mount (AgentDetail.vue:635)
await axios.get(`/api/agents/${agentName}/avatar/identity`, { headers: authHeader })

// Generate avatar (AvatarGenerateModal.vue:97)
await axios.post(`/api/agents/${agentName}/avatar/generate`, {
  identity_prompt: identityPrompt
})

// Remove avatar (AvatarGenerateModal.vue:114)
await axios.delete(`/api/agents/${agentName}/avatar`)
```

### Avatar URL Construction

The avatar URL includes a cache-busting `?v=` timestamp query parameter:

```javascript
// Backend constructs URL in two places:
// 1. agents.py:312 (single agent detail)
avatar_url = f"/api/agents/{agent_name}/avatar?v={identity['updated_at']}"

// 2. helpers.py:157 (agent list batch query)
avatar_url = f"/api/agents/{agent_name}/avatar?v={avatar_updated_at}"
```

The `avatar_url` field is included in agent data returned by both `GET /api/agents` (list) and `GET /api/agents/{name}` (detail).

### Data Flow for Dashboard Nodes

```
helpers.py:get_accessible_agents() -> agent_dict["avatar_url"]
  -> stores/network.js:460 -> avatarUrl: agent.avatar_url || null
    -> AgentNode.vue:28 -> <AgentAvatar :avatar-url="data.avatarUrl" />
```

System agents also get avatarUrl at `stores/network.js:426`.

### On Avatar Updated (refresh cycle)

```
AvatarGenerateModal emits 'updated'
  -> AgentDetail.vue:227 @updated="onAvatarUpdated"
    -> onAvatarUpdated() (line 644):
      1. await loadAgent()        -- re-fetches agent with new avatar_url (cache-busted)
      2. await loadAvatarIdentity() -- re-fetches identity prompt for modal
```

---

## Backend Layer

### Router: `src/backend/routers/avatar.py`

Registered in `src/backend/main.py:356`:
```python
app.include_router(avatar_router)  # Agent Avatars (AVATAR-001)
```

Prefix: `/api/agents`, Tags: `["avatars"]`

#### Endpoint: GET `/{agent_name}/avatar` (line 31)
- **Auth**: None (public asset)
- **Returns**: `FileResponse` with PNG from `/data/avatars/{agent_name}.png`
- **Cache**: `Cache-Control: public, max-age=86400` (24 hours)
- **Error**: 404 if no avatar file exists

#### Endpoint: GET `/{agent_name}/avatar/identity` (line 45)
- **Auth**: Required (access control check via `can_user_access_agent`)
- **Returns**: `{agent_name, identity_prompt, updated_at, has_avatar}`
- **Error**: 403 if user cannot access agent

#### Endpoint: POST `/{agent_name}/avatar/generate` (line 65)
- **Auth**: Required (owner or admin only)
- **Request Body**: `{identity_prompt: string}` (max 500 chars)
- **Flow**:
  1. Validate ownership (owner or admin, line 73-80)
  2. Validate prompt (non-empty, <= 500 chars, lines 82-87)
  3. Check image generation service availability (GEMINI_API_KEY, lines 89-94)
  4. Call `service.generate_image(prompt, use_case="avatar", aspect_ratio="1:1", refine_prompt=True, agent_name=agent_name)` (lines 96-102)
  5. Save PNG to `/data/avatars/{agent_name}.png` (lines 108-110)
  6. Update DB: `db.set_avatar_identity(agent_name, prompt, timestamp)` (lines 113-114)
- **Returns**: `{agent_name, identity_prompt, refined_prompt, updated_at}`
- **Errors**: 404 (not found), 403 (not owner), 400 (empty/too long), 501 (no API key), 422 (generation failed)

#### Endpoint: DELETE `/{agent_name}/avatar` (line 126)
- **Auth**: Required (owner or admin only)
- **Flow**:
  1. Validate ownership (lines 132-139)
  2. Delete file from `/data/avatars/{agent_name}.png` (lines 142-144)
  3. Clear DB: `db.clear_avatar_identity(agent_name)` (line 147)
- **Returns**: `{message: "Avatar removed for {agent_name}"}`

### Image Generation Pipeline

The avatar generation uses the shared image generation service (IMG-001):

**File**: `src/backend/services/image_generation_service.py`

1. **Prompt Refinement** (lines 122-128): Gemini 2.5 Flash (text model) rewrites the raw identity prompt using avatar-specific best practices
2. **Image Generation** (lines 131-156): Gemini 2.5 Flash Image generates the actual PNG

**Avatar-specific prompt engineering**: `src/backend/services/image_generation_prompts.py:166-225`

The avatar prompt (`AVATAR_BEST_PRACTICES`) uses a **consistency-through-extreme-specificity** approach:
- Preserves ALL character details from user's description exactly as given
- Appends a fixed technical specification block (verbatim) to every refined prompt
- Fixed spec defines: tight head-and-shoulders crop, centered, front-facing
- Background: warm dusty rose to cream gradient (fixed colors #D4A5A0 to #F0DDD0)
- Lighting: single soft key light upper-left 45deg, warm 3800K
- Color grading: Kodak Portra 400 film emulation, muted palette
- Lens: 85mm f/1.4, shallow DOF on background only
- Style: cinematic portrait photograph, photographic realism
- No text, no watermarks, no labels
- Circular crop safe (nothing important in corners)

### Avatar URL in Agent Data

Two code paths construct the `avatar_url` field:

1. **Single agent detail** (`src/backend/routers/agents.py:309-314`):
   ```python
   identity = db.get_avatar_identity(agent_name)
   if identity and identity.get("updated_at"):
       agent_dict["avatar_url"] = f"/api/agents/{agent_name}/avatar?v={identity['updated_at']}"
   ```

2. **Agent list (batch)** (`src/backend/services/agent_service/helpers.py:154-159`):
   ```python
   avatar_updated_at = metadata.get("avatar_updated_at")
   agent_dict["avatar_url"] = (
       f"/api/agents/{agent_name}/avatar?v={avatar_updated_at}"
       if avatar_updated_at else None
   )
   ```

### Avatar Cleanup on Agent Operations

**On Delete** (`src/backend/routers/agents.py:422-428`):
```python
avatar_path = Path("/data/avatars") / f"{agent_name}.png"
if avatar_path.exists():
    avatar_path.unlink()
```

**On Rename** (`src/backend/routers/agents.py:1511-1518`):
```python
old_avatar = Path("/data/avatars") / f"{agent_name}.png"
new_avatar = Path("/data/avatars") / f"{sanitized_name}.png"
if old_avatar.exists():
    old_avatar.rename(new_avatar)
```

### Configuration

```python
# src/backend/config.py:104
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
```

Avatar directory: `/data/avatars/` (created on first generate, bind-mounted from host)

---

## Data Layer

### Schema Changes

**Table**: `agent_ownership` (modified)

Two columns added by migration #24:

```sql
avatar_identity_prompt TEXT,  -- User's character description
avatar_updated_at TEXT         -- ISO timestamp for cache-busting
```

**File**: `src/backend/db/schema.py:65-66` (in CREATE TABLE definition)

### Migration #24

**File**: `src/backend/db/migrations.py:647-666`
**Function**: `_migrate_agent_avatar_columns(cursor, conn)`

```python
new_columns = [
    ("avatar_identity_prompt", "TEXT"),
    ("avatar_updated_at", "TEXT"),
]
# Uses ALTER TABLE ADD COLUMN (idempotent check via PRAGMA table_info)
```

### Database Operations

**File**: `src/backend/db/agents.py:802-845` (AgentOperations class)

| Method | Line | Description |
|--------|------|-------------|
| `set_avatar_identity(agent_name, prompt, updated_at)` | 806 | UPDATE agent_ownership SET avatar_identity_prompt, avatar_updated_at |
| `get_avatar_identity(agent_name)` | 818 | SELECT avatar_identity_prompt, avatar_updated_at |
| `clear_avatar_identity(agent_name)` | 834 | UPDATE SET NULL for both columns |

**Delegation**: `src/backend/database.py:418-425` delegates to `self._agent_ops`:
```python
def set_avatar_identity(self, agent_name, prompt, updated_at):
    return self._agent_ops.set_avatar_identity(agent_name, prompt, updated_at)
def get_avatar_identity(self, agent_name):
    return self._agent_ops.get_avatar_identity(agent_name)
def clear_avatar_identity(self, agent_name):
    return self._agent_ops.clear_avatar_identity(agent_name)
```

### Batch Query Integration

The `get_all_agent_metadata()` method (`src/backend/db/agents.py:846`) includes `avatar_updated_at` in its single-query result (line 880) to avoid N+1 queries on the agent list page.

---

## Side Effects

- **File System**: Avatar PNGs stored at `/data/avatars/{agent_name}.png`
- **No WebSocket**: Avatar changes do not broadcast WebSocket events (user refreshes to see update)
- **No Activity Tracking**: Avatar generation is not tracked as an agent activity
- **Cache-busting**: `?v={updated_at}` query param forces browser cache invalidation on re-generation

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Avatar file not found | 404 | "No avatar found" |
| Agent not in DB | 404 | "Agent not found" |
| User not owner/admin | 403 | "Only the agent owner can generate avatars" |
| User cannot access agent | 403 | "Access denied" |
| Empty prompt | 400 | "identity_prompt cannot be empty" |
| Prompt too long | 400 | "identity_prompt must be 500 characters or less" |
| No GEMINI_API_KEY | 501 | "Image generation not available: GEMINI_API_KEY not configured" |
| Generation failed | 422 | Error message from generation service |

---

## Testing

### Prerequisites
- Backend running at `http://localhost:8000`
- `GEMINI_API_KEY` configured in `.env`
- At least one agent created
- Logged in as agent owner or admin

### Test Steps

1. **Generate Avatar**
   **Action**: Navigate to agent detail, hover over avatar area (left edge of header), click camera icon, enter "a wise owl with spectacles", click Generate
   **Expected**: Modal shows spinner, then closes. Avatar appears in header with indigo ring border.
   **Verify**: `GET /api/agents/{name}/avatar` returns PNG. Avatar displays in agent list, dashboard nodes.

2. **Regenerate Avatar**
   **Action**: Click camera icon again, change prompt to "a friendly robot", click Generate
   **Expected**: New avatar replaces old one. Cache-busted URL forces browser refresh.
   **Verify**: File at `/data/avatars/{name}.png` updated. DB `avatar_updated_at` changed.

3. **Remove Avatar**
   **Action**: Open avatar modal, click "Remove Avatar"
   **Expected**: Avatar removed, fallback to gradient initials.
   **Verify**: File deleted. DB columns cleared. `avatar_url` is null in agent data.

4. **Fallback Display**
   **Action**: View agent without avatar
   **Expected**: Circular gradient with 2-letter initials (deterministic color from name)
   **Verify**: Same gradient color every time for same agent name.

5. **Avatar Survives Rename**
   **Action**: Rename agent from "my-agent" to "new-agent"
   **Expected**: Avatar file renamed from `my-agent.png` to `new-agent.png`
   **Verify**: Avatar still displays after rename.

6. **Avatar Cleaned Up on Delete**
   **Action**: Delete agent with avatar
   **Expected**: Avatar file removed from `/data/avatars/`
   **Verify**: File no longer exists.

7. **No API Key**
   **Action**: Remove GEMINI_API_KEY, try to generate avatar
   **Expected**: 501 error "Image generation not available"

8. **Non-Owner Cannot Generate**
   **Action**: View a shared agent as non-owner
   **Expected**: Camera icon overlay does not appear on hover. Avatar modal cannot be triggered.
   **Verify**: `agent.can_share` is false, camera overlay `v-if` hides it.

---

## Related Flows
- [image-generation.md](image-generation.md) - Shared Gemini image generation pipeline (IMG-001)
- [agent-lifecycle.md](agent-lifecycle.md) - Avatar cleanup on delete
- [agent-rename.md](agent-rename.md) - Avatar file rename on agent rename
- [agent-network.md](agent-network.md) - Avatar display in dashboard graph nodes
- [agents-page-ui-improvements.md](agents-page-ui-improvements.md) - Avatar in agent list rows
