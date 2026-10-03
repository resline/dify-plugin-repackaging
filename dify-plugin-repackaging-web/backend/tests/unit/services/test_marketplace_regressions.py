"""Regression tests for Marketplace API compatibility fallbacks."""

import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.services.marketplace import MarketplaceService
from app.services.marketplace_scraper import MarketplaceScraper


def async_context(value):
    """Build a minimal async context manager returning ``value``."""
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=value)
    context.__aexit__ = AsyncMock(return_value=None)
    return context


@pytest.mark.asyncio
async def test_search_plugins_uses_scraper_for_non_json_api_response():
    scraped_result = {
        "plugins": [{"author": "test", "name": "plugin"}],
        "total": 1,
        "page": 1,
        "per_page": 20,
    }
    fallback = MagicMock()
    fallback.scraper.scrape_plugin_list = AsyncMock(return_value=scraped_result)

    with (
        patch.object(MarketplaceService, "_get_from_cache", return_value=None),
        patch.object(MarketplaceService, "_set_cache"),
        patch(
            "app.services.marketplace.get_async_client",
            return_value=async_context(AsyncMock()),
        ),
        patch.object(
            MarketplaceService,
            "_make_api_request",
            new=AsyncMock(side_effect=ValueError("API returned HTML instead of JSON")),
        ),
        patch(
            "app.services.marketplace_scraper.marketplace_fallback_service",
            fallback,
        ),
    ):
        result = await MarketplaceService.search_plugins(query="plugin")

    assert result["plugins"] == scraped_result["plugins"]
    assert result["fallback_used"] is True
    fallback.scraper.scrape_plugin_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_plugin_versions_uses_scraper_for_invalid_json():
    response = Mock()
    response.raise_for_status = Mock()
    response.json.side_effect = json.JSONDecodeError("Invalid JSON", "<html>", 0)
    client = AsyncMock()
    client.get.return_value = response

    fallback = MagicMock()
    fallback.scraper.scrape_plugin_versions = AsyncMock(
        return_value=[{"version": "1.2.3"}],
    )

    with (
        patch.object(MarketplaceService, "_get_from_cache", return_value=None),
        patch.object(MarketplaceService, "_set_cache"),
        patch("httpx.AsyncClient", return_value=async_context(client)),
        patch(
            "app.services.marketplace_scraper.marketplace_fallback_service",
            fallback,
        ),
    ):
        result = await MarketplaceService.get_plugin_versions("test", "plugin")

    assert result == [{"version": "1.2.3"}]
    fallback.scraper.scrape_plugin_versions.assert_awaited_once_with("test", "plugin")


@pytest.mark.asyncio
async def test_scraper_normalizes_decorated_select_version():
    scraper = MarketplaceScraper()
    response = Mock()
    response.text = """
        <html><body>
          <h1>Plugin</h1>
          <select name="version">
            <option>Download v0.0.9 / v0.0.9 (latest)</option>
          </select>
        </body></html>
    """

    with (
        patch.object(scraper, "_get_from_cache", return_value=None),
        patch.object(scraper, "_set_cache"),
        patch.object(scraper, "_make_request", new=AsyncMock(return_value=response)),
    ):
        details = await scraper.scrape_plugin_details("test", "plugin")

    assert details is not None
    assert details["latest_version"] == "0.0.9"
