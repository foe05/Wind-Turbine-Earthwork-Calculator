"""
Crane-pad Rotation Optimisation for Wind Turbine Earthwork Calculator V2

Competing tools (Wind Farm Optimizer, windfarmbop) optimise not only the
platform *height* but also its *orientation*: rotating the crane pad around its
centroid can dramatically reduce cut/fill on sloped terrain by aligning the pad
with the contour lines. This module adds that orientation sweep.

It is deliberately QGIS-independent: the geometry (centroid, rotation) is plain
trigonometry on (x, y) tuples, and the expensive per-angle cut/fill evaluation
is injected as a callback. The QGIS/DEM-aware caller supplies a function that
rotates the real QgsGeometry, samples the DEM and returns a comparable metric;
this module just drives the sweep and picks the best angle. That keeps the
search logic unit-testable without QGIS.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence


Point = tuple[float, float]


@dataclass(frozen=True)
class RotationCandidate:
    """Result of evaluating one orientation."""

    angle_deg: float
    metric: float          # lower is better (e.g. total volume moved)
    payload: Any = None    # optional caller object (e.g. a calculation result)


def polygon_centroid(points: Sequence[Point]) -> Point:
    """Area centroid of a simple polygon (shoelace). Falls back to the vertex
    mean for degenerate (zero-area) inputs. A trailing duplicate of the first
    point is tolerated.
    """
    pts = list(points)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    n = len(pts)
    if n == 0:
        raise ValueError("no points")
    if n < 3:
        # Line/point: mean of vertices.
        return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)

    a2 = 0.0  # twice the signed area
    cx = 0.0
    cy = 0.0
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        a2 += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if a2 == 0.0:
        return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)
    return (cx / (3.0 * a2), cy / (3.0 * a2))


def rotate_points(points: Sequence[Point], angle_deg: float,
                  pivot: Optional[Point] = None) -> list[Point]:
    """Rotate (x, y) points by ``angle_deg`` (counter-clockwise) around ``pivot``.

    ``pivot`` defaults to the polygon centroid, so the footprint rotates in
    place. The original point order (incl. any closing duplicate) is preserved.
    """
    if pivot is None:
        pivot = polygon_centroid(points)
    px, py = pivot
    theta = math.radians(angle_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    out: list[Point] = []
    for x, y in points:
        dx = x - px
        dy = y - py
        rx = px + dx * cos_t - dy * sin_t
        ry = py + dx * sin_t + dy * cos_t
        out.append((rx, ry))
    return out


def default_angles(step_deg: float = 15.0, max_deg: float = 180.0) -> list[float]:
    """Candidate angles 0, step, 2·step, … strictly below ``max_deg``.

    Default 0–180° in 15° steps. 180° suffices for the typical rectangular pad
    (point symmetry); raise ``max_deg`` to 360 for asymmetric footprints.
    """
    if step_deg <= 0:
        raise ValueError(f"step_deg must be positive, got {step_deg}")
    if max_deg <= 0:
        raise ValueError(f"max_deg must be positive, got {max_deg}")
    angles = []
    a = 0.0
    while a < max_deg - 1e-9:
        angles.append(round(a, 6))
        a += step_deg
    return angles


class RotationOptimizer:
    """Sweeps candidate orientations and returns the best-scoring one.

    Usage (QGIS-aware caller injects the evaluation)::

        def evaluate(rotated_xy):
            geom = qgs_polygon_from(rotated_xy)
            result = calculator.calculate_for_geometry(geom)
            return result.total_volume_moved, result

        best = RotationOptimizer().optimize(pad_xy, evaluate)
        # best.angle_deg, best.metric, best.payload
    """

    def __init__(self, angles_deg: Optional[Sequence[float]] = None):
        self.angles_deg = list(angles_deg) if angles_deg is not None else default_angles()
        if not self.angles_deg:
            raise ValueError("angles_deg must not be empty")

    def optimize(
        self,
        points: Sequence[Point],
        evaluate: Callable[[list[Point]], tuple[float, Any]],
        pivot: Optional[Point] = None,
    ) -> RotationCandidate:
        """Rotate ``points`` by each candidate angle, score via ``evaluate``,
        return the lowest-metric candidate.

        ``evaluate(rotated_points)`` must return ``(metric, payload)`` where a
        lower metric is better. Angles whose evaluation raises are skipped
        (logged by the caller if desired); if every angle fails, ValueError.
        """
        if pivot is None:
            pivot = polygon_centroid(points)

        best: Optional[RotationCandidate] = None
        for angle in self.angles_deg:
            rotated = rotate_points(points, angle, pivot)
            try:
                metric, payload = evaluate(rotated)
            except Exception:
                continue
            cand = RotationCandidate(angle_deg=angle, metric=float(metric), payload=payload)
            if best is None or cand.metric < best.metric:
                best = cand
        if best is None:
            raise ValueError("no orientation could be evaluated")
        return best
