"""Unit tests for core/strata_quantities.py — pure Python, no QGIS."""

import importlib.util
import os
import unittest


_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core", "strata_quantities.py",
)


def _load():
    import sys
    name = "strata_quantities_isolated"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestStratumLayer(unittest.TestCase):

    def test_negative_thickness_rejected(self):
        sq = _load()
        with self.assertRaises(ValueError):
            sq.StratumLayer(name="x", thickness_m=0)
        with self.assertRaises(ValueError):
            sq.StratumLayer(name="x", thickness_m=-1)

    def test_negative_cost_rejected(self):
        sq = _load()
        with self.assertRaises(ValueError):
            sq.StratumLayer(name="x", thickness_m=1, cost_per_m3=-1)


class TestStrataCalculatorSplit(unittest.TestCase):

    def _three_layer(self, sq):
        return sq.StrataCalculator([
            sq.StratumLayer(name="top", thickness_m=0.3, cost_per_m3=10, co2_kg_per_m3=2,
                            disposal_cost_per_m3=5),
            sq.StratumLayer(name="mid", thickness_m=0.4, cost_per_m3=20, co2_kg_per_m3=4),
            sq.StratumLayer(name="bot", thickness_m=0.3, cost_per_m3=30, co2_kg_per_m3=6),
        ])

    def test_empty_layers_rejected(self):
        sq = _load()
        with self.assertRaises(ValueError):
            sq.StrataCalculator([])

    def test_total_thickness(self):
        sq = _load()
        self.assertAlmostEqual(self._three_layer(sq).total_thickness_m, 1.0)

    def test_zero_volume_returns_empty_result(self):
        sq = _load()
        res = self._three_layer(sq).split(volume_m3=0.0, area_m2=100.0)
        self.assertEqual(res.layers, [])
        self.assertEqual(res.total_volume_m3, 0.0)

    def test_shallow_cut_only_top_layer(self):
        sq = _load()
        # depth = 0.1 m → only "top" layer, partial thickness
        res = self._three_layer(sq).split(volume_m3=10.0, area_m2=100.0,
                                          mode=sq.StratumMode.CUT)
        self.assertEqual(len(res.layers), 1)
        self.assertEqual(res.layers[0].name, "top")
        self.assertAlmostEqual(res.layers[0].depth_m, 0.1)
        self.assertAlmostEqual(res.layers[0].volume_m3, 10.0)
        # cost = 10 m³ × (10 + 5 disposal) = 150
        self.assertAlmostEqual(res.layers[0].cost_eur, 150.0)
        # co2 = 10 × 2 = 20
        self.assertAlmostEqual(res.layers[0].co2_kg, 20.0)
        self.assertEqual(res.remainder_m3, 0.0)

    def test_medium_cut_peels_top_then_mid(self):
        sq = _load()
        # depth = 0.5 m → all of top (0.3) + 0.2 of mid
        res = self._three_layer(sq).split(volume_m3=50.0, area_m2=100.0,
                                          mode=sq.StratumMode.CUT)
        self.assertEqual([q.name for q in res.layers], ["top", "mid"])
        self.assertAlmostEqual(res.layers[0].depth_m, 0.3)
        self.assertAlmostEqual(res.layers[1].depth_m, 0.2)
        # volumes
        self.assertAlmostEqual(res.layers[0].volume_m3, 30.0)
        self.assertAlmostEqual(res.layers[1].volume_m3, 20.0)
        self.assertAlmostEqual(res.total_volume_m3, 50.0)

    def test_exact_full_stack(self):
        sq = _load()
        # depth = 1.0 m → exactly fills all 3 layers, no remainder
        res = self._three_layer(sq).split(volume_m3=100.0, area_m2=100.0,
                                          mode=sq.StratumMode.CUT)
        self.assertEqual(len(res.layers), 3)
        self.assertAlmostEqual(res.total_volume_m3, 100.0)
        self.assertEqual(res.remainder_m3, 0.0)

    def test_overflow_records_remainder(self):
        sq = _load()
        # depth = 1.5 m → stack only 1.0 m → 0.5 m × 100 m² = 50 m³ remainder
        res = self._three_layer(sq).split(volume_m3=150.0, area_m2=100.0,
                                          mode=sq.StratumMode.CUT)
        self.assertEqual(len(res.layers), 3)
        self.assertAlmostEqual(res.total_volume_m3, 100.0)
        self.assertAlmostEqual(res.remainder_m3, 50.0)

    def test_fill_uses_reversed_order(self):
        sq = _load()
        # Fill consumes from the bottom up: bot first, then mid.
        res = self._three_layer(sq).split(volume_m3=50.0, area_m2=100.0,
                                          mode=sq.StratumMode.FILL)
        self.assertEqual([q.name for q in res.layers], ["bot", "mid"])

    def test_fill_does_not_apply_disposal(self):
        sq = _load()
        # Build only the bottom layer: cost = 30, NOT 30 + 0 (no disposal cfg for bot anyway).
        # Verify by giving top a disposal cost and using fill that never touches top.
        calc = self._three_layer(sq)
        cut_res = calc.split(volume_m3=10.0, area_m2=100.0, mode=sq.StratumMode.CUT)
        fill_res = calc.split(volume_m3=10.0, area_m2=100.0, mode=sq.StratumMode.FILL)
        # Cut hits top (cost 10 + disposal 5 = 15); fill hits bot (cost 30, no disposal added)
        self.assertAlmostEqual(cut_res.total_cost_eur, 10.0 * 15.0)
        self.assertAlmostEqual(fill_res.total_cost_eur, 10.0 * 30.0)

    def test_negative_volume_rejected(self):
        sq = _load()
        with self.assertRaises(ValueError):
            self._three_layer(sq).split(volume_m3=-1, area_m2=10)

    def test_zero_area_rejected(self):
        sq = _load()
        with self.assertRaises(ValueError):
            self._three_layer(sq).split(volume_m3=10, area_m2=0)


class TestDefaultStack(unittest.TestCase):

    def test_default_stack_is_valid(self):
        sq = _load()
        calc = sq.StrataCalculator(sq.default_stack())
        # ~1.0 m total: 0.3 + 0.4 + 0.3
        self.assertAlmostEqual(calc.total_thickness_m, 1.0)
        # Smoke-split 50 m³ over 100 m² → 0.5 m depth
        res = calc.split(volume_m3=50.0, area_m2=100.0)
        self.assertEqual([q.name for q in res.layers],
                         ["Mutterboden", "Frostschutzschicht"])


if __name__ == "__main__":
    unittest.main()
