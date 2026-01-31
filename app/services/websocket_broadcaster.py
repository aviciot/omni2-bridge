"""
WebSocket Broadcaster Service - Real-time MCP Status Updates

Provides real-time updates to dashboard clients about MCP status changes,
health events, and system metrics with user permission filtering.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import logger
from app.database import AsyncSessionLocal
from app.services.subscription_manager import SubscriptionManager

# Bind service name to logger for this module
logger = logger.bind(service="WebSocket")


class WebSocketConnection:
    """Individual WebSocket connection with user context"""
    
    def __init__(self, websocket: WebSocket, user_id: str, user_role: str):
        self.websocket = websocket
        self.user_id = user_id
        self.user_role = user_role
        self.connected_at = time.time()
        self.last_ping = time.time()


class WebSocketBroadcaster:
    """Manages WebSocket connections and broadcasts MCP updates"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.subscription_manager = SubscriptionManager()
        self.running = False
        self.broadcaster_task: Optional[asyncio.Task] = None
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.verbose_logging = False  # Default to quiet
        
    async def load_logging_config(self, db: AsyncSession):
        """Load logging configuration from database"""
        try:
            from sqlalchemy import text
            result = await db.execute(text(
                "SELECT value FROM omni2_dashboard.dashboard_config WHERE key = 'logging'"
            ))
            row = result.fetchone()
            if row and row[0]:
                self.verbose_logging = row[0].get('websocket_verbose', False)
        except Exception as e:
            logger.error("Failed to load logging config", error=str(e))
        
    async def start(self):
        """Start the WebSocket broadcaster"""
        if self.running:
            return
            
        self.running = True
        self.broadcaster_task = asyncio.create_task(self._broadcaster_loop())
        logger.info("WebSocket Broadcaster started")
        
    async def stop(self):
        """Stop the WebSocket broadcaster"""
        self.running = False
        
        if self.broadcaster_task:
            self.broadcaster_task.cancel()
            
        # Close all connections
        for conn_id in list(self.connections.keys()):
            await self._disconnect(conn_id)
            
        logger.info("WebSocket Broadcaster stopped")
        
    async def connect(self, websocket: WebSocket, user_id: str, user_role: str) -> str:
        """Accept new WebSocket connection"""
        # Don't accept here - already accepted in endpoint
        
        conn_id = f"{user_id}_{int(time.time())}"
        self.connections[conn_id] = WebSocketConnection(websocket, user_id, user_role)
        
        if self.verbose_logging:
            logger.info(
                "WebSocket connected",
                user_id=user_id,
                conn_id=conn_id,
                total_connections=len(self.connections)
            )
        
        # Send initial status
        await self._send_initial_status(conn_id)
        
        return conn_id
        
    async def disconnect(self, conn_id: str):
        """Handle WebSocket disconnection"""
        # Remove all subscriptions
        self.subscription_manager.remove_all_subscriptions(conn_id)
        await self._disconnect(conn_id)
        
    async def _disconnect(self, conn_id: str):
        """Internal disconnect logic"""
        if conn_id in self.connections:
            conn = self.connections[conn_id]
            try:
                await conn.websocket.close()
            except:
                pass
            del self.connections[conn_id]
            if self.verbose_logging:
                logger.info("WebSocket disconnected", conn_id=conn_id)
            
    async def subscribe(self, conn_id: str, event_types: List[str], filters: Dict) -> str:
        """Create event subscription"""
        return self.subscription_manager.create_subscription(conn_id, event_types, filters)
    
    async def unsubscribe(self, conn_id: str, sub_id: str) -> bool:
        """Remove event subscription"""
        return self.subscription_manager.remove_subscription(conn_id, sub_id)
    
    async def broadcast_event(self, event_type: str, event_data: Dict):
        """Broadcast event to subscribed connections only"""
        message = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": event_data
        }
        
        # Log based on verbosity setting
        if self.verbose_logging:
            logger.info(
                "Broadcasting event",
                event_type=event_type,
                total_connections=len(self.connections)
            )
        elif event_type in ['mcp_auto_disabled', 'circuit_breaker_state']:
            logger.warning(
                "Critical event broadcast",
                event_type=event_type,
                mcp_name=event_data.get('mcp_name')
            )
        
        # Get connections that match this event
        matching_conns = self.subscription_manager.get_matching_connections(event_type, event_data)
        
        if self.verbose_logging:
            logger.info(
                "Matching connections found",
                event_type=event_type,
                matching_count=len(matching_conns)
            )
        
        # Send to matching connections
        disconnected = []
        for conn_id in matching_conns:
            if conn_id in self.connections:
                conn = self.connections[conn_id]
                try:
                    await conn.websocket.send_text(json.dumps(message))
                    if self.verbose_logging:
                        logger.info("Event sent to connection", conn_id=conn_id, event_type=event_type)
                except WebSocketDisconnect:
                    disconnected.append(conn_id)
                except Exception as e:
                    logger.error("WebSocket send failed", conn_id=conn_id, error=str(e))
                    disconnected.append(conn_id)
        
        # Clean up disconnected
        for conn_id in disconnected:
            await self._disconnect(conn_id)
    
    async def broadcast_mcp_status(self, mcp_name: str, status: str, metadata: Dict = None):
        """Broadcast MCP status change (legacy method - now uses broadcast_event)"""
        await self.broadcast_event("mcp_status_change", {
            "mcp_name": mcp_name,
            "new_status": status,
            "old_status": metadata.get("old_status") if metadata else None,
            "reason": metadata.get("reason") if metadata else None,
            "severity": "error" if status == "inactive" else "info"
        })
        
    async def broadcast_health_event(self, mcp_name: str, event_type: str, data: Dict = None):
        """Broadcast health event to connected clients"""
        message = {
            "type": "health_event",
            "timestamp": datetime.utcnow().isoformat(),
            "mcp_name": mcp_name,
            "event_type": event_type,
            "data": data or {}
        }
        
        await self.message_queue.put(message)
        
    async def broadcast_system_metrics(self, metrics: Dict):
        """Broadcast system metrics to connected clients"""
        message = {
            "type": "system_metrics",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics
        }
        
        await self.message_queue.put(message)
        
    async def _broadcaster_loop(self):
        """Main broadcaster loop"""
        while self.running:
            try:
                # Process message queue
                try:
                    message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                    await self._broadcast_message(message)
                except asyncio.TimeoutError:
                    pass
                    
                # Cleanup stale connections
                await self._cleanup_stale_connections()
                
                # Send periodic ping
                await self._send_periodic_ping()
                
            except Exception as e:
                logger.error("WebSocket broadcaster error", error=str(e))
                await asyncio.sleep(1)
                
    async def _broadcast_message(self, message: Dict):
        """Broadcast message to all eligible connections"""
        if not self.connections:
            return
            
        # Filter connections based on permissions
        eligible_connections = self._filter_connections_by_permission(message)
        
        # Send to all eligible connections
        disconnected = []
        for conn_id, conn in eligible_connections.items():
            try:
                await conn.websocket.send_text(json.dumps(message))
            except WebSocketDisconnect:
                disconnected.append(conn_id)
            except Exception as e:
                logger.warning("WebSocket send failed", conn_id=conn_id, error=str(e))
                disconnected.append(conn_id)
                
        # Clean up disconnected connections
        for conn_id in disconnected:
            await self._disconnect(conn_id)
            
    def _filter_connections_by_permission(self, message: Dict) -> Dict[str, WebSocketConnection]:
        """Filter connections based on user permissions"""
        # For now, all authenticated users can see all MCP status
        # TODO: Implement role-based filtering
        return self.connections.copy()
        
    async def _send_initial_status(self, conn_id: str):
        """Send initial MCP status to new connection"""
        try:
            if AsyncSessionLocal is None:
                logger.warning("⚠️ Database not initialized, skipping initial status")
                return
                
            async with AsyncSessionLocal() as db:
                from sqlalchemy import select, text
                
                # Get current MCP status
                result = await db.execute(text("""
                    SELECT name, health_status, circuit_state, last_health_check
                    FROM omni2.mcp_servers 
                    WHERE status = 'active'
                """))
                
                mcps = []
                for row in result.fetchall():
                    mcps.append({
                        "name": row[0],
                        "health_status": row[1],
                        "circuit_state": row[2],
                        "last_health_check": row[3].isoformat() if row[3] else None
                    })
                
                message = {
                    "type": "initial_status",
                    "timestamp": datetime.utcnow().isoformat(),
                    "mcps": mcps
                }
                
                conn = self.connections.get(conn_id)
                if conn:
                    await conn.websocket.send_text(json.dumps(message))
                    
        except Exception as e:
            logger.error("Failed to send initial status", conn_id=conn_id, error=str(e))
            
    async def _cleanup_stale_connections(self):
        """Remove stale connections (no ping for 5 minutes)"""
        now = time.time()
        stale_connections = []
        
        for conn_id, conn in self.connections.items():
            if now - conn.last_ping > 300:  # 5 minutes
                stale_connections.append(conn_id)
                
        for conn_id in stale_connections:
            await self._disconnect(conn_id)
            
    async def _send_periodic_ping(self):
        """Send periodic ping to maintain connections"""
        if not self.connections:
            return
            
        ping_message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        disconnected = []
        for conn_id, conn in self.connections.items():
            try:
                await conn.websocket.send_text(json.dumps(ping_message))
                conn.last_ping = time.time()
            except:
                disconnected.append(conn_id)
                
        for conn_id in disconnected:
            await self._disconnect(conn_id)


# Global broadcaster instance
_broadcaster: Optional[WebSocketBroadcaster] = None


def get_websocket_broadcaster() -> WebSocketBroadcaster:
    """Get global WebSocket broadcaster instance"""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = WebSocketBroadcaster()
    return _broadcaster


async def start_websocket_broadcaster():
    """Start the global WebSocket broadcaster"""
    broadcaster = get_websocket_broadcaster()
    await broadcaster.start()


async def stop_websocket_broadcaster():
    """Stop the global WebSocket broadcaster"""
    broadcaster = get_websocket_broadcaster()
    await broadcaster.stop()