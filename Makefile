# Makefile for Dify Plugin Repackaging Project

.PHONY: help install test test-unit test-integration test-e2e test-all \
        test-security test-performance lint format coverage clean \
        docker-build docker-test pre-commit ci-local

# Default target
.DEFAULT_GOAL := help

# Variables
BACKEND_DIR := dify-plugin-repackaging-web/backend
FRONTEND_DIR := dify-plugin-repackaging-web/frontend
PYTHON := python3
NPM := npm
DOCKER_COMPOSE := docker-compose
TEST_COMPOSE := docker-compose -f docker-compose.test.yml

# Help target
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*##"; printf "\033[36m\033[0m"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## Install all dependencies
	@echo "Installing backend dependencies..."
	cd $(BACKEND_DIR) && pip install -r requirements.txt -r requirements-test.txt
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && $(NPM) ci
	@echo "Installing pre-commit hooks..."
	pre-commit install

lint: ## Run all linters
	@echo "Linting backend..."
	cd $(BACKEND_DIR) && flake8 app/ && mypy app/ && bandit -r app/
	@echo "Linting frontend..."
	cd $(FRONTEND_DIR) && $(NPM) run lint
	@echo "Linting shell scripts..."
	shellcheck *.sh scripts/*.sh

format: ## Format all code
	@echo "Formatting Python code..."
	cd $(BACKEND_DIR) && black app/ tests/ && isort app/ tests/
	@echo "Formatting frontend code..."
	cd $(FRONTEND_DIR) && $(NPM) run format
	@echo "Formatting complete!"

##@ Testing

test: test-unit ## Run unit tests (default)

test-unit: ## Run unit tests only
	@echo "Running backend unit tests..."
	cd $(BACKEND_DIR) && pytest tests/unit -v
	@echo "Running frontend unit tests..."
	cd $(FRONTEND_DIR) && $(NPM) run test:unit

test-integration: ## Run integration tests
	@echo "Running integration tests..."
	./run_integration_tests.sh

test-e2e: ## Run E2E tests
	@echo "Running E2E tests..."
	cd $(FRONTEND_DIR) && npx playwright test

test-all: ## Run all tests
	@echo "Running all tests..."
	./scripts/run-all-tests.sh

test-security: ## Run security tests
	@echo "Running security tests..."
	cd $(BACKEND_DIR) && safety check && bandit -r app/
	cd $(FRONTEND_DIR) && $(NPM) audit

test-performance: ## Run performance tests
	@echo "Running performance tests..."
	cd testing/performance-tests && locust -f locustfile.py --host http://localhost:8000 --users 10 --spawn-rate 2 --run-time 1m --headless

test-watch: ## Run tests in watch mode
	@echo "Running tests in watch mode..."
	cd $(BACKEND_DIR) && ./run_unit_tests.sh watch

coverage: ## Generate coverage reports
	@echo "Generating backend coverage..."
	cd $(BACKEND_DIR) && pytest tests/unit --cov=app --cov-report=html --cov-report=term
	@echo "Generating frontend coverage..."
	cd $(FRONTEND_DIR) && $(NPM) run test:unit -- --coverage
	@echo "Coverage reports generated!"

##@ Docker

docker-build: ## Build all Docker images
	@echo "Building Docker images..."
	docker build -t dify-plugin-repackaging .
	docker build -t dify-plugin-repackaging-backend $(BACKEND_DIR)
	docker build -t dify-plugin-repackaging-frontend $(FRONTEND_DIR)

docker-test: ## Run tests in Docker
	@echo "Running tests in Docker..."
	$(TEST_COMPOSE) up -d
	$(TEST_COMPOSE) run --rm test-runner
	$(TEST_COMPOSE) down -v

docker-up: ## Start services with Docker Compose
	@echo "Starting services..."
	$(DOCKER_COMPOSE) up -d
	./scripts/wait-for-services.sh

docker-down: ## Stop services
	@echo "Stopping services..."
	$(DOCKER_COMPOSE) down -v

docker-logs: ## Show service logs
	$(DOCKER_COMPOSE) logs -f

##@ CI/CD

pre-commit: ## Run pre-commit hooks on all files
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files

ci-local: ## Run CI pipeline locally
	@echo "Running CI pipeline locally..."
	act -j code-quality
	act -j backend-unit-tests
	act -j frontend-unit-tests
	act -j integration-tests

##@ Utilities

clean: ## Clean up generated files
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	rm -rf test-results/
	rm -rf temp-test/
	@echo "Cleanup complete!"

update-deps: ## Update all dependencies
	@echo "Updating backend dependencies..."
	cd $(BACKEND_DIR) && pip install --upgrade -r requirements.txt -r requirements-test.txt
	@echo "Updating frontend dependencies..."
	cd $(FRONTEND_DIR) && $(NPM) update
	@echo "Dependencies updated!"

check-deps: ## Check for outdated dependencies
	@echo "Checking backend dependencies..."
	cd $(BACKEND_DIR) && pip list --outdated
	@echo "Checking frontend dependencies..."
	cd $(FRONTEND_DIR) && $(NPM) outdated

##@ Quick Commands

quick-test: ## Run quick tests (unit tests for changed files only)
	@echo "Running quick tests..."
	cd $(BACKEND_DIR) && pytest tests/unit -x --testmon
	cd $(FRONTEND_DIR) && $(NPM) run test:unit -- --onlyChanged

fix: format lint ## Fix code issues (format + lint)

verify: lint test-unit ## Verify code quality (lint + unit tests)

full-check: install lint test-all ## Full check (install + lint + all tests)