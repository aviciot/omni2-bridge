"""Redis Event Publisher for PT Service."""

import json
import redis.asyncio as redis
from typing import Dict, Any
from config import settings
from logger import logger


class PTEventPublisher:
    """Publish PT events to Redis for dashboard consumption."""
    
    def __init__(self):
        self.redis_client = None
        self.channel = "pt_events"
    
    async def connect(self):
        """Connect to Redis."""
        self.redis_client = await redis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        logger.info(f"Redis publisher connected: {self.channel}")
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    async def publish_progress(self, run_id: int, completed: int, total: int, 
                              current_test: str = None):
        """Publish PT progress event."""
        event = {
            "event": "pt_progress",
            "run_id": run_id,
            "completed": completed,
            "total": total,
            "current_test": current_test,
            "progress_pct": int((completed / total) * 100) if total > 0 else 0
        }
        await self._publish(event)
    
    async def publish_complete(self, run_id: int, status: str, summary: Dict):
        """Publish PT completion event."""
        event = {
            "event": "pt_complete",
            "run_id": run_id,
            "status": status,
            "summary": summary
        }
        await self._publish(event)
    
    async def publish_started(self, run_id: int, mcp_name: str, preset: str):
        """Publish PT started event."""
        event = {
            "event": "pt_started",
            "run_id": run_id,
            "mcp_name": mcp_name,
            "preset": preset
        }
        await self._publish(event)
    
    async def publish_error(self, run_id: int, error: str):
        """Publish PT error event."""
        event = {
            "event": "pt_error",
            "run_id": run_id,
            "error": error
        }
        await self._publish(event)
    
    async def publish_event(self, run_id: int, event_type: str, data: Dict):
        """Publish custom PT event to WebSocket broadcaster."""
        event = {
            "type": f"pt_{event_type}",
            "run_id": run_id,
            "data": data
        }
        await self._publish(event)
    
    async def _publish(self, event: Dict[str, Any]):
        """Publish event to Redis channel for WebSocket broadcaster."""
        if not self.redis_client:
            logger.warning("Redis not connected, skipping event publish")
            return
        
        try:
            await self.redis_client.publish(self.channel, json.dumps(event))
            logger.debug(f"Published event: {event.get('type', event.get('event'))} (run_id={event.get('run_id')})")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")


# Global instance
_publisher: PTEventPublisher = None

async def get_publisher() -> PTEventPublisher:
    """Get or create global publisher."""
    global _publisher
    if _publisher is None:
        _publisher = PTEventPublisher()
        await _publisher.connect()
    return _publisher
