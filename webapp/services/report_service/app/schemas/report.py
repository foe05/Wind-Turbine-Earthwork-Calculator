"""
Pydantic schemas for report service
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime


class SiteData(BaseModel):
    """Data for a single WKA site"""
    id: int = Field(..., description="Site ID")
    coord_x: float = Field(..., description="X coordinate (UTM)")
    coord_y: float = Field(..., description="Y coordinate (UTM)")

    # Volumes
    foundation_volume: float
    platform_cut: float
    platform_fill: float
    slope_cut: float
    slope_fill: float
    total_cut: float
    total_fill: float

    # Platform
    platform_height: float
    platform_area: float

    # Costs
    cost_total: float
    cost_saving: Optional[float] = 0.0

    # Material balance (optional)
    material_reuse: bool = False
    material_available: Optional[float] = 0.0
    material_required: Optional[float] = 0.0
    material_surplus: Optional[float] = 0.0
    material_deficit: Optional[float] = 0.0
    material_reused: Optional[float] = 0.0


class RoadReportData(BaseModel):
    """Data for Road construction report"""
    road_length: float
    road_width: float
    total_cut: float
    total_fill: float
    net_volume: float
    avg_cut_depth: float
    avg_fill_depth: float
    num_stations: int
    station_interval: float
    design_grade: float
    profile_type: str
    start_elevation: float
    end_elevation: float
    cut_slope: float = 1.5
    fill_slope: float = 2.0
    ditch_cut: Optional[float] = 0.0
    include_ditches: bool = False
    ditch_width: Optional[float] = 0.0
    ditch_depth: Optional[float] = 0.0
    stations: Optional[List[Dict[str, Any]]] = []


class SolarReportData(BaseModel):
    """Data for Solar park report"""
    num_panels: float
    panel_area: float
    panel_density: float
    site_area: float
    foundation_volume: float
    foundation_type: str
    grading_cut: float
    grading_fill: float
    grading_strategy: str
    access_road_cut: float
    access_road_fill: float
    access_road_length: float
    total_cut: float
    total_fill: float
    net_volume: float
    panel_length: float
    panel_width: float
    row_spacing: float
    panel_tilt: float
    orientation: float = 180.0


class TerrainReportData(BaseModel):
    """Data for Terrain analysis report"""
    analysis_type: str
    analysis_type_label: str
    polygon_area: float
    num_sample_points: int
    resolution: float
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


class ReportGenerateRequest(BaseModel):
    """Request to generate a report"""
    project_name: str = Field(..., min_length=1, description="Project name")
    format: Literal["html", "pdf"] = Field("html", description="Output format")
    template: Literal["wka", "road", "solar", "terrain"] = Field("wka", description="Report template")

    # Data fields (use the appropriate one based on template)
    sites: Optional[List[SiteData]] = Field(None, description="WKA site data list")
    road_data: Optional[RoadReportData] = Field(None, description="Road report data")
    solar_data: Optional[SolarReportData] = Field(None, description="Solar park report data")
    terrain_data: Optional[TerrainReportData] = Field(None, description="Terrain analysis report data")


class ReportResponse(BaseModel):
    """Response with generated report"""
    report_id: str = Field(..., description="Report UUID")
    format: str = Field(..., description="Report format")
    download_url: str = Field(..., description="Download URL")
    file_size: int = Field(..., description="File size in bytes")
    generated_at: datetime = Field(..., description="Generation timestamp")
    expires_at: datetime = Field(..., description="Expiration timestamp")
