"""
Unit tests for core/park_optimizer.py

Requires only scipy (already a QGIS-transitive dep via uncertainty.py). Does
not load QGIS, so it runs in a plain Python environment.
"""

import importlib.util
import os
import unittest


try:
    from scipy.optimize import linprog  # noqa: F401
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core",
    "park_optimizer.py",
)


def _load_po_module():
    """Load core/park_optimizer.py without triggering core/__init__.py."""
    import sys
    mod_name = "park_optimizer_isolated"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(SCIPY_AVAILABLE, "scipy not installed")
class TestSiteEarthwork(unittest.TestCase):

    def test_negative_cut_rejected(self):
        po = _load_po_module()
        with self.assertRaises(ValueError):
            po.SiteEarthwork(site_id="A", x=0, y=0, cut_excess_m3=-1)

    def test_negative_fill_rejected(self):
        po = _load_po_module()
        with self.assertRaises(ValueError):
            po.SiteEarthwork(site_id="A", x=0, y=0, fill_need_m3=-1)


@unittest.skipUnless(SCIPY_AVAILABLE, "scipy not installed")
class TestParkOptimizerTrivial(unittest.TestCase):

    def _config(self, max_distance_km=None):
        po = _load_po_module()
        return po.TransportConfig(
            cost_per_m3_km=0.20,
            dump_cost_per_m3=5.00,
            external_gravel_cost_per_m3=15.00,
            max_distance_km=max_distance_km,
        )

    def test_empty_input_returns_empty_solution(self):
        po = _load_po_module()
        solution = po.ParkOptimizer(self._config()).solve([])
        self.assertEqual(solution.flows, [])
        self.assertEqual(solution.total_cost_eur, 0.0)

    def test_single_site_does_not_transport(self):
        po = _load_po_module()
        site = po.SiteEarthwork(site_id="A", x=0, y=0, cut_excess_m3=100)
        sol = po.ParkOptimizer(self._config()).solve([site])
        self.assertEqual(sol.flows, [])
        # All 100 m³ remain to be dumped
        self.assertEqual(sol.residual_dump_m3["A"], 100.0)
        self.assertEqual(sol.total_dump_eur, 500.0)

    def test_one_to_one_transport_when_profitable(self):
        """A has 100 m³ surplus, B needs 100 m³, sites are 1 km apart.

        Transport cost per m³ = 0.20 € · 1 km = 0.20 €.
        Savings per m³ = dump (5) + gravel (15) - transport (0.20) = 19.80 €.
        Optimum is to move all 100 m³.
        """
        po = _load_po_module()
        a = po.SiteEarthwork(site_id="A", x=0, y=0, cut_excess_m3=100.0)
        b = po.SiteEarthwork(site_id="B", x=1000.0, y=0, fill_need_m3=100.0)
        sol = po.ParkOptimizer(self._config()).solve([a, b])
        # Should move 100 m³ from A to B
        self.assertEqual(len(sol.flows), 1)
        flow = sol.flows[0]
        self.assertEqual(flow.from_site, "A")
        self.assertEqual(flow.to_site, "B")
        self.assertAlmostEqual(flow.volume_m3, 100.0, places=4)
        self.assertAlmostEqual(flow.distance_km, 1.0, places=4)
        self.assertAlmostEqual(flow.transport_cost_eur, 20.0, places=2)
        # No residuals
        self.assertAlmostEqual(sol.residual_dump_m3["A"], 0.0, places=4)
        self.assertAlmostEqual(sol.residual_gravel_m3["B"], 0.0, places=4)
        # Baseline = 100*5 + 100*15 = 2000; savings = 2000 - 20 = 1980
        self.assertAlmostEqual(sol.baseline_cost_eur, 2000.0, places=2)
        self.assertAlmostEqual(sol.savings_eur, 1980.0, places=2)

    def test_no_transport_when_too_expensive(self):
        """Transport too expensive: dump cost + gravel cost < transport cost.

        Make distance 200 km so transport = 40 €/m³ > 20 €/m³ saved.
        """
        po = _load_po_module()
        a = po.SiteEarthwork(site_id="A", x=0, y=0, cut_excess_m3=100.0)
        b = po.SiteEarthwork(site_id="B", x=200_000.0, y=0, fill_need_m3=100.0)
        sol = po.ParkOptimizer(self._config()).solve([a, b])
        self.assertEqual(sol.flows, [])
        # Both residuals remain
        self.assertAlmostEqual(sol.residual_dump_m3["A"], 100.0, places=4)
        self.assertAlmostEqual(sol.residual_gravel_m3["B"], 100.0, places=4)
        # Savings should be 0 (no transport happened)
        self.assertAlmostEqual(sol.savings_eur, 0.0, places=2)

    def test_max_distance_km_blocks_transport(self):
        """Even if profitable, max_distance_km should forbid the flow."""
        po = _load_po_module()
        a = po.SiteEarthwork(site_id="A", x=0, y=0, cut_excess_m3=100.0)
        b = po.SiteEarthwork(site_id="B", x=10_000.0, y=0, fill_need_m3=100.0)
        config = self._config(max_distance_km=5.0)  # block 10 km hop
        sol = po.ParkOptimizer(config).solve([a, b])
        self.assertEqual(sol.flows, [])

    def test_partial_transport_when_capacities_mismatch(self):
        """A has 50 surplus, B needs 100 — only 50 can flow."""
        po = _load_po_module()
        a = po.SiteEarthwork(site_id="A", x=0, y=0, cut_excess_m3=50.0)
        b = po.SiteEarthwork(site_id="B", x=1000.0, y=0, fill_need_m3=100.0)
        sol = po.ParkOptimizer(self._config()).solve([a, b])
        self.assertEqual(len(sol.flows), 1)
        self.assertAlmostEqual(sol.flows[0].volume_m3, 50.0, places=4)
        self.assertAlmostEqual(sol.residual_dump_m3["A"], 0.0, places=4)
        # B still needs the remaining 50 m³ as external gravel
        self.assertAlmostEqual(sol.residual_gravel_m3["B"], 50.0, places=4)


@unittest.skipUnless(SCIPY_AVAILABLE, "scipy not installed")
class TestThreeSiteOptimum(unittest.TestCase):
    """Sanity-check that the LP picks the cheaper of two transport options."""

    def test_chooses_cheaper_source_site(self):
        """Two surplus sites A (near) and C (far) feed deficit site B.

        A is 1 km from B (transport 0.20 €/m³); C is 5 km from B (1.00 €/m³).
        B needs exactly 100 m³ — should source from A first.
        """
        po = _load_po_module()
        a = po.SiteEarthwork(site_id="A", x=0,       y=0, cut_excess_m3=100.0)
        b = po.SiteEarthwork(site_id="B", x=1000.0,  y=0, fill_need_m3=100.0)
        c = po.SiteEarthwork(site_id="C", x=6000.0,  y=0, cut_excess_m3=100.0)
        cfg = po.TransportConfig(
            cost_per_m3_km=0.20, dump_cost_per_m3=5.0,
            external_gravel_cost_per_m3=15.0,
        )
        sol = po.ParkOptimizer(cfg).solve([a, b, c])
        # All flows should be A→B; C→B costs more
        flow_a_to_b = [f for f in sol.flows if f.from_site == "A" and f.to_site == "B"]
        flow_c_to_b = [f for f in sol.flows if f.from_site == "C" and f.to_site == "B"]
        self.assertEqual(len(flow_a_to_b), 1)
        self.assertAlmostEqual(flow_a_to_b[0].volume_m3, 100.0, places=2)
        # C should not transport (B already covered, and dumping C is cheaper)
        self.assertEqual(len(flow_c_to_b), 0)


if __name__ == "__main__":
    unittest.main()
