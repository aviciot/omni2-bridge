"""
Redis Handler - Communication with omni2 via pub/sub

Listens for check requests and publishes results.
"""

import redis.asyncio as redis
import json
import asyncio
from typing import Dict, Any

from config import settings
from logger import logger
from guard import PromptGuardService
from db import record_detection, get_user_violation_count


class RedisHandler:
    """Handles Redis pub/sub communication with reconnection."""
    
    def __init__(self, guard_service: PromptGuardService):
        self.guard_service = guard_service
        self.redis_client: redis.Redis = None
        self.pubsub = None
        self._shutdown = False
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 5
    
    async def connect(self):
        """Connect to Redis with retry logic."""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=10,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            self._connected = True
            self._reconnect_attempts = 0
            logger.info(f"Redis connection established at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            
            # Subscribe to channels
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe("prompt_guard_check", "prompt_guard_config_reload")
            logger.info("Subscribed to Redis channels")
            
        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def _reconnect(self) -> bool:
        """Attempt to reconnect to Redis."""
        while self._reconnect_attempts < self._max_reconnect_attempts and not self._shutdown:
            try:
                logger.info(f"Attempting to reconnect to Redis (attempt {self._reconnect_attempts + 1}/{self._max_reconnect_attempts})")
                
                # Close existing connections
                await self._close_connections()
                
                # Wait before reconnecting
                await asyncio.sleep(self._reconnect_delay)
                
                # Reconnect
                await self.connect()
                
                logger.info("Successfully reconnected to Redis")
                return True
                
            except Exception as e:
                self._reconnect_attempts += 1
                logger.error(f"Reconnection attempt {self._reconnect_attempts} failed: {e}")
                
                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    logger.error("Max reconnection attempts reached. Giving up.")
                    return False
        
        return False
    
    async def _close_connections(self):
        """Close existing connections."""
        try:
            if self.pubsub:
                await self.pubsub.unsubscribe()
                await self.pubsub.close()
                self.pubsub = None
        except:
            pass
        
        try:
            if self.redis_client:
                await self.redis_client.close()
                self.redis_client = None
        except:
            pass
        
        self._connected = False
    
    async def close(self):
        """Close Redis connection."""
        self._shutdown = True
        await self._close_connections()
        logger.info("Redis connection closed")
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected and self.redis_client is not None
    
    async def _health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            if not self.redis_client:
                return False
            await self.redis_client.ping()
            return True
        except Exception:
            self._connected = False
            return False
    
    async def listen_for_requests(self):
        """Listen for prompt check requests with reconnection."""
        logger.info("🎧 Starting Redis listener with reconnection support...")
        
        while not self._shutdown:
            try:
                # Ensure we're connected
                if not self._connected:
                    if not await self._reconnect():
                        logger.error("Failed to reconnect. Exiting listener.")
                        break
                
                # Ensure pubsub is setup
                if not self.pubsub:
                    self.pubsub = self.redis_client.pubsub()
                    await self.pubsub.subscribe("prompt_guard_check", "prompt_guard_config_reload")
                    logger.info("Re-subscribed to Redis channels")
                
                logger.info("🎧 Listening for prompt guard requests...")
                
                async for message in self.pubsub.listen():
                    if self._shutdown:
                        break
                    
                    if message["type"] != "message":
                        continue
                    
                    channel = message["channel"]
                    
                    try:
                        data = json.loads(message["data"])
                        
                        if channel == "prompt_guard_check":
                            await self._handle_check_request(data)
                        
                        elif channel == "prompt_guard_config_reload":
                            await self._handle_config_reload(data)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in message: {e}")
                    except Exception as e:
                        logger.error(f"Error handling message: {e}", exc_info=True)
            
            except redis.ConnectionError as e:
                logger.error(f"Redis connection lost: {e}")
                self._connected = False
                continue
                
            except Exception as e:
                logger.error(f"Error in listener: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying
                continue
    
    async def _publish_with_retry(self, channel: str, data: str, max_retries: int = 3) -> bool:
        """Publish message with retry logic."""
        for attempt in range(max_retries):
            try:
                if not self._connected:
                    if not await self._reconnect():
                        return False
                
                await self.redis_client.publish(channel, data)
                return True
                
            except redis.ConnectionError as e:
                logger.error(f"Connection error publishing to {channel} (attempt {attempt + 1}): {e}")
                self._connected = False
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                
            except Exception as e:
                logger.error(f"Failed to publish to {channel} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
        
        return False
    
    async def _handle_check_request(self, data: Dict[str, Any]):
        """Handle prompt check request - only detection, no action decision."""
        request_id = data.get("request_id")
        user_id = data.get("user_id")
        message_text = data.get("message")
        
        if not request_id or not message_text:
            logger.warning("Invalid check request", data=data)
            return
        
        logger.debug("Processing check request", request_id=request_id, user_id=user_id)
        
        # Check prompt - only return detection result
        result = await self.guard_service.check_prompt(message_text, user_id)
        
        # Publish result with retry (omni2 will decide action)
        response = {
            "request_id": request_id,
            "user_id": user_id,
            "result": result,
        }
        
        success = await self._publish_with_retry(
            "prompt_guard_response",
            json.dumps(response)
        )
        
        if success:
            logger.info(
                "Check completed",
                request_id=request_id,
                user_id=user_id,
                safe=result["safe"],
                score=result.get("score", 0),
                latency_ms=result.get("latency_ms", 0),
            )
        else:
            logger.error(f"Failed to publish response for request {request_id}")
    
    async def _handle_config_reload(self, data: Dict[str, Any]):
        """Handle configuration reload request."""
        logger.info("Reloading configuration", data=data)
        
        from db import load_config_from_db
        new_config = await load_config_from_db()
        self.guard_service.reload_config(new_config)
        
        logger.info("Configuration reloaded successfully")
