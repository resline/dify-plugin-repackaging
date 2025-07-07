from celery import Celery
from app.core.config import settings
import redis
import json
import asyncio
from datetime import datetime
from app.services.download import DownloadService
from app.services.repackage import RepackageService
from app.models.task import TaskStatus
import logging
import os

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "dify_repackaging",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Redis client for status updates
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def update_task_status(task_id: str, status: TaskStatus, progress: int = 0, 
                      message: str = "", error: str = None, output_filename: str = None,
                      marketplace_metadata: dict = None):
    """Update task status in Redis"""
    task_data = {
        "task_id": task_id,
        "status": status.value,
        "progress": progress,
        "message": message,
        "updated_at": datetime.utcnow().isoformat(),
        "error": error,
        "output_filename": output_filename
    }
    
    # Include marketplace metadata if provided
    if marketplace_metadata:
        task_data["marketplace_metadata"] = marketplace_metadata
    
    if status == TaskStatus.COMPLETED:
        task_data["completed_at"] = datetime.utcnow().isoformat()
    
    # Store in Redis
    redis_client.setex(
        f"task:{task_id}",
        settings.FILE_RETENTION_HOURS * 3600,
        json.dumps(task_data)
    )
    
    # Publish update for WebSocket
    redis_client.publish(
        f"task_updates:{task_id}",
        json.dumps(task_data)
    )


@celery_app.task(bind=True)
def process_repackaging(self, task_id: str, url: str, platform: str, suffix: str):
    """Main Celery task for processing repackaging requests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Update status to downloading
        update_task_status(task_id, TaskStatus.DOWNLOADING, 5, "Starting download...")
        
        # Download file
        file_path, filename = loop.run_until_complete(
            DownloadService.download_file(url, task_id)
        )
        
        update_task_status(task_id, TaskStatus.PROCESSING, 15, f"Downloaded {filename}")
        
        # Process repackaging
        async def run_repackaging():
            output_filename = None
            async for message, progress in RepackageService.repackage_plugin(
                file_path, platform, suffix, task_id
            ):
                update_task_status(task_id, TaskStatus.PROCESSING, progress, message)
                
                # Extract output filename from message
                if "Output file:" in message:
                    output_filename = message.split("Output file:")[-1].strip()
            
            return output_filename
        
        output_filename = loop.run_until_complete(run_repackaging())
        
        # Mark as completed
        update_task_status(
            task_id, 
            TaskStatus.COMPLETED, 
            100, 
            "Repackaging completed successfully",
            output_filename=output_filename
        )
        
        return {
            "task_id": task_id,
            "status": "completed",
            "output_filename": output_filename
        }
        
    except Exception as e:
        logger.exception(f"Error processing task {task_id}")
        update_task_status(
            task_id,
            TaskStatus.FAILED,
            0,
            "Processing failed",
            error=str(e)
        )
        raise
    
    finally:
        loop.close()


@celery_app.task(bind=True)
def process_marketplace_repackaging(self, task_id: str, author: str, name: str, 
                                  version: str, platform: str, suffix: str,
                                  marketplace_metadata: dict = None):
    """Celery task for processing marketplace plugin repackaging"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Update status to downloading with marketplace metadata
        update_task_status(
            task_id, 
            TaskStatus.DOWNLOADING, 
            5, 
            f"Downloading {author}/{name} v{version} from marketplace...",
            marketplace_metadata=marketplace_metadata
        )
        
        # Build download URL
        from app.services.marketplace import MarketplaceService
        url = MarketplaceService.build_download_url(author, name, version)
        
        # Download file
        file_path, filename = loop.run_until_complete(
            DownloadService.download_file(url, task_id)
        )
        
        update_task_status(
            task_id, 
            TaskStatus.PROCESSING, 
            15, 
            f"Downloaded {filename}",
            marketplace_metadata=marketplace_metadata
        )
        
        # Process repackaging
        async def run_repackaging():
            output_filename = None
            async for message, progress in RepackageService.repackage_plugin(
                file_path, platform, suffix, task_id
            ):
                update_task_status(
                    task_id, 
                    TaskStatus.PROCESSING, 
                    progress, 
                    message,
                    marketplace_metadata=marketplace_metadata
                )
                
                # Extract output filename from message
                if "Output file:" in message:
                    output_filename = message.split("Output file:")[-1].strip()
            
            return output_filename
        
        output_filename = loop.run_until_complete(run_repackaging())
        
        # Mark as completed
        update_task_status(
            task_id, 
            TaskStatus.COMPLETED, 
            100, 
            "Repackaging completed successfully",
            output_filename=output_filename,
            marketplace_metadata=marketplace_metadata
        )
        
        return {
            "task_id": task_id,
            "status": "completed",
            "output_filename": output_filename,
            "marketplace_metadata": marketplace_metadata
        }
        
    except Exception as e:
        logger.exception(f"Error processing marketplace task {task_id}")
        update_task_status(
            task_id,
            TaskStatus.FAILED,
            0,
            "Processing failed",
            error=str(e),
            marketplace_metadata=marketplace_metadata
        )
        raise
    
    finally:
        loop.close()


@celery_app.task
def cleanup_old_files():
    """Periodic task to clean up old files"""
    import shutil
    from datetime import datetime, timedelta
    
    cutoff_time = datetime.utcnow() - timedelta(hours=settings.FILE_RETENTION_HOURS)
    
    temp_dir = settings.TEMP_DIR
    if not os.path.exists(temp_dir):
        return
    
    cleaned = 0
    for task_dir in os.listdir(temp_dir):
        dir_path = os.path.join(temp_dir, task_dir)
        if os.path.isdir(dir_path):
            # Check directory modification time
            mtime = datetime.fromtimestamp(os.path.getmtime(dir_path))
            if mtime < cutoff_time:
                shutil.rmtree(dir_path)
                cleaned += 1
                logger.info(f"Cleaned up old task directory: {task_dir}")
    
    return f"Cleaned {cleaned} old task directories"


# Configure periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-old-files': {
        'task': 'app.workers.celery_app.cleanup_old_files',
        'schedule': 3600.0,  # Run every hour
    },
}