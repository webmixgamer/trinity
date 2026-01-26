# Feature: File Browser (Tree Structure)

> **Updated**: 2026-01-23 - Verified line numbers and architecture. Frontend refactored to use `FilesPanel.vue` component with `useFileBrowser` composable. Protected path handling added to agent server.

## Revision History
| Date | Changes |
|------|---------|
| 2026-01-23 | Verified all line numbers. Updated frontend architecture (FilesPanel + composable). Documented protected paths (delete/edit). |
| 2025-12-30 | Updated line numbers. Service file grew from 137 to 413 lines. |
| 2025-12-27 | Service layer refactoring. File operations moved to `services/agent_service/files.py`. |
| 2025-12-06 | Agent-server modular refactoring (`agent_server/routers/files.py`). |
| 2025-12-01 | Initial tree structure implementation. |

## Overview
Users can browse and download files from agent workspaces through the Trinity web UI without requiring SSH access. The feature displays files in a **hierarchical tree structure** similar to macOS Finder, with expandable/collapsible folders. Users can navigate folder hierarchies, search files, and download individual files.

## User Story
As a Trinity user, I want to browse files in my agent's workspace using a familiar folder tree interface so that I can easily navigate directory structures and access agent-generated artifacts without needing SSH or Docker command-line access.

## Entry Points
- **UI**: `src/frontend/src/views/AgentDetail.vue:157-160` - "Files" tab content (FilesPanel component)
- **API**: `GET /api/agents/{agent_name}/files`
- **API**: `GET /api/agents/{agent_name}/files/download`
- **API**: `GET /api/agents/{agent_name}/files/preview`
- **API**: `DELETE /api/agents/{agent_name}/files`
- **API**: `PUT /api/agents/{agent_name}/files`

---

## Frontend Layer

### Architecture

The file browser uses a **component + composable** architecture:

| Layer | File | Purpose |
|-------|------|---------|
| View | `src/frontend/src/views/AgentDetail.vue:157-160` | Tab content (renders FilesPanel) |
| Component | `src/frontend/src/components/FilesPanel.vue` (130 lines) | File browser UI |
| Component | `src/frontend/src/components/FileTreeNode.vue` (141 lines) | Recursive tree node |
| Composable | `src/frontend/src/composables/useFileBrowser.js` (111 lines) | State and logic |
| Store | `src/frontend/src/stores/agents.js:452-478` | API calls |

### FilesPanel Component

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/components/FilesPanel.vue`

```vue
<!-- Line 157-160 in AgentDetail.vue -->
<div v-if="activeTab === 'files'">
  <FilesPanel :agent-name="agent.name" :agent-status="agent.status" />
</div>
```

**Features** (Lines 1-67):
- **Guard**: Shows "Agent must be running" message if status !== 'running' (Line 3-8)
- **Search Box**: `v-model="fileSearchQuery"` - filters files by name (Line 11-17)
- **Loading State**: Spinner while loading files (Line 21-27)
- **Error State**: Error message with retry button (Line 29-34)
- **Empty State**: "No files found in workspace" (Line 36-38)
- **File Tree**: Recursive FileTreeNode components (Line 52-62)

### FileTreeNode Component

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/components/FileTreeNode.vue`

Recursive component using Vue's `h()` render function (141 lines):

```javascript
// Line 13-21
export default defineComponent({
  name: 'FileTreeNode',
  props: {
    item: Object,           // Tree node (file or directory)
    depth: Number,          // Nesting level for indentation
    searchQuery: String,    // Current search query
    expandedFolders: Set   // Set of expanded folder paths
  },
  emits: ['toggle-folder', 'download'],
  // ...
})
```

**Features**:
- **Folders** (Line 35-88): Chevron icon (rotates when expanded), folder icon, file count badge
- **Files** (Line 89-136): File icon, name, size, download button (visible on hover)
- **Indentation**: 20px per depth level (Line 24, 93)
- **Recursion**: Renders children via self-reference (Line 75-87)

### useFileBrowser Composable

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/composables/useFileBrowser.js`

```javascript
// Line 7-13 - State
const fileTree = ref([])               // Hierarchical tree structure
const filesLoading = ref(false)
const filesError = ref(null)
const fileSearchQuery = ref('')
const expandedFolders = ref(new Set()) // Track which folders are open
const totalFileCount = ref(0)
```

**Functions**:
- `loadFiles()` (Line 51-65) - Fetches file tree from API
- `toggleFolder(path)` (Line 67-75) - Expands/collapses folder
- `downloadFile(filePath, fileName)` (Line 77-96) - Downloads file via blob
- `filteredFileTree` (Line 15-49) - Computed property for search filtering

### Store Actions

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/stores/agents.js`

#### listAgentFiles (Line 452-459)
```javascript
async listAgentFiles(name, path = '/home/developer', showHidden = false) {
  const authStore = useAuthStore()
  const response = await axios.get(`/api/agents/${name}/files`, {
    params: { path, show_hidden: showHidden },
    headers: authStore.authHeader
  })
  return response.data  // Returns: { tree: [...], total_files: N, show_hidden: bool }
}
```

#### downloadAgentFile (Line 461-469)
```javascript
async downloadAgentFile(name, filePath) {
  const authStore = useAuthStore()
  const response = await axios.get(`/api/agents/${name}/files/download`, {
    params: { path: filePath },
    headers: authStore.authHeader,
    responseType: 'text'
  })
  return response.data
}
```

#### deleteAgentFile (Line 471-478)
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

#### updateAgentFile (Line 480-488)
```javascript
async updateAgentFile(name, filePath, content) {
  const authStore = useAuthStore()
  const response = await axios.put(`/api/agents/${name}/files`, {
    content
  }, {
    params: { path: filePath },
    headers: authStore.authHeader
  })
  return response.data
}
```

---

## Backend Layer

### Architecture

The file browser feature uses a **thin router + service layer** architecture:

| Layer | File | Purpose |
|-------|------|---------|
| Router | `src/backend/routers/agents.py:500-569` | Endpoint definitions |
| Service | `src/backend/services/agent_service/files.py` (309 lines) | File listing, download, preview, delete, and update logic |

### Endpoints

#### GET /api/agents/{agent_name}/files

**Router**: `src/backend/routers/agents.py:500-514`
**Service**: `src/backend/services/agent_service/files.py:20-78`

**Purpose**: List all files in agent workspace as hierarchical tree structure

**Parameters**:
- `agent_name` (path) - Agent identifier
- `path` (query, optional) - Directory path (default: `/home/developer`)
- `show_hidden` (query, optional) - Include hidden files (default: `false`)

**Business Logic** (in `list_agent_files_logic()`):
1. Check user authentication (`get_current_user` dependency)
2. Verify user has access to agent (`db.can_user_access_agent()`)
3. Get agent container (`get_agent_container()`)
4. Verify container exists (404 if not)
5. Check container is running (400 if not)
6. Proxy request to agent's internal API at `http://agent-{name}:8000/api/files`
7. Return hierarchical tree JSON

**Response Format** (Tree Structure):
```json
{
  "base_path": "/home/developer",
  "requested_path": ".",
  "tree": [
    {
      "name": "scripts",
      "path": "scripts",
      "type": "directory",
      "file_count": 5,
      "modified": "2025-12-01T10:30:00",
      "children": [
        {
          "name": "deploy.sh",
          "path": "scripts/deploy.sh",
          "type": "file",
          "size": 1234,
          "modified": "2025-12-01T10:30:00"
        }
      ]
    },
    {
      "name": "README.md",
      "path": "README.md",
      "type": "file",
      "size": 5678,
      "modified": "2025-12-01T10:25:00"
    }
  ],
  "total_files": 6,
  "show_hidden": false
}
```

#### GET /api/agents/{agent_name}/files/download

**Router**: `src/backend/routers/agents.py:517-525`
**Service**: `src/backend/services/agent_service/files.py:81-131`

**Purpose**: Download file content from agent workspace

**Parameters**:
- `agent_name` (path) - Agent identifier
- `path` (query, required) - File path relative to workspace

**Business Logic** (in `download_agent_file_logic()`):
1. Check user authentication
2. Verify user has access to agent
3. Get agent container
4. Verify container exists and is running
5. Proxy request to agent's internal API at `http://agent-{name}:8000/api/files/download`
6. Return file content as PlainTextResponse

**Response**: Plain text content of the file

#### GET /api/agents/{agent_name}/files/preview

**Router**: `src/backend/routers/agents.py:528-536`
**Service**: `src/backend/services/agent_service/files.py:187-246`

**Purpose**: Get file with proper MIME type for preview (images, video, audio, etc.)

**Parameters**:
- `agent_name` (path) - Agent identifier
- `path` (query, required) - File path relative to workspace

**Response**: StreamingResponse with correct Content-Type header

#### DELETE /api/agents/{agent_name}/files

**Router**: `src/backend/routers/agents.py:539-547`
**Service**: `src/backend/services/agent_service/files.py:134-184`

**Purpose**: Delete a file or directory from agent workspace

**Parameters**:
- `agent_name` (path) - Agent identifier
- `path` (query, required) - File path to delete

**Protected Paths**: Cannot delete `CLAUDE.md`, `.trinity`, `.git`, `.gitignore`, `.env`, `.mcp.json`, `.mcp.json.template`

**Response**:
```json
{
  "success": true,
  "deleted": "path/to/file",
  "type": "file",
  "file_count": 1
}
```

#### PUT /api/agents/{agent_name}/files

**Router**: `src/backend/routers/agents.py:555-569`
**Service**: `src/backend/services/agent_service/files.py:249-308`

**Purpose**: Update a file's content in agent workspace

**Parameters**:
- `agent_name` (path) - Agent identifier
- `path` (query, required) - File path to update
- `body.content` (body, required) - New file content

**Protected Paths**: Cannot edit `.trinity`, `.git`, `.gitignore`, `.env`, `.mcp.json.template`
**Note**: `CLAUDE.md` and `.mcp.json` ARE editable since users need to modify them

**Response**:
```json
{
  "success": true,
  "path": "CLAUDE.md",
  "size": 1234,
  "modified": "2025-12-01T10:30:00.123456"
}
```

---

## Agent Layer

> **Architecture**: The agent-server uses a modular package structure at `docker/base-image/agent_server/`.

### Agent Server Endpoints

**File**: `/Users/eugene/Dropbox/trinity/trinity/docker/base-image/agent_server/routers/files.py` (370 lines)

#### GET /api/files (Line 23-109)

**Purpose**: Recursively list files in workspace directory as hierarchical tree

**Parameters**:
- `path` (query, optional) - Directory to list (default: `/home/developer`)
- `show_hidden` (query, optional) - Include hidden files (default: `false`)

**Security**:
- Only allows access to `/home/developer` and subdirectories
- Path traversal protection via `Path.resolve()` and prefix check
- Skips hidden files/directories unless `show_hidden=true`

**Business Logic**:
1. Resolve requested path and validate it's within workspace (Line 36-41)
2. Check path exists (404 if not) (Line 43-44)
3. Call recursive `build_tree(directory)` function (Line 46-94)
4. Return structured tree response (Line 96-109)

**build_tree() Function** (Line 46-94):
```python
def build_tree(directory: Path, base_path: Path, include_hidden: bool) -> dict:
    """Build a hierarchical tree structure from a directory."""
    items = []
    total_files = 0

    dir_items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

    for item in dir_items:
        if item.name.startswith('.') and not include_hidden:
            continue

        if item.is_dir():
            subtree = build_tree(item, base_path, include_hidden)  # Recursive
            items.append({
                "name": item.name,
                "path": str(relative_path),
                "type": "directory",
                "children": subtree["children"],
                "file_count": subtree["file_count"],
                "modified": timestamp
            })
            total_files += subtree["file_count"]
        else:
            items.append({
                "name": item.name,
                "path": str(relative_path),
                "type": "file",
                "size": stat.st_size,
                "modified": timestamp
            })
            total_files += 1

    return {"children": items, "file_count": total_files}
```

**Response**:
```json
{
    "base_path": "/home/developer",
    "requested_path": ".",
    "tree": [
        {
            "name": "scripts",
            "path": "scripts",
            "type": "directory",
            "file_count": 2,
            "modified": "2025-12-01T10:30:00.123456",
            "children": [...]
        },
        {
            "name": "example.txt",
            "path": "example.txt",
            "type": "file",
            "size": 1234,
            "modified": "2025-12-01T10:30:00.123456"
        }
    ],
    "total_files": 3,
    "show_hidden": false
}
```

#### GET /api/files/download (Line 112-153)

**Purpose**: Download file content as plain text

**Parameters**:
- `path` (query, required) - File path (absolute or relative to workspace)

**Security**:
- Only allows access to `/home/developer`
- Path traversal protection
- **Max file size: 100MB** (413 error if exceeded)
- Verifies path is a file (400 if directory)

**Business Logic**:
1. Handle both absolute and relative paths (Line 125-128)
2. Resolve path and validate workspace access (Line 130-132)
3. Check file exists (404 if not) (Line 134-135)
4. Verify it's a file, not directory (400 if directory) (Line 137-138)
5. Check file size <= 100MB (413 if too large) (Line 140-144)
6. Read file as UTF-8 text (with error replacement for binary) (Line 146-149)
7. Return as PlainTextResponse

**Response**: Plain text content

#### DELETE /api/files (Line 202-259)

**Purpose**: Delete a file or directory from workspace

**Parameters**:
- `path` (query, required) - File path to delete

**Protected Paths** (Line 157-165):
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

**Business Logic**:
1. Validate path is within workspace
2. Check not deleting home directory itself
3. Check path is not protected (403 if protected)
4. Delete file or directory recursively

#### GET /api/files/preview (Line 262-311)

**Purpose**: Get file with proper MIME type for preview

**Parameters**:
- `path` (query, required) - File path to preview

**Security**:
- Same as download (workspace restriction, 100MB limit)

**Business Logic**:
1. Validate path
2. Detect MIME type via `mimetypes.guess_type()`
3. Return FileResponse with correct Content-Type

#### PUT /api/files (Line 314-369)

**Purpose**: Update a file's content

**Parameters**:
- `path` (query, required) - File path to update
- `content` (body, required) - New file content

**Edit-Protected Paths** (Line 169-175):
```python
# CLAUDE.md and .mcp.json ARE editable since users need to modify them
EDIT_PROTECTED_PATHS = [
    ".trinity",
    ".git",
    ".gitignore",
    ".env",
    ".mcp.json.template",
]
```

**Business Logic**:
1. Validate path is within workspace
2. Check path is not edit-protected
3. Write new content as UTF-8
4. Return updated file info

**Error Handling** (all endpoints):
- 403: Access denied (outside workspace or protected path)
- 404: File not found
- 400: Not a file (is directory)
- 413: File too large (>100MB)
- 500: Read/write error

---

## Data Flow

### File List Request Flow
```
User clicks "Files" tab
  |
FilesPanel mounts / status watcher triggers
  |
loadFiles() called (useFileBrowser composable)
  |
agentsStore.listAgentFiles(name)
  |
GET /api/agents/{name}/files (backend router)
  |
list_agent_files_logic() - Authorization check (JWT + ownership)
  |
agent_http_request() - proxy to agent
  |
GET http://agent-{name}:8000/api/files (agent-server)
  |
build_tree() - Walk /home/developer recursively
  |
Filter hidden files/dirs (unless show_hidden=true)
  |
Collect metadata (name, path, size, modified)
  |
Return hierarchical tree JSON
  |
Display files in UI with search/filter
```

### File Download Flow
```
User clicks download icon
  |
downloadFile(path, name) called (useFileBrowser composable)
  |
agentsStore.downloadAgentFile(name, path)
  |
GET /api/agents/{name}/files/download?path=... (backend router)
  |
download_agent_file_logic() - Authorization check
  |
agent_http_request() - proxy to agent
  |
GET http://agent-{name}:8000/api/files/download?path=... (agent-server)
  |
Validate path within workspace
  |
Check file size <= 100MB
  |
Read file content (UTF-8 with error replacement)
  |
Return PlainTextResponse
  |
Create Blob in browser
  |
Trigger download via <a> element
  |
Show success notification
```

---

## Side Effects

### No Audit Logging
File browser operations are not currently logged to the audit system (removed during service layer refactoring).

### No Database Operations
The file browser (list, download, preview) is read-only and does not modify database tables.
The delete and update operations modify agent workspace files only (not database).

### No WebSocket Broadcasts
This feature does not emit real-time events.

---

## Error Handling

| Error Case | HTTP Status | Message | Where |
|------------|-------------|---------|-------|
| Agent not found | 404 | "Agent not found" | Backend |
| Agent not running | 400 | "Agent must be running to browse/download files" | Backend |
| Agent server not ready | 503 | "Agent server not ready. The agent may still be starting up." | Backend |
| No access permission | 403 | "You don't have permission to access this agent" | Backend |
| Path outside workspace | 403 | "Access denied: only /home/developer accessible" | Agent Server |
| Protected path (delete) | 403 | "Cannot delete protected path: {name}" | Agent Server |
| Protected path (edit) | 403 | "Cannot edit protected path: {name}" | Agent Server |
| Cannot delete home | 403 | "Cannot delete home directory" | Agent Server |
| File not found | 404 | "File not found: {path}" | Agent Server |
| Path is directory | 400 | "Not a file: {path}" | Agent Server |
| File too large | 413 | "File too large: {size} bytes (max 104857600)" | Agent Server |
| File read error | 500 | "Failed to read file: {error}" | Agent Server |
| Network timeout (list) | 504 | "File listing timed out" | Backend (30s) |
| Network timeout (download) | 504 | "File download timed out" | Backend (60s) |
| Network timeout (delete) | 504 | "File deletion timed out" | Backend (30s) |
| Network timeout (update) | 504 | "File update timed out" | Backend (60s) |
| Network timeout (preview) | 504 | "File preview timed out" | Backend (30s) |

---

## Security Considerations

### Authentication & Authorization
- JWT token required (Auth0)
- User must own agent OR be in shared_users list
- Checks performed at backend layer (not bypassed via agent-server)

### Path Traversal Prevention
- All paths resolved via `Path.resolve()`
- Prefix check: must start with `/home/developer`
- No access to system files, .env, .git, or other agent workspace directories

### File Access Restrictions
- Hidden files (.env, .git) skipped by default (use `show_hidden=true` to include)
- Hidden directories (.git, .vscode) not traversed by default
- Max file size: 100MB download/preview limit
- Only text file content for download (binary treated as text with error replacement)
- Preview endpoint returns files with proper MIME types

### Protected Path Handling
**Delete-Protected** (cannot be deleted):
- `CLAUDE.md`, `.trinity`, `.git`, `.gitignore`, `.env`, `.mcp.json`, `.mcp.json.template`

**Edit-Protected** (cannot be modified):
- `.trinity`, `.git`, `.gitignore`, `.env`, `.mcp.json.template`
- Note: `CLAUDE.md` and `.mcp.json` ARE editable since users need to modify them

### Rate Limiting
- Not currently implemented (consider for future if abuse occurs)
- Audit logging provides visibility for abuse detection

### Data Leakage Prevention
- Agent containers are network-isolated (only backend can access)
- Cannot access other agents' workspaces
- Error messages don't expose system paths

---

## Testing

### Prerequisites
1. Running Trinity platform (backend, frontend, agent containers)
2. Authenticated user with an agent (owned or shared)
3. Agent must be in "running" status

### Test Steps

#### 1. File List Display
**Action**: Navigate to agent detail page -> Click "Files" tab
**Expected**:
- Loading spinner appears briefly
- File list loads showing workspace contents
- Each file shows: name, path, size, modified time
- Folders show file count badge

#### 2. Search/Filter Files
**Action**: Type "test" in search box
**Expected**:
- File list filters in real-time
- Only files with "test" in name or path shown
- Counter updates (e.g., "5 file(s)")

#### 3. File Download
**Action**: Click download icon on a file
**Expected**:
- Browser downloads file with original filename
- Success notification appears
- File content matches workspace file

**Verify**:
```bash
# Compare downloaded file with agent workspace file
docker exec agent-{name} cat /home/developer/path/to/file.txt
```

#### 4. Stopped Agent Guard
**Action**: Stop agent, click "Files" tab
**Expected**:
- Empty state with message "Agent must be running to browse files"
- No API calls made
- No errors in console

#### 5. Large File Handling
**Action**: Create 101MB file in workspace, try to download
**Expected**:
- Download fails with error notification
- Error message mentions file size limit
- No browser hang or timeout

**Setup**:
```bash
docker exec agent-{name} dd if=/dev/zero of=/home/developer/large.bin bs=1M count=101
```

#### 6. Permission Checks
**Action**: Try to access agent owned by another user
**Expected**:
- Backend returns 403 Forbidden
- Error notification appears
- No file data exposed

### Edge Cases
- **Empty workspace**: Shows "No files found in workspace"
- **Hidden files**: .env, .git files not shown in list
- **Binary files**: Download works but content may be garbled (treated as text)
- **Network error**: Shows error with retry button
- **Path with spaces**: Handles correctly (URL encoding)

### Cleanup
```bash
# Remove test files
docker exec agent-{name} rm /home/developer/large.bin
```

### Status
Working - Feature tested and operational as of 2025-12-01

---

## Related Flows

### Upstream
- **Agent Lifecycle** - Agent must be running to browse files
- **Auth0 Authentication** - JWT required for API access
- **Agent Sharing** - Shared users can browse files too

### Downstream
- **Audit Logging** - All file operations logged for compliance
- None (read-only feature, no downstream dependencies)

### Similar Features
- **Agent Logs & Telemetry** - Also provides read-only agent data view
- **GitHub Sync** - Another way to extract agent workspace content

---

## Future Enhancements

### Implemented
- [x] **File Preview**: Preview endpoint with proper MIME types (images, video, audio, PDFs)
- [x] **File Delete**: Delete files and directories (with protected path handling)
- [x] **File Edit/Update**: Update file content (with edit-protected path handling)
- [x] **Show Hidden Files**: Toggle to include hidden files in listing

### Potential Improvements
1. **Upload Files**: Allow file upload to workspace
2. **Bulk Download**: Zip multiple files or entire directory
3. **Rename/Move Files**: Rename or move files within workspace
4. **Syntax Highlighting**: Code preview with language detection
5. **File Versioning**: Track file changes over time
6. **Remember expanded state**: Save which folders were expanded across sessions

### Performance Optimizations
- Pagination for workspaces with 1000+ files
- Virtual scrolling for long file lists
- Incremental loading (load on scroll)
- Cache file list for 30 seconds

### Security Enhancements
- Rate limiting per user/agent
- File type whitelist/blacklist
- Virus scanning for downloads
- Max total workspace size check

---

## Implementation Notes

### Why Plain Text?
- Simplifies implementation (no MIME type detection)
- Covers 90% of use cases (logs, code, configs)
- Browser can handle text encoding issues
- Future enhancement can add proper binary support

### Why 100MB Limit?
- Prevents memory issues in Python/JavaScript
- Protects against abuse (downloading GB files)
- Large files should use alternative methods (SSH, Docker cp)

### Why Skip Hidden Files (by default)?
- Prevents accidental exposure of secrets (.env)
- Reduces clutter in file list
- Git repositories (.git) can be huge
- `show_hidden=true` parameter available when needed
- FileManager view has a toggle to show hidden files

### Why Recursive Tree vs Flat List?
- **Hierarchical structure**: Mirrors actual filesystem organization
- **Familiar UX**: Similar to macOS Finder, Windows Explorer
- **Scalability**: Better for large workspaces (only show what's expanded)
- **Navigation**: Easy to drill down into specific directories
- **Visual clarity**: Indentation shows hierarchy at a glance

---

## Changelog

- **2026-01-23**: Verified all line numbers and updated documentation
  - Frontend refactored: FilesPanel component + useFileBrowser composable
  - FileTreeNode now in separate file (141 lines)
  - Backend router lines: 500-569 (was 551-619)
  - Service file: 309 lines (was 413)
  - Agent server: 370 lines with protected path handling
  - Added show_hidden parameter to file listing
  - Documented DELETE_PROTECTED_PATHS and EDIT_PROTECTED_PATHS

- **2025-12-30**: Updated line numbers to reflect current codebase. Service file grew from 137 to 413 lines (added update function). Fixed file paths.
- **2025-12-27**: **Service layer refactoring**: File operations moved to `services/agent_service/files.py`. Router reduced to thin endpoint definitions.
- **2025-12-06**: Updated agent-server references to new modular structure (`agent_server/routers/files.py`)
- **2025-12-06**: Updated line numbers for files endpoints (15-140 in modular file vs 1701-1842 in old monolithic)

- **2025-12-01 (PM)**: Tree structure implementation
  - Converted from flat file list to hierarchical tree structure
  - Added FileTreeNode recursive component using Vue h() render function
  - Implemented expand/collapse functionality with chevron icons
  - Added folder file count badges
  - Auto-expand folders during search
  - Track expanded state with Set-based storage
  - Modified agent-server build_tree() for recursive tree building
  - Folders collapsed by default, 20px indentation per level
  - Download button visible on hover for files

- **2025-12-01 (AM)**: Initial flat list implementation
  - Added Files tab to AgentDetail.vue
  - Implemented backend proxy endpoints
  - Added agent-server file listing/download APIs (flat structure)
  - Added audit logging for file operations
  - Created feature flow documentation
