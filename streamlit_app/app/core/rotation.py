"""
Rotation-Optimizer (1:1-Port aus core/rotation_optimizer.py).

QGIS-frei: reine Trigonometrie auf (x, y)-Tupeln. Die per-Winkel-Bewertung
wird als Callback injiziert; das Sweep-Driver ist hier.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence

Point = tuple[float, float]


@dataclass(frozen=True)
class RotationCandidate:
    angle_deg: float
    metric: float
    payload: Any = None


def polygon_centroid(points: Sequence[Point]) -> Point:
    pts = list(points)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    n = len(pts)
    if n == 0:
        raise ValueError("no points")
    if n < 3:
        return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)
    a2 = 0.0
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


def rotate_points(
    points: Sequence[Point], angle_deg: float, pivot: Optional[Point] = None
) -> list[Point]:
    if pivot is None:
        pivot = polygon_centroid(points)
    px, py = pivot
    theta = math.radians(angle_deg)
    c = math.cos(theta)
    s = math.sin(theta)
    return [(px + (x - px) * c - (y - py) * s, py + (x - px) * s + (y - py) * c) for x, y in points]


def default_angles(step_deg: float = 15.0, max_deg: float = 180.0) -> list[float]:
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
    """Sweep candidate orientations; lowest-metric wins."""

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
