# Marketplace Integration Implementation

This document describes the marketplace integration implementation for the Dify Plugin Repackaging tool.

## Overview

The integration enables seamless repackaging of plugins directly from the Dify Marketplace, while maintaining backward compatibility with direct URL downloads.

## Implementation Details

### 1. Shared Types/Interfaces

#### Backend (Pydantic Models)
- **Location**: `backend/app/models/marketplace.py`
- **Models**:
  - `Plugin`: Basic plugin metadata
  - `PluginDetails`: Extended plugin information with versions
  - `PluginVersion`: Version-specific information
  - `PluginSearchResult`: Search response structure
  - `MarketplacePluginMetadata`: WebSocket message metadata

#### Frontend (TypeScript Interfaces)
- **Location**: `frontend/src/types/marketplace.ts`
- **Interfaces**: Exact TypeScript equivalents of backend models
- **WebSocket Types**: `MarketplaceSelectionMessage`, `TaskProgressMessage`

### 2. WebSocket Enhancement

- **Updated**: `backend/app/api/websocket.py`
- **Features**:
  - Task progress messages now include `marketplace_metadata` field
  - Added `broadcast_marketplace_selection()` for plugin selection events
  - Support for marketplace-specific message types

### 3. Celery Task Updates

- **Updated**: `backend/app/workers/celery_app.py`
- **New Task**: `process_marketplace_repackaging()`
  - Specialized task for marketplace plugins
  - Includes metadata in all status updates
  - Builds download URL automatically
- **Enhanced**: `update_task_status()` now accepts `marketplace_metadata`

### 4. API Endpoints

#### Task Creation
- **Unified Endpoint**: `POST /api/v1/tasks`
  - Supports both `url` and `marketplace_plugin` fields
  - Automatically detects mode and uses appropriate Celery task
  - Maintains full backward compatibility

- **Convenience Endpoint**: `POST /api/v1/tasks/marketplace`
  - Direct marketplace task creation
  - Cleaner API for marketplace-only use cases

#### Marketplace Endpoints
- `GET /api/v1/marketplace/plugins` - Search plugins
- `GET /api/v1/marketplace/plugins/{author}/{name}` - Get plugin details
- `GET /api/v1/marketplace/plugins/{author}/{name}/versions` - List versions
- `GET /api/v1/marketplace/categories` - Get categories
- `POST /api/v1/marketplace/plugins/{author}/{name}/{version}/download-url` - Get download URL

### 5. Integration Tests

- **Location**: `backend/tests/test_marketplace_integration.py`
- **Coverage**:
  - Full flow: search → select → repackage → download
  - WebSocket metadata propagation
  - Backward compatibility with URLs
  - Error handling
  - Mock-based unit tests

- **Manual Test**: `backend/tests/test_integration_manual.py`
  - Live integration testing script
  - Tests all endpoints and flows

## Usage Examples

### Marketplace Plugin Repackaging

```python
# Using unified endpoint
response = requests.post("/api/v1/tasks", json={
    "marketplace_plugin": {
        "author": "langgenius",
        "name": "agent",
        "version": "0.0.9"
    },
    "platform": "manylinux2014_x86_64",
    "suffix": "offline"
})

# Using convenience endpoint
response = requests.post("/api/v1/tasks/marketplace", json={
    "author": "langgenius",
    "name": "agent",
    "version": "0.0.9",
    "platform": "manylinux2014_x86_64",
    "suffix": "offline"
})
```

### Direct URL (Backward Compatible)

```python
response = requests.post("/api/v1/tasks", json={
    "url": "https://github.com/example/plugin/releases/download/v1.0.0/plugin.difypkg",
    "platform": "manylinux2014_x86_64",
    "suffix": "offline"
})
```

### WebSocket with Marketplace Metadata

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tasks/123-456');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.marketplace_metadata) {
        console.log(`Processing ${data.marketplace_metadata.display_name}`);
        console.log(`From: ${data.marketplace_metadata.author}`);
        console.log(`Version: ${data.marketplace_metadata.version}`);
    }
};
```

## Architecture Benefits

1. **Seamless Integration**: Frontend can display rich plugin information during repackaging
2. **Backward Compatible**: Existing URL-based flows continue to work unchanged
3. **Metadata Propagation**: Plugin information flows through the entire pipeline
4. **Type Safety**: Shared types ensure frontend/backend consistency
5. **Extensible**: Easy to add new marketplace features without breaking changes

## Testing

Run integration tests:
```bash
cd backend
pytest tests/test_marketplace_integration.py -v

# Or run manual integration test
python tests/test_integration_manual.py
```

## Future Enhancements

1. Add plugin rating/review integration
2. Support batch repackaging of multiple plugins
3. Add plugin dependency resolution
4. Implement plugin update notifications
5. Add marketplace authentication for private plugins