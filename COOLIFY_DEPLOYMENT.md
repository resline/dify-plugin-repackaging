# Coolify Deployment Guide

## Environment Variables

When deploying on Coolify, make sure to set the following environment variables:

### Required Variables

```bash
# Backend CORS configuration
# Option 1: Simple comma-separated list (recommended)
BACKEND_CORS_ORIGINS=https://dify-plugin.resline.net

# Option 2: Multiple domains
BACKEND_CORS_ORIGINS=https://dify-plugin.resline.net,https://another-domain.com

# Option 3: JSON array (make sure it's properly formatted)
BACKEND_CORS_ORIGINS=["https://dify-plugin.resline.net"]
```

### Optional Variables

```bash
# Rate limiting (default: 10 requests per minute)
RATE_LIMIT_PER_MINUTE=10

# File retention (default: 24 hours)
FILE_RETENTION_HOURS=24

# Maximum file size in bytes (default: 500MB)
MAX_FILE_SIZE=524288000
```

## Common Issues

### Nginx Configuration Mount Error

If you see this error:
```
error mounting "/data/coolify/applications/.../nginx.conf" to rootfs at "/etc/nginx/nginx.conf"
```

**Solution**: The nginx service now builds from a Dockerfile instead of mounting the config file. Make sure:
- The `nginx/` directory exists with `Dockerfile` and `nginx.conf`
- Docker Compose uses `build: ./nginx` instead of mounting volumes

### BACKEND_CORS_ORIGINS Error

If you see this error:
```
pydantic_settings.sources.SettingsError: error parsing value for field "BACKEND_CORS_ORIGINS" from source "EnvSettingsSource"
```

**Solution**: Use the simple comma-separated format instead of JSON:
- ❌ Wrong: `BACKEND_CORS_ORIGINS=[""]` (empty JSON array)
- ✅ Correct: `BACKEND_CORS_ORIGINS=https://your-domain.com`
- ✅ Correct: `BACKEND_CORS_ORIGINS=https://domain1.com,https://domain2.com`

### Services Not Connecting

If backend shows "Host is unreachable":
1. Ensure all services are in the same Docker network
2. Check that service names match in docker-compose
3. Verify Redis is running and accessible

## Docker Compose Configuration

The application uses the following services:
- `backend` - FastAPI application (port 8000)
- `worker` - Celery worker for async tasks
- `celery-beat` - Scheduled task runner
- `frontend` - React application
- `redis` - Message broker and cache
- `nginx` - Reverse proxy (port 80)

All services should be on the same network for inter-service communication.