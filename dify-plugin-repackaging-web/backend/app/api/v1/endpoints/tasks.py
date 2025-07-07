from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from app.models.task import TaskCreate, TaskResponse, TaskStatus, MarketplaceTaskCreate
from app.workers.celery_app import process_repackaging, process_marketplace_repackaging, redis_client
from app.core.config import settings
from app.services.marketplace import MarketplaceService
from pydantic import BaseModel, Field
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uuid
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create router without prefix - it will be added when included in main app
router = APIRouter(tags=["tasks"])


class TaskCreateWithMarketplace(BaseModel):
    """Task creation with optional marketplace plugin fields"""
    url: Optional[str] = Field(None, description="Direct URL to the .difypkg file")
    marketplace_plugin: Optional[dict] = Field(
        None, 
        description="Marketplace plugin info with author, name, and version",
        example={"author": "langgenius", "name": "agent", "version": "0.0.9"}
    )
    platform: str = Field("", description="Target platform for repackaging")
    suffix: str = Field("offline", description="Suffix for the output file")


@router.post("/tasks", response_model=TaskResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def create_task(request: Request, task_data: TaskCreateWithMarketplace):
    """
    Create a new repackaging task
    
    This endpoint supports two modes:
    
    1. **Direct URL mode** - Provide a URL to a .difypkg file:
    ```json
    {
        "url": "https://example.com/plugin.difypkg",
        "platform": "manylinux2014_x86_64",
        "suffix": "offline"
    }
    ```
    
    2. **Marketplace mode** - Specify a plugin from Dify Marketplace:
    ```json
    {
        "marketplace_plugin": {
            "author": "langgenius",
            "name": "agent",
            "version": "0.0.9"
        },
        "platform": "manylinux2014_x86_64",
        "suffix": "offline"
    }
    ```
    
    Parameters:
    - **url**: Direct URL to the .difypkg file (required if marketplace_plugin not provided)
    - **marketplace_plugin**: Plugin information from marketplace (required if url not provided)
    - **platform**: Target platform for repackaging (optional, defaults to auto-detect)
    - **suffix**: Suffix for output file (optional, defaults to "offline")
    
    Returns:
    - Task ID and initial status for tracking the repackaging progress
    
    The task will include marketplace metadata in WebSocket updates when using marketplace mode.
    """
    try:
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Determine download URL
        if task_data.marketplace_plugin:
            # Auto-construct URL from marketplace plugin info
            if not all(k in task_data.marketplace_plugin for k in ["author", "name", "version"]):
                raise HTTPException(
                    status_code=400,
                    detail="marketplace_plugin must contain author, name, and version"
                )
            
            download_url = MarketplaceService.construct_download_url(
                task_data.marketplace_plugin["author"],
                task_data.marketplace_plugin["name"],
                task_data.marketplace_plugin["version"]
            )
            
            plugin_info = task_data.marketplace_plugin
        elif task_data.url:
            # Check if it's a marketplace URL without version
            marketplace_info = MarketplaceService.parse_marketplace_url(task_data.url)
            
            if marketplace_info:
                # It's a marketplace URL - extract author and name
                author, name = marketplace_info
                
                # Get the latest version
                latest_version = await MarketplaceService.get_latest_version(author, name)
                
                if not latest_version:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Could not find plugin {author}/{name} in marketplace or unable to determine latest version"
                    )
                
                # Build download URL with latest version
                download_url = MarketplaceService.construct_download_url(author, name, latest_version)
                
                # Set plugin info for metadata
                plugin_info = {
                    "author": author,
                    "name": name,
                    "version": latest_version
                }
                
                logger.info(f"Resolved marketplace URL to: {author}/{name} v{latest_version}")
            else:
                # Regular direct URL
                download_url = task_data.url
                
                # Validate URL
                if not download_url.endswith('.difypkg'):
                    raise HTTPException(
                        status_code=400,
                        detail="URL must point to a .difypkg file or be a valid marketplace plugin URL"
                    )
                
                plugin_info = None
        else:
            raise HTTPException(
                status_code=400,
                detail="Either url or marketplace_plugin must be provided"
            )
        
        # Create initial task record
        task_record = {
            "task_id": task_id,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "url": download_url,
            "platform": task_data.platform,
            "suffix": task_data.suffix,
            "progress": 0
        }
        
        if plugin_info:
            task_record["plugin_info"] = plugin_info
        
        # Store in Redis
        redis_client.setex(
            f"task:{task_id}",
            settings.FILE_RETENTION_HOURS * 3600,
            json.dumps(task_record)
        )
        
        # Queue the task
        if plugin_info:
            # Use marketplace-aware task
            marketplace_metadata = {
                "source": "marketplace",
                "author": plugin_info["author"],
                "name": plugin_info["name"],
                "version": plugin_info["version"]
            }
            
            process_marketplace_repackaging.delay(
                task_id,
                plugin_info["author"],
                plugin_info["name"],
                plugin_info["version"],
                task_data.platform,
                task_data.suffix,
                marketplace_metadata
            )
        else:
            # Use regular task for backward compatibility
            process_repackaging.delay(
                task_id,
                download_url,
                task_data.platform,
                task_data.suffix
            )
        
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            progress=0
        )
        
    except RateLimitExceeded:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creating task")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/marketplace", response_model=TaskResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def create_marketplace_task(request: Request, task_data: MarketplaceTaskCreate):
    """
    Create a new repackaging task from marketplace plugin
    
    This is a convenience endpoint specifically for marketplace plugins.
    
    Example request:
    ```json
    {
        "author": "langgenius",
        "name": "agent",
        "version": "0.0.9",
        "platform": "manylinux2014_x86_64",
        "suffix": "offline"
    }
    ```
    
    Parameters:
    - **author**: Plugin author username from marketplace
    - **name**: Plugin name identifier  
    - **version**: Specific version to download
    - **platform**: Target platform for repackaging (optional)
    - **suffix**: Suffix for output file (optional, defaults to "offline")
    
    Returns:
    - Task ID and initial status
    
    All tasks created through this endpoint will include marketplace metadata in their WebSocket updates.
    """
    try:
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Build download URL
        download_url = MarketplaceService.construct_download_url(
            task_data.author,
            task_data.name,
            task_data.version
        )
        
        # Create initial task record
        task_record = {
            "task_id": task_id,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "url": download_url,
            "platform": task_data.platform.value,
            "suffix": task_data.suffix,
            "progress": 0,
            "plugin_info": {
                "author": task_data.author,
                "name": task_data.name,
                "version": task_data.version
            }
        }
        
        # Store in Redis
        redis_client.setex(
            f"task:{task_id}",
            settings.FILE_RETENTION_HOURS * 3600,
            json.dumps(task_record)
        )
        
        # Queue the task with marketplace metadata
        marketplace_metadata = {
            "source": "marketplace",
            "author": task_data.author,
            "name": task_data.name,
            "version": task_data.version
        }
        
        process_marketplace_repackaging.delay(
            task_id,
            task_data.author,
            task_data.name,
            task_data.version,
            task_data.platform.value,
            task_data.suffix,
            marketplace_metadata
        )
        
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            progress=0
        )
        
    except RateLimitExceeded:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    except Exception as e:
        logger.exception("Error creating marketplace task")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """Get the status of a repackaging task"""
    # Get task from Redis
    task_data = redis_client.get(f"task:{task_id}")
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = json.loads(task_data)
    
    # Add download URL if task is completed
    download_url = None
    if task.get("status") == TaskStatus.COMPLETED.value and task.get("output_filename"):
        download_url = f"{settings.API_V1_STR}/tasks/{task_id}/download"
    
    return TaskResponse(
        task_id=task["task_id"],
        status=TaskStatus(task["status"]),
        created_at=datetime.fromisoformat(task["created_at"]),
        updated_at=datetime.fromisoformat(task["updated_at"]) if task.get("updated_at") else None,
        completed_at=datetime.fromisoformat(task["completed_at"]) if task.get("completed_at") else None,
        error=task.get("error"),
        progress=task.get("progress", 0),
        download_url=download_url,
        original_filename=task.get("original_filename"),
        output_filename=task.get("output_filename")
    )


@router.get("/tasks/{task_id}/download")
async def download_result(task_id: str):
    """Download the repackaged plugin file"""
    # Get task from Redis
    task_data = redis_client.get(f"task:{task_id}")
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = json.loads(task_data)
    
    # Check if task is completed
    if task.get("status") != TaskStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Task is not completed. Current status: {task.get('status')}"
        )
    
    # Check if output file exists
    output_filename = task.get("output_filename")
    if not output_filename:
        raise HTTPException(status_code=404, detail="Output file not found")
    
    # Build file path
    file_path = os.path.join(settings.TEMP_DIR, task_id, output_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=output_filename
    )


@router.get("/tasks")
async def list_recent_tasks(limit: int = 10):
    """List recent tasks (for demo purposes)"""
    # This is a simple implementation - in production, you'd want proper storage
    keys = redis_client.keys("task:*")
    tasks = []
    
    for key in keys[:limit]:
        task_data = redis_client.get(key)
        if task_data:
            task = json.loads(task_data)
            tasks.append({
                "task_id": task["task_id"],
                "status": task["status"],
                "created_at": task["created_at"],
                "progress": task.get("progress", 0),
                "plugin_info": task.get("plugin_info")
            })
    
    # Sort by created_at
    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {"tasks": tasks[:limit]}