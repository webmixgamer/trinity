# Feature: File Manager (Standalone Page)

> **Created**: 2025-12-27 - Phase 11.5, Requirement 12.2
>
> **Related**: [file-browser.md](file-browser.md) - Original in-agent file browser (Files tab in AgentDetail)

## Overview

The File Manager is a **dedicated standalone page** (`/files` route) providing a two-panel interface for browsing, previewing, and managing files across all running agents. Unlike the Files tab in AgentDetail (which is agent-specific), the File Manager allows quick switching between agents and supports rich media previews (images, video, audio, PDF) plus file deletion with protected path warnings.

## User Story

As a Trinity user, I want to manage files across all my running agents from a single page so that I can quickly browse, preview, download, and delete files without navigating to each agent's detail page.

## Entry Points

- **UI**: `src/frontend/src/views/FileManager.vue` - Standalone page at `/files` route
- **Router**: `src/frontend/src/router/index.js:42-46` - Route definition
- **API Endpoints**:
  - `GET /api/agents/{agent_name}/files` - List files
  - `GET /api/agents/{agent_name}/files/preview` - Preview with MIME type
  - `DELETE /api/agents/{agent_name}/files` - Delete file/folder

---

## Frontend Layer

### Router Configuration

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/router/index.js`

```javascript
// Line 42-46
{
  path: '/files',
  name: 'FileManager',
  component: () => import('../views/FileManager.vue'),
  meta: { requiresAuth: true }
}
```

### Main Component

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/views/FileManager.vue` (494 lines)

#### Component Structure

```
FileManager.vue
  |-- Header: Agent selector dropdown + Refresh button
  |-- Notification Banner (success/error messages)
  |-- Two-Panel Layout:
  |     |-- Left Panel (w-80): File Tree Browser
  |     |     |-- Search input
  |     |     |-- FileTreeNode components (recursive)
  |     |     |-- Footer stats (file count, total size)
  |     |
  |     |-- Right Panel (flex-1): File Preview
  |           |-- FilePreview component
  |           |-- File Info & Actions (download, delete buttons)
  |
  |-- Delete Confirmation Modal
```

#### State Management (Lines 241-270)

```javascript
// Component state
const selectedAgentName = ref(localStorage.getItem('fileManager.selectedAgent') || '')
const fileTree = ref([])
const selectedFile = ref(null)
const searchQuery = ref('')
const loading = ref(false)
const error = ref(null)
const previewData = ref(null)
const previewLoading = ref(false)
const previewError = ref(null)
const downloading = ref(false)
const deleting = ref(false)
const showDeleteConfirm = ref(false)
```

#### Protected Paths (Line 273)

```javascript
const PROTECTED_PATHS = ['CLAUDE.md', '.trinity', '.git', '.gitignore', '.env', '.mcp.json', '.mcp.json.template']
```

#### Agent Selector (Lines 10-26)

- Dropdown shows only running agents (`agentsStore.runningAgents`)
- Selection persisted to `localStorage.fileManager.selectedAgent`
- Auto-loads files on agent change

#### Search/Filter (Lines 74-86, 302-322)

```javascript
const filteredTree = computed(() => {
  if (!searchQuery.value) return fileTree.value

  const query = searchQuery.value.toLowerCase()
  const filterItems = (items) => {
    const result = []
    for (const item of items) {
      const matches = item.name.toLowerCase().includes(query)
      if (item.type === 'directory') {
        const filteredChildren = filterItems(item.children || [])
        if (matches || filteredChildren.length > 0) {
          result.push({ ...item, children: filteredChildren, expanded: true })
        }
      } else if (matches) {
        result.push(item)
      }
    }
    return result
  }
  return filterItems(fileTree.value)
})
```

#### Key Methods

| Method | Lines | Purpose |
|--------|-------|---------|
| `loadFiles()` | 331-345 | Fetch file tree from agent |
| `onAgentChange()` | 347-352 | Handle agent selection, clear state |
| `onFileSelect()` | 354-362 | Select file and load preview |
| `loadPreview()` | 364-375 | Fetch file preview as blob |
| `downloadFile()` | 377-409 | Download file via blob URL |
| `deleteFile()` | 411-434 | Delete file/folder after confirmation |

#### Protected Path Check (Lines 324-328)

```javascript
const isProtectedPath = computed(() => {
  if (!selectedFile.value) return false
  const name = selectedFile.value.name
  return PROTECTED_PATHS.includes(name)
})
```

When a protected file is selected, the Delete button is disabled with tooltip "Protected file cannot be deleted" and a warning message appears.

### FileTreeNode Component

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/components/file-manager/FileTreeNode.vue` (186 lines)

#### Props

```javascript
const props = defineProps({
  item: { type: Object, required: true },
  selectedPath: { type: String, default: null },
  searchQuery: { type: String, default: '' }
})
```

#### File Type Icons (Lines 93-113)

Maps file extensions to icon components:

| Category | Extensions | Icon | Color |
|----------|------------|------|-------|
| Directory | - | FolderIcon/FolderOpenIcon | yellow-500 |
| Video | mp4, webm, mov, avi, mkv | FilmIcon | purple-500 |
| Audio | mp3, wav, ogg, m4a, flac, aac | MusicalNoteIcon | green-500 |
| Image | jpg, jpeg, png, gif, webp, svg, ico, bmp | PhotoIcon | blue-500 |
| Code | js, ts, py, go, vue, css, html, etc. | CodeBracketIcon | gray-500 |
| PDF | pdf | DocumentIcon | red-500 |
| Text | txt, md, json, yaml, sh, etc. | DocumentTextIcon | gray-400 |

#### Expand/Collapse Behavior

- Folders start collapsed
- Click folder row to toggle expansion
- Search auto-expands matching folders
- Chevron rotates 90 degrees when expanded

### FilePreview Component

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/components/file-manager/FilePreview.vue` (230 lines)

#### Props

```javascript
const props = defineProps({
  file: { type: Object, required: true },
  agentName: { type: String, required: true },
  previewData: { type: Object, default: null },
  previewLoading: { type: Boolean, default: false },
  previewError: { type: String, default: null }
})
```

#### File Type Detection (Lines 148-201)

```javascript
const isImage = computed(() => {
  const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'ico', 'bmp']
  const mimeMatch = props.previewData.type?.startsWith('image/')
  return imageExts.includes(ext) || mimeMatch
})

const isVideo = computed(() => { /* mp4, webm, mov, avi, mkv */ })
const isAudio = computed(() => { /* mp3, wav, ogg, m4a, flac, aac */ })
const isPdf = computed(() => { /* pdf */ })
const isText = computed(() => { /* txt, md, json, js, py, etc. */ })
```

#### Preview Types

| Type | Component | Features |
|------|-----------|----------|
| Directory | Folder icon + item count | Shows folder info |
| Image | `<img>` | Max size constraints, shows dimensions |
| Video | `<video controls>` | Native player controls |
| Audio | `<audio controls>` | Centered card with icon |
| PDF | `<embed type="application/pdf">` | Full-height embedded viewer |
| Text/Code | `<pre><code>` | Monospace font, dark theme |
| Unknown | Document icon | "Preview not available" message |

#### Text Content Loading (Lines 204-216)

```javascript
watch(() => props.previewData, async (data) => {
  if (data && isText.value) {
    try {
      const response = await fetch(data.url)
      textContent.value = await response.text()
    } catch (e) {
      textContent.value = 'Failed to load text content'
    }
  }
}, { immediate: true })
```

### Store Actions

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/stores/agents.js`

#### listAgentFiles (Lines 371-378)

```javascript
async listAgentFiles(name, path = '/home/developer') {
  const authStore = useAuthStore()
  const response = await axios.get(`/api/agents/${name}/files`, {
    params: { path },
    headers: authStore.authHeader
  })
  return response.data
}
```

#### deleteAgentFile (Lines 390-397)

```javascript
async deleteAgentFile(name, filePath) {
  const authStore = useAuthStore()
  const response = await axios.delete(`/api/agents/${name}/files`, {
    params: { path: filePath },
    headers: authStore.authHeader
  })
  return response.data
}
```

#### getFilePreviewBlob (Lines 399-412)

```javascript
async getFilePreviewBlob(name, filePath) {
  const authStore = useAuthStore()
  const response = await axios.get(`/api/agents/${name}/files/preview`, {
    params: { path: filePath },
    headers: authStore.authHeader,
    responseType: 'blob'
  })
  return {
    url: URL.createObjectURL(response.data),
    type: response.data.type,
    size: response.data.size
  }
}
```

---

## Backend Layer

### Architecture

| Layer | File | Purpose |
|-------|------|---------|
| Router | `src/backend/routers/agents.py:549-590` | Endpoint definitions |
| Service | `src/backend/services/agent_service/files.py` (287 lines) | File operations logic |

### Endpoints

#### GET /api/agents/{agent_name}/files

**Router**: `src/backend/routers/agents.py:549-557`
**Service**: `src/backend/services/agent_service/files.py:20-77`

See [file-browser.md](file-browser.md) for full documentation.

#### GET /api/agents/{agent_name}/files/preview

**Router**: `src/backend/routers/agents.py:571-579`

```python
@router.get("/{agent_name}/files/preview")
async def preview_agent_file_endpoint(
    agent_name: str,
    request: Request,
    path: str,
    current_user: User = Depends(get_current_user)
):
    """Get file with proper MIME type for preview (images, video, audio, etc.)."""
    return await preview_agent_file_logic(agent_name, path, current_user, request)
```

**Service**: `src/backend/services/agent_service/files.py:204-287`

```python
async def preview_agent_file_logic(
    agent_name: str,
    path: str,
    current_user: User,
    request: Request
) -> StreamingResponse:
    """Get file with proper MIME type for preview."""
    # 1. Check user access permission
    # 2. Get and verify agent container is running
    # 3. Proxy to agent's /api/files/preview endpoint
    # 4. Stream response with correct Content-Type
    # 5. Log audit event
```

**Business Logic**:
1. Check user authentication and agent access permission
2. Get agent container and verify it's running
3. Proxy request to agent's internal API
4. Stream response back with correct MIME type
5. Log audit event (`file_preview` action)

**Response**: `StreamingResponse` with proper `Content-Type` header

#### DELETE /api/agents/{agent_name}/files

**Router**: `src/backend/routers/agents.py:582-590`

```python
@router.delete("/{agent_name}/files")
async def delete_agent_file_endpoint(
    agent_name: str,
    request: Request,
    path: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a file or directory from the agent's workspace."""
    return await delete_agent_file_logic(agent_name, path, current_user, request)
```

**Service**: `src/backend/services/agent_service/files.py:140-201`

```python
async def delete_agent_file_logic(
    agent_name: str,
    path: str,
    current_user: User,
    request: Request
) -> dict:
    """Delete a file or directory from the agent's workspace."""
    # 1. Check user access permission
    # 2. Get and verify agent container is running
    # 3. Proxy DELETE to agent's /api/files endpoint
    # 4. Log audit event with file type and count
```

**Response**:
```json
{
  "success": true,
  "deleted": "path/to/file",
  "type": "file",  // or "directory"
  "file_count": 1  // number of files deleted (for directories)
}
```

---

## Agent Layer

**File**: `/Users/eugene/Dropbox/trinity/trinity/docker/base-image/agent_server/routers/files.py`

### GET /api/files/preview (Lines 229-279)

```python
@router.get("/api/files/preview")
async def preview_file(path: str):
    """Get file with proper MIME type for preview."""
    # Security: Only allow /home/developer access
    # Max file size: 100MB
    # Detect MIME type with mimetypes.guess_type()
    # Return FileResponse with correct media_type
```

**Features**:
- MIME type detection via `mimetypes.guess_type()`
- 100MB file size limit
- Path security (only `/home/developer`)
- Returns `FileResponse` for efficient streaming

### DELETE /api/files (Lines 169-226)

```python
@router.delete("/api/files")
async def delete_file(path: str):
    """Delete a file or directory from the workspace."""
    # Security checks
    # Protected path check
    # Recursive directory deletion with shutil.rmtree()
    # Single file deletion with Path.unlink()
```

**Protected Paths** (Lines 146-154):
```python
PROTECTED_PATHS = [
    "CLAUDE.md",
    ".trinity",
    ".git",
    ".gitignore",
    ".env",
    ".mcp.json",
    ".mcp.json.template",
]
```

**_is_protected_path()** (Lines 157-166):
```python
def _is_protected_path(path: Path) -> bool:
    """Check if path is a protected file/directory."""
    for protected in PROTECTED_PATHS:
        if path.name == protected:
            return True
        # Check parent directories too
        for parent in path.parents:
            if parent.name == protected:
                return True
    return False
```

---

## Data Flow

### File Tree Loading

```
User selects agent from dropdown
  |
onAgentChange() -> localStorage.setItem + loadFiles()
  |
agentsStore.listAgentFiles(name)
  |
GET /api/agents/{name}/files (backend)
  |
Authorization check (JWT + ownership)
  |
GET http://agent-{name}:8000/api/files (agent-server)
  |
Recursive directory traversal
  |
Return hierarchical tree JSON
  |
Render FileTreeNode components
```

### File Preview Loading

```
User clicks file in tree
  |
onFileSelect(item) -> selectedFile = item
  |
loadPreview(file)
  |
agentsStore.getFilePreviewBlob(name, path)
  |
GET /api/agents/{name}/files/preview (backend)
  |
GET http://agent-{name}:8000/api/files/preview (agent)
  |
Return file with Content-Type header
  |
Create blob URL (URL.createObjectURL)
  |
Render appropriate preview component
```

### File Deletion

```
User clicks Delete button
  |
showDeleteConfirm = true (modal opens)
  |
User confirms deletion
  |
deleteFile()
  |
agentsStore.deleteAgentFile(name, path)
  |
DELETE /api/agents/{name}/files?path=... (backend)
  |
DELETE http://agent-{name}:8000/api/files?path=... (agent)
  |
Protected path check (403 if protected)
  |
Directory: shutil.rmtree() / File: path.unlink()
  |
Return { success, deleted, type, file_count }
  |
Audit log: file_delete
  |
Refresh file tree
  |
Show success notification
```

---

## Side Effects

### Audit Logs

| Action | Event Type | Details |
|--------|------------|---------|
| `file_list` | `file_access` | `{"path": "/home/developer"}` |
| `file_preview` | `file_access` | `{"file_path": "...", "content_type": "..."}` |
| `file_delete` | `file_access` | `{"path": "...", "type": "file/directory", "file_count": N}` |

### Local Storage

```javascript
localStorage.setItem('fileManager.selectedAgent', agentName)
```

Persists selected agent across page reloads.

### Blob URL Cleanup

```javascript
onUnmounted(() => {
  if (previewData.value?.url) {
    URL.revokeObjectURL(previewData.value.url)
  }
})
```

Prevents memory leaks from blob URLs.

---

## Error Handling

| Error Case | HTTP Status | Message | Location |
|------------|-------------|---------|----------|
| Agent not found | 404 | "Agent not found" | Backend |
| Agent not running | 400 | "Agent must be running" | Backend |
| No permission | 403 | "You don't have permission to access this agent" | Backend |
| Path outside workspace | 403 | "Access denied: only /home/developer accessible" | Agent |
| Protected path | 403 | "Cannot delete protected path: {name}" | Agent |
| Cannot delete home | 403 | "Cannot delete home directory" | Agent |
| File not found | 404 | "File not found: {path}" | Agent |
| Not a file (preview) | 400 | "Not a file: {path}" | Agent |
| File too large | 413 | "File too large: {size} bytes (max 104857600)" | Agent |
| Timeout (list) | 504 | "File listing timed out" | Backend (30s) |
| Timeout (delete) | 504 | "File deletion timed out" | Backend (30s) |
| Timeout (preview) | 504 | "File preview timed out" | Backend (120s) |

---

## Security Considerations

### Authentication & Authorization

- JWT token required (Auth0 or dev mode)
- User must own agent OR be in shared_users list
- All checks performed at backend layer

### Path Traversal Prevention

- All paths resolved via `Path.resolve()`
- Prefix check: must start with `/home/developer`
- No access to system files outside workspace

### Protected File Deletion Prevention

Agent-level protection for critical files:
- `CLAUDE.md` - Agent instructions
- `.trinity/` - Trinity configuration
- `.git/` - Version control
- `.gitignore` - Git configuration
- `.env` - Environment secrets
- `.mcp.json` - MCP configuration
- `.mcp.json.template` - MCP template

UI-level protection:
- Delete button disabled for protected paths
- Warning message displayed when protected file selected

### File Size Limits

- 100MB maximum for preview and download
- Prevents memory exhaustion attacks
- Large files should use SSH/Docker cp

### Hidden File Visibility

- Hidden files (starting with `.`) skipped in tree listing
- Prevents accidental exposure of secrets

---

## Testing

### Prerequisites

1. Running Trinity platform (backend, frontend, agents)
2. Authenticated user with at least one running agent
3. Agent with files in `/home/developer`

### Test Steps

#### 1. Navigate to File Manager

**Action**: Click "Files" in navigation menu or go to `/files`

**Expected**:
- File Manager page loads
- Agent dropdown shows running agents
- "Select an agent" placeholder if no agent selected

#### 2. Select Agent and Browse

**Action**: Select an agent from dropdown

**Expected**:
- File tree loads in left panel
- Folders show with expand arrows
- Files show with type-appropriate icons
- Footer shows file count and total size

#### 3. Search/Filter Files

**Action**: Type search term in search box

**Expected**:
- Tree filters to show matching items
- Matching folders auto-expand
- Matching names highlighted (yellow background)
- Clear search restores full tree

#### 4. Preview Different File Types

**Action**: Click various file types

| File Type | Expected Preview |
|-----------|------------------|
| Image (png, jpg) | Inline image with dimensions |
| Video (mp4) | Video player with controls |
| Audio (mp3) | Audio player in card |
| PDF | Embedded PDF viewer |
| Code (js, py) | Syntax-highlighted code |
| Text (md, txt) | Plain text in monospace |
| Unknown | "Preview not available" |

#### 5. Download File

**Action**: Click Download button on selected file

**Expected**:
- File downloads with original filename
- Success notification appears

#### 6. Delete File (Non-Protected)

**Action**: Select non-protected file -> Click Delete -> Confirm

**Expected**:
- Confirmation modal appears with file name
- File removed from tree after confirmation
- Success notification shows

#### 7. Protected File Warning

**Action**: Select a protected file (CLAUDE.md, .env, etc.)

**Expected**:
- Delete button is disabled
- Warning message: "This is a protected system file and cannot be deleted"

#### 8. Delete Folder

**Action**: Select folder with files -> Delete -> Confirm

**Expected**:
- Modal shows "This will delete all X files inside"
- Folder and contents removed
- File count updated

#### 9. Agent No Longer Running

**Action**: Stop selected agent while on File Manager page

**Expected**:
- Error notification: "Agent X is no longer running"
- Agent deselected, tree cleared
- Empty state shown

### Edge Cases

- **Empty workspace**: Shows "This folder is empty"
- **Large files (>100MB)**: Preview/download fails with 413 error
- **Binary files**: Shows "Preview not available"
- **Deep nesting**: Tree handles arbitrary depth
- **Special characters in names**: Properly escaped

### Cleanup

```bash
# Remove test files if created
docker exec agent-{name} rm -rf /home/developer/test-dir
```

### Status

Working - Feature implemented and tested 2025-12-27

---

## Related Flows

### Upstream

- **Agent Lifecycle** - Agents must be running to browse files
- **Auth0 Authentication** - JWT required for all API calls
- **Agent Sharing** - Shared users can access files

### Downstream

- **Audit Logging** - All file operations logged
- **File Browser (AgentDetail)** - Similar functionality, single-agent context

### Comparison with File Browser Tab

| Feature | File Manager (`/files`) | Files Tab (AgentDetail) |
|---------|-------------------------|------------------------|
| Location | Standalone page | Tab in agent detail |
| Agent scope | All running agents | Single agent |
| Agent selector | Dropdown | N/A (implicit) |
| File preview | Rich media support | Download only |
| Delete support | Yes, with confirmation | No |
| Protected warnings | Yes | No |
| Persistence | localStorage agent | N/A |

---

## Changelog

- **2025-12-27**: Initial implementation (Phase 11.5, Requirement 12.2)
  - Standalone File Manager page at `/files`
  - Two-panel layout with agent selector
  - FileTreeNode recursive component with file type icons
  - FilePreview component with image/video/audio/PDF/text support
  - Delete operations with confirmation modal
  - Protected file warnings (CLAUDE.md, .trinity, .git, .env, etc.)
  - Backend preview and delete endpoints
  - Agent server preview and delete handlers
  - Search/filter with auto-expand
  - localStorage agent persistence
