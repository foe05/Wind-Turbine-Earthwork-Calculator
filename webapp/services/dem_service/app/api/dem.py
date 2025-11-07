"""
DEM API endpoints
"""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
import logging
from pathlib import Path
from typing import List
import uuid
import os
from datetime import datetime, timedelta
import rasterio

from app.schemas.dem import (
    DEMFetchRequest, DEMFetchResponse,
    DEMInfoResponse, CacheStatsResponse
)
from app.core.config import get_settings
from app.core.cache import DEMCache
from app.core.hoehendaten_api import (
    validate_utm_crs,
    calculate_tiles_for_points,
    fetch_dem_tile_from_api,
    decode_dem_tile,
    create_mosaic_from_tiles,
    save_mosaic_to_file
)

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dem", tags=["DEM"])

# Initialize cache
cache = DEMCache(
    redis_url=settings.REDIS_URL,
    cache_dir=Path(settings.CACHE_DIR)
)


@router.post("/fetch", response_model=DEMFetchResponse)
async def fetch_dem(
    request: DEMFetchRequest,
    background_tasks: BackgroundTasks
):
    """
    Fetch DEM data from hoehendaten.de API

    This endpoint:
    1. Validates UTM coordinates
    2. Calculates required 1km tiles (with 250m buffer)
    3. Fetches tiles from cache or API
    4. Creates mosaic
    5. Saves to file

    WICHTIG: Koordinaten MÜSSEN in UTM sein!
    """
    logger.info("=" * 70)
    logger.info("DEM-Fetch-Anfrage")
    logger.info("=" * 70)
    logger.info(f"Standorte: {len(request.coordinates)}")
    logger.info(f"CRS: {request.crs}")
    logger.info(f"Buffer: {request.buffer_meters}m")
    logger.info(f"Force Refresh: {request.force_refresh}")

    # 1. Validate and extract UTM zone
    try:
        epsg_code, utm_zone = validate_utm_crs(request.crs)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # 2. Calculate required tiles
    tiles_needed = calculate_tiles_for_points(
        request.coordinates,
        radius_m=request.buffer_meters
    )

    if not tiles_needed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keine Kacheln zu laden"
        )

    logger.info(f"\n📦 Lade {len(tiles_needed)} Kachel(n)...")

    # 3. Fetch tiles (from cache or API)
    tile_paths = []  # Paths to temporary tile files
    cache_hits = 0
    api_downloads = 0
    attribution = "hoehendaten.de"

    for easting, northing in tiles_needed:
        # Check cache first (unless force_refresh)
        if not request.force_refresh:
            cached_tile = cache.get_tile(utm_zone, easting, northing)

            if cached_tile:
                # Load from cache
                tile_path = decode_dem_tile(
                    cached_tile['data'],
                    easting,
                    northing,
                    utm_zone
                )

                if tile_path:
                    tile_paths.append(tile_path)
                    cache_hits += 1
                    attribution = cached_tile.get('attribution', attribution)
                    continue

        # Fetch from API
        tile_data = fetch_dem_tile_from_api(easting, northing, utm_zone)

        if not tile_data:
            logger.error(f"Fehler beim Laden: E={easting}, N={northing}")
            continue

        # Decode tile to temp file
        tile_path = decode_dem_tile(
            tile_data['data'],
            easting,
            northing,
            utm_zone
        )

        if tile_path:
            tile_paths.append(tile_path)
            api_downloads += 1
            attribution = tile_data.get('attribution', attribution)

            # Cache for future use
            cache.set_tile(utm_zone, easting, northing, tile_data)

    logger.info(f"\n📊 Cache-Statistik:")
    logger.info(f"   💾 Cache-Hits: {cache_hits}/{len(tiles_needed)}")
    logger.info(f"   ⬇️ API-Downloads: {api_downloads}/{len(tiles_needed)}")
    logger.info(f"   ✓ Erfolgreich geladen: {len(tile_paths)}/{len(tiles_needed)}")

    if not tile_paths:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Keine Kacheln erfolgreich geladen"
        )

    # 4. Create mosaic from tile files
    logger.info(f"\n🔨 Erstelle Mosaik aus {len(tile_paths)} Kachel(n)...")

    try:
        # Open all tile files
        tile_datasets = [rasterio.open(path) for path in tile_paths]

        mosaic_result = create_mosaic_from_tiles(tile_datasets)

        if not mosaic_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Mosaik-Erstellung fehlgeschlagen"
            )

        mosaic, transform, crs = mosaic_result

        # Close datasets
        for dataset in tile_datasets:
            dataset.close()

    finally:
        # Clean up temporary files
        for path in tile_paths:
            try:
                os.unlink(path)
            except Exception as e:
                logger.warning(f"Could not delete temp file {path}: {e}")

    # 5. Save to file
    dem_id = uuid.uuid4()
    output_path = cache.cache_dir / f"dem_{dem_id}.tif"

    success = save_mosaic_to_file(mosaic, transform, crs, output_path)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fehler beim Speichern des Mosaiks"
        )

    logger.info(f"\n✓ DEM erfolgreich erstellt: {dem_id}")
    logger.info("=" * 70 + "\n")

    # Schedule cleanup in background
    background_tasks.add_task(cache.clear_expired)

    return DEMFetchResponse(
        dem_id=dem_id,
        tiles_count=len(tiles_needed),
        utm_zone=utm_zone,
        attribution=attribution,
        cache_hits=cache_hits,
        api_downloads=api_downloads,
        file_path=str(output_path),
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(seconds=settings.DEM_CACHE_TTL_SECONDS)
    )


@router.get("/{dem_id}", response_class=FileResponse)
async def download_dem(dem_id: uuid.UUID):
    """
    Download DEM GeoTIFF file

    Returns the GeoTIFF file for the specified DEM ID
    """
    file_path = cache.cache_dir / f"dem_{dem_id}.tif"

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DEM mit ID {dem_id} nicht gefunden"
        )

    return FileResponse(
        path=file_path,
        media_type="image/tiff",
        filename=f"dem_{dem_id}.tif"
    )


@router.get("/{dem_id}/info", response_model=DEMInfoResponse)
async def get_dem_info(dem_id: uuid.UUID):
    """
    Get DEM metadata

    Returns metadata about the specified DEM
    """
    file_path = cache.cache_dir / f"dem_{dem_id}.tif"

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DEM mit ID {dem_id} nicht gefunden"
        )

    import rasterio

    try:
        with rasterio.open(file_path) as src:
            bounds = src.bounds
            crs = src.crs

            # Extract UTM zone from CRS
            if crs.to_string().startswith('EPSG:'):
                epsg_code = int(crs.to_string().split(':')[1])
                _, utm_zone = validate_utm_crs(crs.to_string())
            else:
                utm_zone = 32  # Default

            return DEMInfoResponse(
                dem_id=dem_id,
                source="hoehendaten",
                utm_zone=utm_zone,
                bounds={
                    "type": "Polygon",
                    "coordinates": [[
                        [bounds.left, bounds.bottom],
                        [bounds.right, bounds.bottom],
                        [bounds.right, bounds.top],
                        [bounds.left, bounds.top],
                        [bounds.left, bounds.bottom]
                    ]]
                },
                tiles_count=1,  # TODO: track this
                resolution=src.res[0],
                file_size=file_path.stat().st_size,
                attribution="hoehendaten.de",
                created_at=datetime.fromtimestamp(file_path.stat().st_ctime),
                expires_at=datetime.fromtimestamp(file_path.stat().st_mtime) +
                          timedelta(seconds=settings.DEM_CACHE_TTL_SECONDS)
            )

    except Exception as e:
        logger.error(f"Fehler beim Lesen der DEM-Info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    Get cache statistics

    Returns information about Redis and file cache
    """
    stats = cache.get_cache_stats()
    return CacheStatsResponse(**stats)


@router.post("/cache/clear-expired")
async def clear_expired_cache():
    """
    Clear expired cache entries

    Removes old files from cache directory
    """
    deleted = cache.clear_expired()

    return {
        "message": f"{deleted} abgelaufene Dateien gelöscht",
        "deleted_count": deleted
    }
