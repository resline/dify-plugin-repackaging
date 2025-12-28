from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
from enum import Enum
import re


class TaskStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Platform(str, Enum):
    MANYLINUX2014_X86_64 = "manylinux2014_x86_64"
    MANYLINUX2014_AARCH64 = "manylinux2014_aarch64"
    MANYLINUX_2_17_X86_64 = "manylinux_2_17_x86_64"
    MANYLINUX_2_17_AARCH64 = "manylinux_2_17_aarch64"
    MACOSX_10_9_X86_64 = "macosx_10_9_x86_64"
    MACOSX_11_0_ARM64 = "macosx_11_0_arm64"
    DEFAULT = ""


class TaskCreate(BaseModel):
    url: HttpUrl = Field(..., description="URL to the .difypkg file")
    platform: Platform = Field(Platform.DEFAULT, description="Target platform for repackaging")
    suffix: str = Field("offline", description="Suffix for the output file")

    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v: Platform) -> Platform:
        """Validate platform against whitelist of allowed values"""
        allowed_platforms = {
            Platform.DEFAULT,
            Platform.MANYLINUX2014_X86_64,
            Platform.MANYLINUX2014_AARCH64,
            Platform.MANYLINUX_2_17_X86_64,
            Platform.MANYLINUX_2_17_AARCH64,
            Platform.MACOSX_10_9_X86_64,
            Platform.MACOSX_11_0_ARM64
        }
        if v not in allowed_platforms:
            raise ValueError(f"Platform must be one of: {', '.join(p.value for p in allowed_platforms)}")
        return v

    @field_validator('suffix')
    @classmethod
    def validate_suffix(cls, v: str) -> str:
        """Validate suffix to prevent command injection"""
        if not v:
            raise ValueError("Suffix cannot be empty")
        if len(v) > 50:
            raise ValueError("Suffix must be 50 characters or less")
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Suffix can only contain alphanumeric characters, underscores, and hyphens")
        return v


class MarketplaceTaskCreate(BaseModel):
    author: str = Field(..., description="Plugin author")
    name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version")
    platform: Platform = Field(Platform.DEFAULT, description="Target platform for repackaging")
    suffix: str = Field("offline", description="Suffix for the output file")

    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v: Platform) -> Platform:
        """Validate platform against whitelist of allowed values"""
        allowed_platforms = {
            Platform.DEFAULT,
            Platform.MANYLINUX2014_X86_64,
            Platform.MANYLINUX2014_AARCH64,
            Platform.MANYLINUX_2_17_X86_64,
            Platform.MANYLINUX_2_17_AARCH64,
            Platform.MACOSX_10_9_X86_64,
            Platform.MACOSX_11_0_ARM64
        }
        if v not in allowed_platforms:
            raise ValueError(f"Platform must be one of: {', '.join(p.value for p in allowed_platforms)}")
        return v

    @field_validator('suffix')
    @classmethod
    def validate_suffix(cls, v: str) -> str:
        """Validate suffix to prevent command injection"""
        if not v:
            raise ValueError("Suffix cannot be empty")
        if len(v) > 50:
            raise ValueError("Suffix must be 50 characters or less")
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Suffix can only contain alphanumeric characters, underscores, and hyphens")
        return v


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    progress: int = Field(0, ge=0, le=100)
    download_url: Optional[str] = None
    original_filename: Optional[str] = None
    output_filename: Optional[str] = None


class TaskProgress(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int
    message: str
    timestamp: datetime