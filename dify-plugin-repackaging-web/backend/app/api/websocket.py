from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.config import settings
import redis.asyncio as redis
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._connection_timestamps: Dict[WebSocket, float] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        async with self._lock:
            if task_id not in self.active_connections:
                self.active_connections[task_id] = []
            self.active_connections[task_id].append(websocket)
            self._connection_timestamps[websocket] = time.time()
            
            # Start cleanup task if not already running
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def disconnect(self, websocket: WebSocket, task_id: str):
        async with self._lock:
            if task_id in self.active_connections and websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
                if not self.active_connections[task_id]:
                    del self.active_connections[task_id]
            
            # Remove from timestamps
            if websocket in self._connection_timestamps:
                del self._connection_timestamps[websocket]
    
    async def send_update(self, task_id: str, data: dict):
        if task_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(data)
                except WebSocketDisconnect:
                    logger.debug(f"WebSocket disconnected during send for task {task_id}")
                    disconnected.append(connection)
                except ConnectionError as e:
                    logger.warning(f"Connection error during send for task {task_id}: {e}")
                    disconnected.append(connection)
                except Exception as e:
                    logger.error(f"Unexpected error during send for task {task_id}: {e}")
                    disconnected.append(connection)
            
            # Remove disconnected clients
            for conn in disconnected:
                await self.disconnect(conn, task_id)
    
    async def _periodic_cleanup(self):
        """Periodically clean up disconnected connections"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._cleanup_disconnected_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def _cleanup_disconnected_connections(self):
        """Remove stale connections that haven't responded to pings"""
        async with self._lock:
            current_time = time.time()
            disconnected: List[tuple[WebSocket, str]] = []
            
            for task_id, connections in self.active_connections.items():
                for conn in connections:
                    try:
                        # Try to ping the connection
                        await conn.send_json({"type": "ping", "timestamp": current_time})
                    except Exception:
                        disconnected.append((conn, task_id))
            
            # Remove disconnected connections
            for conn, task_id in disconnected:
                logger.info(f"Removing stale connection for task {task_id}")
                await self.disconnect(conn, task_id)
    
    async def send_ping(self, websocket: WebSocket) -> bool:
        """Send a ping to check if connection is alive"""
        try:
            await websocket.send_json({"type": "ping", "timestamp": time.time()})
            return True
        except Exception:
            return False


manager = ConnectionManager()


async def broadcast_marketplace_selection(plugin_metadata: dict):
    """
    Broadcast marketplace plugin selection event to all connected clients
    
    This can be used to notify other parts of the application when a user
    selects a plugin from the marketplace browser.
    """
    message = {
        "type": "marketplace_selection",
        "plugin": plugin_metadata,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Broadcast to all connected clients across all tasks
    all_connections = []
    for connections in manager.active_connections.values():
        all_connections.extend(connections)
    
    disconnected = []
    for connection in all_connections:
        try:
            await connection.send_json(message)
        except WebSocketDisconnect:
            logger.debug(f"WebSocket disconnected during broadcast")
            disconnected.append(connection)
        except ConnectionError as e:
            logger.warning(f"Connection error during broadcast: {e}")
            disconnected.append(connection)
        except Exception as e:
            logger.error(f"Unexpected error during broadcast: {e}")
            disconnected.append(connection)
    
    # Clean up disconnected clients
    for conn in disconnected:
        for task_id, connections in manager.active_connections.items():
            if conn in connections:
                await manager.disconnect(conn, task_id)
                break


@router.websocket("/ws/tasks/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time task updates"""
    await manager.connect(websocket, task_id)
    
    # Create Redis subscription
    redis_client = await redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    
    try:
        # Subscribe to task updates
        await pubsub.subscribe(f"task_updates:{task_id}")
        
        # Send initial status
        task_data = await redis_client.get(f"task:{task_id}")
        if task_data:
            await websocket.send_json(json.loads(task_data))
        
        # Listen for updates
        async def listen_for_updates():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await manager.send_update(task_id, data)
        
        # Handle heartbeat with proper error handling
        async def heartbeat():
            try:
                while True:
                    await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                    await websocket.send_json({"type": "heartbeat", "timestamp": time.time()})
            except WebSocketDisconnect:
                logger.debug(f"WebSocket disconnected during heartbeat for task {task_id}")
            except ConnectionError as e:
                logger.warning(f"Connection error during heartbeat for task {task_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during heartbeat for task {task_id}: {e}")
        
        # Handle client messages (including pong responses)
        async def handle_client_messages():
            try:
                while True:
                    message = await websocket.receive_text()
                    try:
                        data = json.loads(message)
                        if data.get("type") == "pong":
                            # Update connection timestamp on pong
                            manager._connection_timestamps[websocket] = time.time()
                    except json.JSONDecodeError:
                        pass
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.error(f"Error handling client message: {e}")
                raise
        
        # Run all tasks concurrently
        await asyncio.gather(
            listen_for_updates(),
            heartbeat(),
            handle_client_messages()
        )
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")
    except Exception as e:
        logger.exception(f"WebSocket error for task {task_id}")
    finally:
        await manager.disconnect(websocket, task_id)
        await pubsub.unsubscribe()
        await redis_client.close()