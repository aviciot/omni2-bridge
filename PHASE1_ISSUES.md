# Phase 1 Status - Issues to Resolve

## Completed
✅ Database schema (user_blocks, chat_welcome_config)
✅ ChatContextService (authorization, blocking, usage limits)
✅ Chat router Phase 1 checks (X-User-Id extraction, context loading)
✅ Debug logging added to both OMNI2 and dashboard backend

## Current Issues

### Issue 1: Token Validation Failing
**Symptom**: Dashboard backend calls OMNI2 via Traefik → Gets 401 "Invalid token"

**Root Cause**: Unknown - need to see debug logs showing:
- What token is being sent from ChatWidget
- What Traefik is doing with the token
- Whether token is expired or malformed

**Debug Steps**:
1. Test chat and check logs: `docker-compose logs --since=1m dashboard-backend | findstr CHAT`
2. Should see: `[CHAT] Token (first 20 chars): Bearer eyJhbGc...`
3. Check if token is valid by decoding JWT

### Issue 2: ChatWidget Visible After Logout
**Symptom**: ChatWidget remains visible and functional even after logout

**Root Cause**: ChatWidget doesn't check if user is logged in

**Fix Needed**: Add check in ChatWidget.tsx:
```typescript
const token = localStorage.getItem("token");
if (!token) {
  return null; // Don't render widget if no token
}
```

## Next Steps

1. **Fix ChatWidget visibility** - Hide when no token
2. **Debug token issue** - Check logs to see what token is being sent
3. **Test with fresh login** - Get new token and try chat
4. **Verify Traefik auth** - Ensure auth-forward middleware is working

## Testing Commands

```bash
# Check dashboard backend logs
cd omni2/dashboard && docker-compose logs --tail=50 dashboard-backend | findstr CHAT

# Check OMNI2 logs
cd omni2 && docker-compose logs --tail=50 omni2 | findstr PHASE1

# Restart services
cd omni2/dashboard && docker-compose restart dashboard-backend
cd omni2 && docker-compose restart omni2

# Test chat endpoint directly (bypass dashboard)
curl -X POST http://localhost:8090/api/v1/chat/ask/stream \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"avi@omni.com","message":"test"}'
```

## Files Modified

- ✅ `omni2/app/routers/chat.py` - Phase 1 checks + debug logging
- ✅ `omni2/app/services/chat_context_service.py` - Context loading
- ✅ `omni2/dashboard/backend/app/routers/chat.py` - Debug logging
- ⏳ `omni2/dashboard/frontend/src/components/ChatWidget.tsx` - Needs visibility fix

## Phase 1 Completion Blockers

1. Token validation issue (401 error)
2. ChatWidget visibility after logout

Once these are resolved, Phase 1 will be complete and we can test:
- Custom welcome messages
- Usage limit enforcement
- User blocking
- MCP filtering by role
