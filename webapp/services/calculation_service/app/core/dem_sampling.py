"""
DEM Sampling Utilities

Extrahiert aus QGIS Plugin WindTurbine_Earthwork_Calculator.py
Konvertiert zu rasterio (statt QGIS QgsRasterLayer)
"""
import numpy as np
from typing import List, Tuple, Optional
import rasterio
from rasterio.windows import Window
from shapely.geometry import Point, Polygon, box
import logging

logger = logging.getLogger(__name__)


def sample_dem_at_points(
    dem_path: str,
    coordinates: List[Tuple[float, float]]
) -> np.ndarray:
    """
    Sample DEM at specific coordinates

    Args:
        dem_path: Path to GeoTIFF file
        coordinates: List of (x, y) tuples in DEM CRS

    Returns:
        NumPy array of elevation values
    """
    with rasterio.open(dem_path) as src:
        # Sample at coordinates
        elevations = []
        for coords in src.sample(coordinates):
            elevations.append(coords[0])

        return np.array(elevations, dtype=float)


def sample_dem_grid(
    dem_path: str,
    center_x: float,
    center_y: float,
    width: float,
    height: float,
    resolution: float = 0.5
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Sample DEM on a regular grid around a center point

    Args:
        dem_path: Path to GeoTIFF file
        center_x: Center X coordinate
        center_y: Center Y coordinate
        width: Grid width in meters
        height: Grid height in meters
        resolution: Sampling resolution in meters

    Returns:
        Tuple of (dem_data, x_coords, y_coords)
    """
    with rasterio.open(dem_path) as src:
        # Calculate bounds
        min_x = center_x - width / 2
        max_x = center_x + width / 2
        min_y = center_y - height / 2
        max_y = center_y + height / 2

        # Create coordinate arrays
        x_coords = np.arange(min_x, max_x, resolution)
        y_coords = np.arange(min_y, max_y, resolution)

        # Sample DEM
        dem_data = np.zeros((len(y_coords), len(x_coords)), dtype=float)

        for i, y in enumerate(y_coords):
            for j, x in enumerate(x_coords):
                # Sample at this point
                coords_list = [(x, y)]
                for val in src.sample(coords_list):
                    dem_data[i, j] = val[0]

        return dem_data, x_coords, y_coords


def sample_dem_polygon(
    dem_path: str,
    polygon_coords: List[Tuple[float, float]],
    resolution: float = 0.5
) -> List[Tuple[float, float, float]]:
    """
    Sample DEM within a polygon

    Args:
        dem_path: Path to GeoTIFF file
        polygon_coords: List of (x, y) tuples defining polygon
        resolution: Sampling resolution in meters

    Returns:
        List of (x, y, z) tuples
    """
    polygon = Polygon(polygon_coords)
    minx, miny, maxx, maxy = polygon.bounds

    # Create sample points
    sample_points = []

    x_range = np.arange(minx, maxx, resolution)
    y_range = np.arange(miny, maxy, resolution)

    for x in x_range:
        for y in y_range:
            point = Point(x, y)
            if polygon.contains(point):
                sample_points.append((x, y))

    if not sample_points:
        return []

    # Sample DEM at these points
    with rasterio.open(dem_path) as src:
        result = []
        for coords in src.sample(sample_points):
            x, y = sample_points[len(result)]
            elevation = coords[0]
            if not np.isnan(elevation):
                result.append((x, y, float(elevation)))

    return result


def sample_dem_efficient(
    dem_path: str,
    polygon_coords: List[Tuple[float, float]],
    resolution: float = 0.5
) -> Tuple[np.ndarray, List[Tuple[float, float]]]:
    """
    Efficient DEM sampling within polygon using windowed reading

    Args:
        dem_path: Path to GeoTIFF file
        polygon_coords: List of (x, y) tuples defining polygon
        resolution: Sampling resolution in meters

    Returns:
        Tuple of (elevation_array, coordinate_list)
    """
    polygon = Polygon(polygon_coords)
    minx, miny, maxx, maxy = polygon.bounds

    with rasterio.open(dem_path) as src:
        # Convert bounds to pixel coordinates
        row_start, col_start = src.index(minx, maxy)
        row_stop, col_stop = src.index(maxx, miny)

        # Read window
        window = Window(
            col_off=max(0, col_start),
            row_off=max(0, row_start),
            width=min(src.width - col_start, col_stop - col_start),
            height=min(src.height - row_start, row_stop - row_start)
        )

        data = src.read(1, window=window)
        transform = src.window_transform(window)

        # Create coordinate arrays
        elevations = []
        coords = []

        rows, cols = data.shape
        for row in range(0, rows, max(1, int(resolution / src.res[0]))):
            for col in range(0, cols, max(1, int(resolution / src.res[1]))):
                x, y = rasterio.transform.xy(transform, row, col)
                point = Point(x, y)

                if polygon.contains(point):
                    elevation = data[row, col]
                    if not np.isnan(elevation):
                        elevations.append(float(elevation))
                        coords.append((x, y))

        return np.array(elevations, dtype=float), coords


def get_dem_bounds(dem_path: str) -> Tuple[float, float, float, float]:
    """
    Get DEM bounding box

    Args:
        dem_path: Path to GeoTIFF file

    Returns:
        Tuple of (minx, miny, maxx, maxy)
    """
    with rasterio.open(dem_path) as src:
        bounds = src.bounds
        return bounds.left, bounds.bottom, bounds.right, bounds.top


def get_dem_resolution(dem_path: str) -> Tuple[float, float]:
    """
    Get DEM resolution

    Args:
        dem_path: Path to GeoTIFF file

    Returns:
        Tuple of (x_resolution, y_resolution) in meters
    """
    with rasterio.open(dem_path) as src:
        return src.res[0], src.res[1]
