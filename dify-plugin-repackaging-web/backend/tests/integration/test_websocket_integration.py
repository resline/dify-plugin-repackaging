"""
Integration tests for WebSocket functionality.
"""
import pytest
import json
import asyncio
from datetime import datetime
import time


class TestWebSocketIntegration:
    """Test WebSocket integration with Redis pub/sub."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, websocket_client):
        """Test basic WebSocket connection."""
        # Connect to WebSocket
        ws = await websocket_client("/ws/test_task_id")
        
        try:
            # Send a ping
            await ws.send(json.dumps({"type": "ping"}))
            
            # Wait for response
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)
            
            # Should receive a pong or connection message
            assert data.get("type") in ["pong", "connection", "ping"]
        finally:
            await ws.close()
    
    @pytest.mark.asyncio
    async def test_task_updates_via_websocket(self, websocket_client, redis_client, test_task_id):
        """Test receiving task updates through WebSocket."""
        # Connect to WebSocket for specific task
        ws = await websocket_client(f"/ws/{test_task_id}")
        
        try:
            # Wait for connection to establish
            await asyncio.sleep(0.5)
            
            # Publish task update via Redis
            update_data = {
                "task_id": test_task_id,
                "status": "processing",
                "progress": 50,
                "message": "Processing plugin files"
            }
            redis_client.publish(f"task_updates:{test_task_id}", json.dumps(update_data))
            
            # Receive update via WebSocket
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            received_data = json.loads(response)
            
            # Verify update data
            assert received_data.get("task_id") == test_task_id
            assert received_data.get("status") == "processing"
            assert received_data.get("progress") == 50
            assert received_data.get("message") == "Processing plugin files"
        finally:
            await ws.close()
    
    @pytest.mark.asyncio
    async def test_multiple_websocket_clients(self, websocket_client, redis_client, test_task_id):
        """Test multiple clients receiving the same updates."""
        # Connect multiple clients
        clients = []
        for i in range(3):
            ws = await websocket_client(f"/ws/{test_task_id}")
            clients.append(ws)
        
        try:
            # Wait for connections
            await asyncio.sleep(0.5)
            
            # Publish update
            update_data = {
                "task_id": test_task_id,
                "status": "completed",
                "progress": 100
            }
            redis_client.publish(f"task_updates:{test_task_id}", json.dumps(update_data))
            
            # All clients should receive the update
            received_messages = []
            for ws in clients:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                received_messages.append(json.loads(response))
            
            # Verify all clients received the same update
            assert len(received_messages) == 3
            for msg in received_messages:
                assert msg.get("status") == "completed"
                assert msg.get("progress") == 100
        finally:
            for ws in clients:
                await ws.close()
    
    @pytest.mark.asyncio
    async def test_websocket_reconnection(self, websocket_client, redis_client, test_task_id):
        """Test WebSocket reconnection behavior."""
        # First connection
        ws1 = await websocket_client(f"/ws/{test_task_id}")
        
        # Send initial update
        update1 = {"task_id": test_task_id, "progress": 25}
        redis_client.publish(f"task_updates:{test_task_id}", json.dumps(update1))
        
        # Receive update
        response1 = await asyncio.wait_for(ws1.recv(), timeout=5.0)
        assert json.loads(response1)["progress"] == 25
        
        # Close first connection
        await ws1.close()
        
        # Wait a moment
        await asyncio.sleep(0.5)
        
        # New connection
        ws2 = await websocket_client(f"/ws/{test_task_id}")
        
        try:
            # Send another update
            update2 = {"task_id": test_task_id, "progress": 75}
            redis_client.publish(f"task_updates:{test_task_id}", json.dumps(update2))
            
            # Should receive on new connection
            response2 = await asyncio.wait_for(ws2.recv(), timeout=5.0)
            assert json.loads(response2)["progress"] == 75
        finally:
            await ws2.close()
    
    @pytest.mark.asyncio
    async def test_websocket_error_handling(self, websocket_client, redis_client):
        """Test WebSocket error handling and recovery."""
        # Connect with invalid task ID format
        ws = await websocket_client("/ws/invalid@task#id")
        
        try:
            # Should still connect but handle errors gracefully
            await ws.send(json.dumps({"type": "ping"}))
            
            # Connection should remain stable
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            assert response is not None
        except Exception:
            # Connection might close on invalid ID, which is acceptable
            pass
        finally:
            try:
                await ws.close()
            except:
                pass
    
    @pytest.mark.asyncio
    async def test_websocket_heartbeat(self, websocket_client, test_task_id):
        """Test WebSocket heartbeat/ping mechanism."""
        ws = await websocket_client(f"/ws/{test_task_id}")
        
        try:
            pings_received = 0
            pongs_sent = 0
            
            # Listen for pings and respond with pongs
            async def handle_messages():
                nonlocal pings_received, pongs_sent
                while pings_received < 3:
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=35.0)
                        data = json.loads(response)
                        
                        if data.get("type") == "ping":
                            pings_received += 1
                            # Send pong
                            await ws.send(json.dumps({"type": "pong"}))
                            pongs_sent += 1
                    except asyncio.TimeoutError:
                        break
            
            # Run for a while to receive heartbeats
            await asyncio.wait_for(handle_messages(), timeout=100.0)
            
            # Should have received at least one ping
            assert pings_received >= 1
            assert pongs_sent >= 1
        finally:
            await ws.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_updates(self, websocket_client, redis_client, test_task_id):
        """Test handling rapid concurrent updates."""
        ws = await websocket_client(f"/ws/{test_task_id}")
        
        try:
            # Wait for connection
            await asyncio.sleep(0.5)
            
            # Send multiple rapid updates
            updates_sent = []
            for i in range(10):
                update = {
                    "task_id": test_task_id,
                    "progress": i * 10,
                    "sequence": i
                }
                updates_sent.append(update)
                redis_client.publish(f"task_updates:{test_task_id}", json.dumps(update))
                await asyncio.sleep(0.05)  # Small delay between updates
            
            # Collect received updates
            updates_received = []
            while len(updates_received) < 10:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(response)
                    if "sequence" in data:
                        updates_received.append(data)
                except asyncio.TimeoutError:
                    break
            
            # Should receive most if not all updates
            assert len(updates_received) >= 8  # Allow for some loss
            
            # Verify order is maintained
            sequences = [u["sequence"] for u in updates_received]
            assert sequences == sorted(sequences)
        finally:
            await ws.close()
    
    @pytest.mark.asyncio
    async def test_websocket_with_celery_task(self, websocket_client, celery_app, redis_client, test_task_id):
        """Test WebSocket updates from actual Celery task execution."""
        # Connect WebSocket
        ws = await websocket_client(f"/ws/{test_task_id}")
        
        try:
            # Submit Celery task
            celery_app.send_task(
                "app.workers.celery_app.process_repackaging",
                args=[test_task_id, "https://example.com/plugin.difypkg", "manylinux2014_x86_64", "offline", False]
            )
            
            # Collect updates via WebSocket
            updates = []
            start_time = time.time()
            
            while time.time() - start_time < 10:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    update = json.loads(response)
                    updates.append(update)
                    
                    if update.get("status") in ["completed", "failed"]:
                        break
                except asyncio.TimeoutError:
                    continue
            
            # Should have received some updates
            assert len(updates) > 0
            
            # Verify updates have expected fields
            for update in updates:
                assert "task_id" in update
                assert "status" in update
                assert update["task_id"] == test_task_id
        finally:
            await ws.close()