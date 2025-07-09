import httpx
import os
from urllib.parse import urlparse
from typing import Tuple, Optional
from app.core.config import settings
from app.utils.http_client import get_async_client, get_default_timeout
import aiofiles
import asyncio
import logging

logger = logging.getLogger(__name__)


class DownloadService:
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate if URL is from allowed domains"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www. prefix if present
        if domain.startswith("www."):
            domain = domain[4:]
        
        return any(domain.endswith(allowed) for allowed in settings.ALLOWED_DOWNLOAD_DOMAINS)
    
    @staticmethod
    async def check_file_size(url: str) -> Optional[int]:
        """
        Check file size using HEAD request
        Returns file size in bytes or None if not available
        """
        try:
            async with get_async_client() as client:
                logger.info(f"Checking file size for URL: {url}")
                response = await client.head(url)
                response.raise_for_status()
                
                content_length = response.headers.get('content-length')
                if content_length:
                    size = int(content_length)
                    logger.info(f"File size for {url}: {size} bytes ({size / (1024*1024):.2f} MB)")
                    return size
                
                logger.warning(f"No content-length header for URL: {url}")
                return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error checking file size for {url}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Failed to check file size for {url}: {type(e).__name__}: {e}")
            return None
    
    @staticmethod
    async def download_file(url: str, task_id: str) -> Tuple[str, str]:
        """Download file from URL and save to temp directory with retry logic"""
        if not DownloadService.validate_url(url):
            raise ValueError(f"URL domain not allowed. Allowed domains: {', '.join(settings.ALLOWED_DOWNLOAD_DOMAINS)}")
        
        # Extract filename from URL
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        
        # For marketplace download URLs, construct filename from the path
        if "marketplace.dify.ai" in parsed.netloc and "/download" in parsed.path:
            # Extract author, name, version from path like /api/v1/plugins/author/name/version/download
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 5:
                author = path_parts[3]
                name = path_parts[4]
                version = path_parts[5]
                filename = f"{author}_{name}_{version}.difypkg"
            else:
                # Fallback to generic filename
                filename = "plugin.difypkg"
        elif not filename.endswith('.difypkg'):
            raise ValueError("URL must point to a .difypkg file")
        
        # Check file size before downloading
        file_size = await DownloadService.check_file_size(url)
        if file_size and file_size > settings.MAX_FILE_SIZE:
            raise ValueError(f"File too large ({file_size} bytes). Maximum size: {settings.MAX_FILE_SIZE} bytes")
        
        # Create task directory
        task_dir = os.path.join(settings.TEMP_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)
        
        # Download file with retry logic
        file_path = os.path.join(task_dir, filename)
        max_retries = 3
        base_delay = 1.0  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Downloading file from {url} (attempt {attempt + 1}/{max_retries})")
                
                # Use longer timeout for larger files
                timeout_seconds = settings.HTTP_TIMEOUT if not file_size else max(settings.HTTP_TIMEOUT, file_size / (100 * 1024))  # At least 100KB/s
                custom_timeout = httpx.Timeout(
                    timeout=timeout_seconds,
                    connect=settings.HTTP_CONNECT_TIMEOUT,
                    read=max(settings.HTTP_READ_TIMEOUT, timeout_seconds),
                    write=settings.HTTP_WRITE_TIMEOUT
                )
                
                async with get_async_client(timeout=custom_timeout) as client:
                    # Stream the download for better memory usage
                    logger.info(f"Starting download with streaming from {url}")
                    async with client.stream('GET', url, follow_redirects=True) as response:
                        # Log response status and headers
                        logger.info(f"Response status: {response.status_code}")
                        logger.debug(f"Response headers: {dict(response.headers)}")
                        
                        response.raise_for_status()
                        
                        # Check file size from response headers if not already known
                        if not file_size:
                            content_length = response.headers.get('content-length')
                            if content_length and int(content_length) > settings.MAX_FILE_SIZE:
                                raise ValueError(f"File too large. Maximum size: {settings.MAX_FILE_SIZE} bytes")
                        
                        # Save file in chunks
                        downloaded_bytes = 0
                        async with aiofiles.open(file_path, 'wb') as f:
                            async for chunk in response.aiter_bytes(chunk_size=8192):
                                await f.write(chunk)
                                downloaded_bytes += len(chunk)
                                
                                # Log progress every 1MB
                                if downloaded_bytes % (1024 * 1024) == 0:
                                    logger.debug(f"Downloaded {downloaded_bytes / (1024 * 1024):.1f} MB")
                        
                        logger.info(f"Download complete: {downloaded_bytes} bytes saved to {file_path}")
                
                logger.info(f"Successfully downloaded file to {file_path}")
                return file_path, filename
                
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Download failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Download failed after {max_retries} attempts: {e}")
                    raise
            except httpx.HTTPStatusError as e:
                # Don't retry on 4xx errors
                if 400 <= e.response.status_code < 500:
                    logger.error(f"Client error downloading file: {e}")
                    raise
                # Retry on 5xx errors
                elif attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Server error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Server error after {max_retries} attempts: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error downloading file: {e}")
                raise
        
        # This should never be reached
        raise RuntimeError("Download failed unexpectedly")