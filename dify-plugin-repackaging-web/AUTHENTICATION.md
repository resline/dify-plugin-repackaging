# Authentication Documentation

## Overview

The Dify Plugin Repackaging Web service supports simple password-based authentication to protect API endpoints. Authentication can be enabled or disabled via environment variables.

## Configuration

### Environment Variable

Set the `AUTH_PASSWORD` environment variable to enable authentication:

```bash
# Enable authentication with password
export AUTH_PASSWORD="your_secure_password_here"

# Disable authentication (development mode)
# Do not set AUTH_PASSWORD or set it to empty string
export AUTH_PASSWORD=""
```

### Docker Compose

```yaml
services:
  backend:
    environment:
      - AUTH_PASSWORD=your_secure_password_here
```

### Coolify Deployment

In Coolify, add the environment variable:

```
AUTH_PASSWORD=your_secure_password_here
```

## Authentication Methods

The API supports two authentication methods:

### 1. HTTP Basic Auth

Use standard HTTP Basic Authentication with any username and the configured password:

```bash
# Using curl
curl -u "admin:your_password" https://api.example.com/api/v1/marketplace/plugins

# Using httpie
http -a admin:your_password https://api.example.com/api/v1/marketplace/plugins

# Using Python requests
import requests
from requests.auth import HTTPBasicAuth

response = requests.get(
    "https://api.example.com/api/v1/marketplace/plugins",
    auth=HTTPBasicAuth("admin", "your_password")
)
```

**Note:** The username is ignored; only the password is validated.

### 2. Custom Header (X-Auth-Token)

Send the password in the `X-Auth-Token` header:

```bash
# Using curl
curl -H "X-Auth-Token: your_password" https://api.example.com/api/v1/marketplace/plugins

# Using httpie
http https://api.example.com/api/v1/marketplace/plugins X-Auth-Token:your_password

# Using Python requests
import requests

response = requests.get(
    "https://api.example.com/api/v1/marketplace/plugins",
    headers={"X-Auth-Token": "your_password"}
)
```

## Public Endpoints

The following endpoints are **always public** and do not require authentication:

- `GET /health` - Health check endpoint
- `GET /docs` - API documentation (Swagger UI)
- `GET /openapi.json` - OpenAPI schema
- `GET /redoc` - Alternative API documentation

## Protected Endpoints

All endpoints under `/api/*` and `/ws/*` require authentication when `AUTH_PASSWORD` is set:

- `/api/v1/marketplace/*` - Marketplace operations
- `/api/v1/tasks/*` - Task management
- `/api/v1/files/*` - File operations
- `/ws` - WebSocket connections

## Security Features

### 1. Constant-Time Comparison

Password comparison uses `secrets.compare_digest()` to prevent timing attacks:

```python
# Secure comparison prevents attackers from guessing passwords
# by measuring response times
secrets.compare_digest(provided_password, configured_password)
```

### 2. Rate Limiting

Failed authentication attempts are rate-limited to prevent brute-force attacks:

- **Limit:** 5 failed attempts per minute per IP address
- **Window:** 60 seconds
- **Response:** HTTP 429 (Too Many Requests)
- **Retry-After:** 60 seconds

```bash
# After 5 failed attempts within 60 seconds:
HTTP/1.1 429 Too Many Requests
Retry-After: 60
{
  "detail": "Too many failed authentication attempts. Please try again later."
}
```

### 3. Authentication Logging

All authentication attempts are logged:

```
# Successful authentication
2025-12-28 10:15:30 - app.core.security - INFO - Successful authentication via X-Auth-Token from 192.168.1.100

# Failed authentication
2025-12-28 10:15:35 - app.core.security - WARNING - Failed authentication via X-Auth-Token from 192.168.1.100

# Rate limiting triggered
2025-12-28 10:15:40 - app.core.security - WARNING - Rate limit exceeded for authentication attempts from 192.168.1.100
```

## Error Responses

### 401 Unauthorized

No authentication provided or invalid credentials:

```json
{
  "detail": "Authentication required. Provide X-Auth-Token header or HTTP Basic Auth."
}
```

Headers:
```
WWW-Authenticate: Basic realm="Dify Plugin Repackaging"
```

### 429 Too Many Requests

Rate limit exceeded:

```json
{
  "detail": "Too many failed authentication attempts. Please try again later."
}
```

Headers:
```
Retry-After: 60
```

## Testing

Use the provided test script to verify authentication:

```bash
# Test with authentication enabled
python3 backend/test_auth.py http://localhost:8000 your_password

# Test public endpoints only (no password)
python3 backend/test_auth.py http://localhost:8000
```

The test script validates:

1. Public endpoints are accessible without auth
2. Protected endpoints require authentication
3. HTTP Basic Auth works correctly
4. X-Auth-Token header works correctly
5. Wrong passwords are rejected
6. Rate limiting is enforced

## Development Mode

For local development, leave `AUTH_PASSWORD` unset or empty to disable authentication:

```bash
# Development - no authentication
docker-compose up

# Production - with authentication
AUTH_PASSWORD=secure_password docker-compose up
```

## Best Practices

1. **Use Strong Passwords:** Generate a random password with at least 32 characters:
   ```bash
   # Generate a secure password
   openssl rand -base64 32
   ```

2. **HTTPS Only:** Always use HTTPS in production to prevent password interception

3. **Rotate Passwords:** Change the password periodically

4. **Monitor Logs:** Check logs for suspicious authentication patterns

5. **Environment Variables:** Never commit passwords to version control

6. **Secrets Management:** Use a secrets manager (e.g., Docker secrets, Kubernetes secrets) in production

## Example: Frontend Integration

### JavaScript/TypeScript

```typescript
// Using fetch with X-Auth-Token
const response = await fetch('https://api.example.com/api/v1/marketplace/plugins', {
  headers: {
    'X-Auth-Token': 'your_password',
    'Content-Type': 'application/json'
  }
});

// Using fetch with Basic Auth
const response = await fetch('https://api.example.com/api/v1/marketplace/plugins', {
  headers: {
    'Authorization': 'Basic ' + btoa('admin:your_password'),
    'Content-Type': 'application/json'
  }
});

// Using axios
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://api.example.com',
  headers: {
    'X-Auth-Token': 'your_password'
  }
});

const response = await api.get('/api/v1/marketplace/plugins');
```

## Troubleshooting

### Authentication Always Fails

1. Check that `AUTH_PASSWORD` is set correctly:
   ```bash
   echo $AUTH_PASSWORD
   ```

2. Verify no extra whitespace in the password

3. Check logs for specific error messages

### Rate Limiting Issues

1. Wait 60 seconds after failed attempts
2. Check if IP address is being correctly identified (X-Forwarded-For header)
3. Review rate limiter configuration in `config.py`

### WebSocket Authentication

WebSocket connections (`/ws/*`) also require authentication. Pass the token in the connection URL or headers:

```javascript
// WebSocket with auth token in URL parameter
const ws = new WebSocket('wss://api.example.com/ws?token=your_password');

// Or use custom headers (if supported by client)
const ws = new WebSocket('wss://api.example.com/ws', {
  headers: {
    'X-Auth-Token': 'your_password'
  }
});
```

**Note:** WebSocket authentication implementation may need additional handling depending on the WebSocket library used.

## Migration Guide

### Enabling Authentication on Existing Deployment

1. Add `AUTH_PASSWORD` to environment variables
2. Restart the service
3. Update all API clients to include authentication
4. Monitor logs for failed authentication attempts
5. Update documentation/client libraries

### Disabling Authentication

1. Remove or empty the `AUTH_PASSWORD` environment variable
2. Restart the service
3. All endpoints become accessible without authentication
