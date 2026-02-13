#!/bin/bash

echo "Starting all-in-one container initialization..."

# Check directory structure
echo "Checking directory structure:"
ls -la /app/
if [ -d "/app/backend" ]; then
    echo "Backend directory exists at /app/backend"
    ls -la /app/backend/
else
    echo "ERROR: Backend directory not found at /app/backend"
    exit 1
fi

# SEC-003: Start Redis with password authentication
echo "Starting Redis server..."
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
if [ -n "$REDIS_PASSWORD" ]; then
    redis-server --daemonize yes --requirepass "$REDIS_PASSWORD"
else
    echo "WARNING: Redis starting without password authentication"
    redis-server --daemonize yes
fi

# Wait for Redis to be ready
echo "Waiting for Redis..."
counter=0
REDIS_AUTH_FLAG=""
if [ -n "$REDIS_PASSWORD" ]; then
    REDIS_AUTH_FLAG="-a $REDIS_PASSWORD"
fi
while ! redis-cli $REDIS_AUTH_FLAG ping > /dev/null 2>&1; do
    counter=$((counter+1))
    if [ $counter -gt 30 ]; then
        echo "ERROR: Redis failed to start after 30 seconds"
        exit 1
    fi
    echo "Waiting for Redis... ($counter/30)"
    sleep 1
done
echo "Redis is ready"

# Test Python environment
echo "Testing Python environment:"
python -c "import sys; print(f'Python path: {sys.path}')"
echo "PYTHONPATH=$PYTHONPATH"

# Test backend module
echo "Testing backend module import..."
cd /app/backend && python -c "import app; print('Backend module imported successfully')" || echo "ERROR: Failed to import backend module"

# Test required dependencies
echo "Testing required dependencies..."
python -c "import fastapi; print('FastAPI imported successfully')" || echo "ERROR: Failed to import FastAPI"
python -c "import redis; print('Redis-py imported successfully')" || echo "ERROR: Failed to import redis"
python -c "import celery; print('Celery imported successfully')" || echo "ERROR: Failed to import celery"

# Start supervisord
echo "Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf