# 🔌 WebSocket System - Complete Analysis

## 📊 **Architecture Overview**

```
┌─────────────────┐
│   Dashboard     │  ws://localhost:3001/ws/mcp-status
│   Frontend      │  (React/Next.js)
│  (Port 3001)    │
└────────┬────────┘
         │
         ↓ WebSocket Connection
┌─────────────────┐
│   Dashboard     │  ws://host.docker.internal:8090/ws/mcp-status
│   Backend       │  (Proxy Layer)
│  (Port 3001)    │
└────────┬────────┘
         │
         ↓ Through Docker Network
┌─────────────────┐
│    Traefik      │  Routes /ws/* → omni2:8000
│   Gateway       │  (No Auth, Priority 200)
│  (Port 8090)    │
└────────┬────────┘
         │
         ↓ Internal Network
┌─────────────────┐
│     OMNI2       │  /ws/mcp-status endpoint
│    Backend      │  (WebSocket Server)
│  (Port 8000)    │
└─────────────────┘
```

---

## 🎯 **Purpose**

**Real-time MCP status updates to dashboard without polling**

### What It Broadcasts:
1. **MCP Status Changes** - healthy/unhealthy/disconnected
2. **Health Events** - recovery/failure/circuit_open
3. **System Metrics** - performance data
4. **Circuit Breaker State** - CLOSED/OPEN/HALF_OPEN

---

## 🔧 **Components Breakdown**

### **1. OMNI2 Backend (WebSocket Server)**
**File:** `app/routers/websocket.py`

```python
@router.websocket("/ws/mcp-status")
async def websocket_mcp_status(websocket: WebSocket):
    # Accept connection
    conn_id = await broadcaster.connect(websocket, user_id, user_role)
    
    # Keep alive and handle messages
    while True:
        data = await websocket.receive_text()
        if data == "ping":
            await websocket.send_text("pong")
```

**Key Features:**
- Accepts WebSocket connections
- Assigns connection ID
- Handles ping/pong for keep-alive
- Delegates to broadcaster service

---

### **2. WebSocket Broadcaster Service**
**File:** `app/services/websocket_broadcaster.py`

**Core Class:** `WebSocketBroadcaster`

#### **Connection Management:**
```python
connections: Dict[str, WebSocketConnection] = {}
# Key: "user_id_timestamp"
# Value: WebSocketConnection(websocket, user_id, user_role)
```

#### **Message Queue:**
```python
message_queue: asyncio.Queue = asyncio.Queue()
# Async queue for broadcasting messages
```

#### **Main Methods:**

| Method | Purpose |
|--------|---------|
| `connect()` | Accept new WebSocket, send initial status |
| `disconnect()` | Close connection, cleanup |
| `broadcast_mcp_status()` | Send MCP status change to all clients |
| `broadcast_health_event()` | Send health event to all clients |
| `broadcast_system_metrics()` | Send system metrics |
| `_broadcaster_loop()` | Background task processing message queue |

---

### **3. Broadcaster Loop (Background Task)**

**Started on app startup** in `main.py`:
```python
await start_websocket_broadcaster()
```

**Loop Logic:**
```python
while self.running:
    # 1. Process message queue (1 sec timeout)
    message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
    await self._broadcast_message(message)
    
    # 2. Cleanup stale connections (5 min timeout)
    await self._cleanup_stale_connections()
    
    # 3. Send periodic ping
    await self._send_periodic_ping()
```

---

### **4. Message Types**

#### **Initial Status** (on connect):
```json
{
  "type": "initial_status",
  "timestamp": "2026-01-29T10:00:00",
  "mcps": [
    {
      "name": "informatica_mcp",
      "health_status": "healthy",
      "circuit_state": "closed",
      "last_health_check": "2026-01-29T09:59:00"
    }
  ]
}
```

#### **MCP Status Change**:
```json
{
  "type": "mcp_status_change",
  "timestamp": "2026-01-29T10:00:00",
  "mcp_name": "informatica_mcp",
  "status": "unhealthy",
  "metadata": {
    "error": "Connection timeout",
    "circuit_state": "open"
  }
}
```

#### **Health Event**:
```json
{
  "type": "health_event",
  "timestamp": "2026-01-29T10:00:00",
  "mcp_name": "informatica_mcp",
  "event_type": "recovery",
  "data": {
    "previous_state": "unhealthy",
    "new_state": "healthy"
  }
}
```

#### **System Metrics**:
```json
{
  "type": "system_metrics",
  "timestamp": "2026-01-29T10:00:00",
  "metrics": {
    "total_mcps": 3,
    "healthy_mcps": 2,
    "unhealthy_mcps": 1
  }
}
```

#### **Ping** (keep-alive):
```json
{
  "type": "ping",
  "timestamp": "2026-01-29T10:00:00"
}
```

---

## 🔐 **Security & Routing**

### **Traefik Configuration**

**Priority:** 200 (highest)
**Path:** `/ws/*`
**Middleware:** NONE (no auth)
**Service:** omni2:8000

```yaml
# In docker-compose.yml
- "traefik.http.routers.omni2-ws.rule=PathPrefix(`/ws/`)"
- "traefik.http.routers.omni2-ws.priority=200"
- "traefik.http.routers.omni2-ws.service=omni2"
```

**Why no auth?**
- WebSocket connections are long-lived
- Auth happens at dashboard backend layer
- Dashboard backend acts as secure proxy

---

## 🔄 **How It Works (Step-by-Step)**

### **Connection Flow:**

1. **Frontend connects** to dashboard backend:
   ```
   ws://localhost:3001/ws/mcp-status
   ```

2. **Dashboard backend proxies** to Traefik:
   ```
   ws://host.docker.internal:8090/ws/mcp-status
   ```

3. **Traefik routes** to OMNI2:
   ```
   ws://omni2:8000/ws/mcp-status
   ```

4. **OMNI2 accepts** connection:
   - Assigns connection ID
   - Sends initial MCP status
   - Adds to broadcaster's connection pool

### **Broadcasting Flow:**

1. **Event occurs** (e.g., MCP fails):
   ```python
   # In mcp_registry.py
   broadcaster = get_websocket_broadcaster()
   await broadcaster.broadcast_mcp_status(
       mcp_name="informatica_mcp",
       status="unhealthy",
       metadata={"error": "Connection timeout"}
   )
   ```

2. **Message queued**:
   ```python
   await self.message_queue.put(message)
   ```

3. **Broadcaster loop processes**:
   ```python
   message = await self.message_queue.get()
   await self._broadcast_message(message)
   ```

4. **Sent to all connections**:
   ```python
   for conn in self.connections.values():
       await conn.websocket.send_text(json.dumps(message))
   ```

5. **Frontend receives** and updates UI

---

## 🚨 **Current Integration Points**

### **Where WebSocket is Called:**

**Currently:** NOT INTEGRATED with circuit breaker/auto-disable

**Should be called from:**

1. **`mcp_registry.py`** - When MCP status changes:
   ```python
   # After auto-disable
   broadcaster = get_websocket_broadcaster()
   await broadcaster.broadcast_mcp_status(
       mcp_name=mcp.name,
       status="inactive",
       metadata={
           "reason": "auto_disabled",
           "failure_cycles": mcp.failure_cycle_count
       }
   )
   ```

2. **`circuit_breaker.py`** - When circuit state changes:
   ```python
   # When circuit opens
   await broadcaster.broadcast_health_event(
       mcp_name=mcp_name,
       event_type="circuit_opened",
       data={"failures": count}
   )
   ```

---

## ⚠️ **Current Issues**

### **1. Not Integrated with Circuit Breaker**
- Circuit breaker state changes don't trigger WebSocket broadcasts
- Dashboard won't see real-time circuit state updates

### **2. Not Integrated with Auto-Disable**
- When MCP auto-disables, no WebSocket notification sent
- Dashboard needs to poll to see status change

### **3. Missing Database Field**
- `circuit_state` column doesn't exist in `mcp_servers` table
- Initial status query will fail

---

## ✅ **What Works**

1. ✅ WebSocket connection/disconnection
2. ✅ Message queue and broadcasting
3. ✅ Ping/pong keep-alive
4. ✅ Multiple client support
5. ✅ Stale connection cleanup
6. ✅ Traefik routing

---

## 🔧 **What Needs Integration**

### **Add to `mcp_registry.py`:**
```python
from app.services.websocket_broadcaster import get_websocket_broadcaster

# After auto-disable
broadcaster = get_websocket_broadcaster()
await broadcaster.broadcast_mcp_status(
    mcp_name=mcp.name,
    status="inactive",
    metadata={"auto_disabled": True, "cycles": mcp.failure_cycle_count}
)

# After successful load
await broadcaster.broadcast_mcp_status(
    mcp_name=mcp.name,
    status="healthy",
    metadata={"tools_count": len(tools)}
)
```

### **Add to `circuit_breaker.py`:**
```python
# When circuit opens
await broadcaster.broadcast_health_event(
    mcp_name=mcp_name,
    event_type="circuit_opened",
    data={"state": "open", "failures": count}
)

# When circuit moves to half_open
await broadcaster.broadcast_health_event(
    mcp_name=mcp_name,
    event_type="circuit_half_open",
    data={"state": "half_open"}
)
```

---

## 📝 **Summary**

**WebSocket System:**
- ✅ **Infrastructure:** Fully built and working
- ✅ **Broadcasting:** Message queue and delivery working
- ✅ **Connections:** Multi-client support working
- ❌ **Integration:** NOT connected to circuit breaker/auto-disable
- ❌ **Database:** Missing `circuit_state` column

**To make it useful:** Need to add broadcast calls in `mcp_registry.py` and `circuit_breaker.py` when status changes occur.
