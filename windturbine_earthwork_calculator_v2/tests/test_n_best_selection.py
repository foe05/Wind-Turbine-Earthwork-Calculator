"""
Unit tests for MultiSurfaceCalculator._select_diverse_candidates.

Only the pure-Python candidate-selection helper is tested here; the full
find_n_best() sweep needs QGIS (calculate_scenario samples a DEM). We load the
static method by file path so core/__init__.py (which imports qgis.core) is not
triggered, then exercise the selection/spacing logic with plain tuples.
"""

import importlib.util
import os
import types
import unittest


_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core",
    "multi_surface_calculator.py",
)


def _load_select_helper():
    """Extract _select_diverse_candidates without importing the qgis-heavy module.

    The function is pure Python (only sorting + arithmetic), so we compile just
    that function's source in isolation.
    """
    import ast
    with open(_MODULE_PATH, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    func_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_select_diverse_candidates":
            func_node = node
            break
    if func_node is None:
        raise AssertionError("_select_diverse_candidates not found in source")

    # Strip the @staticmethod decorator so it compiles as a free function.
    func_node.decorator_list = []
    module = ast.Module(body=[func_node], type_ignores=[])
    ast.fix_missing_locations(module)
    code = compile(module, filename="<select_helper>", mode="exec")
    namespace: dict = {}
    exec(code, namespace)
    return namespace["_select_diverse_candidates"]


class TestSelectDiverseCandidates(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.select = staticmethod(_load_select_helper())

    def test_returns_best_first(self):
        # (metric, height, payload) — lower metric is better
        scored = [
            (300.0, 319.5, "c"),
            (100.0, 320.0, "a"),
            (200.0, 320.5, "b"),
        ]
        result = self.select(scored, n=3, min_spacing_m=0.0)
        # Best-first ordering by metric
        heights = [h for h, _ in result]
        payloads = [p for _, p in result]
        self.assertEqual(payloads, ["a", "b", "c"])
        self.assertEqual(heights, [320.0, 320.5, 319.5])

    def test_limits_to_n(self):
        scored = [(float(i), 300.0 + i, f"p{i}") for i in range(10)]
        result = self.select(scored, n=3, min_spacing_m=0.0)
        self.assertEqual(len(result), 3)
        # The three lowest metrics are i=0,1,2
        self.assertEqual([p for _, p in result], ["p0", "p1", "p2"])

    def test_spacing_filter_skips_adjacent(self):
        # Five near-optimal heights 0.05 m apart; with 0.5 m spacing only the
        # best one survives within each 0.5 m window.
        scored = [
            (10.0, 319.80, "best"),
            (11.0, 319.85, "close1"),
            (12.0, 319.90, "close2"),
            (13.0, 320.50, "far1"),   # > 0.5 m from best
            (14.0, 321.20, "far2"),   # > 0.5 m from far1
        ]
        result = self.select(scored, n=5, min_spacing_m=0.5)
        payloads = [p for _, p in result]
        # 'close1'/'close2' are within 0.5 m of 'best' → skipped
        self.assertEqual(payloads, ["best", "far1", "far2"])

    def test_spacing_zero_keeps_all_up_to_n(self):
        scored = [
            (10.0, 319.80, "a"),
            (11.0, 319.85, "b"),
            (12.0, 319.90, "c"),
        ]
        result = self.select(scored, n=5, min_spacing_m=0.0)
        self.assertEqual(len(result), 3)

    def test_spacing_respects_already_selected_not_just_previous(self):
        # 320.0 selected first (best). 320.3 is 0.3 from it (skip with 0.5).
        # 320.6 is 0.6 from 320.0 but only 0.3 from 320.3 — but 320.3 was NOT
        # selected, so 320.6 should be accepted (0.6 >= 0.5 from 320.0).
        scored = [
            (1.0, 320.0, "a"),
            (2.0, 320.3, "b"),
            (3.0, 320.6, "c"),
        ]
        result = self.select(scored, n=5, min_spacing_m=0.5)
        payloads = [p for _, p in result]
        self.assertEqual(payloads, ["a", "c"])

    def test_empty_input(self):
        self.assertEqual(self.select([], n=3, min_spacing_m=0.0), [])


if __name__ == "__main__":
    unittest.main()
