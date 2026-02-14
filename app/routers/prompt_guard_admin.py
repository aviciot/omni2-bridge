"""
Prompt Guard Admin API

Endpoints for managing prompt guard configuration and viewing detections.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from typing import Dict, Any, List
from pydantic import BaseModel
import json

from app.database import get_db
from app.models import Omni2Config
from app.services.prompt_guard_client import get_prompt_guard_client
from app.utils.logger import logger


router = APIRouter(prefix="/api/v1/prompt-guard", tags=["Prompt Guard"])


class PromptGuardConfig(BaseModel):
    """Prompt guard configuration model."""
    enabled: bool = True
    threshold: float = 0.5
    cache_ttl_seconds: int = 3600
    bypass_roles: List[str] = []
    behavioral_tracking: Dict[str, Any] = {
        "enabled": True,
        "warning_threshold": 3,
        "block_threshold": 5,
        "window_hours": 24,
    }
    actions: Dict[str, bool] = {
        "warn": True,
        "filter": False,
        "block": False,
    }
    messages: Dict[str, str] = {}
    notifications: Dict[str, bool] = {
        "enabled": True,
        "show_violations": True,
        "show_blocks": True,
    }


class DetectionStats(BaseModel):
    """Detection statistics."""
    total_detections: int
    blocked: int
    warned: int
    filtered: int
    unique_users: int
    avg_score: float
    period_hours: int


@router.get("/config")
async def get_config(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get current prompt guard configuration."""
    result = await db.execute(
        select(Omni2Config).where(Omni2Config.config_key == "prompt_guard")
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Prompt guard config not found")
    
    return {
        "config_key": config.config_key,
        "config_value": config.config_value,
        "is_active": config.is_active,
        "updated_at": config.updated_at.isoformat(),
    }


@router.put("/config")
async def update_config(
    config: PromptGuardConfig,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Update prompt guard configuration."""
    try:
        config_dict = config.model_dump()
        logger.info(f"[PROMPT-GUARD] Received config update: {config_dict}")
        
        # Update database
        result = await db.execute(
            text(
                "UPDATE omni2.omni2_config "
                "SET config_value = CAST(:config AS jsonb), updated_at = NOW() "
                "WHERE config_key = 'prompt_guard'"
            ),
            {"config": json.dumps(config_dict)},
        )
        await db.commit()
        logger.info(f"[PROMPT-GUARD] Database updated successfully")
        
        # Publish to Redis for instant update
        from app.database import redis_client
        if redis_client:
            await redis_client.publish(
                "prompt_guard_config_reload",
                json.dumps({"config": config_dict})
            )
        
        # Trigger reload in guard service
        guard_client = get_prompt_guard_client()
        if guard_client:
            await guard_client.reload_config()
        
        logger.info("[PROMPT-GUARD] Configuration updated", config=config_dict)
        
        return {"status": "success", "message": "Configuration updated and reloaded"}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"[PROMPT-GUARD] Failed to update config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/enable")
async def enable_guard(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """Enable prompt guard."""
    await db.execute(
        text(
            "UPDATE omni2.omni2_config "
            "SET config_value = jsonb_set(config_value, '{enabled}', 'true'), "
            "updated_at = NOW() "
            "WHERE config_key = 'prompt_guard'"
        )
    )
    await db.commit()
    
    # Trigger reload
    guard_client = get_prompt_guard_client()
    if guard_client:
        await guard_client.reload_config()
    
    logger.info("[PROMPT-GUARD] Enabled")
    return {"status": "success", "message": "Prompt guard enabled"}


@router.post("/config/disable")
async def disable_guard(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """Disable prompt guard."""
    await db.execute(
        text(
            "UPDATE omni2.omni2_config "
            "SET config_value = jsonb_set(config_value, '{enabled}', 'false'), "
            "updated_at = NOW() "
            "WHERE config_key = 'prompt_guard'"
        )
    )
    await db.commit()
    
    # Trigger reload
    guard_client = get_prompt_guard_client()
    if guard_client:
        await guard_client.reload_config()
    
    logger.warning("[PROMPT-GUARD] Disabled")
    return {"status": "success", "message": "Prompt guard disabled"}


@router.get("/stats")
async def get_stats(
    hours: int = 24,
    db: AsyncSession = Depends(get_db)
) -> DetectionStats:
    """Get detection statistics for the last N hours."""
    result = await db.execute(
        text(
            "SELECT "
            "COUNT(*) as total, "
            "COUNT(DISTINCT user_id) as unique_users, "
            "AVG(injection_score) as avg_score, "
            "SUM(CASE WHEN action = 'block' THEN 1 ELSE 0 END) as blocked, "
            "SUM(CASE WHEN action = 'warn' THEN 1 ELSE 0 END) as warned, "
            "SUM(CASE WHEN action = 'filter' THEN 1 ELSE 0 END) as filtered "
            "FROM omni2.prompt_injection_log "
            "WHERE detected_at > NOW() - INTERVAL '1 hour' * :hours"
        ),
        {"hours": hours},
    )
    row = result.first()
    
    return DetectionStats(
        total_detections=row.total or 0,
        blocked=row.blocked or 0,
        warned=row.warned or 0,
        filtered=row.filtered or 0,
        unique_users=row.unique_users or 0,
        avg_score=round(row.avg_score or 0.0, 4),
        period_hours=hours,
    )


@router.get("/detections")
async def get_recent_detections(
    limit: int = 50,
    user_id: int = None,
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get recent prompt injection detections."""
    query = """
        SELECT 
            pil.id,
            pil.user_id,
            u.email,
            pil.message,
            pil.injection_score,
            pil.action,
            pil.detected_at
        FROM omni2.prompt_injection_log pil
        LEFT JOIN auth_service.users u ON u.id = pil.user_id
        WHERE 1=1
    """
    
    params = {"limit": limit}
    
    if user_id:
        query += " AND pil.user_id = :user_id"
        params["user_id"] = user_id
    
    query += " ORDER BY pil.detected_at DESC LIMIT :limit"
    
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "email": row.email,
            "message": row.message[:100] + "..." if len(row.message) > 100 else row.message,
            "injection_score": float(row.injection_score),
            "action": row.action,
            "detected_at": row.detected_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/top-offenders")
async def get_top_offenders(
    hours: int = 24,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get users with most violations."""
    result = await db.execute(
        text(
            """
            SELECT 
                pil.user_id,
                u.email,
                COUNT(*) as violation_count,
                MAX(pil.injection_score) as max_score,
                MAX(pil.detected_at) as last_violation
            FROM omni2.prompt_injection_log pil
            LEFT JOIN auth_service.users u ON u.id = pil.user_id
            WHERE pil.detected_at > NOW() - INTERVAL '1 hour' * :hours
            GROUP BY pil.user_id, u.email
            ORDER BY violation_count DESC
            LIMIT :limit
            """
        ),
        {"hours": hours, "limit": limit},
    )
    rows = result.fetchall()
    
    return [
        {
            "user_id": row.user_id,
            "email": row.email,
            "violation_count": row.violation_count,
            "max_score": float(row.max_score),
            "last_violation": row.last_violation.isoformat(),
        }
        for row in rows
    ]


@router.delete("/detections/{detection_id}")
async def delete_detection(
    detection_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Delete a detection record."""
    await db.execute(
        text("DELETE FROM omni2.prompt_injection_log WHERE id = :id"),
        {"id": detection_id},
    )
    await db.commit()
    
    return {"status": "success", "message": f"Detection {detection_id} deleted"}


@router.post("/test")
async def test_prompt(
    message: str,
    user_id: int = 1,
) -> Dict[str, Any]:
    """Test a message against prompt guard (for debugging)."""
    guard_client = get_prompt_guard_client()
    
    if not guard_client:
        raise HTTPException(status_code=503, detail="Prompt guard client not available")
    
    result = await guard_client.check_prompt(message, user_id)
    
    return {
        "message": message,
        "user_id": user_id,
        "result": result,
    }


@router.get("/roles")
async def get_roles_config(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get prompt guard configuration for roles."""
    result = await db.execute(
        select(Omni2Config).where(Omni2Config.config_key == "prompt_guard")
    )
    config = result.scalar_one_or_none()
    
    if not config:
        return {"bypass_roles": [], "all_roles": []}
    
    # Get all roles
    roles_result = await db.execute(
        text("SELECT name FROM auth_service.roles ORDER BY name")
    )
    all_roles = [row[0] for row in roles_result.fetchall()]
    
    bypass_roles = config.config_value.get("bypass_roles", [])
    
    return {
        "bypass_roles": bypass_roles,
        "all_roles": all_roles,
        "enabled": config.config_value.get("enabled", True)
    }


@router.put("/roles/bypass")
async def update_bypass_roles(
    bypass_roles: List[str],
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Update roles that bypass prompt guard."""
    try:
        await db.execute(
            text(
                "UPDATE omni2.omni2_config "
                "SET config_value = jsonb_set(config_value, '{bypass_roles}', CAST(:roles AS jsonb)), "
                "updated_at = NOW() "
                "WHERE config_key = 'prompt_guard'"
            ),
            {"roles": json.dumps(bypass_roles)},
        )
        await db.commit()
        
        # Trigger reload
        guard_client = get_prompt_guard_client()
        if guard_client:
            await guard_client.reload_config()
        
        logger.info(f"[PROMPT-GUARD] Bypass roles updated: {bypass_roles}")
        return {"status": "success", "message": "Bypass roles updated"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
