"""
WebSocket Manager for handling WebSocket connections and broadcasting updates.
This module provides centralized WebSocket management with automatic cleanup
and connection health monitoring.
"""

from typing import Dict, List, Optional, Set
import asyncio
import time
import logging
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import json

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections with automatic cleanup and health monitoring.
    
    Features:
    - Thread-safe connection management with async locks
    - Automatic cleanup of stale connections
    - Ping/pong heartbeat mechanism
    - Connection health monitoring
    - Graceful error handling
    """
    
    def __init__(self, cleanup_interval: int = 300, ping_interval: int = 30):
        """
        Initialize the WebSocket manager.
        
        Args:
            cleanup_interval: Seconds between cleanup runs (default: 5 minutes)
            ping_interval: Seconds between ping messages (default: 30 seconds)
        """
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._connection_timestamps: Dict[WebSocket, float] = {}
        self._connection_health: Dict[WebSocket, Dict[str, any]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.cleanup_interval = cleanup_interval
        self.ping_interval = ping_interval
        self._running = False
    
    async def start(self):
        """Start the WebSocket manager background tasks."""
        self._running = True
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("WebSocket manager started")
    
    async def stop(self):
        """Stop the WebSocket manager and clean up resources."""
        self._running = False
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all active connections
        async with self._lock:
            for connections in self.active_connections.values():
                for conn in connections:
                    try:
                        await conn.close()
                    except Exception:
                        pass
            self.active_connections.clear()
            self._connection_timestamps.clear()
            self._connection_health.clear()
        
        logger.info("WebSocket manager stopped")
    
    async def connect(self, websocket: WebSocket, channel_id: str) -> None:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            channel_id: The channel identifier (e.g., task ID)
        """
        await websocket.accept()
        
        async with self._lock:
            if channel_id not in self.active_connections:
                self.active_connections[channel_id] = []
            
            self.active_connections[channel_id].append(websocket)
            self._connection_timestamps[websocket] = time.time()
            self._connection_health[websocket] = {
                'last_ping': time.time(),
                'last_pong': time.time(),
                'ping_count': 0,
                'pong_count': 0,
                'connected_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"WebSocket connected to channel {channel_id}")
            
            # Ensure cleanup task is running
            if self._running and (self._cleanup_task is None or self._cleanup_task.done()):
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def disconnect(self, websocket: WebSocket, channel_id: str) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            channel_id: The channel identifier
        """
        async with self._lock:
            if channel_id in self.active_connections and websocket in self.active_connections[channel_id]:
                self.active_connections[channel_id].remove(websocket)
                if not self.active_connections[channel_id]:
                    del self.active_connections[channel_id]
            
            # Clean up metadata
            self._connection_timestamps.pop(websocket, None)
            self._connection_health.pop(websocket, None)
            
            logger.info(f"WebSocket disconnected from channel {channel_id}")
    
    async def send_to_channel(self, channel_id: str, data: dict) -> int:
        """
        Send data to all connections in a channel.
        
        Args:
            channel_id: The channel identifier
            data: The data to send
            
        Returns:
            Number of successful sends
        """
        if channel_id not in self.active_connections:
            return 0
        
        successful_sends = 0
        disconnected = []
        
        for connection in self.active_connections[channel_id]:
            try:
                await connection.send_json(data)
                successful_sends += 1
            except WebSocketDisconnect:
                logger.debug(f"WebSocket disconnected during send to channel {channel_id}")
                disconnected.append(connection)
            except ConnectionError as e:
                logger.warning(f"Connection error during send to channel {channel_id}: {e}")
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"Unexpected error during send to channel {channel_id}: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            await self.disconnect(conn, channel_id)
        
        return successful_sends
    
    async def broadcast(self, data: dict) -> int:
        """
        Broadcast data to all connected clients.
        
        Args:
            data: The data to broadcast
            
        Returns:
            Number of successful sends
        """
        all_connections = []
        connection_channels = {}
        
        # Collect all connections with their channels
        for channel_id, connections in self.active_connections.items():
            for conn in connections:
                all_connections.append(conn)
                connection_channels[conn] = channel_id
        
        successful_sends = 0
        disconnected = []
        
        for connection in all_connections:
            try:
                await connection.send_json(data)
                successful_sends += 1
            except Exception:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            channel_id = connection_channels.get(conn)
            if channel_id:
                await self.disconnect(conn, channel_id)
        
        return successful_sends
    
    async def send_ping(self, websocket: WebSocket) -> bool:
        """
        Send a ping message to check connection health.
        
        Args:
            websocket: The WebSocket connection
            
        Returns:
            True if ping was sent successfully
        """
        try:
            await websocket.send_json({
                "type": "ping",
                "timestamp": time.time()
            })
            
            if websocket in self._connection_health:
                self._connection_health[websocket]['last_ping'] = time.time()
                self._connection_health[websocket]['ping_count'] += 1
            
            return True
        except Exception:
            return False
    
    def update_pong_received(self, websocket: WebSocket) -> None:
        """
        Update connection health when pong is received.
        
        Args:
            websocket: The WebSocket connection
        """
        if websocket in self._connection_health:
            self._connection_health[websocket]['last_pong'] = time.time()
            self._connection_health[websocket]['pong_count'] += 1
    
    async def _periodic_cleanup(self) -> None:
        """Periodically clean up stale connections."""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_stale_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def _cleanup_stale_connections(self) -> None:
        """Remove connections that haven't responded to pings."""
        async with self._lock:
            current_time = time.time()
            stale_connections: List[tuple[WebSocket, str]] = []
            
            # Check each connection's health
            for channel_id, connections in list(self.active_connections.items()):
                for conn in connections[:]:  # Create a copy to iterate safely
                    health = self._connection_health.get(conn, {})
                    last_pong = health.get('last_pong', 0)
                    
                    # If no pong received for 2 ping intervals, consider stale
                    if current_time - last_pong > self.ping_interval * 2:
                        # Try one more ping
                        if not await self.send_ping(conn):
                            stale_connections.append((conn, channel_id))
                        else:
                            # Give it one more chance
                            continue
                    
                    # Send periodic ping
                    elif current_time - health.get('last_ping', 0) >= self.ping_interval:
                        await self.send_ping(conn)
            
            # Remove stale connections
            for conn, channel_id in stale_connections:
                logger.warning(f"Removing stale connection from channel {channel_id}")
                await self.disconnect(conn, channel_id)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())
    
    def get_channel_count(self) -> int:
        """Get number of active channels."""
        return len(self.active_connections)
    
    def get_connection_info(self) -> Dict[str, any]:
        """Get detailed information about all connections."""
        info = {
            'total_connections': self.get_connection_count(),
            'total_channels': self.get_channel_count(),
            'channels': {}
        }
        
        for channel_id, connections in self.active_connections.items():
            info['channels'][channel_id] = {
                'connection_count': len(connections),
                'connections': []
            }
            
            for conn in connections:
                health = self._connection_health.get(conn, {})
                info['channels'][channel_id]['connections'].append({
                    'connected_at': health.get('connected_at'),
                    'last_ping': health.get('last_ping'),
                    'last_pong': health.get('last_pong'),
                    'ping_count': health.get('ping_count', 0),
                    'pong_count': health.get('pong_count', 0)
                })
        
        return info


# Global WebSocket manager instance
ws_manager = WebSocketManager()