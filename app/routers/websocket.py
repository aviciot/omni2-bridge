"""
WebSocket Router - Real-time MCP Status Updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Header
from app.services.websocket_broadcaster import get_websocket_broadcaster
from app.services.event_registry import get_event_metadata
from app.utils.logger import logger
import json

router = APIRouter()

logger = logger.bind(service="WebSocket-API")

# Logging configuration (loaded from database)
verbose_logging = False


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    x_user_id: str = Header(None),
    x_user_username: str = Header(None),
    x_user_role: str = Header(None)
):
    """
    WebSocket endpoint for real-time MCP status updates.
    
    Authentication: Handled by Traefik ForwardAuth middleware
    Headers injected by Traefik: X-User-Id, X-User-Username, X-User-Role
    """
    await websocket.accept()
    
    # Check if Traefik injected user headers (auth already validated)
    if not x_user_id or not x_user_username:
        await websocket.close(code=1008, reason="Authentication required")
        logger.warning("WebSocket rejected: No auth headers")
        return
    
    user_id = x_user_username
    user_role = x_user_role or "read_only"
    
    # Check permissions
    allowed_roles = ["admin", "developer", "dba", "super_admin"]
    if user_role not in allowed_roles:
        await websocket.close(code=1008, reason=f"Insufficient permissions")
        logger.warning("WebSocket rejected: insufficient permissions", user=user_id, role=user_role)
        return
    
    conn_id = None
    broadcaster = get_websocket_broadcaster()
    try:
        conn_id = await broadcaster.connect(websocket, user_id, user_role)
        
        while True:
            try:
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    action = message.get("action")
                    
                    if action == "subscribe":
                        sub_id = await broadcaster.subscribe(
                            conn_id=conn_id,
                            event_types=message.get("event_types", []),
                            filters=message.get("filters", {})
                        )
                        await websocket.send_json({
                            "type": "subscribed",
                            "subscription_id": sub_id,
                            "event_types": message.get("event_types", []),
                            "filters": message.get("filters", {})
                        })
                    
                    elif action == "unsubscribe":
                        sub_id = message.get("subscription_id")
                        await broadcaster.unsubscribe(conn_id, sub_id)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "subscription_id": sub_id
                        })
                    
                    elif action == "get_metadata":
                        metadata = get_event_metadata()
                        await websocket.send_json({
                            "type": "metadata",
                            "data": metadata
                        })
                    
                    elif action == "ping":
                        await websocket.send_text("pong")
                        
                except json.JSONDecodeError:
                    if data == "ping":
                        await websocket.send_text("pong")
                    
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error("WebSocket error", conn_id=conn_id, error=str(e), error_type=type(e).__name__)
    finally:
        if conn_id:
            await broadcaster.disconnect(conn_id)
