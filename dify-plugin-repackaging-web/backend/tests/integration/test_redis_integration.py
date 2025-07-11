"""
Integration tests for Redis connectivity and operations.
"""
import pytest
import json
import asyncio
from datetime import datetime
import time


class TestRedisIntegration:
    """Test Redis integration functionality."""
    
    def test_redis_connection(self, redis_client):
        """Test basic Redis connectivity."""
        # Test ping
        assert redis_client.ping() is True
        
        # Test basic set/get
        redis_client.set("test_key", "test_value")
        assert redis_client.get("test_key") == "test_value"
        
        # Test expiration
        redis_client.setex("test_expiry", 1, "will_expire")
        assert redis_client.get("test_expiry") == "will_expire"
        time.sleep(1.5)
        assert redis_client.get("test_expiry") is None
    
    def test_task_storage(self, redis_client, test_task_id, test_helpers):
        """Test task data storage and retrieval."""
        # Create task data
        task_data = test_helpers.create_redis_task_data(
            test_task_id,
            status="processing",
            progress=50,
            message="Processing plugin"
        )
        
        # Store task
        redis_client.setex(f"task:{test_task_id}", 3600, task_data)
        
        # Retrieve and verify
        stored_data = redis_client.get(f"task:{test_task_id}")
        assert stored_data is not None
        
        parsed_data = json.loads(stored_data)
        assert parsed_data["task_id"] == test_task_id
        assert parsed_data["status"] == "processing"
        assert parsed_data["progress"] == 50
        assert parsed_data["message"] == "Processing plugin"
    
    def test_pubsub_functionality(self, redis_client, test_task_id):
        """Test Redis pub/sub for task updates."""
        # Create a subscriber
        pubsub = redis_client.pubsub()
        channel = f"task_updates:{test_task_id}"
        pubsub.subscribe(channel)
        
        # Wait for subscription to be ready
        time.sleep(0.1)
        
        # Publish a message
        test_message = {
            "task_id": test_task_id,
            "status": "completed",
            "progress": 100
        }
        redis_client.publish(channel, json.dumps(test_message))
        
        # Receive message
        messages = []
        for message in pubsub.listen():
            if message["type"] == "message":
                messages.append(json.loads(message["data"]))
                break
        
        # Verify message
        assert len(messages) == 1
        assert messages[0]["task_id"] == test_task_id
        assert messages[0]["status"] == "completed"
        
        # Cleanup
        pubsub.unsubscribe(channel)
        pubsub.close()
    
    def test_concurrent_task_updates(self, redis_client, clean_redis):
        """Test concurrent task updates don't cause race conditions."""
        task_id = "concurrent_test"
        
        def update_task(progress):
            """Update task with given progress."""
            task_data = {
                "task_id": task_id,
                "status": "processing",
                "progress": progress,
                "updated_at": datetime.utcnow().isoformat()
            }
            redis_client.set(f"task:{task_id}", json.dumps(task_data))
        
        # Perform concurrent updates
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(update_task, i * 10) for i in range(10)]
            concurrent.futures.wait(futures)
        
        # Verify final state exists
        final_data = redis_client.get(f"task:{task_id}")
        assert final_data is not None
        parsed = json.loads(final_data)
        assert parsed["task_id"] == task_id
        assert 0 <= parsed["progress"] <= 90
    
    def test_task_expiration(self, redis_client, test_task_id, test_helpers):
        """Test task data expiration."""
        # Create task with short TTL
        task_data = test_helpers.create_redis_task_data(test_task_id)
        redis_client.setex(f"task:{test_task_id}", 1, task_data)
        
        # Verify it exists
        assert redis_client.get(f"task:{test_task_id}") is not None
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Verify it's gone
        assert redis_client.get(f"task:{test_task_id}") is None
    
    def test_bulk_operations(self, redis_client, clean_redis):
        """Test bulk Redis operations."""
        # Create multiple tasks
        task_ids = [f"bulk_task_{i}" for i in range(100)]
        
        # Use pipeline for bulk insert
        pipe = redis_client.pipeline()
        for task_id in task_ids:
            task_data = {
                "task_id": task_id,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat()
            }
            pipe.setex(f"task:{task_id}", 3600, json.dumps(task_data))
        pipe.execute()
        
        # Verify all tasks exist
        for task_id in task_ids:
            assert redis_client.get(f"task:{task_id}") is not None
        
        # Bulk delete using pattern
        keys = redis_client.keys("task:bulk_task_*")
        assert len(keys) == 100
        
        if keys:
            redis_client.delete(*keys)
        
        # Verify all deleted
        remaining_keys = redis_client.keys("task:bulk_task_*")
        assert len(remaining_keys) == 0
    
    @pytest.mark.asyncio
    async def test_async_pubsub(self, redis_client, test_task_id):
        """Test async pub/sub operations."""
        import aioredis
        
        # Create async Redis client
        async_redis = await aioredis.from_url(
            redis_client.connection_pool.connection_kwargs['path'],
            decode_responses=True
        )
        
        channel = f"task_updates:{test_task_id}"
        messages_received = []
        
        async def subscriber():
            """Subscribe and receive messages."""
            pubsub = async_redis.pubsub()
            await pubsub.subscribe(channel)
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    messages_received.append(json.loads(message["data"]))
                    if len(messages_received) >= 3:
                        break
            
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        
        async def publisher():
            """Publish test messages."""
            await asyncio.sleep(0.1)  # Let subscriber start
            
            for i in range(3):
                message = {
                    "task_id": test_task_id,
                    "progress": (i + 1) * 33,
                    "sequence": i
                }
                await async_redis.publish(channel, json.dumps(message))
                await asyncio.sleep(0.1)
        
        # Run subscriber and publisher concurrently
        await asyncio.gather(subscriber(), publisher())
        
        # Verify messages
        assert len(messages_received) == 3
        for i, msg in enumerate(messages_received):
            assert msg["sequence"] == i
            assert msg["progress"] == (i + 1) * 33
        
        await async_redis.close()