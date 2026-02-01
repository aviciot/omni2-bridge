from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.services.flow_listener import get_flow_listener
from typing import Optional
import structlog
import httpx
import os

logger = structlog.get_logger()
router = APIRouter()

OMNI2_URL = os.getenv("OMNI2_URL", "http://omni2:8000")

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
async def get_users():
    """Proxy to OMNI2 monitoring users endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{OMNI2_URL}/api/v1/monitoring/users")
        return response.json()


@router.get("/monitoring/list")
async def list_monitored():
    """Proxy to OMNI2 monitoring list endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{OMNI2_URL}/api/v1/monitoring/list")
        return response.json()


@router.post("/monitoring/enable")
async def enable_monitoring(payload: dict):
    """Proxy to OMNI2 monitoring enable endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{OMNI2_URL}/api/v1/monitoring/enable", json=payload)
        return response.json()


@router.post("/monitoring/disable")
async def disable_monitoring(payload: dict):
    """Proxy to OMNI2 monitoring disable endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{OMNI2_URL}/api/v1/monitoring/disable", json=payload)
        return response.json()
