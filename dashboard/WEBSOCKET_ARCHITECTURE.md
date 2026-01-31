# WebSocket Architecture

## Flow
```
Frontend (localhost:3000)
    ↓ ws://localhost:3001/ws/mcp-status
Dashboard Backend (localhost:3001)
    ↓ ws://host.docker.internal:8090/ws/mcp-status
Traefik (localhost:8090)
    ↓ ws://omni2:8000/ws/mcp-status
OMNI2 Backend (omni2:8000)
```

## Components

### 1. Frontend WebSocket Client
**File:** `frontend/src/components/WebSocketDebugWindow.tsx`
- Connects to: `ws://localhost:3001/ws/mcp-status`
- Displays real-time MCP status updates

### 2. Dashboard Backend WebSocket Proxy
**File:** `backend/app/routers/websocket.py`
- Accepts connections from frontend
- Proxies to OMNI2 via Traefik at `ws://host.docker.internal:8090/ws/mcp-status`
- Bidirectional message forwarding

### 3. Traefik External Gateway
**Location:** `omni2/traefik-external/`
**Port:** 8090

**Labels in `omni2/docker-compose.yml`:**
```yaml
# WebSocket endpoint (no auth)
- "traefik.http.routers.omni2-ws.rule=PathPrefix(`/ws/`)"
- "traefik.http.routers.omni2-ws.entrypoints=web"
- "traefik.http.routers.omni2-ws.service=omni2"
- "traefik.http.routers.omni2-ws.priority=200"
```

**Key Settings:**
- Priority: 200 (highest, matches before other routes)
- No auth middleware (direct passthrough)
- Routes all `/ws/*` paths to omni2 service

### 4. OMNI2 Backend WebSocket Server
**Service:** omni2:8000
- Exposes: `/ws/mcp-status`
- Broadcasts MCP server status updates

## Restart Required
Yes, restart dashboard backend:
```bash
# Stop backend
Ctrl+C

# Restart
uvicorn app.main:app --reload --host 0.0.0.0 --port 3001
```

## Traefik Configuration
**File:** `omni2/traefik-external/docker-compose.yml`
- HTTP Port: 8090
- Dashboard: 8091
- Network: `omni2_omni2-network`
- Docker provider enabled
- WebSocket upgrade support (automatic)

## Notes
- WebSocket connections bypass authentication (priority 200, no middleware)
- Dashboard backend acts as secure proxy layer
- Traefik handles WebSocket upgrade automatically
- Frontend never connects directly to OMNI2
