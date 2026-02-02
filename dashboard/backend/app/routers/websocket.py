from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import asyncio
import websockets
from typing import Optional
import structlog
from app.config import settings
from app.database import get_db
from sqlalchemy import text

router = APIRouter()
logger = structlog.get_logger()

# Logging configuration
verbose_logging = False

async def load_logging_config():
    """Load logging configuration from database"""
    global verbose_logging
    try:
        async for db in get_db():
            result = await db.execute(text(
                "SELECT value FROM omni2_dashboard.dashboard_config WHERE key = 'logging'"
            ))
            row = result.fetchone()
            if row and row[0]:
                verbose_logging = row[0].get('websocket_verbose', False)
            break
    except Exception as e:
        logger.error("Failed to load logging config", error=str(e))

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    await websocket.accept()
    
    if not token:
        logger.warning("No token provided, closing connection")
        await websocket.close(code=1008, reason="No token provided")
        return
    
    # Load logging config on first connection
    await load_logging_config()
    
    try:
        omni2_url = settings.OMNI2_WS_URL
        headers = {"Authorization": f"Bearer {token}"}
        
        async with websockets.connect(omni2_url, additional_headers=headers) as omni2_ws:
            if verbose_logging:
                logger.info("Connected to OMNI2 WebSocket")
            
            async def forward_from_omni2():
                try:
                    async for message in omni2_ws:
                        if verbose_logging and "ping" not in message.lower():
                            logger.debug("Forwarding from OMNI2", message_preview=message[:100])
                        await websocket.send_text(message)
                except Exception as e:
                    logger.error("Error forwarding from OMNI2", error=str(e))
                    raise
            
            async def forward_to_omni2():
                try:
                    while True:
                        data = await websocket.receive_text()
                        if verbose_logging and "ping" not in data.lower():
                            logger.debug("Forwarding to OMNI2", message_preview=data[:100])
                        await omni2_ws.send(data)
                except Exception as e:
                    logger.error("Error forwarding to OMNI2", error=str(e))
                    raise
            
            await asyncio.gather(
                forward_from_omni2(),
                forward_to_omni2(),
                return_exceptions=True
            )
    except websockets.exceptions.WebSocketException as e:
        logger.error("WebSocket connection error", error=str(e))
        try:
            await websocket.close(code=1011, reason=f"Connection error: {str(e)[:50]}")
        except:
            pass
    except Exception as e:
        logger.error("Unexpected WebSocket error", error=str(e))
        try:
            await websocket.close(code=1011, reason=str(e)[:100])
        except:
            pass

@router.websocket("/ws/chat")
async def chat_websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    logger.info("[WS-CHAT-PROXY] 🔌 New WebSocket chat connection request")
    await websocket.accept()
    
    if not token:
        logger.warning("[WS-CHAT-PROXY] ❌ No token provided, closing connection")
        await websocket.close(code=1008, reason="No token provided")
        return
    
    logger.info(f"[WS-CHAT-PROXY] ✓ Token received: {token[:20]}...")
    await load_logging_config()
    
    try:
        # Connect to OMNI2 /ws/chat via Traefik
        omni2_chat_url = f"{settings.OMNI2_WS_URL}/chat"
        headers = {"Authorization": f"Bearer {token}"}
        
        logger.info(f"[WS-CHAT-PROXY] 🔗 Connecting to OMNI2: {omni2_chat_url}")
        async with websockets.connect(omni2_chat_url, additional_headers=headers) as omni2_ws:
            logger.info("[WS-CHAT-PROXY] ✅ Connected to OMNI2 Chat WebSocket")
            
            async def forward_from_omni2():
                try:
                    async for message in omni2_ws:
                        # Forward complete message (don't split into frames)
                        await websocket.send_text(message)
                except Exception as e:
                    logger.error("Error forwarding from OMNI2 chat", error=str(e))
                    raise
            
            async def forward_to_omni2():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await omni2_ws.send(data)
                except Exception as e:
                    logger.error("Error forwarding to OMNI2 chat", error=str(e))
                    raise
            
            await asyncio.gather(
                forward_from_omni2(),
                forward_to_omni2(),
                return_exceptions=True
            )
            logger.info("[WS-CHAT-PROXY] 🔌 WebSocket chat connection closed")
    except websockets.exceptions.WebSocketException as e:
        logger.error(f"[WS-CHAT-PROXY] ❌ WebSocket error: {str(e)}")
        try:
            await websocket.close(code=1011, reason=f"Connection error: {str(e)[:50]}")
        except:
            pass
    except Exception as e:
        logger.error(f"[WS-CHAT-PROXY] ❌ Unexpected error: {str(e)}")
        try:
            await websocket.close(code=1011, reason=str(e)[:100])
        except:
            pass
