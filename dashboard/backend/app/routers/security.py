from fastapi import APIRouter, Query, Depends
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db

router = APIRouter(prefix="/security", tags=["security"])

@router.get("/stats")
async def get_security_stats(db: AsyncSession = Depends(get_db)):
    """Get security statistics"""
    now = datetime.now()
    
    # Total incidents by time range
    result = await db.execute(
        text("SELECT COUNT(*) FROM omni2.prompt_injection_log WHERE detected_at >= :since"),
        {"since": now - timedelta(hours=24)}
    )
    incidents_24h = result.scalar() or 0
    
    result = await db.execute(
        text("SELECT COUNT(*) FROM omni2.prompt_injection_log WHERE detected_at >= :since"),
        {"since": now - timedelta(days=7)}
    )
    incidents_7d = result.scalar() or 0
    
    result = await db.execute(
        text("SELECT COUNT(*) FROM omni2.prompt_injection_log WHERE detected_at >= :since"),
        {"since": now - timedelta(days=30)}
    )
    incidents_30d = result.scalar() or 0
    
    # High risk incidents (score >= 0.8)
    result = await db.execute(
        text("SELECT COUNT(*) FROM omni2.prompt_injection_log WHERE injection_score >= 0.8 AND detected_at >= :since"),
        {"since": now - timedelta(days=30)}
    )
    high_risk = result.scalar() or 0
    
    # Blocked users count
    result = await db.execute(
        text("SELECT COUNT(DISTINCT user_id) FROM omni2.prompt_injection_log WHERE action = 'block' AND detected_at >= :since"),
        {"since": now - timedelta(days=30)}
    )
    blocked_users = result.scalar() or 0
    
    # Policy violations (from audit logs)
    result = await db.execute(
        text("SELECT COUNT(*) FROM omni2.audit_logs WHERE was_blocked = true AND timestamp >= :since"),
        {"since": now - timedelta(days=30)}
    )
    policy_violations = result.scalar() or 0
    
    return {
        "total_incidents_24h": incidents_24h,
        "total_incidents_7d": incidents_7d,
        "total_incidents_30d": incidents_30d,
        "high_risk_incidents": high_risk,
        "blocked_users": blocked_users,
        "policy_violations": policy_violations
    }

@router.get("/incidents")
async def get_security_incidents(
    range: str = Query("24h", regex="^(24h|7d|30d)$"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Get recent security incidents"""
    now = datetime.now()
    time_ranges = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}
    since = now - time_ranges[range]
    
    result = await db.execute(text("""
        SELECT 
            p.id,
            p.user_id,
            u.email as user_email,
            p.message,
            p.injection_score,
            p.action,
            p.detected_at
        FROM omni2.prompt_injection_log p
        LEFT JOIN auth_service.users u ON p.user_id = u.id
        WHERE p.detected_at >= :since
        ORDER BY p.detected_at DESC
        LIMIT :limit
    """), {"since": since, "limit": limit})
    
    rows = result.fetchall()
    return [
        {
            "id": row[0],
            "user_id": row[1],
            "user_email": row[2],
            "message": row[3],
            "injection_score": float(row[4]),
            "action": row[5],
            "detected_at": row[6].isoformat() if row[6] else None
        }
        for row in rows
    ]

@router.get("/blocked-users")
async def get_blocked_users(db: AsyncSession = Depends(get_db)):
    """Get list of blocked users"""
    result = await db.execute(text("""
        SELECT 
            p.user_id,
            u.email as user_email,
            COUNT(*) as block_count,
            MAX(p.detected_at) as last_blocked,
            MAX(a.block_reason) as block_reason
        FROM omni2.prompt_injection_log p
        LEFT JOIN auth_service.users u ON p.user_id = u.id
        LEFT JOIN omni2.audit_logs a ON a.user_id = p.user_id AND a.was_blocked = true
        WHERE p.action = 'block'
        GROUP BY p.user_id, u.email
        ORDER BY last_blocked DESC
    """))
    
    rows = result.fetchall()
    return [
        {
            "user_id": row[0],
            "user_email": row[1],
            "block_count": row[2],
            "last_blocked": row[3].isoformat() if row[3] else None,
            "block_reason": row[4]
        }
        for row in rows
    ]
