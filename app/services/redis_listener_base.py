"""
Resilient Redis Pub/Sub Listener Base

Provides a single retry-capable coroutine that wraps any pub/sub subscription
with exponential backoff. All Redis pub/sub listeners in omni2 use this base
so reconnect logic lives in exactly one place.

Also maintains a module-level health registry so the admin dashboard can
display real-time status for every listener component.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from redis.asyncio import Redis

from app.utils.logger import logger


# Module-level registry: name → current health snapshot
_listener_statuses: dict[str, dict[str, Any]] = {}


def get_all_listener_statuses() -> dict[str, dict[str, Any]]:
    """Return a copy of all known listener health snapshots."""
    return dict(_listener_statuses)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _broadcast_health(name: str) -> None:
    """Push a component_health event directly to the WebSocket broadcaster.

    Uses a lazy import and swallows all errors so a broadcaster hiccup
    never takes down the listener itself.
    """
    try:
        from app.services.websocket_broadcaster import get_websocket_broadcaster
        broadcaster = get_websocket_broadcaster()
        if broadcaster is not None:
            await broadcaster.broadcast_event("component_health", _listener_statuses[name])
    except Exception:
        pass


async def resilient_listener(
    redis_client: Redis,
    channel: str,
    handler: Callable[[dict[str, Any]], Awaitable[None]],
    shutdown_flag: Callable[[], bool],
    name: str,
    initial_backoff: float = 1.0,
    max_backoff: float = 60.0,
) -> None:
    """
    Subscribe to a Redis pub/sub channel and call handler for every message.

    Automatically reconnects after any Redis error using exponential backoff
    (1s → 2s → 4s … capped at max_backoff seconds).
    Stops cleanly when shutdown_flag() returns True or the task is cancelled.

    Args:
        redis_client:    Async Redis client instance.
        channel:         Redis pub/sub channel name.
        handler:         Async callable receiving the parsed message dict.
        shutdown_flag:   Zero-argument callable; return True to stop the loop.
        name:            Label used in log output (e.g. "WS-MANAGER").
        initial_backoff: Seconds to wait after the first failure.
        max_backoff:     Maximum seconds to wait between retries.
    """
    backoff = initial_backoff
    reconnect_count = 0

    while not shutdown_flag():
        pubsub = None
        try:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(channel)
            logger.info(f"[{name}] Subscribed to '{channel}'")

            _listener_statuses[name] = {
                "component": name,
                "channel": channel,
                "status": "connected",
                "reconnect_count": reconnect_count,
                "connected_at": _now_iso(),
            }
            await _broadcast_health(name)
            backoff = initial_backoff  # reset on successful connect

            async for message in pubsub.listen():
                if shutdown_flag():
                    break

                if message["type"] != "message":
                    continue

                try:
                    data = json.loads(message["data"])
                    await handler(data)
                except json.JSONDecodeError as exc:
                    logger.error(f"[{name}] Invalid JSON on '{channel}': {exc}")
                except Exception as exc:
                    logger.error(f"[{name}] Handler error on '{channel}': {exc}")

        except asyncio.CancelledError:
            logger.info(f"[{name}] Listener cancelled (clean shutdown)")
            _listener_statuses[name] = {
                "component": name,
                "channel": channel,
                "status": "stopped",
                "reconnect_count": reconnect_count,
                "stopped_at": _now_iso(),
            }
            break  # do not retry on clean cancel

        except Exception as exc:
            reconnect_count += 1
            _listener_statuses[name] = {
                "component": name,
                "channel": channel,
                "status": "reconnecting",
                "reconnect_count": reconnect_count,
                "disconnected_at": _now_iso(),
                "retry_in_seconds": int(backoff),
                "error": str(exc),
            }
            await _broadcast_health(name)

            logger.error(
                f"[{name}] Redis connection lost on '{channel}': {exc}. "
                f"Reconnecting in {backoff:.0f}s"
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)

        finally:
            if pubsub is not None:
                try:
                    await pubsub.unsubscribe(channel)
                    await pubsub.close()
                except Exception:
                    pass

    logger.info(f"[{name}] Listener stopped")
