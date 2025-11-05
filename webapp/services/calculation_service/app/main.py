"""
Calculation Service - Main Application
FastAPI app for earthwork calculations
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.core.config import get_settings
from app.api import calculation

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
    description="Earthwork calculation service for geo-engineering platform",
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
app.include_router(calculation.router)


@app.get("/")
async def root():
    """Health check"""
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "features": [
            "Foundation calculations (circular & polygon)",
            "Platform cut/fill (rectangle & polygon with rotation)",
            "3 optimization methods (mean, min_cut, balanced)",
            "Material balance calculations",
            "Complete WKA site calculations"
        ]
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "calculation_service",
        "version": settings.VERSION
    }
