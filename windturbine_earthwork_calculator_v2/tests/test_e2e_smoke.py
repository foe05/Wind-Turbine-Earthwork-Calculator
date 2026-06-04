"""
End-to-end smoke test of the QGIS-independent core modules.

Runs through a realistic three-turbine park-planning flow in plain Python
(no QGIS, no GDAL), exercising every public module at least once with sensible
inputs and asserting that the outputs hang together. The aim is to prove that
the modules compose — not to replace per-module unit tests.

Steps:
  1. Verify each candidate WEA position against placement constraints.
  2. Build a per-site candidate set and run the park-wide MILP.
  3. Sweep crane-pad rotations on the chosen layout.
  4. Generate the platform mesh and write OBJ / STL / glTF / Three.js viewer.
  5. Export a combined LandXML TIN.
  6. Compute mass-haul along a synthetic longitudinal profile.
  7. Split chosen volumes into soil strata.
  8. Distribute earthwork across construction phases.
  9. Estimate CO₂ for the project.
 10. Write a slope-stability cross-section XML.
 11. Render a variant-comparison HTML.

Files are written into a tempdir that is cleaned up afterwards. Each step
asserts a few invariants so a silent regression in one module is caught.
"""

import importlib.util
import os
import sys
import tempfile
import unittest


_CORE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core",
)


def _load(name):
    """Load a core module by file path so core/__init__.py (which pulls qgis)
    is not triggered."""
    mod_name = f"{name}_e2e"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    path = os.path.join(_CORE_DIR, f"{name}.py")
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


try:
    from shapely.geometry import Polygon, LineString
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

try:
    from scipy.optimize import linprog  # noqa: F401
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


@unittest.skipUnless(SHAPELY_AVAILABLE, "shapely not installed")
@unittest.skipUnless(SCIPY_AVAILABLE, "scipy not installed")
class TestE2EPark(unittest.TestCase):
    """Three-site park planning end-to-end."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="wea_e2e_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_full_park_planning_flow(self):
        # === 1. Placement constraints ===========================================
        pc = _load("placement_constraints")
        # One restricted zone the planner must avoid (Wohnbebauung at NE corner)
        wohngebiet = Polygon([(495000, 5705000), (495300, 5705000),
                              (495300, 5705300), (495000, 5705300)])
        strasse = LineString([(492000, 5701500), (496000, 5701500)])
        validator = pc.PlacementValidator([
            pc.ConstraintLayer("Wohnbebauung", [wohngebiet], min_distance_m=600,
                               severity=pc.Severity.HARD),
            pc.ConstraintLayer("Strasse", [strasse], min_distance_m=50,
                               severity=pc.Severity.SOFT),
        ])
        # Three candidate WEA positions
        candidates = [(492500, 5702500), (493500, 5703500), (494500, 5704000)]
        violations_per_site = [validator.check_position(x, y) for x, y in candidates]
        # All three should be clear of the hard zone (well outside 600 m)
        for vs in violations_per_site:
            self.assertFalse(
                any(v.severity == pc.Severity.HARD for v in vs),
                "no hard violation expected",
            )

        # === 2. Park-wide MILP ==================================================
        po = _load("park_optimizer")
        # Mix of surplus + deficit sites so transport genuinely beats dumping
        # / external gravel. WEA01 always has a surplus, WEA02 always a deficit,
        # WEA03 offers a choice (small surplus vs. balanced) so the solver has
        # something non-trivial to decide.
        sites_milp = [
            po.SiteWithCandidates(
                "WEA01", *candidates[0],
                candidates=[po.SiteCandidate(cut_excess_m3=1500, fill_need_m3=0,
                                             site_cost_eur=0, label="surplus")],
            ),
            po.SiteWithCandidates(
                "WEA02", *candidates[1],
                candidates=[po.SiteCandidate(cut_excess_m3=0, fill_need_m3=1200,
                                             site_cost_eur=0, label="deficit")],
            ),
            po.SiteWithCandidates(
                "WEA03", *candidates[2],
                candidates=[
                    po.SiteCandidate(cut_excess_m3=500, fill_need_m3=0,
                                     site_cost_eur=0, label="surplus"),
                    po.SiteCandidate(cut_excess_m3=0, fill_need_m3=0,
                                     site_cost_eur=20_000, label="balanced"),
                ],
            ),
        ]
        cfg = po.TransportConfig(
            cost_per_m3_km=0.5, dump_cost_per_m3=0.0,
            external_gravel_cost_per_m3=45.0,
        )
        milp = po.ParkOptimizer(cfg).solve_milp(sites_milp)
        # Each site got a candidate
        self.assertEqual(set(milp.chosen_candidate.keys()),
                         {"WEA01", "WEA02", "WEA03"})
        # MILP should haul material between surplus and deficit sites
        self.assertGreater(len(milp.flows), 0)

        # Aggregate for downstream steps
        chosen_cut = sum(c.cut_excess_m3 for c in milp.chosen_candidate.values())
        chosen_fill = sum(c.fill_need_m3 for c in milp.chosen_candidate.values())
        self.assertGreater(chosen_cut + chosen_fill, 0)

        # === 3. Crane-pad rotation analysis =====================================
        ro = _load("rotation_optimizer")
        pad = [(0, 0), (20, 0), (20, 10), (0, 10)]  # 20×10 m rectangle
        # Synthetic metric: prefer the orientation where the long edge is
        # vertical (Y). At 0° the rectangle's x-extent is 20, y-extent 10 →
        # metric x-y = +10; at 90° it flips → -10 (lower = better).
        def evaluate(rot):
            cx, cy = ro.polygon_centroid(rot)
            xs = [p[0] - cx for p in rot]
            ys = [p[1] - cy for p in rot]
            return abs(max(xs) - min(xs)) - abs(max(ys) - min(ys)), None
        best = ro.RotationOptimizer(angles_deg=[0, 30, 60, 90, 120, 150]).optimize(
            pad, evaluate
        )
        # Optimal is 90° (rotated rectangle stands "upright"); evaluate is monotonic.
        self.assertEqual(best.angle_deg, 90.0)

        # === 4. Mesh + viewer ===================================================
        me = _load("mesh_exporter")
        pad_mesh = me.polygon_to_mesh_at_height(pad, height=320.0,
                                                name="kranstellflaeche")
        self.assertEqual(pad_mesh.triangle_count, 2)
        me.write_obj(os.path.join(self.tmpdir, "pad.obj"), pad_mesh)
        me.write_stl(os.path.join(self.tmpdir, "pad.stl"), pad_mesh, binary=True)
        gltf = me.build_gltf_dict([pad_mesh])
        me.write_gltf(os.path.join(self.tmpdir, "scene.gltf"), [pad_mesh])
        me.write_three_js_viewer(os.path.join(self.tmpdir, "viewer.html"),
                                 gltf, title="E2E Test")
        for f in ("pad.obj", "pad.stl", "scene.gltf", "viewer.html"):
            self.assertTrue(os.path.exists(os.path.join(self.tmpdir, f)), f)
        # glTF buffer should decode and match the declared length.
        import base64
        raw = base64.b64decode(gltf["buffers"][0]["uri"].split(",", 1)[1])
        self.assertEqual(len(raw), gltf["buffers"][0]["byteLength"])

        # === 5. LandXML =========================================================
        lx = _load("landxml_export")
        landxml_path = lx.write_landxml(
            os.path.join(self.tmpdir, "surfaces.xml"),
            [lx.surface_from_mesh("kranstellflaeche", pad_mesh)],
            project_name="WEA E2E",
        )
        self.assertTrue(os.path.exists(landxml_path))
        import xml.etree.ElementTree as ET
        root = ET.parse(landxml_path).getroot()
        ns = "{http://www.landxml.org/schema/LandXML-1.2}"
        # LandXML uses <P> for points and <F> for triangle faces.
        self.assertEqual(len(root.findall(f".//{ns}P")), 4)
        self.assertEqual(len(root.findall(f".//{ns}F")), 2)

        # === 6. Mass-haul =======================================================
        mh = _load("mass_haul")
        # Synthetic profile: 100 m of cut then 100 m of fill, balanced over 200 m
        stations = [
            mh.MassHaulStation(0,   cut_m3=80),
            mh.MassHaulStation(50,  cut_m3=80),
            mh.MassHaulStation(100, fill_m3=80),
            mh.MassHaulStation(150, fill_m3=80),
        ]
        mh_res = mh.MassHaulDiagram(stations, compaction_factor=1.0).compute(
            free_haul_distance_m=20.0
        )
        # Net balanced to zero, at least one balance point near the middle
        self.assertAlmostEqual(mh_res.net_m3, 0.0, places=4)
        self.assertGreaterEqual(len(mh_res.balance_points), 1)
        # Free + overhaul sums to total haul
        self.assertAlmostEqual(
            mh_res.free_haul_m3km + mh_res.overhaul_m3km,
            mh_res.total_haul_m3km, places=4,
        )

        # === 7. Strata (per-site) ===============================================
        sq = _load("strata_quantities")
        calc = sq.StrataCalculator(sq.default_stack())
        # 50 m³ over 100 m² = 0.5 m depth → top + part of mid
        strata = calc.split(volume_m3=50.0, area_m2=100.0, mode=sq.StratumMode.CUT)
        self.assertEqual([q.name for q in strata.layers],
                         ["Mutterboden", "Frostschutzschicht"])
        self.assertAlmostEqual(strata.total_volume_m3, 50.0)
        self.assertGreater(strata.total_cost_eur, 0)

        # === 8. Construction phases ============================================
        cp = _load("construction_phases")
        plan = cp.PhasePlanner(cp.default_phases()).plan(
            total_cut_m3=chosen_cut, total_fill_m3=chosen_fill,
        )
        # Default plan: 4 phases, 19 build days
        self.assertEqual(len(plan.phases), 4)
        self.assertEqual(plan.total_duration_days, 19)
        # No remainder with the default shares (each row sums to 1)
        self.assertAlmostEqual(plan.unassigned_cut_m3, 0.0, places=6)

        # === 9. CO₂ =============================================================
        co2 = _load("co2_balance")
        co2_res = co2.CO2Calculator().compute(
            cut_m3=chosen_cut, fill_m3=chosen_fill,
            haul_distance_km=5.0,
            concrete_m3=350.0, steel_kg=42_000.0,
        )
        self.assertGreater(co2_res.total_t, 0.0)
        bd = co2_res.as_breakdown()
        # Components sum to the total
        component_sum = (bd["excavation_kg"] + bd["haul_kg"] + bd["gravel_kg"]
                         + bd["concrete_kg"] + bd["steel_kg"])
        self.assertAlmostEqual(component_sum, bd["total_kg"], places=1)

        # === 10. Slope-stability XML ============================================
        ss = _load("slope_stability_export")
        section = ss.SlopeSection(
            name="WEA01_long_profile",
            profile=[
                ss.ProfilePoint(0.0,   terrain_z_m=320.0, design_z_m=319.5),
                ss.ProfilePoint(50.0,  terrain_z_m=322.0, design_z_m=319.5),
                ss.ProfilePoint(100.0, terrain_z_m=321.0, design_z_m=None),
            ],
            materials=ss.default_materials(),
            piezometric=[(0.0, 315.0), (100.0, 314.5)],
        )
        slope_path = ss.write_slope_xml(
            os.path.join(self.tmpdir, "slope.xml"), [section]
        )
        ss_root = ET.parse(slope_path).getroot()
        ss_ns = "{urn:windturbine-calculator:slope-stability-export:v1}"
        self.assertEqual(len(ss_root.findall(f".//{ss_ns}Material")), 3)

        # === 11. Variant-comparison HTML ========================================
        vc = _load("variant_comparison")
        variants = [
            vc.Variant("319.5 m / 0°",  crane_height_m=319.5,
                       total_cut_m3=6500, total_fill_m3=2400,
                       gravel_m3=120, total_cost_eur=180_000,
                       total_co2_kg=42_000),
            vc.Variant("320.0 m / 45°", crane_height_m=320.0,
                       total_cut_m3=5800, total_fill_m3=2800,
                       gravel_m3=110, total_cost_eur=170_000,
                       total_co2_kg=39_500),
            vc.Variant("320.5 m / 90°", crane_height_m=320.5,
                       total_cut_m3=6100, total_fill_m3=2500,
                       gravel_m3=130, total_cost_eur=175_000,
                       total_co2_kg=41_000),
        ]
        report = vc.VariantComparisonReport(variants)
        winner = report.best_variant("total_cost_eur")
        self.assertEqual(winner.label, "320.0 m / 45°")
        report_path = report.write(
            os.path.join(self.tmpdir, "vergleich.html"),
            project_name="WEA E2E Park",
        )
        with open(report_path, "r", encoding="utf-8") as fh:
            html_out = fh.read()
        # Title + the winning variant's label are both in the rendered HTML
        self.assertIn("WEA E2E Park", html_out)
        for v in variants:
            self.assertIn(v.label.replace("°", "°"), html_out)


if __name__ == "__main__":
    unittest.main()
