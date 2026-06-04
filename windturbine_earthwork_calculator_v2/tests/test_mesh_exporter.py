"""
Unit tests for core/mesh_exporter.py

The OBJ writer and ear-clipping polygon triangulator are pure Python and run
in any environment. The DEM-to-mesh path is tested only when GDAL is
available.
"""

import importlib.util
import math
import os
import tempfile
import unittest


try:
    from osgeo import gdal  # noqa: F401
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False


_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core",
    "mesh_exporter.py",
)


def _load_me_module():
    """Load core/mesh_exporter.py without triggering core/__init__.py."""
    import sys
    mod_name = "mesh_exporter_isolated"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


class TestMeshData(unittest.TestCase):

    def test_extend_reindexes_faces(self):
        me = _load_me_module()
        a = me.MeshData(
            vertices=[(0, 0, 0), (1, 0, 0), (0, 1, 0)],
            faces=[(0, 1, 2)],
            name="a",
        )
        b = me.MeshData(
            vertices=[(2, 0, 0), (3, 0, 0), (2, 1, 0)],
            faces=[(0, 1, 2)],
            name="b",
        )
        a.extend(b)
        self.assertEqual(a.vertex_count, 6)
        self.assertEqual(a.triangle_count, 2)
        self.assertEqual(a.faces, [(0, 1, 2), (3, 4, 5)])


class TestWriteObj(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mesh_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_round_trip(self):
        me = _load_me_module()
        mesh = me.MeshData(
            vertices=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.5)],
            faces=[(0, 1, 2)],
            name="single-triangle",
        )
        path = os.path.join(self.tmpdir, "tri.obj")
        me.write_obj(path, mesh)

        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()

        # Header comment present
        self.assertIn("# OBJ export: single-triangle", content)
        # Object name
        self.assertIn("o single-triangle", content)
        # Three vertex lines
        self.assertEqual(content.count("\nv "), 3)
        # One face line, 1-based indices
        self.assertIn("f 1 2 3", content)

    def test_writes_to_nested_dir(self):
        me = _load_me_module()
        mesh = me.MeshData(
            vertices=[(0, 0, 0), (1, 0, 0), (0, 1, 0)],
            faces=[(0, 1, 2)],
        )
        path = os.path.join(self.tmpdir, "nested", "subdir", "x.obj")
        out = me.write_obj(path, mesh)
        self.assertTrue(os.path.exists(out))


class TestPolygonToMesh(unittest.TestCase):

    def test_simple_square(self):
        me = _load_me_module()
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        mesh = me.polygon_to_mesh_at_height(square, height=5.0, name="pad")
        # 4 vertices, 2 triangles (ear-clipping of a quad)
        self.assertEqual(mesh.vertex_count, 4)
        self.assertEqual(mesh.triangle_count, 2)
        # All vertices at z=5
        for x, y, z in mesh.vertices:
            self.assertEqual(z, 5.0)

    def test_closing_duplicate_tolerated(self):
        me = _load_me_module()
        square_closed = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        mesh = me.polygon_to_mesh_at_height(square_closed, height=0.0)
        # Closing duplicate must be stripped → 4 vertices, 2 triangles
        self.assertEqual(mesh.vertex_count, 4)
        self.assertEqual(mesh.triangle_count, 2)

    def test_clockwise_orientation_corrected(self):
        me = _load_me_module()
        # CW square — ear-clipping must still produce 2 triangles
        cw_square = [(0, 0), (0, 10), (10, 10), (10, 0)]
        mesh = me.polygon_to_mesh_at_height(cw_square, height=1.0)
        self.assertEqual(mesh.triangle_count, 2)

    def test_concave_l_shape(self):
        me = _load_me_module()
        # L-shape:  ____
        #          |   |
        #          |   |____
        #          |        |
        #          |________|
        l_shape = [(0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10)]
        mesh = me.polygon_to_mesh_at_height(l_shape, height=0.0)
        # 6 vertices, 4 triangles (n-2 for simple polygon ear-clipping)
        self.assertEqual(mesh.vertex_count, 6)
        self.assertEqual(mesh.triangle_count, 4)

    def test_degenerate_input(self):
        me = _load_me_module()
        # Only 2 points
        mesh = me.polygon_to_mesh_at_height([(0, 0), (1, 1)], height=0.0)
        self.assertEqual(mesh.vertex_count, 0)
        self.assertEqual(mesh.triangle_count, 0)

    def test_triangle(self):
        me = _load_me_module()
        mesh = me.polygon_to_mesh_at_height(
            [(0, 0), (10, 0), (5, 8)], height=2.0
        )
        self.assertEqual(mesh.vertex_count, 3)
        self.assertEqual(mesh.triangle_count, 1)


class TestSignedArea(unittest.TestCase):

    def test_ccw_positive(self):
        me = _load_me_module()
        # Counter-clockwise unit square
        sq = [(0, 0), (1, 0), (1, 1), (0, 1)]
        self.assertGreater(me._signed_area(sq), 0)

    def test_cw_negative(self):
        me = _load_me_module()
        sq_cw = [(0, 0), (0, 1), (1, 1), (1, 0)]
        self.assertLess(me._signed_area(sq_cw), 0)


@unittest.skipUnless(GDAL_AVAILABLE, "osgeo.gdal not available")
class TestDemToMesh(unittest.TestCase):

    def setUp(self):
        from osgeo import gdal
        import numpy as np
        self.gdal = gdal
        self.np = np
        self.tmpdir = tempfile.mkdtemp(prefix="dem_mesh_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_dem(self, arr, nodata=-9999.0):
        path = os.path.join(self.tmpdir, "dem.tif")
        h, w = arr.shape
        driver = self.gdal.GetDriverByName("GTiff")
        ds = driver.Create(path, w, h, 1, self.gdal.GDT_Float32)
        ds.SetGeoTransform([0.0, 1.0, 0.0, float(h), 0.0, -1.0])
        band = ds.GetRasterBand(1)
        band.WriteRaster(0, 0, w, h, arr.astype(self.np.float32).tobytes())
        band.SetNoDataValue(nodata)
        band.FlushCache()
        ds.FlushCache()
        ds = None
        return path

    def test_basic_dem(self):
        me = _load_me_module()
        dem_arr = self.np.array(
            [[100.0, 101.0, 102.0],
             [101.0, 102.0, 103.0],
             [102.0, 103.0, 104.0]],
            dtype=self.np.float32,
        )
        path = self._make_dem(dem_arr)
        mesh = me.dem_to_mesh(path, decimation=1)
        # 3×3 grid → 9 vertices, 2*2*2 = 8 triangles
        self.assertEqual(mesh.vertex_count, 9)
        self.assertEqual(mesh.triangle_count, 8)
        # All z values are between 100 and 104
        z_vals = [v[2] for v in mesh.vertices]
        self.assertEqual(min(z_vals), 100.0)
        self.assertEqual(max(z_vals), 104.0)

    def test_decimation_reduces_size(self):
        me = _load_me_module()
        # 9×9 DEM
        dem_arr = self.np.linspace(100, 110, 81, dtype=self.np.float32).reshape(9, 9)
        path = self._make_dem(dem_arr)

        mesh_full = me.dem_to_mesh(path, decimation=1)
        mesh_decimated = me.dem_to_mesh(path, decimation=3)
        # 9×9 → decimated to 3×3
        self.assertEqual(mesh_full.vertex_count, 81)
        self.assertEqual(mesh_decimated.vertex_count, 9)

    def test_nodata_skipped(self):
        me = _load_me_module()
        dem_arr = self.np.array(
            [[100.0, -9999.0, 102.0],
             [101.0, 102.0,    103.0],
             [102.0, 103.0,    104.0]],
            dtype=self.np.float32,
        )
        path = self._make_dem(dem_arr, nodata=-9999.0)
        mesh = me.dem_to_mesh(path, decimation=1, nodata_value=-9999.0)
        # 8 valid vertices (1 nodata skipped)
        self.assertEqual(mesh.vertex_count, 8)
        # Quads with the nodata corner are skipped → 8 - some = fewer triangles
        self.assertLess(mesh.triangle_count, 8)

    def test_decimation_zero_rejected(self):
        me = _load_me_module()
        path = self._make_dem(self.np.zeros((3, 3), dtype=self.np.float32))
        with self.assertRaises(ValueError):
            me.dem_to_mesh(path, decimation=0)

    def test_obj_round_trip_with_dem(self):
        me = _load_me_module()
        dem_arr = self.np.array(
            [[100.0, 101.0], [101.0, 102.0]], dtype=self.np.float32
        )
        path = self._make_dem(dem_arr)
        mesh = me.dem_to_mesh(path, decimation=1)
        obj_path = os.path.join(self.tmpdir, "terrain.obj")
        me.write_obj(obj_path, mesh)
        with open(obj_path, "r", encoding="utf-8") as fh:
            content = fh.read()
        # 4 vertices, 2 triangles
        self.assertEqual(content.count("\nv "), 4)
        self.assertEqual(content.count("\nf "), 2)


class TestWriteStl(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="stl_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _square_mesh(self):
        me = _load_me_module()
        # Two triangles forming a flat 1×1 square at z=0
        return me.MeshData(
            vertices=[(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
            faces=[(0, 1, 2), (0, 2, 3)],
            name="sq",
        )

    def test_ascii_stl_structure(self):
        me = _load_me_module()
        path = os.path.join(self.tmpdir, "m.stl")
        me.write_stl(path, self._square_mesh(), binary=False)
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
        self.assertTrue(content.startswith("solid sq"))
        self.assertTrue(content.strip().endswith("endsolid sq"))
        self.assertEqual(content.count("facet normal"), 2)
        self.assertEqual(content.count("vertex"), 6)
        # Flat square in z=0 plane → normal is ±Z (unit)
        self.assertIn("0.000000e+00 0.000000e+00 1.000000e+00", content)

    def test_binary_stl_size_and_count(self):
        me = _load_me_module()
        path = os.path.join(self.tmpdir, "m_bin.stl")
        me.write_stl(path, self._square_mesh(), binary=True)
        size = os.path.getsize(path)
        # 80 header + 4 count + 2 triangles * 50 bytes = 184
        self.assertEqual(size, 80 + 4 + 2 * 50)
        import struct
        with open(path, "rb") as fh:
            fh.read(80)
            (count,) = struct.unpack("<I", fh.read(4))
        self.assertEqual(count, 2)

    def test_degenerate_triangle_normal_is_zero(self):
        me = _load_me_module()
        # Collinear points → zero-area triangle → zero normal, must not raise
        n = me._triangle_normal((0, 0, 0), (1, 1, 1), (2, 2, 2))
        self.assertEqual(n, (0.0, 0.0, 0.0))


class TestGltf(unittest.TestCase):

    def _two_meshes(self):
        me = _load_me_module()
        terrain = me.MeshData(
            vertices=[(100, 200, 10), (101, 200, 11), (101, 201, 12), (100, 201, 11)],
            faces=[(0, 1, 2), (0, 2, 3)],
            name="terrain",
        )
        pad = me.MeshData(
            vertices=[(100, 200, 20), (100.5, 200, 20), (100.5, 200.5, 20)],
            faces=[(0, 1, 2)],
            name="kranstellflaeche",
        )
        return [terrain, pad]

    def test_empty_meshes_produce_valid_empty_gltf(self):
        me = _load_me_module()
        gltf = me.build_gltf_dict([])
        self.assertEqual(gltf["asset"]["version"], "2.0")
        self.assertEqual(gltf["nodes"], [])
        self.assertEqual(gltf["meshes"], [])

    def test_gltf_structure(self):
        me = _load_me_module()
        gltf = me.build_gltf_dict(self._two_meshes())
        # Two nodes / meshes / materials
        self.assertEqual(len(gltf["nodes"]), 2)
        self.assertEqual(len(gltf["meshes"]), 2)
        self.assertEqual(len(gltf["materials"]), 2)
        # Each mesh: 2 accessors (POSITION + indices) → 4 total
        self.assertEqual(len(gltf["accessors"]), 4)
        self.assertEqual(len(gltf["bufferViews"]), 4)
        self.assertEqual(len(gltf["buffers"]), 1)
        # Single embedded base64 buffer
        self.assertTrue(gltf["buffers"][0]["uri"].startswith(
            "data:application/octet-stream;base64,"))
        # Scene references both nodes
        self.assertEqual(gltf["scenes"][0]["nodes"], [0, 1])
        # Terrain gets its configured colour
        terrain_mat = gltf["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"]
        self.assertEqual(terrain_mat, me._GLTF_COLORS["terrain"])

    def test_gltf_recenter_offset_and_buffer_decodes(self):
        me = _load_me_module()
        meshes = self._two_meshes()
        gltf = me.build_gltf_dict(meshes, recenter=True)
        # Recenter offset = min corner of all vertices (x=100, y=200, z=10)
        self.assertEqual(gltf["extras"]["recenter_offset"], [100.0, 200.0, 10.0])
        # Decode the buffer and check byte length matches the declared length
        import base64
        uri = gltf["buffers"][0]["uri"]
        b64 = uri.split(",", 1)[1]
        raw = base64.b64decode(b64)
        self.assertEqual(len(raw), gltf["buffers"][0]["byteLength"])
        # 7 vertices * 3 floats * 4 bytes + 3 triangles * 3 uint32 * 4 bytes
        expected = (7 * 3 * 4) + (3 * 3 * 4)
        self.assertEqual(len(raw), expected)

    def test_gltf_position_accessor_has_min_max(self):
        me = _load_me_module()
        gltf = me.build_gltf_dict(self._two_meshes())
        pos_acc = gltf["accessors"][0]  # first mesh POSITION
        self.assertEqual(pos_acc["type"], "VEC3")
        self.assertEqual(pos_acc["componentType"], 5126)
        self.assertIn("min", pos_acc)
        self.assertIn("max", pos_acc)
        self.assertEqual(len(pos_acc["min"]), 3)

    def test_write_gltf_is_valid_json(self):
        me = _load_me_module()
        import json
        tmpdir = tempfile.mkdtemp(prefix="gltf_test_")
        try:
            path = os.path.join(tmpdir, "scene.gltf")
            me.write_gltf(path, self._two_meshes())
            with open(path, "r", encoding="utf-8") as fh:
                parsed = json.load(fh)
            self.assertEqual(parsed["asset"]["version"], "2.0")
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestThreeJsViewer(unittest.TestCase):

    def test_viewer_embeds_gltf_and_markers(self):
        me = _load_me_module()
        import tempfile as _tf
        tmpdir = _tf.mkdtemp(prefix="viewer_test_")
        try:
            gltf = me.build_gltf_dict([
                me.MeshData(vertices=[(0, 0, 0), (1, 0, 0), (0, 1, 0)],
                            faces=[(0, 1, 2)], name="terrain"),
            ])
            path = os.path.join(tmpdir, "view.html")
            me.write_three_js_viewer(path, gltf, title="Test <Park>")
            with open(path, "r", encoding="utf-8") as fh:
                html = fh.read()
            # Title is HTML-escaped
            self.assertIn("Test &lt;Park&gt;", html)
            # Three.js import map + GLTFLoader present
            self.assertIn("three.module.js", html)
            self.assertIn("GLTFLoader", html)
            # Embedded glTF JSON with </ escaped to avoid script-tag breakout
            self.assertIn('id="gltf-data"', html)
            self.assertNotIn("</script></script>", html)
            self.assertIn('"version": "2.0"', html)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
