"""
Pydantic schemas for DEM service
"""
from pydantic import BaseModel, Field, validator
from typing import List, Tuple, Optional
from datetime import datetime
import uuid


class DEMFetchRequest(BaseModel):
    """
    Request to fetch DEM data

    WICHTIG: Koordinaten MÜSSEN in UTM sein!
    """
    coordinates: List[Tuple[float, float]] = Field(
        ...,
        description="Liste von (Easting, Northing) Koordinaten in UTM",
        min_items=1,
        max_items=123
    )
    crs: str = Field(
        ...,
        description="UTM CRS (z.B. 'EPSG:25832')",
        pattern=r"^EPSG:\d+$"
    )
    buffer_meters: float = Field(
        250.0,
        description="Buffer um jeden Standort in Metern (mindestens 250m)",
        ge=100.0,
        le=1000.0
    )
    force_refresh: bool = Field(
        False,
        description="Cache ignorieren und neu laden"
    )

    @validator('coordinates')
    def validate_coordinates(cls, v):
        """Validate coordinates are reasonable UTM values"""
        for easting, northing in v:
            # UTM Easting: 0-1,000,000
            if not (0 <= easting <= 1_000_000):
                raise ValueError(
                    f"Ungültiger Easting-Wert: {easting}. "
                    f"Erwarte UTM-Koordinaten (0-1,000,000)"
                )

            # UTM Northing: 0-10,000,000 (Nordhalbkugel)
            if not (0 <= northing <= 10_000_000):
                raise ValueError(
                    f"Ungültiger Northing-Wert: {northing}. "
                    f"Erwarte UTM-Koordinaten (0-10,000,000)"
                )

        return v

    @validator('crs')
    def validate_utm_crs(cls, v):
        """Validate CRS is UTM"""
        try:
            epsg_code = int(v.split(':')[1])
        except (IndexError, ValueError):
            raise ValueError(f"Ungültiges CRS Format: {v}")

        # Check if UTM
        valid_utm = (
            (25832 <= epsg_code <= 25836) or  # ETRS89 UTM
            (32632 <= epsg_code <= 32636)     # WGS84 UTM
        )

        if not valid_utm:
            raise ValueError(
                f"CRS muss UTM sein (EPSG:25832-25836 oder EPSG:32632-32636). "
                f"Bekam: {v}"
            )

        return v


class DEMFetchResponse(BaseModel):
    """Response after fetching DEM"""
    dem_id: uuid.UUID
    tiles_count: int
    utm_zone: int
    attribution: str
    cache_hits: int
    api_downloads: int
    file_path: str
    created_at: datetime
    expires_at: datetime


class DEMInfoResponse(BaseModel):
    """DEM metadata"""
    dem_id: uuid.UUID
    source: str  # 'hoehendaten' or 'upload'
    utm_zone: int
    bounds: Optional[dict]  # GeoJSON
    tiles_count: int
    resolution: Optional[float]
    file_size: Optional[int]
    attribution: str
    created_at: datetime
    expires_at: datetime


class DEMUploadResponse(BaseModel):
    """Response after DEM upload"""
    dem_id: uuid.UUID
    file_name: str
    file_size: int
    crs: str
    bounds: dict
    message: str = "DEM erfolgreich hochgeladen"


class CacheStatsResponse(BaseModel):
    """Cache statistics"""
    redis: dict
    file_cache: dict
