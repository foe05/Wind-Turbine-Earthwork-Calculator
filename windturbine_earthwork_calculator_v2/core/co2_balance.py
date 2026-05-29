"""
CO₂ Balance for Wind Turbine Earthwork Calculator V2

Estimates the embodied / operational CO₂ of a WEA site's earthworks and
foundation so the optimisation story can include a sustainability metric —
something the commercial earthwork tools (Civil 3D, RoadEng, Kubla) only offer
via separate LCA add-ons (EC3, One Click LCA).

The model is intentionally simple and transparent: every component is
``quantity × emission_factor``. The default factors are order-of-magnitude
values for German construction (diesel plant, ready-mix concrete, reinforcing
steel, truck haulage). They are **estimates** — for reporting against a real
EPD, override `EmissionFactors`.

QGIS-independent and unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EmissionFactors:
    """CO₂ emission factors (kg CO₂e per unit). Defaults are approximate
    German-construction values; override for EPD-grade reporting.
    """

    excavation_kg_per_m3: float = 2.5        # diesel plant: dig + load (per m³ moved)
    haul_kg_per_m3_km: float = 0.12          # truck haulage (per m³ per km)
    gravel_production_kg_per_m3: float = 5.0  # quarrying + processing crushed stone
    concrete_kg_per_m3: float = 280.0        # ready-mix CEM II foundation concrete
    steel_kg_per_kg: float = 1.5             # reinforcing steel (recycled-content rebar)

    def __post_init__(self) -> None:
        for name in ("excavation_kg_per_m3", "haul_kg_per_m3_km",
                     "gravel_production_kg_per_m3", "concrete_kg_per_m3",
                     "steel_kg_per_kg"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass
class CO2Result:
    """CO₂ breakdown in kg CO₂e."""

    excavation_kg: float = 0.0
    haul_kg: float = 0.0
    gravel_kg: float = 0.0
    concrete_kg: float = 0.0
    steel_kg: float = 0.0

    @property
    def total_kg(self) -> float:
        return (self.excavation_kg + self.haul_kg + self.gravel_kg
                + self.concrete_kg + self.steel_kg)

    @property
    def total_t(self) -> float:
        """Total in tonnes CO₂e."""
        return self.total_kg / 1000.0

    def as_breakdown(self) -> dict:
        """Component → kg, plus total, for report tables."""
        return {
            "excavation_kg": round(self.excavation_kg, 1),
            "haul_kg": round(self.haul_kg, 1),
            "gravel_kg": round(self.gravel_kg, 1),
            "concrete_kg": round(self.concrete_kg, 1),
            "steel_kg": round(self.steel_kg, 1),
            "total_kg": round(self.total_kg, 1),
            "total_t": round(self.total_t, 3),
        }


class CO2Calculator:
    """Computes the CO₂ balance from earthwork + structural quantities."""

    def __init__(self, factors: EmissionFactors = None):
        self.factors = factors or EmissionFactors()

    def compute(
        self,
        cut_m3: float = 0.0,
        fill_m3: float = 0.0,
        gravel_m3: float = 0.0,
        haul_distance_km: float = 0.0,
        concrete_m3: float = 0.0,
        steel_kg: float = 0.0,
    ) -> CO2Result:
        """Estimate CO₂e for one site.

        Args:
            cut_m3: total excavated volume (drives excavation emissions).
            fill_m3: total placed fill (also handled by plant → excavation factor).
            gravel_m3: external crushed-stone volume (production emissions).
            haul_distance_km: average one-way haul distance for moved material
                (cut + gravel are assumed to be transported this far).
            concrete_m3: foundation concrete volume.
            steel_kg: reinforcing steel mass.
        """
        for name, val in (("cut_m3", cut_m3), ("fill_m3", fill_m3),
                          ("gravel_m3", gravel_m3), ("haul_distance_km", haul_distance_km),
                          ("concrete_m3", concrete_m3), ("steel_kg", steel_kg)):
            if val < 0:
                raise ValueError(f"{name} must be non-negative, got {val}")

        f = self.factors
        moved = cut_m3 + fill_m3
        result = CO2Result()
        result.excavation_kg = moved * f.excavation_kg_per_m3
        # Cut spoil + imported gravel are the volumes actually trucked.
        result.haul_kg = (cut_m3 + gravel_m3) * haul_distance_km * f.haul_kg_per_m3_km
        result.gravel_kg = gravel_m3 * f.gravel_production_kg_per_m3
        result.concrete_kg = concrete_m3 * f.concrete_kg_per_m3
        result.steel_kg = steel_kg * f.steel_kg_per_kg
        return result
