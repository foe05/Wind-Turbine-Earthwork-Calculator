"""
DEM Service - Main Application
FastAPI app for DEM fetching from hoehendaten.de API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.core.config import get_settings
from app.api import dem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

settings = get_settings()

# Create app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="DEM fetching service with hoehendaten.de API integration and caching",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dem.router)


@app.get("/")
async def root():
    """Health check"""
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "api": "hoehendaten.de",
        "features": [
            "UTM coordinate system (EPSG:25832-25836)",
            "1km tile management",
            "250m buffer around sites",
            "Redis caching (6 months TTL)",
            "Automatic mosaic creation"
        ]
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "dem_service",
        "version": settings.VERSION
    }
