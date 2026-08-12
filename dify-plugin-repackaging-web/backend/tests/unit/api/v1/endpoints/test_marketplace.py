"""Contract tests for the marketplace API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services.marketplace import MarketplaceService


PLUGIN = {
    "author": "langgenius",
    "name": "agent",
    "display_name": "Agent Plugin",
    "description": "Agent tools",
    "category": "agent",
    "latest_version": "0.0.9",
    "versions": ["0.0.9", "0.0.8"],
}


class TestMarketplaceEndpoints:
    @pytest.mark.asyncio
    async def test_search_plugins_success(self, async_client: AsyncClient):
        result = {
            "plugins": [PLUGIN],
            "total": 1,
            "page": 1,
            "per_page": 20,
            "has_more": False,
        }
        with patch.object(
            MarketplaceService, "search_plugins", new=AsyncMock(return_value=result)
        ) as search:
            response = await async_client.get("/api/v1/marketplace/plugins?q=agent")

        assert response.status_code == 200
        assert response.json() == result
        search.assert_awaited_once_with(
            query="agent", author=None, category=None, page=1, per_page=20
        )

    @pytest.mark.asyncio
    async def test_search_plugins_forwards_filters(self, async_client: AsyncClient):
        with patch.object(
            MarketplaceService,
            "search_plugins",
            new=AsyncMock(return_value={"plugins": [], "total": 0}),
        ) as search:
            response = await async_client.get(
                "/api/v1/marketplace/plugins?author=langgenius&category=agent&page=2&per_page=5"
            )

        assert response.status_code == 200
        search.assert_awaited_once_with(
            query=None,
            author="langgenius",
            category="agent",
            page=2,
            per_page=5,
        )

    @pytest.mark.asyncio
    async def test_search_plugins_validates_pagination(self, async_client: AsyncClient):
        assert (await async_client.get("/api/v1/marketplace/plugins?page=0")).status_code == 422
        assert (
            await async_client.get("/api/v1/marketplace/plugins?per_page=101")
        ).status_code == 422

    @pytest.mark.asyncio
    async def test_search_plugins_maps_service_error(self, async_client: AsyncClient):
        with patch.object(
            MarketplaceService,
            "search_plugins",
            new=AsyncMock(side_effect=RuntimeError("Marketplace unavailable")),
        ):
            response = await async_client.get("/api/v1/marketplace/plugins")

        assert response.status_code == 500
        assert response.json()["detail"] == "Marketplace unavailable"

    @pytest.mark.asyncio
    async def test_get_plugin_details(self, async_client: AsyncClient):
        with patch.object(
            MarketplaceService, "get_plugin_details", new=AsyncMock(return_value=PLUGIN)
        ) as details:
            response = await async_client.get(
                "/api/v1/marketplace/plugins/langgenius/agent"
            )

        assert response.status_code == 200
        assert response.json()["latest_version"] == "0.0.9"
        details.assert_awaited_once_with("langgenius", "agent")

    @pytest.mark.asyncio
    async def test_get_plugin_details_not_found(self, async_client: AsyncClient):
        with patch.object(
            MarketplaceService, "get_plugin_details", new=AsyncMock(return_value=None)
        ):
            response = await async_client.get(
                "/api/v1/marketplace/plugins/unknown/plugin"
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_plugin_versions(self, async_client: AsyncClient):
        versions = [{"version": "0.0.9"}, {"version": "0.0.8"}]
        with patch.object(
            MarketplaceService, "get_plugin_versions", new=AsyncMock(return_value=versions)
        ):
            response = await async_client.get(
                "/api/v1/marketplace/plugins/langgenius/agent/versions"
            )

        assert response.status_code == 200
        assert response.json() == {"versions": versions}

    @pytest.mark.asyncio
    async def test_get_categories_uses_wrapped_contract(self, async_client: AsyncClient):
        with patch.object(
            MarketplaceService,
            "get_categories",
            new=AsyncMock(return_value=["agent", "tool"]),
        ):
            response = await async_client.get("/api/v1/marketplace/categories")

        assert response.status_code == 200
        assert response.json() == {"categories": ["agent", "tool"]}

    @pytest.mark.asyncio
    async def test_get_featured_plugins(self, async_client: AsyncClient):
        result = {"plugins": [{**PLUGIN, "verified": True}], "total": 1}
        with patch.object(
            MarketplaceService, "search_plugins", new=AsyncMock(return_value=result)
        ):
            response = await async_client.get(
                "/api/v1/marketplace/plugins/featured?limit=1"
            )

        assert response.status_code == 200
        assert response.json()["featured"] is True
        assert response.json()["plugins"] == result["plugins"]
