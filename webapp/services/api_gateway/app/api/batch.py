"""
Batch Upload API
Endpoints for batch importing sites from CSV/GeoJSON
"""
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from uuid import UUID, uuid4
import logging
import csv
import json
import io
from pyproj import Transformer

from app.core.database import get_db_connection
from app.core.auth import get_current_user
from app.tasks import calculate_wka_site

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/batch", tags=["Batch Upload"])


# Pydantic Models
class SiteImport(BaseModel):
    """Single site import data"""
    name: Optional[str] = None
    lat: Optional[float] = None  # WGS84 Latitude
    lng: Optional[float] = None  # WGS84 Longitude
    utm_x: Optional[float] = None  # UTM Easting
    utm_y: Optional[float] = None  # UTM Northing
    utm_zone: Optional[int] = None
    foundation_diameter: float = Field(25.0, ge=10.0, le=50.0)
    foundation_depth: float = Field(4.0, ge=1.0, le=10.0)
    platform_length: float = Field(45.0, ge=20.0, le=100.0)
    platform_width: float = Field(45.0, ge=20.0, le=100.0)

    @validator('utm_zone')
    def validate_utm_zone(cls, v, values):
        """Validate UTM zone is provided with UTM coordinates"""
        if ('utm_x' in values or 'utm_y' in values) and v is None:
            raise ValueError("utm_zone required when utm_x or utm_y provided")
        return v


class BatchUploadRequest(BaseModel):
    """Batch upload request"""
    project_id: UUID
    sites: List[SiteImport] = Field(..., max_items=123)
    crs: str = Field("EPSG:25833", pattern=r"^EPSG:\d+$")
    cost_params: Dict[str, Any] = Field(default_factory=lambda: {
        "cost_excavation": 12.0,
        "cost_transport": 5.0,
        "cost_disposal": 8.0,
        "cost_fill_material": 15.0,
        "cost_platform_prep": 5.5,
        "material_reuse": True,
        "swell_factor": 1.25,
        "compaction_factor": 0.9
    })
    auto_start_jobs: bool = Field(True, description="Automatically start calculation jobs")


class BatchUploadResponse(BaseModel):
    """Batch upload response"""
    project_id: UUID
    sites_imported: int
    jobs_created: List[UUID]
    errors: List[str]


def convert_lat_lng_to_utm(lat: float, lng: float, utm_zone: int) -> tuple:
    """
    Convert WGS84 Lat/Lng to UTM coordinates

    Args:
        lat: Latitude (WGS84)
        lng: Longitude (WGS84)
        utm_zone: UTM zone (1-60)

    Returns:
        Tuple of (easting, northing)
    """
    # Determine hemisphere (N or S)
    hemisphere = 'north' if lat >= 0 else 'south'

    # Create transformer
    wgs84 = "EPSG:4326"
    utm_epsg = f"EPSG:326{utm_zone}" if hemisphere == 'north' else f"EPSG:327{utm_zone}"

    transformer = Transformer.from_crs(wgs84, utm_epsg, always_xy=True)

    # Transform coordinates
    easting, northing = transformer.transform(lng, lat)

    return easting, northing


def auto_detect_utm_zone(lng: float) -> int:
    """
    Auto-detect UTM zone from longitude

    Args:
        lng: Longitude (WGS84)

    Returns:
        UTM zone (1-60)
    """
    # UTM zone calculation: ((longitude + 180) / 6) + 1
    zone = int((lng + 180) / 6) + 1
    return max(1, min(60, zone))


@router.post("/upload", response_model=BatchUploadResponse)
async def batch_upload(
    request: BatchUploadRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Batch upload sites

    Accepts list of sites with Lat/Lng or UTM coordinates.
    Automatically converts Lat/Lng to UTM if needed.
    Creates jobs for each site if auto_start_jobs=True.

    **Limits**: Maximum 123 sites per batch.
    """
    try:
        # Validate site count
        if len(request.sites) > 123:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum 123 sites allowed, got {len(request.sites)}"
            )

        # Verify project ownership
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT user_id, utm_zone FROM projects WHERE id = %s",
            (str(request.project_id),)
        )
        result = cur.fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {request.project_id} not found"
            )

        if result[0] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this project"
            )

        project_utm_zone = result[1]

        # Process sites
        jobs_created = []
        errors = []

        for idx, site in enumerate(request.sites):
            try:
                # Determine coordinates
                if site.utm_x and site.utm_y:
                    # UTM coordinates provided
                    easting = site.utm_x
                    northing = site.utm_y
                    utm_zone = site.utm_zone or project_utm_zone
                elif site.lat and site.lng:
                    # Lat/Lng provided - convert to UTM
                    utm_zone = auto_detect_utm_zone(site.lng)
                    easting, northing = convert_lat_lng_to_utm(site.lat, site.lng, utm_zone)
                    logger.info(f"Converted Lat/Lng ({site.lat}, {site.lng}) to UTM ({easting}, {northing}) zone {utm_zone}")
                else:
                    errors.append(f"Site {idx + 1}: Must provide either (lat, lng) or (utm_x, utm_y)")
                    continue

                # Create site name if not provided
                site_name = site.name or f"Site {idx + 1}"

                # Prepare site data
                site_data = {
                    "crs": f"EPSG:326{utm_zone}",  # Assuming northern hemisphere
                    "center_x": easting,
                    "center_y": northing,
                    "foundation_diameter": site.foundation_diameter,
                    "foundation_depth": site.foundation_depth,
                    "platform_length": site.platform_length,
                    "platform_width": site.platform_width,
                    "optimization_method": "balanced",
                    "buffer_meters": 250
                }

                if request.auto_start_jobs:
                    # Create and start job
                    job_id = str(uuid4())

                    # Insert job into database
                    cur.execute("""
                        INSERT INTO jobs (id, project_id, status, progress, input_data, site_count)
                        VALUES (%s, %s, 'pending', 0, %s, 1)
                    """, (
                        job_id,
                        str(request.project_id),
                        json.dumps({"site_data": site_data, "cost_params": request.cost_params})
                    ))

                    # Submit Celery task
                    calculate_wka_site.apply_async(
                        kwargs={
                            "job_id": job_id,
                            "project_id": str(request.project_id),
                            "site_data": site_data,
                            "cost_params": request.cost_params
                        },
                        task_id=job_id
                    )

                    jobs_created.append(job_id)
                    logger.info(f"Created job {job_id} for site {site_name}")

            except Exception as e:
                logger.error(f"Error processing site {idx + 1}: {e}")
                errors.append(f"Site {idx + 1}: {str(e)}")

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Batch upload completed: {len(jobs_created)} jobs created, {len(errors)} errors")

        return BatchUploadResponse(
            project_id=request.project_id,
            sites_imported=len(jobs_created),
            jobs_created=jobs_created,
            errors=errors
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch upload failed: {str(e)}"
        )


@router.post("/upload-csv")
async def upload_csv(
    project_id: UUID,
    file: UploadFile = File(...),
    auto_start_jobs: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """
    Upload sites from CSV file

    Expected CSV format:
    ```
    name,lat,lng,foundation_diameter,foundation_depth,platform_length,platform_width
    Site1,52.5,13.4,25.0,4.0,45.0,45.0
    Site2,52.6,13.5,25.0,4.0,45.0,45.0
    ```

    Alternative with UTM:
    ```
    name,utm_x,utm_y,utm_zone,foundation_diameter,foundation_depth,platform_length,platform_width
    Site1,402500,5885000,33,25.0,4.0,45.0,45.0
    ```

    **Limits**: Maximum 123 sites per file.
    """
    try:
        # Read CSV content
        contents = await file.read()
        csv_data = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_data))

        # Parse sites
        sites = []
        for row in csv_reader:
            site = SiteImport(
                name=row.get('name'),
                lat=float(row['lat']) if 'lat' in row and row['lat'] else None,
                lng=float(row['lng']) if 'lng' in row and row['lng'] else None,
                utm_x=float(row['utm_x']) if 'utm_x' in row and row['utm_x'] else None,
                utm_y=float(row['utm_y']) if 'utm_y' in row and row['utm_y'] else None,
                utm_zone=int(row['utm_zone']) if 'utm_zone' in row and row['utm_zone'] else None,
                foundation_diameter=float(row.get('foundation_diameter', 25.0)),
                foundation_depth=float(row.get('foundation_depth', 4.0)),
                platform_length=float(row.get('platform_length', 45.0)),
                platform_width=float(row.get('platform_width', 45.0))
            )
            sites.append(site)

        # Create batch request
        batch_request = BatchUploadRequest(
            project_id=project_id,
            sites=sites,
            auto_start_jobs=auto_start_jobs
        )

        # Process batch
        return await batch_upload(batch_request, current_user)

    except csv.Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV format: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data in CSV: {str(e)}"
        )
    except Exception as e:
        logger.error(f"CSV upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV upload failed: {str(e)}"
        )


@router.post("/upload-geojson")
async def upload_geojson(
    project_id: UUID,
    file: UploadFile = File(...),
    auto_start_jobs: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """
    Upload sites from GeoJSON file

    Expected GeoJSON format (Point FeatureCollection):
    ```json
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {"type": "Point", "coordinates": [13.4, 52.5]},
          "properties": {
            "name": "Site1",
            "foundation_diameter": 25.0,
            "foundation_depth": 4.0,
            "platform_length": 45.0,
            "platform_width": 45.0
          }
        }
      ]
    }
    ```

    **Limits**: Maximum 123 sites per file.
    """
    try:
        # Read GeoJSON content
        contents = await file.read()
        geojson_data = json.loads(contents.decode('utf-8'))

        # Validate GeoJSON
        if geojson_data.get('type') != 'FeatureCollection':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GeoJSON must be a FeatureCollection"
            )

        # Parse features
        sites = []
        for feature in geojson_data.get('features', []):
            if feature.get('geometry', {}).get('type') != 'Point':
                continue

            coords = feature['geometry']['coordinates']
            props = feature.get('properties', {})

            site = SiteImport(
                name=props.get('name'),
                lng=coords[0],  # GeoJSON uses [lng, lat]
                lat=coords[1],
                foundation_diameter=float(props.get('foundation_diameter', 25.0)),
                foundation_depth=float(props.get('foundation_depth', 4.0)),
                platform_length=float(props.get('platform_length', 45.0)),
                platform_width=float(props.get('platform_width', 45.0))
            )
            sites.append(site)

        # Create batch request
        batch_request = BatchUploadRequest(
            project_id=project_id,
            sites=sites,
            auto_start_jobs=auto_start_jobs
        )

        # Process batch
        return await batch_upload(batch_request, current_user)

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GeoJSON format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"GeoJSON upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GeoJSON upload failed: {str(e)}"
        )
