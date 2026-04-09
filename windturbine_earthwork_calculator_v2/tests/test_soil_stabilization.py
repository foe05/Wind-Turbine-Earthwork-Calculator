"""
Unittest für SoilStabilizationCalculator

Testet die Berechnungslogik mit bekannten Szenarien

Author: Wind Energy Site Planning
Version: 2.0
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.soil_stabilization_calculator import SoilStabilizationCalculator


class TestSoilStabilization(unittest.TestCase):
    """Test cases for SoilStabilizationCalculator"""

    def setUp(self):
        """Set up test fixtures."""
        self.calc = SoilStabilizationCalculator()

    def test_lime_dosage_clay(self):
        """Test Kalkdosierung für Ton"""
        result = self.calc.estimate_lime_dosage(
            soil_type='Ton',
            water_content=22.0,
            optimum_water=14.0,
            current_ev2=20.0,
            target_ev2=60.0
        )

        # Erwartung: 4-6% für Ton, plus Trocknung
        self.assertGreaterEqual(result['percentage'], 4.0)
        self.assertLessEqual(result['percentage'], 8.0)
        self.assertGreater(result['kg_per_m2'], 0)
        self.assertGreater(result['kg_per_m3'], 0)
        self.assertEqual(result['treatment_depth_m'], 0.30)
        self.assertGreater(result['expected_ev2_after'], 20.0)

        print(f"✓ test_lime_dosage_clay: {result['percentage']:.1f}% "
              f"({result['kg_per_m2']:.0f} kg/m²)")

    def test_lime_dosage_schluff(self):
        """Test Kalkdosierung für Schluff"""
        result = self.calc.estimate_lime_dosage(
            soil_type='Schluff',
            water_content=18.0,
            optimum_water=16.0,
            current_ev2=25.0,
            target_ev2=60.0
        )

        # Erwartung: 3-5% für Schluff
        self.assertGreaterEqual(result['percentage'], 3.0)
        self.assertLessEqual(result['percentage'], 7.0)
        self.assertGreater(result['expected_ev2_after'], 25.0)

        print(f"✓ test_lime_dosage_schluff: {result['percentage']:.1f}% "
              f"({result['kg_per_m2']:.0f} kg/m²)")

    def test_no_lime_for_sand(self):
        """Test: Keine Kalkstabilisierung für Sand"""
        result = self.calc.estimate_lime_dosage(
            soil_type='Sand',
            water_content=0,
            optimum_water=0,
            current_ev2=30.0,
            target_ev2=60.0
        )

        # Sand sollte keine Kalkbehandlung bekommen
        self.assertEqual(result['percentage'], 0.0)
        self.assertEqual(result['kg_per_m2'], 0.0)
        self.assertEqual(result['expected_ev2_after'], 30.0)

        print(f"✓ test_no_lime_for_sand: Kein Kalk (wie erwartet)")

    def test_gravel_thickness_low_ev2(self):
        """Test Schotterdicke bei niedrigem Ev2"""
        result = self.calc.calculate_gravel_layer(
            subgrade_ev2=45.0,
            target_ev2=120.0,
            area_m2=3000.0
        )

        # Bei Ev2=45 erwarten wir 35cm Schichtdicke
        self.assertEqual(result['thickness_m'], 0.35)
        self.assertGreater(result['mass_tons'], 0)
        self.assertGreater(result['compacted_volume_m3'], 0)
        self.assertGreater(result['loose_volume_m3'], result['compacted_volume_m3'])

        expected_volume = 3000.0 * 0.35
        self.assertAlmostEqual(result['compacted_volume_m3'], expected_volume, places=1)

        print(f"✓ test_gravel_thickness_low_ev2: {result['thickness_m']*100:.0f} cm, "
              f"{result['mass_tons']:.0f} t")

    def test_gravel_thickness_high_ev2(self):
        """Test Schotterdicke bei hohem Ev2"""
        result = self.calc.calculate_gravel_layer(
            subgrade_ev2=100.0,
            target_ev2=120.0,
            area_m2=3000.0
        )

        # Bei Ev2=100 erwarten wir 20cm Schichtdicke
        self.assertEqual(result['thickness_m'], 0.20)

        print(f"✓ test_gravel_thickness_high_ev2: {result['thickness_m']*100:.0f} cm, "
              f"{result['mass_tons']:.0f} t")

    def test_gravel_thickness_very_low_ev2(self):
        """Test Schotterdicke bei sehr niedrigem Ev2"""
        result = self.calc.calculate_gravel_layer(
            subgrade_ev2=20.0,
            target_ev2=120.0,
            area_m2=3000.0
        )

        # Bei sehr niedrigem Ev2 erwarten wir maximale Dicke (40cm)
        self.assertEqual(result['thickness_m'], 0.40)

        print(f"✓ test_gravel_thickness_very_low_ev2: {result['thickness_m']*100:.0f} cm "
              f"(Maximum)")

    def test_full_calculation_with_lime(self):
        """Test vollständige Berechnung mit Kalkstabilisierung"""
        result = self.calc.calculate_full_requirements(
            platform_area_m2=3000.0,
            soil_type='Schluff',
            current_ev2=25.0,
            water_content=20.0,
            optimum_water=14.0
        )

        # Bei Ev2=25 sollte Kalkbehandlung vorgeschlagen werden
        self.assertIsNotNone(result['lime_treatment'])
        self.assertGreater(result['total_lime_tons'], 0)
        self.assertGreater(result['total_gravel_tons'], 0)
        self.assertEqual(result['area_m2'], 3000.0)
        self.assertEqual(result['initial_ev2'], 25.0)
        self.assertEqual(result['soil_type'], 'Schluff')
        self.assertGreater(result['ev2_after_lime'], result['initial_ev2'])
        self.assertEqual(result['final_ev2_expected'], 120.0)
        self.assertIsInstance(result['quality_notes'], list)
        self.assertGreater(len(result['quality_notes']), 0)
        self.assertIn(result['reliability_rating'], ['high', 'medium', 'low'])

        print(f"✓ test_full_calculation_with_lime:")
        print(f"  Kalk: {result['total_lime_tons']:.1f} t")
        print(f"  Schotter: {result['total_gravel_tons']:.0f} t")
        print(f"  Ev2: {result['initial_ev2']} → {result['final_ev2_expected']} MN/m²")

    def test_no_lime_needed_high_ev2(self):
        """Test: Keine Kalkbehandlung bei ausreichendem Ev2"""
        result = self.calc.calculate_full_requirements(
            platform_area_m2=3000.0,
            soil_type='Sand',
            current_ev2=80.0
        )

        # Bei Ev2=80 keine Kalkbehandlung nötig
        self.assertIsNone(result['lime_treatment'])
        self.assertEqual(result['total_lime_tons'], 0)
        self.assertGreater(result['total_gravel_tons'], 0)
        self.assertEqual(result['ev2_after_lime'], 80.0)

        print(f"✓ test_no_lime_needed_high_ev2: Nur Schotter "
              f"({result['total_gravel_tons']:.0f} t)")

    def test_reliability_rating(self):
        """Test Zuverlässigkeitsbewertung"""
        # Hohe Zuverlässigkeit: Guter Ev2, keine Probleme
        result_high = self.calc.calculate_full_requirements(
            platform_area_m2=3000.0,
            soil_type='Sand',
            current_ev2=80.0
        )
        self.assertEqual(result_high['reliability_rating'], 'high')

        # Niedrige Zuverlässigkeit: Sehr weicher Untergrund
        result_low = self.calc.calculate_full_requirements(
            platform_area_m2=3000.0,
            soil_type='Ton',
            current_ev2=20.0,
            water_content=25.0,
            optimum_water=12.0
        )
        self.assertEqual(result_low['reliability_rating'], 'low')

        print(f"✓ test_reliability_rating: high={result_high['reliability_rating']}, "
              f"low={result_low['reliability_rating']}")

    def test_din_classification_conversion(self):
        """Test DIN 18196 Bodenklassen-Konvertierung"""
        self.assertEqual(self.calc.get_soil_type_from_classification('TL'), 'Ton')
        self.assertEqual(self.calc.get_soil_type_from_classification('UM'), 'Schluff')
        self.assertEqual(self.calc.get_soil_type_from_classification('SE'), 'Sand')
        self.assertEqual(self.calc.get_soil_type_from_classification('GW'), 'Kies')
        self.assertEqual(self.calc.get_soil_type_from_classification('OK'), 'Lehm')

        # Test case-insensitive
        self.assertEqual(self.calc.get_soil_type_from_classification('tl'), 'Ton')

        # Test ungültige Klasse
        with self.assertRaises(ValueError):
            self.calc.get_soil_type_from_classification('INVALID')

        print(f"✓ test_din_classification_conversion: TL→Ton, UM→Schluff, etc.")

    def test_quality_notes_generation(self):
        """Test dass Qualitätshinweise generiert werden"""
        result = self.calc.calculate_full_requirements(
            platform_area_m2=3000.0,
            soil_type='Ton',
            current_ev2=30.0,
            water_content=0,  # Unbekannt
            optimum_water=0
        )

        notes = result['quality_notes']
        self.assertIsInstance(notes, list)
        self.assertGreater(len(notes), 0)

        # Prüfe dass Hinweis für unbekannten Wassergehalt vorhanden ist
        has_water_note = any('Wassergehalt' in note for note in notes)
        self.assertTrue(has_water_note)

        # Prüfe dass Hinweis für bindigen Boden vorhanden ist
        has_drainage_note = any('bindiger' in note.lower() or 'drainage' in note.lower()
                               for note in notes)
        self.assertTrue(has_drainage_note)

        print(f"✓ test_quality_notes_generation: {len(notes)} Hinweise generiert")

    def test_bgr_query_placeholder(self):
        """Test dass BGR-Abfrage Platzhalter funktioniert"""
        from qgis.core import QgsPointXY

        result = self.calc.query_soil_data_from_bgr(QgsPointXY(0, 0))

        self.assertIsInstance(result, dict)
        self.assertIn('available', result)
        self.assertFalse(result['available'])
        self.assertIsNone(result['soil_type'])

        print(f"✓ test_bgr_query_placeholder: Platzhalter funktioniert")


def run_tests():
    """Run all tests with verbose output."""
    print("=" * 70)
    print("SoilStabilizationCalculator - Unit Tests")
    print("=" * 70)

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSoilStabilization)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print("✅ Alle Tests erfolgreich!")
    else:
        print("❌ Einige Tests sind fehlgeschlagen")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
