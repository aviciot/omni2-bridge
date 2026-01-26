# Network Security

**Internal-Only Access, IP Whitelisting, and HTTPS**

---

## 🌐 Overview

Omni2 provides multiple layers of network security to protect your infrastructure.

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
