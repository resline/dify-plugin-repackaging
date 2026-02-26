#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting Dify Plugin Repackaging E2E Tests"
echo "============================================"

# Clean up any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose down -v 2>/dev/null || true

# Build images
echo "🔨 Building Docker images..."
docker-compose build

# Start services
echo "📦 Starting services..."
docker-compose up -d redis backend celery_worker frontend

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose ps | grep -E "(unhealthy|starting)" > /dev/null; then
        echo -n "."
        sleep 2
        elapsed=$((elapsed + 2))
    else
        echo ""
        echo "✅ All services are healthy!"
        break
    fi
done

if [ $elapsed -ge $timeout ]; then
    echo ""
    echo "❌ Timeout waiting for services to be healthy"
    docker-compose logs
    docker-compose down -v
    exit 1
fi

# Show service status
echo ""
echo "📊 Service Status:"
docker-compose ps

# Run E2E tests
echo ""
echo "🧪 Running E2E tests..."
TEST_EXIT_CODE=0
docker-compose run --rm \
    -e PLAYWRIGHT_BASE_URL=http://frontend:80 \
    -e CI=true \
    playwright \
    sh -c "npm install && npx playwright test --reporter=list" || TEST_EXIT_CODE=$?

# Copy test results
if [ -d "playwright-results" ]; then
    echo ""
    echo "📋 Test results saved to ./playwright-results/"
fi

# Clean up
echo ""
echo "🧹 Cleaning up..."
docker-compose down -v

# Exit with test exit code
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ E2E tests passed!"
else
    echo ""
    echo "❌ E2E tests failed with exit code: $TEST_EXIT_CODE"
fi

exit $TEST_EXIT_CODE