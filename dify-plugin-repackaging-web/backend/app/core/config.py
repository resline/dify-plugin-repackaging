from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Dify Plugin Repackaging Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost", "https://localhost"]
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # File handling
    MAX_FILE_SIZE: int = 524288000  # 500MB
    TEMP_DIR: str = "/app/temp"
    SCRIPTS_DIR: str = "/app/scripts"
    FILE_RETENTION_HOURS: int = 24
    
    # Security
    RATE_LIMIT_PER_MINUTE: int = 10
    ALLOWED_DOWNLOAD_DOMAINS: list[str] = [
        "github.com",
        "githubusercontent.com", 
        "marketplace.dify.ai",
        "dify.ai"
    ]
    
    # Marketplace
    MARKETPLACE_API_URL: str = "https://marketplace.dify.ai"
    MARKETPLACE_CACHE_TTL: int = 3600  # 1 hour in seconds
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()