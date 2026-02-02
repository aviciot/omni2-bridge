# WebSocket Chat Implementation - COMPLETE

## ✅ Implementation Status: DONE

## What Was Implemented

### 1. Database Changes
- Added `conversation_id UUID` column to `omni2.interaction_flows`
- Added index `idx_flows_conversation_id` for performance
- **Status**: ✅ Applied

### 2. Flow Tracker Service
- Updated `save_to_db()` method to accept optional `conversation_id` parameter
- Stores conversation_id when provided (WebSocket chat)
- Falls back to NULL for SSE requests (backward compatible)
- **File**: `app/services/flow_tracker.py`
- **Status**: ✅ Updated

### 3. WebSocket Chat Router
- Created new endpoint `/ws/chat`
- Generates `conversation_id` on WebSocket connect
- All messages in same connection share same `conversation_id`
- Implements all logic from `/ask/stream`:
  - Auth check (X-User-Id from Traefik)
  - User context loading
  - Block check
  - Usage limit check
  - Welcome message
  - MCP permissions
  - Tool restrictions
  - Flow tracking (all checkpoints)
  - LLM streaming
- **File**: `app/routers/websocket_chat.py`
- **Status**: ✅ Created

### 4. Router Registration
- Registered `websocket_chat` router in main.py
- **File**: `app/main.py`
- **Status**: ✅ Updated

### 5. Traefik Configuration
- Added route for `/ws/chat` with ForwardAuth
- Priority 210 (higher than `/ws` at 200)
- **File**: `docker-compose.yml`
- **Status**: ✅ Updated

### 6. Service Restart
- Restarted `omni2-bridge` container
- **Status**: ✅ Done

## How It Works

### Connection Flow
```
1. Client connects to ws://omni2/ws/chat
2. Traefik validates JWT → Injects X-User-Id header
3. WebSocket accepts connection
4. Generate conversation_id = UUID
5. Send welcome message
6. Enter message loop
```

### Message Flow
```
Client sends: {"type": "message", "text": "Hello"}
↓
Server processes:
  - Check usage limits
  - Generate session_id = UUID (per message)
  - Log flow checkpoints
  - Stream LLM response
  - Save to DB with conversation_id
↓
Server sends: {"type": "token", "text": "H"}
              {"type": "token", "text": "i"}
              {"type": "done", "result": {...}}
```

### Conversation Tracking
- **conversation_id**: Generated once per WebSocket connection
- **session_id**: Generated per message
- **Relationship**: One conversation → Many sessions (messages)

## Testing

### Connect to WebSocket
```javascript
const ws = new WebSocket('ws://localhost/ws/chat', {
  headers: {
    'Authorization': 'Bearer YOUR_JWT_TOKEN'
  }
});

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};

// Send message
ws.send(JSON.stringify({
  type: 'message',
  text: 'Hello, how are you?'
}));
```

### Verify in Database
```sql
-- Get all conversations for a user
SELECT DISTINCT conversation_id, 
       MIN(created_at) as started_at,
       COUNT(*) as message_count
FROM omni2.interaction_flows
WHERE user_id = 1 AND conversation_id IS NOT NULL
GROUP BY conversation_id
ORDER BY started_at DESC;

-- Get all messages in a conversation
SELECT session_id, created_at, flow_data
FROM omni2.interaction_flows
WHERE conversation_id = 'YOUR_CONVERSATION_ID'
ORDER BY created_at;
```

## Analytics Integration

The existing analytics page at `/analytics/flow-history` will now show:
- **Individual requests** (session_id, conversation_id = NULL) - from SSE `/ask/stream`
- **Conversation groups** (multiple session_ids, same conversation_id) - from WebSocket `/ws/chat`

To add conversation view to analytics, update the query to group by `conversation_id`.

## Benefits

✅ **Natural conversation tracking** - WebSocket connection = conversation
✅ **Backward compatible** - SSE `/ask/stream` still works (conversation_id = NULL)
✅ **Same security** - Uses Traefik ForwardAuth like existing endpoints
✅ **Same logic** - All auth, permissions, flow tracking from `/ask/stream`
✅ **Persistent connection** - True bidirectional chat
✅ **Analytics ready** - All data stored with conversation_id for grouping

## Next Steps

1. **Test the endpoint** - Connect via WebSocket client
2. **Update analytics** - Add conversation grouping view
3. **Build chat UI** - Create frontend that uses `/ws/chat`
4. **Monitor usage** - Check conversation_id is being stored correctly

## Files Changed

1. `app/routers/websocket_chat.py` - NEW
2. `app/services/flow_tracker.py` - UPDATED
3. `app/main.py` - UPDATED
4. `docker-compose.yml` - UPDATED
5. Database: `omni2.interaction_flows` - UPDATED (added conversation_id column)

## Rollback (if needed)

```sql
-- Remove conversation_id column
ALTER TABLE omni2.interaction_flows DROP COLUMN conversation_id;
DROP INDEX omni2.idx_flows_conversation_id;
```

Then revert code changes and restart omni2-bridge.
