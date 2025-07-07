from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.services.marketplace import MarketplaceService
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
        return {"categories": categories}
        
    except Exception as e:
        logger.exception("Error getting categories")
        raise HTTPException(status_code=500, detail=str(e))


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