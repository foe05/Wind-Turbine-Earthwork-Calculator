"""CO₂-Bilanz (1:1-Port aus core/co2_balance.py)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmissionFactors:
    excavation_kg_per_m3: float = 2.5
    haul_kg_per_m3_km: float = 0.12
    gravel_production_kg_per_m3: float = 5.0
    concrete_kg_per_m3: float = 280.0
    steel_kg_per_kg: float = 1.5

    def __post_init__(self) -> None:
        for name in (
            "excavation_kg_per_m3",
            "haul_kg_per_m3_km",
            "gravel_production_kg_per_m3",
            "concrete_kg_per_m3",
            "steel_kg_per_kg",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass
class CO2Result:
    excavation_kg: float = 0.0
    haul_kg: float = 0.0
    gravel_kg: float = 0.0
    concrete_kg: float = 0.0
    steel_kg: float = 0.0

    @property
    def total_kg(self) -> float:
        return self.excavation_kg + self.haul_kg + self.gravel_kg + self.concrete_kg + self.steel_kg

    @property
    def total_t(self) -> float:
        return self.total_kg / 1000.0

    def as_breakdown(self) -> dict:
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
    def __init__(self, factors: EmissionFactors | None = None):
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
        for name, val in (
            ("cut_m3", cut_m3),
            ("fill_m3", fill_m3),
            ("gravel_m3", gravel_m3),
            ("haul_distance_km", haul_distance_km),
            ("concrete_m3", concrete_m3),
            ("steel_kg", steel_kg),
        ):
            if val < 0:
                raise ValueError(f"{name} must be non-negative, got {val}")
        f = self.factors
        moved = cut_m3 + fill_m3
        r = CO2Result()
        r.excavation_kg = moved * f.excavation_kg_per_m3
        r.haul_kg = (cut_m3 + gravel_m3) * haul_distance_km * f.haul_kg_per_m3_km
        r.gravel_kg = gravel_m3 * f.gravel_production_kg_per_m3
        r.concrete_kg = concrete_m3 * f.concrete_kg_per_m3
        r.steel_kg = steel_kg * f.steel_kg_per_kg
        return r
