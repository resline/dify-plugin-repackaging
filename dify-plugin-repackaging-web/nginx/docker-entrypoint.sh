#!/bin/sh
set -e

# Substitute environment variables in nginx config
envsubst '${BACKEND_HOST} ${BACKEND_PORT} ${FRONTEND_HOST} ${FRONTEND_PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Debug: Print the generated config
echo "Generated nginx config:"
cat /etc/nginx/nginx.conf

# Execute the original command
exec "$@"