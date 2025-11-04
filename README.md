# 🌬️ Wind Turbine Earthwork Calculator

**Version 6.0** | QGIS Processing Tool für präzise Erdarbeitsberechnungen bei Windkraftanlagen-Standorten

[![QGIS](https://img.shields.io/badge/QGIS-3.0+-green.svg)](https://qgis.org)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Überblick

Der **Wind Turbine Earthwork Calculator** ist ein leistungsstarkes QGIS-Processing-Tool zur Berechnung von Cut/Fill-Volumen, Material-Bilanz und Kosten für Windkraftanlagen-Standorte. Das Tool berücksichtigt:

- 🏗️ **Fundament-Aushub** (Durchmesser, Tiefe, Typ)
- 🏗️ **Kranstellflächen** (Cut/Fill mit Böschungen)
- ♻️ **Material-Wiederverwendung** (Fundament-Aushub → Kranflächen-Auftrag)
- 💰 **Detaillierte Kostenberechnung**
- 📊 **Automatische HTML-Reports** mit PDF-Export
- 🗺️ **Standflächen-Polygon-Export**
- 🔄 **Beliebige Polygon-Formen** (v5.5)
- 📈 **Geländeschnitt-Modul** (v5.0)
- 🌐 **Hoehendaten.de API Integration** (v6.0)
- 💾 **Intelligentes DEM-Caching** (v6.0)
- 📦 **GeoPackage All-in-One Output** (v6.0)

---

## ✨ Features v6.0

### 🆕 NEU: Hoehendaten.de API Integration & GeoPackage Output

- **Automatischer DEM-Download**:
  - Integration mit hoehendaten.de API für deutschlandweite Höhendaten
  - 1m Auflösung für präzise Berechnungen
  - Kein manuelles DEM-Upload nötig
  - Automatische Multi-Tile-Mosaicking
  - Fallback auf manuellen Upload bei Offline/Ausland

- **Intelligentes Caching-System**:
  - Persistent zwischen QGIS-Sessions (~/.qgis3/hoehendaten_cache/)
  - LRU (Least Recently Used) Strategie
  - Per-Site Radius-Berechnung (250m um jeden Standort)
  - Max. 100 Tiles (~500MB) automatische Limits
  - Cache-Metadata mit Zugriffszähler und Zeitstempel
  - Manueller Force-Refresh für Aktualisierungen

- **GeoPackage All-in-One Output**:
  - Ein einziges .gpkg für alle Outputs
  - DEM-Raster als Layer integriert
  - Alle Vektorlayer (Plattformen, Fundamente, Volumen, Profile)
  - HTML-Report mit gleichem Dateinamen daneben
  - Automatischer Dateiname: WKA_{Rechtswert}_{Hochwert}.gpkg
  - Basierend auf südwestlichstem Punkt des Projekts
  - Speicherung im aktuellen Arbeitsverzeichnis

### Features v5.5

### 🆕 NEU: Polygon-basierte Berechnungen

- **Beliebige Kranstellflächen-Formen**:
  - L-Form, Trapez, Kreis, Freiform
  - Exakte Volumen-Berechnung entlang Polygon-Kontur
  - Böschungen folgen der Polygon-Form
  - Multi-Polygon und Polygon-mit-Loch Support

- **Polygon-Fundamente** (optional):
  - Oktagon, Quadrat, beliebige Formen
  - Alternative zu kreisförmigen Fundamenten
  - Site-ID-basierte Zuordnung
  - Individuelle Tiefe pro Standort

### Features v5.0

- **Geländeschnitt-Modul**:
  - 8 automatische Profile pro Standort
  - Matplotlib-basierte Visualisierung
  - PNG-Export (300 DPI)
  - Integration in HTML-Report

### Features v4.0

- **Polygon-Input-Modus**:

- **2-Schritt-Workflow**:
  1. **Generieren**: Punkte → Automatische Rechteck-Polygone (Nord-Süd)
  2. **Anpassen**: Polygone in QGIS rotieren/verschieben
  3. **Neuberechnen**: Angepasste Polygone als Input → Präzise Volumen mit Rotation!

- **Automatische Eigenschafts-Extraktion**:
  - Centroid → WKA-Standort
  - **Oriented Bounding Box (OBB)** → Präzise Plattformmaße
  - Längste Kante → Rotationswinkel
  
- **Rotations-unterstütztes Sampling**:
  - DEM-Sampling berücksichtigt Polygon-Rotation
  - Präzisere Cut/Fill-Berechnung für angepasste Geometrien
  - Beliebige Rotationswinkel (0°-360°)

- **Auto-Rotation-Optimierung** 🤖:
  - Testet automatisch Rotationen 0°-360° (konfigurierbare Schrittweite)
  - Wählt Rotation mit minimalem Cut/Fill-Ungleichgewicht
  - Nur im Punkt-Modus (für erste Iteration)
  - Spart manuelle Optimierung in QGIS!

- **Performance-Optimierungen**:
  - Rotation-Matrix-Caching (30% schneller bei vielen Standorten)
  - Effizientes Numpy-Array-Processing

- **Robuste Validierung**:
  - CRS-Prüfung (muss projiziert sein)
  - Polygon-Größen-Validierung (10-200m)
  - Fehlerbehandlung für ungültige Geometrien

### Features v3.0

### Kern-Funktionalität

- **Präzise Volumenberechnung**:
  - Fundament-Volumen (Flachgründung, Tiefgründung, Pfahlgründung)
  - Kranstellflächen Cut/Fill mit Böschungen
  - DEM-basiertes Sampling mit konfigurierbarer Auflösung

- **Intelligente Optimierung**:
  - 3 Optimierungsmethoden: Mittelwert, Min. Aushub, Ausgeglichen
  - Automatische Plattformhöhen-Optimierung
  - Material-Bilanz mit Überschuss/Mangel-Analyse

- **Material-Management**:
  - Swell-Faktor (Auflockerung): 1.0 - 1.5
  - Compaction-Faktor (Verdichtung): 0.7 - 1.0
  - Bodentyp-Presets (Sand/Kies, Lehm/Ton, Fels)
  - Wiederverwendungs-Logik

- **Kostenmodul** 🆕:
  - Erdaushub (€/m³)
  - Transport/Abtransport (€/m³)
  - Material-Einkauf (€/m³)
  - Schotter-Einbau (€/m³)
  - Verdichtung (€/m³)
  - Einsparungs-Analyse bei Wiederverwendung

- **Polygon-Export** 🆕:
  - Automatische Generierung von Standflächen-Rechtecken
  - Nord-Süd-Ausrichtung
  - Attribute: Länge, Breite, Fläche, Kosten, Volumen
  - Bereit für manuelle Anpassung in QGIS

### Output-Formate

1. **Punkt-Layer (GeoPackage)**:
   - 25+ Attribute pro Standort
   - Volumen, Kosten, Material-Bilanz
   
2. **Polygon-Layer (GeoPackage)** 🆕:
   - Standflächen als editierbare Rechtecke
   - Für Optimierung und Visualisierung

3. **HTML-Report**:
   - Projekt-Parameter-Übersicht
   - Kosten-Dashboard
   - Volumen-Zusammenfassung
   - Details pro Standort
   - Vergleich Mit/Ohne Wiederverwendung

---

## 🚀 Installation

### Voraussetzungen

- **QGIS**: 3.0 oder höher
- **Python**: 3.7+ (in QGIS integriert)
- **Python-Pakete**:
  - `numpy` (normalerweise mit QGIS vorinstalliert)
  - `requests` (für hoehendaten.de API, siehe Installation)

### Installation des Tools

#### Option 1: Über QGIS Processing Toolbox (empfohlen)

1. **Python-Paket installieren** (für API-Integration):
   ```bash
   # In QGIS Python-Konsole (Plugins → Python-Konsole)
   import subprocess
   import sys
   subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
   ```

2. **Script-Datei kopieren**:
   ```bash
   # Linux/Mac
   cp prototype/WindTurbine_Earthwork_Calculator.py ~/.local/share/QGIS/QGIS3/profiles/default/processing/scripts/

   # Windows
   copy prototype\WindTurbine_Earthwork_Calculator.py %APPDATA%\QGIS\QGIS3\profiles\default\processing\scripts\
   ```

3. **QGIS neu starten** oder Processing Toolbox aktualisieren:
   - Processing → Toolbox → Scripts → Reload Scripts

4. **Tool finden**:
   - Processing Toolbox → Scripts → Windkraft → Wind Turbine Earthwork Calculator v6.0

#### Option 2: Direkt aus Python-Konsole

```python
# In QGIS Python-Konsole
import sys
sys.path.append('/path/to/Wind-Turbine-Earthwork-Calculator/prototype')
from WindTurbine_Earthwork_Calculator import WindTurbineEarthworkCalculatorV3

# Algorithmus registrieren
from qgis.core import QgsApplication
QgsApplication.processingRegistry().addProvider(WindTurbineEarthworkCalculatorV3())
```

---

## 📖 Verwendung

### Zwei Arbeitsweisen

**Option A: Punkt-basiert** (Standard)
- Input: WKA-Standorte als Punkte
- Output: Automatisch generierte Rechteck-Polygone (Nord-Süd)

**Option B: Polygon-basiert** (v4.0 🆕)
- Input: Angepasste Standflächen-Polygone
- Output: Neuberechnete Volumen basierend auf Rotation/Position

### Schritt 1: Input-Daten vorbereiten

**Benötigt**:
- **DEM (Raster)** - OPTIONAL seit v6.0:
  - **NEU**: Automatischer Download via hoehendaten.de API (Deutschland, 1m Auflösung)
  - **Klassisch**: Manuelles DEM (GeoTIFF, etc.) hochladen
  - Empfohlene Auflösung: 1-10m
  - Koordinatensystem: **Projektiert (z.B. UTM)** ⚠️ WICHTIG!

- **WKA-Standorte**:
  - **Punkt-Layer** (Shapefile, GeoPackage, etc.) ODER
  - **Polygon-Layer** (angepasste Standflächen aus vorherigem Lauf)
  - Mindestens 1 Feature
  - Für API-Modus: UTM32N (EPSG:25832) empfohlen
  - **Polygone müssen projiziert sein!**

### Schritt 2: Tool ausführen

1. **Processing Toolbox öffnen**: `Strg+Alt+T`

2. **Tool suchen**: "Wind Turbine" eingeben

3. **Parameter einstellen**:

   **DEM-Quelle** (v6.0 🆕):
   - 🌐 DEM von hoehendaten.de API beziehen: ✓ (Deutschland, 1m Auflösung)
   - 🔄 DEM-Cache aktualisieren: ☐ (nur bei Force-Refresh nötig)
   - Eingabe-DEM: (optional, nur wenn API deaktiviert)

   **Geometrie**:
   - Plattformlänge: z.B. 45m
   - Plattformbreite: z.B. 40m
   - Böschungswinkel: z.B. 34° (1:1.5)
   - Böschungsbreite: z.B. 10m

   **Fundament**:
   - Durchmesser: z.B. 22m
   - Tiefe: z.B. 4m
   - Typ: Flachgründung

   **Material**:
   - Bodenart: Lehm/Ton → setzt automatisch Swell/Compaction
   - Material-Wiederverwendung: ✓ Aktiviert

   **Kosten** (optional):
   - Erdaushub: 8 €/m³
   - Transport: 12 €/m³
   - Material-Einkauf: 15 €/m³
   - Schotter: 25 €/m³
   - Verdichtung: 5 €/m³

   **Outputs** (v6.0 🆕 - Automatisch generiert):
   - 📦 GeoPackage: `WKA_{Rechtswert}_{Hochwert}.gpkg` (automatisch)
   - 📄 HTML-Report: `WKA_{Rechtswert}_{Hochwert}.html` (automatisch)
   - Speicherort: Aktuelles Arbeitsverzeichnis

4. **Run** klicken

### Schritt 3: Ergebnisse analysieren

1. **HTML-Report öffnen** → Überblick über Kosten und Volumen

2. **Volumendaten-Layer prüfen**:
   - Attributtabelle öffnen
   - Nach `cost_total` sortieren → teuerste Standorte zuerst
   - Filtering: z.B. `"material_deficit" > 0` → Standorte mit Mangel

3. **Standflächen anpassen** (v4.0 Workflow 🆕):
   - **Schritt 2a**: Layer `standflaechen.gpkg` bearbeiten (Toggle Editing)
   - **Schritt 2b**: Polygone rotieren/verschieben (z.B. 45° drehen)
   - **Schritt 2c**: Speichern
   - **Schritt 3**: Tool ERNEUT ausführen mit:
     - Input Polygone: `standflaechen.gpkg` ✅
     - Input Punkte: leer lassen oder alte Punkte
   - Siehe [WORKFLOW_STANDFLAECHEN.md](WORKFLOW_STANDFLAECHEN.md)

---

## 📊 Beispiel-Output

### HTML-Report

```
🌬️ Windkraftanlagen - Erdarbeitsberechnung v3.0

📋 Projekt-Parameter:
  Plattform: 45m × 40m (1800m²)
  Fundament: Ø22m, 4m tief (Flachgründung)
  Böschung: 34° | 10m
  Material-Wiederverwendung: ✓ Aktiviert

💰 Kosten-Übersicht:
  Gesamt-Kosten:    123,456 €
  Durchschnitt:      41,152 € (pro WKA)
  💚 Einsparung:     18,234 € (12.8% durch Wiederverwendung)

📊 Volumen-Zusammenfassung:
  Fundamente:        4,562 m³
  Kranflächen Cut:   9,019 m³
  Kranflächen Fill:  7,103 m³
  GESAMT Cut:       13,581 m³
  GESAMT Fill:       7,103 m³
```

### Attribut-Tabelle (Auszug)

| id | cost_total | total_cut | total_fill | material_surplus | material_deficit | saving_pct |
|----|------------|-----------|------------|------------------|------------------|------------|
| 1  | 45,678 €   | 2,300 m³  | 853 m³     | 897 m³           | 0 m³             | 15.3%      |
| 2  | 38,912 €   | 4,534 m³  | 2,412 m³   | 0 m³             | 937 m³           | 8.1%       |
| 3  | 38,866 €   | 6,747 m³  | 4,837 m³   | 0 m³             | 3,789 m³         | 4.2%       |

---

## 🔧 Erweiterte Nutzung

### Python API

```python
from qgis import processing

# Parameter definieren
params = {
    'INPUT_DEM': '/path/to/dem.tif',
    'INPUT_POINTS': '/path/to/standorte.shp',
    'PLATFORM_LENGTH': 45.0,
    'PLATFORM_WIDTH': 40.0,
    'FOUNDATION_DIAMETER': 22.0,
    'FOUNDATION_DEPTH': 4.0,
    'MATERIAL_REUSE': True,
    'COST_EXCAVATION': 8.0,
    'COST_TRANSPORT': 12.0,
    'OUTPUT_POINTS': '/path/to/volumendaten.gpkg',
    'OUTPUT_PLATFORMS': '/path/to/standflaechen.gpkg',
    'OUTPUT_REPORT': '/path/to/report.html'
}

# Ausführen
result = processing.run("script:windturbineearthworkv3", params)
print(f"Report: {result['OUTPUT_REPORT']}")
```

### Batch-Processing

```python
# Mehrere Szenarien durchrechnen
scenarios = [
    {'name': 'Standard', 'FOUNDATION_DEPTH': 4.0, 'MATERIAL_REUSE': True},
    {'name': 'Tief', 'FOUNDATION_DEPTH': 6.0, 'MATERIAL_REUSE': True},
    {'name': 'Ohne_Reuse', 'FOUNDATION_DEPTH': 4.0, 'MATERIAL_REUSE': False},
]

for scenario in scenarios:
    params = base_params.copy()
    params.update(scenario)
    params['OUTPUT_REPORT'] = f'reports/report_{scenario["name"]}.html'
    processing.run("script:windturbineearthworkv3", params)
```

---

## 📐 Methodik

### Volumenberechnung

1. **DEM-Sampling**:
   - Grid-basiertes Sampling im Plattform- und Böschungsbereich
   - Interpolation fehlender Werte

2. **Plattformhöhen-Optimierung**:
   - **Mittelwert**: Durchschnitt aller Geländehöhen
   - **Min. Aushub**: 40. Perzentil (minimiert Cut)
   - **Ausgeglichen**: Iterative Minimierung von |Cut - Fill|

3. **Target-DEM-Erstellung**:
   - Plattform: Konstante Höhe
   - Böschung: Linearer Übergang mit konfigurierbarem Winkel
   - Differenz-DEM: Original - Target

4. **Volumenberechnung**:
   ```
   Cut Volume  = Σ(max(DEM - Target, 0) × Pixel-Fläche)
   Fill Volume = Σ(max(Target - DEM, 0) × Pixel-Fläche)
   ```

### Material-Bilanz

```
Verfügbares Material = (Fundament-Aushub + Kran-Cut) × Swell-Faktor
Benötigtes Material  = Kran-Fill / Compaction-Faktor

IF Verfügbar >= Benötigt:
    Überschuss = Verfügbar - Benötigt → Transport-Kosten
    Wiederverwendet = Benötigt → Verdichtungs-Kosten
ELSE:
    Mangel = Benötigt - Verfügbar → Einkauf + Transport + Verdichtung
    Wiederverwendet = Verfügbar → Verdichtungs-Kosten
```

### Kostenberechnung

**MIT Material-Wiederverwendung**:
```
Kosten = Fundament-Aushub-Kosten
       + Kran-Aushub-Kosten
       + Fundament-Transport-Kosten
       + Überschuss-Transport-Kosten
       + Mangel-Einkaufs-Kosten
       + Wiederverwendungs-Verdichtungs-Kosten
       + Schotter-Kosten
```

**OHNE Material-Wiederverwendung**:
```
Kosten = Fundament-Aushub-Kosten
       + Kran-Aushub-Kosten
       + Gesamt-Abtransport-Kosten
       + Gesamt-Fill-Einkaufs-Kosten
       + Schotter-Kosten
```

**Einsparung** = Kosten(ohne) - Kosten(mit)

---

## 🗺️ Workflow: Standflächen-Optimierung

Siehe detaillierte Anleitung: [WORKFLOW_STANDFLAECHEN.md](prototype/WORKFLOW_STANDFLAECHEN.md)

**Kurzversion**:

1. **Generieren**: Tool mit aktiviertem Polygon-Output ausführen
2. **Anpassen**: Polygone in QGIS rotieren/verschieben (z.B. an Höhenlinien)
3. **Dokumentieren**: Angepasste Geometrie speichern
4. *(v4.0)*: Neuberechnung mit angepassten Polygonen

---

## 🛠️ Entwicklung

### Projekt-Struktur

```
Wind-Turbine-Earthwork-Calculator/
├── prototype/
│   └── WindTurbine_Earthwork_Calculator.py  # Haupt-Processing-Script (v6.0)
│   └── WORKFLOW_STANDFLAECHEN.md            # Workflow-Dokumentation
│   └── installationsanleitung.md            # Installationsanleitung
│   └── INSTALLATION_QGIS.md                 # QGIS-spezifische Installation
├── AGENTS.md                                # Entwickler-Informationen
├── CHANGELOG.md                             # Versions-Historie
├── README.md                                # Diese Datei
├── requirements.txt                         # Python-Dependencies
└── LICENSE                                  # MIT-Lizenz
```

### Beitragen

Pull Requests sind willkommen! Für größere Änderungen bitte zuerst ein Issue öffnen.

**Entwicklungs-Setup**:
```bash
git clone https://github.com/YOURUSERNAME/Wind-Turbine-Earthwork-Calculator.git
cd Wind-Turbine-Earthwork-Calculator
```

Siehe [AGENTS.md](AGENTS.md) für detaillierte Entwickler-Informationen.

---

## 🐛 Bekannte Probleme

- **Große DEMs** (>10.000 × 10.000 Pixel): Kann langsam sein
  - **Workaround**: DEM vorher clippen auf Untersuchungsgebiet

- **CRS-Mismatch**: Tool erwartet Punkte und DEM im gleichen CRS
  - **Workaround**: Vor Ausführung reprojizieren

- **NaN-Werte im DEM**: Werden durch Mittelwert ersetzt
  - **Workaround**: DEM vorher interpolieren (QGIS → Raster → Analysis → Fill NoData)

---

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE) Datei.

---

## 👤 Autor

**Windkraft-Standortplanung**

- GitHub: [@foe05](https://github.com/foe05)
- Projekt: [Wind Turbine Earthwork Calculator](https://github.com/foe05/Wind-Turbine-Earthwork-Calculator)

---

## 🙏 Danksagungen

- **QGIS-Community** für das hervorragende Processing Framework
- **NumPy** für effiziente Array-Operationen
- Alle Tester und Feedback-Geber

---

## 📚 Verwandte Projekte

- [QGIS Processing Scripts](https://docs.qgis.org/latest/en/docs/user_manual/processing/scripts.html)
- [PyQGIS Developer Cookbook](https://docs.qgis.org/latest/en/docs/pyqgis_developer_cookbook/)

---

**⭐ Wenn dieses Tool hilfreich ist, gib dem Projekt einen Stern!**
