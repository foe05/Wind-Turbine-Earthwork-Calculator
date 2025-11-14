"""
Surface Validators for Multi-Surface Projects

Validates spatial relationships between different surface types:
- Foundation must be within/below crane pad
- Boom surface must touch crane pad (shared edge)
- Rotor storage must touch crane pad
- No overlaps between boom and rotor surfaces

Author: Wind Energy Site Planning
Version: 2.0 - Multi-Surface Extension
"""

from typing import Tuple, List, Dict
import math

from qgis.core import QgsGeometry, QgsPointXY, QgsWkbTypes

from .surface_types import MultiSurfaceProject, SurfaceType, SurfaceConfig
from ..utils.logging_utils import get_plugin_logger


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

        # 3. Boom touches crane pad
        valid, error = self.validate_boom_touches_crane_pad()
        if not valid:
            errors.append(error)

        # 4. Rotor storage touches crane pad
        valid, error = self.validate_rotor_touches_crane_pad()
        if not valid:
            errors.append(error)

        # 5. No overlap between boom and rotor
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
        Validate that foundation is within crane pad.

        Args:
            tolerance: Tolerance in meters for containment check

        Returns:
            Tuple of (is_valid, error_message)
        """
        crane_geom = self.project.crane_pad.geometry
        foundation_geom = self.project.foundation.geometry

        # Check if foundation is within crane pad (with small buffer for tolerance)
        crane_buffered = crane_geom.buffer(tolerance, 8)

        if not crane_buffered.contains(foundation_geom):
            # Check if at least mostly contained
            intersection = crane_geom.intersection(foundation_geom)
            overlap_ratio = intersection.area() / foundation_geom.area()

            if overlap_ratio < 0.95:  # At least 95% overlap required
                return False, (
                    f"Fundamentfläche muss innerhalb der Kranstellfläche liegen. "
                    f"Nur {overlap_ratio*100:.1f}% Überlappung gefunden."
                )

        self.logger.info("✓ Foundation is properly contained within crane pad")
        return True, ""

    def validate_boom_touches_crane_pad(self, min_edge_length: float = 3.0) -> Tuple[bool, str]:
        """
        Validate that boom surface touches crane pad with sufficient edge length.

        Args:
            min_edge_length: Minimum required shared edge length in meters

        Returns:
            Tuple of (is_valid, error_message)
        """
        crane_geom = self.project.crane_pad.geometry
        boom_geom = self.project.boom.geometry

        # Check if they touch or intersect
        if not crane_geom.touches(boom_geom) and not crane_geom.intersects(boom_geom):
            return False, "Auslegerfläche muss die Kranstellfläche berühren"

        # Find shared edge length
        shared_edge_length = self._calculate_shared_edge_length(crane_geom, boom_geom)

        if shared_edge_length < min_edge_length:
            return False, (
                f"Auslegerfläche hat zu kurze Verbindung zur Kranstellfläche. "
                f"Gefunden: {shared_edge_length:.1f}m, benötigt: {min_edge_length:.1f}m"
            )

        self.logger.info(
            f"✓ Boom surface touches crane pad with {shared_edge_length:.1f}m shared edge"
        )
        return True, ""

    def validate_rotor_touches_crane_pad(self, min_edge_length: float = 2.0) -> Tuple[bool, str]:
        """
        Validate that rotor storage touches crane pad with sufficient edge length.

        Args:
            min_edge_length: Minimum required shared edge length in meters

        Returns:
            Tuple of (is_valid, error_message)
        """
        crane_geom = self.project.crane_pad.geometry
        rotor_geom = self.project.rotor_storage.geometry

        # Check if they touch or intersect
        if not crane_geom.touches(rotor_geom) and not crane_geom.intersects(rotor_geom):
            return False, "Rotorlagerfläche muss die Kranstellfläche berühren"

        # Find shared edge length
        shared_edge_length = self._calculate_shared_edge_length(crane_geom, rotor_geom)

        if shared_edge_length < min_edge_length:
            return False, (
                f"Rotorlagerfläche hat zu kurze Verbindung zur Kranstellfläche. "
                f"Gefunden: {shared_edge_length:.1f}m, benötigt: {min_edge_length:.1f}m"
            )

        self.logger.info(
            f"✓ Rotor storage touches crane pad with {shared_edge_length:.1f}m shared edge"
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
                f"Auslegerfläche und Rotorlagerfläche dürfen sich nicht überlappen. "
                f"Überlappung: {overlap_area:.1f}m²"
            )

        # Also check if they're just touching (which is ok) vs. overlapping
        if boom_geom.intersects(rotor_geom):
            intersection = boom_geom.intersection(rotor_geom)
            if intersection.type() == QgsWkbTypes.PolygonGeometry:
                # It's a polygon intersection, not just a line/point - this is overlap
                return False, "Auslegerfläche und Rotorlagerfläche überlappen sich"

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
            SurfaceType.CRANE_PAD: (100, 2000),      # 10×10m to ~45×45m
            SurfaceType.FOUNDATION: (50, 500),       # Ø8m to Ø25m
            SurfaceType.BOOM: (50, 1000),            # Various sizes
            SurfaceType.ROTOR_STORAGE: (50, 500),    # Various sizes
        }

        for surface_name in ['crane_pad', 'foundation', 'boom', 'rotor_storage']:
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

        if errors:
            return False, "; ".join(errors)

        return True, ""

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
        boundary1 = geom1.boundary()
        boundary2 = geom2.boundary()

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
        boundary1 = geom1.boundary()
        boundary2 = geom2.boundary()

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
