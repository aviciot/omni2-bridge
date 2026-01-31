# WebSocket Authentication Testing Guide

## Prerequisites

1. **Install websockets library:**
   ```bash
   pip install websockets
   ```

2. **Ensure OMNI2 is running:**
   ```bash
   cd omni2
   docker-compose up -d
   ```

3. **Check logs:**
   ```bash
   docker logs -f omni2-bridge
   ```

---

## Test 1: No Token (Should Fail)

### Using Python Script
```bash
python test_websocket_auth.py
```

### Using Browser Console
```javascript
// Open browser console on login page
const ws = new WebSocket('ws://localhost:8000/ws/mcp-status');
ws.onopen = () => console.log('Connected');
ws.onerror = (e) => console.error('Error:', e);
ws.onclose = (e) => console.log('Closed:', e.code, e.reason);

// Expected: Connection closed with code 1008
// Reason: "Authentication required: No token provided"
```

### Using wscat (if installed)
```bash
npm install -g wscat
wscat -c ws://localhost:8000/ws/mcp-status

# Expected: Connection closed with code 1008
```

---

## Test 2: Invalid Token (Should Fail)

### Using Browser Console
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/mcp-status?token=invalid_token_123');
ws.onopen = () => console.log('Connected');
ws.onerror = (e) => console.error('Error:', e);
ws.onclose = (e) => console.log('Closed:', e.code, e.reason);

// Expected: Connection closed with code 1008
// Reason: "Authentication failed: Invalid or expired token"
```

### Using wscat
```bash
wscat -c "ws://localhost:8000/ws/mcp-status?token=invalid_token_123"

# Expected: Connection closed with code 1008
```

---

## Test 3: Valid Token (Should Succeed)

### Step 1: Get Valid JWT Token

**Option A: From Auth Service (if running)**
```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@company.com", "password": "your_password"}'

# Response will contain: {"access_token": "eyJ..."}
```

**Option B: Generate Test Token**
```python
# Create test_generate_token.py
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "change-this-in-production"  # From .env

payload = {
    "sub": "test@company.com",
    "email": "test@company.com",
    "role": "admin",
    "iat": datetime.utcnow(),
    "exp": datetime.utcnow() + timedelta(hours=1)
}

token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
print(f"Token: {token}")
```

Run:
```bash
pip install pyjwt
python test_generate_token.py
```

### Step 2: Connect with Valid Token

**Using Browser Console:**
```javascript
const token = 'YOUR_JWT_TOKEN_HERE';
const ws = new WebSocket(`ws://localhost:8000/ws/mcp-status?token=${token}`);

ws.onopen = () => {
    console.log('✅ Connected successfully!');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onerror = (e) => {
    console.error('❌ Error:', e);
};

ws.onclose = (e) => {
    console.log('Closed:', e.code, e.reason);
};

// Test ping/pong
setTimeout(() => {
    ws.send('ping');
    console.log('Sent: ping');
}, 2000);
```

**Using Python Script:**
```bash
# Update VALID_TOKEN in test_websocket_auth.py
python test_websocket_auth.py
```

**Expected Results:**
- ✅ Connection accepted
- ✅ Receives `initial_status` message with MCP list
- ✅ Ping/pong works
- ✅ Receives real-time updates

---

## Test 4: Insufficient Permissions (Should Fail)

### Step 1: Generate Token with read_only Role
```python
# Modify test_generate_token.py
payload = {
    "sub": "readonly@company.com",
    "email": "readonly@company.com",
    "role": "read_only",  # ← Changed to read_only
    "iat": datetime.utcnow(),
    "exp": datetime.utcnow() + timedelta(hours=1)
}

token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
print(f"Token: {token}")
```

### Step 2: Try to Connect
```javascript
const token = 'YOUR_READ_ONLY_TOKEN_HERE';
const ws = new WebSocket(`ws://localhost:8000/ws/mcp-status?token=${token}`);

ws.onclose = (e) => {
    console.log('Closed:', e.code, e.reason);
};

// Expected: Connection closed with code 1008
// Reason: "Insufficient permissions: Role 'read_only' not authorized"
```

---

## Test 5: Verify Logs

Check OMNI2 logs to see authentication events:

```bash
docker logs -f omni2-bridge | grep WebSocket
```

**Expected Log Entries:**

```json
// No token
{"level": "warning", "message": "WebSocket connection rejected: No token provided"}

// Invalid token
{"level": "warning", "message": "WebSocket connection rejected: Invalid token"}

// Insufficient permissions
{"level": "warning", "message": "WebSocket connection rejected: User readonly@company.com has insufficient permissions (role: read_only)"}

// Successful connection
{"level": "info", "message": "WebSocket client connected", "conn_id": "abc123", "user": "admin@company.com", "role": "admin"}
```

---

## Test 6: Dashboard Integration Test

### Update Dashboard Frontend (if needed)

**File:** `dashboard/frontend/src/stores/authStore.ts`

```typescript
export const connectWebSocket = () => {
  const token = localStorage.getItem('jwt_token');
  
  if (!token) {
    console.error('No JWT token found - cannot connect to WebSocket');
    return;
  }
  
  const ws = new WebSocket(`ws://localhost:8000/ws/mcp-status?token=${token}`);
  
  ws.onopen = () => {
    console.log('✅ WebSocket connected with authentication');
  };
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleMCPStatusUpdate(data);
  };
  
  ws.onerror = (error) => {
    console.error('❌ WebSocket error:', error);
  };
  
  ws.onclose = (event) => {
    console.log('WebSocket closed:', event.code, event.reason);
    if (event.code === 1008) {
      console.error('Authentication failed - redirecting to login');
      // Redirect to login page
    }
  };
};
```

---

## Troubleshooting

### Issue: "Connection refused"
**Solution:** Ensure OMNI2 is running:
```bash
docker ps | grep omni2-bridge
```

### Issue: "Invalid token" with valid token
**Solution:** Check SECRET_KEY matches between token generation and OMNI2:
```bash
docker exec omni2-bridge env | grep SECRET_KEY
```

### Issue: Auth service not responding
**Solution:** Check if auth service is running:
```bash
docker ps | grep auth
# If not running, WebSocket will reject all tokens
```

### Issue: Token expired
**Solution:** Generate new token with longer expiration:
```python
"exp": datetime.utcnow() + timedelta(hours=24)  # 24 hours
```

---

## Success Criteria

✅ **Test 1:** Connection without token is rejected (code 1008)
✅ **Test 2:** Connection with invalid token is rejected (code 1008)
✅ **Test 3:** Connection with valid admin token succeeds
✅ **Test 4:** Connection with read_only token is rejected (code 1008)
✅ **Test 5:** Logs show authentication events
✅ **Test 6:** Dashboard can connect after login

---

## Security Verification

After implementing authentication, verify:

1. **Login page cannot connect to WebSocket** ✅
2. **Invalid tokens are rejected** ✅
3. **Expired tokens are rejected** ✅
4. **Insufficient permissions are rejected** ✅
5. **Only authenticated users see MCP status** ✅

---

## Next Steps

After successful testing:

1. Update dashboard frontend to pass JWT token
2. Add connection rate limiting (max 5 connections per user)
3. Add audit logging for all WebSocket connections
4. Monitor for authentication failures in production
5. Set up alerts for suspicious connection attempts
