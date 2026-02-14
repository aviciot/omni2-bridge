from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.services.flow_listener import get_flow_listener
from app.config import settings
from typing import Optional, Dict
import structlog
import httpx

logger = structlog.get_logger()
router = APIRouter()

# Use centralized Traefik URL - NEVER bypass Traefik!
OMNI2_URL = settings.omni2_api_url

def get_auth_headers(request: Request) -> Dict[str, str]:
    """Extract auth headers from request to forward to OMNI2"""
    headers = {}
    # Forward Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header:
        headers['Authorization'] = auth_header
    
    # Forward user context headers from auth service
    for header_name in ['X-User-Id', 'X-User-Username', 'X-User-Role']:
        header_value = request.headers.get(header_name)
        if header_value:
            headers[header_name] = header_value
    
    return headers

@router.websocket("/ws/flows/{user_id}")
async def flow_websocket(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time flow events"""
    await websocket.accept()
    logger.info(f"[FLOW-WS] ✓ WebSocket accepted for user {user_id}")
    listener = get_flow_listener()
    
    if not listener:
        logger.error(f"[FLOW-WS] ✗ Flow listener not initialized")
        await websocket.close(code=1011, reason="Flow listener not initialized")
        return
    
    await listener.connect(user_id, websocket)
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"[FLOW-WS] ✗ WebSocket disconnected for user {user_id}")
        await listener.disconnect(user_id, websocket)

@router.get("/flows/user/{user_id}")
async def get_user_flows(
    user_id: str,
    limit: int = Query(50, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Get historical flows for a user"""
    query = text("""
        SELECT flow_id, user_id, session_id, checkpoint, parent_id, 
               metadata, created_at
        FROM omni2.interaction_flows
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    
    result = await db.execute(query, {"user_id": user_id, "limit": limit})
    rows = result.fetchall()
    
    logger.info(f"[FLOW-API] ℹ Retrieved {len(rows)} flows for user {user_id}")
    
    return {
        "user_id": user_id,
        "flows": [
            {
                "flow_id": row[0],
                "user_id": row[1],
                "session_id": row[2],
                "checkpoint": row[3],
                "parent_id": row[4],
                "metadata": row[5],
                "created_at": row[6].isoformat() if row[6] else None
            }
            for row in rows
        ]
    }

@router.get("/flows/user/{user_id}/sessions")
async def get_user_sessions(
    user_id: int,
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get last N sessions for a user with flow counts"""
    query = text("""
        SELECT 
            session_id,
            created_at,
            completed_at,
            flow_data
        FROM omni2.interaction_flows
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    
    result = await db.execute(query, {"user_id": user_id, "limit": limit})
    rows = result.fetchall()
    
    sessions = [
        {
            "session_id": str(row[0]),
            "started_at": row[1].isoformat() if row[1] else None,
            "completed_at": row[2].isoformat() if row[2] else None,
            "event_count": len(row[3].get("events", [])) if row[3] else 0,
            "events": row[3].get("events", []) if row[3] else []
        }
        for row in rows
    ]
    
    return {"user_id": user_id, "sessions": sessions}

@router.get("/flows/session/{session_id}")
async def get_session_flows(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all flows for a session (builds tree structure)"""
    query = text("""
        SELECT flow_id, user_id, session_id, checkpoint, parent_id, 
               metadata, created_at
        FROM omni2.interaction_flows
        WHERE session_id = :session_id
        ORDER BY created_at ASC
    """)
    
    result = await db.execute(query, {"session_id": session_id})
    rows = result.fetchall()
    
    flows = [
        {
            "flow_id": row[0],
            "user_id": row[1],
            "session_id": row[2],
            "checkpoint": row[3],
            "parent_id": row[4],
            "metadata": row[5],
            "created_at": row[6].isoformat() if row[6] else None
        }
        for row in rows
    ]
    
    return {
        "session_id": session_id,
        "flows": flows,
        "tree": _build_tree(flows)
    }

def _build_tree(flows: list) -> dict:
    """Build tree structure from flat flow list"""
    flow_map = {f["flow_id"]: {**f, "children": []} for f in flows}
    root = None
    
    for flow in flows:
        if flow["parent_id"]:
            parent = flow_map.get(flow["parent_id"])
            if parent:
                parent["children"].append(flow_map[flow["flow_id"]])
        else:
            root = flow_map[flow["flow_id"]]
    
    return root or {}


@router.get("/monitoring/users")
async def get_users(request: Request):
    """Proxy to OMNI2 monitoring users endpoint via Traefik"""
    headers = get_auth_headers(request)
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{OMNI2_URL}/monitoring/users", headers=headers)
        return response.json()


@router.get("/monitoring/list")
async def list_monitored(request: Request):
    """Proxy to OMNI2 monitoring list endpoint via Traefik"""
    headers = get_auth_headers(request)
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{OMNI2_URL}/monitoring/list", headers=headers)
        return response.json()


@router.post("/monitoring/enable")
async def enable_monitoring(request: Request):
    """Proxy to OMNI2 monitoring enable endpoint via Traefik"""
    headers = get_auth_headers(request)
    payload = await request.json()
    
    # Ensure payload is in correct format for OMNI2
    if isinstance(payload, dict) and "user_ids" in payload:
        user_ids = payload["user_ids"]
    elif isinstance(payload, list):
        user_ids = payload
    else:
        user_ids = [payload] if isinstance(payload, int) else []
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OMNI2_URL}/monitoring/enable", 
            json=user_ids,  # Send as list directly
            headers=headers
        )
        return response.json()


@router.post("/monitoring/disable")
async def disable_monitoring(request: Request):
    """Proxy to OMNI2 monitoring disable endpoint via Traefik"""
    headers = get_auth_headers(request)
    payload = await request.json()
    
    # Ensure payload is in correct format for OMNI2
    if isinstance(payload, dict) and "user_ids" in payload:
        user_ids = payload["user_ids"]
    elif isinstance(payload, list):
        user_ids = payload
    else:
        user_ids = [payload] if isinstance(payload, int) else []
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OMNI2_URL}/monitoring/disable", 
            json=user_ids,  # Send as list directly
            headers=headers
        )
        return response.json()
