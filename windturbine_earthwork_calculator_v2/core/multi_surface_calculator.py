"""
Multi-Surface Earthwork Calculator

Calculates cut/fill volumes for all surface types in a wind turbine construction site:
- Foundation (Fundamentfläche): Excavation below FOK
- Crane Pad (Kranstellfläche): Planar surface with gravel layer
- Boom Surface (Auslegerfläche): Sloped surface with longitudinal gradient
- Blade Storage (Blattlagerfläche): Planar surface with height offset

Author: Wind Energy Site Planning
Version: 2.0.0 - Multi-Surface Extension
"""

import math
import time
import copy
from typing import Optional, Tuple, Dict, List
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
import multiprocessing as mp

from qgis.core import (
    QgsRasterLayer,
    QgsGeometry,
    QgsPointXY,
    QgsProcessingFeedback,
    QgsRectangle
)

try:
    from osgeo import gdal, ogr, osr
    import tempfile
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False

from .surface_types import (
    MultiSurfaceProject,
    SurfaceType,
    SurfaceCalculationResult,
    MultiSurfaceCalculationResult
)
from .uncertainty import (
    UncertaintyConfig,
    UncertaintyResult,
    UncertaintyAnalysisResult,
    SensitivityResult,
    generate_parameter_samples,
    calculate_sobol_indices,
    TerrainType
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


# ============================================================================
# PARALLEL PROCESSING WORKER FUNCTIONS
# ============================================================================
# These functions must be module-level for pickle serialization

def _calculate_single_height_scenario(height: float, dem_path: str, project_dict: dict,
                                      use_vectorized: bool = True) -> Tuple[float, dict]:
    """
    Worker function to calculate a single height scenario.

    This function runs in a separate process and must be pickle-able.

    Args:
        height: Crane height to test
        dem_path: Path to DEM file
        project_dict: Serialized project configuration
        use_vectorized: Use vectorized sampling

    Returns:
        Tuple of (height, result_dict)
    """
    import traceback

    try:
        # Import inside function to avoid pickling issues
        from qgis.core import QgsRasterLayer, QgsGeometry
        from .surface_types import MultiSurfaceProject, SurfaceConfig, SurfaceType, HeightMode

        # Reconstruct project from dict
        crane_config = SurfaceConfig(
            surface_type=SurfaceType.CRANE_PAD,
            geometry=QgsGeometry.fromWkt(project_dict['crane_wkt']),
            dxf_path=project_dict.get('dxf_path', ''),  # Required parameter
            height_mode=HeightMode.OPTIMIZED,
            metadata=project_dict.get('crane_metadata', {})
        )

        foundation_config = SurfaceConfig(
            surface_type=SurfaceType.FOUNDATION,
            geometry=QgsGeometry.fromWkt(project_dict['foundation_wkt']),
            dxf_path=project_dict.get('dxf_path', ''),  # Required parameter
            height_mode=HeightMode.FIXED,
            height_value=project_dict['fok'],
            metadata=project_dict.get('foundation_metadata', {})
        )

        boom_config = SurfaceConfig(
            surface_type=SurfaceType.BOOM,
            geometry=QgsGeometry.fromWkt(project_dict['boom_wkt']),
            dxf_path=project_dict.get('dxf_path', ''),  # Required parameter
            height_mode=HeightMode.SLOPED,
            slope_longitudinal=project_dict['boom_slope'],
            auto_slope=project_dict['boom_auto_slope'],
            slope_min=project_dict.get('boom_slope_min', 2.0),
            slope_max=project_dict.get('boom_slope_max', 8.0),
            metadata=project_dict.get('boom_metadata', {})
        )

        rotor_config = SurfaceConfig(
            surface_type=SurfaceType.ROTOR_STORAGE,
            geometry=QgsGeometry.fromWkt(project_dict['rotor_wkt']),
            dxf_path=project_dict.get('dxf_path', ''),  # Required parameter
            height_mode=HeightMode.RELATIVE,
            height_reference='crane',
            metadata=project_dict.get('rotor_metadata', {})
        )

        project = MultiSurfaceProject(
            crane_pad=crane_config,
            foundation=foundation_config,
            boom=boom_config,
            rotor_storage=rotor_config,
            fok=project_dict['fok'],
            foundation_depth=project_dict['foundation_depth'],
            gravel_thickness=project_dict['gravel_thickness'],
            rotor_height_offset=project_dict['rotor_height_offset'],
            slope_angle=project_dict['slope_angle'],
            search_range_below_fok=0,
            search_range_above_fok=0,
            search_step=0.1
        )

        # Load DEM
        dem_layer = QgsRasterLayer(dem_path, "DEM")
        if not dem_layer.isValid():
            raise RuntimeError(f"Could not load DEM: {dem_path}")

        # Verify geometries are valid
        if crane_config.geometry.isEmpty() or not crane_config.geometry.isGeosValid():
            raise RuntimeError(f"Invalid crane geometry after WKT reconstruction")
        if foundation_config.geometry.isEmpty() or not foundation_config.geometry.isGeosValid():
            raise RuntimeError(f"Invalid foundation geometry after WKT reconstruction")

        # Create calculator and run single scenario
        calculator = MultiSurfaceCalculator(dem_layer, project)

        # Enable vectorized GDAL in worker processes
        # ProcessPoolExecutor uses separate processes (not threads), so each process
        # has its own GDAL instance - this is safe for parallel execution
        calculator._use_vectorized = use_vectorized

        result = calculator.calculate_scenario(height, feedback=None)

        # Convert result to dict for serialization
        result_dict = result.to_dict()

        return (height, result_dict)

    except Exception as e:
        # Log detailed error information
        import sys
        error_msg = f"Worker error at height {height:.2f}m: {str(e)}\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr, flush=True)  # Print to stderr for debugging
        raise RuntimeError(error_msg) from e


def _calculate_multi_param_scenario(scenario: tuple, dem_path: str, project_dict: dict,
                                     use_vectorized: bool = True) -> Tuple[tuple, dict]:
    """
    Worker function to calculate a multi-parameter scenario.

    This function runs in a separate process and must be pickle-able.

    Args:
        scenario: Tuple of (crane_height, boom_slope, rotor_offset)
        dem_path: Path to DEM file
        project_dict: Serialized project configuration
        use_vectorized: Use vectorized sampling

    Returns:
        Tuple of (scenario, result_dict)
    """
    import traceback

    crane_height, boom_slope, rotor_offset = scenario

    try:
        # Import inside function to avoid pickling issues
        from qgis.core import QgsRasterLayer, QgsGeometry
        from .surface_types import MultiSurfaceProject, SurfaceConfig, SurfaceType, HeightMode

        # Reconstruct project from dict
        crane_config = SurfaceConfig(
            surface_type=SurfaceType.CRANE_PAD,
            geometry=QgsGeometry.fromWkt(project_dict['crane_wkt']),
            dxf_path=project_dict.get('dxf_path', ''),
            height_mode=HeightMode.OPTIMIZED,
            metadata=project_dict.get('crane_metadata', {})
        )

        foundation_config = SurfaceConfig(
            surface_type=SurfaceType.FOUNDATION,
            geometry=QgsGeometry.fromWkt(project_dict['foundation_wkt']),
            dxf_path=project_dict.get('dxf_path', ''),
            height_mode=HeightMode.FIXED,
            height_value=project_dict['fok'],
            metadata=project_dict.get('foundation_metadata', {})
        )

        boom_config = SurfaceConfig(
            surface_type=SurfaceType.BOOM,
            geometry=QgsGeometry.fromWkt(project_dict['boom_wkt']),
            dxf_path=project_dict.get('dxf_path', ''),
            height_mode=HeightMode.SLOPED,
            slope_longitudinal=boom_slope,  # Use scenario slope
            auto_slope=False,  # Disable auto-slope for optimization
            slope_min=project_dict.get('boom_slope_min', 2.0),
            slope_max=project_dict.get('boom_slope_max', 8.0),
            metadata=project_dict.get('boom_metadata', {})
        )

        rotor_config = SurfaceConfig(
            surface_type=SurfaceType.ROTOR_STORAGE,
            geometry=QgsGeometry.fromWkt(project_dict['rotor_wkt']),
            dxf_path=project_dict.get('dxf_path', ''),
            height_mode=HeightMode.RELATIVE,
            height_reference='crane',
            metadata=project_dict.get('rotor_metadata', {})
        )

        project = MultiSurfaceProject(
            crane_pad=crane_config,
            foundation=foundation_config,
            boom=boom_config,
            rotor_storage=rotor_config,
            fok=project_dict['fok'],
            foundation_depth=project_dict['foundation_depth'],
            gravel_thickness=project_dict['gravel_thickness'],
            rotor_height_offset=rotor_offset,  # Use scenario offset
            slope_angle=project_dict['slope_angle'],
            search_range_below_fok=0,
            search_range_above_fok=0,
            search_step=0.1
        )

        # Load DEM
        dem_layer = QgsRasterLayer(dem_path, "DEM")
        if not dem_layer.isValid():
            raise RuntimeError(f"Could not load DEM: {dem_path}")

        # Create calculator and run scenario
        calculator = MultiSurfaceCalculator(dem_layer, project)
        calculator._use_vectorized = use_vectorized

        result = calculator.calculate_scenario(
            crane_height,
            feedback=None,
            boom_slope_percent=boom_slope,
            rotor_height_offset=rotor_offset
        )

        # Convert result to dict for serialization
        result_dict = result.to_dict()

        return (scenario, result_dict)

    except Exception as e:
        import sys
        error_msg = (f"Worker error at scenario h={crane_height:.2f}m, "
                     f"slope={boom_slope:.1f}%, offset={rotor_offset:.2f}m: "
                     f"{str(e)}\n{traceback.format_exc()}")
        print(error_msg, file=sys.stderr, flush=True)
        raise RuntimeError(error_msg) from e


def _calculate_mc_sample_parallel(sample_config: dict, dem_path: str, project_dict: dict,
                                   use_vectorized: bool = True) -> dict:
    """
    Worker function to calculate a single Monte Carlo sample in parallel.

    This function runs in a separate process and must be pickle-able.

    Args:
        sample_config: Dictionary with perturbed parameter values
        dem_path: Path to DEM file
        project_dict: Serialized project configuration
        use_vectorized: Use vectorized sampling

    Returns:
        Dictionary with results from this sample
    """
    import traceback

    try:
        # Import inside function to avoid pickling issues
        from qgis.core import QgsRasterLayer, QgsGeometry
        from .surface_types import MultiSurfaceProject, SurfaceConfig, SurfaceType, HeightMode

        # Reconstruct project from dict with perturbed parameters
        crane_config = SurfaceConfig(
            surface_type=SurfaceType.CRANE_PAD,
            geometry=QgsGeometry.fromWkt(project_dict['crane_wkt']),
            dxf_path=project_dict.get('dxf_path', ''),
            height_mode=HeightMode.OPTIMIZED,
            metadata=project_dict.get('crane_metadata', {})
        )

        foundation_config = SurfaceConfig(
            surface_type=SurfaceType.FOUNDATION,
            geometry=QgsGeometry.fromWkt(project_dict['foundation_wkt']),
            dxf_path=project_dict.get('dxf_path', ''),
            height_mode=HeightMode.FIXED,
            height_value=sample_config['fok'],  # Use perturbed FOK
            metadata=project_dict.get('foundation_metadata', {})
        )

        boom_config = None
        if project_dict.get('boom_wkt'):
            boom_config = SurfaceConfig(
                surface_type=SurfaceType.BOOM,
                geometry=QgsGeometry.fromWkt(project_dict['boom_wkt']),
                dxf_path=project_dict.get('dxf_path', ''),
                height_mode=HeightMode.SLOPED,
                slope_longitudinal=project_dict['boom_slope'],
                auto_slope=project_dict['boom_auto_slope'],
                slope_min=project_dict.get('boom_slope_min', 2.0),
                slope_max=project_dict.get('boom_slope_max', 8.0),
                metadata=project_dict.get('boom_metadata', {})
            )

        rotor_config = None
        if project_dict.get('rotor_wkt'):
            rotor_config = SurfaceConfig(
                surface_type=SurfaceType.ROTOR_STORAGE,
                geometry=QgsGeometry.fromWkt(project_dict['rotor_wkt']),
                dxf_path=project_dict.get('dxf_path', ''),
                height_mode=HeightMode.RELATIVE,
                height_reference='crane',
                metadata=project_dict.get('rotor_metadata', {})
            )

        project = MultiSurfaceProject(
            crane_pad=crane_config,
            foundation=foundation_config,
            boom=boom_config,
            rotor_storage=rotor_config,
            fok=sample_config['fok'],  # Use perturbed FOK
            foundation_depth=sample_config['foundation_depth'],  # Perturbed
            gravel_thickness=sample_config['gravel_thickness'],  # Perturbed
            rotor_height_offset=project_dict['rotor_height_offset'],
            slope_angle=sample_config['slope_angle'],  # Perturbed
            search_range_below_fok=project_dict.get('search_range_below_fok', 2.0),
            search_range_above_fok=project_dict.get('search_range_above_fok', 2.0),
            search_step=project_dict.get('search_step', 0.1)
        )

        # Load DEM
        dem_layer = QgsRasterLayer(dem_path, "DEM")
        if not dem_layer.isValid():
            raise RuntimeError(f"Could not load DEM: {dem_path}")

        # Create calculator and run optimization
        calculator = MultiSurfaceCalculator(dem_layer, project)
        calculator._use_vectorized = use_vectorized

        # Store DEM noise for this sample
        calculator._dem_noise = sample_config.get('dem_noise', 0.0)

        # Run optimization (without parallel to avoid nested parallelism)
        optimal_height, result = calculator.find_optimum(
            feedback=None,
            use_parallel=False
        )

        # Apply boom slope and rotor offset noise to result
        boom_slope = result.boom_slope_percent + sample_config.get('boom_slope_noise', 0.0)
        rotor_offset = result.rotor_height_offset_optimized + sample_config.get('rotor_offset_noise', 0.0)

        return {
            'optimal_height': optimal_height,
            'total_cut': result.total_cut,
            'total_fill': result.total_fill,
            'net_volume': result.net_volume,
            'total_volume_moved': result.total_volume_moved,
            'boom_slope': boom_slope,
            'rotor_offset': rotor_offset,
            'fok': sample_config['fok'],
            'slope_angle': sample_config['slope_angle'],
            'foundation_depth': sample_config['foundation_depth'],
            'gravel_thickness': sample_config['gravel_thickness'],
        }

    except Exception as e:
        import sys
        error_msg = (f"MC worker error: {str(e)}\n{traceback.format_exc()}")
        print(error_msg, file=sys.stderr, flush=True)
        raise RuntimeError(error_msg) from e


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

        # Vectorization setting (can be overridden)
        self._use_vectorized = True

        # Pre-calculate connection edges (for boom surface)
        self.boom_connection_edge = None
        self.boom_slope_direction = None
        self.rotor_connection_edge = None

        self._prepare_surface_relationships()

    def _prepare_surface_relationships(self):
        """Pre-calculate spatial relationships between surfaces."""
        # Find connection edge between crane pad and boom (if boom exists)
        if self.project.boom is not None:
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
        else:
            self.logger.info("No boom surface configured (optional)")

        # Find connection edge between crane pad and rotor storage (if rotor exists)
        if self.project.rotor_storage is not None:
            rotor_edge, rotor_length = find_connection_edge(
                self.project.crane_pad.geometry,
                self.project.rotor_storage.geometry
            )

            if rotor_length > 0:
                self.rotor_connection_edge = rotor_edge
                self.logger.info(f"Rotor storage connection edge: {rotor_length:.1f}m")
            else:
                self.logger.warning("No connection edge found between crane pad and rotor storage")
        else:
            self.logger.info("No rotor storage surface configured (optional)")

    def detect_boom_slope_direction(self) -> tuple[float, float]:
        """
        Detect optimal boom slope direction based on terrain.

        Analyzes terrain in boom area to determine if slope should be
        positive (upward) or negative (downward).

        Returns:
            Tuple of (slope_min, slope_max) in percent
            - If terrain slopes down: (negative, 0) e.g. (-4.0, 0.0)
            - If terrain slopes up: (0, positive) e.g. (0.0, 4.0)
        """
        max_slope = self.project.boom_slope_max

        # Check if boom surface exists
        if self.project.boom is None:
            self.logger.warning("No boom surface configured, returning zero slope")
            return (0.0, 0.0)

        if self.boom_connection_edge is None or self.boom_connection_edge.isEmpty():
            self.logger.warning("No boom connection edge for slope direction detection, using full range")
            return (-max_slope, max_slope)

        if self.boom_slope_direction is None:
            self.logger.warning("No boom slope direction calculated, using full range")
            return (-max_slope, max_slope)

        # Sample terrain in boom area
        samples = self.sample_dem_with_positions(self.project.boom.geometry)

        if len(samples) < 5:
            self.logger.warning("Insufficient samples for slope direction detection, using full range")
            return (-max_slope, max_slope)

        # Calculate terrain slope in boom direction
        distances = []
        elevations = []

        for point, elevation in samples:
            distance = calculate_distance_from_edge(
                point,
                self.boom_connection_edge,
                self.boom_slope_direction
            )
            if distance > 0:  # Only points in slope direction
                distances.append(distance)
                elevations.append(elevation)

        if len(elevations) < 5:
            self.logger.warning("Insufficient valid samples for slope direction detection, using full range")
            return (-max_slope, max_slope)

        # Calculate average terrain slope
        terrain_slope = calculate_terrain_slope(elevations, distances)

        max_slope = self.project.boom_slope_max

        if terrain_slope < -0.5:
            # Terrain slopes down significantly: allow negative slopes
            slope_range = (-max_slope, 0.0)
            self.logger.info(
                f"Boom terrain slopes DOWN ({terrain_slope:.1f}%), "
                f"optimizing in range [{slope_range[0]:.1f}%, {slope_range[1]:.1f}%]"
            )
        elif terrain_slope > 0.5:
            # Terrain slopes up significantly: allow positive slopes
            slope_range = (0.0, max_slope)
            self.logger.info(
                f"Boom terrain slopes UP ({terrain_slope:.1f}%), "
                f"optimizing in range [{slope_range[0]:.1f}%, {slope_range[1]:.1f}%]"
            )
        else:
            # Terrain relatively flat: allow both directions
            slope_range = (-max_slope, max_slope)
            self.logger.info(
                f"Boom terrain relatively FLAT ({terrain_slope:.1f}%), "
                f"optimizing in range [{slope_range[0]:.1f}%, {slope_range[1]:.1f}%]"
            )

        return slope_range

    def _create_project_dict(self) -> dict:
        """
        Create serializable dictionary from project configuration.

        This is used to pass project data to worker processes.

        Returns:
            Dictionary with all project parameters
        """
        return {
            'crane_wkt': self.project.crane_pad.geometry.asWkt(),
            'foundation_wkt': self.project.foundation.geometry.asWkt(),
            'boom_wkt': self.project.boom.geometry.asWkt() if self.project.boom else None,
            'rotor_wkt': self.project.rotor_storage.geometry.asWkt() if self.project.rotor_storage else None,
            'dxf_path': getattr(self.project.crane_pad, 'dxf_path', ''),
            'fok': self.project.fok,
            'foundation_depth': self.project.foundation_depth,
            'gravel_thickness': self.project.gravel_thickness,
            'rotor_height_offset': self.project.rotor_height_offset,
            'slope_angle': self.project.slope_angle,
            'boom_slope': self.project.boom.slope_longitudinal if self.project.boom else 0.0,
            'boom_auto_slope': self.project.boom.auto_slope if self.project.boom else False,
            'boom_slope_min': getattr(self.project.boom, 'slope_min', 2.0) if self.project.boom else 2.0,
            'boom_slope_max': getattr(self.project.boom, 'slope_max', 8.0) if self.project.boom else 8.0,
            'crane_metadata': self.project.crane_pad.metadata,
            'foundation_metadata': self.project.foundation.metadata,
            'boom_metadata': self.project.boom.metadata if self.project.boom else {},
            'rotor_metadata': self.project.rotor_storage.metadata if self.project.rotor_storage else {},
        }

    def sample_dem_in_polygon(self, geometry: QgsGeometry, use_vectorized: bool = None) -> np.ndarray:
        """
        Sample DEM values within a polygon.

        Args:
            geometry: Polygon to sample
            use_vectorized: Use vectorized GDAL method (None=use instance setting)

        Returns:
            Array of elevation values (flattened)
        """
        if use_vectorized is None:
            use_vectorized = self._use_vectorized

        if use_vectorized and GDAL_AVAILABLE:
            return self._sample_dem_vectorized(geometry)
        else:
            return self._sample_dem_legacy(geometry)

    def _sample_dem_vectorized(self, geometry: QgsGeometry) -> np.ndarray:
        """
        Vectorized DEM sampling using GDAL raster masking.

        This method is 100-1000x faster than the legacy pixel-by-pixel approach.

        Args:
            geometry: Polygon to sample

        Returns:
            Array of elevation values (flattened)
        """
        try:
            # Get DEM path
            dem_path = self.dem_layer.source()

            # Open raster with GDAL
            ds = gdal.Open(dem_path, gdal.GA_ReadOnly)
            if ds is None:
                self.logger.warning("Could not open DEM with GDAL, falling back to legacy method")
                return self._sample_dem_legacy(geometry)

            band = ds.GetRasterBand(1)
            nodata = band.GetNoDataValue()
            geotransform = ds.GetGeoTransform()

            # Get geometry bounding box
            bbox = geometry.boundingBox()

            # Convert bbox to pixel coordinates using standard GDAL formula
            # Geotransform: [origin_x, pixel_width, 0, origin_y, 0, pixel_height]
            # pixel_height is typically negative (Y axis goes down in raster)
            origin_x, pixel_width, _, origin_y, _, pixel_height = geotransform

            # Standard GDAL pixel coordinate calculation
            # col = (x - origin_x) / pixel_width
            # row = (y - origin_y) / pixel_height
            x_min_px = int((bbox.xMinimum() - origin_x) / pixel_width)
            x_max_px = int((bbox.xMaximum() - origin_x) / pixel_width) + 1

            # For Y: when pixel_height is negative, larger Y gives smaller row
            y_min_px = int((bbox.yMaximum() - origin_y) / pixel_height)  # Note: yMaximum for min row
            y_max_px = int((bbox.yMinimum() - origin_y) / pixel_height) + 1  # Note: yMinimum for max row

            # Ensure min < max (in case of rounding issues)
            if y_min_px > y_max_px:
                y_min_px, y_max_px = y_max_px, y_min_px

            # Clamp to raster bounds
            x_min_px = max(0, x_min_px)
            y_min_px = max(0, y_min_px)
            x_max_px = min(ds.RasterXSize, x_max_px)
            y_max_px = min(ds.RasterYSize, y_max_px)

            # Read raster window
            width = x_max_px - x_min_px
            height = y_max_px - y_min_px

            if width <= 0 or height <= 0:
                ds = None
                self.logger.warning(
                    f"Invalid raster window: width={width}, height={height}, "
                    f"x_px=[{x_min_px},{x_max_px}], y_px=[{y_min_px},{y_max_px}], "
                    f"pixel_height={pixel_height}, falling back to legacy method"
                )
                return self._sample_dem_legacy(geometry)

            # Read elevation data
            data = band.ReadAsArray(x_min_px, y_min_px, width, height)

            if data is None:
                ds = None
                self.logger.warning("Could not read raster data, falling back to legacy method")
                return self._sample_dem_legacy(geometry)

            # Create temporary in-memory vector for polygon
            mem_driver = ogr.GetDriverByName('Memory')
            mem_ds = mem_driver.CreateDataSource('memData')
            mem_layer = mem_ds.CreateLayer('polygon', srs=None, geom_type=ogr.wkbPolygon)

            # Convert QgsGeometry to OGR
            wkt = geometry.asWkt()
            ogr_geom = ogr.CreateGeometryFromWkt(wkt)
            feature = ogr.Feature(mem_layer.GetLayerDefn())
            feature.SetGeometry(ogr_geom)
            mem_layer.CreateFeature(feature)

            # Create temporary in-memory raster for mask
            mask_driver = gdal.GetDriverByName('MEM')
            mask_ds = mask_driver.Create('', width, height, 1, gdal.GDT_Byte)

            # Set geotransform for mask (adjusted to window)
            # Standard GDAL: x = origin_x + col * pixel_width
            #                y = origin_y + row * pixel_height
            mask_geotransform = list(geotransform)
            mask_geotransform[0] = origin_x + x_min_px * pixel_width
            mask_geotransform[3] = origin_y + y_min_px * pixel_height  # Works for both positive and negative pixel_height
            mask_ds.SetGeoTransform(mask_geotransform)

            # Rasterize polygon to mask
            mask_band = mask_ds.GetRasterBand(1)
            mask_band.Fill(0)
            gdal.RasterizeLayer(mask_ds, [1], mem_layer, burn_values=[1])

            # Read mask
            mask = mask_band.ReadAsArray()

            # Apply mask to elevation data
            masked_data = data[mask == 1]

            # Filter nodata values
            if nodata is not None:
                masked_data = masked_data[masked_data != nodata]

            # Cleanup
            ds = None
            mask_ds = None
            mem_ds = None

            # If vectorized method returned no data, fall back to legacy
            if len(masked_data) == 0:
                self.logger.warning(
                    f"Vectorized sampling returned no data (mask sum={np.sum(mask)}), "
                    f"falling back to legacy method"
                )
                return self._sample_dem_legacy(geometry)

            return masked_data.astype(float).flatten()

        except Exception as e:
            self.logger.warning(f"Vectorized sampling failed: {e}, falling back to legacy method")
            return self._sample_dem_legacy(geometry)

    def _sample_dem_legacy(self, geometry: QgsGeometry) -> np.ndarray:
        """
        Legacy DEM sampling using pixel-by-pixel iteration.

        This method is slow but guaranteed to work.

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

        # Create pixel-aligned extent for block reading
        # This is critical: provider.block() needs the actual extent that corresponds
        # to the pixel coordinates we calculated
        dem_extent = self.dem_layer.extent()
        block_x_min = dem_extent.xMinimum() + x_min_px * self.pixel_size_x
        block_x_max = dem_extent.xMinimum() + x_max_px * self.pixel_size_x
        block_y_max = dem_extent.yMaximum() - y_min_px * self.pixel_size_y
        block_y_min = dem_extent.yMaximum() - y_max_px * self.pixel_size_y

        block_extent = QgsRectangle(block_x_min, block_y_min, block_x_max, block_y_max)

        # Read raster block
        block = self.provider.block(1, block_extent, width, height)

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

        # Create pixel-aligned extent for block reading
        dem_extent = self.dem_layer.extent()
        block_x_min = dem_extent.xMinimum() + x_min_px * self.pixel_size_x
        block_x_max = dem_extent.xMinimum() + x_max_px * self.pixel_size_x
        block_y_max = dem_extent.yMaximum() - y_min_px * self.pixel_size_y
        block_y_min = dem_extent.yMaximum() - y_max_px * self.pixel_size_y

        block_extent = QgsRectangle(block_x_min, block_y_min, block_x_max, block_y_max)

        # Read raster block
        block = self.provider.block(1, block_extent, width, height)

        samples = []
        for row in range(height):
            for col in range(width):
                # Calculate world coordinates
                x = dem_extent.xMinimum() + (x_min_px + col) * self.pixel_size_x
                y = dem_extent.yMaximum() - (y_min_px + row) * self.pixel_size_y

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
                'foundation_depth': round(self.project.foundation_depth, 2),
                'planum_height': round(foundation_bottom, 2)  # Foundation bottom is the planum
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
            # Add debugging information
            geom_bbox = self.project.crane_pad.geometry.boundingBox()
            dem_extent = self.dem_layer.extent()
            error_msg = (
                f"No DEM data in crane pad area. "
                f"Geometry bbox: {geom_bbox.toString()}, "
                f"DEM extent: {dem_extent.toString()}, "
                f"DEM valid: {self.dem_layer.isValid()}, "
                f"DEM source: {self.dem_layer.source()}"
            )
            raise ValueError(error_msg)

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

    def _calculate_boom_surface(self, crane_height: float,
                                boom_slope_percent: Optional[float] = None) -> SurfaceCalculationResult:
        """
        Calculate boom surface earthwork.

        The boom surface has a longitudinal slope, connecting to crane pad at
        crane_height and sloping downward.

        Args:
            crane_height: Crane pad height (connection edge is at this height)
            boom_slope_percent: Optional slope override (if None, uses project default or auto-slope)

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
        if boom_slope_percent is not None:
            # Use provided slope (from optimization)
            slope_percent = boom_slope_percent
        else:
            # Use project default
            slope_percent = self.project.boom.slope_longitudinal

        # If auto-slope is enabled AND no explicit slope provided, try to match terrain
        if self.project.boom.auto_slope and boom_slope_percent is None:
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
                'auto_slope': self.project.boom.auto_slope,
                'slope_width': round(slope_width, 2),
                'planum_height': round(crane_height - 50 * slope_percent / 100, 2)  # Estimated far end height
            }
        )

    def _calculate_rotor_storage(self, crane_height: float,
                                 rotor_height_offset: Optional[float] = None) -> SurfaceCalculationResult:
        """
        Calculate rotor storage earthwork with holm logic.

        Special logic:
        - If terrain is ABOVE rotor height: excavate entire area (cut)
        - If terrain is BELOW rotor height: only fill at holm positions (not entire area)

        Args:
            crane_height: Crane pad height
            rotor_height_offset: Optional height offset override (if None, uses project default)

        Returns:
            Calculation result for rotor storage
        """
        # Rotor storage height
        if rotor_height_offset is not None:
            rotor_height = crane_height + rotor_height_offset
        else:
            rotor_height = crane_height + self.project.rotor_height_offset

        # Sample terrain with positions
        samples = self.sample_dem_with_positions(self.project.rotor_storage.geometry)

        if len(samples) == 0:
            self.logger.warning("No DEM data in rotor storage area")
            return SurfaceCalculationResult(
                surface_type=SurfaceType.ROTOR_STORAGE,
                target_height=rotor_height,
                cut_volume=0.0,
                fill_volume=0.0,
                platform_area=0.0
            )

        elevations_only = [elev for _, elev in samples]
        terrain_min = float(np.min(elevations_only))
        terrain_max = float(np.max(elevations_only))
        terrain_mean = float(np.mean(elevations_only))

        # Calculate cut/fill with holm logic
        cut_volume = 0.0
        fill_volume = 0.0
        holm_fill_volume = 0.0

        # Check if holms are defined
        has_holms = (self.project.rotor_holms is not None and
                     len(self.project.rotor_holms) > 0)

        for point, elevation in samples:
            diff = elevation - rotor_height

            if diff > 0:
                # Terrain ABOVE target: excavate (cut)
                cut_volume += diff * self.pixel_area
            else:
                # Terrain BELOW target
                if has_holms:
                    # Only fill if point is within a holm
                    point_geom = QgsGeometry.fromPointXY(point)
                    is_in_holm = any(holm.contains(point_geom) for holm in self.project.rotor_holms)

                    if is_in_holm:
                        holm_fill_volume += abs(diff) * self.pixel_area
                else:
                    # No holms defined: fill entire area (old behavior)
                    fill_volume += abs(diff) * self.pixel_area

        # Total fill is either holm fill or area fill
        total_fill = holm_fill_volume if has_holms else fill_volume

        # Calculate slope area (only for cut areas)
        max_height_diff = max(abs(terrain_max - rotor_height), abs(terrain_min - rotor_height))
        slope_width = self.calculate_slope_width(max_height_diff)

        slope_polygon = self.project.rotor_storage.geometry.buffer(slope_width, 16)
        slope_only = slope_polygon.difference(self.project.rotor_storage.geometry)
        slope_samples = self.sample_dem_with_positions(slope_only)

        slope_cut = 0.0
        slope_fill = 0.0

        for point, elevation in slope_samples:
            avg_height = (rotor_height + elevation) / 2.0
            diff = elevation - avg_height

            if diff > 0:
                slope_cut += diff * self.pixel_area
            else:
                slope_fill += abs(diff) * self.pixel_area

        total_cut = cut_volume + slope_cut
        total_fill_with_slope = total_fill + slope_fill

        area = self.project.rotor_storage.geometry.area()
        total_area = slope_polygon.area()

        holm_info = ""
        if has_holms:
            holm_area = sum(holm.area() for holm in self.project.rotor_holms)
            holm_info = f", holm_fill={holm_fill_volume:.1f}m³ (holm_area={holm_area:.1f}m²)"

        self.logger.info(
            f"Rotor storage @ {rotor_height:.2f}m: cut={total_cut:.1f}m³, "
            f"fill={total_fill_with_slope:.1f}m³, area={area:.1f}m²{holm_info}"
        )

        return SurfaceCalculationResult(
            surface_type=SurfaceType.ROTOR_STORAGE,
            target_height=rotor_height,
            cut_volume=total_cut,
            fill_volume=total_fill_with_slope,
            platform_area=area,
            slope_area=total_area - area,
            total_area=total_area,
            terrain_min=terrain_min,
            terrain_max=terrain_max,
            terrain_mean=terrain_mean,
            additional_data={
                'height_offset_from_crane': round(rotor_height_offset if rotor_height_offset is not None else self.project.rotor_height_offset, 2),
                'holm_fill_volume': round(holm_fill_volume, 1) if has_holms else 0.0,
                'has_holms': has_holms,
                'slope_width': round(slope_width, 2),
                'planum_height': round(rotor_height, 2)  # Rotor storage has flat target height
            }
        )

    def calculate_scenario(self, crane_height: float,
                          feedback: Optional[QgsProcessingFeedback] = None,
                          boom_slope_percent: Optional[float] = None,
                          rotor_height_offset: Optional[float] = None) -> MultiSurfaceCalculationResult:
        """
        Calculate earthwork for all surfaces at a specific crane pad height.

        Args:
            crane_height: Crane pad height (m ü.NN)
            feedback: Optional feedback object
            boom_slope_percent: Optional boom slope override (if None, uses project default)
            rotor_height_offset: Optional rotor height offset override (if None, uses project default)

        Returns:
            Complete multi-surface calculation result
        """
        # Use provided parameters or fall back to project defaults
        if boom_slope_percent is None and self.project.boom is not None:
            boom_slope_percent = self.project.boom.slope_longitudinal
        if rotor_height_offset is None:
            rotor_height_offset = self.project.rotor_height_offset

        # Calculate each surface
        foundation_result = self._calculate_foundation()
        crane_result = self._calculate_crane_pad(crane_height)

        # Calculate optional surfaces
        boom_result = None
        if self.project.boom is not None:
            boom_result = self._calculate_boom_surface(crane_height, boom_slope_percent or 0.0)

        rotor_result = None
        if self.project.rotor_storage is not None:
            rotor_result = self._calculate_rotor_storage(crane_height, rotor_height_offset)

        # Calculate gravel fill (external material)
        gravel_volume = self.project.crane_pad.geometry.area() * self.project.gravel_thickness

        # Compile results
        surface_results = {
            SurfaceType.FOUNDATION: foundation_result,
            SurfaceType.CRANE_PAD: crane_result,
        }

        if boom_result is not None:
            surface_results[SurfaceType.BOOM] = boom_result
        if rotor_result is not None:
            surface_results[SurfaceType.ROTOR_STORAGE] = rotor_result

        result = MultiSurfaceCalculationResult(
            crane_height=crane_height,
            fok=self.project.fok,
            surface_results=surface_results,
            gravel_fill_external=gravel_volume,
            boom_slope_percent=boom_slope_percent,
            rotor_height_offset_optimized=rotor_height_offset
        )

        if feedback:
            feedback.pushInfo(
                f"  h={crane_height:.2f}m, boom={boom_slope_percent:+.1f}%, rotor={rotor_height_offset:+.2f}m: "
                f"cut={result.total_cut:.0f}m³, fill={result.total_fill:.0f}m³, "
                f"net={result.net_volume:+.0f}m³, gravel={gravel_volume:.0f}m³"
            )

        return result

    def find_optimum(self, feedback: Optional[QgsProcessingFeedback] = None,
                    use_parallel: bool = True, max_workers: int = None) -> Tuple[float, MultiSurfaceCalculationResult]:
        """
        Find optimal parameters that minimize net earthwork volume.

        Multi-parameter optimization:
        - Crane pad height
        - Boom slope (if enabled)
        - Rotor height offset (if enabled)

        Uses two-stage optimization (coarse + fine) for efficiency.

        Args:
            feedback: Optional feedback object
            use_parallel: Use parallel processing (default: True)
            max_workers: Maximum number of parallel workers (None=auto-detect)

        Returns:
            Tuple of (optimal_crane_height, results)
        """
        # Check if multi-parameter optimization is enabled
        optimize_boom = self.project.boom_slope_optimize
        optimize_rotor = self.project.rotor_height_optimize
        optimize_for_net = self.project.optimize_for_net_earthwork

        if not optimize_boom and not optimize_rotor:
            # Simple single-parameter optimization (old behavior)
            self.logger.info("Single-parameter optimization (crane height only)")
            return self._find_optimum_single_parameter(feedback, use_parallel, max_workers)
        else:
            # Multi-parameter optimization
            self.logger.info(
                f"Multi-parameter optimization: "
                f"crane_height=YES, boom_slope={optimize_boom}, rotor_height={optimize_rotor}, "
                f"optimize_for={'NET' if optimize_for_net else 'TOTAL'}"
            )
            return self._find_optimum_multi_parameter(feedback, use_parallel, max_workers)

    def _find_optimum_multi_parameter(self, feedback: Optional[QgsProcessingFeedback],
                                      use_parallel: bool, max_workers: int) -> Tuple[float, MultiSurfaceCalculationResult]:
        """
        Multi-parameter optimization with two-stage search (coarse + fine).

        Optimizes:
        - Crane pad height
        - Boom slope (if enabled)
        - Rotor height offset (if enabled)

        Returns:
            Tuple of (optimal_crane_height, best_result)
        """
        # Detect boom slope direction (only if boom surface exists)
        if self.project.boom is not None and self.project.boom_slope_optimize:
            boom_slope_min, boom_slope_max = self.detect_boom_slope_direction()
        elif self.project.boom is not None:
            boom_slope_min = boom_slope_max = self.project.boom.slope_longitudinal
        else:
            boom_slope_min = boom_slope_max = 0.0

        # === STAGE 1: COARSE SEARCH ===
        self.logger.info("=" * 60)
        self.logger.info("STAGE 1: COARSE SEARCH")
        self.logger.info("=" * 60)

        if feedback:
            feedback.pushInfo("\n" + "=" * 60)
            feedback.pushInfo("STAGE 1: COARSE SEARCH")
            feedback.pushInfo("=" * 60)

        # Crane height range
        height_min = self.project.search_min_height
        height_max = self.project.search_max_height
        height_step_coarse = 1.0  # 1m steps for coarse search

        # Boom slope range (only if boom surface exists)
        if self.project.boom is not None and self.project.boom_slope_optimize:
            slope_step_coarse = self.project.boom_slope_step_coarse
            boom_slopes_coarse = np.arange(boom_slope_min, boom_slope_max + slope_step_coarse, slope_step_coarse)
        elif self.project.boom is not None:
            boom_slopes_coarse = [self.project.boom.slope_longitudinal]
        else:
            boom_slopes_coarse = [0.0]  # No boom surface

        # Rotor height range (only if rotor storage exists)
        if self.project.rotor_storage is not None and self.project.rotor_height_optimize:
            rotor_offset_min = -self.project.rotor_height_offset_max
            rotor_offset_max = self.project.rotor_height_offset_max
            rotor_step_coarse = self.project.rotor_height_step_coarse
            rotor_offsets_coarse = np.arange(rotor_offset_min, rotor_offset_max + rotor_step_coarse, rotor_step_coarse)
        elif self.project.rotor_storage is not None:
            rotor_offsets_coarse = [self.project.rotor_height_offset]
        else:
            rotor_offsets_coarse = [0.0]  # No rotor storage

        heights_coarse = np.arange(height_min, height_max + height_step_coarse, height_step_coarse)

        num_coarse = len(heights_coarse) * len(boom_slopes_coarse) * len(rotor_offsets_coarse)

        self.logger.info(
            f"Coarse search: {len(heights_coarse)} heights × "
            f"{len(boom_slopes_coarse)} boom slopes × "
            f"{len(rotor_offsets_coarse)} rotor offsets = {num_coarse} scenarios"
        )

        if feedback:
            feedback.pushInfo(
                f"Testing {num_coarse} parameter combinations (coarse search)..."
            )

        best_coarse_volume = float('inf')
        best_coarse_params = None
        best_coarse_result = None

        # Build scenario list for parallel execution
        coarse_scenarios = [
            (float(crane_h), float(boom_slope), float(rotor_offset))
            for crane_h in heights_coarse
            for boom_slope in boom_slopes_coarse
            for rotor_offset in rotor_offsets_coarse
        ]

        # Decide parallel vs sequential based on scenario count and use_parallel flag
        if use_parallel and num_coarse >= 20:
            # Parallel execution
            self.logger.info(f"Running coarse search in parallel ({max_workers} workers)")

            # Prepare project dict for serialization
            project_dict = self._create_project_dict()
            dem_path = self.dem_layer.source()

            if max_workers is None:
                max_workers = max(1, mp.cpu_count() - 1)

            completed = 0
            failed = 0

            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                worker_func = partial(
                    _calculate_multi_param_scenario,
                    dem_path=dem_path,
                    project_dict=project_dict,
                    use_vectorized=self._use_vectorized
                )

                futures = {
                    executor.submit(worker_func, scenario): scenario
                    for scenario in coarse_scenarios
                }

                for future in as_completed(futures):
                    scenario = futures[future]
                    completed += 1

                    if feedback and feedback.isCanceled():
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

                    try:
                        _, result_dict = future.result()

                        from .surface_types import MultiSurfaceCalculationResult
                        result = MultiSurfaceCalculationResult.from_dict(result_dict)

                        # Choose optimization metric
                        if self.project.optimize_for_net_earthwork:
                            metric_volume = abs(result.net_volume)
                        else:
                            metric_volume = result.total_volume_moved

                        if metric_volume < best_coarse_volume:
                            best_coarse_volume = metric_volume
                            best_coarse_params = scenario
                            best_coarse_result = result

                        # Progress update
                        if feedback and completed % 50 == 0:
                            progress = int((completed / num_coarse) * 50)
                            feedback.setProgress(progress)
                            if best_coarse_params:
                                feedback.pushInfo(
                                    f"  Coarse: {completed}/{num_coarse} - "
                                    f"Best: h={best_coarse_params[0]:.1f}m, "
                                    f"slope={best_coarse_params[1]:+.1f}%, "
                                    f"rotor={best_coarse_params[2]:+.2f}m"
                                )

                    except Exception as e:
                        failed += 1
                        self.logger.error(f"Error in coarse scenario {scenario}: {e}")

            self.logger.info(f"Coarse search: {completed - failed} successful, {failed} failed")

        else:
            # Sequential execution (fallback or small scenario count)
            self.logger.info("Running coarse search sequentially")
            scenario_count = 0
            first_error = None

            for crane_h, boom_slope, rotor_offset in coarse_scenarios:
                if feedback and feedback.isCanceled():
                    break

                try:
                    result = self.calculate_scenario(
                        crane_height=crane_h,
                        feedback=None,
                        boom_slope_percent=boom_slope,
                        rotor_height_offset=rotor_offset
                    )

                    if self.project.optimize_for_net_earthwork:
                        metric_volume = abs(result.net_volume)
                    else:
                        metric_volume = result.total_volume_moved

                    if metric_volume < best_coarse_volume:
                        best_coarse_volume = metric_volume
                        best_coarse_params = (crane_h, boom_slope, rotor_offset)
                        best_coarse_result = result

                    scenario_count += 1

                    if feedback and scenario_count % 50 == 0:
                        progress = int((scenario_count / num_coarse) * 50)
                        feedback.setProgress(progress)
                        if best_coarse_params:
                            feedback.pushInfo(
                                f"  Coarse: {scenario_count}/{num_coarse} - "
                                f"Best: h={best_coarse_params[0]:.1f}m"
                            )

                except Exception as e:
                    self.logger.error(f"Error in coarse search: {e}")
                    if first_error is None:
                        first_error = e

        if best_coarse_params is None:
            error_msg = "No valid scenarios found in coarse search"
            raise ValueError(error_msg)

        crane_h_coarse, boom_slope_coarse, rotor_offset_coarse = best_coarse_params

        self.logger.info(
            f"Coarse search complete: h={crane_h_coarse:.1f}m, "
            f"slope={boom_slope_coarse:+.1f}%, rotor={rotor_offset_coarse:+.2f}m, "
            f"{'net' if self.project.optimize_for_net_earthwork else 'total'}={best_coarse_volume:.0f}m³"
        )

        # === STAGE 2: FINE SEARCH ===
        self.logger.info("=" * 60)
        self.logger.info("STAGE 2: FINE SEARCH")
        self.logger.info("=" * 60)

        if feedback:
            feedback.pushInfo("\n" + "=" * 60)
            feedback.pushInfo("STAGE 2: FINE SEARCH")
            feedback.pushInfo("=" * 60)

        # Fine search around best coarse result
        height_step_fine = self.project.search_step  # Use user-specified fine step
        heights_fine = np.arange(
            crane_h_coarse - 1.0,
            crane_h_coarse + 1.0 + height_step_fine,
            height_step_fine
        )
        # Clamp to user-defined range
        heights_fine = heights_fine[
            (heights_fine >= height_min) & (heights_fine <= height_max)
        ]

        if self.project.boom is not None and self.project.boom_slope_optimize:
            slope_step_fine = self.project.boom_slope_step_fine
            boom_slopes_fine = np.arange(
                boom_slope_coarse - 0.5,
                boom_slope_coarse + 0.5 + slope_step_fine,
                slope_step_fine
            )
            # Clamp to valid range
            boom_slopes_fine = boom_slopes_fine[
                (boom_slopes_fine >= boom_slope_min) & (boom_slopes_fine <= boom_slope_max)
            ]
        elif self.project.boom is not None:
            boom_slopes_fine = [boom_slope_coarse]
        else:
            boom_slopes_fine = [0.0]  # No boom surface

        if self.project.rotor_storage is not None and self.project.rotor_height_optimize:
            rotor_step_fine = self.project.rotor_height_step_fine
            rotor_offsets_fine = np.arange(
                rotor_offset_coarse - 0.2,
                rotor_offset_coarse + 0.2 + rotor_step_fine,
                rotor_step_fine
            )
            # Clamp to valid range
            rotor_offsets_fine = rotor_offsets_fine[
                (rotor_offsets_fine >= -self.project.rotor_height_offset_max) &
                (rotor_offsets_fine <= self.project.rotor_height_offset_max)
            ]
        elif self.project.rotor_storage is not None:
            rotor_offsets_fine = [rotor_offset_coarse]
        else:
            rotor_offsets_fine = [0.0]  # No rotor storage

        num_fine = len(heights_fine) * len(boom_slopes_fine) * len(rotor_offsets_fine)

        self.logger.info(
            f"Fine search: {len(heights_fine)} heights × "
            f"{len(boom_slopes_fine)} boom slopes × "
            f"{len(rotor_offsets_fine)} rotor offsets = {num_fine} scenarios"
        )

        if feedback:
            feedback.pushInfo(
                f"Testing {num_fine} parameter combinations (fine search)..."
            )

        best_fine_volume = float('inf')
        best_fine_params = None
        best_fine_result = None

        # Build scenario list for parallel execution
        fine_scenarios = [
            (float(crane_h), float(boom_slope), float(rotor_offset))
            for crane_h in heights_fine
            for boom_slope in boom_slopes_fine
            for rotor_offset in rotor_offsets_fine
        ]

        # Decide parallel vs sequential based on scenario count and use_parallel flag
        if use_parallel and num_fine >= 20:
            # Parallel execution
            self.logger.info(f"Running fine search in parallel ({max_workers} workers)")

            # Prepare project dict for serialization
            project_dict = self._create_project_dict()
            dem_path = self.dem_layer.source()

            if max_workers is None:
                max_workers = max(1, mp.cpu_count() - 1)

            completed = 0
            failed = 0

            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                worker_func = partial(
                    _calculate_multi_param_scenario,
                    dem_path=dem_path,
                    project_dict=project_dict,
                    use_vectorized=self._use_vectorized
                )

                futures = {
                    executor.submit(worker_func, scenario): scenario
                    for scenario in fine_scenarios
                }

                for future in as_completed(futures):
                    scenario = futures[future]
                    completed += 1

                    if feedback and feedback.isCanceled():
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

                    try:
                        _, result_dict = future.result()

                        from .surface_types import MultiSurfaceCalculationResult
                        result = MultiSurfaceCalculationResult.from_dict(result_dict)

                        # Choose optimization metric
                        if self.project.optimize_for_net_earthwork:
                            metric_volume = abs(result.net_volume)
                        else:
                            metric_volume = result.total_volume_moved

                        if metric_volume < best_fine_volume:
                            best_fine_volume = metric_volume
                            best_fine_params = scenario
                            best_fine_result = result

                        # Progress update
                        if feedback and completed % 100 == 0:
                            progress = 50 + int((completed / num_fine) * 50)
                            feedback.setProgress(progress)
                            if best_fine_params:
                                feedback.pushInfo(
                                    f"  Fine: {completed}/{num_fine} - "
                                    f"Best: h={best_fine_params[0]:.2f}m, "
                                    f"slope={best_fine_params[1]:+.2f}%, "
                                    f"rotor={best_fine_params[2]:+.3f}m"
                                )

                    except Exception as e:
                        failed += 1
                        self.logger.error(f"Error in fine scenario {scenario}: {e}")

            self.logger.info(f"Fine search: {completed - failed} successful, {failed} failed")

        else:
            # Sequential execution (fallback or small scenario count)
            self.logger.info("Running fine search sequentially")
            scenario_count = 0

            for crane_h, boom_slope, rotor_offset in fine_scenarios:
                if feedback and feedback.isCanceled():
                    break

                try:
                    result = self.calculate_scenario(
                        crane_height=crane_h,
                        feedback=None,
                        boom_slope_percent=boom_slope,
                        rotor_height_offset=rotor_offset
                    )

                    if self.project.optimize_for_net_earthwork:
                        metric_volume = abs(result.net_volume)
                    else:
                        metric_volume = result.total_volume_moved

                    if metric_volume < best_fine_volume:
                        best_fine_volume = metric_volume
                        best_fine_params = (crane_h, boom_slope, rotor_offset)
                        best_fine_result = result

                    scenario_count += 1

                    if feedback and scenario_count % 100 == 0:
                        progress = 50 + int((scenario_count / num_fine) * 50)
                        feedback.setProgress(progress)
                        if best_fine_params:
                            feedback.pushInfo(
                                f"  Fine: {scenario_count}/{num_fine} - "
                                f"Best: h={best_fine_params[0]:.2f}m"
                            )

                except Exception as e:
                    self.logger.error(f"Error in fine search: {e}")

        if best_fine_params is None:
            # Fall back to coarse result
            self.logger.warning("Fine search failed, using coarse result")
            best_fine_params = best_coarse_params
            best_fine_result = best_coarse_result
            best_fine_volume = best_coarse_volume

        crane_h_opt, boom_slope_opt, rotor_offset_opt = best_fine_params

        self.logger.info("=" * 60)
        self.logger.info("OPTIMIZATION COMPLETE")
        self.logger.info("=" * 60)
        self.logger.info(
            f"Optimal parameters:\n"
            f"  Crane height: {crane_h_opt:.2f}m (offset from FOK: {(crane_h_opt - self.project.fok):+.2f}m)\n"
            f"  Boom slope: {boom_slope_opt:+.2f}%\n"
            f"  Rotor offset: {rotor_offset_opt:+.3f}m\n"
            f"  {'Net' if self.project.optimize_for_net_earthwork else 'Total'} earthwork: {best_fine_volume:.0f}m³\n"
            f"  Cut: {best_fine_result.total_cut:.0f}m³, Fill: {best_fine_result.total_fill:.0f}m³\n"
            f"  Net: {best_fine_result.net_volume:+.0f}m³, Gravel: {best_fine_result.gravel_fill_external:.0f}m³"
        )

        if feedback:
            feedback.pushInfo("\n" + "=" * 60)
            feedback.pushInfo("✓ OPTIMIZATION COMPLETE")
            feedback.pushInfo("=" * 60)
            feedback.pushInfo(
                f"Optimal crane height: {crane_h_opt:.2f}m (FOK: {self.project.fok:.2f}m, offset: {(crane_h_opt - self.project.fok):+.2f}m)"
            )
            feedback.pushInfo(f"Optimal boom slope: {boom_slope_opt:+.2f}%")
            feedback.pushInfo(f"Optimal rotor offset: {rotor_offset_opt:+.3f}m")
            feedback.pushInfo(
                f"{'Net' if self.project.optimize_for_net_earthwork else 'Total'} earthwork: {best_fine_volume:.0f}m³"
            )
            feedback.pushInfo(
                f"Cut: {best_fine_result.total_cut:.0f}m³, "
                f"Fill: {best_fine_result.total_fill:.0f}m³, "
                f"Net: {best_fine_result.net_volume:+.0f}m³"
            )
            feedback.pushInfo(f"External gravel: {best_fine_result.gravel_fill_external:.0f}m³")
            feedback.setProgress(100)

        return crane_h_opt, best_fine_result

    def _find_optimum_single_parameter(self, feedback: Optional[QgsProcessingFeedback],
                                       use_parallel: bool, max_workers: int) -> Tuple[float, MultiSurfaceCalculationResult]:
        """Single-parameter optimization (crane height only, backward compatible)."""
        min_height = self.project.search_min_height
        max_height = self.project.search_max_height
        step = self.project.search_step

        self.logger.info(
            f"Optimizing crane pad height: {min_height:.2f}m - {max_height:.2f}m "
            f"(step: {step:.3f}m)"
        )

        heights = np.arange(min_height, max_height + step, step)
        num_scenarios = len(heights)

        # Determine if we should use parallel processing
        if use_parallel and num_scenarios >= 10:
            self.logger.info(f"Using parallel optimization for {num_scenarios} scenarios")
            try:
                return self._find_optimum_parallel(heights, feedback, max_workers)
            except ValueError as e:
                if "No valid scenarios found" in str(e):
                    self.logger.warning("Parallel optimization failed, falling back to sequential")
                    if feedback:
                        feedback.pushInfo("Parallel optimization failed, trying sequential...")
                    # Fallback to sequential
                    return self._find_optimum_sequential(heights, feedback)
                else:
                    raise
            except Exception as e:
                self.logger.warning(f"Parallel optimization error: {e}, falling back to sequential")
                if feedback:
                    feedback.pushInfo(f"Parallel error: {e}, trying sequential...")
                return self._find_optimum_sequential(heights, feedback)
        else:
            self.logger.info(f"Using sequential optimization for {num_scenarios} scenarios")
            return self._find_optimum_sequential(heights, feedback)

    def _find_optimum_sequential(self, heights: np.ndarray,
                                 feedback: Optional[QgsProcessingFeedback]) -> Tuple[float, MultiSurfaceCalculationResult]:
        """Sequential optimization (original implementation)."""
        num_scenarios = len(heights)

        self.logger.info(f"Testing {num_scenarios} height scenarios (sequential)")

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

                # Choose optimization metric
                if self.project.optimize_for_net_earthwork:
                    # Optimize for net volume (minimize absolute difference between cut and fill)
                    metric_volume = abs(result.net_volume)
                else:
                    # Optimize for total volume (minimize total earthwork)
                    metric_volume = result.total_volume_moved

                if metric_volume < best_volume:
                    best_volume = metric_volume
                    best_height = height
                    best_result = result
                elif metric_volume == best_volume:
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

    def _find_optimum_parallel(self, heights: np.ndarray,
                              feedback: Optional[QgsProcessingFeedback],
                              max_workers: int = None) -> Tuple[float, MultiSurfaceCalculationResult]:
        """Parallel optimization using ProcessPoolExecutor."""
        num_scenarios = len(heights)

        if max_workers is None:
            max_workers = max(1, mp.cpu_count() - 1)  # Leave one CPU free

        self.logger.info(
            f"Testing {num_scenarios} height scenarios in parallel "
            f"(using {max_workers} workers)"
        )

        if feedback:
            feedback.pushInfo(
                f"Testing {num_scenarios} crane pad heights in parallel "
                f"({max_workers} CPU cores)..."
            )

        # Prepare serializable project dict
        project_dict = {
            'crane_wkt': self.project.crane_pad.geometry.asWkt(),
            'foundation_wkt': self.project.foundation.geometry.asWkt(),
            'boom_wkt': self.project.boom.geometry.asWkt() if self.project.boom else None,
            'rotor_wkt': self.project.rotor_storage.geometry.asWkt() if self.project.rotor_storage else None,
            'dxf_path': getattr(self.project.crane_pad, 'dxf_path', ''),  # DXF source path
            'fok': self.project.fok,
            'foundation_depth': self.project.foundation_depth,
            'gravel_thickness': self.project.gravel_thickness,
            'rotor_height_offset': self.project.rotor_height_offset,
            'slope_angle': self.project.slope_angle,
            'boom_slope': self.project.boom.slope_longitudinal if self.project.boom else 0.0,
            'boom_auto_slope': self.project.boom.auto_slope if self.project.boom else False,
            'boom_slope_min': getattr(self.project.boom, 'slope_min', 2.0) if self.project.boom else 2.0,
            'boom_slope_max': getattr(self.project.boom, 'slope_max', 8.0) if self.project.boom else 8.0,
            'crane_metadata': self.project.crane_pad.metadata,
            'foundation_metadata': self.project.foundation.metadata,
            'boom_metadata': self.project.boom.metadata if self.project.boom else {},
            'rotor_metadata': self.project.rotor_storage.metadata if self.project.rotor_storage else {},
        }

        dem_path = self.dem_layer.source()

        best_height = None
        best_volume = float('inf')
        best_result = None

        completed = 0
        successful = 0
        failed = 0
        failed_heights = []
        error_messages = []

        # Use ProcessPoolExecutor for CPU-bound calculations
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            worker_func = partial(
                _calculate_single_height_scenario,
                dem_path=dem_path,
                project_dict=project_dict,
                use_vectorized=self._use_vectorized
            )

            futures = {
                executor.submit(worker_func, float(height)): float(height)
                for height in heights
            }

            # Process results as they complete
            for future in as_completed(futures):
                height = futures[future]
                completed += 1

                if feedback and feedback.isCanceled():
                    self.logger.info("Optimization cancelled by user")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                try:
                    _, result_dict = future.result()

                    # Reconstruct result object from dict
                    from .surface_types import MultiSurfaceCalculationResult
                    result = MultiSurfaceCalculationResult.from_dict(result_dict)

                    total_volume = result.total_volume_moved
                    successful += 1

                    if total_volume < best_volume:
                        best_volume = total_volume
                        best_height = height
                        best_result = result
                    elif total_volume == best_volume:
                        if abs(result.net_volume) < abs(best_result.net_volume):
                            best_height = height
                            best_result = result

                    # Progress update
                    if feedback and completed % 10 == 0:
                        progress = int((completed / num_scenarios) * 100)
                        feedback.setProgress(progress)
                        feedback.pushInfo(
                            f"  [{completed}/{num_scenarios}] Best so far: "
                            f"{best_height:.2f}m ({best_volume:.0f}m³)"
                        )

                except Exception as e:
                    failed += 1
                    failed_heights.append(height)
                    error_msg = str(e)
                    error_messages.append(f"{height:.2f}m: {error_msg}")

                    self.logger.error(f"Error calculating scenario h={height:.2f}m: {e}")
                    if feedback:
                        feedback.reportError(
                            f"Error at height {height:.2f}m: {error_msg}",
                            fatalError=False
                        )

        # Log summary statistics
        self.logger.info(
            f"Parallel optimization completed: {successful} successful, {failed} failed "
            f"out of {num_scenarios} scenarios"
        )

        if failed > 0:
            self.logger.warning(f"Failed heights: {failed_heights}")
            self.logger.warning(f"Error details:\n" + "\n".join(error_messages[:5]))  # Log first 5 errors

        if best_result is None:
            error_summary = (
                f"No valid scenarios found during optimization. "
                f"All {num_scenarios} scenarios failed.\n"
                f"Sample errors:\n" + "\n".join(error_messages[:3])
            )
            self.logger.error(error_summary)

            # Try fallback to sequential processing with first height
            if len(heights) > 0:
                self.logger.info("Attempting fallback to sequential processing for debugging...")
                try:
                    test_result = self.calculate_scenario(float(heights[0]), feedback)
                    self.logger.info(f"Sequential calculation succeeded for h={heights[0]:.2f}m")
                    self.logger.info("Issue appears to be with parallel processing, not calculations")
                except Exception as seq_error:
                    self.logger.error(f"Sequential calculation also failed: {seq_error}")
                    import traceback
                    self.logger.error(traceback.format_exc())

            raise ValueError(error_summary)

        self.logger.info(
            f"Parallel optimization complete: optimal crane height = {best_height:.2f}m, "
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

    # =========================================================================
    # UNCERTAINTY PROPAGATION METHODS
    # =========================================================================

    def find_optimum_with_uncertainty(
        self,
        uncertainty_config: UncertaintyConfig,
        feedback: Optional[QgsProcessingFeedback] = None
    ) -> UncertaintyAnalysisResult:
        """
        Find optimal parameters with uncertainty propagation using Monte Carlo.

        Performs Monte Carlo simulation to propagate input uncertainties through
        the optimization process and quantify output uncertainties.

        Args:
            uncertainty_config: Configuration for uncertainty analysis
            feedback: Optional feedback object for progress reporting

        Returns:
            UncertaintyAnalysisResult with distributions and sensitivity analysis
        """
        start_time = time.time()
        n_samples = uncertainty_config.num_samples

        self.logger.info("=" * 60)
        self.logger.info("UNCERTAINTY PROPAGATION ANALYSIS")
        self.logger.info(f"Monte Carlo with {n_samples} samples")
        self.logger.info("=" * 60)

        if feedback:
            feedback.pushInfo("\n" + "=" * 60)
            feedback.pushInfo("UNCERTAINTY PROPAGATION ANALYSIS")
            feedback.pushInfo(f"Running {n_samples} Monte Carlo samples...")
            feedback.pushInfo("=" * 60)

        # 1. Run nominal calculation first
        nominal_height, nominal_result = self.find_optimum(feedback=None, use_parallel=False)

        # 2. Generate parameter samples
        base_values = {
            'fok': self.project.fok,
            'slope_angle': self.project.slope_angle,
            'foundation_depth': self.project.foundation_depth,
            'gravel_thickness': self.project.gravel_thickness,
        }

        samples = generate_parameter_samples(uncertainty_config, base_values)

        # 3. Run Monte Carlo simulation
        mc_results = self._run_monte_carlo_samples(
            samples, uncertainty_config, feedback
        )

        # 4. Analyze results
        analysis_result = self._analyze_monte_carlo_results(
            mc_results, samples, uncertainty_config, nominal_result
        )

        # 5. Calculate Sobol sensitivity indices
        self._calculate_sensitivity(analysis_result, samples, mc_results)

        # Record computation time
        analysis_result.computation_time_seconds = time.time() - start_time

        self.logger.info("=" * 60)
        self.logger.info("UNCERTAINTY ANALYSIS COMPLETE")
        self.logger.info(f"Time: {analysis_result.computation_time_seconds:.1f}s")
        self.logger.info("=" * 60)

        if feedback:
            feedback.pushInfo("\n" + "=" * 60)
            feedback.pushInfo("✓ UNCERTAINTY ANALYSIS COMPLETE")
            feedback.pushInfo("=" * 60)
            feedback.pushInfo(
                f"Crane height: {analysis_result.crane_height.mean:.2f} ± "
                f"{analysis_result.crane_height.std:.2f} m"
            )
            feedback.pushInfo(
                f"Total cut: {analysis_result.total_cut.mean:.0f} ± "
                f"{analysis_result.total_cut.std:.0f} m³"
            )
            feedback.pushInfo(
                f"Computation time: {analysis_result.computation_time_seconds:.1f}s"
            )

        return analysis_result

    def _run_monte_carlo_samples(
        self,
        samples: Dict[str, np.ndarray],
        config: UncertaintyConfig,
        feedback: Optional[QgsProcessingFeedback],
        use_parallel: bool = True
    ) -> List[Dict]:
        """
        Run Monte Carlo samples with perturbed parameters.

        Args:
            samples: Dictionary of parameter samples
            config: Uncertainty configuration
            feedback: Optional feedback object
            use_parallel: Use parallel processing (default True)

        Returns:
            List of result dictionaries from each sample
        """
        n_samples = config.num_samples
        results = []

        # Determine number of workers
        max_workers = max(1, mp.cpu_count() - 1)

        if feedback:
            if use_parallel:
                feedback.pushInfo(
                    f"Running {n_samples} Monte Carlo samples in parallel "
                    f"({max_workers} CPU cores)..."
                )
            else:
                feedback.pushInfo(f"Running {n_samples} Monte Carlo samples...")

        # Create sample configurations
        sample_configs = []
        for i in range(n_samples):
            sample_config = {
                'fok': float(samples['fok'][i]),
                'slope_angle': float(samples['slope_angle'][i]),
                'foundation_depth': float(samples['foundation_depth'][i]),
                'gravel_thickness': float(samples['gravel_thickness'][i]),
                'dem_noise': float(samples['dem_noise'][i]),
                'boom_slope_noise': float(samples.get('boom_slope_noise', np.zeros(n_samples))[i]),
                'rotor_offset_noise': float(samples.get('rotor_offset_noise', np.zeros(n_samples))[i]),
            }
            sample_configs.append(sample_config)

        failed_samples = 0
        last_error = None

        if use_parallel and n_samples >= 10:
            # Parallel execution using ProcessPoolExecutor
            self.logger.info(
                f"Running {n_samples} MC samples in parallel with {max_workers} workers"
            )

            # Prepare serializable project dict
            project_dict = {
                'crane_wkt': self.project.crane_pad.geometry.asWkt(),
                'foundation_wkt': self.project.foundation.geometry.asWkt(),
                'boom_wkt': self.project.boom.geometry.asWkt() if self.project.boom else None,
                'rotor_wkt': self.project.rotor_storage.geometry.asWkt() if self.project.rotor_storage else None,
                'dxf_path': getattr(self.project.crane_pad, 'dxf_path', ''),
                'fok': self.project.fok,
                'foundation_depth': self.project.foundation_depth,
                'gravel_thickness': self.project.gravel_thickness,
                'rotor_height_offset': self.project.rotor_height_offset,
                'slope_angle': self.project.slope_angle,
                'boom_slope': self.project.boom.slope_longitudinal if self.project.boom else 0.0,
                'boom_auto_slope': self.project.boom.auto_slope if self.project.boom else False,
                'boom_slope_min': getattr(self.project.boom, 'slope_min', 2.0) if self.project.boom else 2.0,
                'boom_slope_max': getattr(self.project.boom, 'slope_max', 8.0) if self.project.boom else 8.0,
                'crane_metadata': self.project.crane_pad.metadata,
                'foundation_metadata': self.project.foundation.metadata,
                'boom_metadata': self.project.boom.metadata if self.project.boom else {},
                'rotor_metadata': self.project.rotor_storage.metadata if self.project.rotor_storage else {},
                'search_range_below_fok': self.project.search_range_below_fok,
                'search_range_above_fok': self.project.search_range_above_fok,
                'search_step': self.project.search_step,
            }

            dem_path = self.dem_layer.source()

            # Use ProcessPoolExecutor for parallel execution
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                worker_func = partial(
                    _calculate_mc_sample_parallel,
                    dem_path=dem_path,
                    project_dict=project_dict,
                    use_vectorized=self._use_vectorized
                )

                futures = {
                    executor.submit(worker_func, sample_config): i
                    for i, sample_config in enumerate(sample_configs)
                }

                completed = 0

                # Process results as they complete
                for future in as_completed(futures):
                    sample_idx = futures[future]
                    completed += 1

                    if feedback and feedback.isCanceled():
                        self.logger.info("MC simulation cancelled by user")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

                    try:
                        result = future.result()
                        results.append(result)

                        # Progress update
                        if feedback and completed % max(1, n_samples // 20) == 0:
                            progress = int(completed / n_samples * 100)
                            feedback.setProgress(progress)
                            feedback.pushInfo(
                                f"  [{completed}/{n_samples}] Completed samples"
                            )

                    except Exception as e:
                        failed_samples += 1
                        last_error = e
                        self.logger.error(f"Error in MC sample {sample_idx}: {e}")

                        # If first few samples fail, raise to provide better error message
                        if completed <= 3 and failed_samples == completed:
                            raise ValueError(
                                f"Fehler in den ersten Monte-Carlo-Samples: {e}. "
                                f"Bitte prüfen Sie die Eingabeparameter."
                            ) from e

        else:
            # Sequential execution (for small sample counts or when parallel is disabled)
            for i, sample_config in enumerate(sample_configs):
                if feedback and feedback.isCanceled():
                    break

                try:
                    result = self._calculate_single_mc_sample(sample_config)
                    results.append(result)

                    # Progress update
                    if feedback and (i + 1) % max(1, n_samples // 20) == 0:
                        progress = int((i + 1) / n_samples * 100)
                        feedback.setProgress(progress)
                        feedback.pushInfo(
                            f"  [{i+1}/{n_samples}] Completed sample"
                        )

                except Exception as e:
                    failed_samples += 1
                    last_error = e
                    self.logger.error(f"Error in MC sample {i}: {e}")

                    # If first sample fails, raise immediately to provide better error message
                    if i == 0:
                        raise ValueError(
                            f"Fehler im ersten Monte-Carlo-Sample: {e}. "
                            f"Bitte prüfen Sie die Eingabeparameter."
                        ) from e

        # Log summary of failures
        if failed_samples > 0:
            self.logger.warning(
                f"{failed_samples}/{n_samples} Monte Carlo samples failed. "
                f"Last error: {last_error}"
            )
            if feedback:
                feedback.pushWarning(
                    f"⚠️ {failed_samples} von {n_samples} Samples fehlgeschlagen"
                )

        return results

    def _calculate_single_mc_sample(self, sample_config: Dict) -> Dict:
        """
        Calculate a single Monte Carlo sample with perturbed parameters.

        Args:
            sample_config: Dictionary with perturbed parameter values

        Returns:
            Dictionary with results from this sample
        """
        # Create modified project with perturbed parameters
        modified_project = copy.deepcopy(self.project)

        # Apply parameter perturbations
        modified_project.fok = sample_config['fok']
        modified_project.slope_angle = sample_config['slope_angle']
        modified_project.foundation_depth = sample_config['foundation_depth']
        modified_project.gravel_thickness = sample_config['gravel_thickness']

        # Create new calculator with modified project
        mc_calculator = MultiSurfaceCalculator(self.dem_layer, modified_project)

        # Store DEM noise for this sample
        mc_calculator._dem_noise = sample_config['dem_noise']

        # Run optimization
        optimal_height, result = mc_calculator.find_optimum(
            feedback=None,
            use_parallel=False
        )

        # Apply boom slope and rotor offset noise to result
        boom_slope = result.boom_slope_percent + sample_config['boom_slope_noise']
        rotor_offset = result.rotor_height_offset_optimized + sample_config['rotor_offset_noise']

        return {
            'optimal_height': optimal_height,
            'total_cut': result.total_cut,
            'total_fill': result.total_fill,
            'net_volume': result.net_volume,
            'total_volume_moved': result.total_volume_moved,
            'boom_slope': boom_slope,
            'rotor_offset': rotor_offset,
            'fok': sample_config['fok'],
            'slope_angle': sample_config['slope_angle'],
            'foundation_depth': sample_config['foundation_depth'],
            'gravel_thickness': sample_config['gravel_thickness'],
        }

    def _analyze_monte_carlo_results(
        self,
        mc_results: List[Dict],
        samples: Dict[str, np.ndarray],
        config: UncertaintyConfig,
        nominal_result: MultiSurfaceCalculationResult
    ) -> UncertaintyAnalysisResult:
        """
        Analyze Monte Carlo results and create uncertainty statistics.

        Args:
            mc_results: List of result dictionaries from MC samples
            samples: Input parameter samples
            config: Uncertainty configuration
            nominal_result: Result from nominal calculation

        Returns:
            UncertaintyAnalysisResult with statistics
        """
        # Check if we have any results
        if not mc_results:
            self.logger.error("No Monte Carlo results to analyze - all samples failed!")
            raise ValueError(
                "Keine Monte-Carlo-Ergebnisse vorhanden. "
                "Alle Samples sind fehlgeschlagen. "
                "Bitte prüfen Sie die Eingabeparameter und Geometrien."
            )

        # Extract output arrays
        heights = np.array([r['optimal_height'] for r in mc_results])
        cuts = np.array([r['total_cut'] for r in mc_results])
        fills = np.array([r['total_fill'] for r in mc_results])
        nets = np.array([r['net_volume'] for r in mc_results])
        totals = np.array([r['total_volume_moved'] for r in mc_results])
        boom_slopes = np.array([r['boom_slope'] for r in mc_results])
        rotor_offsets = np.array([r['rotor_offset'] for r in mc_results])

        # Create uncertainty results
        crane_height_unc = UncertaintyResult.from_samples(heights, "crane_height")
        total_cut_unc = UncertaintyResult.from_samples(cuts, "total_cut")
        total_fill_unc = UncertaintyResult.from_samples(fills, "total_fill")
        net_volume_unc = UncertaintyResult.from_samples(nets, "net_volume")
        total_volume_unc = UncertaintyResult.from_samples(totals, "total_volume_moved")

        # Optional outputs
        boom_slope_unc = None
        rotor_offset_unc = None

        if self.project.boom is not None:
            boom_slope_unc = UncertaintyResult.from_samples(boom_slopes, "boom_slope")

        if self.project.rotor_storage is not None:
            rotor_offset_unc = UncertaintyResult.from_samples(rotor_offsets, "rotor_offset")

        return UncertaintyAnalysisResult(
            config=config,
            nominal_result=nominal_result,
            crane_height=crane_height_unc,
            total_cut=total_cut_unc,
            total_fill=total_fill_unc,
            net_volume=net_volume_unc,
            total_volume_moved=total_volume_unc,
            boom_slope=boom_slope_unc,
            rotor_offset=rotor_offset_unc,
            num_samples=len(mc_results),
        )

    def _calculate_sensitivity(
        self,
        analysis_result: UncertaintyAnalysisResult,
        samples: Dict[str, np.ndarray],
        mc_results: List[Dict]
    ):
        """
        Calculate sensitivity indices for each input parameter.

        Updates the analysis_result with sensitivity information.

        Args:
            analysis_result: Result object to update
            samples: Input parameter samples
            mc_results: MC results for correlation analysis
        """
        # Output values for sensitivity analysis
        output_values = np.array([r['total_volume_moved'] for r in mc_results])

        # Parameters to analyze
        param_names = ['fok', 'slope_angle', 'foundation_depth',
                       'gravel_thickness', 'dem_noise']

        # Calculate Sobol-like indices
        sobol_indices = calculate_sobol_indices(samples, output_values, param_names)

        # Create sensitivity results
        for param_name in param_names:
            if param_name not in samples:
                continue

            param_values = samples[param_name]
            sens_result = SensitivityResult.from_samples(
                param_name, param_values, output_values
            )

            # Add Sobol indices
            if param_name in sobol_indices:
                first_order, total = sobol_indices[param_name]
                sens_result.sensitivity_index = first_order
                sens_result.total_sensitivity_index = total

            analysis_result.sensitivity[param_name] = sens_result

        # Log sensitivity ranking
        ranking = analysis_result.get_sensitivity_ranking()
        self.logger.info("Sensitivity ranking (total volume):")
        for param, sensitivity in ranking:
            self.logger.info(f"  {param}: {sensitivity*100:.1f}%")

    def sample_dem_in_polygon_with_noise(
        self,
        geometry: QgsGeometry,
        noise_std: float = 0.0
    ) -> np.ndarray:
        """
        Sample DEM values with optional noise for uncertainty analysis.

        Args:
            geometry: Polygon to sample
            noise_std: Standard deviation of elevation noise (meters)

        Returns:
            Array of elevation values (possibly with noise added)
        """
        elevations = self.sample_dem_in_polygon(geometry)

        if noise_std > 0 and len(elevations) > 0:
            noise = np.random.normal(0, noise_std, len(elevations))
            elevations = elevations + noise

        return elevations
