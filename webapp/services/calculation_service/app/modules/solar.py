"""
Solar Park Earthwork Calculation Module

Calculates earthwork for solar panel installations including:
- Panel array layout generation
- Foundation volumes
- Access road earthwork
- Site grading (minimal, terraced, or full)
"""

import math
from typing import List, Tuple, Dict, Optional
import numpy as np
from shapely.geometry import Point, Polygon, LineString, MultiPoint
from shapely.affinity import rotate, translate


def generate_solar_array_layout(
    boundary: Polygon,
    panel_length: float,
    panel_width: float,
    row_spacing: float,
    panel_tilt: float,
    orientation: float = 180.0  # South-facing (180°)
) -> List[Tuple[float, float]]:
    """
    Generate panel positions within a boundary polygon.

    Args:
        boundary: Site boundary polygon
        panel_length: Panel length in meters
        panel_width: Panel width in meters
        row_spacing: Spacing between panel rows in meters
        panel_tilt: Panel tilt angle in degrees
        orientation: Panel azimuth in degrees (180 = south)

    Returns:
        List of (x, y) coordinates for panel center points
    """
    # Get boundary bounds
    minx, miny, maxx, maxy = boundary.bounds

    # Calculate effective row spacing (considering panel tilt)
    tilt_rad = math.radians(panel_tilt)
    panel_height = panel_length * math.sin(tilt_rad)
    panel_ground_length = panel_length * math.cos(tilt_rad)

    # Minimum row spacing to avoid shading
    # Rule of thumb: 2.5 * panel height
    min_spacing = 2.5 * panel_height
    effective_spacing = max(row_spacing, min_spacing)

    # Generate grid points
    panel_positions = []

    current_y = miny + effective_spacing / 2

    while current_y < maxy:
        current_x = minx + panel_width / 2

        while current_x < maxx:
            point = Point(current_x, current_y)

            # Check if point is within boundary
            if boundary.contains(point):
                panel_positions.append((current_x, current_y))

            current_x += panel_width + 1.0  # 1m spacing between panels in row

        current_y += effective_spacing

    return panel_positions


def calculate_foundation_volumes(
    foundation_type: str,
    num_panels: int,
    panel_length: float,
    panel_width: float
) -> Dict[str, float]:
    """
    Calculate foundation volumes for solar panels.

    Args:
        foundation_type: "driven_piles", "concrete_footings", or "screw_anchors"
        num_panels: Number of panels
        panel_length: Panel length in meters
        panel_width: Panel width in meters

    Returns:
        Dictionary with foundation data
    """
    # Typical foundation specifications per panel
    foundations = {
        "driven_piles": {
            "volume_per_panel": 0.05,  # m³ per panel (steel piles, minimal excavation)
            "description": "Steel piles driven into ground"
        },
        "concrete_footings": {
            "volume_per_panel": 0.3,  # m³ per panel (concrete footings)
            "description": "Concrete footings"
        },
        "screw_anchors": {
            "volume_per_panel": 0.02,  # m³ per panel (minimal excavation)
            "description": "Screw anchors"
        }
    }

    if foundation_type not in foundations:
        foundation_type = "driven_piles"  # Default

    spec = foundations[foundation_type]
    total_volume = num_panels * spec["volume_per_panel"]

    return {
        "foundation_type": foundation_type,
        "volume_per_panel": spec["volume_per_panel"],
        "total_volume": total_volume,
        "num_panels": num_panels,
        "description": spec["description"]
    }


def calculate_grading_minimal(
    dem_path: str,
    boundary: Polygon,
    inverter_positions: List[Tuple[float, float]],
    level_area_size: float = 10.0  # m² around each inverter
) -> Dict[str, float]:
    """
    Minimal grading: Only level areas under inverters/transformers.

    Args:
        dem_path: Path to DEM GeoTIFF
        boundary: Site boundary
        inverter_positions: List of inverter locations
        level_area_size: Size of leveled area around each inverter (m²)

    Returns:
        Grading volumes
    """
    import rasterio

    total_cut = 0.0
    total_fill = 0.0

    with rasterio.open(dem_path) as src:
        for x, y in inverter_positions:
            # Sample elevation at inverter location
            for val in src.sample([(x, y)]):
                target_elevation = float(val[0])

                # Create small level area around inverter
                area_radius = math.sqrt(level_area_size / math.pi)

                # Sample points in circle around inverter
                num_samples = 20
                for i in range(num_samples):
                    angle = (2 * math.pi * i) / num_samples
                    sample_x = x + area_radius * math.cos(angle)
                    sample_y = y + area_radius * math.sin(angle)

                    for sample_val in src.sample([(sample_x, sample_y)]):
                        ground_elevation = float(sample_val[0])
                        if not np.isnan(ground_elevation):
                            diff = ground_elevation - target_elevation
                            if diff > 0:
                                total_cut += diff * (level_area_size / num_samples)
                            else:
                                total_fill += abs(diff) * (level_area_size / num_samples)

    return {
        "grading_cut": total_cut,
        "grading_fill": total_fill,
        "num_leveled_areas": len(inverter_positions)
    }


def calculate_grading_full(
    dem_path: str,
    boundary: Polygon,
    target_elevation: Optional[float] = None,
    optimization_method: str = "balanced",
    resolution: float = 2.0
) -> Dict[str, float]:
    """
    Full site grading: Level entire site to optimal elevation.

    Args:
        dem_path: Path to DEM GeoTIFF
        boundary: Site boundary
        target_elevation: Target elevation (if None, use optimization)
        optimization_method: "mean", "min_cut", or "balanced"
        resolution: Sampling resolution in meters

    Returns:
        Grading volumes
    """
    import rasterio

    # Sample DEM within boundary
    minx, miny, maxx, maxy = boundary.bounds
    sample_points = []

    x = minx
    while x <= maxx:
        y = miny
        while y <= maxy:
            point = Point(x, y)
            if boundary.contains(point):
                sample_points.append((x, y))
            y += resolution
        x += resolution

    # Get elevations
    elevations = []
    with rasterio.open(dem_path) as src:
        for x, y in sample_points:
            for val in src.sample([(x, y)]):
                elevation = float(val[0])
                if not np.isnan(elevation):
                    elevations.append(elevation)

    if len(elevations) == 0:
        return {"grading_cut": 0.0, "grading_fill": 0.0, "target_elevation": 0.0}

    elevations_array = np.array(elevations)

    # Determine target elevation
    if target_elevation is None:
        if optimization_method == "mean":
            target_elevation = float(np.mean(elevations_array))
        elif optimization_method == "min_cut":
            target_elevation = float(np.percentile(elevations_array, 40))
        elif optimization_method == "balanced":
            # Binary search for balanced cut/fill
            min_elev = float(np.min(elevations_array))
            max_elev = float(np.max(elevations_array))
            tolerance = 0.01

            for _ in range(50):
                mid = (min_elev + max_elev) / 2
                diff = elevations_array - mid
                cut = np.sum(np.maximum(diff, 0))
                fill = np.sum(np.maximum(-diff, 0))
                balance = cut - fill

                if abs(balance) < tolerance:
                    target_elevation = mid
                    break

                if balance > 0:
                    min_elev = mid
                else:
                    max_elev = mid

            target_elevation = (min_elev + max_elev) / 2

    # Calculate cut and fill volumes
    cell_area = resolution * resolution
    total_cut = 0.0
    total_fill = 0.0

    for elevation in elevations:
        diff = elevation - target_elevation
        if diff > 0:
            total_cut += diff * cell_area
        else:
            total_fill += abs(diff) * cell_area

    return {
        "grading_cut": total_cut,
        "grading_fill": total_fill,
        "target_elevation": target_elevation,
        "site_area": len(sample_points) * cell_area
    }


def calculate_solar_park_earthwork(
    dem_path: str,
    boundary: List[Tuple[float, float]],
    panel_length: float,
    panel_width: float,
    row_spacing: float,
    panel_tilt: float,
    foundation_type: str,
    grading_strategy: str = "minimal",
    orientation: float = 180.0,
    access_road_width: float = 4.0,
    access_road_length: Optional[float] = None
) -> Dict:
    """
    Calculate total earthwork for solar park installation.

    Args:
        dem_path: Path to DEM GeoTIFF
        boundary: Site boundary coordinates
        panel_length: Panel length (m)
        panel_width: Panel width (m)
        row_spacing: Row spacing (m)
        panel_tilt: Panel tilt angle (°)
        foundation_type: "driven_piles", "concrete_footings", or "screw_anchors"
        grading_strategy: "minimal", "terraced", or "full"
        orientation: Panel azimuth (°)
        access_road_width: Access road width (m)
        access_road_length: Access road length (m), if None calculated as perimeter/4

    Returns:
        Dictionary with earthwork results
    """
    # Create boundary polygon
    boundary_polygon = Polygon(boundary)
    site_area = boundary_polygon.area

    # Generate panel array layout
    panel_positions = generate_solar_array_layout(
        boundary=boundary_polygon,
        panel_length=panel_length,
        panel_width=panel_width,
        row_spacing=row_spacing,
        panel_tilt=panel_tilt,
        orientation=orientation
    )

    num_panels = len(panel_positions)
    if num_panels == 0:
        raise ValueError("No panels could be placed within the boundary")

    # Calculate foundation volumes
    foundation_result = calculate_foundation_volumes(
        foundation_type=foundation_type,
        num_panels=num_panels,
        panel_length=panel_length,
        panel_width=panel_width
    )

    # Calculate grading based on strategy
    if grading_strategy == "minimal":
        # Assume 1 inverter per 50 panels
        num_inverters = max(1, num_panels // 50)
        # Place inverters evenly across site
        inverter_positions = []
        step = len(panel_positions) // num_inverters if num_inverters > 0 else 1
        for i in range(0, len(panel_positions), step):
            if i < len(panel_positions):
                inverter_positions.append(panel_positions[i])

        grading_result = calculate_grading_minimal(
            dem_path=dem_path,
            boundary=boundary_polygon,
            inverter_positions=inverter_positions
        )

    elif grading_strategy == "full":
        grading_result = calculate_grading_full(
            dem_path=dem_path,
            boundary=boundary_polygon,
            optimization_method="balanced"
        )

    else:  # terraced (simplified: between minimal and full)
        full_grading = calculate_grading_full(
            dem_path=dem_path,
            boundary=boundary_polygon,
            optimization_method="balanced"
        )
        # Terraced grading is ~50% of full grading
        grading_result = {
            "grading_cut": full_grading["grading_cut"] * 0.5,
            "grading_fill": full_grading["grading_fill"] * 0.5,
            "target_elevation": full_grading.get("target_elevation", 0.0)
        }

    # Calculate access road earthwork (simplified)
    if access_road_length is None:
        # Estimate access road as perimeter / 4
        access_road_length = boundary_polygon.length / 4

    # Simplified road calculation: assume flat road with minimal cut/fill
    # Use average cut/fill of 0.5m depth, road width
    road_area = access_road_length * access_road_width
    avg_road_depth = 0.3  # m (typical for access roads)
    road_cut = road_area * avg_road_depth * 0.6  # 60% cut
    road_fill = road_area * avg_road_depth * 0.4  # 40% fill

    # Total volumes
    total_cut = foundation_result["total_volume"] + grading_result["grading_cut"] + road_cut
    total_fill = grading_result["grading_fill"] + road_fill

    # Panel array specifications
    total_panel_area = num_panels * panel_length * panel_width
    panel_density = num_panels / site_area  # panels per m²

    return {
        "num_panels": num_panels,
        "panel_area": total_panel_area,
        "panel_density": panel_density,
        "site_area": site_area,
        "foundation_volume": foundation_result["total_volume"],
        "foundation_type": foundation_result["foundation_type"],
        "grading_cut": grading_result["grading_cut"],
        "grading_fill": grading_result["grading_fill"],
        "grading_strategy": grading_strategy,
        "access_road_cut": road_cut,
        "access_road_fill": road_fill,
        "access_road_length": access_road_length,
        "total_cut": total_cut,
        "total_fill": total_fill,
        "net_volume": total_cut - total_fill,
        "panel_positions": panel_positions[:100]  # Limit to first 100 for response size
    }


def validate_solar_parameters(
    panel_length: float,
    panel_width: float,
    row_spacing: float,
    panel_tilt: float
) -> Tuple[bool, Optional[str]]:
    """
    Validate solar park parameters.

    Returns:
        (is_valid, error_message)
    """
    if panel_length < 0.5 or panel_length > 3.0:
        return False, "Panel length must be between 0.5 and 3.0 meters"

    if panel_width < 0.5 or panel_width > 2.5:
        return False, "Panel width must be between 0.5 and 2.5 meters"

    if row_spacing < 2.0 or row_spacing > 20.0:
        return False, "Row spacing must be between 2.0 and 20.0 meters"

    if panel_tilt < 0 or panel_tilt > 60:
        return False, "Panel tilt must be between 0° and 60°"

    return True, None
