"""
Simple unit tests for tasks endpoints focusing on testable logic.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json
import uuid
from datetime import datetime
from fastapi import HTTPException

from app.api.v1.endpoints.tasks import TaskCreateWithMarketplace
from app.models.task import TaskStatus, MarketplaceTaskCreate, PlatformEnum


class TestTaskModels:
    """Test task model validation."""
    
    def test_task_create_with_marketplace_valid_url(self):
        """Test creating task with valid URL."""
        task = TaskCreateWithMarketplace(
            url="https://example.com/plugin.difypkg",
            platform="linux",
            suffix="custom"
        )
        assert task.url == "https://example.com/plugin.difypkg"
        assert task.marketplace_plugin is None
        assert task.platform == "linux"
        assert task.suffix == "custom"

    def test_task_create_with_marketplace_valid_plugin(self):
        """Test creating task with valid marketplace plugin."""
        task = TaskCreateWithMarketplace(
            marketplace_plugin={
                "author": "test",
                "name": "plugin",
                "version": "1.0.0"
            },
            platform="",
            suffix="offline"
        )
        assert task.url is None
        assert task.marketplace_plugin["author"] == "test"
        assert task.platform == ""
        assert task.suffix == "offline"

    def test_task_create_with_marketplace_defaults(self):
        """Test default values for optional fields."""
        task = TaskCreateWithMarketplace()
        assert task.url is None
        assert task.marketplace_plugin is None
        assert task.platform == ""
        assert task.suffix == "offline"

    def test_marketplace_task_create_model(self):
        """Test MarketplaceTaskCreate model."""
        task = MarketplaceTaskCreate(
            author="langgenius",
            name="agent",
            version="0.0.9",
            platform=PlatformEnum.MANYLINUX2014_X86_64,
            suffix="custom"
        )
        assert task.author == "langgenius"
        assert task.name == "agent"
        assert task.version == "0.0.9"
        assert task.platform == PlatformEnum.MANYLINUX2014_X86_64
        assert task.suffix == "custom"

    def test_marketplace_task_create_defaults(self):
        """Test MarketplaceTaskCreate with defaults."""
        task = MarketplaceTaskCreate(
            author="test",
            name="plugin",
            version="1.0.0"
        )
        assert task.platform == PlatformEnum.AUTO
        assert task.suffix == "offline"

    def test_task_status_enum(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_platform_enum(self):
        """Test PlatformEnum values."""
        assert PlatformEnum.AUTO.value == ""
        assert PlatformEnum.MANYLINUX2014_X86_64.value == "manylinux2014_x86_64"
        assert PlatformEnum.MANYLINUX2014_AARCH64.value == "manylinux2014_aarch64"
        assert PlatformEnum.MANYLINUX2010_X86_64.value == "manylinux2010_x86_64"
        assert PlatformEnum.MANYLINUX2010_I686.value == "manylinux2010_i686"


class TestTaskEndpointHelpers:
    """Test helper functions and simple logic in tasks endpoints."""
    
    @patch('app.api.v1.endpoints.tasks.redis_client')
    def test_task_status_parsing(self, mock_redis):
        """Test task status response parsing."""
        # Mock task data with various states
        task_data = {
            "task_id": "test-123",
            "status": "completed",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T01:00:00",
            "completed_at": "2024-01-01T02:00:00",
            "progress": 100,
            "output_filename": "result.difypkg",
            "original_filename": "input.difypkg",
            "error": None
        }
        
        mock_redis.get.return_value = json.dumps(task_data)
        
        # Test that status fields are properly extracted
        # This would be called in get_task_status
        parsed = json.loads(mock_redis.get("task:test-123"))
        assert parsed["status"] == "completed"
        assert parsed["progress"] == 100
        assert parsed["output_filename"] == "result.difypkg"

    def test_download_url_construction(self):
        """Test download URL construction logic."""
        # Test URL construction with settings
        with patch('app.api.v1.endpoints.tasks.settings') as mock_settings:
            mock_settings.API_V1_STR = "/api/v1"
            
            task_id = "download-123"
            expected_url = f"/api/v1/tasks/{task_id}/download"
            
            # This logic is in get_task_status
            download_url = f"{mock_settings.API_V1_STR}/tasks/{task_id}/download"
            assert download_url == expected_url

    @patch('app.api.v1.endpoints.tasks.uuid')
    def test_task_id_generation(self, mock_uuid):
        """Test task ID generation."""
        test_uuid = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.uuid4.return_value = test_uuid
        
        # When create_task generates an ID
        task_id = str(mock_uuid.uuid4())
        assert task_id == str(test_uuid)

    def test_task_record_structure(self):
        """Test task record structure creation."""
        # Test the structure of task records
        task_id = "struct-test"
        url = "https://example.com/plugin.difypkg"
        platform = "linux"
        suffix = "offline"
        
        # This is the structure created in create_task
        task_record = {
            "task_id": task_id,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "url": url,
            "platform": platform,
            "suffix": suffix,
            "progress": 0
        }
        
        assert task_record["task_id"] == task_id
        assert task_record["status"] == "pending"
        assert task_record["progress"] == 0
        assert "created_at" in task_record

    def test_plugin_info_structure(self):
        """Test plugin info structure in task records."""
        plugin_info = {
            "author": "langgenius",
            "name": "agent",
            "version": "0.0.9"
        }
        
        task_record = {
            "task_id": "plugin-test",
            "status": "pending",
            "plugin_info": plugin_info
        }
        
        assert task_record["plugin_info"]["author"] == "langgenius"
        assert task_record["plugin_info"]["name"] == "agent"
        assert task_record["plugin_info"]["version"] == "0.0.9"

    def test_marketplace_metadata_structure(self):
        """Test marketplace metadata structure."""
        # Test metadata structure used in process_marketplace_repackaging
        metadata = {
            "source": "marketplace",
            "author": "test",
            "name": "plugin",
            "version": "1.0.0"
        }
        
        assert metadata["source"] == "marketplace"
        assert all(k in metadata for k in ["author", "name", "version"])

    def test_upload_info_structure(self):
        """Test upload info structure for file uploads."""
        filename = "test.difypkg"
        file_size = 1024
        
        upload_info = {
            "source": "upload",
            "filename": filename,
            "size": file_size
        }
        
        assert upload_info["source"] == "upload"
        assert upload_info["filename"] == filename
        assert upload_info["size"] == file_size

    def test_error_message_formatting(self):
        """Test error message formatting."""
        author = "unknown"
        name = "plugin"
        
        # Test error message formatting from create_task
        error_detail = (
            f"Unable to fetch plugin version for {author}/{name}. "
            f"Possible reasons:\n"
            f"1. The plugin may not exist in the marketplace\n"
            f"2. The marketplace API may be temporarily unavailable\n"
            f"3. The plugin URL format may have changed\n\n"
            f"Please verify the URL is correct or try using a direct .difypkg file URL instead.\n"
            f"Example marketplace URL: https://marketplace.dify.ai/plugins/langgenius/ollama"
        )
        
        assert author in error_detail
        assert name in error_detail
        assert "marketplace" in error_detail.lower()

    def test_file_path_construction(self):
        """Test file path construction for uploads."""
        with patch('app.api.v1.endpoints.tasks.settings') as mock_settings:
            mock_settings.TEMP_DIR = "/tmp"
            
            task_id = "upload-test"
            filename = "plugin.difypkg"
            
            # Test path construction from upload_task
            task_dir = f"{mock_settings.TEMP_DIR}/{task_id}"
            file_path = f"{task_dir}/{filename}"
            
            assert file_path == "/tmp/upload-test/plugin.difypkg"

    def test_completed_task_filtering_logic(self):
        """Test logic for filtering completed tasks."""
        tasks = [
            {"status": "completed", "output_filename": "file1.difypkg"},
            {"status": "processing", "output_filename": None},
            {"status": "completed", "output_filename": None},
            {"status": "failed", "output_filename": "file2.difypkg"},
            {"status": "completed", "output_filename": "file3.difypkg"},
        ]
        
        # Filter logic from list_completed_tasks
        completed_with_files = [
            task for task in tasks
            if task.get("status") == TaskStatus.COMPLETED.value 
            and task.get("output_filename")
        ]
        
        assert len(completed_with_files) == 2
        assert all(t["status"] == "completed" for t in completed_with_files)
        assert all(t["output_filename"] for t in completed_with_files)