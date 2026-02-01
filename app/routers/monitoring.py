"""
Monitoring Control Router

Endpoints to enable/disable flow tracking for specific users.
Stores config in omni2.omni2_config with TTL.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.utils.logger import logger
import json

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


@router.post("/enable")
async def enable_monitoring(user_ids: list[int], ttl_hours: int = 24, db: AsyncSession = Depends(get_db)):
    """Enable real-time flow tracking for multiple users with TTL"""
    expires_at_ts = (datetime.utcnow() + timedelta(hours=ttl_hours)).timestamp()
    
    for user_id in user_ids:
        await db.execute(text("""
            INSERT INTO omni2.omni2_config (config_key, config_value, description, is_active)
            VALUES (:key, jsonb_build_object('expires_at', :expires), :desc, true)
            ON CONFLICT (config_key) DO UPDATE SET config_value = EXCLUDED.config_value, updated_at = NOW()
        """), {
            "key": f"monitor_user_{user_id}",
            "expires": expires_at_ts,
            "desc": f"Flow monitoring for user {user_id}"
        })
    
    await db.commit()
    logger.info(f"[MONITORING] ✓ Enabled for users {user_ids} (TTL: {ttl_hours}h)")
    return {"status": "enabled", "user_ids": user_ids, "expires_at": expires_at_ts}


@router.post("/disable")
async def disable_monitoring(user_ids: list[int], db: AsyncSession = Depends(get_db)):
    """Disable real-time flow tracking for multiple users"""
    for user_id in user_ids:
        await db.execute(text("""
            DELETE FROM omni2.omni2_config WHERE config_key = :key
        """), {"key": f"monitor_user_{user_id}"})
    
    await db.commit()
    logger.info(f"[MONITORING] ✗ Disabled for users {user_ids}")
    return {"status": "disabled", "user_ids": user_ids}


@router.get("/list")
async def list_monitored(db: AsyncSession = Depends(get_db)):
    """Get list of monitored users with expiry times"""
    result = await db.execute(text("""
        SELECT config_key, config_value FROM omni2.omni2_config 
        WHERE config_key LIKE 'monitor_user_%' AND is_active = true
    """))
    
    monitored_users = []
    now = datetime.utcnow().timestamp()
    
    for row in result.fetchall():
        user_id = int(row[0].replace('monitor_user_', ''))
        expires_at = row[1].get('expires_at', 0)
        if expires_at > now:
            monitored_users.append({"user_id": user_id, "expires_at": expires_at})
    
    logger.info(f"[MONITORING] ℹ Listed {len(monitored_users)} active monitored users")
    return {"monitored_users": monitored_users}


@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    """Get list of all users for monitoring selection"""
    result = await db.execute(text("""
        SELECT id, email FROM auth_service.users ORDER BY email
    """))
    
    users = [{"id": row[0], "email": row[1], "full_name": row[1]} for row in result.fetchall()]
    return {"users": users}


@router.get("/flows/{user_id}")
async def get_user_flows(user_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get historical flows for a user from PostgreSQL"""
    result = await db.execute(text("""
        SELECT session_id, flow_data, created_at, completed_at
        FROM omni2.interaction_flows
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT :limit
    """), {"user_id": user_id, "limit": limit})
    
    flows = []
    for row in result.fetchall():
        flows.append({
            "session_id": str(row[0]),
            "flow_data": row[1],
            "created_at": row[2].isoformat() if row[2] else None,
            "completed_at": row[3].isoformat() if row[3] else None
        })
    
    logger.info(f"[MONITORING] ℹ Retrieved {len(flows)} flows for user {user_id}")
    return {"flows": flows}


@router.get("/flows/session/{session_id}")
async def get_flow_by_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get specific flow by session ID"""
    result = await db.execute(text("""
        SELECT session_id, user_id, flow_data, created_at, completed_at
        FROM omni2.interaction_flows
        WHERE session_id = :session_id
    """), {"session_id": session_id})
    
    row = result.fetchone()
    if not row:
        return {"error": "Flow not found"}
    
    return {
        "session_id": str(row[0]),
        "user_id": row[1],
        "flow_data": row[2],
        "created_at": row[3].isoformat() if row[3] else None,
        "completed_at": row[4].isoformat() if row[4] else None
    }
