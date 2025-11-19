# Marketplace Scraper Documentation

## Overview

The Marketplace Scraper is an alternative parser for the Dify Marketplace that provides fallback functionality when the official API is unavailable or has changed. It uses web scraping with BeautifulSoup to extract plugin information directly from the marketplace website.

## Features

- **Web Scraping**: Extracts plugin data directly from HTML pages
- **Automatic Fallback**: Seamlessly switches from API to scraping when needed
- **Caching**: Redis-based caching to reduce load on the marketplace
- **Retry Logic**: Automatic retry with exponential backoff for failed requests
- **Integration**: Fully integrated with existing `MarketplaceService`

## Architecture

### Components

1. **MarketplaceScraper**: Core scraping functionality
   - Parses HTML to extract plugin information
   - Handles different page structures with multiple selector patterns
   - Implements caching and retry logic

2. **MarketplaceServiceWithFallback**: Orchestration layer
   - Tries API first, falls back to scraping
   - Provides unified interface
   - Manages cache invalidation

3. **Integration**: Automatic fallback in `MarketplaceService`
   - No code changes required for existing consumers
   - Transparent fallback mechanism

## Usage

### Direct Scraping

```python
from app.services.marketplace_scraper import MarketplaceScraper

scraper = MarketplaceScraper()

# Scrape plugin list
plugins = await scraper.scrape_plugin_list(page=1, per_page=20, category="agent")

# Scrape plugin details
details = await scraper.scrape_plugin_details("langgenius", "agent")

# Scrape available versions
versions = await scraper.scrape_plugin_versions("langgenius", "agent")
```

### With Fallback Service

```python
from app.services.marketplace_scraper import MarketplaceServiceWithFallback

service = MarketplaceServiceWithFallback()

# Search with automatic fallback
result = await service.search_plugins_with_fallback(query="visualization")

# Check if fallback was used
if result.get('fallback_used'):
    print(f"Fallback reason: {result['fallback_reason']}")
```

### Integrated Usage (Recommended)

```python
from app.services.marketplace import MarketplaceService

# The service now automatically uses fallback
result = await MarketplaceService.search_plugins(query="agent")

# Check if fallback was used
if result.get('fallback_used'):
    print("Results obtained via web scraping")
```

## Fallback Triggers

The scraper is activated when:

1. **API Timeout**: Request takes longer than 10 seconds
2. **API Error**: HTTP errors (4xx, 5xx)
3. **API Incompatibility**: API structure has changed
4. **Network Issues**: Connection failures

## Caching

### Cache Keys

Cache keys are generated using MD5 hash of parameters:
```
marketplace_scraper:operation_type:hash(params)
```

### Cache TTL

- Default: 3600 seconds (1 hour)
- Configurable per operation

### Cache Management

```python
# Get cached data
cached = await service.get_cached_data("scrape_list", page=1)

# Invalidate specific cache
service.invalidate_cache("scrape_list", page=1)

# Clear all scraper cache
service.invalidate_cache()
```

## HTML Parsing Strategy

The scraper uses multiple selector patterns to handle different HTML structures:

### Plugin List Selectors
```python
plugin_selectors = [
    "div[class*='plugin-card']",
    "article[class*='plugin']",
    "div[class*='grid'] > div[class*='card']",
    "div[data-plugin]",
    "a[href*='/plugins/']"
]
```

### Data Extraction
- **Plugin URL**: Extract author/name from href
- **Display Name**: h3, h4, or elements with title class
- **Description**: p tags or description class
- **Category**: Elements with category/tag classes
- **Version**: Elements with version class, regex extraction

## Error Handling

### Retry Logic
- **Attempts**: 3 times
- **Delay**: Exponential backoff (1s, 2s, 3s)
- **Timeout**: 30 seconds per request

### Graceful Degradation
1. Try primary API endpoint
2. Try alternative API endpoint
3. Fall back to web scraping
4. Return cached data if available
5. Return empty result with error info

## Performance Considerations

### Optimization Strategies
- Cache all successful responses
- Parallel requests where possible
- Early termination on selector matches
- Minimal DOM traversal

### Load Management
- Respect rate limits
- Use caching to reduce requests
- Implement request queuing if needed

## Testing

### Unit Tests
```bash
pytest tests/test_marketplace_scraper.py -v
```

### Test Coverage
- Cache operations
- HTML parsing
- Fallback mechanisms
- Error scenarios
- Integration with MarketplaceService

## Monitoring

### Logging
- Info: Successful operations, cache hits
- Warning: Fallback triggers, parsing issues
- Error: Request failures, parsing errors

### Metrics to Track
- Fallback usage rate
- Cache hit rate
- Average response time
- Parsing success rate

## Future Enhancements

1. **Headless Browser Support**: For JavaScript-rendered content
2. **Proxy Support**: For rate limit management
3. **Custom Parsers**: Plugin-specific parsing rules
4. **Webhook Notifications**: Alert on API changes
5. **A/B Testing**: Compare API vs scraping results

## Troubleshooting

### Common Issues

1. **No plugins found**
   - Check network connectivity
   - Verify marketplace URL
   - Check HTML structure changes

2. **Parsing errors**
   - Enable debug logging
   - Check selector patterns
   - Verify HTML structure

3. **Cache issues**
   - Check Redis connectivity
   - Clear cache if corrupted
   - Verify cache key generation

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

- Sanitize scraped content
- Validate URLs before requests
- Implement request throttling
- Use HTTPS only
- No credential storage in cache