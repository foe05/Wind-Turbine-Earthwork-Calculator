"""
Strata Quantities (Bodenschichten) for Wind Turbine Earthwork Calculator V2

Splits a cut or fill volume across a stack of construction soil layers
(Mutterboden / Frostschutz / Schottertragschicht / …) so the report can show
cost, CO₂ and disposal per layer instead of a single aggregate number. This
is a standard takeoff in tools like InSite Elevation Pro, EarthWorks STG and
Carlson Takeoff; the WEA workflow exposes it as a structural addition over
the existing total cut/fill.

The model is volumetric and uniform per layer: each layer has a thickness and
the layers are peeled top-down. A cut of depth d removes layers in order from
the top until d is consumed. A fill of depth d builds layers from the bottom
up (in reverse order). Both modes share the same peeling logic.

QGIS-independent and unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence


class StratumMode(str, Enum):
    """Which direction the layers are consumed."""

    CUT = "cut"    # peel from the top (topsoil first)
    FILL = "fill"  # build from the bottom (base course first)


@dataclass(frozen=True)
class StratumLayer:
    """One construction soil layer with cost and emission characteristics.

    ``thickness_m`` is the per-layer depth. The full stack is interpreted top
    (index 0) to bottom (last). ``disposal_cost_per_m3`` applies to cut volumes
    that must be hauled off-site; for fill it is ignored.
    """

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
    """Per-layer outcome of a takeoff split."""

    name: str
    depth_m: float          # actual depth consumed (≤ layer thickness)
    volume_m3: float
    cost_eur: float
    co2_kg: float


@dataclass
class StrataResult:
    """The full breakdown plus any unattributed remainder."""

    layers: list[StratumQuantity] = field(default_factory=list)
    remainder_m3: float = 0.0  # volume that would not fit in the stack
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
    """Splits cut/fill across a fixed layer stack.

    Args:
        layers: ordered top→bottom. Pass the same stack for both cut and fill —
            the calculator applies it in reverse for fill so the base course is
            built first.
    """

    def __init__(self, layers: Sequence[StratumLayer]):
        if not layers:
            raise ValueError("at least one layer is required")
        self.layers = list(layers)

    @property
    def total_thickness_m(self) -> float:
        return sum(layer.thickness_m for layer in self.layers)

    def split(self, volume_m3: float, area_m2: float,
              mode: StratumMode = StratumMode.CUT) -> StrataResult:
        """Distribute ``volume_m3`` across the layer stack for ``area_m2``.

        Volume is converted to a uniform depth (``volume / area``) and peeled
        layer by layer. For ``CUT`` the topmost layers go first (topsoil,
        then frost protection, then base course). For ``FILL`` the order is
        reversed so the base course is built first.

        Returns a ``StrataResult`` with per-layer entries (in the chosen
        direction) and any remainder that did not fit. A non-zero remainder
        means the cut or fill is deeper than the configured stack.
        """
        if volume_m3 < 0:
            raise ValueError(f"volume_m3 must be non-negative, got {volume_m3}")
        if area_m2 <= 0:
            raise ValueError(f"area_m2 must be positive, got {area_m2}")

        result = StrataResult(mode=mode)
        if volume_m3 == 0:
            return result

        ordered = self.layers if mode == StratumMode.CUT else list(reversed(self.layers))

        target_depth = volume_m3 / area_m2
        remaining_depth = target_depth

        for layer in ordered:
            if remaining_depth <= 0:
                break
            depth = min(layer.thickness_m, remaining_depth)
            volume = depth * area_m2
            unit_cost = (
                layer.cost_per_m3 + layer.disposal_cost_per_m3
                if mode == StratumMode.CUT
                else layer.cost_per_m3
            )
            cost = volume * unit_cost
            co2 = volume * layer.co2_kg_per_m3
            result.layers.append(StratumQuantity(
                name=layer.name, depth_m=depth,
                volume_m3=volume, cost_eur=cost, co2_kg=co2,
            ))
            remaining_depth -= depth

        if remaining_depth > 0:
            result.remainder_m3 = remaining_depth * area_m2

        return result


# ---------------------------------------------------------------------------
# Sensible defaults for a German WEA construction site
# ---------------------------------------------------------------------------


def default_stack() -> list[StratumLayer]:
    """Order-of-magnitude defaults for a standard DACH WEA site.

    Adjust per project; these are documented baselines, not EPD-grade numbers.
    """
    return [
        StratumLayer(
            name="Mutterboden",
            thickness_m=0.30, cost_per_m3=8.0,
            disposal_cost_per_m3=12.0, co2_kg_per_m3=3.0,
        ),
        StratumLayer(
            name="Frostschutzschicht",
            thickness_m=0.40, cost_per_m3=18.0,
            disposal_cost_per_m3=8.0, co2_kg_per_m3=4.0,
        ),
        StratumLayer(
            name="Schottertragschicht",
            thickness_m=0.30, cost_per_m3=28.0,
            disposal_cost_per_m3=5.0, co2_kg_per_m3=5.0,
        ),
    ]
