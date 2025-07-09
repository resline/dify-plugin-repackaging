#!/usr/bin/env python3
"""
Test script to diagnose marketplace API issues
"""
import asyncio
import httpx
import json
import logging
from app.services.marketplace import MarketplaceService
from app.utils.circuit_breaker import marketplace_circuit_breaker

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_direct_api_call():
    """Test direct API call to marketplace"""
    print("\n=== Testing Direct API Call ===")
    
    urls = [
        "https://marketplace.dify.ai/api/v1/plugins/search/advanced",
        "https://marketplace.dify.ai/api/v1/categories",
        "https://marketplace.dify.ai/api/v1/plugins"
    ]
    
    async with httpx.AsyncClient() as client:
        for url in urls:
            print(f"\nTesting: {url}")
            try:
                # Test GET request
                response = await client.get(
                    url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "DifyPluginRepackaging/1.0"
                    },
                    timeout=10.0
                )
                
                print(f"Status: {response.status_code}")
                print(f"Headers: {dict(response.headers)}")
                print(f"Content-Type: {response.headers.get('content-type', 'None')}")
                
                # Try to parse response
                try:
                    data = response.json()
                    print(f"JSON Valid: Yes")
                    print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'List response'}")
                except Exception as e:
                    print(f"JSON Valid: No - {e}")
                    print(f"Response preview: {response.text[:200]}...")
                    
            except Exception as e:
                print(f"Request failed: {e}")


async def test_search_endpoint():
    """Test the search endpoint with POST"""
    print("\n=== Testing Search Endpoint (POST) ===")
    
    url = "https://marketplace.dify.ai/api/v1/plugins/search/advanced"
    
    request_body = {
        "page": 1,
        "page_size": 5,
        "query": "",
        "sort_by": "install_count",
        "sort_order": "DESC",
        "category": "",
        "tags": [],
        "type": "plugin"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                json=request_body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "DifyPluginRepackaging/1.0"
                },
                timeout=10.0
            )
            
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type', 'None')}")
            
            try:
                data = response.json()
                print(f"JSON Valid: Yes")
                print(f"Response structure: {json.dumps(data, indent=2)[:500]}...")
            except Exception as e:
                print(f"JSON Parse Error: {e}")
                print(f"Response: {response.text[:500]}...")
                
        except Exception as e:
            print(f"Request failed: {e}")


async def test_service_methods():
    """Test MarketplaceService methods"""
    print("\n=== Testing MarketplaceService Methods ===")
    
    # Reset circuit breaker first
    marketplace_circuit_breaker.reset()
    print("Circuit breaker reset")
    
    # Test search_plugins
    print("\nTesting search_plugins...")
    try:
        result = await MarketplaceService.search_plugins(page=1, per_page=5)
        print(f"Success: {bool(result)}")
        print(f"Result keys: {list(result.keys())}")
        print(f"Plugins count: {len(result.get('plugins', []))}")
        if result.get('error'):
            print(f"Error: {result['error']}")
    except Exception as e:
        print(f"Failed: {e}")
    
    # Test get_categories
    print("\nTesting get_categories...")
    try:
        categories = await MarketplaceService.get_categories()
        print(f"Categories: {categories}")
    except Exception as e:
        print(f"Failed: {e}")
    
    # Check circuit breaker state
    print(f"\nCircuit breaker state: {marketplace_circuit_breaker.get_state()}")


async def test_fallback_scraper():
    """Test if fallback scraper works"""
    print("\n=== Testing Fallback Scraper ===")
    
    try:
        from app.services.marketplace_scraper import marketplace_fallback_service
        
        result = await marketplace_fallback_service.scraper.scrape_plugin_list(
            page=1, per_page=5
        )
        
        print(f"Scraper success: {bool(result)}")
        print(f"Plugins found: {len(result.get('plugins', []))}")
        
    except Exception as e:
        print(f"Scraper failed: {e}")


async def main():
    """Run all tests"""
    print("Starting Marketplace API Diagnostics...")
    
    await test_direct_api_call()
    await test_search_endpoint()
    await test_service_methods()
    await test_fallback_scraper()
    
    print("\n=== Diagnostics Complete ===")


if __name__ == "__main__":
    asyncio.run(main())