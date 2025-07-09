from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.services.marketplace import MarketplaceService
from app.utils.circuit_breaker import marketplace_circuit_breaker
import logging

logger = logging.getLogger(__name__)

# Create router without prefix - it will be added when included in main app
router = APIRouter(tags=["marketplace"])


@router.get("/marketplace/plugins")
async def search_plugins(
    q: Optional[str] = Query(None, description="Search query"),
    author: Optional[str] = Query(None, description="Filter by author"),
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page")
):
    """
    Search for plugins in the Dify Marketplace
    
    Query parameters:
    - **q**: Search query string (searches name, description, tags)
    - **author**: Filter by specific author username
    - **category**: Filter by category (tool, model, agent, extension, workflow)
    - **page**: Page number for pagination (default: 1)
    - **per_page**: Results per page, max 100 (default: 20)
    
    Example responses:
    ```json
    {
        "plugins": [
            {
                "name": "agent",
                "author": "langgenius", 
                "display_name": "Agent Plugin",
                "description": "Enables agent capabilities",
                "category": "agent",
                "tags": ["agent", "llm"],
                "latest_version": "0.0.9",
                "icon_url": "https://...",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T00:00:00Z",
                "download_count": 1234,
                "rating": 4.5,
                "verified": true
            }
        ],
        "total": 25,
        "page": 1,
        "per_page": 20,
        "has_more": true
    }
    ```
    
    Returns:
    - **plugins**: List of plugin metadata objects
    - **total**: Total number of matching plugins
    - **page**: Current page number
    - **per_page**: Results per page
    - **has_more**: Whether more pages are available
    """
    try:
        result = await MarketplaceService.search_plugins(
            query=q,
            author=author,
            category=category,
            page=page,
            per_page=per_page
        )
        
        if "error" in result:
            logger.warning(f"Marketplace search returned error: {result['error']}")
            
        return result
        
    except Exception as e:
        logger.exception("Error searching marketplace")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/marketplace/plugins/{author}/{name}")
async def get_plugin_details(author: str, name: str):
    """
    Get detailed information about a specific plugin
    
    Returns plugin metadata including:
    - name, author, description
    - latest_version
    - available_versions
    - category, tags
    """
    try:
        plugin = await MarketplaceService.get_plugin_details(author, name)
        
        if not plugin:
            raise HTTPException(
                status_code=404,
                detail=f"Plugin {author}/{name} not found"
            )
        
        return plugin
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting plugin details for {author}/{name}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/marketplace/plugins/{author}/{name}/versions")
async def get_plugin_versions(author: str, name: str):
    """
    Get all available versions for a plugin
    
    Returns list of version objects with:
    - version: Version string
    - created_at: Release date
    - changelog: Version changelog (if available)
    """
    try:
        versions = await MarketplaceService.get_plugin_versions(author, name)
        
        if not versions:
            raise HTTPException(
                status_code=404,
                detail=f"No versions found for plugin {author}/{name}"
            )
        
        return {"versions": versions}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting versions for {author}/{name}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/marketplace/categories")
async def get_categories():
    """Get list of available plugin categories"""
    try:
        categories = await MarketplaceService.get_categories()
        
        # Ensure categories is always a list
        if not isinstance(categories, list):
            categories = ["agent", "tool", "model", "extension", "workflow"]
        
        return {"categories": categories}
        
    except Exception as e:
        logger.exception("Error getting categories")
        # Return default categories instead of error
        return {"categories": ["agent", "tool", "model", "extension", "workflow"]}


@router.get("/marketplace/authors")
async def get_authors():
    """Get list of unique plugin authors from marketplace"""
    try:
        # Try to get from cache first
        from app.workers.celery_app import redis_client
        import json
        
        cache_key = "marketplace:authors_list"
        cached_authors = redis_client.get(cache_key)
        if cached_authors:
            return json.loads(cached_authors)
        
        # Get first page of plugins with max results to extract authors
        result = await MarketplaceService.search_plugins(page=1, per_page=100)
        
        # Handle both successful and fallback responses
        plugins = result.get('plugins', [])
        
        # Extract unique authors
        authors = list(set(plugin.get('author', '') for plugin in plugins if plugin.get('author')))
        authors.sort()
        
        # Add some common known authors if list is too small
        if len(authors) < 5:
            known_authors = ['langgenius', 'dify', 'community']
            for author in known_authors:
                if author not in authors:
                    authors.append(author)
            authors.sort()
        
        response = {"authors": authors}
        
        # Cache the result for 1 hour
        redis_client.setex(cache_key, 3600, json.dumps(response))
        
        return response
        
    except Exception as e:
        logger.exception("Error getting authors")
        # Return some default authors instead of empty list
        return {"authors": ['langgenius', 'dify', 'community']}


@router.post("/marketplace/plugins/{author}/{name}/{version}/download-url")
async def get_download_url(author: str, name: str, version: str):
    """
    Get the download URL for a specific plugin version
    
    This endpoint constructs the download URL without making an API call.
    The actual download will be handled by the existing task creation flow.
    """
    try:
        download_url = MarketplaceService.construct_download_url(author, name, version)
        
        return {
            "download_url": download_url,
            "plugin": {
                "author": author,
                "name": name,
                "version": version
            }
        }
        
    except Exception as e:
        logger.exception(f"Error building download URL for {author}/{name}/{version}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/marketplace/parse-url")
async def parse_marketplace_url(
    url: str = Query(..., description="Marketplace URL to parse")
):
    """
    Parse a marketplace URL to extract plugin information
    
    This endpoint helps debug URL parsing issues and can be used to validate
    marketplace URLs before processing.
    
    Example:
    - Input: https://marketplace.dify.ai/plugins/langgenius/ollama
    - Output: {"author": "langgenius", "name": "ollama", "valid": true}
    """
    try:
        # Parse the URL
        parsed = MarketplaceService.parse_marketplace_url(url)
        
        if parsed:
            author, name = parsed
            # Try to get the latest version
            latest_version = await MarketplaceService.get_latest_version(author, name)
            
            return {
                "valid": True,
                "author": author,
                "name": name,
                "latest_version": latest_version,
                "download_url": MarketplaceService.construct_download_url(author, name, latest_version) if latest_version else None
            }
        else:
            return {
                "valid": False,
                "error": "Not a valid marketplace plugin URL",
                "expected_format": "https://marketplace.dify.ai/plugins/{author}/{name}"
            }
            
    except Exception as e:
        logger.exception(f"Error parsing marketplace URL: {url}")
        return {
            "valid": False,
            "error": str(e)
        }


@router.get("/marketplace/status")
async def get_marketplace_status():
    """Get the current status of the marketplace API and circuit breaker"""
    try:
        circuit_state = marketplace_circuit_breaker.get_state()
        
        # Try a simple API call to check if marketplace is accessible
        api_status = "unknown"
        api_error = None
        
        try:
            # Quick check with minimal impact
            result = await MarketplaceService.search_plugins(page=1, per_page=1)
            if result.get("plugins") is not None:
                api_status = "operational"
            elif result.get("fallback_used"):
                api_status = "degraded"
                api_error = result.get("fallback_reason", "Using fallback")
            else:
                api_status = "error"
                api_error = result.get("error", "Unknown error")
        except Exception as e:
            api_status = "error"
            api_error = str(e)
        
        return {
            "marketplace_api": {
                "status": api_status,
                "error": api_error
            },
            "circuit_breaker": circuit_state,
            "recommendations": {
                "circuit_open": "Wait for automatic recovery or manually reset",
                "api_error": "Check marketplace URL and network connectivity"
            } if circuit_state["state"] == "open" or api_status == "error" else None
        }
        
    except Exception as e:
        logger.exception("Error checking marketplace status")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/marketplace/reset-circuit-breaker")
async def reset_circuit_breaker():
    """Manually reset the marketplace circuit breaker"""
    try:
        marketplace_circuit_breaker.reset()
        
        return {
            "status": "success",
            "message": "Circuit breaker has been reset",
            "circuit_state": marketplace_circuit_breaker.get_state()
        }
        
    except Exception as e:
        logger.exception("Error resetting circuit breaker")
        raise HTTPException(status_code=500, detail=str(e))