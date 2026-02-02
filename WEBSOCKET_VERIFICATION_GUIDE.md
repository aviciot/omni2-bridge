# WebSocket Chat Verification Guide

## New Logging Added

### Dashboard Backend Proxy (`omni2-dashboard-backend`)
```
[WS-CHAT-PROXY] 🔌 New WebSocket chat connection request
[WS-CHAT-PROXY] ✓ Token received: <token>...
[WS-CHAT-PROXY] 🔗 Connecting to OMNI2: ws://host.docker.internal:8090/ws/chat
[WS-CHAT-PROXY] ✅ Connected to OMNI2 Chat WebSocket
[WS-CHAT-PROXY] 🔌 WebSocket chat connection closed
```

### OMNI2 Backend (`omni2-bridge`)
```
[WS-CHAT] 🔌 New WebSocket chat connection
[WS-CHAT] ✓ User ID: 1
[WS-CHAT] 👤 User: avi@omni.com, Role: super_admin
[WS-CHAT] ✅ WebSocket connection accepted
[WS-CHAT] 🆔 Conversation started - ID: <uuid>, User: avi@omni.com
[WS-CHAT] 💬 New message - Session: <session_uuid>, Conversation: <conv_uuid>
[WS-CHAT] ✅ Message complete - Session: <session_uuid>, Conversation: <conv_uuid>
[WS-CHAT] 🔌 User disconnected - Conversation: <uuid>, User: avi@omni.com
[WS-CHAT] 🆔 Conversation ended - ID: <uuid>
```

## How to Test

### 1. Enable WebSocket Mode in ChatWidget
1. Login to dashboard: http://localhost:3001
2. Click purple chat bubble (bottom-right)
3. Look at header - first icon (three dots in circle)
4. **Click it** - should have white background when enabled
5. Send a test message

### 2. Check Dashboard Backend Logs
```bash
docker logs omni2-dashboard-backend --tail 50 | findstr "WS-CHAT-PROXY"
```

**Expected output:**
```
[WS-CHAT-PROXY] 🔌 New WebSocket chat connection request
[WS-CHAT-PROXY] ✓ Token received: eyJ...
[WS-CHAT-PROXY] 🔗 Connecting to OMNI2: ws://host.docker.internal:8090/ws/chat
[WS-CHAT-PROXY] ✅ Connected to OMNI2 Chat WebSocket
```

### 3. Check OMNI2 Backend Logs
```bash
docker logs omni2-bridge --tail 50 | findstr "WS-CHAT"
```

**Expected output:**
```
[WS-CHAT] 🔌 New WebSocket chat connection
[WS-CHAT] ✓ User ID: 1
[WS-CHAT] 👤 User: avi@omni.com, Role: super_admin
[WS-CHAT] ✅ WebSocket connection accepted
[WS-CHAT] 🆔 Conversation started - ID: 12345678-1234-1234-1234-123456789abc, User: avi@omni.com
[WS-CHAT] 💬 New message - Session: abcd1234-..., Conversation: 12345678-...
[WS-CHAT] ✅ Message complete - Session: abcd1234-..., Conversation: 12345678-...
```

### 4. Check Database
```bash
docker exec omni_pg_db psql -U omni -d omni -c "SELECT session_id, conversation_id, user_id, created_at FROM omni2.interaction_flows WHERE conversation_id IS NOT NULL ORDER BY created_at DESC LIMIT 5;"
```

**Expected output:**
```
              session_id              |           conversation_id            | user_id |         created_at         
--------------------------------------+--------------------------------------+---------+----------------------------
 abcd1234-5678-90ab-cdef-123456789abc | 12345678-1234-1234-1234-123456789abc |       1 | 2026-02-01 12:00:00.123456
```

## Troubleshooting

### If you see NO logs with "WS-CHAT":
- You're using SSE mode, not WebSocket mode
- Click the toggle button in chat header (first icon)
- Should have white background when WebSocket is enabled

### If you see "WS-CHAT-PROXY" but NO "WS-CHAT":
- Dashboard backend can't reach OMNI2
- Check Traefik is running: `docker ps | findstr traefik`
- Check OMNI2 is running: `docker ps | findstr omni2-bridge`

### If conversation_id is still NULL in database:
- WebSocket endpoint not being called
- Check you're using `/ws/chat` not `/ws`
- Verify toggle button is enabled (white background)

## Success Indicators

✅ Dashboard backend logs show `[WS-CHAT-PROXY]`
✅ OMNI2 backend logs show `[WS-CHAT] 🆔 Conversation started`
✅ Database shows `conversation_id` is NOT NULL
✅ Multiple messages share same `conversation_id`
