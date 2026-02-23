from fastapi import APIRouter, Request
from app.config import settings
import httpx

router = APIRouter(prefix="/api/v1/monitoring")


@router.get("/components")
async def get_component_health(request: Request):
    """Proxy to omni2-bridge: returns health status of all Redis listener components."""
    headers = {"Authorization": request.headers.get("Authorization", "")}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.TRAEFIK_BASE_URL}/api/v1/monitoring/components",
            headers=headers,
        )
        return response.json()
