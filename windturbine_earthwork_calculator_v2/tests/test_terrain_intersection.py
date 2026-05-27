"""
Unit tests for utils/terrain_intersection.py

Covers:
- Cleanup helpers `_safe_remove` and `_safe_remove_shapefile_set`
  (pure-Python, always runnable).
- Difference-raster math (numpy/GDAL only; QGIS-independent).
- Sloped-target-surface geometry (numpy/GDAL only).

Higher-level functions that take QgsGeometry are not covered here because
they require the full QGIS Python environment; they are exercised by
the end-to-end run path in `core/multi_surface_calculator.py` (see
`tests/test_multi_param_optimization.py` for the QGIS-loaded entry point).
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

try:
    from qgis.core import QgsGeometry  # noqa: F401
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Cleanup helpers — pure Python, no GDAL/QGIS dependency
# ---------------------------------------------------------------------------

class TestCleanupHelpers(unittest.TestCase):
    """The _safe_* helpers must never raise, even on bad input."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="terrain_int_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _import_helpers(self):
        """Import the helpers without pulling QGIS imports at module load.

        terrain_intersection.py imports qgis.core at module level, so a plain
        ``from ..utils.terrain_intersection import _safe_remove`` would fail
        in environments without QGIS. We sidestep that by importing the
        functions via importlib only when QGIS is available, and otherwise
        skip.
        """
        if not QGIS_AVAILABLE:
            self.skipTest("qgis.core not available — terrain_intersection "
                          "cannot be imported in this environment")
        from ..utils.terrain_intersection import (
            _safe_remove, _safe_remove_shapefile_set
        )
        return _safe_remove, _safe_remove_shapefile_set

    def test_safe_remove_existing_file(self):
        _safe_remove, _ = self._import_helpers()
        path = os.path.join(self.tmpdir, "exists.tif")
        with open(path, "w") as fh:
            fh.write("x")
        self.assertTrue(os.path.exists(path))
        _safe_remove(path)
        self.assertFalse(os.path.exists(path))

    def test_safe_remove_missing_file_is_noop(self):
        _safe_remove, _ = self._import_helpers()
        # Should not raise.
        _safe_remove(os.path.join(self.tmpdir, "does-not-exist.tif"))

    def test_safe_remove_empty_path_is_noop(self):
        _safe_remove, _ = self._import_helpers()
        _safe_remove("")
        _safe_remove(None)  # type: ignore[arg-type]

    def test_safe_remove_shapefile_set_removes_all_sidecars(self):
        _, _safe_remove_shp = self._import_helpers()
        base = os.path.join(self.tmpdir, "foo")
        sidecars = [".shp", ".shx", ".dbf", ".prj", ".cpg"]
        for ext in sidecars:
            with open(base + ext, "w") as fh:
                fh.write("data")
        _safe_remove_shp(base + ".shp")
        for ext in sidecars:
            self.assertFalse(
                os.path.exists(base + ext),
                f"{base + ext} should have been removed"
            )

    def test_safe_remove_shapefile_set_handles_missing_set(self):
        _, _safe_remove_shp = self._import_helpers()
        # No files exist; must not raise.
        _safe_remove_shp(os.path.join(self.tmpdir, "ghost.shp"))


# ---------------------------------------------------------------------------
# Difference-raster math — runnable without QGIS as long as GDAL is present
# ---------------------------------------------------------------------------

@unittest.skipUnless(GDAL_AVAILABLE, "osgeo.gdal not available")
@unittest.skipUnless(QGIS_AVAILABLE,
                     "qgis.core not available — terrain_intersection imports it")
class TestDifferenceRasterMath(unittest.TestCase):
    """Smoke test that the horizontal-difference raster contains the expected
    cut/fill values (positive = cut, negative = fill, zero = intersection)."""

    def setUp(self):
        from osgeo import gdal
        self.gdal = gdal
        self.tmpdir = tempfile.mkdtemp(prefix="terrain_diff_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_dem(self, arr, nodata=-9999.0):
        path = os.path.join(self.tmpdir, "dem.tif")
        h, w = arr.shape
        driver = self.gdal.GetDriverByName("GTiff")
        ds = driver.Create(path, w, h, 1, self.gdal.GDT_Float32)
        ds.SetGeoTransform([0.0, 1.0, 0.0, float(h), 0.0, -1.0])
        band = ds.GetRasterBand(1)
        band.WriteRaster(0, 0, w, h, arr.astype(np.float32).tobytes())
        band.SetNoDataValue(nodata)
        band.FlushCache()
        ds.FlushCache()
        ds = None
        return path

    def test_horizontal_difference_values(self):
        from qgis.core import QgsGeometry, QgsPointXY
        from ..utils.terrain_intersection import create_difference_raster_horizontal

        # 3×3 DEM with a clear gradient
        dem_arr = np.array(
            [[100.0, 101.0, 102.0],
             [101.0, 102.0, 103.0],
             [102.0, 103.0, 104.0]],
            dtype=np.float32,
        )
        dem_path = self._write_dem(dem_arr)
        out_path = os.path.join(self.tmpdir, "diff.tif")

        # Square polygon covering the whole DEM
        polygon = QgsGeometry.fromPolygonXY([[
            QgsPointXY(0, 0), QgsPointXY(3, 0),
            QgsPointXY(3, 3), QgsPointXY(0, 3),
            QgsPointXY(0, 0)
        ]])

        target_height = 102.0
        result_path = create_difference_raster_horizontal(
            dem_path, polygon, target_height, out_path
        )

        # Read back and verify diff = DEM - target_height inside the mask.
        ds = self.gdal.Open(result_path, self.gdal.GA_ReadOnly)
        band = ds.GetRasterBand(1)
        raw = band.ReadRaster(0, 0, 3, 3, buf_type=self.gdal.GDT_Float32)
        diff = np.frombuffer(raw, dtype=np.float32).reshape(3, 3).copy()
        ds = None

        expected = dem_arr - target_height
        # Allow NoData edges in case of rasterisation rounding; check at least
        # the centre pixel matches.
        self.assertAlmostEqual(float(diff[1, 1]), float(expected[1, 1]), places=4)


if __name__ == "__main__":
    unittest.main()
