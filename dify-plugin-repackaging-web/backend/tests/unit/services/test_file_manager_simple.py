"""
Simple unit tests for FileManager focusing on testable logic.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import json
from datetime import datetime, timedelta
import tempfile

from app.services.file_manager import FileManager


class TestFileManagerBasics:
    """Test FileManager basic operations."""
    
    def test_file_manager_initialization(self):
        """Test FileManager initialization."""
        with patch('app.services.file_manager.settings') as mock_settings:
            mock_settings.TEMP_DIR = "/tmp/test"
            
            fm = FileManager()
            
            # Initialization doesn't create directories anymore
            assert hasattr(fm, 'get_file_path')
            assert hasattr(fm, 'list_completed_files')

    @patch('app.services.file_manager.settings')
    @patch('app.services.file_manager.redis_client')
    def test_get_file_info_exists(self, mock_redis, mock_settings):
        """Test getting file info when task exists."""
        mock_settings.TEMP_DIR = "/tmp"
        file_id = "test-123"
        
        task_data = {
            "task_id": file_id,
            "status": "completed",
            "output_filename": "test.difypkg",
            "created_at": "2024-01-01T00:00:00",
            "original_filename": "original.difypkg",
            "plugin_info": {"author": "test", "name": "plugin"}
        }
        mock_redis.get.return_value = json.dumps(task_data)
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            with patch('os.path.getsize', return_value=1024):
                result = FileManager.get_file_info(file_id)
                
                assert result is not None
                assert result["file_id"] == file_id
                assert result["filename"] == "test.difypkg"
                assert result["size"] == 1024

    @patch('app.services.file_manager.redis_client')
    def test_get_file_info_not_found(self, mock_redis):
        """Test getting file info when task doesn't exist."""
        mock_redis.get.return_value = None
        
        result = FileManager.get_file_info("nonexistent")
        
        assert result is None

    @patch('app.services.file_manager.redis_client')
    def test_get_file_info_not_completed(self, mock_redis):
        """Test getting file info for incomplete task."""
        task_data = {
            "task_id": "test-123",
            "status": "processing"
        }
        mock_redis.get.return_value = json.dumps(task_data)
        
        result = FileManager.get_file_info("test-123")
        
        assert result is None

    @patch('app.services.file_manager.settings')
    @patch('app.services.file_manager.redis_client')
    def test_get_file_path_success(self, mock_redis, mock_settings):
        """Test getting file path for completed task."""
        mock_settings.TEMP_DIR = "/tmp"
        file_id = "test-456"
        
        task_data = {
            "task_id": file_id,
            "status": "completed",
            "output_filename": "result.difypkg"
        }
        mock_redis.get.return_value = json.dumps(task_data)
        
        with patch('os.path.exists', return_value=True):
            result = FileManager.get_file_path(file_id)
            
            assert result == "/tmp/test-456/result.difypkg"

    @patch('app.services.file_manager.redis_client')
    def test_get_file_path_file_not_exists(self, mock_redis):
        """Test getting file path when file doesn't exist on disk."""
        task_data = {
            "task_id": "test-789",
            "status": "completed",
            "output_filename": "missing.difypkg"
        }
        mock_redis.get.return_value = json.dumps(task_data)
        
        with patch('os.path.exists', return_value=False):
            result = FileManager.get_file_path("test-789")
            
            assert result is None

    @patch('app.services.file_manager.settings')
    @patch('app.services.file_manager.redis_client')
    def test_delete_file_success(self, mock_redis, mock_settings):
        """Test successful file deletion."""
        mock_settings.TEMP_DIR = "/tmp"
        file_id = "delete-123"
        
        task_data = {
            "task_id": file_id,
            "status": "completed",
            "output_filename": "to-delete.difypkg"
        }
        mock_redis.get.return_value = json.dumps(task_data)
        mock_redis.delete.return_value = 1
        
        with patch('os.path.exists', return_value=True):
            with patch('shutil.rmtree') as mock_rmtree:
                result = FileManager.delete_file(file_id)
                
                assert result is True
                mock_rmtree.assert_called_once_with("/tmp/delete-123")
                mock_redis.delete.assert_called_once_with(f"task:{file_id}")

    @patch('app.services.file_manager.redis_client')
    def test_delete_file_not_found(self, mock_redis):
        """Test deleting non-existent file."""
        mock_redis.get.return_value = None
        
        result = FileManager.delete_file("nonexistent")
        
        assert result is False

    @patch('app.services.file_manager.settings')
    @patch('app.services.file_manager.redis_client')
    def test_delete_file_os_error(self, mock_redis, mock_settings):
        """Test handling OS errors during deletion."""
        mock_settings.TEMP_DIR = "/tmp"
        file_id = "error-delete"
        
        task_data = {
            "task_id": file_id,
            "status": "completed"
        }
        mock_redis.get.return_value = json.dumps(task_data)
        
        with patch('os.path.exists', return_value=True):
            with patch('shutil.rmtree', side_effect=OSError("Permission denied")):
                result = FileManager.delete_file(file_id)
                
                assert result is False


class TestFileManagerListOperations:
    """Test file listing operations."""
    
    @patch('app.services.file_manager.settings')
    @patch('app.services.file_manager.redis_client')
    def test_list_completed_files_empty(self, mock_redis, mock_settings):
        """Test listing files when none exist."""
        mock_settings.TEMP_DIR = "/tmp"
        mock_redis.keys.return_value = []
        
        result = FileManager.list_completed_files()
        
        assert result["files"] == []
        assert result["total"] == 0
        assert result["has_more"] is False

    @patch('app.services.file_manager.settings')
    @patch('app.services.file_manager.redis_client')
    def test_list_completed_files_with_pagination(self, mock_redis, mock_settings):
        """Test listing files with pagination."""
        mock_settings.TEMP_DIR = "/tmp"
        
        # Create 5 task keys
        task_keys = [f"task:{i}" for i in range(5)]
        mock_redis.keys.return_value = task_keys
        
        # Mock task data for each
        def get_side_effect(key):
            task_id = key.split(":")[1]
            return json.dumps({
                "task_id": task_id,
                "status": "completed",
                "output_filename": f"file-{task_id}.difypkg",
                "created_at": f"2024-01-0{task_id}T00:00:00"
            })
        
        mock_redis.get.side_effect = get_side_effect
        
        with patch('os.path.exists', return_value=True):
            with patch('os.path.getsize', return_value=1024):
                # Get first page
                result = FileManager.list_completed_files(limit=2, offset=0)
                
                assert len(result["files"]) == 2
                assert result["total"] == 5
                assert result["has_more"] is True
                
                # Get second page
                result = FileManager.list_completed_files(limit=2, offset=2)
                
                assert len(result["files"]) == 2
                assert result["has_more"] is True

    @patch('app.services.file_manager.settings')
    @patch('app.services.file_manager.redis_client')
    def test_list_completed_files_filters_incomplete(self, mock_redis, mock_settings):
        """Test that listing filters out incomplete tasks."""
        mock_settings.TEMP_DIR = "/tmp"
        
        task_keys = ["task:complete", "task:processing", "task:failed"]
        mock_redis.keys.return_value = task_keys
        
        def get_side_effect(key):
            task_id = key.split(":")[1]
            status = "completed" if task_id == "complete" else task_id
            data = {
                "task_id": task_id,
                "status": status,
                "created_at": "2024-01-01T00:00:00"
            }
            if status == "completed":
                data["output_filename"] = "output.difypkg"
            return json.dumps(data)
        
        mock_redis.get.side_effect = get_side_effect
        
        with patch('os.path.exists', return_value=True):
            with patch('os.path.getsize', return_value=1024):
                result = FileManager.list_completed_files()
                
                assert len(result["files"]) == 1
                assert result["files"][0]["file_id"] == "complete"


class TestFileManagerStorageStats:
    """Test storage statistics operations."""
    
    @patch('app.services.file_manager.settings')
    @patch('os.walk')
    def test_get_storage_stats_empty(self, mock_walk, mock_settings):
        """Test storage stats for empty directory."""
        mock_settings.TEMP_DIR = "/tmp/empty"
        mock_walk.return_value = []
        
        with patch('os.path.exists', return_value=True):
            result = FileManager.get_storage_stats()
            
            assert result["total_size"] == 0
            assert result["file_count"] == 0
            assert result["directory_count"] == 0

    @patch('app.services.file_manager.settings')
    @patch('os.walk')
    def test_get_storage_stats_with_files(self, mock_walk, mock_settings):
        """Test storage stats with files."""
        mock_settings.TEMP_DIR = "/tmp/test"
        
        # Mock directory structure
        mock_walk.return_value = [
            ("/tmp/test", ["task1", "task2"], []),
            ("/tmp/test/task1", [], ["file1.difypkg"]),
            ("/tmp/test/task2", [], ["file2.difypkg", "file3.difypkg"])
        ]
        
        def getsize_side_effect(path):
            if "file1" in path:
                return 1024
            elif "file2" in path:
                return 2048
            elif "file3" in path:
                return 512
            return 0
        
        def getmtime_side_effect(path):
            if "file1" in path:
                return 1704067200  # 2024-01-01
            elif "file2" in path:
                return 1704153600  # 2024-01-02
            elif "file3" in path:
                return 1704240000  # 2024-01-03
            return 0
        
        with patch('os.path.exists', return_value=True):
            with patch('os.path.getsize', side_effect=getsize_side_effect):
                with patch('os.path.getmtime', side_effect=getmtime_side_effect):
                    result = FileManager.get_storage_stats()
                    
                    assert result["total_size"] == 3584  # 1024 + 2048 + 512
                    assert result["file_count"] == 3
                    assert result["directory_count"] == 2
                    assert result["total_size_mb"] == pytest.approx(3584 / (1024 * 1024), rel=0.01)


class TestFileManagerCleanup:
    """Test cleanup operations."""
    
    @patch('app.services.file_manager.settings')
    @patch('app.services.file_manager.redis_client')
    def test_cleanup_old_files_none_to_clean(self, mock_redis, mock_settings):
        """Test cleanup when no files are old enough."""
        mock_settings.TEMP_DIR = "/tmp"
        mock_settings.FILE_RETENTION_DAYS = 7
        
        task_keys = ["task:new1", "task:new2"]
        mock_redis.keys.return_value = task_keys
        
        # All tasks are recent
        recent_time = datetime.utcnow() - timedelta(days=1)
        task_data = {
            "task_id": "new1",
            "status": "completed",
            "created_at": recent_time.isoformat()
        }
        mock_redis.get.return_value = json.dumps(task_data)
        
        result = FileManager.cleanup_old_files()
        
        assert result == 0

    @patch('app.services.file_manager.settings')
    @patch('app.services.file_manager.redis_client')
    def test_cleanup_old_files_with_retention(self, mock_redis, mock_settings):
        """Test cleanup with custom retention period."""
        mock_settings.TEMP_DIR = "/tmp"
        
        task_keys = ["task:old", "task:new"]
        mock_redis.keys.return_value = task_keys
        
        def get_side_effect(key):
            task_id = key.split(":")[1]
            if task_id == "old":
                created = datetime.utcnow() - timedelta(days=10)
            else:
                created = datetime.utcnow() - timedelta(days=1)
            
            return json.dumps({
                "task_id": task_id,
                "status": "completed",
                "created_at": created.isoformat()
            })
        
        mock_redis.get.side_effect = get_side_effect
        
        with patch.object(FileManager, 'delete_file', return_value=True) as mock_delete:
            result = FileManager.cleanup_old_files(retention_days=5)
            
            assert result == 1
            mock_delete.assert_called_once_with("old")