# CI/CD Quick Start Guide

## Overview

This guide provides quick commands and workflows for developers working with the Dify Plugin Repackaging CI/CD pipeline.

## Quick Commands

### Local Development

```bash
# Install everything and set up hooks
make install
./scripts/setup-git-hooks.sh

# Run quick tests before committing
make quick-test

# Run full test suite
make test-all

# Fix code issues
make fix

# Full verification
make full-check
```

### Test Commands

```bash
# Unit tests only
make test-unit

# Integration tests
make test-integration

# E2E tests
make test-e2e

# Security scan
make test-security

# Performance tests
make test-performance

# Run all tests with coverage
./scripts/run-all-tests.sh --all
```

### Docker Commands

```bash
# Build images
make docker-build

# Run tests in Docker
make docker-test

# Start services
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

## CI/CD Pipeline Triggers

### Automatic Triggers

1. **Push to main/develop**: Full CI/CD pipeline
2. **Pull Request**: All tests except deployment
3. **Daily Schedule**: Full test suite at 2 AM UTC
4. **Weekly Schedule**: Compatibility matrix tests

### Manual Triggers

```bash
# Trigger workflow manually via GitHub CLI
gh workflow run ci-cd.yml

# Skip tests for hotfix
gh workflow run ci-cd.yml -f skip_tests=true
```

## Pre-commit Hooks

### Setup

```bash
pip install pre-commit
pre-commit install
```

### Running Manually

```bash
# Run on all files
pre-commit run --all-files

# Run on staged files
pre-commit run

# Skip hooks temporarily
git commit --no-verify
```

## Test Results

### Local Reports

- **Backend Coverage**: `dify-plugin-repackaging-web/backend/htmlcov/index.html`
- **Frontend Coverage**: `dify-plugin-repackaging-web/frontend/coverage/lcov-report/index.html`
- **Integration Tests**: `test-results/report.html`
- **E2E Tests**: `dify-plugin-repackaging-web/frontend/playwright-report/index.html`

### CI Reports

- View in GitHub Actions run summary
- Coverage uploaded to Codecov
- Test results as PR comments

## Troubleshooting

### Common Issues

**Tests failing locally?**
```bash
# Clear caches
make clean
pytest --cache-clear

# Rebuild containers
docker-compose -f docker-compose.test.yml build --no-cache
```

**Pre-commit failing?**
```bash
# Update hooks
pre-commit autoupdate

# Run specific hook
pre-commit run black --all-files
```

**CI pipeline slow?**
- Check for unnecessary test retries
- Review Docker layer caching
- Consider parallelizing more tests

## Best Practices

1. **Before Pushing**
   ```bash
   make verify  # Runs lint + unit tests
   ```

2. **After Major Changes**
   ```bash
   make full-check  # Complete verification
   ```

3. **Debugging Failed CI**
   - Check GitHub Actions logs
   - Download artifacts for detailed reports
   - Run same commands locally

4. **Speed Up Development**
   - Use `make quick-test` for rapid feedback
   - Run only affected tests during development
   - Use test watchers for TDD

## Environment Variables

### Required for Tests
```bash
export TESTING=true
export REDIS_URL=redis://localhost:6379/0
export PLAYWRIGHT_BASE_URL=http://localhost:3000
```

### Optional
```bash
export CI=true  # Simulates CI environment
export SKIP_SLOW_TESTS=true  # Skip slow tests
export TEST_PARALLEL=true  # Enable parallel execution
```

## Getting Help

- Run `make help` for all available commands
- Check `docs/TESTING_STRATEGY.md` for detailed information
- Review `.github/workflows/` for CI configuration
- Open an issue for CI/CD problems

---

Remember: The CI/CD pipeline is here to help maintain code quality. If you're consistently fighting it, let's improve it together!