"""
Solar Park Calculation API Endpoints
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Tuple, Optional
import os

from app.modules.solar import (
    calculate_solar_park_earthwork,
    validate_solar_parameters
)

router = APIRouter(prefix="/solar", tags=["solar"])


class SolarCalculationRequest(BaseModel):
    """Request model for solar park earthwork calculation"""
    dem_id: str = Field(..., description="DEM identifier from DEM service")
    boundary: List[List[float]] = Field(..., description="Site boundary coordinates [[x1,y1], [x2,y2], ...]")
    panel_length: float = Field(..., ge=0.5, le=3.0, description="Panel length in meters")
    panel_width: float = Field(..., ge=0.5, le=2.5, description="Panel width in meters")
    row_spacing: float = Field(..., ge=2.0, le=20.0, description="Row spacing in meters")
    panel_tilt: float = Field(..., ge=0, le=60, description="Panel tilt angle in degrees")
    foundation_type: str = Field("driven_piles", description="Foundation type")
    grading_strategy: str = Field("minimal", description="Grading strategy")
    orientation: float = Field(180.0, ge=0, le=360, description="Panel azimuth in degrees (180 = south)")
    access_road_width: float = Field(4.0, ge=2.0, le=8.0, description="Access road width in meters")
    access_road_length: Optional[float] = Field(None, description="Access road length (optional, calculated if None)")


class SolarCalculationResponse(BaseModel):
    """Response model for solar park earthwork calculation"""
    num_panels: int = Field(..., description="Number of panels")
    panel_area: float = Field(..., description="Total panel area in square meters")
    panel_density: float = Field(..., description="Panel density (panels per square meter)")
    site_area: float = Field(..., description="Site area in square meters")
    foundation_volume: float = Field(..., description="Foundation volume in cubic meters")
    foundation_type: str = Field(..., description="Foundation type")
    grading_cut: float = Field(..., description="Grading cut volume in cubic meters")
    grading_fill: float = Field(..., description="Grading fill volume in cubic meters")
    grading_strategy: str = Field(..., description="Grading strategy used")
    access_road_cut: float = Field(..., description="Access road cut volume in cubic meters")
    access_road_fill: float = Field(..., description="Access road fill volume in cubic meters")
    access_road_length: float = Field(..., description="Access road length in meters")
    total_cut: float = Field(..., description="Total cut volume in cubic meters")
    total_fill: float = Field(..., description="Total fill volume in cubic meters")
    net_volume: float = Field(..., description="Net volume (cut - fill) in cubic meters")
    panel_positions: List[List[float]] = Field(..., description="Sample of panel positions (limited to 100)")


@router.post("/calculate", response_model=SolarCalculationResponse)
async def calculate_solar_park_endpoint(request: SolarCalculationRequest):
    """
    Calculate earthwork volumes for solar park installation.

    This endpoint calculates earthwork for:
    - Panel foundation installation
    - Site grading (minimal, terraced, or full)
    - Access road construction

    The calculation includes:
    - Automatic panel array layout generation
    - Foundation volume calculation based on type
    - Grading optimization based on strategy
    - Access road earthwork estimation
    """
    # Validate parameters
    is_valid, error_msg = validate_solar_parameters(
        panel_length=request.panel_length,
        panel_width=request.panel_width,
        row_spacing=request.row_spacing,
        panel_tilt=request.panel_tilt
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Validate foundation type
    valid_foundations = ["driven_piles", "concrete_footings", "screw_anchors"]
    if request.foundation_type not in valid_foundations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid foundation_type. Must be one of: {', '.join(valid_foundations)}"
        )

    # Validate grading strategy
    valid_strategies = ["minimal", "terraced", "full"]
    if request.grading_strategy not in valid_strategies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid grading_strategy. Must be one of: {', '.join(valid_strategies)}"
        )

    # Validate boundary has at least 3 points (polygon)
    if len(request.boundary) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Boundary must have at least 3 points to form a polygon"
        )

    # Get DEM file path
    dem_path = f"/app/cache/dem_{request.dem_id}.tif"
    if not os.path.exists(dem_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DEM file not found for dem_id: {request.dem_id}. Please fetch DEM first."
        )

    try:
        # Convert boundary to tuples
        boundary_coords = [(x, y) for x, y in request.boundary]

        # Calculate solar park earthwork
        result = calculate_solar_park_earthwork(
            dem_path=dem_path,
            boundary=boundary_coords,
            panel_length=request.panel_length,
            panel_width=request.panel_width,
            row_spacing=request.row_spacing,
            panel_tilt=request.panel_tilt,
            foundation_type=request.foundation_type,
            grading_strategy=request.grading_strategy,
            orientation=request.orientation,
            access_road_width=request.access_road_width,
            access_road_length=request.access_road_length
        )

        return SolarCalculationResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Solar park calculation failed: {str(e)}"
        )


@router.post("/validate")
async def validate_solar_parameters_endpoint(
    panel_length: float,
    panel_width: float,
    row_spacing: float,
    panel_tilt: float
):
    """
    Validate solar park parameters.

    Returns validation result and any error messages.
    """
    is_valid, error_msg = validate_solar_parameters(
        panel_length=panel_length,
        panel_width=panel_width,
        row_spacing=row_spacing,
        panel_tilt=panel_tilt
    )

    return {
        "valid": is_valid,
        "error_message": error_msg
    }


@router.get("/foundation-types")
async def get_foundation_types():
    """
    Get available foundation types for solar panels.
    """
    return {
        "foundation_types": [
            {
                "value": "driven_piles",
                "label": "Driven Steel Piles",
                "description": "Steel piles driven into ground, minimal excavation",
                "volume_per_panel": 0.05
            },
            {
                "value": "concrete_footings",
                "label": "Concrete Footings",
                "description": "Poured concrete footings",
                "volume_per_panel": 0.3
            },
            {
                "value": "screw_anchors",
                "label": "Screw Anchors",
                "description": "Helical screw anchors, minimal excavation",
                "volume_per_panel": 0.02
            }
        ]
    }


@router.get("/grading-strategies")
async def get_grading_strategies():
    """
    Get available grading strategies.
    """
    return {
        "grading_strategies": [
            {
                "value": "minimal",
                "label": "Minimal Grading",
                "description": "Only level areas under inverters and transformers"
            },
            {
                "value": "terraced",
                "label": "Terraced Grading",
                "description": "Create level terraces for panel rows"
            },
            {
                "value": "full",
                "label": "Full Site Grading",
                "description": "Level entire site to optimal elevation"
            }
        ]
    }
