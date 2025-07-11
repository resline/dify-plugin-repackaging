#!/bin/bash

# Exit on error
set -e

# Check if --local flag is passed
if [[ "$1" == "--local" ]]; then
    echo "🚀 Starting Dify Plugin Repackaging E2E Tests (Local Mode with Mock Backend)"
    echo "=========================================================================="
    
    # Change to frontend directory
    cd frontend || exit 1
    
    # Run the local E2E test script
    ./run-e2e-with-mock.sh "${@:2}"  # Pass remaining arguments
    exit $?
fi

echo "🚀 Starting Dify Plugin Repackaging E2E Tests (Docker Mode with Mock Backend)"
echo "============================================================================"

# Clean up any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose -f docker-compose-test.yml down -v 2>/dev/null || true

# Start services
echo "📦 Starting test services..."
docker-compose -f docker-compose-test.yml up -d backend-mock frontend-test

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "📊 Service Status:"
docker-compose -f docker-compose-test.yml ps

# Run E2E tests
echo ""
echo "🧪 Running E2E tests..."
docker-compose -f docker-compose-test.yml run --rm playwright-test

# Capture exit code
TEST_EXIT_CODE=$?

# Clean up
echo ""
echo "🧹 Cleaning up..."
docker-compose -f docker-compose-test.yml down -v

# Exit with test exit code
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ E2E tests passed!"
else
    echo ""
    echo "❌ E2E tests failed with exit code: $TEST_EXIT_CODE"
fi

exit $TEST_EXIT_CODE