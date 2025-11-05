"""
Report Service - Main Application
FastAPI app for report generation (HTML/PDF)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.core.config import get_settings
from app.api import report

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
    description="Report generation service (HTML/PDF) for earthwork projects",
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
app.include_router(report.router)


@app.get("/")
async def root():
    """Health check"""
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "features": [
            "HTML report generation (Jinja2 templates)",
            "PDF export (WeasyPrint)",
            "Multiple templates (WKA, Road, Solar, Terrain)",
            "Automatic cleanup of expired reports"
        ]
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "report_service",
        "version": settings.VERSION
    }
