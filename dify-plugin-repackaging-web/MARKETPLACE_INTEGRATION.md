# Marketplace Integration Documentation

## Overview

The Dify Plugin Repackaging web application now includes integrated marketplace browsing capabilities, allowing users to search and select plugins directly from the Dify Marketplace without needing to manually construct URLs.

## New Features

### 1. Marketplace Browser Component
- **Search Functionality**: Search plugins by name or keywords
- **Category Filtering**: Filter plugins by category (agent, tool, model, extension, workflow)
- **Version Selection**: Choose from available versions for each plugin
- **Pagination**: Browse through multiple pages of results
- **Plugin Details**: View plugin metadata including author, description, and latest version

### 2. Dual-Mode Interface
The upload form now supports two modes:
- **Direct URL Mode**: Original functionality for pasting .difypkg URLs
- **Browse Marketplace Mode**: New marketplace browser interface

### 3. Backend API Endpoints

#### Marketplace Endpoints
- `GET /api/v1/marketplace/plugins` - Search/list plugins with filtering
- `GET /api/v1/marketplace/plugins/{author}/{name}` - Get plugin details
- `GET /api/v1/marketplace/plugins/{author}/{name}/versions` - Get available versions
- `GET /api/v1/marketplace/categories` - Get plugin categories
- `POST /api/v1/marketplace/plugins/{author}/{name}/{version}/download-url` - Get download URL

#### Enhanced Task Creation
- `POST /api/v1/tasks/marketplace` - Create task directly from marketplace plugin reference

## Architecture Changes

### Backend Services
1. **MarketplaceService** (`backend/app/services/marketplace.py`)
   - Handles all marketplace API interactions
   - Implements caching with 5-minute TTL
   - Provides search, details, and version listing

2. **Enhanced Task Model** (`backend/app/models/task.py`)
   - Added `MarketplaceTaskCreate` model for marketplace-based tasks
   - Maintains backward compatibility with URL-based tasks

### Frontend Components
1. **MarketplaceBrowser** (`frontend/src/components/MarketplaceBrowser.jsx`)
   - Full-featured marketplace browsing interface
   - Grid layout for plugin cards
   - Interactive selection and version management

2. **Updated UploadForm** (`frontend/src/components/UploadForm.jsx`)
   - Mode toggle between Direct URL and Marketplace
   - Integrated marketplace browser
   - Maintains all existing functionality

### API Integration
- New `marketplaceService` in `frontend/src/services/api.js`
- Handles all marketplace-related API calls
- Maintains separation from task service

## Configuration

The marketplace API URL is configurable via environment variable:
```env
MARKETPLACE_API_URL=https://marketplace.dify.ai
```

## Usage Flow

1. User clicks "Browse Marketplace" mode
2. Searches or browses available plugins
3. Selects a plugin and chooses version
4. Clicks "Repackage Plugin" 
5. System automatically constructs download URL
6. Repackaging proceeds as normal
7. User downloads the offline-packaged plugin

## Benefits

1. **Improved UX**: No need to manually construct or find download URLs
2. **Discovery**: Users can browse and discover plugins
3. **Version Management**: Easy selection of specific plugin versions
4. **Validation**: Only valid marketplace plugins can be selected
5. **Metadata**: Plugin information is preserved throughout the process

## Security Considerations

- Marketplace API calls are read-only
- Download URLs are validated against allowed domains
- Rate limiting applies to all endpoints
- No authentication required for public marketplace data

## Future Enhancements

Potential improvements for future iterations:
1. Plugin preview/details modal
2. Favoriting/bookmarking plugins
3. Search history
4. Bulk repackaging of multiple plugins
5. Plugin compatibility checking
6. Integration with private/enterprise marketplaces