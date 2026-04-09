"""
Unit tests for utils/gdal_compat.py

Regression tests for the ``ReadRaster``/``WriteRaster``-based helpers
added to work around broken ``_gdal_array`` bindings in some QGIS
Python environments (``numpy.core.multiarray failed to import``).
"""

import os
import tempfile
import unittest

import numpy as np


try:
    from osgeo import gdal  # noqa: F401
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False


@unittest.skipUnless(GDAL_AVAILABLE, "osgeo.gdal not available")
class TestGdalCompat(unittest.TestCase):
    """Round-trip tests for read_band_as_array / write_array_to_band."""

    def setUp(self):
        from osgeo import gdal
        self.gdal = gdal
        self.tmpdir = tempfile.mkdtemp(prefix="gdal_compat_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_dem(self, arr, nodata=-9999.0):
        """Create a small in-memory DEM GeoTIFF and return its path."""
        from osgeo import gdal
        path = os.path.join(self.tmpdir, "test.tif")
        h, w = arr.shape
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(path, w, h, 1, gdal.GDT_Float32)
        # Identity-ish geotransform: origin (0, h), pixel size 1.0
        ds.SetGeoTransform([0.0, 1.0, 0.0, float(h), 0.0, -1.0])
        band = ds.GetRasterBand(1)
        band.WriteRaster(0, 0, w, h, arr.astype(np.float32).tobytes())
        band.SetNoDataValue(nodata)
        band.FlushCache()
        ds.FlushCache()
        ds = None
        return path

    def test_read_full_band_matches_expected(self):
        """Reading a full Float32 band round-trips the raw data."""
        from ..utils.gdal_compat import read_band_as_array

        expected = np.array(
            [[1.0, 2.0, 3.0],
             [4.0, 5.0, 6.0],
             [7.0, 8.0, 9.0]],
            dtype=np.float32,
        )
        path = self._make_dem(expected)
        ds = self.gdal.Open(path)
        band = ds.GetRasterBand(1)

        got = read_band_as_array(band)
        np.testing.assert_array_equal(got, expected)
        self.assertEqual(got.shape, (3, 3))
        self.assertEqual(got.dtype, np.float32)

    def test_read_window(self):
        """Reading a subwindow returns the correct slice."""
        from ..utils.gdal_compat import read_band_as_array

        expected = np.arange(25, dtype=np.float32).reshape(5, 5)
        path = self._make_dem(expected)
        ds = self.gdal.Open(path)
        band = ds.GetRasterBand(1)

        got = read_band_as_array(band, xoff=1, yoff=1, win_xsize=3, win_ysize=2)
        np.testing.assert_array_equal(got, expected[1:3, 1:4])

    def test_write_array_to_band(self):
        """Writing an array via the compat helper is readable back."""
        from ..utils.gdal_compat import read_band_as_array, write_array_to_band

        # Start with zeros
        initial = np.zeros((4, 4), dtype=np.float32)
        path = self._make_dem(initial)

        ds = self.gdal.Open(path, self.gdal.GA_Update)
        band = ds.GetRasterBand(1)

        payload = np.array(
            [[10.0, 20.0, 30.0, 40.0],
             [11.0, 21.0, 31.0, 41.0],
             [12.0, 22.0, 32.0, 42.0],
             [13.0, 23.0, 33.0, 43.0]],
            dtype=np.float32,
        )
        write_array_to_band(band, payload)
        band.FlushCache()
        ds.FlushCache()
        ds = None

        # Re-open and read back
        ds2 = self.gdal.Open(path)
        band2 = ds2.GetRasterBand(1)
        got = read_band_as_array(band2)
        np.testing.assert_array_equal(got, payload)

    def test_read_byte_mask(self):
        """Reading a Byte band (polygon mask use-case) returns uint8."""
        from ..utils.gdal_compat import read_band_as_array

        path = os.path.join(self.tmpdir, "mask.tif")
        driver = self.gdal.GetDriverByName("GTiff")
        ds = driver.Create(path, 3, 3, 1, self.gdal.GDT_Byte)
        ds.SetGeoTransform([0.0, 1.0, 0.0, 3.0, 0.0, -1.0])
        band = ds.GetRasterBand(1)
        band.WriteRaster(0, 0, 3, 3, bytes([0, 1, 0, 1, 1, 1, 0, 1, 0]))
        band.FlushCache()
        ds.FlushCache()
        ds = None

        ds2 = self.gdal.Open(path)
        band2 = ds2.GetRasterBand(1)
        mask = read_band_as_array(band2)

        self.assertEqual(mask.dtype, np.uint8)
        self.assertEqual(mask.shape, (3, 3))
        self.assertEqual(int(mask.sum()), 5)


if __name__ == "__main__":
    unittest.main()
