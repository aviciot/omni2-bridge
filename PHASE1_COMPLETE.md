# Phase 1: User Authorization & Context Loading - COMPLETE

## Summary

Phase 1 implements user authorization, blocking, usage limits, and personalized welcome messages before allowing LLM interaction.

## What Was Implemented

### 1. Database Schema
**File**: `omni2/migrations/phase1_chat_context.sql`

**Tables Created**:
- `omni2.user_blocks` - User blocking with custom reasons
- `omni2.chat_welcome_config` - Personalized welcome messages (user/role/team/default priority)

**Columns Added to audit_logs**:
- `cost_usd` - Cost tracking for usage limits
- `session_id` - UUID for interaction flow tracking
- `tools_used` - JSONB array of tools called
- `mcp_servers_used` - TEXT array of MCP servers used

**Test Data Inserted**:
- Default welcome: "Welcome to OMNI2! How can I help you today?"
- User-specific (user_id=1): "Welcome back, Avi! As a super admin, you have unlimited access..."
- Role-specific (role_id=1): "Welcome, Admin! You have access to all MCP servers..."

### 2. Chat Context Service
**File**: `omni2/app/services/chat_context_service.py`

**Functions**:
- `load_user_context(user_id)` - Loads user profile, role, permissions from database
- `check_user_blocked(user_id)` - Returns (is_blocked, reason) from user_blocks table
- `check_usage_limit(user_id, cost_limit)` - Checks daily cost usage vs limit
- `get_welcome_message(user_id, role_id)` - Gets personalized welcome (priority: user > role > default)
- `get_available_mcps(mcp_access)` - Filters active MCP servers by role permissions

### 3. Chat Router Updates
**File**: `omni2/app/routers/chat.py`

**Changes to `/ask/stream` endpoint**:
1. Extract `X-User-Id` header from Traefik (INTEGER user ID)
2. Load user context (profile + role + permissions)
3. Check if user is blocked → Return error with reason
4. Check if account is active → Return error if inactive
5. Check daily usage limit → Return error if exceeded
6. Load personalized welcome message
7. Load available MCPs based on role permissions
8. Send `welcome` SSE event with:
   - Personalized message
   - Username and role
   - Usage info (cost_used, cost_limit, remaining)
   - Available MCP list
9. Then stream LLM response as before

## Authorization Flow

```
Request → Traefik (adds X-User-Id header) → OMNI2 /ask/stream
                                                    ↓
                                          Load user context
                                                    ↓
                                          Check blocked? → Error if blocked
                                                    ↓
                                          Check active? → Error if inactive
                                                    ↓
                                          Check usage limit? → Error if exceeded
                                                    ↓
                                          Load welcome message
                                                    ↓
                                          Load available MCPs
                                                    ↓
                                          Send welcome SSE event
                                                    ↓
                                          Stream LLM response
```

## SSE Events

### Welcome Event (New)
```json
event: welcome
data: {
  "message": "Welcome back, Avi! As a super admin...",
  "username": "avi",
  "role": "super_admin",
  "usage": {
    "cost_used": 1.50,
    "cost_limit": 1000.00,
    "remaining": 998.50
  },
  "available_mcps": ["qa_mcp", "informatica_mcp"]
}
```

### Error Events (Enhanced)
```json
event: error
data: {"error": "Access blocked: Suspended for policy violation"}

event: error
data: {"error": "Account is inactive"}

event: error
data: {"error": "Daily cost limit exceeded. Used: $10.00 / $10.00. Resets tomorrow."}
```

## Testing Instructions

### Test 1: Normal User (avi@omni.com, user_id=1)
```bash
# Login and get token
curl -X POST http://localhost:8090/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"avi","password":"avi123"}'

# Test chat stream (should see custom welcome message)
curl -X POST http://localhost:8090/api/v1/chat/ask/stream \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"avi@omni.com","message":"Hello"}'

# Expected: Welcome event with "Welcome back, Avi! As a super admin..."
```

### Test 2: Block User
```sql
-- Block user_id=1
INSERT INTO omni2.user_blocks (user_id, is_blocked, block_reason)
VALUES (1, true, 'Suspended for policy violation');

-- Try to chat (should get error)
```

### Test 3: Exceed Usage Limit
```sql
-- Set low limit for testing
UPDATE auth_service.roles SET cost_limit_daily = 0.01 WHERE id = 1;

-- Try to chat (should get usage limit error)
```

### Test 4: Custom Welcome Messages
```sql
-- User-specific message (highest priority)
SELECT * FROM omni2.chat_welcome_config WHERE config_type = 'user' AND target_id = 1;

-- Role-specific message (fallback)
SELECT * FROM omni2.chat_welcome_config WHERE config_type = 'role' AND target_id = 1;

-- Default message (final fallback)
SELECT * FROM omni2.chat_welcome_config WHERE config_type = 'default';
```

## Database Queries for Monitoring

### Check User Context
```sql
SELECT 
    u.id, u.username, u.email, u.active,
    r.name as role_name,
    r.mcp_access,
    r.cost_limit_daily,
    ub.is_blocked, ub.block_reason
FROM auth_service.users u
LEFT JOIN auth_service.roles r ON u.role_id = r.id
LEFT JOIN omni2.user_blocks ub ON u.id = ub.user_id
WHERE u.id = 1;
```

### Check Daily Usage
```sql
SELECT 
    user_id,
    COUNT(*) as requests,
    SUM(llm_tokens_used) as total_tokens,
    SUM(cost_usd) as total_cost
FROM omni2.audit_logs
WHERE user_id = 1 
AND timestamp >= CURRENT_DATE
AND success = true
GROUP BY user_id;
```

### View Welcome Messages
```sql
SELECT 
    config_type,
    target_id,
    welcome_message,
    show_usage_info
FROM omni2.chat_welcome_config
ORDER BY 
    CASE config_type
        WHEN 'user' THEN 1
        WHEN 'role' THEN 2
        WHEN 'team' THEN 3
        WHEN 'default' THEN 4
    END;
```

## Next Steps (Phase 2)

1. **Redis Streams Integration** - Track user interaction flow in real-time
2. **Flow Visualization Endpoint** - `/api/v1/flow/{session_id}/live` for React Flow
3. **Tool Filtering in LLM Service** - Only register tools from allowed MCPs
4. **Background Archiver** - Move completed flows from Redis to PostgreSQL
5. **Enhanced Audit Logging** - Add session_id, tools_used, mcp_servers_used to all logs

## Files Modified

- ✅ `omni2/migrations/phase1_chat_context.sql` - Database schema
- ✅ `omni2/app/services/chat_context_service.py` - Context loading service
- ✅ `omni2/app/routers/chat.py` - Chat router with Phase 1 checks
- ✅ Database test data - Custom welcome messages for testing

## Verification

Run these commands to verify Phase 1 is working:

```bash
# 1. Check tables exist
docker exec -i omni_pg_db psql -U omni -d omni -c "\d omni2.user_blocks"
docker exec -i omni_pg_db psql -U omni -d omni -c "\d omni2.chat_welcome_config"

# 2. Check test data
docker exec -i omni_pg_db psql -U omni -d omni -c "SELECT * FROM omni2.chat_welcome_config;"

# 3. Check user context query works
docker exec -i omni_pg_db psql -U omni -d omni -c "
SELECT u.id, u.username, r.name as role, r.mcp_access, r.cost_limit_daily 
FROM auth_service.users u 
LEFT JOIN auth_service.roles r ON u.role_id = r.id 
WHERE u.id = 1;"

# 4. Restart OMNI2 to load new code
cd omni2
docker-compose restart omni2
docker-compose logs -f omni2
```

## Status: ✅ COMPLETE

Phase 1 is fully implemented and ready for testing. The chat endpoint now:
- Validates user authorization before LLM interaction
- Checks blocking status and account activity
- Enforces daily usage limits
- Sends personalized welcome messages
- Provides usage information to users
- Lists available MCP servers based on role permissions
