"""
Unit tests for marketplace service
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx
import json
from datetime import datetime

from app.services.marketplace import MarketplaceService
from app.utils.circuit_breaker import CircuitOpenError
from tests.factories.plugin import MarketplacePluginFactory, PluginFactory


class TestMarketplaceService:
    """Test cases for MarketplaceService."""
    
    @pytest.fixture
    def marketplace_service(self):
        """Create a MarketplaceService instance."""
        return MarketplaceService()
    
    @pytest.fixture
    def mock_circuit_breaker(self, monkeypatch):
        """Mock the circuit breaker."""
        mock_cb = Mock()
        mock_cb.is_open = False
        mock_cb.call = AsyncMock(side_effect=lambda func: func())
        monkeypatch.setattr("app.services.marketplace.marketplace_circuit_breaker", mock_cb)
        return mock_cb
    
    @pytest.mark.asyncio
    async def test_make_api_request_success(self, marketplace_service, mock_httpx_client):
        """Test successful API request."""
        # Arrange
        url = "https://marketplace.dify.ai/api/v1/plugins"
        expected_data = {"plugins": [{"name": "test"}]}
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = json.dumps(expected_data).encode()
        mock_response.json = AsyncMock(return_value=expected_data)
        mock_response.raise_for_status = Mock()
        
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        # Act
        result = await marketplace_service._make_api_request(
            mock_httpx_client, "GET", url
        )
        
        # Assert
        assert result == expected_data
        mock_httpx_client.get.assert_called_once()
        call_args = mock_httpx_client.get.call_args
        assert call_args[0][0] == url
        assert call_args[1]["headers"]["Accept"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_make_api_request_html_error(self, marketplace_service, mock_httpx_client):
        """Test API request returning HTML error page."""
        # Arrange
        url = "https://marketplace.dify.ai/api/v1/plugins"
        html_content = "<html><body>Error</body></html>"
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.content = html_content.encode()
        mock_response.raise_for_status = Mock()
        
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await marketplace_service._make_api_request(
                mock_httpx_client, "GET", url
            )
        
        assert "HTML instead of JSON" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_plugins_success(self, marketplace_service, mock_httpx_client, mock_redis):
        """Test successful plugin search."""
        # Arrange
        plugins = [
            MarketplacePluginFactory.create(),
            MarketplacePluginFactory.create()
        ]
        response_data = {
            "plugins": plugins,
            "total": 2,
            "page": 1,
            "page_size": 20
        }
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json = AsyncMock(return_value=response_data)
        mock_response.raise_for_status = Mock()
        
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        mock_redis.get.return_value = None  # No cache
        
        with patch('app.services.marketplace.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            # Act
            result = await marketplace_service.search_plugins(q="test")
            
            # Assert
            assert result["total"] == 2
            assert len(result["plugins"]) == 2
            mock_redis.set.assert_called_once()  # Should cache result
    
    @pytest.mark.asyncio
    async def test_search_plugins_with_cache(self, marketplace_service, mock_httpx_client, mock_redis):
        """Test plugin search with cached results."""
        # Arrange
        cached_data = {
            "plugins": [MarketplacePluginFactory.create()],
            "total": 1,
            "page": 1,
            "page_size": 20
        }
        mock_redis.get.return_value = json.dumps(cached_data).encode()
        
        # Act
        result = await marketplace_service.search_plugins(q="test")
        
        # Assert
        assert result == cached_data
        # Should not make HTTP request when cache hit
        mock_httpx_client.get.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_search_plugins_circuit_breaker_open(self, marketplace_service, mock_circuit_breaker):
        """Test plugin search when circuit breaker is open."""
        # Arrange
        mock_circuit_breaker.is_open = True
        
        # Act & Assert
        with pytest.raises(CircuitOpenError):
            await marketplace_service.search_plugins()
    
    @pytest.mark.asyncio
    async def test_get_plugin_details_success(self, marketplace_service, mock_httpx_client):
        """Test getting plugin details successfully."""
        # Arrange
        plugin_data = MarketplacePluginFactory.create(
            author="langgenius",
            name="agent",
            versions=["0.0.9", "0.0.8", "0.0.7"]
        )
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json = AsyncMock(return_value=plugin_data)
        mock_response.raise_for_status = Mock()
        
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        with patch('app.services.marketplace.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            # Act
            result = await marketplace_service.get_plugin_details("langgenius", "agent")
            
            # Assert
            assert result["author"] == "langgenius"
            assert result["name"] == "agent"
            assert len(result["versions"]) == 3
    
    @pytest.mark.asyncio
    async def test_get_plugin_version_success(self, marketplace_service, mock_httpx_client):
        """Test getting specific plugin version."""
        # Arrange
        version_data = {
            "version": "0.0.9",
            "download_url": "https://marketplace.dify.ai/download/...",
            "size": 1024000,
            "dependencies": ["requests>=2.0.0"]
        }
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json = AsyncMock(return_value=version_data)
        mock_response.raise_for_status = Mock()
        
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        with patch('app.services.marketplace.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            # Act
            result = await marketplace_service.get_plugin_version(
                "langgenius", "agent", "0.0.9"
            )
            
            # Assert
            assert result["version"] == "0.0.9"
            assert "download_url" in result
    
    @pytest.mark.asyncio
    async def test_get_download_url_success(self, marketplace_service, mock_httpx_client):
        """Test getting plugin download URL."""
        # Arrange
        expected_url = "https://marketplace.dify.ai/api/v1/plugins/langgenius/agent/0.0.9/download"
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "content-type": "application/json",
            "location": expected_url
        }
        mock_response.json = AsyncMock(return_value={"download_url": expected_url})
        mock_response.raise_for_status = Mock()
        
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        with patch('app.services.marketplace.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            # Act
            result = await marketplace_service.get_download_url(
                "langgenius", "agent", "0.0.9"
            )
            
            # Assert
            assert result == expected_url
    
    @pytest.mark.asyncio
    async def test_verify_plugin_exists_true(self, marketplace_service, mock_httpx_client):
        """Test verifying plugin exists."""
        # Arrange
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json = AsyncMock(return_value={"exists": True})
        mock_response.raise_for_status = Mock()
        
        mock_httpx_client.head = AsyncMock(return_value=mock_response)
        
        with patch('app.services.marketplace.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            # Act
            result = await marketplace_service.verify_plugin_exists(
                "langgenius", "agent", "0.0.9"
            )
            
            # Assert
            assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_plugin_exists_false(self, marketplace_service, mock_httpx_client):
        """Test verifying plugin doesn't exist."""
        # Arrange
        mock_httpx_client.head = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Not found",
                request=Mock(),
                response=Mock(status_code=404)
            )
        )
        
        with patch('app.services.marketplace.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            # Act
            result = await marketplace_service.verify_plugin_exists(
                "nonexistent", "plugin", "1.0.0"
            )
            
            # Assert
            assert result is False
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, marketplace_service, mock_httpx_client):
        """Test handling of network errors."""
        # Arrange
        mock_httpx_client.get = AsyncMock(
            side_effect=httpx.NetworkError("Connection failed")
        )
        
        with patch('app.services.marketplace.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            # Act & Assert
            with pytest.raises(httpx.NetworkError):
                await marketplace_service.search_plugins()
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, marketplace_service, mock_httpx_client):
        """Test handling of timeouts."""
        # Arrange
        mock_httpx_client.get = AsyncMock(
            side_effect=httpx.TimeoutException("Request timed out")
        )
        
        with patch('app.services.marketplace.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            # Act & Assert
            with pytest.raises(httpx.TimeoutException):
                await marketplace_service.get_plugin_details("author", "plugin")
    
    @pytest.mark.asyncio
    async def test_parse_marketplace_url(self, marketplace_service):
        """Test parsing marketplace URLs."""
        # Test valid marketplace URLs
        test_cases = [
            (
                "https://marketplace.dify.ai/plugins/langgenius/agent",
                ("langgenius", "agent", None)
            ),
            (
                "https://marketplace.dify.ai/plugins/langgenius/agent/0.0.9",
                ("langgenius", "agent", "0.0.9")
            ),
            (
                "marketplace.dify.ai/plugins/author/name",
                ("author", "name", None)
            )
        ]
        
        for url, expected in test_cases:
            result = marketplace_service.parse_marketplace_url(url)
            assert result == expected
    
    @pytest.mark.asyncio
    async def test_get_categories_success(self, marketplace_service, mock_httpx_client):
        """Test getting marketplace categories."""
        # Arrange
        categories = [
            {"name": "agent", "display_name": "Agent", "count": 10},
            {"name": "tool", "display_name": "Tool", "count": 25}
        ]
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json = AsyncMock(return_value=categories)
        mock_response.raise_for_status = Mock()
        
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        with patch('app.services.marketplace.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            # Act
            result = await marketplace_service.get_categories()
            
            # Assert
            assert len(result) == 2
            assert result[0]["name"] == "agent"
            assert result[1]["count"] == 25


class TestMarketplaceServiceIntegration:
    """Integration tests for MarketplaceService."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, marketplace_service, mock_httpx_client):
        """Test handling concurrent requests."""
        # Arrange
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.raise_for_status = Mock()
        
        mock_httpx_client.get = AsyncMock(return_value=mock_response)
        
        with patch('app.services.marketplace.get_async_client') as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_httpx_client
            
            # Act - Make multiple concurrent requests
            import asyncio
            tasks = [
                marketplace_service.search_plugins(q=f"test{i}")
                for i in range(5)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Assert
            assert len(results) == 5
            assert all(isinstance(r, dict) for r in results)