# Dashboard Flow Tracking Implementation Guide

## Overview
Dashboard needs to display user interaction flows in real-time and historically.

---

## Backend: Redis Listener (Python/FastAPI)

### File: `dashboard/backend/app/services/flow_listener.py`

```python
import asyncio
import json
import redis.asyncio as redis
from app.services.websocket_manager import websocket_manager

async def redis_flow_listener():
    """Background task that listens to Redis Pub/Sub and forwards to WebSocket"""
    redis_client = redis.from_url("redis://omni2-redis:6379", decode_responses=True)
    pubsub = redis_client.pubsub()
    
    # Subscribe to all flow events
    await pubsub.psubscribe("flow_events:*")
    
    print("[FLOW] Redis listener started")
    
    async for message in pubsub.listen():
        if message["type"] == "pmessage":
            try:
                # Extract user_id from channel name
                channel = message["channel"]  # "flow_events:123"
                user_id = int(channel.split(":")[-1])
                
                # Parse event data
                data = json.loads(message["data"])
                
                # Broadcast to WebSocket clients
                await websocket_manager.broadcast({
                    "type": "flow_event",
                    "user_id": user_id,
                    **data
                })
                
            except Exception as e:
                print(f"[FLOW] Error processing message: {e}")
```

### Start listener in `dashboard/backend/app/main.py`:

```python
@app.on_event("startup")
async def startup():
    # ... existing code ...
    
    # Start flow listener
    from app.services.flow_listener import redis_flow_listener
    asyncio.create_task(redis_flow_listener())
```

---

## Frontend: Flow Viewer Component

### File: `dashboard/frontend/src/components/FlowViewer.tsx`

```tsx
'use client';

import { useEffect, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';

interface FlowEvent {
  session_id: string;
  node_id: string;
  event_type: string;
  parent_id?: string;
  timestamp: string;
  [key: string]: any;
}

export default function FlowViewer() {
  const [userId, setUserId] = useState('');
  const [monitoring, setMonitoring] = useState(false);
  const [events, setEvents] = useState<FlowEvent[]>([]);
  const [historicalFlows, setHistoricalFlows] = useState([]);
  const [mode, setMode] = useState<'realtime' | 'historical'>('realtime');
  const { lastMessage } = useWebSocket();

  // Real-time mode: Listen to WebSocket
  useEffect(() => {
    if (lastMessage && mode === 'realtime') {
      const data = JSON.parse(lastMessage.data);
      if (data.type === 'flow_event' && data.user_id === parseInt(userId)) {
        setEvents(prev => [...prev, data]);
      }
    }
  }, [lastMessage, userId, mode]);

  // Start monitoring
  const startMonitoring = async () => {
    const response = await fetch(`http://localhost:8000/api/v1/monitoring/enable/${userId}`, {
      method: 'POST'
    });
    if (response.ok) {
      setMonitoring(true);
      setEvents([]);
    }
  };

  // Stop monitoring
  const stopMonitoring = async () => {
    await fetch(`http://localhost:8000/api/v1/monitoring/disable/${userId}`, {
      method: 'POST'
    });
    setMonitoring(false);
  };

  // Load historical flows
  const loadHistorical = async () => {
    const response = await fetch(`http://localhost:8000/api/v1/monitoring/flows/${userId}`);
    const data = await response.json();
    setHistoricalFlows(data.flows);
  };

  return (
    <div className="p-4">
      {/* Mode Toggle */}
      <div className="mb-4 flex gap-2">
        <button
          onClick={() => setMode('realtime')}
          className={`px-4 py-2 ${mode === 'realtime' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
        >
          Real-Time
        </button>
        <button
          onClick={() => setMode('historical')}
          className={`px-4 py-2 ${mode === 'historical' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
        >
          Historical
        </button>
      </div>

      {/* User Input */}
      <div className="mb-4 flex gap-2">
        <input
          type="number"
          placeholder="User ID"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          className="border p-2"
        />
        
        {mode === 'realtime' ? (
          !monitoring ? (
            <button onClick={startMonitoring} className="bg-green-500 text-white px-4 py-2">
              Start Monitoring
            </button>
          ) : (
            <button onClick={stopMonitoring} className="bg-red-500 text-white px-4 py-2">
              Stop Monitoring
            </button>
          )
        ) : (
          <button onClick={loadHistorical} className="bg-blue-500 text-white px-4 py-2">
            Load History
          </button>
        )}
      </div>

      {/* Real-Time Events */}
      {mode === 'realtime' && monitoring && (
        <div className="space-y-2">
          <h3 className="font-bold">Live Events:</h3>
          {events.map((event, i) => (
            <div key={i} className="border p-3 rounded bg-gray-50">
              <div className="font-bold text-blue-600">{event.event_type}</div>
              <div className="text-xs text-gray-500">
                Node: {event.node_id} | Parent: {event.parent_id || 'root'}
              </div>
              <div className="text-xs text-gray-400">{event.timestamp}</div>
            </div>
          ))}
        </div>
      )}

      {/* Historical Flows */}
      {mode === 'historical' && (
        <div className="space-y-4">
          <h3 className="font-bold">Historical Flows:</h3>
          {historicalFlows.map((flow: any, i) => (
            <div key={i} className="border p-4 rounded">
              <div className="font-bold">Session: {flow.session_id}</div>
              <div className="text-sm text-gray-600">
                {flow.created_at} → {flow.completed_at}
              </div>
              <div className="text-sm">
                Events: {flow.flow_data.events?.length || 0}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

### Add to Live Updates page: `dashboard/frontend/src/app/live-updates/page.tsx`

```tsx
import FlowViewer from '@/components/FlowViewer';

const tabs = [
  { id: 'events', label: 'System Events' },
  { id: 'flows', label: 'User Flows' },  // ← Add this
];

// In render:
{activeTab === 'flows' && <FlowViewer />}
```

---

## Testing Steps

1. **Start Redis**: `docker-compose up -d redis`
2. **Run migration**: `psql -h localhost -p 5435 -U omni -d omni -f migrations/phase2_flow_tracking.sql`
3. **Start OMNI2**: `python -m uvicorn app.main:app --reload`
4. **Start Dashboard Backend**: `cd dashboard/backend && uvicorn app.main:app --reload --port 8001`
5. **Start Dashboard Frontend**: `cd dashboard/frontend && npm run dev`
6. **Test**:
   - Open dashboard → Live Updates → User Flows
   - Enter user ID (e.g., 1)
   - Click "Start Monitoring"
   - Send chat message from that user
   - Watch events appear in real-time
   - Switch to "Historical" mode
   - Click "Load History"
   - See completed flows

---

## Summary

**OMNI2 (Done):**
- ✅ Logs to Redis Streams
- ✅ Publishes to Redis Pub/Sub (if monitored)
- ✅ Saves to PostgreSQL on completion

**Dashboard Backend (TODO):**
- ⏳ Redis listener subscribes to `flow_events:*`
- ⏳ Forwards to WebSocket

**Dashboard Frontend (TODO):**
- ⏳ FlowViewer component
- ⏳ Real-time mode (WebSocket)
- ⏳ Historical mode (API)

---

**Implementation time: ~1 hour**
