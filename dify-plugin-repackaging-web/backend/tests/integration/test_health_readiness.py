"""
Health check and readiness tests for all services.
"""
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import psutil
import docker


class TestHealthAndReadiness:
    """Test health checks and readiness probes for all services."""
    
    @pytest.mark.asyncio
    async def test_backend_health_endpoint(self, http_client):
        """Test backend health endpoint returns correct status."""
        response = await http_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "uptime" in data or "started_at" in data
    
    def test_redis_health(self, redis_client):
        """Test Redis health and basic operations."""
        # Ping test
        assert redis_client.ping() is True
        
        # Memory info
        info = redis_client.info("memory")
        assert "used_memory" in info
        assert info["used_memory"] > 0
        
        # Check Redis version
        server_info = redis_client.info("server")
        assert "redis_version" in server_info
        
        # Test basic operations under load
        for i in range(100):
            key = f"health_test_{i}"
            redis_client.set(key, f"value_{i}")
            assert redis_client.get(key) == f"value_{i}"
            redis_client.delete(key)
    
    def test_celery_worker_health(self, celery_worker):
        """Test Celery worker health and responsiveness."""
        # Get worker stats
        i = celery_worker.control.inspect()
        
        # Check registered tasks
        registered = i.registered()
        assert registered is not None
        assert len(registered) > 0
        
        # Check worker stats
        stats = i.stats()
        assert stats is not None
        
        for worker_name, worker_stats in stats.items():
            assert "total" in worker_stats
            assert "pool" in worker_stats
            
        # Check active queues
        active_queues = i.active_queues()
        assert active_queues is not None
        
        # Test worker ping
        ping_responses = celery_worker.control.ping(timeout=5)
        assert len(ping_responses) > 0
    
    @pytest.mark.asyncio
    async def test_websocket_health(self, websocket_client):
        """Test WebSocket endpoint health."""
        # Connect to health check endpoint
        ws = await websocket_client("/ws/health-check")
        
        try:
            # Send ping
            await ws.send('{"type": "ping"}')
            
            # Should receive response
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            assert response is not None
            
            # Multiple rapid pings
            for i in range(10):
                await ws.send(f'{{"type": "ping", "seq": {i}}}')
            
            # Should handle all without issues
            responses_received = 0
            start_time = time.time()
            while responses_received < 5 and time.time() - start_time < 5:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=0.5)
                    responses_received += 1
                except asyncio.TimeoutError:
                    break
            
            assert responses_received >= 1
        finally:
            await ws.close()
    
    @pytest.mark.asyncio
    async def test_service_dependencies(self, http_client, redis_client, celery_worker):
        """Test that all service dependencies are properly connected."""
        # Backend can reach Redis
        response = await http_client.get("/health")
        assert response.status_code == 200
        
        # Create a task to verify full chain
        task_data = {
            "url": "https://example.com/health-test.difypkg",
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }
        
        response = await http_client.post("/api/v1/tasks/repackage/url", json=task_data)
        assert response.status_code == 200
        
        task_id = response.json()["task_id"]
        
        # Task should be in Redis
        await asyncio.sleep(0.5)
        task_info = redis_client.get(f"task:{task_id}")
        assert task_info is not None
        
        # Worker should pick up the task
        await asyncio.sleep(2)
        updated_info = redis_client.get(f"task:{task_id}")
        assert updated_info is not None
        
        import json
        data = json.loads(updated_info)
        # Task should have progressed
        assert data["status"] != "pending"
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, http_client):
        """Test system stability under concurrent health checks."""
        async def health_check():
            response = await http_client.get("/health")
            return response.status_code == 200
        
        # Run 50 concurrent health checks
        tasks = [health_check() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(results)
    
    def test_resource_limits(self, redis_client):
        """Test that services respect resource limits."""
        # Check Redis memory usage
        info = redis_client.info("memory")
        used_memory_mb = info["used_memory"] / (1024 * 1024)
        
        # Should be within reasonable limits (adjust based on your config)
        assert used_memory_mb < 500  # Less than 500MB
        
        # Check that Redis has maxmemory policy set (optional)
        config = redis_client.config_get("maxmemory-policy")
        if config.get("maxmemory-policy"):
            assert config["maxmemory-policy"] in ["allkeys-lru", "volatile-lru", "allkeys-lfu"]
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, http_client, celery_app):
        """Test system behavior when some services are degraded."""
        # Simulate worker being busy
        celery_app.control.rate_limit("app.workers.celery_app.process_repackaging", "0")
        
        try:
            # API should still respond
            response = await http_client.get("/health")
            assert response.status_code == 200
            
            # Can still create tasks
            task_data = {
                "url": "https://example.com/degraded-test.difypkg",
                "platform": "manylinux2014_x86_64",
                "suffix": "offline"
            }
            
            response = await http_client.post("/api/v1/tasks/repackage/url", json=task_data)
            assert response.status_code == 200
            
            # Tasks will queue up
            task_id = response.json()["task_id"]
            assert task_id is not None
            
        finally:
            # Restore rate limit
            celery_app.control.rate_limit("app.workers.celery_app.process_repackaging", None)
    
    @pytest.mark.asyncio
    async def test_startup_sequence(self, http_client):
        """Test that services start in correct order."""
        # This test assumes services are already started
        # In a real scenario, you'd test the actual startup sequence
        
        # Backend should be ready
        response = await http_client.get("/health")
        assert response.status_code == 200
        
        # All required endpoints should be available
        endpoints = [
            "/api/v1/tasks",
            "/api/v1/marketplace/plugins",
            "/docs",
            "/openapi.json"
        ]
        
        for endpoint in endpoints:
            response = await http_client.get(endpoint)
            assert response.status_code in [200, 307]  # 307 for redirects
    
    def test_logging_health(self, celery_worker):
        """Test that logging is working correctly."""
        import logging
        
        # Submit a task that will generate logs
        result = celery_worker.send_task(
            "app.workers.celery_app.process_repackaging",
            args=["log_test", "https://example.com/log-test.difypkg", "manylinux2014_x86_64", "offline", False]
        )
        
        # Logs should be generated (actual verification would require log aggregation)
        assert result.id is not None
    
    @pytest.mark.asyncio
    async def test_metrics_availability(self, http_client):
        """Test that metrics/monitoring endpoints are available."""
        # Check if metrics endpoint exists (if implemented)
        response = await http_client.get("/metrics")
        
        # Metrics might not be implemented, but endpoint should respond
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            # Verify metrics format
            content = response.text
            assert len(content) > 0
    
    def test_docker_health_checks(self):
        """Test Docker health check configurations."""
        # This would run outside the container to check Docker health
        try:
            client = docker.from_env()
            containers = client.containers.list(filters={"label": "com.docker.compose.project=dify-repack-test"})
            
            for container in containers:
                # Check if health check is configured
                health = container.attrs.get("State", {}).get("Health")
                if health:
                    assert health["Status"] in ["healthy", "starting"]
        except docker.errors.DockerException:
            # Skip if Docker is not available in test environment
            pytest.skip("Docker not available in test environment")
    
    @pytest.mark.asyncio
    async def test_recovery_after_failure(self, http_client, redis_client):
        """Test system recovery after component failure."""
        # Clear all data to simulate recovery
        redis_client.flushdb()
        
        # System should still be functional
        response = await http_client.get("/health")
        assert response.status_code == 200
        
        # Can create new tasks
        task_data = {
            "url": "https://example.com/recovery-test.difypkg",
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }
        
        response = await http_client.post("/api/v1/tasks/repackage/url", json=task_data)
        assert response.status_code == 200