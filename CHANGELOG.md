# Changelog

Alle bedeutenden Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

---

## [2.0.0] - 2025-11-21

### 🚀 Hauptrelease - Modulares QGIS Plugin & Microservices Webapp

#### Hinzugefügt

- **Vollständiges QGIS Processing Plugin** 🔌
  - Komplette Neustrukturierung als modulares Plugin-Paket
  - Installation über QGIS Plugin-Manager möglich
  - Automatische Dependency-Installation (`install_dependencies.py`)
  - Multi-Tab GUI-Dialog für benutzerfreundliche Eingabe
  - Separater Processing Provider und Algorithmus

- **Modulare Code-Architektur** 📦
  - `core/` - Business Logic (QGIS-unabhängig)
    - `dxf_importer.py` - DXF-Parsing mit ezdxf
    - `dem_downloader.py` - API-Integration & Caching
    - `earthwork_calculator.py` - Volumenberechnung
    - `multi_surface_calculator.py` - Multi-Flächen-Support
    - `profile_generator.py` - Geländeschnitte
    - `report_generator.py` - HTML-Reports
    - `workflow_runner.py` - Orchestrierung
  - `gui/` - PyQt5 Dialoge
  - `processing_provider/` - QGIS Integration
  - `utils/` - Hilfsfunktionen & Logging

- **Multi-Surface-Berechnung** 🏗️
  - Kranstellfläche (Hauptfläche)
  - Fundamentfläche (mit Aushubtiefe)
  - Auslegerfläche (mit Gefälle)
  - Rotorblattlagerfläche (mit Höhenversatz)
  - Individuelle Parameter pro Flächentyp
  - Automatische Flächenvalidierung

- **Web-Anwendung (Microservices)** 🌐
  - 6 FastAPI-Services + React Frontend
  - Docker Compose Orchestrierung
  - API Gateway mit Rate-Limiting
  - JWT-Authentifizierung
  - Alle Services auf Version 2.0.0

- **Verbesserte Reports** 📊
  - Übersichtskarte mit allen Flächen (1:3000)
  - Einzelflächen-Details mit Abtrag/Auftrag
  - Globale Höhenparameter (FOK, Kranstellflächen-Höhe)
  - Externes Schottermaterial-Tracking

#### Geändert
- Projektstruktur: Single-File → Modulares Plugin
- Version: 6.0 → **2.0.0** (Neustart der Versionierung für Plugin)
- Plugin-Verzeichnis: `windturbine_earthwork_calculator_v2/`
- HTML-Report-Footer: V2 → V2.0.0
- Alle Python-Module mit Version 2.0.0 Header

#### Dependencies
- `ezdxf>=1.1.0` - DXF-Parsing
- `requests>=2.28.0` - API-Kommunikation
- `shapely>=2.0.0` - Geometrie-Operationen

#### Dokumentation
- Komplett überarbeitete AGENTS.md
- Plugin-spezifische README.md
- Aktualisierte Projekt-Struktur

---

## [6.0.0] - 2025-11-04

### 🚀 Hauptrelease - Hoehendaten.de API Integration & GeoPackage Output (Legacy)

#### Hinzugefügt
- **Hoehendaten.de API Integration** 🌐
  - Automatischer DEM-Download von hoehendaten.de API
  - Deutschland-weite Abdeckung mit 1m Auflösung
  - Multi-Tile-Support mit automatischem Mosaicking
  - `fetch_dem_tile_from_api()`: Holt einzelne 1×1km Kacheln
  - `create_dem_mosaic_from_tiles()`: Erstellt nahtloses Mosaik aus mehreren Tiles
  - `calculate_tiles_for_radius_points()`: Per-Site Radius-Berechnung (250m um jeden Standort)
  - Boolean Parameter `USE_HOEHENDATEN_API` zum Umschalten
  - Fallback auf manuelles DEM bei Offline/API-Fehler

- **Intelligentes DEM-Caching-System** 💾
  - Persistenter Cache in `~/.qgis3/hoehendaten_cache/tiles/`
  - LRU (Least Recently Used) Eviction-Strategie
  - `load_cache_metadata()`: Lädt Cache-Index mit Zugriffszähler und Zeitstempel
  - `save_cache_metadata()`: Speichert Cache-Index persistent
  - `cleanup_cache_lru()`: Entfernt am wenigsten genutzte Tiles bei Überschreitung
  - Max. 100 Tiles (~500MB) automatische Limits
  - Boolean Parameter `FORCE_DEM_REFRESH` für manuellen Cache-Refresh
  - Wiederverwendung zwischen QGIS-Sessions

- **GeoPackage All-in-One Output** 📦
  - Ein einziges .gpkg für alle Outputs (Raster + Vektoren)
  - `generate_geopackage_path()`: Erstellt Dateinamen aus südwestlichstem Punkt
  - `save_raster_to_geopackage()`: Speichert DEM-Raster mit gdal:translate
  - `save_vector_to_geopackage()`: Fügt Vektorlayer hinzu
  - Automatischer Dateiname: `WKA_{Rechtswert}_{Hochwert}.gpkg`
  - HTML-Report mit gleichem Basisdateinamen daneben
  - Speicherung im aktuellen Arbeitsverzeichnis
  - Enthält: DEM-Raster, Plattformen, Fundamente, Volumen-Daten, Profillinien

- **Umfassender Crash-Schutz** 🛡️
  - Multi-layered Validierung bei API-Antworten
  - Base64-Dekodierungs-Fehlerbehandlung
  - GeoTIFF-Validierung vor GDAL-Operationen
  - Try-Catch für alle Raster-Layer-Erstellungen
  - Detailliertes Logging mit ✓/✗/⚠ Indikatoren

#### Geändert
- Dateiname: `prototype.py` → `WindTurbine_Earthwork_Calculator.py`
- Version: 5.5 → **6.0**
- Parameter `INPUT_DEM` jetzt optional (wenn API aktiviert)
- Output-Parameter entfernt (automatische Generierung)
- Alle temporären Outputs werden in finale GeoPackage kopiert
- DEM-Mosaik wird als Layer in GeoPackage integriert

#### Behoben
- **API-Request-Format**: Korrigierte Header (`Accept-Encoding: gzip`) und Request-Body (`data=json.dumps()` statt `json=`)
- **QGIS-Crash-Prevention**: Umfangreiche Validierung verhindert Abstürze durch ungültige Raster-Daten
- **Cache-Konsistenz**: Metadata wird atomar geschrieben, Locking verhindert Race-Conditions

#### Dependencies
- **NEU**: `requests` library (für API-Kommunikation)
- Bestehende Dependencies: `numpy`, `qgis.core`, `PyQt5`

#### Rückwärtskompatibilität
- ✅ Manueller DEM-Upload weiterhin unterstützt (API optional)
- ✅ Alle v5.5 Features (Polygon-basiert, Geländeschnitte) funktionieren unverändert
- ✅ Bestehende Parameter-Kombinationen kompatibel

---

## [5.5.0] - 2025-10-04

### 🚀 Hauptrelease - Polygon-basierte Berechnungen & Professional Reports

#### Hinzugefügt
- **Beliebige Polygon-Formen für Kranstellflächen**
  - Exakte Volumenberechnung für L-Form, Trapez, Kreis, Freiform
  - `_sample_dem_polygon()`: Universelles DEM-Sampling für beliebige Polygone
  - `_create_slope_polygon()`: Böschungen folgen Polygon-Kontur
  - `_calculate_slope_height()`: Höhen-Interpolation auf Böschung
  - `_calculate_crane_pad_polygon()`: Cut/Fill für beliebige Formen
  - Multi-Polygon und Polygon-mit-Loch Support

- **Polygon-Fundamente** (optional)
  - Neue Parameter: `USE_CIRCULAR_FOUNDATIONS`, `FOUNDATION_POLYGONS`
  - `_calculate_foundation_polygon()`: Fundamente in beliebiger Form
  - `_get_foundation_polygon_for_site()`: Site-ID-basierte Zuordnung
  - Individuelle Tiefe pro Standort (Attribut `depth_m`)
  - Oktagon, Quadrat, Freiform unterstützt

- **Professional HTML-Report**
  - Minimalistisches, funktionales Design
  - Eingangspara meter-Tabelle
  - Gesamt-Übersicht (Cut, Fill, Kosten)
  - Details pro Standort mit Koordinaten (UTM)
  - Geländeschnitt-Integration mit Debug-Info
  - PDF-Export-Button
  - Responsive Design

- **Koordinaten im Report**
  - `coord_x`, `coord_y` im Result-Dict
  - UTM-Koordinaten mit Tausender-Trennung

- **Dokumentation**
  - `INSTALLATION_QGIS.md`: Schritt-für-Schritt-Anleitung
  - Single-File-Deployment (nur prototype.py nötig)

#### Geändert
- `_calculate_foundation()` → `_calculate_foundation_circular()` (umbenannt)
- `_calculate_complete_earthwork()`: Unterstützt jetzt Polygon- und Kreis-Modus
- HTML-Report-Generator komplett überarbeitet (inline integriert)
- Version: 4.0 → **5.5**

#### Behoben
- **CRITICAL**: NumPy boolean subtract Fehler
  - Root Cause: `provider.sample()` Tuple-Reihenfolge falsch
  - Fix in `_sample_dem_polygon()`: `val, ok = provider.sample()` statt `sample_result[0/1]`
  - Fix in `_create_target_dem()`: `slope_elevations.astype(float)`
  - Fix in `_calculate_crane_pad()`: Alle Arrays explizit `dtype=float`
  - Fix in `_optimize_balanced_cutfill()`: `elevations.astype(float)`
  - Kompatibel mit NumPy 1.20+ und 2.0+

- **Geländeschnitt-Dateinamen**
  - Problem: CamelCase vs. lowercase Mismatch
  - Fix: Suche auf lowercase umgestellt (`foundation_ns` statt `Foundation_NS`)

#### Rückwärtskompatibilität
- ✅ Bestehende Punkt-basierte Workflows funktionieren unverändert
- ✅ Kreisförmige Fundamente bleiben DEFAULT
- ✅ Alte Rechteck-Funktionen bleiben für Punkt-Modus erhalten

---

## [5.0.0] - 2025-10-03

### 🚀 Geländeschnitt-Modul

#### Hinzugefügt
- **Automatische Profil-Generierung**
  - 8 Schnitte pro Standort (2 Fundament, 6 Kranfläche)
  - Matplotlib-basierte 2D-Visualisierung
  - PNG-Export mit 300 DPI
  - Konfigurierbare Höhenübertreibung (1.0-5.0x)

- **2-stufiger Workflow**
  - Auto-generierte Schnittlinien ODER
  - Benutzerdefinierte Schnittlinien

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

### Behoben (Sicherheit)
- HTML-Escape in Reports und Dialog-Labels gegen XSS-/SSRF-Vektoren (`project_name`,
  `site_name`, `profile_name`, BGR-`description`)
- `log.config` aus Git-Index entfernt; `log.config.example` als Vorlage ergänzt
- DEM-Downloader: 50-MB-Cap und TIFF-Magic-Byte-Prüfung pro hoehendaten.de-Antwort
- DXF-Importer: 500-MB-Cap, Umstellung auf `ezdxf.recover.readfile`
- DEM-Downloader: Tile-Name-Regex-Guard

### Geplant für v3.0 (siehe `RECHERCHE_2026-05-26.md` und Implementierungspläne unter `docs/plans/`)
- **Constraint-basierte Platzierung** — Buffer um Gebäude/Straßen, automatische Konflikt-Vermeidung, Snap-to-Grid
- **Park-weite Batch-Optimierung** — Material-Transport zwischen Standorten minimieren, Park-Gesamtkostenfunktion
- **Geländeschnittkanten & Differenz-Raster** — vollständige Umsetzung gem. `IMPLEMENTATION_TERRAIN_INTERSECTION.md`
- **3D-Mesh-Export & 3D-Viewer** — OBJ/STL-Export, Cesium-/Three.js-/Qgis2threejs-Anbindung

### Geplant für v3.1+
- Rotationswinkel-Optimierung der Kranstellfläche
- Mass-Haul-Diagramm mit Park-weitem Balancing
- LandXML/IFC-4.3-Export für Machine-Control
- ALKIS-Flurstücks-Layer (WFS)

---

## Legende

- **Hinzugefügt**: Neue Features
- **Geändert**: Änderungen an bestehender Funktionalität
- **Veraltet**: Features, die bald entfernt werden
- **Entfernt**: Entfernte Features
- **Behoben**: Bugfixes
- **Sicherheit**: Sicherheits-Patches

---

[6.0.0]: https://github.com/foe05/Wind-Turbine-Earthwork-Calculator/releases/tag/v6.0.0
[5.5.0]: https://github.com/foe05/Wind-Turbine-Earthwork-Calculator/releases/tag/v5.5.0
[5.0.0]: https://github.com/foe05/Wind-Turbine-Earthwork-Calculator/releases/tag/v5.0.0
[4.0.0]: https://github.com/foe05/Wind-Turbine-Earthwork-Calculator/releases/tag/v4.0.0
[3.0.0]: https://github.com/foe05/Wind-Turbine-Earthwork-Calculator/releases/tag/v3.0.0
[2.0.0]: https://github.com/foe05/Wind-Turbine-Earthwork-Calculator/releases/tag/v2.0.0
[1.0.0]: https://github.com/foe05/Wind-Turbine-Earthwork-Calculator/releases/tag/v1.0.0
