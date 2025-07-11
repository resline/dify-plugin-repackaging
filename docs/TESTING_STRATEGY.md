# Testing Strategy and CI/CD Pipeline Documentation

## Overview

This document outlines the comprehensive testing strategy and CI/CD pipeline for the Dify Plugin Repackaging project. Our testing approach ensures code quality, reliability, and compatibility across different environments.

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Types](#test-types)
3. [CI/CD Pipeline](#cicd-pipeline)
4. [Local Development](#local-development)
5. [Test Configuration](#test-configuration)
6. [Troubleshooting](#troubleshooting)

## Testing Philosophy

Our testing strategy follows these principles:

- **Test Early, Test Often**: Automated tests run on every commit
- **Fail Fast**: Quick feedback loops for developers
- **Comprehensive Coverage**: Multiple test types covering different aspects
- **Environment Parity**: Tests run in environments similar to production
- **Performance Awareness**: Tests should be fast and parallelizable

## Test Types

### 1. Unit Tests

**Purpose**: Test individual components in isolation

**Backend Unit Tests** (`dify-plugin-repackaging-web/backend/tests/unit/`)
- API endpoints
- Service layer logic
- Core utilities
- Middleware components

**Frontend Unit Tests** (`dify-plugin-repackaging-web/frontend/src/__tests__/`)
- React components
- Utility functions
- State management
- Custom hooks

**Running Locally**:
```bash
# Backend
cd dify-plugin-repackaging-web/backend
./run_unit_tests.sh

# Frontend
cd dify-plugin-repackaging-web/frontend
npm run test:unit
```

### 2. Integration Tests

**Purpose**: Test component interactions and external dependencies

**Coverage**:
- API integration with external services (Marketplace, GitHub)
- Database operations (Redis)
- Message queue operations (Celery)
- WebSocket connections
- File system operations

**Running Locally**:
```bash
./run_integration_tests.sh
```

### 3. End-to-End (E2E) Tests

**Purpose**: Test complete user workflows

**Test Scenarios**:
- Basic navigation
- URL submission workflow
- Marketplace plugin repackaging
- File upload and download
- Real-time updates via WebSocket
- Error recovery
- Visual regression

**Browsers Tested**:
- Chromium
- Firefox
- WebKit (Safari)
- Mobile viewports

**Running Locally**:
```bash
cd dify-plugin-repackaging-web/frontend
npx playwright test
```

### 4. Security Tests

**Purpose**: Identify security vulnerabilities

**Tools Used**:
- **Bandit**: Python AST-based security scanner
- **Safety**: Dependency vulnerability scanner
- **npm audit**: JavaScript dependency scanner
- **Semgrep**: Static analysis for security patterns

**Running Locally**:
```bash
# Python security
cd dify-plugin-repackaging-web/backend
bandit -r app/
safety check

# JavaScript security
cd dify-plugin-repackaging-web/frontend
npm audit
```

### 5. Performance Tests

**Purpose**: Ensure application performance under load

**Scenarios**:
- Concurrent user load
- Large file uploads
- API endpoint stress testing
- WebSocket connection limits

**Running Locally**:
```bash
cd testing/performance-tests
locust -f locustfile.py --host http://localhost:8000
```

## CI/CD Pipeline

### GitHub Actions Workflows

#### 1. Main CI/CD Pipeline (`.github/workflows/ci-cd.yml`)

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests to `main`
- Daily scheduled runs
- Manual workflow dispatch

**Jobs**:
1. **Code Quality Checks**: Linting and formatting
2. **Shell Script Analysis**: ShellCheck validation
3. **Backend Unit Tests**: Python test matrix
4. **Frontend Unit Tests**: Node.js test matrix
5. **Integration Tests**: Full stack testing
6. **E2E Tests**: Browser automation tests
7. **Security Tests**: Vulnerability scanning
8. **Performance Tests**: Load testing (main branch only)
9. **Docker Build**: Multi-platform image building
10. **Test Report**: Consolidated test results
11. **Deploy**: Production deployment (main branch only)

#### 2. Test Matrix (`.github/workflows/test-matrix.yml`)

**Purpose**: Comprehensive compatibility testing

**Matrix Combinations**:
- OS: Ubuntu, macOS
- Python: 3.11, 3.12
- Node.js: 18, 20
- Redis: 6, 7
- Platforms: linux/amd64, linux/arm64, darwin/amd64, darwin/arm64

### Pre-commit Hooks

**Purpose**: Catch issues before they reach CI

**Checks**:
- Code formatting (Black, Prettier)
- Linting (Flake8, ESLint)
- Type checking (mypy, TypeScript)
- Security scanning
- Quick unit tests
- Commit message validation

**Installation**:
```bash
pip install pre-commit
pre-commit install
```

## Local Development

### Running All Tests

Use the comprehensive test orchestration script:

```bash
# Run all tests
./scripts/run-all-tests.sh

# Run specific test types
./scripts/run-all-tests.sh --unit-only
./scripts/run-all-tests.sh --integration-only
./scripts/run-all-tests.sh --e2e-only

# Run with options
./scripts/run-all-tests.sh --parallel --verbose
./scripts/run-all-tests.sh --all  # Include security and performance
```

### Test Coverage

**Backend Coverage**:
```bash
cd dify-plugin-repackaging-web/backend
pytest tests/unit --cov=app --cov-report=html
# View coverage at htmlcov/index.html
```

**Frontend Coverage**:
```bash
cd dify-plugin-repackaging-web/frontend
npm run test:unit -- --coverage
# View coverage at coverage/lcov-report/index.html
```

### Continuous Testing

**Watch Mode**:
```bash
# Backend
cd dify-plugin-repackaging-web/backend
./run_unit_tests.sh watch

# Frontend
cd dify-plugin-repackaging-web/frontend
npm run test:unit -- --watch
```

## Test Configuration

### Environment Variables

**Testing Environment**:
```bash
# Backend
TESTING=true
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Frontend
PLAYWRIGHT_BASE_URL=http://localhost:3000
CI=true
```

### Test Data

**Fixtures**:
- Backend: `dify-plugin-repackaging-web/backend/tests/fixtures/`
- Frontend: `dify-plugin-repackaging-web/frontend/e2e/fixtures/`

**Mock Services**:
- Location: `testing/mock-services/`
- Purpose: Simulate external APIs for testing

### Docker Test Environment

**Starting Test Environment**:
```bash
docker-compose -f docker-compose.test.yml up -d
```

**Components**:
- Test Redis instance
- Backend API with test configuration
- Celery workers
- Mock external services

## Troubleshooting

### Common Issues

**1. Tests Failing Locally but Passing in CI**
- Check environment variables
- Ensure all services are running
- Clear test cache: `pytest --cache-clear`

**2. E2E Tests Timing Out**
- Increase timeout in playwright.config.ts
- Check if services are healthy
- Review browser console logs

**3. Integration Tests Can't Connect**
- Verify Docker is running
- Check port availability
- Review service health checks

**4. Coverage Not Generated**
- Install coverage dependencies
- Check pytest-cov is installed
- Verify coverage configuration

### Debugging Tests

**Backend Tests**:
```bash
# Run with debugging
pytest tests/unit/test_file.py -v --pdb

# Run specific test
pytest tests/unit/test_file.py::TestClass::test_method
```

**Frontend Tests**:
```bash
# Debug E2E tests
npx playwright test --debug

# Generate trace for failed tests
npx playwright test --trace on
```

### Performance Optimization

**Parallel Execution**:
```bash
# Backend
pytest -n auto

# Frontend E2E
npx playwright test --workers 4
```

**Test Selection**:
```bash
# Run only changed tests
pytest --testmon

# Run tests matching pattern
pytest -k "test_marketplace"
```

## Best Practices

1. **Write Tests First**: Follow TDD when possible
2. **Keep Tests Fast**: Mock external dependencies
3. **Use Descriptive Names**: Test names should explain what they test
4. **Avoid Test Interdependence**: Each test should be independent
5. **Clean Up After Tests**: Remove test data and restore state
6. **Review Test Failures**: Don't ignore flaky tests
7. **Maintain Test Data**: Keep fixtures up to date
8. **Document Complex Tests**: Add comments for non-obvious test logic

## Metrics and Reporting

### Coverage Goals
- Backend: 80% line coverage
- Frontend: 70% line coverage
- Critical paths: 100% coverage

### Test Execution Time
- Unit tests: < 1 minute
- Integration tests: < 5 minutes
- E2E tests: < 10 minutes per browser
- Total CI pipeline: < 30 minutes

### Monitoring
- Test results published to GitHub
- Coverage reports uploaded to Codecov
- Performance metrics tracked over time
- Security scan results reviewed weekly

## Future Improvements

1. **Mutation Testing**: Ensure test quality
2. **Contract Testing**: API compatibility testing
3. **Chaos Engineering**: Resilience testing
4. **Visual Regression**: Automated UI comparison
5. **A/B Testing Framework**: Feature flag testing
6. **Load Testing Automation**: Regular performance benchmarks

---

For questions or improvements to the testing strategy, please open an issue or contact the development team.