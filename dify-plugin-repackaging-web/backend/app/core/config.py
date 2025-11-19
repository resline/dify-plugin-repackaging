from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, Union
import os
import json


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Dify Plugin Repackaging Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # API
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: Union[str, list[str]] = ["http://localhost:3000", "http://localhost", "https://localhost"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, list[str]]) -> Union[str, list[str]]:
        if isinstance(v, str) and not v.startswith("["):
            # If it's a simple string, split by commas
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            # If it's a JSON string, parse it
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If parsing fails, try to fix common issues
                # Remove problematic characters and try again
                v_cleaned = v.strip()
                if v_cleaned.startswith('[""'):
                    # Handle case where it's an empty array with quotes
                    return []
                return [i.strip() for i in v.split(",")]
        return v

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None  # Redis password for authentication

    @field_validator("REDIS_URL", mode="after")
    @classmethod
    def assemble_redis_url(cls, v: str) -> str:
        """
        Ensure REDIS_URL includes password if REDIS_PASSWORD is set.
        This validator runs after REDIS_PASSWORD is set.
        """
        # Note: This is handled in get_redis_url() method below
        return v

    def get_redis_url(self) -> str:
        """
        Get Redis URL with password if configured.
        Returns properly formatted Redis URL.
        """
        if self.REDIS_PASSWORD:
            # Parse existing URL and inject password
            if "://" in self.REDIS_URL:
                protocol, rest = self.REDIS_URL.split("://", 1)
                # Remove any existing password
                if "@" in rest:
                    rest = rest.split("@", 1)[1]
                return f"{protocol}://:{self.REDIS_PASSWORD}@{rest}"
            else:
                return self.REDIS_URL
        return self.REDIS_URL

    # File handling
    MAX_FILE_SIZE: int = 524288000  # 500MB
    TEMP_DIR: str = "/app/temp"
    SCRIPTS_DIR: str = "/app/scripts"
    FILE_RETENTION_HOURS: int = 24
    FILE_RETENTION_DAYS: int = 7  # Retention period for completed files

    # Security
    SECRET_KEY: Optional[str] = None  # Secret key for sessions and cryptographic operations
    RATE_LIMIT_PER_MINUTE: int = 30
    ALLOWED_DOWNLOAD_DOMAINS: list[str] = [
        "github.com",
        "githubusercontent.com",
        "marketplace.dify.ai",
        "dify.ai"
    ]

    # Marketplace
    MARKETPLACE_API_URL: str = "https://marketplace.dify.ai"
    MARKETPLACE_CACHE_TTL: int = 3600  # 1 hour in seconds

    # External APIs
    GITHUB_API_URL: str = "https://github.com"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    def get_celery_broker_url(self) -> str:
        """Get Celery broker URL with password if configured."""
        if self.REDIS_PASSWORD:
            if "://" in self.CELERY_BROKER_URL:
                protocol, rest = self.CELERY_BROKER_URL.split("://", 1)
                if "@" in rest:
                    rest = rest.split("@", 1)[1]
                return f"{protocol}://:{self.REDIS_PASSWORD}@{rest}"
        return self.CELERY_BROKER_URL

    def get_celery_result_backend(self) -> str:
        """Get Celery result backend URL with password if configured."""
        if self.REDIS_PASSWORD:
            if "://" in self.CELERY_RESULT_BACKEND:
                protocol, rest = self.CELERY_RESULT_BACKEND.split("://", 1)
                if "@" in rest:
                    rest = rest.split("@", 1)[1]
                return f"{protocol}://:{self.REDIS_PASSWORD}@{rest}"
        return self.CELERY_RESULT_BACKEND

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30

    # HTTP Client
    HTTP_TIMEOUT: float = 30.0
    HTTP_CONNECT_TIMEOUT: float = 10.0
    HTTP_READ_TIMEOUT: float = 60.0
    HTTP_WRITE_TIMEOUT: float = 30.0
    HTTP_POOL_TIMEOUT: float = 10.0

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()