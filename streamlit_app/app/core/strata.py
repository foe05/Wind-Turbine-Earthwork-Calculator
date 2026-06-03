"""Bodenschichten/Strata (1:1-Port aus core/strata_quantities.py)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


class StratumMode(str, Enum):
    CUT = "cut"
    FILL = "fill"


@dataclass(frozen=True)
class StratumLayer:
    name: str
    thickness_m: float
    cost_per_m3: float = 0.0
    co2_kg_per_m3: float = 0.0
    disposal_cost_per_m3: float = 0.0

    def __post_init__(self) -> None:
        if self.thickness_m <= 0:
            raise ValueError(f"thickness must be positive, got {self.thickness_m}")
        for name in ("cost_per_m3", "co2_kg_per_m3", "disposal_cost_per_m3"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass
class StratumQuantity:
    name: str
    depth_m: float
    volume_m3: float
    cost_eur: float
    co2_kg: float


@dataclass
class StrataResult:
    layers: list[StratumQuantity] = field(default_factory=list)
    remainder_m3: float = 0.0
    mode: StratumMode = StratumMode.CUT

    @property
    def total_volume_m3(self) -> float:
        return sum(layer.volume_m3 for layer in self.layers)

    @property
    def total_cost_eur(self) -> float:
        return sum(layer.cost_eur for layer in self.layers)

    @property
    def total_co2_kg(self) -> float:
        return sum(layer.co2_kg for layer in self.layers)


class StrataCalculator:
    def __init__(self, layers: Sequence[StratumLayer]):
        if not layers:
            raise ValueError("at least one layer is required")
        self.layers = list(layers)

    @property
    def total_thickness_m(self) -> float:
        return sum(layer.thickness_m for layer in self.layers)

    def split(
        self, volume_m3: float, area_m2: float, mode: StratumMode = StratumMode.CUT
    ) -> StrataResult:
        if volume_m3 < 0:
            raise ValueError(f"volume_m3 must be non-negative, got {volume_m3}")
        if area_m2 <= 0:
            raise ValueError(f"area_m2 must be positive, got {area_m2}")
        result = StrataResult(mode=mode)
        if volume_m3 == 0:
            return result
        ordered = self.layers if mode == StratumMode.CUT else list(reversed(self.layers))
        target_depth = volume_m3 / area_m2
        remaining = target_depth
        for layer in ordered:
            if remaining <= 0:
                break
            depth = min(layer.thickness_m, remaining)
            vol = depth * area_m2
            unit_cost = (
                layer.cost_per_m3 + layer.disposal_cost_per_m3
                if mode == StratumMode.CUT
                else layer.cost_per_m3
            )
            cost = vol * unit_cost
            co2 = vol * layer.co2_kg_per_m3
            result.layers.append(
                StratumQuantity(name=layer.name, depth_m=depth, volume_m3=vol, cost_eur=cost, co2_kg=co2)
            )
            remaining -= depth
        if remaining > 0:
            result.remainder_m3 = remaining * area_m2
        return result


def default_stack() -> list[StratumLayer]:
    return [
        StratumLayer("Mutterboden", 0.30, 8.0, 3.0, 12.0),
        StratumLayer("Frostschutzschicht", 0.40, 18.0, 4.0, 8.0),
        StratumLayer("Schottertragschicht", 0.30, 28.0, 5.0, 5.0),
    ]
