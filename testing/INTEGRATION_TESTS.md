# Integration Tests Documentation

## Overview

This directory contains comprehensive integration tests for the dify-plugin-repackaging application. The tests verify that all services work correctly together, including API, Redis, Celery workers, WebSocket connections, and file system operations.

## Test Structure

```
testing/
├── mock-services/         # Mock external services (GitHub, Marketplace)
│   ├── Dockerfile
│   └── main.py           # FastAPI mock service implementation
└── INTEGRATION_TESTS.md  # This file

dify-plugin-repackaging-web/backend/tests/integration/
├── conftest.py                      # Shared fixtures and configuration
├── utils.py                         # Test utilities and helpers
├── test_redis_integration.py        # Redis connectivity and operations
├── test_celery_integration.py       # Celery worker functionality
├── test_websocket_integration.py    # WebSocket pub/sub through Redis
├── test_api_integration.py          # API endpoint integration
├── test_filesystem_integration.py   # File system operations
├── test_external_api_integration.py # External API with mocks
└── test_health_readiness.py         # Health checks and readiness probes
```

## Running Integration Tests

### Prerequisites

- Docker and Docker Compose installed
- Python 3.12+ (for local development)
- At least 4GB of available RAM
- 10GB of free disk space

### Quick Start

```bash
# Run all integration tests
./run_integration_tests.sh

# Run with coverage report
./run_integration_tests.sh --coverage

# Run specific test file
./run_integration_tests.sh --test test_redis_integration.py

# Keep services running after tests (for debugging)
./run_integration_tests.sh --keep-running

# Verbose output
./run_integration_tests.sh --verbose
```

### Manual Testing

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run tests manually
docker-compose -f docker-compose.test.yml run --rm test-runner pytest -v tests/integration/

# Check service logs
docker-compose -f docker-compose.test.yml logs -f backend
docker-compose -f docker-compose.test.yml logs -f worker

# Stop test environment
docker-compose -f docker-compose.test.yml down -v
```

## Test Categories

### 1. Redis Integration Tests
- Connection and basic operations
- Task data storage and retrieval
- Pub/sub functionality
- Concurrent updates handling
- Data expiration
- Bulk operations

### 2. Celery Worker Integration Tests
- Worker connectivity and health
- Task submission and lifecycle
- Marketplace task processing
- Concurrent task handling
- Task retry mechanisms
- Cleanup task execution
- Progress updates via Redis

### 3. WebSocket Integration Tests
- Basic connection establishment
- Task updates via pub/sub
- Multiple client connections
- Reconnection handling
- Error recovery
- Heartbeat/ping mechanism
- Integration with Celery tasks

### 4. API Integration Tests
- Health endpoints
- Task creation (URL, marketplace, file upload)
- Task status retrieval
- File downloads
- Rate limiting
- CORS handling
- Error responses
- Concurrent API calls

### 5. File System Integration Tests
- Shared volume access between services
- Temp directory isolation
- File cleanup after tasks
- Large file handling
- Concurrent file operations
- Script directory access
- Permission handling

### 6. External API Integration Tests
- Mock marketplace API
- Mock GitHub API
- Download from external sources
- Error handling (500, 503, 429)
- Timeout handling
- Rate limit responses
- Webhook callbacks

### 7. Health and Readiness Tests
- Service health endpoints
- Resource limit compliance
- Graceful degradation
- Startup sequence verification
- Recovery after failures

## Test Environment

The test environment uses a separate Docker Compose configuration (`docker-compose.test.yml`) that includes:

- **test-redis**: Isolated Redis instance on port 6380
- **test-backend**: API service with debug logging
- **test-worker**: Celery worker with limited concurrency
- **test-beat**: Celery beat for scheduled tasks
- **test-runner**: Dedicated container for running tests
- **mock-services**: Mock external APIs (GitHub, Marketplace)

## Test Utilities

### ServiceOrchestrator
Manages Docker Compose services for tests:
```python
orchestrator = ServiceOrchestrator()
orchestrator.start_services()
orchestrator.scale_service("worker", 3)
logs = orchestrator.get_service_logs("backend")
orchestrator.stop_services()
```

### HealthChecks
Verify service readiness:
```python
HealthChecks.check_redis()
await HealthChecks.check_backend()
HealthChecks.check_celery_worker()
await HealthChecks.check_websocket()
```

### TestDataGenerator
Create test data:
```python
# Create mock plugin file
TestDataGenerator.create_mock_plugin_file("test.difypkg", size_mb=5)

# Generate task data
task_data = TestDataGenerator.generate_task_data("marketplace", 
    author="test", name="plugin", version="1.0.0")
```

### PerformanceMonitor
Track operation performance:
```python
monitor = PerformanceMonitor()
with monitor.measure("api_call"):
    response = await http_client.get("/api/v1/tasks")

stats = monitor.get_stats("api_call")
print(f"Average time: {stats['avg']}s")
```

### ChaosMonkey
Test resilience:
```python
chaos = ChaosMonkey(orchestrator)
await chaos.kill_random_worker()
await chaos.introduce_network_delay("backend", 500)
await chaos.fill_disk_space("worker", 100)
```

## CI/CD Integration

The integration tests run automatically on:
- Push to main or develop branches
- Pull requests to main
- Daily schedule (2 AM UTC)

GitHub Actions workflow features:
- Docker layer caching
- Parallel test execution
- Test result publishing
- Coverage reporting to Codecov
- Artifact upload for debugging

## Debugging Failed Tests

1. **Check test logs**:
   ```bash
   # View test output
   cat test-results/report.html
   
   # Check service logs
   docker-compose -f docker-compose.test.yml logs backend
   ```

2. **Run tests interactively**:
   ```bash
   # Start services
   docker-compose -f docker-compose.test.yml up -d
   
   # Exec into test runner
   docker-compose -f docker-compose.test.yml exec test-runner bash
   
   # Run specific test with debugging
   pytest -v -s tests/integration/test_redis_integration.py::TestRedisIntegration::test_redis_connection
   ```

3. **Check service health**:
   ```bash
   # Check container status
   docker-compose -f docker-compose.test.yml ps
   
   # Test Redis connection
   docker-compose -f docker-compose.test.yml exec test-redis redis-cli ping
   
   # Check Celery workers
   docker-compose -f docker-compose.test.yml exec test-worker celery -A app.workers.celery_app inspect active
   ```

## Best Practices

1. **Test Isolation**: Each test should clean up after itself
2. **Timeouts**: Use appropriate timeouts for async operations
3. **Retry Logic**: Include retry mechanisms for flaky operations
4. **Mock External Services**: Don't depend on real external APIs
5. **Parallel Safety**: Ensure tests can run in parallel
6. **Resource Cleanup**: Always clean up files and Redis keys

## Adding New Tests

1. Create test file in appropriate category
2. Use provided fixtures from `conftest.py`
3. Follow naming convention: `test_<feature>_integration.py`
4. Include docstrings explaining test purpose
5. Use `pytest.mark.asyncio` for async tests
6. Add cleanup in test teardown

Example:
```python
@pytest.mark.asyncio
async def test_new_feature(http_client, redis_client, clean_redis):
    """Test description here."""
    # Setup
    test_data = {"key": "value"}
    
    # Execute
    response = await http_client.post("/api/endpoint", json=test_data)
    
    # Verify
    assert response.status_code == 200
    
    # Cleanup handled by clean_redis fixture
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 6380, 8002 are free
2. **Docker daemon**: Check Docker is running
3. **Disk space**: Integration tests need ~5GB free space
4. **Memory**: Ensure at least 4GB RAM available
5. **Network issues**: Check Docker network connectivity

### Reset Test Environment

```bash
# Complete cleanup
docker-compose -f docker-compose.test.yml down -v
docker system prune -f
docker volume prune -f

# Rebuild everything
docker-compose -f docker-compose.test.yml build --no-cache
```