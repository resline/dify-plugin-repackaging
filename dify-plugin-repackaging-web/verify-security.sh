#!/bin/bash

# Security Verification Script
# This script verifies all security enhancements are working correctly

set -e

CONTAINER_NAME=${1:-"dify-plugin-repackaging-aio"}
HOST=${2:-"localhost"}
PORT=${3:-"80"}

echo "=================================================="
echo "Security Verification Script"
echo "=================================================="
echo "Container: $CONTAINER_NAME"
echo "Host: $HOST:$PORT"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print success
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to print warning
warning() {
    echo -e "${YELLOW}! $1${NC}"
}

# Function to print section header
section() {
    echo ""
    echo "=================================================="
    echo "$1"
    echo "=================================================="
}

# 1. Verify non-root user execution
section "1. Verifying Non-Root User Execution"

if command -v docker &> /dev/null; then
    echo "Checking processes in container..."

    # Check backend process
    BACKEND_USER=$(docker exec $CONTAINER_NAME ps aux | grep "uvicorn app.main:app" | grep -v grep | awk '{print $1}' | head -1)
    if [ "$BACKEND_USER" = "appuser" ]; then
        success "Backend running as appuser"
    else
        error "Backend NOT running as appuser (running as: $BACKEND_USER)"
    fi

    # Check worker process
    WORKER_USER=$(docker exec $CONTAINER_NAME ps aux | grep "celery.*worker" | grep -v grep | awk '{print $1}' | head -1)
    if [ "$WORKER_USER" = "appuser" ]; then
        success "Celery worker running as appuser"
    else
        error "Celery worker NOT running as appuser (running as: $WORKER_USER)"
    fi

    # Check redis process
    REDIS_USER=$(docker exec $CONTAINER_NAME ps aux | grep "redis-server" | grep -v grep | awk '{print $1}' | head -1)
    if [ "$REDIS_USER" = "appuser" ]; then
        success "Redis running as appuser"
    else
        error "Redis NOT running as appuser (running as: $REDIS_USER)"
    fi

    # Check supervisord (should be root)
    SUPERVISORD_USER=$(docker exec $CONTAINER_NAME ps aux | grep supervisord | grep -v grep | awk '{print $1}' | head -1)
    if [ "$SUPERVISORD_USER" = "root" ]; then
        success "Supervisord running as root (expected)"
    else
        warning "Supervisord NOT running as root (running as: $SUPERVISORD_USER)"
    fi
else
    warning "Docker not available, skipping container process checks"
fi

# 2. Verify security headers
section "2. Verifying Security Headers"

echo "Testing security headers..."
HEADERS=$(curl -s -I http://$HOST:$PORT/)

check_header() {
    local header=$1
    local expected=$2
    if echo "$HEADERS" | grep -qi "$header: $expected"; then
        success "$header: $expected"
        return 0
    else
        error "$header: $expected NOT FOUND"
        return 1
    fi
}

check_header "X-Frame-Options" "SAMEORIGIN"
check_header "X-Content-Type-Options" "nosniff"
check_header "X-XSS-Protection" "1; mode=block"
check_header "Strict-Transport-Security" "max-age=31536000"
check_header "Referrer-Policy" "strict-origin-when-cross-origin"
check_header "Permissions-Policy" "geolocation=()"

# 3. Verify rate limiting
section "3. Verifying Rate Limiting"

echo "Testing API rate limiting (sending 35 requests)..."
SUCCESS_COUNT=0
RATE_LIMITED_COUNT=0

for i in {1..35}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$HOST:$PORT/api/health)
    if [ "$HTTP_CODE" = "200" ]; then
        ((SUCCESS_COUNT++))
    elif [ "$HTTP_CODE" = "429" ]; then
        ((RATE_LIMITED_COUNT++))
    fi
    sleep 0.05
done

echo "Results:"
echo "  - Successful requests: $SUCCESS_COUNT"
echo "  - Rate limited (429): $RATE_LIMITED_COUNT"

if [ $RATE_LIMITED_COUNT -gt 0 ]; then
    success "Rate limiting is working (got $RATE_LIMITED_COUNT rate-limited responses)"
else
    error "Rate limiting NOT working (no 429 responses)"
fi

# Wait for rate limit to reset
echo "Waiting 2 seconds for rate limit to reset..."
sleep 2

echo "Testing upload endpoint rate limiting (sending 10 requests)..."
UPLOAD_SUCCESS=0
UPLOAD_LIMITED=0

for i in {1..10}; do
    # Note: This will fail with 404 or 405 as we're not actually uploading, but we can check for 429
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$HOST:$PORT/api/upload)
    if [ "$HTTP_CODE" = "429" ]; then
        ((UPLOAD_LIMITED++))
    else
        ((UPLOAD_SUCCESS++))
    fi
    sleep 0.05
done

echo "Upload endpoint results:"
echo "  - Non rate-limited: $UPLOAD_SUCCESS"
echo "  - Rate limited (429): $UPLOAD_LIMITED"

if [ $UPLOAD_LIMITED -gt 0 ]; then
    success "Upload rate limiting is working"
else
    warning "Upload rate limiting unclear (endpoint may not exist or have different response)"
fi

# 4. Verify checksum file exists
section "4. Verifying Checksum Configuration"

if [ -f "../SHA256SUMS" ]; then
    success "SHA256SUMS file exists"
    echo ""
    echo "Checksums:"
    cat ../SHA256SUMS | grep -v "^#"
else
    error "SHA256SUMS file NOT found"
fi

# 5. Verify file permissions
section "5. Verifying File Permissions (if Docker available)"

if command -v docker &> /dev/null; then
    echo "Checking file ownership in container..."

    APP_OWNER=$(docker exec $CONTAINER_NAME stat -c '%U:%G' /app)
    if [ "$APP_OWNER" = "appuser:appuser" ]; then
        success "/app owned by appuser:appuser"
    else
        error "/app owned by $APP_OWNER (expected appuser:appuser)"
    fi

    LOG_OWNER=$(docker exec $CONTAINER_NAME stat -c '%U:%G' /var/log/backend.log 2>/dev/null || echo "root:root")
    if [ "$LOG_OWNER" = "appuser:appuser" ]; then
        success "/var/log/backend.log owned by appuser:appuser"
    else
        warning "/var/log/backend.log owned by $LOG_OWNER"
    fi

    REDIS_DIR_OWNER=$(docker exec $CONTAINER_NAME stat -c '%U:%G' /var/lib/redis)
    if [ "$REDIS_DIR_OWNER" = "appuser:appuser" ]; then
        success "/var/lib/redis owned by appuser:appuser"
    else
        error "/var/lib/redis owned by $REDIS_DIR_OWNER (expected appuser:appuser)"
    fi
else
    warning "Docker not available, skipping file permission checks"
fi

# 6. Test health endpoint (should not be rate limited)
section "6. Verifying Health Endpoint"

HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$HOST:$PORT/health)
if [ "$HEALTH_CODE" = "200" ]; then
    success "Health endpoint responding with 200"
else
    error "Health endpoint returned $HEALTH_CODE (expected 200)"
fi

# 7. Summary
section "Security Verification Summary"

echo ""
echo "Verification completed!"
echo ""
echo "Next steps:"
echo "1. Review any errors or warnings above"
echo "2. Check SECURITY.md for detailed configuration"
echo "3. For production, ensure HTTPS is configured"
echo "4. Consider enabling additional monitoring"
echo ""
echo "For more information, see:"
echo "  - /root/repo/dify-plugin-repackaging-web/SECURITY.md"
echo "  - https://owasp.org/www-project-secure-headers/"
echo ""
