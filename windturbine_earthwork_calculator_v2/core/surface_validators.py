"""
Surface Validators for Multi-Surface Projects

Validates spatial relationships between different surface types:
- Foundation must be within/below crane pad
- Boom surface must touch crane pad (shared edge)
- Rotor storage must touch crane pad
- No overlaps between boom and rotor surfaces

Author: Wind Energy Site Planning
Version: 2.0.0 - Multi-Surface Extension
"""

from typing import Tuple, List, Dict
import math

from qgis.core import QgsGeometry, QgsPointXY, QgsWkbTypes

from .surface_types import MultiSurfaceProject, SurfaceType, SurfaceConfig
from ..utils.logging_utils import get_plugin_logger
from ..utils.geometry_utils import get_polygon_boundary


class SurfaceValidator:
    """Validates spatial relationships between surfaces in a multi-surface project."""

    def __init__(self, project: MultiSurfaceProject):
        """
        Initialize validator.

        Args:
            project: Multi-surface project to validate
        """
        self.project = project
        self.logger = get_plugin_logger()

    def validate_all(self) -> Tuple[bool, List[str]]:
        """
        Run all validation checks.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # 1. Validate project configuration
        config_valid, config_error = self.project.validate()
        if not config_valid:
            errors.append(f"Configuration error: {config_error}")

        # 2. Foundation within crane pad
        valid, error = self.validate_foundation_in_crane_pad()
        if not valid:
            errors.append(error)

        # 3. Boom touches crane pad (only if boom exists)
        if self.project.boom is not None:
            valid, error = self.validate_boom_touches_crane_pad()
            if not valid:
                errors.append(error)

        # 4. Rotor storage touches crane pad (only if rotor storage exists)
        if self.project.rotor_storage is not None:
            valid, error = self.validate_rotor_touches_crane_pad()
            if not valid:
                errors.append(error)

        # 5. No overlap between boom and rotor (only if both exist)
        if self.project.boom is not None and self.project.rotor_storage is not None:
            valid, error = self.validate_no_overlap_boom_rotor()
            if not valid:
                errors.append(error)

        # 6. All surfaces have reasonable sizes
        valid, error = self.validate_surface_sizes()
        if not valid:
            errors.append(error)

        is_valid = len(errors) == 0
        return is_valid, errors

    def validate_foundation_in_crane_pad(self, tolerance: float = 0.5) -> Tuple[bool, str]:
        """
        Validate that foundation touches or is within crane pad.

        Args:
            tolerance: Tolerance in meters for touch/containment check

        Returns:
            Tuple of (is_valid, error_message)
        """
        crane_geom = self.project.crane_pad.geometry
        foundation_geom = self.project.foundation.geometry

        # Check if foundation touches or intersects crane pad
        if not crane_geom.touches(foundation_geom) and not crane_geom.intersects(foundation_geom):
            return False, "Fundamentfläche muss die Kranstellfläche berühren oder darin liegen"

        self.logger.info("✓ Foundation touches or is within crane pad")
        return True, ""

    def validate_boom_touches_crane_pad(self, max_distance: float = 5.0) -> Tuple[bool, str]:
        """
        Validate that boom surface is near crane pad and identify connection edge.

        The boom surface does not need to directly touch the crane pad due to
        DXF digitization inaccuracies. Instead, we find the edge of the boom
        that is closest to the foundation (which is on/in the crane pad).

        Args:
            max_distance: Maximum allowed distance between boom and crane pad (meters)

        Returns:
            Tuple of (is_valid, error_message)
        """
        crane_geom = self.project.crane_pad.geometry
        boom_geom = self.project.boom.geometry
        foundation_geom = self.project.foundation.geometry

        # Find the edge of boom closest to foundation
        connection_edge, edge_length = self._find_boom_connection_edge(
            boom_geom, foundation_geom, crane_geom
        )

        if connection_edge is None or edge_length == 0:
            return False, "Konnte keine Verbindungskante der Auslegerfläche zur Kranstellfläche finden"

        # Check distance between boom and crane pad
        distance = crane_geom.distance(boom_geom)

        if distance > max_distance:
            return False, (
                f"Auslegerfläche ist zu weit von der Kranstellfläche entfernt. "
                f"Abstand: {distance:.2f}m, Maximum: {max_distance:.1f}m"
            )

        self.logger.info(
            f"✓ Boom connection edge identified: {edge_length:.2f}m length, "
            f"{distance:.2f}m distance to crane pad"
        )
        return True, ""

    def validate_rotor_touches_crane_pad(self, max_distance: float = 3.0) -> Tuple[bool, str]:
        """
        Validate that rotor storage is near crane pad.

        A small gap between rotor storage and crane pad is allowed.

        Args:
            max_distance: Maximum allowed distance between rotor storage and crane pad (meters)

        Returns:
            Tuple of (is_valid, error_message)
        """
        crane_geom = self.project.crane_pad.geometry
        rotor_geom = self.project.rotor_storage.geometry

        # Calculate distance between rotor storage and crane pad
        distance = crane_geom.distance(rotor_geom)

        if distance > max_distance:
            return False, (
                f"Blattlagerfläche ist zu weit von der Kranstellfläche entfernt. "
                f"Abstand: {distance:.2f}m, Maximum: {max_distance:.1f}m"
            )

        self.logger.info(
            f"✓ Rotor storage is near crane pad (distance: {distance:.2f}m)"
        )
        return True, ""

    def validate_no_overlap_boom_rotor(self) -> Tuple[bool, str]:
        """
        Validate that boom and rotor storage don't overlap.

        Returns:
            Tuple of (is_valid, error_message)
        """
        boom_geom = self.project.boom.geometry
        rotor_geom = self.project.rotor_storage.geometry

        if boom_geom.overlaps(rotor_geom):
            intersection = boom_geom.intersection(rotor_geom)
            overlap_area = intersection.area()
            return False, (
                f"Auslegerfläche und Blattlagerfläche dürfen sich nicht überlappen. "
                f"Überlappung: {overlap_area:.1f}m²"
            )

        # Also check if they're just touching (which is ok) vs. overlapping
        if boom_geom.intersects(rotor_geom):
            intersection = boom_geom.intersection(rotor_geom)
            if intersection.type() == QgsWkbTypes.PolygonGeometry:
                # It's a polygon intersection, not just a line/point - this is overlap
                return False, "Auslegerfläche und Blattlagerfläche überlappen sich"

        self.logger.info("✓ Boom and rotor storage do not overlap")
        return True, ""

    def validate_surface_sizes(self) -> Tuple[bool, str]:
        """
        Validate that all surfaces have reasonable sizes.

        Returns:
            Tuple of (is_valid, error_message)
        """
        errors = []

        # Define reasonable size ranges (m²)
        size_limits = {
            SurfaceType.CRANE_PAD: (100, 20000),     # 10×10m to ~140×140m
            SurfaceType.FOUNDATION: (50, 5000),      # Ø8m to Ø80m
            SurfaceType.BOOM: (50, 10000),           # Various sizes up to 100×100m
            SurfaceType.ROTOR_STORAGE: (50, 5000),   # Various sizes up to ~70×70m
        }

        # Required surfaces
        for surface_name in ['crane_pad', 'foundation']:
            surface: SurfaceConfig = getattr(self.project, surface_name)
            area = surface.geometry.area()
            min_area, max_area = size_limits[surface.surface_type]

            if area < min_area:
                errors.append(
                    f"{surface.surface_type.display_name} zu klein: {area:.1f}m² "
                    f"(Minimum: {min_area}m²)"
                )
            elif area > max_area:
                errors.append(
                    f"{surface.surface_type.display_name} zu groß: {area:.1f}m² "
                    f"(Maximum: {max_area}m²)"
                )
            else:
                self.logger.info(
                    f"✓ {surface.surface_type.display_name} size OK: {area:.1f}m²"
                )

        # Optional surfaces
        for surface_name in ['boom', 'rotor_storage']:
            surface: SurfaceConfig = getattr(self.project, surface_name)
            if surface is None:
                continue

            area = surface.geometry.area()
            min_area, max_area = size_limits[surface.surface_type]

            if area < min_area:
                errors.append(
                    f"{surface.surface_type.display_name} zu klein: {area:.1f}m² "
                    f"(Minimum: {min_area}m²)"
                )
            elif area > max_area:
                errors.append(
                    f"{surface.surface_type.display_name} zu groß: {area:.1f}m² "
                    f"(Maximum: {max_area}m²)"
                )
            else:
                self.logger.info(
                    f"✓ {surface.surface_type.display_name} size OK: {area:.1f}m²"
                )

        if errors:
            return False, "; ".join(errors)

        return True, ""

    def _find_boom_connection_edge(self, boom_geom: QgsGeometry,
                                    foundation_geom: QgsGeometry,
                                    crane_geom: QgsGeometry) -> Tuple[QgsGeometry, float]:
        """
        Find the edge of the boom surface that is closest to the foundation.

        This edge will be used as the connection edge for height calculations,
        even if the boom doesn't directly touch the crane pad.

        Args:
            boom_geom: Boom surface geometry
            foundation_geom: Foundation geometry
            crane_geom: Crane pad geometry

        Returns:
            Tuple of (edge_geometry, edge_length)
                - edge_geometry: QgsGeometry of the connection edge (LineString)
                - edge_length: Length of the edge in meters
        """
        # Get boom boundary
        boom_boundary = get_polygon_boundary(boom_geom)
        if boom_boundary is None:
            return None, 0.0

        # Extract all edges of the boom polygon
        if boom_geom.isMultipart():
            polygons = boom_geom.asMultiPolygon()
            if not polygons or not polygons[0]:
                return None, 0.0
            vertices = polygons[0][0]  # Exterior ring
        else:
            polygon = boom_geom.asPolygon()
            if not polygon or not polygon[0]:
                return None, 0.0
            vertices = polygon[0]  # Exterior ring

        # Get foundation centroid for distance calculation
        foundation_centroid = foundation_geom.centroid().asPoint()

        # Find the edge closest to foundation
        min_distance = float('inf')
        closest_edge = None
        closest_edge_length = 0

        for i in range(len(vertices) - 1):
            p1 = vertices[i]
            p2 = vertices[i + 1]

            # Create edge geometry
            edge = QgsGeometry.fromPolylineXY([p1, p2])
            edge_length = edge.length()

            # Calculate distance from edge midpoint to foundation centroid
            edge_midpoint = edge.centroid().asPoint()
            distance = math.sqrt(
                (edge_midpoint.x() - foundation_centroid.x())**2 +
                (edge_midpoint.y() - foundation_centroid.y())**2
            )

            # Update if this edge is closer
            if distance < min_distance:
                min_distance = distance
                closest_edge = edge
                closest_edge_length = edge_length

        if closest_edge is None:
            return None, 0.0

        self.logger.debug(
            f"  Found boom connection edge: {closest_edge_length:.2f}m length, "
            f"{min_distance:.2f}m from foundation centroid"
        )

        return closest_edge, closest_edge_length

    def _calculate_shared_edge_length(self, geom1: QgsGeometry, geom2: QgsGeometry,
                                     tolerance: float = 0.1) -> float:
        """
        Calculate the total length of shared edges between two polygons.

        Args:
            geom1: First polygon
            geom2: Second polygon
            tolerance: Distance tolerance for considering edges as shared

        Returns:
            Total length of shared edges in meters
        """
        # Get boundaries
        boundary1 = get_polygon_boundary(geom1)
        boundary2 = get_polygon_boundary(geom2)

        if boundary1 is None or boundary2 is None:
            return 0.0

        # Find intersection of boundaries
        intersection = boundary1.intersection(boundary2)

        if intersection.isEmpty():
            return 0.0

        # Calculate total length
        if intersection.type() == QgsWkbTypes.LineGeometry:
            if intersection.isMultipart():
                lines = intersection.asMultiPolyline()
                total_length = sum(
                    QgsGeometry.fromPolylineXY(line).length()
                    for line in lines
                )
            else:
                total_length = intersection.length()
        elif intersection.type() == QgsWkbTypes.PointGeometry:
            # Just touching at points, no shared edge
            total_length = 0.0
        else:
            # Shouldn't happen, but handle gracefully
            total_length = 0.0

        return total_length

    def get_connection_edge(self, surface1: SurfaceType, surface2: SurfaceType) -> QgsGeometry:
        """
        Get the connection edge geometry between two surfaces.

        Args:
            surface1: First surface type
            surface2: Second surface type

        Returns:
            QgsGeometry of the connection edge (LineString or MultiLineString)
        """
        # Get geometries
        geom1 = self._get_surface_geometry(surface1)
        geom2 = self._get_surface_geometry(surface2)

        # Get boundaries
        boundary1 = get_polygon_boundary(geom1)
        boundary2 = get_polygon_boundary(geom2)

        if boundary1 is None or boundary2 is None:
            return QgsGeometry()

        # Find intersection
        connection = boundary1.intersection(boundary2)

        return connection

    def _get_surface_geometry(self, surface_type: SurfaceType) -> QgsGeometry:
        """Get geometry for a surface type."""
        surface_map = {
            SurfaceType.CRANE_PAD: self.project.crane_pad,
            SurfaceType.FOUNDATION: self.project.foundation,
            SurfaceType.BOOM: self.project.boom,
            SurfaceType.ROTOR_STORAGE: self.project.rotor_storage,
        }
        return surface_map[surface_type].geometry


def validate_project(project: MultiSurfaceProject) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate a project.

    Args:
        project: Project to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    validator = SurfaceValidator(project)
    return validator.validate_all()
