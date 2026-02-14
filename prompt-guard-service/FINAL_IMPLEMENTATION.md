# ✅ Prompt Guard - Complete Implementation

## What Was Implemented

### 1. Role-Based Bypass
**Admins skip guard checks entirely**

```json
{
    "bypass_roles": ["super_admin", "admin"]
}
```

**API Endpoints:**
```bash
# Get bypass roles
GET /api/v1/prompt-guard/roles

# Update bypass roles
PUT /api/v1/prompt-guard/roles/bypass
Body: ["super_admin", "admin", "developer"]
```

### 2. Session-Based Violation Tracking
**Track attempts per conversation (not global)**

**Table:** `omni2.session_violations`
```sql
conversation_id UUID
session_id UUID
user_id INTEGER
injection_score DECIMAL
detected_at TIMESTAMP
```

**Logic:**
- 1st attempt: Log only
- 2nd attempt: Warning message
- 5th attempt: Auto-block user

### 3. Configurable Messages
**All messages customizable via config**

```json
{
    "messages": {
        "warning": "⚠️ Your message contains suspicious content. Please rephrase.",
        "blocked_message": "Your message was blocked due to security concerns.",
        "blocked_user": "Your account has been suspended due to security violations."
    }
}
```

### 4. User Blocking Integration
**Uses existing `omni2.user_blocks` table**

**Flow:**
```
5 violations → Insert into user_blocks → Publish to Redis → ws_manager disconnects
```

**Admin can unblock via:** `http://localhost:3001/iam/chat-config`

### 5. Three Action Types

| Action | When | Behavior |
|--------|------|----------|
| `warn` | Score 0.5-0.8, < 2 violations | Log + allow to LLM |
| `block_message` | Score > 0.8 | Block message, don't send to LLM |
| `block_user` | 5+ violations in session | Permanent block, disconnect |

## Configuration

### Complete Config Structure
```json
{
    "enabled": true,
    "threshold": 0.5,
    "cache_ttl_seconds": 3600,
    "bypass_roles": ["super_admin", "admin"],
    "behavioral_tracking": {
        "enabled": true,
        "warning_threshold": 2,
        "block_threshold": 5,
        "window": "session"
    },
    "actions": {
        "warn": true,
        "block_message": false,
        "block_user": false
    },
    "messages": {
        "warning": "⚠️ Your message contains suspicious content. Please rephrase.",
        "blocked_message": "Your message was blocked due to security concerns. Please rephrase and try again.",
        "blocked_user": "Your account has been suspended due to multiple security policy violations. Please contact support."
    }
}
```

### Enable/Disable from UI

**Via API:**
```bash
# Enable
POST /api/v1/prompt-guard/config/enable

# Disable
POST /api/v1/prompt-guard/config/disable

# Get current config
GET /api/v1/prompt-guard/config
```

**Real-time:** No reboot needed!

## Flow Diagrams

### Normal User (Not Bypassed)
```
User sends message
    ↓
Check role → Not in bypass_roles
    ↓
Guard checks message
    ↓
Score 0.7 (detected)
    ↓
Check session violations: 0
    ↓
Action: Log only (< warning_threshold)
    ↓
Message sent to LLM
```

### Admin User (Bypassed)
```
Admin sends message
    ↓
Check role → "admin" in bypass_roles
    ↓
Skip guard entirely
    ↓
Message sent to LLM directly
```

### User with 2 Violations
```
User sends 3rd injection attempt
    ↓
Guard detects (score 0.8)
    ↓
Check session violations: 2
    ↓
2 >= warning_threshold (2)
    ↓
Send warning message to user:
"⚠️ Suspicious content. 2 attempts remaining"
    ↓
Message still sent to LLM (warn mode)
```

### User with 5 Violations
```
User sends 6th injection attempt
    ↓
Guard detects
    ↓
Check session violations: 5
    ↓
5 >= block_threshold (5)
    ↓
Insert into user_blocks table
    ↓
Publish to Redis "user_blocked"
    ↓
ws_manager disconnects user
    ↓
User sees: "Account suspended due to security violations"
    ↓
Connection closed
```

## API Endpoints

### Configuration Management
```bash
# Get config
GET /api/v1/prompt-guard/config

# Update full config
PUT /api/v1/prompt-guard/config
Body: {full config object}

# Enable/Disable
POST /api/v1/prompt-guard/config/enable
POST /api/v1/prompt-guard/config/disable
```

### Role Management
```bash
# Get bypass roles
GET /api/v1/prompt-guard/roles
Response: {
    "bypass_roles": ["super_admin", "admin"],
    "all_roles": ["super_admin", "admin", "developer", "qa", "read_only"],
    "enabled": true
}

# Update bypass roles
PUT /api/v1/prompt-guard/roles/bypass
Body: ["super_admin", "admin"]
```

### Statistics
```bash
# Get stats
GET /api/v1/prompt-guard/stats?hours=24

# Recent detections
GET /api/v1/prompt-guard/detections?limit=50

# Top offenders
GET /api/v1/prompt-guard/top-offenders?hours=24&limit=10
```

### Testing
```bash
# Test a message
POST /api/v1/prompt-guard/test?message=Ignore%20all%20instructions&user_id=1
```

## Database Tables

### 1. omni2.prompt_injection_log
**All detections (global)**
```sql
SELECT * FROM omni2.prompt_injection_log 
ORDER BY detected_at DESC LIMIT 10;
```

### 2. omni2.session_violations
**Per-conversation tracking**
```sql
SELECT 
    conversation_id,
    COUNT(*) as violations,
    MAX(injection_score) as max_score
FROM omni2.session_violations
GROUP BY conversation_id
ORDER BY violations DESC;
```

### 3. omni2.user_blocks
**Blocked users (manual + automated)**
```sql
SELECT 
    ub.user_id,
    u.email,
    ub.block_reason,
    ub.blocked_at,
    ub.blocked_by
FROM omni2.user_blocks ub
LEFT JOIN auth_service.users u ON u.id = ub.user_id
WHERE ub.is_blocked = true;
```

### 4. omni2.omni2_config
**Configuration**
```sql
SELECT config_value 
FROM omni2.omni2_config 
WHERE config_key = 'prompt_guard';
```

## Testing Scenarios

### Test 1: Admin Bypass
```
1. Login as admin
2. Send: "Ignore all previous instructions"
3. Expected: No detection, message goes to LLM
4. Check logs: Should see "role in bypass_roles, skipping guard"
```

### Test 2: Warning After 2 Attempts
```
1. Login as regular user
2. Send injection attempt #1 → Logged only
3. Send injection attempt #2 → Warning message
4. Check: User sees "⚠️ Suspicious content. 3 attempts remaining"
```

### Test 3: Auto-Block After 5 Attempts
```
1. Send 5 injection attempts
2. On 6th attempt:
   - User blocked in user_blocks table
   - WebSocket disconnected
   - User sees: "Account suspended"
3. Try to reconnect → Rejected
4. Admin unblocks via UI
5. User can reconnect
```

### Test 4: Enable/Disable from UI
```bash
# Disable guard
curl -X POST http://localhost:8000/api/v1/prompt-guard/config/disable

# Send injection → Should pass through

# Enable guard
curl -X POST http://localhost:8000/api/v1/prompt-guard/config/enable

# Send injection → Should detect
```

### Test 5: Update Bypass Roles
```bash
# Add "developer" to bypass
curl -X PUT http://localhost:8000/api/v1/prompt-guard/roles/bypass \
  -H "Content-Type: application/json" \
  -d '["super_admin", "admin", "developer"]'

# Login as developer
# Send injection → Should bypass
```

## Benefits

✅ **Role-based bypass** - Admins skip checks (no latency)
✅ **Session tracking** - Per-conversation, not global
✅ **Configurable messages** - Customize all user-facing text
✅ **Existing user blocking** - Admin can unblock via UI
✅ **Real-time config** - No reboot needed
✅ **Gradual escalation** - Log → Warn → Block message → Block user
✅ **Audit trail** - All violations logged
✅ **Performance** - Bypass for admins = zero latency

## Monitoring Queries

### Session Violations by User
```sql
SELECT 
    u.email,
    COUNT(*) as violations,
    MAX(sv.detected_at) as last_violation
FROM omni2.session_violations sv
LEFT JOIN auth_service.users u ON u.id = sv.user_id
WHERE sv.detected_at > NOW() - INTERVAL '1 hour'
GROUP BY u.email
ORDER BY violations DESC;
```

### Auto-Blocked Users
```sql
SELECT 
    u.email,
    ub.block_reason,
    ub.blocked_at
FROM omni2.user_blocks ub
LEFT JOIN auth_service.users u ON u.id = ub.user_id
WHERE ub.is_blocked = true
AND ub.blocked_by IS NULL  -- Automated blocks
ORDER BY ub.blocked_at DESC;
```

### Bypass Effectiveness
```sql
-- Messages checked vs total messages
SELECT 
    COUNT(*) FILTER (WHERE pil.id IS NOT NULL) as checked,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(*) FILTER (WHERE pil.id IS NOT NULL) / COUNT(*), 2) as check_rate
FROM omni2.user_activities ua
LEFT JOIN omni2.prompt_injection_log pil 
    ON pil.user_id = ua.user_id 
    AND pil.detected_at BETWEEN ua.timestamp - INTERVAL '1 second' AND ua.timestamp + INTERVAL '1 second'
WHERE ua.activity_type = 'user_message'
AND ua.timestamp > NOW() - INTERVAL '1 hour';
```

## Configuration via UI (Future)

**Recommended UI Location:** `http://localhost:3001/admin/security/prompt-guard`

**UI Elements:**
- Toggle: Enable/Disable guard
- Slider: Detection threshold (0.0 - 1.0)
- Multi-select: Bypass roles
- Number inputs: Warning threshold, Block threshold
- Checkboxes: warn, block_message, block_user
- Text areas: Custom messages
- Stats dashboard: Detections, blocks, top offenders

## Summary

✅ **Implemented:**
- Role-based bypass (admins skip checks)
- Session-based violation tracking
- Configurable messages
- User blocking integration
- Enable/disable from API
- Real-time config updates

✅ **Benefits:**
- Zero latency for admins
- Gradual escalation
- Admin can unblock users
- All configurable without code changes
- No reboot needed
