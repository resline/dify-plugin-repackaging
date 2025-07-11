"""
Unit tests for marketplace API endpoints
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from httpx import AsyncClient
import json
from datetime import datetime

from app.api.v1.endpoints.marketplace import router
from tests.factories.plugin import MarketplacePluginFactory, PluginFactory


class TestMarketplaceEndpoints:
    """Test cases for marketplace endpoints."""
    
    @pytest.mark.asyncio
    async def test_search_plugins_success(self, async_client: AsyncClient, mock_httpx_client):
        """Test successful plugin search."""
        # Arrange
        mock_plugins = [
            MarketplacePluginFactory.create(
                name="agent",
                author="langgenius",
                display_name="Agent Plugin",
                category="agent"
            ),
            MarketplacePluginFactory.create(
                name="visualization",
                author="antv",
                display_name="Visualization Plugin",
                category="tool"
            )
        ]
        
        with patch('app.api.v1.endpoints.marketplace.MarketplaceService') as mock_service:
            mock_service.return_value.search_plugins = AsyncMock(return_value={
                "plugins": mock_plugins,
                "total": 2,
                "page": 1,
                "per_page": 20
            })
            
            # Act
            response = await async_client.get("/api/v1/marketplace/plugins?q=plugin")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data["plugins"]) == 2
            assert data["total"] == 2
            assert data["plugins"][0]["name"] == "agent"
    
    @pytest.mark.asyncio
    async def test_search_plugins_with_filters(self, async_client: AsyncClient):
        """Test plugin search with filters."""
        # Arrange
        with patch('app.api.v1.endpoints.marketplace.MarketplaceService') as mock_service:
            mock_service.return_value.search_plugins = AsyncMock(return_value={
                "plugins": [MarketplacePluginFactory.create(author="langgenius")],
                "total": 1,
                "page": 1,
                "per_page": 20
            })
            
            # Act
            response = await async_client.get(
                "/api/v1/marketplace/plugins?author=langgenius&category=agent"
            )
            
            # Assert
            assert response.status_code == 200
            mock_service.return_value.search_plugins.assert_called_once_with(
                q=None,
                author="langgenius",
                category="agent",
                page=1,
                per_page=20
            )
    
    @pytest.mark.asyncio
    async def test_search_plugins_circuit_breaker_open(self, async_client: AsyncClient):
        """Test search when circuit breaker is open."""
        with patch('app.api.v1.endpoints.marketplace.marketplace_circuit_breaker') as mock_cb:
            mock_cb.is_open = True
            mock_cb.failure_count = 5
            mock_cb.last_failure_time = datetime.now()
            
            # Act
            response = await async_client.get("/api/v1/marketplace/plugins")
            
            # Assert
            assert response.status_code == 503
            assert "Marketplace service temporarily unavailable" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_plugin_details_success(self, async_client: AsyncClient):
        """Test getting plugin details successfully."""
        # Arrange
        plugin_details = MarketplacePluginFactory.create(
            author="langgenius",
            name="agent",
            display_name="Agent Plugin",
            versions=["0.0.9", "0.0.8", "0.0.7"]
        )
        
        with patch('app.api.v1.endpoints.marketplace.MarketplaceService') as mock_service:
            mock_service.return_value.get_plugin_details = AsyncMock(
                return_value=plugin_details
            )
            
            # Act
            response = await async_client.get("/api/v1/marketplace/plugins/langgenius/agent")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["author"] == "langgenius"
            assert data["name"] == "agent"
            assert len(data["versions"]) == 3
    
    @pytest.mark.asyncio
    async def test_get_plugin_details_not_found(self, async_client: AsyncClient):
        """Test getting details for non-existent plugin."""
        # Arrange
        with patch('app.api.v1.endpoints.marketplace.MarketplaceService') as mock_service:
            mock_service.return_value.get_plugin_details = AsyncMock(return_value=None)
            
            # Act
            response = await async_client.get("/api/v1/marketplace/plugins/unknown/plugin")
            
            # Assert
            assert response.status_code == 404
            assert "Plugin not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_plugin_version_success(self, async_client: AsyncClient):
        """Test getting specific plugin version."""
        # Arrange
        version_data = {
            "version": "0.0.9",
            "download_url": "https://marketplace.dify.ai/download/...",
            "size": 1024000,
            "release_date": "2024-01-15T00:00:00Z",
            "changelog": "- Fixed bugs\n- Added features",
            "dependencies": ["requests>=2.0.0", "pydantic>=2.0.0"]
        }
        
        with patch('app.api.v1.endpoints.marketplace.MarketplaceService') as mock_service:
            mock_service.return_value.get_plugin_version = AsyncMock(
                return_value=version_data
            )
            
            # Act
            response = await async_client.get(
                "/api/v1/marketplace/plugins/langgenius/agent/versions/0.0.9"
            )
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["version"] == "0.0.9"
            assert "download_url" in data
            assert len(data["dependencies"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_categories_success(self, async_client: AsyncClient):
        """Test getting marketplace categories."""
        # Arrange
        categories = [
            {"name": "agent", "display_name": "Agent", "count": 10},
            {"name": "tool", "display_name": "Tool", "count": 25},
            {"name": "model", "display_name": "Model", "count": 5}
        ]
        
        with patch('app.api.v1.endpoints.marketplace.MarketplaceService') as mock_service:
            mock_service.return_value.get_categories = AsyncMock(return_value=categories)
            
            # Act
            response = await async_client.get("/api/v1/marketplace/categories")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert data[0]["name"] == "agent"
            assert data[1]["count"] == 25
    
    @pytest.mark.asyncio
    async def test_get_featured_plugins(self, async_client: AsyncClient):
        """Test getting featured plugins."""
        # Arrange
        featured = [
            MarketplacePluginFactory.create(featured=True, rating=4.8),
            MarketplacePluginFactory.create(featured=True, rating=4.9)
        ]
        
        with patch('app.api.v1.endpoints.marketplace.MarketplaceService') as mock_service:
            mock_service.return_value.get_featured_plugins = AsyncMock(
                return_value=featured
            )
            
            # Act
            response = await async_client.get("/api/v1/marketplace/featured")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert all(p.get("featured", False) for p in data)
    
    @pytest.mark.asyncio
    async def test_pagination_validation(self, async_client: AsyncClient):
        """Test pagination parameter validation."""
        # Act & Assert
        # Test negative page
        response = await async_client.get("/api/v1/marketplace/plugins?page=-1")
        assert response.status_code == 422
        
        # Test page size too large
        response = await async_client.get("/api/v1/marketplace/plugins?per_page=101")
        assert response.status_code == 422
        
        # Test page size zero
        response = await async_client.get("/api/v1/marketplace/plugins?per_page=0")
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_error_handling_service_exception(self, async_client: AsyncClient):
        """Test error handling when service raises exception."""
        # Arrange
        with patch('app.api.v1.endpoints.marketplace.MarketplaceService') as mock_service:
            mock_service.return_value.search_plugins = AsyncMock(
                side_effect=Exception("Service error")
            )
            
            # Act
            response = await async_client.get("/api/v1/marketplace/plugins")
            
            # Assert
            assert response.status_code == 500
            assert "detail" in response.json()


class TestMarketplaceCache:
    """Test marketplace caching functionality."""
    
    @pytest.mark.asyncio
    async def test_search_results_cached(self, async_client: AsyncClient, mock_redis):
        """Test that search results are cached."""
        # Arrange
        cache_key = "marketplace:search:q=test:author=None:category=None:page=1:per_page=20"
        cached_data = {
            "plugins": [MarketplacePluginFactory.create()],
            "total": 1,
            "page": 1,
            "per_page": 20
        }
        mock_redis.get.return_value = json.dumps(cached_data).encode('utf-8')
        
        with patch('app.api.v1.endpoints.marketplace.MarketplaceService') as mock_service:
            # Act
            response = await async_client.get("/api/v1/marketplace/plugins?q=test")
            
            # Assert
            assert response.status_code == 200
            # Service should not be called if cache hit
            mock_service.return_value.search_plugins.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_miss_calls_service(self, async_client: AsyncClient, mock_redis):
        """Test that cache miss calls the service."""
        # Arrange
        mock_redis.get.return_value = None  # Cache miss
        
        with patch('app.api.v1.endpoints.marketplace.MarketplaceService') as mock_service:
            mock_service.return_value.search_plugins = AsyncMock(return_value={
                "plugins": [],
                "total": 0,
                "page": 1,
                "per_page": 20
            })
            
            # Act
            response = await async_client.get("/api/v1/marketplace/plugins")
            
            # Assert
            assert response.status_code == 200
            mock_service.return_value.search_plugins.assert_called_once()
            # Should attempt to cache the result
            mock_redis.set.assert_called_once()