"""
WebSocket Connection Manager

Tracks active WebSocket connections and provides mechanisms for
instant disconnection when users are blocked or need to be disconnected.
"""

import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket
from app.utils.logger import logger
from redis.asyncio import Redis


class WebSocketConnectionManager:
    """Manages active WebSocket connections and handles real-time disconnections"""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        # user_id -> Set[WebSocket]
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.listener_task = None
        self._shutdown = False

    async def connect(self, user_id: int, websocket: WebSocket):
        """Register a WebSocket connection for a user"""
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"[WS-MANAGER] ✓ User {user_id} connected (total: {len(self.active_connections[user_id])} connections)")

    async def disconnect(self, user_id: int, websocket: WebSocket):
        """Unregister a WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                logger.info(f"[WS-MANAGER] ✗ User {user_id} fully disconnected")
            else:
                logger.info(f"[WS-MANAGER] ✗ User {user_id} connection closed (remaining: {len(self.active_connections[user_id])})")

    async def disconnect_user(self, user_id: int, custom_message: str = None):
        """
        Disconnect all WebSocket connections for a specific user.
        Used when user is blocked or needs to be forcefully disconnected.

        Args:
            user_id: User ID to disconnect
            custom_message: Custom message to send before closing connection
        """
        if user_id not in self.active_connections:
            logger.debug(f"[WS-MANAGER] User {user_id} has no active connections")
            return

        connections = self.active_connections[user_id].copy()
        logger.warning(f"[WS-MANAGER] 🚫 Disconnecting user {user_id} ({len(connections)} connections)")

        for ws in connections:
            try:
                # Send custom block message before closing
                if custom_message:
                    await ws.send_json({
                        "type": "blocked",
                        "message": custom_message
                    })
                    await asyncio.sleep(0.5)  # Give time for message to be received

                # Close the connection
                await ws.close(code=1008, reason="User blocked by administrator")
                logger.info(f"[WS-MANAGER] ✓ Closed WebSocket for user {user_id}")
            except Exception as e:
                logger.error(f"[WS-MANAGER] ✗ Error closing WebSocket for user {user_id}: {e}")

        # Clean up
        if user_id in self.active_connections:
            del self.active_connections[user_id]

        logger.info(f"[WS-MANAGER] ✓ User {user_id} fully disconnected ({len(connections)} connections closed)")

    async def start_listener(self):
        """Start listening for block events from Redis Pub/Sub"""
        if self.listener_task is not None:
            logger.warning("[WS-MANAGER] Listener already running")
            return

        self.listener_task = asyncio.create_task(self._listen_for_block_events())
        logger.info("[WS-MANAGER] ✓ Block event listener started")

    async def stop_listener(self):
        """Stop the block event listener"""
        if self.listener_task:
            self._shutdown = True
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
            logger.info("[WS-MANAGER] ✓ Block event listener stopped")

    async def _listen_for_block_events(self):
        """Background task that listens for user block events"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe("user_blocked")

        logger.info("[WS-MANAGER] 🎧 Listening for user block events on 'user_blocked' channel")

        try:
            async for message in pubsub.listen():
                if self._shutdown:
                    break

                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        user_id = data.get("user_id")
                        blocked_services = data.get("blocked_services", [])
                        custom_message = data.get("custom_message")

                        # Only disconnect if 'chat' is in blocked_services
                        if "chat" in blocked_services:
                            logger.warning(f"[WS-MANAGER] 🚫 Received block event for user {user_id} (chat blocked)")
                            await self.disconnect_user(user_id, custom_message)
                        else:
                            logger.info(f"[WS-MANAGER] ℹ️ Block event for user {user_id} (chat not blocked, ignoring)")

                    except json.JSONDecodeError as e:
                        logger.error(f"[WS-MANAGER] ✗ Failed to parse block event: {e}")
                    except Exception as e:
                        logger.error(f"[WS-MANAGER] ✗ Error handling block event: {e}")

        except asyncio.CancelledError:
            logger.info("[WS-MANAGER] 🔇 Block event listener cancelled")
            await pubsub.unsubscribe()
            await pubsub.close()
            raise
        except Exception as e:
            logger.error(f"[WS-MANAGER] ✗ Fatal error in block event listener: {e}")
            await pubsub.unsubscribe()
            await pubsub.close()

    def get_active_users(self) -> list[int]:
        """Get list of users with active connections"""
        return list(self.active_connections.keys())

    def get_connection_count(self, user_id: int) -> int:
        """Get number of active connections for a user"""
        return len(self.active_connections.get(user_id, set()))

    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())


# Global instance
ws_manager: WebSocketConnectionManager = None


def get_ws_manager() -> WebSocketConnectionManager:
    """Dependency injection for WebSocketConnectionManager"""
    return ws_manager


async def init_ws_manager(redis_client: Redis):
    """Initialize the WebSocket connection manager"""
    global ws_manager
    ws_manager = WebSocketConnectionManager(redis_client)
    await ws_manager.start_listener()
    logger.info("[WS-MANAGER] ✓ WebSocket connection manager initialized and listener started")


async def shutdown_ws_manager():
    """Shutdown the WebSocket connection manager"""
    global ws_manager
    if ws_manager:
        await ws_manager.stop_listener()
        logger.info("[WS-MANAGER] ✓ WebSocket connection manager stopped")
