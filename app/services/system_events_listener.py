"""
System Events Listener - Redis Pub/Sub for Dashboard Notifications

Listens to system_events channel and forwards to WebSocket clients.
"""

import asyncio
import json
from typing import Optional
from app.utils.logger import logger

logger = logger.bind(service="SystemEventsListener")

_listener_task: Optional[asyncio.Task] = None
_running = False


async def system_events_listener(redis_client, broadcaster):
    """Listen to system_events Redis channel and forward to WebSocket clients."""
    global _running
    
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("system_events")
    
    logger.info("System events listener started")
    
    try:
        while _running:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            
            if message and message["type"] == "message":
                try:
                    event_data = json.loads(message["data"])
                    event_type = event_data.get("type")
                    data = event_data.get("data", {})
                    
                    # Forward to WebSocket broadcaster
                    await broadcaster.broadcast_event(event_type, data)
                    
                    logger.info(
                        "System event forwarded",
                        event_type=event_type,
                        user_id=data.get("user_id")
                    )
                    
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse system event", error=str(e))
                except Exception as e:
                    logger.error("Error processing system event", error=str(e))
                    
    except asyncio.CancelledError:
        logger.info("System events listener cancelled")
    except Exception as e:
        logger.error("System events listener error", error=str(e))
    finally:
        await pubsub.unsubscribe("system_events")
        await pubsub.close()
        logger.info("System events listener stopped")


async def start_system_events_listener(redis_client):
    """Start the system events listener."""
    global _listener_task, _running
    
    if _listener_task is not None:
        return
    
    _running = True
    
    from app.services.websocket_broadcaster import get_websocket_broadcaster
    broadcaster = get_websocket_broadcaster()
    
    _listener_task = asyncio.create_task(
        system_events_listener(redis_client, broadcaster)
    )
    
    logger.info("System events listener task created")


async def stop_system_events_listener():
    """Stop the system events listener."""
    global _listener_task, _running
    
    _running = False
    
    if _listener_task:
        _listener_task.cancel()
        try:
            await _listener_task
        except asyncio.CancelledError:
            pass
        _listener_task = None
    
    logger.info("System events listener stopped")
