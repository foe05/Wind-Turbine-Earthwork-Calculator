"""
Geometry-Hilfsfunktionen für WTEC (Shapely-Port von utils/geometry_utils.py).

Portiert aus windturbine_earthwork_calculator_v2/utils/geometry_utils.py
ohne QGIS-Abhängigkeiten. QgsGeometry -> shapely.geometry, QgsPointXY -> (x, y)-Tupel
bzw. shapely.geometry.Point an Stellen, an denen Aufrufer .x/.y erwarten.

Signaturen sind nahe am Plugin-Original gehalten, damit nachfolgende Portierungen
(multi_surface_calculator, profile_generator) sie unverändert konsumieren können.
"""

from __future__ import annotations

import math
from typing import Iterable, Optional, Sequence

from shapely.geometry import (
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
    box,
)
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points, unary_union


# ---------------------------------------------------------------------------
# Punkte / Distanzen
# ---------------------------------------------------------------------------

def point_distance(p1: Sequence[float], p2: Sequence[float]) -> float:
    """Euklidische Distanz zwischen zwei (x, y)-Tupeln."""
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def find_nearest_point(
    target: Sequence[float],
    candidates: Sequence[Sequence[float]],
    max_distance: Optional[float] = None,
) -> tuple[Optional[tuple[float, float]], Optional[float], Optional[int]]:
    """Nähester Punkt aus einer Liste — (point, distance, index) oder (None, None, None)."""
    if not candidates:
        return None, None, None

    min_dist = float("inf")
    nearest_pt = None
    nearest_idx = None
    for i, c in enumerate(candidates):
        d = point_distance(target, c)
        if d < min_dist:
            min_dist = d
            nearest_pt = (c[0], c[1])
            nearest_idx = i

    if max_distance is not None and min_dist > max_distance:
        return None, None, None
    return nearest_pt, min_dist, nearest_idx


# ---------------------------------------------------------------------------
# Polygon-Basics
# ---------------------------------------------------------------------------

def buffer_geometry(geometry: BaseGeometry, distance: float) -> BaseGeometry:
    """Buffer mit 8 Segmenten pro Viertelkreis (analog QGIS-Default)."""
    return geometry.buffer(distance, quad_segs=8)


def get_centroid(geometry: BaseGeometry) -> Point:
    """Schwerpunkt als shapely.Point (mit .x/.y-Zugriff)."""
    return geometry.centroid


def create_bbox_with_buffer(geometry: BaseGeometry, buffer_distance: float) -> tuple[float, float, float, float]:
    """Bounding-Box (minx, miny, maxx, maxy) inkl. Puffer."""
    minx, miny, maxx, maxy = geometry.bounds
    return (
        minx - buffer_distance,
        miny - buffer_distance,
        maxx + buffer_distance,
        maxy + buffer_distance,
    )


def get_polygon_vertices(geometry: BaseGeometry) -> list[tuple[float, float]]:
    """Vertices der äußeren Hülle als (x, y)-Tupel; MultiPolygon nutzt erste Komponente."""
    if geometry.is_empty:
        return []
    if isinstance(geometry, MultiPolygon):
        first = next(iter(geometry.geoms), None)
        if first is None:
            return []
        return list(first.exterior.coords)
    if isinstance(geometry, Polygon):
        return list(geometry.exterior.coords)
    return []


def get_polygon_boundary(geometry: BaseGeometry) -> Optional[LineString]:
    """Äußere Hülle eines Polygons als LineString. None bei Nicht-Polygon."""
    verts = get_polygon_vertices(geometry)
    if len(verts) < 2:
        return None
    return LineString(verts)


def get_polygon_radius(geometry: BaseGeometry) -> float:
    """Distanz vom Centroid zum entferntesten Polygon-Vertex."""
    c = get_centroid(geometry)
    vertices = get_polygon_vertices(geometry)
    if not vertices:
        return 0.0
    return max(math.hypot(v[0] - c.x, v[1] - c.y) for v in vertices)


# ---------------------------------------------------------------------------
# Orientierung
# ---------------------------------------------------------------------------

def get_polygon_orientation(geometry: BaseGeometry) -> float:
    """Orientierung über die längste Kante; Rückgabe in [0, 180)."""
    vertices = get_polygon_vertices(geometry)
    if len(vertices) < 3:
        return 0.0

    max_length = 0.0
    longest_angle = 0.0
    for i in range(len(vertices) - 1):
        p1 = vertices[i]
        p2 = vertices[i + 1]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length > max_length:
            max_length = length
            angle_deg = math.degrees(math.atan2(dy, dx))
            if angle_deg < 0:
                angle_deg += 180
            elif angle_deg > 180:
                angle_deg -= 180
            longest_angle = angle_deg
    return float(longest_angle)


def perpendicular_direction(angle: float) -> float:
    """Senkrechte Richtung, normalisiert auf [0, 360)."""
    perp = angle + 90.0
    if perp >= 360:
        perp -= 360
    return perp


# ---------------------------------------------------------------------------
# Polygon-Breite an einem Punkt
# ---------------------------------------------------------------------------

def get_polygon_width_at_point(
    geometry: BaseGeometry, point: Point, direction_angle: float
) -> float:
    """Polygon-Breite senkrecht zur direction_angle durch einen Punkt; 0 wenn kein Schnitt."""
    perp_rad = math.radians(direction_angle + 90.0)
    half_length = 1000.0
    x1 = point.x - half_length * math.cos(perp_rad)
    y1 = point.y - half_length * math.sin(perp_rad)
    x2 = point.x + half_length * math.cos(perp_rad)
    y2 = point.y + half_length * math.sin(perp_rad)
    test_line = LineString([(x1, y1), (x2, y2)])

    boundary = get_polygon_boundary(geometry)
    if boundary is None or not boundary.intersects(test_line):
        return 0.0

    inter = boundary.intersection(test_line)
    pts = _collect_points(inter)
    if len(pts) < 2:
        return 0.0
    return _max_pairwise_distance(pts)


# ---------------------------------------------------------------------------
# Oriented Bounding Box
# ---------------------------------------------------------------------------

def create_oriented_bounding_box(
    geometries: Sequence[BaseGeometry],
    main_angle: float,
    buffer_percent: float = 10.0,
) -> Optional[dict]:
    """Achsenausgerichtete BBox um mehrere Geometrien, ausgerichtet an main_angle."""
    if not geometries:
        return None

    combined = unary_union(list(geometries))
    centroid = get_centroid(combined)

    main_rad = math.radians(main_angle)
    main_ax = (math.cos(main_rad), math.sin(main_rad))
    perp_rad = math.radians(main_angle + 90.0)
    perp_ax = (math.cos(perp_rad), math.sin(perp_rad))

    all_vertices: list[tuple[float, float]] = []
    for g in geometries:
        all_vertices.extend(get_polygon_vertices(g))
    if not all_vertices:
        return None

    mains, perps = [], []
    for vx, vy in all_vertices:
        dx = vx - centroid.x
        dy = vy - centroid.y
        mains.append(dx * main_ax[0] + dy * main_ax[1])
        perps.append(dx * perp_ax[0] + dy * perp_ax[1])

    min_main, max_main = min(mains), max(mains)
    min_perp, max_perp = min(perps), max(perps)
    length = max_main - min_main
    width = max_perp - min_perp
    buf_len = length * (buffer_percent / 100.0)
    buf_wid = width * (buffer_percent / 100.0)
    min_main -= buf_len
    max_main += buf_len
    min_perp -= buf_wid
    max_perp += buf_wid

    corners = []
    for mo, po in [
        (min_main, min_perp),
        (max_main, min_perp),
        (max_main, max_perp),
        (min_main, max_perp),
    ]:
        x = centroid.x + mo * main_ax[0] + po * perp_ax[0]
        y = centroid.y + mo * main_ax[1] + po * perp_ax[1]
        corners.append((x, y))
    corners.append(corners[0])

    return {
        "bbox_polygon": Polygon(corners),
        "center": centroid,
        "width": max_perp - min_perp,
        "length": max_main - min_main,
        "main_angle": main_angle,
        "min_main": min_main,
        "max_main": max_main,
        "min_perp": min_perp,
        "max_perp": max_perp,
    }


# ---------------------------------------------------------------------------
# Querschnitte / Längsprofile durch Polygon
# ---------------------------------------------------------------------------

def create_perpendicular_cross_sections(
    geometry: BaseGeometry, spacing: float = 10.0, overhang_percent: float = 10.0
) -> list[dict]:
    """Querschnittslinien senkrecht zur Hauptorientierung; einheitliche Länge."""
    main_angle = get_polygon_orientation(geometry)
    return _section_lines_through_polygon(
        geometry,
        section_angle=main_angle + 90.0,  # senkrecht
        scan_angle=main_angle,            # gerichtet entlang
        spacing=spacing,
        overhang_percent=overhang_percent,
        type_prefix="Querschnitt",
        cross_angle_key="cross_angle",
    )


def create_parallel_longitudinal_sections(
    geometry: BaseGeometry, spacing: float = 10.0, overhang_percent: float = 10.0
) -> list[dict]:
    """Längsprofile parallel zur Hauptorientierung; einheitliche Länge."""
    main_angle = get_polygon_orientation(geometry)
    return _section_lines_through_polygon(
        geometry,
        section_angle=main_angle,
        scan_angle=main_angle + 90.0,
        spacing=spacing,
        overhang_percent=overhang_percent,
        type_prefix="Längsprofil",
        cross_angle_key="longitudinal_angle",
    )


def create_cross_sections_over_bbox(bbox_info: dict, spacing: float = 10.0) -> list[dict]:
    """Querschnittslinien über eine Oriented-BBox (volle Breite)."""
    if not bbox_info:
        return []
    main_angle = bbox_info["main_angle"]
    center = bbox_info["center"]
    width = bbox_info["width"]
    cross_rad = math.radians(main_angle + 90.0)
    main_rad = math.radians(main_angle)
    main_ax = (math.cos(main_rad), math.sin(main_rad))
    perp_ax = (math.cos(cross_rad), math.sin(cross_rad))

    extent = bbox_info["max_main"] - bbox_info["min_main"]
    num = max(1, int(extent / spacing) + 1)
    sections = []
    for i in range(num):
        t = bbox_info["min_main"] + i * spacing
        if t > bbox_info["max_main"]:
            break
        cx = center.x + t * main_ax[0]
        cy = center.y + t * main_ax[1]
        x1 = cx + bbox_info["min_perp"] * perp_ax[0]
        y1 = cy + bbox_info["min_perp"] * perp_ax[1]
        x2 = cx + bbox_info["max_perp"] * perp_ax[0]
        y2 = cy + bbox_info["max_perp"] * perp_ax[1]
        sections.append(
            {
                "geometry": LineString([(x1, y1), (x2, y2)]),
                "type": f"Querschnitt {i+1:02d}",
                "main_angle": main_angle,
                "cross_angle": main_angle + 90.0,
                "center_point": Point(cx, cy),
                "length": width,
            }
        )
    return sections


def create_longitudinal_sections_over_bbox(bbox_info: dict, spacing: float = 10.0) -> list[dict]:
    """Längsprofile parallel zur Hauptachse einer Oriented-BBox."""
    if not bbox_info:
        return []
    main_angle = bbox_info["main_angle"]
    center = bbox_info["center"]
    length = bbox_info["length"]
    long_rad = math.radians(main_angle)
    perp_rad = math.radians(main_angle + 90.0)
    main_ax = (math.cos(long_rad), math.sin(long_rad))
    perp_ax = (math.cos(perp_rad), math.sin(perp_rad))

    extent = bbox_info["max_perp"] - bbox_info["min_perp"]
    num = max(1, int(extent / spacing) + 1)
    sections = []
    for i in range(num):
        t = bbox_info["min_perp"] + i * spacing
        if t > bbox_info["max_perp"]:
            break
        cx = center.x + t * perp_ax[0]
        cy = center.y + t * perp_ax[1]
        x1 = cx + bbox_info["min_main"] * main_ax[0]
        y1 = cy + bbox_info["min_main"] * main_ax[1]
        x2 = cx + bbox_info["max_main"] * main_ax[0]
        y2 = cy + bbox_info["max_main"] * main_ax[1]
        sections.append(
            {
                "geometry": LineString([(x1, y1), (x2, y2)]),
                "type": f"Längsprofil {i+1:02d}",
                "main_angle": main_angle,
                "longitudinal_angle": main_angle,
                "center_point": Point(cx, cy),
                "length": length,
            }
        )
    return sections


# ---------------------------------------------------------------------------
# Multi-Surface-Helfer
# ---------------------------------------------------------------------------

def find_connection_edge(
    polygon1: BaseGeometry, polygon2: BaseGeometry, tolerance: float = 0.5
) -> tuple[BaseGeometry, float]:
    """Geteilte Grenzlinie zwischen zwei Polygonen mit Toleranz für DXF-Lücken."""
    boundary1 = get_polygon_boundary(polygon1)
    boundary2 = get_polygon_boundary(polygon2)
    if boundary1 is None or boundary2 is None:
        return LineString(), 0.0

    direct = boundary1.intersection(boundary2)
    if not direct.is_empty and "LineString" in direct.geom_type:
        return direct, direct.length

    buf1 = boundary1.buffer(tolerance, quad_segs=5)
    buf2 = boundary2.buffer(tolerance, quad_segs=5)
    overlap = buf1.intersection(buf2)
    if not overlap.is_empty and overlap.geom_type in ("Polygon", "MultiPolygon"):
        approx = boundary1.intersection(overlap)
        if not approx.is_empty and "LineString" in approx.geom_type:
            return approx, approx.length

    # Fallback: nahe Vertex-Paare
    verts1 = list(boundary1.coords)
    verts2 = list(boundary2.coords)
    pairs = [
        (v1, v2, math.hypot(v1[0] - v2[0], v1[1] - v2[1]))
        for v1 in verts1
        for v2 in verts2
        if math.hypot(v1[0] - v2[0], v1[1] - v2[1]) <= tolerance
    ]
    if pairs:
        pairs.sort(key=lambda x: x[2])
        v1, v2, _ = pairs[0]
        midx = (v1[0] + v2[0]) / 2.0
        midy = (v1[1] + v2[1]) / 2.0
        line = LineString([(midx - 0.1, midy), (midx + 0.1, midy)])
        total = sum(p[2] for p in pairs[: min(10, len(pairs))])
        avg_len = total / max(1, len(pairs[:10]))
        return line, max(line.length, avg_len)

    return LineString(), 0.0


def get_connection_edge_center(edge_geometry: BaseGeometry) -> Point:
    if edge_geometry.is_empty:
        raise ValueError("Edge geometry is empty")
    return edge_geometry.centroid


def get_edge_direction(edge_geometry: BaseGeometry) -> float:
    """Richtung einer Edge (0–360) vom ersten zum letzten Vertex."""
    if isinstance(edge_geometry, MultiLineString):
        first = next(iter(edge_geometry.geoms), None)
        if first is None:
            raise ValueError("Empty MultiLineString")
        coords = list(first.coords)
    elif isinstance(edge_geometry, LineString):
        coords = list(edge_geometry.coords)
    else:
        raise ValueError("Edge must be a LineString")
    if len(coords) < 2:
        raise ValueError("Edge must have at least 2 vertices")
    p1, p2 = coords[0], coords[-1]
    angle = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
    if angle < 0:
        angle += 360
    return angle


def calculate_distance_from_edge(
    point: Point, edge_geometry: BaseGeometry, direction: float
) -> float:
    """Vorzeichenbehaftete Distanz vom Punkt zur Edge entlang einer Richtung."""
    closest_on_edge, _ = nearest_points(edge_geometry, point)
    dx = point.x - closest_on_edge.x
    dy = point.y - closest_on_edge.y
    dir_rad = math.radians(direction)
    return dx * math.cos(dir_rad) + dy * math.sin(dir_rad)


def calculate_slope_height(
    base_height: float,
    distance: float,
    slope_percent: float,
    slope_direction: str = "down",
) -> float:
    """Höhe in distance Metern Entfernung bei gegebener Neigung."""
    delta = distance * (slope_percent / 100.0)
    return base_height - delta if slope_direction == "down" else base_height + delta


def identify_surface_at_point(
    point: Point, surface_geometries: dict[str, BaseGeometry]
) -> Optional[str]:
    """Name der Surface, die einen Punkt enthält (oder None)."""
    for name, geom in surface_geometries.items():
        if geom.contains(point):
            return name
    return None


def calculate_terrain_slope(elevations: Sequence[float], distances: Sequence[float]) -> float:
    """Lineare Regression -> mittlere Geländeneigung in Prozent."""
    if len(elevations) < 2 or len(distances) < 2:
        return 0.0
    n = len(elevations)
    sum_x = sum(distances)
    sum_y = sum(elevations)
    sum_xy = sum(d * e for d, e in zip(distances, elevations))
    sum_x2 = sum(d * d for d in distances)
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-10:
        return 0.0
    slope_m_per_m = (n * sum_xy - sum_x * sum_y) / denom
    return slope_m_per_m * 100.0


# ---------------------------------------------------------------------------
# Radial-Linien (für Profile)
# ---------------------------------------------------------------------------

def create_radial_lines(
    center: Point, radius: float, num_lines: int = 8, angle_offset: float = 0.0
) -> list[LineString]:
    """N radiale Linien um einen Mittelpunkt."""
    step = 360.0 / num_lines
    lines = []
    for i in range(num_lines):
        angle = math.radians(angle_offset + i * step)
        end = (center.x + radius * math.cos(angle), center.y + radius * math.sin(angle))
        lines.append(LineString([(center.x, center.y), end]))
    return lines


# ---------------------------------------------------------------------------
# Interne Helpers
# ---------------------------------------------------------------------------

def _collect_points(geom: BaseGeometry) -> list[Point]:
    if geom.is_empty:
        return []
    if isinstance(geom, MultiPoint):
        return list(geom.geoms)
    if isinstance(geom, Point):
        return [geom]
    # Manchmal liefert intersection LineString-Segmente; konvertiere Endpunkte
    if isinstance(geom, LineString):
        return [Point(c) for c in geom.coords]
    if isinstance(geom, MultiLineString):
        out = []
        for sub in geom.geoms:
            out.extend(Point(c) for c in sub.coords)
        return out
    return []


def _max_pairwise_distance(points: Iterable[Point]) -> float:
    pts = list(points)
    max_d = 0.0
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            d = math.hypot(pts[i].x - pts[j].x, pts[i].y - pts[j].y)
            if d > max_d:
                max_d = d
    return max_d


def _section_lines_through_polygon(
    geometry: BaseGeometry,
    section_angle: float,
    scan_angle: float,
    spacing: float,
    overhang_percent: float,
    type_prefix: str,
    cross_angle_key: str,
) -> list[dict]:
    """Gemeinsame Mechanik für Quer- und Längsprofile durch ein Polygon."""
    centroid = get_centroid(geometry)
    vertices = get_polygon_vertices(geometry)
    if not vertices:
        return []

    scan_rad = math.radians(scan_angle)
    scan_ax = (math.cos(scan_rad), math.sin(scan_rad))
    projections = [
        (vx - centroid.x) * scan_ax[0] + (vy - centroid.y) * scan_ax[1]
        for vx, vy in vertices
    ]
    min_proj, max_proj = min(projections), max(projections)
    extent = max_proj - min_proj
    num = max(1, int(extent / spacing) + 1)

    boundary = get_polygon_boundary(geometry)
    if boundary is None:
        return []

    section_rad = math.radians(section_angle)
    section_ax = (math.cos(section_rad), math.sin(section_rad))

    info_list = []
    max_width = 0.0
    for i in range(num):
        t = min_proj + i * spacing
        cx = centroid.x + t * scan_ax[0]
        cy = centroid.y + t * scan_ax[1]
        half_test = 2000.0
        test_line = LineString(
            [
                (cx - half_test * section_ax[0], cy - half_test * section_ax[1]),
                (cx + half_test * section_ax[0], cy + half_test * section_ax[1]),
            ]
        )
        if not boundary.intersects(test_line):
            continue
        inter = boundary.intersection(test_line)
        pts = _collect_points(inter)
        if len(pts) < 2:
            continue
        # Find the two furthest intersection points (entry+exit)
        max_d = 0.0
        p1 = p2 = None
        for j in range(len(pts)):
            for k in range(j + 1, len(pts)):
                d = math.hypot(pts[j].x - pts[k].x, pts[j].y - pts[k].y)
                if d > max_d:
                    max_d = d
                    p1, p2 = pts[j], pts[k]
        if not (p1 and p2 and max_d > 0):
            continue
        if max_d > max_width:
            max_width = max_d
        midpoint = Point((p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0)
        info_list.append({"index": i, "center": midpoint, "width": max_d})

    overhang = max_width * (overhang_percent / 100.0)
    half_unified = (max_width / 2.0) + overhang
    total_unified = max_width + 2 * overhang

    results = []
    for info in info_list:
        c = info["center"]
        line = LineString(
            [
                (
                    c.x - half_unified * section_ax[0],
                    c.y - half_unified * section_ax[1],
                ),
                (
                    c.x + half_unified * section_ax[0],
                    c.y + half_unified * section_ax[1],
                ),
            ]
        )
        results.append(
            {
                "geometry": line,
                "type": f"{type_prefix} {info['index']+1:02d}",
                "main_angle": section_angle - 90.0 if type_prefix == "Querschnitt" else section_angle,
                cross_angle_key: section_angle,
                "center_point": c,
                "length": total_unified,
                "width": info["width"],
            }
        )
    return results
