"""
MCP Gateway Session Cache
==========================
Caches user permissions per session for HTTP Streamable connections.

HTTP Streamable maintains sessions, so we can cache:
- User context (mcp_access, tool_restrictions)
- Available MCPs list
- Filtered tools list

This avoids repeated DB queries for the same user session.
"""

from typing import Dict, Optional
import time
import asyncio
import json
from dataclasses import dataclass
from redis.asyncio import Redis
from app.utils.logger import logger


@dataclass
class SessionCache:
    """Cached session data"""
    user_id: int
    user_context: dict
    available_mcps: list
    filtered_tools: list
    created_at: float
    last_accessed: float
    flow_session_id: str = None  # Stable ID for grouping all tool calls from this token


class MCPGatewaySessionCache:
    """Session cache for MCP Gateway"""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default
        self.cache: Dict[str, SessionCache] = {}
        self.ttl_seconds = ttl_seconds
        self.redis: Optional[Redis] = None
        self.listener_task = None
        self._shutdown = False
    
    def get(self, token: str) -> Optional[SessionCache]:
        """Get cached session data"""
        if token not in self.cache:
            return None
        
        session = self.cache[token]
        
        # Check if expired
        if time.time() - session.created_at > self.ttl_seconds:
            del self.cache[token]
            return None
        
        # Update last accessed
        session.last_accessed = time.time()
        return session
    
    def set(self, token: str, user_id: int, user_context: dict, 
            available_mcps: list, filtered_tools: list):
        """Cache session data"""
        from uuid import uuid4
        self.cache[token] = SessionCache(
            user_id=user_id,
            user_context=user_context,
            available_mcps=available_mcps,
            filtered_tools=filtered_tools,
            created_at=time.time(),
            last_accessed=time.time(),
            flow_session_id=str(uuid4())
        )
    
    def invalidate(self, token: str):
        """Invalidate cached session"""
        if token in self.cache:
            del self.cache[token]
    
    def cleanup_expired(self):
        """Remove expired sessions"""
        now = time.time()
        expired = [
            token for token, session in self.cache.items()
            if now - session.created_at > self.ttl_seconds
        ]
        for token in expired:
            del self.cache[token]
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        return {
            "total_sessions": len(self.cache),
            "ttl_seconds": self.ttl_seconds
        }
    
    def invalidate_user(self, user_id: int):
        """Invalidate all sessions for a user"""
        tokens_to_remove = [
            token for token, session in self.cache.items()
            if session.user_id == user_id
        ]
        for token in tokens_to_remove:
            del self.cache[token]
        if tokens_to_remove:
            logger.info(f"[MCP-CACHE] Invalidated {len(tokens_to_remove)} sessions for user {user_id}")
    
    async def start_listener(self, redis: Redis):
        """Start Redis listener for user_blocked events"""
        self.redis = redis
        self.listener_task = asyncio.create_task(self._listen_for_block_events())
        logger.info("[MCP-CACHE] Started Redis listener for user_blocked events")
    
    async def stop_listener(self):
        """Stop Redis listener"""
        if self.listener_task:
            self._shutdown = True
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
            logger.info("[MCP-CACHE] Stopped Redis listener")
    
    async def _listen_for_block_events(self):
        """Listen for user_blocked events and invalidate cache"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe("user_blocked")
        logger.info("[MCP-CACHE] Listening for user_blocked events")
        
        try:
            async for message in pubsub.listen():
                if self._shutdown:
                    break
                
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        user_id = data.get("user_id")
                        blocked_services = data.get("blocked_services", [])
                        
                        # Only invalidate if 'mcp' is in blocked_services
                        if "mcp" in blocked_services:
                            logger.warning(f"[MCP-CACHE] Block event for user {user_id} (mcp blocked)")
                            self.invalidate_user(user_id)
                        else:
                            logger.info(f"[MCP-CACHE] Block event for user {user_id} (mcp not blocked, ignoring)")
                    except:
                        pass
        except asyncio.CancelledError:
            await pubsub.unsubscribe()
            await pubsub.close()
            raise
        except:
            await pubsub.unsubscribe()
            await pubsub.close()


# Global session cache instance (60 second TTL for token validation security)
_session_cache = MCPGatewaySessionCache(ttl_seconds=60)


def get_session_cache() -> MCPGatewaySessionCache:
    """Get global session cache instance"""
    return _session_cache
