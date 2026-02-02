# WebSocket Chat Architecture - CORRECTED

## Overview
Frontend now properly connects to Dashboard Backend, which proxies to OMNI2 via Traefik.

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (Frontend)                                         │
│  - ChatWidget.tsx                                           │
│  - test_ws_chat.html                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ ws://localhost:8091/ws/chat?token=xxx
                     │ (Dashboard Backend Port)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Dashboard Backend (Proxy Layer)                            │
│  - Port: 8091                                               │
│  - Endpoint: /ws/chat                                       │
│  - File: dashboard/backend/app/routers/websocket.py         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ ws://host.docker.internal:8090/ws/chat
                     │ (Via Traefik - Authorization: Bearer xxx)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Traefik (Reverse Proxy)                                    │
│  - Port: 8090                                               │
│  - Routes to OMNI2 Backend                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Internal routing
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  OMNI2 Backend (Main Service)                               │
│  - Port: 8000 (internal)                                    │
│  - Endpoint: /ws/chat                                       │
│  - File: omni2/app/routers/websocket_chat.py                │
│  - Features:                                                │
│    • User authentication (x-user-id header)                 │
│    • Conversation tracking (conversation_id)                │
│    • LLM streaming                                          │
│    • Tool call tracking                                     │
└─────────────────────────────────────────────────────────────┘
```

## Changes Made

### 1. Dashboard Backend - Added `/ws/chat` Endpoint
**File:** `dashboard/backend/app/routers/websocket.py`

```python
@router.websocket("/ws/chat")
async def chat_websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    # Accepts token as query parameter
    # Proxies to: ws://host.docker.internal:8090/ws/chat
    # Forwards Authorization header to Traefik
```

### 2. Frontend ChatWidget - Updated Connection
**File:** `dashboard/frontend/src/components/ChatWidget.tsx`

**Before:**
```typescript
const wsUrl = `ws://localhost/ws/chat`;
```

**After:**
```typescript
const wsUrl = `ws://localhost:8091/ws/chat?token=${token}`;
```

### 3. Test HTML - Updated Connection
**File:** `omni2/test_ws_chat.html`

**Before:**
```javascript
ws = new WebSocket('ws://localhost/ws/chat');
```

**After:**
```javascript
ws = new WebSocket(`ws://localhost:8091/ws/chat?token=${token}`);
```

## Connection Flow

1. **User Opens Chat**
   - Frontend retrieves JWT token from localStorage
   - Token obtained from dashboard login

2. **Frontend → Dashboard Backend**
   - Connects to: `ws://localhost:8091/ws/chat?token=xxx`
   - Dashboard backend receives token as query parameter

3. **Dashboard Backend → Traefik**
   - Connects to: `ws://host.docker.internal:8090/ws/chat`
   - Adds header: `Authorization: Bearer xxx`

4. **Traefik → OMNI2 Backend**
   - Routes to OMNI2 internal service
   - Traefik adds `x-user-id` header from JWT

5. **OMNI2 Backend Processing**
   - Validates user via `x-user-id` header
   - Creates `conversation_id` for session
   - Loads user context (role, permissions, MCP access)
   - Streams LLM responses back through chain

## Message Protocol

### Client → Server
```json
{
  "type": "message",
  "text": "Hello, what can you do?"
}
```

### Server → Client

**Welcome Message:**
```json
{
  "type": "welcome",
  "text": "Welcome! I'm OMNI2 Assistant..."
}
```

**Streaming Tokens:**
```json
{
  "type": "token",
  "text": "H"
}
```

**Completion:**
```json
{
  "type": "done",
  "result": {
    "tokens_used": 150,
    "tools_used": ["database_query"],
    "tool_calls": 2
  }
}
```

**Error:**
```json
{
  "type": "error",
  "error": "Rate limit exceeded"
}
```

## Port Configuration

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 3001 | Next.js dev server |
| Dashboard Backend | 8091 | FastAPI proxy layer |
| Traefik | 8090 | Reverse proxy |
| OMNI2 Backend | 8000 | Main service (internal) |

## Security

1. **Token Authentication**
   - JWT token required for connection
   - Token passed as query parameter to dashboard backend
   - Dashboard backend forwards as Authorization header

2. **User Validation**
   - Traefik extracts user_id from JWT
   - OMNI2 validates user permissions
   - Checks user blocked status
   - Validates account active status

3. **Conversation Isolation**
   - Each WebSocket connection gets unique conversation_id
   - Messages tracked per conversation
   - Flow tracking for audit trail

## Benefits of This Architecture

1. **Security**: Frontend never directly accesses Traefik
2. **Flexibility**: Dashboard backend can add middleware/logging
3. **Consistency**: Same pattern as `/ws` endpoint
4. **Maintainability**: Single point of configuration
5. **Debugging**: Easier to trace requests through layers

## Testing

### Test with HTML File
1. Login to dashboard (http://localhost:3001)
2. Open browser console
3. Copy token: `localStorage.getItem('token')`
4. Open `test_ws_chat.html`
5. Click "Connect"
6. Send messages

### Test with ChatWidget
1. Login to dashboard
2. Click chat bubble (bottom right)
3. Toggle WebSocket mode (icon in header)
4. Send messages
5. Check conversation tracking in database

## Troubleshooting

### Connection Refused
- Check dashboard backend is running on port 8091
- Verify Traefik is running on port 8090
- Check OMNI2 backend is running

### Authentication Failed
- Verify token in localStorage
- Check token expiration
- Ensure Traefik JWT middleware configured

### No Response
- Check OMNI2 backend logs
- Verify user has MCP access
- Check usage limits not exceeded
