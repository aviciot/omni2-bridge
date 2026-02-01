# Flow Tracking - Quick Test Guide

## 🚀 Quick Start

```bash
# 1. Setup (run once)
cd omni2
setup_flow_tracking.bat

# 2. Run tests
python test_flow_tracking.py

# 3. Monitor logs
docker logs -f omni2-bridge | findstr FLOW
```

## 📋 Manual Testing Steps

### 1. Enable Monitoring
```bash
curl -X POST "http://localhost:8090/api/v1/monitoring/enable/123?ttl_hours=1"
```

**Expected Log:**
```
[MONITORING] ✓ Enabled for user 123 until 2025-01-28T10:00:00 (TTL: 1h)
```

### 2. List Monitored Users
```bash
curl "http://localhost:8090/api/v1/monitoring/list"
```

**Expected Response:**
```json
{
  "monitored_users": [
    {"user_id": 123, "expires_at": "2025-01-28T10:00:00"}
  ]
}
```

### 3. Make Chat Request (with auth)
```bash
curl -X POST "http://localhost:8090/api/v1/ask/stream" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

**Expected Logs (OMNI2):**
```
[FLOW] ✓ User 123 is monitored (expires: 2025-01-28T10:00:00)
[FLOW] → Redis Stream: auth_check (node: a1b2c3d4...)
[FLOW] ⚡ Published to Pub/Sub: auth_check → flow_events:123
[FLOW] → Redis Stream: block_check (node: e5f6g7h8...)
[FLOW] ⚡ Published to Pub/Sub: block_check → flow_events:123
[FLOW] → Redis Stream: usage_check (node: i9j0k1l2...)
[FLOW] ⚡ Published to Pub/Sub: usage_check → flow_events:123
[FLOW] → Redis Stream: llm_thinking (node: m3n4o5p6...)
[FLOW] ⚡ Published to Pub/Sub: llm_thinking → flow_events:123
[FLOW] → Redis Stream: llm_complete (node: u1v2w3x4...)
[FLOW] ⚡ Published to Pub/Sub: llm_complete → flow_events:123
```

**Expected Logs (Dashboard):**
```
[FLOW-LISTENER] ← Received: auth_check for user 123
[FLOW-LISTENER] → Broadcast: auth_check to 1 WS
[FLOW-LISTENER] ← Received: block_check for user 123
[FLOW-LISTENER] → Broadcast: block_check to 1 WS
...
```

### 4. Get Historical Flows
```bash
curl "http://localhost:8090/api/v1/monitoring/flows/123?limit=10"
```

**Expected Log:**
```
[MONITORING] ℹ Retrieved 5 flows for user 123
```

### 5. Disable Monitoring
```bash
curl -X POST "http://localhost:8090/api/v1/monitoring/disable/123"
```

**Expected Log:**
```
[MONITORING] ✗ Disabled for user 123
```

## 🔍 Verification Commands

### Check Redis
```bash
# Ping Redis
docker exec -it omni2-redis redis-cli ping

# Check streams
docker exec -it omni2-redis redis-cli KEYS "flow:*"

# View stream content
docker exec -it omni2-redis redis-cli XRANGE "flow:SESSION_ID" - +
```

### Check Database
```bash
# Connect to PostgreSQL
psql -h localhost -p 5435 -U omni -d omni

# Check monitoring config
SELECT config_value FROM omni2.omni2_config WHERE config_key = 'flow_monitoring';

# Check flows table
SELECT COUNT(*) FROM omni2.interaction_flows;

# View recent flows
SELECT session_id, user_id, created_at, completed_at 
FROM omni2.interaction_flows 
ORDER BY created_at DESC 
LIMIT 5;
```

### Check Logs
```bash
# OMNI2 - All flow logs
docker logs omni2-bridge 2>&1 | findstr /C:"[FLOW]" /C:"[MONITORING]" /C:"[REDIS]"

# OMNI2 - Only Pub/Sub publishes
docker logs omni2-bridge 2>&1 | findstr "Published to Pub/Sub"

# Dashboard - All flow logs
docker logs omni2-dashboard-backend 2>&1 | findstr /C:"[FLOW-"

# Dashboard - Only broadcasts
docker logs omni2-dashboard-backend 2>&1 | findstr "Broadcast:"
```

## 🐛 Troubleshooting

### No Pub/Sub Messages
```bash
# Check if user is monitored
curl "http://localhost:8090/api/v1/monitoring/list"

# Check Redis connection
docker logs omni2-bridge 2>&1 | findstr "[REDIS]"

# Check if listener is running
docker logs omni2-dashboard-backend 2>&1 | findstr "Subscribed to flow_events"
```

### WebSocket Not Receiving
```bash
# Check Dashboard logs
docker logs omni2-dashboard-backend 2>&1 | findstr "[FLOW-WS]"

# Check if listener is broadcasting
docker logs omni2-dashboard-backend 2>&1 | findstr "Broadcast:"
```

### Events Not Logged
```bash
# Check if Redis is enabled
docker exec omni2-bridge env | findstr REDIS_ENABLED

# Check OMNI2 startup logs
docker logs omni2-bridge 2>&1 | findstr "[REDIS]"
```

## 📊 Expected Performance

- **Redis Stream write**: ~2-3ms
- **Monitoring check**: ~1-2ms
- **Pub/Sub publish**: ~1-2ms
- **Total overhead (monitored)**: ~5-7ms
- **Total overhead (not monitored)**: ~3-4ms

## ✅ Success Criteria

1. ✓ Redis connects successfully
2. ✓ Monitoring can be enabled/disabled
3. ✓ Flow events logged to Redis Streams
4. ✓ Pub/Sub messages published (if monitored)
5. ✓ Dashboard listener receives messages
6. ✓ WebSocket broadcasts to clients
7. ✓ Flows saved to PostgreSQL
8. ✓ Historical flows retrievable

## 🎯 Next Steps After Testing

1. Integrate FlowTracker component into Live Updates page
2. Add monitoring controls to Dashboard UI
3. Create Analytics page for historical analysis
4. Add session detail view with tree visualization
