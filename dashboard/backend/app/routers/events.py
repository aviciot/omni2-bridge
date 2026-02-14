from fastapi import APIRouter, Header, HTTPException
import httpx
import structlog
from app.config import settings

router = APIRouter(prefix="/events")
logger = structlog.get_logger()

# Use centralized Traefik URL - NEVER bypass Traefik!
OMNI2_URL = f"{settings.omni2_api_url}/events"

@router.get("/websocket/debug")
async def websocket_debug(authorization: str = Header(None)):
    """Proxy WebSocket debug info from OMNI2"""
    try:
        headers = {"Authorization": authorization} if authorization else {}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OMNI2_URL}/websocket/debug", headers=headers, timeout=10.0)
            return response.json()
    except Exception as e:
        logger.error("Failed to fetch WebSocket debug info", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/broadcast")
async def test_broadcast(authorization: str = Header(None)):
    """Proxy test broadcast to OMNI2"""
    try:
        headers = {"Authorization": authorization} if authorization else {}
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{OMNI2_URL}/test/broadcast", headers=headers, timeout=10.0)
            return response.json()
    except Exception as e:
        logger.error("Failed to trigger test broadcast", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metadata")
async def get_metadata(authorization: str = Header(None)):
    """Proxy event metadata from OMNI2"""
    try:
        headers = {"Authorization": authorization} if authorization else {}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OMNI2_URL}/metadata", headers=headers, timeout=10.0)
            return response.json()
    except Exception as e:
        logger.error("Failed to fetch event metadata", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
