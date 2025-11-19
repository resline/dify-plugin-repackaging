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

# Configure Redis password if REDIS_PASSWORD is set
if [ -n "$REDIS_PASSWORD" ]; then
    echo "Configuring Redis with password authentication..."
    # Add requirepass to redis config if not already present
    if ! grep -q "^requirepass" /etc/redis/redis.conf; then
        echo "requirepass $REDIS_PASSWORD" >> /etc/redis/redis.conf
    else
        # Replace existing requirepass
        sed -i "s/^requirepass .*/requirepass $REDIS_PASSWORD/" /etc/redis/redis.conf
    fi
    echo "Redis password configured"
else
    echo "Redis will run without password authentication (development mode)"
    # Remove any requirepass directive
    sed -i '/^requirepass/d' /etc/redis/redis.conf
fi

# Update supervisord environment variables for backend, worker, and celery-beat
# to include REDIS_PASSWORD if set
if [ -n "$REDIS_PASSWORD" ]; then
    echo "Updating supervisord configuration with Redis password..."

    # Get the properly formatted Redis URLs with password
    REDIS_URL_WITH_PASS="redis://:${REDIS_PASSWORD}@localhost:6379/0"

    # Update backend environment
    sed -i "s|REDIS_URL=\"[^\"]*\"|REDIS_URL=\"${REDIS_URL_WITH_PASS}\"|g" /etc/supervisor/conf.d/supervisord.conf
    sed -i "s|CELERY_BROKER_URL=\"[^\"]*\"|CELERY_BROKER_URL=\"${REDIS_URL_WITH_PASS}\"|g" /etc/supervisor/conf.d/supervisord.conf
    sed -i "s|CELERY_RESULT_BACKEND=\"[^\"]*\"|CELERY_RESULT_BACKEND=\"${REDIS_URL_WITH_PASS}\"|g" /etc/supervisor/conf.d/supervisord.conf
fi

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

# Start supervisord (which will start Redis, backend, workers, nginx)
echo "Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
