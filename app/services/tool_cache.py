"""
Tool Result Cache Service - Performance Optimization

Caches tool execution results to reduce redundant MCP calls and improve response times.
Uses in-memory cache with TTL and LRU eviction.
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, Optional, Any
from collections import OrderedDict

from app.utils.logger import logger

# Bind service name to logger for this module
logger = logger.bind(service="Cache")


class ToolCache:
    """In-memory cache for tool execution results."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize tool cache.
        
        Args:
            max_size: Maximum number of cached entries
            default_ttl: Default time-to-live in seconds (5 minutes)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "invalidations": 0
        }
        self.running = False
        self.cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the cache cleanup task."""
        if self.running:
            return
            
        self.running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("🚀 Tool Cache started", max_size=self.max_size, ttl=self.default_ttl)
        
    async def stop(self):
        """Stop the cache and cleanup task."""
        self.running = False
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
                
        self.cache.clear()
        logger.info("🛑 Tool Cache stopped")
        
    def _generate_cache_key(self, mcp_name: str, tool_name: str, arguments: Dict) -> str:
        """Generate cache key from MCP name, tool name, and arguments."""
        # Sort arguments for consistent hashing
        args_str = json.dumps(arguments, sort_keys=True)
        key_str = f"{mcp_name}:{tool_name}:{args_str}"
        return hashlib.sha256(key_str.encode()).hexdigest()
        
    async def get(self, mcp_name: str, tool_name: str, arguments: Dict) -> Optional[Any]:
        """
        Get cached tool result.
        
        Args:
            mcp_name: Name of the MCP server
            tool_name: Name of the tool
            arguments: Tool arguments
            
        Returns:
            Cached result or None if not found/expired
        """
        cache_key = self._generate_cache_key(mcp_name, tool_name, arguments)
        
        if cache_key not in self.cache:
            self.stats["misses"] += 1
            return None
            
        entry = self.cache[cache_key]
        
        # Check if expired
        if time.time() > entry["expires_at"]:
            del self.cache[cache_key]
            self.stats["misses"] += 1
            return None
            
        # Move to end (LRU)
        self.cache.move_to_end(cache_key)
        
        self.stats["hits"] += 1
        logger.debug("✅ Cache hit", mcp=mcp_name, tool=tool_name)
        
        return entry["result"]
        
    async def set(self, mcp_name: str, tool_name: str, arguments: Dict, result: Any, ttl: Optional[int] = None):
        """
        Cache tool result.
        
        Args:
            mcp_name: Name of the MCP server
            tool_name: Name of the tool
            arguments: Tool arguments
            result: Tool execution result
            ttl: Time-to-live in seconds (uses default if None)
        """
        cache_key = self._generate_cache_key(mcp_name, tool_name, arguments)
        ttl = ttl or self.default_ttl
        
        # Evict oldest entry if cache is full
        if len(self.cache) >= self.max_size and cache_key not in self.cache:
            self.cache.popitem(last=False)
            self.stats["evictions"] += 1
            
        self.cache[cache_key] = {
            "mcp_name": mcp_name,
            "tool_name": tool_name,
            "result": result,
            "cached_at": time.time(),
            "expires_at": time.time() + ttl
        }
        
        logger.debug("💾 Cached result", mcp=mcp_name, tool=tool_name, ttl=ttl)
        
    async def invalidate_mcp(self, mcp_name: str) -> int:
        """
        Invalidate all cached results for an MCP.
        
        Args:
            mcp_name: Name of the MCP server
            
        Returns:
            Number of entries removed
        """
        keys_to_remove = [
            key for key, entry in self.cache.items()
            if entry["mcp_name"] == mcp_name
        ]
        
        for key in keys_to_remove:
            del self.cache[key]
            
        count = len(keys_to_remove)
        if count > 0:
            self.stats["invalidations"] += count
            logger.info("🗑️ Invalidated cache entries", mcp=mcp_name, count=count)
            
        return count
        
    async def invalidate_tool(self, mcp_name: str, tool_name: str) -> int:
        """
        Invalidate all cached results for a specific tool.
        
        Args:
            mcp_name: Name of the MCP server
            tool_name: Name of the tool
            
        Returns:
            Number of entries removed
        """
        keys_to_remove = [
            key for key, entry in self.cache.items()
            if entry["mcp_name"] == mcp_name and entry["tool_name"] == tool_name
        ]
        
        for key in keys_to_remove:
            del self.cache[key]
            
        count = len(keys_to_remove)
        if count > 0:
            self.stats["invalidations"] += count
            logger.info("🗑️ Invalidated tool cache", mcp=mcp_name, tool=tool_name, count=count)
            
        return count
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "evictions": self.stats["evictions"],
            "invalidations": self.stats["invalidations"],
            "hit_rate_percent": round(hit_rate, 2)
        }
        
    async def _cleanup_loop(self):
        """Background task to cleanup expired entries."""
        while self.running:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                now = time.time()
                expired_keys = [
                    key for key, entry in self.cache.items()
                    if now > entry["expires_at"]
                ]
                
                for key in expired_keys:
                    del self.cache[key]
                    
                if expired_keys:
                    logger.debug("🧹 Cleaned up expired cache entries", count=len(expired_keys))
                    
            except Exception as e:
                logger.error("❌ Cache cleanup error", error=str(e))
                await asyncio.sleep(60)


# Global cache instance
_cache: Optional[ToolCache] = None


def get_tool_cache() -> ToolCache:
    """Get global tool cache instance."""
    global _cache
    if _cache is None:
        _cache = ToolCache()
    return _cache


async def start_tool_cache():
    """Start the global tool cache."""
    cache = get_tool_cache()
    await cache.start()


async def stop_tool_cache():
    """Stop the global tool cache."""
    cache = get_tool_cache()
    await cache.stop()
