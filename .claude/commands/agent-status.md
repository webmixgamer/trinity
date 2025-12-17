# Agent Status Check

Check the status of all Trinity agent containers.

## Instructions

1. List all running containers:
   ```bash
   docker ps --filter "label=trinity.platform=agent" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
   ```

2. Check backend health:
   ```bash
   curl -s http://localhost:8000/api/health | python3 -m json.tool
   ```

3. List agents via API:
   ```bash
   curl -s http://localhost:8000/api/agents | python3 -m json.tool
   ```

4. Check Redis connectivity:
   ```bash
   docker exec trinity-redis redis-cli ping
   ```

5. Report status in this format:
   ```
   ## Agent Status Report

   ### Infrastructure
   - Backend: ✅ Running / ❌ Down
   - Redis: ✅ Connected / ❌ Down
   - Audit Logger: ✅ Running / ❌ Down

   ### Agents
   | Name | Status | Uptime | Template |
   |------|--------|--------|----------|
   | agent-1 | running | 2h 15m | github:Org/repo |
   | agent-2 | stopped | - | local-template |

   ### Quick Actions
   - Start agent: `curl -X POST http://localhost:8000/api/agents/{name}/start`
   - Stop agent: `curl -X POST http://localhost:8000/api/agents/{name}/stop`
   - View logs: `docker logs agent-{name}`
   ```

## When to Use

- Before starting development work
- When debugging agent issues
- To verify deployment health
- After infrastructure changes

## Troubleshooting

If agents not showing:
1. Check Docker socket: `ls -la /var/run/docker.sock`
2. Check backend logs: `docker-compose logs backend`
3. Verify network: `docker network ls | grep trinity`
