# CLAUDE CODE PROMPT: QGIS Processing Plugin für Windkraftanlagen-Erdarbeitsoptimierung

## PROJEKT-ÜBERSICHT

Entwickle ein QGIS Processing Plugin, das die optimale Höhe für eine planare Windkraftanlagen-Standfläche in hügeligem Gelände berechnet. Das Plugin soll Erdaushub und -auftrag minimieren und professionelle Reports mit Geländeschnitten erstellen.

---

## TECHNISCHE ANFORDERUNGEN

### Plugin-Typ & Framework
- **Processing Plugin** (nicht GUI Plugin)
- Nutze QGIS Processing Framework für automatische UI-Generierung
- Ziel-Version: **QGIS LTR (aktuell 3.34+)**
- Programmiersprache: **Python 3**
- Modulare Code-Struktur mit separation of concerns

### Python-Abhängigkeiten
- `ezdxf` - DXF-Import und -Verarbeitung
- `requests` - API-Kommunikation mit hoehendaten.de
- `numpy` - Numerische Berechnungen
- `matplotlib` - Geländeschnitt-Visualisierung
- Standard QGIS-Bibliotheken (qgis.core, qgis.processing)

---

## PLUGIN-FUNKTIONALITÄT

### 1. DXF-IMPORT & POLYGON-ERZEUGUNG

**Input:**
- DXF-Datei mit Linien-Geometrien (LWPOLYLINE-Entitäten)
- Alle Linien auf Layer '0'
- Koordinaten in EPSG:25832
- Linien sind NICHT geschlossen und müssen verbunden werden

**Anforderungen:**
- DXF mit `ezdxf` einlesen
- Alle LWPOLYLINE-Entitäten extrahieren
- Start- und Endpunkte der Polylinien finden
- Polylinien in korrekter Reihenfolge zu geschlossenem Polygon verbinden
- Toleranz für Punktverbindung: 0.01m (konfigurierbar)
- Topologische Validierung des resultierenden Polygons:
  - Keine Selbstüberschneidungen
  - Geschlossen
  - Mindestens 3 Vertices
  - Valides Polygon nach OGC Simple Features

**Output:**
- QgsGeometry Polygon-Objekt
- Speicherung im GeoPackage als Layer "standflaeche"

**Fehlerbehandlung:**
- Warnung bei nicht verbindbaren Linien
- Fehler bei ungültigem/leerem Polygon
- CRS-Validierung (muss EPSG:25832 sein)

---

### 2. HÖHENDATEN-ABRUF VON HOEHENDATEN.DE

**API-Dokumentation:** https://hoehendaten.de/api-rawtifrequest.html

**Anforderungen:**
- Berechne 250m Puffer um Standflächenpolygon-Zentroid
- Ermittle betroffene DGM1-Kacheln (1km x 1km)
- API-Request für RAWTIFF-Daten pro Kachel
- Kachel-Naming-Schema: dgm1_32_{easting}_{northing}_{res}
  - Beispiel: dgm1_32_492_5702_1m
  - easting/northing: gerundete Tausender der Kachelecke
  - res: Auflösung (1m für DGM1)

**API-Spezifikation:**
```
GET https://hoehendaten.de/api/v1/rawtiff/{kachelname}
Response: GeoTIFF-Datei als binary
```

**Caching-Strategie:**
- Cache-Verzeichnis: `~/.qgis3/windturbine_plugin_cache/`
- Cache-Format: `{kachelname}.tif`
- Kein automatisches Cache-Löschen (manuell durch User)
- Optional: Force-Refresh Parameter im Processing Dialog

**Mosaik-Erzeugung:**
- Alle heruntergeladenen Kacheln zu einem Raster-Mosaik zusammenfügen
- GDAL/Processing: `gdal:merge` oder `gdal:buildvirtualraster`
- Output: GeoPackage GPKG Raster-Layer "dem_mosaic"

**Fehlerbehandlung:**
- HTTP-Timeout: 30 Sekunden pro Kachel
- HTTP-Fehler (404, 500): Nutzer informieren, welche Kachel fehlt
- Netzwerkfehler: Klare Fehlermeldung mit Hinweis auf Internet-Verbindung
- CRS-Check: DEM muss EPSG:25832 sein

---

### 3. HÖHENOPTIMIERUNG & ERDMASSENBERECHNUNG

**Ziel:** Finde die optimale Höhe ü.NN der planaren Fläche, bei der am wenigsten Erdmasse bewegt werden muss.

**User-Input-Parameter:**
- `min_height`: Untergrenze Höhe ü.NN (float, Meter)
- `max_height`: Obergrenze Höhe ü.NN (float, Meter)
- `height_step`: Schrittweite für Szenarien (default: 0.1m)

**Berechnungsmethodik (aus Prototyp übernehmen):**

Für jede Höhe h zwischen min_height und max_height in height_step-Schritten:

1. **Sample DEM innerhalb Polygon:**
   - Raster-Werte an allen Pixeln innerhalb des Standflächenpolygons auslesen
   - Pro Pixel: Berechne Höhendifferenz `diff = h - dem_value`

2. **Cut/Fill-Volumen:**
   - Cut (Aushub): Summe aller positiven diff * Pixelfläche
   - Fill (Auftrag): Summe aller negativen diff * Pixelfläche

3. **Böschungsberechnung (aus Prototyp):**
   - Böschungswinkel (konfigurierbar, default: 45°)
   - Böschungsbreite aus Höhendifferenz und Winkel berechnen
   - Böschungsvolumen entlang Polygon-Kontur addieren

4. **Fundament-Volumen (aus Prototyp):**
   - Fundamentdurchmesser (konfigurierbar)
   - Fundamenttiefe (konfigurierbar)
   - Fundamenttyp: Kreisförmig/Oktagon/Quadrat

5. **Material-Bilanz (aus Prototyp):**
   - Swell-Faktor (Auflockerung beim Aushub)
   - Compaction-Faktor (Verdichtung beim Einbau)
   - Material-Wiederverwendung optional
   - Schotter-Schicht-Dicke

6. **Kostenberechnung (aus Prototyp):**
   - Aushub-Kosten (€/m³)
   - Transport-Kosten (€/m³)
   - Material-Einkauf (€/m³)
   - Verdichtung (€/m³)
   - Schotter-Einbau (€/m³)

**Optimierung:**
- Berechne für alle Szenarien: `total_volume_moved = cut_volume + fill_volume`
- Optimum: Szenario mit kleinstem total_volume_moved
- Bei Gleichstand: Bevorzuge Szenario mit kleinerem Netto-Volume (|cut - fill|)

**Output:**
- Optimale Höhe (float, Meter ü.NN)
- Alle Berechnungsergebnisse für Optimum:
  - Cut-Volumen (m³)
  - Fill-Volumen (m³)
  - Böschungs-Volumen (m³)
  - Fundament-Volumen (m³)
  - Material-Überschuss/-Mangel (m³)
  - Gesamtkosten (€)

**Konfigurierbare Parameter (alle aus Prototyp übernehmen):**
- Platform Length/Width (falls nicht aus DXF)
- Foundation Diameter/Depth/Type
- Slope Angle
- Swell Factor
- Compaction Factor
- Material Reuse (Boolean)
- Gravel Thickness
- Cost Parameters (Excavation, Transport, Fill, Compaction, Gravel)

---

### 4. GELÄNDESCHNITTE & VISUALISIERUNG

**Anforderungen:**

**Automatische Schnittlinien-Generierung:**
- 8 radiale Schnittlinien vom Polygon-Zentrum ausgehend
- Gleichmäßig verteilt (alle 45°)
- Länge: Polygon-Radius + 50m
- Speichern als Layer "profile_lines" im GeoPackage

**Option für manuelle Schnittlinien:**
- User kann eigene Linien-Layer als Input übergeben
- Processing-Parameter: `profile_lines` (Optional Vector Layer)

**Schnitt-Erzeugung (pro Schnittlinie):**
1. Sample DEM entlang Linie (Schrittweite: 1m)
2. Erzeuge Profile: Entfernung vs. Höhe
3. Überlagere geplante Plattform-Höhe
4. Zeige Cut/Fill-Bereiche farbcodiert

**Matplotlib-Visualisierung:**
- Diagrammgröße: 10" x 6"
- DPI: 300 (für Druck-Qualität)
- X-Achse: Entfernung entlang Profil (m)
- Y-Achse: Höhe ü.NN (m)
- Höhenübertreibung: Konfigurierbar (1.0 - 5.0x), default: 2.0
- Cut-Bereich: Rot gefüllt
- Fill-Bereich: Grün gefüllt
- Gelände: Schwarze Linie
- Plattform: Blaue horizontale Linie
- Legende & Info-Box mit Volumen

**Output:**
- PNG-Dateien: `profile_001.png`, `profile_002.png`, ...
- Speicherort: Neben GeoPackage oder in separatem Ordner
- Referenz im HTML-Report (siehe unten)

---

### 5. HTML-REPORT-GENERIERUNG

**Report-Inhalt (Struktur aus Prototyp übernehmen):**

1. **Header:**
   - Projekt-Titel
   - Erstellungsdatum
   - Plugin-Version

2. **Projekt-Parameter:**
   - Standort (Koordinaten des Polygon-Zentroids)
   - Plattform-Dimensionen
   - Fundament-Spezifikationen
   - Böschungs-Parameter
   - Material-Faktoren
   - Kostenansätze

3. **Optimierungsergebnis:**
   - Optimale Höhe ü.NN (hervorgehoben)
   - Anzahl berechneter Szenarien
   - Höhenbereich (min/max)

4. **Volumen-Übersicht:**
   - Tabelle mit Cut/Fill/Netto-Volumen
   - Fundament-Volumen
   - Böschungs-Volumen
   - Material-Bilanz (wenn Wiederverwendung aktiviert)

5. **Kosten-Aufschlüsselung:**
   - Tabelle nach Kostenarten
   - Gesamt-Kosten
   - Optional: Vergleich mit/ohne Material-Wiederverwendung

6. **Karte (eingebettet):**
   - Standflächen-Polygon im Maßstab 1:1000
   - Hintergrund: DEM als Hillshade oder farbcodiert
   - Format: PNG, eingebettet als Base64

7. **Geländeschnitte:**
   - Alle PNG-Profile eingebettet (Base64 oder referenziert)
   - Bildunterschrift mit Schnitt-Richtung

**HTML-Styling:**
- Responsive Design (Bootstrap oder einfaches CSS)
- Druckfreundlich (CSS media queries)
- Professionelles Layout wie im Prototyp

**Output:**
- `report.html` neben dem GeoPackage
- Vollständig standalone (alle Bilder eingebettet)

---

## MODULARE CODE-STRUKTUR

Empfohlene Verzeichnis-Struktur:

```
windturbine_optimizer/
│
├── __init__.py                          # Plugin-Initialisierung
├── metadata.txt                         # Plugin-Metadaten
├── icon.png                             # Plugin-Icon
│
├── processing_provider/
│   ├── __init__.py
│   ├── provider.py                      # Processing Provider
│   └── optimize_algorithm.py            # Haupt-Algorithm
│
├── core/
│   ├── __init__.py
│   ├── dxf_importer.py                  # DXF → Polygon Konvertierung
│   ├── dem_downloader.py                # Höhendaten-API & Caching
│   ├── earthwork_calculator.py          # Erdmassen-Berechnungen
│   ├── profile_generator.py             # Geländeschnitt-Erzeugung
│   └── report_generator.py              # HTML-Report
│
├── utils/
│   ├── __init__.py
│   ├── validation.py                    # Input-Validierung
│   ├── geometry_utils.py                # Geometrie-Hilfsfunktionen
│   └── logging_utils.py                 # Logging/Debug-Ausgaben
│
└── tests/                               # Unit-Tests (optional, empfohlen)
    ├── __init__.py
    ├── test_dxf_importer.py
    ├── test_dem_downloader.py
    └── test_earthwork_calculator.py
```

**Modul-Verantwortlichkeiten:**

### `dxf_importer.py`
```python
class DXFImporter:
    def __init__(self, dxf_path, tolerance=0.01):
        """
        Args:
            dxf_path: Pfad zur DXF-Datei
            tolerance: Toleranz für Punkt-Verbindung in Metern
        """
    
    def extract_polylines(self) -> List[List[Tuple[float, float]]]:
        """Extrahiert alle LWPOLYLINE-Koordinaten"""
    
    def connect_polylines(self, polylines) -> List[Tuple[float, float]]:
        """Verbindet Polylinien zu geschlossenem Polygon"""
    
    def to_qgs_polygon(self) -> QgsGeometry:
        """Konvertiert zu QgsGeometry Polygon"""
    
    def validate_polygon(self, polygon: QgsGeometry) -> Tuple[bool, str]:
        """Validiert Polygon-Topologie, returns (is_valid, error_message)"""
```

### `dem_downloader.py`
```python
class DEMDownloader:
    def __init__(self, cache_dir=None, force_refresh=False):
        """
        Args:
            cache_dir: Cache-Verzeichnis für TIFF-Dateien
            force_refresh: Wenn True, ignoriere Cache
        """
    
    def calculate_tiles(self, bbox: QgsRectangle) -> List[str]:
        """Berechnet benötigte Kachelnamen aus Bounding Box"""
    
    def download_tile(self, tile_name: str) -> str:
        """Lädt eine Kachel herunter, returns: Pfad zur TIFF-Datei"""
    
    def create_mosaic(self, tile_paths: List[str], output_path: str) -> str:
        """Erstellt Mosaik aus Kacheln, returns: Pfad zu Mosaik-TIFF"""
    
    def save_to_geopackage(self, raster_path: str, gpkg_path: str, layer_name="dem_mosaic"):
        """Speichert Raster ins GeoPackage"""
```

### `earthwork_calculator.py`
```python
class EarthworkCalculator:
    def __init__(self, dem_layer, polygon, config):
        """
        Args:
            dem_layer: QgsRasterLayer mit DEM
            polygon: QgsGeometry der Standfläche
            config: Dict mit allen Konfigurations-Parametern
        """
    
    def calculate_scenario(self, height: float) -> Dict:
        """
        Berechnet Erdmassen für eine Höhe
        Returns: Dict mit cut_volume, fill_volume, slope_volume, etc.
        """
    
    def find_optimum(self, min_height, max_height, step=0.1) -> Tuple[float, Dict]:
        """
        Findet optimale Höhe
        Returns: (optimal_height, results_dict)
        """
    
    def calculate_costs(self, volumes: Dict) -> Dict:
        """Berechnet Kosten aus Volumina"""
```

### `profile_generator.py`
```python
class ProfileGenerator:
    def __init__(self, dem_layer, polygon, platform_height):
        """
        Args:
            dem_layer: QgsRasterLayer
            polygon: QgsGeometry der Standfläche
            platform_height: Optimale Höhe
        """
    
    def generate_auto_profiles(self, num_profiles=8) -> List[QgsGeometry]:
        """Generiert radiale Schnittlinien"""
    
    def extract_profile_data(self, line: QgsGeometry) -> Tuple[List[float], List[float]]:
        """
        Extrahiert Profil-Daten entlang Linie
        Returns: (distances, elevations)
        """
    
    def plot_profile(self, distances, elevations, output_path, **kwargs) -> str:
        """
        Erstellt Matplotlib-Plot
        Returns: Pfad zur PNG-Datei
        """
```

### `report_generator.py`
```python
class ReportGenerator:
    def __init__(self, results: Dict, polygon, dem_layer, profile_pngs):
        """
        Args:
            results: Optimierungsergebnisse
            polygon: Standflächen-Geometrie
            dem_layer: DEM für Karten-Rendering
            profile_pngs: Liste von Pfaden zu Profil-PNGs
        """
    
    def generate_map(self, scale=1000) -> str:
        """Erstellt Karten-PNG als Base64"""
    
    def generate_html(self, output_path: str):
        """Schreibt vollständigen HTML-Report"""
```

---

## PROCESSING ALGORITHM PARAMETER

Der Haupt-Algorithm (`optimize_algorithm.py`) soll folgende Processing-Parameter haben:

**Inputs:**
1. `INPUT_DXF` (File) - DXF-Datei mit Linien
2. `MIN_HEIGHT` (Number) - Untergrenze Höhe ü.NN
3. `MAX_HEIGHT` (Number) - Obergrenze Höhe ü.NN
4. `HEIGHT_STEP` (Number, default=0.1) - Schrittweite
5. `OUTPUT_GPKG` (File Destination) - Pfad für Output-GeoPackage

**Optional (erweiterte Parameter):**
6. `PROFILE_LINES` (Optional Vector Layer) - Manuelle Schnittlinien
7. `FORCE_REFRESH` (Boolean, default=False) - Cache ignorieren
8. `DXF_TOLERANCE` (Number, default=0.01) - Punkt-Verbindungs-Toleranz

**Fundament-Parameter (aus Prototyp):**
9. `FOUNDATION_DIAMETER` (Number, default=20.0)
10. `FOUNDATION_DEPTH` (Number, default=3.0)
11. `FOUNDATION_TYPE` (Enum: Circular/Octagon/Square)

**Böschungs-Parameter:**
12. `SLOPE_ANGLE` (Number, default=45.0)

**Material-Parameter:**
13. `SWELL_FACTOR` (Number, default=1.25)
14. `COMPACTION_FACTOR` (Number, default=0.9)
15. `MATERIAL_REUSE` (Boolean, default=True)
16. `GRAVEL_THICKNESS` (Number, default=0.5)

**Kosten-Parameter (€/m³):**
17. `COST_EXCAVATION` (Number, default=5.0)
18. `COST_TRANSPORT` (Number, default=8.0)
19. `COST_FILL` (Number, default=12.0)
20. `COST_COMPACTION` (Number, default=3.0)
21. `COST_GRAVEL` (Number, default=25.0)

**Visualisierungs-Parameter:**
22. `HEIGHT_EXAGGERATION` (Number, default=2.0, range=1.0-5.0)
23. `NUM_AUTO_PROFILES` (Number, default=8)

**Outputs:**
- `OUTPUT_POLYGON` (Vector Sink) - Standflächen-Polygon
- `OUTPUT_PROFILES` (Vector Sink) - Schnittlinien
- `OUTPUT_REPORT` (File Destination) - HTML-Report-Pfad

---

## FEHLERBEHANDLUNG & VALIDIERUNG

### Input-Validierungen (vor Hauptberechnung):

1. **DXF-Datei:**
   - Datei existiert und lesbar
   - Enthält LWPOLYLINE-Entitäten
   - Koordinatensystem ist EPSG:25832

2. **Höhen-Parameter:**
   - max_height > min_height
   - height_step > 0
   - Schrittanzahl sinnvoll (<1000 Szenarien)

3. **Polygon:**
   - Valide Geometrie (keine Selbstüberschneidung)
   - Fläche > 0
   - Geschlossen

4. **DEM:**
   - CRS = EPSG:25832
   - Überdeckt Polygon + 250m Puffer
   - Valide Raster-Werte (keine NoData im Polygon)

### Fehler-Meldungen:
- Nutze `QgsProcessingException` für kritische Fehler
- Nutze `feedback.reportError()` für Warnungen
- Nutze `feedback.pushInfo()` für Status-Updates

### Logging (Debug-Modus):
- Optionaler `DEBUG` Parameter (Boolean)
- Wenn aktiviert: Detailliertes Logging nach `~/.qgis3/windturbine_plugin.log`
- Logging-Level: INFO in Produktion, DEBUG in Debug-Modus

---

## FORTSCHRITTS-ANZEIGE

Nutze `feedback.setProgress()` für Prozent-Anzeige:

```python
# Beispiel:
total_steps = 5
feedback.pushInfo("Schritt 1/5: DXF einlesen...")
feedback.setProgress(20)

feedback.pushInfo("Schritt 2/5: Höhendaten herunterladen...")
feedback.setProgress(40)

# etc.
```

**Fortschritts-Verteilung:**
- 10%: DXF-Import
- 30%: DEM-Download (10% pro Kachel, max 40% wenn 4 Kacheln)
- 30%: Höhenoptimierung (gleichmäßig über Szenarien)
- 15%: Geländeschnitte
- 10%: Report-Generierung
- 5%: GeoPackage-Speicherung

---

## BEST PRACTICES & CODE-QUALITÄT

1. **Docstrings:**
   - Alle Funktionen mit Google-Style Docstrings
   - Type-Hints wo möglich

2. **Error-Handling:**
   - Try-Except um externe API-Calls
   - Klare Fehlermeldungen für User

3. **Speicher-Effizienz:**
   - Große Raster-Arrays in Chunks verarbeiten
   - Nicht benötigte Variablen löschen (`del`)

4. **Code-Style:**
   - PEP 8 konform
   - Max Zeilen-Länge: 100 Zeichen
   - Aussagekräftige Variablennamen

5. **Kommentare:**
   - Komplexe Algorithmen erklären
   - TODOs markieren, falls nötig

6. **Testing:**
   - Unit-Tests für Kern-Funktionen
   - Teste mit verschiedenen DXF-Dateien
   - Teste Edge-Cases (leere DXF, fehlendes DEM, etc.)

---

## ZUSÄTZLICHE HINWEISE

### Prototyp-Code-Übernahme:
Der hochgeladene Prototyp (`WindTurbine_Earthwork_Calculator.py`) enthält bereits funktionierenden Code für:
- Erdmassen-Berechnungen
- HTML-Report-Generierung
- Geländeschnitt-Visualisierung
- GeoPackage-Output

**Diese Teile sollen übernommen und in die modulare Struktur integriert werden.**

### DXF-Beispiel-Analyse:
Die hochgeladene DXF-Datei `Kranstellfläche_Marsberg_V172-7_2-175m.dxf` zeigt:
- 42 nicht geschlossene LWPOLYLINE-Entitäten
- Alle auf Layer '0'
- Koordinaten in EPSG:25832
- Typischer Use-Case für das Plugin

**Der DXF-Import muss diese Struktur korrekt verarbeiten können.**

### Performance-Ziele:
- DXF-Import: < 2 Sekunden
- DEM-Download: < 30 Sekunden (pro Kachel)
- Optimierung (100 Szenarien): < 60 Sekunden
- Report-Generierung: < 10 Sekunden

### User-Experience:
- Klare Fortschritts-Meldungen
- Schätzung der verbleibenden Zeit bei langen Prozessen
- Möglichkeit zum Abbrechen (nutze `feedback.isCanceled()`)

---

## DELIVERABLES

Nach Fertigstellung sollte das Plugin folgendes beinhalten:

1. **Vollständiger Plugin-Code** gemäß obiger Struktur
2. **metadata.txt** mit Plugin-Informationen
3. **README.md** mit:
   - Installations-Anleitung
   - Verwendungs-Beispiel
   - Parameter-Erklärung
   - Anforderungen & Abhängigkeiten
4. **requirements.txt** für Python-Abhängigkeiten
5. **Beispiel-DXF-Datei** und erwarteter Output
6. **Optional:** Unit-Tests

---

## BEISPIEL-WORKFLOW (User-Perspektive)

1. User öffnet QGIS und lädt Plugin
2. Navigiert zu Processing Toolbox → Windturbine Optimizer
3. Wählt "Optimize Wind Turbine Platform" Algorithm
4. Gibt Parameter ein:
   - DXF-Datei: `standfläche.dxf`
   - Min Höhe: 300.0 m ü.NN
   - Max Höhe: 310.0 m ü.NN
   - Output: `C:/Projekte/WKA_Marsberg.gpkg`
5. Klickt "Run"
6. Plugin:
   - Liest DXF ein
   - Lädt DEM-Kacheln von hoehendaten.de
   - Berechnet 100 Szenarien (Schritt 0.1m)
   - Findet Optimum bei 305.3 m ü.NN
   - Erstellt 8 Geländeschnitte
   - Generiert HTML-Report
   - Speichert alles in GeoPackage
7. Output:
   - `WKA_Marsberg.gpkg` mit Layern:
     - `standflaeche` (Polygon)
     - `profile_lines` (Lines)
     - `dem_mosaic` (Raster)
   - `report.html` neben GeoPackage
   - 8 PNG-Dateien mit Geländeschnitten

---

## ENTWICKLUNGS-PRIORITÄTEN

**Phase 1 (MVP - Minimum Viable Product):**
1. DXF-Import & Polygon-Erzeugung
2. DEM-Download & Mosaik
3. Basis-Erdmassenberechnung (ohne Böschung/Fundament)
4. Einfacher Text-Output mit optimalem Wert

**Phase 2:**
5. Vollständige Erdmassenberechnung (mit Prototyp-Logik)
6. GeoPackage-Output
7. Basis-HTML-Report

**Phase 3:**
8. Geländeschnitte & Visualisierung
9. Erweiterte Validierungen
10. Debug-Modus & Logging

**Phase 4 (Polish):**
11. Umfassender HTML-Report mit Karten
12. Unit-Tests
13. Dokumentation & Beispiele

---

## KONTAKT BEI FRAGEN

Falls während der Entwicklung Unklarheiten auftreten:
- Prototyp-Code konsultieren
- QGIS PyQGIS Cookbook: https://docs.qgis.org/3.34/en/docs/pyqgis_developer_cookbook/
- ezdxf Dokumentation: https://ezdxf.mozman.at/
- hoehendaten.de API: https://hoehendaten.de/api-rawtifrequest.html

---

**HINWEIS FÜR CLAUDE CODE:**
Dies ist ein umfangreiches Projekt. Beginne mit Phase 1 und erstelle zuerst die Projekt-Struktur mit allen Dateien. Implementiere dann Modul für Modul, teste zwischendurch, und integriere schrittweise die Funktionalität aus dem Prototyp.

Viel Erfolg! 🌬️🏗️
