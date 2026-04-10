"""
DEM Downloader for Wind Turbine Earthwork Calculator V2

Downloads elevation data from hoehendaten.de API and creates mosaics.

API Documentation: https://hoehendaten.de/api-rawtifrequest.html

Author: Wind Energy Site Planning
Version: 2.0.0
"""

import os
import math
import base64
from pathlib import Path
from typing import List, Tuple, Optional
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from qgis.core import (
    QgsRectangle,
    QgsGeometry,
    QgsProcessingFeedback,
    QgsCoordinateReferenceSystem
)

from ..utils.geometry_utils import create_bbox_with_buffer, get_centroid
from ..utils.logging_utils import get_plugin_logger


class DEMDownloader:
    """
    Downloads DEM tiles from hoehendaten.de API and creates mosaics.

    The downloader:
    - Calculates required DEM tiles based on bounding box
    - Downloads tiles from hoehendaten.de API
    - Caches downloaded tiles
    - Creates mosaics from multiple tiles
    - Saves results to GeoTIFF
    """

    # API configuration
    API_BASE_URL = "https://api.hoehendaten.de:14444/v1/rawtif"
    TILE_SIZE = 1000  # 1km x 1km tiles
    TILE_PREFIX = "dgm1_32"
    TILE_RESOLUTION = "1m"

    def __init__(self, cache_dir: Optional[str] = None, force_refresh: bool = False):
        """
        Initialize DEM downloader.

        Args:
            cache_dir (str): Directory for caching tiles (default: workspace cache)
            force_refresh (bool): If True, ignore cache and re-download

        Raises:
            ImportError: If requests package is not available
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "requests package is required for DEM download. "
                "Please install it using: pip install requests"
            )

        self.force_refresh = force_refresh
        self.logger = get_plugin_logger()

        # Set up cache directory
        if cache_dir is None:
            # Use workspace cache directory
            cache_dir = Path.home() / '.qgis3' / 'windturbine_calculator_v2' / 'dem_cache'

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"DEM cache directory: {self.cache_dir}")

    def calculate_tiles(self, bbox: QgsRectangle, buffer_m: float = 250) -> List[str]:
        """
        Calculate required DEM tile names based on bounding box.

        Tiles are named: dgm1_32_{easting}_{northing}_1m
        - easting/northing are the southwest corner in km (rounded down)

        Args:
            bbox (QgsRectangle): Bounding box in EPSG:25832
            buffer_m (float): Buffer distance in meters

        Returns:
            List[str]: List of tile names
        """
        # Add buffer
        bbox_buffered = QgsRectangle(
            bbox.xMinimum() - buffer_m,
            bbox.yMinimum() - buffer_m,
            bbox.xMaximum() + buffer_m,
            bbox.yMaximum() + buffer_m
        )

        self.logger.info(
            f"Calculating tiles for bbox: "
            f"X: {bbox_buffered.xMinimum():.0f}-{bbox_buffered.xMaximum():.0f}, "
            f"Y: {bbox_buffered.yMinimum():.0f}-{bbox_buffered.yMaximum():.0f}"
        )

        # Calculate tile indices
        # hoehendaten.de uses 1km tiles aligned to the UTM grid
        # Tile names use the SW corner in km (rounded down to nearest km)

        min_easting_km = math.floor(bbox_buffered.xMinimum() / self.TILE_SIZE)
        max_easting_km = math.floor(bbox_buffered.xMaximum() / self.TILE_SIZE)
        min_northing_km = math.floor(bbox_buffered.yMinimum() / self.TILE_SIZE)
        max_northing_km = math.floor(bbox_buffered.yMaximum() / self.TILE_SIZE)

        tiles = []
        for easting_km in range(min_easting_km, max_easting_km + 1):
            for northing_km in range(min_northing_km, max_northing_km + 1):
                tile_name = f"{self.TILE_PREFIX}_{easting_km}_{northing_km}_{self.TILE_RESOLUTION}"
                tiles.append(tile_name)

        self.logger.info(f"Required tiles: {len(tiles)} - {tiles}")
        return tiles

    def download_tile(self, tile_name: str, timeout: int = 30,
                     feedback: Optional[QgsProcessingFeedback] = None) -> Optional[str]:
        """
        Download a single DEM tile from hoehendaten.de API.

        Args:
            tile_name (str): Name of the tile (e.g., "dgm1_32_492_5702_1m")
            timeout (int): HTTP timeout in seconds
            feedback (QgsProcessingFeedback): Feedback object for progress

        Returns:
            str: Path to downloaded TIFF file, or None if download failed

        Raises:
            requests.RequestException: If download fails
        """
        import json

        tile_path = self.cache_dir / f"{tile_name}.tif"

        # Check cache
        if tile_path.exists() and not self.force_refresh:
            self.logger.info(f"Using cached tile: {tile_name}")
            if feedback:
                feedback.pushInfo(f"Using cached tile: {tile_name}")
            return str(tile_path)

        # Parse tile name to get coordinates
        # Format: dgm1_32_492_5702_1m
        parts = tile_name.split('_')
        if len(parts) < 4:
            self.logger.error(f"Invalid tile name format: {tile_name}")
            return None

        zone = int(parts[1])  # 32
        easting = int(parts[2]) * 1000 + 500  # 492 -> 492500
        northing = int(parts[3]) * 1000 + 500  # 5702 -> 5702500

        # Prepare API request payload
        payload = {
            "Type": "RawTIFRequest",
            "ID": tile_name,
            "Attributes": {
                "Zone": zone,
                "Easting": float(easting),
                "Northing": float(northing)
            }
        }

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip'
        }

        self.logger.info(f"Downloading tile: {tile_name} from {self.API_BASE_URL}")
        self.logger.info(f"Payload: Zone={zone}, E={easting}, N={northing}")

        if feedback:
            feedback.pushInfo(f"Downloading DEM tile: {tile_name} (Zone {zone}, E={easting}, N={northing})...")

        try:
            response = requests.post(
                self.API_BASE_URL,
                data=json.dumps(payload),
                headers=headers,
                timeout=timeout,
                stream=True
            )

            # Check for errors
            if response.status_code != 200:
                self.logger.warning(f"Tile request failed (HTTP {response.status_code}): {tile_name}")
                self.logger.warning(f"Response: {response.text[:500]}")
                if feedback:
                    feedback.reportError(f"Tile not available: {tile_name} (HTTP {response.status_code})", fatalError=False)
                return None

            response.raise_for_status()

            # Parse JSON response
            response_json = response.json()

            # Validate response structure
            if response_json.get('Type') != 'RawTIFResponse':
                self.logger.error(f"Unexpected response type: {response_json.get('Type')}")
                if feedback:
                    feedback.reportError(f"Invalid API response for {tile_name}", fatalError=False)
                return None

            # Extract Base64-encoded TIFF data
            attributes = response_json.get('Attributes', {})
            raw_tifs = attributes.get('RawTIFs', [])

            if not raw_tifs or len(raw_tifs) == 0:
                self.logger.error(f"No RawTIFs data in response for {tile_name}")
                if feedback:
                    feedback.reportError(f"No TIFF data in response for {tile_name}", fatalError=False)
                return None

            base64_data = raw_tifs[0].get('Data', '')

            if not base64_data:
                self.logger.error(f"Empty TIFF data in response for {tile_name}")
                if feedback:
                    feedback.reportError(f"Empty TIFF data for {tile_name}", fatalError=False)
                return None

            # Decode Base64 to binary TIFF data
            try:
                tiff_binary = base64.b64decode(base64_data)
            except Exception as e:
                self.logger.error(f"Failed to decode Base64 data for {tile_name}: {e}")
                if feedback:
                    feedback.reportError(f"Failed to decode TIFF data for {tile_name}", fatalError=False)
                return None

            # Write binary TIFF data to file
            with open(tile_path, 'wb') as f:
                f.write(tiff_binary)

            file_size_mb = len(tiff_binary) / 1024 / 1024
            self.logger.info(f"Downloaded and decoded tile: {tile_name} ({file_size_mb:.2f} MB)")
            if feedback:
                feedback.pushInfo(f"✓ Downloaded: {tile_name} ({file_size_mb:.2f} MB)")

            return str(tile_path)

        except requests.HTTPError as e:
            self.logger.error(f"HTTP error downloading {tile_name}: {e}")
            if feedback:
                feedback.reportError(f"HTTP error downloading {tile_name}: {e}", fatalError=False)
            return None

        except requests.RequestException as e:
            self.logger.error(f"Error downloading {tile_name}: {e}")
            if feedback:
                feedback.reportError(f"Error downloading {tile_name}: {e}", fatalError=False)
            return None

    def download_tiles(self, tile_names: List[str],
                      feedback: Optional[QgsProcessingFeedback] = None,
                      max_workers: int = 4) -> List[str]:
        """
        Download multiple DEM tiles in parallel.

        Args:
            tile_names (List[str]): List of tile names
            feedback (QgsProcessingFeedback): Feedback object
            max_workers (int): Maximum number of parallel downloads (default: 4)

        Returns:
            List[str]: Paths to downloaded TIFF files
        """
        self.logger.info(f"Starting parallel download of {len(tile_names)} tiles with {max_workers} workers")

        tile_paths = []
        failed_tiles = []

        # Use ThreadPoolExecutor for I/O-bound downloads
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_tile = {
                executor.submit(self.download_tile, tile_name, feedback=feedback): tile_name
                for tile_name in tile_names
            }

            # Process completed downloads
            completed = 0
            for future in as_completed(future_to_tile):
                tile_name = future_to_tile[future]
                completed += 1

                if feedback and feedback.isCanceled():
                    self.logger.info("Download cancelled by user")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                try:
                    tile_path = future.result()
                    if tile_path:
                        tile_paths.append(tile_path)
                        if feedback:
                            feedback.pushInfo(f"  ✓ [{completed}/{len(tile_names)}] {tile_name}")
                    else:
                        failed_tiles.append(tile_name)
                        if feedback:
                            feedback.pushInfo(f"  ✗ [{completed}/{len(tile_names)}] {tile_name} (failed)")
                except Exception as e:
                    self.logger.error(f"Error downloading {tile_name}: {e}")
                    failed_tiles.append(tile_name)
                    if feedback:
                        feedback.reportError(f"Download error for {tile_name}: {e}", fatalError=False)

        self.logger.info(f"Downloaded {len(tile_paths)}/{len(tile_names)} tiles successfully")
        if failed_tiles:
            self.logger.warning(f"Failed tiles: {failed_tiles}")

        return tile_paths

    def create_mosaic(self, tile_paths: List[str], output_path: str,
                     feedback: Optional[QgsProcessingFeedback] = None) -> str:
        """
        Create a mosaic from multiple DEM tiles.

        Args:
            tile_paths (List[str]): Paths to input TIFF files
            output_path (str): Path for output mosaic
            feedback (QgsProcessingFeedback): Feedback object

        Returns:
            str: Path to mosaic file

        Raises:
            Exception: If mosaic creation fails
        """
        if not tile_paths:
            raise ValueError("No tiles to mosaic")

        if len(tile_paths) == 1:
            # Only one tile, no need to mosaic
            self.logger.info("Only one tile, copying instead of mosaicking")
            import shutil
            shutil.copy(tile_paths[0], output_path)
            return output_path

        self.logger.info(f"Creating mosaic from {len(tile_paths)} tiles")
        if feedback:
            feedback.pushInfo(f"Creating DEM mosaic from {len(tile_paths)} tiles...")

        # We intentionally do NOT use processing.run("gdal:merge", ...) here.
        # That entry point shells out to gdal_merge.py, which copies pixels
        # via band.ReadAsArray() / band.WriteArray(). On QGIS builds where
        # GDAL's _gdal_array numpy bridge is broken ("numpy.core.multiarray
        # failed to import"), every read returns empty and the resulting
        # mosaic is silently filled with nodata only. See gdal_compat.py.
        try:
            import numpy as np
            from osgeo import gdal
            from ..utils.gdal_compat import (
                read_band_as_array,
                write_array_to_band,
            )
        except ImportError as e:
            raise Exception(
                f"GDAL/numpy not available for mosaic creation: {e}"
            )

        try:
            return self._create_mosaic_via_gdal_compat(
                tile_paths, output_path, feedback, np, gdal,
                read_band_as_array, write_array_to_band
            )
        except Exception as e:
            self.logger.error(f"Failed to create mosaic: {e}")
            raise

    def _create_mosaic_via_gdal_compat(
        self, tile_paths, output_path, feedback,
        np, gdal, read_band_as_array, write_array_to_band
    ):
        """
        Mosaic tiles onto a single GeoTIFF using the ReadRaster/WriteRaster
        path from ``gdal_compat``. This avoids GDAL's ``_gdal_array`` numpy
        extension entirely.

        Assumes all source tiles share the same pixel size and projection
        (true for the hoehendaten.de dgm1 1m tiles we download).
        """
        datasets = []
        try:
            for tile_path in tile_paths:
                ds = gdal.Open(tile_path, gdal.GA_ReadOnly)
                if ds is None:
                    self.logger.warning(
                        f"Could not open tile with GDAL, skipping: {tile_path}"
                    )
                    continue
                datasets.append(ds)

            if not datasets:
                raise Exception("No valid raster tiles to mosaic")

            # Use the first tile's grid as the reference
            gt0 = datasets[0].GetGeoTransform()
            pixel_w = gt0[1]
            pixel_h = gt0[5]  # usually negative
            projection = datasets[0].GetProjection()

            if pixel_w == 0 or pixel_h == 0:
                raise Exception(f"First tile has degenerate pixel size: {gt0}")

            # Union of all tile extents in world coordinates
            min_x = None
            max_x = None
            min_y = None
            max_y = None
            for ds in datasets:
                gt = ds.GetGeoTransform()
                tile_min_x = gt[0]
                tile_max_y = gt[3]
                tile_max_x = tile_min_x + ds.RasterXSize * gt[1]
                tile_min_y = tile_max_y + ds.RasterYSize * gt[5]
                if min_x is None or tile_min_x < min_x:
                    min_x = tile_min_x
                if max_x is None or tile_max_x > max_x:
                    max_x = tile_max_x
                if min_y is None or tile_min_y < min_y:
                    min_y = tile_min_y
                if max_y is None or tile_max_y > max_y:
                    max_y = tile_max_y

            out_width = int(round((max_x - min_x) / pixel_w))
            out_height = int(round((min_y - max_y) / pixel_h))  # pixel_h < 0

            if out_width <= 0 or out_height <= 0:
                raise Exception(
                    f"Invalid mosaic dimensions: {out_width}x{out_height}"
                )

            self.logger.info(
                f"Mosaic grid: {out_width}x{out_height} px, "
                f"pixel=({pixel_w}, {pixel_h}), "
                f"extent=[{min_x}, {min_y}, {max_x}, {max_y}]"
            )

            # Create the output raster and pre-fill with nodata
            driver = gdal.GetDriverByName("GTiff")
            out_ds = driver.Create(
                output_path, out_width, out_height, 1, gdal.GDT_Float32,
                options=["COMPRESS=LZW", "TILED=YES"]
            )
            if out_ds is None:
                raise Exception(f"Could not create output raster: {output_path}")

            out_ds.SetGeoTransform((min_x, pixel_w, 0, max_y, 0, pixel_h))
            if projection:
                out_ds.SetProjection(projection)
            out_band = out_ds.GetRasterBand(1)
            out_nodata = -9999.0
            out_band.SetNoDataValue(out_nodata)
            out_band.Fill(out_nodata)

            # Copy each tile into the output via ReadRaster/WriteRaster
            for idx, ds in enumerate(datasets):
                gt = ds.GetGeoTransform()
                src_band = ds.GetRasterBand(1)
                src_nodata = src_band.GetNoDataValue()
                src_w = ds.RasterXSize
                src_h = ds.RasterYSize

                dst_col = int(round((gt[0] - min_x) / pixel_w))
                dst_row = int(round((gt[3] - max_y) / pixel_h))

                # Clamp against the output grid (defensive; normally exact)
                if (
                    dst_col < 0 or dst_row < 0
                    or dst_col + src_w > out_width
                    or dst_row + src_h > out_height
                ):
                    self.logger.warning(
                        f"Tile {idx} does not fit mosaic window "
                        f"(dst=({dst_col},{dst_row}), src={src_w}x{src_h}, "
                        f"out={out_width}x{out_height}), skipping"
                    )
                    continue

                data = read_band_as_array(src_band, 0, 0, src_w, src_h)
                data = data.astype(np.float32, copy=False)

                # If the source tile has nodata pixels, preserve whatever is
                # already in the destination (from earlier tiles or the
                # initial fill) for those positions.
                if src_nodata is not None:
                    valid_mask = data != np.float32(src_nodata)
                    if not valid_mask.all():
                        existing = read_band_as_array(
                            out_band, dst_col, dst_row, src_w, src_h
                        ).astype(np.float32, copy=False)
                        data = np.where(valid_mask, data, existing)

                write_array_to_band(out_band, data, dst_col, dst_row)

            out_band.FlushCache()
            out_ds.FlushCache()

            # Sanity check: sample a central window and verify we got real
            # elevation data, not just nodata. Without this we can silently
            # ship a broken mosaic again (regression guard).
            sample_win = min(64, out_width, out_height)
            if sample_win > 0:
                cx = max(0, (out_width - sample_win) // 2)
                cy = max(0, (out_height - sample_win) // 2)
                sample = read_band_as_array(
                    out_band, cx, cy, sample_win, sample_win
                ).astype(np.float32, copy=False)
                valid_sample = sample[sample != np.float32(out_nodata)]
                if valid_sample.size == 0:
                    self.logger.error(
                        f"Mosaic sanity check failed: center window "
                        f"({sample_win}x{sample_win} at {cx},{cy}) is "
                        f"entirely nodata ({out_nodata}). DEM pipeline is "
                        f"broken and all downstream Cut/Fill volumes will "
                        f"be zero."
                    )
                    if feedback:
                        feedback.reportError(
                            "DEM mosaic is empty (nodata only). "
                            "Calculated earthwork volumes will be zero.",
                            fatalError=False,
                        )
                else:
                    self.logger.info(
                        f"Mosaic sanity check OK: center window min="
                        f"{float(valid_sample.min()):.2f}, "
                        f"max={float(valid_sample.max()):.2f}, "
                        f"mean={float(valid_sample.mean()):.2f}, "
                        f"valid={valid_sample.size}/{sample.size}"
                    )

            out_band = None
            out_ds = None

            self.logger.info(f"Mosaic created: {output_path}")
            return output_path

        finally:
            for ds in datasets:
                ds = None

    def download_for_geometry(self, geometry: QgsGeometry, output_path: str,
                             buffer_m: float = 250,
                             feedback: Optional[QgsProcessingFeedback] = None) -> str:
        """
        Download and mosaic DEM data for a geometry.

        This is the main workflow method that:
        1. Calculates required tiles
        2. Downloads tiles
        3. Creates mosaic
        4. Returns path to mosaic

        Args:
            geometry (QgsGeometry): Geometry to cover
            output_path (str): Path for output mosaic
            buffer_m (float): Buffer distance in meters
            feedback (QgsProcessingFeedback): Feedback object

        Returns:
            str: Path to mosaic file
        """
        # Calculate tiles
        bbox = geometry.boundingBox()
        tile_names = self.calculate_tiles(bbox, buffer_m)

        if not tile_names:
            raise ValueError("No tiles calculated for geometry")

        if feedback:
            feedback.pushInfo(f"Need to download {len(tile_names)} DEM tile(s)")

        # Download tiles
        tile_paths = self.download_tiles(tile_names, feedback)

        if not tile_paths:
            raise Exception("Failed to download any DEM tiles")

        if len(tile_paths) < len(tile_names):
            self.logger.warning(
                f"Only {len(tile_paths)}/{len(tile_names)} tiles downloaded. "
                f"Coverage may be incomplete."
            )
            if feedback:
                feedback.reportError(
                    f"Warning: Only {len(tile_paths)}/{len(tile_names)} tiles available",
                    fatalError=False
                )

        # Create mosaic
        mosaic_path = self.create_mosaic(tile_paths, output_path, feedback)

        return mosaic_path

    def get_cache_info(self) -> dict:
        """
        Get information about cached tiles.

        Returns:
            dict: Cache information (num_tiles, total_size_mb, cache_dir)
        """
        cache_files = list(self.cache_dir.glob("*.tif"))
        total_size = sum(f.stat().st_size for f in cache_files)

        return {
            'num_tiles': len(cache_files),
            'total_size_mb': total_size / 1024 / 1024,
            'cache_dir': str(self.cache_dir)
        }

    def clear_cache(self):
        """Clear all cached tiles."""
        cache_files = list(self.cache_dir.glob("*.tif"))
        for f in cache_files:
            f.unlink()
        self.logger.info(f"Cleared {len(cache_files)} cached tiles")
