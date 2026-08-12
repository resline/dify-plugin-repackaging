"""WebSocket endpoint for real-time task status updates."""

import asyncio
import json
import logging
import time
from contextlib import suppress
from datetime import datetime, timezone

import redis.asyncio as redis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.security import SESSION_COOKIE_NAME, verify_session_token
from app.core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# Backwards-compatible export used by existing callers and tests.
manager = ws_manager


async def broadcast_marketplace_selection(plugin_metadata: dict) -> None:
    await manager.broadcast({
        "type": "marketplace_selection",
        "plugin": plugin_metadata,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@router.websocket("/ws/tasks/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str) -> None:
    """Stream one task's Redis updates until either peer disconnects."""
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = None
    connected = False
    workers: set[asyncio.Task] = set()

    try:
        if settings.AUTH_PASSWORD and not verify_session_token(
            websocket.cookies.get(SESSION_COOKIE_NAME)
        ):
            logger.warning("Unauthenticated WebSocket request for task %s", task_id)
            await websocket.close(code=1008, reason="Authentication required")
            return

        task_data = await redis_client.get(f"task:{task_id}")
        if not task_data:
            logger.warning("WebSocket requested missing task %s", task_id)
            await websocket.close(code=1008, reason="Task not found")
            return

        await manager.connect(task_id, websocket, send_confirmation=False)
        connected = True

        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"task_updates:{task_id}")
        await websocket.send_json(json.loads(task_data))

        async def listen_for_updates() -> None:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await websocket.send_json(json.loads(message["data"]))

        async def heartbeat() -> None:
            while True:
                await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": time.time(),
                })

        async def receive_client_messages() -> None:
            while True:
                raw_message = await websocket.receive_text()
                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError:
                    continue
                if message.get("type") in {"pong", "heartbeat"}:
                    await manager.handle_pong(websocket)

        workers = {
            asyncio.create_task(listen_for_updates()),
            asyncio.create_task(heartbeat()),
            asyncio.create_task(receive_client_messages()),
        }
        done, pending = await asyncio.wait(
            workers,
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            exception = task.exception()
            if exception:
                raise exception

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for task %s", task_id)
    except asyncio.CancelledError:
        raise
    except ConnectionError:
        logger.info("WebSocket transport stopped for task %s", task_id)
    except Exception:
        logger.exception("WebSocket error for task %s", task_id)
    finally:
        for task in workers:
            if not task.done():
                task.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)

        if connected:
            await manager.disconnect(task_id, websocket, close=False)

        if pubsub is not None:
            with suppress(Exception):
                await pubsub.unsubscribe(f"task_updates:{task_id}")
            with suppress(Exception):
                await pubsub.aclose()

        with suppress(Exception):
            await redis_client.aclose()
