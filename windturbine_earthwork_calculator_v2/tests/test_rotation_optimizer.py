"""
Unit tests for core/rotation_optimizer.py — pure Python, no QGIS.
"""

import importlib.util
import math
import os
import unittest


_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core", "rotation_optimizer.py",
)


def _load():
    import sys
    name = "rotation_optimizer_isolated"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestPolygonCentroid(unittest.TestCase):

    def test_unit_square_centroid(self):
        ro = _load()
        c = ro.polygon_centroid([(0, 0), (2, 0), (2, 2), (0, 2)])
        self.assertAlmostEqual(c[0], 1.0)
        self.assertAlmostEqual(c[1], 1.0)

    def test_closing_duplicate_tolerated(self):
        ro = _load()
        c = ro.polygon_centroid([(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)])
        self.assertAlmostEqual(c[0], 1.0)
        self.assertAlmostEqual(c[1], 1.0)

    def test_single_point(self):
        ro = _load()
        c = ro.polygon_centroid([(5, 7)])
        self.assertEqual(c, (5.0, 7.0))

    def test_empty_raises(self):
        ro = _load()
        with self.assertRaises(ValueError):
            ro.polygon_centroid([])


class TestRotatePoints(unittest.TestCase):

    def test_rotate_90_around_origin(self):
        ro = _load()
        rotated = ro.rotate_points([(1, 0)], 90.0, pivot=(0, 0))
        self.assertAlmostEqual(rotated[0][0], 0.0, places=6)
        self.assertAlmostEqual(rotated[0][1], 1.0, places=6)

    def test_rotate_about_centroid_preserves_centroid(self):
        ro = _load()
        square = [(0, 0), (2, 0), (2, 2), (0, 2)]
        rotated = ro.rotate_points(square, 37.0)
        c0 = ro.polygon_centroid(square)
        c1 = ro.polygon_centroid(rotated)
        self.assertAlmostEqual(c0[0], c1[0], places=6)
        self.assertAlmostEqual(c0[1], c1[1], places=6)

    def test_rotation_preserves_edge_lengths(self):
        ro = _load()
        square = [(0, 0), (4, 0), (4, 1), (0, 1)]  # 4×1 rectangle
        rotated = ro.rotate_points(square, 30.0)

        def dist(a, b):
            return math.hypot(a[0] - b[0], a[1] - b[1])

        for i in range(len(square)):
            j = (i + 1) % len(square)
            self.assertAlmostEqual(
                dist(square[i], square[j]), dist(rotated[i], rotated[j]), places=6
            )

    def test_360_is_identity(self):
        ro = _load()
        pts = [(1.5, 2.5), (3.0, 4.0)]
        rotated = ro.rotate_points(pts, 360.0, pivot=(0, 0))
        for (x0, y0), (x1, y1) in zip(pts, rotated):
            self.assertAlmostEqual(x0, x1, places=6)
            self.assertAlmostEqual(y0, y1, places=6)


class TestDefaultAngles(unittest.TestCase):

    def test_default_range(self):
        ro = _load()
        angles = ro.default_angles()
        self.assertEqual(angles[0], 0.0)
        self.assertEqual(angles[-1], 165.0)  # last below 180
        self.assertEqual(len(angles), 12)    # 0,15,...,165

    def test_custom_step_max(self):
        ro = _load()
        angles = ro.default_angles(step_deg=90.0, max_deg=360.0)
        self.assertEqual(angles, [0.0, 90.0, 180.0, 270.0])

    def test_invalid(self):
        ro = _load()
        with self.assertRaises(ValueError):
            ro.default_angles(step_deg=0)
        with self.assertRaises(ValueError):
            ro.default_angles(max_deg=0)


class TestRotationOptimizer(unittest.TestCase):

    def test_picks_lowest_metric(self):
        ro = _load()
        # Synthetic metric: minimal at 90°. evaluate returns |angle-90|.
        opt = ro.RotationOptimizer(angles_deg=[0, 45, 90, 135])
        square = [(0, 0), (2, 0), (2, 2), (0, 2)]

        def evaluate(rotated):
            # Recover the angle from the optimizer is not possible here, so we
            # encode a metric based on a known reference vertex direction.
            # Simpler: use a closure counter mapping is overkill; instead we
            # compute a metric from the first vertex angle relative to centroid.
            cx, cy = ro.polygon_centroid(rotated)
            x, y = rotated[0]
            ang = math.degrees(math.atan2(y - cy, x - cx)) % 360.0
            # original first vertex (0,0) points at 225° from centroid (1,1);
            # after rotation by k°, it's 225+k. We want the rotation closest to
            # making it 315° (i.e. rotation 90).
            target = 315.0
            metric = abs(((ang - target + 180) % 360) - 180)
            return metric, f"ang={ang:.1f}"

        best = opt.optimize(square, evaluate)
        self.assertEqual(best.angle_deg, 90.0)
        self.assertIsNotNone(best.payload)

    def test_payload_returned(self):
        ro = _load()
        opt = ro.RotationOptimizer(angles_deg=[0, 30])
        result = opt.optimize(
            [(0, 0), (1, 0), (0, 1)],
            lambda r: (0.0 if r else 1.0, {"n": len(r)}),
        )
        self.assertEqual(result.payload, {"n": 3})

    def test_all_evaluations_fail_raises(self):
        ro = _load()
        opt = ro.RotationOptimizer(angles_deg=[0, 30, 60])

        def boom(_rotated):
            raise RuntimeError("nope")

        with self.assertRaises(ValueError):
            opt.optimize([(0, 0), (1, 0), (0, 1)], boom)

    def test_skips_failing_angles(self):
        ro = _load()
        opt = ro.RotationOptimizer(angles_deg=[0, 30, 60])
        calls = {"n": 0}

        def evaluate(rotated):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("first fails")
            return float(calls["n"]), None

        best = opt.optimize([(0, 0), (1, 0), (0, 1)], evaluate)
        # First angle failed; best is the cheapest of the survivors (metric 2)
        self.assertAlmostEqual(best.metric, 2.0)

    def test_empty_angles_rejected(self):
        ro = _load()
        with self.assertRaises(ValueError):
            ro.RotationOptimizer(angles_deg=[])


if __name__ == "__main__":
    unittest.main()
