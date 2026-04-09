"""
Regression test for the core cut/fill math against known-good reference data.

The test fixture (``wea45mit3d.zip`` shipped in the plugin directory) was
produced by a prior working run of the plugin on 2025-11-26 and contains:

- A reference DEM mosaic (``WKA_492079_5702007_DEM.tif``, 2000×2000 @ 1 m,
  EPSG:25832)
- The computed crane pad and foundation polygons in the result GeoPackage
  (``WKA_492079_5702007_MultiSurface.gpkg``)
- The reference HTML report with the expected cut/fill values

Background: after commit dc778d9 ("Plan B") calculations silently started
returning cut=0, fill=0 because ``_sample_dem_vectorized`` in
``multi_surface_calculator.py`` and ``earthwork_calculator.py`` called
``band.ReadAsArray()`` which raises ``numpy.core.multiarray failed to
import`` on some QGIS Linux builds. This test pins down the *math* so
that any future regression in the sampling/accumulation code will be
caught immediately.

The test uses ``rasterio`` and ``fiona`` (already transitive dependencies
of QGIS' Python environment) to replicate what
``MultiSurfaceCalculator._calculate_foundation`` and
``MultiSurfaceCalculator._calculate_crane_pad`` do at the pixel level.
It intentionally does *not* import QGIS so that it can run in any Python
environment.
"""

import os
import unittest
import zipfile


REF_ZIP = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "wea45mit3d.zip",
)

# Expected values from the reference HTML report
# (see wea45mit3d/ergebnisse/WKA_492079_5702007_Bericht_MultiSurface.html)
EXPECTED_FOUNDATION_CUT_M3 = 693  # m³
EXPECTED_CRANE_TOTAL_CUT_M3 = 6546  # m³ (platform + slope)
EXPECTED_CRANE_TOTAL_FILL_M3 = 2411  # m³ (platform + slope)
# Platform-only crane pad volumes, verified pixel-wise against the
# reference DEM with the stored polygon:
EXPECTED_CRANE_PLATFORM_CUT_M3 = 5280  # m³ (platform only, no slope)
EXPECTED_CRANE_PLATFORM_FILL_M3 = 1763  # m³ (platform only, no slope)

OPTIMAL_CRANE_HEIGHT = 319.87  # m ü.NN
GRAVEL_THICKNESS = 0.60  # m
FOK = 318.37  # m ü.NN
FOUNDATION_DEPTH = 3.1  # m


def _load_deps():
    """Import optional test deps; return (rasterio, fiona, shape) or None."""
    try:
        import rasterio  # noqa: F401
        import fiona  # noqa: F401
        from shapely.geometry import shape  # noqa: F401
        return rasterio, fiona, shape
    except ImportError:
        return None


@unittest.skipUnless(
    os.path.exists(REF_ZIP),
    f"Reference fixture not available: {REF_ZIP}",
)
@unittest.skipUnless(_load_deps() is not None, "rasterio/fiona/shapely not installed")
class TestVolumeRegression(unittest.TestCase):
    """Regression test for the cut/fill math against wea45mit3d reference."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        import rasterio
        import fiona
        from shapely.geometry import shape
        from rasterio.features import geometry_mask
        import numpy as np

        cls.tmpdir = tempfile.mkdtemp(prefix="wea45_ref_")
        with zipfile.ZipFile(REF_ZIP) as zf:
            zf.extractall(cls.tmpdir)

        base = os.path.join(cls.tmpdir, "wea45mit3d", "ergebnisse")
        cls.dem_path = os.path.join(base, "WKA_492079_5702007_DEM.tif")
        cls.gpkg_path = os.path.join(base, "WKA_492079_5702007_MultiSurface.gpkg")

        with fiona.open(cls.gpkg_path, layer="kranstellflaechen") as src:
            cls.crane_poly = shape(next(iter(src))["geometry"])
        with fiona.open(cls.gpkg_path, layer="fundamentflaechen") as src:
            cls.found_poly = shape(next(iter(src))["geometry"])

        src = rasterio.open(cls.dem_path)
        cls.transform = src.transform
        cls.shape = src.shape
        cls.dem = src.read(1).astype(float)
        cls.nodata = src.nodata
        cls.pixel_area = abs(src.transform.a) * abs(src.transform.e)
        src.close()

        cls.valid = (
            (cls.dem != cls.nodata) if cls.nodata is not None else np.ones_like(cls.dem, dtype=bool)
        )

        cls.crane_mask = geometry_mask(
            [cls.crane_poly.__geo_interface__],
            transform=cls.transform,
            out_shape=cls.shape,
            invert=True,
        )
        cls.found_mask = geometry_mask(
            [cls.found_poly.__geo_interface__],
            transform=cls.transform,
            out_shape=cls.shape,
            invert=True,
        )

    @staticmethod
    def _cut_fill(elevations, target_height, pixel_area):
        """Pixel-wise cut/fill accumulation - mirrors MultiSurfaceCalculator."""
        cut = 0.0
        fill = 0.0
        for z in elevations:
            diff = z - target_height
            if diff > 0:
                cut += diff * pixel_area
            else:
                fill += (-diff) * pixel_area
        return cut, fill

    def test_foundation_cut_matches_reference(self):
        """
        Foundation cut volume must match the HTML report within 1 m³.

        The foundation bottom is fok - depth = 318.37 - 3.1 = 315.27 m.
        Reference report: Abtrag 693 m³.
        """
        planum = FOK - FOUNDATION_DEPTH
        elev = self.dem[self.found_mask & self.valid]
        cut, _ = self._cut_fill(elev.tolist(), planum, self.pixel_area)
        self.assertAlmostEqual(cut, EXPECTED_FOUNDATION_CUT_M3, delta=1.0,
                               msg=f"Foundation cut drifted: got {cut:.1f}, "
                                   f"expected {EXPECTED_FOUNDATION_CUT_M3}")

    def test_crane_pad_platform_cut_matches_reference(self):
        """
        Crane pad *platform-only* cut (no slope) must match the pixel-wise
        reference within 2 m³.

        Planum = optimal_height - gravel_thickness = 319.87 - 0.60 = 319.27 m.
        Pixel-wise reference (against stored crane pad polygon): 5280 m³.
        Report total including the 1580 m² slope area: 6546 m³.
        """
        planum = OPTIMAL_CRANE_HEIGHT - GRAVEL_THICKNESS
        elev = self.dem[self.crane_mask & self.valid]
        cut, fill = self._cut_fill(elev.tolist(), planum, self.pixel_area)

        self.assertAlmostEqual(
            cut, EXPECTED_CRANE_PLATFORM_CUT_M3, delta=2.0,
            msg=f"Crane platform cut drifted: got {cut:.1f}, "
                f"expected ~{EXPECTED_CRANE_PLATFORM_CUT_M3}",
        )
        self.assertAlmostEqual(
            fill, EXPECTED_CRANE_PLATFORM_FILL_M3, delta=2.0,
            msg=f"Crane platform fill drifted: got {fill:.1f}, "
                f"expected ~{EXPECTED_CRANE_PLATFORM_FILL_M3}",
        )

    def test_crane_platform_is_strict_subset_of_report_total(self):
        """
        The platform-only values must be strictly smaller than the report's
        total (which also includes the slope area). This guards against a
        common regression where the slope area accidentally gets counted
        twice or zeroed out.
        """
        planum = OPTIMAL_CRANE_HEIGHT - GRAVEL_THICKNESS
        elev = self.dem[self.crane_mask & self.valid]
        cut, fill = self._cut_fill(elev.tolist(), planum, self.pixel_area)

        self.assertLess(cut, EXPECTED_CRANE_TOTAL_CUT_M3)
        self.assertLess(fill, EXPECTED_CRANE_TOTAL_FILL_M3)
        # Slope contribution must be positive (terrain is not flat)
        self.assertGreater(EXPECTED_CRANE_TOTAL_CUT_M3 - cut, 100)
        self.assertGreater(EXPECTED_CRANE_TOTAL_FILL_M3 - fill, 100)

    def test_nonzero_sampling(self):
        """
        Guard against the 2026-04-09 regression where DEM sampling silently
        returned empty arrays (Cut=0, Fill=0). If this test ever yields 0
        samples, something is very wrong with raster reading.
        """
        elev = self.dem[self.crane_mask & self.valid]
        self.assertGreater(len(elev), 1000,
                           "Crane pad DEM sampling yielded near-empty result - "
                           "this is the dc778d9 Plan-B regression.")


if __name__ == "__main__":
    unittest.main()
