# WebSocket Chat Implementation Plan

## Objective
Add `/ws/chat` WebSocket endpoint for LLM conversations with automatic conversation tracking

## References
- **Source**: `/api/v1/chat/ask/stream` (SSE endpoint in `app/routers/chat.py`)
- **Pattern**: `/ws` (existing WebSocket in `app/routers/websocket.py`)

## Key Features to Port from `/ask/stream`
1. ✅ Auth check (X-User-Id from Traefik)
2. ✅ User context loading
3. ✅ Block check
4. ✅ Usage limit check
5. ✅ Welcome message
6. ✅ MCP permissions
7. ✅ Tool restrictions
8. ✅ Flow tracking (all checkpoints)
9. ✅ LLM streaming
10. ✅ **NEW**: Conversation tracking (WebSocket connection ID = conversation_id)

## Database Changes
```sql
ALTER TABLE omni2.interaction_flows ADD COLUMN conversation_id UUID;
CREATE INDEX idx_flows_conversation_id ON omni2.interaction_flows(conversation_id);
```

## Implementation Steps

### 1. Database Migration
- Add conversation_id column
- Add index for performance

### 2. Update Flow Tracker Service
- Add conversation_id parameter to save_to_db()
- Store conversation_id alongside session_id

### 3. Create WebSocket Chat Router
**File**: `app/routers/websocket_chat.py`
- WebSocket endpoint `/ws/chat`
- Generate conversation_id on connect
- Message loop for bidirectional chat
- Reuse all logic from `/ask/stream`

### 4. Add Traefik Route
**File**: `docker-compose.yml`
- Add route for `/ws/chat` with ForwardAuth

### 5. Register Router
**File**: `app/main.py`
- Include websocket_chat router

## Message Protocol
```json
// Client → Server
{"type": "message", "text": "Hello"}

// Server → Client
{"type": "welcome", "text": "Welcome message..."}
{"type": "token", "text": "H"}
{"type": "token", "text": "i"}
{"type": "done", "result": {"tokens_used": 100}}
{"type": "error", "error": "Error message"}
```

## Conversation Tracking
- **conversation_id**: Generated when WebSocket connects (UUID)
- **session_id**: Generated per message (UUID)
- **Relationship**: One conversation has many sessions (messages)

## Analytics Query
```sql
-- Get all messages in a conversation
SELECT * FROM omni2.interaction_flows 
WHERE conversation_id = 'xxx' 
ORDER BY created_at;

-- Get all conversations for a user
SELECT DISTINCT conversation_id, MIN(created_at) as started_at, COUNT(*) as message_count
FROM omni2.interaction_flows
WHERE user_id = 1
GROUP BY conversation_id
ORDER BY started_at DESC;
```

## Testing
1. Connect to `/ws/chat`
2. Send multiple messages
3. Verify all messages have same conversation_id
4. Disconnect and reconnect
5. Verify new conversation_id is generated
