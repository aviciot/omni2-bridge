# MCP Server Status System - Explanation & Improvement Plan

## 📊 **Current Status System**

### **How Status is Presented**

The MCP servers list shows a **Status** column with colored badges:

| Status | Badge | Meaning |
|--------|-------|---------|
| **Healthy** | 🟢 Green | MCP server responded to health check successfully |
| **Unhealthy** | 🔴 Red | MCP server failed health check or unreachable |
| **Unknown** | 🟡 Yellow | No health check performed yet |
| **Disabled** | ⚪ Gray | Server is disabled in database |

### **Status Badge Code**
```typescript
const getStatusBadge = (status: string, enabled: boolean) => {
  if (!enabled) return "Disabled";
  
  switch (status) {
    case 'healthy': return "Healthy" (green);
    case 'unhealthy': return "Unhealthy" (red);
    default: return "Unknown" (yellow);
  }
};
```

---

## 🔄 **How Information Flows**

### **Current Architecture (Pull-Based)**

```
┌─────────────────┐
│   Dashboard     │
│   Frontend      │
│  (React/Next)   │
└────────┬────────┘
         │ HTTP GET /api/v1/mcp/tools/servers
         ↓
┌─────────────────┐
│   Dashboard     │
│    Backend      │
│   (FastAPI)     │
└────────┬────────┘
         │ HTTP GET via Traefik
         ↓
┌─────────────────┐
│     Omni2       │
│      App        │
│   (FastAPI)     │
└────────┬────────┘
         │ Query Database
         ↓
┌─────────────────┐
│   PostgreSQL    │
│   mcp_servers   │
│   table         │
└─────────────────┘
```

### **Data Flow Steps:**

1. **Frontend Loads** → Calls `mcpApi.getServers()`
2. **Dashboard Backend** → Proxies request to Omni2 via Traefik
3. **Omni2 App** → Queries `mcp_servers` table in PostgreSQL
4. **Database Returns** → Server records with `health_status` field
5. **Response Flows Back** → Through Omni2 → Dashboard Backend → Frontend
6. **Frontend Renders** → Status badges based on `health_status` field

### **When Status Updates:**

Currently, status updates happen:
- ❌ **NOT in real-time**
- ✅ **On page load** (frontend fetches data)
- ✅ **On manual reload** (user clicks reload button)
- ✅ **On periodic health checks** (if configured in Omni2)

---

## 🗄️ **Database Schema**

### **mcp_servers Table**
```sql
CREATE TABLE mcp_servers (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) UNIQUE NOT NULL,
  url VARCHAR(512) NOT NULL,
  protocol VARCHAR(50) DEFAULT 'http',
  enabled BOOLEAN DEFAULT true,
  health_status VARCHAR(50) DEFAULT 'unknown',  -- ← Status stored here
  last_health_check TIMESTAMP,                  -- ← Last check time
  timeout_seconds INTEGER DEFAULT 30,
  auth_type VARCHAR(50),
  auth_config JSONB,
  description TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### **How Status Gets Updated:**

1. **Background Health Checker** (if running in Omni2):
   - Periodically pings each MCP server's `/health` endpoint
   - Updates `health_status` and `last_health_check` in database
   - Runs every X minutes (configurable)

2. **Manual Reload**:
   - User clicks "Reload" button
   - Triggers health check immediately
   - Updates database

3. **On Server Registration**:
   - When adding new MCP server
   - Discovery process checks health
   - Sets initial status

---

## ⚠️ **Current Limitations**

### **Problems:**

1. ❌ **No Real-Time Updates**
   - Status only updates when page refreshes
   - User must manually reload to see changes
   - Stale data if MCP goes down

2. ❌ **Polling Required**
   - Frontend must poll backend repeatedly
   - Wastes bandwidth and resources
   - Delays in seeing status changes

3. ❌ **No Notifications**
   - User doesn't know when MCP goes down
   - No alerts for unhealthy servers
   - Must actively check dashboard

4. ❌ **Limited History**
   - Only shows current status
   - No uptime tracking
   - No historical health data

---

## 🚀 **Improvement Plan Using Redis Streams**

### **Why Redis Streams?**

Omni2 already has Redis infrastructure for:
- WebSocket broadcasting
- Event streaming
- Real-time updates

We can leverage this for **real-time MCP status updates**!

### **Proposed Architecture (Push-Based)**

```
┌─────────────────┐
│  Health Checker │  ← Background worker in Omni2
│   (Omni2 App)   │
└────────┬────────┘
         │ Checks MCP health every 30s
         ↓
┌─────────────────┐
│   PostgreSQL    │  ← Updates database
│   mcp_servers   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Redis Stream   │  ← Publishes event
│ "mcp:health"    │
└────────┬────────┘
         │ Real-time event
         ↓
┌─────────────────┐
│   Dashboard     │  ← Listens via WebSocket
│   Frontend      │
└─────────────────┘
```

### **Implementation Steps:**

#### **1. Redis Stream Events**

Create a new Redis stream for MCP health events:

```python
# In Omni2 health checker
async def publish_health_update(server_name: str, status: str):
    event = {
        "server_name": server_name,
        "health_status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "response_time_ms": response_time
    }
    
    await redis.xadd(
        "mcp:health:updates",
        {"data": json.dumps(event)}
    )
```

#### **2. WebSocket Subscription**

Dashboard frontend subscribes to MCP health updates:

```typescript
// In Dashboard Frontend
useEffect(() => {
  const ws = new WebSocket('ws://localhost:3000/ws');
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'mcp_health_update') {
      // Update server status in real-time
      updateServerStatus(data.server_name, data.health_status);
    }
  };
}, []);
```

#### **3. Background Health Checker**

Continuous health monitoring in Omni2:

```python
# In Omni2 App
async def health_checker_loop():
    while True:
        servers = await get_enabled_mcp_servers()
        
        for server in servers:
            try:
                # Check health
                status = await check_mcp_health(server)
                
                # Update database
                await update_server_health(server.id, status)
                
                # Publish to Redis stream
                await publish_health_update(server.name, status)
                
            except Exception as e:
                await publish_health_update(server.name, "unhealthy")
        
        await asyncio.sleep(30)  # Check every 30 seconds
```

---

## 🎯 **Benefits of Redis Stream Approach**

### **Real-Time Updates**
✅ Status updates appear instantly in dashboard
✅ No need to refresh page
✅ See MCP failures immediately

### **Efficient**
✅ No polling required
✅ Push-based updates only when status changes
✅ Reduces server load

### **Scalable**
✅ Multiple dashboard instances can subscribe
✅ Redis handles fan-out efficiently
✅ Works with load balancing

### **Rich Events**
✅ Can include response time, error messages
✅ Historical data in Redis stream
✅ Can replay events if needed

### **Notifications**
✅ Can trigger alerts when MCP goes down
✅ Email/Slack notifications possible
✅ Dashboard can show toast notifications

---

## 📈 **Additional Improvements**

### **1. Uptime Tracking**
```sql
CREATE TABLE mcp_health_history (
  id SERIAL PRIMARY KEY,
  server_id INTEGER REFERENCES mcp_servers(id),
  health_status VARCHAR(50),
  response_time_ms INTEGER,
  error_message TEXT,
  checked_at TIMESTAMP DEFAULT NOW()
);
```

### **2. Status Dashboard Widget**
```
┌─────────────────────────────┐
│  MCP Server Health          │
├─────────────────────────────┤
│  🟢 performance_mcp  99.9%  │
│  🟢 docker_mcp       100%   │
│  🔴 template_mcp     0%     │
│                             │
│  Last 24h: 3 incidents      │
└─────────────────────────────┘
```

### **3. Alert Rules**
```yaml
alerts:
  - name: "MCP Down"
    condition: "health_status == 'unhealthy'"
    duration: "5 minutes"
    actions:
      - slack: "#alerts"
      - email: "admin@company.com"
```

---

## 🔧 **Implementation Priority**

### **Phase 1: Real-Time Status (High Priority)**
- Add Redis stream publishing in health checker
- Add WebSocket subscription in dashboard
- Show live status updates

### **Phase 2: History & Analytics (Medium Priority)**
- Create health_history table
- Track uptime percentage
- Show historical charts

### **Phase 3: Alerts & Notifications (Low Priority)**
- Configure alert rules
- Slack/Email integration
- Dashboard notifications

---

## 📝 **Summary**

### **Current System:**
- ❌ Pull-based (polling)
- ❌ No real-time updates
- ❌ Manual refresh required
- ✅ Simple and working

### **Improved System:**
- ✅ Push-based (Redis streams)
- ✅ Real-time updates
- ✅ Automatic notifications
- ✅ Historical tracking
- ✅ Leverages existing Redis infrastructure

**Recommendation:** Implement Phase 1 (Real-Time Status) first, as it provides immediate value with minimal changes to existing architecture.
