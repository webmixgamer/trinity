# Public External Access Setup for Trinity

> **Purpose**: Enable external (non-VPN) access to Trinity's public agent chat links while keeping the main platform internal.
> **Infrastructure**: GCP + Tailscale VPN
> **Priority**: Medium
> **Requester**: Eugene
> **Date**: 2026-02-16

---

## Current State

- Trinity runs on GCP VM (`ability-services` in `us-central1-a`)
- Platform accessible only via Tailscale VPN
- Public Agent Links feature exists but links only work for VPN users
- Production URL: `https://trinity.abilityai.dev` (internal)

## Goal

Allow agent owners to share public chat links with external users (clients, prospects) who are NOT on the Tailscale VPN, while keeping the admin/management interface internal.

## Use Case

- Occasional sharing with trusted people
- Stable external URL that doesn't change
- Security via unguessable tokens (192-bit random strings)
- No per-link external/internal toggle needed - just one external gateway

---

## Endpoints to Expose Externally

Only these routes need external access:

| Route | Type | Purpose |
|-------|------|---------|
| `/chat/:token` | Frontend | Public chat UI |
| `/api/public/link/{token}` | Backend | Validate link |
| `/api/public/verify/request` | Backend | Request email code |
| `/api/public/verify/confirm` | Backend | Confirm email code |
| `/api/public/chat/{token}` | Backend | Send chat message |

Everything else (admin, agents, credentials, etc.) stays VPN-only.

---

## Option 1: Tailscale Funnel (Recommended)

Tailscale Funnel exposes services to the public internet through Tailscale's infrastructure.

### Pros
- No firewall changes on GCP
- Automatic HTTPS with Tailscale certs
- Simple setup
- Traffic goes through Tailscale's CDN

### Cons
- Requires Tailscale plan that supports Funnel
- URL will be `https://<machine>.<tailnet>.ts.net/...`
- Less control over domain name

### Setup Steps

1. **Check Tailscale plan supports Funnel**
   ```bash
   tailscale funnel status
   ```

2. **Enable Funnel on the Trinity server**
   ```bash
   # SSH to ability-services
   gcloud compute ssh ability-services --zone=us-central1-a

   # Enable HTTPS serving
   tailscale serve --bg --https=443 / proxy http://localhost:80

   # Enable Funnel (exposes to internet)
   tailscale funnel 443 on
   ```

3. **Verify**
   ```bash
   tailscale funnel status
   # Should show: https://<machine>.<tailnet>.ts.net/ -> proxy http://localhost:80
   ```

4. **Get the public URL**
   ```bash
   tailscale funnel status
   # Note the URL, e.g.: https://ability-services.tail12345.ts.net
   ```

5. **Optional: Restrict to public routes only**

   If you want to be extra careful, configure nginx on the server to only allow public routes on a specific port, then funnel that port:

   ```nginx
   # /etc/nginx/sites-available/public-only
   server {
       listen 8888;

       location /chat {
           proxy_pass http://localhost:80;
       }

       location /api/public {
           proxy_pass http://localhost:8000;
       }

       location / {
           return 403 "Not available";
       }
   }
   ```

   Then funnel port 8888 instead:
   ```bash
   tailscale serve --bg --https=443 / proxy http://localhost:8888
   tailscale funnel 443 on
   ```

---

## Option 2: GCP Load Balancer + Cloud Armor

Use GCP's native load balancer with path-based routing.

### Pros
- Use your own domain (e.g., `public.abilityai.dev`)
- Full control over routing rules
- Cloud Armor for DDoS protection
- Native GCP integration

### Cons
- More complex setup
- Monthly cost (~$18/month for LB + backend)
- Requires opening firewall ports

### Setup Steps

1. **Reserve a static external IP**
   ```bash
   gcloud compute addresses create trinity-public-ip --global
   ```

2. **Create a serverless NEG or instance group**
   ```bash
   # Point to your VM
   gcloud compute instance-groups unmanaged create trinity-ig \
     --zone=us-central1-a
   gcloud compute instance-groups unmanaged add-instances trinity-ig \
     --zone=us-central1-a \
     --instances=ability-services
   ```

3. **Create backend service**
   ```bash
   gcloud compute backend-services create trinity-public-backend \
     --protocol=HTTP \
     --port-name=http \
     --health-checks=trinity-health-check \
     --global
   ```

4. **Create URL map with path rules**
   ```bash
   # Only allow /chat/* and /api/public/*
   gcloud compute url-maps create trinity-public-lb \
     --default-service=trinity-public-backend

   # Add path matcher (detailed config in YAML)
   ```

5. **Create HTTPS frontend with managed cert**
   ```bash
   gcloud compute ssl-certificates create trinity-public-cert \
     --domains=public.abilityai.dev \
     --global

   gcloud compute target-https-proxies create trinity-public-proxy \
     --url-map=trinity-public-lb \
     --ssl-certificates=trinity-public-cert

   gcloud compute forwarding-rules create trinity-public-https \
     --global \
     --target-https-proxy=trinity-public-proxy \
     --ports=443 \
     --address=trinity-public-ip
   ```

6. **Update DNS**
   - Point `public.abilityai.dev` to the static IP

7. **Add Cloud Armor policy (optional)**
   ```bash
   gcloud compute security-policies create trinity-public-policy
   # Add rate limiting rules
   ```

---

## Option 3: Cloudflare Tunnel (Simple Alternative)

Run cloudflared on the GCP VM to create a tunnel.

### Pros
- Free tier available
- Use your own domain via Cloudflare
- No firewall changes
- Built-in DDoS protection

### Cons
- Requires Cloudflare account
- Domain must use Cloudflare DNS

### Setup Steps

1. **Install cloudflared on VM**
   ```bash
   wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
   sudo dpkg -i cloudflared-linux-amd64.deb
   ```

2. **Login and create tunnel**
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create trinity-public
   ```

3. **Configure tunnel** (`~/.cloudflared/config.yml`)
   ```yaml
   tunnel: trinity-public
   credentials-file: /root/.cloudflared/<tunnel-id>.json

   ingress:
     - hostname: public.abilityai.dev
       path: /chat/*
       service: http://localhost:80
     - hostname: public.abilityai.dev
       path: /api/public/*
       service: http://localhost:8000
     - service: http_status:404
   ```

4. **Run as service**
   ```bash
   sudo cloudflared service install
   sudo systemctl start cloudflared
   ```

5. **Add DNS record in Cloudflare**
   - CNAME `public` -> `<tunnel-id>.cfargotunnel.com`

---

## Trinity Code Changes Required

Regardless of which option you choose, Trinity needs a small code change to generate external URLs.

### 1. Add Environment Variable

Add to `.env` on the server:
```bash
# External URL for public chat links (optional)
# When set, "Copy External Link" button appears in PublicLinksPanel
PUBLIC_CHAT_URL=https://public.abilityai.dev
# Or for Tailscale Funnel:
PUBLIC_CHAT_URL=https://ability-services.tail12345.ts.net
```

### 2. Backend Changes

**File**: `src/backend/config.py`
```python
PUBLIC_CHAT_URL = os.getenv("PUBLIC_CHAT_URL", "")
```

**File**: `src/backend/routers/public_links.py`
- Modify `create_public_link()` and `list_public_links()` to include `external_url` field when `PUBLIC_CHAT_URL` is set

### 3. Frontend Changes

**File**: `src/frontend/src/components/PublicLinksPanel.vue`
- Add "Copy External Link" button when external URL is available
- Show both internal and external URLs in the link list

---

## Recommendation

**Start with Tailscale Funnel** (Option 1) because:
1. You're already using Tailscale
2. Zero GCP configuration changes
3. Can be set up in 5 minutes
4. Can always migrate to GCP LB later if needed

If Tailscale Funnel isn't available on your plan, use **Cloudflare Tunnel** (Option 3) as it's free and simple.

---

## Security Considerations

1. **Token Security**: Public link tokens are 192-bit random strings - effectively unguessable
2. **Rate Limiting**: Already implemented (30 requests/min per IP)
3. **Email Verification**: Optional per-link setting for tracking
4. **Link Expiration**: Can set expiration dates on links
5. **Disable/Delete**: Links can be disabled or deleted anytime
6. **Audit Logging**: All public access is logged

---

## Testing Checklist

After setup:

- [ ] Can access `https://<public-url>/chat/<token>` from outside VPN
- [ ] Cannot access `https://<public-url>/` (should 403 or redirect)
- [ ] Cannot access `https://<public-url>/api/agents` (should 403)
- [ ] Public chat works end-to-end
- [ ] Email verification works (if enabled on link)
- [ ] Rate limiting works (try 31+ requests in a minute)
- [ ] Internal URL still works for VPN users

---

## Files Referenced

- `src/backend/routers/public.py` - Public endpoints (no auth)
- `src/backend/routers/public_links.py` - Owner CRUD endpoints
- `src/frontend/src/views/PublicChat.vue` - Public chat UI
- `src/frontend/src/components/PublicLinksPanel.vue` - Link management
- `docs/memory/feature-flows/public-agent-links.md` - Full feature documentation
