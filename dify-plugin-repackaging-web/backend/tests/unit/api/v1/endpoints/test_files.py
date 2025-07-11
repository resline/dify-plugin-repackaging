"""
Unit tests for files API endpoints
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import os
import json
from datetime import datetime
from pathlib import Path
from httpx import AsyncClient

from app.api.v1.endpoints.files import router
from app.services.file_manager import FileManager


class TestFilesEndpoint:
    """Test cases for files endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_files_success(self, async_client: AsyncClient, temp_directory):
        """Test listing files successfully."""
        # Arrange
        mock_files = [
            {
                "file_id": "task-123",
                "filename": "plugin-offline.difypkg",
                "original_filename": "plugin.difypkg",
                "size": 1024000,
                "created_at": "2024-01-15T10:30:00Z",
                "plugin_info": {
                    "author": "langgenius",
                    "name": "agent",
                    "version": "0.0.9"
                },
                "download_url": "/api/v1/files/task-123/download"
            },
            {
                "file_id": "task-456",
                "filename": "another-plugin-offline.difypkg",
                "original_filename": "another-plugin.difypkg",
                "size": 2048000,
                "created_at": "2024-01-16T11:00:00Z",
                "plugin_info": None,
                "download_url": "/api/v1/files/task-456/download"
            }
        ]
        
        with patch('app.api.v1.endpoints.files.FileManager') as mock_manager:
            mock_manager.return_value.list_completed_files = AsyncMock(
                return_value={
                    "files": mock_files,
                    "total": 2,
                    "limit": 50,
                    "offset": 0
                }
            )
            
            # Act
            response = await async_client.get("/api/v1/files")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data["files"]) == 2
            assert data["total"] == 2
            assert data["files"][0]["file_id"] == "task-123"
            assert data["files"][1]["size"] == 2048000
    
    @pytest.mark.asyncio
    async def test_list_files_with_pagination(self, async_client: AsyncClient):
        """Test listing files with pagination."""
        # Arrange
        with patch('app.api.v1.endpoints.files.FileManager') as mock_manager:
            mock_manager.return_value.list_completed_files = AsyncMock(
                return_value={
                    "files": [],
                    "total": 100,
                    "limit": 20,
                    "offset": 40
                }
            )
            
            # Act
            response = await async_client.get("/api/v1/files?limit=20&offset=40")
            
            # Assert
            assert response.status_code == 200
            mock_manager.return_value.list_completed_files.assert_called_once_with(
                limit=20,
                offset=40
            )
    
    @pytest.mark.asyncio
    async def test_list_files_validation(self, async_client: AsyncClient):
        """Test parameter validation for list files."""
        # Test invalid limit
        response = await async_client.get("/api/v1/files?limit=201")
        assert response.status_code == 422
        
        response = await async_client.get("/api/v1/files?limit=0")
        assert response.status_code == 422
        
        # Test invalid offset
        response = await async_client.get("/api/v1/files?offset=-1")
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_download_file_success(self, async_client: AsyncClient, temp_directory):
        """Test downloading a file successfully."""
        # Arrange
        file_id = "task-123"
        file_content = b"Test plugin content"
        file_path = os.path.join(temp_directory, "output", file_id, "plugin-offline.difypkg")
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        with patch('app.api.v1.endpoints.files.FileManager') as mock_manager:
            mock_manager.return_value.get_file_path = Mock(return_value=file_path)
            
            # Act
            response = await async_client.get(f"/api/v1/files/{file_id}/download")
            
            # Assert
            assert response.status_code == 200
            assert response.content == file_content
            assert response.headers["content-type"] == "application/octet-stream"
            assert "content-disposition" in response.headers
    
    @pytest.mark.asyncio
    async def test_download_file_not_found(self, async_client: AsyncClient):
        """Test downloading non-existent file."""
        # Arrange
        file_id = "non-existent"
        
        with patch('app.api.v1.endpoints.files.FileManager') as mock_manager:
            mock_manager.return_value.get_file_path = Mock(return_value=None)
            
            # Act
            response = await async_client.get(f"/api/v1/files/{file_id}/download")
            
            # Assert
            assert response.status_code == 404
            assert "File not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_file_success(self, async_client: AsyncClient, temp_directory):
        """Test deleting a file successfully."""
        # Arrange
        file_id = "task-123"
        file_path = os.path.join(temp_directory, "output", file_id, "plugin-offline.difypkg")
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(b"Test content")
        
        with patch('app.api.v1.endpoints.files.FileManager') as mock_manager:
            mock_manager.return_value.delete_file = AsyncMock(return_value=True)
            
            # Act
            response = await async_client.delete(f"/api/v1/files/{file_id}")
            
            # Assert
            assert response.status_code == 200
            assert response.json()["message"] == "File deleted successfully"
            mock_manager.return_value.delete_file.assert_called_once_with(file_id)
    
    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, async_client: AsyncClient):
        """Test deleting non-existent file."""
        # Arrange
        file_id = "non-existent"
        
        with patch('app.api.v1.endpoints.files.FileManager') as mock_manager:
            mock_manager.return_value.delete_file = AsyncMock(return_value=False)
            
            # Act
            response = await async_client.delete(f"/api/v1/files/{file_id}")
            
            # Assert
            assert response.status_code == 404
            assert "File not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_file_info_success(self, async_client: AsyncClient):
        """Test getting file information."""
        # Arrange
        file_id = "task-123"
        file_info = {
            "file_id": file_id,
            "filename": "plugin-offline.difypkg",
            "original_filename": "plugin.difypkg",
            "size": 1024000,
            "created_at": "2024-01-15T10:30:00Z",
            "plugin_info": {
                "author": "langgenius",
                "name": "agent",
                "version": "0.0.9"
            },
            "md5": "d41d8cd98f00b204e9800998ecf8427e",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        }
        
        with patch('app.api.v1.endpoints.files.FileManager') as mock_manager:
            mock_manager.return_value.get_file_info = AsyncMock(return_value=file_info)
            
            # Act
            response = await async_client.get(f"/api/v1/files/{file_id}")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["file_id"] == file_id
            assert data["size"] == 1024000
            assert "md5" in data
            assert "sha256" in data
    
    @pytest.mark.asyncio
    async def test_get_file_info_not_found(self, async_client: AsyncClient):
        """Test getting info for non-existent file."""
        # Arrange
        file_id = "non-existent"
        
        with patch('app.api.v1.endpoints.files.FileManager') as mock_manager:
            mock_manager.return_value.get_file_info = AsyncMock(return_value=None)
            
            # Act
            response = await async_client.get(f"/api/v1/files/{file_id}")
            
            # Assert
            assert response.status_code == 404
            assert "File not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_cleanup_old_files(self, async_client: AsyncClient):
        """Test cleanup of old files endpoint."""
        # Arrange
        with patch('app.api.v1.endpoints.files.FileManager') as mock_manager:
            mock_manager.return_value.cleanup_old_files = AsyncMock(
                return_value={
                    "deleted_count": 5,
                    "freed_space": 10485760  # 10 MB
                }
            )
            
            # Act
            response = await async_client.post("/api/v1/files/cleanup?days=7")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["deleted_count"] == 5
            assert data["freed_space"] == 10485760
            mock_manager.return_value.cleanup_old_files.assert_called_once_with(days=7)
    
    @pytest.mark.asyncio
    async def test_get_storage_stats(self, async_client: AsyncClient):
        """Test getting storage statistics."""
        # Arrange
        with patch('app.api.v1.endpoints.files.FileManager') as mock_manager:
            mock_manager.return_value.get_storage_stats = AsyncMock(
                return_value={
                    "total_files": 50,
                    "total_size": 524288000,  # 500 MB
                    "average_file_size": 10485760,  # 10 MB
                    "largest_file": {
                        "file_id": "task-789",
                        "filename": "large-plugin.difypkg",
                        "size": 104857600  # 100 MB
                    },
                    "storage_by_date": {
                        "2024-01-15": 5,
                        "2024-01-16": 10
                    }
                }
            )
            
            # Act
            response = await async_client.get("/api/v1/files/stats")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["total_files"] == 50
            assert data["total_size"] == 524288000
            assert "largest_file" in data
            assert "storage_by_date" in data


class TestFileManagerIntegration:
    """Integration tests for FileManager service."""
    
    @pytest.mark.asyncio
    async def test_file_lifecycle(self, async_client: AsyncClient, temp_directory, mock_file_manager):
        """Test complete file lifecycle: create, list, download, delete."""
        # Arrange
        file_id = "test-lifecycle"
        file_content = b"Test lifecycle content"
        
        # Create file
        file_path = mock_file_manager.get_output_path(file_id, "plugin-offline.difypkg")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        with patch('app.api.v1.endpoints.files.FileManager', return_value=mock_file_manager):
            # List files
            response = await async_client.get("/api/v1/files")
            assert response.status_code == 200
            
            # Get file info
            file_info = await mock_file_manager.get_file_info(file_id)
            assert file_info is not None
            
            # Download file
            assert os.path.exists(file_path)
            
            # Delete file
            await mock_file_manager.delete_file(file_id)
            assert not os.path.exists(file_path)
    
    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self, async_client: AsyncClient, mock_file_manager):
        """Test concurrent file operations."""
        # Arrange
        file_ids = [f"concurrent-{i}" for i in range(5)]
        
        with patch('app.api.v1.endpoints.files.FileManager', return_value=mock_file_manager):
            # Create multiple files concurrently
            import asyncio
            
            async def create_file(file_id):
                path = mock_file_manager.get_output_path(file_id, "test.difypkg")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as f:
                    f.write(f"Content for {file_id}".encode())
                return file_id
            
            # Create files
            created = await asyncio.gather(*[create_file(fid) for fid in file_ids])
            assert len(created) == 5
            
            # List all files
            files = await mock_file_manager.list_completed_files()
            assert files["total"] >= 5