"""Bauphasen (1:1-Port aus core/construction_phases.py)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class Phase:
    name: str
    start_day: int
    duration_days: int
    cut_share: float = 0.0
    fill_share: float = 0.0

    def __post_init__(self) -> None:
        if self.duration_days <= 0:
            raise ValueError(f"duration_days must be positive, got {self.duration_days}")
        if self.start_day < 0:
            raise ValueError(f"start_day must be non-negative, got {self.start_day}")
        for name in ("cut_share", "fill_share"):
            v = getattr(self, name)
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"{name} must be in [0, 1], got {v}")

    @property
    def end_day(self) -> int:
        return self.start_day + self.duration_days


@dataclass
class PhaseQuantity:
    name: str
    start_day: int
    end_day: int
    cut_m3: float
    fill_m3: float
    cost_eur: float
    co2_kg: float


@dataclass
class PhasePlan:
    phases: list[PhaseQuantity] = field(default_factory=list)
    unassigned_cut_m3: float = 0.0
    unassigned_fill_m3: float = 0.0
    total_duration_days: int = 0

    @property
    def total_cost_eur(self) -> float:
        return sum(p.cost_eur for p in self.phases)

    @property
    def total_co2_kg(self) -> float:
        return sum(p.co2_kg for p in self.phases)


class PhasePlanner:
    def __init__(
        self,
        phases: Sequence[Phase],
        cut_cost_per_m3: float = 8.0,
        fill_cost_per_m3: float = 12.0,
        co2_per_m3_moved: float = 2.5,
    ):
        if not phases:
            raise ValueError("at least one phase is required")
        for f in (cut_cost_per_m3, fill_cost_per_m3, co2_per_m3_moved):
            if f < 0:
                raise ValueError("cost/CO₂ factors must be non-negative")
        self.phases = list(phases)
        self.cut_cost_per_m3 = cut_cost_per_m3
        self.fill_cost_per_m3 = fill_cost_per_m3
        self.co2_per_m3_moved = co2_per_m3_moved
        total_cut_share = sum(p.cut_share for p in self.phases)
        total_fill_share = sum(p.fill_share for p in self.phases)
        if total_cut_share - 1.0 > 1e-6:
            raise ValueError(f"sum of cut_share must be ≤ 1, got {total_cut_share}")
        if total_fill_share - 1.0 > 1e-6:
            raise ValueError(f"sum of fill_share must be ≤ 1, got {total_fill_share}")

    def plan(self, total_cut_m3: float, total_fill_m3: float) -> PhasePlan:
        if total_cut_m3 < 0 or total_fill_m3 < 0:
            raise ValueError("totals must be non-negative")
        result = PhasePlan()
        assigned_cut = 0.0
        assigned_fill = 0.0
        max_end = 0
        for ph in self.phases:
            cut = total_cut_m3 * ph.cut_share
            fill = total_fill_m3 * ph.fill_share
            cost = cut * self.cut_cost_per_m3 + fill * self.fill_cost_per_m3
            co2 = (cut + fill) * self.co2_per_m3_moved
            result.phases.append(
                PhaseQuantity(
                    name=ph.name,
                    start_day=ph.start_day,
                    end_day=ph.end_day,
                    cut_m3=cut,
                    fill_m3=fill,
                    cost_eur=cost,
                    co2_kg=co2,
                )
            )
            assigned_cut += cut
            assigned_fill += fill
            max_end = max(max_end, ph.end_day)
        result.unassigned_cut_m3 = max(0.0, total_cut_m3 - assigned_cut)
        result.unassigned_fill_m3 = max(0.0, total_fill_m3 - assigned_fill)
        result.total_duration_days = max_end
        return result


def default_phases() -> list[Phase]:
    return [
        Phase("Wegebau", 0, 5, cut_share=0.20, fill_share=0.30),
        Phase("Kranstellflächen-Bau", 5, 7, cut_share=0.50, fill_share=0.40),
        Phase("Fundamentbau", 12, 4, cut_share=0.20, fill_share=0.20),
        Phase("Restarbeiten", 16, 3, cut_share=0.10, fill_share=0.10),
    ]
