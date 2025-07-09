"""
HTTP client utilities with proper timeout and logging configuration
"""
import httpx
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def get_default_timeout() -> httpx.Timeout:
    """Get default timeout configuration for HTTP clients"""
    return httpx.Timeout(
        timeout=settings.HTTP_TIMEOUT,
        connect=settings.HTTP_CONNECT_TIMEOUT,
        read=settings.HTTP_READ_TIMEOUT,
        write=settings.HTTP_WRITE_TIMEOUT,
        pool=settings.HTTP_POOL_TIMEOUT
    )


def get_async_client(**kwargs) -> httpx.AsyncClient:
    """
    Create an async HTTP client with default configuration
    
    Args:
        **kwargs: Additional arguments to pass to httpx.AsyncClient
        
    Returns:
        Configured httpx.AsyncClient instance
    """
    default_kwargs = {
        "timeout": get_default_timeout(),
        "follow_redirects": True,
        "limits": httpx.Limits(
            max_keepalive_connections=5,
            max_connections=10,
            keepalive_expiry=30.0
        ),
        "headers": {
            "User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION}",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9"
        }
    }
    
    # Merge with provided kwargs (provided kwargs override defaults)
    default_kwargs.update(kwargs)
    
    # Log client creation
    logger.debug(f"Creating async HTTP client with config: {default_kwargs}")
    
    return httpx.AsyncClient(**default_kwargs)


async def make_request_with_retry(
    method: str,
    url: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
    **kwargs
) -> httpx.Response:
    """
    Make an HTTP request with retry logic
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: URL to request
        max_retries: Maximum number of retries
        base_delay: Base delay between retries (exponential backoff)
        **kwargs: Additional arguments to pass to the request
        
    Returns:
        httpx.Response object
        
    Raises:
        httpx.HTTPError: If all retries fail
    """
    import asyncio
    
    for attempt in range(max_retries):
        try:
            async with get_async_client() as client:
                logger.info(f"Making {method} request to {url} (attempt {attempt + 1}/{max_retries})")
                
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                
                logger.info(f"Request successful: {method} {url} - Status: {response.status_code}")
                return response
                
        except httpx.TimeoutException as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"Request timeout for {method} {url} (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"Request timeout after {max_retries} attempts: {method} {url}")
                raise
                
        except httpx.HTTPStatusError as e:
            # Don't retry on 4xx errors
            if 400 <= e.response.status_code < 500:
                logger.error(f"Client error for {method} {url}: {e.response.status_code}")
                raise
            # Retry on 5xx errors
            elif attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"Server error for {method} {url} (attempt {attempt + 1}/{max_retries}): "
                    f"{e.response.status_code}. Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"Server error after {max_retries} attempts: {method} {url}")
                raise
                
        except Exception as e:
            logger.error(f"Unexpected error for {method} {url}: {e}")
            raise
    
    # This should never be reached
    raise RuntimeError(f"Request failed unexpectedly: {method} {url}")