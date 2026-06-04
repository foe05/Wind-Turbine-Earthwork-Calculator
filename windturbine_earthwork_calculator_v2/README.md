# Wind Turbine Earthwork Calculator V2

**A QGIS Processing Plugin for Optimizing Wind Turbine Crane Pad Heights**

Version: 2.0.0 (released); v3.0 foundations in progress
Author: Wind Energy Site Planning
Date: November 2025 (release); foundations updated May 2026

---

## 📋 Overview

This QGIS plugin optimizes the platform height for wind turbine crane pads by calculating and minimizing earthwork volumes (cut and fill). It processes DXF files containing crane pad outlines, downloads high-resolution elevation data, and generates comprehensive reports with terrain profiles.

### Key Features

**Erdmassen-Workflow**
- ✅ **DXF Import** — LWPOLYLINE/POLYLINE → Polygone via `ezdxf` (recover-Mode, 500 MB-Cap)
- ✅ **DEM-Akquise** — hoehendaten.de DGM1 (1 m) mit 50 MB-Tile-Cap + TIFF-Magic-Byte-Check, oder lokales GeoTIFF (Drohnenbefliegung) als Alternative
- ✅ **Höhen-Optimierung** — single- + multi-parameter Sweep, parallel via `ProcessPoolExecutor` (Linux/macOS), LRU-Cache für DEM-Samples, vektorisierte Cut/Fill-Mathematik
- ✅ **Multi-Surface-Berechnung** — Kranstellfläche, Fundament, Auslegerfläche, Rotorblattlagerfläche, Zufahrt
- ✅ **Geländeschnitte** — Quer- + Längsprofile als PNG
- ✅ **Schnittkanten + Differenz-Raster** — 14 LineString-Layer (2D + 3D) + 7 GeoTIFFs je Standort
- ✅ **BGR-Bodendaten** — Bodenart + Stabilisierungs-Klasse via BGR WFS
- ✅ **Opt-in-Telemetrie** — vier anonyme Events an `log.broetzens.de`; default aus, gitignored Key

**Berichte + Export**
- ✅ **HTML / PDF / Excel Reports** — Single-Site + Multi-Site, mit XSS-sicherem HTML-Escape
- ✅ **GeoPackage** — alle Vektor-Layer in einer Datei (DEM als Side-Car-GeoTIFF)
- ✅ **3D-Export** — OBJ + STL (ASCII/binär) + glTF + selbst-enthaltener Three.js-Viewer pro Standort
- ✅ **LandXML 1.2** — TIN-Surfaces je Fläche für Machine-Control (Trimble/Topcon/Leica) und BIM
- ✅ **Slope-Stability-XML** — opt-in Querschnitt-Export für Slide/GeoStudio mit Material- + Piezometer-Daten

**Planung + Optimierung (v3-Module)**
- ✅ **Restriktions-Tab** — Layer-Picker pro Kategorie (Wohnbebauung, Straßen, Schutzgebiete), Hard/Soft-Severity, Snap-to-Grid-Vorschlag der nächsten gültigen Position; automatischer Preflight des Kran-Centroids vor dem DEM-Download
- ✅ **Park-Optimierung** — Transport-LP über mehrere Standorte (`solve`) und Kandidaten-MILP für gemeinsame Höhen-/Transport-Wahl (`solve_milp`); Sektion im Multi-Site-Report
- ✅ **Rotationswinkel-Analyse** — opt-in, sweept Plattform-Ausrichtungen und zeigt die Einsparung im Bericht
- ✅ **Mass-Haul-Diagramm** — opt-in, Massenausgleichspunkte + Free-Haul/Overhaul aus dem repräsentativen Längsprofil
- ✅ **Bodenschichten (Strata)** — Aufschlüsselung von Cut/Fill in Mutterboden → Frostschutz → Schotter mit Kosten und CO₂
- ✅ **Bauphasen-Verteilung** — Standardplan Wegebau → Pad → Fundament → Restarbeiten mit Zeitachse
- ✅ **CO₂-Bilanz** — Erdbewegung × LKW-km × Faktor + Beton/Stahl
- ✅ **Variantenvergleich** — Side-by-Side HTML mehrerer Planungs-Varianten (Python-API)

Headless-Nutzung der Planungs-Module siehe `docs/PYTHON_API.md`.

---

## 🚀 Installation

### Prerequisites

- **QGIS LTR 3.34+** (Long Term Release)
- **Python 3.9+** (included with QGIS)
- **Internet connection** (for DEM download)

### Step 1: Copy Plugin to QGIS Directory

Copy the entire `windturbine_earthwork_calculator_v2` folder to your QGIS plugins directory:

**Linux:**
```bash
cp -r windturbine_earthwork_calculator_v2 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

**Windows:**
```
C:\Users\{YourUsername}\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\
```

**macOS:**
```
~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/
```

### Step 2: Install Python Dependencies

The plugin requires two additional Python packages:

```bash
# Run this in your terminal/command prompt
pip install --user ezdxf requests
```

Alternatively, run the included installation script:

```bash
cd ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/windturbine_earthwork_calculator_v2
python install_dependencies.py
```

### Step 3: Enable Plugin in QGIS

1. Start QGIS
2. Go to **Plugins → Manage and Install Plugins**
3. Click **Installed**
4. Find **Wind Turbine Earthwork Calculator V2**
5. Check the checkbox to enable it

---

## 📖 Usage

### Quick Start

1. **Open Processing Toolbox**
   - View → Panels → Processing Toolbox
   - Or press `Ctrl+Alt+T`

2. **Find the Algorithm**
   - Expand **Wind Turbine Earthwork Calculator V2**
   - Double-click **Optimize Platform Height**

3. **Configure Parameters**
   - **Input DXF File**: Select your crane pad DXF file
   - **Min/Max Height**: Set height range (e.g., 300-310m ü.NN)
   - **Output GeoPackage**: Choose output file path

4. **Run**
   - Click **Run**
   - Wait for processing (typically 2-5 minutes)

### Input Requirements

#### DXF File Format

- **Entities**: LWPOLYLINE or POLYLINE
- **CRS**: EPSG:25832 (UTM Zone 32N)
- **Closure**: Lines will be automatically connected
- **Layer**: Any layer (default: Layer '0')

Example DXF structure:
```
- LWPOLYLINE entities (42 lines forming crane pad outline)
- Coordinates in meters (UTM 32N)
- Not necessarily closed (plugin connects them automatically)
```

#### Height Range

- **Min Height**: Minimum platform height to test (m ü.NN)
- **Max Height**: Maximum platform height to test (m ü.NN)
- **Step**: Height increment for optimization (default: 0.1m)

**Example**: Min=300, Max=310, Step=0.1 → Tests 101 scenarios

### Advanced Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| Height Step | 0.1 m | 0.01-10 m | Optimization granularity |
| DXF Tolerance | 0.01 m | 0.001-10 m | Point connection tolerance |
| Slope Angle | 45° | 15-60° | Embankment slope angle |
| Num Profiles | 8 | 4-16 | Number of terrain cross-sections |
| Vertical Exag. | 2.0x | 1.0-5.0x | Profile visualization scaling |
| Force DEM Refresh | False | - | Ignore cache, re-download DEM |

### Output Files

After successful execution, you'll get:

```
output_directory/
├── project.gpkg                  # GeoPackage with all vector data
│   ├── platform_polygon          # Optimized crane pad polygon
│   └── profile_lines             # Terrain cross-section lines
├── project.dem.tif               # DEM mosaic (GeoTIFF)
├── project.html                  # HTML report
└── profiles/                     # Terrain profile images
    ├── profile_001.png
    ├── profile_002.png
    ├── ...
    └── profile_008.png
```

---

## 🔧 Workflow Details

### Step 1: DXF Import

The plugin:
1. Reads all LWPOLYLINE entities from the DXF file
2. Connects polylines by matching endpoints (within tolerance)
3. Creates a closed polygon
4. Validates topology (no self-intersections, valid area)

**Output**: QGIS polygon geometry in EPSG:25832

### Step 2: DEM Download

The plugin:
1. Calculates required 1km×1km DEM tiles (with 250m buffer)
2. Downloads tiles from hoehendaten.de API
3. Caches tiles locally (~/.qgis3/windturbine_calculator_v2/dem_cache/)
4. Mosaics tiles into single raster

**Note**: First run downloads tiles (~10-40 MB), subsequent runs use cache.

### Step 3: Height Optimization

For each height h in range (min → max, step):
1. Sample DEM elevations within platform polygon
2. Calculate cut volume (where terrain > platform)
3. Calculate fill volume (where terrain < platform)
4. Calculate slope/embankment volumes
5. Sum total volume moved

**Optimal height** = height with minimum total volume

### Step 4: Terrain Profiles

The plugin generates radial cross-sections:
- 8 equally-spaced lines from platform center
- Samples DEM along each line (0.5m intervals)
- Creates matplotlib plots showing:
  - Existing terrain (black line)
  - Planned platform (blue line)
  - Cut areas (red fill)
  - Fill areas (green fill)

### Step 5: HTML Report

Generates a professional report with:
- Executive summary (optimal height, volumes)
- Project parameters (location, area, slope angle)
- Detailed results (terrain statistics, volume breakdown)
- Embedded terrain profile images
- Print-friendly styling

---

## 🛠️ Troubleshooting

### Plugin doesn't appear in QGIS

**Solution:**
1. Check plugin directory location
2. Ensure `__init__.py` and `metadata.txt` exist
3. Restart QGIS
4. Check **Plugins → Manage and Install Plugins → Installed**

### ImportError: No module named 'ezdxf'

**Solution:**
```bash
pip install --user ezdxf
```
Or run `install_dependencies.py`

### DEM Download Fails (HTTP 404)

**Reason**: Tile not available on hoehendaten.de

**Solution**:
- Check if your area is covered by German DEM data
- Verify DXF coordinates are in EPSG:25832
- Try with a different location

### Processing takes very long

**Reasons**:
- Height range too large
- Height step too small
- Too many scenarios

**Solution**:
- Reduce height range (e.g., 300-305 instead of 300-400)
- Increase step size (e.g., 0.2m instead of 0.1m)
- Aim for < 1000 scenarios

### Polygon is invalid (self-intersection)

**Reason**: DXF polylines create invalid geometry

**Solution**:
- Check DXF file in CAD software
- Ensure polylines form a valid closed shape
- Fix overlapping segments
- Adjust DXF tolerance parameter

---

## 📊 Example

### Input

- **DXF File**: `Kranstellfläche_Marsberg_V172-7.2-175m.dxf`
- **Location**: Marsberg, Germany (EPSG:25832)
- **Min Height**: 300.0 m ü.NN
- **Max Height**: 310.0 m ü.NN
- **Step**: 0.1 m

### Output

```
Optimal Platform Height: 305.3 m ü.NN
Total Cut Volume: 3,421 m³
Total Fill Volume: 2,987 m³
Total Earthwork: 6,408 m³
Net Balance: +434 m³ (surplus cut)

Platform Area: 1,850 m²
Terrain Range: 8.5 m (min: 301.2, max: 309.7)
```

---

## 🐛 Known Issues

1. **Raster output format**: The DEM is intentionally written as a separate GeoTIFF (not into the GeoPackage). GeoPackage raster support in QGIS is functional but inconsistent across plugin readers (rasterio/GDAL/QGIS); a side-car GeoTIFF guarantees compatibility.
2. **Large DXF Files**: Very complex DXF files (>1000 polylines) may be slow to import. The common path uses Shapely `linemerge`/`unary_union` (efficient); only a rarely-reached fallback is O(n²). Files above 500 MB are rejected outright for safety.
3. **Memory Usage**: DEM sampling reads only the polygon's bounding-box window (not the whole band), so RAM scales with the construction area rather than the full DEM. A bounded LRU cache avoids re-sampling the same surface across the height sweep, and the cut/fill volume math is vectorised. Very large areas in the legacy fallback path can still be RAM-heavy.

---

## 🐍 Public Python API

Twelve of the `core/` modules are **QGIS-independent** — they only need numpy /
scipy / shapely (plus stdlib XML for the writers). They can be imported from
plain Python scripts, batch jobs, CI pipelines or your own GUI without ever
loading `qgis.core`. The QGIS-integrated workflow uses them too, so behaviour
is consistent between the plugin and headless use.

| Module | Public entry points |
|---|---|
| `core/park_optimizer.py` | `ParkOptimizer.solve` (LP), `ParkOptimizer.solve_milp` (MILP) |
| `core/placement_constraints.py` | `PlacementValidator.check_position` / `suggest_nearest_valid` |
| `core/rotation_optimizer.py` | `RotationOptimizer.optimize`, `rotate_points`, `polygon_centroid` |
| `core/mesh_exporter.py` | `write_obj`, `write_stl`, `write_gltf`, `write_three_js_viewer`, `dem_to_mesh`, `polygon_to_mesh_at_height` |
| `core/landxml_export.py` | `write_landxml`, `surface_from_mesh` |
| `core/mass_haul.py` | `MassHaulDiagram.compute` |
| `core/co2_balance.py` | `CO2Calculator.compute`, `EmissionFactors` |
| `core/strata_quantities.py` | `StrataCalculator.split`, `default_stack` |
| `core/construction_phases.py` | `PhasePlanner.plan`, `default_phases` |
| `core/slope_stability_export.py` | `write_slope_xml`, `section_from_profile`, `default_materials` |
| `core/variant_comparison.py` | `VariantComparisonReport.write`, `best_variant` |
| `core/mesh_exporter.py` (helpers) | `MeshData`, `build_gltf_dict` |

Usage examples for every module are in **`docs/PYTHON_API.md`**.

An **end-to-end smoke test** that walks through a realistic three-turbine park
planning flow across most of these modules ships as
`tests/test_e2e_smoke.py` — useful both as a regression guard and as a
worked example. To run the full plain-Python test suite (no QGIS install
needed):

```bash
pip install --user pytest shapely scipy numpy
pytest windturbine_earthwork_calculator_v2/tests/ \
    --ignore=windturbine_earthwork_calculator_v2/tests/test_dxf_import.py \
    --ignore=windturbine_earthwork_calculator_v2/tests/test_multi_site_report.py
# (the ignored ones import the QGIS-bound package layer)
```

The plain-Python subset currently runs **166 tests** in well under three
seconds; GDAL-bound tests skip cleanly when `osgeo` is missing.

---

## 🔄 Changelog

For the full per-release log see the repository-root `CHANGELOG.md`.

### Unreleased (Stand 2026-06-01)

**Neue Konkurrenz-/Planungs-Features (alle mit plain-Python-Tests):**
- `core/mass_haul.py` — Mass-Haul-Diagramm (Compaction, Balance-Punkte, Free-Haul); im Report
- `core/rotation_optimizer.py` — Plattform-Ausrichtungs-Sweep; opt-in im Workflow + Report
- `core/co2_balance.py` — CO₂e-Bilanz; automatische Sektion im Single-Site-Report
- `core/landxml_export.py` — LandXML 1.2 TIN-Surfaces; auto-export neben OBJ/glTF
- `core/strata_quantities.py` — Bodenschichten-Aufschlüsselung; Auto-Sektion im Report
- `core/construction_phases.py` — Bauphasen-Planung mit Zeitachse; Auto-Sektion im Report
- `core/slope_stability_export.py` — Querschnitt-XML für Slide/GeoStudio; opt-in im Workflow
- `core/variant_comparison.py` — Side-by-Side HTML mehrerer Varianten (Library)
- **Drohnen-DEM-Import:** GUI-Filepicker; STEP 4 überspringt hoehendaten.de bei lokalem GeoTIFF
- `docs/PYTHON_API.md` — vollständige Public-API-Dokumentation
- `tests/test_e2e_smoke.py` — End-to-End Smoke-Test über alle QGIS-freien Module

**Performance (#9/#10):**
- LRU-Cache (maxsize 16) für DEM-Samples im Höhen-Sweep
- Vektorisierte Cut/Fill-Schleifen (Kranstellfläche + Fundament), Äquivalenz bewiesen
- Hinweise zu großen DEMs (>10 km²) + dokumentierte Performance-Charakteristik

### Unreleased (Stand 2026-05-27)

**Sicherheits-Härtung:**
- HTML-Escape für extern beziehbare Strings in allen Reports und Dialog-Labels
- `log.config` aus dem Git-Index entfernt; nur `log.config.example` ausgeliefert
- DEM-Downloader: 50 MB-Cap pro hoehendaten.de-Tile + TIFF-Magic-Byte-Prüfung
- DEM-Downloader: Warnung bei DEM-Anfragen über 10 km²
- DXF-Importer: 500 MB-Cap und Umstellung auf `ezdxf.recover.readfile`
- Tile-Name-Regex-Guard im DEM-Downloader

**Terrain-Intersection (Geländeschnittkanten & Differenz-Raster):**
- Cleanup-Helper (`_safe_remove`, `_safe_remove_shapefile_set`) für robuste Temp-Datei-Entsorgung
- Umstellung von `tempfile.mktemp` auf `tempfile.mkstemp` (Race-Condition behoben)
- Test-Skelett `tests/test_terrain_intersection.py` ergänzt
- `IMPLEMENTATION_TERRAIN_INTERSECTION.md` mit Implementierungs-Status angereichert

**v3-Foundation-Module (eigenständig nutzbar, GUI-Integration folgt):**
- `core/placement_constraints.py` — Constraint-Validator mit STRtree + Snap-to-Grid (16 Tests),
  **GUI-Tab „🚧 Restriktionen"** in `gui/main_dialog.py` (Layer-Picker pro Kategorie,
  Distanz, Hard/Soft, interaktiver Positions-Checker + Vorschlag nächster gültiger Position)
- `core/park_optimizer.py` — Park-weite Optimierung via scipy: Transport-LP (`solve`)
  + Kandidaten-MILP (`solve_milp`, wählt Höhen-Kandidat pro Standort + Transport gemeinsam); 16 Tests
- `core/mesh_exporter.py` — 3D-Export für DEM und Plattform-Polygone in OBJ, STL
  (ASCII/binär) und glTF + selbst-enthaltener Three.js-Viewer (25 Tests),
  **im Workflow verdrahtet:** jeder Lauf schreibt Terrain + Flächen als OBJ,
  ein kombiniertes `scene.gltf` und `viewer.html` nach `WKA_<x>_<y>_meshes/`
  (auto-on, per Param `export_obj=False` abschaltbar)
- `docs/plans/V3_ROADMAP.md` — konsolidierter v3-Implementierungsplan

**Repo-Hygiene:**
- Platzhalter-URLs `yourusername`/`YOURUSERNAME` durchgehend ersetzt
- `metadata.txt`: tracker/repository/homepage und author-Email
- CHANGELOG-Linksammlung um v5.x/v6.x ergänzt
- AGENTS.md-Projektstruktur aktualisiert (alle aktuellen Module gelistet)

### Version 2.0.0 (November 2025)

- Complete refactoring as QGIS Processing Plugin
- Modular architecture (separation of concerns)
- DXF import with automatic polygon generation
- hoehendaten.de API integration with caching
- Automated terrain profile generation
- Professional HTML reports
- Comprehensive error handling and validation
- Full logging support

### Version 1.0 (Previous)

- Initial standalone script version
- Manual workflow
- Single-file implementation

---

## 📡 Telemetry

The plugin can optionally forward a small set of anonymous usage events to the
central logging service at `log.broetzens.de`. Telemetry is **opt-in** and
**off by default**.

### What is sent

Exactly four events, each with a minimal payload:

| Event | When | Payload fields |
|---|---|---|
| `calculation_started` | Beginning of the earthwork calculation | `num_turbines`, `dem_source_type`, `platform_w`, `platform_h`, `rotation_opt_enabled` (fields are omitted if not determinable) |
| `calculation_completed` | After a successful calculation | `duration_ms`, `cut_m3`, `fill_m3`, `balance_m3`, `num_turbines` |
| `calculation_failed` | On calculation error | `error_class` (exception class name only), `step` |
| `report_generated` | After a successful HTML / vector-layer export | `format` (e.g. `"html"`, `"vector_layer"`) |

Each request additionally includes:
- `tool`: `wind-turbine-earthwork-calculator`
- `tool_version`: plugin version from `metadata.txt`
- `instance`: an anonymous UUID4 generated on first start and stored in QGIS
  `QSettings` under `wind-turbine-earthwork-calculator/installation_id`

**No PII is ever sent.** No file paths, file names, coordinates, user names,
hostnames, IP addresses, stack traces or exception messages are included.

### Where it goes

All events are sent via `POST https://log.broetzens.de/api/log` with a
5-second timeout, from a background daemon thread. Errors are swallowed
silently — the plugin never blocks or crashes because of telemetry.

### How to enable telemetry

1. Locate the file `log.config` inside the installed plugin directory (next
   to `__init__.py`). It ships with the placeholder `REPLACE_WITH_YOUR_API_KEY`.
2. Replace the contents of that file with your real API key (a single line,
   no quotes, no `key=value` syntax, no comments).
3. Restart QGIS.

Status is logged once at plugin load to the QGIS message log (panel
*WindTurbine Telemetry*), either confirming activation or noting that
telemetry is inactive.

### How to disable telemetry

Either leave `log.config` empty, keep the shipped placeholder
`REPLACE_WITH_YOUR_API_KEY`, or delete the file. In any of those states the
telemetry module is a strict no-op and makes no network calls.

> **Note:** `log.config` is listed in the repository's `.gitignore`. The
> committed placeholder stays in place, but your locally edited real key is
> never pushed.

---

## 📝 License

This plugin is provided "as-is" for wind energy site planning purposes.

---

## 👥 Support

For issues, questions, or feature requests:

1. Check this README and troubleshooting section
2. Review QGIS logs: View → Panels → Log Messages
3. Check plugin logs: `~/.qgis3/windturbine_calculator_v2/*.log`

---

## 🙏 Acknowledgments

- **QGIS Project** - For the excellent GIS platform
- **hoehendaten.de** - For providing free high-resolution DEM data
- **ezdxf** - For DXF file parsing capabilities

---

**Happy Optimizing! 🌬️💨**
