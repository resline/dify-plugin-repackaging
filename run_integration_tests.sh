#!/bin/bash
# Integration test runner script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="dify-repack-test"
COMPOSE_FILE="docker-compose.test.yml"
TEST_RESULTS_DIR="./test-results"
COVERAGE_DIR="./coverage"

# Parse command line arguments
RUN_SPECIFIC=""
KEEP_RUNNING=false
VERBOSE=false
COVERAGE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--test)
            RUN_SPECIFIC="$2"
            shift 2
            ;;
        -k|--keep-running)
            KEEP_RUNNING=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -t, --test <test>     Run specific test file or pattern"
            echo "  -k, --keep-running    Keep services running after tests"
            echo "  -v, --verbose         Verbose output"
            echo "  -c, --coverage        Generate coverage report"
            echo "  -h, --help            Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

cleanup() {
    if [ "$KEEP_RUNNING" = false ]; then
        log_info "Cleaning up test environment..."
        docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down -v
    else
        log_info "Keeping test environment running (use 'docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down -v' to stop)"
    fi
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Create directories
mkdir -p $TEST_RESULTS_DIR
mkdir -p $COVERAGE_DIR

# Start test environment
log_info "Starting test environment..."
docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d

# Wait for services to be ready
log_info "Waiting for services to be ready..."
sleep 10

# Check service health
log_info "Checking service health..."
docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME ps

# Run tests
log_info "Running integration tests..."

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="pytest --cov=app --cov-report=html:${COVERAGE_DIR}/html --cov-report=term"
else
    PYTEST_CMD="pytest"
fi

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

PYTEST_CMD="$PYTEST_CMD --tb=short"
PYTEST_CMD="$PYTEST_CMD --junitxml=${TEST_RESULTS_DIR}/junit.xml"
PYTEST_CMD="$PYTEST_CMD --html=${TEST_RESULTS_DIR}/report.html"
PYTEST_CMD="$PYTEST_CMD --self-contained-html"

if [ -n "$RUN_SPECIFIC" ]; then
    PYTEST_CMD="$PYTEST_CMD $RUN_SPECIFIC"
else
    PYTEST_CMD="$PYTEST_CMD dify-plugin-repackaging-web/backend/tests/integration"
fi

# Execute tests in test runner container
log_info "Executing: $PYTEST_CMD"
docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME run --rm test-runner $PYTEST_CMD

# Check test results
if [ $? -eq 0 ]; then
    log_info "All integration tests passed!"
    
    # Show coverage if enabled
    if [ "$COVERAGE" = true ]; then
        log_info "Coverage report generated in ${COVERAGE_DIR}/html/index.html"
    fi
else
    log_error "Integration tests failed!"
    
    # Show logs from failed services
    log_error "Showing logs from services..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs --tail=50
    
    exit 1
fi

# Generate test summary
log_info "Test Summary:"
if [ -f "${TEST_RESULTS_DIR}/junit.xml" ]; then
    python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('${TEST_RESULTS_DIR}/junit.xml')
root = tree.getroot()
testsuite = root.find('testsuite')
if testsuite is not None:
    print(f'Total tests: {testsuite.get(\"tests\", 0)}')
    print(f'Passed: {int(testsuite.get(\"tests\", 0)) - int(testsuite.get(\"failures\", 0)) - int(testsuite.get(\"errors\", 0))}')
    print(f'Failed: {testsuite.get(\"failures\", 0)}')
    print(f'Errors: {testsuite.get(\"errors\", 0)}')
    print(f'Time: {testsuite.get(\"time\", 0)}s')
"
fi

log_info "Test report available at: ${TEST_RESULTS_DIR}/report.html"