"""
Application configuration module.

Loads settings from environment variables using Pydantic Settings.
Provides type-safe configuration with validation.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application metadata
    app_name: str = "DeadDrop"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Storage configuration
    storage_path: str = "./storage"
    max_file_size: int = 52428800  # 50MB in bytes (50 * 1024 * 1024)
    
    # Redis configuration
    redis_url: str = "redis://localhost:6379"
    
    # CORS configuration (comma-separated origins in env var)
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # TTL options (in seconds)
    ttl_1_hour: int = 3600
    ttl_1_day: int = 86400
    ttl_3_days: int = 259200
    
    # Download limits
    min_downloads: int = 1
    max_downloads: int = 5
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    @property
    def allowed_ttls(self) -> List[int]:
        """Get list of allowed TTL values."""
        return [self.ttl_1_hour, self.ttl_1_day, self.ttl_3_days]


# Global settings instance
settings = Settings()
