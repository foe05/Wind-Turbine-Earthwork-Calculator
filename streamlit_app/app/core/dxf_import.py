"""
DXF-Import (portiert aus core/dxf_importer.py, QGIS-frei).

Liest LWPOLYLINE/POLYLINE/LINE aus DXF, verbindet zu geschlossenen Polygonen
und liefert shapely.Polygon. CRS-Auto-Detektion über Koordinatenbereich
(WGS84/UTM32/UTM33/Gauss-Krüger 3/4).

Sicherheits-Caps und Magic-Number-Checks aus dem Plugin sind erhalten.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from pathlib import Path
from typing import Optional

import ezdxf
from ezdxf import recover as ezdxf_recover
from shapely.geometry import LineString, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import linemerge, polygonize, unary_union

from .geometry import point_distance
from .validation import ValidationError, validate_polygon_topology

log = logging.getLogger(__name__)

# Schutz gegen Memory-DoS via riesiger DXF-Eingaben
MAX_DXF_SIZE_BYTES = 500 * 1024 * 1024

# Sicherheit/UX
SUPPORTED_ENTITY_TYPES = {"LWPOLYLINE", "POLYLINE", "LINE"}


class DXFImporter:
    """DXF → shapely.Polygon. Erhalten: Recovery-Modus, Size-Cap, Multi-Strategie-Connect."""

    def __init__(self, dxf_path: str | Path, tolerance: float = 0.01, crs_epsg: int = 25832):
        self.dxf_path = Path(dxf_path)
        if not self.dxf_path.exists():
            raise FileNotFoundError(f"DXF-Datei nicht gefunden: {dxf_path}")
        self.tolerance = float(tolerance)
        self.crs_epsg = int(crs_epsg)
        self.doc: Optional[ezdxf.document.Drawing] = None
        self.polylines: list[list[tuple[float, float]]] = []

    # ------------------------------------------------------------------ Load

    def load_dxf(self) -> None:
        """Lädt DXF mit ezdxf.recover; Size-Cap vor Parsen."""
        size = self.dxf_path.stat().st_size
        if size > MAX_DXF_SIZE_BYTES:
            raise ValidationError(
                f"DXF zu groß: {size / 1024 / 1024:.1f} MB > "
                f"{MAX_DXF_SIZE_BYTES / 1024 / 1024:.0f} MB Limit"
            )
        log.info("Lade DXF %s (%.2f MB)", self.dxf_path, size / 1024 / 1024)
        self.doc, auditor = ezdxf_recover.readfile(str(self.dxf_path))
        if auditor.has_errors:
            log.warning("DXF-Audit: %d strukturelle Probleme (recovery)", len(auditor.errors))

    # ----------------------------------------------------------- CRS-Detect

    def detect_coordinate_system(self) -> dict:
        """Heuristisches CRS-Detect aus Koordinatenbereich."""
        if self.doc is None:
            self.load_dxf()
        assert self.doc is not None

        modelspace = self.doc.modelspace()
        all_x: list[float] = []
        all_y: list[float] = []
        for ent in modelspace:
            t = ent.dxftype()
            if t == "LWPOLYLINE":
                for p in ent.get_points("xy"):
                    all_x.append(p[0])
                    all_y.append(p[1])
            elif t == "POLYLINE":
                for v in ent.vertices:
                    all_x.append(v.dxf.location.x)
                    all_y.append(v.dxf.location.y)
            elif t == "LINE":
                all_x.extend([ent.dxf.start.x, ent.dxf.end.x])
                all_y.extend([ent.dxf.start.y, ent.dxf.end.y])

        if not all_x:
            return {
                "detected_epsg": None,
                "confidence": "unknown",
                "coordinate_range": None,
                "suggestions": [],
                "warnings": ["Keine Koordinaten im DXF gefunden"],
            }

        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)
        coord_range = {"x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max}

        suggestions = []
        warnings = []
        detected_epsg = None
        confidence = "unknown"

        # WGS84 (Grad)
        if abs(x_min) < 180 and abs(x_max) < 180 and abs(y_min) < 90 and abs(y_max) < 90:
            suggestions.append({"epsg": 4326, "name": "WGS84", "reason": "Werte im Bereich ±180/±90"})
            warnings.append("WGS84 erkannt — Plugin erwartet projiziertes CRS in Metern.")
            confidence = "high"
        # UTM 32N
        elif 200000 <= x_min and x_max <= 500000 and 5400000 <= y_min and y_max <= 6100000:
            if 300000 <= x_min and x_max <= 400000:
                suggestions.append({"epsg": 25832, "name": "ETRS89 / UTM 32N", "reason": "X in 300k–400k"})
                detected_epsg = 25832
                confidence = "high"
            else:
                suggestions.append({"epsg": 25832, "name": "ETRS89 / UTM 32N", "reason": "X in UTM-32N-Bereich"})
                confidence = "medium"
        # UTM 33N
        elif 300000 <= x_min and x_max <= 600000 and 5400000 <= y_min and y_max <= 6100000:
            if 400000 <= x_min and x_max <= 500000:
                suggestions.append({"epsg": 25833, "name": "ETRS89 / UTM 33N", "reason": "X in 400k–500k"})
                detected_epsg = 25833
                confidence = "high"
            else:
                suggestions.append({"epsg": 25833, "name": "ETRS89 / UTM 33N", "reason": "X in UTM-33N-Bereich"})
                confidence = "medium"
        # Gauss-Krüger 3
        elif 3200000 <= x_min and x_max <= 3900000 and 5400000 <= y_min and y_max <= 6100000:
            suggestions.append({"epsg": 31467, "name": "DHDN / GK Zone 3", "reason": "X in 3.2M–3.9M"})
            warnings.append("Gauss-Krüger erkannt (Legacy) — Umrechnung auf ETRS89/UTM empfohlen.")
            detected_epsg = 31467
            confidence = "high" if 3300000 <= x_min and x_max <= 3700000 else "medium"
        # Gauss-Krüger 4
        elif 4200000 <= x_min and x_max <= 4900000 and 5400000 <= y_min and y_max <= 6100000:
            suggestions.append({"epsg": 31468, "name": "DHDN / GK Zone 4", "reason": "X in 4.2M–4.9M"})
            warnings.append("Gauss-Krüger erkannt (Legacy) — Umrechnung auf ETRS89/UTM empfohlen.")
            detected_epsg = 31468
            confidence = "high" if 4300000 <= x_min and x_max <= 4700000 else "medium"
        else:
            confidence = "low"
            warnings.append(f"CRS nicht eindeutig erkannt — Werte EPSG:{self.crs_epsg} prüfen.")

        return {
            "detected_epsg": detected_epsg,
            "confidence": confidence,
            "coordinate_range": coord_range,
            "suggestions": suggestions,
            "warnings": warnings,
        }

    def validate_coordinate_system(self, expected_epsg: Optional[int] = None) -> tuple[bool, str]:
        """Prüft, ob die DXF-Koordinaten zum erwarteten CRS passen."""
        expected = expected_epsg if expected_epsg is not None else self.crs_epsg
        det = self.detect_coordinate_system()
        rng = det["coordinate_range"]
        if rng is None:
            raise ValueError("DXF enthält keine Koordinaten")
        range_str = (
            f"X=[{rng['x_min']:.2f}, {rng['x_max']:.2f}], "
            f"Y=[{rng['y_min']:.2f}, {rng['y_max']:.2f}]"
        )

        if det["detected_epsg"] == expected and det["confidence"] == "high":
            return True, f"CRS bestätigt: EPSG:{expected} ({range_str})"
        if det["detected_epsg"] and det["detected_epsg"] != expected and det["confidence"] == "high":
            return False, (
                f"CRS-Mismatch: erkannt EPSG:{det['detected_epsg']}, erwartet EPSG:{expected}. "
                f"{range_str}"
            )
        return True, f"CRS unsicher (Konfidenz {det['confidence']}) — angenommen EPSG:{expected}. {range_str}"

    # ----------------------------------------------------- Layer + Entities

    def get_available_layers(self) -> list[str]:
        if self.doc is None:
            self.load_dxf()
        assert self.doc is not None
        layers: list[str] = []
        for ent in self.doc.modelspace():
            ln = ent.dxf.layer
            if ln and ln not in layers:
                layers.append(ln)
        layers.sort()
        return layers

    def validate_layer_exists(self, layer_name: str) -> None:
        layers = self.get_available_layers()
        if layer_name not in layers:
            raise ValidationError(
                f"DXF-Layer '{layer_name}' nicht gefunden. "
                f"Verfügbare Layer: {', '.join(layers) if layers else '(keine)'}"
            )

    def validate_entity_types(self, layer_name: Optional[str] = None) -> dict:
        """Zählt Entity-Typen und warnt vor nicht unterstützten."""
        if self.doc is None:
            self.load_dxf()
        assert self.doc is not None

        counts = {t: 0 for t in ("LWPOLYLINE", "POLYLINE", "LINE", "CIRCLE", "ARC")}
        other: dict[str, int] = {}
        total = 0
        for ent in self.doc.modelspace():
            if layer_name and ent.dxf.layer != layer_name:
                continue
            total += 1
            t = ent.dxftype()
            if t in counts:
                counts[t] += 1
            else:
                other[t] = other.get(t, 0) + 1
        supported = counts["LWPOLYLINE"] + counts["POLYLINE"] + counts["LINE"]

        warnings: list[str] = []
        if supported == 0:
            extras = ", ".join(f"{t}({c})" for t, c in {**counts, **other}.items() if c)
            raise ValidationError(
                f"Keine unterstützten Geometrien (LWPOLYLINE/POLYLINE/LINE) im DXF gefunden. "
                f"Stattdessen: {extras or 'nichts'}."
            )
        if counts["CIRCLE"] + counts["ARC"] > 0:
            warnings.append("CIRCLE/ARC-Entities werden ignoriert — in CAD zu LWPOLYLINE konvertieren.")
        return {
            **counts,
            "other": other,
            "total_entities": total,
            "supported_entities": supported,
            "unsupported_entities": total - supported,
            "warnings": warnings,
            "preferred_type": "LWPOLYLINE",
        }

    def extract_polylines(self, layer_name: Optional[str] = None) -> list[list[tuple[float, float]]]:
        """Sammelt 2D-Koordinaten aus LWPOLYLINE/POLYLINE/LINE."""
        if self.doc is None:
            self.load_dxf()
        assert self.doc is not None
        self.polylines = []
        ms = self.doc.modelspace()

        for ent in ms.query("LWPOLYLINE"):
            if layer_name and ent.dxf.layer != layer_name:
                continue
            coords = [(p[0], p[1]) for p in ent.get_points("xy")]
            if coords:
                self.polylines.append(coords)

        for ent in ms.query("POLYLINE"):
            if layer_name and ent.dxf.layer != layer_name:
                continue
            coords = [(v.dxf.location.x, v.dxf.location.y) for v in ent.vertices]
            if coords:
                self.polylines.append(coords)

        for ent in ms.query("LINE"):
            if layer_name and ent.dxf.layer != layer_name:
                continue
            self.polylines.append([
                (ent.dxf.start.x, ent.dxf.start.y),
                (ent.dxf.end.x, ent.dxf.end.y),
            ])
        log.info("Extrahiert: %d Polylinien/Linien", len(self.polylines))
        return self.polylines

    # --------------------------------------------------- Polygon-Connecting

    def _connect_with_shapely(
        self, polylines: list[list[tuple[float, float]]], gap_tolerance: float = 0.5
    ) -> Optional[list[tuple[float, float]]]:
        """Robuste Verbindung via shapely linemerge/polygonize + Buffer-Trick."""
        lines = [LineString(pl) for pl in polylines if len(pl) >= 2]
        if not lines:
            return None
        merged = linemerge(lines)
        geoms = list(merged.geoms) if hasattr(merged, "geoms") else [merged]

        # Shortcut 1: linemerge hat bereits einen geschlossenen Ring geliefert
        if isinstance(merged, LineString) and merged.is_ring:
            poly = Polygon(merged.coords)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if isinstance(poly, Polygon) and not poly.is_empty:
                return list(poly.exterior.coords)

        # Shortcut 2: direkte Polygonisierung der gemergten Linien
        polys = list(polygonize(geoms))
        if polys:
            largest = max(polys, key=lambda p: p.area)
            if not largest.is_valid:
                largest = largest.buffer(0)
            if isinstance(largest, Polygon) and not largest.is_empty and largest.area > 1.0:
                return list(largest.exterior.coords)

        if gap_tolerance > 0:
            union_geom = unary_union(geoms)
            buffered = union_geom.buffer(gap_tolerance)
            if isinstance(buffered, Polygon) and not buffered.is_empty and buffered.area > 100:
                return list(buffered.exterior.coords)
            cleaned = buffered.buffer(-gap_tolerance)
            if isinstance(cleaned, Polygon) and not cleaned.is_empty:
                return list(cleaned.exterior.coords)
            boundary = cleaned.boundary if hasattr(cleaned, "boundary") else cleaned
            boundary_geoms = list(boundary.geoms) if hasattr(boundary, "geoms") else [boundary]
            polys = list(polygonize(boundary_geoms))
            if not polys:
                return None
            largest = max(polys, key=lambda p: p.area)
            if not largest.is_valid:
                largest = largest.buffer(0)
            if largest.is_empty:
                return None
            return list(largest.exterior.coords)

        cleaned = unary_union(geoms)
        if isinstance(cleaned, Polygon) and not cleaned.is_empty:
            return list(cleaned.exterior.coords)
        return None

    def _build_segment_graph(
        self, polylines: list[list[tuple[float, float]]]
    ) -> dict[tuple[float, float], list[tuple[float, float]]]:
        graph: dict[tuple[float, float], list[tuple[float, float]]] = defaultdict(list)
        for pl in polylines:
            for i in range(len(pl) - 1):
                a = (round(pl[i][0], 3), round(pl[i][1], 3))
                b = (round(pl[i + 1][0], 3), round(pl[i + 1][1], 3))
                if b not in graph[a]:
                    graph[a].append(b)
                if a not in graph[b]:
                    graph[b].append(a)
        return dict(graph)

    def _find_outer_boundary(
        self, graph: dict[tuple[float, float], list[tuple[float, float]]]
    ) -> list[tuple[float, float]]:
        if not graph:
            return []
        start = min(graph.keys(), key=lambda p: (p[0], p[1]))
        boundary = [start]
        current = start
        previous: Optional[tuple[float, float]] = None
        max_iter = len(graph) * 10
        for _ in range(max_iter):
            neighbors = graph.get(current, [])
            if not neighbors:
                break
            candidates = [n for n in neighbors if n != previous] or neighbors
            if not candidates:
                break
            if previous is not None:
                incoming = math.atan2(current[1] - previous[1], current[0] - previous[0])
                best_diff = float("inf")
                next_pt = candidates[0]
                for c in candidates:
                    outgoing = math.atan2(c[1] - current[1], c[0] - current[0])
                    diff = (outgoing - incoming) % (2 * math.pi)
                    if diff < best_diff:
                        best_diff = diff
                        next_pt = c
            else:
                best_angle = -math.pi
                next_pt = candidates[0]
                for c in candidates:
                    a = math.atan2(c[1] - current[1], c[0] - current[0])
                    if a > best_angle:
                        best_angle = a
                        next_pt = c
            if next_pt == start:
                break
            if next_pt in boundary:
                break
            boundary.append(next_pt)
            previous = current
            current = next_pt
        if boundary and boundary[0] != boundary[-1]:
            boundary.append(boundary[0])
        return boundary

    def _connect_sequential(
        self, polylines: list[list[tuple[float, float]]]
    ) -> list[tuple[float, float]]:
        connected = list(polylines[0])
        remaining = [list(pl) for pl in polylines[1:]]
        max_iter = len(remaining) * 2
        for _ in range(max_iter):
            if not remaining:
                break
            start = connected[0]
            end = connected[-1]
            best = (float("inf"), None, False, False)
            for idx, pl in enumerate(remaining):
                pls, ple = pl[0], pl[-1]
                checks = [
                    (point_distance(end, pls), False, False),
                    (point_distance(end, ple), True, False),
                    (point_distance(start, ple), False, True),
                    (point_distance(start, pls), True, True),
                ]
                for d, rev, at_start in checks:
                    if d < best[0] and d <= self.tolerance:
                        best = (d, idx, rev, at_start)
            d, idx, rev, at_start = best
            if idx is None:
                break
            pl = remaining.pop(idx)
            if rev:
                pl = list(reversed(pl))
            if at_start:
                connected = pl[:-1] + connected
            else:
                connected = connected[:-1] + pl
        if point_distance(connected[0], connected[-1]) > self.tolerance:
            connected.append(connected[0])
        return connected

    def connect_polylines(
        self, polylines: Optional[list[list[tuple[float, float]]]] = None
    ) -> list[tuple[float, float]]:
        if polylines is None:
            polylines = self.polylines
        if not polylines:
            raise ValueError("Keine Polylinien zum Verbinden")

        if len(polylines) == 1:
            coords = polylines[0]
            if point_distance(coords[0], coords[-1]) <= self.tolerance:
                return coords
            return coords + [coords[0]]

        for gap in (0.5, 1.0, 2.0, 5.0):
            coords = self._connect_with_shapely(polylines, gap_tolerance=gap)
            if coords and len(coords) >= 4:
                return coords

        graph = self._build_segment_graph(polylines)
        boundary = self._find_outer_boundary(graph)
        if boundary and len(boundary) >= 4:
            return boundary
        return self._connect_sequential(polylines)

    # ---------------------------------------------- Polygon-Erzeugung + API

    def to_polygon(
        self, coords: Optional[list[tuple[float, float]]] = None
    ) -> Polygon:
        if coords is None:
            coords = self.connect_polylines()
        if not coords:
            raise ValueError("Keine Koordinaten zum Konvertieren")
        if point_distance(coords[0], coords[-1]) > 1e-6:
            coords = coords + [coords[0]]
        poly = Polygon(coords)
        if not poly.is_valid:
            poly = poly.buffer(0)
        # Außenring auf counter-clockwise normalisieren (validate_polygon_topology erwartet CCW).
        if isinstance(poly, Polygon):
            poly = orient(poly, sign=1.0)
        return poly

    def import_as_polygon(self, layer_name: Optional[str] = None) -> tuple[Polygon, dict]:
        """Komplett-Workflow: load -> extract -> connect -> validate -> Polygon."""
        polylines = self.extract_polylines(layer_name)
        if not polylines:
            raise ValueError(
                f"Keine Polylinien im DXF (Layer={layer_name or 'alle'})"
            )
        coords = self.connect_polylines(polylines)
        poly = self.to_polygon(coords)
        validate_polygon_topology(poly)
        metadata = {
            "source_file": str(self.dxf_path),
            "num_polylines": len(polylines),
            "num_vertices": len(coords),
            "area": poly.area,
            "perimeter": poly.length,
            "crs_epsg": self.crs_epsg,
            "tolerance": self.tolerance,
        }
        log.info("Polygon importiert: %d Vertices, %.2f m²", metadata["num_vertices"], metadata["area"])
        return poly, metadata

    def import_holms(self, layer_name: Optional[str] = None) -> tuple[list[Polygon], dict]:
        """Mehrere Holm-Polygone als Einzelgeometrien."""
        polylines = self.extract_polylines(layer_name)
        if not polylines:
            raise ValueError("Keine Polylinien im DXF")
        holms: list[Polygon] = []
        failed = 0
        for pl in polylines:
            if len(pl) < 3:
                continue
            if point_distance(pl[0], pl[-1]) > self.tolerance:
                continue
            try:
                poly = Polygon(pl)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                if isinstance(poly, Polygon) and not poly.is_empty and poly.is_valid:
                    holms.append(orient(poly, sign=1.0))
                else:
                    failed += 1
            except Exception:
                failed += 1

        # Fallback: polygonize über alle Linien
        if not holms:
            lines = [LineString(pl) for pl in polylines if len(pl) >= 2]
            for poly in polygonize(lines):
                if poly.is_valid and poly.area > 1.0:
                    holms.append(orient(poly, sign=1.0))

        if not holms:
            raise ValueError(f"Konnte keine Holm-Polygone erzeugen (failed={failed})")

        total = sum(h.area for h in holms)
        return holms, {
            "source_file": str(self.dxf_path),
            "num_holms": len(holms),
            "total_area": total,
            "failed_holms": failed,
            "crs_epsg": self.crs_epsg,
            "tolerance": self.tolerance,
            "individual_areas": [round(h.area, 2) for h in holms],
        }
