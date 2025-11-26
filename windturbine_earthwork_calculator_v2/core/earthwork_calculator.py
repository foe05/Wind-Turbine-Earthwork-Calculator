"""
Earthwork Calculator for Wind Turbine Earthwork Calculator V2

Calculates cut/fill volumes and optimizes platform height.

Adapted from WindTurbine_Earthwork_Calculator.py with optimizations.

Author: Wind Energy Site Planning
Version: 2.0.0
"""

import math
from typing import Dict, Tuple, List, Optional
import numpy as np

from qgis.core import (
    QgsRasterLayer,
    QgsGeometry,
    QgsPointXY,
    QgsProcessingFeedback,
    QgsRectangle
)

try:
    from osgeo import gdal, ogr
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False

from ..utils.geometry_utils import get_centroid
from ..utils.logging_utils import get_plugin_logger


class EarthworkCalculator:
    """
    Calculates earthwork volumes for wind turbine crane pads.

    The calculator:
    - Samples DEM within and around the platform polygon
    - Calculates cut/fill volumes for different platform heights
    - Includes slope (embankment) calculations
    - Optimizes platform height to minimize total earthwork
    """

    def __init__(self, dem_layer: QgsRasterLayer, polygon: QgsGeometry, config: dict):
        """
        Initialize earthwork calculator.

        Args:
            dem_layer (QgsRasterLayer): Digital elevation model
            polygon (QgsGeometry): Platform polygon geometry
            config (dict): Configuration parameters:
                - slope_angle: Slope angle in degrees (default: 45°)
                - foundation_diameter: Foundation diameter in meters (optional)
                - foundation_depth: Foundation depth in meters (optional)
                - swell_factor: Soil swell factor (default: 1.25)
                - compaction_factor: Soil compaction factor (default: 0.9)
                - gravel_thickness: Gravel layer thickness (default: 0.5m)
        """
        self.dem_layer = dem_layer
        self.polygon = polygon
        self.config = config
        self.logger = get_plugin_logger()

        # Get raster properties
        self.provider = dem_layer.dataProvider()
        self.pixel_size_x = dem_layer.rasterUnitsPerPixelX()
        self.pixel_size_y = dem_layer.rasterUnitsPerPixelY()
        self.pixel_area = self.pixel_size_x * self.pixel_size_y

        # Configuration
        self.slope_angle = config.get('slope_angle', 45.0)
        self.foundation_diameter = config.get('foundation_diameter', 0)
        self.foundation_depth = config.get('foundation_depth', 0)

        # Calculate slope width from angle
        # At 45°, vertical drop = horizontal distance
        # slope_width = vertical_drop / tan(angle)
        # We'll calculate this dynamically based on actual height differences

    def sample_dem_in_polygon(self, geometry: QgsGeometry, use_vectorized: bool = True) -> np.ndarray:
        """
        Sample DEM values within a polygon.

        Args:
            geometry (QgsGeometry): Polygon to sample
            use_vectorized: Use vectorized GDAL method (default: True, much faster)

        Returns:
            np.ndarray: Array of elevation values (flattened)
        """
        if use_vectorized and GDAL_AVAILABLE:
            return self._sample_dem_vectorized(geometry)
        else:
            return self._sample_dem_legacy(geometry)

    def _sample_dem_vectorized(self, geometry: QgsGeometry) -> np.ndarray:
        """Vectorized DEM sampling using GDAL raster masking (100-1000x faster)."""
        try:
            dem_path = self.dem_layer.source()
            ds = gdal.Open(dem_path, gdal.GA_ReadOnly)
            if ds is None:
                return self._sample_dem_legacy(geometry)

            band = ds.GetRasterBand(1)
            nodata = band.GetNoDataValue()
            geotransform = ds.GetGeoTransform()
            bbox = geometry.boundingBox()

            # Convert bbox to pixel coordinates
            origin_x, pixel_width, _, origin_y, _, pixel_height = geotransform
            x_min_px = int((bbox.xMinimum() - origin_x) / pixel_width)
            x_max_px = int((bbox.xMaximum() - origin_x) / pixel_width) + 1
            y_min_px = int((bbox.yMinimum() - origin_y) / pixel_height)
            y_max_px = int((bbox.yMaximum() - origin_y) / pixel_height) + 1

            x_min_px = max(0, x_min_px)
            y_min_px = max(0, y_min_px)
            x_max_px = min(ds.RasterXSize, x_max_px)
            y_max_px = min(ds.RasterYSize, y_max_px)

            width = x_max_px - x_min_px
            height = y_max_px - y_min_px

            if width <= 0 or height <= 0:
                ds = None
                return np.array([])

            data = band.ReadAsArray(x_min_px, y_min_px, width, height)
            if data is None:
                ds = None
                return self._sample_dem_legacy(geometry)

            # Create mask from polygon
            mem_driver = ogr.GetDriverByName('Memory')
            mem_ds = mem_driver.CreateDataSource('memData')
            mem_layer = mem_ds.CreateLayer('polygon', srs=None, geom_type=ogr.wkbPolygon)

            wkt = geometry.asWkt()
            ogr_geom = ogr.CreateGeometryFromWkt(wkt)
            feature = ogr.Feature(mem_layer.GetLayerDefn())
            feature.SetGeometry(ogr_geom)
            mem_layer.CreateFeature(feature)

            mask_driver = gdal.GetDriverByName('MEM')
            mask_ds = mask_driver.Create('', width, height, 1, gdal.GDT_Byte)

            mask_geotransform = list(geotransform)
            mask_geotransform[0] = origin_x + x_min_px * pixel_width
            mask_geotransform[3] = origin_y + y_min_px * pixel_height
            mask_ds.SetGeoTransform(mask_geotransform)

            mask_band = mask_ds.GetRasterBand(1)
            mask_band.Fill(0)
            gdal.RasterizeLayer(mask_ds, [1], mem_layer, burn_values=[1])

            mask = mask_band.ReadAsArray()
            masked_data = data[mask == 1]

            if nodata is not None:
                masked_data = masked_data[masked_data != nodata]

            ds = None
            mask_ds = None
            mem_ds = None

            return masked_data.astype(float).flatten()

        except Exception as e:
            self.logger.warning(f"Vectorized sampling failed: {e}, using legacy method")
            return self._sample_dem_legacy(geometry)

    def _sample_dem_legacy(self, geometry: QgsGeometry) -> np.ndarray:
        """Legacy DEM sampling using pixel-by-pixel iteration (slow but reliable)."""
        bbox = geometry.boundingBox()

        x_min_px = int((bbox.xMinimum() - self.dem_layer.extent().xMinimum()) / self.pixel_size_x)
        x_max_px = int((bbox.xMaximum() - self.dem_layer.extent().xMinimum()) / self.pixel_size_x) + 1
        y_min_px = int((self.dem_layer.extent().yMaximum() - bbox.yMaximum()) / self.pixel_size_y)
        y_max_px = int((self.dem_layer.extent().yMaximum() - bbox.yMinimum()) / self.pixel_size_y) + 1

        x_min_px = max(0, x_min_px)
        y_min_px = max(0, y_min_px)
        x_max_px = min(self.dem_layer.width(), x_max_px)
        y_max_px = min(self.dem_layer.height(), y_max_px)

        width = x_max_px - x_min_px
        height = y_max_px - y_min_px

        if width <= 0 or height <= 0:
            return np.array([])

        block = self.provider.block(1, bbox, width, height)

        elevations = []
        for row in range(height):
            for col in range(width):
                x = self.dem_layer.extent().xMinimum() + (x_min_px + col) * self.pixel_size_x
                y = self.dem_layer.extent().yMaximum() - (y_min_px + row) * self.pixel_size_y

                point = QgsPointXY(x, y)
                point_geom = QgsGeometry.fromPointXY(point)

                if geometry.contains(point_geom):
                    value = block.value(row, col)
                    if not block.isNoData(row, col) and value is not None:
                        elevations.append(float(value))

        return np.array(elevations, dtype=float)

    def calculate_slope_width(self, max_height_diff: float) -> float:
        """
        Calculate slope width based on maximum height difference and slope angle.

        Args:
            max_height_diff (float): Maximum height difference (meters)

        Returns:
            float: Slope width (meters)
        """
        angle_rad = math.radians(self.slope_angle)
        slope_width = max_height_diff / math.tan(angle_rad)
        return slope_width

    def calculate_scenario(self, height: float,
                          feedback: Optional[QgsProcessingFeedback] = None) -> Dict:
        """
        Calculate earthwork volumes for a specific platform height.

        Args:
            height (float): Platform height (m above sea level)
            feedback (QgsProcessingFeedback): Feedback object (optional)

        Returns:
            Dict: Results containing:
                - platform_height: Platform height
                - terrain_min/max/mean/std: Terrain statistics
                - platform_cut/fill: Cut/fill volumes on platform
                - slope_cut/fill: Cut/fill volumes on slope
                - total_cut/fill: Total volumes
                - total_volume_moved: Sum of cut and fill
                - net_volume: Difference (cut - fill)
        """
        # Sample DEM within platform polygon
        platform_elevations = self.sample_dem_in_polygon(self.polygon)

        if len(platform_elevations) == 0:
            raise ValueError("No DEM data within polygon")

        # Calculate terrain statistics
        terrain_min = float(np.min(platform_elevations))
        terrain_max = float(np.max(platform_elevations))
        terrain_mean = float(np.mean(platform_elevations))
        terrain_std = float(np.std(platform_elevations))

        # Calculate cut/fill on platform
        platform_cut = 0.0
        platform_fill = 0.0

        for elevation in platform_elevations:
            diff = elevation - height
            if diff > 0:  # Cut (existing terrain is higher than platform)
                platform_cut += diff * self.pixel_area
            else:  # Fill (existing terrain is lower than platform)
                platform_fill += abs(diff) * self.pixel_area

        # Calculate slope area
        max_height_diff = max(abs(terrain_max - height), abs(terrain_min - height))
        slope_width = self.calculate_slope_width(max_height_diff)

        # Create buffered polygon for slope
        slope_polygon = self.polygon.buffer(slope_width, 16)

        # Create slope-only polygon (buffer minus platform)
        slope_only = slope_polygon.difference(self.polygon)

        # Sample DEM in slope area
        slope_elevations = self.sample_dem_in_polygon(slope_only)

        # Calculate cut/fill on slope
        # For simplification, we use a linear interpolation from platform edge to natural terrain
        slope_cut = 0.0
        slope_fill = 0.0

        for elevation in slope_elevations:
            # Simplified: assume mid-height between platform and terrain
            # This is an approximation - the actual slope profile is more complex
            avg_height = (height + elevation) / 2.0
            diff = elevation - avg_height

            if diff > 0:
                slope_cut += diff * self.pixel_area
            else:
                slope_fill += abs(diff) * self.pixel_area

        # Calculate totals
        total_cut = platform_cut + slope_cut
        total_fill = platform_fill + slope_fill
        total_volume_moved = total_cut + total_fill
        net_volume = total_cut - total_fill

        # Platform area
        platform_area = self.polygon.area()
        total_area = slope_polygon.area()

        results = {
            'platform_height': round(height, 2),
            'terrain_min': round(terrain_min, 2),
            'terrain_max': round(terrain_max, 2),
            'terrain_mean': round(terrain_mean, 2),
            'terrain_std': round(terrain_std, 2),
            'terrain_range': round(terrain_max - terrain_min, 2),
            'platform_cut': round(platform_cut, 1),
            'platform_fill': round(platform_fill, 1),
            'slope_cut': round(slope_cut, 1),
            'slope_fill': round(slope_fill, 1),
            'total_cut': round(total_cut, 1),
            'total_fill': round(total_fill, 1),
            'total_volume_moved': round(total_volume_moved, 1),
            'net_volume': round(net_volume, 1),
            'platform_area': round(platform_area, 1),
            'total_area': round(total_area, 1),
            'slope_width': round(slope_width, 2)
        }

        return results

    def find_optimum(self, min_height: float, max_height: float, step: float = 0.1,
                    feedback: Optional[QgsProcessingFeedback] = None) -> Tuple[float, Dict]:
        """
        Find optimal platform height that minimizes earthwork.

        Args:
            min_height (float): Minimum height to test (m above sea level)
            max_height (float): Maximum height to test (m above sea level)
            step (float): Height step size (default: 0.1m)
            feedback (QgsProcessingFeedback): Feedback object (optional)

        Returns:
            Tuple[float, Dict]: (optimal_height, results_dict)
        """
        self.logger.info(
            f"Optimizing platform height: {min_height:.1f}m - {max_height:.1f}m "
            f"(step: {step:.2f}m)"
        )

        heights = np.arange(min_height, max_height + step, step)
        num_scenarios = len(heights)

        self.logger.info(f"Testing {num_scenarios} height scenarios")

        if feedback:
            feedback.pushInfo(f"Testing {num_scenarios} height scenarios...")

        best_height = None
        best_volume = float('inf')
        best_results = None

        all_results = []

        for i, height in enumerate(heights):
            if feedback and feedback.isCanceled():
                break

            # Calculate scenario
            try:
                results = self.calculate_scenario(height, feedback)
                all_results.append(results)

                # Check if this is better than current best
                total_volume = results['total_volume_moved']

                if total_volume < best_volume:
                    best_volume = total_volume
                    best_height = height
                    best_results = results
                elif total_volume == best_volume:
                    # Tie-breaker: prefer smaller net volume (balanced cut/fill)
                    if abs(results['net_volume']) < abs(best_results['net_volume']):
                        best_height = height
                        best_results = results

                # Progress update
                if feedback and i % 10 == 0:
                    progress = int((i / num_scenarios) * 100)
                    feedback.setProgress(progress)
                    feedback.pushInfo(
                        f"  {i}/{num_scenarios}: h={height:.1f}m, "
                        f"volume={total_volume:.0f}m³"
                    )

            except Exception as e:
                self.logger.error(f"Error calculating scenario h={height:.1f}m: {e}")
                if feedback:
                    feedback.reportError(f"Error at height {height:.1f}m: {e}", fatalError=False)

        if best_results is None:
            error_msg = (
                f"Keine gültigen Szenarien gefunden!\n"
                f"Höhenbereich: {min_height:.2f} - {max_height:.2f} m ü.NN\n"
                f"Getestete Höhen: {num_scenarios}\n"
                f"Mögliche Ursachen:\n"
                f"  - Suchbereich zu klein\n"
                f"  - DGM-Daten außerhalb des gültigen Bereichs\n"
                f"  - Geometrien nicht korrekt"
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        self.logger.info(
            f"Optimization complete: optimal height = {best_height:.2f}m, "
            f"total volume = {best_volume:.0f}m³"
        )

        if feedback:
            feedback.pushInfo(
                f"\n✓ Optimal height: {best_height:.2f}m "
                f"(total earthwork: {best_volume:.0f}m³)"
            )

        # Add optimization info to results
        best_results['optimization'] = {
            'num_scenarios': num_scenarios,
            'height_range': (min_height, max_height),
            'step': step,
            'all_results': all_results
        }

        return best_height, best_results
