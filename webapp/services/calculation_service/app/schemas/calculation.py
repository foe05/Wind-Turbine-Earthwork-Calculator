"""
Pydantic schemas for calculation service
"""
from pydantic import BaseModel, Field, validator
from typing import List, Tuple, Optional, Literal
from enum import Enum


class FoundationType(str, Enum):
    """Foundation types"""
    SHALLOW = "shallow"  # 0: Flachgründung
    DEEP = "deep"        # 1: Tiefgründung mit Konus
    PILE = "pile"        # 2: Pfahlgründung


class OptimizationMethod(str, Enum):
    """Platform height optimization methods"""
    MEAN = "mean"            # 0: Mittelwert
    MIN_CUT = "min_cut"      # 1: Minimaler Aushub
    BALANCED = "balanced"    # 2: Ausgeglichene Cut/Fill-Balance


# =============================================================================
# Foundation Requests/Responses
# =============================================================================

class FoundationCircularRequest(BaseModel):
    """Request for circular foundation calculation"""
    diameter: float = Field(..., gt=0, le=50, description="Fundament-Durchmesser in Metern")
    depth: float = Field(..., gt=0, le=10, description="Fundamenttiefe in Metern")
    foundation_type: FoundationType = Field(FoundationType.SHALLOW, description="Fundament-Typ")


class FoundationPolygonRequest(BaseModel):
    """Request for polygon foundation calculation"""
    dem_id: str = Field(..., description="DEM ID from DEM service")
    polygon_coords: List[Tuple[float, float]] = Field(..., min_items=3, description="Fundament-Polygon Koordinaten (UTM)")
    depth: float = Field(..., gt=0, le=10, description="Fundamenttiefe in Metern")
    foundation_type: FoundationType = Field(FoundationType.SHALLOW, description="Fundament-Typ")
    resolution: float = Field(0.5, gt=0, le=2, description="Sample-Auflösung in Metern")


class FoundationResponse(BaseModel):
    """Response with foundation volume"""
    volume: float = Field(..., description="Aushubvolumen in m³")
    area: Optional[float] = Field(None, description="Grundfläche in m²")
    depth: float = Field(..., description="Tiefe in m")
    foundation_type: str = Field(..., description="Fundament-Typ")


# =============================================================================
# Platform Requests/Responses
# =============================================================================

class PlatformPolygonRequest(BaseModel):
    """Request for polygon-based platform calculation"""
    dem_id: str = Field(..., description="DEM ID from DEM service")
    platform_coords: List[Tuple[float, float]] = Field(..., min_items=3, description="Plattform-Polygon Koordinaten (UTM)")
    slope_width: float = Field(10.0, gt=0, le=50, description="Böschungsbreite in Metern")
    slope_angle: float = Field(34.0, gt=0, le=70, description="Böschungswinkel in Grad")
    optimization_method: OptimizationMethod = Field(OptimizationMethod.MEAN, description="Optimierungsmethode")
    resolution: float = Field(0.5, gt=0, le=2, description="Sample-Auflösung in Metern")


class PlatformRectangleRequest(BaseModel):
    """Request for rectangle-based platform calculation"""
    dem_id: str = Field(..., description="DEM ID from DEM service")
    center_x: float = Field(..., description="Zentrum X-Koordinate (UTM)")
    center_y: float = Field(..., description="Zentrum Y-Koordinate (UTM)")
    length: float = Field(..., gt=0, le=200, description="Plattform-Länge in Metern")
    width: float = Field(..., gt=0, le=200, description="Plattform-Breite in Metern")
    slope_width: float = Field(10.0, gt=0, le=50, description="Böschungsbreite in Metern")
    slope_angle: float = Field(34.0, gt=0, le=70, description="Böschungswinkel in Grad")
    optimization_method: OptimizationMethod = Field(OptimizationMethod.MEAN, description="Optimierungsmethode")
    rotation_angle: float = Field(0.0, ge=-180, le=180, description="Rotationswinkel in Grad")
    resolution: float = Field(0.5, gt=0, le=2, description="Sample-Auflösung in Metern")


class PlatformResponse(BaseModel):
    """Response with platform cut/fill volumes"""
    platform_height: float = Field(..., description="Plattformhöhe in m")

    # Terrain statistics
    terrain_min: float = Field(..., description="Minimale Geländehöhe in m")
    terrain_max: float = Field(..., description="Maximale Geländehöhe in m")
    terrain_mean: float = Field(..., description="Mittlere Geländehöhe in m")
    terrain_std: float = Field(..., description="Standardabweichung in m")
    terrain_range: float = Field(..., description="Höhenbereich in m")

    # Volumes
    platform_cut: float = Field(..., description="Plattform-Aushub in m³")
    platform_fill: float = Field(..., description="Plattform-Auftrag in m³")
    slope_cut: float = Field(..., description="Böschungs-Aushub in m³")
    slope_fill: float = Field(..., description="Böschungs-Auftrag in m³")
    total_cut: float = Field(..., description="Gesamt-Aushub in m³")
    total_fill: float = Field(..., description="Gesamt-Auftrag in m³")

    # Areas
    platform_area: float = Field(..., description="Plattformfläche in m²")
    total_area: float = Field(..., description="Gesamtfläche (inkl. Böschung) in m²")


# =============================================================================
# WKA (Wind Turbine) Complete Site Calculation
# =============================================================================

class WKASiteRequest(BaseModel):
    """Request for complete WKA site calculation"""
    dem_id: str = Field(..., description="DEM ID from DEM service")

    # Site location
    center_x: float = Field(..., description="Standort X-Koordinate (UTM)")
    center_y: float = Field(..., description="Standort Y-Koordinate (UTM)")

    # Foundation parameters
    foundation_diameter: float = Field(22.0, gt=0, le=50, description="Fundament-Durchmesser in m")
    foundation_depth: float = Field(4.0, gt=0, le=10, description="Fundamenttiefe in m")
    foundation_type: FoundationType = Field(FoundationType.SHALLOW, description="Fundament-Typ")

    # Platform parameters
    platform_length: float = Field(45.0, gt=0, le=200, description="Kranflächen-Länge in m")
    platform_width: float = Field(40.0, gt=0, le=200, description="Kranflächen-Breite in m")
    slope_width: float = Field(10.0, gt=0, le=50, description="Böschungsbreite in m")
    slope_angle: float = Field(34.0, gt=0, le=70, description="Böschungswinkel in Grad")
    optimization_method: OptimizationMethod = Field(OptimizationMethod.BALANCED, description="Optimierungsmethode")
    rotation_angle: float = Field(0.0, ge=-180, le=180, description="Rotationswinkel in Grad")

    # Material reuse
    material_reuse: bool = Field(True, description="Material-Wiederverwendung aktiv")
    swell_factor: float = Field(1.25, gt=1.0, le=2.0, description="Auflockerungsfaktor")
    compaction_factor: float = Field(0.85, gt=0.5, lt=1.0, description="Verdichtungsfaktor")

    # Resolution
    resolution: float = Field(0.5, gt=0, le=2, description="Sample-Auflösung in Metern")


class WKASiteResponse(BaseModel):
    """Response with complete WKA site calculation"""
    # Foundation
    foundation_volume: float = Field(..., description="Fundament-Aushub in m³")

    # Platform
    platform_height: float = Field(..., description="Plattformhöhe in m")
    platform_cut: float = Field(..., description="Plattform-Aushub in m³")
    platform_fill: float = Field(..., description="Plattform-Auftrag in m³")
    slope_cut: float = Field(..., description="Böschungs-Aushub in m³")
    slope_fill: float = Field(..., description="Böschungs-Auftrag in m³")

    # Totals
    total_cut: float = Field(..., description="Gesamt-Aushub (Fundament + Plattform) in m³")
    total_fill: float = Field(..., description="Gesamt-Auftrag in m³")
    net_volume: float = Field(..., description="Netto-Volumen (Cut - Fill) in m³")

    # Material balance
    material_available: float = Field(..., description="Verfügbares Material (aufgelockert) in m³")
    material_required: float = Field(..., description="Benötigtes Material in m³")
    material_surplus: float = Field(..., description="Überschuss in m³")
    material_deficit: float = Field(..., description="Mangel in m³")
    material_reused: float = Field(..., description="Wiederverwendetes Material in m³")

    # Terrain stats
    terrain_min: float
    terrain_max: float
    terrain_mean: float
    terrain_std: float
    terrain_range: float

    # Areas
    platform_area: float
    total_area: float
