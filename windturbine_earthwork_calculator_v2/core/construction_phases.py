"""
Construction Phases (Bauphasen) for Wind Turbine Earthwork Calculator V2

Splits the earthwork into the construction phases of a typical WEA site
(access road → crane pad → foundation → finishing) and projects volume, cost
and CO₂ onto a build timeline. This is the phasing view that Kubla Cubed
exposes as "phase tabs" — a natural fit for the schedule discussion that
follows the earthwork numbers.

The model is intentionally simple: the user supplies phases with a share of
the total cut and fill, plus a start-day and duration, and the planner
distributes the total earthwork accordingly. Shares < 1 are tolerated (an
unassigned remainder is reported separately) so partial plans still work.

QGIS-independent and unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence


@dataclass(frozen=True)
class Phase:
    """One construction phase.

    ``cut_share`` and ``fill_share`` are fractions (0..1) of the total cut /
    fill that fall into this phase. Volume-specific costs are taken from the
    planner's cost config; emission factors from the CO₂ config.
    """

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
            val = getattr(self, name)
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} must be in [0, 1], got {val}")

    @property
    def end_day(self) -> int:
        return self.start_day + self.duration_days


@dataclass
class PhaseQuantity:
    """The earthwork outcome for one phase."""

    name: str
    start_day: int
    end_day: int
    cut_m3: float
    fill_m3: float
    cost_eur: float
    co2_kg: float


@dataclass
class PhasePlan:
    """Full per-phase breakdown plus any unassigned remainder."""

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
    """Distributes total cut/fill across a list of construction phases."""

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

        # Soft check on shares — sum may be < 1 (partial plan) but never > 1.
        total_cut_share = sum(p.cut_share for p in self.phases)
        total_fill_share = sum(p.fill_share for p in self.phases)
        if total_cut_share - 1.0 > 1e-6:
            raise ValueError(f"sum of cut_share must be ≤ 1, got {total_cut_share}")
        if total_fill_share - 1.0 > 1e-6:
            raise ValueError(f"sum of fill_share must be ≤ 1, got {total_fill_share}")

    def plan(self, total_cut_m3: float, total_fill_m3: float) -> PhasePlan:
        """Compute per-phase quantities + the leftover that no phase claimed."""
        if total_cut_m3 < 0 or total_fill_m3 < 0:
            raise ValueError("totals must be non-negative")

        result = PhasePlan()
        assigned_cut = 0.0
        assigned_fill = 0.0
        max_end = 0

        for phase in self.phases:
            cut = total_cut_m3 * phase.cut_share
            fill = total_fill_m3 * phase.fill_share
            cost = cut * self.cut_cost_per_m3 + fill * self.fill_cost_per_m3
            co2 = (cut + fill) * self.co2_per_m3_moved
            result.phases.append(PhaseQuantity(
                name=phase.name,
                start_day=phase.start_day,
                end_day=phase.end_day,
                cut_m3=cut,
                fill_m3=fill,
                cost_eur=cost,
                co2_kg=co2,
            ))
            assigned_cut += cut
            assigned_fill += fill
            max_end = max(max_end, phase.end_day)

        result.unassigned_cut_m3 = max(0.0, total_cut_m3 - assigned_cut)
        result.unassigned_fill_m3 = max(0.0, total_fill_m3 - assigned_fill)
        result.total_duration_days = max_end
        return result


# ---------------------------------------------------------------------------
# Default phases for a typical DACH WEA site
# ---------------------------------------------------------------------------


def default_phases() -> list[Phase]:
    """A reasonable starting plan for a single-turbine site (19 build days).

    Phase 1 — Wegebau (access road): 5 d, 20 % cut / 30 % fill.
    Phase 2 — Kranstellflächen-Bau: 7 d, 50 % / 40 %.
    Phase 3 — Fundamentbau: 4 d, 20 % / 20 %.
    Phase 4 — Restarbeiten: 3 d, 10 % / 10 %.
    """
    return [
        Phase("Wegebau",            start_day=0,  duration_days=5,
              cut_share=0.20, fill_share=0.30),
        Phase("Kranstellflächen-Bau", start_day=5,  duration_days=7,
              cut_share=0.50, fill_share=0.40),
        Phase("Fundamentbau",       start_day=12, duration_days=4,
              cut_share=0.20, fill_share=0.20),
        Phase("Restarbeiten",       start_day=16, duration_days=3,
              cut_share=0.10, fill_share=0.10),
    ]
