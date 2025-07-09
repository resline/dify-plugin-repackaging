"""
WebSocket functionality tests
"""

import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from app.main import app
from app.api.websocket import manager
import time


def test_websocket_connection():
    """Test basic WebSocket connection"""
    client = TestClient(app)
    
    with client.websocket_connect("/ws/tasks/test-task-123") as websocket:
        # Should receive initial connection
        data = websocket.receive_json()
        assert data is not None


def test_websocket_heartbeat():
    """Test WebSocket heartbeat mechanism"""
    client = TestClient(app)
    
    with client.websocket_connect("/ws/tasks/test-task-123") as websocket:
        # Wait for heartbeat (should arrive within 35 seconds)
        start_time = time.time()
        heartbeat_received = False
        
        while time.time() - start_time < 35:
            try:
                data = websocket.receive_json(timeout=1)
                if data.get("type") == "heartbeat":
                    heartbeat_received = True
                    break
            except:
                continue
        
        assert heartbeat_received, "No heartbeat received within timeout"


def test_websocket_ping_pong():
    """Test WebSocket ping/pong mechanism"""
    client = TestClient(app)
    
    with client.websocket_connect("/ws/tasks/test-task-123") as websocket:
        # Send a pong response
        websocket.send_json({"type": "pong", "timestamp": time.time()})
        
        # Connection should remain active
        heartbeat_received = False
        start_time = time.time()
        
        while time.time() - start_time < 35:
            try:
                data = websocket.receive_json(timeout=1)
                if data.get("type") == "heartbeat":
                    heartbeat_received = True
                    break
            except:
                continue
        
        assert heartbeat_received, "Connection should remain active after pong"


def test_multiple_connections():
    """Test multiple WebSocket connections to same task"""
    client = TestClient(app)
    
    with client.websocket_connect("/ws/tasks/test-task-123") as ws1:
        with client.websocket_connect("/ws/tasks/test-task-123") as ws2:
            # Both connections should be active
            # Wait for heartbeats on both
            ws1_heartbeat = False
            ws2_heartbeat = False
            
            start_time = time.time()
            while time.time() - start_time < 35:
                try:
                    data1 = ws1.receive_json(timeout=0.1)
                    if data1.get("type") == "heartbeat":
                        ws1_heartbeat = True
                except:
                    pass
                
                try:
                    data2 = ws2.receive_json(timeout=0.1)
                    if data2.get("type") == "heartbeat":
                        ws2_heartbeat = True
                except:
                    pass
                
                if ws1_heartbeat and ws2_heartbeat:
                    break
            
            assert ws1_heartbeat and ws2_heartbeat, "Both connections should receive heartbeats"


@pytest.mark.asyncio
async def test_connection_manager_cleanup():
    """Test connection manager cleanup functionality"""
    # Create a mock WebSocket
    class MockWebSocket:
        def __init__(self):
            self.messages = []
            self.closed = False
        
        async def accept(self):
            pass
        
        async def send_json(self, data):
            if self.closed:
                raise ConnectionError("Connection closed")
            self.messages.append(data)
        
        async def close(self):
            self.closed = True
    
    # Test connection and cleanup
    ws = MockWebSocket()
    task_id = "test-cleanup-123"
    
    await manager.connect(ws, task_id)
    assert task_id in manager.active_connections
    assert ws in manager.active_connections[task_id]
    
    # Disconnect
    await manager.disconnect(ws, task_id)
    assert task_id not in manager.active_connections
    
    # Test stale connection cleanup
    ws2 = MockWebSocket()
    await manager.connect(ws2, task_id)
    
    # Close the connection to simulate stale connection
    ws2.closed = True
    
    # Run cleanup
    await manager._cleanup_disconnected_connections()
    
    # Connection should be removed
    assert task_id not in manager.active_connections or ws2 not in manager.active_connections.get(task_id, [])