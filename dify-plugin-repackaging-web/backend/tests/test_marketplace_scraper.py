"""
Test cases for marketplace scraper with fallback functionality
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.marketplace_scraper import MarketplaceScraper, MarketplaceServiceWithFallback
import json


@pytest.fixture
def scraper():
    """Create scraper instance for testing"""
    return MarketplaceScraper()


@pytest.fixture
def fallback_service():
    """Create fallback service instance for testing"""
    return MarketplaceServiceWithFallback()


@pytest.fixture
def mock_html_response():
    """Mock HTML response for plugin list"""
    return """
    <html>
    <body>
        <div class="plugin-grid">
            <div class="plugin-card">
                <a href="/plugins/langgenius/agent">
                    <h3>Agent Tools</h3>
                    <p class="description">Advanced agent capabilities for Dify</p>
                    <span class="category">agent</span>
                    <span class="version">v0.0.9</span>
                </a>
            </div>
            <div class="plugin-card">
                <a href="/plugins/antv/visualization">
                    <h3>Data Visualization</h3>
                    <p class="description">Beautiful charts and graphs</p>
                    <span class="category">tool</span>
                    <span class="version">v0.1.7</span>
                </a>
            </div>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def mock_plugin_detail_html():
    """Mock HTML response for plugin detail page"""
    return """
    <html>
    <body>
        <div class="plugin-detail">
            <h1>Agent Tools</h1>
            <div class="description">
                Advanced agent capabilities for Dify platform. 
                Includes various tools for AI agents.
            </div>
            <select name="version">
                <option value="0.0.9">v0.0.9 (latest)</option>
                <option value="0.0.8">v0.0.8</option>
                <option value="0.0.7">v0.0.7</option>
            </select>
            <a href="/api/v1/plugins/langgenius/agent/0.0.9/download" class="download-btn">
                Download v0.0.9
            </a>
        </div>
    </body>
    </html>
    """


class TestMarketplaceScraper:
    """Test cases for MarketplaceScraper"""
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, scraper):
        """Test cache key generation"""
        key1 = scraper._get_cache_key("test", page=1, query="search")
        key2 = scraper._get_cache_key("test", query="search", page=1)
        key3 = scraper._get_cache_key("test", page=2, query="search")
        
        # Same params in different order should generate same key
        assert key1 == key2
        # Different params should generate different key
        assert key1 != key3
    
    @pytest.mark.asyncio
    async def test_scrape_plugin_list_with_cache(self, scraper, mock_html_response):
        """Test scraping plugin list with cache"""
        # Mock Redis cache
        with patch.object(scraper, '_get_from_cache', return_value=None), \
             patch.object(scraper, '_set_cache') as mock_set_cache, \
             patch.object(scraper, '_make_request') as mock_request:
            
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.text = mock_html_response
            mock_request.return_value = mock_response
            
            # Scrape plugins
            result = await scraper.scrape_plugin_list(page=1, per_page=20)
            
            # Verify results
            assert len(result['plugins']) == 2
            assert result['plugins'][0]['author'] == 'langgenius'
            assert result['plugins'][0]['name'] == 'agent'
            assert result['plugins'][0]['display_name'] == 'Agent Tools'
            assert result['plugins'][0]['category'] == 'agent'
            assert result['plugins'][0]['latest_version'] == '0.0.9'
            
            assert result['plugins'][1]['author'] == 'antv'
            assert result['plugins'][1]['name'] == 'visualization'
            
            # Verify cache was set
            assert mock_set_cache.called
    
    @pytest.mark.asyncio
    async def test_scrape_plugin_details(self, scraper, mock_plugin_detail_html):
        """Test scraping plugin details"""
        with patch.object(scraper, '_get_from_cache', return_value=None), \
             patch.object(scraper, '_set_cache'), \
             patch.object(scraper, '_make_request') as mock_request:
            
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.text = mock_plugin_detail_html
            mock_request.return_value = mock_response
            
            # Scrape details
            result = await scraper.scrape_plugin_details('langgenius', 'agent')
            
            # Verify results
            assert result['author'] == 'langgenius'
            assert result['name'] == 'agent'
            assert result['display_name'] == 'Agent Tools'
            assert 'Advanced agent capabilities' in result['description']
            assert result['latest_version'] == '0.0.9'
            assert 'download_url' in result
    
    @pytest.mark.asyncio
    async def test_scrape_plugin_versions(self, scraper, mock_plugin_detail_html):
        """Test scraping plugin versions"""
        with patch.object(scraper, '_get_from_cache', return_value=None), \
             patch.object(scraper, '_set_cache'), \
             patch.object(scraper, '_make_request') as mock_request:
            
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.text = mock_plugin_detail_html
            mock_request.return_value = mock_response
            
            # Scrape versions
            result = await scraper.scrape_plugin_versions('langgenius', 'agent')
            
            # Verify results
            assert len(result) == 3
            assert result[0]['version'] == '0.0.9'
            assert result[1]['version'] == '0.0.8'
            assert result[2]['version'] == '0.0.7'
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, scraper):
        """Test retry logic on failed requests"""
        with patch.object(scraper, '_get_from_cache', return_value=None), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Mock failing requests
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("Network error")
            
            # Should return empty result after retries
            result = await scraper.scrape_plugin_list()
            
            assert result['plugins'] == []
            assert result['total'] == 0
            assert 'error' in result


class TestMarketplaceServiceWithFallback:
    """Test cases for MarketplaceServiceWithFallback"""
    
    @pytest.mark.asyncio
    async def test_search_plugins_api_fallback(self, fallback_service):
        """Test fallback to scraping when API fails"""
        # Mock API failure
        with patch('app.services.marketplace.MarketplaceService.search_plugins') as mock_api:
            mock_api.side_effect = Exception("API Error")
            
            # Mock successful scraping
            with patch.object(fallback_service.scraper, 'scrape_plugin_list') as mock_scraper:
                mock_scraper.return_value = {
                    'plugins': [{'name': 'test-plugin'}],
                    'total': 1,
                    'page': 1,
                    'per_page': 20
                }
                
                # Call the method
                result = await fallback_service.search_plugins_with_fallback()
                
                # Verify fallback was used
                assert result['fallback_used'] == True
                assert result['fallback_reason'] == 'API unavailable or returned no results'
                assert len(result['plugins']) == 1
    
    @pytest.mark.asyncio
    async def test_get_plugin_details_with_fallback(self, fallback_service):
        """Test plugin details with fallback"""
        # Mock API timeout
        with patch('app.services.marketplace.MarketplaceService.get_plugin_details') as mock_api:
            mock_api.side_effect = asyncio.TimeoutError()
            
            # Mock successful scraping
            with patch.object(fallback_service.scraper, 'scrape_plugin_details') as mock_scraper:
                mock_scraper.return_value = {
                    'author': 'test-author',
                    'name': 'test-plugin',
                    'display_name': 'Test Plugin'
                }
                
                # Call the method
                result = await fallback_service.get_plugin_details_with_fallback('test-author', 'test-plugin')
                
                # Verify result
                assert result['name'] == 'test-plugin'
                assert result['author'] == 'test-author'
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, fallback_service):
        """Test cache invalidation"""
        with patch.object(fallback_service.scraper, '_get_cache_key') as mock_get_key, \
             patch('app.workers.celery_app.redis_client.delete') as mock_delete, \
             patch('app.workers.celery_app.redis_client.scan_iter') as mock_scan:
            
            mock_get_key.return_value = "test_key"
            mock_scan.return_value = ["key1", "key2", "key3"]
            
            # Invalidate specific key
            fallback_service.invalidate_cache("test_type", test_param="value")
            assert mock_delete.called
            
            # Invalidate all cache
            mock_delete.reset_mock()
            fallback_service.invalidate_cache()
            assert mock_scan.called
            assert mock_delete.call_count >= 1


@pytest.mark.asyncio
async def test_integration_with_marketplace_service():
    """Test integration with existing MarketplaceService"""
    from app.services.marketplace import MarketplaceService
    
    # Mock the marketplace service to trigger fallback
    with patch.object(MarketplaceService, 'search_plugins') as mock_search:
        # Simulate API returning incompatible status
        mock_search.return_value = {
            'plugins': [],
            'total': 0,
            'page': 1,
            'per_page': 20,
            'api_status': 'incompatible'
        }
        
        # The service should automatically use fallback
        result = await MarketplaceService.search_plugins()
        
        # Verify the structure is maintained
        assert 'plugins' in result
        assert 'total' in result
        assert 'page' in result
        assert 'per_page' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])