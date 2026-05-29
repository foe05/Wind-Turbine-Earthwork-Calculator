"""
Mass-Haul Diagram for Wind Turbine Earthwork Calculator V2

A mass-haul diagram is the classic civil-engineering tool for optimising
earth movement along a linear alignment (here: a wind-farm access road or a
chain of platforms). It plots the *cumulative* earthwork ordinate — cut adds,
fill subtracts — against stationing. From that curve you read:

  - balance points (where the curve returns to a reference level → cut and
    fill balance between two stations, so no net import/export there),
  - the haul (volume × distance moved), split into free-haul (cheap, within a
    contractual free-haul distance) and overhaul (the expensive remainder),
  - the dominant direction of material movement.

Fill volumes are scaled by a compaction factor: 1 m³ of in-situ cut does not
fill 1 m³ of embankment because the placed material is compacted. The default
follows the project convention (swell 1.25 loose, compaction 0.85 placed) →
to fill 1 m³ of compacted embankment you need 1 / 0.85 ≈ 1.176 m³ of bank cut.

This module is QGIS-independent and unit-testable in plain Python.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence


@dataclass(frozen=True)
class MassHaulStation:
    """Earthwork balance over one segment, located at a stationing value (m)."""

    station_m: float
    cut_m3: float = 0.0
    fill_m3: float = 0.0

    def __post_init__(self) -> None:
        if self.cut_m3 < 0 or self.fill_m3 < 0:
            raise ValueError(
                f"cut/fill must be non-negative at station {self.station_m}"
            )


@dataclass(frozen=True)
class BalancePoint:
    """An interpolated station where the mass-haul ordinate equals a reference."""

    station_m: float
    reference_ordinate_m3: float


@dataclass
class MassHaulResult:
    """Computed mass-haul curve and derived quantities."""

    stations_m: list[float] = field(default_factory=list)
    ordinates_m3: list[float] = field(default_factory=list)  # cumulative, swell-adjusted
    balance_points: list[BalancePoint] = field(default_factory=list)
    total_cut_m3: float = 0.0
    total_fill_m3: float = 0.0
    # net = total_cut - adjusted_total_fill; >0 surplus (export), <0 deficit (import)
    net_m3: float = 0.0
    max_ordinate_m3: float = 0.0
    min_ordinate_m3: float = 0.0
    total_haul_m3km: float = 0.0       # ∫ |ordinate| ds, in m³·km
    free_haul_m3km: float = 0.0
    overhaul_m3km: float = 0.0


class MassHaulDiagram:
    """Builds a mass-haul curve from stationed cut/fill data.

    Args:
        stations: ordered (by station) sequence of MassHaulStation. Order is
            enforced (sorted) defensively.
        compaction_factor: placed/compacted fraction (0 < f <= 1). Fill volumes
            are divided by this to express the in-situ cut needed to produce
            them, so cut and fill are compared on the same bank-volume basis.
    """

    def __init__(self, stations: Sequence[MassHaulStation],
                 compaction_factor: float = 0.85):
        if not (0.0 < compaction_factor <= 1.0):
            raise ValueError(
                f"compaction_factor must be in (0, 1], got {compaction_factor}"
            )
        self.stations = sorted(stations, key=lambda s: s.station_m)
        self.compaction_factor = compaction_factor

    def compute(self, free_haul_distance_m: float = 0.0) -> MassHaulResult:
        """Compute the cumulative curve, balance points and haul figures.

        Args:
            free_haul_distance_m: contractual free-haul distance. Haul within
                this distance is "free"; beyond it is "overhaul". 0 puts all
                haul into overhaul.
        """
        result = MassHaulResult()
        if not self.stations:
            return result

        # Cumulative ordinate: cut adds, compaction-adjusted fill subtracts.
        cumulative = 0.0
        for s in self.stations:
            adjusted_fill = s.fill_m3 / self.compaction_factor
            cumulative += s.cut_m3 - adjusted_fill
            result.stations_m.append(s.station_m)
            result.ordinates_m3.append(cumulative)
            result.total_cut_m3 += s.cut_m3
            result.total_fill_m3 += s.fill_m3

        result.net_m3 = cumulative
        result.max_ordinate_m3 = max(result.ordinates_m3)
        result.min_ordinate_m3 = min(result.ordinates_m3)

        # Balance points: zero crossings of the ordinate (reference = 0),
        # linearly interpolated between adjacent stations.
        result.balance_points = self._zero_crossings(
            result.stations_m, result.ordinates_m3
        )

        # Haul = ∫ |ordinate| ds (trapezoidal), reported in m³·km.
        total_haul_m3m = self._abs_area(result.stations_m, result.ordinates_m3)
        result.total_haul_m3km = total_haul_m3m / 1000.0

        # Free-haul vs overhaul split: the portion of the integrated haul whose
        # transport distance is within the free-haul distance is "free". We
        # approximate per-segment haul distance by the local stationing step.
        free_m3m, over_m3m = self._split_free_overhaul(
            result.stations_m, result.ordinates_m3, free_haul_distance_m
        )
        result.free_haul_m3km = free_m3m / 1000.0
        result.overhaul_m3km = over_m3m / 1000.0

        return result

    # ------- internals ------------------------------------------------------

    @staticmethod
    def _zero_crossings(stations: list[float], ordinates: list[float]) -> list[BalancePoint]:
        points: list[BalancePoint] = []
        for i in range(len(ordinates) - 1):
            y0, y1 = ordinates[i], ordinates[i + 1]
            x0, x1 = stations[i], stations[i + 1]
            if y0 == 0.0:
                points.append(BalancePoint(x0, 0.0))
            # Strict sign change between the two ordinates → one crossing.
            if (y0 < 0.0 < y1) or (y1 < 0.0 < y0):
                t = y0 / (y0 - y1)  # fraction along the segment where y=0
                points.append(BalancePoint(x0 + t * (x1 - x0), 0.0))
        # The very last ordinate being exactly zero is also a balance point.
        if ordinates and ordinates[-1] == 0.0:
            points.append(BalancePoint(stations[-1], 0.0))
        return points

    @staticmethod
    def _abs_area(stations: list[float], ordinates: list[float]) -> float:
        """Trapezoidal ∫ |ordinate| ds. Handles sign changes within a segment."""
        area = 0.0
        for i in range(len(ordinates) - 1):
            x0, x1 = stations[i], stations[i + 1]
            y0, y1 = ordinates[i], ordinates[i + 1]
            dx = x1 - x0
            if dx <= 0:
                continue
            if (y0 >= 0 and y1 >= 0) or (y0 <= 0 and y1 <= 0):
                area += abs(y0 + y1) / 2.0 * dx
            else:
                # Sign change: split at the zero crossing into two triangles.
                t = y0 / (y0 - y1)
                xz = dx * t
                area += abs(y0) / 2.0 * xz
                area += abs(y1) / 2.0 * (dx - xz)
        return area

    @staticmethod
    def _split_free_overhaul(stations: list[float], ordinates: list[float],
                             free_haul_distance_m: float) -> tuple[float, float]:
        """Split the |ordinate| haul integral into free-haul and overhaul parts.

        Per segment the local span (station step) is compared against the
        free-haul distance: the share of the segment haul up to the free-haul
        distance is free, the rest is overhaul. This is an approximation of the
        textbook free-haul/overhaul split that needs no per-volume tracing.
        """
        free = 0.0
        over = 0.0
        for i in range(len(ordinates) - 1):
            x0, x1 = stations[i], stations[i + 1]
            y0, y1 = ordinates[i], ordinates[i + 1]
            dx = x1 - x0
            if dx <= 0:
                continue
            seg_haul = abs(y0 + y1) / 2.0 * dx
            if free_haul_distance_m <= 0:
                over += seg_haul
            elif dx <= free_haul_distance_m:
                free += seg_haul
            else:
                free_share = free_haul_distance_m / dx
                free += seg_haul * free_share
                over += seg_haul * (1.0 - free_share)
        return free, over
