"""
Road Earthwork Calculation Module

Calculates cut and fill volumes for road construction based on:
- Road centerline geometry
- Cross-section profile
- Design grade
- Cut and fill slopes
"""

import math
from typing import List, Tuple, Dict, Optional
import numpy as np
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union


def interpolate_elevation_along_line(
    dem_path: str,
    line_coords: List[Tuple[float, float]],
    interval: float = 10.0
) -> List[Tuple[float, float, float]]:
    """
    Sample DEM elevation along a line at regular intervals.

    Args:
        dem_path: Path to DEM GeoTIFF file
        line_coords: List of (x, y) coordinates defining the centerline
        interval: Sampling interval in meters

    Returns:
        List of (x, y, elevation) tuples at each station
    """
    import rasterio
    from shapely.geometry import LineString

    # Create LineString from coordinates
    line = LineString(line_coords)
    total_length = line.length

    # Generate stations along line at intervals
    stations = []
    current_distance = 0.0

    while current_distance <= total_length:
        point = line.interpolate(current_distance)
        stations.append((point.x, point.y, current_distance))
        current_distance += interval

    # Add final point if not already included
    if abs(current_distance - interval - total_length) > 0.01:
        point = line.interpolate(total_length)
        stations.append((point.x, point.y, total_length))

    # Sample DEM at each station
    result = []
    with rasterio.open(dem_path) as src:
        for x, y, distance in stations:
            # Sample single point
            for val in src.sample([(x, y)]):
                elevation = float(val[0])
                if not np.isnan(elevation):
                    result.append((x, y, distance, elevation))

    return result


def calculate_design_elevation(
    start_elevation: float,
    distance: float,
    grade_percent: float
) -> float:
    """
    Calculate design elevation at a given distance based on grade.

    Args:
        start_elevation: Starting elevation (m)
        distance: Distance from start (m)
        grade_percent: Design grade (%, positive = uphill)

    Returns:
        Design elevation at distance (m)
    """
    grade_decimal = grade_percent / 100.0
    return start_elevation + (distance * grade_decimal)


def calculate_cross_section_area(
    cut_depth: float,
    fill_depth: float,
    road_width: float,
    cut_slope: float = 1.5,  # 1:1.5 (1 vertical : 1.5 horizontal)
    fill_slope: float = 2.0,  # 1:2.0
    profile_type: str = "flat"
) -> Dict[str, float]:
    """
    Calculate cross-sectional area for cut or fill.

    Args:
        cut_depth: Depth of cut (m, positive = cut)
        fill_depth: Depth of fill (m, positive = fill)
        road_width: Road width (m)
        cut_slope: Cut slope ratio (H:V)
        fill_slope: Fill slope ratio (H:V)
        profile_type: "flat", "crowned", or "superelevated"

    Returns:
        Dictionary with cut_area and fill_area (m²)
    """
    cut_area = 0.0
    fill_area = 0.0

    # Adjust road width for crowned profile (slight increase due to slope)
    effective_width = road_width
    if profile_type == "crowned":
        # 2% crown adds negligible width
        effective_width = road_width * 1.001
    elif profile_type == "superelevated":
        # Super-elevation can add more
        effective_width = road_width * 1.01

    if cut_depth > 0:
        # Cut section: trapezoidal area
        # Bottom width = road_width
        # Top width = road_width + 2 * (cut_depth * cut_slope)
        # Area = (bottom + top) / 2 * height
        top_width = effective_width + 2 * (cut_depth * cut_slope)
        cut_area = ((effective_width + top_width) / 2) * cut_depth

    if fill_depth > 0:
        # Fill section: trapezoidal area
        top_width = effective_width
        bottom_width = effective_width + 2 * (fill_depth * fill_slope)
        fill_area = ((top_width + bottom_width) / 2) * fill_depth

    return {
        "cut_area": cut_area,
        "fill_area": fill_area
    }


def calculate_volume_between_stations(
    area1: float,
    area2: float,
    distance: float
) -> float:
    """
    Calculate volume between two stations using average-end-area method.

    Args:
        area1: Cross-section area at station 1 (m²)
        area2: Cross-section area at station 2 (m²)
        distance: Distance between stations (m)

    Returns:
        Volume (m³)
    """
    avg_area = (area1 + area2) / 2.0
    return avg_area * distance


def calculate_road_earthwork(
    dem_path: str,
    centerline: List[Tuple[float, float]],
    road_width: float,
    design_grade: float,
    cut_slope: float = 1.5,
    fill_slope: float = 2.0,
    profile_type: str = "flat",
    station_interval: float = 10.0,
    start_elevation: Optional[float] = None
) -> Dict:
    """
    Calculate total cut and fill volumes for a road.

    Args:
        dem_path: Path to DEM GeoTIFF file
        centerline: List of (x, y) coordinates defining road centerline
        road_width: Road width (m)
        design_grade: Design grade (%)
        cut_slope: Cut slope ratio (H:V)
        fill_slope: Fill slope ratio (H:V)
        profile_type: "flat", "crowned", or "superelevated"
        station_interval: Sampling interval (m)
        start_elevation: Starting elevation (if None, use first DEM sample)

    Returns:
        Dictionary with earthwork results
    """
    # Sample DEM along centerline
    stations = interpolate_elevation_along_line(dem_path, centerline, station_interval)

    if len(stations) == 0:
        raise ValueError("No valid elevation data found along road centerline")

    # Use first station elevation as start if not provided
    if start_elevation is None:
        start_elevation = stations[0][3]  # elevation from first station

    # Calculate cut/fill at each station
    station_data = []
    total_cut_volume = 0.0
    total_fill_volume = 0.0
    prev_cut_area = 0.0
    prev_fill_area = 0.0
    prev_distance = 0.0

    for x, y, distance, ground_elevation in stations:
        # Calculate design elevation at this distance
        design_elevation = calculate_design_elevation(start_elevation, distance, design_grade)

        # Determine cut or fill depth
        difference = ground_elevation - design_elevation
        cut_depth = max(0, difference)
        fill_depth = max(0, -difference)

        # Calculate cross-section areas
        areas = calculate_cross_section_area(
            cut_depth=cut_depth,
            fill_depth=fill_depth,
            road_width=road_width,
            cut_slope=cut_slope,
            fill_slope=fill_slope,
            profile_type=profile_type
        )

        cut_area = areas["cut_area"]
        fill_area = areas["fill_area"]

        # Calculate volumes using average-end-area method (except for first station)
        if len(station_data) > 0:
            station_distance = distance - prev_distance
            cut_volume = calculate_volume_between_stations(prev_cut_area, cut_area, station_distance)
            fill_volume = calculate_volume_between_stations(prev_fill_area, fill_area, station_distance)
            total_cut_volume += cut_volume
            total_fill_volume += fill_volume

        # Store station data
        station_data.append({
            "station": len(station_data),
            "distance": distance,
            "x": x,
            "y": y,
            "ground_elevation": ground_elevation,
            "design_elevation": design_elevation,
            "cut_depth": cut_depth,
            "fill_depth": fill_depth,
            "cut_area": cut_area,
            "fill_area": fill_area
        })

        prev_cut_area = cut_area
        prev_fill_area = fill_area
        prev_distance = distance

    # Calculate statistics
    line = LineString(centerline)
    road_length = line.length

    avg_cut_depth = np.mean([s["cut_depth"] for s in station_data if s["cut_depth"] > 0]) if any(s["cut_depth"] > 0 for s in station_data) else 0.0
    avg_fill_depth = np.mean([s["fill_depth"] for s in station_data if s["fill_depth"] > 0]) if any(s["fill_depth"] > 0 for s in station_data) else 0.0

    return {
        "road_length": road_length,
        "total_cut": total_cut_volume,
        "total_fill": total_fill_volume,
        "net_volume": total_cut_volume - total_fill_volume,
        "avg_cut_depth": avg_cut_depth,
        "avg_fill_depth": avg_fill_depth,
        "num_stations": len(station_data),
        "station_interval": station_interval,
        "design_grade": design_grade,
        "road_width": road_width,
        "profile_type": profile_type,
        "stations": station_data,
        "start_elevation": start_elevation,
        "end_elevation": station_data[-1]["design_elevation"] if station_data else start_elevation
    }


def calculate_road_with_ditches(
    dem_path: str,
    centerline: List[Tuple[float, float]],
    road_width: float,
    ditch_width: float,
    ditch_depth: float,
    **kwargs
) -> Dict:
    """
    Calculate road earthwork including side ditches.

    Args:
        dem_path: Path to DEM GeoTIFF file
        centerline: Road centerline coordinates
        road_width: Road width (m)
        ditch_width: Ditch width (m)
        ditch_depth: Ditch depth (m)
        **kwargs: Additional arguments passed to calculate_road_earthwork

    Returns:
        Dictionary with earthwork results including ditches
    """
    # Calculate main road earthwork
    road_result = calculate_road_earthwork(
        dem_path=dem_path,
        centerline=centerline,
        road_width=road_width,
        **kwargs
    )

    # Calculate ditch volumes (simplified: rectangular cross-section)
    # Two ditches (one on each side)
    ditch_area_per_side = ditch_width * ditch_depth
    total_ditch_area = 2 * ditch_area_per_side
    ditch_volume = total_ditch_area * road_result["road_length"]

    # Add ditch volume to total cut
    road_result["ditch_cut"] = ditch_volume
    road_result["total_cut"] += ditch_volume
    road_result["net_volume"] = road_result["total_cut"] - road_result["total_fill"]

    return road_result


def validate_road_parameters(
    road_width: float,
    design_grade: float,
    cut_slope: float,
    fill_slope: float
) -> Tuple[bool, Optional[str]]:
    """
    Validate road design parameters.

    Returns:
        (is_valid, error_message)
    """
    if road_width < 2.0 or road_width > 20.0:
        return False, "Road width must be between 2.0 and 20.0 meters"

    if abs(design_grade) > 15.0:
        return False, "Design grade must be between -15% and +15%"

    if cut_slope < 0.5 or cut_slope > 3.0:
        return False, "Cut slope must be between 0.5 and 3.0 (H:V)"

    if fill_slope < 1.0 or fill_slope > 4.0:
        return False, "Fill slope must be between 1.0 and 4.0 (H:V)"

    return True, None
