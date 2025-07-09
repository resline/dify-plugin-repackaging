"""
File management service for handling completed files
"""
import os
import json
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.core.config import settings
from app.workers.celery_app import redis_client
import logging

logger = logging.getLogger(__name__)


class FileManager:
    """Service for managing completed repackaged files"""
    
    @staticmethod
    def get_file_info(task_id: str) -> Optional[Dict]:
        """
        Get file information from a completed task
        
        Returns:
            Dict with file information or None if not found
        """
        try:
            # Get task data from Redis
            task_data = redis_client.get(f"task:{task_id}")
            if not task_data:
                return None
            
            task = json.loads(task_data)
            
            # Check if task is completed and has output file
            if task.get("status") != "completed" or not task.get("output_filename"):
                return None
            
            # Build file path
            file_path = os.path.join(settings.TEMP_DIR, task_id, task["output_filename"])
            
            # Check if file exists
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                return None
            
            # Get file stats
            file_stats = os.stat(file_path)
            
            # Build file info
            file_info = {
                "file_id": task_id,
                "filename": task["output_filename"],
                "original_filename": task.get("original_filename"),
                "size": file_stats.st_size,
                "created_at": task.get("completed_at", task.get("created_at")),
                "modified_at": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                "plugin_info": task.get("plugin_info"),
                "marketplace_metadata": task.get("marketplace_metadata"),
                "platform": task.get("platform", ""),
                "suffix": task.get("suffix", "offline"),
                "download_url": f"/api/v1/files/{task_id}/download"
            }
            
            return file_info
            
        except Exception as e:
            logger.error(f"Error getting file info for task {task_id}: {e}")
            return None
    
    @staticmethod
    def list_completed_files(limit: int = 100, offset: int = 0) -> Dict:
        """
        List all completed files with pagination
        
        Args:
            limit: Maximum number of files to return
            offset: Number of files to skip
            
        Returns:
            Dict with files list and pagination info
        """
        try:
            # Get all task keys
            all_keys = redis_client.keys("task:*")
            
            # Filter completed tasks with files
            completed_files = []
            
            for key in all_keys:
                task_data = redis_client.get(key)
                if task_data:
                    task = json.loads(task_data)
                    
                    # Only include completed tasks with output files
                    if task.get("status") == "completed" and task.get("output_filename"):
                        task_id = task["task_id"]
                        file_info = FileManager.get_file_info(task_id)
                        
                        if file_info:
                            completed_files.append(file_info)
            
            # Sort by created_at (newest first)
            completed_files.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            # Apply pagination
            total = len(completed_files)
            paginated_files = completed_files[offset:offset + limit]
            
            return {
                "files": paginated_files,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total
            }
            
        except Exception as e:
            logger.error(f"Error listing completed files: {e}")
            return {
                "files": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "has_more": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_file_path(file_id: str) -> Optional[str]:
        """
        Get the actual file path for a completed file
        
        Args:
            file_id: The file ID (task ID)
            
        Returns:
            File path if exists, None otherwise
        """
        file_info = FileManager.get_file_info(file_id)
        if not file_info:
            return None
        
        file_path = os.path.join(settings.TEMP_DIR, file_id, file_info["filename"])
        
        if os.path.exists(file_path):
            return file_path
        
        return None
    
    @staticmethod
    def cleanup_old_files(retention_days: Optional[int] = None) -> int:
        """
        Clean up files older than retention period
        
        Args:
            retention_days: Number of days to retain files (default from settings)
            
        Returns:
            Number of files cleaned up
        """
        if retention_days is None:
            retention_days = settings.FILE_RETENTION_DAYS
        
        cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
        cleaned_count = 0
        
        try:
            temp_dir = settings.TEMP_DIR
            if not os.path.exists(temp_dir):
                return 0
            
            # Iterate through task directories
            for task_dir in os.listdir(temp_dir):
                dir_path = os.path.join(temp_dir, task_dir)
                
                if os.path.isdir(dir_path):
                    # Check directory modification time
                    mtime = datetime.fromtimestamp(os.path.getmtime(dir_path))
                    
                    if mtime < cutoff_time:
                        # Check if this is a completed task
                        task_data = redis_client.get(f"task:{task_dir}")
                        
                        if task_data:
                            task = json.loads(task_data)
                            
                            # Only clean up completed or failed tasks
                            if task.get("status") in ["completed", "failed"]:
                                shutil.rmtree(dir_path)
                                cleaned_count += 1
                                logger.info(f"Cleaned up old task directory: {task_dir}")
                                
                                # Also remove from Redis
                                redis_client.delete(f"task:{task_dir}")
                        else:
                            # No Redis data, safe to remove
                            shutil.rmtree(dir_path)
                            cleaned_count += 1
                            logger.info(f"Cleaned up orphaned directory: {task_dir}")
            
            logger.info(f"Cleaned up {cleaned_count} old directories")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return cleaned_count
    
    @staticmethod
    def get_storage_stats() -> Dict:
        """
        Get storage statistics for the temp directory
        
        Returns:
            Dict with storage statistics
        """
        try:
            temp_dir = settings.TEMP_DIR
            
            if not os.path.exists(temp_dir):
                return {
                    "total_size": 0,
                    "file_count": 0,
                    "directory_count": 0,
                    "oldest_file": None,
                    "newest_file": None
                }
            
            total_size = 0
            file_count = 0
            directory_count = 0
            oldest_mtime = None
            newest_mtime = None
            
            # Walk through all files and directories
            for root, dirs, files in os.walk(temp_dir):
                directory_count += len(dirs)
                
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_stats = os.stat(file_path)
                        total_size += file_stats.st_size
                        file_count += 1
                        
                        mtime = file_stats.st_mtime
                        if oldest_mtime is None or mtime < oldest_mtime:
                            oldest_mtime = mtime
                        if newest_mtime is None or mtime > newest_mtime:
                            newest_mtime = mtime
                            
                    except OSError:
                        # Skip files that can't be accessed
                        pass
            
            return {
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count,
                "directory_count": directory_count,
                "oldest_file": datetime.fromtimestamp(oldest_mtime).isoformat() if oldest_mtime else None,
                "newest_file": datetime.fromtimestamp(newest_mtime).isoformat() if newest_mtime else None
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {
                "error": str(e)
            }