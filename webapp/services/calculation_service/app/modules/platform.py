"""
Platform (Crane Pad) Cut/Fill Calculations

Extrahiert aus QGIS Plugin WindTurbine_Earthwork_Calculator.py
Konvertiert zu rasterio/shapely (statt QGIS)
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import math
import logging

from app.core.dem_sampling import sample_dem_polygon, sample_dem_efficient
from app.modules.optimization import optimize_platform_height

logger = logging.getLogger(__name__)


def calculate_platform_cutfill_polygon(
    dem_path: str,
    platform_polygon: List[Tuple[float, float]],
    slope_width: float,
    slope_angle: float,
    optimization_method: str = "mean",
    resolution: float = 0.5
) -> Dict:
    """
    Berechnet Cut/Fill für beliebige Polygon-Form

    Basiert auf: WindTurbine_Earthwork_Calculator.py:2104-2191
    (_calculate_crane_pad_polygon)

    Args:
        dem_path: Path to DEM GeoTIFF
        platform_polygon: List of (x, y) coordinates defining platform
        slope_width: Width of slope area in meters
        slope_angle: Slope angle in degrees
        optimization_method: "mean", "min_cut", or "balanced"
        resolution: Sampling resolution in meters

    Returns:
        Dict with volumes and statistics
    """
    logger.info(f"Calculating platform cut/fill for polygon (optimization: {optimization_method})")

    # 1. Sample DEM within platform area
    platform_points = sample_dem_polygon(dem_path, platform_polygon, resolution)

    if len(platform_points) == 0:
        raise ValueError("No DEM data found within platform polygon")

    # 2. Optimize platform height
    elevations = np.array([z for (x, y, z) in platform_points], dtype=float)

    platform_height = optimize_platform_height(elevations, optimization_method)

    logger.info(f"  Optimized platform height: {platform_height:.2f}m")
    logger.info(f"  Terrain: min={np.min(elevations):.2f}m, max={np.max(elevations):.2f}m, mean={np.mean(elevations):.2f}m")

    # 3. Create slope polygon
    platform_poly = Polygon(platform_polygon)
    slope_poly = platform_poly.buffer(slope_width)

    # Get slope area (excluding platform)
    slope_coords = list(slope_poly.exterior.coords)

    # 4. Sample DEM within slope area
    slope_points = sample_dem_polygon(dem_path, slope_coords, resolution)

    # 5. Calculate Cut/Fill on platform
    platform_cut = 0.0
    platform_fill = 0.0
    cell_area = resolution * resolution

    for (x, y, existing_z) in platform_points:
        diff = existing_z - platform_height
        if diff > 0:  # Cut
            platform_cut += diff * cell_area
        else:  # Fill
            platform_fill += abs(diff) * cell_area

    # 6. Calculate Cut/Fill on slope
    slope_cut = 0.0
    slope_fill = 0.0

    for (x, y, existing_z) in slope_points:
        point = Point(x, y)

        # Skip points inside platform
        if platform_poly.contains(point):
            continue

        # Calculate target height on slope
        target_z = calculate_slope_height(
            x, y, platform_polygon, platform_height, slope_angle, slope_width
        )

        diff = existing_z - target_z
        if diff > 0:  # Cut
            slope_cut += diff * cell_area
        else:  # Fill
            slope_fill += abs(diff) * cell_area

    # 7. Statistics
    platform_area = platform_poly.area
    total_area = slope_poly.area

    return {
        'platform_height': round(platform_height, 2),
        'terrain_min': round(float(np.min(elevations)), 2),
        'terrain_max': round(float(np.max(elevations)), 2),
        'terrain_mean': round(float(np.mean(elevations)), 2),
        'terrain_std': round(float(np.std(elevations)), 2),
        'terrain_range': round(float(np.max(elevations) - np.min(elevations)), 2),
        'platform_cut': round(platform_cut, 1),
        'platform_fill': round(platform_fill, 1),
        'slope_cut': round(slope_cut, 1),
        'slope_fill': round(slope_fill, 1),
        'total_cut': round(platform_cut + slope_cut, 1),
        'total_fill': round(platform_fill + slope_fill, 1),
        'platform_area': round(platform_area, 1),
        'total_area': round(total_area, 1)
    }


def calculate_platform_cutfill_rectangle(
    dem_path: str,
    center_x: float,
    center_y: float,
    length: float,
    width: float,
    slope_width: float,
    slope_angle: float,
    optimization_method: str = "mean",
    rotation_angle: float = 0.0,
    resolution: float = 0.5
) -> Dict:
    """
    Berechnet Cut/Fill für rechteckige Plattform mit optionaler Rotation

    Basiert auf: WindTurbine_Earthwork_Calculator.py:2193-2254
    (_calculate_crane_pad)

    Args:
        dem_path: Path to DEM GeoTIFF
        center_x: Center X coordinate
        center_y: Center Y coordinate
        length: Platform length in meters
        width: Platform width in meters
        slope_width: Width of slope area in meters
        slope_angle: Slope angle in degrees
        optimization_method: "mean", "min_cut", or "balanced"
        rotation_angle: Rotation angle in degrees (0 = no rotation)
        resolution: Sampling resolution in meters

    Returns:
        Dict with volumes and statistics
    """
    logger.info(f"Calculating platform cut/fill for rectangle ({length}x{width}m, rotation: {rotation_angle}°)")

    # 1. Create platform polygon with rotation
    platform_polygon = create_rotated_rectangle(
        center_x, center_y, length, width, rotation_angle
    )

    # 2. Use polygon-based calculation
    result = calculate_platform_cutfill_polygon(
        dem_path,
        platform_polygon,
        slope_width,
        slope_angle,
        optimization_method,
        resolution
    )

    return result


def create_rotated_rectangle(
    center_x: float,
    center_y: float,
    length: float,
    width: float,
    rotation_degrees: float = 0.0
) -> List[Tuple[float, float]]:
    """
    Create a rotated rectangle polygon

    Args:
        center_x: Center X coordinate
        center_y: Center Y coordinate
        length: Length (along rotation axis)
        width: Width
        rotation_degrees: Rotation angle in degrees

    Returns:
        List of (x, y) corner coordinates
    """
    # Half dimensions
    half_length = length / 2
    half_width = width / 2

    # Corner points (unrotated)
    corners = [
        (-half_length, -half_width),
        (half_length, -half_width),
        (half_length, half_width),
        (-half_length, half_width)
    ]

    # Rotate and translate
    rotation_rad = math.radians(rotation_degrees)
    cos_angle = math.cos(rotation_rad)
    sin_angle = math.sin(rotation_rad)

    rotated_corners = []
    for (dx, dy) in corners:
        # Rotate
        x_rot = dx * cos_angle - dy * sin_angle
        y_rot = dx * sin_angle + dy * cos_angle

        # Translate to center
        x = center_x + x_rot
        y = center_y + y_rot

        rotated_corners.append((x, y))

    return rotated_corners


def calculate_slope_height(
    x: float,
    y: float,
    platform_polygon: List[Tuple[float, float]],
    platform_height: float,
    slope_angle: float,
    slope_width: float
) -> float:
    """
    Calculate target height on slope

    Args:
        x: Point X coordinate
        y: Point Y coordinate
        platform_polygon: Platform polygon coordinates
        platform_height: Platform height
        slope_angle: Slope angle in degrees
        slope_width: Slope width

    Returns:
        Target elevation at point
    """
    point = Point(x, y)
    platform_poly = Polygon(platform_polygon)

    # Distance to platform edge
    distance = point.distance(platform_poly.exterior)

    if distance > slope_width:
        # Beyond slope → natural terrain
        return platform_height  # Will be handled by DEM sampling

    # Height change on slope
    slope_ratio = math.tan(math.radians(slope_angle))
    height_change = distance * slope_ratio

    # Target height = platform height - height change
    target_height = platform_height - height_change

    return target_height


def calculate_slope_statistics(
    platform_cut: float,
    platform_fill: float,
    slope_cut: float,
    slope_fill: float
) -> Dict:
    """
    Calculate additional slope statistics

    Args:
        platform_cut: Platform cut volume
        platform_fill: Platform fill volume
        slope_cut: Slope cut volume
        slope_fill: Slope fill volume

    Returns:
        Dict with statistics
    """
    total_cut = platform_cut + slope_cut
    total_fill = platform_fill + slope_fill
    net_volume = total_cut - total_fill

    return {
        'total_cut': round(total_cut, 1),
        'total_fill': round(total_fill, 1),
        'net_volume': round(net_volume, 1),
        'cut_fill_ratio': round(total_cut / total_fill, 2) if total_fill > 0 else 0.0,
        'platform_cut_pct': round(100 * platform_cut / total_cut, 1) if total_cut > 0 else 0.0,
        'slope_cut_pct': round(100 * slope_cut / total_cut, 1) if total_cut > 0 else 0.0
    }
