"""
Prompt Guard Client for omni2

Communicates with prompt-guard-service via Redis pub/sub.
Provides async interface for checking prompts.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from redis.asyncio import Redis

from app.utils.logger import logger


class PromptGuardClient:
    """Client for prompt guard service via Redis pub/sub."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.pubsub = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._listener_task: Optional[asyncio.Task] = None
        self._enabled = True
    
    async def start(self):
        """Start listening for responses."""
        if self._listener_task:
            logger.warning("[PROMPT-GUARD] Listener already running")
            return
        
        try:
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe("prompt_guard_response")
            self._listener_task = asyncio.create_task(self._listen_for_responses())
            logger.info("[PROMPT-GUARD] ✅ Client started")
        except Exception as e:
            logger.error(f"[PROMPT-GUARD] Failed to start: {e}")
            self._enabled = False
    
    async def stop(self):
        """Stop listening for responses."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        
        logger.info("[PROMPT-GUARD] ✅ Client stopped")
    
    async def check_prompt(
        self,
        message: str,
        user_id: int,
        timeout: float = 2.0
    ) -> Dict[str, Any]:
        """
        Check if message contains prompt injection.
        
        Args:
            message: User message to check
            user_id: User ID
            timeout: Max wait time in seconds
        
        Returns:
            {
                "safe": bool,
                "score": float,
                "action": str,  # "allow", "warn", "filter", "block"
                "reason": str,
                "cached": bool,
                "latency_ms": int,
            }
        """
        if not self._enabled:
            # Fail open - allow if guard is disabled
            return {
                "safe": True,
                "score": 0.0,
                "action": "allow",
                "reason": "Guard disabled",
                "cached": False,
                "latency_ms": 0,
            }
        
        request_id = str(uuid.uuid4())
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        try:
            # Publish check request
            request = {
                "request_id": request_id,
                "user_id": user_id,
                "message": message,
            }
            
            await self.redis.publish(
                "prompt_guard_check",
                json.dumps(request),
            )
            
            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
            
        except asyncio.TimeoutError:
            logger.warning(
                "[PROMPT-GUARD] Check timeout",
                request_id=request_id,
                user_id=user_id,
            )
            # Fail open on timeout
            return {
                "safe": True,
                "score": 0.0,
                "action": "allow",
                "reason": "Timeout",
                "cached": False,
                "latency_ms": int(timeout * 1000),
            }
        except Exception as e:
            logger.error(f"[PROMPT-GUARD] Check error: {e}")
            # Fail open on error
            return {
                "safe": True,
                "score": 0.0,
                "action": "allow",
                "reason": f"Error: {str(e)}",
                "cached": False,
                "latency_ms": 0,
            }
        finally:
            # Cleanup
            self._pending_requests.pop(request_id, None)
    
    async def _listen_for_responses(self):
        """Background task listening for responses."""
        logger.info("[PROMPT-GUARD] 🎧 Listening for responses...")
        
        try:
            async for message in self.pubsub.listen():
                if message["type"] != "message":
                    continue
                
                try:
                    data = json.loads(message["data"])
                    request_id = data.get("request_id")
                    result = data.get("result")
                    
                    if request_id in self._pending_requests:
                        future = self._pending_requests[request_id]
                        if not future.done():
                            future.set_result(result)
                
                except json.JSONDecodeError as e:
                    logger.error(f"[PROMPT-GUARD] Invalid JSON: {e}")
                except Exception as e:
                    logger.error(f"[PROMPT-GUARD] Error handling response: {e}")
        
        except asyncio.CancelledError:
            logger.info("[PROMPT-GUARD] Listener cancelled")
            raise
        except Exception as e:
            logger.error(f"[PROMPT-GUARD] Fatal listener error: {e}", exc_info=True)
    
    async def reload_config(self):
        """Trigger configuration reload in guard service."""
        try:
            await self.redis.publish(
                "prompt_guard_config_reload",
                json.dumps({"timestamp": asyncio.get_event_loop().time()}),
            )
            logger.info("[PROMPT-GUARD] Config reload triggered")
        except Exception as e:
            logger.error(f"[PROMPT-GUARD] Failed to trigger reload: {e}")


# Global instance
_prompt_guard_client: Optional[PromptGuardClient] = None


async def init_prompt_guard_client(redis_client: Redis):
    """Initialize prompt guard client."""
    global _prompt_guard_client
    _prompt_guard_client = PromptGuardClient(redis_client)
    await _prompt_guard_client.start()
    logger.info("[PROMPT-GUARD] ✅ Client initialized")


async def shutdown_prompt_guard_client():
    """Shutdown prompt guard client."""
    global _prompt_guard_client
    if _prompt_guard_client:
        await _prompt_guard_client.stop()
        _prompt_guard_client = None


def get_prompt_guard_client() -> Optional[PromptGuardClient]:
    """Get prompt guard client instance."""
    return _prompt_guard_client
