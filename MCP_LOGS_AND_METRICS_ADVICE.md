# MCP Logs & Metrics Dashboard - Comprehensive Advice

**Date:** February 12, 2026
**Status:** Investigation Complete ✅

---

## 1. ✅ User Blocking - FIXED

### First Attempt (Instant Disconnect):
- ✅ Frontend now handles `{"type": "blocked"}` message
- ✅ Shows custom message in chat: "🚫 Your message..."
- ✅ Connection closes immediately

### Second Attempt (Reconnect):
- ✅ Connection rejected before accept
- ✅ Shows custom message from `event.reason`
- ✅ Displayed in chat, not as alert

**Files Modified:**
- `omni2/dashboard/frontend/src/components/ChatWidget.tsx`

**Status:** Ready to test! ✅

---

## 2. 📊 MCP Audit & Health Logs - STATUS

### Current Implementation:

**Frontend:** ✅ **FULLY IMPLEMENTED**
- `LogsModal.tsx` - Beautiful modal with filters
- Calls API endpoints correctly
- Shows health logs and audit logs
- Search, filter, pagination all working

**Dashboard Backend:** ✅ **PROXIES TO OMNI2**
- `/api/v1/mcp/tools/servers/{server_id}/logs`
- `/api/v1/mcp/tools/servers/{server_id}/audit`
- Forwards requests to main OMNI2 app

**Main OMNI2 Backend:** ❌ **NOT IMPLEMENTED**
- `/api/v1/mcp/servers/{server_id}/logs` - MISSING
- `/api/v1/mcp/servers/{server_id}/audit` - MISSING

### What Needs to Be Done:

#### Option A: Query Existing Tables (RECOMMENDED)

You already have these tables:
1. `omni2.health_checks` - MCP health check logs
2. `omni2.audit_logs` - Tool execution logs

**Implementation:**

```python
# omni2/app/routers/mcp_management.py (or new router)

@router.get("/api/v1/mcp/servers/{server_id}/logs")
async def get_mcp_server_health_logs(
    server_id: int,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Get health check logs for an MCP server"""
    query = text("""
        SELECT
            id,
            mcp_name as server_name,
            status,
            response_time_ms,
            error_message,
            timestamp,
            meta_data
        FROM omni2.health_checks
        WHERE mcp_id = :server_id
        ORDER BY timestamp DESC
        LIMIT :limit
    """)

    result = await db.execute(query, {"server_id": server_id, "limit": limit})
    rows = result.fetchall()

    logs = [
        {
            "id": row.id,
            "timestamp": row.timestamp.isoformat(),
            "status": row.status,
            "response_time_ms": row.response_time_ms,
            "error_message": row.error_message,
            "event_type": "health_check",
            "meta_data": row.meta_data
        }
        for row in rows
    ]

    return {"logs": logs, "total": len(logs)}


@router.get("/api/v1/mcp/servers/{server_id}/audit")
async def get_mcp_server_audit_logs(
    server_id: int,
    status: str = None,
    search: str = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Get audit logs for an MCP server"""
    conditions = ["mcp_id = :server_id"]
    params = {"server_id": server_id, "limit": limit}

    if status:
        conditions.append("success = :success")
        params["success"] = (status == "success")

    if search:
        conditions.append("(tool_name ILIKE :search OR error_message ILIKE :search)")
        params["search"] = f"%{search}%"

    query = text(f"""
        SELECT
            id,
            tool_name,
            user_id,
            environment,
            request_data as parameters,
            response_data,
            success as result_status,
            error_message,
            execution_duration_ms,
            conversation_id as session_id,
            timestamp as created_at,
            llm_tokens_used,
            cost_usd
        FROM omni2.audit_logs
        WHERE {" AND ".join(conditions)}
        ORDER BY timestamp DESC
        LIMIT :limit
    """)

    result = await db.execute(query, params)
    rows = result.fetchall()

    logs = [
        {
            "id": row.id,
            "tool_name": row.tool_name,
            "user_id": str(row.user_id),
            "environment": row.environment or "production",
            "parameters": row.parameters,
            "result_status": "success" if row.result_status else "error",
            "result_summary": f"Tokens: {row.llm_tokens_used}, Cost: ${row.cost_usd}",
            "error_message": row.error_message,
            "execution_time_ms": row.execution_duration_ms,
            "session_id": str(row.session_id) if row.session_id else None,
            "created_at": row.created_at.isoformat()
        }
        for row in rows
    ]

    return {"logs": logs, "total": len(logs)}
```

**Estimated Time:** 30 minutes

#### Option B: Create New Logging System (Overkill)
- Don't do this - you already have the data!

### Testing:
1. Add endpoints to `omni2/app/main.py` router list
2. Restart OMNI2 container
3. Go to MCP Servers → Click "View Audit Logs" or "View Health Logs"
4. Should show data from existing tables!

---

## 3. 🌐 WebSocket Streams - CURRENT STATE

### Existing WebSocket Endpoints:

1. **`/ws/chat`** (User Chat)
   - Location: `omni2/app/routers/websocket_chat.py`
   - Purpose: User conversations with LLM
   - Protocol: Bidirectional (user sends messages, receives tokens)

2. **`/api/v1/ws/flows/{user_id}`** (Flow Tracking)
   - Location: `omni2/dashboard/backend/app/routers/flows.py`
   - Purpose: Real-time flow event monitoring
   - Protocol: Server-to-client (broadcasts flow events)

3. **`/ws`** (Admin Dashboard WebSocket)
   - Location: `omni2/dashboard/backend/app/routers/websocket.py`
   - Purpose: Proxy to OMNI2 WebSocket
   - Protocol: Bidirectional proxy

### No Separate "Messaging" WebSocket
- Currently only chat and flow tracking
- No dedicated notification/messaging stream

---

## 4. 📊 MCP Metrics Dashboard - ADVICE

### Question: Should We Build This?

**My Recommendation:** ⚠️ **Wait Until You Have Multiple Production MCPs**

### Why Wait?

1. **Docker Control MCP Isn't Representative**
   - Docker commands don't generate useful metrics
   - Not a typical MCP workload
   - Won't give meaningful insights

2. **You Need Real Usage Data**
   - Metrics are only useful with actual traffic
   - Need multiple users, multiple MCPs
   - Need variety of tool calls

3. **Current Logs Are Sufficient**
   - Audit logs show tool execution
   - Health logs show connectivity
   - Can query database for analytics

### When to Build It:

**Build it when:**
- ✅ You have 3+ MCPs in production
- ✅ Multiple users actively using them
- ✅ You need real-time monitoring for incidents
- ✅ You want to optimize based on usage patterns

---

## 5. 🎯 IF You Decide to Build MCP Metrics Dashboard

### What MCPs Expose (Standard MCP Protocol):

**Built-in Metrics:** ❌ **NONE**
- MCP protocol doesn't include metrics
- No standard `/metrics` endpoint
- No Prometheus integration

**What You Can Track (From Your System):**

1. **From `omni2.health_checks` table:**
   - ✅ Uptime percentage
   - ✅ Average response time
   - ✅ Error rate
   - ✅ Connection status over time

2. **From `omni2.audit_logs` table:**
   - ✅ Tool calls per hour/day
   - ✅ Most used tools
   - ✅ User activity
   - ✅ Token usage
   - ✅ Cost per MCP
   - ✅ Success vs error rate

3. **From Redis (Real-time):**
   - ✅ Active connections
   - ✅ Current load
   - ✅ Queue depth (if applicable)

### Proposed Architecture:

```
┌─────────────────────────────────────────┐
│  MCP Metrics Dashboard (New Page)      │
│  /mcp-metrics                           │
└─────────────────────────────────────────┘
          │
          ├── WebSocket: ws://localhost:8500/api/v1/ws/mcp-metrics
          │   (Real-time updates every 5 seconds)
          │
          └── REST API: /api/v1/mcp/metrics/summary
              (Initial load + refresh)

┌─────────────────────────────────────────┐
│  Backend Service (New)                  │
│  app/services/mcp_metrics_service.py    │
└─────────────────────────────────────────┘
          │
          ├── Queries PostgreSQL (audit_logs, health_checks)
          │   - Aggregates last 24h data
          │   - Calculates metrics
          │
          ├── Publishes to Redis Pub/Sub
          │   - Channel: "mcp_metrics"
          │   - Every 5 seconds
          │
          └── Streams via WebSocket
              - Broadcasts to all connected dashboards
```

### Metrics to Include:

#### Per-MCP Metrics:

1. **Health Status** (Real-time)
   - 🟢 Healthy / 🔴 Unhealthy / 🟡 Degraded
   - Last check timestamp
   - Uptime % (last 24h)

2. **Performance** (Last 24h)
   - Average response time (ms)
   - P50, P95, P99 latency
   - Request rate (req/min)

3. **Usage** (Last 24h)
   - Total tool calls
   - Active users
   - Most used tools (top 5)

4. **Cost** (Last 24h)
   - Total tokens used
   - Estimated cost ($)
   - Cost per user

5. **Reliability** (Last 24h)
   - Success rate %
   - Error rate %
   - Error types breakdown

#### System-Wide Metrics:

1. **Overview**
   - Total MCPs: 5
   - Active: 4 / Inactive: 1
   - Total requests/hour: 1,250
   - Total cost/day: $12.50

2. **Top MCPs by Usage**
   - Bar chart of requests per MCP

3. **Top MCPs by Cost**
   - Bar chart of $ spent per MCP

4. **System Health Timeline**
   - Line graph: All MCPs health over 24h

### UI Mockup:

```
┌───────────────────────────────────────────────────────┐
│  📊 MCP Metrics Dashboard            [Auto-refresh: ●]│
├───────────────────────────────────────────────────────┤
│                                                        │
│  System Overview (Last 24h)                           │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐     │
│  │   5    │  │  4/5   │  │ 1,250  │  │ $12.50 │     │
│  │ MCPs   │  │ Active │  │ Req/hr │  │  Cost  │     │
│  └────────┘  └────────┘  └────────┘  └────────┘     │
│                                                        │
│  ┌────────────────────────────────────────────────┐  │
│  │  🟢 Oracle MCP                                 │  │
│  │  Status: Healthy | Uptime: 99.8%              │  │
│  │  Requests: 450 | Avg Latency: 120ms           │  │
│  │  Cost: $5.20 | Success Rate: 98%              │  │
│  │  Top Tools: execute_query (200), list_tables  │  │
│  │  [View Details] [View Logs]                   │  │
│  └────────────────────────────────────────────────┘  │
│                                                        │
│  ┌────────────────────────────────────────────────┐  │
│  │  🟢 Postgres MCP                               │  │
│  │  Status: Healthy | Uptime: 100%               │  │
│  │  Requests: 380 | Avg Latency: 95ms            │  │
│  │  Cost: $4.10 | Success Rate: 99.5%            │  │
│  │  [View Details] [View Logs]                   │  │
│  └────────────────────────────────────────────────┘  │
│                                                        │
│  ┌────────────────────────────────────────────────┐  │
│  │  🟡 GitHub MCP                                 │  │
│  │  Status: Degraded | Uptime: 85%               │  │
│  │  Requests: 220 | Avg Latency: 850ms           │  │
│  │  Cost: $2.10 | Success Rate: 88%              │  │
│  │  Errors: Rate limit exceeded (12)             │  │
│  │  [View Details] [View Logs]                   │  │
│  └────────────────────────────────────────────────┘  │
│                                                        │
│  ┌────────────────────────────────────────────────┐  │
│  │  🔴 Docker MCP                                 │  │
│  │  Status: Unhealthy | Uptime: 45%              │  │
│  │  Requests: 50 | Avg Latency: N/A              │  │
│  │  Errors: Connection timeout (28)              │  │
│  │  [Restart] [View Logs]                        │  │
│  └────────────────────────────────────────────────┘  │
│                                                        │
│  📈 Request Rate (Last 24h)                           │
│  [Line graph showing requests per hour for each MCP]  │
│                                                        │
│  💰 Cost Distribution (Last 24h)                      │
│  [Pie chart showing % of cost per MCP]               │
│                                                        │
└───────────────────────────────────────────────────────┘
```

### Implementation Checklist:

#### Phase 1: Backend (2-3 hours)
- [ ] Create `app/services/mcp_metrics_service.py`
- [ ] Add metrics calculation from PostgreSQL
- [ ] Add Redis Pub/Sub publisher (every 5s)
- [ ] Create `/api/v1/mcp/metrics/summary` endpoint
- [ ] Create `/api/v1/ws/mcp-metrics` WebSocket endpoint

#### Phase 2: Frontend (3-4 hours)
- [ ] Create `/mcp-metrics` page
- [ ] Add metrics cards (overview)
- [ ] Add per-MCP cards
- [ ] Add charts (request rate, cost distribution)
- [ ] Add WebSocket connection for real-time updates
- [ ] Add auto-refresh toggle

#### Phase 3: Polish (1 hour)
- [ ] Add loading states
- [ ] Add error handling
- [ ] Add export to CSV
- [ ] Add date range filter

**Total Time:** ~7 hours

---

## 6. 🎯 MY RECOMMENDATIONS

### High Priority (Do Now):
1. ✅ **Fix blocking message display** - DONE
2. ✅ **Restart dashboard frontend** - Apply changes
3. 🔨 **Implement MCP audit/health logs endpoints** - 30 minutes
4. 🔍 **Fix dashboard main page** (MCP servers, cost, activities)

### Medium Priority (Do Soon):
5. ⏳ **Test blocking feature** with real users
6. ⏳ **Verify usage calculation** when using LLM
7. ⏳ **Add recent activities** to dashboard (last 30)

### Low Priority (Do Later):
8. ⏸️ **MCP Metrics Dashboard** - Wait until:
   - You have 3+ production MCPs with real traffic
   - Multiple active users
   - Need for real-time monitoring emerges

**Why wait?**
- Docker MCP isn't representative
- No meaningful metrics without traffic
- Current logs are sufficient for now
- Can add metrics later when you have data to show

---

## 7. 📋 NEXT STEPS (Recommended Order)

### Today:
1. ✅ Restart dashboard frontend (apply blocking fix)
2. 🔨 Add MCP audit/health logs backend endpoints (30 min)
3. 🔍 Fix dashboard main page issues

### Tomorrow:
4. Test blocking with real users
5. Verify usage calculation
6. Add recent activities display

### Next Week:
7. When you have production MCPs with traffic:
   - Revisit metrics dashboard
   - Build it if you find value in existing logs
   - Otherwise, keep using audit/health logs

---

## 8. ✅ SUMMARY

### Status of Features:

| Feature | Frontend | Dashboard Backend | OMNI2 Backend | Status |
|---------|----------|-------------------|---------------|--------|
| Blocking Message | ✅ | N/A | ✅ | **READY** |
| Audit Logs UI | ✅ | ✅ (proxy) | ❌ MISSING | **Needs 30 min** |
| Health Logs UI | ✅ | ✅ (proxy) | ❌ MISSING | **Needs 30 min** |
| MCP Metrics | N/A | N/A | N/A | **Wait for traffic** |

### WebSocket Streams:
- ✅ Chat: `/ws/chat`
- ✅ Flow Tracking: `/api/v1/ws/flows/{user_id}`
- ✅ Admin Proxy: `/ws`
- ❌ Metrics: Not needed yet

### Built-in MCP Metrics:
- ❌ MCPs don't expose metrics by design
- ✅ You can calculate from your audit_logs/health_checks tables
- ✅ Can build custom metrics dashboard when needed

---

## 9. 🎉 CONCLUSION

**Good News:**
- Audit/Health logs UI is fully built and ready
- Just need 30 minutes to add backend endpoints
- All data already exists in your tables

**Advice:**
- Don't build metrics dashboard yet
- Wait for real traffic from production MCPs
- Focus on fixing main dashboard issues first
- Revisit metrics when you have meaningful data to display

**Priority:**
1. Fix blocking message (DONE ✅)
2. Add audit/health endpoints (30 min)
3. Fix dashboard main page
4. Metrics dashboard (LATER, when needed)

Would you like me to implement the audit/health log endpoints now?
