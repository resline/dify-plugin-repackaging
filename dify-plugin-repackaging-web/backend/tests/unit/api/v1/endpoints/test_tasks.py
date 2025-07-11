"""
Unit tests for tasks API endpoints
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from httpx import AsyncClient
import json
import uuid
from datetime import datetime

from app.api.v1.endpoints.tasks import router
from app.models.task import TaskStatus
from tests.factories.plugin import TaskFactory, MarketplacePluginFactory


class TestTasksEndpoint:
    """Test cases for task endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_task_with_url(self, async_client: AsyncClient, mock_celery, mock_redis):
        """Test creating a task with direct URL."""
        # Arrange
        task_data = {
            "url": "https://example.com/plugin.difypkg",
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }
        expected_task_id = str(uuid.uuid4())
        
        with patch('app.api.v1.endpoints.tasks.uuid.uuid4', return_value=expected_task_id):
            mock_celery.send_task.return_value.id = expected_task_id
            mock_redis.set.return_value = True
            
            # Act
            response = await async_client.post("/api/v1/tasks", json=task_data)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == expected_task_id
            assert data["status"] == "pending"
            assert data["type"] == "url"
            
            # Verify Redis was called
            mock_redis.set.assert_called()
            
            # Verify Celery task was sent
            mock_celery.send_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_task_with_marketplace(self, async_client: AsyncClient, mock_celery, mock_redis):
        """Test creating a task with marketplace plugin."""
        # Arrange
        task_data = {
            "marketplace_plugin": {
                "author": "langgenius",
                "name": "agent",
                "version": "0.0.9"
            },
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }
        expected_task_id = str(uuid.uuid4())
        
        with patch('app.api.v1.endpoints.tasks.uuid.uuid4', return_value=expected_task_id):
            mock_celery.send_task.return_value.id = expected_task_id
            mock_redis.set.return_value = True
            
            # Act
            response = await async_client.post("/api/v1/tasks", json=task_data)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == expected_task_id
            assert data["status"] == "pending"
            assert data["type"] == "marketplace"
    
    @pytest.mark.asyncio
    async def test_create_task_validation_error(self, async_client: AsyncClient):
        """Test task creation with invalid data."""
        # Arrange
        task_data = {
            # Missing both url and marketplace_plugin
            "platform": "manylinux2014_x86_64"
        }
        
        # Act
        response = await async_client.post("/api/v1/tasks", json=task_data)
        
        # Assert
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_get_task_status_success(self, async_client: AsyncClient, mock_redis):
        """Test getting task status successfully."""
        # Arrange
        task_id = str(uuid.uuid4())
        task_data = TaskFactory.create(
            task_id=task_id,
            status="processing",
            progress=50
        )
        mock_redis.get.return_value = json.dumps(task_data).encode('utf-8')
        
        # Act
        response = await async_client.get(f"/api/v1/tasks/{task_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "processing"
        assert data["progress"] == 50
    
    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self, async_client: AsyncClient, mock_redis):
        """Test getting status for non-existent task."""
        # Arrange
        task_id = str(uuid.uuid4())
        mock_redis.get.return_value = None
        
        # Act
        response = await async_client.get(f"/api/v1/tasks/{task_id}")
        
        # Assert
        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_cancel_task_success(self, async_client: AsyncClient, mock_redis, mock_celery):
        """Test canceling a task successfully."""
        # Arrange
        task_id = str(uuid.uuid4())
        task_data = TaskFactory.create(task_id=task_id, status="processing")
        mock_redis.get.return_value = json.dumps(task_data).encode('utf-8')
        mock_redis.set.return_value = True
        
        # Mock Celery control
        mock_control = Mock()
        mock_celery.control = mock_control
        
        # Act
        response = await async_client.post(f"/api/v1/tasks/{task_id}/cancel")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Task cancelled successfully"
        
        # Verify control.revoke was called
        mock_control.revoke.assert_called_once_with(task_id, terminate=True)
    
    @pytest.mark.asyncio
    async def test_download_task_result_success(self, async_client: AsyncClient, mock_redis, temp_directory):
        """Test downloading task result successfully."""
        # Arrange
        task_id = str(uuid.uuid4())
        output_file = f"{temp_directory}/output/{task_id}/plugin-offline.difypkg"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Create a test file
        with open(output_file, "wb") as f:
            f.write(b"Test plugin content")
        
        task_data = TaskFactory.create(
            task_id=task_id,
            status="completed",
            result={"output_file": output_file}
        )
        mock_redis.get.return_value = json.dumps(task_data).encode('utf-8')
        
        # Act
        response = await async_client.get(f"/api/v1/tasks/{task_id}/download")
        
        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        assert b"Test plugin content" in response.content
    
    @pytest.mark.asyncio
    async def test_download_task_result_not_ready(self, async_client: AsyncClient, mock_redis):
        """Test downloading result for incomplete task."""
        # Arrange
        task_id = str(uuid.uuid4())
        task_data = TaskFactory.create(task_id=task_id, status="processing")
        mock_redis.get.return_value = json.dumps(task_data).encode('utf-8')
        
        # Act
        response = await async_client.get(f"/api/v1/tasks/{task_id}/download")
        
        # Assert
        assert response.status_code == 400
        assert "Task not completed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_upload_file_success(self, async_client: AsyncClient, mock_celery, mock_redis, temp_directory):
        """Test uploading a file for repackaging."""
        # Arrange
        file_content = b"PK\x03\x04Test plugin content"
        files = {
            "file": ("test_plugin.difypkg", file_content, "application/zip")
        }
        data = {
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }
        expected_task_id = str(uuid.uuid4())
        
        with patch('app.api.v1.endpoints.tasks.uuid.uuid4', return_value=expected_task_id):
            with patch('app.api.v1.endpoints.tasks.FileManager') as mock_file_manager:
                mock_file_manager.return_value.save_uploaded_file = AsyncMock(
                    return_value=f"{temp_directory}/uploads/{expected_task_id}/test_plugin.difypkg"
                )
                mock_celery.send_task.return_value.id = expected_task_id
                mock_redis.set.return_value = True
                
                # Act
                response = await async_client.post(
                    "/api/v1/tasks/upload",
                    files=files,
                    data=data
                )
                
                # Assert
                assert response.status_code == 200
                result = response.json()
                assert result["task_id"] == expected_task_id
                assert result["status"] == "pending"
                assert result["type"] == "local"
    
    @pytest.mark.asyncio
    async def test_get_all_tasks(self, async_client: AsyncClient, mock_redis):
        """Test getting all tasks with pagination."""
        # Arrange
        task_keys = [f"task:{uuid.uuid4()}" for _ in range(5)]
        mock_redis.keys.return_value = task_keys
        
        # Mock task data for each key
        def mock_get(key):
            task_id = key.split(":")[1]
            return json.dumps(TaskFactory.create(task_id=task_id)).encode('utf-8')
        
        mock_redis.get.side_effect = mock_get
        
        # Act
        response = await async_client.get("/api/v1/tasks?page=1&page_size=3")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 3
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 3
    
    @pytest.mark.asyncio
    async def test_delete_task_success(self, async_client: AsyncClient, mock_redis, temp_directory):
        """Test deleting a task and its files."""
        # Arrange
        task_id = str(uuid.uuid4())
        task_data = TaskFactory.create(
            task_id=task_id,
            status="completed",
            result={"output_file": f"{temp_directory}/output/{task_id}/plugin.difypkg"}
        )
        mock_redis.get.return_value = json.dumps(task_data).encode('utf-8')
        mock_redis.delete.return_value = 1
        
        # Create task directory
        task_dir = f"{temp_directory}/output/{task_id}"
        os.makedirs(task_dir, exist_ok=True)
        
        # Act
        response = await async_client.delete(f"/api/v1/tasks/{task_id}")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Task deleted successfully"
        mock_redis.delete.assert_called_once_with(f"task:{task_id}")
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, async_client: AsyncClient):
        """Test rate limiting on task creation."""
        # This test would need a more complex setup to actually test rate limiting
        # For now, we just verify the rate limiter is applied
        from app.api.v1.endpoints.tasks import create_task
        
        # Check that the rate limiter decorator is applied
        assert hasattr(create_task, "_rate_limit")


class TestTaskValidation:
    """Test task validation logic."""
    
    def test_task_create_validation_both_url_and_marketplace(self):
        """Test validation when both URL and marketplace are provided."""
        from app.api.v1.endpoints.tasks import TaskCreateWithMarketplace
        
        with pytest.raises(ValueError):
            TaskCreateWithMarketplace(
                url="https://example.com/plugin.difypkg",
                marketplace_plugin={"author": "test", "name": "test", "version": "1.0.0"}
            )
    
    def test_task_create_validation_neither_url_nor_marketplace(self):
        """Test validation when neither URL nor marketplace is provided."""
        from app.api.v1.endpoints.tasks import TaskCreateWithMarketplace
        
        # This should be handled by the endpoint logic, not the model
        task = TaskCreateWithMarketplace(platform="linux")
        assert task.url is None
        assert task.marketplace_plugin is None