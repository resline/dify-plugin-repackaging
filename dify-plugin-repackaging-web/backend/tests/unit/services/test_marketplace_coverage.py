"""
Comprehensive unit tests for marketplace service to increase coverage.
Focus on API request handling, caching, error handling, and fallback mechanisms.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import httpx
import json
from typing import Dict, List, Optional

from app.services.marketplace import MarketplaceService
from app.utils.circuit_breaker import CircuitOpenError


class TestMarketplaceServiceAPI:
    """Test MarketplaceService API interaction methods."""
    
    @pytest.mark.asyncio
    async def test_make_api_request_get_success(self):
        """Test successful GET API request."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = b'{"data": "test"}'
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response
        
        with patch('app.services.marketplace.marketplace_circuit_breaker.async_call') as mock_breaker:
            async def call_func(func):
                return await func()
            mock_breaker.side_effect = call_func
            
            result = await MarketplaceService._make_api_request(
                mock_client, "GET", "https://test.com/api"
            )
            
            assert result == mock_response
            mock_client.get.assert_called_once_with(
                "https://test.com/api",
                headers={"Accept": "application/json"}
            )

    @pytest.mark.asyncio
    async def test_make_api_request_post_with_json(self):
        """Test successful POST API request with JSON data."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        
        with patch('app.services.marketplace.marketplace_circuit_breaker.async_call') as mock_breaker:
            async def call_func(func):
                return await func()
            mock_breaker.side_effect = call_func
            
            result = await MarketplaceService._make_api_request(
                mock_client, "POST", "https://test.com/api",
                json={"test": "data"}
            )
            
            assert result == mock_response
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_api_request_html_response(self):
        """Test handling HTML response when JSON expected."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.content = b'<html>Error page</html>'
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response
        
        with patch('app.services.marketplace.marketplace_circuit_breaker.async_call') as mock_breaker:
            async def call_func(func):
                return await func()
            mock_breaker.side_effect = call_func
            
            with pytest.raises(ValueError, match="API returned HTML instead of JSON"):
                await MarketplaceService._make_api_request(
                    mock_client, "GET", "https://test.com/api"
                )

    @pytest.mark.asyncio
    async def test_make_api_request_invalid_json(self):
        """Test handling invalid JSON response."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.content = b'Invalid JSON'
        mock_response.text = "Invalid JSON"
        mock_response.json.side_effect = json.JSONDecodeError("Invalid", "doc", 0)
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response
        
        with patch('app.services.marketplace.marketplace_circuit_breaker.async_call') as mock_breaker:
            async def call_func(func):
                return await func()
            mock_breaker.side_effect = call_func
            
            with pytest.raises(ValueError, match="Invalid response format"):
                await MarketplaceService._make_api_request(
                    mock_client, "GET", "https://test.com/api"
                )

    @pytest.mark.asyncio
    async def test_make_api_request_circuit_breaker_open(self):
        """Test handling circuit breaker open state."""
        mock_client = AsyncMock()
        
        with patch('app.services.marketplace.marketplace_circuit_breaker.async_call') as mock_breaker:
            mock_breaker.side_effect = CircuitOpenError()
            
            with pytest.raises(CircuitOpenError):
                await MarketplaceService._make_api_request(
                    mock_client, "GET", "https://test.com/api"
                )


class TestMarketplaceServiceCache:
    """Test caching functionality."""
    
    def test_get_cache_key_simple(self):
        """Test cache key generation without params."""
        key = MarketplaceService._get_cache_key("plugins")
        assert key == "marketplace:plugins"

    def test_get_cache_key_with_params(self):
        """Test cache key generation with params."""
        key = MarketplaceService._get_cache_key(
            "search",
            {"query": "test", "page": 1}
        )
        assert "marketplace:search:" in key
        assert "query" in key
        assert "test" in key

    def test_get_from_cache_exists(self, mock_redis):
        """Test getting existing value from cache."""
        test_data = {"plugins": ["test"]}
        mock_redis.get.return_value = json.dumps(test_data)
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            result = MarketplaceService._get_from_cache("test_key")
            
            assert result == test_data
            mock_redis.get.assert_called_once_with("test_key")

    def test_get_from_cache_not_exists(self, mock_redis):
        """Test getting non-existent value from cache."""
        mock_redis.get.return_value = None
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            result = MarketplaceService._get_from_cache("test_key")
            
            assert result is None

    def test_get_from_cache_redis_error(self, mock_redis):
        """Test handling Redis errors when getting from cache."""
        mock_redis.get.side_effect = Exception("Redis error")
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            result = MarketplaceService._get_from_cache("test_key")
            
            assert result is None

    def test_set_cache_success(self, mock_redis):
        """Test setting value in cache."""
        test_data = {"plugins": ["test"]}
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            with patch('app.services.marketplace.settings.MARKETPLACE_CACHE_TTL', 3600):
                MarketplaceService._set_cache("test_key", test_data)
                
                mock_redis.setex.assert_called_once_with(
                    "test_key",
                    3600,
                    json.dumps(test_data)
                )

    def test_set_cache_redis_error(self, mock_redis):
        """Test handling Redis errors when setting cache."""
        mock_redis.setex.side_effect = Exception("Redis error")
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            # Should not raise exception
            MarketplaceService._set_cache("test_key", {"data": "test"})


class TestSearchPlugins:
    """Test search_plugins method."""
    
    @pytest.mark.asyncio
    async def test_search_plugins_from_cache(self, mock_redis):
        """Test returning search results from cache."""
        cached_data = {
            "plugins": [{"name": "test"}],
            "total": 1,
            "page": 1,
            "per_page": 20
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            result = await MarketplaceService.search_plugins(query="test")
            
            assert result == cached_data
            mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_plugins_api_success(self, mock_redis):
        """Test successful API search."""
        mock_redis.get.return_value = None  # No cache
        
        api_response = {
            "data": [
                {"name": "plugin1", "author": "test"},
                {"name": "plugin2", "author": "test"}
            ],
            "total": 2
        }
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            with patch('app.services.marketplace.get_async_client') as mock_get_client:
                mock_client = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.headers = {"content-type": "application/json"}
                mock_response.json.return_value = api_response
                mock_response.raise_for_status = Mock()
                mock_client.get.return_value = mock_response
                
                mock_get_client.return_value.__aenter__.return_value = mock_client
                
                with patch('app.services.marketplace.marketplace_circuit_breaker.async_call') as mock_breaker:
                    async def call_func(func):
                        return await func()
                    mock_breaker.side_effect = call_func
                    
                    result = await MarketplaceService.search_plugins(
                        query="test",
                        page=1,
                        per_page=20
                    )
                    
                    assert len(result["plugins"]) == 2
                    assert result["total"] == 2
                    assert result["api_endpoint"] is not None
                    assert result["has_more"] is False

    @pytest.mark.asyncio
    async def test_search_plugins_multiple_api_attempts(self, mock_redis):
        """Test falling back to alternative API endpoints."""
        mock_redis.get.return_value = None
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            with patch('app.services.marketplace.get_async_client') as mock_get_client:
                mock_client = AsyncMock()
                
                # First API fails
                mock_response1 = Mock()
                mock_response1.status_code = 500
                mock_response1.raise_for_status.side_effect = httpx.HTTPError("Server error")
                
                # Second API succeeds
                mock_response2 = Mock()
                mock_response2.status_code = 200
                mock_response2.headers = {"content-type": "application/json"}
                mock_response2.json.return_value = {"data": [], "total": 0}
                mock_response2.raise_for_status = Mock()
                
                mock_client.get.side_effect = [mock_response1, mock_response2]
                mock_get_client.return_value.__aenter__.return_value = mock_client
                
                with patch('app.services.marketplace.marketplace_circuit_breaker.async_call') as mock_breaker:
                    call_count = 0
                    async def call_func(func):
                        nonlocal call_count
                        call_count += 1
                        if call_count == 1:
                            # First call fails
                            raise httpx.HTTPError("Server error")
                        return await func()
                    mock_breaker.side_effect = call_func
                    
                    result = await MarketplaceService.search_plugins()
                    
                    assert result["plugins"] == []
                    assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_search_plugins_fallback_to_scraper(self, mock_redis):
        """Test falling back to web scraper when API fails."""
        mock_redis.get.return_value = None
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            with patch('app.services.marketplace.get_async_client') as mock_get_client:
                mock_client = AsyncMock()
                mock_client.get.side_effect = httpx.HTTPError("API down")
                mock_get_client.return_value.__aenter__.return_value = mock_client
                
                with patch('app.services.marketplace.marketplace_circuit_breaker.async_call') as mock_breaker:
                    mock_breaker.side_effect = CircuitOpenError()
                    
                    with patch('app.services.marketplace_scraper.marketplace_fallback_service') as mock_fallback:
                        mock_fallback.scraper.scrape_plugin_list = AsyncMock(
                            return_value={
                                "plugins": [{"name": "scraped"}],
                                "total": 1,
                                "page": 1,
                                "per_page": 20
                            }
                        )
                        
                        result = await MarketplaceService.search_plugins()
                        
                        assert result["plugins"][0]["name"] == "scraped"
                        assert result["api_status"] == "incompatible"
                        assert result["fallback_used"] is True

    @pytest.mark.asyncio
    async def test_search_plugins_all_methods_fail(self, mock_redis):
        """Test when both API and scraper fail."""
        mock_redis.get.return_value = None
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            with patch('app.services.marketplace.get_async_client') as mock_get_client:
                mock_client = AsyncMock()
                mock_client.get.side_effect = httpx.HTTPError("API down")
                mock_get_client.return_value.__aenter__.return_value = mock_client
                
                with patch('app.services.marketplace.marketplace_circuit_breaker.async_call') as mock_breaker:
                    mock_breaker.side_effect = httpx.HTTPError("API down")
                    
                    with patch('app.services.marketplace_scraper.marketplace_fallback_service') as mock_fallback:
                        mock_fallback.scraper.scrape_plugin_list.side_effect = Exception("Scraper failed")
                        
                        result = await MarketplaceService.search_plugins()
                        
                        assert result["plugins"] == []
                        assert result["error"] == "Dify Marketplace API has changed and web scraping failed."
                        assert result["api_status"] == "incompatible"


class TestGetPluginDetails:
    """Test get_plugin_details method."""
    
    @pytest.mark.asyncio
    async def test_get_plugin_details_from_search(self, mock_redis):
        """Test getting plugin details via search method."""
        mock_redis.get.return_value = None
        
        search_result = {
            "plugins": [
                {
                    "author": "test",
                    "name": "plugin",
                    "version": "1.0.0",
                    "description": "Test plugin"
                }
            ],
            "total": 1
        }
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            with patch.object(MarketplaceService, 'search_plugins', 
                            return_value=search_result) as mock_search:
                result = await MarketplaceService.get_plugin_details("test", "plugin")
                
                assert result["author"] == "test"
                assert result["name"] == "plugin"
                mock_search.assert_called_once_with(
                    query="plugin",
                    author="test",
                    per_page=1
                )

    @pytest.mark.asyncio
    async def test_get_plugin_details_direct_api(self, mock_redis):
        """Test getting plugin details via direct API when search doesn't find it."""
        mock_redis.get.return_value = None
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            with patch.object(MarketplaceService, 'search_plugins', 
                            return_value={"plugins": [], "total": 0}):
                
                with patch('httpx.AsyncClient') as mock_client_class:
                    mock_client = AsyncMock()
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "author": "test",
                        "name": "plugin",
                        "latest_version": "2.0.0"
                    }
                    mock_response.raise_for_status = Mock()
                    mock_client.get.return_value = mock_response
                    
                    mock_client_class.return_value.__aenter__.return_value = mock_client
                    
                    result = await MarketplaceService.get_plugin_details("test", "plugin")
                    
                    assert result["latest_version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_get_plugin_details_fallback_to_scraper(self, mock_redis):
        """Test falling back to scraper for plugin details."""
        mock_redis.get.return_value = None
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            with patch.object(MarketplaceService, 'search_plugins', 
                            side_effect=Exception("Search failed")):
                
                with patch('app.services.marketplace_scraper.marketplace_fallback_service') as mock_fallback:
                    mock_fallback.scraper.scrape_plugin_details = AsyncMock(
                        return_value={
                            "author": "test",
                            "name": "plugin",
                            "version": "1.0.0"
                        }
                    )
                    
                    result = await MarketplaceService.get_plugin_details("test", "plugin")
                    
                    assert result["fallback_used"] is True
                    assert result["fallback_reason"] == "API request failed"


class TestGetPluginVersions:
    """Test get_plugin_versions method."""
    
    @pytest.mark.asyncio
    async def test_get_plugin_versions_success(self, mock_redis):
        """Test getting plugin versions successfully."""
        mock_redis.get.return_value = None
        
        versions_data = [
            {"version": "1.0.0", "created_at": "2024-01-01"},
            {"version": "0.9.0", "created_at": "2023-12-01"}
        ]
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = versions_data
                mock_response.raise_for_status = Mock()
                mock_client.get.return_value = mock_response
                
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                result = await MarketplaceService.get_plugin_versions("test", "plugin")
                
                assert len(result) == 2
                assert result[0]["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_plugin_versions_fallback(self, mock_redis):
        """Test fallback for plugin versions."""
        mock_redis.get.return_value = None
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get.side_effect = httpx.HTTPError("API error")
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                with patch('app.services.marketplace_scraper.marketplace_fallback_service') as mock_fallback:
                    mock_fallback.scraper.scrape_plugin_versions = AsyncMock(
                        return_value=[{"version": "1.0.0"}]
                    )
                    
                    result = await MarketplaceService.get_plugin_versions("test", "plugin")
                    
                    assert len(result) == 1
                    assert result[0]["version"] == "1.0.0"


class TestBuildDownloadUrl:
    """Test URL building methods."""
    
    def test_build_download_url(self):
        """Test building download URL."""
        url = MarketplaceService.build_download_url("author", "plugin", "1.0.0")
        assert url == "https://marketplace.dify.ai/api/v1/plugins/author/plugin/1.0.0/download"

    def test_construct_download_url(self):
        """Test construct_download_url alias."""
        url = MarketplaceService.construct_download_url("test", "plugin", "2.0.0")
        assert url == "https://marketplace.dify.ai/api/v1/plugins/test/plugin/2.0.0/download"


class TestGetCategories:
    """Test get_categories method."""
    
    @pytest.mark.asyncio
    async def test_get_categories_from_api(self, mock_redis):
        """Test getting categories from API."""
        mock_redis.get.return_value = None
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = ["agent", "tool", "model"]
                mock_response.raise_for_status = Mock()
                mock_client.get.return_value = mock_response
                
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                result = await MarketplaceService.get_categories()
                
                assert len(result) == 3
                assert "agent" in result

    @pytest.mark.asyncio
    async def test_get_categories_dict_response(self, mock_redis):
        """Test handling dict response format for categories."""
        mock_redis.get.return_value = None
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "categories": ["workflow", "extension"]
                }
                mock_response.raise_for_status = Mock()
                mock_client.get.return_value = mock_response
                
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                result = await MarketplaceService.get_categories()
                
                assert len(result) == 2
                assert "workflow" in result

    @pytest.mark.asyncio
    async def test_get_categories_default_on_error(self, mock_redis):
        """Test returning default categories on error."""
        mock_redis.get.return_value = None
        
        with patch('app.services.marketplace.redis_client', mock_redis):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get.side_effect = httpx.HTTPError("API error")
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                result = await MarketplaceService.get_categories()
                
                assert len(result) == 5  # Default categories
                assert "agent" in result
                assert "tool" in result


class TestParseMarketplaceUrl:
    """Test parse_marketplace_url method."""
    
    def test_parse_marketplace_url_standard(self):
        """Test parsing standard marketplace URL."""
        url = "https://marketplace.dify.ai/plugins/langgenius/ollama"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result == ("langgenius", "ollama")

    def test_parse_marketplace_url_with_trailing_slash(self):
        """Test parsing URL with trailing slash."""
        url = "http://marketplace.dify.ai/plugins/author/plugin/"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result == ("author", "plugin")

    def test_parse_marketplace_url_with_query_params(self):
        """Test parsing URL with query parameters."""
        url = "https://marketplace.dify.ai/plugins/test/plugin?source=web"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result == ("test", "plugin")

    def test_parse_marketplace_url_singular_plugin(self):
        """Test parsing URL with singular 'plugin' path."""
        url = "https://marketplace.dify.ai/plugin/author/name"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result == ("author", "name")

    def test_parse_marketplace_url_without_protocol(self):
        """Test parsing URL without protocol."""
        url = "marketplace.dify.ai/plugins/author/name"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result == ("author", "name")

    def test_parse_marketplace_url_invalid(self):
        """Test parsing invalid marketplace URL."""
        url = "https://example.com/plugins/author/name"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result is None

    def test_parse_marketplace_url_empty_parts(self):
        """Test parsing URL with empty author/name."""
        url = "https://marketplace.dify.ai/plugins//name"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result is None

    def test_parse_marketplace_url_exception(self):
        """Test handling exceptions in URL parsing."""
        with patch('app.services.marketplace.urlparse', side_effect=Exception("Parse error")):
            result = MarketplaceService.parse_marketplace_url("invalid")
            assert result is None


class TestGetLatestVersion:
    """Test get_latest_version method."""
    
    @pytest.mark.asyncio
    async def test_get_latest_version_first_attempt(self):
        """Test getting latest version on first API attempt."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "code": 0,
                "data": {
                    "plugin": {
                        "latest_version": "2.0.0"
                    }
                }
            }
            mock_client.get.return_value = mock_response
            
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await MarketplaceService.get_latest_version("author", "plugin")
            
            assert result == "2.0.0"

    @pytest.mark.asyncio
    async def test_get_latest_version_fallback_to_search(self):
        """Test falling back to search method for latest version."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            # All direct API attempts fail
            mock_response = Mock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response
            
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            with patch.object(MarketplaceService, 'search_plugins') as mock_search:
                mock_search.return_value = {
                    "plugins": [{
                        "author": "author",
                        "name": "plugin",
                        "latest_version": "1.5.0"
                    }]
                }
                
                result = await MarketplaceService.get_latest_version("author", "plugin")
                
                assert result == "1.5.0"

    @pytest.mark.asyncio
    async def test_get_latest_version_fallback_to_details(self):
        """Test falling back to plugin details for latest version."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("API error")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            with patch.object(MarketplaceService, 'search_plugins') as mock_search:
                mock_search.return_value = {"plugins": []}
                
                with patch.object(MarketplaceService, 'get_plugin_details') as mock_details:
                    mock_details.return_value = {
                        "latest_version": "1.0.0"
                    }
                    
                    result = await MarketplaceService.get_latest_version("author", "plugin")
                    
                    assert result == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_latest_version_not_found(self):
        """Test when no version can be found."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("API error")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            with patch.object(MarketplaceService, 'search_plugins') as mock_search:
                mock_search.return_value = {"plugins": []}
                
                with patch.object(MarketplaceService, 'get_plugin_details') as mock_details:
                    mock_details.return_value = None
                    
                    result = await MarketplaceService.get_latest_version("author", "plugin")
                    
                    assert result is None

    @pytest.mark.asyncio
    async def test_get_latest_version_exception(self):
        """Test handling exceptions in get_latest_version."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.side_effect = Exception("Client creation failed")
            
            result = await MarketplaceService.get_latest_version("author", "plugin")
            
            assert result is None