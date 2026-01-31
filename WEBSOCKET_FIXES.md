# WebSocket Fixes Applied

## Issues Found:
1. **Code 1011** - Missing `broadcaster` variable in OMNI2 WebSocket endpoint
2. **Failed to fetch** - Frontend calling wrong API URLs (port 8090 instead of 8500)
3. **Missing routes** - Dashboard backend didn't have event proxy routes

---

## Fixes Applied:

### 1. OMNI2 WebSocket (app/routers/websocket.py)
✅ Added missing `broadcaster = get_websocket_broadcaster()` line
- This was causing NameError and code 1011 disconnections

### 2. Dashboard Backend (backend/app/routers/events.py)
✅ Created new events proxy router with 3 endpoints:
- `GET /api/v1/events/websocket/debug` - Proxy to OMNI2
- `POST /api/v1/events/test/broadcast` - Proxy to OMNI2  
- `GET /api/v1/events/metadata` - Proxy to OMNI2

### 3. Dashboard Backend (backend/app/main.py)
✅ Added events router to main app

### 4. Frontend (frontend/src/app/live-updates/page.tsx)
✅ Fixed API URLs:
- Changed: `http://localhost:8090/api/v1/events/*`
- To: `http://localhost:8500/api/v1/events/*`

---

## Test Now:

1. **Restart services** (if needed):
   ```bash
   docker-compose restart omni2 dashboard-backend
   ```

2. **Open Live Updates**: http://localhost:3000/live-updates

3. **Should see**:
   - ✅ Connected (green status)
   - ✅ No more code 1011 errors
   - ✅ Debug Info button works
   - ✅ Test Event button works

4. **Check logs**:
   - Browser console: Should show subscription confirmed
   - Dashboard backend: Should show successful proxy
   - OMNI2: Should show connection accepted

---

## Expected Flow:

```
Browser → Dashboard Backend (8500) → Traefik (80) → OMNI2 (8000)
   ✅          ✅ Proxy                ✅ Auth         ✅ Events
```

All communication goes through Traefik for authentication!
