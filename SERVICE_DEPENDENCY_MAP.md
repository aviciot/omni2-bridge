# OMNI2 Chat Router - Service Dependency Map

## Current State (chat.py)

### Endpoint 1: `/ask` (Non-streaming, OLD approach)
**Status**: LEGACY - Used by Slack bot, not by dashboard
**Services Used**:
- ✅ `llm_service` - Calls LLM
- ✅ `audit_service` - Logs to old schema (broken but needed for Slack)
- ✅ `user_service` - Loads user from YAML config
- ✅ `rate_limiter` - In-memory rate limiting
- ✅ `usage_limit_service` - Checks daily limits

**Why Keep**: Slack bot uses this endpoint

---

### Endpoint 2: `/ask/stream` (SSE streaming, NEW Phase 1 approach)
**Status**: ACTIVE - Used by dashboard chat widget
**Services Used**:
- ✅ `llm_service` - Calls LLM with streaming
- ✅ `context_service` - NEW Phase 1 service (replaces all below)
  - Loads user from auth_service.users (not YAML)
  - Checks blocking (user_blocks table)
  - Checks usage limits (audit_logs cost tracking)
  - Loads welcome message (chat_welcome_config)
  - Filters MCPs by permissions

**Services NOT Used** (replaced by context_service):
- ❌ `audit_service` - Disabled (broken schema)
- ❌ `user_service` - Replaced by context_service.load_user_context()
- ❌ `rate_limiter` - Replaced by context_service.check_usage_limit()
- ❌ `usage_limit_service` - Replaced by context_service.check_usage_limit()

---

## Why We Need Both Approaches

### `/ask` endpoint (OLD):
- Slack bot integration uses this
- Uses YAML-based user config
- Uses in-memory rate limiting
- Non-streaming response

### `/ask/stream` endpoint (NEW):
- Dashboard chat widget uses this
- Uses database-based user config (auth_service.users)
- Uses database-based usage tracking (audit_logs)
- SSE streaming response
- Phase 1 authorization checks

---

## Cleanup Plan

### Option 1: Keep Both (CURRENT)
- ✅ No breaking changes
- ✅ Slack bot keeps working
- ❌ Duplicate code
- ❌ Two different authorization approaches

### Option 2: Migrate `/ask` to Phase 1 (FUTURE)
- Update Slack bot to use `/ask/stream`
- Remove old services (audit_service, user_service, rate_limiter, usage_limit_service)
- Single authorization approach
- Requires Slack bot changes

---

## Recommendation

**Keep both for now** - Don't break Slack bot. When ready to migrate Slack:
1. Update Slack bot to call `/ask/stream`
2. Remove `/ask` endpoint
3. Remove old service imports
4. Clean up unused services

---

## Service Status Summary

| Service | Used by /ask | Used by /ask/stream | Status |
|---------|--------------|---------------------|--------|
| llm_service | ✅ | ✅ | KEEP |
| context_service | ❌ | ✅ | KEEP (NEW) |
| audit_service | ✅ | ❌ | KEEP (for /ask) |
| user_service | ✅ | ❌ | KEEP (for /ask) |
| rate_limiter | ✅ | ❌ | KEEP (for /ask) |
| usage_limit_service | ✅ | ❌ | KEEP (for /ask) |
