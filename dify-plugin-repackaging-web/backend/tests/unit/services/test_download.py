"""
Unit tests for download service
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import httpx
import os
import tempfile
from pathlib import Path

from app.services.download import DownloadService
from app.core.config import settings


class TestDownloadService:
    """Test cases for DownloadService."""
    
    @pytest.fixture
    def download_service(self):
        """Create a DownloadService instance."""
        return DownloadService()
    
    @pytest.fixture
    def mock_allowed_domains(self, monkeypatch):
        """Mock allowed download domains."""
        monkeypatch.setattr(
            settings, 
            "ALLOWED_DOWNLOAD_DOMAINS",
            ["github.com", "marketplace.dify.ai", "example.com"]
        )
    
    def test_validate_url_success(self, download_service, mock_allowed_domains):
        """Test URL validation with allowed domains."""
        # Test various allowed URLs
        valid_urls = [
            "https://github.com/owner/repo/releases/download/v1.0.0/plugin.difypkg",
            "https://marketplace.dify.ai/api/v1/plugins/download/test.difypkg",
            "https://www.github.com/file.zip",
            "https://example.com/downloads/plugin.difypkg",
            "http://marketplace.dify.ai/file"  # HTTP should also work
        ]
        
        for url in valid_urls:
            assert download_service.validate_url(url) is True, f"URL should be valid: {url}"
    
    def test_validate_url_failure(self, download_service, mock_allowed_domains):
        """Test URL validation with disallowed domains."""
        # Test various disallowed URLs
        invalid_urls = [
            "https://malicious.com/plugin.difypkg",
            "https://github.evil.com/file.zip",
            "https://marketplace-dify.ai/file",  # Similar but not exact
            "ftp://github.com/file",  # Wrong protocol
            "https://subdomain.github.com.evil.com/file"
        ]
        
        for url in invalid_urls:
            assert download_service.validate_url(url) is False, f"URL should be invalid: {url}"
    
    @pytest.mark.asyncio
    async def test_check_file_size_success(self, download_service, mock_httpx_client):
        """Test checking file size successfully."""
        # Arrange
        url = "https://example.com/plugin.difypkg"
        expected_size = 1024 * 1024 * 5  # 5 MB
        
        mock_response = AsyncMock()
        mock_response.headers = {"content-length": str(expected_size)}
        mock_response.raise_for_status = Mock()
        
        mock_httpx_client.head = AsyncMock(return_value=mock_response)
        
        # Act
        with patch('app.services.download.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            size = await download_service.check_file_size(url)
        
        # Assert
        assert size == expected_size
        mock_httpx_client.head.assert_called_once_with(url)
    
    @pytest.mark.asyncio
    async def test_check_file_size_no_content_length(self, download_service, mock_httpx_client):
        """Test checking file size when content-length header is missing."""
        # Arrange
        url = "https://example.com/plugin.difypkg"
        
        mock_response = AsyncMock()
        mock_response.headers = {}  # No content-length
        mock_response.raise_for_status = Mock()
        
        mock_httpx_client.head = AsyncMock(return_value=mock_response)
        
        # Act
        with patch('app.services.download.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            size = await download_service.check_file_size(url)
        
        # Assert
        assert size is None
    
    @pytest.mark.asyncio
    async def test_check_file_size_http_error(self, download_service, mock_httpx_client):
        """Test checking file size with HTTP error."""
        # Arrange
        url = "https://example.com/plugin.difypkg"
        
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_httpx_client.head = AsyncMock(
            side_effect=httpx.HTTPStatusError("Not found", request=Mock(), response=mock_response)
        )
        
        # Act
        with patch('app.services.download.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            size = await download_service.check_file_size(url)
        
        # Assert
        assert size is None
    
    @pytest.mark.asyncio
    async def test_download_file_success(self, download_service, mock_httpx_client, temp_directory):
        """Test successful file download."""
        # Arrange
        url = "https://example.com/plugin.difypkg"
        file_content = b"Test plugin content with binary data"
        output_path = os.path.join(temp_directory, "test_plugin.difypkg")
        
        mock_response = AsyncMock()
        mock_response.content = file_content
        mock_response.headers = {"content-length": str(len(file_content))}
        mock_response.raise_for_status = Mock()
        mock_response.aiter_bytes = AsyncMock(return_value=iter([file_content]))
        
        # Create an async iterator for content
        async def content_iterator():
            yield file_content
        
        mock_response.aiter_bytes = Mock(return_value=content_iterator())
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        # Act
        with patch('app.services.download.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            progress_updates = []
            async for progress, message in download_service.download_file(url, output_path):
                progress_updates.append((progress, message))
        
        # Assert
        assert os.path.exists(output_path)
        with open(output_path, 'rb') as f:
            assert f.read() == file_content
        
        assert len(progress_updates) > 0
        assert progress_updates[-1][0] == 100  # Final progress is 100%
    
    @pytest.mark.asyncio
    async def test_download_file_with_progress(self, download_service, mock_httpx_client, temp_directory):
        """Test file download with progress tracking."""
        # Arrange
        url = "https://example.com/large_plugin.difypkg"
        chunks = [b"chunk1" * 100, b"chunk2" * 100, b"chunk3" * 100]
        total_size = sum(len(chunk) for chunk in chunks)
        output_path = os.path.join(temp_directory, "large_plugin.difypkg")
        
        mock_response = AsyncMock()
        mock_response.headers = {"content-length": str(total_size)}
        mock_response.raise_for_status = Mock()
        
        # Create async iterator for chunks
        async def chunk_iterator():
            for chunk in chunks:
                yield chunk
        
        mock_response.aiter_bytes = Mock(return_value=chunk_iterator())
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        # Act
        with patch('app.services.download.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            progress_values = []
            async for progress, message in download_service.download_file(url, output_path):
                progress_values.append(progress)
        
        # Assert
        assert len(progress_values) >= len(chunks)
        assert progress_values[0] < progress_values[-1]  # Progress increases
        assert progress_values[-1] == 100
    
    @pytest.mark.asyncio
    async def test_download_file_size_limit(self, download_service, mock_httpx_client, temp_directory):
        """Test download with file size limit."""
        # Arrange
        url = "https://example.com/huge_plugin.difypkg"
        max_size = settings.MAX_DOWNLOAD_SIZE
        
        mock_response = AsyncMock()
        mock_response.headers = {"content-length": str(max_size + 1)}  # Exceed limit
        mock_response.raise_for_status = Mock()
        
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        # Act & Assert
        with patch('app.services.download.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            with pytest.raises(ValueError) as exc_info:
                async for _ in download_service.download_file(
                    url, os.path.join(temp_directory, "huge.difypkg")
                ):
                    pass
            
            assert "exceeds maximum allowed size" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_download_file_network_error(self, download_service, mock_httpx_client, temp_directory):
        """Test download with network error."""
        # Arrange
        url = "https://example.com/plugin.difypkg"
        output_path = os.path.join(temp_directory, "plugin.difypkg")
        
        mock_httpx_client.get = AsyncMock(
            side_effect=httpx.NetworkError("Connection failed")
        )
        
        # Act & Assert
        with patch('app.services.download.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            with pytest.raises(Exception) as exc_info:
                async for _ in download_service.download_file(url, output_path):
                    pass
            
            assert "Connection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_download_file_timeout(self, download_service, mock_httpx_client, temp_directory):
        """Test download with timeout."""
        # Arrange
        url = "https://example.com/slow_plugin.difypkg"
        output_path = os.path.join(temp_directory, "plugin.difypkg")
        
        mock_httpx_client.get = AsyncMock(
            side_effect=httpx.TimeoutException("Request timed out")
        )
        
        # Act & Assert
        with patch('app.services.download.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            with pytest.raises(Exception) as exc_info:
                async for _ in download_service.download_file(url, output_path):
                    pass
            
            assert "timed out" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_download_file_cleanup_on_error(self, download_service, mock_httpx_client, temp_directory):
        """Test that partial downloads are cleaned up on error."""
        # Arrange
        url = "https://example.com/plugin.difypkg"
        output_path = os.path.join(temp_directory, "partial_plugin.difypkg")
        
        mock_response = AsyncMock()
        mock_response.headers = {"content-length": "1000"}
        mock_response.raise_for_status = Mock()
        
        # Simulate error after partial download
        async def error_iterator():
            yield b"partial content"
            raise httpx.NetworkError("Connection lost")
        
        mock_response.aiter_bytes = Mock(return_value=error_iterator())
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        # Act
        with patch('app.services.download.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            try:
                async for _ in download_service.download_file(url, output_path):
                    pass
            except:
                pass
        
        # Assert - File should be cleaned up
        assert not os.path.exists(output_path)
    
    def test_get_filename_from_url(self, download_service):
        """Test extracting filename from URL."""
        # Test various URL patterns
        test_cases = [
            ("https://example.com/plugin.difypkg", "plugin.difypkg"),
            ("https://example.com/path/to/plugin-v1.0.0.difypkg", "plugin-v1.0.0.difypkg"),
            ("https://example.com/download?file=plugin.difypkg", "plugin.difypkg"),
            ("https://example.com/", "download"),  # Fallback
            ("https://example.com/path/", "download"),  # Fallback
        ]
        
        for url, expected in test_cases:
            filename = download_service.get_filename_from_url(url)
            assert filename == expected, f"Expected {expected} for {url}, got {filename}"


class TestDownloadServiceIntegration:
    """Integration tests for DownloadService."""
    
    @pytest.mark.asyncio
    async def test_concurrent_downloads(self, download_service, mock_httpx_client, temp_directory):
        """Test multiple concurrent downloads."""
        # Arrange
        urls = [
            "https://example.com/plugin1.difypkg",
            "https://example.com/plugin2.difypkg",
            "https://example.com/plugin3.difypkg"
        ]
        
        mock_response = AsyncMock()
        mock_response.content = b"Test content"
        mock_response.headers = {"content-length": "12"}
        mock_response.raise_for_status = Mock()
        
        async def content_iterator():
            yield b"Test content"
        
        mock_response.aiter_bytes = Mock(return_value=content_iterator())
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        # Act
        with patch('app.services.download.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            download_tasks = []
            for i, url in enumerate(urls):
                output_path = os.path.join(temp_directory, f"plugin{i}.difypkg")
                task = download_service.download_file(url, output_path)
                download_tasks.append([x async for x in task])
            
            results = await asyncio.gather(*download_tasks)
        
        # Assert
        assert len(results) == 3
        for i in range(3):
            assert os.path.exists(os.path.join(temp_directory, f"plugin{i}.difypkg"))