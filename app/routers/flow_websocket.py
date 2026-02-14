"""
Flow WebSocket Router - Real-time flow event streaming
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.database import redis_client
from app.utils.logger import logger
import json
import asyncio

router = APIRouter()

@router.websocket("/api/v1/ws/flows/{user_id}")
async def flow_websocket(websocket: WebSocket, user_id: int):
    """
    WebSocket endpoint for real-time flow event streaming.
    Subscribes to Redis pub/sub channel: flow_events:{user_id}
    """
    await websocket.accept()
    logger.info(f"[FLOW-WS] Client connected for user {user_id}")
    
    if not redis_client:
        await websocket.close(code=1011, reason="Redis not available")
        return
    
    # Subscribe to Redis pub/sub channel
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"flow_events:{user_id}")
    logger.info(f"[FLOW-WS] Subscribed to flow_events:{user_id}")
    
    async def redis_listener():
        """Listen for Redis pub/sub messages"""
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await websocket.send_json(data)
        except Exception as e:
            logger.error(f"[FLOW-WS] Redis listener error: {e}")
    
    # Start Redis listener task
    listener_task = asyncio.create_task(redis_listener())
    
    try:
        # Keep connection alive and handle client messages
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"[FLOW-WS] Client disconnected for user {user_id}")
    finally:
        listener_task.cancel()
        await pubsub.unsubscribe(f"flow_events:{user_id}")
        await pubsub.close()
        logger.info(f"[FLOW-WS] Cleaned up for user {user_id}")
