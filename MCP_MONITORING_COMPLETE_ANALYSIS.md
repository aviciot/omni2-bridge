# MCP Monitoring System - Complete Analysis & Improvement Plan

## 🔍 **Current System - How It Works**

### **1. Background Health Checker Loop**
Location: `omni2/app/main.py` → `health_check_loop()`

```python
async def health_check_loop():
    interval = 60  # Default: every 60 seconds
    
    while True:
        # Load config from database
        config = await db.get_config('health_check')
        interval = config.get('interval_seconds', 60)
        
        # Check health of ALL MCPs
        mcp_registry = get_mcp_registry()
        for mcp_name in mcp_registry.get_loaded_mcps():
            await mcp_registry.health_check(mcp_name, db)
        
        await asyncio.sleep(interval)
```

**What it does:**
- ✅ Runs continuously in background
- ✅ Checks ALL loaded MCPs every 60 seconds (configurable)
- ✅ Updates database `health_status` field
- ✅ Logs health events to `mcp_health_logs` table

---

### **2. Health Check Process**
Location: `omni2/app/services/mcp_registry.py` → `health_check()`

```python
async def health_check(self, mcp_name: str, db: AsyncSession):
    # 1. Check if MCP is loaded
    if mcp_name not in self.mcps:
        # Update DB: unhealthy
        mcp.health_status = 'unhealthy'
        await db.commit()
        return {"healthy": False}
    
    # 2. Try to list tools (health check)
    try:
        tools_result = await client.list_tools()
        
        # 3. Log success
        await self._log_health(db, mcp.id, 'healthy', response_time_ms)
        
        return {"healthy": True, "tool_count": len(tools)}
        
    except Exception as e:
        # 4. Update DB: unhealthy
        mcp.health_status = 'unhealthy'
        await db.commit()
        
        # 5. Log failure
        await self._log_health(db, mcp.id, 'unhealthy', error_message=str(e))
        
        return {"healthy": False, "error": str(e)}
```

---

### **3. When Status Changes - Redis Events**
Location: `omni2/app/services/mcp_registry.py` → `load_mcp()`

```python
# When status changes from unhealthy → healthy
if old_health_status != 'healthy':
    broadcaster = get_websocket_broadcaster()
    await broadcaster.broadcast_event(
        event_type="mcp_status_change",
        event_data={
            "mcp_name": mcp.name,
            "old_status": old_health_status,
            "new_status": "healthy",
            "reason": "Successfully connected",
            "severity": "info",
            "tool_count": len(tools),
            "response_time_ms": response_time_ms
        }
    )

# When status changes from healthy → unhealthy
if old_health_status != 'unhealthy':
    await broadcaster.broadcast_event(
        event_type="mcp_status_change",
        event_data={
            "mcp_name": mcp.name,
            "old_status": old_health_status,
            "new_status": "unhealthy",
            "reason": error_msg,
            "severity": "high",
            "error_count": mcp.error_count
        }
    )
```

**Redis Stream:** `system:events`

---

### **4. Dashboard Gets Status**
Location: `omni2/dashboard/frontend` → `mcpApi.getServers()`

```
Frontend → Dashboard Backend → Omni2 App → PostgreSQL
```

**Query:**
```sql
SELECT id, name, url, health_status, last_health_check
FROM omni2.mcp_servers
WHERE status = 'active'
```

**Returns:**
```json
{
  "servers": [
    {
      "name": "docker_controller_auth",
      "health_status": "unhealthy",  // ← From database
      "last_health_check": "2026-02-20T14:30:00Z"
    }
  ]
}
```

---

## ⚠️ **Current Problems**

### **Problem 1: Stale Status in Dashboard**
```
Health Check Loop (60s) → Updates DB → Dashboard polls → Shows status
                          ↓
                    Takes 60s to update!
```

**Why "docker_controller_auth" shows unhealthy:**
1. Health check ran BEFORE auth was configured → Failed → Set `health_status = 'unhealthy'`
2. You added auth token to database
3. Health logs NOW use correct token → Show healthy
4. But `health_status` field still says "unhealthy" (waiting for next check)
5. Dashboard shows the OLD `health_status` value

**Solution:** Wait for next health check cycle (60s) OR click reload button

---

### **Problem 2: No Real-Time Updates**
- ❌ Dashboard doesn't listen to Redis events
- ❌ Must refresh page to see changes
- ❌ Reload button might be disabled (UI bug)

---

### **Problem 3: Mixed Data Sources**
**Current confusion:**
- **URL, Protocol, Timeout** → Should come from **Database** (source of truth)
- **Capabilities (tools/prompts/resources)** → Should come from **Redis Cache** (fast)
- **Status** → Should come from **Redis Stream** (real-time)

**Right now:**
- Everything comes from Database (slow, stale)
- Redis events are published but dashboard doesn't listen

---

## 🎯 **Recommended Architecture**

### **Data Source Strategy:**

| Data Type | Source | Why | Update Frequency |
|-----------|--------|-----|------------------|
| **Static Config** | PostgreSQL | Source of truth | On edit only |
| **Capabilities** | Redis Cache | Fast access | On MCP reload |
| **Status** | Redis Stream | Real-time | On status change |
| **Health Logs** | PostgreSQL | Historical data | Every check |

### **Static Config (Database)**
```
- name
- url
- protocol
- timeout_seconds
- auth_type
- auth_config
- description
```

### **Capabilities (Redis Cache)**
```
Key: mcp:capabilities:{mcp_name}
Value: {
  "tools": [...],
  "prompts": [...],
  "resources": [...],
  "cached_at": "2026-02-20T14:30:00Z"
}
TTL: 10 minutes
```

### **Status (Redis Stream)**
```
Stream: mcp:status:updates
Events:
  - mcp_status_change
  - mcp_auto_disabled
  - mcp_health_check
```

---

## 🚀 **Improvement Plan**

### **Phase 1: Fix Immediate Issues** (Quick Wins)

#### **1.1 Fix Reload Button**
```typescript
// dashboard/frontend/src/components/mcp/MCPServerTable.tsx
const handleReload = async (serverName: string) => {
  setReloading(serverName);
  try {
    await mcpApi.checkHealth(serverName);
    await refreshServers(); // Refresh list
  } finally {
    setReloading(null);
  }
};
```

#### **1.2 Add Manual Refresh Button**
```typescript
<button onClick={() => refreshServers()}>
  🔄 Refresh All
</button>
```

---

### **Phase 2: Real-Time Status Updates** (High Priority)

#### **2.1 Dashboard Listens to Redis Events**
```typescript
// dashboard/frontend/src/hooks/useMCPStatus.ts
useEffect(() => {
  const ws = new WebSocket('ws://localhost:3000/ws');
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'mcp_status_change') {
      // Update server status in real-time
      updateServerStatus(data.mcp_name, data.new_status);
      
      // Show toast notification
      toast.info(`${data.mcp_name}: ${data.old_status} → ${data.new_status}`);
    }
  };
}, []);
```

#### **2.2 Omni2 Already Publishes Events!**
✅ Events are already being published to Redis
✅ Just need dashboard to subscribe

---

### **Phase 3: Optimize Data Flow** (Medium Priority)

#### **3.1 Cache Capabilities in Redis**
```python
# omni2/app/services/mcp_registry.py
async def load_mcp(self, mcp: MCPServer, db: AsyncSession):
    # ... existing code ...
    
    # Cache capabilities in Redis
    await redis.setex(
        f"mcp:capabilities:{mcp.name}",
        600,  # 10 minutes TTL
        json.dumps({
            "tools": tools,
            "prompts": prompts,
            "resources": resources,
            "cached_at": datetime.utcnow().isoformat()
        })
    )
```

#### **3.2 Dashboard Reads from Redis**
```typescript
// Fast path: Get capabilities from Redis
const capabilities = await redis.get(`mcp:capabilities:${mcpName}`);

// Fallback: Get from database if not in cache
if (!capabilities) {
  capabilities = await mcpApi.getCapabilities(mcpName);
}
```

---

### **Phase 4: Smart Health Checking** (Low Priority)

#### **4.1 Adaptive Intervals**
```python
# Check healthy MCPs less frequently
if mcp.health_status == 'healthy':
    interval = 300  # 5 minutes
else:
    interval = 30   # 30 seconds (check unhealthy more often)
```

#### **4.2 Event-Driven Checks**
```python
# Check immediately when:
- MCP config changes
- Auth token updated
- Manual reload requested
```

---

## 📊 **Recommended Data Flow**

### **On Page Load:**
```
1. Frontend → GET /api/v1/mcp/tools/servers
2. Backend → Query PostgreSQL (static config)
3. Backend → Query Redis (capabilities cache)
4. Backend → Merge data
5. Frontend → Display table
6. Frontend → Subscribe to WebSocket (real-time updates)
```

### **On Status Change:**
```
1. Health Check Loop → Detects change
2. Update PostgreSQL (health_status)
3. Publish to Redis Stream (mcp:status:updates)
4. WebSocket Broadcaster → Push to all connected clients
5. Frontend → Update UI instantly
6. Frontend → Show toast notification
```

### **On Manual Reload:**
```
1. User clicks reload button
2. Frontend → POST /api/v1/mcp/tools/health/{mcp_name}
3. Backend → Trigger immediate health check
4. Backend → Update database
5. Backend → Publish Redis event
6. Frontend → Receives WebSocket update
7. Frontend → Updates UI
```

---

## 🎯 **Implementation Priority**

### **Immediate (This Week):**
1. ✅ Fix reload button (enable it)
2. ✅ Add "Refresh All" button
3. ✅ Show last check timestamp

### **High Priority (Next Week):**
1. ✅ Dashboard subscribes to Redis events
2. ✅ Real-time status updates
3. ✅ Toast notifications for status changes

### **Medium Priority (Next Sprint):**
1. ✅ Cache capabilities in Redis
2. ✅ Optimize data fetching
3. ✅ Add uptime percentage

### **Low Priority (Future):**
1. ✅ Adaptive health check intervals
2. ✅ Historical status charts
3. ✅ Alert rules and notifications

---

## 🔧 **Quick Fix for Your Issue**

**Why "docker_controller_auth" shows unhealthy:**
```sql
-- Check current status
SELECT name, health_status, last_health_check, auth_config
FROM omni2.mcp_servers
WHERE name = 'docker_controller_auth';

-- Manual fix (if needed)
UPDATE omni2.mcp_servers
SET health_status = 'healthy',
    last_health_check = NOW()
WHERE name = 'docker_controller_auth';
```

**Or wait 60 seconds** for the next health check cycle to run with the correct auth token.

---

## 📝 **Summary**

### **Current System:**
- ✅ Background health checker runs every 60s
- ✅ Updates database
- ✅ Publishes Redis events
- ❌ Dashboard doesn't listen to events
- ❌ Dashboard shows stale data

### **Recommended System:**
- ✅ Keep background health checker
- ✅ Keep database updates
- ✅ Keep Redis events
- ✅ **ADD:** Dashboard subscribes to WebSocket
- ✅ **ADD:** Real-time UI updates
- ✅ **ADD:** Redis cache for capabilities

**Next Step:** Implement Phase 1 (Fix reload button) and Phase 2 (Real-time updates) for immediate improvement.
