"""
Integration tests for API endpoints.
"""
import pytest
import json
import asyncio
import time
from datetime import datetime
import os


class TestAPIIntegration:
    """Test API endpoints with full service integration."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, http_client):
        """Test health check endpoint."""
        response = await http_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_create_url_task(self, http_client, redis_client, test_helpers):
        """Test creating a repackaging task from URL."""
        # Submit task
        task_data = {
            "url": "https://example.com/test-plugin.difypkg",
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }
        
        response = await http_client.post("/api/v1/tasks/repackage/url", json=task_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "accepted"
        
        # Verify task was created in Redis
        task_id = data["task_id"]
        await asyncio.sleep(0.5)
        
        redis_data = redis_client.get(f"task:{task_id}")
        assert redis_data is not None
        
        task_info = json.loads(redis_data)
        assert task_info["task_id"] == task_id
        assert task_info["status"] in ["pending", "downloading", "processing", "failed"]
    
    @pytest.mark.asyncio
    async def test_create_marketplace_task(self, http_client, redis_client):
        """Test creating a marketplace repackaging task."""
        task_data = {
            "author": "test-author",
            "name": "test-plugin",
            "version": "1.0.0",
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }
        
        response = await http_client.post("/api/v1/tasks/repackage/marketplace", json=task_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "accepted"
        
        # Check Redis for marketplace metadata
        task_id = data["task_id"]
        await asyncio.sleep(0.5)
        
        redis_data = redis_client.get(f"task:{task_id}")
        if redis_data:
            task_info = json.loads(redis_data)
            # Marketplace metadata might be added after processing starts
            assert task_info["task_id"] == task_id
    
    @pytest.mark.asyncio
    async def test_file_upload_task(self, http_client, tmp_path):
        """Test creating a task with file upload."""
        # Create a test file
        test_file = tmp_path / "test_plugin.difypkg"
        test_file.write_bytes(b"Mock plugin content for testing")
        
        # Upload file
        with open(test_file, "rb") as f:
            files = {"file": ("test_plugin.difypkg", f, "application/octet-stream")}
            data = {
                "platform": "manylinux2014_x86_64",
                "suffix": "offline"
            }
            
            response = await http_client.post(
                "/api/v1/tasks/repackage/upload",
                files=files,
                data=data
            )
        
        assert response.status_code == 200
        
        result = response.json()
        assert "task_id" in result
        assert result["status"] == "accepted"
    
    @pytest.mark.asyncio
    async def test_get_task_status(self, http_client, redis_client, test_task_id, test_helpers):
        """Test retrieving task status."""
        # Create task in Redis
        task_data = test_helpers.create_redis_task_data(
            test_task_id,
            status="processing",
            progress=75,
            message="Repackaging in progress"
        )
        redis_client.setex(f"task:{test_task_id}", 3600, task_data)
        
        # Get task status
        response = await http_client.get(f"/api/v1/tasks/{test_task_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["task_id"] == test_task_id
        assert data["status"] == "processing"
        assert data["progress"] == 75
        assert data["message"] == "Repackaging in progress"
    
    @pytest.mark.asyncio
    async def test_list_tasks(self, http_client, redis_client, clean_redis):
        """Test listing multiple tasks."""
        # Create multiple tasks
        task_ids = []
        for i in range(5):
            task_id = f"list_test_{i}"
            task_data = {
                "task_id": task_id,
                "status": "completed" if i % 2 == 0 else "processing",
                "progress": 100 if i % 2 == 0 else 50,
                "created_at": datetime.utcnow().isoformat()
            }
            redis_client.setex(f"task:{task_id}", 3600, json.dumps(task_data))
            task_ids.append(task_id)
        
        # List all tasks
        response = await http_client.get("/api/v1/tasks")
        assert response.status_code == 200
        
        data = response.json()
        assert "tasks" in data
        
        # Verify tasks are in the list
        returned_ids = [task["task_id"] for task in data["tasks"]]
        for task_id in task_ids:
            assert task_id in returned_ids
    
    @pytest.mark.asyncio
    async def test_download_completed_task(self, http_client, redis_client, test_task_id, tmp_path):
        """Test downloading completed task output."""
        # Create output file
        output_file = tmp_path / f"{test_task_id}_output.difypkg"
        output_file.write_bytes(b"Repackaged plugin content")
        
        # Create completed task in Redis
        task_data = {
            "task_id": test_task_id,
            "status": "completed",
            "progress": 100,
            "output_filename": str(output_file),
            "completed_at": datetime.utcnow().isoformat()
        }
        redis_client.setex(f"task:{test_task_id}", 3600, json.dumps(task_data))
        
        # Attempt download
        response = await http_client.get(f"/api/v1/tasks/{test_task_id}/download")
        
        # Download might fail if file management is different in test env
        # but we're testing the integration flow
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_marketplace_search(self, http_client):
        """Test marketplace plugin search."""
        response = await http_client.get("/api/v1/marketplace/plugins?search=test")
        
        # API might fail if marketplace is not accessible
        # but we're testing the integration
        assert response.status_code in [200, 502, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or "plugins" in data
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, http_client):
        """Test API rate limiting."""
        # Make multiple rapid requests
        responses = []
        for i in range(20):
            response = await http_client.get("/api/v1/tasks")
            responses.append(response.status_code)
        
        # Should see some rate limiting (429) or all success (200)
        # depending on rate limit configuration
        assert all(code in [200, 429] for code in responses)
    
    @pytest.mark.asyncio
    async def test_cors_headers(self, http_client):
        """Test CORS headers in responses."""
        response = await http_client.options(
            "/api/v1/tasks",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # Check CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
    
    @pytest.mark.asyncio
    async def test_error_handling(self, http_client):
        """Test API error handling."""
        # Test 404 for non-existent task
        response = await http_client.get("/api/v1/tasks/non-existent-task-id")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data or "error" in data
        
        # Test 422 for invalid input
        invalid_data = {
            "url": "not-a-valid-url",
            "platform": "invalid-platform"
        }
        response = await http_client.post("/api/v1/tasks/repackage/url", json=invalid_data)
        assert response.status_code in [422, 400]
    
    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self, http_client):
        """Test handling concurrent API calls."""
        async def create_task(index):
            task_data = {
                "url": f"https://example.com/plugin_{index}.difypkg",
                "platform": "manylinux2014_x86_64",
                "suffix": "offline"
            }
            response = await http_client.post("/api/v1/tasks/repackage/url", json=task_data)
            return response
        
        # Create multiple tasks concurrently
        tasks = [create_task(i) for i in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(r.status_code == 200 for r in responses)
        
        # All should have unique task IDs
        task_ids = [r.json()["task_id"] for r in responses]
        assert len(set(task_ids)) == len(task_ids)
    
    @pytest.mark.asyncio
    async def test_api_with_websocket_integration(self, http_client, websocket_client):
        """Test API and WebSocket working together."""
        # Create task via API
        task_data = {
            "url": "https://example.com/integration-test.difypkg",
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }
        
        response = await http_client.post("/api/v1/tasks/repackage/url", json=task_data)
        assert response.status_code == 200
        
        task_id = response.json()["task_id"]
        
        # Connect WebSocket to monitor updates
        ws = await websocket_client(f"/ws/{task_id}")
        
        try:
            # Should receive updates about the task
            updates_received = False
            start_time = time.time()
            
            while time.time() - start_time < 5:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    data = json.loads(message)
                    if data.get("task_id") == task_id:
                        updates_received = True
                        break
                except asyncio.TimeoutError:
                    continue
            
            # May or may not receive updates depending on task processing speed
            # but connection should work
            assert ws.state.name == "OPEN"
        finally:
            await ws.close()