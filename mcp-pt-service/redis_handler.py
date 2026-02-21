"""Redis Handler - Communication with omni2 via pub/sub."""

import redis.asyncio as redis
import json
import asyncio
from typing import Dict, Any

from config import settings
from logger import logger
from scanner import MCPPTScanner


class RedisHandler:
    """Handles Redis pub/sub communication."""
    
    def __init__(self, scanner: MCPPTScanner):
        self.scanner = scanner
        self.redis_client: redis.Redis = None
        self.pubsub = None
        self._shutdown = False
        self._connected = False
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=10,
            )
            
            await self.redis_client.ping()
            self._connected = True
            logger.info(f"Redis connected at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe("mcp_pt_scan", "mcp_pt_config_reload")
            logger.info("Subscribed to Redis channels")
            
        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connection."""
        self._shutdown = True
        try:
            if self.pubsub:
                await self.pubsub.unsubscribe()
                await self.pubsub.close()
        except:
            pass
        
        try:
            if self.redis_client:
                await self.redis_client.close()
        except:
            pass
        
        logger.info("Redis connection closed")
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected and self.redis_client is not None
    
    async def listen_for_requests(self):
        """Listen for scan requests."""
        logger.info("Listening for MCP PT scan requests...")
        
        while not self._shutdown:
            try:
                if not self._connected:
                    await asyncio.sleep(5)
                    continue
                
                async for message in self.pubsub.listen():
                    if self._shutdown:
                        break
                    
                    if message["type"] != "message":
                        continue
                    
                    channel = message["channel"]
                    
                    try:
                        data = json.loads(message["data"])
                        
                        if channel == "mcp_pt_scan":
                            await self._handle_scan_request(data)
                        
                        elif channel == "mcp_pt_config_reload":
                            await self._handle_config_reload(data)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in message: {e}")
                    except Exception as e:
                        logger.error(f"Error handling message: {e}", exc_info=True)
            
            except Exception as e:
                logger.error(f"Error in listener: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    async def _handle_scan_request(self, data: Dict[str, Any]):
        """Handle MCP scan request."""
        scan_id = data.get("scan_id")
        mcp_name = data.get("mcp_name")
        mcp_url = data.get("mcp_url")
        test_prompts = data.get("test_prompts", [])
        
        if not scan_id or not mcp_name or not mcp_url:
            logger.warning("Invalid scan request", data=data)
            return
        
        logger.info(f"Processing scan request {scan_id} for {mcp_name}")
        
        # Perform scan
        result = await self.scanner.scan_mcp(mcp_name, mcp_url, test_prompts)
        
        # Save to database
        await save_scan_result(mcp_name, mcp_url, result)
        
        # Publish result
        response = {
            "scan_id": scan_id,
            "mcp_name": mcp_name,
            "result": result,
        }
        
        try:
            await self.redis_client.publish(
                "mcp_pt_response",
                json.dumps(response)
            )
            logger.info(f"Scan completed for {mcp_name} - Score: {result['score']}")
        except Exception as e:
            logger.error(f"Failed to publish scan result: {e}")
    
    async def _handle_config_reload(self, data: Dict[str, Any]):
        """Handle configuration reload request."""
        logger.info("Reloading configuration", data=data)
        
        from db import load_config_from_db
        new_config = await load_config_from_db()
        self.scanner.reload_config(new_config)
        
        logger.info("Configuration reloaded successfully")


# Global Redis client for simple get/set operations
_redis_client = None

async def get_redis():
    """Get Redis client for simple operations."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True
        )
    return _redis_client
