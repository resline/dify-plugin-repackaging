from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from app.models.task import TaskCreate, TaskResponse, TaskStatus
from app.workers.celery_app import process_repackaging, redis_client
from app.core.config import settings
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

# Create router
router = APIRouter(tags=["tasks"])


@router.post("/tasks", response_model=TaskResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def create_task(request: Request, task_data: TaskCreate):
    """Create a new repackaging task"""
    try:
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Validate URL
        if not str(task_data.url).endswith('.difypkg'):
            raise HTTPException(
                status_code=400,
                detail="URL must point to a .difypkg file"
            )
        
        # Create initial task record
        task_record = {
            "task_id": task_id,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "url": str(task_data.url),
            "platform": task_data.platform.value,
            "suffix": task_data.suffix,
            "progress": 0
        }
        
        # Store in Redis
        redis_client.setex(
            f"task:{task_id}",
            settings.FILE_RETENTION_HOURS * 3600,
            json.dumps(task_record)
        )
        
        # Queue the task
        process_repackaging.delay(
            task_id,
            str(task_data.url),
            task_data.platform.value,
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
    except Exception as e:
        logger.exception("Error creating task")
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
                "progress": task.get("progress", 0)
            })
    
    # Sort by created_at
    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {"tasks": tasks[:limit]}