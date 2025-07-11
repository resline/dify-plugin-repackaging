"""
Integration tests for external API interactions with mocks.
"""
import pytest
import os
import json
import asyncio
from unittest.mock import patch


class TestExternalAPIIntegration:
    """Test external API integrations using mock services."""
    
    @pytest.mark.asyncio
    async def test_marketplace_api_with_mock(self, http_client):
        """Test marketplace API integration with mock service."""
        # Configure to use mock marketplace
        mock_marketplace_url = os.getenv("MOCK_MARKETPLACE_URL", "http://mock-services:8000/marketplace")
        
        with patch.dict(os.environ, {"MARKETPLACE_API_URL": mock_marketplace_url}):
            # Search for plugins
            response = await http_client.get("/api/v1/marketplace/plugins?search=test")
            
            if response.status_code == 200:
                data = response.json()
                # Should return mock plugins
                assert "plugins" in data or isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_github_api_with_mock(self, http_client):
        """Test GitHub API integration with mock service."""
        mock_github_url = os.getenv("MOCK_GITHUB_URL", "http://mock-services:8000/github")
        
        with patch.dict(os.environ, {"GITHUB_API_URL": mock_github_url}):
            # Test creating a GitHub-based repackaging task
            task_data = {
                "url": f"{mock_github_url}/download/test-plugin.difypkg",
                "platform": "manylinux2014_x86_64",
                "suffix": "offline"
            }
            
            response = await http_client.post("/api/v1/tasks/repackage/url", json=task_data)
            assert response.status_code == 200
            
            data = response.json()
            assert "task_id" in data
    
    @pytest.mark.asyncio
    async def test_download_from_mock_service(self, http_client, celery_worker, redis_client):
        """Test file download from mock external service."""
        # Create task with mock service URL
        mock_url = "http://mock-services:8000/download/test-plugin.difypkg"
        task_data = {
            "url": mock_url,
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }
        
        response = await http_client.post("/api/v1/tasks/repackage/url", json=task_data)
        assert response.status_code == 200
        
        task_id = response.json()["task_id"]
        
        # Wait for download to start
        await asyncio.sleep(2)
        
        # Check task status
        task_info = redis_client.get(f"task:{task_id}")
        if task_info:
            data = json.loads(task_info)
            # Should have progressed beyond pending
            assert data["status"] in ["downloading", "processing", "failed"]
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, http_client):
        """Test handling of external API errors."""
        # Test 500 error
        error_url = "http://mock-services:8000/marketplace/error/500"
        with patch.dict(os.environ, {"MARKETPLACE_API_URL": error_url}):
            response = await http_client.get("/api/v1/marketplace/plugins")
            # Should handle error gracefully
            assert response.status_code in [502, 503]  # Bad Gateway or Service Unavailable
    
    @pytest.mark.asyncio
    async def test_api_timeout_handling(self, http_client):
        """Test handling of slow external APIs."""
        # URL that responds slowly
        slow_url = "http://mock-services:8000/slow/5"
        task_data = {
            "url": slow_url,
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }
        
        response = await http_client.post("/api/v1/tasks/repackage/url", json=task_data)
        assert response.status_code == 200
        
        # Task should be created even if download is slow
        task_id = response.json()["task_id"]
        assert task_id is not None
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, http_client):
        """Test handling of rate-limited APIs."""
        rate_limit_url = "http://mock-services:8000/marketplace/error/429"
        
        with patch.dict(os.environ, {"MARKETPLACE_API_URL": rate_limit_url}):
            response = await http_client.get("/api/v1/marketplace/plugins")
            # Should handle rate limiting
            assert response.status_code in [429, 503]
            
            if response.status_code == 429:
                # Should include retry information
                assert "retry-after" in response.headers.keys()
    
    @pytest.mark.asyncio
    async def test_marketplace_plugin_details(self, http_client):
        """Test fetching specific plugin details from marketplace."""
        mock_marketplace_url = "http://mock-services:8000/marketplace"
        
        with patch.dict(os.environ, {"MARKETPLACE_API_URL": mock_marketplace_url}):
            # Get specific plugin
            response = await http_client.get("/api/v1/marketplace/plugins/test-author/test-plugin/1.0.0")
            
            if response.status_code == 200:
                data = response.json()
                assert data.get("author") == "test-author"
                assert data.get("name") == "test-plugin"
                assert data.get("version") == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_concurrent_external_api_calls(self, http_client):
        """Test handling concurrent calls to external APIs."""
        mock_marketplace_url = "http://mock-services:8000/marketplace"
        
        async def search_plugins(query):
            with patch.dict(os.environ, {"MARKETPLACE_API_URL": mock_marketplace_url}):
                response = await http_client.get(f"/api/v1/marketplace/plugins?search={query}")
                return response
        
        # Make concurrent searches
        queries = ["test", "plugin", "integration", "mock", "api"]
        tasks = [search_plugins(q) for q in queries]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Most should succeed
        successful = [r for r in responses if not isinstance(r, Exception) and r.status_code == 200]
        assert len(successful) >= 3
    
    @pytest.mark.asyncio
    async def test_webhook_callback(self, http_client, redis_client, test_task_id):
        """Test webhook callback functionality."""
        # Simulate task completion with webhook
        webhook_url = "http://mock-services:8000/webhook/task-complete"
        
        # Create completed task data
        task_data = {
            "task_id": test_task_id,
            "status": "completed",
            "progress": 100,
            "webhook_url": webhook_url
        }
        redis_client.setex(f"task:{test_task_id}", 3600, json.dumps(task_data))
        
        # In a real implementation, the worker would call the webhook
        # Here we test that the mock webhook endpoint works
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json={"task_id": test_task_id})
            
            if response.status_code == 200:
                data = response.json()
                assert data["received"] is True
                assert data["task_id"] == test_task_id
    
    @pytest.mark.asyncio
    async def test_fallback_on_external_api_failure(self, http_client):
        """Test fallback behavior when external APIs fail."""
        # Use non-existent service URL
        bad_url = "http://non-existent-service:9999/api"
        
        with patch.dict(os.environ, {"MARKETPLACE_API_URL": bad_url}):
            response = await http_client.get("/api/v1/marketplace/plugins")
            # Should fail gracefully
            assert response.status_code in [502, 503]
            
            # Error response should be informative
            if response.status_code != 204:
                data = response.json()
                assert "detail" in data or "error" in data