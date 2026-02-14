# Usage Tracking Investigation - Task B

**Date:** February 12, 2026
**Status:** 🚨 CRITICAL ISSUE FOUND
**Investigator:** Claude Code

---

## Executive Summary

**CRITICAL FINDING:** WebSocket chat endpoint (`/ws/chat`) - which is the primary user interface at http://localhost:3001 - **DOES NOT track tokens or cost** in the audit system. Only the HTTP REST endpoint (`/api/v1/chat/ask`) tracks usage, but this endpoint is **not used by the main chat widget**.

**Result:** User usage limits and cost tracking are **not working** for WebSocket chat users.

---

## Investigation Findings

### 1. Three Chat Endpoints Discovered

#### Endpoint A: HTTP REST `/api/v1/chat/ask` (Line 228)
**File:** `omni2/app/routers/chat.py:228`
**Usage Tracking:** ✅ YES
**Used By:** Slack bot, external integrations
**Code:**
```python
await audit_service.log_chat_request(
    user_id=request.user_id,
    message=request.message,
    result=result,
    duration_ms=duration_ms,
    ip_address=http_request.client.host if http_request.client else None,
    user_agent=http_request.headers.get("user-agent"),
    slack_user_id=slack_user_id,
    # ... other fields
)
```

#### Endpoint B: HTTP Streaming `/api/v1/chat/ask/stream` (Line 291)
**File:** `omni2/app/routers/chat.py:291`
**Usage Tracking:** ❌ NO
**Used By:** Unknown (possibly legacy)
**What It Logs:** Only flow events
**Missing:** audit_service.log_chat_request() call

#### Endpoint C: WebSocket `/ws/chat` (PRIMARY ENDPOINT)
**File:** `omni2/app/routers/websocket_chat.py:20`
**Usage Tracking:** ❌ NO
**Used By:** Main chat widget at http://localhost:3001
**What It Logs:**
- `omni2.user_activities` (via activity_tracker)
- `omni2.flow_events` (via flow_tracker)
**Missing:** audit_service.log_chat_request() call

---

## Why This Is Critical

### User Flow:
1. User opens chat at http://localhost:3001
2. ChatWidget connects to `/ws/chat` WebSocket endpoint
3. User sends messages → LLM processes → Tokens consumed
4. **NO audit log written** (no tokens, no cost)
5. Usage limit check queries `audit_logs` table → finds 0 usage
6. User can consume infinite tokens/cost

### Impact:
- ❌ Cost tracking not working
- ❌ Usage limits not enforced properly
- ❌ Dashboard "Cost" section empty
- ❌ User usage statistics incorrect
- ❌ Billing/quota management broken

---

## Two Audit Systems Found (Confusion)

### System 1: `omni2.audit_logs` (Schema-Prefixed)
**Schema File:** `omni2/init_omni2_schema.sql:18-42`
**Fields:**
```sql
CREATE TABLE omni2.audit_logs (
    id integer NOT NULL,
    user_id integer,
    timestamp timestamp with time zone DEFAULT now() NOT NULL,
    question text NOT NULL,
    mcp_target character varying(255),
    tool_called character varying(255),
    tool_params jsonb,
    success boolean NOT NULL,
    duration_ms integer,
    result_summary text,
    error_message text,
    llm_tokens_used integer,  -- Single token field
    -- No separate input/output/cached tokens
    -- No cost_usd field in schema!
);
```

**Queried By:**
- `chat_context_service.py:check_usage_limit()` - References `cost_usd` field that **doesn't exist in schema**

### System 2: `audit_logs` (NO Schema Prefix)
**Service:** `app/services/audit_service.py`
**Fields:**
```python
INSERT INTO audit_logs (  -- Note: NO schema prefix
    user_id, question, answer,
    tokens_input, tokens_output, tokens_cached,  -- Separated tokens
    cost_estimate,  -- Different from cost_usd
    duration_ms, ip_address, user_agent,
    slack_user_id, slack_channel,
    tool_calls, tools_used, iterations,
    created_at
) VALUES (...)
```

**Used By:**
- `chat.py:/api/v1/chat/ask` endpoint (HTTP REST)
- `usage_limit_service.py:check_user_limit()` - Queries this table

**Cost Calculation:**
```python
def _estimate_cost(tokens_input, tokens_output, tokens_cached):
    # Claude 3.5 Haiku pricing (per million tokens)
    PRICE_INPUT = 0.80
    PRICE_OUTPUT = 4.00
    PRICE_CACHED = 0.08

    return round(
        (tokens_input / 1_000_000) * PRICE_INPUT +
        (tokens_output / 1_000_000) * PRICE_OUTPUT +
        (tokens_cached / 1_000_000) * PRICE_CACHED,
        6
    )
```

---

## Schema Mismatches

### Issue 1: Two Different Tables
- `omni2.audit_logs` (schema SQL)
- `audit_logs` (audit_service.py)
**Question:** Are these the same table or different?

### Issue 2: Field Name Conflicts
- Schema has: `llm_tokens_used` (single field)
- Service writes: `tokens_input`, `tokens_output`, `tokens_cached` (three fields)
- `chat_context_service.py` queries: `cost_usd`
- Service writes: `cost_estimate`

### Issue 3: Usage Checking Inconsistency
- `chat_context_service.py` queries `omni2.audit_logs` for `cost_usd`
- `usage_limit_service.py` queries `audit_logs` (no prefix) for `cost_estimate`
- **Which is correct?**

---

## Activity Tracking (Separate System)

### What WebSocket Chat DOES Track:
**Table:** `omni2.user_activities`
**Service:** `app/services/activity_tracker.py`
**Records:**
- User messages (message text, length)
- Tool calls (mcp_server, tool_name, parameters)
- Tool responses (status, duration_ms)
- Assistant responses (message, tokens_used, model)

**Purpose:** Conversation flow visualization (not usage/cost tracking)

**Data:** Stored as JSONB in `activity_data` field

---

## Flow Tracking (Also Separate)

### What WebSocket Chat Also Tracks:
**Table:** `omni2.flow_events`
**Service:** `app/services/flow_tracker.py`
**Records:**
- auth_check, block_check, usage_check
- mcp_permission_check, tool_filter
- llm_thinking, llm_complete
- tool_call, error events

**Purpose:** Flow visualization in analytics dashboard

**Token Field:** Has `tokens` field in `llm_complete` event, but only stored in flow_events (not used for usage limits)

---

## Verification Needed

### Database Queries to Run:

#### Query 1: Check if tables exist
```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_name IN ('audit_logs')
ORDER BY table_schema, table_name;
```
**Expected:** Verify if `omni2.audit_logs` and/or `public.audit_logs` exist

#### Query 2: Check actual audit_logs columns
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'omni2' AND table_name = 'audit_logs'
ORDER BY ordinal_position;
```
**Check For:**
- Does `cost_usd` field exist?
- Is it `llm_tokens_used` or `tokens_input/output/cached`?

#### Query 3: Check if any audit logs exist
```sql
-- Check omni2.audit_logs
SELECT COUNT(*), MAX(timestamp) as last_entry
FROM omni2.audit_logs;

-- Check public.audit_logs (if exists)
SELECT COUNT(*), MAX(created_at) as last_entry
FROM audit_logs;
```

#### Query 4: Sample data structure
```sql
SELECT * FROM omni2.audit_logs LIMIT 1;
SELECT * FROM audit_logs LIMIT 1;  -- if exists
```

---

## Root Cause Analysis

### Why WebSocket Doesn't Track Usage:

Looking at `websocket_chat.py:209-257`:
```python
elif event.get("type") == "done":
    result = event.get('result', {})

    # Records tool responses (if any)
    # Records assistant response to activity_tracker
    # Records flow completion to flow_tracker
    # Saves flow to database

    # BUT: NO audit_service.log_chat_request() call!
    # Missing token/cost tracking!
```

Compare with `chat.py:228`:
```python
# Calculate duration
duration_ms = int((time.time() - start_time) * 1000)

# Log to audit (async, non-blocking)
await audit_service.log_chat_request(
    user_id=request.user_id,
    message=request.message,
    result=result,
    duration_ms=duration_ms,
    # ... includes tokens and cost
)
```

---

## Token Data Flow

### Where Tokens Come From:
**LLM Service Response:**
```python
result = {
    "answer": "...",
    "tokens_input": 1234,
    "tokens_output": 567,
    "tokens_cached": 89,
    "model": "claude-3-5-haiku-20241022",
    "tool_calls": 2,
    "tools_used": ["docker_mcp.list_containers"],
    "iterations": 1
}
```

### Where Tokens Go:
1. ✅ **HTTP `/ask` endpoint:** → audit_service → `audit_logs` table
2. ❌ **WebSocket `/ws/chat`:** → activity_tracker → `user_activities` (tokens_used field only)
3. ❌ **HTTP `/ask/stream`:** → flow_tracker → `flow_events` (tokens field only)

### Usage Limit Checks:
```python
# In chat_context_service.py:check_usage_limit()
query = text("""
    SELECT
        COALESCE(SUM(llm_tokens_used), 0) as tokens_used,
        COALESCE(SUM(cost_usd), 0) as cost_used
    FROM omni2.audit_logs
    WHERE user_id = :user_id
    AND timestamp >= CURRENT_DATE
    AND success = true
""")
```
**Problem:** WebSocket chat never writes to this table!

---

## Fix Required

### Option 1: Add audit_service to WebSocket (Recommended)
**Location:** `websocket_chat.py:209` (in "done" event handler)
**Action:** Add audit_service.log_chat_request() call
**Pros:** Consistent with HTTP endpoint, proper usage tracking
**Cons:** Requires audit_service dependency injection

### Option 2: Use activity_tracker for usage
**Action:** Query `user_activities` for tokens instead of `audit_logs`
**Pros:** Already tracking tokens in activities
**Cons:** Activities table designed for conversation flow, not usage limits

### Option 3: Use flow_tracker for usage
**Action:** Query `flow_events` for tokens in `llm_complete` events
**Pros:** Already capturing tokens
**Cons:** Flow events designed for flow visualization, not usage enforcement

### Recommendation: **Option 1**
Add audit logging to WebSocket endpoint to ensure consistent usage tracking across all endpoints.

---

## Dashboard Impact

### Why Dashboard Sections Are Empty:

#### 1. Cost Display Empty
**Root Cause:** WebSocket chat doesn't write cost to audit_logs
**Dashboard Query:** Expects data in audit_logs table
**Result:** Shows $0.00 or empty

#### 2. Recent Activities
**Status:** Different issue - frontend needs investigation
**Data Source:** `user_activities` table (this IS being populated)

#### 3. MCP Servers Display
**Status:** Different issue - needs separate investigation
**Likely:** Frontend or API endpoint issue

---

## Summary

### ✅ What Works:
- HTTP REST `/api/v1/chat/ask` endpoint tracks usage properly
- Activity tracking (conversation flow) works
- Flow tracking (analytics) works
- Slack bot integration has proper usage tracking

### ❌ What Doesn't Work:
- WebSocket chat (main UI) doesn't track tokens/cost
- HTTP streaming endpoint doesn't track tokens/cost
- Usage limits not enforced for WebSocket users
- Cost dashboard empty for WebSocket users

### 🔍 Needs Verification:
- Two audit systems - which is production?
- Schema mismatch - which fields actually exist?
- Database queries needed to confirm reality

---

## Next Steps

1. **Run database verification queries** (see "Verification Needed" section)
2. **Confirm which audit table is production** (omni2.audit_logs vs audit_logs)
3. **Fix WebSocket endpoint** to call audit_service (after confirmation)
4. **Fix HTTP streaming endpoint** to call audit_service (after confirmation)
5. **Resolve schema mismatches** (cost_usd vs cost_estimate)
6. **Update dashboard queries** if needed
7. **Test usage limits** with WebSocket chat after fix

---

## Files Referenced

### Primary Files:
- `omni2/app/routers/websocket_chat.py` - WebSocket chat (NEEDS FIX)
- `omni2/app/routers/chat.py` - HTTP chat (WORKING) + streaming (NEEDS FIX)
- `omni2/app/services/audit_service.py` - Audit logging service
- `omni2/app/services/chat_context_service.py` - Usage checking (has schema ref issue)
- `omni2/app/services/usage_limit_service.py` - Usage limits (different table query)

### Supporting Files:
- `omni2/app/services/activity_tracker.py` - Activity logging (separate)
- `omni2/app/services/flow_tracker.py` - Flow logging (separate)
- `omni2/init_omni2_schema.sql` - Database schema

### Frontend:
- `omni2/dashboard/frontend/src/components/ChatWidget.tsx` - Uses WebSocket endpoint

---

## Risk Assessment

**Severity:** 🔴 HIGH
**Impact:** Usage limits not enforced, cost tracking broken, potential unlimited API usage
**Urgency:** HIGH - Users can currently exceed quotas without restriction
**Complexity:** MEDIUM - Clear fix, but needs schema verification first
**Estimated Fix Time:** 30 minutes once schema is verified

---

**Investigation Complete - Ready for Task C (Security Design)**
