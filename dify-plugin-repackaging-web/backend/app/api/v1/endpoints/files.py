"""
File management endpoints for listing and downloading completed files
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from app.services.file_manager import FileManager
from app.core.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["files"])


@router.get("/files")
async def list_files(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of files to return"),
    offset: int = Query(default=0, ge=0, description="Number of files to skip")
):
    """
    List all completed repackaged files
    
    Returns a paginated list of completed files with their metadata including:
    - file_id: Unique identifier for the file (same as task_id)
    - filename: Name of the repackaged file
    - original_filename: Original filename before repackaging
    - size: File size in bytes
    - created_at: When the file was created
    - plugin_info: Marketplace plugin information if applicable
    - download_url: URL to download the file
    
    Query parameters:
    - **limit**: Maximum number of files to return (1-200, default: 50)
    - **offset**: Number of files to skip for pagination (default: 0)
    
    Example response:
    ```json
    {
        "files": [
            {
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "langgenius_agent_0.0.9-offline.difypkg",
                "original_filename": "langgenius_agent_0.0.9.difypkg",
                "size": 2048576,
                "created_at": "2024-01-15T10:30:00Z",
                "plugin_info": {
                    "author": "langgenius",
                    "name": "agent",
                    "version": "0.0.9"
                },
                "download_url": "/api/v1/files/123e4567-e89b-12d3-a456-426614174000/download"
            }
        ],
        "total": 42,
        "limit": 50,
        "offset": 0,
        "has_more": false
    }
    ```
    """
    try:
        result = FileManager.list_completed_files(limit=limit, offset=offset)
        return result
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/files/{file_id}/download")
async def download_file(file_id: str):
    """
    Download a completed repackaged file
    
    Parameters:
    - **file_id**: The unique identifier of the file (same as task_id)
    
    Returns:
    - The repackaged .difypkg file as a binary download
    
    Errors:
    - **404**: File not found or task not completed
    - **500**: Internal server error
    """
    try:
        # Get file path
        file_path = FileManager.get_file_path(file_id)
        
        if not file_path:
            raise HTTPException(
                status_code=404,
                detail="File not found. The file may have been deleted or the task is not completed."
            )
        
        # Get file info for the filename
        file_info = FileManager.get_file_info(file_id)
        filename = file_info["filename"] if file_info else "plugin.difypkg"
        
        logger.info(f"Serving file download: {file_id} -> {filename}")
        
        return FileResponse(
            file_path,
            media_type="application/octet-stream",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/files/{file_id}")
async def get_file_info(file_id: str):
    """
    Get detailed information about a specific file
    
    Parameters:
    - **file_id**: The unique identifier of the file (same as task_id)
    
    Returns detailed file information including:
    - All fields from the list endpoint
    - platform: Target platform used for repackaging
    - suffix: File suffix used
    - marketplace_metadata: Additional marketplace information if available
    
    Errors:
    - **404**: File not found
    """
    try:
        file_info = FileManager.get_file_info(file_id)
        
        if not file_info:
            raise HTTPException(
                status_code=404,
                detail="File not found. The file may have been deleted or the task is not completed."
            )
        
        return file_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info for {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/files/stats/storage")
async def get_storage_stats():
    """
    Get storage statistics for all files
    
    Returns storage information including:
    - total_size: Total size of all files in bytes
    - total_size_mb: Total size in megabytes
    - file_count: Number of files
    - directory_count: Number of task directories
    - oldest_file: Timestamp of the oldest file
    - newest_file: Timestamp of the newest file
    
    This endpoint is useful for monitoring storage usage and cleanup needs.
    """
    try:
        stats = FileManager.get_storage_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """
    Delete a specific file
    
    Parameters:
    - **file_id**: The unique identifier of the file to delete (same as task_id)
    
    Returns:
    - Success message if file was deleted
    
    Errors:
    - **404**: File not found
    - **500**: Internal server error
    """
    try:
        # Check if file exists
        file_info = FileManager.get_file_info(file_id)
        
        if not file_info:
            raise HTTPException(
                status_code=404,
                detail="File not found or already deleted"
            )
        
        # Delete the file
        success = FileManager.delete_file(file_id)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete file"
            )
        
        logger.info(f"File {file_id} deleted successfully")
        
        return {
            "message": "File deleted successfully",
            "file_id": file_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/files/cleanup")
async def cleanup_old_files(
    retention_days: Optional[int] = Query(
        default=None,
        ge=1,
        le=365,
        description="Number of days to retain files (default from settings)"
    )
):
    """
    Manually trigger cleanup of old files
    
    This endpoint allows manual cleanup of files older than the retention period.
    By default, it uses the FILE_RETENTION_DAYS setting (7 days).
    
    Parameters:
    - **retention_days**: Override the default retention period (1-365 days)
    
    Returns:
    - Number of files cleaned up
    
    Note: Automatic cleanup runs periodically via Celery, so manual cleanup
    is typically not necessary unless you need immediate space recovery.
    """
    try:
        cleaned_count = FileManager.cleanup_old_files(retention_days)
        
        logger.info(f"Manual cleanup completed: {cleaned_count} files removed")
        
        return {
            "cleaned_count": cleaned_count,
            "retention_days": retention_days or settings.FILE_RETENTION_DAYS,
            "message": f"Cleaned up {cleaned_count} old files"
        }
        
    except Exception as e:
        logger.error(f"Error during manual cleanup: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")