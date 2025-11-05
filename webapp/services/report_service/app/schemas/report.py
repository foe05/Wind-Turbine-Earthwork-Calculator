"""
Pydantic schemas for report service
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
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


class ReportGenerateRequest(BaseModel):
    """Request to generate a report"""
    project_name: str = Field(..., min_length=1, description="Project name")
    sites: List[SiteData] = Field(..., min_items=1, description="Site data list")
    format: Literal["html", "pdf"] = Field("html", description="Output format")
    template: Literal["wka", "road", "solar", "terrain"] = Field("wka", description="Report template")


class ReportResponse(BaseModel):
    """Response with generated report"""
    report_id: str = Field(..., description="Report UUID")
    format: str = Field(..., description="Report format")
    download_url: str = Field(..., description="Download URL")
    file_size: int = Field(..., description="File size in bytes")
    generated_at: datetime = Field(..., description="Generation timestamp")
    expires_at: datetime = Field(..., description="Expiration timestamp")
