"""
Terrain Analysis API Endpoints
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os

from app.modules.terrain import (
    analyze_terrain,
    validate_terrain_parameters
)

router = APIRouter(prefix="/terrain", tags=["terrain"])


class TerrainAnalysisRequest(BaseModel):
    """Request model for terrain analysis"""
    dem_id: str = Field(..., description="DEM identifier from DEM service")
    polygon: List[List[float]] = Field(..., description="Analysis polygon coordinates [[x1,y1], [x2,y2], ...]")
    analysis_type: str = Field(..., description="Analysis type")
    resolution: float = Field(1.0, ge=0.1, le=10.0, description="Sampling resolution in meters")
    target_elevation: Optional[float] = Field(None, description="Target elevation for volume_calculation")
    optimization_method: str = Field("balanced", description="Optimization method for cut_fill_balance")
    contour_interval: float = Field(1.0, ge=0.1, le=50.0, description="Contour interval for contour_generation")


class TerrainAnalysisResponse(BaseModel):
    """Response model for terrain analysis"""
    analysis_type: str
    polygon_area: float
    num_sample_points: int
    resolution: float
    # Optional fields depending on analysis type
    optimal_elevation: Optional[float] = None
    cut_volume: Optional[float] = None
    fill_volume: Optional[float] = None
    net_volume: Optional[float] = None
    target_elevation: Optional[float] = None
    min_elevation: Optional[float] = None
    max_elevation: Optional[float] = None
    avg_elevation: Optional[float] = None
    statistics: Optional[Dict[str, Any]] = None
    slope_analysis: Optional[Dict[str, Any]] = None
    contour_data: Optional[Dict[str, Any]] = None


@router.post("/analyze", response_model=TerrainAnalysisResponse)
async def analyze_terrain_endpoint(request: TerrainAnalysisRequest):
    """
    Perform terrain analysis within a polygon.

    Analysis types:
    - **cut_fill_balance**: Find optimal grade elevation to balance cut and fill
    - **volume_calculation**: Calculate cut/fill volumes at specified elevation
    - **slope_analysis**: Analyze slope percentages across terrain
    - **contour_generation**: Generate contour lines

    The analysis samples DEM data within the polygon at specified resolution
    and performs the requested analysis.
    """
    # Validate parameters
    is_valid, error_msg = validate_terrain_parameters(
        resolution=request.resolution,
        contour_interval=request.contour_interval
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Validate analysis type
    valid_types = ["cut_fill_balance", "volume_calculation", "slope_analysis", "contour_generation"]
    if request.analysis_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid analysis_type. Must be one of: {', '.join(valid_types)}"
        )

    # Validate optimization method
    valid_methods = ["mean", "min_cut", "balanced"]
    if request.optimization_method not in valid_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid optimization_method. Must be one of: {', '.join(valid_methods)}"
        )

    # Validate polygon has at least 3 points
    if len(request.polygon) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Polygon must have at least 3 points"
        )

    # Validate target_elevation for volume_calculation
    if request.analysis_type == "volume_calculation" and request.target_elevation is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_elevation is required for volume_calculation analysis"
        )

    # Get DEM file path
    dem_path = f"/app/cache/dem_{request.dem_id}.tif"
    if not os.path.exists(dem_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DEM file not found for dem_id: {request.dem_id}. Please fetch DEM first."
        )

    try:
        # Convert polygon to tuples
        polygon_coords = [(x, y) for x, y in request.polygon]

        # Analyze terrain
        result = analyze_terrain(
            dem_path=dem_path,
            polygon=polygon_coords,
            analysis_type=request.analysis_type,
            resolution=request.resolution,
            target_elevation=request.target_elevation,
            optimization_method=request.optimization_method,
            contour_interval=request.contour_interval
        )

        return TerrainAnalysisResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terrain analysis failed: {str(e)}"
        )


@router.post("/validate")
async def validate_terrain_parameters_endpoint(
    resolution: float,
    contour_interval: Optional[float] = None
):
    """
    Validate terrain analysis parameters.

    Returns validation result and any error messages.
    """
    is_valid, error_msg = validate_terrain_parameters(
        resolution=resolution,
        contour_interval=contour_interval
    )

    return {
        "valid": is_valid,
        "error_message": error_msg
    }


@router.get("/analysis-types")
async def get_analysis_types():
    """
    Get available terrain analysis types.
    """
    return {
        "analysis_types": [
            {
                "value": "cut_fill_balance",
                "label": "Cut/Fill Balance",
                "description": "Find optimal grade elevation to balance cut and fill volumes",
                "requires": ["polygon", "resolution", "optimization_method"]
            },
            {
                "value": "volume_calculation",
                "label": "Volume Calculation",
                "description": "Calculate cut and fill volumes at specified elevation",
                "requires": ["polygon", "resolution", "target_elevation"]
            },
            {
                "value": "slope_analysis",
                "label": "Slope Analysis",
                "description": "Analyze slope percentages across terrain",
                "requires": ["polygon", "resolution"]
            },
            {
                "value": "contour_generation",
                "label": "Contour Generation",
                "description": "Generate contour lines at specified interval",
                "requires": ["polygon", "resolution", "contour_interval"]
            }
        ]
    }


@router.get("/optimization-methods")
async def get_optimization_methods():
    """
    Get available optimization methods for cut/fill balance.
    """
    return {
        "optimization_methods": [
            {
                "value": "mean",
                "label": "Mean Elevation",
                "description": "Use average elevation as grade"
            },
            {
                "value": "min_cut",
                "label": "Minimize Cut",
                "description": "Use 40th percentile to minimize cut volume"
            },
            {
                "value": "balanced",
                "label": "Balanced Cut/Fill",
                "description": "Find elevation where cut equals fill"
            }
        ]
    }
