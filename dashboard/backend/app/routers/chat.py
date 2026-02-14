"""
Chat Router - Proxy to OMNI2 chat endpoint
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
import httpx
import logging
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    user_id: str


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    authorization: str = Header(None)
):
    """Proxy streaming chat request to OMNI2 using SSE"""
    from fastapi.responses import StreamingResponse
    
    print(f"[CHAT] === INCOMING REQUEST ===")
    print(f"[CHAT] user_id: {request.user_id}")
    print(f"[CHAT] message: {request.message[:50]}")
    print(f"[CHAT] authorization header: {authorization}")
    print(f"[CHAT] authorization type: {type(authorization)}")
    print(f"[CHAT] authorization length: {len(authorization) if authorization else 0}")
    
    token = authorization.replace("Bearer ", "") if authorization else None
    print(f"[CHAT] token after strip: {token[:30] if token else 'NONE'}...")
    
    if not token:
        print("[CHAT] ERROR: No token provided")
        raise HTTPException(status_code=401, detail="No token provided")
    
    async def event_stream():
        try:
            # Use centralized Traefik URL - NEVER bypass Traefik!
            url = f"{settings.omni2_api_url}/chat/ask/stream"
            print(f"[CHAT] Connecting to: {url}")
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}"
                }
                print(f"[CHAT] Sending headers: {headers}")
                print(f"[CHAT] Sending payload: user_id={request.user_id}, message={request.message[:30]}...")
                
                async with client.stream(
                    "POST",
                    url,
                    json={
                        "message": request.message,
                        "user_id": request.user_id
                    },
                    headers=headers
                ) as response:
                    print(f"[CHAT] OMNI2 response status: {response.status_code}")
                    print(f"[CHAT] OMNI2 response headers: {dict(response.headers)}")
                    if response.status_code != 200:
                        error_body = await response.aread()
                        print(f"[CHAT] ERROR: OMNI2 returned {response.status_code}: {error_body}")
                        error_msg = f"event: error\ndata: {{\"error\": \"OMNI2 returned {response.status_code}\"}}\n\n"
                        yield error_msg.encode()
                        return
                    
                    logger.info(f"[CHAT] Starting to stream response from OMNI2")
                    async for chunk in response.aiter_bytes():
                        yield chunk
                    logger.info(f"[CHAT] Finished streaming response")
        except Exception as e:
            logger.error(f"Chat stream error: {str(e)}")
            error_msg = f"event: error\ndata: {{\"error\": \"{str(e)}\"}}\n\n"
            yield error_msg.encode()
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
