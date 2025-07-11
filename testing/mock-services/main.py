"""
Mock external services for integration testing.
"""
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Optional

app = FastAPI(title="Mock External Services")

# Mock plugin data
MOCK_PLUGINS = [
    {
        "author": "test-author",
        "name": "test-plugin",
        "version": "1.0.0",
        "description": "A test plugin for integration testing",
        "download_url": "http://mock-services:8000/download/test-plugin-1.0.0.difypkg"
    },
    {
        "author": "another-author",
        "name": "another-plugin",
        "version": "2.0.0",
        "description": "Another test plugin",
        "download_url": "http://mock-services:8000/download/another-plugin-2.0.0.difypkg"
    }
]

# Mock GitHub releases
MOCK_RELEASES = [
    {
        "tag_name": "v1.0.0",
        "name": "Release 1.0.0",
        "assets": [
            {
                "name": "plugin.difypkg",
                "browser_download_url": "http://mock-services:8000/github/download/plugin.difypkg"
            }
        ]
    }
]


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mock-services"}


@app.get("/marketplace/plugins")
async def list_marketplace_plugins(search: Optional[str] = None):
    """Mock marketplace plugin listing."""
    plugins = MOCK_PLUGINS
    
    if search:
        plugins = [p for p in plugins if search.lower() in p["name"].lower() or search.lower() in p["description"].lower()]
    
    return {"plugins": plugins, "total": len(plugins)}


@app.get("/marketplace/plugins/{author}/{name}/{version}")
async def get_marketplace_plugin(author: str, name: str, version: str):
    """Mock getting specific plugin details."""
    for plugin in MOCK_PLUGINS:
        if plugin["author"] == author and plugin["name"] == name and plugin["version"] == version:
            return plugin
    
    raise HTTPException(status_code=404, detail="Plugin not found")


@app.get("/download/{filename}")
async def download_mock_plugin(filename: str):
    """Mock plugin download."""
    # Create a mock .difypkg file
    with tempfile.NamedTemporaryFile(suffix=".difypkg", delete=False) as tmp:
        # Write mock plugin content
        tmp.write(b"PK")  # ZIP file header
        tmp.write(b"\x03\x04")  # More ZIP headers
        tmp.write(b"Mock plugin content for: " + filename.encode())
        tmp_path = tmp.name
    
    try:
        return FileResponse(
            tmp_path,
            media_type="application/octet-stream",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    finally:
        # Clean up temp file after response
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.get("/github/repos/{owner}/{repo}/releases")
async def list_github_releases(owner: str, repo: str):
    """Mock GitHub releases listing."""
    return MOCK_RELEASES


@app.get("/github/repos/{owner}/{repo}/releases/tags/{tag}")
async def get_github_release_by_tag(owner: str, repo: str, tag: str):
    """Mock getting GitHub release by tag."""
    for release in MOCK_RELEASES:
        if release["tag_name"] == tag:
            return release
    
    raise HTTPException(status_code=404, detail="Release not found")


@app.get("/github/download/{filename}")
async def download_github_asset(filename: str):
    """Mock GitHub asset download."""
    return await download_mock_plugin(filename)


# Simulate API errors for testing error handling
@app.get("/marketplace/error/{error_code}")
async def simulate_error(error_code: int):
    """Simulate various HTTP errors for testing."""
    if error_code == 500:
        raise HTTPException(status_code=500, detail="Internal server error")
    elif error_code == 503:
        raise HTTPException(status_code=503, detail="Service unavailable")
    elif error_code == 429:
        return Response(
            status_code=429,
            content="Rate limit exceeded",
            headers={"Retry-After": "60"}
        )
    else:
        raise HTTPException(status_code=error_code, detail=f"Simulated error {error_code}")


# Simulate slow responses for timeout testing
@app.get("/slow/{delay_seconds}")
async def slow_response(delay_seconds: int):
    """Simulate slow API response."""
    import asyncio
    await asyncio.sleep(min(delay_seconds, 30))  # Cap at 30 seconds
    return {"message": f"Response after {delay_seconds} seconds"}


# Mock webhook endpoint for testing callbacks
@app.post("/webhook/task-complete")
async def webhook_callback(data: Dict):
    """Mock webhook endpoint for task completion callbacks."""
    return {
        "received": True,
        "task_id": data.get("task_id"),
        "timestamp": datetime.utcnow().isoformat()
    }