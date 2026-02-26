"""
Security module for authentication and authorization.
Provides simple password-based authentication via HTTP Basic Auth or custom header.
"""

import secrets
import logging
from typing import Optional, Tuple
from fastapi import Request, HTTPException, status
from app.core.config import settings
import base64
import hashlib
import time
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter for failed authentication attempts."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts = defaultdict(list)

    def is_rate_limited(self, identifier: str) -> bool:
        """Check if the identifier is rate limited."""
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean up old attempts
        self.attempts[identifier] = [
            timestamp for timestamp in self.attempts[identifier]
            if timestamp > cutoff
        ]

        # Check if rate limited
        return len(self.attempts[identifier]) >= self.max_attempts

    def record_attempt(self, identifier: str):
        """Record a failed authentication attempt."""
        self.attempts[identifier].append(time.time())

    def reset(self, identifier: str):
        """Reset attempts for an identifier (on successful auth)."""
        if identifier in self.attempts:
            del self.attempts[identifier]


# Global rate limiter instance
auth_rate_limiter = RateLimiter(
    max_attempts=settings.AUTH_RATE_LIMIT_PER_MINUTE,
    window_seconds=60
)


def constant_time_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.
    Uses secrets.compare_digest for secure comparison.
    """
    if not a or not b:
        return False

    # Use secrets.compare_digest for constant-time comparison
    # First normalize to bytes to ensure proper comparison
    a_bytes = a.encode('utf-8')
    b_bytes = b.encode('utf-8')

    return secrets.compare_digest(a_bytes, b_bytes)


def extract_basic_auth(authorization_header: str) -> Optional[Tuple[str, str]]:
    """
    Extract username and password from HTTP Basic Auth header.
    Returns (username, password) tuple or None if invalid.
    """
    try:
        scheme, credentials = authorization_header.split(' ', 1)
        if scheme.lower() != 'basic':
            return None

        decoded = base64.b64decode(credentials).decode('utf-8')
        username, password = decoded.split(':', 1)
        return username, password
    except Exception as e:
        logger.debug(f"Failed to parse Basic Auth header: {e}")
        return None


def verify_password(provided_password: str) -> bool:
    """
    Verify the provided password against the configured AUTH_PASSWORD.
    Uses constant-time comparison to prevent timing attacks.
    """
    if not settings.AUTH_PASSWORD:
        # No password configured, authentication is disabled
        return True

    return constant_time_compare(provided_password, settings.AUTH_PASSWORD)


def get_client_identifier(request: Request) -> str:
    """
    Get a unique identifier for the client for rate limiting.
    Uses direct client IP to prevent spoofing via X-Forwarded-For.
    """
    if request.client:
        return request.client.host
    return "unknown"


async def verify_authentication(request: Request) -> bool:
    """
    Verify authentication for the request.
    Supports both HTTP Basic Auth and X-Auth-Token header.

    Returns True if authenticated, raises HTTPException if not.

    Rate limiting strategy:
    - Only applies to requests WITH credentials (potential brute-force attacks)
    - Missing credentials return 401 without counting as failed attempt
    - Wrong credentials count as failed attempt and trigger rate limiting
    """
    # If no password is configured, authentication is disabled
    if not settings.AUTH_PASSWORD:
        logger.debug("Authentication disabled (no AUTH_PASSWORD configured)")
        return True

    client_id = get_client_identifier(request)

    # Method 1: Check X-Auth-Token header
    auth_token = request.headers.get("X-Auth-Token")
    if auth_token:
        # Check rate limit BEFORE verifying credentials (prevent brute-force)
        if auth_rate_limiter.is_rate_limited(client_id):
            logger.warning(f"Rate limit exceeded for authentication attempts from {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed authentication attempts. Please try again later.",
                headers={"Retry-After": "60"}
            )

        if verify_password(auth_token):
            logger.info(f"Successful authentication via X-Auth-Token from {client_id}")
            auth_rate_limiter.reset(client_id)
            return True
        else:
            # WRONG credentials provided - record as failed attempt
            logger.warning(f"Failed authentication via X-Auth-Token from {client_id}")
            auth_rate_limiter.record_attempt(client_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

    # Method 2: Check HTTP Basic Auth
    authorization = request.headers.get("Authorization")
    if authorization:
        credentials = extract_basic_auth(authorization)
        if credentials:
            username, password = credentials

            # Check rate limit BEFORE verifying credentials (prevent brute-force)
            if auth_rate_limiter.is_rate_limited(client_id):
                logger.warning(f"Rate limit exceeded for authentication attempts from {client_id}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many failed authentication attempts. Please try again later.",
                    headers={"Retry-After": "60"}
                )

            if verify_password(password):
                logger.info(f"Successful authentication via Basic Auth (user: {username}) from {client_id}")
                auth_rate_limiter.reset(client_id)
                return True
            else:
                # WRONG credentials provided - record as failed attempt
                logger.warning(f"Failed authentication via Basic Auth (user: {username}) from {client_id}")
                auth_rate_limiter.record_attempt(client_id)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

    # No authentication provided - this is NOT a brute-force attack, just missing credentials
    # Return 401 WITHOUT recording as failed attempt
    logger.warning(f"No authentication provided from {client_id}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide X-Auth-Token header or HTTP Basic Auth."
    )


def is_public_endpoint(path: str) -> bool:
    """
    Check if the endpoint is public (doesn't require authentication).
    Public endpoints: /health, /docs, /openapi.json, /redoc
    """
    public_paths = [
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc"
    ]

    # Check exact matches
    if path in public_paths:
        return True

    # Check if it's a static file for docs
    if path.startswith("/docs") or path.startswith("/redoc"):
        return True

    return False
