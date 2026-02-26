"""
Flow Tracker Service

Tracks user interaction flows for debugging and monitoring.
Always logs to Redis, conditionally broadcasts to Dashboard WebSocket.
Monitoring config stored in omni2.omni2_config with TTL.
"""

import json
import time
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from typing import Optional
from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_redis
from app.utils.logger import logger


class FlowTracker:
    """Tracks user interaction flows"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def is_monitored(self, user_id: int, db: AsyncSession) -> bool:
        """Check if user is being monitored (from DB config with TTL)"""
        try:
            result = await db.execute(text("""
                SELECT config_value FROM omni2.omni2_config 
                WHERE config_key = :key AND is_active = true
            """), {"key": f"monitor_user_{user_id}"})
            row = result.fetchone()
            
            if not row:
                return False
            
            config = row[0]
            expires_at = config.get('expires_at', 0)
            
            if time.time() < expires_at:
                logger.debug(f"[FLOW] ✓ User {user_id} is monitored")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[FLOW] ✗ Failed to check monitoring status: {e}")
            return False
    
    async def log_event(
        self,
        session_id: UUID,
        user_id: int,
        event_type: str,
        db: AsyncSession,
        parent_id: Optional[str] = None,
        **data
    ) -> str:
        """
        Log event to Redis and conditionally broadcast to WebSocket.
        
        Args:
            session_id: Session UUID
            user_id: User ID
            event_type: Event type (auth_check, tool_call, etc.)
            parent_id: Parent node ID (for tree structure)
            **data: Additional event data
        
        Returns:
            node_id: Generated node ID
        """
        node_id = str(uuid4())
        
        # Always save to Redis
        event_data = {
            "node_id": node_id,
            "event_type": event_type,
            "parent_id": parent_id or "",
            "timestamp": str(time.time()),
            **{k: str(v) for k, v in data.items()}
        }
        
        await self.redis.xadd(f"flow:{session_id}", event_data)
        await self.redis.expire(f"flow:{session_id}", 86400)
        logger.debug(f"[FLOW] → Redis Stream: {event_type} (node: {node_id[:8]}...)")
        
        # Publish to Redis Pub/Sub for real-time dashboard (if monitored)
        if await self.is_monitored(user_id, db):
            await self.redis.publish(
                f"flow_events:{user_id}",
                json.dumps({
                    "user_id": user_id,
                    "session_id": str(session_id),
                    "node_id": node_id,
                    "event_type": event_type,
                    "parent_id": parent_id,
                    "timestamp": event_data["timestamp"],
                    **data
                })
            )
            logger.info(f"[FLOW] ⚡ Published to Pub/Sub: {event_type} → flow_events:{user_id}")
        
        return node_id
    
    async def save_to_db(self, session_id: UUID, user_id: int, db: AsyncSession, conversation_id: Optional[UUID] = None, source: str = "chat"):
        """
        Save flow from Redis to PostgreSQL and cleanup Redis.
        
        Args:
            session_id: Session UUID
            user_id: User ID
            db: Database session
            conversation_id: Optional conversation UUID (for WebSocket chat)
        """
        try:
            # Read all events from Redis
            events = await self.redis.xrange(f"flow:{session_id}")
            
            if not events:
                logger.warning(f"[FLOW] ⚠ No events found for session {session_id}")
                return
            
            # Convert to JSON
            flow_data = {
                "session_id": str(session_id),
                "user_id": user_id,
                "events": [dict(event[1]) for event in events]
            }
            
            # Save to PostgreSQL with conversation_id
            if conversation_id:
                await db.execute(text("""
                    INSERT INTO omni2.interaction_flows (session_id, user_id, conversation_id, flow_data, completed_at, source)
                    VALUES (:sid, :uid, :cid, :data, NOW(), :source)
                """), {
                    "sid": str(session_id),
                    "uid": user_id,
                    "cid": str(conversation_id),
                    "data": json.dumps(flow_data),
                    "source": source
                })
            else:
                await db.execute(text("""
                    INSERT INTO omni2.interaction_flows (session_id, user_id, flow_data, completed_at, source)
                    VALUES (:sid, :uid, :data, NOW(), :source)
                """), {
                    "sid": str(session_id),
                    "uid": user_id,
                    "data": json.dumps(flow_data),
                    "source": source
                })
            await db.commit()
            
            # Delete from Redis
            await self.redis.delete(f"flow:{session_id}")
            
            logger.info(f"[FLOW] ✓ Saved session {session_id} to DB ({len(events)} events, conversation: {conversation_id or 'N/A'})")
            
        except Exception as e:
            logger.error(f"[FLOW] ✗ Failed to save session {session_id}: {e}")
            await db.rollback()


async def get_flow_tracker(redis: Redis = Depends(get_redis)) -> FlowTracker:
    """Dependency injection for FlowTracker"""
    return FlowTracker(redis)
