"""Test marketplace URL parsing functionality"""

import pytest
from app.services.marketplace import MarketplaceService
from app.core.config import settings


class TestMarketplaceURLParsing:
    """Test marketplace URL parsing"""
    
    def test_valid_marketplace_url(self):
        """Test parsing valid marketplace URLs"""
        # Test URL without trailing slash
        url = "https://marketplace.dify.ai/plugins/langgenius/ollama"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result is not None
        assert result == ("langgenius", "ollama")
        
        # Test URL with trailing slash
        url = "https://marketplace.dify.ai/plugins/langgenius/ollama/"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result is not None
        assert result == ("langgenius", "ollama")
        
        # Test with http protocol
        url = "http://marketplace.dify.ai/plugins/author/plugin"
        result = MarketplaceService.parse_marketplace_url(url)
        assert result is not None
        assert result == ("author", "plugin")
    
    def test_invalid_marketplace_urls(self):
        """Test that invalid URLs return None"""
        invalid_urls = [
            "https://marketplace.dify.ai/plugins/",  # Missing plugin name
            "https://marketplace.dify.ai/plugins/author",  # Missing plugin name
            "https://marketplace.dify.ai/plugins/author/plugin/version",  # Has version
            "https://github.com/user/repo",  # Wrong domain
            "https://marketplace.dify.ai/api/v1/plugins/author/plugin",  # API URL
            "not-a-url",  # Invalid URL
            "",  # Empty string
        ]
        
        for url in invalid_urls:
            result = MarketplaceService.parse_marketplace_url(url)
            assert result is None, f"URL {url} should return None"
    
    def test_custom_marketplace_url(self):
        """Test parsing with custom marketplace URL from settings"""
        # Save original value
        original_url = settings.MARKETPLACE_API_URL
        
        try:
            # Test with custom URL
            settings.MARKETPLACE_API_URL = "https://custom.marketplace.com"
            url = "https://custom.marketplace.com/plugins/myauthor/myplugin"
            result = MarketplaceService.parse_marketplace_url(url)
            assert result is not None
            assert result == ("myauthor", "myplugin")
        finally:
            # Restore original value
            settings.MARKETPLACE_API_URL = original_url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])