"""
Unit tests for core/mass_haul.py — pure Python, no QGIS/GDAL.
"""

import importlib.util
import os
import unittest


_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core", "mass_haul.py",
)


def _load():
    import sys
    name = "mass_haul_isolated"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestMassHaulStation(unittest.TestCase):

    def test_negative_rejected(self):
        mh = _load()
        with self.assertRaises(ValueError):
            mh.MassHaulStation(station_m=0, cut_m3=-1)


class TestMassHaulDiagram(unittest.TestCase):

    def test_invalid_compaction(self):
        mh = _load()
        with self.assertRaises(ValueError):
            mh.MassHaulDiagram([], compaction_factor=0.0)
        with self.assertRaises(ValueError):
            mh.MassHaulDiagram([], compaction_factor=1.5)

    def test_empty(self):
        mh = _load()
        res = mh.MassHaulDiagram([]).compute()
        self.assertEqual(res.ordinates_m3, [])
        self.assertEqual(res.total_haul_m3km, 0.0)

    def test_cumulative_ordinate_no_compaction(self):
        mh = _load()
        stations = [
            mh.MassHaulStation(0, cut_m3=100),
            mh.MassHaulStation(100, cut_m3=50),
            mh.MassHaulStation(200, fill_m3=150),
        ]
        res = mh.MassHaulDiagram(stations, compaction_factor=1.0).compute()
        # Cumulative: 100, 150, 0  (fill 150 / 1.0 subtracted)
        self.assertEqual(res.ordinates_m3, [100.0, 150.0, 0.0])
        self.assertEqual(res.total_cut_m3, 150.0)
        self.assertEqual(res.total_fill_m3, 150.0)
        self.assertAlmostEqual(res.net_m3, 0.0)
        self.assertEqual(res.max_ordinate_m3, 150.0)

    def test_compaction_increases_fill_demand(self):
        mh = _load()
        stations = [
            mh.MassHaulStation(0, cut_m3=100),
            mh.MassHaulStation(100, fill_m3=85),
        ]
        # fill 85 / 0.85 = 100 → balances exactly
        res = mh.MassHaulDiagram(stations, compaction_factor=0.85).compute()
        self.assertAlmostEqual(res.ordinates_m3[-1], 0.0, places=6)
        self.assertAlmostEqual(res.net_m3, 0.0, places=6)

    def test_net_surplus_and_deficit(self):
        mh = _load()
        surplus = mh.MassHaulDiagram(
            [mh.MassHaulStation(0, cut_m3=200), mh.MassHaulStation(100, fill_m3=50)],
            compaction_factor=1.0,
        ).compute()
        self.assertAlmostEqual(surplus.net_m3, 150.0)  # export

        deficit = mh.MassHaulDiagram(
            [mh.MassHaulStation(0, cut_m3=50), mh.MassHaulStation(100, fill_m3=200)],
            compaction_factor=1.0,
        ).compute()
        self.assertAlmostEqual(deficit.net_m3, -150.0)  # import

    def test_balance_point_interpolated(self):
        mh = _load()
        # Ordinate goes +100 → -100 between station 0 and 100 → crosses 0 at 50
        stations = [
            mh.MassHaulStation(0, cut_m3=100),
            mh.MassHaulStation(100, fill_m3=200),
        ]
        res = mh.MassHaulDiagram(stations, compaction_factor=1.0).compute()
        # ordinates: [100, -100] → zero crossing at station 50
        self.assertEqual(len(res.balance_points), 1)
        self.assertAlmostEqual(res.balance_points[0].station_m, 50.0, places=6)

    def test_stations_sorted_defensively(self):
        mh = _load()
        stations = [
            mh.MassHaulStation(200, fill_m3=150),
            mh.MassHaulStation(0, cut_m3=100),
            mh.MassHaulStation(100, cut_m3=50),
        ]
        res = mh.MassHaulDiagram(stations, compaction_factor=1.0).compute()
        self.assertEqual(res.stations_m, [0.0, 100.0, 200.0])

    def test_haul_integral_simple(self):
        mh = _load()
        # Constant ordinate 100 over 1000 m → area 100*1000 = 100000 m³·m = 100 m³·km
        stations = [
            mh.MassHaulStation(0, cut_m3=100),
            mh.MassHaulStation(1000, cut_m3=0),
        ]
        res = mh.MassHaulDiagram(stations, compaction_factor=1.0).compute()
        # ordinates [100, 100], trapezoid area = 100 * 1000 = 100000 m³·m
        self.assertAlmostEqual(res.total_haul_m3km, 100.0, places=6)

    def test_free_haul_split(self):
        mh = _load()
        # Single 1000 m segment, ordinate 100 → haul 100 m³·km.
        stations = [
            mh.MassHaulStation(0, cut_m3=100),
            mh.MassHaulStation(1000, cut_m3=0),
        ]
        res = mh.MassHaulDiagram(stations, compaction_factor=1.0).compute(
            free_haul_distance_m=500.0
        )
        # 500 of the 1000 m span is free → half free, half overhaul
        self.assertAlmostEqual(res.free_haul_m3km, 50.0, places=6)
        self.assertAlmostEqual(res.overhaul_m3km, 50.0, places=6)
        # Sum equals total
        self.assertAlmostEqual(
            res.free_haul_m3km + res.overhaul_m3km, res.total_haul_m3km, places=6
        )

    def test_zero_free_haul_all_overhaul(self):
        mh = _load()
        stations = [
            mh.MassHaulStation(0, cut_m3=100),
            mh.MassHaulStation(1000, cut_m3=0),
        ]
        res = mh.MassHaulDiagram(stations, compaction_factor=1.0).compute(
            free_haul_distance_m=0.0
        )
        self.assertAlmostEqual(res.free_haul_m3km, 0.0, places=6)
        self.assertAlmostEqual(res.overhaul_m3km, res.total_haul_m3km, places=6)


if __name__ == "__main__":
    unittest.main()
