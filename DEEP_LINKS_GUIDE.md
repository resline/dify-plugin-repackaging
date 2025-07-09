# Deep Links Guide for Dify Plugin Repackaging

## Overview

The application now supports deep links to automatically process plugins from the Dify Marketplace. This allows users to directly share links that will pre-fill the form or automatically start processing.

## Supported URL Formats

### 1. Direct Plugin URL Parameter
```
https://dify-plugin.resline.net/?plugin=https://marketplace.dify.ai/plugins/langgenius/ollama
```
This will:
- Switch to the URL tab
- Pre-fill the URL field
- Auto-start processing if the URL is valid

### 2. Individual Plugin Parameters
```
https://dify-plugin.resline.net/?author=langgenius&name=ollama
https://dify-plugin.resline.net/?author=langgenius&name=ollama&version=0.0.9
```
This will:
- Switch to the marketplace tab
- Auto-start processing with the specified plugin
- Use latest version if version parameter is not provided

## Marketplace URL Format Support

The application now supports multiple marketplace URL formats:

### Supported Formats:
- `https://marketplace.dify.ai/plugins/langgenius/ollama`
- `http://marketplace.dify.ai/plugins/langgenius/ollama/`
- `marketplace.dify.ai/plugins/langgenius/ollama` (without protocol)
- `https://marketplace.dify.ai/plugin/langgenius/ollama` (singular form)
- URLs with query parameters: `?source=...` etc.

### Auto-detection Features:
- Automatically detects marketplace URLs and fetches the latest version
- Handles URLs with or without trailing slashes
- Supports both HTTP and HTTPS protocols
- Automatically adds HTTPS if protocol is missing

## Error Handling

The application provides detailed error messages for common issues:

1. **Plugin Not Found**: Clear message indicating the plugin doesn't exist
2. **API Unavailable**: Suggests using direct .difypkg URLs as fallback
3. **Invalid URL Format**: Shows expected format with examples

## API Endpoints

### Parse Marketplace URL (for debugging)
```bash
curl -X POST "https://dify-plugin.resline.net/api/v1/marketplace/parse-url?url=https://marketplace.dify.ai/plugins/langgenius/ollama"
```

Response:
```json
{
  "valid": true,
  "author": "langgenius",
  "name": "ollama",
  "latest_version": "0.0.9",
  "download_url": "https://marketplace.dify.ai/api/v1/plugins/langgenius/ollama/0.0.9/download"
}
```

## Implementation Details

### Frontend Changes:
1. **useDeepLink Hook**: Handles URL parameter parsing and auto-submission
2. **Enhanced URL Validation**: Supports marketplace URLs with or without protocol
3. **Auto-tab Selection**: Automatically switches to appropriate tab based on deep link

### Backend Changes:
1. **Improved URL Parsing**: More flexible regex patterns for marketplace URLs
2. **Better Version Detection**: Multiple API format attempts for compatibility
3. **Enhanced Error Messages**: Detailed troubleshooting information

## Testing Deep Links

1. **Test marketplace URL detection**:
   ```
   https://dify-plugin.resline.net/?plugin=marketplace.dify.ai/plugins/langgenius/agent
   ```

2. **Test direct parameters**:
   ```
   https://dify-plugin.resline.net/?author=langgenius&name=agent&version=0.0.9
   ```

3. **Test auto-processing**:
   ```
   https://dify-plugin.resline.net/?plugin=https://github.com/user/repo/releases/download/v1.0/plugin.difypkg
   ```

## Troubleshooting

### Common Issues:

1. **"Unable to fetch plugin version"**
   - Verify the plugin exists in the marketplace
   - Check if the marketplace API is accessible
   - Try using a direct .difypkg URL instead

2. **URL not recognized as marketplace URL**
   - Ensure the URL follows the format: `marketplace.dify.ai/plugins/{author}/{name}`
   - Remove any extra path segments or version numbers
   - Use the parse-url API endpoint to debug

3. **Deep link not working**
   - Check browser console for JavaScript errors
   - Ensure URL parameters are properly encoded
   - Verify the application is fully loaded before deep link processing