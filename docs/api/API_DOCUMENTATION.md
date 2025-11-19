# Dify Plugin Repackaging API Documentation

## Overview

The Dify Plugin Repackaging API provides endpoints for repackaging Dify plugins with their dependencies for offline installation. It supports both direct URL downloads and integration with the Dify Marketplace.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API does not require authentication but implements rate limiting.

## Rate Limiting

- Default: 10 requests per minute per IP address
- Rate limit headers are included in responses

## Endpoints

### Task Management

#### Create Repackaging Task

**POST** `/tasks`

Creates a new repackaging task. Supports both direct URL and marketplace plugin modes.

##### Request Body

**Option 1: Direct URL Mode**
```json
{
    "url": "https://example.com/plugin.difypkg",
    "platform": "manylinux2014_x86_64",
    "suffix": "offline"
}
```

**Option 2: Marketplace Mode**
```json
{
    "marketplace_plugin": {
        "author": "langgenius",
        "name": "agent",
        "version": "0.0.9"
    },
    "platform": "manylinux2014_x86_64",
    "suffix": "offline"
}
```

##### Parameters

- `url` (string, optional): Direct URL to .difypkg file
- `marketplace_plugin` (object, optional): Marketplace plugin details
  - `author` (string, required): Plugin author username
  - `name` (string, required): Plugin name
  - `version` (string, required): Plugin version
- `platform` (string, optional): Target platform. Options:
  - `manylinux2014_x86_64`
  - `manylinux2014_aarch64`
  - `manylinux_2_17_x86_64`
  - `manylinux_2_17_aarch64`
  - `macosx_10_9_x86_64`
  - `macosx_11_0_arm64`
  - `""` (empty string for auto-detect)
- `suffix` (string, optional): Output file suffix (default: "offline")

##### Response

```json
{
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "pending",
    "created_at": "2024-01-01T00:00:00Z",
    "progress": 0
}
```

#### Create Marketplace Task (Convenience Endpoint)

**POST** `/tasks/marketplace`

Creates a repackaging task specifically for marketplace plugins.

##### Request Body

```json
{
    "author": "langgenius",
    "name": "agent",
    "version": "0.0.9",
    "platform": "manylinux2014_x86_64",
    "suffix": "offline"
}
```

##### Response

Same as `/tasks` endpoint.

#### Get Task Status

**GET** `/tasks/{task_id}`

Retrieves the current status of a repackaging task.

##### Response

```json
{
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "completed",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:05:00Z",
    "completed_at": "2024-01-01T00:10:00Z",
    "progress": 100,
    "download_url": "/api/v1/tasks/123e4567-e89b-12d3-a456-426614174000/download",
    "original_filename": "agent.difypkg",
    "output_filename": "agent-offline.difypkg"
}
```

##### Status Values

- `pending`: Task queued
- `downloading`: Downloading plugin
- `processing`: Repackaging in progress
- `completed`: Successfully completed
- `failed`: Task failed (check `error` field)

#### Download Result

**GET** `/tasks/{task_id}/download`

Downloads the repackaged plugin file.

##### Response

Binary file download with appropriate headers.

#### List Recent Tasks

**GET** `/tasks`

Lists recent tasks (limited functionality for demo).

##### Query Parameters

- `limit` (integer, optional): Number of tasks to return (default: 10)

### Marketplace Integration

#### Search Plugins

**GET** `/marketplace/plugins`

Search for plugins in the Dify Marketplace.

##### Query Parameters

- `q` (string, optional): Search query
- `author` (string, optional): Filter by author
- `category` (string, optional): Filter by category
- `page` (integer, optional): Page number (default: 1)
- `per_page` (integer, optional): Results per page (default: 20, max: 100)

##### Response

```json
{
    "plugins": [
        {
            "name": "agent",
            "author": "langgenius",
            "display_name": "Agent Plugin",
            "description": "Enables agent capabilities",
            "category": "agent",
            "tags": ["agent", "llm"],
            "latest_version": "0.0.9",
            "icon_url": "https://...",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-15T00:00:00Z",
            "download_count": 1234,
            "rating": 4.5,
            "verified": true
        }
    ],
    "total": 25,
    "page": 1,
    "per_page": 20,
    "has_more": true
}
```

#### Get Plugin Details

**GET** `/marketplace/plugins/{author}/{name}`

Get detailed information about a specific plugin.

##### Response

```json
{
    "name": "agent",
    "author": "langgenius",
    "display_name": "Agent Plugin",
    "description": "Enables agent capabilities in Dify",
    "category": "agent",
    "tags": ["agent", "llm", "ai"],
    "latest_version": "0.0.9",
    "icon_url": "https://...",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T00:00:00Z",
    "download_count": 1234,
    "rating": 4.5,
    "verified": true,
    "readme": "# Agent Plugin\n\nThis plugin enables...",
    "license": "MIT",
    "homepage_url": "https://github.com/langgenius/agent",
    "repository_url": "https://github.com/langgenius/agent",
    "available_versions": [
        {
            "version": "0.0.9",
            "created_at": "2024-01-15T00:00:00Z",
            "changelog": "Bug fixes and improvements"
        },
        {
            "version": "0.0.8",
            "created_at": "2024-01-01T00:00:00Z",
            "changelog": "Initial release"
        }
    ],
    "dependencies": {
        "requests": ">=2.25.0",
        "pydantic": ">=2.0.0"
    },
    "screenshots": [
        "https://..."
    ]
}
```

#### Get Plugin Versions

**GET** `/marketplace/plugins/{author}/{name}/versions`

Get all available versions for a plugin.

##### Response

```json
{
    "versions": [
        {
            "version": "0.0.9",
            "created_at": "2024-01-15T00:00:00Z",
            "changelog": "Bug fixes and improvements",
            "download_count": 500
        },
        {
            "version": "0.0.8",
            "created_at": "2024-01-01T00:00:00Z",
            "changelog": "Initial release",
            "download_count": 734
        }
    ]
}
```

#### Get Categories

**GET** `/marketplace/categories`

Get list of available plugin categories.

##### Response

```json
{
    "categories": [
        {
            "id": "agent",
            "name": "Agent",
            "description": "Agent-related plugins",
            "icon": "robot",
            "plugin_count": 15
        },
        {
            "id": "tool",
            "name": "Tool",
            "description": "Tool plugins for various tasks",
            "icon": "wrench",
            "plugin_count": 42
        }
    ]
}
```

#### Get Download URL

**POST** `/marketplace/plugins/{author}/{name}/{version}/download-url`

Get the download URL for a specific plugin version.

##### Response

```json
{
    "download_url": "https://marketplace.dify.ai/api/v1/plugins/langgenius/agent/0.0.9/download",
    "plugin": {
        "author": "langgenius",
        "name": "agent",
        "version": "0.0.9"
    }
}
```

## WebSocket API

### Task Progress Updates

**WebSocket** `/ws/tasks/{task_id}`

Connect to receive real-time updates for a specific task.

#### Message Types

##### Task Progress Update
```json
{
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "processing",
    "progress": 50,
    "message": "Processing dependencies...",
    "updated_at": "2024-01-01T00:05:00Z",
    "marketplace_metadata": {
        "source": "marketplace",
        "author": "langgenius",
        "name": "agent",
        "version": "0.0.9",
        "display_name": "Agent Plugin",
        "category": "agent",
        "icon_url": "https://..."
    }
}
```

##### Heartbeat
```json
{
    "type": "heartbeat"
}
```

## Error Responses

### 400 Bad Request
```json
{
    "detail": "URL must point to a .difypkg file"
}
```

### 404 Not Found
```json
{
    "detail": "Task not found"
}
```

### 429 Too Many Requests
```json
{
    "detail": "Rate limit exceeded. Please try again later."
}
```

### 500 Internal Server Error
```json
{
    "detail": "Internal server error message"
}
```

## Examples

### Example 1: Repackage from Direct URL

```bash
# Create task
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/example/plugin/releases/download/v1.0.0/plugin.difypkg",
    "platform": "manylinux2014_x86_64",
    "suffix": "offline"
  }'

# Check status
curl http://localhost:8000/api/v1/tasks/123e4567-e89b-12d3-a456-426614174000

# Download result
curl -O http://localhost:8000/api/v1/tasks/123e4567-e89b-12d3-a456-426614174000/download
```

### Example 2: Repackage from Marketplace

```bash
# Search for plugins
curl "http://localhost:8000/api/v1/marketplace/plugins?q=agent&page=1"

# Create task for marketplace plugin
curl -X POST http://localhost:8000/api/v1/tasks/marketplace \
  -H "Content-Type: application/json" \
  -d '{
    "author": "langgenius",
    "name": "agent",
    "version": "0.0.9",
    "platform": "manylinux2014_x86_64"
  }'
```

### Example 3: WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tasks/123e4567-e89b-12d3-a456-426614174000');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type !== 'heartbeat') {
        console.log('Task update:', data);
        if (data.marketplace_metadata) {
            console.log('Marketplace plugin:', data.marketplace_metadata);
        }
    }
};
```