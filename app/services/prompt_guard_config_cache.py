"""
Prompt Guard Config Cache - Listens to Redis for config updates
"""

import asyncio
import json
from typing import Optional, Dict, Any
from app.utils.logger import logger

_config_cache: Optional[Dict[str, Any]] = None
_listener_task: Optional[asyncio.Task] = None

async def start_config_listener(redis_client):
    """Start listening to Redis for config updates"""
    global _listener_task
    _listener_task = asyncio.create_task(_listen_to_config_updates(redis_client))
    logger.info("[PROMPT-GUARD-CACHE] Started config listener")

async def _listen_to_config_updates(redis_client):
    """Background task to listen for config updates"""
    global _config_cache
    
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("prompt_guard_config_reload")
    
    logger.info("[PROMPT-GUARD-CACHE] Subscribed to prompt_guard_config_reload")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    _config_cache = data.get("config")
                    logger.info(f"[PROMPT-GUARD-CACHE] Config updated from Redis: {_config_cache}")
                except Exception as e:
                    logger.error(f"[PROMPT-GUARD-CACHE] Failed to parse config: {e}")
    except asyncio.CancelledError:
        logger.info("[PROMPT-GUARD-CACHE] Listener cancelled")
        await pubsub.unsubscribe("prompt_guard_config_reload")
        await pubsub.close()

def get_cached_config() -> Optional[Dict[str, Any]]:
    """Get cached config (returns None if not loaded)"""
    return _config_cache

async def stop_config_listener():
    """Stop the config listener"""
    global _listener_task
    if _listener_task:
        _listener_task.cancel()
        try:
            await _listener_task
        except asyncio.CancelledError:
            pass
        _listener_task = None
        logger.info("[PROMPT-GUARD-CACHE] Stopped config listener")
