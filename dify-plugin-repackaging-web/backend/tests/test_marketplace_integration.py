import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient
from app.models.task import TaskStatus, Platform
from app.models.marketplace import Plugin, PluginSearchResult, PluginVersion, MarketplacePluginMetadata
from app.workers.celery_app import update_task_status, process_marketplace_repackaging


class TestMarketplaceIntegration:
    """Integration tests for marketplace functionality"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        with patch('app.workers.celery_app.redis_client') as mock:
            mock.setex = MagicMock()
            mock.publish = MagicMock()
            mock.get = MagicMock()
            mock.keys = MagicMock(return_value=[])
            yield mock
    
    @pytest.fixture
    def mock_marketplace_service(self):
        """Mock MarketplaceService"""
        with patch('app.services.marketplace.MarketplaceService') as mock:
            # Mock search_plugins
            mock.search_plugins = AsyncMock(return_value={
                "plugins": [
                    {
                        "name": "test-plugin",
                        "author": "test-author",
                        "display_name": "Test Plugin",
                        "description": "A test plugin",
                        "category": "tool",
                        "tags": ["test", "demo"],
                        "latest_version": "1.0.0",
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat(),
                        "verified": True
                    }
                ],
                "total": 1,
                "page": 1,
                "per_page": 20,
                "has_more": False
            })
            
            # Mock get_plugin_details
            mock.get_plugin_details = AsyncMock(return_value={
                "name": "test-plugin",
                "author": "test-author",
                "display_name": "Test Plugin",
                "description": "A test plugin",
                "category": "tool",
                "tags": ["test", "demo"],
                "latest_version": "1.0.0",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "verified": True,
                "available_versions": [
                    {"version": "1.0.0", "created_at": datetime.utcnow().isoformat()},
                    {"version": "0.9.0", "created_at": datetime.utcnow().isoformat()}
                ]
            })
            
            # Mock build_download_url
            mock.build_download_url = MagicMock(
                return_value="https://marketplace.dify.ai/api/v1/plugins/test-author/test-plugin/1.0.0/download"
            )
            mock.construct_download_url = mock.build_download_url
            
            yield mock
    
    @pytest.fixture
    def mock_download_service(self):
        """Mock DownloadService"""
        with patch('app.services.download.DownloadService') as mock:
            mock.download_file = AsyncMock(
                return_value=("/tmp/test-task/test-plugin.difypkg", "test-plugin.difypkg")
            )
            yield mock
    
    @pytest.fixture
    def mock_repackage_service(self):
        """Mock RepackageService"""
        with patch('app.services.repackage.RepackageService') as mock:
            async def mock_repackage():
                yield ("Starting repackaging...", 20)
                yield ("Processing dependencies...", 50)
                yield ("Repackaging complete", 90)
                yield ("Output file: test-plugin-offline.difypkg", 100)
            
            mock.repackage_plugin = MagicMock(return_value=mock_repackage())
            yield mock
    
    def test_marketplace_plugin_metadata_creation(self):
        """Test creation of marketplace plugin metadata"""
        metadata = MarketplacePluginMetadata(
            source="marketplace",
            author="test-author",
            name="test-plugin",
            version="1.0.0",
            display_name="Test Plugin",
            category="tool"
        )
        
        assert metadata.source == "marketplace"
        assert metadata.author == "test-author"
        assert metadata.name == "test-plugin"
        assert metadata.version == "1.0.0"
        assert metadata.display_name == "Test Plugin"
        assert metadata.category == "tool"
    
    def test_update_task_status_with_marketplace_metadata(self, mock_redis):
        """Test task status update includes marketplace metadata"""
        task_id = "test-task-123"
        marketplace_metadata = {
            "source": "marketplace",
            "author": "test-author",
            "name": "test-plugin",
            "version": "1.0.0"
        }
        
        update_task_status(
            task_id,
            TaskStatus.DOWNLOADING,
            progress=10,
            message="Downloading plugin...",
            marketplace_metadata=marketplace_metadata
        )
        
        # Verify Redis calls
        assert mock_redis.setex.called
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == f"task:{task_id}"
        
        stored_data = json.loads(call_args[0][2])
        assert stored_data["marketplace_metadata"] == marketplace_metadata
        assert stored_data["status"] == "downloading"
        assert stored_data["progress"] == 10
        
        # Verify publish call
        assert mock_redis.publish.called
        publish_args = mock_redis.publish.call_args
        assert publish_args[0][0] == f"task_updates:{task_id}"
        
        published_data = json.loads(publish_args[0][1])
        assert published_data["marketplace_metadata"] == marketplace_metadata
    
    @pytest.mark.asyncio
    async def test_marketplace_task_creation_flow(self, client: TestClient, mock_redis):
        """Test creating a task from marketplace plugin"""
        with patch('app.workers.celery_app.process_marketplace_repackaging.delay') as mock_delay:
            response = client.post("/api/v1/tasks/marketplace", json={
                "author": "test-author",
                "name": "test-plugin",
                "version": "1.0.0",
                "platform": "",
                "suffix": "offline"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data
            assert data["status"] == "pending"
            
            # Verify Celery task was queued
            assert mock_delay.called
            call_args = mock_delay.call_args[0]
            assert call_args[1] == "test-author"
            assert call_args[2] == "test-plugin"
            assert call_args[3] == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_url_flow(self, client: TestClient, mock_redis):
        """Test that direct URL flow still works"""
        with patch('app.workers.celery_app.process_repackaging.delay') as mock_delay:
            response = client.post("/api/v1/tasks", json={
                "url": "https://example.com/plugin.difypkg",
                "platform": "",
                "suffix": "offline"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data
            assert data["status"] == "pending"
            
            # Verify regular Celery task was queued (not marketplace version)
            assert mock_delay.called
            call_args = mock_delay.call_args[0]
            assert "https://example.com/plugin.difypkg" in call_args
    
    @pytest.mark.asyncio
    async def test_unified_endpoint_with_marketplace(self, client: TestClient, mock_redis):
        """Test unified /tasks endpoint with marketplace plugin"""
        with patch('app.workers.celery_app.process_marketplace_repackaging.delay') as mock_delay:
            response = client.post("/api/v1/tasks", json={
                "marketplace_plugin": {
                    "author": "test-author",
                    "name": "test-plugin",
                    "version": "1.0.0"
                },
                "platform": "",
                "suffix": "offline"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data
            assert data["status"] == "pending"
            
            # Verify marketplace Celery task was queued
            assert mock_delay.called
            call_args = mock_delay.call_args[0]
            assert call_args[1] == "test-author"
            assert call_args[2] == "test-plugin"
            assert call_args[3] == "1.0.0"
    
    def test_websocket_message_with_marketplace_metadata(self, mock_redis):
        """Test WebSocket messages include marketplace metadata"""
        task_id = "test-task-123"
        marketplace_metadata = {
            "source": "marketplace",
            "author": "test-author",
            "name": "test-plugin",
            "version": "1.0.0",
            "display_name": "Test Plugin",
            "category": "tool"
        }
        
        # Simulate task progress update
        update_task_status(
            task_id,
            TaskStatus.PROCESSING,
            progress=50,
            message="Processing plugin...",
            marketplace_metadata=marketplace_metadata
        )
        
        # Verify WebSocket publish includes metadata
        publish_call = mock_redis.publish.call_args
        published_data = json.loads(publish_call[0][1])
        
        assert published_data["marketplace_metadata"] == marketplace_metadata
        assert published_data["status"] == "processing"
        assert published_data["progress"] == 50
    
    @pytest.mark.asyncio
    async def test_full_marketplace_repackaging_flow(
        self, 
        mock_redis,
        mock_marketplace_service,
        mock_download_service,
        mock_repackage_service
    ):
        """Test complete flow: search → select → repackage → download"""
        task_id = "test-task-123"
        
        # Mock the full Celery task execution
        with patch('asyncio.new_event_loop'), \
             patch('asyncio.set_event_loop'), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            # Create a real event loop for testing
            loop = asyncio.new_event_loop()
            mock_loop.return_value = loop
            
            # Mock run_until_complete to actually run the coroutines
            def run_coro(coro):
                if asyncio.iscoroutine(coro):
                    return loop.run_until_complete(coro)
                return coro
            
            loop.run_until_complete = run_coro
            
            # Test data
            marketplace_metadata = {
                "source": "marketplace",
                "author": "test-author",
                "name": "test-plugin",
                "version": "1.0.0"
            }
            
            # Simulate the Celery task
            try:
                result = process_marketplace_repackaging(
                    None,  # self (task instance)
                    task_id,
                    "test-author",
                    "test-plugin",
                    "1.0.0",
                    "",
                    "offline",
                    marketplace_metadata
                )
                
                # Verify result
                assert result["task_id"] == task_id
                assert result["status"] == "completed"
                assert result["marketplace_metadata"] == marketplace_metadata
                assert "test-plugin-offline.difypkg" in result["output_filename"]
                
                # Verify status updates were called
                assert mock_redis.setex.called
                assert mock_redis.publish.called
                
            finally:
                loop.close()
    
    def test_marketplace_error_handling(self, mock_redis):
        """Test error handling in marketplace flow"""
        task_id = "test-task-123"
        marketplace_metadata = {
            "source": "marketplace",
            "author": "test-author",
            "name": "test-plugin",
            "version": "1.0.0"
        }
        
        # Simulate error
        error_message = "Failed to download plugin"
        update_task_status(
            task_id,
            TaskStatus.FAILED,
            progress=0,
            message="Processing failed",
            error=error_message,
            marketplace_metadata=marketplace_metadata
        )
        
        # Verify error was included in status
        call_args = mock_redis.setex.call_args
        stored_data = json.loads(call_args[0][2])
        assert stored_data["status"] == "failed"
        assert stored_data["error"] == error_message
        assert stored_data["marketplace_metadata"] == marketplace_metadata
    
    @pytest.mark.asyncio
    async def test_marketplace_search_endpoint(self, client: TestClient, mock_marketplace_service):
        """Test marketplace search functionality"""
        response = client.get("/api/v1/marketplace/plugins?q=test&page=1&per_page=20")
        
        assert response.status_code == 200
        data = response.json()
        assert "plugins" in data
        assert len(data["plugins"]) == 1
        assert data["plugins"][0]["name"] == "test-plugin"
        assert data["total"] == 1
    
    @pytest.mark.asyncio
    async def test_marketplace_plugin_details(self, client: TestClient, mock_marketplace_service):
        """Test getting plugin details from marketplace"""
        response = client.get("/api/v1/marketplace/plugins/test-author/test-plugin")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-plugin"
        assert data["author"] == "test-author"
        assert "available_versions" in data
        assert len(data["available_versions"]) == 2


# Fixtures for FastAPI test client
@pytest.fixture
def client():
    """Create test client"""
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])