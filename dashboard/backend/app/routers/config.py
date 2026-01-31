from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from pydantic import BaseModel
from typing import Any

router = APIRouter()

class ConfigUpdate(BaseModel):
    key: str
    value: Any

@router.get("/config")
async def get_dashboard_config(db: AsyncSession = Depends(get_db)):
    """Get dashboard configuration from database"""
    try:
        result = await db.execute(
            text("SELECT key, value FROM omni2_dashboard.dashboard_config")
        )
        config_rows = result.fetchall()
        
        config = {}
        for row in config_rows:
            config[row.key] = row.value
            
        return {"success": True, "config": config}
    except Exception as e:
        return {"success": False, "config": {}, "error": str(e)}

@router.get("/config/dev_features")
async def get_dev_features(db: AsyncSession = Depends(get_db)):
    """Get dev_features configuration"""
    try:
        result = await db.execute(
            text("SELECT value FROM omni2_dashboard.dashboard_config WHERE key = 'dev_features'")
        )
        row = result.fetchone()
        
        if row:
            return row.value
        else:
            return {"websocket_debug": False, "quick_login": False}
    except Exception as e:
        return {"websocket_debug": False, "quick_login": False}

@router.put("/config")
async def update_config(config: ConfigUpdate, db: AsyncSession = Depends(get_db)):
    """Update dashboard configuration"""
    try:
        import json
        
        # Convert value to JSON string for JSONB
        json_value = json.dumps(config.value)
        
        # Check if key exists
        result = await db.execute(
            text("SELECT key FROM omni2_dashboard.dashboard_config WHERE key = :key"),
            {"key": config.key}
        )
        exists = result.fetchone()
        
        if exists:
            # Update existing - use cast instead of :: in parameter
            await db.execute(
                text("UPDATE omni2_dashboard.dashboard_config SET value = CAST(:value AS jsonb) WHERE key = :key"),
                {"key": config.key, "value": json_value}
            )
        else:
            # Insert new
            await db.execute(
                text("INSERT INTO omni2_dashboard.dashboard_config (key, value) VALUES (:key, CAST(:value AS jsonb))"),
                {"key": config.key, "value": json_value}
            )
        
        await db.commit()
        return {"success": True, "message": f"Configuration '{config.key}' updated successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))