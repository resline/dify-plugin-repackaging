"""
Pytest configuration and shared fixtures for all tests
"""

import os
import sys
import asyncio
import tempfile
from typing import Generator, AsyncGenerator
from unittest.mock import Mock, AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from redis import Redis
from celery import Celery

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.config import settings
from app.core.websocket_manager import WebSocketManager
from app.services.file_manager import FileManager


# Test environment setup
os.environ["TESTING"] = "true"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # Use different DB for tests


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("redis.Redis") as mock:
        redis_mock = Mock(spec=Redis)
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.delete.return_value = 1
        redis_mock.exists.return_value = False
        redis_mock.expire.return_value = True
        redis_mock.ttl.return_value = -1
        mock.return_value = redis_mock
        yield redis_mock


@pytest.fixture
def mock_celery():
    """Mock Celery app and tasks."""
    with patch("app.services.repackage.celery_app") as mock_app:
        # Mock Celery task
        mock_task = Mock()
        mock_task.delay.return_value = Mock(id="test-task-id-123")
        mock_task.AsyncResult.return_value = Mock(
            id="test-task-id-123",
            state="PENDING",
            info=None
        )
        mock_app.send_task.return_value = mock_task
        yield mock_app


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager."""
    manager = Mock(spec=WebSocketManager)
    manager.send_task_update = AsyncMock()
    manager.disconnect = AsyncMock()
    manager.send_heartbeat = AsyncMock()
    return manager


@pytest.fixture
def temp_directory():
    """Create a temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_file_manager(temp_directory):
    """Mock file manager with temporary directory."""
    manager = FileManager()
    # Override paths to use temp directory
    manager.base_dir = temp_directory
    manager.uploads_dir = os.path.join(temp_directory, "uploads")
    manager.output_dir = os.path.join(temp_directory, "output")
    os.makedirs(manager.uploads_dir, exist_ok=True)
    os.makedirs(manager.output_dir, exist_ok=True)
    return manager


@pytest.fixture
def sample_plugin_data():
    """Sample plugin data for testing."""
    return {
        "author": "langgenius",
        "name": "agent",
        "version": "0.0.9",
        "description": "A sample plugin for testing",
        "tags": ["agent", "tools"],
        "downloads": 1234,
        "updated_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_marketplace_response():
    """Sample marketplace API response."""
    return {
        "data": [
            {
                "author": "langgenius",
                "name": "agent",
                "version": "0.0.9",
                "description": "Agent tools plugin",
                "tags": ["agent", "tools"],
                "downloads": 1234,
                "updated_at": "2024-01-01T00:00:00Z"
            },
            {
                "author": "antv",
                "name": "visualization",
                "version": "0.1.7",
                "description": "Data visualization plugin",
                "tags": ["visualization", "charts"],
                "downloads": 5678,
                "updated_at": "2024-01-02T00:00:00Z"
            }
        ],
        "total": 2,
        "page": 1,
        "page_size": 10
    }


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for external API calls."""
    with patch("httpx.AsyncClient") as mock_class:
        mock_client = AsyncMock()
        mock_class.return_value.__aenter__.return_value = mock_client
        mock_class.return_value.__aexit__.return_value = None
        yield mock_client


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for shell command execution."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"Success", b"")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process
        yield mock_exec


@pytest.fixture
def auth_headers():
    """Authentication headers for protected endpoints."""
    return {"Authorization": "Bearer test-token-123"}


@pytest.fixture
def sample_file_upload(temp_directory):
    """Create a sample file for upload testing."""
    file_path = os.path.join(temp_directory, "test_plugin.difypkg")
    with open(file_path, "wb") as f:
        f.write(b"PK\x03\x04")  # ZIP file header
        f.write(b"Sample plugin content")
    
    with open(file_path, "rb") as f:
        yield {
            "file": ("test_plugin.difypkg", f, "application/zip")
        }


# Async fixtures for WebSocket testing
@pytest_asyncio.fixture
async def websocket_client():
    """Create a WebSocket test client."""
    from fastapi.testclient import TestClient
    client = TestClient(app)
    return client


# Test data factories
@pytest.fixture
def task_factory():
    """Factory for creating test task data."""
    def _create_task(task_id=None, status="pending", **kwargs):
        return {
            "task_id": task_id or "test-task-123",
            "status": status,
            "type": kwargs.get("type", "market"),
            "created_at": kwargs.get("created_at", "2024-01-01T00:00:00Z"),
            "updated_at": kwargs.get("updated_at", "2024-01-01T00:00:00Z"),
            "progress": kwargs.get("progress", 0),
            "message": kwargs.get("message", "Task created"),
            "result": kwargs.get("result", None),
            "error": kwargs.get("error", None),
            **kwargs
        }
    return _create_task


# Environment setup/teardown
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")
    monkeypatch.setenv("MARKETPLACE_API_URL", "https://marketplace.dify.ai")
    monkeypatch.setenv("GITHUB_API_URL", "https://api.github.com")
    yield
    # Cleanup if needed


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up after each test."""
    yield
    # Clear any remaining async tasks
    try:
        loop = asyncio.get_event_loop()
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
    except:
        pass