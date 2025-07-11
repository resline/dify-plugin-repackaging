"""
Simple unit tests for marketplace service focusing on pure functions.
These tests don't require Redis or external dependencies.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from typing import Dict, List

from app.services.marketplace import MarketplaceService


class TestMarketplaceHelpers:
    """Test MarketplaceService helper methods."""
    
    def test_build_download_url(self):
        """Test building download URL."""
        url = MarketplaceService.build_download_url("author", "plugin", "1.0.0")
        assert url == "https://marketplace.dify.ai/api/v1/plugins/author/plugin/1.0.0/download"

    def test_construct_download_url_alias(self):
        """Test construct_download_url alias."""
        url = MarketplaceService.construct_download_url("test", "plugin", "2.0.0")
        assert url == "https://marketplace.dify.ai/api/v1/plugins/test/plugin/2.0.0/download"

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
        url = "https://marketplace.dify.ai/plugins/test/plugin?source=web&ref=123"
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

    def test_parse_marketplace_url_www_prefix(self):
        """Test parsing URL with www prefix."""
        url = "https://www.marketplace.dify.ai/plugins/author/name"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result == ("author", "name")

    def test_parse_marketplace_url_invalid_domain(self):
        """Test parsing invalid marketplace URL."""
        url = "https://example.com/plugins/author/name"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result is None

    def test_parse_marketplace_url_empty_parts(self):
        """Test parsing URL with empty author/name."""
        url = "https://marketplace.dify.ai/plugins//name"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result is None

    def test_parse_marketplace_url_missing_name(self):
        """Test parsing URL with missing plugin name."""
        url = "https://marketplace.dify.ai/plugins/author/"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result is None

    def test_parse_marketplace_url_fragment(self):
        """Test parsing URL with fragment."""
        url = "https://marketplace.dify.ai/plugins/author/name#details"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result == ("author", "name")

    def test_parse_marketplace_url_special_characters(self):
        """Test parsing URL with special characters in names."""
        url = "https://marketplace.dify.ai/plugins/author-123/plugin_name"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result == ("author-123", "plugin_name")

    def test_parse_marketplace_url_encoded_characters(self):
        """Test parsing URL with URL-encoded characters."""
        url = "https://marketplace.dify.ai/plugins/author%20name/plugin%20name"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result == ("author%20name", "plugin%20name")


class TestMarketplaceCacheOperations:
    """Test caching operations without Redis dependency."""
    
    @patch('app.services.marketplace.redis_client')
    def test_get_from_cache_exists(self, mock_redis):
        """Test getting existing value from cache."""
        test_data = {"plugins": ["test"]}
        mock_redis.get.return_value = json.dumps(test_data)
        
        result = MarketplaceService._get_from_cache("test_key")
        
        assert result == test_data
        mock_redis.get.assert_called_once_with("test_key")

    @patch('app.services.marketplace.redis_client')
    def test_get_from_cache_not_exists(self, mock_redis):
        """Test getting non-existent value from cache."""
        mock_redis.get.return_value = None
        
        result = MarketplaceService._get_from_cache("test_key")
        
        assert result is None

    @patch('app.services.marketplace.redis_client')
    def test_get_from_cache_invalid_json(self, mock_redis):
        """Test handling invalid JSON in cache."""
        mock_redis.get.return_value = "invalid json{"
        
        result = MarketplaceService._get_from_cache("test_key")
        
        assert result is None

    @patch('app.services.marketplace.redis_client')
    def test_get_from_cache_redis_error(self, mock_redis):
        """Test handling Redis errors when getting from cache."""
        mock_redis.get.side_effect = Exception("Redis error")
        
        result = MarketplaceService._get_from_cache("test_key")
        
        assert result is None

    @patch('app.services.marketplace.redis_client')
    @patch('app.services.marketplace.settings')
    def test_set_cache_success(self, mock_settings, mock_redis):
        """Test setting value in cache."""
        mock_settings.MARKETPLACE_CACHE_TTL = 3600
        test_data = {"plugins": ["test"]}
        
        MarketplaceService._set_cache("test_key", test_data)
        
        mock_redis.setex.assert_called_once_with(
            "test_key",
            3600,
            json.dumps(test_data)
        )

    @patch('app.services.marketplace.redis_client')
    def test_set_cache_redis_error(self, mock_redis):
        """Test handling Redis errors when setting cache."""
        mock_redis.setex.side_effect = Exception("Redis error")
        
        # Should not raise exception
        MarketplaceService._set_cache("test_key", {"data": "test"})
        
        # Verify it was attempted
        mock_redis.setex.assert_called_once()