"""
Road Calculation API Endpoints
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Tuple, Optional
import os
import tempfile
from uuid import uuid4

from app.modules.road import (
    calculate_road_earthwork,
    calculate_road_with_ditches,
    validate_road_parameters
)

router = APIRouter(prefix="/road", tags=["road"])


class RoadCalculationRequest(BaseModel):
    """Request model for road earthwork calculation"""
    dem_id: str = Field(..., description="DEM identifier from DEM service")
    centerline: List[List[float]] = Field(..., description="Road centerline coordinates [[x1,y1], [x2,y2], ...]")
    road_width: float = Field(..., ge=2.0, le=20.0, description="Road width in meters")
    design_grade: float = Field(..., ge=-15.0, le=15.0, description="Design grade in percent")
    cut_slope: float = Field(1.5, ge=0.5, le=3.0, description="Cut slope ratio (H:V)")
    fill_slope: float = Field(2.0, ge=1.0, le=4.0, description="Fill slope ratio (H:V)")
    profile_type: str = Field("flat", description="Profile type: flat, crowned, superelevated")
    station_interval: float = Field(10.0, ge=1.0, le=50.0, description="Station interval in meters")
    start_elevation: Optional[float] = Field(None, description="Starting elevation (optional)")
    include_ditches: bool = Field(False, description="Include side ditches")
    ditch_width: Optional[float] = Field(None, ge=0.5, le=3.0, description="Ditch width in meters")
    ditch_depth: Optional[float] = Field(None, ge=0.2, le=2.0, description="Ditch depth in meters")


class StationData(BaseModel):
    """Station profile data"""
    station: int
    distance: float
    x: float
    y: float
    ground_elevation: float
    design_elevation: float
    cut_depth: float
    fill_depth: float
    cut_area: float
    fill_area: float


class RoadCalculationResponse(BaseModel):
    """Response model for road earthwork calculation"""
    road_length: float = Field(..., description="Total road length in meters")
    total_cut: float = Field(..., description="Total cut volume in cubic meters")
    total_fill: float = Field(..., description="Total fill volume in cubic meters")
    net_volume: float = Field(..., description="Net volume (cut - fill) in cubic meters")
    avg_cut_depth: float = Field(..., description="Average cut depth in meters")
    avg_fill_depth: float = Field(..., description="Average fill depth in meters")
    num_stations: int = Field(..., description="Number of stations")
    station_interval: float = Field(..., description="Station interval in meters")
    design_grade: float = Field(..., description="Design grade in percent")
    road_width: float = Field(..., description="Road width in meters")
    profile_type: str = Field(..., description="Profile type")
    start_elevation: float = Field(..., description="Starting elevation in meters")
    end_elevation: float = Field(..., description="Ending elevation in meters")
    ditch_cut: Optional[float] = Field(None, description="Ditch cut volume if included")
    stations: List[StationData] = Field(..., description="Station-by-station profile data")


@router.post("/calculate", response_model=RoadCalculationResponse)
async def calculate_road_endpoint(request: RoadCalculationRequest):
    """
    Calculate earthwork volumes for road construction.

    This endpoint calculates cut and fill volumes for a road based on:
    - Road centerline geometry
    - Cross-section profile (flat, crowned, or superelevated)
    - Design grade
    - Cut and fill slope ratios

    The calculation uses the average-end-area method to compute volumes
    between stations along the road centerline.
    """
    # Validate parameters
    is_valid, error_msg = validate_road_parameters(
        road_width=request.road_width,
        design_grade=request.design_grade,
        cut_slope=request.cut_slope,
        fill_slope=request.fill_slope
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Validate profile type
    valid_profiles = ["flat", "crowned", "superelevated"]
    if request.profile_type not in valid_profiles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid profile_type. Must be one of: {', '.join(valid_profiles)}"
        )

    # Validate centerline has at least 2 points
    if len(request.centerline) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Centerline must have at least 2 points"
        )

    # Validate ditch parameters if included
    if request.include_ditches:
        if request.ditch_width is None or request.ditch_depth is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ditch_width and ditch_depth required when include_ditches is True"
            )

    # Get DEM file path (cached from DEM service)
    dem_path = f"/app/cache/dem_{request.dem_id}.tif"
    if not os.path.exists(dem_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DEM file not found for dem_id: {request.dem_id}. Please fetch DEM first."
        )

    try:
        # Convert centerline to tuples
        centerline_coords = [(x, y) for x, y in request.centerline]

        # Calculate road earthwork
        if request.include_ditches:
            result = calculate_road_with_ditches(
                dem_path=dem_path,
                centerline=centerline_coords,
                road_width=request.road_width,
                ditch_width=request.ditch_width,
                ditch_depth=request.ditch_depth,
                design_grade=request.design_grade,
                cut_slope=request.cut_slope,
                fill_slope=request.fill_slope,
                profile_type=request.profile_type,
                station_interval=request.station_interval,
                start_elevation=request.start_elevation
            )
        else:
            result = calculate_road_earthwork(
                dem_path=dem_path,
                centerline=centerline_coords,
                road_width=request.road_width,
                design_grade=request.design_grade,
                cut_slope=request.cut_slope,
                fill_slope=request.fill_slope,
                profile_type=request.profile_type,
                station_interval=request.station_interval,
                start_elevation=request.start_elevation
            )

        return RoadCalculationResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Road calculation failed: {str(e)}"
        )


@router.post("/validate")
async def validate_road_parameters_endpoint(
    road_width: float,
    design_grade: float,
    cut_slope: float,
    fill_slope: float
):
    """
    Validate road design parameters.

    Returns validation result and any error messages.
    """
    is_valid, error_msg = validate_road_parameters(
        road_width=road_width,
        design_grade=design_grade,
        cut_slope=cut_slope,
        fill_slope=fill_slope
    )

    return {
        "valid": is_valid,
        "error_message": error_msg
    }


@router.get("/profile-types")
async def get_profile_types():
    """
    Get available road profile types.
    """
    return {
        "profile_types": [
            {
                "value": "flat",
                "label": "Flat (0% Crown)",
                "description": "Flat cross-section, no crown"
            },
            {
                "value": "crowned",
                "label": "Crowned (2% Crown)",
                "description": "Standard crown for drainage"
            },
            {
                "value": "superelevated",
                "label": "Super-elevated (3-8% Banking)",
                "description": "Banking for curves"
            }
        ]
    }
