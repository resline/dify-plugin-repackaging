from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from app.services.marketplace import MarketplaceService
from app.utils.circuit_breaker import marketplace_circuit_breaker
import logging
import json

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
            
        # Ensure response is JSON with proper content type
        return JSONResponse(
            content=result,
            headers={"Content-Type": "application/json"}
        )
        
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
        
        # Return as JSON response
        return JSONResponse(
            content=plugin,
            headers={"Content-Type": "application/json"}
        )
        
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
        
        return JSONResponse(
            content={"versions": versions},
            headers={"Content-Type": "application/json"}
        )
        
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
        
        return JSONResponse(
            content={"categories": categories},
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.exception("Error getting categories")
        # Return default categories instead of error
        return JSONResponse(
            content={"categories": ["agent", "tool", "model", "extension", "workflow"]},
            headers={"Content-Type": "application/json"}
        )


@router.get("/marketplace/plugins/featured")
async def get_featured_plugins(
    limit: int = Query(6, ge=1, le=20, description="Number of featured plugins to return")
):
    """
    Get featured or recommended plugins from the marketplace
    
    This endpoint returns a curated list of popular or recommended plugins.
    Currently returns the most popular plugins based on search results.
    
    Parameters:
    - **limit**: Number of featured plugins to return (1-20, default: 6)
    
    Returns:
    - Same format as the search endpoint but with featured plugins
    """
    try:
        # For now, return popular/verified plugins
        # In a real implementation, this could be a curated list
        result = await MarketplaceService.search_plugins(
            page=1,
            per_page=limit
        )
        
        # If we have plugins, filter for verified ones or popular categories
        if result.get("plugins"):
            plugins = result["plugins"]
            
            # Prioritize verified plugins or specific popular authors
            popular_authors = ["langgenius", "dify", "community"]
            featured_plugins = []
            
            # First add verified or popular author plugins
            for plugin in plugins:
                if (plugin.get("verified") or 
                    plugin.get("author") in popular_authors or
                    plugin.get("download_count", 0) > 100):
                    featured_plugins.append(plugin)
            
            # If not enough, add the rest
            for plugin in plugins:
                if plugin not in featured_plugins and len(featured_plugins) < limit:
                    featured_plugins.append(plugin)
            
            result["plugins"] = featured_plugins[:limit]
            result["total"] = len(featured_plugins)
            result["featured"] = True
        
        return JSONResponse(
            content=result,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.exception("Error getting featured plugins")
        # Fallback to regular search
        try:
            result = await MarketplaceService.search_plugins(page=1, per_page=limit)
            result["featured"] = False
            return JSONResponse(
                content=result,
                headers={"Content-Type": "application/json"}
            )
        except:
            raise HTTPException(status_code=500, detail=str(e))


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
            return JSONResponse(
                content=json.loads(cached_authors),
                headers={"Content-Type": "application/json"}
            )
        
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
        
        return JSONResponse(
            content=response,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.exception("Error getting authors")
        # Return some default authors instead of empty list
        return JSONResponse(
            content={"authors": ['langgenius', 'dify', 'community']},
            headers={"Content-Type": "application/json"}
        )


@router.post("/marketplace/plugins/{author}/{name}/{version}/download-url")
async def get_download_url(author: str, name: str, version: str):
    """
    Get the download URL for a specific plugin version
    
    This endpoint constructs the download URL without making an API call.
    The actual download will be handled by the existing task creation flow.
    """
    try:
        download_url = MarketplaceService.construct_download_url(author, name, version)
        
        return JSONResponse(
            content={
                "download_url": download_url,
                "plugin": {
                    "author": author,
                    "name": name,
                    "version": version
                }
            },
            headers={"Content-Type": "application/json"}
        )
        
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
            
            return JSONResponse(
                content={
                    "valid": True,
                    "author": author,
                    "name": name,
                    "latest_version": latest_version,
                    "download_url": MarketplaceService.construct_download_url(author, name, latest_version) if latest_version else None
                },
                headers={"Content-Type": "application/json"}
            )
        else:
            return JSONResponse(
                content={
                    "valid": False,
                    "error": "Not a valid marketplace plugin URL",
                    "expected_format": "https://marketplace.dify.ai/plugins/{author}/{name}"
                },
                headers={"Content-Type": "application/json"}
            )
            
    except Exception as e:
        logger.exception(f"Error parsing marketplace URL: {url}")
        return JSONResponse(
            content={
                "valid": False,
                "error": str(e)
            },
            headers={"Content-Type": "application/json"}
        )


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
        
        return JSONResponse(
            content={
                "marketplace_api": {
                    "status": api_status,
                    "error": api_error
                },
                "circuit_breaker": circuit_state,
                "recommendations": {
                    "circuit_open": "Wait for automatic recovery or manually reset",
                    "api_error": "Check marketplace URL and network connectivity"
                } if circuit_state["state"] == "open" or api_status == "error" else None
            },
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.exception("Error checking marketplace status")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/marketplace/reset-circuit-breaker")
async def reset_circuit_breaker():
    """Manually reset the marketplace circuit breaker"""
    try:
        marketplace_circuit_breaker.reset()
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Circuit breaker has been reset",
                "circuit_state": marketplace_circuit_breaker.get_state()
            },
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.exception("Error resetting circuit breaker")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/marketplace/debug")
async def debug_marketplace():
    """Debug endpoint to test marketplace connectivity and responses"""
    debug_info = {
        "circuit_breaker": marketplace_circuit_breaker.get_state(),
        "tests": {}
    }
    
    # Test 1: Direct API call
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://marketplace.dify.ai/api/v1/categories",
                headers={"Accept": "application/json"}
            )
            debug_info["tests"]["direct_api_call"] = {
                "status": response.status_code,
                "content_type": response.headers.get("content-type", "Not set"),
                "is_json": "application/json" in response.headers.get("content-type", ""),
                "response_preview": response.text[:200] if response.text else "Empty"
            }
    except Exception as e:
        debug_info["tests"]["direct_api_call"] = {
            "error": str(e),
            "type": type(e).__name__
        }
    
    # Test 2: Service method
    try:
        result = await MarketplaceService.search_plugins(page=1, per_page=1)
        debug_info["tests"]["service_search"] = {
            "success": True,
            "has_plugins": bool(result.get("plugins")),
            "plugin_count": len(result.get("plugins", [])),
            "has_error": "error" in result,
            "fallback_used": result.get("fallback_used", False)
        }
    except Exception as e:
        debug_info["tests"]["service_search"] = {
            "success": False,
            "error": str(e),
            "type": type(e).__name__
        }
    
    # Test 3: Check fallback
    try:
        from app.services.marketplace_scraper import marketplace_fallback_service
        debug_info["tests"]["fallback_available"] = True
    except:
        debug_info["tests"]["fallback_available"] = False
    
    return JSONResponse(
        content=debug_info,
        headers={"Content-Type": "application/json"}
    )