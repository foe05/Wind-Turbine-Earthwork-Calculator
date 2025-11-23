"""
3D Geometry utility functions for Wind Turbine Earthwork Calculator V2

Provides functions for creating 3D geometries (PolygonZ, LineStringZ)
for QGIS 3D visualization of earthwork results.

Author: Wind Energy Site Planning
Version: 2.0.0 - 3D Extension
"""

import math
import numpy as np
from typing import Optional
from osgeo import gdal

from qgis.core import (
    QgsGeometry,
    QgsPointXY,
    QgsPoint,
    QgsLineString,
    QgsPolygon,
    QgsMultiPolygon,
    QgsWkbTypes
)


def polygon_to_polygonz(geometry: QgsGeometry, z_value: float) -> QgsGeometry:
    """
    Convert a 2D polygon to a 3D PolygonZ with constant Z value.

    Args:
        geometry: 2D polygon geometry
        z_value: Z coordinate (height) for all vertices

    Returns:
        QgsGeometry: 3D PolygonZ geometry
    """
    if geometry.isEmpty():
        return QgsGeometry()

    if geometry.isMultipart():
        # Handle MultiPolygon
        multi_polygon = QgsMultiPolygon()
        polygons_2d = geometry.asMultiPolygon()

        for polygon_2d in polygons_2d:
            polygon_3d = QgsPolygon()

            # Exterior ring
            if polygon_2d:
                exterior_points = [
                    QgsPoint(pt.x(), pt.y(), z_value)
                    for pt in polygon_2d[0]
                ]
                exterior_ring = QgsLineString(exterior_points)
                polygon_3d.setExteriorRing(exterior_ring)

                # Interior rings (holes)
                for i in range(1, len(polygon_2d)):
                    interior_points = [
                        QgsPoint(pt.x(), pt.y(), z_value)
                        for pt in polygon_2d[i]
                    ]
                    interior_ring = QgsLineString(interior_points)
                    polygon_3d.addInteriorRing(interior_ring)

            multi_polygon.addGeometry(polygon_3d)

        return QgsGeometry(multi_polygon)
    else:
        # Handle single Polygon
        polygon_2d = geometry.asPolygon()
        if not polygon_2d:
            return QgsGeometry()

        polygon_3d = QgsPolygon()

        # Exterior ring
        exterior_points = [
            QgsPoint(pt.x(), pt.y(), z_value)
            for pt in polygon_2d[0]
        ]
        exterior_ring = QgsLineString(exterior_points)
        polygon_3d.setExteriorRing(exterior_ring)

        # Interior rings (holes)
        for i in range(1, len(polygon_2d)):
            interior_points = [
                QgsPoint(pt.x(), pt.y(), z_value)
                for pt in polygon_2d[i]
            ]
            interior_ring = QgsLineString(interior_points)
            polygon_3d.addInteriorRing(interior_ring)

        return QgsGeometry(polygon_3d)


def polygon_to_polygonz_with_dem(
    geometry: QgsGeometry,
    dem_path: str,
    z_offset: float = 0.0
) -> QgsGeometry:
    """
    Convert a 2D polygon to a 3D PolygonZ with Z values from DEM.

    Each vertex gets its Z value from the DEM plus an optional offset.

    Args:
        geometry: 2D polygon geometry
        dem_path: Path to DEM raster file
        z_offset: Additional offset to add to DEM values (meters)

    Returns:
        QgsGeometry: 3D PolygonZ geometry with terrain heights
    """
    if geometry.isEmpty():
        return QgsGeometry()

    # Open DEM
    dem_ds = gdal.Open(dem_path)
    if dem_ds is None:
        raise ValueError(f"Could not open DEM: {dem_path}")

    dem_band = dem_ds.GetRasterBand(1)
    dem_transform = dem_ds.GetGeoTransform()

    def get_dem_z(x: float, y: float) -> float:
        """Get Z value from DEM at given coordinates."""
        col = int((x - dem_transform[0]) / dem_transform[1])
        row = int((y - dem_transform[3]) / dem_transform[5])

        # Clamp to valid range
        col = max(0, min(col, dem_ds.RasterXSize - 1))
        row = max(0, min(row, dem_ds.RasterYSize - 1))

        z = dem_band.ReadAsArray(col, row, 1, 1)[0, 0]
        return float(z) + z_offset

    if geometry.isMultipart():
        multi_polygon = QgsMultiPolygon()
        polygons_2d = geometry.asMultiPolygon()

        for polygon_2d in polygons_2d:
            polygon_3d = QgsPolygon()

            if polygon_2d:
                # Exterior ring
                exterior_points = [
                    QgsPoint(pt.x(), pt.y(), get_dem_z(pt.x(), pt.y()))
                    for pt in polygon_2d[0]
                ]
                exterior_ring = QgsLineString(exterior_points)
                polygon_3d.setExteriorRing(exterior_ring)

                # Interior rings
                for i in range(1, len(polygon_2d)):
                    interior_points = [
                        QgsPoint(pt.x(), pt.y(), get_dem_z(pt.x(), pt.y()))
                        for pt in polygon_2d[i]
                    ]
                    interior_ring = QgsLineString(interior_points)
                    polygon_3d.addInteriorRing(interior_ring)

            multi_polygon.addGeometry(polygon_3d)

        dem_ds = None
        return QgsGeometry(multi_polygon)
    else:
        polygon_2d = geometry.asPolygon()
        if not polygon_2d:
            dem_ds = None
            return QgsGeometry()

        polygon_3d = QgsPolygon()

        # Exterior ring
        exterior_points = [
            QgsPoint(pt.x(), pt.y(), get_dem_z(pt.x(), pt.y()))
            for pt in polygon_2d[0]
        ]
        exterior_ring = QgsLineString(exterior_points)
        polygon_3d.setExteriorRing(exterior_ring)

        # Interior rings
        for i in range(1, len(polygon_2d)):
            interior_points = [
                QgsPoint(pt.x(), pt.y(), get_dem_z(pt.x(), pt.y()))
                for pt in polygon_2d[i]
            ]
            interior_ring = QgsLineString(interior_points)
            polygon_3d.addInteriorRing(interior_ring)

        dem_ds = None
        return QgsGeometry(polygon_3d)


def polygon_to_sloped_polygonz(
    geometry: QgsGeometry,
    base_height: float,
    slope_percent: float,
    slope_direction_deg: float
) -> QgsGeometry:
    """
    Convert a 2D polygon to a 3D PolygonZ with sloped surface.

    The height varies across the polygon based on slope direction and percent.
    Used for boom surfaces with longitudinal slope.

    Args:
        geometry: 2D polygon geometry
        base_height: Height at the origin/reference point (m)
        slope_percent: Slope in percent (positive = descending in slope direction)
        slope_direction_deg: Direction of slope descent in degrees (0 = east)

    Returns:
        QgsGeometry: 3D PolygonZ with sloped surface
    """
    if geometry.isEmpty():
        return QgsGeometry()

    # Calculate slope direction vector
    slope_rad = math.radians(slope_direction_deg)
    slope_dir_x = math.cos(slope_rad)
    slope_dir_y = math.sin(slope_rad)

    # Get centroid as reference point
    centroid = geometry.centroid().asPoint()

    def calc_z(x: float, y: float) -> float:
        """Calculate Z based on distance along slope direction."""
        # Vector from centroid to point
        dx = x - centroid.x()
        dy = y - centroid.y()

        # Distance along slope direction
        dist_along_slope = dx * slope_dir_x + dy * slope_dir_y

        # Height change (positive slope_percent = descending)
        height_change = dist_along_slope * (slope_percent / 100.0)

        return base_height - height_change

    if geometry.isMultipart():
        multi_polygon = QgsMultiPolygon()
        polygons_2d = geometry.asMultiPolygon()

        for polygon_2d in polygons_2d:
            polygon_3d = QgsPolygon()

            if polygon_2d:
                exterior_points = [
                    QgsPoint(pt.x(), pt.y(), calc_z(pt.x(), pt.y()))
                    for pt in polygon_2d[0]
                ]
                exterior_ring = QgsLineString(exterior_points)
                polygon_3d.setExteriorRing(exterior_ring)

                for i in range(1, len(polygon_2d)):
                    interior_points = [
                        QgsPoint(pt.x(), pt.y(), calc_z(pt.x(), pt.y()))
                        for pt in polygon_2d[i]
                    ]
                    interior_ring = QgsLineString(interior_points)
                    polygon_3d.addInteriorRing(interior_ring)

            multi_polygon.addGeometry(polygon_3d)

        return QgsGeometry(multi_polygon)
    else:
        polygon_2d = geometry.asPolygon()
        if not polygon_2d:
            return QgsGeometry()

        polygon_3d = QgsPolygon()

        exterior_points = [
            QgsPoint(pt.x(), pt.y(), calc_z(pt.x(), pt.y()))
            for pt in polygon_2d[0]
        ]
        exterior_ring = QgsLineString(exterior_points)
        polygon_3d.setExteriorRing(exterior_ring)

        for i in range(1, len(polygon_2d)):
            interior_points = [
                QgsPoint(pt.x(), pt.y(), calc_z(pt.x(), pt.y()))
                for pt in polygon_2d[i]
            ]
            interior_ring = QgsLineString(interior_points)
            polygon_3d.addInteriorRing(interior_ring)

        return QgsGeometry(polygon_3d)


def create_slope_surface_3d(
    inner_polygon: QgsGeometry,
    outer_polygon: QgsGeometry,
    inner_height: float,
    dem_path: str,
    slope_angle_deg: float = 45.0,
    num_segments: int = 8
) -> QgsGeometry:
    """
    Create a 3D slope/embankment surface between inner and outer polygons.

    The inner edge is at inner_height, the outer edge follows terrain.
    Creates a MultiPolygonZ representing the inclined slope faces.

    Args:
        inner_polygon: Inner polygon (platform edge)
        outer_polygon: Outer polygon (embankment toe)
        inner_height: Height at inner edge (platform height)
        dem_path: Path to DEM for terrain heights
        slope_angle_deg: Embankment angle in degrees
        num_segments: Number of segments around polygon for slope faces

    Returns:
        QgsGeometry: MultiPolygonZ of slope faces
    """
    if inner_polygon.isEmpty() or outer_polygon.isEmpty():
        return QgsGeometry()

    # Open DEM
    dem_ds = gdal.Open(dem_path)
    if dem_ds is None:
        raise ValueError(f"Could not open DEM: {dem_path}")

    dem_band = dem_ds.GetRasterBand(1)
    dem_transform = dem_ds.GetGeoTransform()

    def get_dem_z(x: float, y: float) -> float:
        col = int((x - dem_transform[0]) / dem_transform[1])
        row = int((y - dem_transform[3]) / dem_transform[5])
        col = max(0, min(col, dem_ds.RasterXSize - 1))
        row = max(0, min(row, dem_ds.RasterYSize - 1))
        return float(dem_band.ReadAsArray(col, row, 1, 1)[0, 0])

    # Get vertices
    inner_verts = _get_polygon_vertices(inner_polygon)
    outer_verts = _get_polygon_vertices(outer_polygon)

    if not inner_verts or not outer_verts:
        dem_ds = None
        return QgsGeometry()

    # Create slope faces between corresponding vertices
    multi_polygon = QgsMultiPolygon()

    # Sample points along both polygons
    inner_points = _sample_polygon_boundary(inner_polygon, num_segments * len(inner_verts))
    outer_points = _sample_polygon_boundary(outer_polygon, num_segments * len(outer_verts))

    # Match points and create quad faces
    for i in range(len(inner_points) - 1):
        # Find closest outer points
        inner_p1 = inner_points[i]
        inner_p2 = inner_points[i + 1]

        # Find corresponding outer points (simple nearest neighbor)
        outer_p1 = _find_nearest_point(inner_p1, outer_points)
        outer_p2 = _find_nearest_point(inner_p2, outer_points)

        if outer_p1 is None or outer_p2 is None:
            continue

        # Create quad face with Z values
        quad_points = [
            QgsPoint(inner_p1.x(), inner_p1.y(), inner_height),
            QgsPoint(inner_p2.x(), inner_p2.y(), inner_height),
            QgsPoint(outer_p2.x(), outer_p2.y(), get_dem_z(outer_p2.x(), outer_p2.y())),
            QgsPoint(outer_p1.x(), outer_p1.y(), get_dem_z(outer_p1.x(), outer_p1.y())),
            QgsPoint(inner_p1.x(), inner_p1.y(), inner_height)  # Close polygon
        ]

        quad_polygon = QgsPolygon()
        quad_ring = QgsLineString(quad_points)
        quad_polygon.setExteriorRing(quad_ring)
        multi_polygon.addGeometry(quad_polygon)

    dem_ds = None
    return QgsGeometry(multi_polygon)


def create_vertical_profile_polygon(
    line_geometry: QgsGeometry,
    dem_path: str,
    profile_data: dict,
    surface_key: str = 'existing_z'
) -> QgsGeometry:
    """
    Create a vertical PolygonZ from a profile line.

    The polygon represents a vertical cross-section with:
    - Bottom edge: terrain profile from DEM
    - Top edge: specified surface (existing terrain, platform, etc.)

    Args:
        line_geometry: 2D profile line geometry
        dem_path: Path to DEM raster
        profile_data: Dict with 'distances' and elevation arrays
        surface_key: Key in profile_data for top surface ('existing_z', 'crane_top_z', etc.)

    Returns:
        QgsGeometry: PolygonZ representing vertical profile section
    """
    if line_geometry.isEmpty():
        return QgsGeometry()

    # Get line vertices
    if line_geometry.isMultipart():
        lines = line_geometry.asMultiPolyline()
        if not lines:
            return QgsGeometry()
        vertices = lines[0]
    else:
        vertices = line_geometry.asPolyline()

    if len(vertices) < 2:
        return QgsGeometry()

    # Get profile data
    distances = profile_data.get('distances', [])
    top_elevations = profile_data.get(surface_key, profile_data.get('existing_z', []))
    bottom_elevations = profile_data.get('existing_z', [])

    if not distances or not top_elevations:
        return QgsGeometry()

    # Interpolate XY coordinates along line for each distance
    line_length = sum(
        math.sqrt((vertices[i+1].x() - vertices[i].x())**2 +
                  (vertices[i+1].y() - vertices[i].y())**2)
        for i in range(len(vertices) - 1)
    )

    if line_length == 0:
        return QgsGeometry()

    def interpolate_xy(distance: float) -> tuple:
        """Get XY coordinates at distance along line."""
        remaining = distance
        for i in range(len(vertices) - 1):
            seg_length = math.sqrt(
                (vertices[i+1].x() - vertices[i].x())**2 +
                (vertices[i+1].y() - vertices[i].y())**2
            )
            if remaining <= seg_length:
                t = remaining / seg_length if seg_length > 0 else 0
                x = vertices[i].x() + t * (vertices[i+1].x() - vertices[i].x())
                y = vertices[i].y() + t * (vertices[i+1].y() - vertices[i].y())
                return (x, y)
            remaining -= seg_length
        return (vertices[-1].x(), vertices[-1].y())

    # Build polygon points: top edge (forward) + bottom edge (backward)
    polygon_points = []

    # Top edge (forward along profile)
    for i, dist in enumerate(distances):
        x, y = interpolate_xy(dist)
        z = top_elevations[i] if i < len(top_elevations) else top_elevations[-1]
        polygon_points.append(QgsPoint(x, y, z))

    # Bottom edge (backward along profile)
    for i in range(len(distances) - 1, -1, -1):
        x, y = interpolate_xy(distances[i])
        z = bottom_elevations[i] if i < len(bottom_elevations) else bottom_elevations[-1]
        polygon_points.append(QgsPoint(x, y, z))

    # Close polygon
    if polygon_points:
        polygon_points.append(polygon_points[0])

    # Create PolygonZ
    polygon_3d = QgsPolygon()
    ring = QgsLineString(polygon_points)
    polygon_3d.setExteriorRing(ring)

    return QgsGeometry(polygon_3d)


def create_profile_vertical_wall(
    line_geometry: QgsGeometry,
    z_min: float,
    z_max: float,
    num_samples: int = 50
) -> QgsGeometry:
    """
    Create a simple vertical wall polygon along a profile line.

    This creates a constant-height vertical surface along the line,
    useful for showing the extent of a cross-section.

    Args:
        line_geometry: 2D profile line geometry
        z_min: Bottom Z value
        z_max: Top Z value
        num_samples: Number of sample points along line

    Returns:
        QgsGeometry: PolygonZ representing vertical wall
    """
    if line_geometry.isEmpty():
        return QgsGeometry()

    # Get line vertices
    if line_geometry.isMultipart():
        lines = line_geometry.asMultiPolyline()
        if not lines:
            return QgsGeometry()
        vertices = lines[0]
    else:
        vertices = line_geometry.asPolyline()

    if len(vertices) < 2:
        return QgsGeometry()

    # Sample points along line
    points_2d = _sample_line_points(vertices, num_samples)

    # Build polygon: top edge (forward) + bottom edge (backward)
    polygon_points = []

    # Top edge
    for pt in points_2d:
        polygon_points.append(QgsPoint(pt.x(), pt.y(), z_max))

    # Bottom edge (reverse)
    for pt in reversed(points_2d):
        polygon_points.append(QgsPoint(pt.x(), pt.y(), z_min))

    # Close polygon
    polygon_points.append(polygon_points[0])

    # Create PolygonZ
    polygon_3d = QgsPolygon()
    ring = QgsLineString(polygon_points)
    polygon_3d.setExteriorRing(ring)

    return QgsGeometry(polygon_3d)


def line_to_linestringz(
    geometry: QgsGeometry,
    dem_path: str,
    z_offset: float = 0.0
) -> QgsGeometry:
    """
    Convert a 2D line to a 3D LineStringZ with Z from DEM.

    Args:
        geometry: 2D line geometry
        dem_path: Path to DEM raster
        z_offset: Additional Z offset

    Returns:
        QgsGeometry: 3D LineStringZ with terrain heights
    """
    if geometry.isEmpty():
        return QgsGeometry()

    # Open DEM
    dem_ds = gdal.Open(dem_path)
    if dem_ds is None:
        raise ValueError(f"Could not open DEM: {dem_path}")

    dem_band = dem_ds.GetRasterBand(1)
    dem_transform = dem_ds.GetGeoTransform()

    def get_dem_z(x: float, y: float) -> float:
        col = int((x - dem_transform[0]) / dem_transform[1])
        row = int((y - dem_transform[3]) / dem_transform[5])
        col = max(0, min(col, dem_ds.RasterXSize - 1))
        row = max(0, min(row, dem_ds.RasterYSize - 1))
        return float(dem_band.ReadAsArray(col, row, 1, 1)[0, 0]) + z_offset

    # Get vertices
    if geometry.isMultipart():
        lines = geometry.asMultiPolyline()
        if not lines:
            dem_ds = None
            return QgsGeometry()
        vertices = lines[0]
    else:
        vertices = geometry.asPolyline()

    # Create 3D points
    points_3d = [
        QgsPoint(pt.x(), pt.y(), get_dem_z(pt.x(), pt.y()))
        for pt in vertices
    ]

    dem_ds = None
    return QgsGeometry(QgsLineString(points_3d))


def sample_terrain_boundary(
    geometry: QgsGeometry,
    dem_path: str,
    num_samples: int = 100
) -> list[tuple[float, float, float]]:
    """
    Sample terrain heights along polygon boundary.

    Args:
        geometry: 2D polygon geometry
        dem_path: Path to DEM raster
        num_samples: Number of sample points

    Returns:
        List of (x, y, z) tuples along boundary
    """
    if geometry.isEmpty():
        return []

    # Open DEM
    dem_ds = gdal.Open(dem_path)
    if dem_ds is None:
        raise ValueError(f"Could not open DEM: {dem_path}")

    dem_band = dem_ds.GetRasterBand(1)
    dem_transform = dem_ds.GetGeoTransform()

    def get_dem_z(x: float, y: float) -> float:
        col = int((x - dem_transform[0]) / dem_transform[1])
        row = int((y - dem_transform[3]) / dem_transform[5])
        col = max(0, min(col, dem_ds.RasterXSize - 1))
        row = max(0, min(row, dem_ds.RasterYSize - 1))
        return float(dem_band.ReadAsArray(col, row, 1, 1)[0, 0])

    # Sample boundary points
    boundary_points = _sample_polygon_boundary(geometry, num_samples)

    # Get Z for each point
    result = [
        (pt.x(), pt.y(), get_dem_z(pt.x(), pt.y()))
        for pt in boundary_points
    ]

    dem_ds = None
    return result


# =============================================================================
# Helper Functions
# =============================================================================

def _get_polygon_vertices(geometry: QgsGeometry) -> list[QgsPointXY]:
    """Extract vertices from a polygon geometry."""
    if geometry.isMultipart():
        polygons = geometry.asMultiPolygon()
        if polygons and polygons[0]:
            return polygons[0][0]
        return []
    else:
        polygon = geometry.asPolygon()
        if polygon and polygon[0]:
            return polygon[0]
        return []


def _sample_polygon_boundary(geometry: QgsGeometry, num_samples: int) -> list[QgsPointXY]:
    """Sample evenly spaced points along polygon boundary."""
    vertices = _get_polygon_vertices(geometry)
    if not vertices:
        return []

    # Calculate total perimeter
    perimeter = 0.0
    for i in range(len(vertices) - 1):
        perimeter += math.sqrt(
            (vertices[i+1].x() - vertices[i].x())**2 +
            (vertices[i+1].y() - vertices[i].y())**2
        )

    if perimeter == 0:
        return []

    # Sample at regular intervals
    step = perimeter / num_samples
    samples = []

    current_dist = 0.0
    seg_start = 0
    remaining_in_seg = 0.0

    for i in range(num_samples):
        target_dist = i * step

        # Find which segment contains target_dist
        cumulative = 0.0
        for j in range(len(vertices) - 1):
            seg_len = math.sqrt(
                (vertices[j+1].x() - vertices[j].x())**2 +
                (vertices[j+1].y() - vertices[j].y())**2
            )
            if cumulative + seg_len >= target_dist:
                # Interpolate within this segment
                t = (target_dist - cumulative) / seg_len if seg_len > 0 else 0
                x = vertices[j].x() + t * (vertices[j+1].x() - vertices[j].x())
                y = vertices[j].y() + t * (vertices[j+1].y() - vertices[j].y())
                samples.append(QgsPointXY(x, y))
                break
            cumulative += seg_len

    return samples


def _sample_line_points(vertices: list[QgsPointXY], num_samples: int) -> list[QgsPointXY]:
    """Sample evenly spaced points along a line."""
    if len(vertices) < 2:
        return vertices

    # Calculate total length
    length = 0.0
    for i in range(len(vertices) - 1):
        length += math.sqrt(
            (vertices[i+1].x() - vertices[i].x())**2 +
            (vertices[i+1].y() - vertices[i].y())**2
        )

    if length == 0:
        return [vertices[0]]

    # Sample at regular intervals
    step = length / (num_samples - 1) if num_samples > 1 else length
    samples = []

    for i in range(num_samples):
        target_dist = i * step

        # Find point at target_dist
        cumulative = 0.0
        for j in range(len(vertices) - 1):
            seg_len = math.sqrt(
                (vertices[j+1].x() - vertices[j].x())**2 +
                (vertices[j+1].y() - vertices[j].y())**2
            )
            if cumulative + seg_len >= target_dist or j == len(vertices) - 2:
                t = (target_dist - cumulative) / seg_len if seg_len > 0 else 0
                t = min(1.0, max(0.0, t))
                x = vertices[j].x() + t * (vertices[j+1].x() - vertices[j].x())
                y = vertices[j].y() + t * (vertices[j+1].y() - vertices[j].y())
                samples.append(QgsPointXY(x, y))
                break
            cumulative += seg_len

    return samples


def _find_nearest_point(target: QgsPointXY, candidates: list[QgsPointXY]) -> Optional[QgsPointXY]:
    """Find the nearest point from a list of candidates."""
    if not candidates:
        return None

    min_dist = float('inf')
    nearest = None

    for pt in candidates:
        dist = math.sqrt((pt.x() - target.x())**2 + (pt.y() - target.y())**2)
        if dist < min_dist:
            min_dist = dist
            nearest = pt

    return nearest


def get_geometry_z_range(geometry: QgsGeometry) -> tuple[float, float]:
    """
    Get the Z range (min, max) of a 3D geometry.

    Args:
        geometry: 3D geometry (PolygonZ, LineStringZ, etc.)

    Returns:
        Tuple of (z_min, z_max)
    """
    if geometry.isEmpty():
        return (0.0, 0.0)

    abstract_geom = geometry.constGet()
    if abstract_geom is None:
        return (0.0, 0.0)

    # Collect all Z values
    z_values = []

    for i in range(abstract_geom.vertexCount()):
        vertex = abstract_geom.vertexAt(i)
        if hasattr(vertex, 'z'):
            z_values.append(vertex.z())

    if not z_values:
        return (0.0, 0.0)

    return (min(z_values), max(z_values))
