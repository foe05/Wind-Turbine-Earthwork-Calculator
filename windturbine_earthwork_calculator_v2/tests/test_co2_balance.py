"""
Unit tests for core/co2_balance.py — pure Python, no QGIS.
"""

import importlib.util
import os
import unittest


_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core", "co2_balance.py",
)


def _load():
    import sys
    name = "co2_balance_isolated"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestEmissionFactors(unittest.TestCase):

    def test_negative_factor_rejected(self):
        co2 = _load()
        with self.assertRaises(ValueError):
            co2.EmissionFactors(concrete_kg_per_m3=-1)


class TestCO2Calculator(unittest.TestCase):

    def test_zero_input_zero_output(self):
        co2 = _load()
        res = co2.CO2Calculator().compute()
        self.assertEqual(res.total_kg, 0.0)

    def test_excavation_only(self):
        co2 = _load()
        factors = co2.EmissionFactors(excavation_kg_per_m3=2.0)
        res = co2.CO2Calculator(factors).compute(cut_m3=100, fill_m3=50)
        # moved = 150 × 2.0 = 300
        self.assertAlmostEqual(res.excavation_kg, 300.0)
        self.assertAlmostEqual(res.total_kg, 300.0)

    def test_haul_uses_cut_plus_gravel(self):
        co2 = _load()
        factors = co2.EmissionFactors(
            excavation_kg_per_m3=0.0, gravel_production_kg_per_m3=0.0,
            haul_kg_per_m3_km=0.1,
        )
        res = co2.CO2Calculator(factors).compute(
            cut_m3=100, gravel_m3=50, haul_distance_km=10
        )
        # (100 + 50) × 10 km × 0.1 = 150
        self.assertAlmostEqual(res.haul_kg, 150.0)

    def test_concrete_and_steel(self):
        co2 = _load()
        factors = co2.EmissionFactors(
            excavation_kg_per_m3=0.0, concrete_kg_per_m3=300.0, steel_kg_per_kg=2.0,
        )
        res = co2.CO2Calculator(factors).compute(concrete_m3=10, steel_kg=500)
        self.assertAlmostEqual(res.concrete_kg, 3000.0)
        self.assertAlmostEqual(res.steel_kg, 1000.0)
        self.assertAlmostEqual(res.total_kg, 4000.0)

    def test_total_tonnes(self):
        co2 = _load()
        factors = co2.EmissionFactors(excavation_kg_per_m3=10.0)
        res = co2.CO2Calculator(factors).compute(cut_m3=100)  # 1000 kg
        self.assertAlmostEqual(res.total_t, 1.0)

    def test_full_breakdown_sums(self):
        co2 = _load()
        res = co2.CO2Calculator().compute(
            cut_m3=1000, fill_m3=500, gravel_m3=200,
            haul_distance_km=5, concrete_m3=50, steel_kg=8000,
        )
        bd = res.as_breakdown()
        component_sum = (bd["excavation_kg"] + bd["haul_kg"] + bd["gravel_kg"]
                         + bd["concrete_kg"] + bd["steel_kg"])
        self.assertAlmostEqual(component_sum, bd["total_kg"], places=1)
        self.assertGreater(bd["total_kg"], 0.0)

    def test_negative_input_rejected(self):
        co2 = _load()
        with self.assertRaises(ValueError):
            co2.CO2Calculator().compute(cut_m3=-5)


if __name__ == "__main__":
    unittest.main()
