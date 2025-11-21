"""
Surface Types and Data Structures for Multi-Surface Earthwork Calculator

Defines the data structures for handling multiple surface types:
- Crane pad (Kranstellfläche)
- Foundation (Fundamentfläche)
- Boom surface (Auslegerfläche)
- Blade storage (Blattlagerfläche)

Author: Wind Energy Site Planning
Version: 2.0 - Multi-Surface Extension
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum

from qgis.core import QgsGeometry


class SurfaceType(Enum):
    """Types of surfaces in a wind turbine construction site."""
    CRANE_PAD = "kranstellflaeche"
    FOUNDATION = "fundamentflaeche"
    BOOM = "auslegerflaeche"
    ROTOR_STORAGE = "rotorflaeche"

    def __str__(self):
        return self.value

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        names = {
            SurfaceType.CRANE_PAD: "Kranstellfläche",
            SurfaceType.FOUNDATION: "Fundamentfläche",
            SurfaceType.BOOM: "Auslegerfläche",
            SurfaceType.ROTOR_STORAGE: "Blattlagerfläche"
        }
        return names[self]


class HeightMode(Enum):
    """Modes for calculating surface height."""
    FIXED = "fixed"              # Fixed absolute height (e.g., FOK)
    RELATIVE = "relative"        # Relative to another surface
    SLOPED = "sloped"           # With longitudinal slope
    OPTIMIZED = "optimized"     # Optimized variable height


@dataclass
class SurfaceConfig:
    """
    Configuration for a single surface.

    Attributes:
        surface_type: Type of surface
        geometry: QGIS polygon geometry
        dxf_path: Path to source DXF file
        height_mode: How height is calculated
        height_value: Fixed height value (m ü.NN) or None
        height_reference: Reference surface for relative heights
        slope_longitudinal: Longitudinal slope in percent (0-8%)
        slope_transverse: Transverse slope in percent (should be 0 for most)
        auto_slope: Auto-adjust slope to terrain within limits
        include_in_optimization: Include in volume optimization
        calculate_cut_fill: Calculate cut/fill volumes
        metadata: Additional metadata from DXF import
    """
    surface_type: SurfaceType
    geometry: QgsGeometry
    dxf_path: str

    # Height parameters
    height_mode: HeightMode = HeightMode.FIXED
    height_value: Optional[float] = None
    height_reference: Optional[str] = None  # 'fok', 'crane', etc.

    # Slope parameters (for boom surface)
    slope_longitudinal: float = 0.0  # Percent
    slope_transverse: float = 0.0    # Percent
    auto_slope: bool = False         # Auto-adjust to terrain
    slope_min: float = 2.0           # Minimum allowed slope %
    slope_max: float = 8.0           # Maximum allowed slope %

    # Calculation parameters
    include_in_optimization: bool = True
    calculate_cut_fill: bool = True

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.slope_longitudinal < 0 or self.slope_longitudinal > 100:
            raise ValueError(f"Invalid slope_longitudinal: {self.slope_longitudinal}%")

        if self.surface_type == SurfaceType.BOOM:
            if self.slope_longitudinal < self.slope_min or self.slope_longitudinal > self.slope_max:
                raise ValueError(
                    f"Boom slope {self.slope_longitudinal}% outside allowed range "
                    f"[{self.slope_min}%, {self.slope_max}%]"
                )


@dataclass
class MultiSurfaceProject:
    """
    Complete multi-surface project configuration.

    This represents all surfaces and parameters for a wind turbine site.

    Attributes:
        crane_pad: Crane pad surface configuration
        foundation: Foundation surface configuration
        boom: Boom surface configuration
        rotor_storage: Rotor storage surface configuration
        fok: Foundation top edge elevation (Fundamentoberkante) in m ü.NN
        foundation_depth: Depth below FOK to foundation bottom in meters
        foundation_diameter: Foundation diameter (optional, from DXF if available)
        gravel_thickness: Gravel layer thickness on crane pad in meters
        rotor_height_offset: Height difference between crane pad and rotor storage
        slope_angle: Embankment/slope angle in degrees
        search_range_below_fok: Search range below FOK for optimization (meters)
        search_range_above_fok: Search range above FOK for optimization (meters)
        search_step: Step size for height optimization (meters)
    """
    # Required surface configurations
    crane_pad: SurfaceConfig
    foundation: SurfaceConfig

    # Global height parameters (all in meters ü.NN or relative meters)
    fok: float  # Foundation top edge (Fundamentoberkante)

    # Optional surface configurations
    boom: Optional[SurfaceConfig] = None
    rotor_storage: Optional[SurfaceConfig] = None

    # Rotor blade support beams (Holme) - optional
    rotor_holms: Optional[list] = None  # List of QgsGeometry polygons for support beams
    foundation_depth: float = 3.5
    foundation_diameter: Optional[float] = None
    gravel_thickness: float = 0.5
    rotor_height_offset: float = 0.0  # Maximum allowed offset (will be optimized)
    rotor_height_offset_max: float = 0.5  # Maximum allowed offset range for optimization

    # Slope/embankment parameters
    slope_angle: float = 45.0  # degrees

    # Optimization parameters - Crane pad height
    search_range_below_fok: float = 0.5
    search_range_above_fok: float = 0.5
    search_step: float = 0.1

    # Optimization parameters - Boom slope
    boom_slope_max: float = 4.0  # Maximum allowed boom slope in percent (will optimize between -max and +max or 0 to ±max)
    boom_slope_optimize: bool = True  # Whether to optimize boom slope
    boom_slope_step_coarse: float = 0.5  # Coarse step for boom slope optimization (percent)
    boom_slope_step_fine: float = 0.1  # Fine step for boom slope optimization (percent)

    # Optimization parameters - Rotor height
    rotor_height_optimize: bool = True  # Whether to optimize rotor height
    rotor_height_step_coarse: float = 0.2  # Coarse step for rotor height optimization (meters)
    rotor_height_step_fine: float = 0.05  # Fine step for rotor height optimization (meters)

    # Optimization mode
    optimize_for_net_earthwork: bool = True  # True = minimize net (Cut-Fill), False = minimize total (Cut+Fill)

    @property
    def search_min_height(self) -> float:
        """Minimum height for optimization search."""
        return self.fok - self.search_range_below_fok

    @property
    def search_max_height(self) -> float:
        """Maximum height for optimization search."""
        return self.fok + self.search_range_above_fok

    @property
    def foundation_bottom_elevation(self) -> float:
        """Elevation of foundation bottom."""
        return self.fok - self.foundation_depth

    def validate(self) -> tuple[bool, str]:
        """
        Validate project configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        errors = []

        # Check FOK is reasonable
        if self.fok < 0 or self.fok > 10000:
            errors.append(f"FOK {self.fok} m ü.NN seems unreasonable")

        # Check foundation depth is positive
        if self.foundation_depth <= 0:
            errors.append(f"Foundation depth must be positive, got {self.foundation_depth}m")

        # Check gravel thickness is reasonable
        if self.gravel_thickness < 0 or self.gravel_thickness > 2.0:
            errors.append(f"Gravel thickness {self.gravel_thickness}m seems unreasonable")

        # Check slope angle is reasonable
        if self.slope_angle < 15 or self.slope_angle > 60:
            errors.append(f"Slope angle {self.slope_angle}° outside reasonable range [15°, 60°]")

        # Check search ranges
        if self.search_range_below_fok < 0:
            errors.append(f"Search range below FOK must be positive")
        if self.search_range_above_fok < 0:
            errors.append(f"Search range above FOK must be positive")
        if self.search_step <= 0:
            errors.append(f"Search step must be positive")

        # Check geometries are valid (required surfaces)
        for surface_name in ['crane_pad', 'foundation']:
            surface = getattr(self, surface_name)
            if surface.geometry.isEmpty():
                errors.append(f"{surface.surface_type.display_name} geometry is empty")
            if not surface.geometry.isGeosValid():
                errors.append(f"{surface.surface_type.display_name} geometry is invalid")

        # Check geometries are valid (optional surfaces)
        for surface_name in ['boom', 'rotor_storage']:
            surface = getattr(self, surface_name)
            if surface is not None:
                if surface.geometry.isEmpty():
                    errors.append(f"{surface.surface_type.display_name} geometry is empty")
                if not surface.geometry.isGeosValid():
                    errors.append(f"{surface.surface_type.display_name} geometry is invalid")

        if errors:
            return False, "; ".join(errors)

        return True, "Valid"


@dataclass
class SurfaceCalculationResult:
    """
    Results for a single surface calculation at a specific height.

    Attributes:
        surface_type: Type of surface
        target_height: Target/design height (can vary across surface for sloped)
        cut_volume: Volume of material to cut (m³)
        fill_volume: Volume of material to fill (m³)
        platform_area: Area of the surface (m²)
        slope_area: Area of embankment/slope (m²)
        total_area: Total area including slope (m²)
        terrain_min: Minimum terrain elevation in surface
        terrain_max: Maximum terrain elevation in surface
        terrain_mean: Mean terrain elevation in surface
        additional_data: Surface-specific additional data
    """
    surface_type: SurfaceType
    target_height: float
    cut_volume: float
    fill_volume: float
    platform_area: float
    slope_area: float = 0.0
    total_area: float = 0.0
    terrain_min: float = 0.0
    terrain_max: float = 0.0
    terrain_mean: float = 0.0
    additional_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def net_volume(self) -> float:
        """Net volume (cut - fill)."""
        return self.cut_volume - self.fill_volume

    @property
    def total_volume_moved(self) -> float:
        """Total volume moved (cut + fill)."""
        return self.cut_volume + self.fill_volume


@dataclass
class MultiSurfaceCalculationResult:
    """
    Complete calculation results for all surfaces at a specific crane pad height.

    Attributes:
        crane_height: Crane pad height (m ü.NN)
        fok: Foundation top edge elevation
        surface_results: Dictionary of results per surface type
        total_cut: Total cut volume across all surfaces
        total_fill: Total fill volume across all surfaces
        total_volume_moved: Total volume moved
        net_volume: Net volume (cut - fill)
        gravel_fill_external: External gravel fill volume (not from site)
        boom_slope_percent: Optimized boom slope in percent
        rotor_height_offset_optimized: Optimized rotor height offset in meters
    """
    crane_height: float
    fok: float
    surface_results: Dict[SurfaceType, SurfaceCalculationResult]
    gravel_fill_external: float = 0.0  # External gravel volume (m³)
    boom_slope_percent: float = 0.0  # Optimized boom slope (%)
    rotor_height_offset_optimized: float = 0.0  # Optimized rotor height offset (m)

    @property
    def total_cut(self) -> float:
        """Total cut volume across all surfaces."""
        return sum(r.cut_volume for r in self.surface_results.values())

    @property
    def total_fill(self) -> float:
        """Total fill volume across all surfaces."""
        return sum(r.fill_volume for r in self.surface_results.values())

    @property
    def total_volume_moved(self) -> float:
        """Total volume moved across all surfaces."""
        return self.total_cut + self.total_fill

    @property
    def net_volume(self) -> float:
        """Net volume across all surfaces."""
        return self.total_cut - self.total_fill

    @property
    def total_platform_area(self) -> float:
        """Total platform area across all surfaces."""
        return sum(r.platform_area for r in self.surface_results.values())

    @property
    def total_slope_area(self) -> float:
        """Total slope area across all surfaces."""
        return sum(r.slope_area for r in self.surface_results.values())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting and serialization."""
        return {
            'crane_height': round(self.crane_height, 2),
            'fok': round(self.fok, 2),
            'total_cut': round(self.total_cut, 1),
            'total_fill': round(self.total_fill, 1),
            'total_volume_moved': round(self.total_volume_moved, 1),
            'net_volume': round(self.net_volume, 1),
            'gravel_fill_external': round(self.gravel_fill_external, 1),
            'boom_slope_percent': round(self.boom_slope_percent, 2),
            'rotor_height_offset_optimized': round(self.rotor_height_offset_optimized, 3),
            'total_platform_area': round(self.total_platform_area, 1),
            'total_slope_area': round(self.total_slope_area, 1),
            'surfaces': {
                surface_type.value: {
                    'target_height': round(result.target_height, 2),
                    'cut': round(result.cut_volume, 1),
                    'fill': round(result.fill_volume, 1),
                    'area': round(result.platform_area, 1),
                    'slope_area': round(result.slope_area, 1),
                    'total_area': round(result.total_area, 1),
                    'terrain_min': round(result.terrain_min, 2),
                    'terrain_max': round(result.terrain_max, 2),
                    'terrain_mean': round(result.terrain_mean, 2),
                    **result.additional_data
                }
                for surface_type, result in self.surface_results.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MultiSurfaceCalculationResult':
        """
        Reconstruct MultiSurfaceCalculationResult from dictionary.

        This is used for deserializing results from parallel workers.

        Args:
            data: Dictionary created by to_dict()

        Returns:
            MultiSurfaceCalculationResult instance
        """
        # Reconstruct surface results
        surface_results = {}
        for surface_type_str, surface_data in data['surfaces'].items():
            surface_type = SurfaceType(surface_type_str)

            # Extract additional_data (everything except known fields)
            known_fields = {
                'target_height', 'cut', 'fill', 'area', 'slope_area',
                'total_area', 'terrain_min', 'terrain_max', 'terrain_mean'
            }
            additional_data = {
                k: v for k, v in surface_data.items()
                if k not in known_fields
            }

            result = SurfaceCalculationResult(
                surface_type=surface_type,
                target_height=surface_data['target_height'],
                cut_volume=surface_data['cut'],
                fill_volume=surface_data['fill'],
                platform_area=surface_data['area'],
                slope_area=surface_data.get('slope_area', 0.0),
                total_area=surface_data.get('total_area', 0.0),
                terrain_min=surface_data.get('terrain_min', 0.0),
                terrain_max=surface_data.get('terrain_max', 0.0),
                terrain_mean=surface_data.get('terrain_mean', 0.0),
                additional_data=additional_data
            )
            surface_results[surface_type] = result

        return cls(
            crane_height=data['crane_height'],
            fok=data['fok'],
            surface_results=surface_results,
            gravel_fill_external=data.get('gravel_fill_external', 0.0),
            boom_slope_percent=data.get('boom_slope_percent', 0.0),
            rotor_height_offset_optimized=data.get('rotor_height_offset_optimized', 0.0)
        )
