"""
User Activities Router - Dashboard Backend Direct DB Access
"""

from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from typing import Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/activities/conversations")
async def get_conversations(
    user_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    mcp_server: Optional[str] = None,
    limit: int = Query(50, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Get list of conversations with summary stats"""
    
    where_clauses = []
    params = {"limit": limit}
    
    if user_id:
        where_clauses.append("user_id = :user_id")
        params["user_id"] = user_id
    
    if date_from:
        where_clauses.append("created_at >= :date_from")
        params["date_from"] = datetime.fromisoformat(date_from)
    
    if date_to:
        where_clauses.append("created_at <= :date_to")
        params["date_to"] = datetime.fromisoformat(date_to)
    
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    query = text(f"""
        WITH conversation_summary AS (
            SELECT 
                conversation_id,
                user_id,
                MIN(created_at) as started_at,
                MAX(created_at) as ended_at,
                COUNT(*) as activity_count,
                SUM(CASE WHEN activity_type = 'mcp_tool_call' THEN 1 ELSE 0 END) as tool_calls,
                AVG(CASE WHEN duration_ms IS NOT NULL THEN duration_ms ELSE NULL END) as avg_duration_ms,
                ARRAY_AGG(DISTINCT activity_data->>'mcp_server') FILTER (WHERE activity_data->>'mcp_server' IS NOT NULL) as mcp_servers,
                (SELECT activity_data->>'message' FROM omni2.user_activities 
                 WHERE conversation_id = ua.conversation_id AND activity_type = 'user_message' 
                 ORDER BY sequence_num LIMIT 1) as first_message
            FROM omni2.user_activities ua
            {where_sql}
            GROUP BY conversation_id, user_id
        )
        SELECT * FROM conversation_summary
        ORDER BY started_at DESC
        LIMIT :limit
    """)
    
    result = await db.execute(query, params)
    rows = result.fetchall()
    
    conversations = []
    for row in rows:
        duration_seconds = None
        if row[2] and row[3]:
            duration_seconds = (row[3] - row[2]).total_seconds()
        
        conversations.append({
            "conversation_id": str(row[0]),
            "user_id": row[1],
            "started_at": row[2].isoformat() if row[2] else None,
            "ended_at": row[3].isoformat() if row[3] else None,
            "duration_seconds": duration_seconds,
            "activity_count": row[4],
            "tool_calls": row[5],
            "avg_tool_duration_ms": int(row[6]) if row[6] else None,
            "mcp_servers": row[7] if row[7] else [],
            "first_message": row[8]
        })
    
    logger.info(f"[ACTIVITIES] Retrieved {len(conversations)} conversations")
    
    return {
        "conversations": conversations,
        "total": len(conversations)
    }


@router.get("/activities/conversation/{conversation_id}")
async def get_conversation_activities(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all activities for a specific conversation"""
    
    query = text("""
        SELECT 
            activity_id,
            conversation_id,
            session_id,
            user_id,
            sequence_num,
            activity_type,
            activity_data,
            duration_ms,
            created_at
        FROM omni2.user_activities
        WHERE conversation_id = :conversation_id
        ORDER BY sequence_num ASC
    """)
    
    result = await db.execute(query, {"conversation_id": conversation_id})
    rows = result.fetchall()
    
    if not rows:
        return {
            "conversation_id": conversation_id,
            "activities": [],
            "error": "Conversation not found"
        }
    
    activities = []
    for row in rows:
        activities.append({
            "activity_id": str(row[0]),
            "conversation_id": str(row[1]),
            "session_id": str(row[2]),
            "user_id": row[3],
            "sequence_num": row[4],
            "activity_type": row[5],
            "activity_data": row[6],
            "duration_ms": row[7],
            "created_at": row[8].isoformat() if row[8] else None
        })
    
    started_at = rows[0][8]
    ended_at = rows[-1][8]
    duration_seconds = (ended_at - started_at).total_seconds() if started_at and ended_at else 0
    tool_calls = sum(1 for a in activities if a["activity_type"] == "mcp_tool_call")
    
    logger.info(f"[ACTIVITIES] Retrieved {len(activities)} activities for conversation {conversation_id}")
    
    return {
        "conversation_id": conversation_id,
        "user_id": rows[0][3],
        "started_at": started_at.isoformat() if started_at else None,
        "ended_at": ended_at.isoformat() if ended_at else None,
        "duration_seconds": duration_seconds,
        "total_activities": len(activities),
        "tool_calls": tool_calls,
        "activities": activities
    }
