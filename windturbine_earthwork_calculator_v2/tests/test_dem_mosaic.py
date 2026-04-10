"""
Regression tests for core/dem_downloader.py::DEMDownloader.create_mosaic

Guards against the 2026-04 incident where gdal:merge (QGIS processing) was
silently producing nodata-only mosaics in QGIS environments with a broken
_gdal_array numpy bridge, which in turn caused all Cut/Fill volumes in the
generated report to be zero.

These tests mosaic two adjacent in-memory GeoTIFFs and verify that the
resulting raster actually contains the source pixel values at the expected
positions, rather than just the initial nodata fill.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import numpy as np


try:
    from osgeo import gdal  # noqa: F401
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False


@unittest.skipUnless(GDAL_AVAILABLE, "osgeo.gdal not available")
class TestCreateMosaic(unittest.TestCase):
    """End-to-end tests for DEMDownloader.create_mosaic."""

    def setUp(self):
        from osgeo import gdal
        self.gdal = gdal
        self.tmpdir = tempfile.mkdtemp(prefix="dem_mosaic_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_tile(self, name, origin_x, origin_y, arr, nodata=-9999.0):
        """
        Write a small Float32 GeoTIFF tile. ``origin_x`` / ``origin_y`` is
        the world coordinate of the top-left corner; pixel size is 1.0,
        north-up.
        """
        path = os.path.join(self.tmpdir, name)
        h, w = arr.shape
        driver = self.gdal.GetDriverByName("GTiff")
        ds = driver.Create(path, w, h, 1, self.gdal.GDT_Float32)
        ds.SetGeoTransform([float(origin_x), 1.0, 0.0, float(origin_y), 0.0, -1.0])
        band = ds.GetRasterBand(1)
        band.WriteRaster(0, 0, w, h, arr.astype(np.float32).tobytes())
        band.SetNoDataValue(nodata)
        band.FlushCache()
        ds.FlushCache()
        ds = None
        return path

    def _make_downloader(self):
        """
        Build a DEMDownloader without touching QGIS. DEMDownloader's
        __init__ only needs a cache dir and a logger; we stub the logger.
        """
        from ..core.dem_downloader import DEMDownloader

        downloader = DEMDownloader.__new__(DEMDownloader)
        downloader.cache_dir = self.tmpdir
        downloader.force_refresh = False
        downloader.logger = MagicMock()
        return downloader

    def test_mosaic_two_adjacent_tiles_preserves_pixel_values(self):
        """
        Mosaicing two side-by-side tiles must yield a raster whose pixels
        match the source tiles in their original positions. This is the
        regression test for the 'all-nodata mosaic' incident.
        """
        # Tile A: 10x10, values 1..100, at world origin (0, 10)
        # Tile B: 10x10, values 101..200, east of A at origin (10, 10)
        arr_a = np.arange(1, 101, dtype=np.float32).reshape(10, 10)
        arr_b = np.arange(101, 201, dtype=np.float32).reshape(10, 10)

        tile_a = self._write_tile("tile_a.tif", 0, 10, arr_a)
        tile_b = self._write_tile("tile_b.tif", 10, 10, arr_b)

        out_path = os.path.join(self.tmpdir, "mosaic.tif")
        downloader = self._make_downloader()
        result = downloader.create_mosaic([tile_a, tile_b], out_path)

        self.assertEqual(result, out_path)
        self.assertTrue(os.path.exists(out_path))

        # Read back the full mosaic
        from ..utils.gdal_compat import read_band_as_array
        ds = self.gdal.Open(out_path)
        self.assertIsNotNone(ds, "mosaic could not be opened")
        self.assertEqual(ds.RasterXSize, 20)
        self.assertEqual(ds.RasterYSize, 10)

        band = ds.GetRasterBand(1)
        mosaic = read_band_as_array(band)

        # Left half must equal tile A, right half must equal tile B.
        np.testing.assert_array_equal(mosaic[:, :10], arr_a)
        np.testing.assert_array_equal(mosaic[:, 10:], arr_b)

        # And — explicitly — the mosaic must NOT be all-nodata. That's the
        # exact failure mode we regressed against.
        nodata = band.GetNoDataValue()
        self.assertIsNotNone(nodata)
        self.assertFalse(
            np.all(mosaic == np.float32(nodata)),
            "Mosaic is entirely nodata — DEM pipeline regression!",
        )

        ds = None

    def test_mosaic_single_tile_is_a_copy(self):
        """With only one tile, create_mosaic should just copy it."""
        arr = np.full((5, 5), 42.0, dtype=np.float32)
        tile = self._write_tile("only.tif", 0, 5, arr)

        out_path = os.path.join(self.tmpdir, "mosaic_single.tif")
        downloader = self._make_downloader()
        result = downloader.create_mosaic([tile], out_path)

        self.assertEqual(result, out_path)
        self.assertTrue(os.path.exists(out_path))

        from ..utils.gdal_compat import read_band_as_array
        ds = self.gdal.Open(out_path)
        band = ds.GetRasterBand(1)
        mosaic = read_band_as_array(band)
        np.testing.assert_array_equal(mosaic, arr)
        ds = None

    def test_mosaic_empty_input_raises(self):
        downloader = self._make_downloader()
        with self.assertRaises(ValueError):
            downloader.create_mosaic([], os.path.join(self.tmpdir, "x.tif"))

    def test_mosaic_does_not_use_gdal_merge(self):
        """
        Paranoid guard: create_mosaic must NOT route through
        ``processing.run("gdal:merge", ...)``, because that subprocess
        breaks on QGIS builds with a broken _gdal_array numpy bridge.
        """
        arr_a = np.full((4, 4), 1.0, dtype=np.float32)
        arr_b = np.full((4, 4), 2.0, dtype=np.float32)
        tile_a = self._write_tile("a.tif", 0, 4, arr_a)
        tile_b = self._write_tile("b.tif", 4, 4, arr_b)

        # If somebody re-adds ``import processing``, make sure this call
        # would blow up instead of silently producing nodata mosaics.
        with patch.dict("sys.modules", {"processing": None}):
            downloader = self._make_downloader()
            out_path = os.path.join(self.tmpdir, "no_merge.tif")
            downloader.create_mosaic([tile_a, tile_b], out_path)

        ds = self.gdal.Open(out_path)
        band = ds.GetRasterBand(1)
        from ..utils.gdal_compat import read_band_as_array
        got = read_band_as_array(band)
        self.assertEqual(got.shape, (4, 8))
        np.testing.assert_array_equal(got[:, :4], arr_a)
        np.testing.assert_array_equal(got[:, 4:], arr_b)
        ds = None

    def test_mosaic_respects_source_nodata(self):
        """
        A nodata pixel in tile A should not overwrite a valid pixel in
        tile B (when they overlap), and an isolated nodata pixel in one
        tile should remain nodata in the mosaic if no other tile covers
        it.
        """
        # Tile A: 4x4, one nodata corner
        arr_a = np.arange(1, 17, dtype=np.float32).reshape(4, 4)
        arr_a[0, 0] = -9999.0  # nodata pixel
        tile_a = self._write_tile("a.tif", 0, 4, arr_a)

        downloader = self._make_downloader()
        out_path = os.path.join(self.tmpdir, "nd.tif")
        # Only one tile, but single-tile path is shutil.copy, which keeps
        # the nodata as-is — so we give it two disjoint tiles instead.
        arr_b = np.full((4, 4), 99.0, dtype=np.float32)
        tile_b = self._write_tile("b.tif", 4, 4, arr_b)

        downloader.create_mosaic([tile_a, tile_b], out_path)

        ds = self.gdal.Open(out_path)
        band = ds.GetRasterBand(1)
        nodata = band.GetNoDataValue()
        from ..utils.gdal_compat import read_band_as_array
        got = read_band_as_array(band)

        # The corner from tile A stayed nodata (kept from the initial fill).
        self.assertEqual(float(got[0, 0]), float(nodata))
        # But the rest of tile A is intact.
        np.testing.assert_array_equal(got[0, 1:4], arr_a[0, 1:4])
        np.testing.assert_array_equal(got[1:, :4], arr_a[1:, :])
        # And tile B is intact.
        np.testing.assert_array_equal(got[:, 4:], arr_b)
        ds = None


if __name__ == "__main__":
    unittest.main()
