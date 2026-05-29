# AGENTS.md - Developer & AI Assistant Guide

**Projekt**: Wind Turbine Earthwork Calculator
**Version**: 2.0.0 (Plugin); v3.0 in Arbeit
**Datum**: Mai 2026
**Zweck**: Informationen für AI-Assistenten (Amp, Cursor, Claude Code, etc.) und Entwickler

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
│   ├── log.config.example                 # Telemetry-API-Key-Template (echte log.config ist gitignored)
│   ├── core/                              # Kern-Module (QGIS-Logik + algorithmische Module)
│   │   ├── dxf_importer.py               # DXF Import (ezdxf + recover-Mode + 500 MB Cap)
│   │   ├── dem_downloader.py             # hoehendaten.de API + 50 MB/Tile Cap + Magic-Byte-Check
│   │   ├── earthwork_calculator.py       # Volumenberechnung (single-surface)
│   │   ├── multi_surface_calculator.py   # Multi-Flächen-Berechnung + Parallelisierung
│   │   ├── multi_site_report_generator.py # HTML/PDF/Excel-Report über mehrere WEA-Standorte
│   │   ├── profile_generator.py          # Geländeschnitte als PNGs
│   │   ├── report_generator.py           # HTML-Einzelstandort-Report (mit HTML-Escape)
│   │   ├── workflow_runner.py            # Workflow-Orchestrierung
│   │   ├── site_aggregator.py            # Multi-Site-Aggregation für Reports
│   │   ├── site_data.py                  # Standort-Datenmodelle
│   │   ├── soil_stabilization_calculator.py # Bodenstabilisierungs-Berechnung
│   │   ├── surface_types.py              # Datenstrukturen (alle Flächen + Schnittkanten)
│   │   ├── surface_validators.py         # Validierung
│   │   ├── bgr_soil_api.py               # BGR-Bodendaten-WFS-Client
│   │   ├── uncertainty.py                # Unsicherheitsanalyse (Sobol etc.)
│   │   ├── uncertainty_visualizations.py # Plots für Unsicherheits-Reports
│   │   ├── placement_constraints.py      # ⭐ v3: Constraint-Validator + Snap-to-Grid (shapely)
│   │   ├── park_optimizer.py             # ⭐ v3: Park-weite Transport-Optimierung (scipy.linprog)
│   │   └── mesh_exporter.py              # ⭐ v3: OBJ-Mesh-Export (DEM + Polygon-Triangulation)
│   ├── gui/                              # GUI-Komponenten
│   │   └── main_dialog.py                # Tab-basierter Dialog
│   ├── processing_provider/              # QGIS Processing
│   │   ├── provider.py                   # Processing Provider
│   │   └── optimize_algorithm.py         # Haupt-Algorithmus
│   ├── utils/                            # Hilfsfunktionen
│   │   ├── central_logging.py            # Opt-in Telemetrie (file-gated, gitignored Key)
│   │   ├── error_messages.py             # Lokalisierte Fehlertext-IDs
│   │   ├── gdal_compat.py                # ReadRaster/WriteRaster-Wrapper (umgeht broken _gdal_array)
│   │   ├── geometry_3d.py                # 3D-Geometrie-Helfer (PolygonZ, LineStringZ)
│   │   ├── geometry_utils.py             # 2D-Geometrie-Helfer
│   │   ├── i18n.py                       # DE/EN-Lokalisierung
│   │   ├── layer_styling.py              # QGIS-Layer-Styles
│   │   ├── logging_utils.py              # Plugin-Logger
│   │   ├── terrain_intersection.py       # Geländeschnittkanten + Differenz-Raster (mit Cleanup-Helfern)
│   │   └── validation.py                 # Input-Validierung
│   └── tests/                            # 18 Test-Module + 2 Guides
│       ├── test_bgr_api.py
│       ├── test_central_logging.py
│       ├── test_dem_mosaic.py
│       ├── test_dxf_import.py
│       ├── test_gdal_compat.py
│       ├── test_geometry_3d.py
│       ├── test_mesh_exporter.py         # ⭐ v3
│       ├── test_multi_param_optimization.py
│       ├── test_multi_site_report.py
│       ├── test_parallel_optimization.py
│       ├── test_park_optimizer.py        # ⭐ v3
│       ├── test_placement_constraints.py # ⭐ v3
│       ├── test_report_fixes.py
│       ├── test_site_aggregator.py
│       ├── test_soil_stabilization.py
│       ├── test_terrain_intersection.py  # ⭐ v3
│       ├── test_uncertainty.py
│       ├── test_validation_enhanced.py
│       ├── test_volume_regression.py     # ⚠ braucht Fixture wea45mit3d.zip (in 5374657 gelöscht)
│       ├── TEST_RESULTS.md
│       └── PARALLELIZATION_TEST_GUIDE.md
├── webapp/                               # Web-Anwendung (Microservices, gesondert betrachtet)
├── docs/
│   ├── MULTI_SURFACE_BENUTZERHANDBUCH.md  # User-Handbuch
│   └── plans/V3_ROADMAP.md                # ⭐ v3-Implementierungsplan
├── shared/                                # Webapp-only — vom Plugin nicht genutzt
├── AGENTS.md                              # Diese Datei
├── CLAUDE.md                              # Claude-Code-spezifischer Kontext (gitignored)
├── CHANGELOG.md                           # Versions-Historie
├── CONTRIBUTING.md                        # Contributing-Guide
├── IMPLEMENTATION_TERRAIN_INTERSECTION.md # Spec + Status #4
├── RECHERCHE_2026-05-26.md                # Wettbewerbsanalyse + Feature-Ideen
├── E2E_*.md, MANUAL_*.md                  # Manuelle Test-Guides
└── LICENSE                                # MIT-Lizenz
```

⭐ markiert Module, die in der v3-Foundation-Session (Mai 2026) neu angelegt
wurden und Kern-APIs für die geplanten Roadmap-Features bereitstellen.

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
- `scipy` ✓ (genutzt von `uncertainty.py`, `park_optimizer.py`)

**Zusätzlich erforderlich** (siehe `requirements.txt`):
- `ezdxf>=1.1.0` - DXF-Parsing (mit `recover.readfile` für robustere Tolerance gegen malformed DXF)
- `requests>=2.28.0` - API-Kommunikation
- `shapely>=2.0.0` - Geometrie-Operationen (auch `placement_constraints.py`)
- `weasyprint>=56.0` - PDF-Generierung
- `openpyxl>=3.0.0` - Excel-Export im Multi-Site-Report

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
       (recover-Mode, 500 MB Cap, CRS-Detection)

2. DEM-Download
   └─→ dem_downloader.py → QgsRasterLayer
       (hoehendaten.de, 50 MB/Tile Cap, TIFF-Magic-Check, >10 km² Warnung)

3. Höhen-Optimierung
   └─→ multi_surface_calculator.py → MultiSurfaceCalculationResult
       - crane_height, total_cut, total_fill, surfaces, …
       - Parallel via ProcessPoolExecutor (Linux/macOS, Commit abecfcf)

4. Geländeschnittkanten + Differenz-Raster (NEU seit ~2026-05)
   └─→ utils/terrain_intersection.py → 14 LineString-Layer + 7 GeoTIFFs

5. Profil-Generierung
   └─→ profile_generator.py → List[PNG-Pfade]

6. Report-Generierung
   └─→ report_generator.py / multi_site_report_generator.py → HTML/PDF/Excel
       (HTML-Escape für project_name, site_name, profile_name, BGR-description)
```

### v3-Roadmap-Module

- **`core/placement_constraints.py`** — `PlacementValidator.check_position(x, y)`,
  `suggest_nearest_valid(x, y, ...)` für Buffer-Constraints (Wohnbebauung,
  Straßen, Schutzgebiete). STRtree-Indexierung, Hard/Soft-Severity,
  QgsVectorLayer-Adapter. **GUI: Tab „🚧 Restriktionen"** in `main_dialog.py`
  (`_create_constraints_tab`). Workflow-Preflight noch offen. V3_ROADMAP #1.
- **`core/park_optimizer.py`** — `ParkOptimizer.solve(sites)` (Transport-LP via
  `scipy.optimize.linprog`) + `solve_milp(sites)` (Kandidaten-MILP via
  `scipy.optimize.milp`, wählt Höhen-Kandidat pro Standort + Transport gemeinsam).
  GUI + N-Best-Extraktion aus `MultiSurfaceCalculator` offen. V3_ROADMAP #2.
- **`core/mesh_exporter.py`** — `write_obj()`, `dem_to_mesh()`,
  `polygon_to_mesh_at_height()` für 3D-Export. Ear-Clipping (konkave Polygone).
  **Im Workflow verdrahtet** (`workflow_runner._export_meshes`). V3_ROADMAP #5.

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

**Letzte Aktualisierung**: 2026-05-27
**Version dieses Dokuments**: 2.1.0 (v3-Foundation-Session)
