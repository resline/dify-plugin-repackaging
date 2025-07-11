#!/bin/bash
# Comprehensive test orchestration script

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/dify-plugin-repackaging-web/backend"
FRONTEND_DIR="$PROJECT_ROOT/dify-plugin-repackaging-web/frontend"
TEST_RESULTS_DIR="$PROJECT_ROOT/test-results"
COVERAGE_DIR="$PROJECT_ROOT/coverage"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test tracking
TESTS_PASSED=0
TESTS_FAILED=0
TEST_SUITES=()

# Parse command line arguments
RUN_UNIT=true
RUN_INTEGRATION=true
RUN_E2E=true
RUN_SECURITY=false
RUN_PERFORMANCE=false
PARALLEL=false
VERBOSE=false
COVERAGE=true
FAIL_FAST=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit-only)
            RUN_INTEGRATION=false
            RUN_E2E=false
            shift
            ;;
        --integration-only)
            RUN_UNIT=false
            RUN_E2E=false
            shift
            ;;
        --e2e-only)
            RUN_UNIT=false
            RUN_INTEGRATION=false
            shift
            ;;
        --all)
            RUN_SECURITY=true
            RUN_PERFORMANCE=true
            shift
            ;;
        --parallel|-p)
            PARALLEL=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --fail-fast)
            FAIL_FAST=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --unit-only         Run only unit tests"
            echo "  --integration-only  Run only integration tests"
            echo "  --e2e-only         Run only E2E tests"
            echo "  --all              Run all tests including security and performance"
            echo "  --parallel, -p     Run tests in parallel where possible"
            echo "  --verbose, -v      Verbose output"
            echo "  --no-coverage      Skip coverage collection"
            echo "  --fail-fast        Stop on first test failure"
            echo "  --help, -h         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Functions
log_section() {
    echo ""
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_failure() {
    echo -e "${RED}❌ $1${NC}"
}

run_test_suite() {
    local suite_name=$1
    local command=$2
    local working_dir=${3:-$PROJECT_ROOT}
    
    log_info "Running $suite_name..."
    TEST_SUITES+=("$suite_name")
    
    cd "$working_dir"
    
    if eval "$command"; then
        log_success "$suite_name passed!"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_failure "$suite_name failed!"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        if [ "$FAIL_FAST" = true ]; then
            log_error "Fail-fast mode enabled. Stopping tests."
            exit 1
        fi
        return 1
    fi
}

# Create directories
mkdir -p "$TEST_RESULTS_DIR"
mkdir -p "$COVERAGE_DIR"
mkdir -p "$COVERAGE_DIR/backend"
mkdir -p "$COVERAGE_DIR/frontend"
mkdir -p "$COVERAGE_DIR/combined"

# Start time tracking
START_TIME=$(date +%s)

log_section "🚀 Starting Comprehensive Test Suite"
echo "Configuration:"
echo "  - Unit Tests: $RUN_UNIT"
echo "  - Integration Tests: $RUN_INTEGRATION"
echo "  - E2E Tests: $RUN_E2E"
echo "  - Security Tests: $RUN_SECURITY"
echo "  - Performance Tests: $RUN_PERFORMANCE"
echo "  - Parallel Mode: $PARALLEL"
echo "  - Coverage: $COVERAGE"
echo "  - Fail Fast: $FAIL_FAST"

# Backend Unit Tests
if [ "$RUN_UNIT" = true ]; then
    log_section "🔬 Backend Unit Tests"
    
    PYTEST_OPTS="-v"
    if [ "$COVERAGE" = true ]; then
        PYTEST_OPTS="$PYTEST_OPTS --cov=app --cov-report=xml:$COVERAGE_DIR/backend/coverage.xml --cov-report=html:$COVERAGE_DIR/backend/html"
    fi
    if [ "$PARALLEL" = true ]; then
        PYTEST_OPTS="$PYTEST_OPTS -n auto"
    fi
    if [ "$VERBOSE" = true ]; then
        PYTEST_OPTS="$PYTEST_OPTS -vv"
    fi
    
    run_test_suite "Backend Unit Tests" \
        "pytest tests/unit $PYTEST_OPTS --junitxml=$TEST_RESULTS_DIR/backend-unit.xml" \
        "$BACKEND_DIR"
fi

# Frontend Unit Tests
if [ "$RUN_UNIT" = true ]; then
    log_section "🎨 Frontend Unit Tests"
    
    # First run linting
    run_test_suite "Frontend Linting" \
        "npm run lint" \
        "$FRONTEND_DIR"
    
    # Type checking
    run_test_suite "Frontend Type Checking" \
        "npm run type-check" \
        "$FRONTEND_DIR"
    
    # Unit tests
    JEST_OPTS=""
    if [ "$COVERAGE" = true ]; then
        JEST_OPTS="--coverage --coverageDirectory=$COVERAGE_DIR/frontend"
    fi
    
    run_test_suite "Frontend Unit Tests" \
        "npm run test:unit -- $JEST_OPTS --reporters=default --reporters=jest-junit --outputFile=$TEST_RESULTS_DIR/frontend-unit.xml" \
        "$FRONTEND_DIR"
fi

# Integration Tests
if [ "$RUN_INTEGRATION" = true ]; then
    log_section "🔗 Integration Tests"
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    INTEGRATION_OPTS=""
    if [ "$COVERAGE" = true ]; then
        INTEGRATION_OPTS="--coverage"
    fi
    if [ "$VERBOSE" = true ]; then
        INTEGRATION_OPTS="$INTEGRATION_OPTS --verbose"
    fi
    
    run_test_suite "Integration Tests" \
        "./run_integration_tests.sh $INTEGRATION_OPTS" \
        "$PROJECT_ROOT"
fi

# E2E Tests
if [ "$RUN_E2E" = true ]; then
    log_section "🌐 End-to-End Tests"
    
    # Start services if not running
    if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_info "Starting services for E2E tests..."
        cd "$PROJECT_ROOT"
        docker-compose up -d
        ./scripts/wait-for-services.sh
    fi
    
    # Run E2E tests for each browser
    if [ "$PARALLEL" = true ]; then
        # Run browsers in parallel
        (
            run_test_suite "E2E Tests - Chromium" \
                "npx playwright test --project=chromium --reporter=json,html" \
                "$FRONTEND_DIR"
        ) &
        
        (
            run_test_suite "E2E Tests - Firefox" \
                "npx playwright test --project=firefox --reporter=json,html" \
                "$FRONTEND_DIR"
        ) &
        
        (
            run_test_suite "E2E Tests - WebKit" \
                "npx playwright test --project=webkit --reporter=json,html" \
                "$FRONTEND_DIR"
        ) &
        
        wait
    else
        # Run browsers sequentially
        run_test_suite "E2E Tests - Chromium" \
            "npx playwright test --project=chromium --reporter=json,html" \
            "$FRONTEND_DIR"
        
        run_test_suite "E2E Tests - Firefox" \
            "npx playwright test --project=firefox --reporter=json,html" \
            "$FRONTEND_DIR"
        
        run_test_suite "E2E Tests - WebKit" \
            "npx playwright test --project=webkit --reporter=json,html" \
            "$FRONTEND_DIR"
    fi
fi

# Security Tests
if [ "$RUN_SECURITY" = true ]; then
    log_section "🔒 Security Tests"
    
    # Python security checks
    run_test_suite "Python Security - Safety Check" \
        "safety check --json > $TEST_RESULTS_DIR/safety-report.json || true" \
        "$BACKEND_DIR"
    
    run_test_suite "Python Security - Bandit" \
        "bandit -r app/ -f json -o $TEST_RESULTS_DIR/bandit-report.json" \
        "$BACKEND_DIR"
    
    # JavaScript security checks
    run_test_suite "JavaScript Security - npm audit" \
        "npm audit --json > $TEST_RESULTS_DIR/npm-audit.json || true" \
        "$FRONTEND_DIR"
fi

# Performance Tests
if [ "$RUN_PERFORMANCE" = true ]; then
    log_section "⚡ Performance Tests"
    
    # Ensure services are running
    if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_info "Starting services for performance tests..."
        cd "$PROJECT_ROOT"
        docker-compose up -d
        ./scripts/wait-for-services.sh
    fi
    
    run_test_suite "Performance Tests - Locust" \
        "locust -f locustfile.py --host http://localhost:8000 --users 10 --spawn-rate 2 --run-time 1m --headless --html $TEST_RESULTS_DIR/performance-report.html" \
        "$PROJECT_ROOT/testing/performance-tests"
fi

# Calculate test duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

# Generate coverage report
if [ "$COVERAGE" = true ] && [ "$TESTS_PASSED" -gt 0 ]; then
    log_section "📊 Generating Combined Coverage Report"
    
    # Combine coverage data if both backend and frontend tests ran
    if [ -f "$COVERAGE_DIR/backend/coverage.xml" ] && [ -f "$COVERAGE_DIR/frontend/lcov.info" ]; then
        log_info "Combining coverage reports..."
        # Add coverage combination logic here
    fi
fi

# Summary
log_section "📈 Test Results Summary"
echo ""
echo -e "${CYAN}Test Suites Run:${NC} ${#TEST_SUITES[@]}"
echo -e "${GREEN}Tests Passed:${NC} $TESTS_PASSED"
echo -e "${RED}Tests Failed:${NC} $TESTS_FAILED"
echo -e "${BLUE}Duration:${NC} ${MINUTES}m ${SECONDS}s"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    log_success "All tests passed! 🎉"
    exit 0
else
    log_failure "Some tests failed. Please check the logs above."
    exit 1
fi