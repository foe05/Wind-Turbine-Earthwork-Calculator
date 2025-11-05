"""
API Gateway - Main Application
Central entry point for all microservices
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

from app.core.config import get_settings
from app.api import proxy, websocket, jobs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Central API Gateway for Geo-Engineering Platform",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(proxy.router)
app.include_router(websocket.router)
app.include_router(jobs.router)


@app.get("/")
@limiter.limit("60/minute")
async def root():
    """Health check and service info"""
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "services": {
            "auth": settings.AUTH_SERVICE_URL,
            "dem": settings.DEM_SERVICE_URL,
            "calculation": settings.CALCULATION_SERVICE_URL,
            "cost": settings.COST_SERVICE_URL,
            "report": settings.REPORT_SERVICE_URL
        },
        "features": [
            "Service routing and proxying",
            "JWT authentication middleware",
            "Rate limiting",
            "CORS support",
            "Background job processing (Celery)",
            "WebSocket real-time progress updates"
        ]
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "api_gateway",
        "version": settings.VERSION
    }


@app.get("/services")
async def list_services():
    """List all available microservices"""
    return {
        "auth_service": {
            "url": settings.AUTH_SERVICE_URL,
            "endpoints": ["/auth/request-login", "/auth/verify/{token}", "/auth/me"]
        },
        "dem_service": {
            "url": settings.DEM_SERVICE_URL,
            "endpoints": ["/dem/fetch", "/dem/{dem_id}", "/dem/cache/stats"]
        },
        "calculation_service": {
            "url": settings.CALCULATION_SERVICE_URL,
            "endpoints": [
                "/calc/foundation/circular",
                "/calc/foundation/polygon",
                "/calc/platform/rectangle",
                "/calc/platform/polygon",
                "/calc/wka/site"
            ]
        },
        "cost_service": {
            "url": settings.COST_SERVICE_URL,
            "endpoints": ["/costs/material-balance", "/costs/calculate", "/costs/presets"]
        },
        "report_service": {
            "url": settings.REPORT_SERVICE_URL,
            "endpoints": ["/report/generate", "/report/download/{report_id}/{filename}"]
        }
    }
