"""
Bodenstabilisierung (Port aus core/soil_stabilization_calculator.py).

Kalkdosierung + Schottertragschicht nach DIN 18196 / RStO 12 für WEA-
Kranstellflächen. QGIS-frei; Logging über stdlib.
"""

from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)


# Ev2-Bereiche je Bodenart (MN/m²)
SOIL_EV2_RANGES = {
    "Ton_weich": (15, 25),
    "Ton_steif": (25, 40),
    "Ton_halbfest": (40, 60),
    "Schluff_weich": (20, 35),
    "Schluff_mitteldicht": (35, 50),
    "Lehm_steif": (30, 50),
    "Lehm_halbfest": (50, 80),
    "Sand_locker": (30, 50),
    "Sand_mitteldicht": (50, 80),
    "Sand_dicht": (80, 120),
    "Kies_mitteldicht": (100, 150),
    "Kies_dicht": (150, 220),
}

LIME_DOSAGE_RANGES = {
    "Ton": (4.0, 6.0),
    "Schluff": (3.0, 5.0),
    "Lehm": (3.0, 5.0),
    "Sand": (0.0, 0.0),
    "Kies": (0.0, 0.0),
}

GRAVEL_THICKNESS_TABLE = [
    (100, 0.20),
    (80, 0.25),
    (60, 0.30),
    (45, 0.35),
    (0, 0.40),
]

OPTIMUM_WATER_CONTENT = {
    "Ton": 16.0,
    "Schluff": 18.0,
    "Lehm": 15.0,
    "Sand": 10.0,
    "Kies": 8.0,
}

DIN_SOIL_CLASSIFICATION = {
    "TL": "Ton", "TM": "Ton", "TA": "Ton",
    "UL": "Schluff", "UM": "Schluff", "UA": "Schluff",
    "SE": "Sand", "SI": "Sand", "SU": "Sand", "SW": "Sand", "ST": "Sand",
    "GE": "Kies", "GI": "Kies", "GU": "Kies", "GW": "Kies", "GT": "Kies",
    "OU": "Lehm", "OT": "Lehm", "OK": "Lehm",
}


class SoilStabilizationCalculator:
    TREATMENT_DEPTH_M = 0.30
    SOIL_BULK_DENSITY = 1.8  # t/m³
    GRAVEL_BULK_DENSITY = 2.1
    GRAVEL_LOOSENING_FACTOR = 1.15

    def estimate_lime_dosage(
        self,
        soil_type: str,
        water_content: float,
        optimum_water: float,
        current_ev2: float,
        target_ev2: float = 60.0,
    ) -> dict:
        """Kalkdosierung in % Masse + kg/m²/m³ + erwarteter Ev2 nach Behandlung."""
        if soil_type not in LIME_DOSAGE_RANGES:
            raise ValueError(f"Unbekannte Bodenart: {soil_type}")
        dmin, dmax = LIME_DOSAGE_RANGES[soil_type]
        if dmin == 0:
            return {
                "percentage": 0.0,
                "kg_per_m3": 0.0,
                "kg_per_m2": 0.0,
                "treatment_depth_m": 0.0,
                "expected_ev2_after": current_ev2,
                "note": f"Kalkstabilisierung für {soil_type} nicht empfohlen",
            }
        base = (dmin + dmax) / 2.0
        water_corr = 0.0
        if water_content > 0 and optimum_water > 0:
            excess = water_content - optimum_water
            if excess > 0:
                water_corr = excess * 0.3
        ev2_corr = 0.0
        if current_ev2 > 0 and target_ev2 / current_ev2 > 3.0:
            ev2_corr = 1.0
        dosage = max(2.0, min(8.0, base + water_corr + ev2_corr))
        treat_vol_per_m2 = self.TREATMENT_DEPTH_M
        soil_mass_per_m2 = treat_vol_per_m2 * self.SOIL_BULK_DENSITY
        kg_per_m2 = (dosage / 100.0) * soil_mass_per_m2 * 1000
        kg_per_m3 = kg_per_m2 / self.TREATMENT_DEPTH_M
        improvement = 2.0 + (dosage / 10.0)
        expected = min(current_ev2 * improvement, target_ev2) if current_ev2 > 0 else target_ev2
        return {
            "percentage": round(dosage, 1),
            "kg_per_m3": round(kg_per_m3, 1),
            "kg_per_m2": round(kg_per_m2, 1),
            "treatment_depth_m": self.TREATMENT_DEPTH_M,
            "expected_ev2_after": round(expected, 1),
        }

    def calculate_gravel_layer(
        self, subgrade_ev2: float, target_ev2: float = 120.0, area_m2: float = 1.0
    ) -> dict:
        """Schotterdicke aus Lookup-Tabelle (Planum-Ev2) + Volumen + Masse."""
        thickness = GRAVEL_THICKNESS_TABLE[-1][1]
        for min_ev2, t in GRAVEL_THICKNESS_TABLE:
            if subgrade_ev2 >= min_ev2:
                thickness = t
                break
        volume_m3 = thickness * area_m2 * self.GRAVEL_LOOSENING_FACTOR
        mass_t = volume_m3 * self.GRAVEL_BULK_DENSITY / self.GRAVEL_LOOSENING_FACTOR
        return {
            "thickness_m": thickness,
            "volume_m3": round(volume_m3, 2),
            "mass_t": round(mass_t, 2),
            "loosening_factor": self.GRAVEL_LOOSENING_FACTOR,
            "target_ev2": target_ev2,
        }

    @staticmethod
    def soil_type_from_din18196(code: str) -> Optional[str]:
        """Bodenart aus DIN-18196-Code (z. B. 'TM' → 'Ton')."""
        return DIN_SOIL_CLASSIFICATION.get(code.upper())

    @staticmethod
    def optimum_water_content(soil_type: str) -> float:
        """Optimaler Wassergehalt nach DIN 18127 für Bodenart."""
        return OPTIMUM_WATER_CONTENT.get(soil_type, 12.0)
