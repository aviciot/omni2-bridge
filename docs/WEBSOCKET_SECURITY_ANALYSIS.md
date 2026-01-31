# WebSocket Security Analysis

**Why WebSocket Connections Bypass Authentication**

---

## 🔍 Executive Summary

**FINDING**: The WebSocket endpoint `/ws/mcp-status` is **intentionally configured to bypass authentication** and is accessible to anyone, even on the login screen.

**RISK LEVEL**: 🟡 **MEDIUM** - Exposes real-time MCP status information to unauthenticated users

**RECOMMENDATION**: Implement WebSocket authentication using JWT tokens or session cookies

---

## 🔐 Current Authentication Architecture

### Protected Endpoints (With Auth)
```yaml
# Traefik Configuration (docker-compose.yml)
traefik.http.routers.omni2-protected.rule: PathPrefix(`/api/v1`)
traefik.http.routers.omni2-protected.middlewares: auth-forward,cors
```

**How it works:**
1. Request hits Traefik gateway
2. `auth-forward` middleware intercepts request
3. Traefik forwards to auth service: `http://mcp-auth-service:8080/validate`
4. Auth service validates JWT token from `Authorization: Bearer <token>` header
5. If valid, auth service returns user info in headers:
   - `X-User-Id`
   - `X-User-Username`
   - `X-User-Role`
   - `X-User-Permissions`
6. Request proceeds to OMNI2 backend

### Public Endpoints (No Auth)
```yaml
# Health checks, docs, OpenAPI spec
traefik.http.routers.omni2-public.rule: PathPrefix(`/health`) || PathPrefix(`/docs`) || PathPrefix(`/openapi.json`)
traefik.http.routers.omni2-public.priority: 50
```

### WebSocket Endpoint (No Auth) ⚠️
```yaml
# WebSocket - BYPASSES AUTHENTICATION
traefik.http.routers.omni2-ws.rule: Path(`/ws/mcp-status`)
traefik.http.routers.omni2-ws.priority: 200
# NO MIDDLEWARES = NO AUTH
```

---

## 🚨 Why WebSocket Bypasses Authentication

### 1. **Traefik Configuration**
The WebSocket route is configured **without** the `auth-forward` middleware:

```yaml
# ❌ NO AUTH MIDDLEWARE
- "traefik.http.routers.omni2-ws.rule=Path(`/ws/mcp-status`)"
- "traefik.http.routers.omni2-ws.entrypoints=web"
- "traefik.http.routers.omni2-ws.service=omni2"
- "traefik.http.routers.omni2-ws.priority=200"
# Missing: middlewares=auth-forward,cors
```

Compare to protected routes:
```yaml
# ✅ WITH AUTH MIDDLEWARE
- "traefik.http.routers.omni2-protected.rule=PathPrefix(`/api/v1`)"
- "traefik.http.routers.omni2-protected.middlewares=auth-forward,cors"
```

### 2. **Application Code**
The WebSocket endpoint has a TODO comment acknowledging missing auth:

```python
# omni2/app/routers/websocket.py

@router.websocket("/ws/mcp-status")
async def websocket_mcp_status(websocket: WebSocket):
    broadcaster = get_websocket_broadcaster()
    
    # ⚠️ For now, accept all connections (TODO: add auth)
    user_id = "dashboard"
    user_role = "admin"
    
    try:
        conn_id = await broadcaster.connect(websocket, user_id, user_role)
        # ... rest of code
```

**Key Issues:**
- Hardcoded `user_id = "dashboard"` and `user_role = "admin"`
- No token validation
- No session checking
- No permission verification
- Comment explicitly states: `TODO: add auth`

### 3. **No Authentication Dependency**
Other routers use FastAPI's `Depends()` for authentication:

```python
# Example from chat.py
@router.post("/ask")
async def ask_question(
    request: ChatRequest,
    user_service: UserService = Depends(get_user_service),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    # ... other dependencies
):
```

WebSocket endpoint has **NO** authentication dependencies:
```python
# websocket.py - NO AUTH DEPENDENCIES
@router.websocket("/ws/mcp-status")
async def websocket_mcp_status(websocket: WebSocket):
    # Direct connection, no auth check
```

---

## 📊 What Information is Exposed?

### Data Sent Over WebSocket

```python
# From websocket_broadcaster.py

# 1. Initial Status (on connect)
{
    "type": "initial_status",
    "mcps": [
        {
            "id": 1,
            "name": "oracle_mcp",
            "status": "active",
            "circuit_state": "CLOSED",  # ⚠️ Circuit breaker state
            "last_health_check": "2025-01-26T10:30:00Z",
            "health_status": "healthy"
        }
    ]
}

# 2. MCP Status Changes
{
    "type": "mcp_status_change",
    "mcp_id": 1,
    "mcp_name": "oracle_mcp",
    "old_status": "active",
    "new_status": "inactive",
    "reason": "Auto-disabled after 3 failure cycles",  # ⚠️ Failure details
    "timestamp": "2025-01-26T10:35:00Z"
}

# 3. Health Events
{
    "type": "health_event",
    "mcp_id": 1,
    "mcp_name": "oracle_mcp",
    "event": "recovery",
    "message": "MCP recovered after circuit breaker timeout",
    "timestamp": "2025-01-26T10:40:00Z"
}

# 4. System Metrics
{
    "type": "system_metrics",
    "active_mcps": 5,
    "total_mcps": 8,
    "circuit_breakers_open": 2,
    "timestamp": "2025-01-26T10:45:00Z"
}
```

### Sensitive Information Exposed:
- ✅ **MCP names** - Internal system architecture
- ✅ **MCP status** - Which systems are up/down
- ✅ **Circuit breaker states** - Failure patterns
- ✅ **Failure reasons** - Error details
- ✅ **Health check results** - System reliability
- ✅ **System metrics** - Infrastructure overview

---

## 🎯 Security Implications

### Risk Assessment

| Risk | Severity | Impact |
|------|----------|--------|
| **Information Disclosure** | 🟡 Medium | Attackers can monitor system health and identify vulnerable MCPs |
| **Reconnaissance** | 🟡 Medium | Reveals internal architecture and service names |
| **Timing Attacks** | 🟢 Low | Could correlate failures with attack attempts |
| **DoS Potential** | 🟢 Low | Unlimited connections could exhaust resources |

### Attack Scenarios

1. **Passive Monitoring**
   - Attacker connects to WebSocket from login screen
   - Monitors MCP failures in real-time
   - Identifies best time to attack (when systems are down)

2. **Architecture Reconnaissance**
   - Discovers all MCP names and types
   - Maps internal system dependencies
   - Identifies critical vs non-critical services

3. **Resource Exhaustion**
   - Opens thousands of WebSocket connections
   - Exhausts server memory/connections
   - Causes legitimate users to be denied service

---

## ✅ Recommended Solutions

### Option 1: JWT Token Authentication (Recommended)

**Implementation:**

```python
# omni2/app/routers/websocket.py

from fastapi import WebSocket, WebSocketDisconnect, Query, HTTPException
from app.services.auth_client import validate_token

@router.websocket("/ws/mcp-status")
async def websocket_mcp_status(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token for authentication")
):
    """
    WebSocket endpoint with JWT authentication.
    
    Usage: ws://localhost:8000/ws/mcp-status?token=<jwt_token>
    """
    broadcaster = get_websocket_broadcaster()
    
    # Validate token before accepting connection
    user_data = await validate_token(token)
    if not user_data:
        await websocket.close(code=1008, reason="Invalid or expired token")
        logger.warning("WebSocket connection rejected: Invalid token")
        return
    
    user_id = user_data.get("email") or user_data.get("sub")
    user_role = user_data.get("role", "read_only")
    
    # Check if user has permission to view MCP status
    if user_role not in ["admin", "developer", "dba"]:
        await websocket.close(code=1008, reason="Insufficient permissions")
        logger.warning(f"WebSocket connection rejected: User {user_id} lacks permissions")
        return
    
    try:
        conn_id = await broadcaster.connect(websocket, user_id, user_role)
        logger.info("WebSocket client connected", conn_id=conn_id, user=user_id, role=user_role)
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected", conn_id=conn_id)
                break
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
    finally:
        await broadcaster.disconnect(conn_id)
```

**Frontend Changes:**

```typescript
// dashboard/frontend/src/stores/authStore.ts

export const connectWebSocket = () => {
  const token = localStorage.getItem('jwt_token');
  if (!token) {
    console.error('No JWT token found');
    return;
  }
  
  // Pass token as query parameter
  const ws = new WebSocket(`ws://localhost:8000/ws/mcp-status?token=${token}`);
  
  ws.onopen = () => console.log('WebSocket connected');
  ws.onmessage = (event) => handleMessage(JSON.parse(event.data));
  ws.onerror = (error) => console.error('WebSocket error:', error);
  ws.onclose = () => console.log('WebSocket disconnected');
};
```

**Traefik Configuration:**
```yaml
# No changes needed - auth happens at application level
- "traefik.http.routers.omni2-ws.rule=Path(`/ws/mcp-status`)"
- "traefik.http.routers.omni2-ws.entrypoints=web"
- "traefik.http.routers.omni2-ws.service=omni2"
- "traefik.http.routers.omni2-ws.priority=200"
```

---

### Option 2: Cookie-Based Session Authentication

**Implementation:**

```python
from fastapi import WebSocket, Cookie, HTTPException

@router.websocket("/ws/mcp-status")
async def websocket_mcp_status(
    websocket: WebSocket,
    session_id: str = Cookie(None)
):
    """
    WebSocket endpoint with session cookie authentication.
    """
    if not session_id:
        await websocket.close(code=1008, reason="No session cookie")
        return
    
    # Validate session (implement session store)
    user_data = await validate_session(session_id)
    if not user_data:
        await websocket.close(code=1008, reason="Invalid session")
        return
    
    # ... rest of code
```

---

### Option 3: Traefik ForwardAuth (Most Secure)

**Traefik Configuration:**

```yaml
# docker-compose.yml
labels:
  - "traefik.http.routers.omni2-ws.rule=Path(`/ws/mcp-status`)"
  - "traefik.http.routers.omni2-ws.entrypoints=web"
  - "traefik.http.routers.omni2-ws.middlewares=auth-forward"  # ✅ ADD THIS
  - "traefik.http.routers.omni2-ws.service=omni2"
  - "traefik.http.routers.omni2-ws.priority=200"
```

**Application Code:**

```python
from fastapi import WebSocket, Header

@router.websocket("/ws/mcp-status")
async def websocket_mcp_status(
    websocket: WebSocket,
    x_user_id: str = Header(None),
    x_user_role: str = Header(None)
):
    """
    WebSocket endpoint with Traefik ForwardAuth.
    User info injected by auth service via headers.
    """
    if not x_user_id:
        await websocket.close(code=1008, reason="Authentication required")
        return
    
    user_id = x_user_id
    user_role = x_user_role or "read_only"
    
    # ... rest of code
```

---

## 📋 Implementation Checklist

- [ ] Choose authentication method (JWT recommended)
- [ ] Update `websocket.py` to validate tokens/sessions
- [ ] Update frontend to pass authentication credentials
- [ ] Add rate limiting to prevent connection spam
- [ ] Add connection limits per user
- [ ] Log all WebSocket connections for audit
- [ ] Add role-based filtering (admins see all, users see limited data)
- [ ] Test authentication with valid/invalid tokens
- [ ] Test connection rejection scenarios
- [ ] Update documentation

---

## 🔍 Testing Authentication

### Test 1: Unauthenticated Connection (Should Fail)
```bash
# Without token - should be rejected
wscat -c ws://localhost:8000/ws/mcp-status
# Expected: Connection closed with code 1008
```

### Test 2: Invalid Token (Should Fail)
```bash
# With invalid token - should be rejected
wscat -c "ws://localhost:8000/ws/mcp-status?token=invalid_token_123"
# Expected: Connection closed with code 1008
```

### Test 3: Valid Token (Should Succeed)
```bash
# With valid JWT token - should connect
wscat -c "ws://localhost:8000/ws/mcp-status?token=<valid_jwt_token>"
# Expected: Connection established, receives initial_status message
```

---

## 📚 References

- **Traefik ForwardAuth**: https://doc.traefik.io/traefik/middlewares/http/forwardauth/
- **FastAPI WebSocket Security**: https://fastapi.tiangolo.com/advanced/websockets/
- **JWT Best Practices**: https://tools.ietf.org/html/rfc8725
- **WebSocket Security**: https://owasp.org/www-community/vulnerabilities/WebSocket_Security

---

## 🎯 Conclusion

The WebSocket endpoint is **intentionally unsecured** with a TODO comment acknowledging this. This was likely done for rapid development but should be addressed before production deployment.

**Immediate Action Required:**
1. Implement JWT token authentication (Option 1)
2. Add connection rate limiting
3. Add audit logging for all connections
4. Test thoroughly with valid/invalid credentials

**Priority**: 🟡 **MEDIUM** - Should be fixed before production, but not a critical vulnerability in development environment.
