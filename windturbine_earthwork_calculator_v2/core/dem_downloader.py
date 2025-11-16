"""
DEM Downloader for Wind Turbine Earthwork Calculator V2

Downloads elevation data from hoehendaten.de API and creates mosaics.

API Documentation: https://hoehendaten.de/api-rawtifrequest.html

Author: Wind Energy Site Planning
Version: 2.0
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
    QgsRasterLayer,
    QgsProcessingFeedback,
    QgsCoordinateReferenceSystem
)
import processing

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

        try:
            # Load tiles as raster layers first
            raster_layers = []
            for tile_path in tile_paths:
                layer = QgsRasterLayer(tile_path, f"tile_{len(raster_layers)}")
                if layer.isValid():
                    raster_layers.append(layer)
                else:
                    self.logger.warning(f"Could not load tile as raster: {tile_path}")

            if not raster_layers:
                raise Exception("No valid raster tiles to mosaic")

            # Use GDAL merge
            result = processing.run(
                "gdal:merge",
                {
                    'INPUT': raster_layers,
                    'PCT': False,  # No palette
                    'SEPARATE': False,  # Combine into single band
                    'NODATA_INPUT': -9999,
                    'NODATA_OUTPUT': -9999,
                    'DATA_TYPE': 5,  # Float32
                    'OUTPUT': output_path
                },
                feedback=feedback
            )

            mosaic_path = result['OUTPUT']
            self.logger.info(f"Mosaic created: {mosaic_path}")

            return mosaic_path

        except Exception as e:
            self.logger.error(f"Failed to create mosaic: {e}")
            raise

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
