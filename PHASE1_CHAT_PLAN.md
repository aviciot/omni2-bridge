# Phase 1: Chat Context & Authorization - Implementation Plan

## User Interaction Flow (AGREED)

### 1. Widget Opens
- Shows hardcoded welcome message (simple, no DB call)
- User sees input box ready

### 2. User Sends First Message
- Frontend sends message to `/api/v1/chat/stream`
- Backend performs Phase 1 checks:
  - Extract X-User-Id from Traefik header
  - Load user context (email, role, permissions, limits)
  - Check if user is blocked → return error if blocked
  - Check if account is active → return error if inactive
  - Check daily usage limit → return error if exceeded
  - Load welcome message from DB (user > role > team > default priority)
  - Get available MCPs based on role permissions
- Backend sends SSE events:
  - `event: welcome` with personalized message + usage info
  - `event: token` with LLM response tokens
  - `event: done` with final result

### 3. Frontend Displays
- Welcome message appears FIRST (from SSE welcome event)
- Then LLM response streams below it
- User sees personalized greeting with their name/role

## Implementation Tasks

### ✅ DONE:
1. Database tables (user_blocks, chat_welcome_config)
2. ChatContextService (all Phase 1 functions)
3. Chat router Phase 1 checks
4. ChatWidget SSE streaming
5. Token authentication fixed

### 🔧 TODO NOW:

#### 1. Add Custom Welcome to Widget
- Listen for `event: welcome` in SSE stream
- Display welcome message at top of chat
- Show usage info if included

#### 2. Cleanup OMNI2 /stream Endpoint
- Remove old rate_limiter code (using Phase 1 usage limits now)
- Remove old user_service code (using context_service now)
- Remove audit_service calls (broken, fix later)
- Keep only: context checks → LLM stream → done

#### 3. Test Phase 1 Flow
- Send message "hello"
- Verify logs show Phase 1 execution
- Verify welcome message appears
- Verify LLM response streams

## Code Locations

- **Frontend**: `dashboard/frontend/src/components/ChatWidget.tsx`
- **Backend Router**: `app/routers/chat.py` → `/ask/stream` endpoint
- **Context Service**: `app/services/chat_context_service.py`
- **Database**: `omni2.user_blocks`, `omni2.chat_welcome_config`

## Next Phase (Phase 2)
- Fix audit logging to use auth_service.users
- Add session tracking
- Add cost tracking per request
- Test blocking/limits enforcement
