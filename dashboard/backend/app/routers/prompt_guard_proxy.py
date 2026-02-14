from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
import httpx

router = APIRouter(prefix="/api/v1/prompt-guard")

OMNI2_URL = "http://omni2-bridge:8000"

@router.get("/config")
async def get_config(db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{OMNI2_URL}/api/v1/prompt-guard/config")
        return response.json()

@router.put("/config")
async def update_config(config: dict, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        response = await client.put(f"{OMNI2_URL}/api/v1/prompt-guard/config", json=config)
        return response.json()

@router.post("/config/{action}")
async def toggle_config(action: str, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{OMNI2_URL}/api/v1/prompt-guard/config/{action}")
        return response.json()

@router.get("/roles")
async def get_roles(db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{OMNI2_URL}/api/v1/prompt-guard/roles")
        return response.json()
