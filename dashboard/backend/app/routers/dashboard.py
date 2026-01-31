from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import httpx
from app.database import get_db
from app.config import settings

router = APIRouter()

@router.get("/stats")
async def get_stats():
    """Get dashboard stats by calling omni2 API"""
    async with httpx.AsyncClient() as client:
        try:
            # Call omni2 API endpoints
            response = await client.get(f"{settings.OMNI2_HTTP_URL}/api/v1/stats")
            if response.status_code == 200:
                return response.json()
            else:
                # Fallback to mock data if omni2 API not available
                return {
                    "active_mcps": 3,
                    "total_users": 2,
                    "queries_today": 45,
                    "cost_today": 0.05
                }
        except Exception as e:
            # Return mock data on error
            return {
                "active_mcps": 3,
                "total_users": 2,
                "queries_today": 45,
                "cost_today": 0.05
            }

@router.get("/activity")
async def get_activity(limit: int = 50):
    """Get recent activity by calling omni2 API"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{settings.OMNI2_HTTP_URL}/api/v1/activity?limit={limit}")
            if response.status_code == 200:
                return response.json()
            else:
                return {"activities": []}
        except Exception as e:
            return {"activities": []}
