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


def create_oriented_bounding_box(geometries, main_angle, buffer_percent=10.0):
    """
    Create an oriented bounding box around multiple geometries aligned with a main axis.

    The bounding box is aligned with the main_angle (typically the longest edge of the
    crane pad) and encompasses all provided geometries plus a buffer zone.

    Args:
        geometries (list): List of QgsGeometry objects to encompass
        main_angle (float): Main orientation angle in degrees (0-180)
        buffer_percent (float): Buffer as percentage of bounding box size (default: 10%)

    Returns:
        dict: Dictionary containing:
            - 'bbox_polygon': QgsGeometry polygon of the oriented bounding box
            - 'center': QgsPointXY center point
            - 'width': Width perpendicular to main axis (in meters)
            - 'length': Length along main axis (in meters)
            - 'main_angle': Main orientation angle
    """
    if not geometries:
        return None

    # Combine all geometries to get overall extent
    combined = QgsGeometry.unaryUnion(geometries)
    centroid = get_centroid(combined)

    # Convert angle to radians
    main_rad = math.radians(main_angle)
    main_axis_x = math.cos(main_rad)
    main_axis_y = math.sin(main_rad)

    # Perpendicular axis
    perp_rad = math.radians(main_angle + 90.0)
    perp_axis_x = math.cos(perp_rad)
    perp_axis_y = math.sin(perp_rad)

    # Collect all vertices from all geometries
    all_vertices = []
    for geom in geometries:
        vertices = get_polygon_vertices(geom)
        all_vertices.extend(vertices)

    if not all_vertices:
        return None

    # Project all vertices onto main and perpendicular axes
    main_projections = []
    perp_projections = []

    for v in all_vertices:
        dx = v.x() - centroid.x()
        dy = v.y() - centroid.y()

        # Project onto main axis
        main_proj = dx * main_axis_x + dy * main_axis_y
        main_projections.append(main_proj)

        # Project onto perpendicular axis
        perp_proj = dx * perp_axis_x + dy * perp_axis_y
        perp_projections.append(perp_proj)

    # Get min/max projections (these define the oriented bounding box)
    min_main = min(main_projections)
    max_main = max(main_projections)
    min_perp = min(perp_projections)
    max_perp = max(perp_projections)

    # Calculate dimensions
    length_along_main = max_main - min_main
    width_along_perp = max_perp - min_perp

    # Apply buffer
    buffer_length = length_along_main * (buffer_percent / 100.0)
    buffer_width = width_along_perp * (buffer_percent / 100.0)

    min_main -= buffer_length
    max_main += buffer_length
    min_perp -= buffer_width
    max_perp += buffer_width

    # Recalculate dimensions with buffer
    length_with_buffer = max_main - min_main
    width_with_buffer = max_perp - min_perp

    # Create the four corners of the oriented bounding box
    # Corner order: bottom-left, bottom-right, top-right, top-left (counter-clockwise)
    corners = []
    for main_offset, perp_offset in [(min_main, min_perp), (max_main, min_perp),
                                      (max_main, max_perp), (min_main, max_perp)]:
        x = centroid.x() + main_offset * main_axis_x + perp_offset * perp_axis_x
        y = centroid.y() + main_offset * main_axis_y + perp_offset * perp_axis_y
        corners.append(QgsPointXY(x, y))

    # Close the polygon
    corners.append(corners[0])

    # Create polygon geometry
    bbox_polygon = QgsGeometry.fromPolygonXY([corners])

    return {
        'bbox_polygon': bbox_polygon,
        'center': centroid,
        'width': width_with_buffer,
        'length': length_with_buffer,
        'main_angle': main_angle,
        'min_main': min_main,
        'max_main': max_main,
        'min_perp': min_perp,
        'max_perp': max_perp
    }


def create_perpendicular_cross_sections(geometry, spacing=10.0, overhang_percent=10.0):
    """
    Create perpendicular cross-section lines through a polygon.

    The cross-sections are perpendicular to the main orientation of the polygon,
    spaced at regular intervals, and ALL have the same length based on the
    maximum width of the polygon plus overhang.

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
            - 'length': Total length of the line (uniform for all)
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

    # PHASE 1: Determine maximum width across all cross-sections
    section_info = []  # Store center points and widths
    max_width = 0

    for i in range(num_sections):
        # Position along main axis
        t = min_proj + i * spacing

        # Calculate center point of this cross-section along main axis
        center_x = centroid.x() + t * main_axis_x
        center_y = centroid.y() + t * main_axis_y

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

                    # Track maximum width
                    max_width = max(max_width, width)

                    # Calculate the midpoint between the two intersection points
                    mid_x = (point1.x() + point2.x()) / 2.0
                    mid_y = (point1.y() + point2.y()) / 2.0
                    true_center = QgsPointXY(mid_x, mid_y)

                    # Store info for phase 2
                    section_info.append({
                        'index': i,
                        'center': true_center,
                        'width': width
                    })

    # Calculate unified length based on maximum width
    overhang = max_width * (overhang_percent / 100.0)
    unified_half_length = (max_width / 2.0) + overhang
    unified_total_length = max_width + 2 * overhang

    # PHASE 2: Create all cross-sections with unified length
    cross_sections = []

    for info in section_info:
        i = info['index']
        true_center = info['center']
        width = info['width']

        # Create cross-section line with unified length from center
        x1 = true_center.x() - unified_half_length * math.cos(cross_rad)
        y1 = true_center.y() - unified_half_length * math.sin(cross_rad)
        x2 = true_center.x() + unified_half_length * math.cos(cross_rad)
        y2 = true_center.y() + unified_half_length * math.sin(cross_rad)

        line_geom = QgsGeometry.fromPolylineXY([
            QgsPointXY(x1, y1),
            QgsPointXY(x2, y2)
        ])

        cross_section = {
            'geometry': line_geom,
            'type': f'Querschnitt {i+1:02d}',
            'main_angle': main_angle,
            'cross_angle': cross_angle,
            'center_point': true_center,
            'length': unified_total_length,
            'width': width  # Individual width for reference
        }

        cross_sections.append(cross_section)

    return cross_sections


def create_cross_sections_over_bbox(bbox_info, spacing=10.0):
    """
    Create perpendicular cross-section lines across an oriented bounding box.

    Cross-sections are perpendicular to the main axis and extend across the
    entire width of the bounding box.

    Args:
        bbox_info (dict): Bounding box info from create_oriented_bounding_box()
        spacing (float): Distance between cross-sections in meters (default: 10m)

    Returns:
        list: List of dictionaries with:
            - 'geometry': QgsGeometry line object
            - 'type': Profile type identifier
            - 'main_angle': Main orientation angle
            - 'cross_angle': Cross-section angle (perpendicular to main)
            - 'center_point': Center point of the cross-section
            - 'length': Total length of the line
    """
    if not bbox_info:
        return []

    main_angle = bbox_info['main_angle']
    center = bbox_info['center']
    min_main = bbox_info['min_main']
    max_main = bbox_info['max_main']
    min_perp = bbox_info['min_perp']
    max_perp = bbox_info['max_perp']
    width = bbox_info['width']

    # Cross-sections are perpendicular to main orientation
    cross_angle = main_angle + 90.0
    cross_rad = math.radians(cross_angle)

    # Axes
    main_rad = math.radians(main_angle)
    main_axis_x = math.cos(main_rad)
    main_axis_y = math.sin(main_rad)

    perp_axis_x = math.cos(cross_rad)
    perp_axis_y = math.sin(cross_rad)

    # Calculate number of cross-sections along main axis
    extent_along_main = max_main - min_main
    num_sections = max(1, int(extent_along_main / spacing) + 1)

    cross_sections = []

    for i in range(num_sections):
        # Position along main axis
        t = min_main + i * spacing

        # Don't exceed bbox
        if t > max_main:
            break

        # Calculate center point of this cross-section
        center_x = center.x() + t * main_axis_x
        center_y = center.y() + t * main_axis_y
        section_center = QgsPointXY(center_x, center_y)

        # Create cross-section line spanning full width of bbox
        x1 = center_x + min_perp * perp_axis_x
        y1 = center_y + min_perp * perp_axis_y
        x2 = center_x + max_perp * perp_axis_x
        y2 = center_y + max_perp * perp_axis_y

        line_geom = QgsGeometry.fromPolylineXY([
            QgsPointXY(x1, y1),
            QgsPointXY(x2, y2)
        ])

        cross_section = {
            'geometry': line_geom,
            'type': f'Querschnitt {i+1:02d}',
            'main_angle': main_angle,
            'cross_angle': cross_angle,
            'center_point': section_center,
            'length': width
        }

        cross_sections.append(cross_section)

    return cross_sections


def create_longitudinal_sections_over_bbox(bbox_info, spacing=10.0):
    """
    Create longitudinal section lines across an oriented bounding box.

    Longitudinal sections are parallel to the main axis and extend across the
    entire length of the bounding box.

    Args:
        bbox_info (dict): Bounding box info from create_oriented_bounding_box()
        spacing (float): Distance between longitudinal sections in meters (default: 10m)

    Returns:
        list: List of dictionaries with:
            - 'geometry': QgsGeometry line object
            - 'type': Profile type identifier
            - 'main_angle': Main orientation angle
            - 'longitudinal_angle': Longitudinal section angle (parallel to main)
            - 'center_point': Center point of the longitudinal section
            - 'length': Total length of the line
    """
    if not bbox_info:
        return []

    main_angle = bbox_info['main_angle']
    center = bbox_info['center']
    min_main = bbox_info['min_main']
    max_main = bbox_info['max_main']
    min_perp = bbox_info['min_perp']
    max_perp = bbox_info['max_perp']
    length = bbox_info['length']

    # Longitudinal sections are parallel to main orientation
    longitudinal_angle = main_angle
    longitudinal_rad = math.radians(longitudinal_angle)

    # Perpendicular axis for spacing
    perp_angle = main_angle + 90.0
    perp_rad = math.radians(perp_angle)

    # Axes
    main_axis_x = math.cos(longitudinal_rad)
    main_axis_y = math.sin(longitudinal_rad)

    perp_axis_x = math.cos(perp_rad)
    perp_axis_y = math.sin(perp_rad)

    # Calculate number of longitudinal sections along perpendicular axis
    extent_along_perp = max_perp - min_perp
    num_sections = max(1, int(extent_along_perp / spacing) + 1)

    longitudinal_sections = []

    for i in range(num_sections):
        # Position along perpendicular axis
        t = min_perp + i * spacing

        # Don't exceed bbox
        if t > max_perp:
            break

        # Calculate center point of this longitudinal section
        center_x = center.x() + t * perp_axis_x
        center_y = center.y() + t * perp_axis_y
        section_center = QgsPointXY(center_x, center_y)

        # Create longitudinal section line spanning full length of bbox
        x1 = center_x + min_main * main_axis_x
        y1 = center_y + min_main * main_axis_y
        x2 = center_x + max_main * main_axis_x
        y2 = center_y + max_main * main_axis_y

        line_geom = QgsGeometry.fromPolylineXY([
            QgsPointXY(x1, y1),
            QgsPointXY(x2, y2)
        ])

        longitudinal_section = {
            'geometry': line_geom,
            'type': f'Längsprofil {i+1:02d}',
            'main_angle': main_angle,
            'longitudinal_angle': longitudinal_angle,
            'center_point': section_center,
            'length': length
        }

        longitudinal_sections.append(longitudinal_section)

    return longitudinal_sections


def create_parallel_longitudinal_sections(geometry, spacing=10.0, overhang_percent=10.0):
    """
    Create longitudinal section lines through a polygon, parallel to main orientation.

    The longitudinal sections are parallel to the main orientation of the polygon,
    spaced at regular intervals perpendicular to the main axis, and ALL have the
    same length based on the maximum length of the polygon plus overhang.

    Args:
        geometry (QgsGeometry): Polygon geometry
        spacing (float): Distance between longitudinal sections in meters (default: 10m)
        overhang_percent (float): Percentage to extend beyond polygon on each side (default: 10%)

    Returns:
        list: List of dictionaries with:
            - 'geometry': QgsGeometry line object
            - 'type': Profile type identifier
            - 'main_angle': Main orientation angle
            - 'longitudinal_angle': Longitudinal section angle (parallel to main)
            - 'center_point': Center point of the longitudinal section
            - 'length': Total length of the line (uniform for all)
            - 'width': Length of polygon at this location
    """
    import numpy as np

    # Get main orientation of polygon
    main_angle = get_polygon_orientation(geometry)

    # Longitudinal sections are parallel to main orientation
    longitudinal_angle = main_angle
    longitudinal_rad = math.radians(longitudinal_angle)

    # Position sections along perpendicular axis
    perp_angle = main_angle + 90.0
    perp_rad = math.radians(perp_angle)

    # Get polygon centroid
    centroid = get_centroid(geometry)

    # Get polygon bounds
    bbox = geometry.boundingBox()

    # Calculate extent along perpendicular direction
    # Project all vertices onto perpendicular axis
    if geometry.isMultipart():
        polygons = geometry.asMultiPolygon()
        vertices = polygons[0][0] if polygons else []
    else:
        polygon = geometry.asPolygon()
        vertices = polygon[0] if polygon else []

    perp_axis_x = math.cos(perp_rad)
    perp_axis_y = math.sin(perp_rad)

    # Project all vertices onto perpendicular axis
    projections = []
    for v in vertices:
        # Vector from centroid to vertex
        dx = v.x() - centroid.x()
        dy = v.y() - centroid.y()
        # Dot product with perpendicular axis direction
        projection = dx * perp_axis_x + dy * perp_axis_y
        projections.append(projection)

    min_proj = min(projections)
    max_proj = max(projections)
    extent_along_perp = max_proj - min_proj

    # Calculate number of longitudinal sections
    num_sections = max(1, int(extent_along_perp / spacing) + 1)

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

    # PHASE 1: Determine maximum length across all longitudinal sections
    section_info = []  # Store center points and lengths
    max_length = 0

    for i in range(num_sections):
        # Position along perpendicular axis
        t = min_proj + i * spacing

        # Calculate center point of this longitudinal section along perp axis
        center_x = centroid.x() + t * perp_axis_x
        center_y = centroid.y() + t * perp_axis_y

        # Create a very long test line parallel to main axis through this point
        test_half_length = 2000  # Very long to ensure we cross the polygon
        test_x1 = center_x - test_half_length * math.cos(longitudinal_rad)
        test_y1 = center_y - test_half_length * math.sin(longitudinal_rad)
        test_x2 = center_x + test_half_length * math.cos(longitudinal_rad)
        test_y2 = center_y + test_half_length * math.sin(longitudinal_rad)

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
                    # This is the actual length of the polygon at this location
                    length_at_section = max_dist

                    # Track maximum length
                    max_length = max(max_length, length_at_section)

                    # Calculate the midpoint between the two intersection points
                    mid_x = (point1.x() + point2.x()) / 2.0
                    mid_y = (point1.y() + point2.y()) / 2.0
                    true_center = QgsPointXY(mid_x, mid_y)

                    # Store info for phase 2
                    section_info.append({
                        'index': i,
                        'center': true_center,
                        'length': length_at_section
                    })

    # Calculate unified length based on maximum length
    overhang = max_length * (overhang_percent / 100.0)
    unified_half_length = (max_length / 2.0) + overhang
    unified_total_length = max_length + 2 * overhang

    # PHASE 2: Create all longitudinal sections with unified length
    longitudinal_sections = []

    for info in section_info:
        i = info['index']
        true_center = info['center']
        length_at_section = info['length']

        # Create longitudinal section line with unified length from center
        x1 = true_center.x() - unified_half_length * math.cos(longitudinal_rad)
        y1 = true_center.y() - unified_half_length * math.sin(longitudinal_rad)
        x2 = true_center.x() + unified_half_length * math.cos(longitudinal_rad)
        y2 = true_center.y() + unified_half_length * math.sin(longitudinal_rad)

        line_geom = QgsGeometry.fromPolylineXY([
            QgsPointXY(x1, y1),
            QgsPointXY(x2, y2)
        ])

        longitudinal_section = {
            'geometry': line_geom,
            'type': f'Längsprofil {i+1:02d}',
            'main_angle': main_angle,
            'longitudinal_angle': longitudinal_angle,
            'center_point': true_center,
            'length': unified_total_length,
            'width': length_at_section  # Individual length for reference
        }

        longitudinal_sections.append(longitudinal_section)

    return longitudinal_sections


# ==============================================================================
# Multi-Surface Helper Functions
# ==============================================================================

def get_polygon_boundary(geom: QgsGeometry) -> QgsGeometry:
    """
    Extract the boundary (exterior ring) of a polygon geometry.

    QgsGeometry does not have a boundary() method, so we need to extract
    the exterior ring and convert it to a LineString geometry.

    Args:
        geom (QgsGeometry): Polygon geometry

    Returns:
        QgsGeometry: LineString geometry representing the polygon boundary,
                     or None if geometry is invalid
    """
    if geom is None or geom.isEmpty():
        return None

    if geom.type() != QgsWkbTypes.PolygonGeometry:
        return None

    # Get the exterior ring
    if geom.isMultipart():
        polygons = geom.asMultiPolygon()
        if not polygons or not polygons[0]:
            return None
        # Use first polygon's outer ring
        exterior_ring = polygons[0][0]
    else:
        polygon = geom.asPolygon()
        if not polygon or not polygon[0]:
            return None
        # Get outer ring (first element)
        exterior_ring = polygon[0]

    # Create line geometry from ring
    return QgsGeometry.fromPolylineXY(exterior_ring)


def find_connection_edge(polygon1: QgsGeometry, polygon2: QgsGeometry,
                        tolerance: float = 0.1) -> tuple[QgsGeometry, float]:
    """
    Find the connection edge between two polygons that share a border.

    This function identifies the shared boundary segment(s) between two adjacent
    polygons. Useful for finding the connection between crane pad and boom surface.

    Args:
        polygon1 (QgsGeometry): First polygon
        polygon2 (QgsGeometry): Second polygon
        tolerance (float): Distance tolerance for edge matching (meters)

    Returns:
        tuple: (connection_geometry, total_length)
            - connection_geometry: QgsGeometry of shared edge (LineString or MultiLineString)
            - total_length: Total length of shared edges in meters
    """
    # Get boundaries of both polygons
    boundary1 = get_polygon_boundary(polygon1)
    boundary2 = get_polygon_boundary(polygon2)

    if boundary1 is None or boundary2 is None:
        return QgsGeometry(), 0.0

    # Find intersection of boundaries
    connection = boundary1.intersection(boundary2)

    # Calculate total length
    if connection.isEmpty():
        length = 0.0
    elif connection.type() == QgsWkbTypes.LineGeometry:
        length = connection.length()
    elif connection.type() == QgsWkbTypes.PointGeometry:
        # Only touching at points, no real edge
        length = 0.0
    else:
        length = 0.0

    return connection, length


def get_connection_edge_center(edge_geometry: QgsGeometry) -> QgsPointXY:
    """
    Get the center point of a connection edge.

    Args:
        edge_geometry (QgsGeometry): Edge geometry (LineString or MultiLineString)

    Returns:
        QgsPointXY: Center point of the edge
    """
    if edge_geometry.isEmpty():
        raise ValueError("Edge geometry is empty")

    # Use the centroid of the edge
    centroid = edge_geometry.centroid()
    return centroid.asPoint()


def get_edge_direction(edge_geometry: QgsGeometry) -> float:
    """
    Get the direction/orientation of an edge.

    Args:
        edge_geometry (QgsGeometry): Edge geometry (LineString)

    Returns:
        float: Direction angle in degrees (0-360)
    """
    if edge_geometry.type() != QgsWkbTypes.LineGeometry:
        raise ValueError("Edge must be a LineString")

    # Get vertices
    if edge_geometry.isMultipart():
        lines = edge_geometry.asMultiPolyline()
        if not lines:
            raise ValueError("Empty MultiLineString")
        # Use first line segment of first line
        vertices = lines[0]
    else:
        vertices = edge_geometry.asPolyline()

    if len(vertices) < 2:
        raise ValueError("Edge must have at least 2 vertices")

    # Calculate angle from first to last point
    p1 = vertices[0]
    p2 = vertices[-1]

    dx = p2.x() - p1.x()
    dy = p2.y() - p1.y()

    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)

    # Normalize to 0-360
    if angle_deg < 0:
        angle_deg += 360

    return angle_deg


def calculate_distance_from_edge(point: QgsPointXY, edge_geometry: QgsGeometry,
                                 direction: float) -> float:
    """
    Calculate the signed distance from a point to an edge along a specific direction.

    This is used for calculating boom surface heights with slope. The distance
    is positive in the direction of the slope.

    Args:
        point (QgsPointXY): Point to measure from
        edge_geometry (QgsGeometry): Connection edge
        direction (float): Direction angle in degrees for measuring distance

    Returns:
        float: Signed distance in meters (positive = in slope direction)
    """
    # Find closest point on edge to our point
    closest_point = edge_geometry.nearestPoint(QgsGeometry.fromPointXY(point))
    closest_xy = closest_point.asPoint()

    # Calculate vector from closest edge point to our point
    dx = point.x() - closest_xy.x()
    dy = point.y() - closest_xy.y()

    # Project onto direction vector
    direction_rad = math.radians(direction)
    direction_x = math.cos(direction_rad)
    direction_y = math.sin(direction_rad)

    # Dot product gives signed distance
    signed_distance = dx * direction_x + dy * direction_y

    return signed_distance


def perpendicular_direction(angle: float) -> float:
    """
    Get the perpendicular direction to a given angle.

    Args:
        angle (float): Angle in degrees

    Returns:
        float: Perpendicular angle (angle + 90°, normalized to 0-360)
    """
    perp = angle + 90.0
    if perp >= 360:
        perp -= 360
    return perp


def calculate_slope_height(base_height: float, distance: float, slope_percent: float,
                          slope_direction: str = 'down') -> float:
    """
    Calculate height at a distance from base with given slope.

    Args:
        base_height (float): Height at base/connection edge (m ü.NN)
        distance (float): Distance from base in slope direction (meters)
        slope_percent (float): Slope in percent (e.g., 5.0 for 5%)
        slope_direction (str): 'down' (default) or 'up'

    Returns:
        float: Height at the given distance (m ü.NN)
    """
    # Calculate height change
    height_change = distance * (slope_percent / 100.0)

    if slope_direction == 'down':
        return base_height - height_change
    else:  # 'up'
        return base_height + height_change


def identify_surface_at_point(point: QgsPointXY, surface_geometries: dict) -> str:
    """
    Identify which surface a point belongs to.

    Args:
        point (QgsPointXY): Point to check
        surface_geometries (dict): Dictionary of {surface_name: QgsGeometry}

    Returns:
        str: Name of surface containing the point, or None
    """
    point_geom = QgsGeometry.fromPointXY(point)

    for surface_name, geometry in surface_geometries.items():
        if geometry.contains(point_geom):
            return surface_name

    return None


def get_polygon_vertices(geometry: QgsGeometry) -> list[QgsPointXY]:
    """
    Extract vertices from a polygon geometry.

    Args:
        geometry (QgsGeometry): Polygon geometry

    Returns:
        list[QgsPointXY]: List of vertices
    """
    if geometry.isMultipart():
        polygons = geometry.asMultiPolygon()
        if polygons and polygons[0]:
            return polygons[0][0]  # Exterior ring of first polygon
        return []
    else:
        polygon = geometry.asPolygon()
        if polygon and polygon[0]:
            return polygon[0]  # Exterior ring
        return []


def calculate_terrain_slope(elevations: list[float], distances: list[float]) -> float:
    """
    Calculate average terrain slope from elevation profile.

    Args:
        elevations (list[float]): Elevation values along profile
        distances (list[float]): Distance values along profile

    Returns:
        float: Average slope in percent
    """
    if len(elevations) < 2 or len(distances) < 2:
        return 0.0

    # Simple linear regression
    n = len(elevations)
    sum_x = sum(distances)
    sum_y = sum(elevations)
    sum_xy = sum(d * e for d, e in zip(distances, elevations))
    sum_x2 = sum(d * d for d in distances)

    # Slope = (n*sum_xy - sum_x*sum_y) / (n*sum_x2 - sum_x^2)
    denominator = n * sum_x2 - sum_x * sum_x
    if abs(denominator) < 1e-10:
        return 0.0

    slope_m_per_m = (n * sum_xy - sum_x * sum_y) / denominator

    # Convert to percent
    slope_percent = slope_m_per_m * 100.0

    return slope_percent
