# Network Security

**Zero-Trust Architecture: OMNI2 Complete Isolation Behind Traefik**

---

## 🌐 Overview

Omni2 implements a **zero-trust network architecture** where the backend (OMNI2) has **NO exposed ports** and is completely isolated behind Traefik gateway. All access is authenticated and authorized through Traefik's ForwardAuth middleware.

---

## 🔒 OMNI2 Complete Isolation (Production Architecture)

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    EXTERNAL NETWORK                          │
│                                                               │
│  👤 User → http://localhost:8090/api/v1/...              │
└────────────────────────────┬────────────────────────────┘
                             │
                             │ ONLY ENTRY POINT
                             │
┌────────────────────────────┴────────────────────────────┐
│         🚦 TRAEFIK GATEWAY (Port 8090)                  │
│                                                               │
│  ✅ ForwardAuth Middleware                                  │
│  ✅ JWT Validation                                          │
│  ✅ CORS Headers                                            │
│  ✅ Rate Limiting                                           │
│  ✅ WebSocket Upgrade                                       │
└────────────────────────────┬────────────────────────────┘
                             │
                             │ INTERNAL DOCKER NETWORK ONLY
                             │ (172.x.x.x)
                             │
┌────────────────────────────┴────────────────────────────┐
│         🔒 OMNI2 BACKEND (NO PORTS)                     │
│                                                               │
│  ❌ NO PORT EXPOSURE                                        │
│  ✅ Only accessible via Docker network                     │
│  ✅ Traefik routes to omni2-bridge:8000                    │
│  ✅ Complete isolation from host                           │
│  ✅ Impossible to bypass authentication                    │
└─────────────────────────────────────────────────────────┘
```

### Docker Configuration

**OMNI2 (Isolated):**
```yaml
omni2:
  container_name: omni2-bridge
  # NO PORTS EXPOSED - Complete isolation
  # ports:
  #   - "8000:8000"  # REMOVED: No direct access
  networks:
    - omni2-network  # Internal Docker network only
  labels:
    - "traefik.enable=true"
    - "traefik.http.services.omni2.loadbalancer.server.port=8000"
    # Traefik accesses via internal network
```

**Traefik (Gateway):**
```yaml
traefik-external:
  ports:
    - "8090:80"   # HTTP (localhost only)
    - "8443:443"  # HTTPS (localhost only)
    - "8091:8080" # Dashboard (localhost only)
  networks:
    - omni2_omni2-network  # Same network as OMNI2
```

### Security Benefits

| Benefit | Description |
|---------|-------------|
| **Zero Direct Access** | OMNI2 has no exposed ports, impossible to access directly |
| **Forced Authentication** | ALL requests must go through Traefik ForwardAuth |
| **Defense in Depth** | Even if Traefik compromised, OMNI2 still isolated |
| **No Port Scanning** | OMNI2 invisible to network scans |
| **Container Isolation** | Docker network isolation prevents lateral movement |
| **Single Entry Point** | Only Traefik exposed, simplified security monitoring |
| **Attack Surface Minimization** | Reduced attack vectors |

---

## 🚦 Traefik as Security Gateway

### ForwardAuth Pattern

**How It Works:**
1. User sends request with JWT token
2. Traefik intercepts ALL requests to protected routes
3. Traefik forwards token to auth_service for validation
4. If valid, auth_service returns user headers (X-User-Id, X-User-Role)
5. Traefik forwards request to OMNI2 with user headers
6. OMNI2 trusts headers (no JWT validation needed)

**Security Advantages:**
- Single point of authentication
- OMNI2 doesn't need JWT validation logic
- Consistent auth across all services
- Easy to add new protected services
- Centralized security policy

### Route Priority

```yaml
# Priority determines which route matches first
# Higher number = higher priority

# WebSocket (Priority 200) - Matches first
- "traefik.http.routers.omni2-ws.rule=Path(`/ws/mcp-status`)"
- "traefik.http.routers.omni2-ws.priority=200"

# Protected API (Priority 100)
- "traefik.http.routers.omni2-protected.rule=PathPrefix(`/api/v1`)"
- "traefik.http.routers.omni2-protected.middlewares=auth-forward,cors"
- "traefik.http.routers.omni2-protected.priority=100"

# Public routes (Priority 50)
- "traefik.http.routers.omni2-public.rule=PathPrefix(`/health`)"
- "traefik.http.routers.omni2-public.priority=50"
```

---

## Internal-Only Access (Default)

**Current Configuration:**
```yaml
ports:
  - "8090:80"  # Binds to localhost only
```

**Access Control:**
- ✅ Accessible from localhost (127.0.0.1)
- ✅ Accessible from Docker network (172.x.x.x)
- ✗ NOT accessible from external network

**Benefits:**
- No exposure to internet
- Safe for development
- No firewall rules needed

---

## IP Whitelisting (Production)

**Configuration:**
```yaml
labels:
  - "traefik.http.middlewares.internal-only.ipwhitelist.sourcerange=192.168.1.0/24,10.0.0.0/8"
  - "traefik.http.routers.admin.middlewares=auth-forward,internal-only"
```

**Use Cases:**
- Restrict admin dashboard to office network
- Allow only VPN users
- Block specific countries (via Cloudflare)

---

## HTTPS/TLS

### Development
- HTTP only (localhost)
- No certificate needed

### Production
- HTTPS required
- Let's Encrypt (free, auto-renewal)
- Or custom certificate

**Configuration:**
```yaml
command:
  - --entrypoints.websecure.address=:443
  - --certificatesresolvers.letsencrypt.acme.email=admin@company.com
  - --certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json
```

---

## Firewall Rules

**Recommended:**
```bash
# Allow only necessary ports
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

**[Back to Security Overview](./SECURITY_OVERVIEW)**
