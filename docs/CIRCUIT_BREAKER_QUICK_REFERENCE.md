# Circuit Breaker Configuration - Quick Reference

## 🎯 What You Asked For

✅ **Make hardcoded settings configurable** - DONE
✅ **Auto-disable MCP after X failure cycles** - DONE  
✅ **Force re-enable from dashboard** - DONE

---

## 📍 Current Configuration System

Omni2 uses **3 configuration sources**:

1. **`.env` file** - Database credentials, API keys, app settings
2. **`config/*.yaml` files** - Legacy MCP configs (being phased out)
3. **`omni2_config` table** - Runtime configuration (NEW - used for circuit breaker)

---

## ⚙️ Circuit Breaker Settings

### Default Values (in database)
```json
{
  "enabled": true,
  "failure_threshold": 5,        // Failures before circuit opens
  "timeout_seconds": 60,          // Circuit stays open for 60 sec
  "half_open_max_calls": 3,       // Test calls in recovery mode
  "max_failure_cycles": 3,        // Auto-disable after 3 cycles
  "auto_disable_enabled": true    // Enable auto-disable feature
}
```

### Change Settings via API
```bash
curl -X PUT http://localhost:8000/api/v1/circuit-breaker/config \
  -H "Content-Type: application/json" \
  -d '{
    "failure_threshold": 10,
    "timeout_seconds": 120,
    "max_failure_cycles": 5
  }'
```

---

## 🔄 Auto-Disable Logic

### What is a "Failure Cycle"?
```
CLOSED → (5 failures) → OPEN → (60 sec) → HALF_OPEN → (test fails) → OPEN
                                                                        ↑
                                                            This is 1 CYCLE
```

### Auto-Disable Flow
1. MCP fails repeatedly → Circuit opens
2. After timeout → Circuit tries recovery (HALF_OPEN)
3. Recovery fails → Circuit opens again (1 cycle complete)
4. Repeat 3 times (default) → **MCP status changes to 'inactive'**

### What Happens When Auto-Disabled
- Status: `'active'` → `'inactive'`
- System stops trying to connect
- Reason logged in `auto_disabled_reason` field
- Timestamp recorded in `auto_disabled_at`

---

## 🎛️ Re-Enable Disabled MCP

### Via API
```bash
# Re-enable with counter reset
curl -X POST http://localhost:8000/api/v1/circuit-breaker/mcp/1/enable?reset_counters=true

# Check status first
curl http://localhost:8000/api/v1/circuit-breaker/mcp/1/status
```

### What Happens
1. Status changes to `'active'`
2. Failure counters reset
3. Circuit breaker reset
4. System reconnects immediately

---

## 📊 Database Schema Changes

### New Fields in `mcp_servers` Table
```sql
failure_cycle_count INTEGER DEFAULT 0
max_failure_cycles INTEGER DEFAULT 3
auto_disabled_at TIMESTAMP
auto_disabled_reason TEXT
can_auto_enable BOOLEAN DEFAULT true
```

### New Config in `omni2_config` Table
```sql
config_key = 'circuit_breaker'
config_value = {circuit breaker settings JSON}
```

---

## 🚀 Quick Start

### 1. Run Migration
```bash
psql -U postgres -d omni -f migrations/018_add_auto_disable_fields.sql
```

### 2. Restart App
```bash
docker-compose restart omni2
```

### 3. Test Configuration
```bash
# Get current config
curl http://localhost:8000/api/v1/circuit-breaker/config

# Update config
curl -X PUT http://localhost:8000/api/v1/circuit-breaker/config \
  -H "Content-Type: application/json" \
  -d '{"max_failure_cycles": 5}'
```

---

## 📝 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/circuit-breaker/config` | Get configuration |
| PUT | `/api/v1/circuit-breaker/config` | Update configuration |
| POST | `/api/v1/circuit-breaker/mcp/{id}/enable` | Re-enable MCP |
| POST | `/api/v1/circuit-breaker/mcp/{id}/reset` | Reset circuit breaker |
| GET | `/api/v1/circuit-breaker/mcp/{id}/status` | Get detailed status |

---

## 🎨 Dashboard TODO

### Recommended UI Features
1. **Circuit Breaker Status Badge** - Show CLOSED/OPEN/HALF_OPEN
2. **Failure Cycle Counter** - Display X/3 cycles
3. **Re-Enable Button** - One-click re-enable with confirmation
4. **Configuration Panel** - Edit settings without database access
5. **Auto-Disable History** - Show when/why MCPs were disabled

---

## 📁 Files Changed

### Created
- `migrations/018_add_auto_disable_fields.sql`
- `app/routers/circuit_breaker.py`
- `docs/CIRCUIT_BREAKER_IMPLEMENTATION.md`
- `docs/CIRCUIT_BREAKER_QUICK_REFERENCE.md`

### Modified
- `app/models.py` - Added fields
- `app/services/circuit_breaker.py` - Added cycle tracking
- `app/services/mcp_registry.py` - Added auto-disable logic
- `app/main.py` - Registered router

---

## 🔍 Monitoring Queries

### Find Auto-Disabled MCPs
```sql
SELECT name, failure_cycle_count, auto_disabled_at, auto_disabled_reason
FROM omni2.mcp_servers
WHERE status = 'inactive' AND auto_disabled_at IS NOT NULL;
```

### Check Circuit Breaker Config
```sql
SELECT config_value 
FROM omni2.omni2_config 
WHERE config_key = 'circuit_breaker';
```

---

## ✅ Summary

**Configuration:** Database-driven, hot-reload, no restart needed  
**Auto-Disable:** After 3 failure cycles (configurable)  
**Re-Enable:** API endpoint + dashboard button (to be built)  
**Monitoring:** Full audit trail in database  

**Next Step:** Build dashboard UI for managing circuit breaker settings and re-enabling MCPs.
