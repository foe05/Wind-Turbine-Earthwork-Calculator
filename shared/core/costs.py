"""
Cost Calculations

Extrahiert aus QGIS Plugin WindTurbine_Earthwork_Calculator.py
"""
from typing import Dict


def calculate_costs(
    foundation_volume: float,
    crane_cut: float,
    crane_fill: float,
    platform_area: float,
    material_balance: Dict[str, float],
    material_reuse: bool = True,
    swell_factor: float = 1.25,
    compaction_factor: float = 0.85,
    cost_excavation: float = 8.0,
    cost_transport: float = 12.0,
    cost_fill_import: float = 15.0,
    cost_gravel: float = 25.0,
    cost_compaction: float = 5.0,
    gravel_thickness: float = 0.5
) -> Dict[str, float]:
    """
    Berechnet detaillierte Kosten für Erdarbeiten

    Args:
        foundation_volume: Fundament-Aushubvolumen (m³)
        crane_cut: Kranflächen-Aushub (m³)
        crane_fill: Kranflächen-Auftrag (m³)
        platform_area: Plattformfläche (m²)
        material_balance: Dict mit Material-Bilanz
        material_reuse: Wiederverwendung aktiv?
        swell_factor: Auflockerungsfaktor
        compaction_factor: Verdichtungsfaktor
        cost_excavation: Kosten pro m³ Aushub (€)
        cost_transport: Kosten pro m³ Transport (€)
        cost_fill_import: Kosten pro m³ Material-Einkauf (€)
        cost_gravel: Kosten pro m³ Schotter (€)
        cost_compaction: Kosten pro m³ Verdichtung (€)
        gravel_thickness: Schotterschicht-Dicke (m)

    Returns:
        Dict mit allen Kosten-Komponenten
    """

    # A) BASIS-KOSTEN (immer)
    kosten_fundament_aushub = foundation_volume * cost_excavation
    kosten_fundament_transport = foundation_volume * swell_factor * cost_transport
    kosten_kranflaeche_aushub = crane_cut * cost_excavation

    # D) SCHOTTER-KOSTEN (immer)
    schotter_volumen = platform_area * gravel_thickness
    kosten_schotter = schotter_volumen * cost_gravel

    # B) KOSTEN MIT Material-Wiederverwendung
    if material_reuse:
        # Wiederverwendetes Material kostet nur Verdichtung
        kosten_wiederverwendung = material_balance['reused'] * cost_compaction

        # Überschuss muss abtransportiert werden
        kosten_ueberschuss = material_balance['surplus'] * cost_transport

        # Mangel muss eingekauft werden (inkl. Transport + Verdichtung)
        kosten_mangel = material_balance['deficit'] * (
            cost_fill_import + cost_transport + cost_compaction
        )

        # E) GESAMT-KOSTEN mit Wiederverwendung
        kosten_transport_gesamt = kosten_fundament_transport + kosten_ueberschuss
        kosten_fill_gesamt = kosten_mangel
        kosten_verdichtung_gesamt = kosten_wiederverwendung

        total_kosten_mit = (
            kosten_fundament_aushub +
            kosten_kranflaeche_aushub +
            kosten_wiederverwendung +
            kosten_ueberschuss +
            kosten_mangel +
            kosten_schotter
        )
    else:
        kosten_transport_gesamt = 0
        kosten_fill_gesamt = 0
        kosten_verdichtung_gesamt = 0
        total_kosten_mit = 0

    # C) KOSTEN OHNE Material-Wiederverwendung (für Vergleich)
    # Alles muss abtransportiert werden
    kosten_abtransport_ohne = (foundation_volume + crane_cut) * swell_factor * cost_transport

    # Alles für Fill muss eingekauft werden
    kosten_fill_ohne = crane_fill * (cost_fill_import + cost_transport + cost_compaction)

    total_kosten_ohne = (
        kosten_fundament_aushub +
        kosten_kranflaeche_aushub +
        kosten_abtransport_ohne +
        kosten_fill_ohne +
        kosten_schotter
    )

    # F) EINSPARUNG durch Wiederverwendung
    if material_reuse:
        total_kosten = total_kosten_mit
        einsparung = total_kosten_ohne - total_kosten_mit
        if total_kosten_ohne > 0:
            einsparung_prozent = (einsparung / total_kosten_ohne) * 100
        else:
            einsparung_prozent = 0
    else:
        total_kosten = total_kosten_ohne
        kosten_transport_gesamt = kosten_abtransport_ohne
        kosten_fill_gesamt = kosten_fill_ohne
        kosten_verdichtung_gesamt = crane_fill * cost_compaction
        einsparung = 0
        einsparung_prozent = 0

    # Gesamt-Kosten nach Kategorie
    kosten_aushub_gesamt = kosten_fundament_aushub + kosten_kranflaeche_aushub

    return {
        'cost_total': round(total_kosten, 2),
        'cost_excavation': round(kosten_aushub_gesamt, 2),
        'cost_transport': round(kosten_transport_gesamt, 2),
        'cost_fill': round(kosten_fill_gesamt, 2),
        'cost_gravel': round(kosten_schotter, 2),
        'cost_compaction': round(kosten_verdichtung_gesamt, 2),
        'cost_saving': round(einsparung, 2),
        'saving_pct': round(einsparung_prozent, 2),
        'gravel_vol': round(schotter_volumen, 2),
        'cost_total_without_reuse': round(total_kosten_ohne, 2),
        'cost_total_with_reuse': round(total_kosten_mit if material_reuse else 0, 2)
    }
