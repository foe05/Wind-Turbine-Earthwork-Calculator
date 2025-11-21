"""
Configuration for API Gateway
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # App
    APP_NAME: str = "Geo-Engineering API Gateway"
    VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"

    # Service URLs
    AUTH_SERVICE_URL: str = "http://auth_service:8001"
    DEM_SERVICE_URL: str = "http://dem_service:8002"
    CALCULATION_SERVICE_URL: str = "http://calculation_service:8003"
    COST_SERVICE_URL: str = "http://cost_service:8004"
    REPORT_SERVICE_URL: str = "http://report_service:8005"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings"""
    return Settings()
