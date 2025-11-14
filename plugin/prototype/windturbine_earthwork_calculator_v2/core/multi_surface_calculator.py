"""
Multi-Surface Earthwork Calculator

Calculates cut/fill volumes for all surface types in a wind turbine construction site:
- Foundation (Fundamentfläche): Excavation below FOK
- Crane Pad (Kranstellfläche): Planar surface with gravel layer
- Boom Surface (Auslegerfläche): Sloped surface with longitudinal gradient
- Rotor Storage (Rotorlagerfläche): Planar surface with height offset

Author: Wind Energy Site Planning
Version: 2.0 - Multi-Surface Extension
"""

import math
from typing import Optional, Tuple, Dict
import numpy as np

from qgis.core import (
    QgsRasterLayer,
    QgsGeometry,
    QgsPointXY,
    QgsProcessingFeedback
)

from .surface_types import (
    MultiSurfaceProject,
    SurfaceType,
    SurfaceCalculationResult,
    MultiSurfaceCalculationResult
)
from ..utils.geometry_utils import (
    find_connection_edge,
    get_edge_direction,
    calculate_distance_from_edge,
    calculate_slope_height,
    perpendicular_direction,
    calculate_terrain_slope
)
from ..utils.logging_utils import get_plugin_logger


class MultiSurfaceCalculator:
    """
    Calculator for multi-surface earthwork optimization.

    This calculator handles all four surface types simultaneously and finds
    the optimal crane pad height that minimizes total earthwork volume.
    """

    def __init__(self, dem_layer: QgsRasterLayer, project: MultiSurfaceProject):
        """
        Initialize multi-surface calculator.

        Args:
            dem_layer: Digital elevation model raster layer
            project: Multi-surface project configuration
        """
        self.dem_layer = dem_layer
        self.project = project
        self.logger = get_plugin_logger()

        # Get raster properties
        self.provider = dem_layer.dataProvider()
        self.pixel_size_x = dem_layer.rasterUnitsPerPixelX()
        self.pixel_size_y = dem_layer.rasterUnitsPerPixelY()
        self.pixel_area = self.pixel_size_x * self.pixel_size_y

        # Pre-calculate connection edges (for boom surface)
        self.boom_connection_edge = None
        self.boom_slope_direction = None
        self.rotor_connection_edge = None

        self._prepare_surface_relationships()

    def _prepare_surface_relationships(self):
        """Pre-calculate spatial relationships between surfaces."""
        # Find connection edge between crane pad and boom
        boom_edge, boom_length = find_connection_edge(
            self.project.crane_pad.geometry,
            self.project.boom.geometry
        )

        if boom_length > 0:
            self.boom_connection_edge = boom_edge
            # Determine slope direction (perpendicular to edge, pointing into boom)
            edge_angle = get_edge_direction(boom_edge)
            # The slope goes perpendicular to the connection edge, into the boom surface
            self.boom_slope_direction = perpendicular_direction(edge_angle)

            self.logger.info(
                f"Boom connection edge: {boom_length:.1f}m, "
                f"slope direction: {self.boom_slope_direction:.1f}°"
            )
        else:
            self.logger.warning("No connection edge found between crane pad and boom")

        # Find connection edge between crane pad and rotor storage
        rotor_edge, rotor_length = find_connection_edge(
            self.project.crane_pad.geometry,
            self.project.rotor_storage.geometry
        )

        if rotor_length > 0:
            self.rotor_connection_edge = rotor_edge
            self.logger.info(f"Rotor storage connection edge: {rotor_length:.1f}m")
        else:
            self.logger.warning("No connection edge found between crane pad and rotor storage")

    def sample_dem_in_polygon(self, geometry: QgsGeometry) -> np.ndarray:
        """
        Sample DEM values within a polygon.

        Args:
            geometry: Polygon to sample

        Returns:
            Array of elevation values (flattened)
        """
        bbox = geometry.boundingBox()

        # Calculate pixel indices
        x_min_px = int((bbox.xMinimum() - self.dem_layer.extent().xMinimum()) / self.pixel_size_x)
        x_max_px = int((bbox.xMaximum() - self.dem_layer.extent().xMinimum()) / self.pixel_size_x) + 1
        y_min_px = int((self.dem_layer.extent().yMaximum() - bbox.yMaximum()) / self.pixel_size_y)
        y_max_px = int((self.dem_layer.extent().yMaximum() - bbox.yMinimum()) / self.pixel_size_y) + 1

        # Clamp to raster extent
        x_min_px = max(0, x_min_px)
        y_min_px = max(0, y_min_px)
        x_max_px = min(self.dem_layer.width(), x_max_px)
        y_max_px = min(self.dem_layer.height(), y_max_px)

        width = x_max_px - x_min_px
        height = y_max_px - y_min_px

        if width <= 0 or height <= 0:
            return np.array([])

        # Read raster block
        block = self.provider.block(1, bbox, width, height)

        elevations = []
        for row in range(height):
            for col in range(width):
                # Calculate world coordinates
                x = self.dem_layer.extent().xMinimum() + (x_min_px + col) * self.pixel_size_x
                y = self.dem_layer.extent().yMaximum() - (y_min_px + row) * self.pixel_size_y

                point = QgsPointXY(x, y)
                point_geom = QgsGeometry.fromPointXY(point)

                # Check if point is within geometry
                if geometry.contains(point_geom):
                    value = block.value(row, col)
                    if not block.isNoData(row, col) and value is not None:
                        elevations.append(float(value))

        return np.array(elevations, dtype=float)

    def sample_dem_with_positions(self, geometry: QgsGeometry) -> list[tuple[QgsPointXY, float]]:
        """
        Sample DEM values within a polygon with position information.

        Args:
            geometry: Polygon to sample

        Returns:
            List of (point, elevation) tuples
        """
        bbox = geometry.boundingBox()

        # Calculate pixel indices
        x_min_px = int((bbox.xMinimum() - self.dem_layer.extent().xMinimum()) / self.pixel_size_x)
        x_max_px = int((bbox.xMaximum() - self.dem_layer.extent().xMinimum()) / self.pixel_size_x) + 1
        y_min_px = int((self.dem_layer.extent().yMaximum() - bbox.yMaximum()) / self.pixel_size_y)
        y_max_px = int((self.dem_layer.extent().yMaximum() - bbox.yMinimum()) / self.pixel_size_y) + 1

        # Clamp to raster extent
        x_min_px = max(0, x_min_px)
        y_min_px = max(0, y_min_px)
        x_max_px = min(self.dem_layer.width(), x_max_px)
        y_max_px = min(self.dem_layer.height(), y_max_px)

        width = x_max_px - x_min_px
        height = y_max_px - y_min_px

        if width <= 0 or height <= 0:
            return []

        # Read raster block
        block = self.provider.block(1, bbox, width, height)

        samples = []
        for row in range(height):
            for col in range(width):
                # Calculate world coordinates
                x = self.dem_layer.extent().xMinimum() + (x_min_px + col) * self.pixel_size_x
                y = self.dem_layer.extent().yMaximum() - (y_min_px + row) * self.pixel_size_y

                point = QgsPointXY(x, y)
                point_geom = QgsGeometry.fromPointXY(point)

                # Check if point is within geometry
                if geometry.contains(point_geom):
                    value = block.value(row, col)
                    if not block.isNoData(row, col) and value is not None:
                        samples.append((point, float(value)))

        return samples

    def calculate_slope_width(self, max_height_diff: float) -> float:
        """
        Calculate slope width based on maximum height difference and slope angle.

        Args:
            max_height_diff: Maximum height difference (meters)

        Returns:
            Slope width (meters)
        """
        angle_rad = math.radians(self.project.slope_angle)
        slope_width = max_height_diff / math.tan(angle_rad)
        return slope_width

    def _calculate_foundation(self) -> SurfaceCalculationResult:
        """
        Calculate foundation excavation volume.

        The foundation is excavated from current terrain down to foundation bottom
        (FOK - foundation_depth). The volume is pure excavation (cut), minimal fill
        is just for reference (actual fill is concrete, not soil).

        Returns:
            Calculation result for foundation
        """
        # Sample terrain in foundation area
        elevations = self.sample_dem_in_polygon(self.project.foundation.geometry)

        if len(elevations) == 0:
            self.logger.warning("No DEM data in foundation area")
            return SurfaceCalculationResult(
                surface_type=SurfaceType.FOUNDATION,
                target_height=self.project.fok,
                cut_volume=0.0,
                fill_volume=0.0,
                platform_area=0.0
            )

        terrain_min = float(np.min(elevations))
        terrain_max = float(np.max(elevations))
        terrain_mean = float(np.mean(elevations))

        # Foundation bottom elevation
        foundation_bottom = self.project.foundation_bottom_elevation

        # Calculate excavation volume
        # Volume = area × depth, but we calculate it pixel by pixel for accuracy
        cut_volume = 0.0

        for elevation in elevations:
            # Excavate from terrain to foundation bottom
            depth = elevation - foundation_bottom
            if depth > 0:
                cut_volume += depth * self.pixel_area

        # Minimal fill (for reference - actual fill is concrete)
        # Just the volume of the foundation itself as placeholder
        fill_volume_ref = self.project.foundation.geometry.area() * self.project.foundation_depth * 0.1

        area = self.project.foundation.geometry.area()

        self.logger.info(
            f"Foundation: cut={cut_volume:.1f}m³, "
            f"depth={self.project.foundation_depth:.2f}m, area={area:.1f}m²"
        )

        return SurfaceCalculationResult(
            surface_type=SurfaceType.FOUNDATION,
            target_height=self.project.fok,
            cut_volume=cut_volume,
            fill_volume=fill_volume_ref,
            platform_area=area,
            terrain_min=terrain_min,
            terrain_max=terrain_max,
            terrain_mean=terrain_mean,
            additional_data={
                'foundation_bottom': round(foundation_bottom, 2),
                'foundation_depth': round(self.project.foundation_depth, 2)
            }
        )

    def _calculate_crane_pad(self, crane_height: float) -> SurfaceCalculationResult:
        """
        Calculate crane pad earthwork.

        The crane pad is planar at crane_height - gravel_thickness.
        This is the main optimization variable.

        Args:
            crane_height: Target crane pad height (m ü.NN)

        Returns:
            Calculation result for crane pad
        """
        # Sample terrain in crane pad area
        elevations = self.sample_dem_in_polygon(self.project.crane_pad.geometry)

        if len(elevations) == 0:
            raise ValueError("No DEM data in crane pad area")

        terrain_min = float(np.min(elevations))
        terrain_max = float(np.max(elevations))
        terrain_mean = float(np.mean(elevations))

        # Planum height (below crane surface due to gravel layer)
        planum_height = crane_height - self.project.gravel_thickness

        # Calculate cut/fill on platform
        cut_volume = 0.0
        fill_volume = 0.0

        for elevation in elevations:
            diff = elevation - planum_height
            if diff > 0:  # Cut (existing terrain is higher than planum)
                cut_volume += diff * self.pixel_area
            else:  # Fill (existing terrain is lower than planum)
                fill_volume += abs(diff) * self.pixel_area

        # Calculate slope area around crane pad
        max_height_diff = max(abs(terrain_max - planum_height), abs(terrain_min - planum_height))
        slope_width = self.calculate_slope_width(max_height_diff)

        # Buffered polygon for slope
        slope_polygon = self.project.crane_pad.geometry.buffer(slope_width, 16)
        slope_only = slope_polygon.difference(self.project.crane_pad.geometry)

        # Sample DEM in slope area
        slope_elevations = self.sample_dem_in_polygon(slope_only)

        # Calculate cut/fill on slope (simplified - mid-height approximation)
        slope_cut = 0.0
        slope_fill = 0.0

        for elevation in slope_elevations:
            avg_height = (planum_height + elevation) / 2.0
            diff = elevation - avg_height

            if diff > 0:
                slope_cut += diff * self.pixel_area
            else:
                slope_fill += abs(diff) * self.pixel_area

        total_cut = cut_volume + slope_cut
        total_fill = fill_volume + slope_fill

        area = self.project.crane_pad.geometry.area()
        total_area = slope_polygon.area()

        self.logger.info(
            f"Crane pad @ {crane_height:.2f}m: cut={total_cut:.1f}m³, "
            f"fill={total_fill:.1f}m³, area={area:.1f}m²"
        )

        return SurfaceCalculationResult(
            surface_type=SurfaceType.CRANE_PAD,
            target_height=crane_height,
            cut_volume=total_cut,
            fill_volume=total_fill,
            platform_area=area,
            slope_area=slope_polygon.area() - area,
            total_area=total_area,
            terrain_min=terrain_min,
            terrain_max=terrain_max,
            terrain_mean=terrain_mean,
            additional_data={
                'planum_height': round(planum_height, 2),
                'gravel_thickness': round(self.project.gravel_thickness, 2),
                'slope_width': round(slope_width, 2)
            }
        )

    def _calculate_boom_surface(self, crane_height: float) -> SurfaceCalculationResult:
        """
        Calculate boom surface earthwork.

        The boom surface has a longitudinal slope, connecting to crane pad at
        crane_height and sloping downward.

        Args:
            crane_height: Crane pad height (connection edge is at this height)

        Returns:
            Calculation result for boom surface
        """
        if self.boom_connection_edge is None or self.boom_connection_edge.isEmpty():
            self.logger.warning("No boom connection edge available")
            return SurfaceCalculationResult(
                surface_type=SurfaceType.BOOM,
                target_height=crane_height,
                cut_volume=0.0,
                fill_volume=0.0,
                platform_area=0.0
            )

        # Sample terrain with positions
        samples = self.sample_dem_with_positions(self.project.boom.geometry)

        if len(samples) == 0:
            self.logger.warning("No DEM data in boom area")
            return SurfaceCalculationResult(
                surface_type=SurfaceType.BOOM,
                target_height=crane_height,
                cut_volume=0.0,
                fill_volume=0.0,
                platform_area=0.0
            )

        # Determine slope percentage
        slope_percent = self.project.boom.slope_longitudinal

        # If auto-slope is enabled, try to match terrain
        if self.project.boom.auto_slope:
            # Calculate terrain slope in boom area
            distances = []
            elevations_for_slope = []

            for point, elevation in samples:
                distance = calculate_distance_from_edge(
                    point,
                    self.boom_connection_edge,
                    self.boom_slope_direction
                )
                if distance > 0:  # Only points in slope direction
                    distances.append(distance)
                    elevations_for_slope.append(elevation)

            if len(elevations_for_slope) > 5:
                terrain_slope = calculate_terrain_slope(elevations_for_slope, distances)
                # Clamp to allowed range
                slope_percent = max(
                    self.project.boom.slope_min,
                    min(self.project.boom.slope_max, abs(terrain_slope))
                )
                self.logger.info(
                    f"Auto-adjusted boom slope: terrain={terrain_slope:.2f}%, "
                    f"used={slope_percent:.2f}%"
                )

        # Calculate cut/fill
        cut_volume = 0.0
        fill_volume = 0.0
        elevations_only = []

        for point, terrain_elevation in samples:
            # Calculate distance from connection edge in slope direction
            distance = calculate_distance_from_edge(
                point,
                self.boom_connection_edge,
                self.boom_slope_direction
            )

            # Target height at this distance
            # Note: distance can be negative (wrong side of edge), handle gracefully
            if distance < 0:
                # Point is on wrong side of connection edge (shouldn't happen if geometries are correct)
                target_height = crane_height
            else:
                target_height = calculate_slope_height(
                    crane_height,
                    distance,
                    slope_percent,
                    'down'
                )

            elevations_only.append(terrain_elevation)

            # Cut/fill
            diff = terrain_elevation - target_height
            if diff > 0:
                cut_volume += diff * self.pixel_area
            else:
                fill_volume += abs(diff) * self.pixel_area

        terrain_min = float(np.min(elevations_only)) if elevations_only else 0.0
        terrain_max = float(np.max(elevations_only)) if elevations_only else 0.0
        terrain_mean = float(np.mean(elevations_only)) if elevations_only else 0.0

        # Calculate slope area (embankment around boom surface)
        # Similar to crane pad but potentially more complex due to sloped target
        max_height_diff = max(
            abs(terrain_max - crane_height),
            abs(terrain_min - (crane_height - 50 * slope_percent / 100))  # Estimate far end
        )
        slope_width = self.calculate_slope_width(max_height_diff)

        slope_polygon = self.project.boom.geometry.buffer(slope_width, 16)
        slope_only = slope_polygon.difference(self.project.boom.geometry)
        slope_elevations = self.sample_dem_in_polygon(slope_only)

        slope_cut = 0.0
        slope_fill = 0.0

        for elevation in slope_elevations:
            # Simplified: use average of crane height and estimated far end
            avg_height = crane_height - 25 * slope_percent / 100
            diff = elevation - avg_height

            if diff > 0:
                slope_cut += diff * self.pixel_area
            else:
                slope_fill += abs(diff) * self.pixel_area

        total_cut = cut_volume + slope_cut
        total_fill = fill_volume + slope_fill

        area = self.project.boom.geometry.area()
        total_area = slope_polygon.area()

        self.logger.info(
            f"Boom surface @ {crane_height:.2f}m: slope={slope_percent:.2f}%, "
            f"cut={total_cut:.1f}m³, fill={total_fill:.1f}m³"
        )

        return SurfaceCalculationResult(
            surface_type=SurfaceType.BOOM,
            target_height=crane_height,  # At connection edge
            cut_volume=total_cut,
            fill_volume=total_fill,
            platform_area=area,
            slope_area=total_area - area,
            total_area=total_area,
            terrain_min=terrain_min,
            terrain_max=terrain_max,
            terrain_mean=terrain_mean,
            additional_data={
                'slope_percent': round(slope_percent, 2),
                'slope_direction': round(self.boom_slope_direction, 1),
                'auto_slope': self.project.boom.auto_slope
            }
        )

    def _calculate_rotor_storage(self, crane_height: float) -> SurfaceCalculationResult:
        """
        Calculate rotor storage earthwork.

        The rotor storage is planar but at a different height than the crane pad,
        determined by rotor_height_offset.

        Args:
            crane_height: Crane pad height

        Returns:
            Calculation result for rotor storage
        """
        # Rotor storage height
        rotor_height = crane_height + self.project.rotor_height_offset

        # Sample terrain
        elevations = self.sample_dem_in_polygon(self.project.rotor_storage.geometry)

        if len(elevations) == 0:
            self.logger.warning("No DEM data in rotor storage area")
            return SurfaceCalculationResult(
                surface_type=SurfaceType.ROTOR_STORAGE,
                target_height=rotor_height,
                cut_volume=0.0,
                fill_volume=0.0,
                platform_area=0.0
            )

        terrain_min = float(np.min(elevations))
        terrain_max = float(np.max(elevations))
        terrain_mean = float(np.mean(elevations))

        # Calculate cut/fill
        cut_volume = 0.0
        fill_volume = 0.0

        for elevation in elevations:
            diff = elevation - rotor_height
            if diff > 0:
                cut_volume += diff * self.pixel_area
            else:
                fill_volume += abs(diff) * self.pixel_area

        # Calculate slope area
        max_height_diff = max(abs(terrain_max - rotor_height), abs(terrain_min - rotor_height))
        slope_width = self.calculate_slope_width(max_height_diff)

        slope_polygon = self.project.rotor_storage.geometry.buffer(slope_width, 16)
        slope_only = slope_polygon.difference(self.project.rotor_storage.geometry)
        slope_elevations = self.sample_dem_in_polygon(slope_only)

        slope_cut = 0.0
        slope_fill = 0.0

        for elevation in slope_elevations:
            avg_height = (rotor_height + elevation) / 2.0
            diff = elevation - avg_height

            if diff > 0:
                slope_cut += diff * self.pixel_area
            else:
                slope_fill += abs(diff) * self.pixel_area

        total_cut = cut_volume + slope_cut
        total_fill = fill_volume + slope_fill

        area = self.project.rotor_storage.geometry.area()
        total_area = slope_polygon.area()

        self.logger.info(
            f"Rotor storage @ {rotor_height:.2f}m: cut={total_cut:.1f}m³, "
            f"fill={total_fill:.1f}m³, area={area:.1f}m²"
        )

        return SurfaceCalculationResult(
            surface_type=SurfaceType.ROTOR_STORAGE,
            target_height=rotor_height,
            cut_volume=total_cut,
            fill_volume=total_fill,
            platform_area=area,
            slope_area=total_area - area,
            total_area=total_area,
            terrain_min=terrain_min,
            terrain_max=terrain_max,
            terrain_mean=terrain_mean,
            additional_data={
                'height_offset_from_crane': round(self.project.rotor_height_offset, 2)
            }
        )

    def calculate_scenario(self, crane_height: float,
                          feedback: Optional[QgsProcessingFeedback] = None) -> MultiSurfaceCalculationResult:
        """
        Calculate earthwork for all surfaces at a specific crane pad height.

        Args:
            crane_height: Crane pad height (m ü.NN)
            feedback: Optional feedback object

        Returns:
            Complete multi-surface calculation result
        """
        # Calculate each surface
        foundation_result = self._calculate_foundation()
        crane_result = self._calculate_crane_pad(crane_height)
        boom_result = self._calculate_boom_surface(crane_height)
        rotor_result = self._calculate_rotor_storage(crane_height)

        # Compile results
        surface_results = {
            SurfaceType.FOUNDATION: foundation_result,
            SurfaceType.CRANE_PAD: crane_result,
            SurfaceType.BOOM: boom_result,
            SurfaceType.ROTOR_STORAGE: rotor_result
        }

        result = MultiSurfaceCalculationResult(
            crane_height=crane_height,
            fok=self.project.fok,
            surface_results=surface_results
        )

        if feedback:
            feedback.pushInfo(
                f"  h={crane_height:.2f}m: "
                f"total_cut={result.total_cut:.0f}m³, "
                f"total_fill={result.total_fill:.0f}m³, "
                f"total_moved={result.total_volume_moved:.0f}m³"
            )

        return result

    def find_optimum(self, feedback: Optional[QgsProcessingFeedback] = None) -> Tuple[float, MultiSurfaceCalculationResult]:
        """
        Find optimal crane pad height that minimizes total earthwork volume.

        The search range is defined by project.search_min_height to project.search_max_height
        (relative to FOK).

        Args:
            feedback: Optional feedback object

        Returns:
            Tuple of (optimal_crane_height, results)
        """
        min_height = self.project.search_min_height
        max_height = self.project.search_max_height
        step = self.project.search_step

        self.logger.info(
            f"Optimizing crane pad height: {min_height:.2f}m - {max_height:.2f}m "
            f"(step: {step:.3f}m)"
        )

        heights = np.arange(min_height, max_height + step, step)
        num_scenarios = len(heights)

        self.logger.info(f"Testing {num_scenarios} height scenarios")

        if feedback:
            feedback.pushInfo(f"Testing {num_scenarios} crane pad heights...")

        best_height = None
        best_volume = float('inf')
        best_result = None

        all_results = []

        for i, height in enumerate(heights):
            if feedback and feedback.isCanceled():
                break

            try:
                result = self.calculate_scenario(height, feedback)
                all_results.append(result)

                total_volume = result.total_volume_moved

                if total_volume < best_volume:
                    best_volume = total_volume
                    best_height = height
                    best_result = result
                elif total_volume == best_volume:
                    # Tie-breaker: prefer more balanced cut/fill
                    if abs(result.net_volume) < abs(best_result.net_volume):
                        best_height = height
                        best_result = result

                # Progress update
                if feedback and i % 10 == 0:
                    progress = int((i / num_scenarios) * 100)
                    feedback.setProgress(progress)

            except Exception as e:
                self.logger.error(f"Error calculating scenario h={height:.2f}m: {e}")
                if feedback:
                    feedback.reportError(f"Error at height {height:.2f}m: {e}", fatalError=False)

        if best_result is None:
            raise ValueError("No valid scenarios found during optimization")

        self.logger.info(
            f"Optimization complete: optimal crane height = {best_height:.2f}m, "
            f"total volume = {best_volume:.0f}m³"
        )

        if feedback:
            feedback.pushInfo(
                f"\n✓ Optimal crane pad height: {best_height:.2f}m "
                f"(total earthwork: {best_volume:.0f}m³)"
            )
            feedback.pushInfo(
                f"  FOK: {self.project.fok:.2f}m, "
                f"Offset from FOK: {(best_height - self.project.fok):+.2f}m"
            )

        return best_height, best_result
