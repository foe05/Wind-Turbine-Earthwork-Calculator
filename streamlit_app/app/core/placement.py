"""
Placement-Constraints (Port aus core/placement_constraints.py).

Validiert WEA-Standort gegen Mindestabstände (Wohnen, Straßen, Schutzgebiete);
sucht nächstgelegene zulässige Position auf Grid. STRtree-Beschleunigung.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Sequence

from shapely.geometry import Point
from shapely.geometry import base as shapely_base
from shapely.strtree import STRtree


class Severity(str, Enum):
    HARD = "hard"
    SOFT = "soft"


@dataclass(frozen=True)
class ConstraintLayer:
    name: str
    geometries: Sequence[shapely_base.BaseGeometry]
    min_distance_m: float
    severity: Severity = Severity.HARD

    def __post_init__(self) -> None:
        if self.min_distance_m < 0:
            raise ValueError(f"min_distance_m must be non-negative, got {self.min_distance_m}")


@dataclass(frozen=True)
class Violation:
    layer_name: str
    severity: Severity
    actual_distance_m: float
    required_distance_m: float

    @property
    def shortfall_m(self) -> float:
        return max(0.0, self.required_distance_m - self.actual_distance_m)


class PlacementValidator:
    """Prüft Kandidatenpositionen gegen Constraint-Layer."""

    def __init__(self, constraints: Iterable[ConstraintLayer]):
        self.constraints = list(constraints)
        self._trees: list[Optional[STRtree]] = []
        for c in self.constraints:
            self._trees.append(STRtree(list(c.geometries)) if c.geometries else None)

    def check_position(self, x: float, y: float) -> list[Violation]:
        candidate = Point(x, y)
        violations: list[Violation] = []
        for c, tree in zip(self.constraints, self._trees):
            dist = self._nearest_distance(candidate, c, tree)
            if dist < c.min_distance_m:
                violations.append(
                    Violation(
                        layer_name=c.name,
                        severity=c.severity,
                        actual_distance_m=dist,
                        required_distance_m=c.min_distance_m,
                    )
                )
        return violations

    def is_position_valid(
        self, x: float, y: float, allow_soft_violations: bool = True
    ) -> bool:
        for v in self.check_position(x, y):
            if v.severity == Severity.HARD:
                return False
            if not allow_soft_violations and v.severity == Severity.SOFT:
                return False
        return True

    def suggest_nearest_valid(
        self,
        x: float,
        y: float,
        search_radius_m: float = 100.0,
        grid_step_m: float = 5.0,
        allow_soft_violations: bool = True,
    ) -> Optional[tuple[float, float]]:
        if grid_step_m <= 0:
            raise ValueError(f"grid_step_m must be positive, got {grid_step_m}")
        if search_radius_m <= 0:
            raise ValueError(f"search_radius_m must be positive, got {search_radius_m}")

        if self.is_position_valid(x, y, allow_soft_violations=allow_soft_violations):
            return (x, y)

        max_steps = int(math.ceil(search_radius_m / grid_step_m))
        for ring in range(1, max_steps + 1):
            ring_radius = ring * grid_step_m
            if ring_radius > search_radius_m:
                break
            best: Optional[tuple[float, float]] = None
            best_dist_sq = float("inf")
            for cand_x, cand_y in _ring_points(x, y, ring, grid_step_m):
                dx, dy = cand_x - x, cand_y - y
                dist_sq = dx * dx + dy * dy
                if dist_sq > search_radius_m * search_radius_m:
                    continue
                if dist_sq >= best_dist_sq:
                    continue
                if self.is_position_valid(cand_x, cand_y, allow_soft_violations=allow_soft_violations):
                    best = (cand_x, cand_y)
                    best_dist_sq = dist_sq
            if best is not None:
                return best
        return None

    @staticmethod
    def _nearest_distance(
        candidate: Point,
        constraint: ConstraintLayer,
        tree: Optional[STRtree],
    ) -> float:
        if not constraint.geometries:
            return float("inf")
        if tree is None:
            return min(candidate.distance(g) for g in constraint.geometries)
        nearest = tree.nearest(candidate)
        if isinstance(nearest, shapely_base.BaseGeometry):
            geom = nearest
        else:
            geom = constraint.geometries[int(nearest)]
        return candidate.distance(geom)


def _ring_points(
    cx: float, cy: float, ring: int, step: float
) -> Iterable[tuple[float, float]]:
    if ring == 0:
        yield (cx, cy)
        return
    r = ring * step
    for i in range(-ring, ring + 1):
        yield (cx + i * step, cy + r)
        yield (cx + i * step, cy - r)
    for j in range(-ring + 1, ring):
        yield (cx - r, cy + j * step)
        yield (cx + r, cy + j * step)
