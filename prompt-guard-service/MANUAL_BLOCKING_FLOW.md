# Manual User Blocking Flow (from UI)

## Complete Flow Diagram

```
Admin UI (http://localhost:3001/iam/chat-config)
    ↓
[Admin clicks "Block User"]
    ↓
PUT /api/v1/iam/chat-config/users/{user_id}/block
    {
        "is_blocked": true,
        "block_reason": "Inappropriate behavior",
        "custom_block_message": "Your account has been suspended"
    }
    ↓
Backend (iam_chat_config.py)
    ↓
1. Insert/Update omni2.user_blocks table
    ↓
2. Commit to database
    ↓
3. Publish to Redis: "user_blocked" channel
    {
        "user_id": 123,
        "custom_message": "Your account has been suspended",
        "blocked_by": admin_user_id,
        "timestamp": "..."
    }
    ↓
ws_connection_manager (listening on "user_blocked")
    ↓
4. Receives Redis message
    ↓
5. Finds all active WebSocket connections for user_id
    ↓
6. Sends custom message to user:
    {
        "type": "blocked",
        "message": "Your account has been suspended"
    }
    ↓
7. Closes all WebSocket connections (code: 1008)
    ↓
User disconnected immediately (real-time)
```

## Database Tables

### omni2.user_blocks
```sql
user_id              INTEGER PRIMARY KEY
is_blocked           BOOLEAN (default: false)
block_reason         TEXT (admin notes)
blocked_at           TIMESTAMP (when blocked)
blocked_by           INTEGER (admin user_id)
custom_block_message TEXT (message shown to user)
```

### Example Row
```
user_id: 123
is_blocked: true
block_reason: "Multiple prompt injection attempts"
blocked_at: 2026-02-14 11:00:00
blocked_by: 1 (admin)
custom_block_message: "Your account has been suspended due to security violations"
```

## API Endpoints

### 1. Get Block Status
```bash
GET /api/v1/iam/chat-config/users/{user_id}/block

Response:
{
    "user_id": 123,
    "is_blocked": true,
    "block_reason": "Multiple prompt injection attempts",
    "custom_block_message": "Your account has been suspended",
    "blocked_at": "2026-02-14T11:00:00",
    "blocked_by": 1
}
```

### 2. Block User
```bash
PUT /api/v1/iam/chat-config/users/{user_id}/block
Content-Type: application/json

{
    "is_blocked": true,
    "block_reason": "Inappropriate behavior",
    "custom_block_message": "Your account has been suspended"
}

Response:
{
    "success": true,
    "message": "User blocked successfully"
}
```

### 3. Unblock User
```bash
PUT /api/v1/iam/chat-config/users/{user_id}/block
Content-Type: application/json

{
    "is_blocked": false
}

Response:
{
    "success": true,
    "message": "User unblocked successfully"
}
```

## Redis Pub/Sub

### Channel: `user_blocked`

**Published When:** Admin blocks user via UI

**Message Format:**
```json
{
    "user_id": 123,
    "custom_message": "Your account has been suspended",
    "blocked_by": 1,
    "timestamp": "1707912345.678"
}
```

**Subscribers:**
- `ws_connection_manager` - Disconnects active WebSocket connections

## WebSocket Disconnection

### ws_connection_manager Flow

1. **Listens** to Redis `user_blocked` channel
2. **Receives** block event with user_id
3. **Finds** all active WebSocket connections for that user
4. **Sends** custom message to user:
   ```json
   {
       "type": "blocked",
       "message": "Your account has been suspended"
   }
   ```
5. **Waits** 0.5 seconds (for message delivery)
6. **Closes** WebSocket connection (code: 1008 - Policy Violation)
7. **Removes** from active connections list

### User Experience

1. User is chatting via WebSocket
2. Admin blocks user in UI
3. **Within 1 second:**
   - User receives message: "Your account has been suspended"
   - WebSocket connection closes
   - Chat UI shows disconnection
4. User tries to reconnect
5. Connection rejected (blocked check in websocket_chat.py)

## Blocking Check on Connection

### websocket_chat.py
```python
# Check if user is blocked
is_blocked, block_reason = await context_service.check_user_blocked(user_id)
if is_blocked:
    logger.warning(f"[WS-CHAT] 🚫 User {user_id} is blocked: {block_reason}")
    await websocket.close(code=1008, reason=f"Access blocked: {block_reason}")
    return
```

### context_service.check_user_blocked()
```python
async def check_user_blocked(self, user_id: int) -> tuple[bool, str]:
    """Check if user is blocked."""
    result = await self.db.execute(
        text(
            "SELECT is_blocked, custom_block_message "
            "FROM omni2.user_blocks "
            "WHERE user_id = :user_id AND is_blocked = true"
        ),
        {"user_id": user_id}
    )
    row = result.fetchone()
    
    if row:
        return (True, row.custom_block_message or "Access blocked")
    return (False, None)
```

## Real-time Behavior

### Scenario 1: User Already Connected
```
1. User connected via WebSocket
2. Admin blocks user
3. Redis pub/sub triggers
4. ws_connection_manager disconnects user
5. User sees message + disconnection
6. Total time: < 1 second
```

### Scenario 2: User Tries to Connect
```
1. User tries to connect
2. WebSocket accepts connection
3. Checks user_blocks table
4. Finds is_blocked = true
5. Closes connection immediately
6. User sees: "Access blocked: {custom_message}"
```

## Integration with Prompt Guard

### Proposed Flow

```python
# In websocket_chat.py after guard detection

if session_violations >= 5:  # Configurable threshold
    # Use existing blocking mechanism
    await db.execute(
        text(
            "INSERT INTO omni2.user_blocks "
            "(user_id, is_blocked, block_reason, custom_block_message, blocked_by) "
            "VALUES (:user_id, true, :reason, :message, NULL) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "is_blocked = true, "
            "block_reason = :reason, "
            "custom_block_message = :message, "
            "blocked_at = NOW()"
        ),
        {
            "user_id": user_id,
            "reason": f"Automated block: {session_violations} prompt injection attempts",
            "message": "Your account has been suspended due to security policy violations"
        }
    )
    await db.commit()
    
    # Publish to Redis (same as manual block)
    await redis.publish(
        "user_blocked",
        json.dumps({
            "user_id": user_id,
            "custom_message": "Your account has been suspended due to security policy violations",
            "blocked_by": None,  # Automated
            "timestamp": time.time()
        })
    )
    
    # ws_connection_manager will disconnect user automatically
    return
```

## Admin Unblock Flow

```
Admin UI → Unblock button
    ↓
PUT /api/v1/iam/chat-config/users/{user_id}/block
    {"is_blocked": false}
    ↓
DELETE FROM omni2.user_blocks WHERE user_id = X
    ↓
User can reconnect immediately
```

## Key Benefits

✅ **Real-time** - User disconnected within 1 second
✅ **Centralized** - Single table for all blocks (manual + automated)
✅ **Auditable** - blocked_by, blocked_at, block_reason tracked
✅ **Reversible** - Admin can unblock via UI
✅ **Custom Messages** - Different messages for different reasons
✅ **No Reboot** - Works via Redis pub/sub
✅ **Existing Infrastructure** - Uses ws_connection_manager

## Testing

### Test Manual Block
```bash
# Block user
curl -X PUT "http://localhost:8000/api/v1/iam/chat-config/users/1/block" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{
    "is_blocked": true,
    "block_reason": "Test block",
    "custom_block_message": "Test: Your account is temporarily suspended"
  }'

# Check if user disconnected
docker logs omni2-bridge --tail 20 | grep "User 1"

# Unblock
curl -X PUT "http://localhost:8000/api/v1/iam/chat-config/users/1/block" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"is_blocked": false}'
```

### Test Automated Block (Prompt Guard)
```
1. Send 5 injection attempts
2. Check user_blocks table
3. Verify user disconnected
4. Try to reconnect (should fail)
5. Admin unblocks via UI
6. User can reconnect
```
