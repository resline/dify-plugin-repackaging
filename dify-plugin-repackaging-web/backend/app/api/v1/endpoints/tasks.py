from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from app.models.task import TaskCreate, TaskResponse, TaskStatus, MarketplaceTaskCreate
from app.workers.celery_app import process_repackaging, process_marketplace_repackaging, redis_client
from app.core.config import settings
from app.services.marketplace import MarketplaceService
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uuid
import json
import os
import shutil
from datetime import datetime, timezone
import logging
import re

logger = logging.getLogger(__name__)


def validate_task_id(task_id: str) -> str:
    """Validate task_id is a valid UUID format to prevent path traversal."""
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    if not uuid_pattern.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    return task_id


# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create router without prefix - it will be added when included in main app
router = APIRouter(tags=["tasks"])


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and command injection.

    Args:
        filename: The original filename

    Returns:
        Sanitized filename safe for use in file operations

    Raises:
        ValueError: If filename is invalid or unsafe
    """
    if not filename:
        raise ValueError("Filename cannot be empty")

    # Use basename to strip any path components (prevents path traversal)
    safe_filename = os.path.basename(filename)

    # Replace any characters not matching [a-zA-Z0-9._-] with underscore
    safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', safe_filename)

    # Ensure filename is not empty after sanitization
    if not safe_filename or safe_filename in ('.', '..'):
        raise ValueError("Invalid filename after sanitization")

    # Ensure the filename ends with .difypkg
    if not safe_filename.endswith('.difypkg'):
        # If it was stripped, add it back
        if '.difypkg' in filename:
            safe_filename = safe_filename + '.difypkg'
        else:
            raise ValueError("Filename must end with .difypkg extension")

    return safe_filename


def validate_platform(platform: str) -> str:
    """
    Validate platform parameter against whitelist.

    Args:
        platform: Platform string to validate

    Returns:
        Validated platform string

    Raises:
        ValueError: If platform is not in whitelist
    """
    allowed_platforms = {
        "",  # Empty string for default
        "manylinux2014_x86_64",
        "manylinux2014_aarch64",
        "manylinux_2_17_x86_64",
        "manylinux_2_17_aarch64",
        "macosx_10_9_x86_64",
        "macosx_11_0_arm64"
    }

    if platform not in allowed_platforms:
        raise ValueError(
            f"Invalid platform '{platform}'. Must be one of: {', '.join(sorted(p for p in allowed_platforms if p))}"
        )

    return platform


def validate_suffix(suffix: str) -> str:
    """
    Validate suffix parameter to prevent command injection.

    Args:
        suffix: Suffix string to validate

    Returns:
        Validated suffix string

    Raises:
        ValueError: If suffix contains invalid characters or is too long
    """
    if not suffix:
        raise ValueError("Suffix cannot be empty")

    if len(suffix) > 50:
        raise ValueError("Suffix must be 50 characters or less")

    if not re.match(r'^[a-zA-Z0-9_-]+$', suffix):
        raise ValueError("Suffix can only contain alphanumeric characters, underscores, and hyphens")

    return suffix


def validate_task_path(task_dir: str, file_path: str) -> str:
    """
    Validate that a file path stays within the task directory (prevents path traversal).

    Args:
        task_dir: The base task directory
        file_path: The file path to validate

    Returns:
        The resolved absolute path

    Raises:
        ValueError: If path traversal is detected
    """
    # Get absolute paths
    abs_task_dir = os.path.abspath(task_dir)
    abs_file_path = os.path.abspath(file_path)

    # Check if the file path is within the task directory
    if not abs_file_path.startswith(abs_task_dir + os.sep):
        raise ValueError("Path traversal detected: file path must be within task directory")

    return abs_file_path


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

    @field_validator('platform')
    @classmethod
    def validate_platform_field(cls, v: str) -> str:
        """Validate platform against whitelist"""
        return validate_platform(v)

    @field_validator('suffix')
    @classmethod
    def validate_suffix_field(cls, v: str) -> str:
        """Validate suffix to prevent command injection"""
        return validate_suffix(v)


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
        # Log request data for debugging
        logger.info(f"Create task request: url={task_data.url}, marketplace_plugin={task_data.marketplace_plugin}")
        
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
            logger.info(f"Checking if URL is a marketplace URL: {task_data.url}")
            marketplace_info = MarketplaceService.parse_marketplace_url(task_data.url)
            
            if marketplace_info:
                logger.info(f"Marketplace URL detected: {marketplace_info}")
                # It's a marketplace URL - extract author and name
                author, name = marketplace_info
                
                # Get the latest version
                latest_version = await MarketplaceService.get_latest_version(author, name)
                
                if not latest_version:
                    # Try to provide more specific error message
                    error_detail = (
                        f"Unable to fetch plugin version for {author}/{name}. "
                        f"Possible reasons:\n"
                        f"1. The plugin may not exist in the marketplace\n"
                        f"2. The marketplace API may be temporarily unavailable\n"
                        f"3. The plugin URL format may have changed\n\n"
                        f"Please verify the URL is correct or try using a direct .difypkg file URL instead.\n"
                        f"Example marketplace URL: https://marketplace.dify.ai/plugins/langgenius/ollama"
                    )
                    logger.error(f"Failed to get latest version for marketplace URL: {task_data.url}")
                    raise HTTPException(
                        status_code=503,
                        detail=error_detail
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
                logger.info(f"Not a marketplace URL, treating as direct download: {task_data.url}")
                download_url = task_data.url
                
                # Validate URL
                if not download_url.endswith('.difypkg'):
                    raise HTTPException(
                        status_code=400,
                        detail="URL must point to a .difypkg file or be a valid marketplace plugin URL (e.g., https://marketplace.dify.ai/plugins/author/name)"
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
            "created_at": datetime.now(timezone.utc).isoformat(),
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
            created_at=datetime.now(timezone.utc),
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
        error_msg = getattr(e, 'message', str(e)) if hasattr(e, 'message') else str(type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Internal server error: {error_msg}")


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
            "created_at": datetime.now(timezone.utc).isoformat(),
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
            created_at=datetime.now(timezone.utc),
            progress=0
        )
        
    except RateLimitExceeded:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    except Exception as e:
        logger.exception("Error creating marketplace task")
        error_msg = getattr(e, 'message', str(e)) if hasattr(e, 'message') else str(type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Internal server error: {error_msg}")


@router.post("/tasks/upload", response_model=TaskResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def upload_task(
    request: Request,
    file: UploadFile = File(...),
    platform: str = Form(""),
    suffix: str = Form("offline")
):
    """
    Create a new repackaging task by uploading a .difypkg file

    This endpoint allows you to upload a .difypkg file directly from your computer
    for repackaging with offline dependencies.

    Parameters:
    - **file**: The .difypkg file to upload (required)
    - **platform**: Target platform for repackaging (optional, defaults to auto-detect)
    - **suffix**: Suffix for output file (optional, defaults to "offline")

    File restrictions:
    - Must have .difypkg extension
    - Maximum size: 100MB

    Returns:
    - Task ID and initial status for tracking the repackaging progress
    """
    try:
        # Validate platform and suffix parameters
        try:
            platform = validate_platform(platform)
            suffix = validate_suffix(suffix)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Validate and sanitize filename
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Filename cannot be empty"
            )

        try:
            safe_filename = sanitize_filename(file.filename)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid filename: {str(e)}"
            )

        # Check file size (100MB limit)
        file.file.seek(0, 2)  # Move to end of file
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning

        if file_size > 100 * 1024 * 1024:  # 100MB
            raise HTTPException(
                status_code=400,
                detail="File size must be less than 100MB"
            )

        # Generate task ID
        task_id = str(uuid.uuid4())

        # Create task directory
        task_dir = os.path.join(settings.TEMP_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)

        # Save uploaded file with sanitized filename
        file_path = os.path.join(task_dir, safe_filename)

        # Validate path to prevent traversal
        try:
            file_path = validate_task_path(task_dir, file_path)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file path: {str(e)}"
            )

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create initial task record
        task_record = {
            "task_id": task_id,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "url": f"file://{file_path}",
            "platform": platform,
            "suffix": suffix,
            "progress": 0,
            "original_filename": safe_filename,
            "upload_info": {
                "source": "upload",
                "filename": safe_filename,
                "size": file_size
            }
        }
        
        # Store in Redis
        redis_client.setex(
            f"task:{task_id}",
            settings.FILE_RETENTION_HOURS * 3600,
            json.dumps(task_record)
        )
        
        # Queue the task - using local file path
        process_repackaging.delay(
            task_id,
            file_path,  # Use local file path instead of URL
            platform,
            suffix,
            is_local_file=True  # Flag to indicate it's a local file
        )
        
        logger.info(f"Created upload task {task_id} for file {safe_filename}")
        
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            progress=0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creating upload task")
        error_msg = getattr(e, 'message', str(e)) if hasattr(e, 'message') else str(type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Internal server error: {error_msg}")




@router.get("/tasks/completed")
async def list_completed_tasks(limit: int = Query(default=10, ge=1, le=100)):
    """
    List completed tasks with their download information
    
    This endpoint returns only tasks that have completed successfully and have
    downloadable files available.
    
    Parameters:
    - **limit**: Maximum number of tasks to return (1-100, default: 10)
    
    Returns:
    - List of completed tasks with download URLs
    """
    try:
        # Get all task keys from Redis
        keys = list(redis_client.scan_iter("task:*"))
        completed_tasks = []
        
        for key in keys:
            task_data = redis_client.get(key)
            if task_data:
                task = json.loads(task_data)
                
                # Only include completed tasks
                if task.get("status") == TaskStatus.COMPLETED.value and task.get("output_filename"):
                    # Check if the output file still exists
                    file_path = os.path.join(settings.TEMP_DIR, task["task_id"], task["output_filename"])
                    if os.path.exists(file_path):
                        completed_tasks.append({
                            "task_id": task["task_id"],
                            "status": task["status"],
                            "created_at": task["created_at"],
                            "completed_at": task.get("completed_at"),
                            "original_filename": task.get("original_filename"),
                            "output_filename": task.get("output_filename"),
                            "plugin_info": task.get("plugin_info"),
                            "download_url": f"{settings.API_V1_STR}/tasks/{task['task_id']}/download",
                            "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else None
                        })
        
        # Sort by completed_at (most recent first)
        completed_tasks.sort(
            key=lambda x: x.get("completed_at", x["created_at"]), 
            reverse=True
        )
        
        # Return limited results
        return {
            "tasks": completed_tasks[:limit],
            "total": len(completed_tasks),
            "limit": limit
        }
    except Exception as e:
        logger.exception("Error listing completed tasks")
        error_msg = getattr(e, 'message', str(e)) if hasattr(e, 'message') else str(type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Internal server error: {error_msg}")


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """Get the status of a repackaging task"""
    validate_task_id(task_id)
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
    validate_task_id(task_id)
    try:
        logger.info(f"Download request for task: {task_id}")
        
        # Get task from Redis
        task_data = redis_client.get(f"task:{task_id}")
        
        if not task_data:
            logger.warning(f"Task not found in Redis: {task_id}")
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = json.loads(task_data)
        logger.info(f"Task status: {task.get('status')}")
        logger.info(f"Task data: {json.dumps(task, indent=2)}")
        
        # Check if task is completed
        if task.get("status") != TaskStatus.COMPLETED.value:
            raise HTTPException(
                status_code=400,
                detail=f"Task is not completed. Current status: {task.get('status')}"
            )
        
        # Check if output file exists
        output_filename = task.get("output_filename")
        if not output_filename:
            logger.error(f"No output filename in task data: {task}")
            raise HTTPException(status_code=404, detail="Output file not found")
        
        # Log environment info
        logger.info(f"TEMP_DIR setting: {settings.TEMP_DIR}")
        logger.info(f"Output filename: {output_filename}")
        
        # Build file path
        file_path = os.path.join(settings.TEMP_DIR, task_id, output_filename)
        logger.info(f"Looking for file at: {file_path}")
        
        # Check parent directory
        parent_dir = os.path.dirname(file_path)
        if not os.path.exists(parent_dir):
            logger.error(f"Parent directory does not exist: {parent_dir}")
            # Try to list temp directory
            if os.path.exists(settings.TEMP_DIR):
                logger.info(f"TEMP_DIR contents: {os.listdir(settings.TEMP_DIR)}")
            else:
                logger.error(f"TEMP_DIR does not exist: {settings.TEMP_DIR}")
            raise HTTPException(status_code=404, detail="File not found on server")
        
        # List directory contents
        logger.info(f"Task directory contents: {os.listdir(parent_dir)}")
        
        if not os.path.exists(file_path):
            logger.error(f"File not found on disk: {file_path}")
            # Check if file exists with different case
            for fname in os.listdir(parent_dir):
                logger.info(f"Found file: {fname} (looking for: {output_filename})")
                if fname.lower() == output_filename.lower():
                    logger.warning(f"File exists with different case: {fname}")
            raise HTTPException(status_code=404, detail="File not found on server")
        
        # Check file permissions
        file_stat = os.stat(file_path)
        logger.info(f"File permissions: {oct(file_stat.st_mode)}, size: {file_stat.st_size}")
        
        logger.info(f"Serving file: {file_path}")
        return FileResponse(
            file_path,
            media_type="application/octet-stream",
            filename=output_filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in download_result: {e}")
        error_msg = getattr(e, 'message', str(e)) if hasattr(e, 'message') else str(type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Internal server error: {error_msg}")


@router.get("/tasks")
async def list_recent_tasks(limit: int = 10):
    """List recent tasks (for demo purposes)"""
    # This is a simple implementation - in production, you'd want proper storage
    keys = list(redis_client.scan_iter("task:*"))
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
