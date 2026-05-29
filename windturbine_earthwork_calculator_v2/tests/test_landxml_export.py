"""
Unit tests for core/landxml_export.py — pure Python (stdlib XML), no QGIS.
"""

import importlib.util
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET


_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core", "landxml_export.py",
)
_NS = "{http://www.landxml.org/schema/LandXML-1.2}"


def _load():
    import sys
    name = "landxml_export_isolated"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _square_surface(lx, name="kranstellflaeche"):
    # 4 points, 2 triangles
    return lx.LandXMLSurface(
        name=name,
        points=[(100.0, 200.0, 10.0), (110.0, 200.0, 11.0),
                (110.0, 210.0, 12.0), (100.0, 210.0, 11.0)],
        faces=[(0, 1, 2), (0, 2, 3)],
    )


class TestBuildLandXML(unittest.TestCase):

    def test_root_and_namespace(self):
        lx = _load()
        tree = lx.build_landxml([_square_surface(lx)])
        root = tree.getroot()
        self.assertEqual(root.tag, f"{_NS}LandXML")
        self.assertEqual(root.attrib["version"], "1.2")

    def test_units_present(self):
        lx = _load()
        root = lx.build_landxml([_square_surface(lx)]).getroot()
        metric = root.find(f"{_NS}Units/{_NS}Metric")
        self.assertIsNotNone(metric)
        self.assertEqual(metric.attrib["linearUnit"], "meter")

    def test_surface_points_and_faces(self):
        lx = _load()
        root = lx.build_landxml([_square_surface(lx)]).getroot()
        surf = root.find(f"{_NS}Surfaces/{_NS}Surface")
        self.assertEqual(surf.attrib["name"], "kranstellflaeche")
        pnts = surf.findall(f"{_NS}Definition/{_NS}Pnts/{_NS}P")
        faces = surf.findall(f"{_NS}Definition/{_NS}Faces/{_NS}F")
        self.assertEqual(len(pnts), 4)
        self.assertEqual(len(faces), 2)

    def test_point_ids_are_1_based(self):
        lx = _load()
        root = lx.build_landxml([_square_surface(lx)]).getroot()
        pnts = root.findall(f".//{_NS}P")
        ids = [p.attrib["id"] for p in pnts]
        self.assertEqual(ids, ["1", "2", "3", "4"])

    def test_point_coordinate_order_is_northing_easting_elev(self):
        lx = _load()
        root = lx.build_landxml([_square_surface(lx)]).getroot()
        first_p = root.find(f".//{_NS}P")
        # Input point 0 = (x=100 easting, y=200 northing, z=10) →
        # LandXML order "northing easting elev" → "200 100 10"
        parts = first_p.text.split()
        self.assertAlmostEqual(float(parts[0]), 200.0)  # northing (y)
        self.assertAlmostEqual(float(parts[1]), 100.0)  # easting (x)
        self.assertAlmostEqual(float(parts[2]), 10.0)   # elevation (z)

    def test_face_indices_are_1_based(self):
        lx = _load()
        root = lx.build_landxml([_square_surface(lx)]).getroot()
        first_f = root.find(f".//{_NS}F")
        # face (0,1,2) → "1 2 3"
        self.assertEqual(first_f.text.split(), ["1", "2", "3"])

    def test_multiple_surfaces(self):
        lx = _load()
        root = lx.build_landxml([
            _square_surface(lx, "kranstellflaeche"),
            _square_surface(lx, "fundamentsohle"),
        ]).getroot()
        surfs = root.findall(f"{_NS}Surfaces/{_NS}Surface")
        self.assertEqual(len(surfs), 2)
        self.assertEqual({s.attrib["name"] for s in surfs},
                         {"kranstellflaeche", "fundamentsohle"})


class TestWriteLandXML(unittest.TestCase):

    def test_write_and_reparse(self):
        lx = _load()
        tmpdir = tempfile.mkdtemp(prefix="landxml_test_")
        try:
            path = os.path.join(tmpdir, "surfaces.xml")
            lx.write_landxml(path, [_square_surface(lx)], project_name="Park A")
            self.assertTrue(os.path.exists(path))
            # Re-parse to confirm well-formed XML
            tree = ET.parse(path)
            root = tree.getroot()
            self.assertEqual(root.tag, f"{_NS}LandXML")
            self.assertEqual(len(root.findall(f".//{_NS}P")), 4)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestSurfaceFromMesh(unittest.TestCase):

    def test_adapter_from_mesh_like(self):
        lx = _load()

        class FakeMesh:
            vertices = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
            faces = [(0, 1, 2)]

        surf = lx.surface_from_mesh("terrain", FakeMesh())
        self.assertEqual(surf.name, "terrain")
        self.assertEqual(len(surf.points), 3)
        self.assertEqual(len(surf.faces), 1)


if __name__ == "__main__":
    unittest.main()
