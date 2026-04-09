"""
Test-Script für BGR WFS-API Integration

Testet die Verbindung und Datenabfrage vom BGR WFS-Service.

Author: Wind Energy Site Planning
Version: 2.0
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from qgis.core import QgsPointXY, QgsCoordinateReferenceSystem
from core.bgr_soil_api import BGRSoilAPI, get_soil_data_from_bgr


def test_connection():
    """Testet Verbindung zum BGR WFS-Service."""
    print("=" * 70)
    print("TEST 1: BGR WFS-Service Verbindung")
    print("=" * 70)

    api = BGRSoilAPI()
    result = api.test_connection()

    print(f"Erfolg: {result['success']}")
    print(f"Status: {result['status_code']}")
    print(f"Meldung: {result['message']}")
    print()

    return result['success']


def test_soil_query_berlin():
    """Testet Bodendaten-Abfrage für Berlin."""
    print("=" * 70)
    print("TEST 2: Bodendaten-Abfrage Berlin (Brandenburger Tor)")
    print("=" * 70)

    # Brandenburger Tor: 52.5163° N, 13.3777° E (WGS84)
    point = QgsPointXY(13.3777, 52.5163)
    crs = QgsCoordinateReferenceSystem("EPSG:4326")

    print(f"Koordinaten: {point.x():.4f}, {point.y():.4f} ({crs.authid()})")
    print("Abfrage läuft...")
    print()

    result = get_soil_data_from_bgr(point, crs, buffer_m=500.0)

    if result.get('success'):
        print("✓ Abfrage erfolgreich!")
        print(f"  Bodenart: {result.get('soil_type')}")
        print(f"  BGR-Code: {result.get('soil_code')}")
        print(f"  Beschreibung: {result.get('description', '')[:100]}...")
        print(f"  Quelle: {result.get('source')}")
        print(f"  Legende: {result.get('legend', '')}")
    else:
        print(f"✗ Abfrage fehlgeschlagen: {result.get('error')}")

    print()
    return result.get('success', False)


def test_soil_query_hamburg():
    """Testet Bodendaten-Abfrage für Hamburg."""
    print("=" * 70)
    print("TEST 3: Bodendaten-Abfrage Hamburg (Rathaus)")
    print("=" * 70)

    # Hamburg Rathaus: 53.5511° N, 9.9937° E (WGS84)
    point = QgsPointXY(9.9937, 53.5511)
    crs = QgsCoordinateReferenceSystem("EPSG:4326")

    print(f"Koordinaten: {point.x():.4f}, {point.y():.4f} ({crs.authid()})")
    print("Abfrage läuft...")
    print()

    result = get_soil_data_from_bgr(point, crs, buffer_m=500.0)

    if result.get('success'):
        print("✓ Abfrage erfolgreich!")
        print(f"  Bodenart: {result.get('soil_type')}")
        print(f"  BGR-Code: {result.get('soil_code')}")
        print(f"  Beschreibung: {result.get('description', '')[:100]}...")
        print(f"  Quelle: {result.get('source')}")
    else:
        print(f"✗ Abfrage fehlgeschlagen: {result.get('error')}")

    print()
    return result.get('success', False)


def test_soil_query_utm():
    """Testet Bodendaten-Abfrage mit UTM-Koordinaten."""
    print("=" * 70)
    print("TEST 4: Bodendaten-Abfrage mit UTM32 (München)")
    print("=" * 70)

    # München (ungefähr): UTM Zone 32N
    point = QgsPointXY(691000, 5333000)
    crs = QgsCoordinateReferenceSystem("EPSG:25832")  # UTM Zone 32N

    print(f"Koordinaten: {point.x():.0f}, {point.y():.0f} ({crs.authid()})")
    print("Abfrage läuft (mit Koordinatentransformation)...")
    print()

    result = get_soil_data_from_bgr(point, crs, buffer_m=500.0)

    if result.get('success'):
        print("✓ Abfrage erfolgreich!")
        print(f"  Bodenart: {result.get('soil_type')}")
        print(f"  BGR-Code: {result.get('soil_code')}")
        print(f"  Beschreibung: {result.get('description', '')[:100]}...")
        print(f"  Quelle: {result.get('source')}")
    else:
        print(f"✗ Abfrage fehlgeschlagen: {result.get('error')}")

    print()
    return result.get('success', False)


def test_outside_germany():
    """Testet Abfrage außerhalb Deutschlands (sollte fehlschlagen)."""
    print("=" * 70)
    print("TEST 5: Abfrage außerhalb Deutschlands (Paris)")
    print("=" * 70)

    # Paris: 48.8566° N, 2.3522° E
    point = QgsPointXY(2.3522, 48.8566)
    crs = QgsCoordinateReferenceSystem("EPSG:4326")

    print(f"Koordinaten: {point.x():.4f}, {point.y():.4f}")
    print("Abfrage läuft (sollte keine Daten finden)...")
    print()

    result = get_soil_data_from_bgr(point, crs, buffer_m=500.0)

    if result.get('success'):
        print(f"✓ Unerwartete Daten gefunden: {result.get('soil_type')}")
        success = False
    else:
        print(f"✓ Erwarteter Fehler: {result.get('error')}")
        success = True

    print()
    return success


def run_all_tests():
    """Führt alle Tests aus."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "BGR WFS-API Test Suite" + " " * 31 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    tests = [
        ("Connection Test", test_connection),
        ("Berlin Query", test_soil_query_berlin),
        ("Hamburg Query", test_soil_query_hamburg),
        ("UTM Coordinates", test_soil_query_utm),
        ("Outside Germany", test_outside_germany),
    ]

    results = []

    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"✗ Exception in {name}: {e}")
            results.append((name, False))

    # Zusammenfassung
    print("=" * 70)
    print("ZUSAMMENFASSUNG")
    print("=" * 70)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8} | {name}")

    print()
    print(f"Ergebnis: {passed}/{total} Tests erfolgreich")
    print("=" * 70)

    return passed == total


if __name__ == '__main__':
    print("\nHINWEIS: Diese Tests benötigen eine aktive Internet-Verbindung!")
    print("         Der BGR WFS-Service muss erreichbar sein.")
    print()

    input("Drücken Sie Enter zum Starten der Tests...")

    success = run_all_tests()

    print()
    if success:
        print("✅ Alle Tests erfolgreich!")
        sys.exit(0)
    else:
        print("❌ Einige Tests sind fehlgeschlagen")
        print("   Bitte prüfen Sie Internet-Verbindung und BGR-Service-Verfügbarkeit")
        sys.exit(1)
