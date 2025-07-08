"""
Alternative marketplace parser with web scraping fallback
Handles both API and web scraping with caching and retry logic
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple, Any
import json
import re
import logging
from datetime import datetime, timedelta
import asyncio
from urllib.parse import urljoin, urlparse, parse_qs
import hashlib
from app.core.config import settings
from app.workers.celery_app import redis_client

logger = logging.getLogger(__name__)


class MarketplaceScraper:
    """Web scraper for Dify Marketplace with caching and fallback mechanisms"""
    
    def __init__(self):
        self.base_url = "https://marketplace.dify.ai"
        self.api_base_url = "https://marketplace.dify.ai"  # Updated to match new API
        self.cache_prefix = "marketplace_scraper"
        self.cache_ttl = 3600  # 1 hour
        self.retry_count = 3
        self.retry_delay = 1  # seconds
        
    def _get_cache_key(self, key_type: str, **kwargs) -> str:
        """Generate consistent cache key"""
        params_str = json.dumps(kwargs, sort_keys=True)
        hash_key = hashlib.md5(params_str.encode()).hexdigest()
        return f"{self.cache_prefix}:{key_type}:{hash_key}"
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get data from Redis cache"""
        try:
            cached_data = redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None
    
    def _set_cache(self, key: str, data: Any, ttl: Optional[int] = None):
        """Set data in Redis cache with TTL"""
        try:
            ttl = ttl or self.cache_ttl
            redis_client.setex(key, ttl, json.dumps(data))
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    async def _make_request(self, url: str, method: str = "GET", **kwargs) -> Optional[httpx.Response]:
        """Make HTTP request with retry logic"""
        for attempt in range(self.retry_count):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    if method == "GET":
                        response = await client.get(url, **kwargs)
                    elif method == "POST":
                        response = await client.post(url, **kwargs)
                    else:
                        raise ValueError(f"Unsupported method: {method}")
                    
                    response.raise_for_status()
                    return response
                    
            except httpx.HTTPError as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.retry_count}): {e}")
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"All retry attempts failed for {url}")
        
        return None
    
    async def scrape_plugin_list(self, page: int = 1, per_page: int = 20, 
                                category: Optional[str] = None, 
                                query: Optional[str] = None) -> Dict:
        """Scrape plugin list from marketplace website"""
        cache_key = self._get_cache_key("scrape_list", page=page, per_page=per_page, 
                                       category=category, query=query)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Returning cached scraped plugin list")
            return cached_result
        
        try:
            # Build URL with query parameters
            params = {"page": page}
            if category:
                params["category"] = category
            if query:
                params["q"] = query
            
            url = f"{self.base_url}/plugins"
            response = await self._make_request(url, params=params)
            
            if not response:
                return {"plugins": [], "total": 0, "page": page, "per_page": per_page}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            plugins = []
            
            # Try different selectors based on common marketplace patterns
            plugin_selectors = [
                "div[class*='plugin-card']",
                "article[class*='plugin']",
                "div[class*='grid'] > div[class*='card']",
                "div[data-plugin]",
                "a[href*='/plugins/']"
            ]
            
            plugin_elements = []
            for selector in plugin_selectors:
                plugin_elements = soup.select(selector)
                if plugin_elements:
                    break
            
            for element in plugin_elements[:per_page]:
                plugin_data = self._extract_plugin_data(element, soup)
                if plugin_data:
                    plugins.append(plugin_data)
            
            # Try to extract total count
            total = len(plugins)
            pagination = soup.select_one("div[class*='pagination'], nav[aria-label='pagination']")
            if pagination:
                # Look for total pages or items
                total_text = pagination.get_text()
                numbers = re.findall(r'\d+', total_text)
                if numbers:
                    total = int(numbers[-1]) * per_page
            
            result = {
                "plugins": plugins,
                "total": total,
                "page": page,
                "per_page": per_page,
                "source": "scraper"
            }
            
            # Cache the result
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error scraping plugin list: {e}", exc_info=True)
            return {"plugins": [], "total": 0, "page": page, "per_page": per_page, "error": str(e)}
    
    def _extract_plugin_data(self, element, soup) -> Optional[Dict]:
        """Extract plugin data from HTML element"""
        try:
            plugin_data = {}
            
            # Extract plugin URL and parse author/name
            link = element.select_one("a[href*='/plugins/']")
            if not link:
                link = element if element.name == 'a' else element.find_parent('a')
            
            if link and link.get('href'):
                href = link['href']
                match = re.search(r'/plugins/([^/]+)/([^/?]+)', href)
                if match:
                    plugin_data['author'] = match.group(1)
                    plugin_data['name'] = match.group(2)
            
            # Extract display name
            name_selectors = ["h3", "h4", "[class*='title']", "[class*='name']"]
            for selector in name_selectors:
                name_elem = element.select_one(selector)
                if name_elem:
                    plugin_data['display_name'] = name_elem.get_text(strip=True)
                    break
            
            # Extract description
            desc_selectors = ["p", "[class*='description']", "[class*='desc']"]
            for selector in desc_selectors:
                desc_elem = element.select_one(selector)
                if desc_elem:
                    plugin_data['description'] = desc_elem.get_text(strip=True)
                    break
            
            # Extract category
            cat_selectors = ["[class*='category']", "[class*='tag']", "span.badge"]
            for selector in cat_selectors:
                cat_elem = element.select_one(selector)
                if cat_elem:
                    plugin_data['category'] = cat_elem.get_text(strip=True).lower()
                    break
            
            # Extract version
            ver_selectors = ["[class*='version']", "[class*='ver']"]
            for selector in ver_selectors:
                ver_elem = element.select_one(selector)
                if ver_elem:
                    ver_text = ver_elem.get_text(strip=True)
                    ver_match = re.search(r'(\d+\.\d+\.\d+)', ver_text)
                    if ver_match:
                        plugin_data['latest_version'] = ver_match.group(1)
                    break
            
            # Set defaults
            plugin_data.setdefault('display_name', plugin_data.get('name', 'Unknown'))
            plugin_data.setdefault('description', 'No description available')
            plugin_data.setdefault('category', 'other')
            plugin_data.setdefault('latest_version', '0.0.1')
            plugin_data.setdefault('tags', [])
            plugin_data.setdefault('created_at', datetime.now().isoformat())
            plugin_data.setdefault('updated_at', datetime.now().isoformat())
            
            # Only return if we have the essential fields
            if 'author' in plugin_data and 'name' in plugin_data:
                return plugin_data
                
        except Exception as e:
            logger.warning(f"Error extracting plugin data: {e}")
        
        return None
    
    async def scrape_plugin_details(self, author: str, name: str) -> Optional[Dict]:
        """Scrape detailed plugin information from plugin page"""
        cache_key = self._get_cache_key("scrape_details", author=author, name=name)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Returning cached scraped details for {author}/{name}")
            return cached_result
        
        try:
            url = f"{self.base_url}/plugins/{author}/{name}"
            response = await self._make_request(url)
            
            if not response:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract plugin details
            details = {
                "author": author,
                "name": name,
                "display_name": name,
                "description": "",
                "category": "other",
                "tags": [],
                "latest_version": "0.0.1",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Extract display name
            title_elem = soup.select_one("h1, h2, [class*='title']")
            if title_elem:
                details['display_name'] = title_elem.get_text(strip=True)
            
            # Extract description
            desc_elem = soup.select_one("[class*='description'], [class*='desc'], .readme")
            if desc_elem:
                details['description'] = desc_elem.get_text(strip=True)
            
            # Extract version info
            version_elem = soup.select_one("[class*='version'], select[name='version']")
            if version_elem:
                if version_elem.name == 'select':
                    # Get first option as latest version
                    first_option = version_elem.select_one('option')
                    if first_option:
                        details['latest_version'] = first_option.get_text(strip=True)
                else:
                    ver_text = version_elem.get_text(strip=True)
                    ver_match = re.search(r'(\d+\.\d+\.\d+)', ver_text)
                    if ver_match:
                        details['latest_version'] = ver_match.group(1)
            
            # Extract download link
            download_link = soup.select_one("a[href*='.difypkg'], a[href*='/download'], button[onclick*='download']")
            if download_link:
                details['download_url'] = urljoin(url, download_link.get('href', ''))
            
            # Cache the result
            self._set_cache(cache_key, details)
            return details
            
        except Exception as e:
            logger.error(f"Error scraping plugin details for {author}/{name}: {e}", exc_info=True)
            return None
    
    async def scrape_plugin_versions(self, author: str, name: str) -> List[Dict]:
        """Scrape available versions from plugin page"""
        cache_key = self._get_cache_key("scrape_versions", author=author, name=name)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Returning cached scraped versions for {author}/{name}")
            return cached_result
        
        try:
            url = f"{self.base_url}/plugins/{author}/{name}"
            response = await self._make_request(url)
            
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            versions = []
            
            # Look for version selector or list
            version_selectors = [
                "select[name='version'] option",
                "[class*='version-list'] li",
                "[class*='versions'] a",
                "[data-version]"
            ]
            
            version_elements = []
            for selector in version_selectors:
                version_elements = soup.select(selector)
                if version_elements:
                    break
            
            for elem in version_elements:
                ver_text = elem.get_text(strip=True)
                ver_match = re.search(r'(\d+\.\d+\.\d+)', ver_text)
                if ver_match:
                    version_info = {
                        "version": ver_match.group(1),
                        "created_at": datetime.now().isoformat(),
                        "changelog": ""
                    }
                    versions.append(version_info)
            
            # If no versions found, use the latest version from details
            if not versions:
                details = await self.scrape_plugin_details(author, name)
                if details and 'latest_version' in details:
                    versions = [{
                        "version": details['latest_version'],
                        "created_at": datetime.now().isoformat(),
                        "changelog": ""
                    }]
            
            # Cache the result
            self._set_cache(cache_key, versions)
            return versions
            
        except Exception as e:
            logger.error(f"Error scraping versions for {author}/{name}: {e}", exc_info=True)
            return []
    
    def extract_download_url(self, author: str, name: str, version: str) -> str:
        """Generate or extract download URL for a plugin version"""
        # Try known URL patterns
        patterns = [
            f"{self.base_url}/api/v1/plugins/{author}/{name}/{version}/download",
            f"{self.base_url}/plugins/{author}/{name}/download/{version}",
            f"{self.base_url}/downloads/{author}/{name}/{version}.difypkg"
        ]
        
        return patterns[0]  # Default to API pattern


class MarketplaceServiceWithFallback:
    """Enhanced marketplace service with fallback to web scraping"""
    
    def __init__(self):
        self.scraper = MarketplaceScraper()
        self.api_timeout = 10  # seconds
        
    async def search_plugins_with_fallback(
        self,
        query: Optional[str] = None,
        author: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict:
        """Search plugins with API fallback to web scraping"""
        
        # First try the API
        try:
            from app.services.marketplace import MarketplaceService
            result = await asyncio.wait_for(
                MarketplaceService.search_plugins(query, author, category, page, per_page),
                timeout=self.api_timeout
            )
            
            # Check if API returned valid results
            if result.get('plugins') or not result.get('error'):
                logger.info("Successfully fetched from API")
                return result
                
        except asyncio.TimeoutError:
            logger.warning("API request timed out, falling back to scraper")
        except Exception as e:
            logger.warning(f"API request failed: {e}, falling back to scraper")
        
        # Fallback to web scraping
        logger.info("Using web scraper for plugin search")
        scraped_result = await self.scraper.scrape_plugin_list(page, per_page, category, query)
        
        # Add fallback indicator
        scraped_result['fallback_used'] = True
        scraped_result['fallback_reason'] = 'API unavailable or returned no results'
        
        return scraped_result
    
    async def get_plugin_details_with_fallback(self, author: str, name: str) -> Optional[Dict]:
        """Get plugin details with fallback to web scraping"""
        
        # First try the API
        try:
            from app.services.marketplace import MarketplaceService
            result = await asyncio.wait_for(
                MarketplaceService.get_plugin_details(author, name),
                timeout=self.api_timeout
            )
            
            if result:
                logger.info(f"Successfully fetched details from API for {author}/{name}")
                return result
                
        except asyncio.TimeoutError:
            logger.warning(f"API request timed out for {author}/{name}, falling back to scraper")
        except Exception as e:
            logger.warning(f"API request failed for {author}/{name}: {e}, falling back to scraper")
        
        # Fallback to web scraping
        logger.info(f"Using web scraper for plugin details: {author}/{name}")
        return await self.scraper.scrape_plugin_details(author, name)
    
    async def get_plugin_versions_with_fallback(self, author: str, name: str) -> List[Dict]:
        """Get plugin versions with fallback to web scraping"""
        
        # First try the API
        try:
            from app.services.marketplace import MarketplaceService
            result = await asyncio.wait_for(
                MarketplaceService.get_plugin_versions(author, name),
                timeout=self.api_timeout
            )
            
            if result:
                logger.info(f"Successfully fetched versions from API for {author}/{name}")
                return result
                
        except asyncio.TimeoutError:
            logger.warning(f"API request timed out for versions of {author}/{name}, falling back to scraper")
        except Exception as e:
            logger.warning(f"API request failed for versions of {author}/{name}: {e}, falling back to scraper")
        
        # Fallback to web scraping
        logger.info(f"Using web scraper for plugin versions: {author}/{name}")
        return await self.scraper.scrape_plugin_versions(author, name)
    
    def build_download_url_with_fallback(self, author: str, name: str, version: str) -> str:
        """Build download URL with fallback patterns"""
        from app.services.marketplace import MarketplaceService
        
        # First try the standard API pattern
        primary_url = MarketplaceService.build_download_url(author, name, version)
        
        # Return primary URL - actual fallback happens during download
        return primary_url
    
    async def get_cached_data(self, key_type: str, **kwargs) -> Optional[Any]:
        """Get any cached data by type"""
        cache_key = self.scraper._get_cache_key(key_type, **kwargs)
        return self.scraper._get_from_cache(cache_key)
    
    def invalidate_cache(self, key_type: Optional[str] = None, **kwargs):
        """Invalidate cache entries"""
        if key_type:
            cache_key = self.scraper._get_cache_key(key_type, **kwargs)
            try:
                redis_client.delete(cache_key)
                logger.info(f"Invalidated cache for {cache_key}")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache: {e}")
        else:
            # Clear all scraper cache
            pattern = f"{self.scraper.cache_prefix}:*"
            try:
                for key in redis_client.scan_iter(match=pattern):
                    redis_client.delete(key)
                logger.info("Invalidated all scraper cache")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache: {e}")


# Create a singleton instance
marketplace_fallback_service = MarketplaceServiceWithFallback()