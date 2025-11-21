# AGENTS.md - Developer & AI Assistant Guide

**Projekt**: Wind Turbine Earthwork Calculator
**Version**: 2.0.0
**Datum**: November 2025
**Zweck**: Informationen für AI-Assistenten (Amp, Cursor, etc.) und Entwickler

---

## 📁 Projekt-Struktur

```
Wind-Turbine-Earthwork-Calculator/
├── windturbine_earthwork_calculator_v2/   # QGIS Plugin (Haupt-Komponente)
│   ├── __init__.py                        # Plugin Entry Point
│   ├── plugin.py                          # Plugin-Hauptklasse
│   ├── metadata.txt                       # QGIS Plugin Metadata
│   ├── install_dependencies.py            # Dependency Installer
│   ├── requirements.txt                   # Python Dependencies
│   ├── README.md                          # Plugin Documentation
│   ├── core/                              # Kern-Module
│   │   ├── dxf_importer.py               # DXF Import
│   │   ├── dem_downloader.py             # hoehendaten.de API
│   │   ├── earthwork_calculator.py       # Volumenberechnung
│   │   ├── multi_surface_calculator.py   # Multi-Flächen-Berechnung
│   │   ├── profile_generator.py          # Geländeschnitte
│   │   ├── report_generator.py           # HTML-Report
│   │   ├── workflow_runner.py            # Workflow-Orchestrierung
│   │   ├── surface_types.py              # Datenstrukturen
│   │   └── surface_validators.py         # Validierung
│   ├── gui/                              # GUI-Komponenten
│   │   └── main_dialog.py                # Tab-basierter Dialog
│   ├── processing_provider/              # QGIS Processing
│   │   ├── provider.py                   # Processing Provider
│   │   └── optimize_algorithm.py         # Haupt-Algorithmus
│   ├── utils/                            # Hilfsfunktionen
│   │   ├── geometry_utils.py             # Geometrie-Helfer
│   │   └── logging_utils.py              # Logging
│   └── tests/                            # Tests
│       └── test_multi_param_optimization.py
├── webapp/                               # Web-Anwendung (Microservices)
│   ├── docker-compose.yml                # Docker Orchestrierung
│   ├── services/                         # Microservices
│   │   ├── api_gateway/                  # API Gateway
│   │   ├── auth_service/                 # Authentifizierung
│   │   ├── dem_service/                  # DEM-Daten
│   │   ├── calculation_service/          # Berechnungen
│   │   ├── cost_service/                 # Kostenberechnung
│   │   └── report_service/               # Report-Generierung
│   └── frontend/                         # React Frontend
├── prototype/                            # Legacy (veraltet)
├── AGENTS.md                             # Diese Datei
├── CHANGELOG.md                          # Versions-Historie
├── README.md                             # Projekt-README
└── LICENSE                               # MIT-Lizenz
```

---

## 🔌 QGIS Plugin (Haupt-Komponente)

### Übersicht

Das QGIS Plugin ist ein vollständiges Processing-Plugin mit:
- DXF-Import für Kranstellflächen
- automatischem DEM-Download von hoehendaten.de
- Höhenoptimierung zur Minimierung der Erdbewegungen
- Geländeschnitt-Generierung
- professionellen HTML-Reports

### Installation

```bash
# Linux
cp -r windturbine_earthwork_calculator_v2 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/

# Windows
# Copy to: %APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\

# Dependencies installieren
cd windturbine_earthwork_calculator_v2
python install_dependencies.py
```

### Kern-Dependencies

**Bereits in QGIS enthalten**:
- `numpy` ✓
- `PyQt5` ✓
- `matplotlib` ✓
- `GDAL/OGR` ✓

**Zusätzlich erforderlich**:
- `ezdxf>=1.1.0` - DXF-Parsing
- `requests>=2.28.0` - API-Kommunikation
- `shapely>=2.0.0` - Geometrie-Operationen

### Architektur

```python
# Modularer Aufbau
windturbine_earthwork_calculator_v2/
├── core/                    # Business Logic (keine QGIS-Dependencies)
│   ├── dxf_importer.py     # Liest DXF, gibt Polygon zurück
│   ├── dem_downloader.py   # Holt DEM von API, cached lokal
│   ├── earthwork_calculator.py  # Berechnet Cut/Fill
│   └── report_generator.py # Generiert HTML
│
├── processing_provider/     # QGIS-Integration
│   └── optimize_algorithm.py  # QgsProcessingAlgorithm
│
└── gui/                     # UI-Komponenten
    └── main_dialog.py       # Multi-Tab Dialog
```

### Datenfluss

```
1. DXF-Import
   └─→ dxf_importer.py → QgsGeometry (Polygon)

2. DEM-Download
   └─→ dem_downloader.py → QgsRasterLayer

3. Höhen-Optimierung
   └─→ earthwork_calculator.py → Dict mit Ergebnissen
       - optimal_height
       - total_cut, total_fill
       - terrain_min, terrain_max

4. Profil-Generierung
   └─→ profile_generator.py → List[PNG-Pfade]

5. Report-Generierung
   └─→ report_generator.py → HTML-Datei
```

---

## 🌐 Web-Anwendung

### Übersicht

6 FastAPI Microservices + React Frontend, orchestriert mit Docker Compose.

### Services

| Service | Port | Funktion |
|---------|------|----------|
| api_gateway | 8000 | Routing, Rate-Limiting |
| auth_service | 8001 | JWT-Authentifizierung |
| dem_service | 8002 | DEM-Daten & Caching |
| calculation_service | 8003 | Erdmassenberechnung |
| cost_service | 8004 | Kostenberechnung |
| report_service | 8005 | PDF/HTML-Reports |
| frontend | 3000 | React Web-UI |

### Starten

```bash
cd webapp
docker-compose up -d
```

---

## 🔧 Entwicklung

### Python-Version

- **QGIS 3.34 LTR**: Python 3.12
- **Webapp**: Python 3.11+

### Code-Konventionen

**Python-Stil**:
- PEP 8 (mit QGIS-Ausnahmen für camelCase)
- 4 Spaces Indentation
- Type Hints verwenden
- Deutsche Variablennamen für Fachbegriffe OK

**Naming**:
```python
# Klassen: CamelCase
class EarthworkCalculator

# Methoden: snake_case
def calculate_volumes()

# Private: _snake_case
def _sample_dem_grid()

# Konstanten: UPPER_SNAKE_CASE
DEFAULT_SLOPE_ANGLE = 45.0
```

### Debugging

**QGIS Logs**:
- View → Panels → Log Messages (Strg+5)
- Plugin-Logs: `~/.qgis3/windturbine_calculator_v2/*.log`

**Python Console**:
```python
import traceback
try:
    processing.run("windturbine:optimize_platform_height", params)
except Exception as e:
    print(traceback.format_exc())
```

---

## 🧪 Testing

### Plugin Tests

```bash
cd windturbine_earthwork_calculator_v2
python -m pytest tests/
```

### Manuelle Tests

1. Plugin in QGIS aktivieren
2. Processing Toolbox öffnen
3. "Wind Turbine Earthwork Calculator V2" finden
4. "Optimize Platform Height" ausführen

**Test-Checkliste**:
- [ ] Plugin erscheint in Processing Toolbox
- [ ] DXF-Import funktioniert
- [ ] DEM wird heruntergeladen
- [ ] Optimierung läuft durch
- [ ] HTML-Report wird generiert
- [ ] GeoPackage enthält alle Layer

---

## 📝 Änderungen machen

### Neue Berechnung hinzufügen

1. **Core-Modul erstellen/erweitern**:
```python
# core/new_calculator.py
def calculate_new_feature(polygon, dem_layer):
    """Berechnet neue Feature."""
    # Implementierung
    return {'result': value}
```

2. **In Workflow integrieren**:
```python
# core/workflow_runner.py
from .new_calculator import calculate_new_feature
# In run_workflow() aufrufen
```

3. **In Report anzeigen**:
```python
# core/report_generator.py
# In _generate_results() HTML hinzufügen
```

### Parameter zum Algorithmus hinzufügen

```python
# processing_provider/optimize_algorithm.py

# 1. Konstante definieren
NEW_PARAM = 'NEW_PARAM'

# 2. In initAlgorithm()
self.addParameter(QgsProcessingParameterNumber(
    self.NEW_PARAM,
    self.tr('Neuer Parameter'),
    type=QgsProcessingParameterNumber.Double,
    defaultValue=10.0
))

# 3. In processAlgorithm() auslesen
new_value = self.parameterAsDouble(parameters, self.NEW_PARAM, context)
```

---

## 🚀 Release

### Version-Bumping

1. **metadata.txt** aktualisieren:
```ini
version=2.0.0
changelog=Version 2.0.0 (2025-11-21)
```

2. **Alle Python-Dateien** mit `Version: X.X.X` aktualisieren

3. **CHANGELOG.md** aktualisieren

4. **Git Tag**:
```bash
git tag -a v2.0.0 -m "Version 2.0.0"
git push origin v2.0.0
```

---

## 📚 Referenzen

### QGIS

- [Processing Scripts](https://docs.qgis.org/latest/en/docs/user_manual/processing/scripts.html)
- [PyQGIS API](https://qgis.org/pyqgis/latest/)
- [Plugin Development](https://docs.qgis.org/latest/en/docs/pyqgis_developer_cookbook/)

### APIs

- [hoehendaten.de API](https://hoehendaten.de/api-rawtifrequest.html)

---

## ❓ FAQ

**Q: Wie füge ich eine neue Flächenart hinzu?**
A: In `core/surface_types.py` neuen `SurfaceType` definieren, in `multi_surface_calculator.py` Berechnung implementieren.

**Q: Wo werden DEM-Kacheln gecached?**
A: `~/.qgis3/windturbine_calculator_v2/dem_cache/`

**Q: Wie teste ich ohne echte DEM-Daten?**
A: Mit den Unit-Tests in `tests/` die Mock-Daten verwenden.

**Q: Kann ich ezdxf durch eine andere Library ersetzen?**
A: Ja, nur `dxf_importer.py` muss angepasst werden. Die anderen Module sind unabhängig.

---

## 📞 Support

**Für AI-Assistenten**: Diese Datei enthält alle notwendigen Informationen für Code-Änderungen.

**Für Menschen**:
- Issues: GitHub Issue Tracker
- Diskussionen: GitHub Discussions

---

**Letzte Aktualisierung**: November 2025
**Version dieses Dokuments**: 2.0.0
