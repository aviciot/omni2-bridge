# Investigation: Database Logs and Usage Tracking

**Date:** February 12, 2026
**Status:** Investigation Complete
**Tasks:** A) Audit/Health Logs, B) Usage Tracking

---

## PART A: Audit Logs & Health Logs Investigation

### 1. Database Schema - What Tables Exist?

#### Table 1: `omni2.audit_logs`
**Location:** `init_omni2_schema.sql` (lines 18-42)

**Structure:**
```sql
CREATE TABLE omni2.audit_logs (
    id integer NOT NULL,
    user_id integer,
    timestamp timestamp with time zone DEFAULT now() NOT NULL,
    question text NOT NULL,
    mcp_target character varying(255),          -- Which MCP was targeted
    tool_called character varying(255),         -- Which tool was called
    tool_params jsonb,                          -- Tool parameters
    success boolean NOT NULL,
    duration_ms integer,
    result_summary text,
    error_message text,
    error_id character varying(50),
    slack_channel character varying(100),       -- Slack integration fields
    slack_user_id character varying(50),
    slack_message_ts character varying(50),
    slack_thread_ts character varying(50),
    llm_confidence numeric(3,2),
    llm_reasoning text,
    llm_tokens_used integer,                    -- Total tokens used
    ip_address inet,
    user_agent text,
    was_blocked boolean,
    block_reason text
);
```

**Purpose:** Tool execution audit trail
**Indexed On:** user_id, timestamp, tool_called, mcp_target, success, was_blocked

---

#### Table 2: `omni2.mcp_health_log`
**Location:** `init_omni2_schema.sql` (lines 80-89)

**Structure:**
```sql
CREATE TABLE omni2.mcp_health_log (
    id integer NOT NULL,
    mcp_server_id integer NOT NULL,             -- FK to mcp_servers
    timestamp timestamp with time zone DEFAULT now() NOT NULL,
    status character varying(20) NOT NULL,      -- healthy/unhealthy/timeout
    response_time_ms integer,
    error_message text,
    meta_data jsonb,
    event_type character varying(50)            -- health_check/startup/shutdown
);
```

**Purpose:** MCP server health monitoring
**Indexed On:** mcp_server_id, timestamp, event_type

---

### 2. Code Flow - What's Actually Writing to These Tables?

#### Problem Discovered: TWO DIFFERENT AUDIT SYSTEMS!

##### System 1: `audit_service.py` (Lines 1-498)
**Writes to:** `audit_logs` (NO schema prefix - likely different table!)

**Fields Written:**
```python
INSERT INTO audit_logs (
    user_id,                  # (SELECT id FROM users WHERE email = :user_id)
    request_type,             # 'chat'
    message,                  # Full user message
    message_preview,          # First 197 chars
    iterations,               # Number of LLM iterations
    tool_calls_count,         # Number of tool calls
    tools_used,               # Array of tool names
    mcps_accessed,            # Array of MCP names
    duration_ms,              # Request duration
    tokens_input,             # Input tokens
    tokens_output,            # Output tokens
    tokens_cached,            # Cached tokens
    cost_estimate,            # Calculated cost
    status,                   # success/error/warning
    warning,                  # Warning message
    response_preview,         # First 500 chars of response
    ip_address,               # Client IP
    user_agent,               # Client UA
    slack_user_id,            # Slack integration
    slack_channel,
    slack_message_ts,
    slack_thread_ts,
    success,                  # Boolean
    created_at                # NOW()
)
```

**Used By:**
- `app/routers/chat.py` (REST endpoint)
- May be older/unused system

**Does NOT match omni2.audit_logs schema!**

---

##### System 2: `activity_tracker.py` (Need to investigate)
**Likely writes to:** `omni2.audit_logs` (with schema prefix)

**Need to verify:**
- Where is this service?
- Is it being used?
- Does it match the schema?

---

### 3. Health Logs - Who Writes Them?

**Need to find:**
- Health check service/scheduler
- MCP coordinator health checks
- Where `mcp_health_log` INSERTs happen

**Likely location:**
- `app/services/mcp_coordinator.py` or similar
- Background health check task
- Circuit breaker pattern implementation

---

### 4. What the Frontend LogsModal Expects

**Health Logs API Contract:**
```typescript
interface HealthLog {
  id: number;
  timestamp: string;
  status: string;              // healthy/unhealthy/timeout
  response_time_ms: number;
  error_message?: string;
  event_type: string;          // health_check
  meta_data?: any;
}
```

**Audit Logs API Contract:**
```typescript
interface AuditLog {
  id: number;
  tool_name: string;           // Tool that was called
  user_id: string;             // User email
  environment: string;         // production/staging
  parameters: any;             // Tool parameters
  result_status: string;       // success/error
  result_summary?: string;     // Summary of result
  error_message?: string;      // Error if failed
  execution_time_ms: number;   // Duration
  workflow_run_id?: string;    // Optional workflow ID
  session_id?: string;         // Conversation/session ID
  created_at: string;          // Timestamp
}
```

---

### 5. Mapping: Database → UI Expectations

#### For Health Logs (mcp_health_log):

| DB Field | UI Expects | Mapping |
|----------|------------|---------|
| id | id | ✅ Direct |
| timestamp | timestamp | ✅ Direct |
| status | status | ✅ Direct |
| response_time_ms | response_time_ms | ✅ Direct |
| error_message | error_message | ✅ Direct |
| event_type | event_type | ✅ Direct |
| meta_data | meta_data | ✅ Direct |

**Verdict:** ✅ **PERFECT MATCH** - Can use directly!

---

#### For Audit Logs (omni2.audit_logs):

| DB Field | UI Expects | Mapping | Issue |
|----------|------------|---------|-------|
| id | id | ✅ Direct | |
| tool_called | tool_name | ✅ Rename | |
| user_id | user_id | ⚠️ Join | Need email, not ID |
| - | environment | ❌ Missing | Default to "production" |
| tool_params | parameters | ✅ Direct | |
| success | result_status | ⚠️ Convert | Boolean → "success"/"error" |
| result_summary | result_summary | ✅ Direct | |
| error_message | error_message | ✅ Direct | |
| duration_ms | execution_time_ms | ✅ Rename | |
| - | workflow_run_id | ❌ Missing | Optional, can be NULL |
| - | session_id | ❌ Missing | Optional, can be NULL |
| timestamp | created_at | ✅ Direct | |

**Verdict:** ⚠️ **MOSTLY COMPATIBLE** - Need query transformation!

---

### 6. Required SQL Query for Audit Logs Endpoint

```sql
-- GET /api/v1/mcp/servers/{server_id}/audit
SELECT
    a.id,
    a.tool_called as tool_name,
    COALESCE(u.email, CAST(a.user_id AS VARCHAR)) as user_id,
    'production' as environment,
    a.tool_params as parameters,
    CASE
        WHEN a.success THEN 'success'
        ELSE 'error'
    END as result_status,
    a.result_summary,
    a.error_message,
    a.duration_ms as execution_time_ms,
    NULL as workflow_run_id,
    NULL as session_id,
    a.timestamp as created_at
FROM omni2.audit_logs a
LEFT JOIN auth_service.users u ON a.user_id = u.id
WHERE a.mcp_target = (
    SELECT name FROM omni2.mcp_servers WHERE id = :server_id
)
AND (:status IS NULL OR
     ((:status = 'success' AND a.success = true) OR
      (:status = 'error' AND a.success = false)))
AND (:search IS NULL OR
     a.tool_called ILIKE :search OR
     a.error_message ILIKE :search OR
     a.result_summary ILIKE :search)
ORDER BY a.timestamp DESC
LIMIT :limit;
```

---

### 7. Required SQL Query for Health Logs Endpoint

```sql
-- GET /api/v1/mcp/servers/{server_id}/logs
SELECT
    id,
    timestamp,
    status,
    response_time_ms,
    error_message,
    event_type,
    meta_data
FROM omni2.mcp_health_log
WHERE mcp_server_id = :server_id
ORDER BY timestamp DESC
LIMIT :limit;
```

---

### 8. Critical Questions to Resolve

1. ✅ **Is `omni2.audit_logs` actually being used?**
   - Yes, schema exists
   - Need to find who writes to it

2. ✅ **Is `omni2.mcp_health_log` being populated?**
   - Yes, schema exists
   - Need to verify health check service is running

3. ❓ **What is `audit_service.py` for?**
   - Different schema
   - Might be older/unused
   - Need to trace usage

4. ❓ **Where is activity_tracker.py?**
   - Imported in websocket_chat.py
   - Likely the REAL audit logger
   - Need to examine

5. ❓ **Are health checks running?**
   - Check startup logs
   - Verify background tasks
   - Query database to see if data exists

---

### 9. Verification Commands

#### Check if omni2.audit_logs has data:
```sql
SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
FROM omni2.audit_logs;
```

#### Check if mcp_health_log has data:
```sql
SELECT COUNT(*), MIN(timestamp), MAX(timestamp),
       status, mcp_server_id
FROM omni2.mcp_health_log
GROUP BY status, mcp_server_id;
```

#### Check which MCPs have health logs:
```sql
SELECT m.name, m.id, COUNT(h.id) as log_count,
       MAX(h.timestamp) as last_check
FROM omni2.mcp_servers m
LEFT JOIN omni2.mcp_health_log h ON m.id = h.mcp_server_id
GROUP BY m.id, m.name;
```

---

## PART B: User Usage Tracking Investigation

### 1. Where Usage Should Be Tracked

**Requirements:**
- Tokens used (input, output, cached)
- Cost calculated
- Written to database per request
- Quota checked before request
- Quota updated after request

---

### 2. Code Flow Trace

#### A. Chat Request Comes In
**Location:** `app/routers/websocket_chat.py` or `app/routers/chat.py`

**Steps:**
1. User authenticated
2. Context loaded (includes `cost_limit_daily`)
3. **Check current usage** via `context_service.check_usage_limit()`
4. Block if exceeded
5. Call LLM service
6. **Log audit after completion**

---

#### B. Usage Check (Before Request)
**Location:** `app/services/chat_context_service.py` (lines 72-99)

```python
async def check_usage_limit(self, user_id: int, cost_limit_daily: float) -> dict:
    """Check if user has exceeded daily usage limit"""
    query = text("""
        SELECT
            COALESCE(SUM(llm_tokens_used), 0) as tokens_used,
            COALESCE(SUM(cost_usd), 0) as cost_used
        FROM omni2.audit_logs
        WHERE user_id = :user_id
        AND timestamp >= CURRENT_DATE
        AND success = true
    """)

    # Calculate remaining
    remaining = max(0, cost_limit_daily - cost_used)
    exceeded = cost_used >= cost_limit_daily

    return {
        "allowed": not exceeded,
        "tokens_used": tokens_used,
        "cost_used": cost_used,
        "cost_limit": cost_limit_daily,
        "remaining": remaining,
        "exceeded": exceeded
    }
```

**Key Fields:**
- Reads from `omni2.audit_logs`
- Sums `llm_tokens_used` and `cost_usd` for today
- Compares against `cost_limit_daily` from role

---

#### C. LLM Call
**Location:** `app/services/llm_service.py`

**What happens:**
1. Build messages with tool definitions
2. Call Anthropic API
3. Get response with usage metadata
4. Extract:
   - `usage.input_tokens`
   - `usage.output_tokens`
   - `usage.cache_read_input_tokens` (cached)
5. Calculate cost
6. Return result dict

---

#### D. Audit Logging (After Request)

**Question:** Which service is used?

**Option 1:** `audit_service.py` (lines 26-182)
- Writes to `audit_logs` (no schema)
- Fields: `tokens_input`, `tokens_output`, `tokens_cached`, `cost_estimate`

**Option 2:** `activity_tracker.py` (need to find)
- Writes to `omni2.audit_logs`
- Fields: `llm_tokens_used`, ??? (need to verify)

**Critical:** Need to verify which one is actually being called!

---

### 3. Expected Fields in omni2.audit_logs

From schema (`init_omni2_schema.sql`):
```sql
llm_tokens_used integer,  -- Total tokens
```

**Problem:** Only ONE field for tokens!
- No separate input/output/cached tracking
- Just total

**But usage check sums:**
```sql
COALESCE(SUM(llm_tokens_used), 0) as tokens_used
```

**And also references:**
```sql
COALESCE(SUM(cost_usd), 0) as cost_used
```

**BUT:** `cost_usd` column doesn't exist in schema!

---

### 4. Schema Mismatch Issues

**What schema says:**
```sql
CREATE TABLE omni2.audit_logs (
    ...
    llm_tokens_used integer,
    ...
    -- NO cost_usd field!
);
```

**What code expects:**
```sql
SELECT ... COALESCE(SUM(cost_usd), 0) as cost_used ...
```

**Possible explanations:**
1. Schema file is outdated
2. Migration added `cost_usd` column
3. Code is broken and query fails
4. Using a different table

**Need to check:** Actual database schema vs file schema!

---

### 5. Verification: What's Actually in the Database?

#### Query table structure:
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'omni2'
  AND table_name = 'audit_logs'
ORDER BY ordinal_position;
```

#### Check if cost_usd exists:
```sql
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'omni2'
  AND table_name = 'audit_logs'
  AND column_name = 'cost_usd';
```

#### Check recent audit logs:
```sql
SELECT id, user_id, timestamp, tool_called,
       llm_tokens_used, success,
       -- Try to select cost_usd if it exists
       -- Otherwise this will error
       cost_usd
FROM omni2.audit_logs
ORDER BY timestamp DESC
LIMIT 5;
```

---

### 6. Where Usage is Written

**Need to find:**
1. After LLM completes, who writes the audit log?
2. Does it populate `llm_tokens_used`?
3. Does it populate `cost_usd` (if field exists)?
4. Is there a cost calculation function?

**Search for:**
```python
# Look for INSERT or UPDATE to audit_logs
grep -r "INSERT INTO.*audit_logs" omni2/app/
grep -r "llm_tokens_used" omni2/app/
grep -r "cost_usd" omni2/app/
```

---

### 7. Cost Calculation

**From audit_service.py (lines 300-333):**
```python
def _estimate_cost(
    self,
    tokens_input: int,
    tokens_output: int,
    tokens_cached: int
) -> float:
    """
    Claude 3.5 Haiku pricing (as of Dec 2024):
    - Input: $0.80 per million tokens
    - Output: $4.00 per million tokens
    - Cached input: $0.08 per million tokens

    Returns:
        Estimated cost in USD
    """
    PRICE_INPUT = 0.80
    PRICE_OUTPUT = 4.00
    PRICE_CACHED = 0.08

    cost_input = (tokens_input / 1_000_000) * PRICE_INPUT
    cost_output = (tokens_output / 1_000_000) * PRICE_OUTPUT
    cost_cached = (tokens_cached / 1_000_000) * PRICE_CACHED

    return round(cost_input + cost_output + cost_cached, 6)
```

**This function exists!** But:
- Is it being called?
- Where is the result stored?
- Does it match actual Anthropic billing?

---

## SUMMARY OF FINDINGS

### Audit Logs:
1. ✅ Schema exists: `omni2.audit_logs`
2. ⚠️ TWO audit systems found (confusion!)
3. ❓ Not clear which one is actively used
4. ⚠️ Schema file may be outdated (missing `cost_usd`?)
5. ✅ Can build compatible query for LogsModal

### Health Logs:
1. ✅ Schema exists: `omni2.mcp_health_log`
2. ✅ Perfect match with UI expectations
3. ❓ Need to verify health checks are running
4. ❓ Need to verify data is being written

### Usage Tracking:
1. ✅ Code exists to check daily usage
2. ⚠️ References `cost_usd` field that may not exist
3. ✅ Cost calculation function exists
4. ❓ Not clear where/when it's called
5. ❓ Need to verify actual write happens after LLM call

---

## NEXT STEPS

### Immediate Actions:

1. **Query actual database** to see:
   - What columns exist in omni2.audit_logs
   - If data is being written
   - If cost_usd field exists

2. **Check logs** for:
   - "Audit log created" messages
   - Which audit service is logging
   - Health check runs

3. **Find activity_tracker.py** and examine:
   - What it writes
   - Where it's called
   - How it differs from audit_service.py

4. **Test a chat request** and trace:
   - Does usage get checked?
   - Does LLM call succeed?
   - Does audit log get written?
   - Are tokens/cost populated?

5. **Verify health checks** are running:
   - Check startup logs
   - Query mcp_health_log for recent entries
   - Verify background task is active

---

## IMPLEMENTATION RECOMMENDATION

### Don't implement endpoints yet!

**Reason:** Too many unknowns:
- Which table is actually being used?
- What fields actually exist?
- Is data being written at all?

### Instead:

1. **Run verification queries** on actual database
2. **Trace one complete request** from start to finish
3. **Document actual vs expected state**
4. **THEN** decide how to implement endpoints

This will save time and prevent building on wrong assumptions!

---

## END OF INVESTIGATION PART A & B

**Status:** Need real database queries and log analysis to proceed.

**Next Document:** Part C - Security Risk Scoring System Design
