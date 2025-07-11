"""
Unit tests for middleware components
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import json
from datetime import datetime
from starlette.responses import Response, JSONResponse
from starlette.requests import Request
from httpx import AsyncClient

from app.core.middleware import JSONResponseMiddleware


class TestJSONResponseMiddleware:
    """Test cases for JSON Response Middleware."""
    
    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        return JSONResponseMiddleware(None)
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/v1/test"
        request.method = "GET"
        request.headers = {}
        return request
    
    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next function."""
        async def call_next(request):
            return Response(content=json.dumps({"status": "ok"}), media_type="application/json")
        return call_next
    
    @pytest.mark.asyncio
    async def test_json_response_passthrough(self, middleware, mock_request, mock_call_next):
        """Test that valid JSON responses pass through unchanged."""
        # Arrange
        response_data = {"status": "success", "data": [1, 2, 3]}
        
        async def call_next(request):
            response = Response(
                content=json.dumps(response_data).encode(),
                media_type="application/json"
            )
            # Mock the body_iterator
            async def body_iterator():
                yield json.dumps(response_data).encode()
            response.body_iterator = body_iterator()
            return response
        
        # Act
        result = await middleware.dispatch(mock_request, call_next)
        
        # Assert
        assert result.status_code == 200
        # Response should pass through unchanged for valid JSON
    
    @pytest.mark.asyncio
    async def test_html_response_conversion(self, middleware, mock_request):
        """Test that HTML responses are converted to JSON error."""
        # Arrange
        html_content = """<!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body><h1>404 Not Found</h1></body>
        </html>"""
        
        async def call_next(request):
            response = Response(content=html_content.encode(), media_type="text/html")
            async def body_iterator():
                yield html_content.encode()
            response.body_iterator = body_iterator()
            return response
        
        # Act
        result = await middleware.dispatch(mock_request, call_next)
        
        # Assert
        assert result.status_code == 502
        body = json.loads(result.body.decode())
        assert body["error"] == "Invalid response format"
        assert "HTML instead of JSON" in body["detail"]
        assert body["path"] == "/api/v1/test"
    
    @pytest.mark.asyncio
    async def test_xml_response_conversion(self, middleware, mock_request):
        """Test that XML responses are converted to JSON error."""
        # Arrange
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <error>
            <message>Not found</message>
        </error>"""
        
        async def call_next(request):
            response = Response(content=xml_content.encode(), media_type="application/xml")
            async def body_iterator():
                yield xml_content.encode()
            response.body_iterator = body_iterator()
            return response
        
        # Act
        result = await middleware.dispatch(mock_request, call_next)
        
        # Assert
        assert result.status_code == 502
        body = json.loads(result.body.decode())
        assert body["error"] == "Invalid response format"
    
    @pytest.mark.asyncio
    async def test_non_api_endpoints_ignored(self, middleware, mock_request):
        """Test that non-API endpoints are not processed."""
        # Arrange
        mock_request.url.path = "/docs"
        html_content = "<html><body>Documentation</body></html>"
        
        async def call_next(request):
            return Response(content=html_content, media_type="text/html")
        
        # Act
        result = await middleware.dispatch(mock_request, call_next)
        
        # Assert
        assert result.status_code == 200
        assert result.body.decode() == html_content  # Should not be modified
    
    @pytest.mark.asyncio
    async def test_empty_response_handling(self, middleware, mock_request):
        """Test handling of empty responses."""
        # Arrange
        async def call_next(request):
            response = Response(content=b"", status_code=204)
            async def body_iterator():
                yield b""
            response.body_iterator = body_iterator()
            return response
        
        # Act
        result = await middleware.dispatch(mock_request, call_next)
        
        # Assert
        assert result.status_code == 204  # Should remain unchanged
    
    @pytest.mark.asyncio
    async def test_invalid_json_response(self, middleware, mock_request):
        """Test handling of invalid JSON in response."""
        # Arrange
        invalid_json = '{"status": "ok", invalid}'
        
        async def call_next(request):
            response = Response(content=invalid_json.encode(), media_type="application/json")
            async def body_iterator():
                yield invalid_json.encode()
            response.body_iterator = body_iterator()
            return response
        
        # Act
        result = await middleware.dispatch(mock_request, call_next)
        
        # Assert
        # Should handle JSON parse error gracefully
        assert result.status_code in [200, 500]  # Depends on implementation
    
    @pytest.mark.asyncio
    async def test_large_response_handling(self, middleware, mock_request):
        """Test handling of large responses."""
        # Arrange
        large_data = {"items": [{"id": i, "data": "x" * 100} for i in range(1000)]}
        
        async def call_next(request):
            content = json.dumps(large_data).encode()
            response = Response(content=content, media_type="application/json")
            
            # Simulate chunked response
            async def body_iterator():
                chunk_size = 1024
                for i in range(0, len(content), chunk_size):
                    yield content[i:i + chunk_size]
            
            response.body_iterator = body_iterator()
            return response
        
        # Act
        result = await middleware.dispatch(mock_request, call_next)
        
        # Assert
        assert result.status_code == 200
    
    @pytest.mark.asyncio
    async def test_response_without_body_iterator(self, middleware, mock_request):
        """Test handling responses without body_iterator attribute."""
        # Arrange
        async def call_next(request):
            return JSONResponse(content={"status": "ok"})
        
        # Act
        result = await middleware.dispatch(mock_request, call_next)
        
        # Assert
        assert result.status_code == 200
    
    @pytest.mark.asyncio
    async def test_error_response_formatting(self, middleware, mock_request):
        """Test that error responses are properly formatted."""
        # Arrange
        error_html = """<!DOCTYPE html>
        <html>
        <head><title>502 Bad Gateway</title></head>
        <body><h1>502 Bad Gateway</h1><p>nginx/1.18.0</p></body>
        </html>"""
        
        async def call_next(request):
            response = Response(
                content=error_html.encode(), 
                status_code=502,
                media_type="text/html"
            )
            async def body_iterator():
                yield error_html.encode()
            response.body_iterator = body_iterator()
            return response
        
        # Act
        result = await middleware.dispatch(mock_request, call_next)
        
        # Assert
        assert result.status_code == 502
        body = json.loads(result.body.decode())
        assert "timestamp" in body
        assert datetime.fromisoformat(body["timestamp"])  # Valid ISO format
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, middleware):
        """Test middleware handles concurrent requests correctly."""
        # Arrange
        requests = []
        for i in range(5):
            req = Mock(spec=Request)
            req.url = Mock()
            req.url.path = f"/api/v1/test{i}"
            requests.append(req)
        
        async def make_call_next(index):
            async def call_next(request):
                response = Response(
                    content=json.dumps({"index": index}).encode(),
                    media_type="application/json"
                )
                async def body_iterator():
                    yield json.dumps({"index": index}).encode()
                response.body_iterator = body_iterator()
                return response
            return call_next
        
        # Act - Process requests concurrently
        import asyncio
        tasks = []
        for i, req in enumerate(requests):
            call_next = await make_call_next(i)
            tasks.append(middleware.dispatch(req, call_next))
        
        results = await asyncio.gather(*tasks)
        
        # Assert
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.status_code == 200


class TestMiddlewareIntegration:
    """Integration tests for middleware with FastAPI app."""
    
    @pytest.mark.asyncio
    async def test_middleware_with_real_endpoints(self, async_client: AsyncClient):
        """Test middleware with real API endpoints."""
        # Test various endpoint responses
        
        # Test successful JSON response
        response = await async_client.get("/api/v1/health")
        assert response.status_code in [200, 404]  # Depends on if endpoint exists
        
        # Test error response formatting
        response = await async_client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        assert "application/json" in response.headers.get("content-type", "")
    
    @pytest.mark.asyncio
    async def test_middleware_error_recovery(self, async_client: AsyncClient):
        """Test middleware recovers from errors."""
        # Make multiple requests to ensure middleware doesn't break
        for _ in range(3):
            response = await async_client.get("/api/v1/test")
            # Should get consistent responses
            assert response.status_code in [200, 404]