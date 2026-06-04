"""
3D-Mesh-Export for Wind Turbine Earthwork Calculator V2

Exports DEM rasters and constructed surfaces (crane pad, foundation, …) as
Wavefront OBJ meshes for use in external 3D viewers (Three.js, Cesium,
Blender, Sketchfab, etc.) and for downstream BIM workflows.

Supported output formats:
  - OBJ  — ``write_obj`` (human-readable, universal)
  - STL  — ``write_stl`` (ASCII or binary; CAD/3D-printing interchange)
  - glTF — ``write_gltf`` / ``build_gltf_dict`` (native web/Three.js format,
    multiple coloured meshes in one file, recentred + Y-up)
  - HTML — ``write_three_js_viewer`` (self-contained Three.js viewer that
    embeds the glTF inline, so no local-file CORS issues)

The writers and the DEM/polygon mesh builders are QGIS-independent and
unit-testable in plain Python. The DEM helper uses GDAL but does not load
qgis.core. See `docs/plans/V3_ROADMAP.md` Section #5.
"""

from __future__ import annotations

import base64
import json
import math
import os
import struct
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class MeshData:
    """Lightweight triangle mesh: (x, y, z) vertices and (i, j, k) faces.

    Vertex indices are 0-based here; the OBJ writer converts to 1-based.
    """

    vertices: list[tuple[float, float, float]] = field(default_factory=list)
    faces: list[tuple[int, int, int]] = field(default_factory=list)
    name: str = "mesh"

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    @property
    def triangle_count(self) -> int:
        return len(self.faces)

    def extend(self, other: "MeshData") -> None:
        """Merge another mesh into this one, re-indexing the other's faces."""
        offset = len(self.vertices)
        self.vertices.extend(other.vertices)
        self.faces.extend((i + offset, j + offset, k + offset) for i, j, k in other.faces)


# ---------------------------------------------------------------------------
# OBJ writer
# ---------------------------------------------------------------------------


def write_obj(path: str, mesh: MeshData) -> str:
    """Write a `MeshData` to a Wavefront OBJ file.

    Returns the absolute output path. Vertex coordinates are written with 4
    decimal places of precision (1/10 mm at metre scale) — adjust here if a
    different precision is needed.
    """
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)

    with open(abs_path, "w", encoding="utf-8") as fh:
        if mesh.name:
            fh.write(f"# OBJ export: {mesh.name}\n")
        fh.write(f"# {mesh.vertex_count} vertices, {mesh.triangle_count} triangles\n")
        if mesh.name:
            fh.write(f"o {mesh.name}\n")
        for x, y, z in mesh.vertices:
            fh.write(f"v {x:.4f} {y:.4f} {z:.4f}\n")
        # OBJ uses 1-based indices
        for i, j, k in mesh.faces:
            fh.write(f"f {i + 1} {j + 1} {k + 1}\n")

    return abs_path


# ---------------------------------------------------------------------------
# Polygon → mesh (constant height)
# ---------------------------------------------------------------------------


def polygon_to_mesh_at_height(
    polygon_xy: Sequence[tuple[float, float]],
    height: float,
    name: str = "platform",
) -> MeshData:
    """Triangulate a (possibly non-convex) simple polygon at constant z.

    Uses **ear-clipping** triangulation, which handles concave polygons but
    not holes; for the WEA platform types (crane pad, foundation, ramp) this
    is sufficient since they are simple closed polygons without holes.

    `polygon_xy` should be the exterior ring as a sequence of (x, y) points.
    A closing duplicate of the first point is tolerated and ignored.
    Returns a `MeshData` with all vertices at z=`height`.
    """
    pts = list(polygon_xy)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        return MeshData(name=name)

    # Ear-clipping needs a counter-clockwise orientation.
    if _signed_area(pts) < 0:
        pts = list(reversed(pts))

    mesh = MeshData(name=name)
    for x, y in pts:
        mesh.vertices.append((float(x), float(y), float(height)))

    indices = list(range(len(pts)))
    # Standard O(n²) ear-clipping; fine for typical surface polygons (< 100 pts).
    while len(indices) > 3:
        ear_found = False
        for k in range(len(indices)):
            i_prev = indices[k - 1]
            i_curr = indices[k]
            i_next = indices[(k + 1) % len(indices)]
            if _is_ear(pts, i_prev, i_curr, i_next, indices):
                mesh.faces.append((i_prev, i_curr, i_next))
                indices.pop(k)
                ear_found = True
                break
        if not ear_found:
            # Degenerate / self-intersecting input — bail out with what we have.
            break

    if len(indices) == 3:
        mesh.faces.append((indices[0], indices[1], indices[2]))

    return mesh


# ---------------------------------------------------------------------------
# DEM → mesh (GDAL-backed)
# ---------------------------------------------------------------------------


def dem_to_mesh(
    dem_path: str,
    decimation: int = 4,
    nodata_value: Optional[float] = None,
    name: str = "terrain",
) -> MeshData:
    """Convert a DEM raster to a triangle mesh, optionally decimated.

    `decimation` is the integer stride: 1 keeps every pixel, 4 keeps every
    4th pixel in each axis (16× fewer triangles). Nodata pixels are skipped
    and their adjacent quads are omitted.

    Coordinates are emitted in the DEM's CRS (typically UTM metres). The
    GeoTransform is used to map pixel (col, row) → (x, y).
    """
    try:
        from osgeo import gdal
    except ImportError as exc:
        raise ImportError("osgeo.gdal is required for dem_to_mesh") from exc

    if decimation < 1:
        raise ValueError(f"decimation must be >= 1, got {decimation}")

    ds = gdal.Open(dem_path, gdal.GA_ReadOnly)
    if ds is None:
        raise ValueError(f"Could not open DEM: {dem_path}")

    gt = ds.GetGeoTransform()  # (ox, dx, 0, oy, 0, dy)
    band = ds.GetRasterBand(1)
    nodata = nodata_value if nodata_value is not None else band.GetNoDataValue()

    # Use ReadRaster + np.frombuffer to avoid the broken `_gdal_array`
    # bindings in some QGIS builds (see utils/gdal_compat.py).
    import numpy as np
    raw = band.ReadRaster(0, 0, ds.RasterXSize, ds.RasterYSize, buf_type=gdal.GDT_Float32)
    full = np.frombuffer(raw, dtype=np.float32).reshape((ds.RasterYSize, ds.RasterXSize))
    ds = None

    # Decimate via slicing — cheap and exact.
    dem = full[::decimation, ::decimation].copy()
    rows, cols = dem.shape
    if rows < 2 or cols < 2:
        return MeshData(name=name)

    # Pixel-to-world transform for decimated grid
    ox, dx, _, oy, _, dy = gt
    step_x = dx * decimation
    step_y = dy * decimation

    mesh = MeshData(name=name)

    # Build a flat vertex grid; skip nodata vertices by recording None index.
    vertex_index = [[-1] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            z = float(dem[r, c])
            if nodata is not None and z == nodata:
                continue
            # Cell-centre coordinates (most DEMs use pixel-corner GT, but the
            # half-pixel offset is irrelevant for visualisation).
            x = ox + (c + 0.5) * step_x
            y = oy + (r + 0.5) * step_y
            vertex_index[r][c] = len(mesh.vertices)
            mesh.vertices.append((x, y, z))

    # Two triangles per quad, skip quads with any nodata corner.
    for r in range(rows - 1):
        for c in range(cols - 1):
            v_tl = vertex_index[r][c]
            v_tr = vertex_index[r][c + 1]
            v_bl = vertex_index[r + 1][c]
            v_br = vertex_index[r + 1][c + 1]
            if -1 in (v_tl, v_tr, v_bl, v_br):
                continue
            mesh.faces.append((v_tl, v_tr, v_br))
            mesh.faces.append((v_tl, v_br, v_bl))

    return mesh


# ---------------------------------------------------------------------------
# Internal: ear-clipping helpers
# ---------------------------------------------------------------------------


def _signed_area(pts: Sequence[tuple[float, float]]) -> float:
    """Signed area (positive for CCW orientation in screen coords)."""
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += (x2 - x1) * (y2 + y1)
    return -s / 2.0


def _triangle_area_2d(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    """2× the signed area of triangle abc — positive if CCW."""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_in_triangle(p: tuple[float, float],
                       a: tuple[float, float],
                       b: tuple[float, float],
                       c: tuple[float, float]) -> bool:
    """True if p is strictly inside triangle abc (boundary excluded)."""
    d1 = _triangle_area_2d(p, a, b)
    d2 = _triangle_area_2d(p, b, c)
    d3 = _triangle_area_2d(p, c, a)
    has_neg = d1 < 0 or d2 < 0 or d3 < 0
    has_pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (has_neg and has_pos)


def _is_ear(pts: Sequence[tuple[float, float]],
            i_prev: int, i_curr: int, i_next: int,
            remaining: Iterable[int]) -> bool:
    """True if triangle (prev, curr, next) is an ear of the polygon."""
    a, b, c = pts[i_prev], pts[i_curr], pts[i_next]
    # Must be a convex vertex (counter-clockwise turn) — orientation is already CCW.
    if _triangle_area_2d(a, b, c) <= 0:
        return False
    # No other vertex may lie inside the triangle.
    for idx in remaining:
        if idx in (i_prev, i_curr, i_next):
            continue
        if _point_in_triangle(pts[idx], a, b, c):
            return False
    return True


# ---------------------------------------------------------------------------
# STL writer
# ---------------------------------------------------------------------------


def _triangle_normal(v0, v1, v2):
    """Unit normal of triangle (v0, v1, v2); (0,0,0) for degenerate triangles."""
    ux, uy, uz = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
    vx, vy, vz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


def write_stl(path: str, mesh: MeshData, binary: bool = False) -> str:
    """Write a `MeshData` to an STL file (ASCII by default, binary optional).

    STL has no concept of objects or colours, so one mesh maps to one file.
    Binary STL is far more compact for large terrain meshes; ASCII is
    human-readable. Returns the absolute output path.
    """
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    name = mesh.name or "mesh"

    if binary:
        with open(abs_path, "wb") as fh:
            header = f"STL {name}".encode("ascii", "replace")[:80]
            fh.write(header + b" " * (80 - len(header)))
            fh.write(struct.pack("<I", mesh.triangle_count))
            for i, j, k in mesh.faces:
                v0, v1, v2 = mesh.vertices[i], mesh.vertices[j], mesh.vertices[k]
                nx, ny, nz = _triangle_normal(v0, v1, v2)
                fh.write(struct.pack("<fff", nx, ny, nz))
                for v in (v0, v1, v2):
                    fh.write(struct.pack("<fff", v[0], v[1], v[2]))
                fh.write(struct.pack("<H", 0))  # attribute byte count
        return abs_path

    lines = [f"solid {name}"]
    for i, j, k in mesh.faces:
        v0, v1, v2 = mesh.vertices[i], mesh.vertices[j], mesh.vertices[k]
        nx, ny, nz = _triangle_normal(v0, v1, v2)
        lines.append(f"  facet normal {nx:.6e} {ny:.6e} {nz:.6e}")
        lines.append("    outer loop")
        for v in (v0, v1, v2):
            lines.append(f"      vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {name}")

    with open(abs_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return abs_path


# ---------------------------------------------------------------------------
# glTF writer
# ---------------------------------------------------------------------------


# Per-surface base colours (RGBA 0..1) for the glTF materials / viewer.
_GLTF_COLORS = {
    "terrain": [0.70, 0.68, 0.62, 1.0],
    "kranstellflaeche": [0.85, 0.20, 0.20, 1.0],
    "fundamentsohle": [0.55, 0.27, 0.07, 1.0],
    "auslegerflaeche": [0.10, 0.65, 0.20, 1.0],
    "rotorflaeche": [0.65, 0.10, 0.65, 1.0],
    "zufahrt": [0.10, 0.30, 0.80, 1.0],
}
_GLTF_COLOR_DEFAULT = [0.50, 0.50, 0.55, 1.0]


def build_gltf_dict(meshes: Sequence[MeshData], recenter: bool = True) -> dict:
    """Build a glTF 2.0 document (as a dict) from one or more meshes.

    - Multiple meshes become separate nodes with per-name PBR materials, so a
      terrain + several surfaces render as distinct coloured objects.
    - Coordinates are converted from the project's Z-up (x=easting, y=northing,
      z=elevation) to glTF's right-handed Y-up: ``(x, z, -y)``.
    - When ``recenter`` is True the min corner is subtracted before writing, so
      large UTM coordinates do not lose precision in float32 and the model sits
      near the origin for easy camera framing.

    All geometry shares a single base64-embedded binary buffer, so the result
    is a self-contained ``.gltf`` needing no sidecar ``.bin``.
    """
    non_empty = [m for m in meshes if m.triangle_count > 0 and m.vertex_count > 0]
    if not non_empty:
        return {
            "asset": {"version": "2.0", "generator": "windturbine-mesh-exporter"},
            "scenes": [{"nodes": []}], "scene": 0, "nodes": [], "meshes": [],
        }

    if recenter:
        ox = min(v[0] for m in non_empty for v in m.vertices)
        oy = min(v[1] for m in non_empty for v in m.vertices)
        oz = min(v[2] for m in non_empty for v in m.vertices)
    else:
        ox = oy = oz = 0.0

    blob = bytearray()
    buffer_views = []
    accessors = []
    gltf_meshes = []
    materials = []
    nodes = []

    for mi, mesh in enumerate(non_empty):
        # Positions: Z-up → Y-up, recentred.
        gx_list, gy_list, gz_list = [], [], []
        pos_bytes = bytearray()
        for (x, y, z) in mesh.vertices:
            gx = x - ox
            gy = z - oz       # elevation becomes Y (up)
            gz = -(y - oy)    # northing becomes -Z (right-handed)
            pos_bytes += struct.pack("<fff", gx, gy, gz)
            gx_list.append(gx)
            gy_list.append(gy)
            gz_list.append(gz)
        pos_offset = len(blob)
        blob += pos_bytes

        idx_bytes = bytearray()
        for (a, b, c) in mesh.faces:
            idx_bytes += struct.pack("<III", a, b, c)
        idx_offset = len(blob)
        blob += idx_bytes

        pos_bv = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": pos_offset,
                             "byteLength": len(pos_bytes), "target": 34962})
        idx_bv = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": idx_offset,
                             "byteLength": len(idx_bytes), "target": 34963})

        pos_acc = len(accessors)
        accessors.append({
            "bufferView": pos_bv, "componentType": 5126,  # FLOAT
            "count": mesh.vertex_count, "type": "VEC3",
            "min": [min(gx_list), min(gy_list), min(gz_list)],
            "max": [max(gx_list), max(gy_list), max(gz_list)],
        })
        idx_acc = len(accessors)
        accessors.append({
            "bufferView": idx_bv, "componentType": 5125,  # UNSIGNED_INT
            "count": mesh.triangle_count * 3, "type": "SCALAR",
        })

        mat_idx = len(materials)
        colour = _GLTF_COLORS.get(mesh.name, _GLTF_COLOR_DEFAULT)
        materials.append({
            "name": f"{mesh.name}_mat",
            "pbrMetallicRoughness": {
                "baseColorFactor": colour,
                "metallicFactor": 0.1,
                "roughnessFactor": 0.85,
            },
            "doubleSided": True,
        })

        gltf_meshes.append({
            "name": mesh.name,
            "primitives": [{
                "attributes": {"POSITION": pos_acc},
                "indices": idx_acc,
                "material": mat_idx,
            }],
        })
        nodes.append({"mesh": mi, "name": mesh.name})

    uri = "data:application/octet-stream;base64," + base64.b64encode(bytes(blob)).decode("ascii")

    return {
        "asset": {"version": "2.0", "generator": "windturbine-mesh-exporter"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": gltf_meshes,
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"uri": uri, "byteLength": len(blob)}],
        "extras": {"recenter_offset": [ox, oy, oz]},
    }


def write_gltf(path: str, meshes: Sequence[MeshData], recenter: bool = True) -> str:
    """Write one or more meshes to a self-contained ``.gltf`` file."""
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    gltf = build_gltf_dict(meshes, recenter=recenter)
    with open(abs_path, "w", encoding="utf-8") as fh:
        json.dump(gltf, fh)
    return abs_path


# ---------------------------------------------------------------------------
# Three.js viewer
# ---------------------------------------------------------------------------


def write_three_js_viewer(path: str, gltf_dict: dict,
                          title: str = "WEA 3D-Ansicht") -> str:
    """Write a self-contained HTML viewer that renders ``gltf_dict`` with Three.js.

    The glTF document is embedded inline as JSON and parsed via
    ``GLTFLoader.parse`` — so the viewer has no local-file CORS problems and
    needs no sidecar mesh files. Three.js itself is loaded from a CDN
    (jsDelivr) via an ES-module import map, so opening the file requires
    internet access once (the browser caches it afterwards).
    """
    import html as _html

    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)

    gltf_json = json.dumps(gltf_dict)
    safe_title = _html.escape(title)
    # Keep the embedded JSON out of a <script> close-tag injection.
    gltf_json_safe = gltf_json.replace("</", "<\\/")

    template = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<style>
  html, body { margin: 0; height: 100%; overflow: hidden; font-family: sans-serif; }
  #info { position: absolute; top: 8px; left: 8px; padding: 6px 10px;
          background: rgba(255,255,255,0.8); border-radius: 4px; font-size: 12px; }
  #c { width: 100vw; height: 100vh; display: block; }
</style>
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
  }
}
</script>
</head>
<body>
<div id="info">__TITLE__ — Maus: drehen / zoomen / verschieben</div>
<canvas id="c"></canvas>
<script id="gltf-data" type="application/json">__GLTF__</script>
<script type="module">
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeef1f4);

const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 100000);
const controls = new OrbitControls(camera, renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 0.7));
const sun = new THREE.DirectionalLight(0xffffff, 0.9);
sun.position.set(1, 2, 1);
scene.add(sun);

const data = JSON.parse(document.getElementById('gltf-data').textContent);
const loader = new GLTFLoader();
loader.parse(JSON.stringify(data), '', (gltf) => {
  scene.add(gltf.scene);
  // Frame the camera to the model bounding box.
  const box = new THREE.Box3().setFromObject(gltf.scene);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  camera.position.set(center.x + maxDim, center.y + maxDim, center.z + maxDim);
  camera.near = maxDim / 1000;
  camera.far = maxDim * 1000;
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.update();
}, (err) => {
  document.getElementById('info').textContent = 'Fehler beim Laden der 3D-Daten: ' + err;
});

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
</script>
</body>
</html>
"""
    html_out = (template
                .replace("__TITLE__", safe_title)
                .replace("__GLTF__", gltf_json_safe))

    with open(abs_path, "w", encoding="utf-8") as fh:
        fh.write(html_out)
    return abs_path
