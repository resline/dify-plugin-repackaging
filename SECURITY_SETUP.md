# Security Setup Guide - Secrets Management

This guide explains the security improvements implemented for the Dify Plugin Repackaging project and how to properly configure secrets for production deployment.

## Overview of Changes

All hardcoded credentials and sensitive configuration have been removed and replaced with environment variable-based configuration. The project now supports:

1. **Redis password authentication** for production security
2. **Secret key management** for cryptographic operations
3. **Environment-specific configuration** through `.env` files
4. **Proper `.gitignore` rules** to prevent secret leaks

## Quick Start

### 1. Create Your Environment File

Copy the example file and configure your secrets:

```bash
# In project root
cp .env.example .env

# Edit the file with your actual values
nano .env
```

### 2. Generate Strong Secrets

Generate a strong Redis password:
```bash
openssl rand -base64 32
```

Generate a secret key for the application:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Configure Essential Variables

At minimum, configure these variables in your `.env` file:

```bash
# Production domain
BACKEND_CORS_ORIGINS=https://your-production-domain.com

# Generate using: openssl rand -base64 32
REDIS_PASSWORD=your-strong-redis-password-here

# Generate using: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your-secret-key-here

# Redis URLs with password
REDIS_URL=redis://:your-strong-redis-password-here@redis:6379/0
CELERY_BROKER_URL=redis://:your-strong-redis-password-here@redis:6379/0
CELERY_RESULT_BACKEND=redis://:your-strong-redis-password-here@redis:6379/0

# Set to false in production
DEBUG=false
```

## Deployment Options

### Option 1: Coolify All-in-One Deployment

For Coolify deployments using the all-in-one container:

1. **Navigate to your Coolify project**

2. **Configure environment variables in Coolify UI:**
   - `BACKEND_CORS_ORIGINS` - Your domain(s)
   - `REDIS_PASSWORD` - Strong password for Redis
   - `SECRET_KEY` - Application secret key
   - `DEBUG` - Set to `false`
   - Other optional variables as needed

3. **Deploy:**
   ```bash
   # Coolify will use: dify-plugin-repackaging-web/docker-compose.coolify-aio.yml
   ```

4. **The all-in-one container automatically:**
   - Configures Redis with password at startup
   - Updates all service configurations to use the password
   - Starts all services (Redis, Backend, Celery workers, Nginx)

### Option 2: Production Multi-Container Deployment

For production deployments with separate containers:

1. **Create `.env` file in `dify-plugin-repackaging-web/` directory:**
   ```bash
   cd dify-plugin-repackaging-web
   cp .env.example .env
   nano .env
   ```

2. **Configure all required variables** (see `.env.example` for full list)

3. **Deploy:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Option 3: Development Setup

For local development:

1. **Create `.env` file:**
   ```bash
   cd dify-plugin-repackaging-web
   cp .env.example .env
   ```

2. **For development, you can leave REDIS_PASSWORD empty:**
   ```bash
   REDIS_PASSWORD=
   DEBUG=true
   BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost
   ```

3. **Start development environment:**
   ```bash
   docker-compose up -d
   ```

## Environment Variables Reference

### Required Variables (Production)

| Variable | Description | Example |
|----------|-------------|---------|
| `BACKEND_CORS_ORIGINS` | Allowed CORS origins (comma-separated or JSON array) | `https://example.com` or `["https://example.com","https://api.example.com"]` |
| `REDIS_PASSWORD` | Password for Redis authentication | Generated via `openssl rand -base64 32` |
| `SECRET_KEY` | Application secret key for cryptographic operations | Generated via Python secrets module |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Celery result backend URL | `redis://localhost:6379/0` |
| `DEBUG` | Enable debug mode | `false` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit per IP | `30` |
| `FILE_RETENTION_HOURS` | Temp file retention in hours | `24` |
| `MAX_FILE_SIZE` | Max upload size in bytes | `524288000` (500MB) |
| `GITHUB_API_URL` | GitHub API base URL | `https://github.com` |
| `MARKETPLACE_API_URL` | Dify Marketplace API URL | `https://marketplace.dify.ai` |

## Security Best Practices

### 1. Never Commit Secrets

The `.gitignore` file is configured to exclude all `.env` files:

```gitignore
# Environment variables and secrets
.env
.env.local
.env.*.local
.env.production
.env.development
.env.staging
*.secret
*.key
```

**Always verify before committing:**
```bash
git status
# Ensure .env files are not listed
```

### 2. Use Strong Passwords

- **Redis Password**: At least 32 characters, use `openssl rand -base64 32`
- **Secret Key**: At least 32 characters, use Python's `secrets` module

### 3. Rotate Secrets Regularly

In production:
1. Generate new secrets
2. Update environment variables
3. Restart services
4. Invalidate old sessions if using SECRET_KEY for authentication

### 4. Separate Secrets per Environment

Use different `.env` files for different environments:

- `.env.development` - Local development
- `.env.staging` - Staging environment
- `.env.production` - Production environment

**Never copy production secrets to development!**

### 5. Restrict Access

- Use Coolify's environment variable management for production
- Limit who can access production environment variables
- Use secrets management tools (HashiCorp Vault, AWS Secrets Manager, etc.) for enterprise deployments

## How It Works

### Code-Level Implementation

The application uses helper methods in `config.py` to construct Redis URLs with passwords:

```python
# In app/core/config.py
class Settings(BaseSettings):
    REDIS_PASSWORD: Optional[str] = None

    def get_redis_url(self) -> str:
        """Get Redis URL with password if configured."""
        if self.REDIS_PASSWORD:
            # Inject password into URL
            protocol, rest = self.REDIS_URL.split("://", 1)
            if "@" in rest:
                rest = rest.split("@", 1)[1]
            return f"{protocol}://:{self.REDIS_PASSWORD}@{rest}"
        return self.REDIS_URL
```

All Redis connections use these helper methods:
- `settings.get_redis_url()` - For direct Redis connections
- `settings.get_celery_broker_url()` - For Celery broker
- `settings.get_celery_result_backend()` - For Celery results

### Container-Level Implementation

#### All-in-One Container (Coolify)

The `start.sh` script dynamically configures Redis at container startup:

1. Reads `REDIS_PASSWORD` environment variable
2. Updates Redis configuration file with password
3. Updates supervisord configuration for all services
4. Starts all services with proper authentication

#### Multi-Container Deployment

Each service container:
1. Receives environment variables from `.env` file
2. Redis container starts with optional `--requirepass` flag
3. Backend/Worker containers use password-enabled URLs
4. Health checks use password authentication when configured

## Troubleshooting

### Redis Connection Errors

**Error:** `NOAUTH Authentication required`

**Solution:** Ensure all services have the same `REDIS_PASSWORD`:
```bash
# Check environment variables
docker-compose exec backend env | grep REDIS
docker-compose exec worker env | grep REDIS
```

### Celery Workers Not Connecting

**Error:** `Cannot connect to redis://redis:6379/0`

**Solution:** Update Celery URLs to include password:
```bash
CELERY_BROKER_URL=redis://:your-password@redis:6379/0
CELERY_RESULT_BACKEND=redis://:your-password@redis:6379/0
```

### CORS Errors

**Error:** `Access-Control-Allow-Origin` errors in browser

**Solution:** Update `BACKEND_CORS_ORIGINS` to include your domain:
```bash
# Single domain
BACKEND_CORS_ORIGINS=https://your-domain.com

# Multiple domains
BACKEND_CORS_ORIGINS=https://domain1.com,https://domain2.com

# Or JSON format
BACKEND_CORS_ORIGINS=["https://domain1.com","https://domain2.com"]
```

## Migration Guide

If you're upgrading from a version without proper secrets management:

### 1. Create Environment File
```bash
cp .env.example .env
```

### 2. Generate Secrets
```bash
# Generate Redis password
echo "REDIS_PASSWORD=$(openssl rand -base64 32)" >> .env

# Generate secret key
echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env
```

### 3. Update Redis URLs
```bash
# In .env file, update with your generated REDIS_PASSWORD
REDIS_PASSWORD=your-generated-password
REDIS_URL=redis://:your-generated-password@redis:6379/0
CELERY_BROKER_URL=redis://:your-generated-password@redis:6379/0
CELERY_RESULT_BACKEND=redis://:your-generated-password@redis:6379/0
```

### 4. Update CORS Origins
```bash
# Replace hardcoded domain with your production domain
BACKEND_CORS_ORIGINS=https://your-actual-domain.com
```

### 5. Redeploy
```bash
# For all-in-one
docker-compose -f docker-compose.coolify-aio.yml up -d --build

# For multi-container
docker-compose -f docker-compose.prod.yml up -d --build
```

## Additional Resources

- [.env.example](/root/repo/.env.example) - Full environment variable template
- [Coolify Documentation](https://coolify.io/docs) - Coolify deployment guide
- [Redis Security](https://redis.io/topics/security) - Redis security best practices
- [Celery Security](https://docs.celeryproject.org/en/stable/userguide/security.html) - Celery security guide

## Support

If you encounter issues:

1. Check logs: `docker-compose logs -f backend worker celery-beat`
2. Verify environment variables: `docker-compose exec backend env`
3. Test Redis connection: `docker-compose exec redis redis-cli -a your-password ping`
4. Review this guide for common solutions

For additional help, please open an issue on GitHub.
