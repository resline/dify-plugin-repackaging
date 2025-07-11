"""
Unit tests for WebSocket Manager
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json
import time

from fastapi import WebSocket, WebSocketDisconnect
from app.core.websocket_manager import WebSocketManager
from tests.factories.plugin import WebSocketMessageFactory


class TestWebSocketManager:
    """Test cases for WebSocket Manager."""
    
    @pytest.fixture
    def manager(self):
        """Create a WebSocket manager instance."""
        return WebSocketManager(cleanup_interval=300, ping_interval=30)
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = Mock(spec=WebSocket)
        ws.send_json = AsyncMock()
        ws.send_text = AsyncMock()
        ws.send_bytes = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.ping = AsyncMock()
        ws.pong = AsyncMock()
        ws.client_state = Mock(value=1)  # WebSocketState.CONNECTED
        return ws
    
    @pytest.mark.asyncio
    async def test_connect_success(self, manager, mock_websocket):
        """Test successful WebSocket connection."""
        # Act
        await manager.connect("task-123", mock_websocket)
        
        # Assert
        assert "task-123" in manager.active_connections
        assert mock_websocket in manager.active_connections["task-123"]
        assert mock_websocket in manager._connection_timestamps
        assert mock_websocket in manager._connection_health
        
        # Verify initial message sent
        mock_websocket.send_json.assert_called_once()
        initial_msg = mock_websocket.send_json.call_args[0][0]
        assert initial_msg["type"] == "connection"
        assert initial_msg["status"] == "connected"
    
    @pytest.mark.asyncio
    async def test_connect_multiple_clients(self, manager, mock_websocket):
        """Test multiple clients connecting to same task."""
        # Arrange
        ws1 = mock_websocket
        ws2 = Mock(spec=WebSocket)
        ws2.send_json = AsyncMock()
        ws2.send_text = AsyncMock()
        ws2.close = AsyncMock()
        ws2.client_state = Mock(value=1)
        
        # Act
        await manager.connect("task-123", ws1)
        await manager.connect("task-123", ws2)
        
        # Assert
        assert len(manager.active_connections["task-123"]) == 2
        assert ws1 in manager.active_connections["task-123"]
        assert ws2 in manager.active_connections["task-123"]
    
    @pytest.mark.asyncio
    async def test_disconnect_success(self, manager, mock_websocket):
        """Test successful WebSocket disconnection."""
        # Arrange
        await manager.connect("task-123", mock_websocket)
        
        # Act
        await manager.disconnect("task-123", mock_websocket)
        
        # Assert
        assert mock_websocket not in manager.active_connections.get("task-123", [])
        assert mock_websocket not in manager._connection_timestamps
        assert mock_websocket not in manager._connection_health
        mock_websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_last_client_removes_task(self, manager, mock_websocket):
        """Test that disconnecting last client removes task entry."""
        # Arrange
        await manager.connect("task-123", mock_websocket)
        
        # Act
        await manager.disconnect("task-123", mock_websocket)
        
        # Assert
        assert "task-123" not in manager.active_connections
    
    @pytest.mark.asyncio
    async def test_send_task_update_success(self, manager, mock_websocket):
        """Test sending task update to connected clients."""
        # Arrange
        await manager.connect("task-123", mock_websocket)
        update_data = {
            "status": "processing",
            "progress": 50,
            "message": "Processing..."
        }
        
        # Act
        await manager.send_task_update("task-123", update_data)
        
        # Assert
        assert mock_websocket.send_json.call_count == 2  # Initial + update
        update_call = mock_websocket.send_json.call_args_list[1]
        sent_data = update_call[0][0]
        assert sent_data["type"] == "task_update"
        assert sent_data["data"] == update_data
    
    @pytest.mark.asyncio
    async def test_send_task_update_no_connections(self, manager):
        """Test sending update when no connections exist."""
        # Act & Assert - Should not raise exception
        await manager.send_task_update("task-123", {"status": "processing"})
    
    @pytest.mark.asyncio
    async def test_send_task_update_connection_error(self, manager, mock_websocket):
        """Test handling connection errors during send."""
        # Arrange
        await manager.connect("task-123", mock_websocket)
        mock_websocket.send_json.side_effect = Exception("Connection closed")
        
        # Act
        await manager.send_task_update("task-123", {"status": "processing"})
        
        # Assert - Connection should be removed
        assert mock_websocket not in manager.active_connections.get("task-123", [])
    
    @pytest.mark.asyncio
    async def test_broadcast_success(self, manager, mock_websocket):
        """Test broadcasting message to all connections."""
        # Arrange
        ws1 = mock_websocket
        ws2 = Mock(spec=WebSocket)
        ws2.send_json = AsyncMock()
        ws2.client_state = Mock(value=1)
        
        await manager.connect("task-123", ws1)
        await manager.connect("task-456", ws2)
        
        # Act
        await manager.broadcast({"type": "system", "message": "Maintenance"})
        
        # Assert
        assert ws1.send_json.call_count >= 2  # Initial + broadcast
        assert ws2.send_json.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_send_heartbeat(self, manager, mock_websocket):
        """Test sending heartbeat to connections."""
        # Arrange
        await manager.connect("task-123", mock_websocket)
        
        # Act
        await manager.send_heartbeat("task-123")
        
        # Assert
        heartbeat_call = mock_websocket.send_json.call_args_list[-1]
        sent_data = heartbeat_call[0][0]
        assert sent_data["type"] == "heartbeat"
        assert "timestamp" in sent_data
    
    @pytest.mark.asyncio
    async def test_cleanup_stale_connections(self, manager, mock_websocket):
        """Test cleanup of stale connections."""
        # Arrange
        await manager.connect("task-123", mock_websocket)
        
        # Make connection appear stale
        manager._connection_timestamps[mock_websocket] = time.time() - 3600  # 1 hour ago
        manager._connection_health[mock_websocket] = {
            "last_pong": time.time() - 3600,
            "ping_count": 10,
            "pong_count": 0
        }
        
        # Act
        await manager._cleanup_stale_connections()
        
        # Assert
        assert mock_websocket not in manager.active_connections.get("task-123", [])
    
    @pytest.mark.asyncio
    async def test_handle_pong(self, manager, mock_websocket):
        """Test handling pong response."""
        # Arrange
        await manager.connect("task-123", mock_websocket)
        
        # Act
        await manager.handle_pong(mock_websocket)
        
        # Assert
        health = manager._connection_health[mock_websocket]
        assert health["pong_count"] == 1
        assert health["last_pong"] > 0
    
    @pytest.mark.asyncio
    async def test_is_connection_healthy(self, manager, mock_websocket):
        """Test connection health check."""
        # Arrange
        await manager.connect("task-123", mock_websocket)
        
        # Test healthy connection
        assert manager.is_connection_healthy(mock_websocket) is True
        
        # Test unhealthy connection (old last pong)
        manager._connection_health[mock_websocket]["last_pong"] = time.time() - 120
        assert manager.is_connection_healthy(mock_websocket) is False
    
    @pytest.mark.asyncio
    async def test_get_connection_count(self, manager, mock_websocket):
        """Test getting connection count."""
        # Arrange
        ws1 = mock_websocket
        ws2 = Mock(spec=WebSocket)
        ws2.client_state = Mock(value=1)
        
        await manager.connect("task-123", ws1)
        await manager.connect("task-123", ws2)
        await manager.connect("task-456", ws1)
        
        # Act & Assert
        assert manager.get_connection_count() == 3
        assert manager.get_connection_count("task-123") == 2
        assert manager.get_connection_count("task-456") == 1
        assert manager.get_connection_count("task-789") == 0
    
    @pytest.mark.asyncio
    async def test_close_all_connections(self, manager, mock_websocket):
        """Test closing all connections."""
        # Arrange
        ws1 = mock_websocket
        ws2 = Mock(spec=WebSocket)
        ws2.send_json = AsyncMock()
        ws2.close = AsyncMock()
        ws2.client_state = Mock(value=1)
        
        await manager.connect("task-123", ws1)
        await manager.connect("task-456", ws2)
        
        # Act
        await manager.close_all_connections()
        
        # Assert
        assert len(manager.active_connections) == 0
        ws1.close.assert_called_once()
        ws2.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_stop_manager(self, manager):
        """Test starting and stopping the manager."""
        # Act
        await manager.start()
        assert manager._running is True
        assert manager._cleanup_task is not None
        
        await manager.stop()
        assert manager._running is False
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, manager):
        """Test handling concurrent connections safely."""
        # Arrange
        websockets = []
        for i in range(10):
            ws = Mock(spec=WebSocket)
            ws.send_json = AsyncMock()
            ws.client_state = Mock(value=1)
            websockets.append(ws)
        
        # Act - Connect all concurrently
        tasks = [manager.connect(f"task-{i}", ws) for i, ws in enumerate(websockets)]
        await asyncio.gather(*tasks)
        
        # Assert
        total_connections = sum(len(conns) for conns in manager.active_connections.values())
        assert total_connections == 10
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, manager, mock_websocket):
        """Test manager recovers from errors gracefully."""
        # Arrange
        await manager.connect("task-123", mock_websocket)
        
        # Simulate various errors
        mock_websocket.send_json.side_effect = [
            WebSocketDisconnect(),
            Exception("Unknown error"),
            None  # Success
        ]
        
        # Act - Should handle errors without crashing
        await manager.send_task_update("task-123", {"status": "error"})
        await manager.send_task_update("task-123", {"status": "retry"})
        
        # Re-add connection
        await manager.connect("task-123", mock_websocket)
        await manager.send_task_update("task-123", {"status": "success"})
        
        # Assert - Last call should succeed
        last_call = mock_websocket.send_json.call_args_list[-1]
        assert last_call[0][0]["data"]["status"] == "success"


class TestWebSocketManagerIntegration:
    """Integration tests for WebSocket Manager with real async behavior."""
    
    @pytest.mark.asyncio
    async def test_periodic_cleanup(self):
        """Test that periodic cleanup runs correctly."""
        # Arrange
        manager = WebSocketManager(cleanup_interval=0.1, ping_interval=0.05)
        mock_ws = Mock(spec=WebSocket)
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.ping = AsyncMock()
        mock_ws.client_state = Mock(value=1)
        
        await manager.connect("task-123", mock_ws)
        
        # Make connection stale
        manager._connection_timestamps[mock_ws] = time.time() - 3600
        
        # Act
        await manager.start()
        await asyncio.sleep(0.2)  # Wait for cleanup to run
        
        # Assert
        assert mock_ws not in manager.active_connections.get("task-123", [])
        
        # Cleanup
        await manager.stop()