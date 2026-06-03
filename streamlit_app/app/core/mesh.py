"""
3D-Mesh-Export (Port aus core/mesh_exporter.py).

OBJ, STL (ASCII+Binary), glTF 2.0 (embedded), Three.js-Viewer-HTML.
DEM→Mesh nutzt rasterio statt GDAL direkt.
"""

from __future__ import annotations

import base64
import html as _html
import json
import math
import os
import struct
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence


@dataclass
class MeshData:
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
        offset = len(self.vertices)
        self.vertices.extend(other.vertices)
        self.faces.extend((i + offset, j + offset, k + offset) for i, j, k in other.faces)


# ---------------------------------------------------------------- Ear-clipping

def _signed_area(pts: Sequence[tuple[float, float]]) -> float:
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += (x2 - x1) * (y2 + y1)
    return -s / 2.0


def _triangle_area_2d(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_in_triangle(p, a, b, c) -> bool:
    d1 = _triangle_area_2d(p, a, b)
    d2 = _triangle_area_2d(p, b, c)
    d3 = _triangle_area_2d(p, c, a)
    has_neg = d1 < 0 or d2 < 0 or d3 < 0
    has_pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (has_neg and has_pos)


def _is_ear(pts, i_prev, i_curr, i_next, remaining) -> bool:
    a, b, c = pts[i_prev], pts[i_curr], pts[i_next]
    if _triangle_area_2d(a, b, c) <= 0:
        return False
    for idx in remaining:
        if idx in (i_prev, i_curr, i_next):
            continue
        if _point_in_triangle(pts[idx], a, b, c):
            return False
    return True


def polygon_to_mesh_at_height(
    polygon_xy: Sequence[tuple[float, float]], height: float, name: str = "platform"
) -> MeshData:
    """Triangulate ein Polygon bei konstantem z (Ear-Clipping, kein Loch-Support)."""
    pts = list(polygon_xy)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        return MeshData(name=name)
    if _signed_area(pts) < 0:
        pts = list(reversed(pts))

    mesh = MeshData(name=name)
    for x, y in pts:
        mesh.vertices.append((float(x), float(y), float(height)))
    indices = list(range(len(pts)))
    while len(indices) > 3:
        ear = False
        for k in range(len(indices)):
            i_prev = indices[k - 1]
            i_curr = indices[k]
            i_next = indices[(k + 1) % len(indices)]
            if _is_ear(pts, i_prev, i_curr, i_next, indices):
                mesh.faces.append((i_prev, i_curr, i_next))
                indices.pop(k)
                ear = True
                break
        if not ear:
            break
    if len(indices) == 3:
        mesh.faces.append((indices[0], indices[1], indices[2]))
    return mesh


# ---------------------------------------------------------------- DEM→Mesh (rasterio)

def dem_to_mesh(
    dem_path: str,
    decimation: int = 4,
    nodata_value: Optional[float] = None,
    name: str = "terrain",
) -> MeshData:
    """DEM-Raster → Dreieck-Mesh via rasterio (NoData übersprungen)."""
    import numpy as np
    import rasterio

    if decimation < 1:
        raise ValueError(f"decimation must be >= 1, got {decimation}")
    with rasterio.open(dem_path) as src:
        full = src.read(1).astype("float32")
        gt_a, gt_b, gt_c = src.transform.a, src.transform.b, src.transform.c
        gt_d, gt_e, gt_f = src.transform.d, src.transform.e, src.transform.f
        nodata = nodata_value if nodata_value is not None else src.nodata

    dem = full[::decimation, ::decimation].copy()
    rows, cols = dem.shape
    if rows < 2 or cols < 2:
        return MeshData(name=name)

    step_x = gt_a * decimation
    step_y = gt_e * decimation  # negativ bei north-up

    mesh = MeshData(name=name)
    vertex_index = [[-1] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            z = float(dem[r, c])
            if nodata is not None and z == nodata:
                continue
            x = gt_c + (c + 0.5) * step_x
            y = gt_f + (r + 0.5) * step_y
            vertex_index[r][c] = len(mesh.vertices)
            mesh.vertices.append((x, y, z))

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


# ---------------------------------------------------------------- Writers

def write_obj(path: str, mesh: MeshData) -> str:
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
        for i, j, k in mesh.faces:
            fh.write(f"f {i + 1} {j + 1} {k + 1}\n")
    return abs_path


def _triangle_normal(v0, v1, v2):
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
                fh.write(struct.pack("<H", 0))
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


# ---------------------------------------------------------------- glTF

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
    non_empty = [m for m in meshes if m.triangle_count > 0 and m.vertex_count > 0]
    if not non_empty:
        return {
            "asset": {"version": "2.0", "generator": "wtec-mesh"},
            "scenes": [{"nodes": []}],
            "scene": 0,
            "nodes": [],
            "meshes": [],
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
        pos_bytes = bytearray()
        gx_list, gy_list, gz_list = [], [], []
        for x, y, z in mesh.vertices:
            gx = x - ox
            gy = z - oz
            gz = -(y - oy)
            pos_bytes += struct.pack("<fff", gx, gy, gz)
            gx_list.append(gx)
            gy_list.append(gy)
            gz_list.append(gz)
        pos_offset = len(blob)
        blob += pos_bytes
        idx_bytes = bytearray()
        for a, b, c in mesh.faces:
            idx_bytes += struct.pack("<III", a, b, c)
        idx_offset = len(blob)
        blob += idx_bytes

        pos_bv = len(buffer_views)
        buffer_views.append(
            {"buffer": 0, "byteOffset": pos_offset, "byteLength": len(pos_bytes), "target": 34962}
        )
        idx_bv = len(buffer_views)
        buffer_views.append(
            {"buffer": 0, "byteOffset": idx_offset, "byteLength": len(idx_bytes), "target": 34963}
        )

        pos_acc = len(accessors)
        accessors.append(
            {
                "bufferView": pos_bv,
                "componentType": 5126,
                "count": mesh.vertex_count,
                "type": "VEC3",
                "min": [min(gx_list), min(gy_list), min(gz_list)],
                "max": [max(gx_list), max(gy_list), max(gz_list)],
            }
        )
        idx_acc = len(accessors)
        accessors.append(
            {"bufferView": idx_bv, "componentType": 5125, "count": mesh.triangle_count * 3, "type": "SCALAR"}
        )
        mat_idx = len(materials)
        colour = _GLTF_COLORS.get(mesh.name, _GLTF_COLOR_DEFAULT)
        materials.append(
            {
                "name": f"{mesh.name}_mat",
                "pbrMetallicRoughness": {
                    "baseColorFactor": colour,
                    "metallicFactor": 0.1,
                    "roughnessFactor": 0.85,
                },
                "doubleSided": True,
            }
        )
        gltf_meshes.append(
            {
                "name": mesh.name,
                "primitives": [
                    {
                        "attributes": {"POSITION": pos_acc},
                        "indices": idx_acc,
                        "material": mat_idx,
                    }
                ],
            }
        )
        nodes.append({"mesh": mi, "name": mesh.name})

    uri = "data:application/octet-stream;base64," + base64.b64encode(bytes(blob)).decode("ascii")
    return {
        "asset": {"version": "2.0", "generator": "wtec-mesh"},
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
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    gltf = build_gltf_dict(meshes, recenter=recenter)
    with open(abs_path, "w", encoding="utf-8") as fh:
        json.dump(gltf, fh)
    return abs_path


# ---------------------------------------------------------------- Three.js Viewer

def write_three_js_viewer(path: str, gltf_dict: dict, title: str = "WEA 3D-Ansicht") -> str:
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    gltf_json = json.dumps(gltf_dict).replace("</", "<\\/")
    safe_title = _html.escape(title)
    template = """<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8">
<title>__TITLE__</title>
<style>html,body{margin:0;height:100%;overflow:hidden;font-family:sans-serif}
#info{position:absolute;top:8px;left:8px;padding:6px 10px;background:rgba(255,255,255,0.8);border-radius:4px;font-size:12px}
#c{width:100vw;height:100vh;display:block}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head><body>
<div id="info">__TITLE__ — Maus: drehen / zoomen / verschieben</div>
<canvas id="c"></canvas>
<script id="gltf-data" type="application/json">__GLTF__</script>
<script type="module">
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const canvas=document.getElementById('c');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true});
renderer.setSize(window.innerWidth,window.innerHeight);renderer.setPixelRatio(window.devicePixelRatio);
const scene=new THREE.Scene();scene.background=new THREE.Color(0xeef1f4);
const camera=new THREE.PerspectiveCamera(55,window.innerWidth/window.innerHeight,0.1,100000);
const controls=new OrbitControls(camera,renderer.domElement);
scene.add(new THREE.AmbientLight(0xffffff,0.7));
const sun=new THREE.DirectionalLight(0xffffff,0.9);sun.position.set(1,2,1);scene.add(sun);
const data=JSON.parse(document.getElementById('gltf-data').textContent);
const loader=new GLTFLoader();
loader.parse(JSON.stringify(data),'',(gltf)=>{scene.add(gltf.scene);
const box=new THREE.Box3().setFromObject(gltf.scene);
const size=box.getSize(new THREE.Vector3());const center=box.getCenter(new THREE.Vector3());
const maxDim=Math.max(size.x,size.y,size.z)||1;
camera.position.set(center.x+maxDim,center.y+maxDim,center.z+maxDim);
camera.near=maxDim/1000;camera.far=maxDim*1000;camera.updateProjectionMatrix();
controls.target.copy(center);controls.update();});
function animate(){requestAnimationFrame(animate);controls.update();renderer.render(scene,camera);}animate();
window.addEventListener('resize',()=>{camera.aspect=window.innerWidth/window.innerHeight;camera.updateProjectionMatrix();renderer.setSize(window.innerWidth,window.innerHeight);});
</script></body></html>"""
    html_out = template.replace("__TITLE__", safe_title).replace("__GLTF__", gltf_json)
    with open(abs_path, "w", encoding="utf-8") as fh:
        fh.write(html_out)
    return abs_path
