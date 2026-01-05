# Querying Trinity Logs

Trinity uses Vector to aggregate all container logs into JSON files.

## Log Locations

| File | Contents |
|------|----------|
| `/data/logs/platform.json` | Backend, frontend, MCP server, Redis |
| `/data/logs/agents.json` | All agent containers |

## Accessing Logs

Logs are stored in the `trinity-logs` Docker volume. To access them:

```bash
# Find the volume location
docker volume inspect trinity-logs

# Or exec into a container that has access
docker exec trinity-vector cat /data/logs/platform.json | tail -100

# Or mount the volume to a temporary container
docker run --rm -v trinity-logs:/logs alpine cat /logs/platform.json | tail -100
```

## Query Examples

### Find Errors

```bash
# All errors in last 100 lines
docker exec trinity-vector sh -c "cat /data/logs/platform.json | tail -100" | jq 'select(.level == "error")'

# Errors for specific agent
docker exec trinity-vector sh -c "grep 'agent-ruby' /data/logs/agents.json | tail -50" | jq 'select(.level == "error")'
```

### Agent Activity

```bash
# What did agent-ruby log?
docker exec trinity-vector sh -c "grep 'agent-ruby' /data/logs/agents.json | tail -50" | jq -r '.message'

# All agent container logs
docker exec trinity-vector sh -c "cat /data/logs/agents.json | tail -100" | jq -r '.container_name + ": " + .message'
```

### Authentication Events

```bash
# Login attempts
docker exec trinity-vector sh -c "grep -i 'login\|auth' /data/logs/platform.json | tail -50" | jq .
```

### Backend Requests

```bash
# Recent backend logs
docker exec trinity-vector sh -c "grep 'trinity-backend' /data/logs/platform.json | tail -50" | jq .
```

## Live Tail

```bash
# Follow platform logs
docker exec trinity-vector sh -c "tail -f /data/logs/platform.json" | jq .

# Follow agent logs
docker exec trinity-vector sh -c "tail -f /data/logs/agents.json" | jq .
```

## Log Structure

Each log entry contains:

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

For JSON-formatted log messages (from Python's structured logging), Vector parses them:

```json
{
  "timestamp": "2025-12-31T12:00:00.000Z",
  "container_name": "trinity-backend",
  "message": "{\"level\": \"INFO\", ...}",
  "parsed": {
    "level": "INFO",
    "logger": "trinity.agents",
    "message": "Agent created",
    "agent_name": "test-agent"
  }
}
```

## Vector Health

```bash
# Check Vector status
curl http://localhost:8686/health

# Vector API (if enabled)
curl http://localhost:8686/api/v1/topology
```

## Known Limitations

### Historical Logs Not Captured

Vector's `docker_logs` source only captures logs from **after** it starts watching a container. This means:

| Scenario | Impact |
|----------|--------|
| Container started before Vector | No logs until container restarts |
| Vector restart | Logs during downtime lost |
| Pre-existing agents | Startup logs not captured |

**Mitigation**: Backend depends on Vector being healthy before starting, so newly created agents will always have logs captured.

**For pre-existing containers**, restart them to begin capturing logs:

```bash
# Restart an agent to start capturing its logs
docker restart agent-my-agent

# Restart all agents
docker ps --filter "label=trinity.platform=agent" -q | xargs -r docker restart
```

See [GitHub issue #7358](https://github.com/vectordotdev/vector/issues/7358) for upstream tracking.

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

Vector doesn't currently have rotation configured. Monitor log file sizes:

```bash
docker exec trinity-vector ls -lh /data/logs/
```

To clear logs:
```bash
docker exec trinity-vector sh -c "echo '' > /data/logs/platform.json"
docker exec trinity-vector sh -c "echo '' > /data/logs/agents.json"
```
