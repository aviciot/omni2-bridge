import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket
import structlog

logger = structlog.get_logger()

class FlowListener:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.listener_task = None
        
    async def start(self):
        """Start Redis listener in background"""
        if self.listener_task is None:
            self.listener_task = asyncio.create_task(self._listen_redis())
            logger.info("flow_listener_started")
    
    async def stop(self):
        """Stop Redis listener"""
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
            logger.info("flow_listener_stopped")
    
    async def _listen_redis(self):
        """Subscribe to Redis Pub/Sub and forward to WebSockets"""
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe("flow_events:*")
        
        logger.info("[FLOW-LISTENER] ✓ Subscribed to flow_events:* pattern")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    user_id = channel.split(":")[-1]
                    data = json.loads(message["data"])
                    
                    logger.info(f"[FLOW-LISTENER] ← Received: {data.get('event_type')} for user {user_id}")
                    await self._broadcast_to_user(user_id, data)
        except asyncio.CancelledError:
            logger.info("[FLOW-LISTENER] ⚠ Listener cancelled, cleaning up...")
            await pubsub.unsubscribe()
            await pubsub.close()
            raise
    
    async def connect(self, user_id: str, websocket: WebSocket):
        """Register WebSocket connection for user"""
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"[FLOW-LISTENER] ✓ WS connected: user={user_id}, total={len(self.active_connections[user_id])}")
    
    async def disconnect(self, user_id: str, websocket: WebSocket):
        """Unregister WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"[FLOW-LISTENER] ✗ WS disconnected: user={user_id}")
    
    async def _broadcast_to_user(self, user_id: str, data: dict):
        """Send flow event to all WebSocket connections for user"""
        if user_id not in self.active_connections:
            logger.debug(f"[FLOW-LISTENER] No active WS for user {user_id}")
            return
        
        dead_connections = set()
        sent_count = 0
        for ws in self.active_connections[user_id]:
            try:
                await ws.send_json(data)
                sent_count += 1
            except Exception as e:
                logger.error(f"[FLOW-LISTENER] ✗ WS send failed: user={user_id}, error={str(e)}")
                dead_connections.add(ws)
        
        logger.info(f"[FLOW-LISTENER] → Broadcast: {data.get('event_type')} to {sent_count} WS")
        
        # Clean up dead connections
        for ws in dead_connections:
            self.active_connections[user_id].discard(ws)

# Global instance
flow_listener: FlowListener = None

def get_flow_listener() -> FlowListener:
    return flow_listener

async def init_flow_listener(redis_client):
    global flow_listener
    flow_listener = FlowListener(redis_client)
    await flow_listener.start()
    logger.info("[FLOW-LISTENER] ✓ Flow listener initialized and started")

async def shutdown_flow_listener():
    global flow_listener
    if flow_listener:
        await flow_listener.stop()
        logger.info("[FLOW-LISTENER] ✓ Flow listener stopped")
