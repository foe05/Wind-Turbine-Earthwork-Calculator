"""
Placement Constraint Validation for Wind Turbine Earthwork Calculator V2

Validates whether a candidate WEA position respects minimum-distance constraints
to obstacles like buildings, roads, or protected areas, and suggests the nearest
valid alternative when a candidate position violates a hard constraint.

The core math is QGIS-independent and operates on Shapely geometries, so it can
be unit-tested without spinning up QGIS. A thin adapter for QgsVectorLayer →
Shapely is provided at the bottom of this module behind an optional import.

See `docs/plans/V3_ROADMAP.md` Section #1 for the full design context.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Literal, Optional, Sequence

try:
    from shapely.geometry import Point, base as shapely_base
    from shapely.strtree import STRtree
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    """How strictly a constraint must be respected."""

    HARD = "hard"  # Violation blocks placement entirely
    SOFT = "soft"  # Violation is reported as a warning only


@dataclass(frozen=True)
class ConstraintLayer:
    """A named layer of obstacle geometries with a minimum-distance buffer.

    `geometries` is a list of Shapely geometries (Polygon, LineString, or Point)
    in the same CRS as the candidate position. `min_distance_m` is the required
    clearance between the candidate point and the nearest geometry edge.
    """

    name: str
    geometries: Sequence["shapely_base.BaseGeometry"]
    min_distance_m: float
    severity: Severity = Severity.HARD

    def __post_init__(self) -> None:
        if self.min_distance_m < 0:
            raise ValueError(
                f"min_distance_m must be non-negative, got {self.min_distance_m}"
            )


@dataclass(frozen=True)
class Violation:
    """A single constraint violation for a candidate position."""

    layer_name: str
    severity: Severity
    actual_distance_m: float
    required_distance_m: float

    @property
    def shortfall_m(self) -> float:
        """How many meters short of the requirement (>= 0)."""
        return max(0.0, self.required_distance_m - self.actual_distance_m)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class PlacementValidator:
    """Checks candidate WEA positions against a list of constraint layers.

    Typical usage:

        validator = PlacementValidator([
            ConstraintLayer("Wohnbebauung", buildings, min_distance_m=600.0),
            ConstraintLayer("Strassen", roads, min_distance_m=50.0, severity=Severity.SOFT),
        ])
        violations = validator.check_position(x=492000.0, y=5702000.0)
        if any(v.severity == Severity.HARD for v in violations):
            ...
    """

    def __init__(self, constraints: Iterable[ConstraintLayer]):
        if not SHAPELY_AVAILABLE:
            raise ImportError(
                "shapely is required for PlacementValidator. "
                "Install via QGIS' OSGeo4W Shell or `pip install shapely`."
            )
        self.constraints = list(constraints)
        # Pre-build STRtree per layer for O(log n) nearest-neighbour lookups
        # on large constraint layers (OSM buildings can have 100k+ items).
        self._trees: list[Optional[STRtree]] = []
        for c in self.constraints:
            if c.geometries:
                self._trees.append(STRtree(list(c.geometries)))
            else:
                self._trees.append(None)

    # ------- core checks ----------------------------------------------------

    def check_position(self, x: float, y: float) -> list[Violation]:
        """Return all violations (hard + soft) for the candidate (x, y)."""
        candidate = Point(x, y)
        violations: list[Violation] = []
        for constraint, tree in zip(self.constraints, self._trees):
            distance = self._nearest_distance(candidate, constraint, tree)
            if distance < constraint.min_distance_m:
                violations.append(Violation(
                    layer_name=constraint.name,
                    severity=constraint.severity,
                    actual_distance_m=distance,
                    required_distance_m=constraint.min_distance_m,
                ))
        return violations

    def is_position_valid(self, x: float, y: float,
                          allow_soft_violations: bool = True) -> bool:
        """True iff there is no hard violation (and no soft one when ``allow_soft_violations=False``)."""
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
        """Search a regular grid around (x, y) for the closest constraint-respecting position.

        Returns ``None`` if no valid position is found within ``search_radius_m``.
        Step size and radius should be chosen to balance speed vs. resolution;
        defaults of 5 m / 100 m give a 41×41 = 1681-point sweep, which is
        sub-second for typical constraint layers.
        """
        if grid_step_m <= 0:
            raise ValueError(f"grid_step_m must be positive, got {grid_step_m}")
        if search_radius_m <= 0:
            raise ValueError(f"search_radius_m must be positive, got {search_radius_m}")

        # Early exit: the candidate itself may already be valid
        if self.is_position_valid(x, y, allow_soft_violations=allow_soft_violations):
            return (x, y)

        # Iterate outward in rings of equal Chebyshev distance so we find the
        # geometrically-nearest valid position first.
        max_steps = int(math.ceil(search_radius_m / grid_step_m))
        best: Optional[tuple[float, float]] = None
        best_dist_sq = float("inf")

        for ring in range(1, max_steps + 1):
            ring_radius = ring * grid_step_m
            if ring_radius > search_radius_m:
                break
            for cand_x, cand_y in _ring_points(x, y, ring, grid_step_m):
                # Skip candidates strictly outside the search disc
                dx, dy = cand_x - x, cand_y - y
                dist_sq = dx * dx + dy * dy
                if dist_sq > search_radius_m * search_radius_m:
                    continue
                if dist_sq >= best_dist_sq:
                    # Cannot improve on current best — skip to save constraint checks
                    continue
                if self.is_position_valid(cand_x, cand_y,
                                          allow_soft_violations=allow_soft_violations):
                    best = (cand_x, cand_y)
                    best_dist_sq = dist_sq
            # If anything was found in this ring, no need to check further rings —
            # they're guaranteed to be farther.
            if best is not None:
                return best

        return None

    # ------- internals ------------------------------------------------------

    @staticmethod
    def _nearest_distance(
        candidate: "Point",
        constraint: ConstraintLayer,
        tree: Optional["STRtree"],
    ) -> float:
        """Distance to the nearest geometry in the layer (or +inf if layer empty)."""
        if not constraint.geometries:
            return float("inf")
        if tree is None:
            # Fallback: linear scan
            return min(candidate.distance(g) for g in constraint.geometries)
        nearest = tree.nearest(candidate)
        # shapely 2.x STRtree.nearest returns an array index (numpy int64);
        # shapely 1.x returned the geometry itself.
        if isinstance(nearest, shapely_base.BaseGeometry):
            geom = nearest
        else:
            # numpy.int64 / int / ndarray-with-one-element all support __index__
            geom = constraint.geometries[int(nearest)]
        return candidate.distance(geom)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ring_points(cx: float, cy: float, ring: int, step: float) -> Iterable[tuple[float, float]]:
    """Yield the (x, y) points on the Chebyshev-distance-`ring` ring of a square grid.

    Ring 0 = (cx, cy) only. Ring 1 = the 8 neighbours. Ring N = the 8N points
    forming the square at Chebyshev distance N.
    """
    if ring == 0:
        yield (cx, cy)
        return
    r = ring * step
    # Top and bottom edges (including corners)
    for i in range(-ring, ring + 1):
        yield (cx + i * step, cy + r)
        yield (cx + i * step, cy - r)
    # Left and right edges (excluding corners — already yielded above)
    for j in range(-ring + 1, ring):
        yield (cx - r, cy + j * step)
        yield (cx + r, cy + j * step)


# ---------------------------------------------------------------------------
# Optional QGIS adapter
# ---------------------------------------------------------------------------


def constraint_from_qgis_layer(
    name: str,
    layer: "object",  # QgsVectorLayer; typed as object to avoid QGIS import at module load
    min_distance_m: float,
    severity: Severity = Severity.HARD,
    feature_filter: Optional[str] = None,
) -> ConstraintLayer:
    """Adapter: read all features from a `QgsVectorLayer` and build a `ConstraintLayer`.

    `feature_filter` is an optional QGIS expression that limits which features are
    used (e.g. ``"category = 'residential'"``).
    """
    try:
        from qgis.core import QgsFeatureRequest
    except ImportError as exc:
        raise ImportError(
            "qgis.core is required for constraint_from_qgis_layer; "
            "use ConstraintLayer directly with shapely geometries instead."
        ) from exc
    if not SHAPELY_AVAILABLE:
        raise ImportError("shapely is required for constraint_from_qgis_layer")
    from shapely import wkt as shapely_wkt

    request = QgsFeatureRequest()
    if feature_filter:
        request.setFilterExpression(feature_filter)

    geoms: list = []
    for feat in layer.getFeatures(request):
        g = feat.geometry()
        if g is None or g.isEmpty():
            continue
        # QgsGeometry → WKT → Shapely; this avoids depending on a QgsGeometry-to-shapely
        # adapter that has changed signature across QGIS versions.
        geoms.append(shapely_wkt.loads(g.asWkt()))

    return ConstraintLayer(
        name=name,
        geometries=geoms,
        min_distance_m=min_distance_m,
        severity=severity,
    )
