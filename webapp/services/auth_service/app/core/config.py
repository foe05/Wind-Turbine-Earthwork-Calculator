"""
Configuration for Auth Service
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # App
    APP_NAME: str = "Geo-Engineering Auth Service"
    VERSION: str = "2.0.0"
    DEBUG: bool = True  # Default to True for development

    # Database
    DATABASE_URL: str

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # Magic Link
    MAGIC_LINK_EXPIRATION_MINUTES: int = 15
    MAGIC_LINK_SECRET: str = "magic-link-secret-change-in-production"

    # SMTP (all optional for development)
    SMTP_HOST: str = ""  # Empty by default
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@geo-engineering.example.com"
    SMTP_USE_TLS: bool = True

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings"""
    return Settings()
