import httpx
from typing import List, Dict, Optional, Tuple
from app.core.config import settings
from app.workers.celery_app import redis_client
import logging
import json
import re

logger = logging.getLogger(__name__)


class MarketplaceService:
    """Service for interacting with Dify Marketplace API"""
    
    @staticmethod
    def _get_cache_key(endpoint: str, params: dict = None) -> str:
        """Generate cache key from endpoint and params"""
        if params:
            param_str = json.dumps(params, sort_keys=True)
            return f"marketplace:{endpoint}:{param_str}"
        return f"marketplace:{endpoint}"
    
    @staticmethod
    def _get_from_cache(key: str) -> Optional[dict]:
        """Get value from Redis cache if not expired"""
        try:
            cached_data = redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Error getting from cache: {e}")
        return None
    
    @staticmethod
    def _set_cache(key: str, data: dict):
        """Set value in Redis cache with TTL"""
        try:
            redis_client.setex(
                key,
                settings.MARKETPLACE_CACHE_TTL,
                json.dumps(data)
            )
        except Exception as e:
            logger.warning(f"Error setting cache: {e}")
    
    @staticmethod
    async def search_plugins(
        query: Optional[str] = None,
        author: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict:
        """
        Search for plugins in the marketplace
        
        Returns a dict with:
        - plugins: List of plugin metadata
        - total: Total number of results
        - page: Current page
        - per_page: Results per page
        """
        # Build cache key
        cache_key = MarketplaceService._get_cache_key(
            "search",
            {"query": query, "author": author, "category": category, "page": page, "per_page": per_page}
        )
        
        # Check cache
        cached_result = MarketplaceService._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Returning cached search results for: {cache_key}")
            return cached_result
        
        # Build request parameters
        params = {
            "page": page,
            "per_page": per_page
        }
        if query:
            params["q"] = query
        if author:
            params["author"] = author
        if category:
            params["category"] = category
        
        try:
            # Make API request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{settings.MARKETPLACE_API_URL}/api/v1/plugins",
                    params=params
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Cache the result
                MarketplaceService._set_cache(cache_key, result)
                
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"Error searching marketplace: {e}")
            # Return empty result on error
            return {
                "plugins": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "error": str(e)
            }
    
    @staticmethod
    async def get_plugin_details(author: str, name: str) -> Optional[Dict]:
        """
        Get detailed information about a specific plugin
        
        Returns plugin metadata including:
        - name, author, description
        - latest_version
        - available_versions
        - category, tags
        - created_at, updated_at
        """
        cache_key = MarketplaceService._get_cache_key(f"plugin:{author}:{name}")
        
        # Check cache
        cached_result = MarketplaceService._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Returning cached plugin details for: {author}/{name}")
            return cached_result
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{settings.MARKETPLACE_API_URL}/api/v1/plugins/{author}/{name}"
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Cache the result
                MarketplaceService._set_cache(cache_key, result)
                
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"Error getting plugin details for {author}/{name}: {e}")
            return None
    
    @staticmethod
    async def get_plugin_versions(author: str, name: str) -> List[Dict]:
        """
        Get all available versions for a plugin
        
        Returns list of version objects with:
        - version: Version string
        - created_at: Release date
        - changelog: Version changelog (if available)
        """
        cache_key = MarketplaceService._get_cache_key(f"versions:{author}:{name}")
        
        # Check cache
        cached_result = MarketplaceService._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Returning cached versions for: {author}/{name}")
            return cached_result
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{settings.MARKETPLACE_API_URL}/api/v1/plugins/{author}/{name}/versions",
                    params={"page": 1, "page_size": 20}  # Add required pagination params
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Cache the result
                MarketplaceService._set_cache(cache_key, result)
                
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"Error getting plugin versions for {author}/{name}: {e}")
            return []
    
    @staticmethod
    def build_download_url(author: str, name: str, version: str) -> str:
        """Build the download URL for a specific plugin version"""
        return f"{settings.MARKETPLACE_API_URL}/api/v1/plugins/{author}/{name}/{version}/download"
    
    @staticmethod
    def construct_download_url(author: str, name: str, version: str) -> str:
        """Alias for build_download_url - construct the download URL for a specific plugin version"""
        return MarketplaceService.build_download_url(author, name, version)
    
    @staticmethod
    async def get_categories() -> List[str]:
        """Get list of available plugin categories"""
        cache_key = MarketplaceService._get_cache_key("categories")
        
        # Check cache
        cached_result = MarketplaceService._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{settings.MARKETPLACE_API_URL}/api/v1/categories"
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Cache the result
                MarketplaceService._set_cache(cache_key, result)
                
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"Error getting categories: {e}")
            # Return default categories on error
            return ["agent", "tool", "model", "extension", "workflow"]
    
    @staticmethod
    def parse_marketplace_url(url: str) -> Optional[Tuple[str, str]]:
        """
        Parse a marketplace URL to extract author and plugin name
        
        Supports URLs like:
        - https://marketplace.dify.ai/plugins/langgenius/ollama
        - http://marketplace.dify.ai/plugins/langgenius/ollama/
        
        Returns:
            Tuple of (author, name) if valid marketplace URL, None otherwise
        """
        # Remove settings.MARKETPLACE_API_URL to handle both production and custom URLs
        marketplace_base = settings.MARKETPLACE_API_URL.rstrip('/')
        # Remove protocol to make matching easier
        marketplace_host = marketplace_base.replace('https://', '').replace('http://', '')
        
        # Pattern to match marketplace plugin URLs
        pattern = rf'^https?://{re.escape(marketplace_host)}/plugins/([^/]+)/([^/]+)/?$'
        
        match = re.match(pattern, url.strip())
        if match:
            author = match.group(1)
            name = match.group(2)
            logger.info(f"Parsed marketplace URL: author={author}, name={name}")
            return (author, name)
        
        return None
    
    @staticmethod
    async def get_latest_version(author: str, name: str) -> Optional[str]:
        """
        Get the latest version of a plugin
        
        Args:
            author: Plugin author
            name: Plugin name
            
        Returns:
            Latest version string if found, None otherwise
        """
        try:
            logger.info(f"Getting latest version for {author}/{name}")
            
            # Try to get plugin details which includes latest_version
            plugin_details = await MarketplaceService.get_plugin_details(author, name)
            
            if plugin_details and 'latest_version' in plugin_details:
                logger.info(f"Found latest version in plugin details: {plugin_details['latest_version']}")
                return plugin_details['latest_version']
            
            # Fallback to getting versions list
            logger.info(f"Fetching versions list for {author}/{name}")
            versions = await MarketplaceService.get_plugin_versions(author, name)
            
            if versions and len(versions) > 0:
                # Versions are typically returned sorted with latest first
                latest = versions[0].get('version')
                logger.info(f"Found latest version from versions list: {latest}")
                return latest
                
            logger.warning(f"No versions found for {author}/{name}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest version for {author}/{name}: {e}", exc_info=True)
            return None