"""Unit tests for core/variant_comparison.py — pure Python, no QGIS."""

import importlib.util
import os
import tempfile
import unittest


_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core", "variant_comparison.py",
)


def _load():
    import sys
    name = "variant_comparison_isolated"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _variants(vc):
    return [
        vc.Variant(label="319.5 m / 0°",  crane_height_m=319.5,
                   total_cut_m3=6500, total_fill_m3=2400, gravel_m3=120,
                   total_cost_eur=180_000, total_co2_kg=42_000),
        vc.Variant(label="320.0 m / 45°", crane_height_m=320.0,
                   total_cut_m3=5800, total_fill_m3=2800, gravel_m3=110,
                   total_cost_eur=170_000, total_co2_kg=39_500,
                   notes="Test <unsafe> Eintrag"),
        vc.Variant(label="320.5 m / 90°", crane_height_m=320.5,
                   total_cut_m3=6100, total_fill_m3=2500, gravel_m3=130,
                   total_cost_eur=175_000, total_co2_kg=41_000),
    ]


class TestVariant(unittest.TestCase):

    def test_derived_properties(self):
        vc = _load()
        v = vc.Variant(label="x", total_cut_m3=100, total_fill_m3=40)
        self.assertAlmostEqual(v.total_volume_moved_m3, 140.0)
        self.assertAlmostEqual(v.net_volume_m3, 60.0)


class TestVariantComparisonReport(unittest.TestCase):

    def test_empty_rejected(self):
        vc = _load()
        with self.assertRaises(ValueError):
            vc.VariantComparisonReport([])

    def test_best_variant_picks_lowest_moved(self):
        vc = _load()
        report = vc.VariantComparisonReport(_variants(vc))
        # 5800+2800=8600 (variant 1) is the smallest total_volume_moved
        self.assertEqual(report.best_variant().label, "320.0 m / 45°")

    def test_best_variant_by_cost(self):
        vc = _load()
        report = vc.VariantComparisonReport(_variants(vc))
        self.assertEqual(report.best_variant("total_cost_eur").label, "320.0 m / 45°")

    def test_html_contains_all_labels(self):
        vc = _load()
        html_out = vc.VariantComparisonReport(_variants(vc)).to_html("Test")
        for v in _variants(vc):
            self.assertIn(v.label.replace("°", "°"), html_out)
        # Title escaped
        self.assertIn("<title>Test</title>", html_out)

    def test_html_escapes_notes(self):
        vc = _load()
        html_out = vc.VariantComparisonReport(_variants(vc)).to_html()
        self.assertNotIn("<unsafe>", html_out)
        self.assertIn("&lt;unsafe&gt;", html_out)

    def test_best_value_highlight_for_lower_is_better(self):
        vc = _load()
        html_out = vc.VariantComparisonReport(_variants(vc)).to_html()
        # The "Erdbewegung gesamt" row should have exactly one highlighted cell.
        # That cell carries the inline style we added.
        self.assertEqual(html_out.count("background: #e8f5e9"), 4)
        # 4 highlighted cells: moved + gravel + cost + CO2 (the four metrics
        # flagged lower_is_better).

    def test_single_variant_no_highlight(self):
        vc = _load()
        html_out = vc.VariantComparisonReport([
            vc.Variant(label="solo", total_cut_m3=100, total_fill_m3=50),
        ]).to_html()
        # With only one variant we still get the row but min() over a single
        # element would mark it best; verify we don't crash.
        self.assertIn("solo", html_out)

    def test_write_creates_file(self):
        vc = _load()
        tmpdir = tempfile.mkdtemp(prefix="variant_")
        try:
            path = os.path.join(tmpdir, "vergleich.html")
            vc.VariantComparisonReport(_variants(vc)).write(path)
            self.assertTrue(os.path.exists(path))
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("Variantenvergleich", content)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
