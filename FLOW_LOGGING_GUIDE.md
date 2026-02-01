# Flow Tracking System - Logging Guide

## Log Prefixes & Symbols

### OMNI2 Backend
- `[REDIS]` - Redis connection and operations
- `[FLOW]` - FlowTracker service operations
- `[MONITORING]` - Monitoring control API operations

### Dashboard Backend
- `[DASHBOARD]` - Main application lifecycle
- `[FLOW-LISTENER]` - Redis Pub/Sub listener operations
- `[FLOW-WS]` - WebSocket connection management
- `[FLOW-API]` - Flow API endpoint operations

### Visual Indicators
- `✓` / `✅` - Success
- `✗` / `❌` - Error
- `⚠` - Warning
- `→` - Outgoing action
- `←` - Incoming action
- `⚡` - Pub/Sub publish
- `ℹ` - Information

---

## Expected Log Flow

### 1. System Startup

**OMNI2:**
```
[REDIS] Connecting to omni2-redis:6379...
[REDIS] ✅ Redis connection successful
```

**Dashboard:**
```
[DASHBOARD] 🚀 Starting Dashboard API
[DASHBOARD] ✓ Redis connected
[FLOW-LISTENER] ✓ Flow listener initialized and started
[FLOW-LISTENER] ✓ Subscribed to flow_events:* pattern
```

### 2. Enable Monitoring

**Request:**
```bash
POST /api/v1/monitoring/enable/123
```

**Log:**
```
[MONITORING] ✓ Enabled for user 123 until 2025-01-28T10:00:00 (TTL: 24h)
```

### 3. User Makes Request (Monitored)

**OMNI2 Logs:**
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
[FLOW] → Redis Stream: tool_call (node: q7r8s9t0...)
[FLOW] ⚡ Published to Pub/Sub: tool_call → flow_events:123
[FLOW] → Redis Stream: llm_complete (node: u1v2w3x4...)
[FLOW] ⚡ Published to Pub/Sub: llm_complete → flow_events:123
```

**Dashboard Logs:**
```
[FLOW-LISTENER] ← Received: auth_check for user 123
[FLOW-LISTENER] → Broadcast: auth_check to 1 WS
[FLOW-LISTENER] ← Received: block_check for user 123
[FLOW-LISTENER] → Broadcast: block_check to 1 WS
[FLOW-LISTENER] ← Received: usage_check for user 123
[FLOW-LISTENER] → Broadcast: usage_check to 1 WS
[FLOW-LISTENER] ← Received: llm_thinking for user 123
[FLOW-LISTENER] → Broadcast: llm_thinking to 1 WS
[FLOW-LISTENER] ← Received: tool_call for user 123
[FLOW-LISTENER] → Broadcast: tool_call to 1 WS
[FLOW-LISTENER] ← Received: llm_complete for user 123
[FLOW-LISTENER] → Broadcast: llm_complete to 1 WS
```

### 4. User Makes Request (Not Monitored)

**OMNI2 Logs:**
```
[FLOW] User 456 not monitored
[FLOW] → Redis Stream: auth_check (node: y5z6a7b8...)
[FLOW] → Redis Stream: block_check (node: c9d0e1f2...)
[FLOW] → Redis Stream: usage_check (node: g3h4i5j6...)
[FLOW] → Redis Stream: llm_thinking (node: k7l8m9n0...)
[FLOW] → Redis Stream: llm_complete (node: o1p2q3r4...)
```

**Dashboard Logs:**
```
(No logs - not published to Pub/Sub)
```

### 5. WebSocket Connection

**Dashboard Logs:**
```
[FLOW-WS] ✓ WebSocket accepted for user 123
[FLOW-LISTENER] ✓ WS connected: user=123, total=1
```

### 6. WebSocket Disconnection

**Dashboard Logs:**
```
[FLOW-WS] ✗ WebSocket disconnected for user 123
[FLOW-LISTENER] ✗ WS disconnected: user=123
```

### 7. Save Flow to Database

**OMNI2 Logs:**
```
[FLOW] ✓ Saved session abc-123-def to DB (6 events)
```

### 8. Query Historical Flows

**Request:**
```bash
GET /api/v1/monitoring/flows/123
```

**Log:**
```
[MONITORING] ℹ Retrieved 15 flows for user 123
```

### 9. List Monitored Users

**Request:**
```bash
GET /api/v1/monitoring/list
```

**Log:**
```
[MONITORING] ℹ Listed 3 active monitored users
```

### 10. Disable Monitoring

**Request:**
```bash
POST /api/v1/monitoring/disable/123
```

**Log:**
```
[MONITORING] ✗ Disabled for user 123
```

---

## Troubleshooting

### No Pub/Sub Messages
**Check:**
1. Is user monitored? Look for: `[FLOW] ✓ User X is monitored`
2. Is Redis connected? Look for: `[REDIS] ✅ Redis connection successful`
3. Is listener running? Look for: `[FLOW-LISTENER] ✓ Subscribed to flow_events:*`

### WebSocket Not Receiving
**Check:**
1. Is WebSocket connected? Look for: `[FLOW-WS] ✓ WebSocket accepted`
2. Is listener broadcasting? Look for: `[FLOW-LISTENER] → Broadcast: X to Y WS`
3. Check for errors: `[FLOW-LISTENER] ✗ WS send failed`

### Events Not Logged
**Check:**
1. Is Redis enabled? Look for: `[REDIS] ✅ Redis connection successful`
2. Check for errors: `[FLOW] ✗ Failed to check monitoring status`

### Database Save Failed
**Check:**
1. Look for: `[FLOW] ✗ Failed to save session`
2. Check database connection
3. Verify table exists: `omni2.interaction_flows`

---

## Performance Monitoring

### Expected Timings
- Redis Stream write: ~2-3ms
- Monitoring check: ~1-2ms (cached)
- Pub/Sub publish: ~1-2ms
- Total overhead (monitored): ~5-7ms
- Total overhead (not monitored): ~3-4ms

### Log Volume
- **Monitored user**: 6-10 log lines per request
- **Non-monitored user**: 6 log lines per request (no Pub/Sub)
- **Dashboard**: 6-12 log lines per monitored request

---

## Quick Commands

### View OMNI2 Logs
```bash
docker logs -f omni2-bridge | grep FLOW
```

### View Dashboard Logs
```bash
docker logs -f omni2-dashboard-backend | grep FLOW
```

### View All Flow Logs
```bash
docker logs -f omni2-bridge | grep -E "\[FLOW\]|\[MONITORING\]|\[REDIS\]"
docker logs -f omni2-dashboard-backend | grep -E "\[FLOW-"
```

### Filter by User
```bash
docker logs -f omni2-bridge | grep "user 123"
```

### Filter by Session
```bash
docker logs -f omni2-bridge | grep "session abc-123"
```
