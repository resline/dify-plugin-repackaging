import httpx
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
from app.core.config import settings
from app.workers.celery_app import redis_client
from app.utils.http_client import get_async_client
import logging
import json
import re
import asyncio
from app.utils.circuit_breaker import marketplace_circuit_breaker, CircuitOpenError

logger = logging.getLogger(__name__)


class MarketplaceService:
    """Service for interacting with Dify Marketplace API"""
    
    @staticmethod
    async def _make_api_request(client: httpx.AsyncClient, method: str, url: str, **kwargs):
        """Make an API request with circuit breaker protection"""
        async def _request():
            # Ensure headers include Accept: application/json
            headers = kwargs.get("headers", {})
            headers["Accept"] = "application/json"
            kwargs["headers"] = headers
            
            if method.upper() == "GET":
                response = await client.get(url, **kwargs)
            elif method.upper() == "POST":
                response = await client.post(url, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Log response details for debugging
            logger.debug(f"Response from {url}: status={response.status_code}, headers={dict(response.headers)}")
            
            response.raise_for_status()
            
            # Validate response content type
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type.lower() and response.content:
                logger.warning(f"Non-JSON response from {url}: {content_type}")
                
                # Check if it's HTML (common error page)
                if "text/html" in content_type.lower():
                    logger.error(f"Received HTML response from {url} - likely an error page or API change")
                    raise ValueError(f"API returned HTML instead of JSON - API may have changed")
                
                # Try to parse anyway
                try:
                    response.json()
                except Exception:
                    logger.error(f"Response preview: {response.text[:200]}...")
                    raise ValueError(f"Invalid response format from {url}: expected JSON, got {content_type}")
            
            return response
        
        return await marketplace_circuit_breaker.async_call(_request)
    
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
            # Try multiple API endpoints in order
            api_attempts = [
                {
                    "url": "https://marketplace.dify.ai/api/v1/plugins",
                    "method": "GET",
                    "params": params,
                    "transformer": lambda r: {
                        "plugins": r.get("data", r.get("plugins", [])),
                        "total": r.get("total", len(r.get("data", r.get("plugins", [])))),
                        "page": page,
                        "per_page": per_page
                    }
                },
                {
                    "url": "https://marketplace-plugin.dify.dev/api/v1/plugins",
                    "method": "GET", 
                    "params": params,
                    "transformer": lambda r: {
                        "plugins": r.get("data", r.get("plugins", [])),
                        "total": r.get("total", len(r.get("data", r.get("plugins", [])))),
                        "page": page,
                        "per_page": per_page
                    }
                }
            ]
            
            # Try each API endpoint
            async with get_async_client() as client:
                last_error = None
                
                for attempt in api_attempts:
                    try:
                        logger.info(f"Trying marketplace API: {attempt['url']}")
                        
                        if attempt["method"] == "GET":
                            response = await MarketplaceService._make_api_request(
                                client,
                                "GET",
                                attempt["url"],
                                params=attempt["params"]
                            )
                        else:
                            response = await MarketplaceService._make_api_request(
                                client,
                                "POST",
                                attempt["url"],
                                json=attempt.get("json", {}),
                                headers={
                                    "Content-Type": "application/json",
                                    "Accept": "application/json"
                                }
                            )
                        
                        # Parse response
                        try:
                            result = response.json()
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON from {attempt['url']}: {e}")
                            continue
                        
                        # Transform and return result
                        transformed_result = attempt["transformer"](result)
                        
                        # Add success metadata
                        transformed_result["api_endpoint"] = attempt["url"]
                        transformed_result["has_more"] = transformed_result["total"] > (page * per_page)
                        
                        # Cache the result
                        MarketplaceService._set_cache(cache_key, transformed_result)
                        
                        return transformed_result
                        
                    except (httpx.HTTPError, CircuitOpenError, ValueError) as e:
                        last_error = e
                        logger.warning(f"API attempt failed for {attempt['url']}: {e}")
                        continue
                
                # All API attempts failed, raise the last error
                if last_error:
                    raise last_error
                    
        except (httpx.HTTPError, CircuitOpenError) as e:
            # API is not working - try web scraping fallback
            if isinstance(e, CircuitOpenError):
                logger.warning("Circuit breaker is open, falling back to web scraper.")
            else:
                logger.warning("Dify Marketplace API has been updated, falling back to web scraper.")
            try:
                from app.services.marketplace_scraper import marketplace_fallback_service
                scraped_result = await marketplace_fallback_service.scraper.scrape_plugin_list(
                    page=page, per_page=per_page, category=category, query=query
                )
                
                # Add API status info
                scraped_result["api_status"] = "incompatible"
                scraped_result["fallback_used"] = True
                scraped_result["fallback_reason"] = "API endpoints changed"
                
                # Cache the scraped result
                MarketplaceService._set_cache(cache_key, scraped_result)
                
                return scraped_result
                
            except Exception as scrape_error:
                logger.error(f"Web scraping also failed: {scrape_error}")
                return {
                    "plugins": [],
                    "total": 0,
                    "page": page,
                    "per_page": per_page,
                    "error": "Dify Marketplace API has changed and web scraping failed.",
                    "api_status": "incompatible"
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
            # First try to get details from search results
            # Since the direct plugin detail API returns 404, we use search
            search_result = await MarketplaceService.search_plugins(
                query=name,
                author=author,
                per_page=1
            )
            
            if search_result.get("plugins"):
                # Find the exact match in search results
                for plugin in search_result["plugins"]:
                    if plugin.get("author") == author and plugin.get("name") == name:
                        # Cache and return the plugin details
                        MarketplaceService._set_cache(cache_key, plugin)
                        return plugin
            
            # If not found in search, try direct API (might work for some plugins)
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.get(
                        f"{settings.MARKETPLACE_API_URL}/api/v1/plugins/{author}/{name}"
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    
                    # Cache the result
                    MarketplaceService._set_cache(cache_key, result)
                    
                    return result
                except httpx.HTTPError:
                    # Direct API failed, continue to fallback
                    pass
                
        except Exception as e:
            logger.error(f"Error getting plugin details for {author}/{name}: {e}")
            
            # Try web scraping fallback
            try:
                from app.services.marketplace_scraper import marketplace_fallback_service
                scraped_details = await marketplace_fallback_service.scraper.scrape_plugin_details(author, name)
                
                if scraped_details:
                    # Add fallback info
                    scraped_details["fallback_used"] = True
                    scraped_details["fallback_reason"] = "API request failed"
                    
                    # Cache the scraped result
                    MarketplaceService._set_cache(cache_key, scraped_details)
                    
                    return scraped_details
                    
            except Exception as scrape_error:
                logger.error(f"Web scraping also failed for plugin details: {scrape_error}")
            
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
            
            # Try web scraping fallback
            try:
                from app.services.marketplace_scraper import marketplace_fallback_service
                scraped_versions = await marketplace_fallback_service.scraper.scrape_plugin_versions(author, name)
                
                if scraped_versions:
                    # Cache the scraped result
                    MarketplaceService._set_cache(cache_key, scraped_versions)
                    
                    return scraped_versions
                    
            except Exception as scrape_error:
                logger.error(f"Web scraping also failed for plugin versions: {scrape_error}")
            
            return []
    
    @staticmethod
    def build_download_url(author: str, name: str, version: str) -> str:
        """Build the download URL for a specific plugin version"""
        # Use the hardcoded marketplace URL for downloads
        marketplace_api_url = "https://marketplace.dify.ai"
        return f"{marketplace_api_url}/api/v1/plugins/{author}/{name}/{version}/download"
    
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
        if cached_result and isinstance(cached_result, list):
            return cached_result
        
        # Default categories
        default_categories = ["agent", "tool", "model", "extension", "workflow"]
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{settings.MARKETPLACE_API_URL}/api/v1/categories"
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Handle different response formats
                if isinstance(result, list):
                    categories = result
                elif isinstance(result, dict) and "categories" in result:
                    categories = result["categories"]
                else:
                    logger.warning(f"Unexpected categories response format: {type(result)}")
                    categories = default_categories
                
                # Validate categories
                if not categories or not isinstance(categories, list):
                    categories = default_categories
                
                # Cache the result
                MarketplaceService._set_cache(cache_key, categories)
                
                return categories
                
        except httpx.HTTPError as e:
            logger.error(f"Error getting categories: {e}")
            # Return default categories on error
            return default_categories
    
    @staticmethod
    def parse_marketplace_url(url: str) -> Optional[Tuple[str, str]]:
        """
        Parse a marketplace URL to extract author and plugin name
        
        Supports URLs like:
        - https://marketplace.dify.ai/plugins/langgenius/ollama
        - http://marketplace.dify.ai/plugins/langgenius/ollama/
        - https://marketplace.dify.ai/plugins/langgenius/openai_api_compatible?source=...
        - https://marketplace.dify.ai/plugin/langgenius/ollama (singular form)
        - marketplace.dify.ai/plugins/langgenius/ollama (without protocol)
        
        Returns:
            Tuple of (author, name) if valid marketplace URL, None otherwise
        """
        try:
            # Clean the URL
            url = url.strip()
            
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Remove query parameters and fragments
            url_without_query = url.split('?')[0].split('#')[0].strip()
            
            # Parse the URL to extract components
            parsed = urlparse(url_without_query)
            
            # Check if it's a marketplace URL (with or without www)
            if parsed.netloc in ['marketplace.dify.ai', 'www.marketplace.dify.ai']:
                # Extract plugin info from path
                # Support both /plugins/ and /plugin/ paths
                path_match = re.match(r'^/plugins?/([^/]+)/([^/]+)/?$', parsed.path)
                if path_match:
                    author = path_match.group(1).strip()
                    name = path_match.group(2).strip()
                    
                    # Validate author and name are not empty
                    if author and name:
                        logger.info(f"Parsed marketplace URL: author={author}, name={name}")
                        return (author, name)
                    else:
                        logger.warning(f"Empty author or name in URL: {url_without_query}")
            
            logger.info(f"Not a valid marketplace URL: {url_without_query}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing marketplace URL {url}: {e}")
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
            
            # Try multiple API formats for better compatibility
            attempts = [
                # New API format
                {
                    "url": f"https://marketplace.dify.ai/api/v1/plugins/{author}/{name}",
                    "extractor": lambda r: r.get("data", {}).get("plugin", {}).get("latest_version") if r.get("code") == 0 else None
                },
                # Alternative format
                {
                    "url": f"https://marketplace.dify.ai/api/v1/plugins/{author}/{name}",
                    "extractor": lambda r: r.get("latest_version")
                },
                # Direct plugin info
                {
                    "url": f"{settings.MARKETPLACE_API_URL}/api/v1/plugins/{author}/{name}",
                    "extractor": lambda r: r.get("latest_version")
                }
            ]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for attempt in attempts:
                    try:
                        response = await client.get(
                            attempt["url"],
                            headers={"Content-Type": "application/json"}
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            latest_version = attempt["extractor"](result)
                            
                            if latest_version:
                                logger.info(f"Found latest version: {latest_version} using {attempt['url']}")
                                return latest_version
                    except Exception as e:
                        logger.debug(f"Attempt failed for {attempt['url']}: {e}")
                        continue
            
            # Fallback to search method
            logger.info(f"Trying search method for {author}/{name}")
            search_result = await MarketplaceService.search_plugins(
                query=name,
                author=author,
                per_page=1
            )
            
            if search_result.get("plugins"):
                for plugin in search_result["plugins"]:
                    if plugin.get("author") == author and plugin.get("name") == name:
                        latest_version = plugin.get("latest_version")
                        if latest_version:
                            logger.info(f"Found latest version via search: {latest_version}")
                            return latest_version
            
            # Final fallback to plugin details
            logger.info(f"Trying plugin details method for {author}/{name}")
            plugin_details = await MarketplaceService.get_plugin_details(author, name)
            
            if plugin_details and 'latest_version' in plugin_details:
                logger.info(f"Found latest version in plugin details: {plugin_details['latest_version']}")
                return plugin_details['latest_version']
            
            logger.warning(f"No versions found for {author}/{name} after all attempts")
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest version for {author}/{name}: {e}", exc_info=True)
            return None