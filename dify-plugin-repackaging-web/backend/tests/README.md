# Backend Tests

This directory contains the test suite for the dify-plugin-repackaging backend.

## Test Structure

```
tests/
├── unit/                   # Unit tests for individual components
│   ├── api/               # API endpoint tests
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── test_tasks.py
│   │           ├── test_marketplace.py
│   │           └── test_files.py
│   ├── services/          # Service layer tests
│   │   ├── test_repackage.py
│   │   ├── test_download.py
│   │   └── test_marketplace.py
│   └── core/              # Core component tests
│       ├── test_websocket_manager.py
│       └── test_middleware.py
├── integration/           # Integration tests
├── factories/             # Test data factories
│   └── plugin.py
├── fixtures/              # Test fixtures and sample data
└── conftest.py           # Pytest configuration and shared fixtures
```

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all unit tests
./run_unit_tests.sh

# Run with coverage
./run_unit_tests.sh coverage
```

### Test Commands

```bash
# Run specific test suites
./run_unit_tests.sh unit        # Unit tests only
./run_unit_tests.sh api         # API tests only
./run_unit_tests.sh services    # Service tests only
./run_unit_tests.sh core        # Core component tests only

# Run tests in parallel (faster)
./run_unit_tests.sh parallel

# Run tests in watch mode
./run_unit_tests.sh watch

# Run with pytest directly
pytest tests/unit -v
pytest tests/unit/api -v -k "test_create_task"
pytest tests/unit --cov=app --cov-report=html
```

## Test Guidelines

### Writing Tests

1. **Test Isolation**: Each test should be independent and not rely on other tests
2. **Use Fixtures**: Leverage pytest fixtures for common setup
3. **Mock External Dependencies**: Use mocks for Redis, Celery, HTTP calls, etc.
4. **Test Edge Cases**: Include tests for error conditions and edge cases
5. **Descriptive Names**: Use clear, descriptive test names that explain what is being tested

### Test Categories

Tests are organized by component type:

- **Unit Tests**: Test individual functions/methods in isolation
- **Integration Tests**: Test interaction between components
- **API Tests**: Test REST API endpoints
- **Service Tests**: Test business logic in service layer
- **WebSocket Tests**: Test real-time communication

### Using Test Factories

We use factory-boy for creating test data:

```python
from tests.factories.plugin import PluginFactory, TaskFactory

# Create test data
plugin = PluginFactory.create(
    author="langgenius",
    name="agent",
    version="0.0.9"
)

task = TaskFactory.create(
    status="processing",
    progress=50
)
```

### Common Fixtures

Available fixtures from `conftest.py`:

- `test_client`: FastAPI test client
- `async_client`: Async HTTP test client
- `mock_redis`: Mocked Redis client
- `mock_celery`: Mocked Celery app
- `mock_websocket_manager`: Mocked WebSocket manager
- `temp_directory`: Temporary directory for file operations
- `mock_file_manager`: File manager with temp directory
- `sample_plugin_data`: Sample plugin data
- `auth_headers`: Authentication headers

### Coverage Requirements

- Minimum coverage: 80%
- Focus on critical paths and business logic
- Exclude test files and migrations from coverage

## Debugging Tests

### Running Specific Tests

```bash
# Run a specific test file
pytest tests/unit/api/v1/endpoints/test_tasks.py

# Run a specific test class
pytest tests/unit/api/v1/endpoints/test_tasks.py::TestTasksEndpoint

# Run a specific test method
pytest tests/unit/api/v1/endpoints/test_tasks.py::TestTasksEndpoint::test_create_task_success

# Run tests matching a pattern
pytest -k "create_task"
```

### Debugging Options

```bash
# Show print statements
pytest -s

# Show local variables on failure
pytest -l

# Drop into debugger on failure
pytest --pdb

# Show slowest tests
pytest --durations=10
```

## Continuous Integration

Tests are automatically run on:
- Every push to main branch
- Every pull request
- Can be triggered manually

The CI pipeline:
1. Installs dependencies
2. Runs linting (ruff, black)
3. Runs type checking (mypy)
4. Runs unit tests with coverage
5. Uploads coverage reports

## Best Practices

1. **Keep Tests Fast**: Unit tests should run quickly (< 1 second each)
2. **Use Async Tests**: For async code, use `@pytest.mark.asyncio`
3. **Clean Up Resources**: Ensure files and connections are cleaned up
4. **Test Error Messages**: Verify error responses contain helpful messages
5. **Document Complex Tests**: Add comments for complex test scenarios

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure PYTHONPATH includes the project root
2. **Async Warnings**: Use `pytest-asyncio` for async tests
3. **Redis Connection**: Mock Redis for unit tests
4. **File Permissions**: Temp directories should be writable

### Getting Help

- Check test output for detailed error messages
- Run with `-vv` for verbose output
- Check `conftest.py` for available fixtures
- Review existing tests for examples