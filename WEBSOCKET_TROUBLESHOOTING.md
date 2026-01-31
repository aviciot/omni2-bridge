# WebSocket Troubleshooting Guide

## Changes Made

### 1. Frontend (Dashboard)
- ✅ Added detailed console logging for all WebSocket events
- ✅ Added auto-reconnection (3 second delay)
- ✅ Logs connection state, messages, errors, and close events

### 2. Backend Proxy (Dashboard Backend)
- ✅ Added detailed logging for message forwarding
- ✅ Better error handling with specific error types
- ✅ Logs connection lifecycle

### 3. OMNI2 WebSocket
- ✅ Added detailed logging for all actions
- ✅ Logs subscription creation, message handling
- ✅ Better cleanup logging

---

## How to Check Logs

### Browser Console (F12)
Look for these log patterns:
```
🔌 Connecting to WebSocket...
✅ WebSocket connected
📤 Sending subscription: {...}
✅ Subscription confirmed: sub_abc123
📨 Message received: mcp_status_change {...}
🔌 WebSocket closed: {code: 1006, reason: "", wasClean: false}
🔄 Reconnecting in 3 seconds...
```

### Dashboard Backend Logs
```bash
docker logs dashboard-backend -f
```
Look for:
```
🔌 WebSocket connection accepted
🔗 Connecting to OMNI2 via Traefik
✅ Connected to OMNI2 WebSocket
📨 Forwarding message from OMNI2 to client
❌ Error forwarding from OMNI2
🔌 WebSocket connection closed
```

### OMNI2 Logs
```bash
docker logs omni2 -f
```
Look for:
```
🔌 WebSocket connection accepted user_id=admin
✅ WebSocket client connected conn_id=admin_123
🎯 Action received action=subscribe
✅ Subscription created sub_id=sub_abc123
🔌 WebSocket client disconnected
🧹 WebSocket cleanup complete
```

---

## Common Disconnection Causes

### 1. **Code 1006 (Abnormal Closure)**
- Network issue or proxy timeout
- Check: Dashboard backend → Traefik → OMNI2 connection
- Solution: Check Traefik logs, verify network connectivity

### 2. **Code 1008 (Policy Violation)**
- Authentication failure
- Check: Token validity, Traefik ForwardAuth headers
- Solution: Verify token in localStorage, check auth_service

### 3. **Code 1011 (Internal Error)**
- Backend error during message processing
- Check: Dashboard backend or OMNI2 logs for exceptions
- Solution: Fix the error in backend code

### 4. **Periodic Disconnects**
- Possible timeout or keepalive issue
- Check: How often it disconnects (every 30s, 60s, 5min?)
- Solution: May need to implement ping/pong keepalive

---

## Testing Steps

1. **Open Live Updates page**
   - Check browser console for connection logs

2. **Click "Debug Info"**
   - Should show your connection in active_connections
   - Should show subscription details

3. **Click "Test Event"**
   - Should receive 2 events within 1 second
   - Check all 3 logs (browser, dashboard backend, OMNI2)

4. **Wait 5 minutes**
   - Does it disconnect?
   - Check close code in browser console
   - Check backend logs for error

5. **If disconnected**
   - Should auto-reconnect after 3 seconds
   - Should re-subscribe automatically

---

## Next Steps

After checking logs, report:
1. **Close code** from browser console (e.g., 1006, 1008, 1011)
2. **Error messages** from any of the 3 log sources
3. **Frequency** - How often does it disconnect?
4. **Pattern** - Does it happen during specific actions?

This will help identify the root cause.
