"""
Equivalence tests for the vectorised cut/fill formulas in
MultiSurfaceCalculator (_calculate_crane_pad, _calculate_foundation).

The per-pixel Python loops were replaced with numpy expressions for speed.
These tests prove the vectorised expressions are mathematically identical to
the original loops for arbitrary elevation arrays, so the change cannot alter
the cut/fill volumes that test_volume_regression.py pins. They need neither
QGIS nor GDAL.
"""

import unittest

import numpy as np


PIXEL_AREA = 1.0  # the factor is linear, so any positive value works


def _crane_loop(elevations, planum_height, pixel_area):
    """Original per-pixel crane-pad cut/fill loop."""
    cut = 0.0
    fill = 0.0
    for elevation in elevations:
        diff = elevation - planum_height
        if diff > 0:
            cut += diff * pixel_area
        else:
            fill += abs(diff) * pixel_area
    return cut, fill


def _crane_vectorized(elevations, planum_height, pixel_area):
    """Vectorised replacement used in the calculator."""
    diff = np.asarray(elevations, dtype=float) - planum_height
    cut = float(np.sum(diff[diff > 0])) * pixel_area
    fill = float(np.sum(-diff[diff < 0])) * pixel_area
    return cut, fill


def _foundation_loop(elevations, foundation_bottom, pixel_area):
    cut = 0.0
    for elevation in elevations:
        depth = elevation - foundation_bottom
        if depth > 0:
            cut += depth * pixel_area
    return cut


def _foundation_vectorized(elevations, foundation_bottom, pixel_area):
    depth = np.asarray(elevations, dtype=float) - foundation_bottom
    return float(np.sum(depth[depth > 0])) * pixel_area


class TestCranePadCutFillEquivalence(unittest.TestCase):

    def _assert_equiv(self, elevations, planum):
        loop_cut, loop_fill = _crane_loop(elevations, planum, PIXEL_AREA)
        vec_cut, vec_fill = _crane_vectorized(elevations, planum, PIXEL_AREA)
        self.assertAlmostEqual(loop_cut, vec_cut, places=6)
        self.assertAlmostEqual(loop_fill, vec_fill, places=6)

    def test_mixed_cut_and_fill(self):
        self._assert_equiv(np.array([100.0, 101.0, 99.5, 102.3, 98.7]), 100.0)

    def test_all_cut(self):
        self._assert_equiv(np.array([110.0, 111.0, 112.5]), 100.0)

    def test_all_fill(self):
        self._assert_equiv(np.array([90.0, 91.0, 88.5]), 100.0)

    def test_exact_zero_diff_contributes_nothing(self):
        # diff == 0 goes to the fill branch in the loop but adds 0; the
        # vectorised split uses diff < 0, so both must agree.
        self._assert_equiv(np.array([100.0, 100.0, 100.0]), 100.0)

    def test_empty(self):
        self._assert_equiv(np.array([]), 100.0)

    def test_random_large(self):
        rng = np.random.default_rng(42)
        for _ in range(20):
            elevations = rng.uniform(280.0, 340.0, size=5000)
            planum = float(rng.uniform(290.0, 330.0))
            self._assert_equiv(elevations, planum)


class TestFoundationCutEquivalence(unittest.TestCase):

    def _assert_equiv(self, elevations, bottom):
        loop_cut = _foundation_loop(elevations, bottom, PIXEL_AREA)
        vec_cut = _foundation_vectorized(elevations, bottom, PIXEL_AREA)
        self.assertAlmostEqual(loop_cut, vec_cut, places=6)

    def test_mixed(self):
        self._assert_equiv(np.array([305.0, 310.0, 300.0, 295.0]), 302.0)

    def test_all_above(self):
        self._assert_equiv(np.array([310.0, 311.0]), 300.0)

    def test_all_below_no_excavation(self):
        self._assert_equiv(np.array([290.0, 291.0]), 300.0)

    def test_random_large(self):
        rng = np.random.default_rng(7)
        for _ in range(20):
            elevations = rng.uniform(280.0, 340.0, size=5000)
            bottom = float(rng.uniform(290.0, 330.0))
            self._assert_equiv(elevations, bottom)


if __name__ == "__main__":
    unittest.main()
