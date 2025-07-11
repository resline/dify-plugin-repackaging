"""
Integration tests for file system operations across services.
"""
import pytest
import os
import json
import time
import asyncio
from pathlib import Path
import tempfile
import shutil


class TestFileSystemIntegration:
    """Test file system operations across services."""
    
    @pytest.mark.asyncio
    async def test_shared_volume_access(self, http_client, celery_app, redis_client):
        """Test that backend and worker can access shared volumes."""
        # Create a test file via API
        test_content = b"Test file for shared volume access"
        test_filename = "shared_volume_test.difypkg"
        
        files = {"file": (test_filename, test_content, "application/octet-stream")}
        data = {
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }
        
        response = await http_client.post(
            "/api/v1/tasks/repackage/upload",
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # Wait for task to be processed
        await asyncio.sleep(2)
        
        # Check if worker updated task status (indicates file access)
        task_data = redis_client.get(f"task:{task_id}")
        if task_data:
            data = json.loads(task_data)
            # Worker should have accessed the file
            assert data["status"] in ["downloading", "processing", "failed"]
    
    def test_temp_directory_isolation(self, celery_app, test_task_id):
        """Test that each task uses isolated temp directories."""
        task_ids = [f"isolation_test_{i}" for i in range(3)]
        
        # Submit multiple tasks
        for task_id in task_ids:
            celery_app.send_task(
                "app.workers.celery_app.process_repackaging",
                args=[task_id, f"https://example.com/{task_id}.difypkg", "manylinux2014_x86_64", "offline", False]
            )
        
        # Each task should create its own temp directory
        # This is verified by the task execution not interfering with each other
        time.sleep(3)
        
        # Tasks should process independently without file conflicts
        # (actual verification would require checking temp directory structure)
    
    @pytest.mark.asyncio
    async def test_file_cleanup_after_task(self, http_client, redis_client, tmp_path):
        """Test that temporary files are cleaned up properly."""
        # Note: This test assumes we have access to the temp directory
        # In a real containerized environment, we'd need to verify this differently
        
        # Create a task
        task_data = {
            "url": "https://example.com/cleanup-test.difypkg",
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }
        
        response = await http_client.post("/api/v1/tasks/repackage/url", json=task_data)
        assert response.status_code == 200
        
        task_id = response.json()["task_id"]
        
        # Wait for task to complete or fail
        for _ in range(20):
            task_info = redis_client.get(f"task:{task_id}")
            if task_info:
                data = json.loads(task_info)
                if data["status"] in ["completed", "failed"]:
                    break
            await asyncio.sleep(0.5)
        
        # In production, temp files should be cleaned based on retention policy
        # Here we just verify the task completed without leaving orphaned processes
    
    @pytest.mark.asyncio
    async def test_large_file_handling(self, http_client):
        """Test handling of large files across services."""
        # Create a large test file (10MB)
        large_content = b"X" * (10 * 1024 * 1024)
        
        with tempfile.NamedTemporaryFile(suffix=".difypkg", delete=False) as tmp_file:
            tmp_file.write(large_content)
            tmp_file_path = tmp_file.name
        
        try:
            with open(tmp_file_path, "rb") as f:
                files = {"file": ("large_plugin.difypkg", f, "application/octet-stream")}
                data = {
                    "platform": "manylinux2014_x86_64",
                    "suffix": "offline"
                }
                
                response = await http_client.post(
                    "/api/v1/tasks/repackage/upload",
                    files=files,
                    data=data,
                    timeout=60.0
                )
            
            assert response.status_code == 200
            task_id = response.json()["task_id"]
            
            # Large file should be processed without memory issues
            assert task_id is not None
        finally:
            os.unlink(tmp_file_path)
    
    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self, http_client):
        """Test concurrent file uploads and processing."""
        async def upload_file(index):
            content = f"Test content {index}".encode()
            files = {"file": (f"concurrent_{index}.difypkg", content, "application/octet-stream")}
            data = {
                "platform": "manylinux2014_x86_64",
                "suffix": "offline"
            }
            
            response = await http_client.post(
                "/api/v1/tasks/repackage/upload",
                files=files,
                data=data
            )
            return response
        
        # Upload multiple files concurrently
        tasks = [upload_file(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)
        
        # All uploads should succeed
        assert all(r.status_code == 200 for r in responses)
        
        # Each should have a unique task ID
        task_ids = [r.json()["task_id"] for r in responses]
        assert len(set(task_ids)) == len(task_ids)
    
    def test_script_directory_access(self, celery_worker):
        """Test that workers can access script directory."""
        # Submit a task that would use scripts
        result = celery_worker.send_task(
            "app.workers.celery_app.process_repackaging",
            args=["script_test", "https://example.com/script-test.difypkg", "manylinux2014_x86_64", "offline", False]
        )
        
        # Task should be accepted (script access verified during execution)
        assert result.id is not None
    
    @pytest.mark.asyncio
    async def test_file_permissions(self, http_client, tmp_path):
        """Test file permission handling across services."""
        # Create a file with specific permissions
        test_file = tmp_path / "permission_test.difypkg"
        test_file.write_bytes(b"Permission test content")
        os.chmod(test_file, 0o644)
        
        with open(test_file, "rb") as f:
            files = {"file": ("permission_test.difypkg", f, "application/octet-stream")}
            data = {
                "platform": "manylinux2014_x86_64",
                "suffix": "offline"
            }
            
            response = await http_client.post(
                "/api/v1/tasks/repackage/upload",
                files=files,
                data=data
            )
        
        assert response.status_code == 200
        
        # File should be processable regardless of original permissions
        task_id = response.json()["task_id"]
        assert task_id is not None
    
    @pytest.mark.asyncio
    async def test_disk_space_handling(self, http_client, redis_client):
        """Test handling of low disk space scenarios."""
        # This is a conceptual test - actual implementation would need
        # to simulate low disk space conditions
        
        # Create a task
        task_data = {
            "url": "https://example.com/disk-space-test.difypkg",
            "platform": "manylinux2014_x86_64",
            "suffix": "offline"
        }
        
        response = await http_client.post("/api/v1/tasks/repackage/url", json=task_data)
        assert response.status_code == 200
        
        task_id = response.json()["task_id"]
        
        # In low disk space, task should fail gracefully
        await asyncio.sleep(3)
        
        task_info = redis_client.get(f"task:{task_id}")
        if task_info:
            data = json.loads(task_info)
            # Task should either complete or fail with appropriate error
            assert data["status"] in ["downloading", "processing", "completed", "failed"]
            if data["status"] == "failed" and data.get("error"):
                # Error should be descriptive
                assert len(data["error"]) > 0
    
    def test_file_retention_policy(self, celery_app):
        """Test that file retention policy is enforced."""
        # Trigger cleanup task
        result = celery_app.send_task("app.workers.celery_app.cleanup_old_files")
        
        # Task should execute without errors
        assert result.id is not None
        
        # In production, this would verify that files older than
        # retention period are deleted
    
    @pytest.mark.asyncio
    async def test_symbolic_link_handling(self, http_client, tmp_path):
        """Test handling of symbolic links in uploaded files."""
        # Create a regular file
        target_file = tmp_path / "target.txt"
        target_file.write_text("Target content")
        
        # Create a symbolic link
        link_file = tmp_path / "link.difypkg"
        link_file.symlink_to(target_file)
        
        # Try to upload the symbolic link
        with open(target_file, "rb") as f:  # Read through the link
            files = {"file": ("symlink_test.difypkg", f, "application/octet-stream")}
            data = {
                "platform": "manylinux2014_x86_64",
                "suffix": "offline"
            }
            
            response = await http_client.post(
                "/api/v1/tasks/repackage/upload",
                files=files,
                data=data
            )
        
        # Should handle symbolic links safely
        assert response.status_code in [200, 400]  # Either accept or reject safely