"""Centralized WebSocket connection management."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Track task sockets, broadcast updates, and remove stale connections."""

    def __init__(self, cleanup_interval: float = 300, ping_interval: float = 30):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._connection_timestamps: Dict[WebSocket, float] = {}
        self._connection_health: Dict[WebSocket, Dict[str, Any]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.cleanup_interval = cleanup_interval
        self.ping_interval = ping_interval
        self._running = False

    async def start(self) -> None:
        self._running = True
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("WebSocket manager started")

    async def stop(self) -> None:
        self._running = False
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        self._cleanup_task = None
        await self.close_all_connections()
        logger.info("WebSocket manager stopped")

    async def connect(
        self,
        channel_id: str,
        websocket: WebSocket,
        *,
        send_confirmation: bool = True,
    ) -> None:
        await websocket.accept()
        now = time.time()
        async with self._lock:
            self.active_connections.setdefault(channel_id, []).append(websocket)
            self._connection_timestamps[websocket] = now
            self._connection_health[websocket] = {
                "last_ping": now,
                "last_pong": now,
                "ping_count": 0,
                "pong_count": 0,
                "connected_at": datetime.now(timezone.utc).isoformat(),
            }

        if send_confirmation:
            try:
                await websocket.send_json({
                    "type": "connection",
                    "status": "connected",
                    "channel_id": channel_id,
                })
            except Exception as exc:
                # Registration still succeeds. A later send/heartbeat will clean up
                # a transport that was closed during the initial acknowledgement.
                logger.warning("Could not confirm WebSocket connection: %s", exc)

    def _remove_connection_locked(self, channel_id: str, websocket: WebSocket) -> None:
        connections = self.active_connections.get(channel_id)
        if connections and websocket in connections:
            connections.remove(websocket)
            if not connections:
                self.active_connections.pop(channel_id, None)

        if not any(websocket in sockets for sockets in self.active_connections.values()):
            self._connection_timestamps.pop(websocket, None)
            self._connection_health.pop(websocket, None)

    async def disconnect(
        self,
        channel_id: str,
        websocket: WebSocket,
        *,
        close: bool = True,
    ) -> None:
        async with self._lock:
            self._remove_connection_locked(channel_id, websocket)

        if close:
            try:
                await websocket.close()
            except Exception:
                pass

    async def send_to_channel(self, channel_id: str, data: dict) -> int:
        async with self._lock:
            connections = list(self.active_connections.get(channel_id, []))

        successful = 0
        disconnected: List[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_json(data)
                successful += 1
            except (WebSocketDisconnect, ConnectionError):
                disconnected.append(connection)
            except Exception as exc:
                logger.warning("WebSocket send failed for %s: %s", channel_id, exc)
                disconnected.append(connection)

        for connection in disconnected:
            await self.disconnect(channel_id, connection)
        return successful

    async def send_task_update(self, channel_id: str, data: dict) -> int:
        return await self.send_to_channel(channel_id, {
            "type": "task_update",
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def broadcast(self, data: dict) -> int:
        async with self._lock:
            channels = list(self.active_connections)
        results = await asyncio.gather(
            *(self.send_to_channel(channel_id, data) for channel_id in channels)
        )
        return sum(results)

    async def send_ping(self, websocket: WebSocket) -> bool:
        try:
            await websocket.send_json({"type": "ping", "timestamp": time.time()})
            health = self._connection_health.get(websocket)
            if health is not None:
                health["last_ping"] = time.time()
                health["ping_count"] += 1
            return True
        except Exception:
            return False

    async def send_heartbeat(self, channel_id: str) -> int:
        return await self.send_to_channel(channel_id, {
            "type": "heartbeat",
            "timestamp": time.time(),
        })

    async def handle_pong(self, websocket: WebSocket) -> None:
        now = time.time()
        self._connection_timestamps[websocket] = now
        health = self._connection_health.get(websocket)
        if health is not None:
            health["last_pong"] = now
            health["pong_count"] += 1

    def update_pong_received(self, websocket: WebSocket) -> None:
        """Synchronous compatibility helper for callers that already own the loop."""
        now = time.time()
        self._connection_timestamps[websocket] = now
        health = self._connection_health.get(websocket)
        if health is not None:
            health["last_pong"] = now
            health["pong_count"] += 1

    def is_connection_healthy(self, websocket: WebSocket) -> bool:
        health = self._connection_health.get(websocket)
        return bool(
            health
            and time.time() - health.get("last_pong", 0) <= self.ping_interval * 2
        )

    async def _periodic_cleanup(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_stale_connections()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("WebSocket cleanup failed")

    async def _cleanup_stale_connections(self) -> None:
        now = time.time()
        stale: List[tuple[str, WebSocket]] = []
        ping_candidates: List[WebSocket] = []

        # Never await disconnect while holding this lock. disconnect acquires the
        # same lock, which was the source of the previous cleanup deadlock.
        async with self._lock:
            for channel_id, connections in list(self.active_connections.items()):
                for connection in list(connections):
                    health = self._connection_health.get(connection, {})
                    last_activity = self._connection_timestamps.get(connection, 0)
                    last_pong = health.get("last_pong", 0)
                    if (
                        now - last_activity > self.ping_interval * 2
                        or now - last_pong > self.ping_interval * 2
                    ):
                        stale.append((channel_id, connection))
                    elif now - health.get("last_ping", 0) >= self.ping_interval:
                        ping_candidates.append(connection)

        failed_pings = {
            connection
            for connection, sent in zip(
                ping_candidates,
                await asyncio.gather(*(self.send_ping(conn) for conn in ping_candidates)),
            )
            if not sent
        } if ping_candidates else set()

        stale.extend(
            (channel_id, connection)
            for channel_id, connections in list(self.active_connections.items())
            for connection in connections
            if connection in failed_pings
        )

        for channel_id, connection in dict.fromkeys(stale):
            logger.info("Removing stale WebSocket from %s", channel_id)
            await self.disconnect(channel_id, connection)

    def get_connection_count(self, channel_id: Optional[str] = None) -> int:
        if channel_id is not None:
            return len(self.active_connections.get(channel_id, []))
        return sum(len(connections) for connections in self.active_connections.values())

    def get_channel_count(self) -> int:
        return len(self.active_connections)

    def get_connection_info(self) -> Dict[str, Any]:
        return {
            "total_connections": self.get_connection_count(),
            "total_channels": self.get_channel_count(),
            "channels": {
                channel_id: {
                    "connection_count": len(connections),
                    "connections": [
                        dict(self._connection_health.get(connection, {}))
                        for connection in connections
                    ],
                }
                for channel_id, connections in self.active_connections.items()
            },
        }

    async def close_all_connections(self) -> None:
        async with self._lock:
            connections = list({
                connection
                for channel_connections in self.active_connections.values()
                for connection in channel_connections
            })
            self.active_connections.clear()
            self._connection_timestamps.clear()
            self._connection_health.clear()

        await asyncio.gather(
            *(connection.close() for connection in connections),
            return_exceptions=True,
        )


ws_manager = WebSocketManager()
