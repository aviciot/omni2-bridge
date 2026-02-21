# UI Improvement Plan - MCP Status System

## Current Circuit Breaker Analysis ✅

### Existing Protection (Already Implemented!)

**Circuit Breaker States:**
- `CLOSED` → Normal operation
- `OPEN` → Fast-fail after 5 consecutive failures (configurable)
- `HALF_OPEN` → Testing recovery after 60 seconds

**Built-in Stability Features:**
1. **Failure Threshold**: Requires 5 consecutive failures before marking unhealthy (prevents single-failure blinking)
2. **Recovery Testing**: After 60s timeout, allows 3 test calls in HALF_OPEN state
3. **Failure Cycles**: Tracks complete failure cycles (CLOSED → OPEN → HALF_OPEN → OPEN = 1 cycle)
4. **Auto-Disable**: After 3 failure cycles, MCP status changes to 'inactive' (stops health checks)

**Configuration (from database):**
```json
{
  "enabled": true,
  "failure_threshold": 5,        // 5 failures before OPEN
  "timeout_seconds": 60,          // Wait 60s before retry
  "half_open_max_calls": 3,       // 3 test calls in recovery
  "max_failure_cycles": 3,        // Auto-disable after 3 cycles
  "auto_disable_enabled": true
}
```

### Answer to "Blinking" Question

**Status WILL NOT blink** because:
- Single failure → failure_count = 1 (status stays "healthy")
- Second failure → failure_count = 2 (status stays "healthy")
- Third failure → failure_count = 3 (status stays "healthy")
- Fourth failure → failure_count = 4 (status stays "healthy")
- Fifth failure → failure_count = 5 → **NOW status becomes "unhealthy"**

**Recovery also requires stability:**
- First success in HALF_OPEN → status stays "unhealthy"
- Second success → status stays "unhealthy"
- Third success → Circuit CLOSES → **NOW status becomes "healthy"**

**Conclusion:** The existing circuit breaker already provides excellent stability. No additional logic needed!

---

## Data Source Strategy

### Architecture Flow
```
Frontend → Dashboard Backend API → Redis (status) + PostgreSQL (config)
```

### Data Sources by Type

**PostgreSQL (Static Config):**
- URL, protocol, auth credentials
- MCP name, description
- Retry settings, timeout values
- Status field ('active' or 'inactive')
- Updated rarely, safe to cache

**Redis (Dynamic Data):**
- Current health status ('healthy', 'unhealthy')
- Capabilities (tools, prompts, resources)
- Last check timestamp
- Circuit breaker state
- Updated frequently (every 60s health check)

**Redis Stream (Real-time Events):**
- `system:events` stream
- Event types: `mcp_status_change`, `circuit_breaker_state`, `mcp_auto_disabled`
- Already published by backend, not consumed by frontend yet

---

## Implementation Plan

### Phase 1: Fix Reload Button (Immediate)
**Goal:** Make reload button fetch fresh data from backend

**Current Problem:**
- Dashboard shows stale `health_status` from database
- Health check runs every 60s, but UI doesn't refresh

**Solution:**
```typescript
// In MCPServerList.tsx
const handleReload = async () => {
  setLoading(true);
  try {
    // Force backend to run health check NOW
    await api.post(`/api/v1/mcp/${mcpId}/health-check`);
    
    // Wait 2 seconds for health check to complete
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Fetch fresh data
    await fetchMCPs();
  } finally {
    setLoading(false);
  }
};
```

**Backend Endpoint (new):**
```python
@router.post("/mcp/{mcp_id}/health-check")
async def trigger_health_check(mcp_id: int, db: AsyncSession = Depends(get_db)):
    """Trigger immediate health check for MCP."""
    registry = get_mcp_registry()
    
    # Get MCP name from database
    result = await db.execute(select(MCPServer).where(MCPServer.id == mcp_id))
    mcp = result.scalar_one_or_none()
    
    if not mcp:
        raise HTTPException(404, "MCP not found")
    
    # Run health check
    health_result = await registry.health_check(mcp.name, db)
    
    return {
        "mcp_id": mcp_id,
        "mcp_name": mcp.name,
        "health_result": health_result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

**Files to Modify:**
- `omni2/app/routers/mcp.py` - Add health check endpoint
- `omni2/dashboard/frontend/src/components/mcp/MCPServerList.tsx` - Update reload handler

---

### Phase 2: Real-time WebSocket Updates (High Priority)
**Goal:** Dashboard receives instant status updates without polling

**Current State:**
- Backend already publishes events to Redis `system:events` stream
- Backend already has WebSocket broadcaster
- Frontend doesn't subscribe to WebSocket yet

**Solution:**
```typescript
// In MCPServerList.tsx
useEffect(() => {
  const ws = new WebSocket('ws://localhost:8000/ws');
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.event_type === 'mcp_status_change') {
      // Update specific MCP in state
      setMcps(prev => prev.map(mcp => 
        mcp.name === data.event_data.mcp_name
          ? { ...mcp, health_status: data.event_data.new_status }
          : mcp
      ));
      
      // Show toast notification
      toast.info(`${data.event_data.mcp_name}: ${data.event_data.reason}`);
    }
    
    if (data.event_type === 'circuit_breaker_state') {
      // Show circuit breaker notification
      toast.warning(`${data.event_data.mcp_name}: Circuit breaker ${data.event_data.new_state}`);
    }
    
    if (data.event_type === 'mcp_auto_disabled') {
      // Show critical notification
      toast.error(`${data.event_data.mcp_name} auto-disabled: ${data.event_data.reason}`);
      
      // Refresh MCP list
      fetchMCPs();
    }
  };
  
  return () => ws.close();
}, []);
```

**Backend WebSocket Endpoint (check if exists):**
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    broadcaster = get_websocket_broadcaster()
    
    # Subscribe to events
    async for event in broadcaster.subscribe():
        await websocket.send_json(event)
```

**Files to Modify:**
- `omni2/dashboard/frontend/src/components/mcp/MCPServerList.tsx` - Add WebSocket subscription
- `omni2/app/main.py` - Verify WebSocket endpoint exists

---

### Phase 3: Redis Caching for Capabilities (Medium Priority)
**Goal:** Fetch tools/prompts/resources from Redis instead of database

**Current State:**
- `mcp_registry.py` already caches tools/prompts/resources in memory
- Dashboard fetches from database (stale data)

**Solution:**
```python
# New endpoint in mcp.py
@router.get("/mcp/{mcp_name}/capabilities")
async def get_mcp_capabilities(mcp_name: str):
    """Get MCP capabilities from Redis cache."""
    registry = get_mcp_registry()
    
    return {
        "mcp_name": mcp_name,
        "tools": registry.get_tools(mcp_name).get(mcp_name, []),
        "prompts": registry.get_prompts(mcp_name).get(mcp_name, []),
        "resources": registry.get_resources(mcp_name).get(mcp_name, []),
        "cached_at": datetime.now(timezone.utc).isoformat()
    }
```

**Frontend Change:**
```typescript
// In EditMCPServerModal.tsx
const fetchCapabilities = async (mcpName: string) => {
  // OLD: const response = await api.get(`/api/v1/mcp/${mcpId}/tools`);
  // NEW: Fetch from Redis cache
  const response = await api.get(`/api/v1/mcp/${mcpName}/capabilities`);
  
  setTools(response.data.tools);
  setPrompts(response.data.prompts);
  setResources(response.data.resources);
};
```

**Files to Modify:**
- `omni2/app/routers/mcp.py` - Add capabilities endpoint
- `omni2/dashboard/frontend/src/components/mcp/EditMCPServerModal.tsx` - Use new endpoint

---

### Phase 4: Preserve Tool Testing Functionality (CRITICAL)
**Goal:** Ensure edit modal's tool testing remains functional after changes

**Current Functionality (MUST PRESERVE):**
- Edit button opens modal
- Modal shows tools list
- User can select tool and test it
- Tool execution calls backend API
- Results displayed in modal

**Verification Checklist:**
- [ ] Edit button still opens modal
- [ ] Tools list still loads
- [ ] Tool selection still works
- [ ] Tool execution still calls correct endpoint
- [ ] Results still display correctly
- [ ] Authentication still passed correctly

**Testing Endpoint (verify exists):**
```python
@router.post("/mcp/{mcp_name}/tools/{tool_name}/execute")
async def execute_tool(
    mcp_name: str,
    tool_name: str,
    arguments: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Execute tool on MCP."""
    registry = get_mcp_registry()
    result = await registry.call_tool(mcp_name, tool_name, arguments)
    return result
```

**Files to Verify:**
- `omni2/app/routers/mcp.py` - Tool execution endpoint
- `omni2/dashboard/frontend/src/components/mcp/EditMCPServerModal.tsx` - Tool testing UI

---

## Summary of Changes

### What We're Changing:
1. **Reload Button** → Triggers immediate health check + fetches fresh data
2. **Status Updates** → Real-time via WebSocket (no polling)
3. **Capabilities** → Fetch from Redis cache (not database)

### What We're NOT Changing:
1. **Circuit Breaker Logic** → Already perfect, no changes needed
2. **Tool Testing** → Must remain fully functional
3. **Authentication Flow** → Keep existing implementation
4. **Database Schema** → No migrations needed

### Data Flow After Changes:
```
User Action          → Backend API        → Data Source
─────────────────────────────────────────────────────────
Load MCP List        → GET /mcp           → PostgreSQL (config) + Redis (status)
Reload Button        → POST /health-check → Triggers health check → Redis
Status Update        → WebSocket          → Redis Stream (real-time)
View Tools           → GET /capabilities  → Redis Cache (memory)
Test Tool            → POST /execute      → MCP Registry (live call)
Edit Config          → PUT /mcp/{id}      → PostgreSQL (persisted)
```

---

## Implementation Order

### Week 1: Fix Immediate Issues
1. Add health check trigger endpoint
2. Update reload button to use new endpoint
3. Test with docker-control-mcp

### Week 2: Real-time Updates
1. Add WebSocket subscription to frontend
2. Test status change events
3. Add toast notifications

### Week 3: Redis Caching
1. Add capabilities endpoint
2. Update frontend to use Redis cache
3. Verify tool testing still works

### Week 4: Testing & Polish
1. End-to-end testing
2. Performance testing
3. Documentation updates

---

## Risk Mitigation

### Risk: Breaking Tool Testing
**Mitigation:** Test tool execution after every change

### Risk: WebSocket Connection Issues
**Mitigation:** Add reconnection logic with exponential backoff

### Risk: Stale Redis Cache
**Mitigation:** Cache already refreshes on hot reload (every 30s)

### Risk: Database vs Redis Inconsistency
**Mitigation:** PostgreSQL remains source of truth for config, Redis only for ephemeral data

---

## Success Metrics

1. **Status Updates:** < 2 seconds from health check to UI update (currently 60s)
2. **Reload Button:** < 3 seconds to show fresh status (currently shows stale data)
3. **Tool Testing:** 100% functional (no regressions)
4. **No Blinking:** Status changes only after circuit breaker thresholds met
5. **Real-time Events:** WebSocket delivers events within 500ms

---

## Questions Answered

**Q: Will status blink between health checks?**
A: No. Circuit breaker requires 5 consecutive failures before marking unhealthy. Already implemented.

**Q: Should we add more logic to prevent blinking?**
A: No. Existing circuit breaker is well-designed and sufficient.

**Q: How does dashboard get data?**
A: Frontend → Dashboard Backend → Redis (status) + PostgreSQL (config)

**Q: Will tool testing still work?**
A: Yes. We're only changing how status is displayed, not how tools are executed.

**Q: What about authentication?**
A: No changes to auth flow. Existing bearer token/API key system remains.
