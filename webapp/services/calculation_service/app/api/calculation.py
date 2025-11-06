"""
Calculation API endpoints
"""
from fastapi import APIRouter, HTTPException, status
import logging
import httpx
import os
from pathlib import Path

from app.schemas.calculation import (
    FoundationCircularRequest, FoundationPolygonRequest, FoundationResponse,
    PlatformPolygonRequest, PlatformRectangleRequest, PlatformResponse,
    WKASiteRequest, WKASiteResponse
)

# Import shared modules (PYTHONPATH is set in docker-compose.yml)
from shared.core.foundation import calculate_foundation_circular, calculate_foundation_polygon
from shared.core.material_balance import calculate_material_balance

from app.modules.platform import (
    calculate_platform_cutfill_polygon,
    calculate_platform_cutfill_rectangle
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calc", tags=["Calculation"])

# DEM Service URL
DEM_SERVICE_URL = os.getenv("DEM_SERVICE_URL", "http://dem_service:8002")


async def get_dem_file_path(dem_id: str) -> str:
    """
    Get DEM file path from DEM service

    Args:
        dem_id: DEM ID from DEM service

    Returns:
        Path to DEM GeoTIFF file

    Raises:
        HTTPException: If DEM not found
    """
    async with httpx.AsyncClient() as client:
        try:
            # Download DEM from DEM service
            response = await client.get(
                f"{DEM_SERVICE_URL}/dem/{dem_id}",
                timeout=30.0
            )

            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"DEM with ID {dem_id} not found"
                )

            response.raise_for_status()

            # Save to temp file
            temp_dir = Path("/tmp/dem_cache")
            temp_dir.mkdir(parents=True, exist_ok=True)

            dem_path = temp_dir / f"dem_{dem_id}.tif"

            with open(dem_path, "wb") as f:
                f.write(response.content)

            return str(dem_path)

        except httpx.HTTPError as e:
            logger.error(f"Error fetching DEM from service: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"DEM service unavailable: {str(e)}"
            )


@router.post("/foundation/circular", response_model=FoundationResponse)
async def calculate_foundation_circular_endpoint(request: FoundationCircularRequest):
    """
    Calculate circular foundation volume

    Simple geometric calculation, no DEM required.
    """
    logger.info(f"Calculating circular foundation: d={request.diameter}m, depth={request.depth}m")

    # Map enum to int
    foundation_type_map = {
        "shallow": 0,
        "deep": 1,
        "pile": 2
    }

    result = calculate_foundation_circular(
        diameter=request.diameter,
        depth=request.depth,
        foundation_type=foundation_type_map[request.foundation_type]
    )

    return FoundationResponse(
        volume=result['volume'],
        area=3.14159 * (request.diameter / 2) ** 2,  # Circle area
        depth=result['depth'],
        foundation_type=request.foundation_type
    )


@router.post("/foundation/polygon", response_model=FoundationResponse)
async def calculate_foundation_polygon_endpoint(request: FoundationPolygonRequest):
    """
    Calculate polygon foundation volume

    Requires DEM for terrain sampling.
    """
    logger.info(f"Calculating polygon foundation: {len(request.polygon_coords)} vertices, depth={request.depth}m")

    # Get DEM file
    dem_path = await get_dem_file_path(request.dem_id)

    # Map enum to int
    foundation_type_map = {
        "shallow": 0,
        "deep": 1,
        "pile": 2
    }

    # Calculate (requires DEM data and transform - simplified for now)
    import rasterio
    with rasterio.open(dem_path) as src:
        dem_data = src.read(1)
        dem_transform = src.transform

        result = calculate_foundation_polygon(
            polygon_points=request.polygon_coords,
            dem_data=dem_data,
            dem_transform=dem_transform,
            depth=request.depth,
            foundation_type=foundation_type_map[request.foundation_type],
            resolution=request.resolution
        )

    return FoundationResponse(
        volume=result['volume'],
        area=result['area'],
        depth=result['depth'],
        foundation_type=request.foundation_type
    )


@router.post("/platform/polygon", response_model=PlatformResponse)
async def calculate_platform_polygon_endpoint(request: PlatformPolygonRequest):
    """
    Calculate platform cut/fill for polygon shape

    Requires DEM for terrain sampling.
    """
    logger.info(f"Calculating platform (polygon): {len(request.platform_coords)} vertices")

    # Get DEM file
    dem_path = await get_dem_file_path(request.dem_id)

    # Calculate
    result = calculate_platform_cutfill_polygon(
        dem_path=dem_path,
        platform_polygon=request.platform_coords,
        slope_width=request.slope_width,
        slope_angle=request.slope_angle,
        optimization_method=request.optimization_method,
        resolution=request.resolution
    )

    return PlatformResponse(**result)


@router.post("/platform/rectangle", response_model=PlatformResponse)
async def calculate_platform_rectangle_endpoint(request: PlatformRectangleRequest):
    """
    Calculate platform cut/fill for rectangle shape with rotation

    Requires DEM for terrain sampling.
    """
    logger.info(f"Calculating platform (rectangle): {request.length}x{request.width}m @ ({request.center_x}, {request.center_y})")

    # Get DEM file
    dem_path = await get_dem_file_path(request.dem_id)

    # Calculate
    result = calculate_platform_cutfill_rectangle(
        dem_path=dem_path,
        center_x=request.center_x,
        center_y=request.center_y,
        length=request.length,
        width=request.width,
        slope_width=request.slope_width,
        slope_angle=request.slope_angle,
        optimization_method=request.optimization_method,
        rotation_angle=request.rotation_angle,
        resolution=request.resolution
    )

    return PlatformResponse(**result)


@router.post("/wka/site", response_model=WKASiteResponse)
async def calculate_wka_site_endpoint(request: WKASiteRequest):
    """
    Complete WKA site calculation

    Combines foundation + platform + material balance.
    This is the main endpoint for WKA calculations.
    """
    logger.info("=" * 70)
    logger.info(f"WKA Site Calculation @ ({request.center_x}, {request.center_y})")
    logger.info("=" * 70)

    # Get DEM file
    dem_path = await get_dem_file_path(request.dem_id)

    # 1. Foundation calculation
    logger.info("1. Calculating foundation...")
    foundation_type_map = {"shallow": 0, "deep": 1, "pile": 2}

    foundation_result = calculate_foundation_circular(
        diameter=request.foundation_diameter,
        depth=request.foundation_depth,
        foundation_type=foundation_type_map[request.foundation_type]
    )

    logger.info(f"   Foundation volume: {foundation_result['volume']:.1f} m³")

    # 2. Platform calculation
    logger.info("2. Calculating platform...")

    platform_result = calculate_platform_cutfill_rectangle(
        dem_path=dem_path,
        center_x=request.center_x,
        center_y=request.center_y,
        length=request.platform_length,
        width=request.platform_width,
        slope_width=request.slope_width,
        slope_angle=request.slope_angle,
        optimization_method=request.optimization_method,
        rotation_angle=request.rotation_angle,
        resolution=request.resolution
    )

    logger.info(f"   Platform height: {platform_result['platform_height']}m")
    logger.info(f"   Total cut: {platform_result['total_cut']:.1f} m³")
    logger.info(f"   Total fill: {platform_result['total_fill']:.1f} m³")

    # 3. Material balance
    logger.info("3. Calculating material balance...")

    if request.material_reuse:
        material_balance = calculate_material_balance(
            foundation_volume=foundation_result['volume'],
            crane_cut=platform_result['total_cut'],
            crane_fill=platform_result['total_fill'],
            swell_factor=request.swell_factor,
            compaction_factor=request.compaction_factor
        )
        logger.info(f"   Available: {material_balance['available']:.1f} m³")
        logger.info(f"   Required: {material_balance['required']:.1f} m³")
        logger.info(f"   Surplus: {material_balance['surplus']:.1f} m³")
        logger.info(f"   Deficit: {material_balance['deficit']:.1f} m³")
    else:
        material_balance = {
            'available': 0.0,
            'required': 0.0,
            'surplus': 0.0,
            'deficit': 0.0,
            'reused': 0.0
        }

    # 4. Combine results
    total_cut = foundation_result['volume'] + platform_result['total_cut']
    total_fill = platform_result['total_fill']
    net_volume = total_cut - total_fill

    logger.info("=" * 70)
    logger.info(f"✓ Total Cut: {total_cut:.1f} m³")
    logger.info(f"✓ Total Fill: {total_fill:.1f} m³")
    logger.info(f"✓ Net Volume: {net_volume:.1f} m³")
    logger.info("=" * 70 + "\n")

    return WKASiteResponse(
        # Foundation
        foundation_volume=round(foundation_result['volume'], 1),

        # Platform
        platform_height=platform_result['platform_height'],
        platform_cut=platform_result['platform_cut'],
        platform_fill=platform_result['platform_fill'],
        slope_cut=platform_result['slope_cut'],
        slope_fill=platform_result['slope_fill'],

        # Totals
        total_cut=round(total_cut, 1),
        total_fill=round(total_fill, 1),
        net_volume=round(net_volume, 1),

        # Material balance
        material_available=round(material_balance['available'], 1),
        material_required=round(material_balance['required'], 1),
        material_surplus=round(material_balance['surplus'], 1),
        material_deficit=round(material_balance['deficit'], 1),
        material_reused=round(material_balance['reused'], 1),

        # Terrain stats
        terrain_min=platform_result['terrain_min'],
        terrain_max=platform_result['terrain_max'],
        terrain_mean=platform_result['terrain_mean'],
        terrain_std=platform_result['terrain_std'],
        terrain_range=platform_result['terrain_range'],

        # Areas
        platform_area=platform_result['platform_area'],
        total_area=platform_result['total_area']
    )
