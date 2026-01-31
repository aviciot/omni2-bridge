"""
Circuit Breaker Configuration Router

Endpoints for managing circuit breaker settings and MCP auto-disable functionality.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone

from app.database import get_db
from app.models import MCPServer, Omni2Config
from app.services.circuit_breaker import get_circuit_breaker
from app.services.mcp_registry import get_mcp_registry
from app.utils.logger import logger

router = APIRouter(prefix="/circuit-breaker")


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration model."""
    enabled: bool = True
    failure_threshold: int = 5
    timeout_seconds: int = 60
    half_open_max_calls: int = 3
    max_failure_cycles: int = 3
    auto_disable_enabled: bool = True


@router.get("/config")
async def get_circuit_breaker_config(db: AsyncSession = Depends(get_db)):
    """Get current circuit breaker configuration."""
    try:
        result = await db.execute(
            select(Omni2Config).where(
                Omni2Config.config_key == 'circuit_breaker',
                Omni2Config.is_active == True
            )
        )
        config = result.scalar_one_or_none()
        
        if not config:
            return {
                "success": False,
                "error": "Circuit breaker configuration not found"
            }
        
        return {
            "success": True,
            "config": config.config_value
        }
    except Exception as e:
        logger.error("Failed to get circuit breaker config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config")
async def update_circuit_breaker_config(
    config: CircuitBreakerConfig,
    db: AsyncSession = Depends(get_db)
):
    """Update circuit breaker configuration."""
    try:
        result = await db.execute(
            select(Omni2Config).where(Omni2Config.config_key == 'circuit_breaker')
        )
        db_config = result.scalar_one_or_none()
        
        if not db_config:
            # Create new config
            db_config = Omni2Config(
                config_key='circuit_breaker',
                config_value=config.model_dump(),
                description='Circuit breaker configuration for MCP failure management',
                is_active=True
            )
            db.add(db_config)
        else:
            # Update existing
            db_config.config_value = config.model_dump()
            db_config.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        # Reload config in circuit breaker
        circuit_breaker = get_circuit_breaker()
        await circuit_breaker.load_config(db)
        
        logger.info("Circuit breaker config updated", config=config.model_dump())
        
        return {
            "success": True,
            "message": "Circuit breaker configuration updated successfully",
            "config": config.model_dump()
        }
    except Exception as e:
        logger.error("Failed to update circuit breaker config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcp/{server_id}/enable")
async def enable_mcp_server(
    server_id: int,
    reset_counters: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    Re-enable an auto-disabled MCP server.
    
    Args:
        server_id: MCP server ID
        reset_counters: Reset failure counters (default: True)
    """
    try:
        result = await db.execute(
            select(MCPServer).where(MCPServer.id == server_id)
        )
        mcp = result.scalar_one_or_none()
        
        if not mcp:
            raise HTTPException(status_code=404, detail=f"MCP server {server_id} not found")
        
        if not mcp.can_auto_enable:
            raise HTTPException(
                status_code=403,
                detail=f"MCP '{mcp.name}' cannot be auto-enabled. Manual intervention required."
            )
        
        # Re-enable the MCP
        mcp.status = 'active'
        mcp.health_status = 'unknown'
        mcp.auto_disabled_at = None
        mcp.auto_disabled_reason = None
        
        if reset_counters:
            mcp.failure_cycle_count = 0
            mcp.error_count = 0
            
            # Reset circuit breaker
            circuit_breaker = get_circuit_breaker()
            circuit_breaker.reset(mcp.name)
        
        await db.commit()
        
        # Trigger reload in registry
        registry = get_mcp_registry()
        await registry.load_mcp(mcp, db)
        
        logger.info(
            "MCP server re-enabled",
            server_id=server_id,
            name=mcp.name,
            reset_counters=reset_counters
        )
        
        return {
            "success": True,
            "message": f"MCP '{mcp.name}' re-enabled successfully",
            "server": {
                "id": mcp.id,
                "name": mcp.name,
                "status": mcp.status,
                "health_status": mcp.health_status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to enable MCP server", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/{server_id}/status")
async def get_mcp_circuit_status(
    server_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get circuit breaker status for specific MCP."""
    try:
        result = await db.execute(
            select(MCPServer).where(MCPServer.id == server_id)
        )
        mcp = result.scalar_one_or_none()
        
        if not mcp:
            raise HTTPException(status_code=404, detail=f"MCP server {server_id} not found")
        
        circuit_breaker = get_circuit_breaker()
        
        return {
            "success": True,
            "server": {
                "id": mcp.id,
                "name": mcp.name,
                "status": mcp.status,
                "health_status": mcp.health_status
            },
            "circuit_breaker": {
                "state": circuit_breaker.get_state(mcp.name),
                "failure_cycles": circuit_breaker.get_failure_cycles(mcp.name),
                "retry_after_seconds": circuit_breaker.get_retry_after(mcp.name),
                "is_open": circuit_breaker.is_open(mcp.name)
            },
            "auto_disable": {
                "failure_cycle_count": mcp.failure_cycle_count,
                "max_failure_cycles": mcp.max_failure_cycles,
                "auto_disabled_at": mcp.auto_disabled_at.isoformat() if mcp.auto_disabled_at else None,
                "auto_disabled_reason": mcp.auto_disabled_reason,
                "can_auto_enable": mcp.can_auto_enable
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get MCP circuit status", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcp/{server_id}/reset")
async def reset_mcp_circuit_breaker(
    server_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Manually reset circuit breaker for MCP (without changing status)."""
    try:
        result = await db.execute(
            select(MCPServer).where(MCPServer.id == server_id)
        )
        mcp = result.scalar_one_or_none()
        
        if not mcp:
            raise HTTPException(status_code=404, detail=f"MCP server {server_id} not found")
        
        # Reset circuit breaker
        circuit_breaker = get_circuit_breaker()
        circuit_breaker.reset(mcp.name)
        
        # Reset database counters
        mcp.failure_cycle_count = 0
        mcp.error_count = 0
        await db.commit()
        
        logger.info("Circuit breaker reset", server_id=server_id, name=mcp.name)
        
        return {
            "success": True,
            "message": f"Circuit breaker reset for '{mcp.name}'",
            "circuit_state": circuit_breaker.get_state(mcp.name)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to reset circuit breaker", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
