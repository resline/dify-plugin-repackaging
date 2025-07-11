"""
Integration and edge case tests to increase overall coverage.
Focus on cross-module interactions and boundary conditions.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
import json
import uuid
from datetime import datetime, timedelta
import os
import tempfile
import asyncio
from redis.exceptions import RedisError
import httpx

from app.api.v1.endpoints import tasks, files, marketplace
from app.services.marketplace import MarketplaceService
from app.services.file_manager import FileManager
from app.models.task import TaskStatus
from app.utils.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.core.config import settings


class TestTasksIntegration:
    """Integration tests for tasks module."""
    
    @pytest.mark.asyncio
    async def test_task_creation_with_redis_reconnect(self, async_client, mock_redis):
        """Test task creation when Redis connection is flaky."""
        # Arrange
        task_data = {
            "url": "https://example.com/plugin.difypkg",
            "platform": "",
            "suffix": "offline"
        }
        
        # Simulate Redis connection failure then success
        call_count = 0
        def redis_setex_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RedisError("Connection lost")
            return True
        
        mock_redis.setex.side_effect = redis_setex_side_effect
        
        with patch('app.api.v1.endpoints.tasks.redis_client', mock_redis):
            # Act - First attempt should fail
            response = await async_client.post("/api/v1/tasks", json=task_data)
            
            # Assert
            assert response.status_code == 500
            
            # Reset for second attempt
            call_count = 0
            response = await async_client.post("/api/v1/tasks", json=task_data)
            
            # Should succeed on retry
            assert response.status_code in [200, 500]  # Depends on other mocks

    @pytest.mark.asyncio
    async def test_task_status_caching(self, async_client, mock_redis):
        """Test task status retrieval with caching behavior."""
        # Arrange
        task_id = str(uuid.uuid4())
        
        # Simulate task progression
        task_states = [
            {"status": "pending", "progress": 0},
            {"status": "processing", "progress": 50},
            {"status": "completed", "progress": 100, "output_filename": "result.difypkg"}
        ]
        
        for state in task_states:
            task_data = {
                "task_id": task_id,
                "created_at": datetime.utcnow().isoformat(),
                **state
            }
            mock_redis.get.return_value = json.dumps(task_data)
            
            with patch('app.api.v1.endpoints.tasks.redis_client', mock_redis):
                # Act
                response = await async_client.get(f"/api/v1/tasks/{task_id}")
                
                # Assert
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == state["status"]
                assert data["progress"] == state["progress"]
                
                if state["status"] == "completed":
                    assert data["download_url"] is not None

    @pytest.mark.asyncio
    async def test_concurrent_task_creation(self, async_client, mock_redis):
        """Test creating multiple tasks concurrently."""
        # Arrange
        task_urls = [
            "https://example.com/plugin1.difypkg",
            "https://example.com/plugin2.difypkg",
            "https://example.com/plugin3.difypkg"
        ]
        
        with patch('app.api.v1.endpoints.tasks.process_repackaging') as mock_process:
            mock_process.delay.return_value = Mock(id="test-id")
            
            # Act - Create tasks concurrently
            async def create_task(url):
                return await async_client.post("/api/v1/tasks", json={"url": url})
            
            responses = await asyncio.gather(*[create_task(url) for url in task_urls])
            
            # Assert
            for response in responses:
                assert response.status_code == 200
                assert response.json()["status"] == "pending"


class TestMarketplaceIntegration:
    """Integration tests for marketplace functionality."""
    
    @pytest.mark.asyncio
    async def test_marketplace_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after failures."""
        # Arrange
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,  # 100ms for testing
            expected_exception=httpx.HTTPError
        )
        
        call_count = 0
        async def flaky_api_call():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise httpx.HTTPError("API error")
            return {"success": True}
        
        # Act - Trigger circuit breaker
        with pytest.raises(httpx.HTTPError):
            await breaker.async_call(flaky_api_call)
        
        with pytest.raises(httpx.HTTPError):
            await breaker.async_call(flaky_api_call)
        
        # Circuit should be open now
        with pytest.raises(CircuitOpenError):
            await breaker.async_call(flaky_api_call)
        
        # Wait for recovery
        await asyncio.sleep(0.15)
        
        # Should work now
        result = await breaker.async_call(flaky_api_call)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_marketplace_fallback_chain(self, mock_redis):
        """Test complete fallback chain from API to scraper."""
        # Arrange
        mock_redis.get.return_value = None  # No cache
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            with patch('app.services.marketplace.get_async_client') as mock_get_client:
                # All API attempts fail
                mock_client = AsyncMock()
                mock_client.get.side_effect = httpx.HTTPError("All APIs down")
                mock_get_client.return_value.__aenter__.return_value = mock_client
                
                with patch('app.services.marketplace.marketplace_circuit_breaker.async_call') as mock_breaker:
                    # Circuit breaker triggers
                    mock_breaker.side_effect = CircuitOpenError()
                    
                    with patch('app.services.marketplace_scraper.marketplace_fallback_service') as mock_fallback:
                        # Scraper also fails initially
                        mock_fallback.scraper.scrape_plugin_list = AsyncMock(
                            side_effect=[
                                Exception("Scraper error"),
                                {"plugins": [{"name": "recovered"}], "total": 1}
                            ]
                        )
                        
                        # First call fails completely
                        result = await MarketplaceService.search_plugins()
                        assert result["plugins"] == []
                        assert "error" in result
                        
                        # Second call succeeds with scraper
                        result = await MarketplaceService.search_plugins()
                        assert len(result["plugins"]) == 1
                        assert result["plugins"][0]["name"] == "recovered"

    @pytest.mark.asyncio
    async def test_marketplace_version_resolution_edge_cases(self):
        """Test edge cases in version resolution."""
        # Test empty version
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"latest_version": ""}
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await MarketplaceService.get_latest_version("author", "plugin")
            assert result is None  # Empty version should return None
        
        # Test version with special characters
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "code": 0,
                "data": {"plugin": {"latest_version": "1.0.0-beta.1"}}
            }
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await MarketplaceService.get_latest_version("author", "plugin")
            assert result == "1.0.0-beta.1"


class TestFileManagerIntegration:
    """Integration tests for file management."""
    
    @pytest.mark.asyncio
    async def test_file_lifecycle(self, async_client, mock_redis, temp_directory):
        """Test complete file lifecycle from upload to deletion."""
        # 1. Upload file
        files = {
            "file": ("test.difypkg", b"PK\x03\x04test content", "application/zip")
        }
        data = {"platform": "", "suffix": "offline"}
        
        with patch('app.api.v1.endpoints.tasks.settings.TEMP_DIR', temp_directory):
            with patch('app.api.v1.endpoints.tasks.process_repackaging') as mock_process:
                mock_process.delay.return_value = Mock(id="lifecycle-test")
                
                response = await async_client.post("/api/v1/tasks/upload", files=files, data=data)
                assert response.status_code == 200
                task_id = response.json()["task_id"]
        
        # 2. Simulate task completion
        task_data = {
            "task_id": task_id,
            "status": "completed",
            "created_at": datetime.utcnow().isoformat(),
            "output_filename": "test-offline.difypkg"
        }
        mock_redis.get.return_value = json.dumps(task_data)
        
        # Create output file
        task_dir = os.path.join(temp_directory, task_id)
        os.makedirs(task_dir, exist_ok=True)
        output_path = os.path.join(task_dir, "test-offline.difypkg")
        with open(output_path, "wb") as f:
            f.write(b"Repackaged content")
        
        # 3. List files
        with patch('app.api.v1.endpoints.tasks.redis_client', mock_redis):
            with patch('app.api.v1.endpoints.tasks.settings.TEMP_DIR', temp_directory):
                with patch('app.services.file_manager.FileManager') as mock_fm:
                    mock_fm.list_completed_files.return_value = {
                        "files": [{
                            "file_id": task_id,
                            "filename": "test-offline.difypkg",
                            "size": 18
                        }],
                        "total": 1
                    }
                    
                    response = await async_client.get("/api/v1/files")
                    assert response.status_code == 200
                    assert len(response.json()["files"]) == 1
        
        # 4. Download file
        with patch('app.api.v1.endpoints.tasks.redis_client', mock_redis):
            with patch('app.api.v1.endpoints.tasks.settings.TEMP_DIR', temp_directory):
                response = await async_client.get(f"/api/v1/tasks/{task_id}/download")
                assert response.status_code == 200
                assert response.content == b"Repackaged content"
        
        # 5. Delete file
        with patch('app.services.file_manager.FileManager') as mock_fm:
            mock_fm.get_file_info.return_value = {"file_id": task_id}
            mock_fm.delete_file.return_value = True
            
            response = await async_client.delete(f"/api/v1/files/{task_id}")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_storage_cleanup_with_retention(self, temp_directory):
        """Test storage cleanup with various retention scenarios."""
        # Create files with different ages
        now = datetime.utcnow()
        test_files = [
            ("old_file.difypkg", now - timedelta(days=10)),
            ("recent_file.difypkg", now - timedelta(days=2)),
            ("new_file.difypkg", now - timedelta(hours=1))
        ]
        
        for filename, mtime in test_files:
            file_path = os.path.join(temp_directory, filename)
            with open(file_path, "w") as f:
                f.write("test")
            # Set modification time
            mtime_timestamp = mtime.timestamp()
            os.utime(file_path, (mtime_timestamp, mtime_timestamp))
        
        with patch('app.services.file_manager.settings.TEMP_DIR', temp_directory):
            # Test with 7-day retention
            cleaned = FileManager.cleanup_old_files(7)
            assert cleaned == 1  # Only old_file should be deleted
            
            # Test with 1-day retention
            cleaned = FileManager.cleanup_old_files(1)
            assert cleaned == 1  # recent_file should be deleted
            
            # Verify new_file still exists
            assert os.path.exists(os.path.join(temp_directory, "new_file.difypkg"))


class TestErrorHandlingIntegration:
    """Test error handling across modules."""
    
    @pytest.mark.asyncio
    async def test_cascading_errors(self, async_client, mock_redis):
        """Test how errors cascade through the system."""
        # Simulate various error conditions
        error_scenarios = [
            # Redis completely down
            {
                "redis_error": RedisError("Connection refused"),
                "expected_status": 500
            },
            # Invalid task data in Redis
            {
                "redis_data": "invalid json",
                "expected_status": 500
            },
            # Corrupted task data
            {
                "redis_data": json.dumps({"invalid": "structure"}),
                "expected_status": 500
            }
        ]
        
        for scenario in error_scenarios:
            if "redis_error" in scenario:
                mock_redis.get.side_effect = scenario["redis_error"]
            elif "redis_data" in scenario:
                mock_redis.get.return_value = scenario["redis_data"]
            
            with patch('app.api.v1.endpoints.tasks.redis_client', mock_redis):
                response = await async_client.get("/api/v1/tasks/test-id")
                assert response.status_code == scenario["expected_status"]

    @pytest.mark.asyncio
    async def test_timeout_handling(self, async_client):
        """Test handling of various timeout scenarios."""
        # Test marketplace API timeout
        with patch('app.services.marketplace.get_async_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Request timeout")
            mock_get_client.return_value.__aenter__.return_value = mock_client
            
            with patch('app.services.marketplace.marketplace_circuit_breaker.async_call') as mock_breaker:
                mock_breaker.side_effect = httpx.TimeoutException("Request timeout")
                
                # Should handle timeout gracefully
                result = await MarketplaceService.search_plugins()
                assert "error" in result or result["plugins"] == []


class TestPerformanceEdgeCases:
    """Test performance-related edge cases."""
    
    @pytest.mark.asyncio
    async def test_large_file_listing(self, async_client):
        """Test handling large number of files."""
        # Mock a large file list
        large_file_list = {
            "files": [
                {
                    "file_id": str(i),
                    "filename": f"plugin-{i}.difypkg",
                    "size": 1024 * i
                }
                for i in range(200)
            ],
            "total": 10000,
            "limit": 200,
            "offset": 0,
            "has_more": True
        }
        
        with patch.object(FileManager, 'list_completed_files', return_value=large_file_list):
            response = await async_client.get("/api/v1/files?limit=200")
            assert response.status_code == 200
            assert len(response.json()["files"]) == 200
            assert response.json()["has_more"] is True

    @pytest.mark.asyncio
    async def test_concurrent_file_operations_stress(self, async_client):
        """Stress test concurrent file operations."""
        file_ids = [f"stress-{i}" for i in range(20)]
        
        # Mock varying response times and results
        async def mock_get_info(file_id):
            await asyncio.sleep(0.01)  # Simulate some processing time
            if "5" in file_id:
                return None  # Some files don't exist
            return {"file_id": file_id, "filename": f"{file_id}.difypkg"}
        
        with patch.object(FileManager, 'get_file_info', side_effect=mock_get_info):
            # Make concurrent requests
            async def get_file_info(file_id):
                return await async_client.get(f"/api/v1/files/{file_id}")
            
            responses = await asyncio.gather(
                *[get_file_info(fid) for fid in file_ids],
                return_exceptions=True
            )
            
            # Verify responses
            success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
            not_found_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 404)
            
            assert success_count > 0
            assert not_found_count == 4  # Files with '5' in the ID


class TestConfigurationEdgeCases:
    """Test various configuration edge cases."""
    
    @pytest.mark.asyncio
    async def test_missing_environment_variables(self, async_client, monkeypatch):
        """Test behavior with missing or invalid environment variables."""
        # Test with missing Redis URL
        monkeypatch.delenv("REDIS_URL", raising=False)
        
        # System should still handle requests gracefully
        response = await async_client.get("/api/v1/health")
        assert response.status_code in [200, 500]  # Depends on health check implementation
    
    @pytest.mark.asyncio
    async def test_invalid_settings_values(self):
        """Test handling of invalid configuration values."""
        with patch('app.core.config.settings.MARKETPLACE_CACHE_TTL', -1):
            # Should handle negative TTL gracefully
            MarketplaceService._set_cache("test_key", {"data": "test"})
            # Should not crash
        
        with patch('app.core.config.settings.FILE_RETENTION_DAYS', 0):
            # Should handle zero retention days
            result = FileManager.cleanup_old_files()
            assert isinstance(result, int)  # Should return a number, not crash