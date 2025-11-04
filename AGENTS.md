# AGENTS.md - Developer & AI Assistant Guide

**Projekt**: Wind Turbine Earthwork Calculator
**Version**: 6.0 (Hoehendaten.de API Integration & GeoPackage Output)
**Datum**: November 2025
**Zweck**: Informationen für AI-Assistenten (Amp, Cursor, etc.) und Entwickler

---

## 📁 Projekt-Struktur

```
Wind-Turbine-Earthwork-Calculator/
├── prototype/
│   ├── WindTurbine_Earthwork_Calculator.py  # Haupt-QGIS-Processing-Tool (4000+ Zeilen)
│   ├── installationsanleitung.md            # Schritt-für-Schritt Anleitung
│   ├── INSTALLATION_QGIS.md                 # QGIS-spezifische Installation
│   └── WORKFLOW_STANDFLAECHEN.md            # Workflow-Dokumentation
├── AGENTS.md                                # Diese Datei
├── CHANGELOG.md                             # Versions-Historie
├── README.md                                # Projekt-README
├── requirements.txt                         # Python-Dependencies
└── LICENSE                                  # MIT-Lizenz
```

### Haupt-Datei: `prototype/WindTurbine_Earthwork_Calculator.py`

**Typ**: QGIS Processing Algorithm (Python)
**Klasse**: `WindTurbineEarthworkCalculatorV3`
**Framework**: QGIS Processing Framework 3.0+
**Größe**: ~4000 Zeilen (v6.0)

**Kern-Dependencies**:
- `qgis.core.*` - QGIS-API
- `PyQt5.QtCore` - Qt-Framework
- `numpy` - Array-Operationen
- `math` - Mathematische Funktionen
- `requests` - HTTP-API-Kommunikation (v6.0 NEU)
- `json` - JSON-Parsing für API
- `base64` - Base64-Dekodierung für GeoTIFF-Daten

---

## 🔧 Entwicklungs-Umgebung

### QGIS-Umgebung

**Pfade** (wichtig für Tests):
```bash
# Linux
QGIS_SCRIPTS: ~/.local/share/QGIS/QGIS3/profiles/default/processing/scripts/
QGIS_PYTHON:  /usr/share/qgis/python/

# Windows
QGIS_SCRIPTS: %APPDATA%\QGIS\QGIS3\profiles\default\processing\scripts\
QGIS_PYTHON:  C:\Program Files\QGIS 3.x\apps\qgis\python\

# macOS
QGIS_SCRIPTS: ~/Library/Application Support/QGIS/QGIS3/profiles/default/processing/scripts/
```

### Python-Version

**QGIS 3.x**: Python 3.7+ (abhängig von QGIS-Version)
- QGIS 3.34: Python 3.12
- QGIS 3.22: Python 3.9

### Externe Pakete

**Bereits in QGIS enthalten**:
- `numpy` ✓
- `PyQt5` ✓
- `math`, `sys`, `os` ✓ (stdlib)
- `json`, `base64` ✓ (stdlib)

**NEU in v6.0 (muss installiert werden)**:
- `requests` ✓ (für hoehendaten.de API)
  ```bash
  # Installation in QGIS Python
  import subprocess, sys
  subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
  ```

**NICHT verwenden**:
- `pandas` ✗ (nicht standardmäßig in QGIS)
- `scipy` ✗ (nicht standardmäßig in QGIS)
- `matplotlib` ✗ (nur für Plots, nicht im Processing-Tool)

---

## 🏗️ Code-Architektur

### Klassen-Struktur

```python
class WindTurbineEarthworkCalculatorV3(QgsProcessingAlgorithm):
    # Parameter-Konstanten (INPUT_*, OUTPUT_*, etc.)
    
    # === QGIS Processing Framework Methods ===
    def initAlgorithm()          # Parameter-Definitionen
    def processAlgorithm()       # Haupt-Logik
    def name()                   # Tool-ID
    def displayName()            # Tool-Name (UI)
    def group()                  # Gruppen-Name
    def shortHelpString()        # Hilfe-Text
    
    # === Berechnungs-Methoden ===
    def _calculate_complete_earthwork()  # Orchestriert alle Berechnungen
    def _calculate_foundation()          # Fundament-Volumen
    def _calculate_crane_pad()           # Kranflächen Cut/Fill
    def _calculate_material_balance()    # Material-Bilanz
    def _calculate_costs()               # Kosten-Berechnung (NEU v3.0)
    
    # === DEM-Verarbeitung ===
    def _sample_dem_grid()               # DEM-Daten extrahieren
    def _create_platform_mask()          # Plattform-Maske
    def _create_slope_mask()             # Böschungs-Maske
    def _create_target_dem()             # Ziel-DEM (Soll-Zustand)
    def _optimize_balanced_cutfill()     # Cut/Fill-Optimierung

    # === API-Integration (NEU v6.0) ===
    def fetch_dem_tile_from_api()        # Lädt 1×1km Kachel von hoehendaten.de
    def calculate_tiles_for_radius_points()  # Berechnet benötigte Tiles (250m Radius)
    def create_dem_mosaic_from_tiles()   # Erstellt Mosaik aus mehreren Tiles

    # === Caching-System (NEU v6.0) ===
    def get_cache_directory()            # Gibt Cache-Pfad zurück
    def load_cache_metadata()            # Lädt Cache-Index (JSON)
    def save_cache_metadata()            # Speichert Cache-Index
    def cleanup_cache_lru()              # Entfernt alte Tiles (LRU)

    # === GeoPackage-Output (NEU v6.0) ===
    def get_southwest_point_from_features()  # Findet südwestlichsten Punkt
    def generate_geopackage_path()       # Generiert WKA_{X}_{Y}.gpkg Pfad
    def save_raster_to_geopackage()      # Speichert Raster in GPKG
    def save_vector_to_geopackage()      # Speichert Vektor in GPKG

    # === Output-Erzeugung ===
    def _create_output_fields()          # Punkt-Layer-Felder
    def _create_platform_fields()        # Polygon-Layer-Felder (NEU v3.0)
    def _create_output_feature()         # Punkt-Feature erzeugen
    def _create_platform_polygon()       # Rechteck-Polygon erzeugen (NEU v3.0)
    def _create_html_report()            # HTML-Report generieren
    def _log_result()                    # Console-Output
```

### Datenfluss

```
Input:
  - DEM (Raster)
  - Points (Vector)
  - Parameter (Doubles, Enums, Booleans)
    ↓
1. processAlgorithm()
    ↓
2. Loop über alle Punkte
    ├─→ _calculate_foundation()        → foundation_result
    ├─→ _calculate_crane_pad()         → crane_result
    │    ├─→ _sample_dem_grid()
    │    ├─→ _optimize_balanced_cutfill()
    │    └─→ _create_target_dem()
    ├─→ _calculate_material_balance()  → material_balance
    └─→ _calculate_costs()             → cost_result
    ↓
3. Feature-Erstellung
    ├─→ _create_output_feature()       → Punkt-Feature
    └─→ _create_platform_polygon()     → Polygon-Feature (optional)
    ↓
4. Report-Generierung
    └─→ _create_html_report()          → HTML-Datei
    ↓
Output:
  - Volumendaten.gpkg (Punkte)
  - Standflaechen.gpkg (Polygone, optional)
  - Report.html
```

---

## 🧪 Testing

### Manuelle Tests in QGIS

**Setup**:
1. Testdaten vorbereiten:
   ```
   test_data/
   ├── dem_test.tif           # Klein (500×500), UTM
   └── wka_standorte.shp      # 3 Punkte
   ```

2. Script nach QGIS kopieren:
   ```bash
   cp prototype/prototype.py ~/.local/share/QGIS/QGIS3/profiles/default/processing/scripts/
   ```

3. QGIS öffnen → Processing Toolbox → Reload Scripts

4. Tool ausführen mit Test-Parametern

**Test-Checkliste**:
- [ ] Tool erscheint in Processing Toolbox
- [ ] Alle Parameter werden korrekt angezeigt
- [ ] Berechnung läuft ohne Fehler durch
- [ ] Punkt-Output hat alle Attribute gefüllt
- [ ] Polygon-Output (falls aktiviert) hat korrekte Geometrie
- [ ] HTML-Report öffnet und zeigt Daten an
- [ ] Console-Log zeigt Kosten korrekt formatiert

### Python-Console-Tests

```python
# In QGIS Python-Console
from prototype import WindTurbineEarthworkCalculatorV3

# Instanz erstellen
alg = WindTurbineEarthworkCalculatorV3()

# Test-Parameter
params = {
    'INPUT_DEM': '/path/to/test_dem.tif',
    'INPUT_POINTS': '/path/to/test_points.shp',
    'PLATFORM_LENGTH': 45.0,
    'PLATFORM_WIDTH': 40.0,
    'FOUNDATION_DIAMETER': 22.0,
    'FOUNDATION_DEPTH': 4.0,
    'FOUNDATION_TYPE': 0,
    'MATERIAL_REUSE': True,
    'COST_EXCAVATION': 8.0,
    'OUTPUT_POINTS': '/tmp/test_output.gpkg',
    'OUTPUT_REPORT': '/tmp/test_report.html'
}

# Ausführen
import processing
result = processing.run("script:windturbineearthworkv3", params)
print(result)
```

### Unit-Tests (TODO)

**Geplant für v3.1**:
```python
# tests/test_calculations.py
import unittest
from prototype import WindTurbineEarthworkCalculatorV3

class TestEarthworkCalculations(unittest.TestCase):
    def test_foundation_volume_flat(self):
        # Test Flachgründung
        pass
    
    def test_material_balance_surplus(self):
        # Test Überschuss-Szenario
        pass
    
    def test_cost_calculation_with_reuse(self):
        # Test Kosten mit Wiederverwendung
        pass
```

---

## 🎨 Code-Konventionen

### Python-Stil

**Befolge**:
- PEP 8 (mit QGIS-spezifischen Abweichungen)
- 4 Spaces für Indentation
- Max. Zeilenlänge: ~100 Zeichen (flexibel für QGIS-API-Calls)
- Deutsche Variablennamen für Domain-Logik OK (z.B. `kosten_aushub`)

**Naming**:
```python
# Klassen: CamelCase
class WindTurbineEarthworkCalculatorV3

# Methoden (public): snake_case
def processAlgorithm()           # QGIS-Framework (Ausnahme)
def displayName()                # QGIS-Framework (Ausnahme)

# Methoden (private): _snake_case
def _calculate_foundation()
def _create_output_feature()

# Variablen: snake_case
platform_length = 45.0
foundation_volume = 1234.5

# Konstanten: UPPER_SNAKE_CASE
INPUT_DEM = 'INPUT_DEM'
MAX_SLOPE = 5.0
```

**Docstrings**:
```python
def _calculate_costs(self, foundation_volume, crane_cut, ...):
    """
    Berechnet detaillierte Kosten für Erdarbeiten
    
    Args:
        foundation_volume: Fundament-Aushubvolumen (m³)
        crane_cut: Kranflächen-Aushub (m³)
        ...
    
    Returns:
        Dict mit allen Kosten-Komponenten
        
    Beispiel:
        >>> result = _calculate_costs(1000, 500, ...)
        >>> print(result['cost_total'])
        45678.50
    """
```

### QGIS-spezifische Patterns

**Parameter-Definition**:
```python
self.addParameter(QgsProcessingParameterNumber(
    self.PARAMETER_NAME,              # Konstante
    self.tr('Display Name'),          # Übersetzbar
    type=QgsProcessingParameterNumber.Double,
    defaultValue=10.0,
    minValue=0.0,
    maxValue=100.0
))
```

**Feature-Erstellung**:
```python
feature = QgsFeature()
feature.setGeometry(QgsGeometry.fromPointXY(point))
feature.setFields(fields)
feature.setAttribute('name', value)
sink.addFeature(feature)
```

**Error-Handling**:
```python
if condition_failed:
    raise QgsProcessingException('Beschreibende Fehlermeldung')
```

---

## 🐛 Debugging

### QGIS Python-Console

**Fehler tracen**:
```python
import traceback
try:
    processing.run("script:windturbineearthworkv3", params)
except Exception as e:
    print(traceback.format_exc())
```

**Variable inspizieren**:
```python
# In _calculate_costs() einfügen:
print(f"DEBUG: foundation_volume = {foundation_volume}")
print(f"DEBUG: material_balance = {material_balance}")
```

### Log-Dateien

**QGIS Log-Panel**:
- View → Panels → Log Messages (Strg+5)
- Alle `feedback.pushInfo()` erscheinen hier

**Python stderr**:
```bash
# QGIS von Terminal starten, um stderr zu sehen
qgis
```

### Häufige Fehler

**1. AttributeError: 'NoneType' object has no attribute 'get'**
```python
# Problem:
value = result.get('key')  # result ist None

# Lösung:
value = result.get('key', default_value) if result else default_value
```

**2. Feature schreiben schlägt fehl: "Could not convert value"**
```python
# Problem:
feature.setAttribute('field', None)  # None wird nicht konvertiert

# Lösung:
def safe_get(key, default=0.0):
    value = result.get(key, default)
    if value is None or value == '':
        return default
    return float(value)
```

**3. DEM sampling gibt NaN**
```python
# Problem:
dem_data[i, j] = elevation  # elevation ist None

# Lösung:
dem_data[i, j] = float(elevation) if elevation is not None else np.nan
# Später: np.nanmean() verwenden
```

---

## 📝 Änderungen machen

### Neue Feature hinzufügen

**1. Parameter hinzufügen**:
```python
# In initAlgorithm()
self.addParameter(QgsProcessingParameterNumber(
    self.NEW_PARAMETER, self.tr('New Parameter'),
    defaultValue=10.0))

# Konstante oben definieren
NEW_PARAMETER = 'NEW_PARAMETER'
```

**2. In processAlgorithm() auslesen**:
```python
new_value = self.parameterAsDouble(parameters, self.NEW_PARAMETER, context)
```

**3. An Berechnungs-Methode übergeben**:
```python
result = self._calculate_something(..., new_value)
```

**4. In HTML-Report anzeigen** (optional):
```python
html += f"<li>New Parameter: {new_value}</li>"
```

### Neue Berechnungs-Methode

**Template**:
```python
def _calculate_new_feature(self, input_param1, input_param2):
    """
    Beschreibung
    
    Args:
        input_param1: Beschreibung
        input_param2: Beschreibung
    
    Returns:
        Dict mit Ergebnissen
    """
    # Berechnung
    result_value = input_param1 * input_param2
    
    return {
        'result': round(result_value, 2)
    }
```

### HTML-Report erweitern

**Wichtig**: F-Strings verwenden!
```python
# FALSCH (wird nicht interpoliert):
html += """
<td>{variable}</td>
"""

# RICHTIG:
html += f"""
<td>{variable}</td>
"""
```

**Neuer Abschnitt**:
```python
html += f"""
<h2>🆕 Neue Sektion</h2>
<table>
    <tr>
        <th>Name</th>
        <th>Wert</th>
    </tr>
    <tr>
        <td>Parameter 1</td>
        <td>{param1:.2f}</td>
    </tr>
</table>
"""
```

---

## 🚀 Build & Deploy

### Deployment nach QGIS

**Manuell**:
```bash
# Datei kopieren
cp prototype/prototype.py ~/.local/share/QGIS/QGIS3/profiles/default/processing/scripts/

# QGIS reload
# In QGIS: Processing → Toolbox → Reload Scripts
```

**Automatisch** (Linux/Mac):
```bash
# install.sh erstellen
#!/bin/bash
QGIS_SCRIPTS="$HOME/.local/share/QGIS/QGIS3/profiles/default/processing/scripts"
mkdir -p "$QGIS_SCRIPTS"
cp prototype/prototype.py "$QGIS_SCRIPTS/"
echo "✅ Script installed to $QGIS_SCRIPTS"
```

### Version-Bumping

**1. In Code aktualisieren**:
```python
# WindTurbine_Earthwork_Calculator.py Zeile 1-46
VERSION: 6.0 (hoehendaten.de API Integration & GeoPackage Output)
DATUM: November 2025
```

**2. README.md aktualisieren**:
```markdown
**Version 6.0** | QGIS Processing Tool
```

**3. CHANGELOG.md aktualisieren**:
```markdown
## [6.0.0] - 2025-11-04
### Hinzugefügt
- Hoehendaten.de API Integration
- DEM-Caching-System
- GeoPackage Output
```

**4. Git Tag**:
```bash
git tag -a v6.0 -m "Version 6.0: Hoehendaten.de API Integration & GeoPackage Output"
git push origin v6.0
```

---

## 📚 Wichtige QGIS-API-Referenzen

**Processing Framework**:
- https://docs.qgis.org/latest/en/docs/user_manual/processing/scripts.html
- https://qgis.org/pyqgis/latest/core/QgsProcessingAlgorithm.html

**Geometrie**:
- https://qgis.org/pyqgis/latest/core/QgsGeometry.html
- https://qgis.org/pyqgis/latest/core/QgsPointXY.html

**Raster**:
- https://qgis.org/pyqgis/latest/core/QgsRasterLayer.html
- https://qgis.org/pyqgis/latest/core/QgsRasterDataProvider.html

**Features & Fields**:
- https://qgis.org/pyqgis/latest/core/QgsFeature.html
- https://qgis.org/pyqgis/latest/core/QgsFields.html

---

## 🔮 Zukünftige Features (v7.0+)

### Erweiterte Caching-Strategien

**Geplante Verbesserungen**:
- Automatische Cache-Vorwärmung basierend auf Projekt-Historie
- Shared Cache zwischen mehreren Nutzern (Netzwerk-Share)
- Differentielle Updates (nur neue/geänderte Standorte)
- Cache-Statistiken im Report (Hit-Rate, Speichernutzung)

### Multi-Provider DEM-Support

**Konzept**: Unterstützung weiterer DEM-APIs
- OpenTopography API (international)
- NASA SRTM (weltweit, 30m)
- Copernicus DEM (EU, 30m)
- Automatische Provider-Auswahl basierend auf Koordinaten

### Polygon-Input-Modus (bereits in v4.0 teilweise implementiert)

**Geplante Änderungen**:

```python
# Neuer Parameter
self.addParameter(QgsProcessingParameterFeatureSource(
    self.INPUT_POLYGONS, 
    self.tr('WKA-Standflächen (Polygone)'),
    [QgsProcessing.TypeVectorPolygon], 
    optional=True
))

# Neue Logik in processAlgorithm()
if polygon_input_provided:
    for polygon_feature in polygon_source.getFeatures():
        # Centroid extrahieren
        centroid = polygon_feature.geometry().centroid().asPoint()
        
        # Bounding Box für Maße
        bbox = polygon_feature.geometry().boundingBox()
        platform_length = bbox.height()
        platform_width = bbox.width()
        
        # Rotation ermitteln
        rotation_angle = calculate_polygon_rotation(polygon_feature)
        
        # DEM mit Rotation sampeln
        result = _calculate_with_rotation(
            centroid, platform_length, platform_width, rotation_angle)
```

### Auto-Optimierung

**Konzept**: Verschiedene Rotationswinkel testen
```python
def _optimize_platform_rotation(self, dem_layer, point, length, width):
    """
    Testet Rotationen 0° - 345° (alle 15°)
    Gibt Rotation mit minimalem |Cut - Fill| zurück
    """
    best_rotation = 0
    best_balance = float('inf')
    
    for angle in range(0, 360, 15):
        result = self._calculate_crane_pad_rotated(
            dem_layer, point, length, width, angle)
        
        balance = abs(result['total_cut'] - result['total_fill'])
        if balance < best_balance:
            best_balance = balance
            best_rotation = angle
    
    return best_rotation
```

---

## ❓ FAQ für AI-Assistenten

**Q: Wie füge ich einen neuen Output-Parameter hinzu?**  
A: Siehe "Änderungen machen" → Output in `initAlgorithm()` definieren, in `processAlgorithm()` `parameterAsSink()` aufrufen, Sink befüllen, in Return-Dict aufnehmen.

**Q: Warum schlagen Feature-Writes fehl mit "conversion error"?**  
A: Alle Attribute müssen korrekte Datentypen haben. Nutze `safe_get()` Funktion für robuste Konvertierung zu Float/Int.

**Q: Wie teste ich das Tool ohne QGIS-GUI?**  
A: Mit `processing.run()` in Python-Console oder externem Script. Braucht trotzdem QGIS-Installation.

**Q: Wo finde ich QGIS-Logs?**  
A: View → Panels → Log Messages (Strg+5) in QGIS. Oder Terminal-Output wenn QGIS von Kommandozeile gestartet.

**Q: Wie formatiere ich HTML richtig mit Variablen?**  
A: IMMER f-Strings verwenden: `html += f"<td>{variable}</td>"` statt `html += "<td>{variable}</td>"`

**Q: Kann ich Pandas/Scipy verwenden?**  
A: Nein, nicht standardmäßig in QGIS. Nur NumPy ist sicher verfügbar.

---

## 📞 Support

**Für AI-Assistenten**: Diese Datei enthält alle notwendigen Informationen für Code-Änderungen.

**Für Menschen**:
- Issues: GitHub Issue Tracker
- Diskussionen: GitHub Discussions

---

**Letzte Aktualisierung**: November 2025
**Version dieses Dokuments**: 2.0 (v6.0 Release)
