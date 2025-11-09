"""
Geometry utility functions for Wind Turbine Earthwork Calculator V2

Provides helper functions for geometric operations.
"""

import math
from qgis.core import (
    QgsGeometry,
    QgsPointXY,
    QgsRectangle,
    QgsWkbTypes
)


def point_distance(p1, p2):
    """
    Calculate Euclidean distance between two points.

    Args:
        p1 (tuple): First point (x, y)
        p2 (tuple): Second point (x, y)

    Returns:
        float: Distance in meters
    """
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)


def find_nearest_point(target, candidates, max_distance=None):
    """
    Find the nearest point from a list of candidates.

    Args:
        target (tuple): Target point (x, y)
        candidates (list): List of candidate points [(x, y), ...]
        max_distance (float): Maximum allowed distance (optional)

    Returns:
        tuple: (nearest_point, distance, index) or (None, None, None) if no match
    """
    if not candidates:
        return None, None, None

    min_dist = float('inf')
    nearest_point = None
    nearest_index = None

    for i, candidate in enumerate(candidates):
        dist = point_distance(target, candidate)
        if dist < min_dist:
            min_dist = dist
            nearest_point = candidate
            nearest_index = i

    if max_distance is not None and min_dist > max_distance:
        return None, None, None

    return nearest_point, min_dist, nearest_index


def buffer_geometry(geometry, distance):
    """
    Create a buffer around a geometry.

    Args:
        geometry (QgsGeometry): Input geometry
        distance (float): Buffer distance in meters

    Returns:
        QgsGeometry: Buffered geometry
    """
    return geometry.buffer(distance, 8)  # 8 segments per quarter circle


def get_centroid(geometry):
    """
    Get the centroid of a geometry.

    Args:
        geometry (QgsGeometry): Input geometry

    Returns:
        QgsPointXY: Centroid point
    """
    return geometry.centroid().asPoint()


def create_bbox_with_buffer(geometry, buffer_distance):
    """
    Create a bounding box around a geometry with buffer.

    Args:
        geometry (QgsGeometry): Input geometry
        buffer_distance (float): Buffer distance in meters

    Returns:
        QgsRectangle: Bounding box
    """
    bbox = geometry.boundingBox()
    return QgsRectangle(
        bbox.xMinimum() - buffer_distance,
        bbox.yMinimum() - buffer_distance,
        bbox.xMaximum() + buffer_distance,
        bbox.yMaximum() + buffer_distance
    )


def validate_polygon_topology(geometry):
    """
    Validate polygon topology.

    Args:
        geometry (QgsGeometry): Polygon geometry to validate

    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if geometry.isEmpty():
        return False, "Geometry is empty"

    if not geometry.isGeosValid():
        error = geometry.validateGeometry()
        if error:
            # what() is a property/string, not a method
            error_msg = error[0].what if hasattr(error[0], 'what') else str(error[0])
            return False, f"Invalid geometry: {error_msg}"
        return False, "Invalid geometry (unknown error)"

    if geometry.type() != QgsWkbTypes.PolygonGeometry:
        return False, f"Wrong geometry type: {geometry.type()}, expected Polygon"

    area = geometry.area()
    if area <= 0:
        return False, f"Invalid area: {area}"

    # Check for minimum vertices
    if geometry.isMultipart():
        parts = geometry.asMultiPolygon()
        if not parts:
            return False, "Empty multipolygon"
        vertices = len(parts[0][0])  # First ring of first polygon
    else:
        polygon = geometry.asPolygon()
        if not polygon or not polygon[0]:
            return False, "Empty polygon"
        vertices = len(polygon[0])

    if vertices < 4:  # Minimum 3 vertices + closing vertex
        return False, f"Too few vertices: {vertices}, minimum is 4 (including closing vertex)"

    return True, "Valid polygon"


def create_radial_lines(center, radius, num_lines=8, angle_offset=0):
    """
    Create radial lines from a center point.

    Args:
        center (QgsPointXY): Center point
        radius (float): Line length in meters
        num_lines (int): Number of radial lines
        angle_offset (float): Starting angle in degrees

    Returns:
        list: List of QgsGeometry line objects
    """
    lines = []
    angle_step = 360.0 / num_lines

    for i in range(num_lines):
        angle = math.radians(angle_offset + i * angle_step)

        # Calculate end point
        end_x = center.x() + radius * math.cos(angle)
        end_y = center.y() + radius * math.sin(angle)
        end_point = QgsPointXY(end_x, end_y)

        # Create line geometry
        line = QgsGeometry.fromPolylineXY([center, end_point])
        lines.append(line)

    return lines


def get_polygon_radius(geometry):
    """
    Get approximate radius of a polygon (distance from centroid to furthest vertex).

    Args:
        geometry (QgsGeometry): Polygon geometry

    Returns:
        float: Approximate radius in meters
    """
    centroid = get_centroid(geometry)

    if geometry.isMultipart():
        polygons = geometry.asMultiPolygon()
        vertices = polygons[0][0] if polygons else []
    else:
        polygon = geometry.asPolygon()
        vertices = polygon[0] if polygon else []

    max_distance = 0
    for vertex in vertices:
        point = QgsPointXY(vertex[0], vertex[1])
        distance = math.sqrt(
            (point.x() - centroid.x())**2 +
            (point.y() - centroid.y())**2
        )
        max_distance = max(max_distance, distance)

    return max_distance


def coords_to_qgs_point(coords):
    """
    Convert coordinate tuple to QgsPointXY.

    Args:
        coords (tuple): Coordinates (x, y)

    Returns:
        QgsPointXY: QGIS point object
    """
    return QgsPointXY(coords[0], coords[1])


def get_polygon_orientation(geometry):
    """
    Calculate the main orientation/direction of a polygon using the longest edge.

    This method finds the longest edge of the polygon and uses its direction
    as the main orientation.

    Args:
        geometry (QgsGeometry): Polygon geometry

    Returns:
        float: Orientation angle in degrees (0-180), measured counter-clockwise from east
    """
    # Extract vertices
    if geometry.isMultipart():
        polygons = geometry.asMultiPolygon()
        vertices = polygons[0][0] if polygons else []
    else:
        polygon = geometry.asPolygon()
        vertices = polygon[0] if polygon else []

    if len(vertices) < 3:
        return 0.0

    # Find the longest edge
    max_length = 0
    longest_edge_angle = 0.0

    for i in range(len(vertices) - 1):
        p1 = vertices[i]
        p2 = vertices[i + 1]

        # Calculate edge length
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.sqrt(dx * dx + dy * dy)

        if length > max_length:
            max_length = length
            # Calculate angle of this edge
            angle_rad = math.atan2(dy, dx)
            angle_deg = math.degrees(angle_rad)

            # Normalize to 0-180 range (we don't care about direction, just orientation)
            if angle_deg < 0:
                angle_deg += 180
            elif angle_deg > 180:
                angle_deg -= 180

            longest_edge_angle = angle_deg

    return float(longest_edge_angle)


def get_polygon_width_at_point(geometry, point, direction_angle):
    """
    Get the width of a polygon at a specific point along a given direction.

    This creates a line perpendicular to the direction through the point and
    calculates where it intersects the polygon boundary.

    Args:
        geometry (QgsGeometry): Polygon geometry
        point (QgsPointXY): Point on or near the polygon
        direction_angle (float): Direction angle in degrees

    Returns:
        float: Width of polygon perpendicular to the direction, or 0 if no intersection
    """
    # Create a long line perpendicular to the main direction through the point
    # Perpendicular angle is main_angle + 90 degrees
    perp_angle = direction_angle + 90.0
    perp_rad = math.radians(perp_angle)

    # Make the line very long to ensure it crosses the polygon
    half_length = 1000  # meters

    x1 = point.x() - half_length * math.cos(perp_rad)
    y1 = point.y() - half_length * math.sin(perp_rad)
    x2 = point.x() + half_length * math.cos(perp_rad)
    y2 = point.y() + half_length * math.sin(perp_rad)

    test_line = QgsGeometry.fromPolylineXY([QgsPointXY(x1, y1), QgsPointXY(x2, y2)])

    # Find intersection with polygon boundary
    # Convert polygon to line string (boundary)
    if geometry.isMultipart():
        polygons = geometry.asMultiPolygon()
        if polygons and polygons[0]:
            boundary_coords = polygons[0][0]  # Exterior ring
        else:
            return 0.0
    else:
        polygon = geometry.asPolygon()
        if polygon and polygon[0]:
            boundary_coords = polygon[0]  # Exterior ring
        else:
            return 0.0

    # Create boundary as LineString
    boundary = QgsGeometry.fromPolylineXY(boundary_coords)

    if boundary.intersects(test_line):
        intersection = boundary.intersection(test_line)

        # The intersection might be multipoint
        if intersection.type() == QgsWkbTypes.PointGeometry:
            if intersection.isMultipart():
                points = intersection.asMultiPoint()
            else:
                points = [intersection.asPoint()]

            if len(points) >= 2:
                # Calculate distance between furthest points
                max_dist = 0
                for i in range(len(points)):
                    for j in range(i + 1, len(points)):
                        p1 = points[i]
                        p2 = points[j]
                        dist = math.sqrt((p2.x() - p1.x())**2 + (p2.y() - p1.y())**2)
                        max_dist = max(max_dist, dist)
                return max_dist

    return 0.0


def create_perpendicular_cross_sections(geometry, spacing=10.0, overhang_percent=10.0):
    """
    Create perpendicular cross-section lines through a polygon.

    The cross-sections are perpendicular to the main orientation of the polygon,
    spaced at regular intervals, and extend beyond the polygon edges.

    Args:
        geometry (QgsGeometry): Polygon geometry
        spacing (float): Distance between cross-sections in meters (default: 10m)
        overhang_percent (float): Percentage to extend beyond polygon on each side (default: 10%)

    Returns:
        list: List of dictionaries with:
            - 'geometry': QgsGeometry line object
            - 'type': Profile type identifier
            - 'main_angle': Main orientation angle
            - 'cross_angle': Cross-section angle (perpendicular to main)
            - 'center_point': Center point of the cross-section
            - 'length': Total length of the line
            - 'width': Width of polygon at this location
    """
    import numpy as np

    # Get main orientation of polygon
    main_angle = get_polygon_orientation(geometry)

    # Cross-sections are perpendicular to main orientation
    cross_angle = main_angle + 90.0
    cross_rad = math.radians(cross_angle)

    # Get the oriented bounding box by rotating the polygon
    # We'll work along the main axis
    centroid = get_centroid(geometry)

    # Get polygon bounds
    bbox = geometry.boundingBox()

    # Calculate extent along main direction
    # For this, we need to project all vertices onto the main axis
    if geometry.isMultipart():
        polygons = geometry.asMultiPolygon()
        vertices = polygons[0][0] if polygons else []
    else:
        polygon = geometry.asPolygon()
        vertices = polygon[0] if polygon else []

    main_rad = math.radians(main_angle)
    main_axis_x = math.cos(main_rad)
    main_axis_y = math.sin(main_rad)

    # Project all vertices onto main axis
    projections = []
    for v in vertices:
        # Vector from centroid to vertex
        dx = v.x() - centroid.x()
        dy = v.y() - centroid.y()
        # Dot product with main axis direction
        projection = dx * main_axis_x + dy * main_axis_y
        projections.append(projection)

    min_proj = min(projections)
    max_proj = max(projections)
    extent_along_main = max_proj - min_proj

    # Calculate number of cross-sections
    num_sections = max(1, int(extent_along_main / spacing) + 1)

    cross_sections = []

    # Extract polygon boundary
    if geometry.isMultipart():
        polygons = geometry.asMultiPolygon()
        if polygons and polygons[0]:
            boundary_coords = polygons[0][0]  # Exterior ring
        else:
            return []
    else:
        poly = geometry.asPolygon()
        if poly and poly[0]:
            boundary_coords = poly[0]  # Exterior ring
        else:
            return []

    boundary = QgsGeometry.fromPolylineXY(boundary_coords)

    # Create cross-sections at regular intervals
    for i in range(num_sections):
        # Position along main axis
        t = min_proj + i * spacing

        # Calculate center point of this cross-section along main axis
        center_x = centroid.x() + t * main_axis_x
        center_y = centroid.y() + t * main_axis_y
        test_center = QgsPointXY(center_x, center_y)

        # Create a very long test line perpendicular to main axis through this point
        test_half_length = 2000  # Very long to ensure we cross the polygon
        test_x1 = center_x - test_half_length * math.cos(cross_rad)
        test_y1 = center_y - test_half_length * math.sin(cross_rad)
        test_x2 = center_x + test_half_length * math.cos(cross_rad)
        test_y2 = center_y + test_half_length * math.sin(cross_rad)

        test_line = QgsGeometry.fromPolylineXY([
            QgsPointXY(test_x1, test_y1),
            QgsPointXY(test_x2, test_y2)
        ])

        # Find intersection points with polygon boundary
        if boundary.intersects(test_line):
            intersection = boundary.intersection(test_line)

            # Get intersection points
            intersection_points = []
            if intersection.type() == QgsWkbTypes.PointGeometry:
                if intersection.isMultipart():
                    intersection_points = intersection.asMultiPoint()
                else:
                    intersection_points = [intersection.asPoint()]

            # We need at least 2 intersection points
            if len(intersection_points) >= 2:
                # Find the two furthest intersection points (entry and exit of polygon)
                max_dist = 0
                point1 = None
                point2 = None

                for j in range(len(intersection_points)):
                    for k in range(j + 1, len(intersection_points)):
                        p1 = intersection_points[j]
                        p2 = intersection_points[k]
                        dist = math.sqrt((p2.x() - p1.x())**2 + (p2.y() - p1.y())**2)
                        if dist > max_dist:
                            max_dist = dist
                            point1 = p1
                            point2 = p2

                if point1 and point2 and max_dist > 0:
                    # This is the actual width of the polygon at this location
                    width = max_dist

                    # Calculate the midpoint between the two intersection points
                    # This is the true center of the cross-section
                    mid_x = (point1.x() + point2.x()) / 2.0
                    mid_y = (point1.y() + point2.y()) / 2.0
                    true_center = QgsPointXY(mid_x, mid_y)

                    # Calculate overhang distance
                    overhang = width * (overhang_percent / 100.0)
                    half_length = (width / 2.0) + overhang
                    total_length = width + 2 * overhang

                    # Create final cross-section line from true center
                    x1 = mid_x - half_length * math.cos(cross_rad)
                    y1 = mid_y - half_length * math.sin(cross_rad)
                    x2 = mid_x + half_length * math.cos(cross_rad)
                    y2 = mid_y + half_length * math.sin(cross_rad)

                    line_geom = QgsGeometry.fromPolylineXY([
                        QgsPointXY(x1, y1),
                        QgsPointXY(x2, y2)
                    ])

                    # Verify that endpoints are outside the polygon
                    p1_geom = QgsGeometry.fromPointXY(QgsPointXY(x1, y1))
                    p2_geom = QgsGeometry.fromPointXY(QgsPointXY(x2, y2))

                    # If endpoints are still inside, extend them further
                    safety_factor = 1.5
                    while geometry.contains(p1_geom) or geometry.contains(p2_geom):
                        half_length *= safety_factor
                        total_length = width + 2 * (half_length - width / 2.0)

                        x1 = mid_x - half_length * math.cos(cross_rad)
                        y1 = mid_y - half_length * math.sin(cross_rad)
                        x2 = mid_x + half_length * math.cos(cross_rad)
                        y2 = mid_y + half_length * math.sin(cross_rad)

                        line_geom = QgsGeometry.fromPolylineXY([
                            QgsPointXY(x1, y1),
                            QgsPointXY(x2, y2)
                        ])

                        p1_geom = QgsGeometry.fromPointXY(QgsPointXY(x1, y1))
                        p2_geom = QgsGeometry.fromPointXY(QgsPointXY(x2, y2))

                        # Safety break to avoid infinite loop
                        if half_length > width * 10:
                            break

                    cross_section = {
                        'geometry': line_geom,
                        'type': f'Schnitt {i+1:02d}',
                        'main_angle': main_angle,
                        'cross_angle': cross_angle,
                        'center_point': true_center,
                        'length': total_length,
                        'width': width
                    }

                    cross_sections.append(cross_section)

    return cross_sections
