"""
Events API Router - Event metadata and subscription management
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
import asyncio

from app.database import get_db
from app.services.event_registry import get_event_metadata
from app.services.websocket_broadcaster import get_websocket_broadcaster
from app.models import MCPServer

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("/metadata")
async def get_events_metadata():
    """
    Get event metadata (categories, types, filterable fields)
    
    Returns event registry information for building subscription UI
    """
    return get_event_metadata()


@router.get("/mcp-list")
async def get_mcp_list(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Get list of MCP servers for filter dropdowns
    
    Returns list of MCP names and IDs for multiselect filters
    """
    result = await db.execute(
        select(MCPServer.id, MCPServer.name, MCPServer.status)
        .order_by(MCPServer.name)
    )
    
    mcps = []
    for row in result:
        mcps.append({
            "id": row.id,
            "name": row.name,
            "status": row.status
        })
    
    return mcps


@router.get("/websocket/debug")
async def websocket_debug():
    """
    Get WebSocket debug information
    
    Returns active connections, subscriptions, and stats
    """
    broadcaster = get_websocket_broadcaster()
    
    connections = []
    for conn_id, conn in broadcaster.connections.items():
        subs = broadcaster.subscription_manager.get_subscriptions(conn_id)
        connections.append({
            "conn_id": conn_id,
            "user_id": conn.user_id,
            "user_role": conn.user_role,
            "connected_at": conn.connected_at,
            "subscriptions": len(subs),
            "subscription_details": [
                {
                    "id": sub.id,
                    "event_types": sub.event_types,
                    "filters": sub.filters
                }
                for sub in subs
            ]
        })
    
    return {
        "active_connections": len(broadcaster.connections),
        "connections": connections,
        "subscription_stats": broadcaster.subscription_manager.get_stats()
    }


@router.post("/test/broadcast")
async def test_broadcast_events():
    """
    Broadcast test events for WebSocket testing
    
    Sends all event types to connected WebSocket clients
    """
    broadcaster = get_websocket_broadcaster()
    mcp_name = "Dockers Controller"
    
    # Broadcast events in background
    async def send_events():
        await broadcaster.broadcast_event(
            event_type="mcp_status_change",
            event_data={
                "mcp_name": mcp_name,
                "old_status": "healthy",
                "new_status": "unhealthy",
                "reason": "Test event",
                "severity": "high"
            }
        )
        await asyncio.sleep(0.5)
        
        await broadcaster.broadcast_event(
            event_type="circuit_breaker_state",
            event_data={
                "mcp_name": mcp_name,
                "old_state": "CLOSED",
                "new_state": "OPEN",
                "reason": "Test event",
                "severity": "critical"
            }
        )
    
    asyncio.create_task(send_events())
    
    return {"status": "broadcasting", "message": "Test events queued for broadcast"}
