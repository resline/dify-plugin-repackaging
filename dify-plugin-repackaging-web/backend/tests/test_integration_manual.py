#!/usr/bin/env python3
"""
Manual integration test script for marketplace functionality
Run this to verify the full integration flow
"""

import asyncio
import httpx
import json
from datetime import datetime


async def test_marketplace_integration():
    """Test the complete marketplace integration flow"""
    base_url = "http://localhost:8000/api/v1"
    
    print("=== Dify Plugin Repackaging - Marketplace Integration Test ===\n")
    
    async with httpx.AsyncClient() as client:
        # 1. Test marketplace search
        print("1. Testing marketplace search...")
        response = await client.get(f"{base_url}/marketplace/plugins?q=agent&page=1&per_page=5")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Found {data['total']} plugins")
            if data['plugins']:
                plugin = data['plugins'][0]
                print(f"   ✓ First result: {plugin['author']}/{plugin['name']} v{plugin['latest_version']}")
        else:
            print(f"   ✗ Search failed: {response.status_code}")
            return
        
        # 2. Test plugin details
        print("\n2. Testing plugin details...")
        if data['plugins']:
            plugin = data['plugins'][0]
            response = await client.get(f"{base_url}/marketplace/plugins/{plugin['author']}/{plugin['name']}")
            if response.status_code == 200:
                details = response.json()
                print(f"   ✓ Got details for {details['display_name']}")
                print(f"   ✓ Available versions: {len(details.get('available_versions', []))}")
            else:
                print(f"   ✗ Details failed: {response.status_code}")
        
        # 3. Test creating task with marketplace plugin
        print("\n3. Testing task creation with marketplace plugin...")
        task_data = {
            "marketplace_plugin": {
                "author": plugin['author'],
                "name": plugin['name'],
                "version": plugin['latest_version']
            },
            "platform": "",
            "suffix": "offline"
        }
        
        response = await client.post(f"{base_url}/tasks", json=task_data)
        if response.status_code == 200:
            task = response.json()
            task_id = task['task_id']
            print(f"   ✓ Created task: {task_id}")
            print(f"   ✓ Status: {task['status']}")
        else:
            print(f"   ✗ Task creation failed: {response.status_code}")
            print(f"   ✗ Error: {response.text}")
            return
        
        # 4. Test task status check
        print("\n4. Testing task status...")
        await asyncio.sleep(2)  # Wait a bit for processing
        
        response = await client.get(f"{base_url}/tasks/{task_id}")
        if response.status_code == 200:
            status = response.json()
            print(f"   ✓ Task status: {status['status']}")
            print(f"   ✓ Progress: {status['progress']}%")
        else:
            print(f"   ✗ Status check failed: {response.status_code}")
        
        # 5. Test backward compatibility with URL
        print("\n5. Testing backward compatibility (direct URL)...")
        url_task_data = {
            "url": "https://github.com/example/test.difypkg",
            "platform": "",
            "suffix": "offline"
        }
        
        response = await client.post(f"{base_url}/tasks", json=url_task_data)
        if response.status_code == 200:
            task = response.json()
            print(f"   ✓ Created URL-based task: {task['task_id']}")
        else:
            print(f"   ✗ URL task creation failed: {response.status_code}")
        
        # 6. Test marketplace convenience endpoint
        print("\n6. Testing marketplace convenience endpoint...")
        marketplace_task_data = {
            "author": plugin['author'],
            "name": plugin['name'],
            "version": plugin['latest_version'],
            "platform": "",
            "suffix": "offline"
        }
        
        response = await client.post(f"{base_url}/tasks/marketplace", json=marketplace_task_data)
        if response.status_code == 200:
            task = response.json()
            print(f"   ✓ Created marketplace task: {task['task_id']}")
        else:
            print(f"   ✗ Marketplace endpoint failed: {response.status_code}")
        
        print("\n=== Integration test completed ===")


def test_websocket_metadata():
    """Test that WebSocket messages include marketplace metadata"""
    from app.workers.celery_app import update_task_status
    from app.models.task import TaskStatus
    
    print("\n=== Testing WebSocket metadata ===")
    
    task_id = "test-123"
    marketplace_metadata = {
        "source": "marketplace",
        "author": "test-author",
        "name": "test-plugin",
        "version": "1.0.0",
        "display_name": "Test Plugin",
        "category": "tool"
    }
    
    # This would normally publish to Redis and WebSocket
    update_task_status(
        task_id,
        TaskStatus.PROCESSING,
        progress=50,
        message="Processing test...",
        marketplace_metadata=marketplace_metadata
    )
    
    print("✓ WebSocket update with marketplace metadata sent")


if __name__ == "__main__":
    print("Starting marketplace integration tests...\n")
    
    # Run async tests
    asyncio.run(test_marketplace_integration())
    
    # Test WebSocket metadata
    test_websocket_metadata()
    
    print("\n✓ All tests completed!")
    print("\nNote: Some tests may fail if the backend server is not running.")
    print("Start the server with: cd backend && uvicorn app.main:app --reload")