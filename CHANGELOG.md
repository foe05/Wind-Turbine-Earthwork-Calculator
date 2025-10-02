# Changelog

Alle bedeutenden Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

---

## [4.0.0] - 2025-10-02

### 🚀 Hauptrelease - Polygon-Input-Modus & Rotations-Support

#### Hinzugefügt
- **Polygon-Input-Modus** 🔄
  - Neuer optionaler Parameter `INPUT_POLYGONS` für angepasste Standflächen
  - Automatische Extraktion von Centroid, Maßen und Rotation aus Polygonen
  - Dual-Modus: Tool kann jetzt ENTWEDER Punkte ODER Polygone verarbeiten
  - Unterstützung für beliebig rotierte Rechteck-Polygone

- **Rotations-unterstütztes DEM-Sampling**
  - `_create_platform_mask()` jetzt mit Rotations-Parameter
  - `_create_slope_mask()` jetzt mit Rotations-Parameter
  - `_create_target_dem()` jetzt mit Rotations-Parameter
  - Koordinaten-Transformation mittels Rotations-Matrix

- **Automatische Polygon-Analyse**
  - `_extract_polygon_properties()`: Extrahiert alle relevanten Eigenschaften
  - `_calculate_polygon_rotation()`: Berechnet Rotationswinkel aus längster Kante
  - **Oriented Bounding Box (OBB)**: Präzisere Maße für rotierte Polygone
  - Polygon-Validierung: Prüft Größe (10-200m), Typ, Gültigkeit

- **Auto-Rotation-Optimierung** 🤖
  - Neuer Parameter `AUTO_ROTATE`: Aktiviert automatische Rotations-Optimierung
  - Neuer Parameter `ROTATION_STEP`: Schrittweite (5°-45°, Standard: 15°)
  - `_optimize_platform_rotation()`: Testet alle Rotationen, wählt beste
  - Minimiert Cut/Fill-Ungleichgewicht automatisch
  - Funktioniert nur im Punkt-Modus (sinnvoll für erste Iteration)

- **Performance-Optimierungen**
  - `_get_rotation_matrix()`: Cached Berechnung von cos/sin
  - Vermeidet redundante Trigonometrie-Berechnungen
  - Bis zu 30% schneller bei Auto-Rotation mit vielen Standorten

- **Robuste Validierung**
  - CRS-Prüfung: Polygone müssen projiziert sein (z.B. UTM)
  - CRS-Match-Warning: Wenn Polygon-CRS ≠ DEM-CRS
  - Polygon-Größen-Validierung: Min 10m, Max 200m
  - Safe-Konvertierung für alle Polygon-Attribute

- **Verbesserter Workflow**
  - 2-Schritt-Prozess jetzt vollständig funktionsfähig:
    1. Punkte → Polygone generieren (Nord-Süd)
    2. Polygone manuell anpassen (rotieren/verschieben)
    3. Polygone als Input → Neuberechnung mit Rotation!

#### Geändert
- Algorithmus-Version: v3.0 → **v4.0**
- Display-Name: "...v3.0" → "...v4.0"
- Help-Text komplett überarbeitet mit 2-Schritt-Workflow-Anleitung
- `_calculate_complete_earthwork()`: Neue Parameter `rotation_angle`
- `_calculate_crane_pad()`: Neue Parameter `rotation_angle`
- Polygon-Output im Polygon-Modus: Original-Geometrie beibehalten

#### Behoben
- Edge Case: Fehlerbehandlung bei ungültigen Polygon-Geometrien
- CRS-Probleme werden jetzt früh erkannt und gemeldet
- Rotation-Berechnung robust gegen fehlerhafte Geometrien

---

## [3.0.0] - 2025-10-02

### 🎉 Hauptrelease - Kostenmodul & Standflächen-Export

#### Hinzugefügt
- **Kostenmodul** 💰
  - Detaillierte Kostenberechnung für alle Erdarbeiten
  - 6 neue Kosten-Parameter (Aushub, Transport, Material-Einkauf, Schotter, Verdichtung, Schotter-Schichtdicke)
  - Einsparungs-Analyse: Vergleich Mit/Ohne Material-Wiederverwendung
  - Kosten-Breakdown im HTML-Report mit Prozent-Anteilen
  - 9 neue Output-Attribute für Kosten in GeoPackage

- **Standflächen-Polygon-Export** 🗺️
  - Neuer optionaler Output: Standflächen als Polygone
  - Automatische Generierung von Rechteck-Polygonen (Nord-Süd-Ausrichtung)
  - 8 Attribute pro Polygon (id, length, width, area, cost_total, found_vol, total_cut, total_fill)
  - Bereit für manuelle Anpassung in QGIS

- **HTML-Report Verbesserungen**
  - Kosten-Übersicht mit Dashboard-Cards
  - Detaillierte Parameter-Zusammenfassung (Plattform, Fundament, Böschung, Material, Kosten)
  - Kosten-Aufschlüsselung mit Tabelle und Prozent-Anteilen
  - Vergleichs-Sektion Mit/Ohne Wiederverwendung
  - Moderne CSS-Styling mit Gradients und Shadows

- **Dokumentation**
  - [WORKFLOW_STANDFLAECHEN.md](WORKFLOW_STANDFLAECHEN.md) - Workflow für 2-Schritt-Prozess
  - [AGENTS.md](AGENTS.md) - Entwickler & AI-Assistenten Guide
  - Aktualisierte [README.md](README.md) mit vollständiger Feature-Liste

#### Geändert
- Erweiterte Attribut-Tabelle von 16 auf 25+ Felder
- Verbesserte `safe_get()` Funktion für robustes Feature-Schreiben
- HTML-Report verwendet jetzt konsequent F-Strings für Variable-Interpolation

#### Behoben
- **#1**: "Could not convert value" Fehler beim Schreiben von Features
  - Ursache: `None` oder leere Strings in Double-Feldern
  - Lösung: `safe_get()` Funktion mit Type-Checking und Fallback-Werten
- F-String Bugs im HTML-Report (Variablen wurden nicht interpoliert)
- Polygon-Attribute werden jetzt korrekt als Float konvertiert

---

## [2.0.0] - 2025-09-15

### Hauptrelease - Fundament & Material-Wiederverwendung

#### Hinzugefügt
- **Fundament-Berechnung**
  - 3 Fundament-Typen: Flachgründung, Tiefgründung, Pfahlgründung
  - Konfigurierbare Durchmesser und Tiefe
  - Separate Volumenberechnung für Fundament-Aushub

- **Material-Wiederverwendung** ♻️
  - Intelligente Logik: Fundament-Aushub → Kranflächen-Auftrag
  - Material-Bilanz mit Überschuss/Mangel-Berechnung
  - Swell-Faktor (Auflockerung) und Compaction-Faktor (Verdichtung)
  - Bodentyp-Presets: Sand/Kies, Lehm/Ton, Fels

- **HTML-Report**
  - Automatische Generierung mit detaillierten Ergebnissen
  - Zusammenfassung aller Standorte
  - Details pro Standort in Tabellenform

- **Output-Formate**
  - GeoPackage (.gpkg) statt Shapefile
  - 16 Attribute pro Feature

#### Geändert
- Algorithmus-Name: `windturbineearthworkv2` → `windturbineearthworkv3`
- Klassenname: `WindTurbineEarthworkCalculator` → `WindTurbineEarthworkCalculatorV3`

---

## [1.0.0] - 2025-08-01

### Initial Release - Basis-Funktionalität

#### Hinzugefügt
- **Grundlegende Volumenberechnung**
  - Kranstellflächen Cut/Fill basierend auf DEM
  - Böschungs-Volumen mit konfigurierbarem Winkel
  - 3 Optimierungsmethoden: Mittelwert, Min. Aushub, Ausgeglichen

- **Parameter**
  - Plattformlänge und -breite
  - Max. Plattform-Neigung
  - Böschungswinkel und -breite

- **Output**
  - Punkt-Shapefile mit Volumen-Attributen
  - Console-Log mit Berechnungsergebnissen

- **DEM-Verarbeitung**
  - Grid-basiertes Sampling
  - Plattform- und Böschungs-Masken
  - Target-DEM-Generierung

---

## [Unveröffentlicht]

### In Entwicklung (v5.0)

#### Geplant
- **Constraint-basierte Platzierung**
  - Buffer um Gebäude/Straßen
  - Automatische Konflikt-Vermeidung
  - Snap-to-Grid für standardisierte Platzierung

- **Batch-Optimierung**
  - Material-Transport zwischen Standorten minimieren
  - Kostenfunktion über gesamten Windpark
  - Multi-Site-Optimierung

- **3D-Visualisierung**
  - Export für 3D-Viewer (z.B. Cesium, Three.js)
  - Interaktive Darstellung von Cut/Fill
  - Export als 3D-Mesh (OBJ, STL)

---

## Legende

- **Hinzugefügt**: Neue Features
- **Geändert**: Änderungen an bestehender Funktionalität
- **Veraltet**: Features, die bald entfernt werden
- **Entfernt**: Entfernte Features
- **Behoben**: Bugfixes
- **Sicherheit**: Sicherheits-Patches

---

[4.0.0]: https://github.com/YOURUSERNAME/Wind-Turbine-Earthwork-Calculator/releases/tag/v4.0.0
[3.0.0]: https://github.com/YOURUSERNAME/Wind-Turbine-Earthwork-Calculator/releases/tag/v3.0.0
[2.0.0]: https://github.com/YOURUSERNAME/Wind-Turbine-Earthwork-Calculator/releases/tag/v2.0.0
[1.0.0]: https://github.com/YOURUSERNAME/Wind-Turbine-Earthwork-Calculator/releases/tag/v1.0.0
