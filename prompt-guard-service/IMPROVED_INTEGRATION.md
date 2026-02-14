# Improved Prompt Guard Integration

## Current Issues
1. Guard service decides action (should be omni2)
2. Blocking doesn't use existing user management
3. No warning message to user
4. No session-based attempt tracking

## Proposed Solution

### Architecture
```
User Message → omni2 → Guard (detect only) → omni2 (decide action)
                  ↓
            [Check config]
                  ↓
         warn / block / allow
                  ↓
    [Update user status if needed]
                  ↓
    [Send warning message to user]
                  ↓
    [Disconnect via ws_manager if blocked]
```

### Changes Needed

#### 1. Guard Service (DETECTION ONLY)
**Returns:**
```json
{
    "safe": false,
    "score": 0.85,
    "reason": "Pattern: ignore previous instructions",
    "latency_ms": 5
}
```
**NO action decision!**

#### 2. omni2 websocket_chat.py (DECISION LOGIC)

```python
# After guard check
guard_result = await prompt_guard.check_prompt(user_message, user_id)

if not guard_result["safe"]:
    # Load config from DB
    config = await load_prompt_guard_config(db)
    
    # Get user's violation count in this session
    session_violations = await get_session_violations(conversation_id, db)
    
    # Determine action
    if session_violations >= config["session_block_threshold"]:
        action = "block_user"  # Permanent block
    elif session_violations >= config["session_warn_threshold"]:
        action = "warn"  # Warning message
    elif guard_result["score"] > 0.8 and config["actions"]["block"]:
        action = "block_message"  # Block this message only
    else:
        action = "warn"
    
    # Execute action
    if action == "block_user":
        # Use existing user blocking mechanism
        await block_user_for_injection(user_id, guard_result, db)
        
        # Disconnect via ws_manager (existing mechanism)
        ws_manager = get_ws_manager()
        await ws_manager.disconnect_user(
            user_id, 
            custom_message="Account suspended due to security policy violations"
        )
        return
    
    elif action == "warn":
        # Send warning to user
        await websocket.send_json({
            "type": "warning",
            "message": "⚠️ Your message contains suspicious content. Please rephrase.",
            "details": guard_result["reason"] if is_admin else None
        })
        
        # Log violation
        await record_session_violation(conversation_id, session_id, user_id, guard_result, db)
        
        # Continue to LLM (warn only)
    
    elif action == "block_message":
        # Block this message only
        await websocket.send_json({
            "type": "blocked",
            "message": "Your message was blocked due to security concerns. Please rephrase."
        })
        
        # Log violation
        await record_session_violation(conversation_id, session_id, user_id, guard_result, db)
        return  # Don't send to LLM
```

#### 3. New Configuration Fields

Add to `omni2_config.prompt_guard`:
```json
{
    "enabled": true,
    "threshold": 0.5,
    "actions": {
        "warn": true,
        "block_message": false,
        "block_user": false
    },
    "session_tracking": {
        "enabled": true,
        "warn_threshold": 2,
        "block_threshold": 5,
        "window": "session"
    },
    "user_blocking": {
        "enabled": true,
        "auto_block": true,
        "block_reason_template": "Automated block: {count} prompt injection attempts detected"
    }
}
```

#### 4. User Blocking Function

```python
async def block_user_for_injection(user_id: int, guard_result: dict, db: AsyncSession):
    """Block user using existing auth_service mechanism."""
    
    # Count total violations
    result = await db.execute(
        text("SELECT COUNT(*) FROM omni2.prompt_injection_log WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    violation_count = result.scalar()
    
    # Update user status (existing field)
    await db.execute(
        text(
            "UPDATE auth_service.users "
            "SET active = false, "
            "updated_at = NOW() "
            "WHERE id = :user_id"
        ),
        {"user_id": user_id}
    )
    
    # Log to audit
    await db.execute(
        text(
            "INSERT INTO omni2.audit_logs "
            "(user_id, timestamp, question, success, was_blocked, block_reason) "
            "VALUES (:user_id, NOW(), :question, false, true, :reason)"
        ),
        {
            "user_id": user_id,
            "question": "Prompt injection attempt",
            "reason": f"Auto-blocked after {violation_count} injection attempts"
        }
    )
    
    await db.commit()
    
    # Publish to Redis for instant disconnect (existing mechanism)
    from app.database import redis_client
    await redis_client.publish(
        "user_blocked",
        json.dumps({
            "user_id": user_id,
            "custom_message": f"Account suspended: {violation_count} security violations detected"
        })
    )
```

#### 5. Session Violation Tracking

New table:
```sql
CREATE TABLE omni2.session_violations (
    id SERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL,
    session_id UUID NOT NULL,
    user_id INTEGER NOT NULL,
    injection_score DECIMAL(5,4) NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (user_id) REFERENCES auth_service.users(id) ON DELETE CASCADE
);

CREATE INDEX idx_session_violations_conversation ON omni2.session_violations(conversation_id);
CREATE INDEX idx_session_violations_user ON omni2.session_violations(user_id);
```

### Real-time Config Changes

**YES - Already works!**

1. **Guard config:** 
   - Update DB: `UPDATE omni2.omni2_config SET config_value = ... WHERE config_key = 'prompt_guard'`
   - Trigger reload: `PUBLISH prompt_guard_config_reload`
   - **No reboot needed!**

2. **User blocking:**
   - Update DB: `UPDATE auth_service.users SET active = false WHERE id = X`
   - Publish: `PUBLISH user_blocked {"user_id": X}`
   - User disconnected instantly via `ws_connection_manager`
   - **No reboot needed!**

### Warning Messages

**YES - Can send warning!**

```python
# In websocket_chat.py
if action == "warn":
    await websocket.send_json({
        "type": "warning",
        "severity": "high",
        "message": "⚠️ Security Alert: Your message contains suspicious patterns.",
        "details": {
            "score": guard_result["score"],
            "reason": guard_result["reason"],
            "attempts_remaining": config["session_block_threshold"] - session_violations
        }
    })
    # Message still goes to LLM (warn mode)
```

### Session-based Attempt Tracking

**YES - Track per conversation!**

```python
# Count violations in current conversation
session_violations = await db.execute(
    text(
        "SELECT COUNT(*) FROM omni2.session_violations "
        "WHERE conversation_id = :conv_id"
    ),
    {"conv_id": conversation_id}
).scalar()

# After 2 attempts: Warning
# After 5 attempts: Block user permanently
```

## Implementation Steps

1. ✅ Remove action decision from guard service (DONE)
2. ⬜ Add session_violations table
3. ⬜ Update websocket_chat.py with decision logic
4. ⬜ Add warning message support
5. ⬜ Integrate with existing user blocking
6. ⬜ Add session violation tracking
7. ⬜ Update configuration schema
8. ⬜ Test real-time config changes
9. ⬜ Test warning messages
10. ⬜ Test user blocking integration

## Benefits

✅ Uses existing user management (admin can unblock)
✅ Real-time config changes (no reboot)
✅ Warning messages to users
✅ Session-based tracking
✅ Gradual escalation (warn → block message → block user)
✅ Audit trail in existing tables
✅ Leverages existing ws_connection_manager
