"""
Terrain Modeling and Analysis Module

Provides general terrain analysis capabilities including:
- Cut/fill balance optimization
- Volume calculations at specified grade
- Slope analysis
- Contour generation
- Terrain statistics
"""

import math
from typing import List, Tuple, Dict, Optional
import numpy as np
from shapely.geometry import Polygon, Point
import rasterio


def sample_dem_polygon(
    dem_path: str,
    polygon_coords: List[Tuple[float, float]],
    resolution: float = 1.0
) -> List[Tuple[float, float, float]]:
    """
    Sample DEM elevations within a polygon at specified resolution.

    Args:
        dem_path: Path to DEM GeoTIFF file
        polygon_coords: Polygon boundary coordinates
        resolution: Sampling resolution in meters

    Returns:
        List of (x, y, elevation) tuples
    """
    polygon = Polygon(polygon_coords)
    minx, miny, maxx, maxy = polygon.bounds

    # Generate sample points
    sample_points = []
    x = minx
    while x <= maxx:
        y = miny
        while y <= maxy:
            point = Point(x, y)
            if polygon.contains(point):
                sample_points.append((x, y))
            y += resolution
        x += resolution

    # Sample DEM at points
    result = []
    with rasterio.open(dem_path) as src:
        for x, y in sample_points:
            for val in src.sample([(x, y)]):
                elevation = float(val[0])
                if not np.isnan(elevation):
                    result.append((x, y, elevation))

    return result


def calculate_cut_fill_balance(
    elevations: np.ndarray,
    optimization_method: str = "balanced"
) -> Tuple[float, Dict]:
    """
    Find optimal grade elevation to balance cut and fill.

    Args:
        elevations: Array of elevation values
        optimization_method: "mean", "min_cut", or "balanced"

    Returns:
        (optimal_elevation, statistics)
    """
    if optimization_method == "mean":
        optimal_elevation = float(np.mean(elevations))

    elif optimization_method == "min_cut":
        # 40th percentile minimizes cut
        optimal_elevation = float(np.percentile(elevations, 40))

    elif optimization_method == "balanced":
        # Binary search for balanced cut/fill
        min_elev = float(np.min(elevations))
        max_elev = float(np.max(elevations))
        tolerance = 0.01

        for _ in range(50):
            mid = (min_elev + max_elev) / 2
            diff = elevations - mid
            cut = np.sum(np.maximum(diff, 0))
            fill = np.sum(np.maximum(-diff, 0))
            balance = cut - fill

            if abs(balance) < tolerance:
                optimal_elevation = mid
                break

            if balance > 0:
                min_elev = mid
            else:
                max_elev = mid

        optimal_elevation = (min_elev + max_elev) / 2

    else:
        optimal_elevation = float(np.mean(elevations))

    # Calculate statistics at optimal elevation
    diff = elevations - optimal_elevation
    cut_mask = diff > 0
    fill_mask = diff < 0

    stats = {
        "optimal_elevation": optimal_elevation,
        "min_elevation": float(np.min(elevations)),
        "max_elevation": float(np.max(elevations)),
        "avg_elevation": float(np.mean(elevations)),
        "elevation_range": float(np.max(elevations) - np.min(elevations)),
        "cut_points": int(np.sum(cut_mask)),
        "fill_points": int(np.sum(fill_mask)),
        "avg_cut_depth": float(np.mean(diff[cut_mask])) if np.any(cut_mask) else 0.0,
        "avg_fill_depth": float(np.mean(-diff[fill_mask])) if np.any(fill_mask) else 0.0
    }

    return optimal_elevation, stats


def calculate_volume_at_elevation(
    sample_points: List[Tuple[float, float, float]],
    target_elevation: float,
    resolution: float
) -> Dict[str, float]:
    """
    Calculate cut and fill volumes at a specified elevation.

    Args:
        sample_points: List of (x, y, elevation) tuples
        target_elevation: Target grade elevation
        resolution: Sampling resolution (for area calculation)

    Returns:
        Dictionary with volume data
    """
    cell_area = resolution * resolution
    total_cut = 0.0
    total_fill = 0.0

    for x, y, elevation in sample_points:
        diff = elevation - target_elevation
        if diff > 0:
            total_cut += diff * cell_area
        else:
            total_fill += abs(diff) * cell_area

    return {
        "cut_volume": total_cut,
        "fill_volume": total_fill,
        "net_volume": total_cut - total_fill,
        "target_elevation": target_elevation
    }


def calculate_slope_analysis(
    sample_points: List[Tuple[float, float, float]],
    resolution: float
) -> Dict:
    """
    Analyze slope percentages across terrain.

    Args:
        sample_points: List of (x, y, elevation) tuples
        resolution: Sampling resolution

    Returns:
        Dictionary with slope statistics
    """
    # Create 2D grid of elevations
    # Group by y-coordinate first
    points_by_y = {}
    for x, y, z in sample_points:
        y_key = round(y / resolution) * resolution
        if y_key not in points_by_y:
            points_by_y[y_key] = []
        points_by_y[y_key].append((x, y, z))

    # Calculate slopes
    slopes = []

    for y_key, row_points in points_by_y.items():
        # Sort by x
        row_points_sorted = sorted(row_points, key=lambda p: p[0])

        # Calculate slopes between adjacent points in row
        for i in range(len(row_points_sorted) - 1):
            x1, y1, z1 = row_points_sorted[i]
            x2, y2, z2 = row_points_sorted[i + 1]

            # Horizontal distance
            horiz_dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            if horiz_dist > 0:
                # Vertical difference
                vert_diff = abs(z2 - z1)
                # Slope percentage
                slope_pct = (vert_diff / horiz_dist) * 100
                slopes.append(slope_pct)

    if len(slopes) == 0:
        return {
            "avg_slope": 0.0,
            "min_slope": 0.0,
            "max_slope": 0.0,
            "slope_std": 0.0
        }

    slopes_array = np.array(slopes)

    return {
        "avg_slope": float(np.mean(slopes_array)),
        "min_slope": float(np.min(slopes_array)),
        "max_slope": float(np.max(slopes_array)),
        "slope_std": float(np.std(slopes_array)),
        "median_slope": float(np.median(slopes_array)),
        "slope_percentile_90": float(np.percentile(slopes_array, 90))
    }


def generate_contours(
    sample_points: List[Tuple[float, float, float]],
    contour_interval: float = 1.0
) -> Dict:
    """
    Generate contour data (simplified implementation).

    Args:
        sample_points: List of (x, y, elevation) tuples
        contour_interval: Contour interval in meters

    Returns:
        Dictionary with contour information
    """
    if len(sample_points) == 0:
        return {"contours": [], "min_elevation": 0, "max_elevation": 0}

    elevations = [z for x, y, z in sample_points]
    min_elev = min(elevations)
    max_elev = max(elevations)

    # Generate contour levels
    contour_levels = []
    level = math.ceil(min_elev / contour_interval) * contour_interval

    while level <= max_elev:
        contour_levels.append(level)
        level += contour_interval

    # For each contour level, find points near that elevation
    # (This is a simplified approach; full contour generation would use marching squares)
    contours = []
    for level in contour_levels:
        # Find points within ±interval/2 of this level
        tolerance = contour_interval / 2
        points_near_level = [
            (x, y) for x, y, z in sample_points
            if abs(z - level) < tolerance
        ]

        if len(points_near_level) > 0:
            contours.append({
                "elevation": level,
                "point_count": len(points_near_level),
                "sample_points": points_near_level[:20]  # Limit to 20 points per contour
            })

    return {
        "contours": contours,
        "min_elevation": min_elev,
        "max_elevation": max_elev,
        "contour_interval": contour_interval,
        "num_contours": len(contours)
    }


def analyze_terrain(
    dem_path: str,
    polygon: List[Tuple[float, float]],
    analysis_type: str,
    resolution: float = 1.0,
    target_elevation: Optional[float] = None,
    optimization_method: str = "balanced",
    contour_interval: float = 1.0
) -> Dict:
    """
    Perform terrain analysis within a polygon.

    Args:
        dem_path: Path to DEM GeoTIFF file
        polygon: Polygon boundary coordinates
        analysis_type: "cut_fill_balance", "volume_calculation", "slope_analysis", or "contour_generation"
        resolution: Sampling resolution in meters
        target_elevation: Target elevation for volume calculation
        optimization_method: Optimization method for cut/fill balance
        contour_interval: Contour interval for contour generation

    Returns:
        Dictionary with analysis results
    """
    # Sample DEM within polygon
    sample_points = sample_dem_polygon(dem_path, polygon, resolution)

    if len(sample_points) == 0:
        raise ValueError("No valid elevation data found within polygon")

    # Extract elevations
    elevations = np.array([z for x, y, z in sample_points])

    # Calculate polygon area
    polygon_geom = Polygon(polygon)
    polygon_area = polygon_geom.area

    # Perform analysis based on type
    result = {
        "analysis_type": analysis_type,
        "polygon_area": polygon_area,
        "num_sample_points": len(sample_points),
        "resolution": resolution
    }

    if analysis_type == "cut_fill_balance":
        optimal_elev, stats = calculate_cut_fill_balance(elevations, optimization_method)

        # Calculate volumes at optimal elevation
        volume_data = calculate_volume_at_elevation(sample_points, optimal_elev, resolution)

        result.update({
            "optimal_elevation": optimal_elev,
            "cut_volume": volume_data["cut_volume"],
            "fill_volume": volume_data["fill_volume"],
            "net_volume": volume_data["net_volume"],
            "statistics": stats
        })

    elif analysis_type == "volume_calculation":
        if target_elevation is None:
            raise ValueError("target_elevation required for volume_calculation analysis")

        volume_data = calculate_volume_at_elevation(sample_points, target_elevation, resolution)

        result.update({
            "cut_volume": volume_data["cut_volume"],
            "fill_volume": volume_data["fill_volume"],
            "net_volume": volume_data["net_volume"],
            "target_elevation": target_elevation,
            "min_elevation": float(np.min(elevations)),
            "max_elevation": float(np.max(elevations)),
            "avg_elevation": float(np.mean(elevations))
        })

    elif analysis_type == "slope_analysis":
        slope_data = calculate_slope_analysis(sample_points, resolution)

        result.update({
            "slope_analysis": slope_data,
            "min_elevation": float(np.min(elevations)),
            "max_elevation": float(np.max(elevations)),
            "avg_elevation": float(np.mean(elevations))
        })

    elif analysis_type == "contour_generation":
        contour_data = generate_contours(sample_points, contour_interval)

        result.update({
            "contour_data": contour_data
        })

    else:
        raise ValueError(f"Invalid analysis_type: {analysis_type}")

    return result


def validate_terrain_parameters(
    resolution: float,
    contour_interval: Optional[float] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate terrain analysis parameters.

    Returns:
        (is_valid, error_message)
    """
    if resolution < 0.1 or resolution > 10.0:
        return False, "Resolution must be between 0.1 and 10.0 meters"

    if contour_interval is not None:
        if contour_interval < 0.1 or contour_interval > 50.0:
            return False, "Contour interval must be between 0.1 and 50.0 meters"

    return True, None
