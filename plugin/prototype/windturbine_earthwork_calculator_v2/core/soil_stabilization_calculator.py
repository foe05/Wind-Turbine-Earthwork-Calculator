"""
Soil Stabilization Calculator for Wind Turbine Earthwork Calculator V2

Berechnet Kalk- und Schottermengen für WEA-Kranstellflächen basierend auf
geotechnischen Parametern und Bodenstabilisierungsanforderungen.

Author: Wind Energy Site Planning
Version: 2.0
"""

from typing import Dict, Optional, Tuple
import math

from qgis.core import QgsPointXY

from ..utils.logging_utils import get_plugin_logger


# Ev2-Standardwerte nach Bodenart (MN/m²)
SOIL_EV2_RANGES = {
    'Ton_weich': (15, 25),
    'Ton_steif': (25, 40),
    'Ton_halbfest': (40, 60),
    'Schluff_weich': (20, 35),
    'Schluff_mitteldicht': (35, 50),
    'Lehm_steif': (30, 50),
    'Lehm_halbfest': (50, 80),
    'Sand_locker': (30, 50),
    'Sand_mitteldicht': (50, 80),
    'Sand_dicht': (80, 120),
    'Kies_mitteldicht': (100, 150),
    'Kies_dicht': (150, 220)
}

# Kalkdosierung nach Bodenart (% Masse)
LIME_DOSAGE_RANGES = {
    'Ton': (4.0, 6.0),
    'Schluff': (3.0, 5.0),
    'Lehm': (3.0, 5.0),
    'Sand': (0, 0),  # Nicht empfohlen
    'Kies': (0, 0)   # Nicht empfohlen
}

# Schotterdicke nach Planum-Ev2 (m)
# Liste von Tupeln (min_ev2, dicke_m)
GRAVEL_THICKNESS_TABLE = [
    (100, 0.20),
    (80, 0.25),
    (60, 0.30),
    (45, 0.35),
    (0, 0.40)
]

# Typische optimale Wassergehalte nach Proctor (%)
# Basierend auf DIN 18127 Erfahrungswerte
OPTIMUM_WATER_CONTENT = {
    'Ton': 16.0,      # Bindige Böden: höherer Optimum-Wassergehalt
    'Schluff': 18.0,  # Mittlere Bindigkeit
    'Lehm': 15.0,     # Gemischtkörnig
    'Sand': 10.0,     # Nicht-bindig: niedriger Optimum-Wassergehalt
    'Kies': 8.0       # Grobkörnig: sehr niedriger Optimum-Wassergehalt
}

# DIN 18196 Bodenklassen-Mapping
DIN_SOIL_CLASSIFICATION = {
    'TL': 'Ton',
    'TM': 'Ton',
    'TA': 'Ton',
    'UL': 'Schluff',
    'UM': 'Schluff',
    'UA': 'Schluff',
    'SE': 'Sand',
    'SI': 'Sand',
    'SU': 'Sand',
    'SW': 'Sand',
    'ST': 'Sand',
    'GE': 'Kies',
    'GI': 'Kies',
    'GU': 'Kies',
    'GW': 'Kies',
    'GT': 'Kies',
    'OU': 'Lehm',
    'OT': 'Lehm',
    'OK': 'Lehm'
}


class SoilStabilizationCalculator:
    """
    Berechnet Kalk- und Schottermengen für Bodenstabilisierung von WEA-Kranstellflächen.

    Die Berechnungen basieren auf:
    - DIN 18196 (Bodenklassifikation)
    - TP BF-StB (Bodenverfestigung mit Bindemitteln)
    - ZTV E-StB (Erdarbeiten im Straßenbau)
    - RStO 12 (Richtlinien für die Standardisierung des Oberbaues)

    WICHTIG: Alle Berechnungen sind Richtwerte für Vordimensionierung.
    Standortspezifische Eignungsprüfungen sind zwingend erforderlich!
    """

    def __init__(self):
        """Initialisiere mit Konstanten und Lookup-Tabellen."""
        self.logger = get_plugin_logger()

        # Konstanten für Berechnungen
        self.TREATMENT_DEPTH_M = 0.30  # Standard-Behandlungstiefe in Metern
        self.SOIL_BULK_DENSITY = 1.8   # Rohdichte Boden in t/m³
        self.GRAVEL_BULK_DENSITY = 2.1  # Rohdichte Schotter in t/m³
        self.GRAVEL_LOOSENING_FACTOR = 1.15  # Auflockerungsfaktor Schotter

        # Ev2-Verbesserungsfaktoren durch Kalkstabilisierung
        # (konservativ: 2-3x, optimal: 4-5x)
        self.EV2_IMPROVEMENT_FACTOR_MIN = 2.0
        self.EV2_IMPROVEMENT_FACTOR_MAX = 4.0

        self.logger.info("SoilStabilizationCalculator initialisiert")

    def estimate_lime_dosage(
        self,
        soil_type: str,
        water_content: float,
        optimum_water: float,
        current_ev2: float,
        target_ev2: float = 60.0
    ) -> Dict:
        """
        Berechnet Kalkdosierung basierend auf Bodenparametern.

        Args:
            soil_type: Bodenart ('Ton', 'Schluff', 'Lehm', 'Sand', 'Kies')
            water_content: Aktueller Wassergehalt in % (0 = unbekannt)
            optimum_water: Optimaler Wassergehalt nach Proctor in % (0 = unbekannt)
            current_ev2: Aktueller Ev2-Wert in MN/m²
            target_ev2: Ziel-Ev2 nach Kalkbehandlung in MN/m² (default: 60)

        Returns:
            Dict mit:
                - percentage: Kalkdosierung in % Masse
                - kg_per_m3: Kalkmenge in kg/m³ (bei 30cm Tiefe)
                - kg_per_m2: Kalkmenge in kg/m² (flächenspezifisch)
                - treatment_depth_m: Behandlungstiefe in m
                - expected_ev2_after: Erwarteter Ev2 nach Behandlung
        """
        try:
            self.logger.info(
                f"Berechne Kalkdosierung: Bodenart={soil_type}, "
                f"w={water_content}%, Ev2={current_ev2} MN/m²"
            )

            # Basis-Dosierung aus Lookup-Tabelle
            if soil_type not in LIME_DOSAGE_RANGES:
                raise ValueError(f"Unbekannte Bodenart: {soil_type}")

            dosage_min, dosage_max = LIME_DOSAGE_RANGES[soil_type]

            # Keine Kalkstabilisierung für Sand/Kies empfohlen
            if dosage_min == 0:
                self.logger.warning(
                    f"Kalkstabilisierung für {soil_type} nicht empfohlen"
                )
                return {
                    'percentage': 0.0,
                    'kg_per_m3': 0.0,
                    'kg_per_m2': 0.0,
                    'treatment_depth_m': 0.0,
                    'expected_ev2_after': current_ev2
                }

            # Basis-Dosierung (Mittelwert)
            base_dosage = (dosage_min + dosage_max) / 2.0

            # Korrektur für Wassergehalt
            water_correction = 0.0
            if water_content > 0 and optimum_water > 0:
                water_excess = water_content - optimum_water
                if water_excess > 0:
                    # Zusätzlicher Kalk für Trocknung
                    # Pro 1% Wasserüberschuss: +0.3% Kalk
                    water_correction = water_excess * 0.3
                    self.logger.info(
                        f"Wassergehalt {water_content}% > Optimum {optimum_water}%: "
                        f"+{water_correction:.1f}% Kalk für Trocknung"
                    )

            # Korrektur für Ev2-Verbesserungsbedarf
            ev2_ratio = target_ev2 / current_ev2 if current_ev2 > 0 else 1.0
            ev2_correction = 0.0

            if ev2_ratio > 3.0:
                # Sehr hohe Verbesserung benötigt mehr Bindemittel
                ev2_correction = 1.0
                self.logger.info(
                    f"Hoher Ev2-Verbesserungsbedarf ({ev2_ratio:.1f}x): "
                    f"+{ev2_correction:.1f}% Kalk"
                )

            # Finale Dosierung
            final_dosage = base_dosage + water_correction + ev2_correction

            # Begrenzung auf sinnvolle Werte (2-8%)
            final_dosage = max(2.0, min(8.0, final_dosage))

            # Umrechnung auf kg/m³ und kg/m²
            # Behandlungsvolumen pro m²: 1 m² × 0.3 m = 0.3 m³
            # Masse Boden: 0.3 m³ × 1.8 t/m³ = 0.54 t/m²
            treatment_volume_per_m2 = self.TREATMENT_DEPTH_M  # m³/m²
            soil_mass_per_m2 = treatment_volume_per_m2 * self.SOIL_BULK_DENSITY  # t/m²

            kg_per_m2 = (final_dosage / 100.0) * soil_mass_per_m2 * 1000  # kg/m²
            kg_per_m3 = kg_per_m2 / self.TREATMENT_DEPTH_M  # kg/m³

            # Erwartete Ev2-Verbesserung
            # Konservative Schätzung: 2.5-fache Verbesserung bei optimaler Dosierung
            improvement_factor = 2.0 + (final_dosage / 10.0)  # 2.0 - 2.8
            expected_ev2_after = min(current_ev2 * improvement_factor, target_ev2)

            result = {
                'percentage': round(final_dosage, 1),
                'kg_per_m3': round(kg_per_m3, 1),
                'kg_per_m2': round(kg_per_m2, 1),
                'treatment_depth_m': self.TREATMENT_DEPTH_M,
                'expected_ev2_after': round(expected_ev2_after, 1)
            }

            self.logger.info(
                f"Kalkdosierung berechnet: {result['percentage']}% "
                f"({result['kg_per_m2']} kg/m²), "
                f"erwarteter Ev2: {result['expected_ev2_after']} MN/m²"
            )

            return result

        except Exception as e:
            self.logger.error(f"Fehler bei Kalkdosierung-Berechnung: {e}", exc_info=True)
            raise

    def calculate_gravel_layer(
        self,
        subgrade_ev2: float,
        target_ev2: float = 120.0,
        area_m2: float = 1.0
    ) -> Dict:
        """
        Berechnet Schottertragschicht nach RStO 12.

        Args:
            subgrade_ev2: Ev2 des Planums (nach Kalkbehandlung) in MN/m²
            target_ev2: Ziel-Ev2 auf Schotter in MN/m² (default: 120 für WEA)
            area_m2: Flächengröße in m² (default: 1.0)

        Returns:
            Dict mit:
                - thickness_m: Schichtdicke verdichtet in m
                - compacted_volume_m3: Volumen verdichtet in m³
                - loose_volume_m3: Volumen lose (mit Auflockerung)
                - mass_tons: Masse in Tonnen
                - area_specific_kg_m2: Flächenspezifische Masse in kg/m²
        """
        try:
            self.logger.info(
                f"Berechne Schottertragschicht: Planum Ev2={subgrade_ev2} MN/m², "
                f"Fläche={area_m2:.0f} m²"
            )

            # Schichtdicke aus Tabelle ermitteln
            thickness_m = 0.40  # Default: dickste Schicht

            for min_ev2, thickness in GRAVEL_THICKNESS_TABLE:
                if subgrade_ev2 >= min_ev2:
                    thickness_m = thickness
                    break

            self.logger.info(
                f"Schichtdicke aus RStO 12: {thickness_m*100:.0f} cm "
                f"(bei Planum-Ev2 {subgrade_ev2} MN/m²)"
            )

            # Volumenberechnung
            compacted_volume_m3 = area_m2 * thickness_m
            loose_volume_m3 = compacted_volume_m3 * self.GRAVEL_LOOSENING_FACTOR

            # Massenberechnung (verdichteter Zustand)
            mass_tons = compacted_volume_m3 * self.GRAVEL_BULK_DENSITY

            # Flächenspezifisch
            area_specific_kg_m2 = (mass_tons / area_m2) * 1000 if area_m2 > 0 else 0

            result = {
                'thickness_m': round(thickness_m, 2),
                'compacted_volume_m3': round(compacted_volume_m3, 1),
                'loose_volume_m3': round(loose_volume_m3, 1),
                'mass_tons': round(mass_tons, 1),
                'area_specific_kg_m2': round(area_specific_kg_m2, 0)
            }

            self.logger.info(
                f"Schottertragschicht: {result['thickness_m']*100:.0f} cm, "
                f"{result['mass_tons']:.0f} t ({result['loose_volume_m3']:.0f} m³ lose)"
            )

            return result

        except Exception as e:
            self.logger.error(f"Fehler bei Schotterberechnung: {e}", exc_info=True)
            raise

    def calculate_full_requirements(
        self,
        platform_area_m2: float,
        soil_type: str,
        current_ev2: float,
        water_content: Optional[float] = None,
        optimum_water: Optional[float] = None
    ) -> Dict:
        """
        Vollständige Berechnung für Kranstellfläche.

        Args:
            platform_area_m2: Kranstellfläche in m²
            soil_type: Bodenart (z.B. 'Ton', 'Schluff')
            current_ev2: Aktueller Ev2-Wert in MN/m²
            water_content: Aktueller Wassergehalt in % (optional)
            optimum_water: Optimaler Wassergehalt in % (optional)

        Returns:
            Dict mit vollständigen Ergebnissen:
                - area_m2: Flächengröße
                - initial_ev2: Ausgangs-Ev2
                - soil_type: Bodenart
                - lime_treatment: Dict mit Kalkbehandlung oder None
                - ev2_after_lime: Ev2 nach Kalkbehandlung
                - gravel_layer: Dict mit Schottertragschicht
                - final_ev2_expected: Erwarteter finaler Ev2
                - total_lime_tons: Gesamtmenge Kalk in Tonnen
                - total_gravel_tons: Gesamtmenge Schotter in Tonnen
                - quality_notes: Liste mit Hinweisen
                - reliability_rating: 'high', 'medium', 'low'
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("BODENSTABILISIERUNG - Vollständige Berechnung")
            self.logger.info("=" * 60)
            self.logger.info(f"Fläche: {platform_area_m2:.0f} m²")
            self.logger.info(f"Bodenart: {soil_type}")
            self.logger.info(f"Ausgangs-Ev2: {current_ev2} MN/m²")

            quality_notes = []

            # Setze Standardwerte für optionale Parameter
            if water_content is None or water_content == 0:
                water_content = 0
                quality_notes.append(
                    "Wassergehalt unbekannt - Standarddosierung verwendet"
                )

            if optimum_water is None or optimum_water == 0:
                optimum_water = 0

            # === SCHRITT 1: Kalkstabilisierung (falls erforderlich) ===
            lime_treatment = None
            ev2_after_lime = current_ev2
            total_lime_tons = 0.0

            # Kalkbehandlung bei Ev2 < 45 MN/m²
            if current_ev2 < 45.0:
                self.logger.info("Ev2 < 45 MN/m² → Kalkstabilisierung erforderlich")

                lime_treatment = self.estimate_lime_dosage(
                    soil_type=soil_type,
                    water_content=water_content,
                    optimum_water=optimum_water,
                    current_ev2=current_ev2,
                    target_ev2=60.0  # Ziel: mindestens 60 MN/m²
                )

                if lime_treatment['percentage'] > 0:
                    ev2_after_lime = lime_treatment['expected_ev2_after']
                    total_lime_tons = (lime_treatment['kg_per_m2'] * platform_area_m2) / 1000

                    quality_notes.append(
                        f"Kalkstabilisierung mit {lime_treatment['percentage']:.1f}% "
                        f"(ca. {total_lime_tons:.1f} t) erforderlich"
                    )

                    if lime_treatment['percentage'] > 6.0:
                        quality_notes.append(
                            "WARNUNG: Hohe Kalkdosierung - Eignungsprüfung nach "
                            "TP BF-StB zwingend erforderlich!"
                        )
                else:
                    quality_notes.append(
                        f"Kalkstabilisierung für {soil_type} nicht geeignet - "
                        "Alternative Maßnahmen prüfen (Bodenaustausch, Zement)"
                    )
            else:
                self.logger.info("Ev2 ≥ 45 MN/m² → Keine Kalkstabilisierung erforderlich")
                quality_notes.append(
                    "Planum-Ev2 ausreichend - keine Bodenverfestigung nötig"
                )

            # === SCHRITT 2: Schottertragschicht ===
            gravel_layer = self.calculate_gravel_layer(
                subgrade_ev2=ev2_after_lime,
                target_ev2=120.0,
                area_m2=platform_area_m2
            )

            total_gravel_tons = gravel_layer['mass_tons']

            quality_notes.append(
                f"Schottertragschicht {gravel_layer['thickness_m']*100:.0f} cm "
                f"(ca. {total_gravel_tons:.0f} t)"
            )

            # === SCHRITT 3: Finaler Ev2 ===
            # Mit Schottertragschicht wird Ziel-Ev2 erreicht
            final_ev2_expected = 120.0

            # === SCHRITT 4: Zuverlässigkeitsbewertung ===
            reliability_rating = self._assess_reliability(
                soil_type=soil_type,
                current_ev2=current_ev2,
                water_content=water_content,
                lime_treatment=lime_treatment
            )

            # === SCHRITT 5: Zusätzliche Qualitätshinweise ===
            if gravel_layer['thickness_m'] > 0.30:
                quality_notes.append(
                    "Dicke Schotterschicht - Stufenweise Verdichtung erforderlich "
                    "(max. 20cm pro Lage)"
                )

            if soil_type in ['Ton', 'Schluff', 'Lehm']:
                quality_notes.append(
                    "Bindiger Boden - Drainage und Oberflächenentwässerung kritisch!"
                )

            if current_ev2 < 25.0:
                quality_notes.append(
                    "ACHTUNG: Sehr weicher Untergrund - Tragfähigkeitsprüfung "
                    "und ggf. Bodenaustausch erwägen"
                )
                reliability_rating = 'low'

            # === ERGEBNIS ===
            result = {
                'area_m2': round(platform_area_m2, 1),
                'initial_ev2': round(current_ev2, 1),
                'soil_type': soil_type,
                'lime_treatment': lime_treatment,
                'ev2_after_lime': round(ev2_after_lime, 1),
                'gravel_layer': gravel_layer,
                'final_ev2_expected': round(final_ev2_expected, 1),
                'total_lime_tons': round(total_lime_tons, 1),
                'total_gravel_tons': round(total_gravel_tons, 0),
                'quality_notes': quality_notes,
                'reliability_rating': reliability_rating
            }

            self.logger.info("=" * 60)
            self.logger.info("ERGEBNIS:")
            self.logger.info(f"  Kalk: {result['total_lime_tons']:.1f} t")
            self.logger.info(f"  Schotter: {result['total_gravel_tons']:.0f} t")
            self.logger.info(f"  Finaler Ev2: {result['final_ev2_expected']:.0f} MN/m²")
            self.logger.info(f"  Zuverlässigkeit: {result['reliability_rating']}")
            self.logger.info("=" * 60)

            return result

        except Exception as e:
            self.logger.error(f"Fehler bei Gesamtberechnung: {e}", exc_info=True)
            raise

    def _assess_reliability(
        self,
        soil_type: str,
        current_ev2: float,
        water_content: float,
        lime_treatment: Optional[Dict]
    ) -> str:
        """
        Bewertet Zuverlässigkeit der Berechnung.

        Returns:
            'high', 'medium', oder 'low'
        """
        # Hohe Zuverlässigkeit: Standard-Szenarien
        if current_ev2 >= 45.0 and water_content == 0:
            return 'high'

        # Niedrige Zuverlässigkeit: Kritische Fälle
        if current_ev2 < 25.0:
            return 'low'

        if lime_treatment and lime_treatment.get('percentage', 0) > 6.0:
            return 'low'

        if soil_type in ['Sand', 'Kies'] and current_ev2 < 45.0:
            return 'low'

        # Ansonsten: Mittlere Zuverlässigkeit
        return 'medium'

    def get_soil_type_from_classification(self, din_class: str) -> str:
        """
        Konvertiert DIN 18196 Bodenklasse zu vereinfachtem Typ.

        Args:
            din_class: DIN 18196 Bodenklasse (z.B. 'TL', 'UM', 'SE', 'GW')

        Returns:
            Vereinfachter Typ: 'Ton', 'Schluff', 'Lehm', 'Sand', 'Kies'

        Raises:
            ValueError: Wenn Bodenklasse unbekannt
        """
        din_class_upper = din_class.upper().strip()

        if din_class_upper in DIN_SOIL_CLASSIFICATION:
            soil_type = DIN_SOIL_CLASSIFICATION[din_class_upper]
            self.logger.info(f"DIN-Klasse {din_class} → {soil_type}")
            return soil_type
        else:
            raise ValueError(
                f"Unbekannte DIN-Bodenklasse: {din_class}. "
                f"Bekannte Klassen: {', '.join(DIN_SOIL_CLASSIFICATION.keys())}"
            )

    def query_soil_data_from_bgr(
        self,
        coordinates: QgsPointXY,
        crs: 'QgsCoordinateReferenceSystem'
    ) -> Dict:
        """
        Fragt Bodendaten von BGR-WFS ab.

        Args:
            coordinates: WEA-Standort
            crs: Koordinatenreferenzsystem

        Returns:
            Dict mit:
                - soil_type: Bodenart oder None
                - soil_code: BGR Bodenart-Code
                - source: Datenquelle
                - available: Bool ob Daten verfügbar
                - description: Bodenbeschreibung
                - error: Fehlermeldung (optional)
        """
        try:
            from .bgr_soil_api import get_soil_data_from_bgr

            self.logger.info("Starte BGR-Bodendaten-Abfrage...")

            result = get_soil_data_from_bgr(coordinates, crs, buffer_m=100.0)

            if result.get('success'):
                self.logger.info(
                    f"BGR-Daten erfolgreich: {result.get('soil_type')} "
                    f"(Code: {result.get('soil_code')})"
                )

                return {
                    'soil_type': result.get('soil_type'),
                    'soil_code': result.get('soil_code'),
                    'source': result.get('source', 'BGR WFS'),
                    'available': True,
                    'description': result.get('description', ''),
                    'legend': result.get('legend', '')
                }
            else:
                self.logger.warning(
                    f"BGR-Abfrage fehlgeschlagen: {result.get('error')}"
                )

                return {
                    'soil_type': None,
                    'soil_code': None,
                    'source': 'BGR WFS (Fehler)',
                    'available': False,
                    'error': result.get('error', 'Unbekannter Fehler')
                }

        except ImportError as e:
            self.logger.error(f"BGR-API-Modul konnte nicht geladen werden: {e}")
            return {
                'soil_type': None,
                'soil_code': None,
                'source': 'BGR WFS (nicht verfügbar)',
                'available': False,
                'error': 'BGR-API-Modul fehlt'
            }
        except Exception as e:
            self.logger.error(f"BGR-Abfrage fehlgeschlagen: {e}", exc_info=True)
            return {
                'soil_type': None,
                'soil_code': None,
                'source': 'BGR WFS (Fehler)',
                'available': False,
                'error': str(e)
            }
