# Security Implementation Details

## Overview

This document provides technical details about the authentication implementation for developers.

## Architecture

### Components

1. **config.py** - Configuration management
   - `AUTH_PASSWORD`: Optional password setting
   - `AUTH_RATE_LIMIT_PER_MINUTE`: Rate limit configuration

2. **security.py** - Authentication logic
   - Password verification with constant-time comparison
   - HTTP Basic Auth parsing
   - X-Auth-Token header support
   - Rate limiting for failed attempts
   - Client identifier extraction

3. **main.py** - Middleware integration
   - Authentication middleware for protected endpoints
   - Public endpoint bypass
   - Error handling and logging

### Authentication Flow

```
┌─────────────┐
│   Request   │
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│ Is Public Endpoint?  │
│ (/health, /docs)     │
└──────┬───────────────┘
       │
       ├─── Yes ──────────────────────┐
       │                              │
       ▼                              │
┌──────────────────────┐              │
│ Is API Endpoint?     │              │
│ (/api/*, /ws/*)      │              │
└──────┬───────────────┘              │
       │                              │
       ├─── No ────────────────────┐  │
       │                           │  │
       ▼                           │  │
┌──────────────────────┐           │  │
│ AUTH_PASSWORD set?   │           │  │
└──────┬───────────────┘           │  │
       │                           │  │
       ├─── No (disabled) ─────────┤  │
       │                           │  │
       ▼                           │  │
┌──────────────────────┐           │  │
│ Check Rate Limit     │           │  │
└──────┬───────────────┘           │  │
       │                           │  │
       ├─── Exceeded ──> 429       │  │
       │                           │  │
       ▼                           │  │
┌──────────────────────┐           │  │
│ Extract Credentials  │           │  │
│ (Basic Auth or Token)│           │  │
└──────┬───────────────┘           │  │
       │                           │  │
       ▼                           │  │
┌──────────────────────┐           │  │
│ Verify Password      │           │  │
│ (constant-time)      │           │  │
└──────┬───────────────┘           │  │
       │                           │  │
       ├─── Invalid ──> 401        │  │
       │                           │  │
       ▼                           ▼  ▼
   ┌────────────────────────────────────┐
   │    Process Request (call_next)     │
   └────────────────────────────────────┘
```

## Security Features

### 1. Constant-Time Comparison

**Purpose:** Prevent timing attacks where attackers measure response times to guess passwords.

**Implementation:**
```python
import secrets

def constant_time_compare(a: str, b: str) -> bool:
    a_bytes = a.encode('utf-8')
    b_bytes = b.encode('utf-8')
    return secrets.compare_digest(a_bytes, b_bytes)
```

**Why it matters:**
- Regular `==` comparison returns as soon as it finds a mismatch
- Timing differences can reveal information about the password
- `secrets.compare_digest()` always takes the same time regardless of where strings differ

### 2. Rate Limiting

**Purpose:** Prevent brute-force attacks by limiting failed authentication attempts.

**Implementation:**
```python
class RateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts = defaultdict(list)

    def is_rate_limited(self, identifier: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old attempts
        self.attempts[identifier] = [
            t for t in self.attempts[identifier] if t > cutoff
        ]

        return len(self.attempts[identifier]) >= self.max_attempts
```

**Configuration:**
- Default: 5 attempts per 60 seconds per IP
- Tracked by client IP address
- Supports X-Forwarded-For header for proxies
- In-memory storage (resets on restart)

**Production considerations:**
- For high-availability deployments, consider Redis-based rate limiting
- Current implementation is per-instance (not shared across multiple backend instances)

### 3. Client Identification

**Purpose:** Identify unique clients for rate limiting and logging.

**Implementation:**
```python
def get_client_identifier(request: Request) -> str:
    # Try X-Forwarded-For (proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return "unknown"
```

**Headers considered:**
- `X-Forwarded-For`: First IP in the chain (real client IP when behind proxy)
- `request.client.host`: Direct connection IP

### 4. Logging

**Purpose:** Audit trail for security monitoring.

**Events logged:**
- Successful authentication (INFO level)
- Failed authentication (WARNING level)
- Rate limit exceeded (WARNING level)
- Public endpoint access (DEBUG level)

**Log format:**
```
2025-12-28 10:15:30 - app.core.security - INFO - Successful authentication via X-Auth-Token from 192.168.1.100
2025-12-28 10:15:35 - app.core.security - WARNING - Failed authentication via Basic Auth (user: admin) from 192.168.1.100
2025-12-28 10:15:40 - app.core.security - WARNING - Rate limit exceeded for authentication attempts from 192.168.1.100
```

## Authentication Methods

### HTTP Basic Auth

**Format:** `Authorization: Basic base64(username:password)`

**Implementation:**
```python
def extract_basic_auth(authorization_header: str) -> Optional[Tuple[str, str]]:
    scheme, credentials = authorization_header.split(' ', 1)
    if scheme.lower() != 'basic':
        return None

    decoded = base64.b64decode(credentials).decode('utf-8')
    username, password = decoded.split(':', 1)
    return username, password
```

**Notes:**
- Username is extracted but not validated (only password matters)
- Follows RFC 7617 standard
- Automatically supported by most HTTP clients

### X-Auth-Token Header

**Format:** `X-Auth-Token: password`

**Implementation:**
```python
auth_token = request.headers.get("X-Auth-Token")
if auth_token and verify_password(auth_token):
    return True
```

**Advantages:**
- Simpler than Basic Auth
- No base64 encoding needed
- Easier to use in JavaScript/frontend code

## Middleware Order

**Critical:** Middleware execution order matters!

```python
# 1. CORS (runs last, added first)
app.add_middleware(CORSMiddleware, ...)

# 2. Rate limiting
app.add_middleware(SlowAPIMiddleware)

# 3. Custom middleware
app.add_middleware(JSONResponseMiddleware)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestValidationMiddleware)

# 4. HTTP middleware (runs first, added last)
@app.middleware("http")
async def authentication_middleware(...): ...

@app.middleware("http")
async def log_requests(...): ...
```

**Execution order:** Bottom to top (log_requests → authentication → ... → CORS)

## Public Endpoints

**Definition:**
```python
def is_public_endpoint(path: str) -> bool:
    public_paths = ["/health", "/docs", "/openapi.json", "/redoc"]
    return path in public_paths or path.startswith(("/docs", "/redoc"))
```

**Rationale:**
- `/health`: Required for container health checks and monitoring
- `/docs`, `/openapi.json`, `/redoc`: API documentation (can be restricted if needed)

## Configuration

### Environment Variables

```bash
# Disable authentication (default for development)
# AUTH_PASSWORD not set or empty

# Enable authentication
export AUTH_PASSWORD="your-secure-password"

# Adjust rate limiting
export AUTH_RATE_LIMIT_PER_MINUTE=10
```

### Pydantic Settings

```python
class Settings(BaseSettings):
    AUTH_PASSWORD: Optional[str] = None
    AUTH_RATE_LIMIT_PER_MINUTE: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = True
```

**Benefits:**
- Type validation
- Environment variable support
- .env file support
- Default values

## Testing

### Unit Tests

```python
# Test constant-time comparison
def test_constant_time_compare():
    assert constant_time_compare("password", "password") == True
    assert constant_time_compare("password", "wrong") == False
    assert constant_time_compare("", "") == False

# Test rate limiting
def test_rate_limiter():
    limiter = RateLimiter(max_attempts=3, window_seconds=60)

    # First 3 attempts should work
    for i in range(3):
        assert not limiter.is_rate_limited("client1")
        limiter.record_attempt("client1")

    # 4th attempt should be rate limited
    assert limiter.is_rate_limited("client1")

# Test authentication
async def test_authentication():
    # Mock request with valid token
    request = MockRequest(headers={"X-Auth-Token": "correct_password"})
    assert await verify_authentication(request) == True

    # Mock request with invalid token
    request = MockRequest(headers={"X-Auth-Token": "wrong_password"})
    with pytest.raises(HTTPException) as exc:
        await verify_authentication(request)
    assert exc.value.status_code == 401
```

### Integration Tests

Use the provided `test_auth.py` script:

```bash
# Start server with authentication
export AUTH_PASSWORD="test123"
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Run tests
python3 test_auth.py http://localhost:8000 test123
```

## Performance Considerations

### In-Memory Rate Limiting

**Current implementation:**
- Simple `defaultdict` stores timestamps
- No persistence across restarts
- Not shared across multiple instances

**For production with multiple instances:**

Option 1: Redis-based rate limiting
```python
import redis
from datetime import datetime, timedelta

class RedisRateLimiter:
    def __init__(self, redis_client, max_attempts=5, window_seconds=60):
        self.redis = redis_client
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds

    def is_rate_limited(self, identifier: str) -> bool:
        key = f"auth_attempts:{identifier}"
        count = self.redis.get(key)
        return int(count or 0) >= self.max_attempts

    def record_attempt(self, identifier: str):
        key = f"auth_attempts:{identifier}"
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.window_seconds)
        pipe.execute()
```

Option 2: Distributed cache (memcached)
Option 3: Database-based tracking

### Password Hashing

**Current implementation:** Direct comparison (suitable for API tokens)

**For user passwords (future enhancement):**
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

## Security Hardening Checklist

- [x] Constant-time password comparison
- [x] Rate limiting for failed attempts
- [x] Audit logging
- [x] HTTPS enforcement (deployment configuration)
- [x] Public endpoint exclusion
- [ ] Password complexity requirements (future)
- [ ] Token expiration (future)
- [ ] Multi-factor authentication (future)
- [ ] IP whitelist/blacklist (future)
- [ ] Distributed rate limiting (for multi-instance deployments)

## Troubleshooting

### Issue: Rate limiting not working across instances

**Symptom:** Different backend instances have separate rate limit counters

**Solution:** Implement Redis-based rate limiting (see Performance Considerations)

### Issue: Timing attack concerns

**Symptom:** Security audit flags timing vulnerabilities

**Verification:** Current implementation uses `secrets.compare_digest()` which is timing-safe

### Issue: WebSocket authentication

**Symptom:** WebSocket connections fail with 401

**Solution:** WebSocket authentication requires special handling:
```python
# In WebSocket endpoint
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Extract token from query parameter or header
    token = websocket.query_params.get("token")
    if not verify_password(token):
        await websocket.close(code=1008)  # Policy violation
        return

    await websocket.accept()
    # ... rest of WebSocket logic
```

## Future Enhancements

1. **JWT Tokens:** Replace simple password with JWT for stateless authentication
2. **API Keys:** Support multiple API keys with different permissions
3. **User Management:** Add user accounts with different roles
4. **OAuth2:** Integrate with external identity providers
5. **Session Management:** Add session support with expiration
6. **Password Rotation:** Automatic password expiration and rotation
7. **Two-Factor Authentication:** SMS or TOTP-based 2FA
8. **IP Whitelisting:** Restrict access by IP address
9. **Certificate-Based Auth:** mTLS support

## References

- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [RFC 7617: HTTP Basic Authentication](https://tools.ietf.org/html/rfc7617)
- [Python secrets module](https://docs.python.org/3/library/secrets.html)
