"""
Configuration for Report Service
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # App
    APP_NAME: str = "Geo-Engineering Report Service"
    VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Reports
    REPORTS_DIR: str = "/app/reports"
    REPORT_EXPIRATION_DAYS: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings"""
    return Settings()
