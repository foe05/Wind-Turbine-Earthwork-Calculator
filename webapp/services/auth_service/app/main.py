"""
Auth Service - Main Application
FastAPI app for authentication (Magic Links + JWT)
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api import auth
from app.db.init_db import init_db

logger = logging.getLogger(__name__)
settings = get_settings()

# Create app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Authentication service with magic links and JWT",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        logger.info("Starting up auth service...")
        init_db()
        logger.info("Auth service started successfully")
    except Exception as e:
        logger.error(f"Failed to start auth service: {e}")
        raise

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)


@app.get("/")
async def root():
    """Health check"""
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "healthy"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "auth_service",
        "version": settings.VERSION
    }
