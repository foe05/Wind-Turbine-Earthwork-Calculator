"""Unit tests for core/slope_stability_export.py — pure Python, no QGIS."""

import importlib.util
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET


_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core", "slope_stability_export.py",
)
_NS = "{urn:windturbine-calculator:slope-stability-export:v1}"


def _load():
    import sys
    name = "slope_stability_isolated"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _section(ss):
    return ss.SlopeSection(
        name="test",
        profile=[
            ss.ProfilePoint(x_m=0.0, terrain_z_m=320.0, design_z_m=318.5),
            ss.ProfilePoint(x_m=10.0, terrain_z_m=321.0, design_z_m=None),
            ss.ProfilePoint(x_m=20.0, terrain_z_m=319.0, design_z_m=317.0),
        ],
        materials=[
            ss.SoilMaterial("Mutterboden", 17, 22.0, 5.0),
            ss.SoilMaterial("Schluff", 19, 27.5, 10.0, top_z_m=319.7),
        ],
        piezometric=[(0.0, 316.0), (20.0, 315.5)],
    )


class TestSoilMaterial(unittest.TestCase):

    def test_unit_weight_positive(self):
        ss = _load()
        with self.assertRaises(ValueError):
            ss.SoilMaterial("x", 0.0, 30.0, 5.0)

    def test_friction_in_range(self):
        ss = _load()
        with self.assertRaises(ValueError):
            ss.SoilMaterial("x", 18.0, 90.0, 5.0)
        with self.assertRaises(ValueError):
            ss.SoilMaterial("x", 18.0, -1.0, 5.0)

    def test_cohesion_non_negative(self):
        ss = _load()
        with self.assertRaises(ValueError):
            ss.SoilMaterial("x", 18.0, 30.0, -1.0)


class TestBuildSlopeXML(unittest.TestCase):

    def test_root(self):
        ss = _load()
        root = ss.build_slope_xml([_section(ss)], project_name="Park A").getroot()
        self.assertEqual(root.tag, f"{_NS}SlopeStabilityExport")
        self.assertEqual(root.attrib["version"], "1.0")
        project = root.find(f"{_NS}Project")
        self.assertEqual(project.attrib["name"], "Park A")

    def test_section_and_counts(self):
        ss = _load()
        root = ss.build_slope_xml([_section(ss)]).getroot()
        section = root.find(f"{_NS}Section")
        self.assertEqual(section.attrib["name"], "test")
        self.assertEqual(section.find(f"{_NS}Profile").attrib["count"], "3")
        self.assertEqual(section.find(f"{_NS}Materials").attrib["count"], "2")
        self.assertEqual(section.find(f"{_NS}Piezometric").attrib["count"], "2")

    def test_design_z_omitted_when_none(self):
        ss = _load()
        root = ss.build_slope_xml([_section(ss)]).getroot()
        points = root.findall(f".//{_NS}Profile/{_NS}Point")
        self.assertIn("design_z_m", points[0].attrib)
        self.assertNotIn("design_z_m", points[1].attrib)  # None → omitted
        self.assertIn("design_z_m", points[2].attrib)

    def test_material_attributes(self):
        ss = _load()
        root = ss.build_slope_xml([_section(ss)]).getroot()
        mats = root.findall(f".//{_NS}Material")
        self.assertEqual(mats[0].attrib["name"], "Mutterboden")
        self.assertAlmostEqual(float(mats[0].attrib["friction_angle_deg"]), 22.0)
        self.assertAlmostEqual(float(mats[0].attrib["cohesion_kPa"]), 5.0)
        self.assertNotIn("top_z_m", mats[0].attrib)  # not set
        self.assertIn("top_z_m", mats[1].attrib)     # set
        self.assertAlmostEqual(float(mats[1].attrib["top_z_m"]), 319.7)

    def test_piezometric_points(self):
        ss = _load()
        root = ss.build_slope_xml([_section(ss)]).getroot()
        pts = root.findall(f".//{_NS}Piezometric/{_NS}Point")
        self.assertEqual(len(pts), 2)
        self.assertAlmostEqual(float(pts[0].attrib["x_m"]), 0.0)
        self.assertAlmostEqual(float(pts[0].attrib["z_m"]), 316.0)

    def test_section_without_piezo_omits_element(self):
        ss = _load()
        s = ss.SlopeSection(
            name="no-piezo",
            profile=[ss.ProfilePoint(0, 100, 99)],
            materials=[ss.SoilMaterial("m", 18, 30, 5)],
        )
        root = ss.build_slope_xml([s]).getroot()
        self.assertIsNone(root.find(f".//{_NS}Piezometric"))


class TestWriteAndReparse(unittest.TestCase):

    def test_round_trip(self):
        ss = _load()
        tmpdir = tempfile.mkdtemp(prefix="slopexml_")
        try:
            path = os.path.join(tmpdir, "slope.xml")
            ss.write_slope_xml(path, [_section(ss)])
            root = ET.parse(path).getroot()
            self.assertEqual(root.tag, f"{_NS}SlopeStabilityExport")
            self.assertEqual(len(root.findall(f".//{_NS}Point")), 3 + 2)  # profile + piezo
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestSectionFromProfile(unittest.TestCase):

    def test_adapter_handles_nan(self):
        ss = _load()
        import math
        profile = {
            "distances": [0.0, 5.0, 10.0],
            "existing_z": [320.0, 321.0, 319.0],
            "bottom_z": [318.0, math.nan, 317.0],
        }
        section = ss.section_from_profile("road", profile, ss.default_materials())
        self.assertEqual(len(section.profile), 3)
        self.assertEqual(section.profile[0].design_z_m, 318.0)
        self.assertIsNone(section.profile[1].design_z_m)
        self.assertEqual(section.profile[2].design_z_m, 317.0)

    def test_adapter_requires_keys(self):
        ss = _load()
        with self.assertRaises(ValueError):
            ss.section_from_profile("x", {"distances": [], "existing_z": []})


if __name__ == "__main__":
    unittest.main()
