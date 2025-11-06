"""
Service proxy endpoints - Route requests to microservices
"""
from fastapi import APIRouter, Request, Response, HTTPException, Depends
import httpx
import logging

from app.core.config import get_settings
from app.middleware.auth import verify_token

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter()


async def proxy_request(
    request: Request,
    service_url: str,
    path: str
):
    """
    Proxy request to microservice

    Args:
        request: Incoming request
        service_url: Base URL of target service
        path: Path to append

    Returns:
        Response from target service
    """
    target_url = f"{service_url}{path}"

    # Get request body
    body = await request.body()

    # Forward headers (exclude host)
    headers = dict(request.headers)
    headers.pop("host", None)

    logger.info(f"Proxying {request.method} request to: {target_url}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params,
                timeout=30.0
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )

        except httpx.HTTPError as e:
            logger.error(f"Proxy error: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Service unavailable: {str(e)}"
            )


# Auth Service Routes
@router.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_auth(path: str, request: Request):
    """Proxy to Auth Service"""
    return await proxy_request(request, settings.AUTH_SERVICE_URL, f"/auth/{path}")


# DEM Service Routes
@router.api_route("/dem/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_dem(path: str, request: Request):
    """Proxy to DEM Service"""
    return await proxy_request(request, settings.DEM_SERVICE_URL, f"/dem/{path}")


# Calculation Service Routes
@router.api_route("/calc/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_calculation(path: str, request: Request):
    """Proxy to Calculation Service"""
    return await proxy_request(request, settings.CALCULATION_SERVICE_URL, f"/calc/{path}")


# Cost Service Routes
@router.api_route("/costs/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_cost(path: str, request: Request):
    """Proxy to Cost Service"""
    return await proxy_request(request, settings.COST_SERVICE_URL, f"/costs/{path}")


# Report Service Routes
@router.api_route("/report/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_report(path: str, request: Request):
    """Proxy to Report Service"""
    return await proxy_request(request, settings.REPORT_SERVICE_URL, f"/report/{path}")
