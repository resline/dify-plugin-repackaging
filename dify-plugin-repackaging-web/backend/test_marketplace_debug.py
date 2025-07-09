#!/usr/bin/env python3
"""
Debug script to test marketplace API endpoints
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_marketplace_endpoints():
    """Test various marketplace endpoints to diagnose issues"""
    
    base_url = "http://localhost:8000/api/v1"
    marketplace_url = "https://marketplace.dify.ai"
    
    tests = []
    
    print("=" * 80)
    print(f"Marketplace Debug Test - {datetime.now()}")
    print("=" * 80)
    
    # Test 1: Backend health check
    print("\n1. Testing backend health...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url.replace('/api/v1', '')}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            tests.append(("Backend Health", "PASS"))
    except Exception as e:
        print(f"   ERROR: {e}")
        tests.append(("Backend Health", "FAIL"))
    
    # Test 2: Marketplace status endpoint
    print("\n2. Testing marketplace status endpoint...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/marketplace/status")
            print(f"   Status: {response.status_code}")
            data = response.json()
            print(f"   API Status: {data['marketplace_api']['status']}")
            print(f"   Circuit Breaker: {data['circuit_breaker']['state']}")
            tests.append(("Marketplace Status", "PASS"))
    except Exception as e:
        print(f"   ERROR: {e}")
        tests.append(("Marketplace Status", "FAIL"))
    
    # Test 3: Categories endpoint
    print("\n3. Testing categories endpoint...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/marketplace/categories")
            print(f"   Status: {response.status_code}")
            data = response.json()
            print(f"   Categories: {data.get('categories', [])}")
            tests.append(("Categories", "PASS" if data.get('categories') else "FAIL"))
    except Exception as e:
        print(f"   ERROR: {e}")
        tests.append(("Categories", "FAIL"))
    
    # Test 4: Authors endpoint
    print("\n4. Testing authors endpoint...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/marketplace/authors")
            print(f"   Status: {response.status_code}")
            data = response.json()
            authors = data.get('authors', [])
            print(f"   Authors count: {len(authors)}")
            print(f"   Sample authors: {authors[:5]}")
            tests.append(("Authors", "PASS" if authors else "FAIL"))
    except Exception as e:
        print(f"   ERROR: {e}")
        tests.append(("Authors", "FAIL"))
    
    # Test 5: Search plugins
    print("\n5. Testing plugin search...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/marketplace/plugins", 
                                      params={"page": 1, "per_page": 5})
            print(f"   Status: {response.status_code}")
            data = response.json()
            plugins = data.get('plugins', [])
            print(f"   Plugins found: {len(plugins)}")
            print(f"   Total: {data.get('total', 0)}")
            print(f"   Using fallback: {data.get('fallback_used', False)}")
            if plugins:
                print(f"   First plugin: {plugins[0].get('author')}/{plugins[0].get('name')}")
            tests.append(("Plugin Search", "PASS" if plugins else "FAIL"))
    except Exception as e:
        print(f"   ERROR: {e}")
        tests.append(("Plugin Search", "FAIL"))
    
    # Test 6: Direct marketplace API test
    print("\n6. Testing direct marketplace API...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test new API endpoint
            response = await client.post(
                f"{marketplace_url}/api/v1/plugins/search/advanced",
                json={
                    "page": 1,
                    "page_size": 5,
                    "query": "",
                    "sort_by": "install_count",
                    "sort_order": "DESC",
                    "category": "",
                    "tags": [],
                    "type": "plugin"
                },
                headers={"Content-Type": "application/json"}
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   API Response OK")
                tests.append(("Direct API", "PASS"))
            else:
                print(f"   API Response: {response.text[:200]}")
                tests.append(("Direct API", "FAIL"))
    except Exception as e:
        print(f"   ERROR: {e}")
        tests.append(("Direct API", "FAIL"))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY:")
    print("=" * 80)
    for test_name, result in tests:
        status_icon = "✓" if result == "PASS" else "✗"
        print(f"{status_icon} {test_name}: {result}")
    
    passed = sum(1 for _, result in tests if result == "PASS")
    total = len(tests)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    # Recommendations
    print("\nRECOMMENDATIONS:")
    if any(result == "FAIL" for _, result in tests):
        print("- Check if the backend service is running properly")
        print("- Verify Redis connection is working")
        print("- Check network connectivity to marketplace.dify.ai")
        print("- Look for errors in backend logs")
        print("- Try resetting circuit breaker: POST /api/v1/marketplace/reset-circuit-breaker")
    else:
        print("- All tests passed! The marketplace should be working correctly.")

if __name__ == "__main__":
    asyncio.run(test_marketplace_endpoints())