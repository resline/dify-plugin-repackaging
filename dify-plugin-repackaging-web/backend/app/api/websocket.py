from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.config import settings
import redis.asyncio as redis
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        if task_id in self.active_connections:
            self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
    
    async def send_update(self, task_id: str, data: dict):
        if task_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(data)
                except:
                    disconnected.append(connection)
            
            # Remove disconnected clients
            for conn in disconnected:
                self.disconnect(conn, task_id)


manager = ConnectionManager()


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
        
        # Handle heartbeat
        async def heartbeat():
            try:
                while True:
                    await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                    await websocket.send_json({"type": "heartbeat"})
            except:
                pass
        
        # Run both tasks concurrently
        await asyncio.gather(
            listen_for_updates(),
            heartbeat(),
            websocket.receive_text()  # This will raise exception on disconnect
        )
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")
    except Exception as e:
        logger.exception(f"WebSocket error for task {task_id}")
    finally:
        manager.disconnect(websocket, task_id)
        await pubsub.unsubscribe()
        await redis_client.close()