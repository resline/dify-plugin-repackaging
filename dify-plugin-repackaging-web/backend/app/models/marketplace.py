from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class PluginVersion(BaseModel):
    """Version information for a plugin"""
    version: str = Field(..., description="Version string (e.g., '1.0.0')")
    created_at: datetime = Field(..., description="Release date")
    changelog: Optional[str] = Field(None, description="Version changelog")
    download_count: Optional[int] = Field(0, description="Number of downloads")


class PluginAuthor(BaseModel):
    """Plugin author information"""
    name: str = Field(..., description="Author username/identifier")
    display_name: Optional[str] = Field(None, description="Author display name")
    avatar_url: Optional[str] = Field(None, description="Author avatar URL")


class Plugin(BaseModel):
    """Plugin metadata from marketplace"""
    name: str = Field(..., description="Plugin identifier name")
    author: str = Field(..., description="Plugin author username")
    display_name: str = Field(..., description="Plugin display name")
    description: str = Field(..., description="Plugin description")
    category: str = Field(..., description="Plugin category")
    tags: List[str] = Field(default_factory=list, description="Plugin tags")
    latest_version: str = Field(..., description="Latest version string")
    icon_url: Optional[str] = Field(None, description="Plugin icon URL")
    created_at: datetime = Field(..., description="Plugin creation date")
    updated_at: datetime = Field(..., description="Last update date")
    download_count: Optional[int] = Field(0, description="Total download count")
    rating: Optional[float] = Field(None, description="Average rating (0-5)")
    verified: bool = Field(False, description="Whether plugin is verified")


class PluginDetails(Plugin):
    """Detailed plugin information including versions"""
    readme: Optional[str] = Field(None, description="Plugin README content")
    license: Optional[str] = Field(None, description="Plugin license")
    homepage_url: Optional[str] = Field(None, description="Plugin homepage URL")
    repository_url: Optional[str] = Field(None, description="Repository URL")
    available_versions: List[PluginVersion] = Field(default_factory=list, description="Available versions")
    dependencies: Optional[Dict[str, str]] = Field(None, description="Plugin dependencies")
    screenshots: Optional[List[str]] = Field(None, description="Screenshot URLs")


class PluginSearchResult(BaseModel):
    """Search results from marketplace"""
    plugins: List[Plugin] = Field(..., description="List of plugins")
    total: int = Field(..., description="Total number of results")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Results per page")
    has_more: bool = Field(False, description="Whether more results are available")


class MarketplaceCategory(BaseModel):
    """Marketplace category information"""
    id: str = Field(..., description="Category identifier")
    name: str = Field(..., description="Category display name")
    description: Optional[str] = Field(None, description="Category description")
    icon: Optional[str] = Field(None, description="Category icon identifier")
    plugin_count: Optional[int] = Field(0, description="Number of plugins in category")


class MarketplaceStats(BaseModel):
    """Marketplace statistics"""
    total_plugins: int = Field(0, description="Total number of plugins")
    total_downloads: int = Field(0, description="Total downloads across all plugins")
    categories: List[MarketplaceCategory] = Field(default_factory=list, description="Available categories")


class PluginDownloadInfo(BaseModel):
    """Information for downloading a plugin"""
    download_url: str = Field(..., description="Direct download URL")
    plugin: Dict[str, str] = Field(..., description="Plugin metadata (author, name, version)")
    size: Optional[int] = Field(None, description="File size in bytes")
    checksum: Optional[str] = Field(None, description="File checksum")


class MarketplacePluginMetadata(BaseModel):
    """Metadata to include in WebSocket messages for marketplace plugins"""
    source: str = Field("marketplace", description="Source of the plugin")
    author: str = Field(..., description="Plugin author")
    name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version")
    display_name: Optional[str] = Field(None, description="Plugin display name")
    category: Optional[str] = Field(None, description="Plugin category")
    icon_url: Optional[str] = Field(None, description="Plugin icon URL")