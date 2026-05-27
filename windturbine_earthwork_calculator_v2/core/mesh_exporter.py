"""
3D-Mesh-Export for Wind Turbine Earthwork Calculator V2

Exports DEM rasters and constructed surfaces (crane pad, foundation, …) as
Wavefront OBJ meshes for use in external 3D viewers (Three.js, Cesium,
Blender, Sketchfab, etc.) and for downstream BIM workflows.

OBJ was chosen for the first iteration because it is:
  - human-readable (easy to debug),
  - universally supported by 3D tools,
  - free of binary-encoding dependencies.

STL and glTF can be added later by extending the small `MeshData` data class
with format-specific writers. See `docs/plans/V3_ROADMAP.md` Section #5.

The core helpers (write_obj, polygon_to_mesh_at_height) are
QGIS-independent and unit-testable in plain Python. The DEM helper uses GDAL
but does not load qgis.core.
"""

from __future__ import annotations

import math
import os
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
