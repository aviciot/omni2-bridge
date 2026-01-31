# Circuit Breaker Configuration & Auto-Disable Implementation

## 📋 Summary

This implementation adds **configurable circuit breaker settings** and **automatic MCP disabling** after repeated failure cycles.

---

## ✅ What Was Implemented

### 1. **Database Configuration System**
- Circuit breaker settings stored in `omni2_config` table
- Runtime configuration with hot-reload capability
- No need to restart application when changing settings

### 2. **Auto-Disable Tracking**
- New fields in `mcp_servers` table:
  - `failure_cycle_count` - Tracks complete failure cycles
  - `max_failure_cycles` - Threshold before auto-disable (default: 3)
  - `auto_disabled_at` - Timestamp when disabled
  - `auto_disabled_reason` - Detailed reason for disable
  - `can_auto_enable` - Permission flag for re-enabling

### 3. **Circuit Breaker Enhancements**
- Tracks failure cycles (OPEN → HALF_OPEN → OPEN = 1 cycle)
- Auto-disables MCP after max cycles reached
- Configurable thresholds and timeouts
- Per-MCP state tracking

### 4. **Admin API Endpoints**
- `GET /api/v1/circuit-breaker/config` - Get current configuration
- `PUT /api/v1/circuit-breaker/config` - Update configuration
- `POST /api/v1/circuit-breaker/mcp/{id}/enable` - Re-enable disabled MCP
- `POST /api/v1/circuit-breaker/mcp/{id}/reset` - Reset circuit breaker
- `GET /api/v1/circuit-breaker/mcp/{id}/status` - Get detailed status

---

## 🔧 Configuration Options

### Circuit Breaker Settings (in database)

```json
{
  "enabled": true,
  "failure_threshold": 5,           // Failures before circuit opens
  "timeout_seconds": 60,             // How long circuit stays open
  "half_open_max_calls": 3,          // Test calls in HALF_OPEN state
  "max_failure_cycles": 3,           // Cycles before auto-disable
  "auto_disable_enabled": true       // Enable/disable auto-disable feature
}
```

### How to Change Configuration

**Option 1: Via API**
```bash
curl -X PUT http://localhost:8000/api/v1/circuit-breaker/config \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "failure_threshold": 10,
    "timeout_seconds": 120,
    "half_open_max_calls": 5,
    "max_failure_cycles": 5,
    "auto_disable_enabled": true
  }'
```

**Option 2: Direct Database Update**
```sql
UPDATE omni2.omni2_config 
SET config_value = '{
  "enabled": true,
  "failure_threshold": 10,
  "timeout_seconds": 120,
  "half_open_max_calls": 5,
  "max_failure_cycles": 5,
  "auto_disable_enabled": true
}'::jsonb
WHERE config_key = 'circuit_breaker';
```

---

## 🔄 How Auto-Disable Works

### Failure Cycle Flow

```
1. MCP fails 5 times → Circuit OPENS
2. Wait 60 seconds → Circuit moves to HALF_OPEN
3. Test with 3 calls → If fails → Circuit OPENS again (Cycle 1)
4. Repeat steps 2-3 → (Cycle 2)
5. Repeat steps 2-3 → (Cycle 3)
6. After 3 cycles → MCP status changes to 'inactive'
```

### What Happens When Auto-Disabled

- MCP `status` changes from `'active'` to `'inactive'`
- System stops trying to connect
- `auto_disabled_at` timestamp recorded
- `auto_disabled_reason` contains detailed error message
- MCP filtered out from active MCP list

---

## 🎛️ Dashboard Integration

### Re-Enable Disabled MCP

**Via API:**
```bash
# Re-enable and reset counters
curl -X POST http://localhost:8000/api/v1/circuit-breaker/mcp/1/enable?reset_counters=true

# Re-enable without resetting counters
curl -X POST http://localhost:8000/api/v1/circuit-breaker/mcp/1/enable?reset_counters=false
```

**What Happens:**
1. Status changes back to `'active'`
2. Failure counters reset (if requested)
3. Circuit breaker state reset
4. System attempts to reconnect immediately
5. Audit log entry created

### Check MCP Status

```bash
curl http://localhost:8000/api/v1/circuit-breaker/mcp/1/status
```

**Response:**
```json
{
  "success": true,
  "server": {
    "id": 1,
    "name": "informatica_mcp",
    "status": "inactive",
    "health_status": "unhealthy"
  },
  "circuit_breaker": {
    "state": "open",
    "failure_cycles": 3,
    "retry_after_seconds": 45,
    "is_open": true
  },
  "auto_disable": {
    "failure_cycle_count": 3,
    "max_failure_cycles": 3,
    "auto_disabled_at": "2025-01-15T10:30:00Z",
    "auto_disabled_reason": "Auto-disabled after 3 failure cycles. Last error: Connection refused",
    "can_auto_enable": true
  }
}
```

---

## 📁 Files Modified/Created

### Created Files
1. `migrations/018_add_auto_disable_fields.sql` - Database migration
2. `app/routers/circuit_breaker.py` - API endpoints
3. `docs/CIRCUIT_BREAKER_IMPLEMENTATION.md` - This document

### Modified Files
1. `app/models.py` - Added auto-disable fields to MCPServer model
2. `app/services/circuit_breaker.py` - Added cycle tracking and auto-disable logic
3. `app/services/mcp_registry.py` - Integrated auto-disable on failure
4. `app/main.py` - Registered circuit breaker router

---

## 🚀 Deployment Steps

### 1. Run Database Migration
```bash
psql -U postgres -d omni -f migrations/018_add_auto_disable_fields.sql
```

### 2. Restart Application
```bash
# Docker
docker-compose restart omni2

# Local
# Application will auto-reload if in dev mode
```

### 3. Verify Configuration
```bash
curl http://localhost:8000/api/v1/circuit-breaker/config
```

---

## 🧪 Testing

### Test Auto-Disable Flow

1. **Create test MCP with low thresholds:**
```sql
UPDATE omni2.omni2_config 
SET config_value = '{
  "enabled": true,
  "failure_threshold": 2,
  "timeout_seconds": 10,
  "half_open_max_calls": 1,
  "max_failure_cycles": 2,
  "auto_disable_enabled": true
}'::jsonb
WHERE config_key = 'circuit_breaker';
```

2. **Stop MCP server** (simulate failure)

3. **Trigger requests** to the MCP

4. **Watch logs** for auto-disable message:
```
🚫 MCP auto-disabled after 2 failure cycles
```

5. **Check database:**
```sql
SELECT name, status, failure_cycle_count, auto_disabled_reason 
FROM omni2.mcp_servers 
WHERE auto_disabled_at IS NOT NULL;
```

6. **Re-enable via API:**
```bash
curl -X POST http://localhost:8000/api/v1/circuit-breaker/mcp/1/enable
```

---

## 📊 Monitoring

### Query Auto-Disabled MCPs
```sql
SELECT 
    id,
    name,
    status,
    failure_cycle_count,
    auto_disabled_at,
    auto_disabled_reason
FROM omni2.mcp_servers
WHERE status = 'inactive' 
  AND auto_disabled_at IS NOT NULL
ORDER BY auto_disabled_at DESC;
```

### Query Circuit Breaker Events
```sql
SELECT 
    m.name,
    h.timestamp,
    h.status,
    h.event_type,
    h.error_message,
    h.metadata
FROM omni2.mcp_health_log h
JOIN omni2.mcp_servers m ON h.mcp_server_id = m.id
WHERE h.event_type IN ('load_failed', 'health_check_failed')
ORDER BY h.timestamp DESC
LIMIT 50;
```

---

## 🎯 Next Steps (Dashboard UI)

### Recommended Dashboard Features

1. **MCP Status Panel**
   - Show circuit breaker state (CLOSED/OPEN/HALF_OPEN)
   - Display failure cycle count
   - Show time until retry
   - Highlight auto-disabled MCPs

2. **Re-Enable Button**
   - One-click re-enable for disabled MCPs
   - Confirmation dialog with reason display
   - Option to reset counters

3. **Configuration Panel**
   - Edit circuit breaker settings
   - Per-MCP override settings
   - Real-time validation

4. **Monitoring Dashboard**
   - Failure cycle trends
   - Auto-disable history
   - Circuit breaker state timeline

---

## 🔐 Security Considerations

- Only admins should access circuit breaker endpoints
- Add authentication middleware to `/api/v1/circuit-breaker/*`
- Audit all re-enable actions
- Rate limit configuration changes

---

## 📝 Notes

- Configuration changes take effect immediately (hot-reload)
- Auto-disable only affects `status`, not database record
- Re-enabling triggers immediate connection attempt
- Circuit breaker state is in-memory (resets on restart)
- Database tracks persistent failure counts
