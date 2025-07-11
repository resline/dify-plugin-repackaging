"""
Integration test configuration and fixtures.
"""
import os
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
import redis
import httpx
from celery import Celery
import time
from tenacity import retry, stop_after_delay, wait_fixed
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6380/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6380/0")


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def redis_client() -> Generator[redis.Redis, None, None]:
    """Provide a Redis client for tests."""
    client = redis.from_url(REDIS_URL, decode_responses=True)
    
    # Wait for Redis to be ready
    @retry(stop=stop_after_delay(30), wait=wait_fixed(1))
    def wait_for_redis():
        client.ping()
        logger.info("Redis is ready")
    
    wait_for_redis()
    yield client
    client.close()


@pytest.fixture(scope="session")
def celery_app() -> Celery:
    """Provide a Celery app instance for tests."""
    from app.workers.celery_app import celery_app
    return celery_app


@pytest_asyncio.fixture(scope="session")
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async HTTP client for API tests."""
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30.0) as client:
        # Wait for backend to be ready
        @retry(stop=stop_after_delay(30), wait=wait_fixed(1))
        async def wait_for_backend():
            response = await client.get("/health")
            response.raise_for_status()
            logger.info("Backend is ready")
        
        await wait_for_backend()
        yield client


@pytest.fixture(scope="function")
def clean_redis(redis_client):
    """Clean Redis before and after each test."""
    # Clean before test
    redis_client.flushdb()
    yield
    # Clean after test
    redis_client.flushdb()


@pytest.fixture(scope="function")
def test_task_id():
    """Generate a unique task ID for testing."""
    import uuid
    return str(uuid.uuid4())


@pytest.fixture(scope="function")
def mock_plugin_file(tmp_path):
    """Create a mock plugin file for testing."""
    plugin_file = tmp_path / "test_plugin.difypkg"
    plugin_file.write_bytes(b"Mock plugin content")
    return str(plugin_file)


@pytest_asyncio.fixture
async def websocket_client():
    """Provide a WebSocket client for testing."""
    import websockets
    
    async def connect(path: str):
        uri = f"ws://localhost:8000{path}"
        return await websockets.connect(uri)
    
    return connect


@pytest.fixture
def celery_worker(celery_app):
    """Ensure Celery worker is running and healthy."""
    @retry(stop=stop_after_delay(30), wait=wait_fixed(1))
    def wait_for_worker():
        # Check if worker is responding
        i = celery_app.control.inspect()
        stats = i.stats()
        if not stats:
            raise Exception("No Celery workers available")
        logger.info(f"Celery workers ready: {list(stats.keys())}")
    
    wait_for_worker()
    return celery_app


class IntegrationTestHelpers:
    """Helper methods for integration tests."""
    
    @staticmethod
    async def wait_for_task_completion(redis_client, task_id: str, timeout: int = 60):
        """Wait for a task to complete or fail."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            task_data = redis_client.get(f"task:{task_id}")
            if task_data:
                import json
                data = json.loads(task_data)
                status = data.get("status")
                if status in ["completed", "failed"]:
                    return data
            await asyncio.sleep(0.5)
        raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")
    
    @staticmethod
    async def create_test_task(http_client: httpx.AsyncClient, task_type: str = "url", **kwargs):
        """Create a test task via API."""
        if task_type == "url":
            data = {
                "url": kwargs.get("url", "https://example.com/plugin.difypkg"),
                "platform": kwargs.get("platform", "manylinux2014_x86_64"),
                "suffix": kwargs.get("suffix", "offline")
            }
            response = await http_client.post("/api/v1/tasks/repackage/url", json=data)
        elif task_type == "marketplace":
            data = {
                "author": kwargs.get("author", "test-author"),
                "name": kwargs.get("name", "test-plugin"),
                "version": kwargs.get("version", "1.0.0"),
                "platform": kwargs.get("platform", "manylinux2014_x86_64"),
                "suffix": kwargs.get("suffix", "offline")
            }
            response = await http_client.post("/api/v1/tasks/repackage/marketplace", json=data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
        
        response.raise_for_status()
        return response.json()
    
    @staticmethod
    def create_redis_task_data(task_id: str, status: str = "pending", **kwargs):
        """Create task data in Redis for testing."""
        import json
        from datetime import datetime
        
        task_data = {
            "task_id": task_id,
            "status": status,
            "progress": kwargs.get("progress", 0),
            "message": kwargs.get("message", ""),
            "created_at": kwargs.get("created_at", datetime.utcnow().isoformat()),
            "updated_at": datetime.utcnow().isoformat()
        }
        task_data.update(kwargs)
        return json.dumps(task_data)


@pytest.fixture
def test_helpers():
    """Provide test helper methods."""
    return IntegrationTestHelpers()