"""
Example usage of the marketplace scraper with fallback mechanism
"""

import asyncio
from app.services.marketplace_scraper import MarketplaceServiceWithFallback, MarketplaceScraper
from app.services.marketplace import MarketplaceService
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_direct_scraping():
    """Example of using the scraper directly"""
    print("\n=== Direct Scraping Example ===")
    
    scraper = MarketplaceScraper()
    
    # Scrape plugin list
    print("\n1. Scraping plugin list...")
    plugins = await scraper.scrape_plugin_list(page=1, per_page=5)
    
    if plugins['plugins']:
        print(f"Found {len(plugins['plugins'])} plugins:")
        for plugin in plugins['plugins']:
            print(f"  - {plugin['author']}/{plugin['name']} - {plugin['display_name']}")
        
        # Get details for first plugin
        first_plugin = plugins['plugins'][0]
        print(f"\n2. Getting details for {first_plugin['author']}/{first_plugin['name']}...")
        
        details = await scraper.scrape_plugin_details(
            first_plugin['author'], 
            first_plugin['name']
        )
        
        if details:
            print(f"  Display Name: {details['display_name']}")
            print(f"  Description: {details['description'][:100]}...")
            print(f"  Latest Version: {details['latest_version']}")
        
        # Get versions
        print(f"\n3. Getting versions...")
        versions = await scraper.scrape_plugin_versions(
            first_plugin['author'], 
            first_plugin['name']
        )
        
        if versions:
            print(f"  Found {len(versions)} versions:")
            for ver in versions[:3]:  # Show first 3
                print(f"    - {ver['version']}")
    else:
        print("No plugins found or scraping failed")


async def example_fallback_service():
    """Example of using the fallback service"""
    print("\n=== Fallback Service Example ===")
    
    fallback_service = MarketplaceServiceWithFallback()
    
    # Search with fallback
    print("\n1. Searching plugins with automatic fallback...")
    result = await fallback_service.search_plugins_with_fallback(
        query="agent",
        page=1,
        per_page=5
    )
    
    if result.get('fallback_used'):
        print(f"  ⚠️  Fallback was used: {result.get('fallback_reason')}")
    
    if result['plugins']:
        print(f"  Found {len(result['plugins'])} plugins")
        
        # Get details with fallback
        first_plugin = result['plugins'][0]
        print(f"\n2. Getting details with fallback for {first_plugin['author']}/{first_plugin['name']}...")
        
        details = await fallback_service.get_plugin_details_with_fallback(
            first_plugin['author'],
            first_plugin['name']
        )
        
        if details:
            print(f"  Successfully retrieved details")
            print(f"  Latest version: {details.get('latest_version', 'Unknown')}")


async def example_integrated_usage():
    """Example showing how the fallback is integrated into MarketplaceService"""
    print("\n=== Integrated Usage Example ===")
    
    # The MarketplaceService now automatically uses fallback
    print("\n1. Using MarketplaceService (with automatic fallback)...")
    
    try:
        # This will automatically fallback to scraping if API fails
        result = await MarketplaceService.search_plugins(
            query="visualization",
            page=1,
            per_page=5
        )
        
        if result.get('fallback_used'):
            print(f"  ℹ️  Service automatically used web scraping fallback")
        
        if result.get('api_status') == 'incompatible':
            print(f"  ⚠️  API is incompatible, results from web scraping")
        
        print(f"  Found {len(result['plugins'])} plugins")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")


async def example_cache_management():
    """Example of cache management"""
    print("\n=== Cache Management Example ===")
    
    fallback_service = MarketplaceServiceWithFallback()
    
    # Check cached data
    print("\n1. Checking for cached data...")
    cached = await fallback_service.get_cached_data(
        "scrape_list",
        page=1,
        per_page=20,
        category=None,
        query=None
    )
    
    if cached:
        print(f"  Found cached data with {len(cached.get('plugins', []))} plugins")
    else:
        print("  No cached data found")
    
    # Invalidate specific cache
    print("\n2. Invalidating specific cache entry...")
    fallback_service.invalidate_cache(
        "scrape_list",
        page=1,
        per_page=20,
        category=None,
        query=None
    )
    print("  Cache invalidated")
    
    # Invalidate all cache
    print("\n3. Invalidating all scraper cache...")
    fallback_service.invalidate_cache()
    print("  All cache cleared")


async def main():
    """Run all examples"""
    print("Marketplace Scraper Examples")
    print("=" * 50)
    
    # Run examples
    await example_direct_scraping()
    await example_fallback_service()
    await example_integrated_usage()
    await example_cache_management()
    
    print("\n" + "=" * 50)
    print("Examples completed!")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())