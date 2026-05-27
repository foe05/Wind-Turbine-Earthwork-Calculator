"""
Unit tests for core/placement_constraints.py

These tests only require shapely (already a transitive dep of dxf_importer);
they do not import QGIS, so they run in any plain Python 3.10+ environment.

We import the module by file path rather than via ``from ..core...`` so that
``core/__init__.py`` (which eagerly imports surface_types → qgis.core) is not
triggered. This lets the tests run in a plain Python environment.
"""

import importlib.util
import math
import os
import unittest


try:
    from shapely.geometry import Point, Polygon, LineString  # noqa: F401
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False


_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core",
    "placement_constraints.py",
)


def _load_pc_module():
    """Load core/placement_constraints.py without triggering core/__init__.py."""
    import sys
    mod_name = "placement_constraints_isolated"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    # Register before exec_module: @dataclass resolution needs cls.__module__
    # to be reachable via sys.modules.
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(SHAPELY_AVAILABLE, "shapely not installed")
class TestConstraintLayer(unittest.TestCase):

    def test_negative_distance_rejected(self):
        pc = _load_pc_module()
        with self.assertRaises(ValueError):
            pc.ConstraintLayer(name="x", geometries=[], min_distance_m=-1.0)

    def test_zero_distance_allowed(self):
        pc = _load_pc_module()
        c = pc.ConstraintLayer(name="x", geometries=[], min_distance_m=0.0)
        self.assertEqual(c.min_distance_m, 0.0)


@unittest.skipUnless(SHAPELY_AVAILABLE, "shapely not installed")
class TestPlacementValidator(unittest.TestCase):

    def _make_validator(self, layers):
        pc = _load_pc_module()
        return pc.PlacementValidator(layers)

    def test_no_constraints_position_is_always_valid(self):
        validator = self._make_validator([])
        self.assertEqual(validator.check_position(0.0, 0.0), [])
        self.assertTrue(validator.is_position_valid(123.4, 567.8))

    def test_far_from_obstacle_is_valid(self):
        pc = _load_pc_module()
        building = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
        validator = self._make_validator([
            pc.ConstraintLayer("buildings", [building], min_distance_m=50.0),
        ])
        # 100 m away should clear a 50 m buffer easily
        self.assertEqual(validator.check_position(200, 200), [])

    def test_inside_buffer_reports_hard_violation(self):
        pc = _load_pc_module()
        building = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
        validator = self._make_validator([
            pc.ConstraintLayer("buildings", [building], min_distance_m=50.0),
        ])
        violations = validator.check_position(30, 5)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].layer_name, "buildings")
        self.assertEqual(violations[0].severity, pc.Severity.HARD)
        # Distance from (30, 5) to the right edge of the building (x=10) is 20
        self.assertAlmostEqual(violations[0].actual_distance_m, 20.0, places=4)
        self.assertAlmostEqual(violations[0].required_distance_m, 50.0)
        self.assertAlmostEqual(violations[0].shortfall_m, 30.0, places=4)

    def test_soft_violation_marked_correctly(self):
        pc = _load_pc_module()
        road = LineString([(0, 0), (100, 0)])
        validator = self._make_validator([
            pc.ConstraintLayer("roads", [road], min_distance_m=20.0,
                               severity=pc.Severity.SOFT),
        ])
        violations = validator.check_position(50, 5)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].severity, pc.Severity.SOFT)

    def test_is_valid_with_only_soft_violations(self):
        pc = _load_pc_module()
        road = LineString([(0, 0), (100, 0)])
        validator = self._make_validator([
            pc.ConstraintLayer("roads", [road], min_distance_m=20.0,
                               severity=pc.Severity.SOFT),
        ])
        # By default soft violations are tolerated
        self.assertTrue(validator.is_position_valid(50, 5))
        # But not if explicitly disallowed
        self.assertFalse(validator.is_position_valid(
            50, 5, allow_soft_violations=False))

    def test_hard_and_soft_both_reported(self):
        pc = _load_pc_module()
        building = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
        road = LineString([(0, 5), (100, 5)])
        validator = self._make_validator([
            pc.ConstraintLayer("buildings", [building], min_distance_m=50.0,
                               severity=pc.Severity.HARD),
            pc.ConstraintLayer("roads", [road], min_distance_m=20.0,
                               severity=pc.Severity.SOFT),
        ])
        violations = validator.check_position(25, 5)
        # Should violate both (building 15 m away, road right next to it)
        layer_names = sorted(v.layer_name for v in violations)
        self.assertEqual(layer_names, ["buildings", "roads"])

    def test_empty_layer_never_violates(self):
        pc = _load_pc_module()
        validator = self._make_validator([
            pc.ConstraintLayer("empty", [], min_distance_m=999.0),
        ])
        self.assertTrue(validator.is_position_valid(0, 0))


@unittest.skipUnless(SHAPELY_AVAILABLE, "shapely not installed")
class TestSuggestNearestValid(unittest.TestCase):

    def _validator_blocking_origin(self, radius=30.0):
        """Single circular building centred at (0,0); 30 m clearance required."""
        pc = _load_pc_module()
        # Approximate a circle as a 36-gon
        circle = Point(0, 0).buffer(5.0, quad_segs=9)
        return pc.PlacementValidator([
            pc.ConstraintLayer("buildings", [circle], min_distance_m=radius),
        ])

    def test_origin_returns_itself_when_valid(self):
        pc = _load_pc_module()
        validator = pc.PlacementValidator([
            pc.ConstraintLayer("buildings", [Point(1000, 1000)], min_distance_m=5.0),
        ])
        suggestion = validator.suggest_nearest_valid(0, 0, search_radius_m=20)
        self.assertEqual(suggestion, (0, 0))

    def test_finds_nearby_valid_point(self):
        validator = self._validator_blocking_origin(radius=20.0)
        # (0, 0) is blocked. Suggestion must be at least ~20 m from the circle's
        # edge (~5 m radius), so >= 25 m from origin (the boundary is inclusive
        # since the validator's check is strict `<`).
        suggestion = validator.suggest_nearest_valid(
            0, 0, search_radius_m=50.0, grid_step_m=5.0
        )
        self.assertIsNotNone(suggestion)
        x, y = suggestion
        distance_from_origin = math.hypot(x, y)
        # Allow slight under-25 because the circle is polygon-approximated
        # (9-quad ~= 36-gon vertices are slightly inside true r=5)
        self.assertGreaterEqual(
            distance_from_origin, 24.5,
            f"Expected suggestion close to or beyond 25 m from origin, got {distance_from_origin}"
        )
        # And the validator must now consider it valid
        self.assertTrue(validator.is_position_valid(x, y))

    def test_returns_none_when_no_valid_within_radius(self):
        validator = self._validator_blocking_origin(radius=200.0)
        # 200 m buffer + 5 m circle = need > 205 m, but search radius is only 50 m
        suggestion = validator.suggest_nearest_valid(
            0, 0, search_radius_m=50.0, grid_step_m=10.0
        )
        self.assertIsNone(suggestion)

    def test_negative_step_rejected(self):
        validator = self._validator_blocking_origin()
        with self.assertRaises(ValueError):
            validator.suggest_nearest_valid(0, 0, grid_step_m=-1.0)


@unittest.skipUnless(SHAPELY_AVAILABLE, "shapely not installed")
class TestRingPoints(unittest.TestCase):

    def test_ring_0_is_centre_only(self):
        _ring_points = _load_pc_module()._ring_points
        pts = list(_ring_points(10, 20, ring=0, step=1.0))
        self.assertEqual(pts, [(10, 20)])

    def test_ring_1_has_8_points(self):
        _ring_points = _load_pc_module()._ring_points
        pts = list(_ring_points(0, 0, ring=1, step=1.0))
        self.assertEqual(len(pts), 8)
        # All at Chebyshev distance 1 from origin
        for x, y in pts:
            self.assertEqual(max(abs(x), abs(y)), 1)

    def test_ring_N_has_8N_points(self):
        _ring_points = _load_pc_module()._ring_points
        for n in (2, 3, 5):
            pts = list(_ring_points(0, 0, ring=n, step=1.0))
            self.assertEqual(len(pts), 8 * n,
                             f"Ring {n} should have {8*n} points, got {len(pts)}")


if __name__ == "__main__":
    unittest.main()
