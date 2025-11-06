"""
Material Balance Calculations

Extrahiert aus QGIS Plugin WindTurbine_Earthwork_Calculator.py
"""
from typing import Dict


def calculate_material_balance(
    foundation_volume: float,
    crane_cut: float,
    crane_fill: float,
    swell_factor: float = 1.25,
    compaction_factor: float = 0.85
) -> Dict[str, float]:
    """
    Berechnet Material-Bilanz für Erdarbeiten

    Logik:
    - Verfügbares Material: Fundament + Kranflächen-Aushub (aufgelockert)
    - Benötigtes Material: Kranflächen-Auftrag (verdichtet)

    Args:
        foundation_volume: Fundament-Aushubvolumen in m³
        crane_cut: Kranflächen-Aushub in m³
        crane_fill: Kranflächen-Auftrag in m³
        swell_factor: Auflockerungsfaktor (Standard: 1.25)
        compaction_factor: Verdichtungsfaktor (Standard: 0.85)

    Returns:
        Dict mit:
        - available: Verfügbares Material (aufgelockert)
        - required: Benötigtes Material (anstehend)
        - surplus: Überschuss (wenn available > required)
        - deficit: Mangel (wenn available < required)
        - reused: Wiederverwendetes Material
    """
    # Verfügbares Material (aufgelockert)
    available = (foundation_volume + crane_cut) * swell_factor

    # Benötigtes Material (anstehend, vor Verdichtung)
    required = crane_fill / compaction_factor

    if available >= required:
        # Überschuss
        surplus = available - required
        deficit = 0
        reused = required
    else:
        # Mangel
        surplus = 0
        deficit = required - available
        reused = available

    return {
        'available': available,
        'required': required,
        'surplus': surplus,
        'deficit': deficit,
        'reused': reused
    }
