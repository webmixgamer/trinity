# Implementation Plan: Database Batch Queries (N+1 Fix)

> **Priority**: HIGH
> **Estimated Impact**: 120-180 queries → 2-3 queries per request
> **Dependencies**: None (can be done in parallel with Docker stats fix)
> **Related Issue**: N+1 query problem in `get_accessible_agents()`

---

## Problem Summary

The `get_accessible_agents()` function makes **8-10 separate database queries per agent**:

```python
# Current flow (simplified):
def get_accessible_agents(current_user: User) -> list:
    all_agents = list_all_agents()                    # Docker call
    user_data = db.get_user_by_username(...)          # 1 query

    for agent in all_agents:                          # N iterations
        db.can_user_access_agent(...)                 # 2-3 queries
        db.get_agent_owner(...)                       # 1 query
        db.is_agent_shared_with_user(...)             # 2 queries
        db.get_autonomy_enabled(...)                  # 1 query
        db.get_git_config(...)                        # 1 query
        db.get_resource_limits(...)                   # 1 query
```

**Impact**: 20 agents × 9 queries = **180 database queries** per request

---

## Solution: Batch Query with Single JOIN

Replace per-agent queries with a single query that fetches all metadata at once.

---

## Implementation Steps

### Step 1: Add Batch Metadata Function

**File**: `src/backend/db/agents.py`

Add a new method to `AgentOperations` class:

```python
def get_all_agent_metadata(self, user_email: str = None) -> Dict[str, Dict]:
    """
    Fetch all agent metadata in a SINGLE query.

    This eliminates the N+1 query problem by joining all related tables
    and returning a dict keyed by agent_name.

    Args:
        user_email: Current user's email for checking share access

    Returns:
        Dict mapping agent_name to metadata dict containing:
        - owner_id, owner_username, owner_email
        - is_system, autonomy_enabled
        - memory_limit, cpu_limit
        - github_repo
        - is_shared_with_user (bool)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Single query that joins all needed tables
        cursor.execute("""
            SELECT
                ao.agent_name,
                ao.owner_id,
                u.username as owner_username,
                u.email as owner_email,
                COALESCE(ao.is_system, 0) as is_system,
                COALESCE(ao.autonomy_enabled, 0) as autonomy_enabled,
                COALESCE(ao.use_platform_api_key, 1) as use_platform_api_key,
                ao.memory_limit,
                ao.cpu_limit,
                gc.github_repo,
                gc.github_branch,
                CASE
                    WHEN s.id IS NOT NULL THEN 1
                    ELSE 0
                END as is_shared_with_user
            FROM agent_ownership ao
            LEFT JOIN users u ON ao.owner_id = u.id
            LEFT JOIN git_configs gc ON gc.agent_name = ao.agent_name
            LEFT JOIN agent_sharing s ON s.agent_name = ao.agent_name
                AND LOWER(s.shared_with_email) = LOWER(?)
        """, (user_email or '',))

        result = {}
        for row in cursor.fetchall():
            result[row["agent_name"]] = {
                "owner_id": row["owner_id"],
                "owner_username": row["owner_username"],
                "owner_email": row["owner_email"],
                "is_system": bool(row["is_system"]),
                "autonomy_enabled": bool(row["autonomy_enabled"]),
                "use_platform_api_key": bool(row["use_platform_api_key"]),
                "memory_limit": row["memory_limit"],
                "cpu_limit": row["cpu_limit"],
                "github_repo": row["github_repo"],
                "github_branch": row["github_branch"],
                "is_shared_with_user": bool(row["is_shared_with_user"]),
            }

        return result
```

---

### Step 2: Update get_accessible_agents()

**File**: `src/backend/services/agent_service/helpers.py`

Rewrite to use the batch query:

```python
def get_accessible_agents(current_user: User) -> list:
    """
    Get list of all agents accessible to the current user.

    OPTIMIZED: Uses batch query to fetch all metadata in 2 queries total
    instead of 8-10 queries per agent (N+1 problem fix).
    """
    # Fast Docker call (no stats) - see Docker stats optimization plan
    all_agents = list_all_agents_fast()

    # Single query for user info
    user_data = db.get_user_by_username(current_user.username)
    if not user_data:
        return []

    is_admin = user_data["role"] == "admin"
    user_email = user_data.get("email")

    # SINGLE batch query for ALL agent metadata
    all_metadata = db.get_all_agent_metadata(user_email)

    accessible_agents = []
    for agent in all_agents:
        agent_dict = agent.dict() if hasattr(agent, 'dict') else dict(agent)
        agent_name = agent_dict.get("name")

        # Get metadata from batch result (not individual query)
        metadata = all_metadata.get(agent_name, {})

        # Access control check using batch data
        owner_username = metadata.get("owner_username")
        is_owner = owner_username == current_user.username
        is_shared = bool(metadata.get("is_shared_with_user"))

        # Skip if no access
        if not (is_admin or is_owner or is_shared):
            continue

        # Populate agent dict from batch metadata
        agent_dict["owner"] = owner_username
        agent_dict["is_owner"] = is_owner
        agent_dict["is_shared"] = is_shared and not is_owner and not is_admin
        agent_dict["is_system"] = metadata.get("is_system", False)
        agent_dict["autonomy_enabled"] = metadata.get("autonomy_enabled", False)
        agent_dict["github_repo"] = metadata.get("github_repo")
        agent_dict["memory_limit"] = metadata.get("memory_limit")
        agent_dict["cpu_limit"] = metadata.get("cpu_limit")

        accessible_agents.append(agent_dict)

    return accessible_agents
```

---

### Step 3: Handle Orphaned Agents

Agents that exist in Docker but not in the database (orphaned containers) need handling:

```python
# In get_accessible_agents():

# For agents not in metadata (orphaned - exist in Docker but not DB)
if not metadata:
    # Only admin can see orphaned agents
    if not is_admin:
        continue
    # Show with minimal info
    agent_dict["owner"] = None
    agent_dict["is_owner"] = False
    agent_dict["is_shared"] = False
    agent_dict["is_system"] = False
    agent_dict["autonomy_enabled"] = False
    agent_dict["github_repo"] = None
    agent_dict["memory_limit"] = None
    agent_dict["cpu_limit"] = None
```

---

### Step 4: Export New Function

**File**: `src/backend/database.py`

Ensure the new method is accessible via the `db` singleton:

```python
# In DatabaseOperations class or wherever db methods are exposed
# The method is already on AgentOperations which db inherits/composes
```

---

## Files to Modify

| File | Change |
|------|--------|
| `src/backend/db/agents.py` | Add `get_all_agent_metadata()` method |
| `src/backend/services/agent_service/helpers.py` | Rewrite `get_accessible_agents()` to use batch |

---

## Database Schema Reference

The batch query joins these tables:

```sql
-- agent_ownership (main table)
CREATE TABLE agent_ownership (
    id INTEGER PRIMARY KEY,
    agent_name TEXT UNIQUE NOT NULL,
    owner_id INTEGER REFERENCES users(id),
    is_system INTEGER DEFAULT 0,
    autonomy_enabled INTEGER DEFAULT 0,
    use_platform_api_key INTEGER DEFAULT 1,
    memory_limit TEXT,
    cpu_limit TEXT,
    created_at TEXT
);

-- users (for owner info)
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    email TEXT,
    role TEXT DEFAULT 'user'
);

-- git_configs (for GitHub repo)
CREATE TABLE git_configs (
    id INTEGER PRIMARY KEY,
    agent_name TEXT UNIQUE,
    github_repo TEXT,
    github_branch TEXT DEFAULT 'main'
);

-- agent_sharing (for share access)
CREATE TABLE agent_sharing (
    id INTEGER PRIMARY KEY,
    agent_name TEXT,
    shared_with_email TEXT,
    shared_by_id INTEGER,
    UNIQUE(agent_name, shared_with_email)
);
```

---

## Testing Plan

### Query Count Verification

Add temporary logging to count queries:

```python
# Temporary - add to get_db_connection()
import threading
_query_count = threading.local()

def get_db_connection():
    if not hasattr(_query_count, 'count'):
        _query_count.count = 0
    _query_count.count += 1
    logger.debug(f"DB connection #{_query_count.count}")
    # ... rest of function

def reset_query_count():
    _query_count.count = 0

def get_query_count():
    return getattr(_query_count, 'count', 0)
```

### Before Implementation

```bash
# With 20 agents, count queries
curl http://localhost:8000/api/agents -H "Authorization: Bearer $TOKEN"
# Check logs: Should see 120-180+ "DB connection" messages
```

### After Implementation

```bash
# Same request
curl http://localhost:8000/api/agents -H "Authorization: Bearer $TOKEN"
# Check logs: Should see only 2-3 "DB connection" messages
```

### Functional Tests

1. **Admin sees all agents**: Login as admin, verify all agents visible
2. **Owner sees own agents**: Login as user, verify only owned agents visible
3. **Shared agents visible**: Share agent with user, verify they can see it
4. **Metadata correct**: Verify owner, github_repo, autonomy_enabled all correct
5. **Orphaned agents**: Create container manually, verify only admin sees it

---

## Performance Comparison

| Metric | Before | After |
|--------|--------|-------|
| Queries per request | 120-180 | 2-3 |
| SQLite connections | 120-180 | 2-3 |
| Response time (DB portion) | ~500ms | ~10ms |

---

## Edge Cases

### 1. No Agents Exist
- Batch query returns empty dict
- Loop doesn't iterate
- Returns empty list

### 2. User Has No Access to Any Agent
- Batch query includes share check
- All agents filtered out
- Returns empty list

### 3. Agent Exists in Docker but Not DB
- Not in batch result
- Only visible to admin
- Shows with null metadata

### 4. User Email is Null
- Pass empty string to batch query
- is_shared_with_user = 0 for all
- Only owned agents visible

---

## Rollback Plan

If issues arise, revert `helpers.py` to original per-agent queries:

```python
# Restore original implementation
for agent in all_agents:
    if not db.can_user_access_agent(current_user.username, agent_name):
        continue
    owner = db.get_agent_owner(agent_name)
    # ... etc
```

---

## Future Optimization: Index Additions

If query is still slow with many agents, add indexes:

```sql
-- Already exists (UNIQUE constraint creates index)
-- CREATE UNIQUE INDEX idx_agent_ownership_name ON agent_ownership(agent_name);

-- May help for share lookups
CREATE INDEX idx_agent_sharing_email ON agent_sharing(LOWER(shared_with_email));
```

---

## Completion Checklist

- [ ] Add `get_all_agent_metadata()` to db/agents.py
- [ ] Update `get_accessible_agents()` to use batch query
- [ ] Handle orphaned agents (Docker-only, no DB record)
- [ ] Test with admin user
- [ ] Test with regular user (owned agents)
- [ ] Test with shared agents
- [ ] Verify query count reduced (logging)
- [ ] Update changelog.md
