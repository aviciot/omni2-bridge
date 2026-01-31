from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/charts", tags=["charts"])

@router.get("/queries")
async def get_queries_chart():
    """Hourly query count (last 24h) from omni2 API"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{settings.OMNI2_HTTP_URL}/api/v1/charts/queries")
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return {"data": []}

@router.get("/cost")
async def get_cost_chart():
    """Cost by MCP (today) from omni2 API"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{settings.OMNI2_HTTP_URL}/api/v1/charts/cost")
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return {"data": []}

@router.get("/response-times")
async def get_response_times_chart():
    """Response time percentiles from omni2 API"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{settings.OMNI2_HTTP_URL}/api/v1/charts/response-times")
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return {"data": []}

@router.get("/errors")
async def get_errors_chart():
    """Error rate by MCP from omni2 API"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{settings.OMNI2_HTTP_URL}/api/v1/charts/errors")
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return {"data": []}
