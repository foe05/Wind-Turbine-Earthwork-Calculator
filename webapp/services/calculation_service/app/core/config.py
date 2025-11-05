"""
Configuration for Calculation Service
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # App
    APP_NAME: str = "Geo-Engineering Calculation Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # DEM Service
    DEM_SERVICE_URL: str = "http://dem_service:8002"

    # Cache
    TEMP_DIR: str = "/tmp/calc_cache"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings"""
    return Settings()
