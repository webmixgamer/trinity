# Deployment Status Check

Check health of production deployment.

## Prerequisites

This command requires `CLAUDE.local.md` to be configured with your deployment details:
- Production URL
- Server IP
- GCP project and zone
- VM name

If `CLAUDE.local.md` doesn't exist, create it from `CLAUDE.local.md.example`.

## Instructions

1. Read `CLAUDE.local.md` to get deployment configuration
2. Check production frontend:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://${PRODUCTION_URL}
   ```

3. Check production backend:
   ```bash
   curl -s https://${PRODUCTION_URL}/api/health | python3 -m json.tool
   ```

4. Check MCP server:
   ```bash
   curl -s http://${SERVER_IP}:8007/mcp | head -20
   ```

5. Check audit logger:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" http://${SERVER_IP}:8006/docs
   ```

6. (If SSH access available) Check containers on VM:
   ```bash
   gcloud compute ssh ${VM_NAME} --zone=${GCP_ZONE} --command="docker ps --format 'table {{.Names}}\t{{.Status}}'"
   ```

7. Report status:
   ```
   ## Production Deployment Status

   ### Services
   | Service | URL | Status |
   |---------|-----|--------|
   | Frontend | https://${PRODUCTION_URL} | ✅ 200 |
   | Backend API | https://${PRODUCTION_URL}/api/ | ✅ Healthy |
   | MCP Server | :8007/mcp | ✅ Running |
   | Audit Logger | :8006/docs | ✅ Running |

   ### SSL Certificate
   - Issuer: Let's Encrypt
   - Expiry: [date from cert]
   - Auto-renewal: ✅ Enabled

   ### Port Allocation
   | Port | Service |
   |------|---------|
   | 3005 | Frontend |
   | 8005 | Backend |
   | 8006 | Audit Logger |
   | 8007 | MCP Server |
   | 2224-2242 | Agent SSH |

   ### Quick Actions
   - Deploy: `./scripts/deploy/gcp-deploy.sh`
   - Backup DB: `./scripts/deploy/backup-database.sh`
   - View logs: `gcloud compute ssh ${VM_NAME} --command="docker-compose logs -f"`
   ```

## When to Use

- Before and after production deployments
- When users report production issues
- For daily health checks
- After SSL certificate renewals

## Troubleshooting

If services are down:
1. SSH to VM: `gcloud compute ssh ${VM_NAME} --zone=${GCP_ZONE}`
2. Check containers: `docker ps -a`
3. Check logs: `docker-compose -f docker-compose.prod.yml logs`
4. Restart services: `docker-compose -f docker-compose.prod.yml up -d`
