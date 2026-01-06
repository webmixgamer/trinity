# Feature: Vector Logging

## Overview

Centralized log aggregation system that captures all Docker container stdout/stderr via Vector, routing platform service logs and agent logs to separate JSON files for queryability.

## User Story

As a platform operator, I want all container logs automatically captured and organized so that I can debug issues, monitor agent activity, and audit platform operations without manual log collection.

## Entry Points

- **Infrastructure**: Automatic - Vector captures all Docker container logs via Docker socket
- **Query**: CLI via `docker exec trinity-vector` with `jq`/`grep`
- **Health**: `GET http://localhost:8686/health` (Vector API)

## Architecture

```
Container stdout/stderr
        |
        v
   Docker Engine
        |
   Docker Socket (/var/run/docker.sock)
        |
        v
   Vector (timberio/vector:0.43.1-alpine)
        |
   VRL Transform (enrich, parse JSON, extract level)
        |
   +-----------+-----------+
   |                       |
   v                       v
route_platform         route_agents
(is_platform=true)     (is_agent=true)
   |                       |
   v                       v
/data/logs/platform.json   /data/logs/agents.json
```

## Data Flow

### 1. Log Capture

**Source**: `/Users/eugene/Dropbox/trinity/trinity/config/vector.yaml:9-14`

```yaml
sources:
  docker_logs:
    type: docker_logs
    # Automatically discovers all containers
    # Uses Docker socket to stream logs in real-time
```

Vector connects to Docker socket and streams all container logs in real-time.

### 2. Enrichment Transform

**Source**: `/Users/eugene/Dropbox/trinity/trinity/config/vector.yaml:17-47`

VRL (Vector Remap Language) transform enriches each log entry:

```vrl
# Add useful metadata
.service = .container_name
.is_agent = starts_with(string!(.container_name), "agent-")
.is_platform = !.is_agent && starts_with(string!(.container_name), "trinity-")

# Parse JSON logs if present (Python/Node often log JSON)
if is_string(.message) {
  parsed, err = parse_json(.message)
  if err == null {
    .parsed = parsed
  }
}

# Extract log level if present
if exists(.parsed.level) {
  .level = .parsed.level
} else if exists(.parsed.levelname) {
  .level = .parsed.levelname
} else if match(string!(.message), r'(?i)\b(error|err)\b') {
  .level = "error"
} else if match(string!(.message), r'(?i)\b(warn|warning)\b') {
  .level = "warning"
} else {
  .level = "info"
}
```

### 3. Routing

**Source**: `/Users/eugene/Dropbox/trinity/trinity/config/vector.yaml:49-65`

Two filter transforms route logs based on container naming:

| Filter | Condition | Output |
|--------|-----------|--------|
| `route_platform` | `.is_platform == true` | Platform service logs |
| `route_agents` | `.is_agent == true` | Agent container logs |

**Container Naming Convention**:
- Platform: `trinity-*` (backend, frontend, redis, mcp-server, vector)
- Agents: `agent-*` (all Trinity-managed agent containers)

### 4. File Sinks

**Source**: `/Users/eugene/Dropbox/trinity/trinity/config/vector.yaml:67-90`

| Sink | Input | Path | Format |
|------|-------|------|--------|
| `platform_logs` | `route_platform` | `/data/logs/platform.json` | JSON |
| `agent_logs` | `route_agents` | `/data/logs/agents.json` | JSON |

## Backend Layer

### Structured Logging Configuration

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/logging_config.py`

The backend uses a custom JSON formatter for Vector-compatible output:

```python
class JsonFormatter(logging.Formatter):
    """Format logs as JSON for easy parsing by Vector."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "event_type"):
            log_entry["event_type"] = record.event_type
        if hasattr(record, "agent_name"):
            log_entry["agent_name"] = record.agent_name
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "user_email"):
            log_entry["user_email"] = record.user_email
        if hasattr(record, "action"):
            log_entry["action"] = record.action
        if hasattr(record, "result"):
            log_entry["result"] = record.result
        if hasattr(record, "details"):
            log_entry["details"] = record.details

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)
```

### Logging Setup

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/main.py:164`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Set up structured JSON logging (captured by Vector)
    setup_logging()
```

### Logger Usage

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/logging_config.py:70-72`

```python
def get_logger(name: str) -> logging.Logger:
    """Get a Trinity logger instance."""
    return logging.getLogger(f"trinity.{name}")
```

**Example usage in services**:

```python
from logging_config import get_logger

logger = get_logger("agents")

logger.info(
    "Agent created",
    extra={
        "event_type": "agent_management",
        "action": "create",
        "agent_name": name,
        "user_id": current_user.id
    }
)
```

## Docker Compose Configuration

**File**: `/Users/eugene/Dropbox/trinity/trinity/docker-compose.yml:127-148`

```yaml
vector:
  image: timberio/vector:0.43.1-alpine
  container_name: trinity-vector
  restart: unless-stopped
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./config/vector.yaml:/etc/vector/vector.yaml:ro
    - trinity-logs:/data/logs
  ports:
    - "8686:8686"  # Vector API (health checks)
  networks:
    - trinity-network
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  healthcheck:
    test: ["CMD", "wget", "-q", "-O", "-", "http://localhost:8686/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

**Volume**: `/Users/eugene/Dropbox/trinity/trinity/docker-compose.yml:175`

```yaml
volumes:
  trinity-logs:  # Vector log storage
```

## Log Structure

### Platform Log Entry

```json
{
  "timestamp": "2025-12-31T12:00:00.000Z",
  "container_name": "trinity-backend",
  "container_id": "abc123...",
  "message": "The log message",
  "level": "info",
  "is_agent": false,
  "is_platform": true,
  "service": "trinity-backend"
}
```

### Parsed JSON Log Entry

When the backend logs structured JSON, Vector parses it:

```json
{
  "timestamp": "2025-12-31T12:00:00.000Z",
  "container_name": "trinity-backend",
  "message": "{\"level\": \"INFO\", ...}",
  "parsed": {
    "level": "INFO",
    "logger": "trinity.agents",
    "message": "Agent created",
    "agent_name": "test-agent",
    "user_id": "user_123"
  },
  "level": "INFO",
  "is_platform": true,
  "service": "trinity-backend"
}
```

## Query Interface

Full documentation: `/Users/eugene/Dropbox/trinity/trinity/docs/QUERYING_LOGS.md`

### Accessing Logs

```bash
# Via Vector container
docker exec trinity-vector cat /data/logs/platform.json | tail -100

# Via temporary container
docker run --rm -v trinity-logs:/logs alpine cat /logs/platform.json | tail -100
```

### Common Queries

```bash
# Find errors in platform logs
docker exec trinity-vector sh -c "cat /data/logs/platform.json | tail -100" | jq 'select(.level == "error")'

# Filter by agent
docker exec trinity-vector sh -c "grep 'agent-ruby' /data/logs/agents.json | tail -50" | jq -r '.message'

# Live tail platform logs
docker exec trinity-vector sh -c "tail -f /data/logs/platform.json" | jq .

# Backend-only logs
docker exec trinity-vector sh -c "grep 'trinity-backend' /data/logs/platform.json | tail -50" | jq .

# Authentication events
docker exec trinity-vector sh -c "grep -i 'login\|auth' /data/logs/platform.json | tail -50" | jq .
```

### Health Check

```bash
# Vector health
curl http://localhost:8686/health

# Vector topology
curl http://localhost:8686/api/v1/topology
```

## Log Retention & Archival

### Overview

Automated log retention system that:
1. Rotates logs daily to date-stamped files
2. Archives old logs with compression to local storage
3. Deletes originals after successful archive

### Configuration

Environment variables in `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_RETENTION_DAYS` | `90` | Days to keep logs before archival |
| `LOG_ARCHIVE_ENABLED` | `true` | Enable automated archival |
| `LOG_CLEANUP_HOUR` | `3` | Hour (UTC) to run nightly archival |
| `LOG_ARCHIVE_PATH` | `/data/archives` | Local path for archived logs |

### Daily Rotation

Vector writes logs to date-stamped files:
- `platform-2026-01-05.json` (today's platform logs)
- `agents-2026-01-05.json` (today's agent logs)

Files rotate automatically at midnight UTC.

### Automated Archival

The backend runs a nightly job (default: 3 AM UTC) that:

1. **Finds old files**: Identifies logs older than retention period
2. **Compresses**: Gzip level 9 (~90% size reduction)
3. **Verifies**: SHA256 integrity check
4. **Stores locally**: Moves to mounted archive volume
5. **Cleans up**: Deletes original files after successful archive

### API Endpoints

Admin-only endpoints for log management:

```bash
# Get log statistics
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/logs/stats

# Get retention configuration
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/logs/retention

# Update retention (runtime only)
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"retention_days": 30, "archive_enabled": true, "cleanup_hour": 3}' \
  http://localhost:8000/api/logs/retention

# Manually trigger archival
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"retention_days": 90, "delete_after_archive": true}' \
  http://localhost:8000/api/logs/archive

# Check archival service health
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/logs/health
```

### Custom Backup Strategies

Trinity archives logs locally by default, keeping all data within your infrastructure (sovereign deployment). You can implement custom backup strategies using standard Docker volume management:

#### Option 1: Mount NAS/NFS for Archives

Mount a network storage device to the archives volume:

```yaml
# In docker-compose.yml
services:
  backend:
    volumes:
      - type: bind
        source: /mnt/nas/trinity-archives  # Your NAS mount point
        target: /data/archives
```

#### Option 2: rsync to Backup Server

Create a cron job to sync archives to another server:

```bash
# /etc/cron.daily/trinity-archive-sync
#!/bin/bash
rsync -avz --delete \
  /var/lib/docker/volumes/trinity-archives/_data/ \
  backup-server:/backups/trinity-logs/
```

#### Option 3: Docker Volume Backup

Use Docker's built-in volume backup:

```bash
# Backup archives volume to tarball
docker run --rm \
  -v trinity-archives:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/trinity-archives-$(date +%Y%m%d).tar.gz /data

# Restore from tarball
docker run --rm \
  -v trinity-archives:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/trinity-archives-20260105.tar.gz -C /
```

#### Option 4: Cross-Instance Volume Copy

Copy archives between Docker instances:

```bash
# Export from instance A
docker run --rm \
  -v trinity-archives:/source \
  -v $(pwd):/dest \
  alpine sh -c "cd /source && tar czf - ." > trinity-archives.tar.gz

# Import to instance B (transfer trinity-archives.tar.gz via scp/rsync)
docker run --rm \
  -v trinity-archives:/dest \
  -v $(pwd):/source \
  alpine sh -c "cd /dest && tar xzf /source/trinity-archives.tar.gz"
```

### Storage Locations

| Location | Contents | Purpose |
|----------|----------|---------|
| `/data/logs/` | Active log files | Daily logs (current + retention period) |
| `/data/archives/` | Compressed archives | Local storage of archived logs |
| Docker volume `trinity-archives` | Persistent storage | Mounted at `/data/archives` in backend |

### Disk Space Management

Example with 90-day retention:
- Daily log size: ~150 MB
- 90 days uncompressed: ~13.5 GB
- 90 days compressed: ~1.35 GB (10% of original)
- Active logs stay at ~13.5 GB (stable after 90 days)

## Side Effects

- **File Output**: Logs written to Docker volume `trinity-logs` with daily rotation
- **Compressed Archives**: Old logs archived to Docker volume `trinity-archives`
- **No Database**: Logs are file-based, not persisted to SQLite
- **No WebSocket**: No real-time log streaming to UI (query only)

## Error Handling

| Error Case | Impact | Resolution |
|------------|--------|------------|
| Docker socket unavailable | No log capture | Check Vector container permissions |
| Volume full | Log writes fail | Clear old logs, increase volume size |
| Vector container down | Logs lost during downtime | Restart Vector service |
| Invalid VRL transform | Logs dropped | Check Vector logs for parse errors |
| Pre-existing container | No logs until restart | Restart the container: `docker restart agent-<name>` |

### Known Limitation: Historical Logs

Vector's `docker_logs` source **only captures logs from after it starts watching** a container. This is a known upstream limitation ([GitHub #7358](https://github.com/vectordotdev/vector/issues/7358)).

**Mitigation in Trinity:**
- Backend depends on Vector being healthy before starting (`condition: service_healthy`)
- This ensures all newly created agents have their logs captured from the start
- Pre-existing containers (from before Vector started) need to be restarted to begin log capture

## Security Considerations

- Docker socket mounted **read-only** (`/var/run/docker.sock:ro`)
- `no-new-privileges` security option enabled
- All capabilities dropped (`cap_drop: ALL`)
- No sensitive data in log messages (credentials masked at source)
- Log files on Docker volume (not host filesystem by default)

## Troubleshooting

### Logs Not Appearing

1. Check Vector is running:
   ```bash
   docker ps | grep vector
   ```

2. Check Vector logs:
   ```bash
   docker logs trinity-vector --tail 50
   ```

3. Verify Docker socket access:
   ```bash
   docker exec trinity-vector ls -la /var/run/docker.sock
   ```

### Large Log Files

Monitor file sizes:
```bash
docker exec trinity-vector ls -lh /data/logs/
```

Clear logs (if needed):
```bash
docker exec trinity-vector sh -c "echo '' > /data/logs/platform.json"
docker exec trinity-vector sh -c "echo '' > /data/logs/agents.json"
```

## Related Flows

- **Upstream**: All container stdout/stderr (backend, frontend, agents)
- **Downstream**: None (terminal sink - query only)
- **Replaced**: `audit-logger` service (fire-and-forget HTTP calls, 173+ call sites removed)
- **Related**: [opentelemetry-integration.md](opentelemetry-integration.md) - OTel metrics (separate from logs)

## Testing

### Prerequisites
- Trinity platform running (`./scripts/deploy/start.sh`)
- Vector container healthy

### Test Steps

1. **Verify Vector Running**
   - Action: `docker ps | grep vector`
   - Expected: `trinity-vector` container running
   - Verify: Container healthy (no restart loops)

2. **Check Log Files Created**
   - Action: `docker exec trinity-vector ls -la /data/logs/`
   - Expected: `platform.json` and `agents.json` exist
   - Verify: Files have non-zero size

3. **Verify Platform Log Capture**
   - Action: Make API request (e.g., `curl http://localhost:8000/api/health`)
   - Expected: Log appears in platform.json
   - Verify: `docker exec trinity-vector sh -c "tail -5 /data/logs/platform.json" | jq .`

4. **Verify Agent Log Capture**
   - Action: Start an agent, wait for activity
   - Expected: Logs appear in agents.json
   - Verify: `docker exec trinity-vector sh -c "tail -5 /data/logs/agents.json" | jq .`

5. **Verify JSON Parsing**
   - Action: Check for `.parsed` field in backend logs
   - Expected: Structured Python logs have `parsed` object
   - Verify: `docker exec trinity-vector sh -c "grep trinity-backend /data/logs/platform.json | tail -1" | jq '.parsed'`

6. **Verify Health Endpoint**
   - Action: `curl http://localhost:8686/health`
   - Expected: Returns health status
   - Verify: Non-error HTTP response

### Edge Cases
- Container with non-trinity prefix: Should not appear in either log file
- Invalid JSON in message: Should still capture raw message
- Very long log lines: Captured but may be truncated

### Cleanup
No cleanup required - logs accumulate until manually cleared.

### Status
- [x] Vector service deployed (2025-12-31)
- [x] Audit logger removed
- [x] Structured logging in backend
- [x] Query documentation complete

## Revision History

| Date | Change |
|------|--------|
| 2026-01-06 | Refactored to sovereign architecture - removed external S3 dependency, added pluggable storage interface |
| 2026-01-05 | Added log retention, rotation, and archival capabilities |
| 2025-12-31 | Initial implementation - replaced audit-logger with Vector |
