#!/bin/bash
# Wait for all services to be ready

set -e

# Configuration
MAX_RETRIES=30
RETRY_INTERVAL=5

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

wait_for_service() {
    local service_name=$1
    local health_check_cmd=$2
    local retries=0

    log_info "Waiting for $service_name to be ready..."

    while [ $retries -lt $MAX_RETRIES ]; do
        if eval "$health_check_cmd" > /dev/null 2>&1; then
            log_info "$service_name is ready!"
            return 0
        fi

        retries=$((retries + 1))
        log_warning "$service_name not ready yet. Retry $retries/$MAX_RETRIES..."
        sleep $RETRY_INTERVAL
    done

    log_error "$service_name failed to become ready after $MAX_RETRIES retries"
    return 1
}

# Wait for Redis
wait_for_service "Redis" "docker-compose exec -T redis redis-cli ping | grep -q PONG"

# Wait for Backend API
wait_for_service "Backend API" "curl -f http://localhost:8000/health"

# Wait for Frontend
wait_for_service "Frontend" "curl -f http://localhost:3000"

# Wait for Celery Worker
wait_for_service "Celery Worker" "docker-compose exec -T worker celery -A app.workers.celery_app inspect ping"

log_info "All services are ready!"