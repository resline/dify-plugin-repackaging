#!/bin/bash

# Start Redis in background
redis-server --daemonize yes

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! redis-cli ping > /dev/null 2>&1; do
    sleep 1
done
echo "Redis is ready"

# Start supervisord
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf