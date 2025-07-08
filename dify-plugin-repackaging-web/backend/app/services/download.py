import httpx
import os
from urllib.parse import urlparse
from typing import Tuple
from app.core.config import settings
import aiofiles


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
    async def download_file(url: str, task_id: str) -> Tuple[str, str]:
        """Download file from URL and save to temp directory"""
        if not DownloadService.validate_url(url):
            raise ValueError(f"URL domain not allowed. Allowed domains: {', '.join(settings.ALLOWED_DOWNLOAD_DOMAINS)}")
        
        # Extract filename from URL
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename.endswith('.difypkg'):
            raise ValueError("URL must point to a .difypkg file")
        
        # Create task directory
        task_dir = os.path.join(settings.TEMP_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)
        
        # Download file
        file_path = os.path.join(task_dir, filename)
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            # Check file size
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > settings.MAX_FILE_SIZE:
                raise ValueError(f"File too large. Maximum size: {settings.MAX_FILE_SIZE} bytes")
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(response.content)
        
        return file_path, filename