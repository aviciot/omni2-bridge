# Production Deployment Configuration

## Environment Variables

### Dashboard Backend (.env)

```bash
# Development (Docker)
OMNI2_WS_URL=ws://host.docker.internal:8090/ws
OMNI2_HTTP_URL=http://host.docker.internal:8090

# Production (Separate Servers)
OMNI2_WS_URL=wss://omni2-api.company.com/ws
OMNI2_HTTP_URL=https://omni2-api.company.com
```

---

## Architecture

### Development (Same Host)
```
Browser → Dashboard Backend → Host → Traefik (8090) → OMNI2
```

### Production (Different Servers)
```
Dashboard Server (AWS)
    ↓
https://omni2-api.company.com (Public URL)
    ↓
Traefik (Load Balancer + Auth)
    ↓
OMNI2 Backend (Internal Network)
```

---

## Configuration Files

### 1. Dashboard Backend Config
File: `dashboard/backend/app/config.py`
```python
OMNI2_WS_URL: str = "ws://host.docker.internal:8090/ws"
OMNI2_HTTP_URL: str = "http://host.docker.internal:8090"
```

### 2. Dashboard Backend .env
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
OMNI2_WS_URL=wss://omni2-api.company.com/ws
OMNI2_HTTP_URL=https://omni2-api.company.com
ENVIRONMENT=production
DEV_MODE=false
```

---

## Production Checklist

- [ ] Set `OMNI2_WS_URL` to public WebSocket URL
- [ ] Set `OMNI2_HTTP_URL` to public HTTPS URL
- [ ] Configure Traefik SSL certificates
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEV_MODE=false`
- [ ] Configure CORS_ORIGINS for production domains
- [ ] Test WebSocket connection through public URL
- [ ] Verify auth_service ForwardAuth works

---

## Testing Production Config

```bash
# Test HTTP endpoint
curl https://omni2-api.company.com/health

# Test WebSocket (use wscat)
wscat -c wss://omni2-api.company.com/ws?token=YOUR_TOKEN
```

---

## Security Notes

✅ All traffic goes through Traefik (auth enforced)
✅ OMNI2 has no public ports (internal only)
✅ Dashboard backend uses public URL (like any external client)
✅ SSL/TLS encryption in production (wss:// and https://)
