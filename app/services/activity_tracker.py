"""
Activity Tracker Service

Tracks user-facing activities for conversation flow visualization.
Records: user messages, tool calls, tool responses, assistant responses.
"""

import uuid
import json
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings
from app.utils.logger import logger

logger = logger.bind(service="ActivityTracker")


class ActivityTracker:
    """Service for tracking user activities in conversations."""
    
    def __init__(self):
        self.enabled = getattr(settings, 'ACTIVITY_TRACKING_ENABLED', True)
    
    async def record_user_message(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: int,
        sequence_num: int,
        message: str
    ) -> Optional[uuid.UUID]:
        """Record a user message activity."""
        if not self.enabled:
            return None
        
        activity_data = {
            "message": message,
            "message_length": len(message)
        }
        
        return await self._insert_activity(
            db=db,
            conversation_id=conversation_id,
            session_id=session_id,
            user_id=user_id,
            sequence_num=sequence_num,
            activity_type="user_message",
            activity_data=activity_data
        )
    
    async def record_tool_call(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: int,
        sequence_num: int,
        mcp_server: str,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Optional[uuid.UUID]:
        """Record an MCP tool call activity."""
        if not self.enabled:
            return None
        
        activity_data = {
            "mcp_server": mcp_server,
            "tool_name": tool_name,
            "parameters": parameters
        }
        
        return await self._insert_activity(
            db=db,
            conversation_id=conversation_id,
            session_id=session_id,
            user_id=user_id,
            sequence_num=sequence_num,
            activity_type="mcp_tool_call",
            activity_data=activity_data
        )
    
    async def record_tool_response(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: int,
        sequence_num: int,
        mcp_server: str,
        tool_name: str,
        status: str,
        duration_ms: int,
        result_summary: Optional[str] = None
    ) -> Optional[uuid.UUID]:
        """Record an MCP tool response activity."""
        if not self.enabled:
            return None
        
        activity_data = {
            "mcp_server": mcp_server,
            "tool_name": tool_name,
            "status": status,
            "result_summary": result_summary
        }
        
        return await self._insert_activity(
            db=db,
            conversation_id=conversation_id,
            session_id=session_id,
            user_id=user_id,
            sequence_num=sequence_num,
            activity_type="mcp_tool_response",
            activity_data=activity_data,
            duration_ms=duration_ms
        )
    
    async def record_assistant_response(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: int,
        sequence_num: int,
        message: str,
        tokens_used: int,
        model: Optional[str] = None
    ) -> Optional[uuid.UUID]:
        """Record an assistant response activity."""
        if not self.enabled:
            return None
        
        activity_data = {
            "message": message[:500],  # Store first 500 chars
            "message_length": len(message),
            "tokens_used": tokens_used,
            "model": model
        }
        
        return await self._insert_activity(
            db=db,
            conversation_id=conversation_id,
            session_id=session_id,
            user_id=user_id,
            sequence_num=sequence_num,
            activity_type="assistant_response",
            activity_data=activity_data
        )
    
    async def _insert_activity(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: int,
        sequence_num: int,
        activity_type: str,
        activity_data: Dict[str, Any],
        duration_ms: Optional[int] = None
    ) -> Optional[uuid.UUID]:
        """Insert activity record into database."""
        try:
            activity_id = uuid.uuid4()
            
            query = text("""
                INSERT INTO omni2.user_activities (
                    activity_id,
                    conversation_id,
                    session_id,
                    user_id,
                    sequence_num,
                    activity_type,
                    activity_data,
                    duration_ms,
                    created_at
                ) VALUES (
                    :activity_id,
                    :conversation_id,
                    :session_id,
                    :user_id,
                    :sequence_num,
                    :activity_type,
                    :activity_data,
                    :duration_ms,
                    NOW()
                )
            """)
            
            await db.execute(
                query,
                {
                    "activity_id": activity_id,
                    "conversation_id": conversation_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "sequence_num": sequence_num,
                    "activity_type": activity_type,
                    "activity_data": json.dumps(activity_data),
                    "duration_ms": duration_ms
                }
            )
            
            await db.commit()
            
            logger.debug(
                "Activity recorded",
                activity_type=activity_type,
                conversation_id=str(conversation_id),
                sequence_num=sequence_num
            )
            
            return activity_id
            
        except Exception as e:
            logger.error(
                "Failed to record activity",
                activity_type=activity_type,
                error=str(e),
                exc_info=True
            )
            await db.rollback()
            return None


# Global instance
_activity_tracker: Optional[ActivityTracker] = None


def get_activity_tracker() -> ActivityTracker:
    """Get or create global activity tracker instance."""
    global _activity_tracker
    if _activity_tracker is None:
        _activity_tracker = ActivityTracker()
    return _activity_tracker
