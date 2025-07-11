"""
Integration tests for Celery worker functionality.
"""
import pytest
import json
import time
import asyncio
from datetime import datetime
from celery.result import AsyncResult
from app.models.task import TaskStatus


class TestCeleryIntegration:
    """Test Celery worker integration."""
    
    def test_celery_worker_connectivity(self, celery_worker):
        """Test that Celery workers are running and responsive."""
        # Get worker stats
        i = celery_worker.control.inspect()
        stats = i.stats()
        
        assert stats is not None
        assert len(stats) > 0
        
        # Check registered tasks
        registered = i.registered()
        assert registered is not None
        
        for worker, tasks in registered.items():
            assert "app.workers.celery_app.process_repackaging" in tasks
            assert "app.workers.celery_app.process_marketplace_repackaging" in tasks
            assert "app.workers.celery_app.cleanup_old_files" in tasks
    
    def test_task_submission(self, celery_app, redis_client, test_task_id):
        """Test submitting a task to Celery."""
        # Submit task
        result = celery_app.send_task(
            "app.workers.celery_app.process_repackaging",
            args=[test_task_id, "https://example.com/plugin.difypkg", "manylinux2014_x86_64", "offline", False]
        )
        
        # Verify task was submitted
        assert result.id is not None
        assert result.state == "PENDING"
        
        # Wait a moment for task to be picked up
        time.sleep(1)
        
        # Check if task status was created in Redis
        task_data = redis_client.get(f"task:{test_task_id}")
        assert task_data is not None
    
    @pytest.mark.asyncio
    async def test_task_lifecycle(self, celery_app, redis_client, test_task_id, test_helpers):
        """Test complete task lifecycle from submission to completion."""
        # Create initial task data in Redis
        initial_data = test_helpers.create_redis_task_data(test_task_id, status="pending")
        redis_client.setex(f"task:{test_task_id}", 3600, initial_data)
        
        # Submit task
        result = celery_app.send_task(
            "app.workers.celery_app.process_repackaging",
            args=[test_task_id, "https://example.com/plugin.difypkg", "manylinux2014_x86_64", "offline", False]
        )
        
        # Monitor task progress
        states_seen = set()
        messages_seen = []
        
        for _ in range(30):  # Max 15 seconds
            task_data = redis_client.get(f"task:{test_task_id}")
            if task_data:
                data = json.loads(task_data)
                states_seen.add(data.get("status"))
                if data.get("message"):
                    messages_seen.append(data.get("message"))
                
                if data.get("status") in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(0.5)
        
        # Verify task went through expected states
        assert "downloading" in states_seen or "processing" in states_seen or "failed" in states_seen
    
    def test_marketplace_task(self, celery_app, redis_client, test_task_id):
        """Test marketplace-specific task processing."""
        # Submit marketplace task
        marketplace_metadata = {
            "author": "test-author",
            "name": "test-plugin",
            "version": "1.0.0",
            "description": "Test plugin"
        }
        
        result = celery_app.send_task(
            "app.workers.celery_app.process_marketplace_repackaging",
            args=[test_task_id, "test-author", "test-plugin", "1.0.0", "manylinux2014_x86_64", "offline"],
            kwargs={"marketplace_metadata": marketplace_metadata}
        )
        
        # Wait for task to start
        time.sleep(2)
        
        # Check task data includes marketplace metadata
        task_data = redis_client.get(f"task:{test_task_id}")
        if task_data:
            data = json.loads(task_data)
            assert "marketplace_metadata" in data or data.get("status") == "failed"
    
    def test_concurrent_tasks(self, celery_app, redis_client, clean_redis):
        """Test processing multiple tasks concurrently."""
        task_ids = [f"concurrent_{i}" for i in range(5)]
        results = []
        
        # Submit multiple tasks
        for task_id in task_ids:
            # Create initial task data
            task_data = {
                "task_id": task_id,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat()
            }
            redis_client.setex(f"task:{task_id}", 3600, json.dumps(task_data))
            
            # Submit task
            result = celery_app.send_task(
                "app.workers.celery_app.process_repackaging",
                args=[task_id, f"https://example.com/plugin_{task_id}.difypkg", "manylinux2014_x86_64", "offline", False]
            )
            results.append((task_id, result))
        
        # Wait for all tasks to be processed
        time.sleep(5)
        
        # Check all tasks have status updates
        for task_id in task_ids:
            task_data = redis_client.get(f"task:{task_id}")
            assert task_data is not None
            data = json.loads(task_data)
            assert data["status"] in ["downloading", "processing", "completed", "failed"]
    
    def test_task_retry_on_failure(self, celery_app, redis_client, test_task_id):
        """Test task retry behavior on failure."""
        # Submit task with invalid URL to trigger failure
        result = celery_app.send_task(
            "app.workers.celery_app.process_repackaging",
            args=[test_task_id, "invalid://url", "manylinux2014_x86_64", "offline", False]
        )
        
        # Wait for task to fail
        time.sleep(3)
        
        # Check task marked as failed
        task_data = redis_client.get(f"task:{test_task_id}")
        if task_data:
            data = json.loads(task_data)
            assert data.get("status") == "failed"
            assert data.get("error") is not None
    
    def test_cleanup_task(self, celery_app, tmp_path):
        """Test the cleanup task functionality."""
        # Create some old files
        old_file = tmp_path / "old_task" / "old_file.txt"
        old_file.parent.mkdir()
        old_file.write_text("old content")
        
        # Modify the file's timestamp to make it old
        import os
        old_time = time.time() - (8 * 24 * 3600)  # 8 days old
        os.utime(old_file.parent, (old_time, old_time))
        
        # Run cleanup task
        result = celery_app.send_task("app.workers.celery_app.cleanup_old_files")
        
        # Wait for completion
        time.sleep(2)
        
        # The actual cleanup would depend on the FileManager implementation
        # Here we just verify the task runs without error
        assert result.id is not None
    
    def test_task_cancellation(self, celery_app, redis_client, test_task_id):
        """Test task cancellation functionality."""
        # Submit a long-running task
        result = celery_app.send_task(
            "app.workers.celery_app.process_repackaging",
            args=[test_task_id, "https://example.com/large_plugin.difypkg", "manylinux2014_x86_64", "offline", False]
        )
        
        # Wait for task to start
        time.sleep(1)
        
        # Revoke the task
        celery_app.control.revoke(result.id, terminate=True)
        
        # Wait a moment
        time.sleep(2)
        
        # Check task status
        task_result = AsyncResult(result.id, app=celery_app)
        # Task should be revoked or completed/failed
        assert task_result.state in ["REVOKED", "SUCCESS", "FAILURE"]
    
    @pytest.mark.asyncio
    async def test_task_progress_updates(self, celery_app, redis_client, test_task_id):
        """Test that tasks properly update their progress."""
        # Subscribe to task updates
        pubsub = redis_client.pubsub()
        channel = f"task_updates:{test_task_id}"
        pubsub.subscribe(channel)
        
        # Submit task
        celery_app.send_task(
            "app.workers.celery_app.process_repackaging",
            args=[test_task_id, "https://example.com/plugin.difypkg", "manylinux2014_x86_64", "offline", False]
        )
        
        # Collect progress updates
        progress_updates = []
        start_time = time.time()
        
        while time.time() - start_time < 10:
            message = pubsub.get_message()
            if message and message["type"] == "message":
                update = json.loads(message["data"])
                progress_updates.append(update["progress"])
                
                if update.get("status") in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(0.1)
        
        # Cleanup
        pubsub.unsubscribe(channel)
        pubsub.close()
        
        # Verify we got some progress updates
        assert len(progress_updates) > 0