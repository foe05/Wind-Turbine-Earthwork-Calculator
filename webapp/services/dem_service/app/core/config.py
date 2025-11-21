"""
Configuration for DEM Service
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""

    # App
    APP_NAME: str = "Geo-Engineering DEM Service"
    VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # hoehendaten.de API
    HOEHENDATEN_API_URL: str = "https://api.hoehendaten.de:14444/v1/rawtif"

    # Cache
    DEM_CACHE_TTL_SECONDS: int = 15552000  # 6 Monate
    DEM_BUFFER_METERS: float = 250.0
    CACHE_DIR: str = "/app/cache"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings"""
    return Settings()
