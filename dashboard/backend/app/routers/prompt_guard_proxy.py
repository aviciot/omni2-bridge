from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.config import settings
import httpx

router = APIRouter(prefix="/api/v1/prompt-guard")

@router.get("/config")
async def get_config(request: Request, db: AsyncSession = Depends(get_db)):
    headers = {"Authorization": request.headers.get("Authorization", "")}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.TRAEFIK_BASE_URL}/api/v1/prompt-guard/config", headers=headers)
        return response.json()

@router.put("/config")
async def update_config(config: dict, request: Request, db: AsyncSession = Depends(get_db)):
    headers = {"Authorization": request.headers.get("Authorization", "")}
    async with httpx.AsyncClient() as client:
        response = await client.put(f"{settings.TRAEFIK_BASE_URL}/api/v1/prompt-guard/config", json=config, headers=headers)
        return response.json()

@router.post("/config/{action}")
async def toggle_config(action: str, request: Request, db: AsyncSession = Depends(get_db)):
    headers = {"Authorization": request.headers.get("Authorization", "")}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{settings.TRAEFIK_BASE_URL}/api/v1/prompt-guard/config/{action}", headers=headers)
        return response.json()

@router.get("/roles")
async def get_roles(request: Request, db: AsyncSession = Depends(get_db)):
    headers = {"Authorization": request.headers.get("Authorization", "")}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.TRAEFIK_BASE_URL}/api/v1/prompt-guard/roles", headers=headers)
        return response.json()
