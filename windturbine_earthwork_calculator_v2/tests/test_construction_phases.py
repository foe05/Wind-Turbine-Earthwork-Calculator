"""Unit tests for core/construction_phases.py — pure Python, no QGIS."""

import importlib.util
import os
import unittest


_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core", "construction_phases.py",
)


def _load():
    import sys
    name = "construction_phases_isolated"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestPhase(unittest.TestCase):

    def test_duration_must_be_positive(self):
        cp = _load()
        with self.assertRaises(ValueError):
            cp.Phase("x", start_day=0, duration_days=0)

    def test_negative_start_rejected(self):
        cp = _load()
        with self.assertRaises(ValueError):
            cp.Phase("x", start_day=-1, duration_days=5)

    def test_share_out_of_range_rejected(self):
        cp = _load()
        with self.assertRaises(ValueError):
            cp.Phase("x", start_day=0, duration_days=5, cut_share=1.5)
        with self.assertRaises(ValueError):
            cp.Phase("x", start_day=0, duration_days=5, fill_share=-0.1)

    def test_end_day(self):
        cp = _load()
        p = cp.Phase("x", start_day=3, duration_days=4)
        self.assertEqual(p.end_day, 7)


class TestPhasePlanner(unittest.TestCase):

    def test_empty_phases_rejected(self):
        cp = _load()
        with self.assertRaises(ValueError):
            cp.PhasePlanner([])

    def test_share_sum_above_one_rejected(self):
        cp = _load()
        with self.assertRaises(ValueError):
            cp.PhasePlanner([
                cp.Phase("a", 0, 1, cut_share=0.7),
                cp.Phase("b", 1, 1, cut_share=0.7),
            ])

    def test_simple_distribution(self):
        cp = _load()
        planner = cp.PhasePlanner([
            cp.Phase("a", 0, 2, cut_share=0.4, fill_share=0.5),
            cp.Phase("b", 2, 3, cut_share=0.6, fill_share=0.5),
        ], cut_cost_per_m3=10.0, fill_cost_per_m3=20.0, co2_per_m3_moved=2.0)
        plan = planner.plan(total_cut_m3=100.0, total_fill_m3=200.0)
        self.assertEqual(len(plan.phases), 2)
        self.assertAlmostEqual(plan.phases[0].cut_m3, 40.0)
        self.assertAlmostEqual(plan.phases[0].fill_m3, 100.0)
        self.assertAlmostEqual(plan.phases[1].cut_m3, 60.0)
        self.assertAlmostEqual(plan.phases[1].fill_m3, 100.0)
        # Cost phase a = 40*10 + 100*20 = 400+2000 = 2400; CO2 = (40+100)*2 = 280
        self.assertAlmostEqual(plan.phases[0].cost_eur, 2400.0)
        self.assertAlmostEqual(plan.phases[0].co2_kg, 280.0)
        self.assertEqual(plan.phases[0].end_day, 2)
        self.assertEqual(plan.total_duration_days, 5)
        # Fully assigned
        self.assertAlmostEqual(plan.unassigned_cut_m3, 0.0)
        self.assertAlmostEqual(plan.unassigned_fill_m3, 0.0)

    def test_partial_plan_records_remainder(self):
        cp = _load()
        planner = cp.PhasePlanner([
            cp.Phase("only", 0, 5, cut_share=0.7, fill_share=0.6),
        ])
        plan = planner.plan(total_cut_m3=100, total_fill_m3=100)
        self.assertAlmostEqual(plan.phases[0].cut_m3, 70.0)
        self.assertAlmostEqual(plan.unassigned_cut_m3, 30.0)
        self.assertAlmostEqual(plan.unassigned_fill_m3, 40.0)

    def test_negative_totals_rejected(self):
        cp = _load()
        planner = cp.PhasePlanner([cp.Phase("x", 0, 1, cut_share=1.0)])
        with self.assertRaises(ValueError):
            planner.plan(total_cut_m3=-1, total_fill_m3=0)

    def test_total_aggregates(self):
        cp = _load()
        planner = cp.PhasePlanner([
            cp.Phase("a", 0, 1, cut_share=0.5),
            cp.Phase("b", 1, 1, cut_share=0.5),
        ], cut_cost_per_m3=10.0)
        plan = planner.plan(total_cut_m3=100, total_fill_m3=0)
        self.assertAlmostEqual(plan.total_cost_eur, 1000.0)

    def test_default_phases_smoke(self):
        cp = _load()
        plan = cp.PhasePlanner(cp.default_phases()).plan(
            total_cut_m3=1000, total_fill_m3=500,
        )
        # 4 phases, shares sum to 1, 19-day duration
        self.assertEqual(len(plan.phases), 4)
        self.assertEqual(plan.total_duration_days, 19)
        self.assertAlmostEqual(plan.unassigned_cut_m3, 0.0, places=6)
        self.assertAlmostEqual(plan.unassigned_fill_m3, 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
