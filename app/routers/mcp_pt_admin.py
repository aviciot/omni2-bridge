"""
MCP PT Admin API

Endpoints for managing MCP penetration testing.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Dict, Any, List
from pydantic import BaseModel
import json
import uuid

from app.database import get_db, get_redis
from app.models import Omni2Config
from app.utils.logger import logger


router = APIRouter(prefix="/api/v1/mcp-pt", tags=["MCP PT"])


class MCPPTConfig(BaseModel):
    """MCP PT configuration model."""
    enabled: bool = True
    tools: Dict[str, bool] = {
        "presidio": True,
        "truffleHog": True,
        "nuclei": False,
        "semgrep": False,
    }
    scan_depth: str = "standard"
    auto_scan: bool = False
    schedule_cron: str = "0 2 * * *"


class ScanRequest(BaseModel):
    """Scan request model."""
    mcp_names: List[str]
    test_prompts: List[str] = []


@router.get("/config")
async def get_config(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get current MCP PT configuration."""
    result = await db.execute(
        select(Omni2Config).where(Omni2Config.config_key == "mcp_pt")
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="MCP PT config not found")
    
    return {
        "config_key": config.config_key,
        "config_value": config.config_value,
        "is_active": config.is_active,
        "updated_at": config.updated_at.isoformat(),
    }


@router.put("/config")
async def update_config(
    config: MCPPTConfig,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Update MCP PT configuration."""
    try:
        config_dict = config.model_dump()
        logger.info(f"[MCP-PT] Received config update: {config_dict}")
        
        # Update database
        result = await db.execute(
            text(
                "UPDATE omni2.omni2_config "
                "SET config_value = CAST(:config AS jsonb), updated_at = NOW() "
                "WHERE config_key = 'mcp_pt'"
            ),
            {"config": json.dumps(config_dict)},
        )
        await db.commit()
        logger.info(f"[MCP-PT] Database updated successfully")
        
        logger.info("[MCP-PT] Configuration updated", config=config_dict)
        
        return {"status": "success", "message": "Configuration updated and reloaded"}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"[MCP-PT] Failed to update config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan")
async def start_scan(
    request: ScanRequest,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Start MCP penetration test scan."""
    logger.info(f"[MCP-PT] ========== SCAN REQUEST RECEIVED ==========")
    logger.info(f"[MCP-PT] MCP Names: {request.mcp_names}")
    logger.info(f"[MCP-PT] Test Prompts: {request.test_prompts}")
    
    try:
        # Get MCP servers info
        logger.info(f"[MCP-PT] Querying database for MCPs...")
        result = await db.execute(
            text(
                "SELECT name, url FROM omni2.mcp_servers "
                "WHERE name = ANY(:names) AND status = 'active'"
            ),
            {"names": request.mcp_names},
        )
        mcps = result.fetchall()
        logger.info(f"[MCP-PT] Found {len(mcps)} active MCPs: {[m[0] for m in mcps]}")
        
        if not mcps:
            logger.warning(f"[MCP-PT] No active MCPs found for: {request.mcp_names}")
            raise HTTPException(status_code=404, detail="No active MCPs found")
        
        scan_ids = []
        
        logger.info(f"[MCP-PT] ✅ Redis available, publishing scans...")
        for mcp in mcps:
            scan_id = str(uuid.uuid4())
            scan_ids.append(scan_id)
            
            message = {
                "scan_id": scan_id,
                "mcp_name": mcp[0],
                "mcp_url": mcp[1],
                "test_prompts": request.test_prompts,
            }
            
            logger.info(f"[MCP-PT] Publishing scan {scan_id} for {mcp[0]} to Redis channel 'mcp_pt_scan'")
            await redis.publish(
                "mcp_pt_scan",
                json.dumps(message)
            )
            logger.info(f"[MCP-PT] ✅ Scan request published for {mcp[0]}")
        
        logger.info(f"[MCP-PT] ========== SCAN REQUEST COMPLETED ==========")
        return {
            "status": "success",
            "message": f"Scan started for {len(mcps)} MCP(s)",
            "scan_ids": scan_ids,
        }
        
    except Exception as e:
        logger.error(f"[MCP-PT] Failed to start scan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scans")
async def get_scans(
    limit: int = 50,
    mcp_name: str = None,
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get recent scan results."""
    query = """
        SELECT 
            id,
            mcp_name,
            mcp_url,
            score,
            critical_count,
            high_count,
            medium_count,
            low_count,
            scanned_at
        FROM omni2.mcp_pt_scans
        WHERE 1=1
    """
    
    params = {"limit": limit}
    
    if mcp_name:
        query += " AND mcp_name = :mcp_name"
        params["mcp_name"] = mcp_name
    
    query += " ORDER BY scanned_at DESC LIMIT :limit"
    
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    return [
        {
            "id": row.id,
            "mcp_name": row.mcp_name,
            "mcp_url": row.mcp_url,
            "score": row.score,
            "findings": {
                "critical": row.critical_count,
                "high": row.high_count,
                "medium": row.medium_count,
                "low": row.low_count,
            },
            "scanned_at": row.scanned_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/scans/{scan_id}")
async def get_scan_detail(
    scan_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get detailed scan result."""
    result = await db.execute(
        text(
            "SELECT * FROM omni2.mcp_pt_scans WHERE id = :id"
        ),
        {"id": scan_id},
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    return {
        "id": row.id,
        "mcp_name": row.mcp_name,
        "mcp_url": row.mcp_url,
        "score": row.score,
        "scan_result": dict(row.scan_result),
        "scanned_at": row.scanned_at.isoformat(),
    }


@router.get("/mcps")
async def get_available_mcps(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    """Get list of available MCPs for scanning."""
    result = await db.execute(
        text(
            "SELECT name, url, is_active FROM omni2.mcp_servers ORDER BY name"
        )
    )
    rows = result.fetchall()
    
    return [
        {
            "name": row.name,
            "url": row.url,
            "is_active": row.is_active,
        }
        for row in rows
    ]


@router.delete("/scans/{scan_id}")
async def delete_scan(
    scan_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Delete a scan record."""
    await db.execute(
        text("DELETE FROM omni2.mcp_pt_scans WHERE id = :id"),
        {"id": scan_id},
    )
    await db.commit()
    
    return {"status": "success", "message": f"Scan {scan_id} deleted"}
