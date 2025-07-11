"""
Comprehensive unit tests for files API endpoints to increase coverage.
Focus on FileManager interactions, error handling, and edge cases.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from httpx import AsyncClient
import os
import tempfile
from datetime import datetime

from app.api.v1.endpoints.files import (
    list_files, download_file, get_file_info,
    get_storage_stats, delete_file, cleanup_old_files
)
from app.services.file_manager import FileManager


class TestListFilesEndpoint:
    """Test list_files endpoint with comprehensive coverage."""
    
    @pytest.mark.asyncio
    async def test_list_files_success(self, async_client: AsyncClient):
        """Test successful file listing with pagination."""
        # Arrange
        expected_result = {
            "files": [
                {
                    "file_id": "123",
                    "filename": "plugin-offline.difypkg",
                    "original_filename": "plugin.difypkg",
                    "size": 1024,
                    "created_at": "2024-01-15T10:30:00Z",
                    "plugin_info": {
                        "author": "test",
                        "name": "plugin",
                        "version": "1.0.0"
                    },
                    "download_url": "/api/v1/files/123/download"
                }
            ],
            "total": 1,
            "limit": 50,
            "offset": 0,
            "has_more": False
        }
        
        with patch.object(FileManager, 'list_completed_files', return_value=expected_result):
            # Act
            response = await async_client.get("/api/v1/files")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data["files"]) == 1
            assert data["files"][0]["file_id"] == "123"
            assert data["total"] == 1
            assert data["has_more"] is False

    @pytest.mark.asyncio
    async def test_list_files_with_pagination(self, async_client: AsyncClient):
        """Test file listing with custom pagination parameters."""
        # Arrange
        with patch.object(FileManager, 'list_completed_files') as mock_list:
            mock_list.return_value = {
                "files": [],
                "total": 100,
                "limit": 20,
                "offset": 40,
                "has_more": True
            }
            
            # Act
            response = await async_client.get("/api/v1/files?limit=20&offset=40")
            
            # Assert
            assert response.status_code == 200
            mock_list.assert_called_once_with(limit=20, offset=40)
            data = response.json()
            assert data["has_more"] is True
            assert data["offset"] == 40

    @pytest.mark.asyncio
    async def test_list_files_invalid_pagination(self, async_client: AsyncClient):
        """Test file listing with invalid pagination parameters."""
        # Act & Assert - Test limit too high
        response = await async_client.get("/api/v1/files?limit=300")
        assert response.status_code == 422  # Validation error
        
        # Act & Assert - Test negative offset
        response = await async_client.get("/api/v1/files?offset=-1")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_files_exception(self, async_client: AsyncClient):
        """Test handling exceptions in list_files."""
        # Arrange
        with patch.object(FileManager, 'list_completed_files', side_effect=Exception("Database error")):
            # Act
            response = await async_client.get("/api/v1/files")
            
            # Assert
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]


class TestDownloadFileEndpoint:
    """Test download_file endpoint coverage."""
    
    @pytest.mark.asyncio
    async def test_download_file_success(self, async_client: AsyncClient, temp_directory):
        """Test successful file download."""
        # Arrange
        file_id = "test-123"
        file_content = b"Test plugin content"
        file_path = os.path.join(temp_directory, "test.difypkg")
        
        # Create test file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        with patch.object(FileManager, 'get_file_path', return_value=file_path):
            with patch.object(FileManager, 'get_file_info', return_value={"filename": "test-offline.difypkg"}):
                # Act
                response = await async_client.get(f"/api/v1/files/{file_id}/download")
                
                # Assert
                assert response.status_code == 200
                assert response.headers["content-type"] == "application/octet-stream"
                assert response.content == file_content

    @pytest.mark.asyncio
    async def test_download_file_not_found(self, async_client: AsyncClient):
        """Test downloading non-existent file."""
        # Arrange
        file_id = "nonexistent"
        
        with patch.object(FileManager, 'get_file_path', return_value=None):
            # Act
            response = await async_client.get(f"/api/v1/files/{file_id}/download")
            
            # Assert
            assert response.status_code == 404
            assert "File not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_download_file_no_filename(self, async_client: AsyncClient, temp_directory):
        """Test download when file info is missing."""
        # Arrange
        file_id = "test-456"
        file_path = os.path.join(temp_directory, "test.difypkg")
        
        with open(file_path, "wb") as f:
            f.write(b"content")
        
        with patch.object(FileManager, 'get_file_path', return_value=file_path):
            with patch.object(FileManager, 'get_file_info', return_value=None):
                # Act
                response = await async_client.get(f"/api/v1/files/{file_id}/download")
                
                # Assert
                assert response.status_code == 200
                # Should use default filename
                assert response.headers.get("content-disposition") is not None

    @pytest.mark.asyncio
    async def test_download_file_exception(self, async_client: AsyncClient):
        """Test handling exceptions during download."""
        # Arrange
        file_id = "error-test"
        
        with patch.object(FileManager, 'get_file_path', side_effect=Exception("Storage error")):
            # Act
            response = await async_client.get(f"/api/v1/files/{file_id}/download")
            
            # Assert
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]


class TestGetFileInfoEndpoint:
    """Test get_file_info endpoint coverage."""
    
    @pytest.mark.asyncio
    async def test_get_file_info_success(self, async_client: AsyncClient):
        """Test getting file info successfully."""
        # Arrange
        file_id = "info-123"
        file_info = {
            "file_id": file_id,
            "filename": "plugin-offline.difypkg",
            "original_filename": "plugin.difypkg",
            "size": 2048,
            "created_at": "2024-01-15T10:30:00Z",
            "platform": "manylinux2014_x86_64",
            "suffix": "offline",
            "marketplace_metadata": {
                "source": "marketplace",
                "author": "test",
                "name": "plugin",
                "version": "1.0.0"
            }
        }
        
        with patch.object(FileManager, 'get_file_info', return_value=file_info):
            # Act
            response = await async_client.get(f"/api/v1/files/{file_id}")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["file_id"] == file_id
            assert data["platform"] == "manylinux2014_x86_64"
            assert data["marketplace_metadata"]["author"] == "test"

    @pytest.mark.asyncio
    async def test_get_file_info_not_found(self, async_client: AsyncClient):
        """Test getting info for non-existent file."""
        # Arrange
        file_id = "nonexistent"
        
        with patch.object(FileManager, 'get_file_info', return_value=None):
            # Act
            response = await async_client.get(f"/api/v1/files/{file_id}")
            
            # Assert
            assert response.status_code == 404
            assert "File not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_file_info_exception(self, async_client: AsyncClient):
        """Test handling exceptions in get_file_info."""
        # Arrange
        file_id = "error-test"
        
        with patch.object(FileManager, 'get_file_info', side_effect=Exception("Database error")):
            # Act
            response = await async_client.get(f"/api/v1/files/{file_id}")
            
            # Assert
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]


class TestGetStorageStatsEndpoint:
    """Test get_storage_stats endpoint coverage."""
    
    @pytest.mark.asyncio
    async def test_get_storage_stats_success(self, async_client: AsyncClient):
        """Test getting storage statistics successfully."""
        # Arrange
        stats = {
            "total_size": 1073741824,  # 1GB
            "total_size_mb": 1024.0,
            "file_count": 42,
            "directory_count": 42,
            "oldest_file": "2024-01-01T00:00:00Z",
            "newest_file": "2024-01-15T12:00:00Z"
        }
        
        with patch.object(FileManager, 'get_storage_stats', return_value=stats):
            # Act
            response = await async_client.get("/api/v1/files/stats/storage")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["total_size"] == 1073741824
            assert data["file_count"] == 42
            assert data["oldest_file"] == "2024-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_get_storage_stats_empty(self, async_client: AsyncClient):
        """Test storage stats when no files exist."""
        # Arrange
        stats = {
            "total_size": 0,
            "total_size_mb": 0.0,
            "file_count": 0,
            "directory_count": 0,
            "oldest_file": None,
            "newest_file": None
        }
        
        with patch.object(FileManager, 'get_storage_stats', return_value=stats):
            # Act
            response = await async_client.get("/api/v1/files/stats/storage")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["total_size"] == 0
            assert data["file_count"] == 0

    @pytest.mark.asyncio
    async def test_get_storage_stats_exception(self, async_client: AsyncClient):
        """Test handling exceptions in storage stats."""
        # Arrange
        with patch.object(FileManager, 'get_storage_stats', side_effect=Exception("IO error")):
            # Act
            response = await async_client.get("/api/v1/files/stats/storage")
            
            # Assert
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]


class TestDeleteFileEndpoint:
    """Test delete_file endpoint coverage."""
    
    @pytest.mark.asyncio
    async def test_delete_file_success(self, async_client: AsyncClient):
        """Test successful file deletion."""
        # Arrange
        file_id = "delete-123"
        file_info = {
            "file_id": file_id,
            "filename": "plugin-offline.difypkg"
        }
        
        with patch.object(FileManager, 'get_file_info', return_value=file_info):
            with patch.object(FileManager, 'delete_file', return_value=True):
                # Act
                response = await async_client.delete(f"/api/v1/files/{file_id}")
                
                # Assert
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "File deleted successfully"
                assert data["file_id"] == file_id

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, async_client: AsyncClient):
        """Test deleting non-existent file."""
        # Arrange
        file_id = "nonexistent"
        
        with patch.object(FileManager, 'get_file_info', return_value=None):
            # Act
            response = await async_client.delete(f"/api/v1/files/{file_id}")
            
            # Assert
            assert response.status_code == 404
            assert "File not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_file_failed(self, async_client: AsyncClient):
        """Test when file deletion fails."""
        # Arrange
        file_id = "fail-delete"
        file_info = {"file_id": file_id}
        
        with patch.object(FileManager, 'get_file_info', return_value=file_info):
            with patch.object(FileManager, 'delete_file', return_value=False):
                # Act
                response = await async_client.delete(f"/api/v1/files/{file_id}")
                
                # Assert
                assert response.status_code == 500
                assert "Failed to delete file" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_file_exception(self, async_client: AsyncClient):
        """Test handling exceptions during deletion."""
        # Arrange
        file_id = "error-delete"
        
        with patch.object(FileManager, 'get_file_info', side_effect=Exception("Permission denied")):
            # Act
            response = await async_client.delete(f"/api/v1/files/{file_id}")
            
            # Assert
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]


class TestCleanupOldFilesEndpoint:
    """Test cleanup_old_files endpoint coverage."""
    
    @pytest.mark.asyncio
    async def test_cleanup_old_files_default_retention(self, async_client: AsyncClient):
        """Test cleanup with default retention period."""
        # Arrange
        with patch.object(FileManager, 'cleanup_old_files', return_value=10):
            with patch('app.api.v1.endpoints.files.settings.FILE_RETENTION_DAYS', 7):
                # Act
                response = await async_client.delete("/api/v1/files/cleanup")
                
                # Assert
                assert response.status_code == 200
                data = response.json()
                assert data["cleaned_count"] == 10
                assert data["retention_days"] == 7
                assert "Cleaned up 10 old files" in data["message"]

    @pytest.mark.asyncio
    async def test_cleanup_old_files_custom_retention(self, async_client: AsyncClient):
        """Test cleanup with custom retention period."""
        # Arrange
        with patch.object(FileManager, 'cleanup_old_files', return_value=5) as mock_cleanup:
            # Act
            response = await async_client.delete("/api/v1/files/cleanup?retention_days=30")
            
            # Assert
            assert response.status_code == 200
            mock_cleanup.assert_called_once_with(30)
            data = response.json()
            assert data["cleaned_count"] == 5
            assert data["retention_days"] == 30

    @pytest.mark.asyncio
    async def test_cleanup_old_files_invalid_retention(self, async_client: AsyncClient):
        """Test cleanup with invalid retention period."""
        # Act & Assert - Too low
        response = await async_client.delete("/api/v1/files/cleanup?retention_days=0")
        assert response.status_code == 422
        
        # Act & Assert - Too high
        response = await async_client.delete("/api/v1/files/cleanup?retention_days=400")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_cleanup_old_files_no_files_to_clean(self, async_client: AsyncClient):
        """Test cleanup when no files need cleaning."""
        # Arrange
        with patch.object(FileManager, 'cleanup_old_files', return_value=0):
            # Act
            response = await async_client.delete("/api/v1/files/cleanup")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["cleaned_count"] == 0
            assert "Cleaned up 0 old files" in data["message"]

    @pytest.mark.asyncio
    async def test_cleanup_old_files_exception(self, async_client: AsyncClient):
        """Test handling exceptions during cleanup."""
        # Arrange
        with patch.object(FileManager, 'cleanup_old_files', side_effect=Exception("Permission error")):
            # Act
            response = await async_client.delete("/api/v1/files/cleanup")
            
            # Assert
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]


class TestFileManagerIntegration:
    """Test FileManager integration points in files endpoints."""
    
    @pytest.mark.asyncio
    async def test_file_manager_error_propagation(self, async_client: AsyncClient):
        """Test that FileManager errors are properly propagated."""
        # Test various FileManager errors
        error_scenarios = [
            ("list_completed_files", "/api/v1/files", "get"),
            ("get_storage_stats", "/api/v1/files/stats/storage", "get"),
        ]
        
        for method_name, endpoint, http_method in error_scenarios:
            with patch.object(FileManager, method_name, side_effect=OSError("Disk full")):
                # Act
                if http_method == "get":
                    response = await async_client.get(endpoint)
                else:
                    response = await async_client.delete(endpoint)
                
                # Assert
                assert response.status_code == 500
                assert "Internal server error" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self, async_client: AsyncClient):
        """Test handling concurrent file operations."""
        # Arrange
        file_ids = ["file1", "file2", "file3"]
        
        # Mock FileManager to simulate concurrent access
        with patch.object(FileManager, 'get_file_info') as mock_get_info:
            # Simulate different states for concurrent requests
            mock_get_info.side_effect = [
                {"file_id": "file1", "filename": "file1.difypkg"},
                None,  # file2 doesn't exist
                {"file_id": "file3", "filename": "file3.difypkg"}
            ]
            
            # Act - Make concurrent-like requests
            responses = []
            for file_id in file_ids:
                response = await async_client.get(f"/api/v1/files/{file_id}")
                responses.append((file_id, response.status_code))
            
            # Assert
            assert responses[0][1] == 200  # file1 exists
            assert responses[1][1] == 404  # file2 not found
            assert responses[2][1] == 200  # file3 exists