"""
Mass-Haul-Diagramm (1:1-Port aus core/mass_haul.py).

Kumulative Abtrag/Auftrag-Ordinate über Stationierung, Massenausgleichspunkte,
Trapez-Integral des |Ordinate| (Haul), Free-Haul/Overhaul-Split.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class MassHaulStation:
    station_m: float
    cut_m3: float = 0.0
    fill_m3: float = 0.0

    def __post_init__(self) -> None:
        if self.cut_m3 < 0 or self.fill_m3 < 0:
            raise ValueError(f"cut/fill must be non-negative at station {self.station_m}")


@dataclass(frozen=True)
class BalancePoint:
    station_m: float
    reference_ordinate_m3: float


@dataclass
class MassHaulResult:
    stations_m: list[float] = field(default_factory=list)
    ordinates_m3: list[float] = field(default_factory=list)
    balance_points: list[BalancePoint] = field(default_factory=list)
    total_cut_m3: float = 0.0
    total_fill_m3: float = 0.0
    net_m3: float = 0.0
    max_ordinate_m3: float = 0.0
    min_ordinate_m3: float = 0.0
    total_haul_m3km: float = 0.0
    free_haul_m3km: float = 0.0
    overhaul_m3km: float = 0.0


class MassHaulDiagram:
    def __init__(self, stations: Sequence[MassHaulStation], compaction_factor: float = 0.85):
        if not (0.0 < compaction_factor <= 1.0):
            raise ValueError(f"compaction_factor must be in (0, 1], got {compaction_factor}")
        self.stations = sorted(stations, key=lambda s: s.station_m)
        self.compaction_factor = compaction_factor

    def compute(self, free_haul_distance_m: float = 0.0) -> MassHaulResult:
        result = MassHaulResult()
        if not self.stations:
            return result

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
        result.balance_points = self._zero_crossings(result.stations_m, result.ordinates_m3)

        total_haul_m3m = self._abs_area(result.stations_m, result.ordinates_m3)
        result.total_haul_m3km = total_haul_m3m / 1000.0

        free_m3m, over_m3m = self._split_free_overhaul(
            result.stations_m, result.ordinates_m3, free_haul_distance_m
        )
        result.free_haul_m3km = free_m3m / 1000.0
        result.overhaul_m3km = over_m3m / 1000.0
        return result

    @staticmethod
    def _zero_crossings(stations: list[float], ordinates: list[float]) -> list[BalancePoint]:
        points: list[BalancePoint] = []
        for i in range(len(ordinates) - 1):
            y0, y1 = ordinates[i], ordinates[i + 1]
            x0, x1 = stations[i], stations[i + 1]
            if y0 == 0.0:
                points.append(BalancePoint(x0, 0.0))
            if (y0 < 0.0 < y1) or (y1 < 0.0 < y0):
                t = y0 / (y0 - y1)
                points.append(BalancePoint(x0 + t * (x1 - x0), 0.0))
        if ordinates and ordinates[-1] == 0.0:
            points.append(BalancePoint(stations[-1], 0.0))
        return points

    @staticmethod
    def _abs_area(stations: list[float], ordinates: list[float]) -> float:
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
                t = y0 / (y0 - y1)
                xz = dx * t
                area += abs(y0) / 2.0 * xz
                area += abs(y1) / 2.0 * (dx - xz)
        return area

    @staticmethod
    def _split_free_overhaul(
        stations: list[float], ordinates: list[float], free_haul_distance_m: float
    ) -> tuple[float, float]:
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
