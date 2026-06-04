# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Layout

Two implementations live side by side:

- `windturbine_earthwork_calculator_v2/` — **QGIS 3.34+ Processing Plugin**. Authoritative source of the calculation logic. Stays untouched during the Streamlit migration (Decision 2026-06-03).
- `streamlit_app/` — **Streamlit SaaS** version, single-tenant per customer. New code from 2026-06-03 onwards; ports plugin modules into a QGIS-free stack (NumPy + Shapely + rasterio + GeoPandas + scipy).

Legacy: a prior FastAPI/React `webapp/` and `shared/` Python layer were dropped in commit `6506d24` because they covered ~20% of plugin parity and had known code-drift to the plugin.

The reference fixture `windturbine_earthwork_calculator_v2/wea45mit3d.zip` pins the authoritative cut/fill math. Both `tests/test_volume_regression.py` (plugin) and `streamlit_app/tests/regression/test_wea45_regression.py` (Streamlit) assert the same numbers: Foundation cut 693 m³ ±1, Crane platform cut 5280 m³ ±2 / fill 1763 m³ ±2.

## QGIS Plugin Architecture

Entry points: the plugin registers **both** a QGIS Processing algorithm *and* a standalone dialog.

- `plugin.py` — QGIS plugin class; sets up the `WindTurbineProvider` and a toolbar action opening `MainDialog`.
- `processing_provider/optimize_algorithm.py` — `QgsProcessingAlgorithm` invoked from the Processing Toolbox.
- `gui/main_dialog.py` — Tab-based dialog (separate execution path that calls `core/workflow_runner.py`).
- `core/workflow_runner.py` — Orchestrates: DXF import → DEM download → optimization → profiles → report.

The `core/` package has **no QGIS dependencies** in principle — it takes geometries/rasters in, returns dicts/files out — so most logic is testable without QGIS. The only modules that touch QGIS APIs are `plugin.py`, `gui/`, and `processing_provider/`.

Data flow (per site):
1. `dxf_importer.py` — LWPOLYLINE/POLYLINE → connected polygon (EPSG:25832, UTM Zone 32N expected)
2. `dem_downloader.py` — Pulls 1 km × 1 km tiles from `hoehendaten.de` API, caches to `~/.qgis3/windturbine_calculator_v2/dem_cache/`, mosaics with `create_mosaic` (recent fix `85f57f9` rewrote this without `gdal_merge` to avoid silent nodata output)
3. `earthwork_calculator.py` / `multi_surface_calculator.py` — Sweeps heights, samples DEM inside polygons, computes cut/fill and slope/embankment volumes. `multi_surface_calculator.py` handles the multi-flächen case (crane pad + foundation + boom + rotor storage).
4. `profile_generator.py` — Radial cross-sections as matplotlib PNGs
5. `report_generator.py` / `multi_site_report_generator.py` — HTML (and WeasyPrint PDF) reports
6. Output: GeoPackage (vectors) + GeoTIFF (DEM) + HTML/PDF + profile PNGs

Plugin-specific dependencies (not bundled with QGIS): `ezdxf`, `requests`, `shapely`, `weasyprint`, `openpyxl`. See `install_dependencies.py`.

Parallel optimization: multiprocessing is enabled on Linux/macOS (commit `abecfcf`); be careful when editing `core/` modules that they remain picklable.

### Telemetry

`utils/central_logging.py` optionally POSTs four anonymous events to `log.broetzens.de`. **Opt-in only** — enabled by writing an API key to `log.config` (gitignored; repo ships a placeholder `REPLACE_WITH_YOUR_API_KEY`). Strict no-op when placeholder/empty/missing. No PII, no paths, no coords.

## Streamlit App Architecture (`streamlit_app/`)

Single Streamlit process + PostgreSQL (PostGIS) for persistence, single-tenant per customer behind an Authelia reverse proxy. No microservices, no React, no JWT — operational footprint is one Docker Compose per customer.

```
streamlit_app/
  CLAUDE.md           # stack + conventions specific to the Streamlit app
  Dockerfile          # python:3.12-slim + GDAL + Pango/Cairo (for WeasyPrint)
  docker-compose.yml  # app + postgis/postgis:16-3.4
  pyproject.toml      # streamlit, shapely, rasterio, geopandas, scipy, ezdxf, weasyprint, ...
  app/
    Home.py           # Streamlit entry: sidebar params, DXF upload, run-pipeline, results
    pages/            # additional Streamlit pages (1-5: Varianten, Multi-Site, Unsicherheit, Boden, 3D)
    core/             # ported plugin modules (NO QGIS imports)
      geometry.py             # shapely port of utils/geometry_utils.py
      validation.py           # input validation, single-language German
      dxf_import.py           # ezdxf + multi-strategy boundary trace; CRS auto-detect
      dem_download.py         # hoehendaten.de client + rasterio.merge mosaic (nodata sanity-check)
      earthwork.py            # pixel-wise cut/fill + height sweep (coarse → fine)
      multi_surface.py        # SurfaceType/Config/Project + orchestration with Boom/Rotor/Road sweeps
      slope_volume.py         # boundary-discretized slope-volume approximation
      profiles.py             # matplotlib Agg cross/longitudinal sections
      report.py               # Jinja2 + WeasyPrint HTML/PDF; overview map via matplotlib
      rotation.py             # candidate-angle sweep with injectable evaluator
      placement.py            # STRtree-accelerated constraint checks
      mass_haul.py            # cumulative ordinate + balance points + haul integral
      co2.py                  # emission-factor breakdown
      phases.py               # construction-phase volume/cost/CO2 distribution
      strata.py               # soil-stack peeling (Mutterboden / Frostschutz / Schotter)
      variants.py             # side-by-side HTML comparison
      uncertainty.py          # Monte Carlo + LHS + sensitivity ranking
      soil_stabilization.py   # DIN 18196 lime dosage + RStO 12 gravel layer
      bgr_api.py              # BGR BÜK200 WFS client (pyproj transform)
      landxml.py              # LandXML 1.2 TIN export
      slope_stability.py      # slope-stability XML (geotechnical interchange)
      mesh.py                 # OBJ/STL/glTF/Three.js viewer; rasterio DEM→mesh
      geopackage.py           # multi-surface GeoPackage via geopandas
      park_optimizer.py       # LP + MILP via scipy.optimize for park-wide transport
      site_data.py            # SiteData + MultiSiteProject aggregation
      multi_site_report.py    # HTML + XLSX multi-site comparison
    services/
      pipeline.py     # end-to-end orchestration (DXF→DEM→Calc→Profiles→Report→Exports)
    templates/
      report.html     # Jinja2 report template
  tests/
    regression/       # wea45 volume regression (same numbers as the plugin)
    test_*.py         # 140 tests across all 25 ported modules
```

QGIS-API substitutions used while porting:

| Plugin (QGIS) | Streamlit |
|---|---|
| `QgsRasterLayer` + `band.ReadAsArray()` | `rasterio.open(...).read()` |
| `QgsVectorLayer` + `QgsGeometry` | `geopandas.GeoDataFrame` + `shapely.geometry` |
| `QgsCoordinateTransform` | `pyproj.Transformer` |
| `QgsMapRendererCustomPainterJob` | `matplotlib` with shapely overlay |
| `QgsProcessingFeedback` | `streamlit.status` / `progress` callback |
| `QThread` / multiprocessing | `concurrent.futures` or `dramatiq`/`rq` (job-dependent) |
| PyQt5 dialog | Streamlit `st.tabs` / `st.sidebar` |

Plugin feature parity reached (2026-06-03). All 25 core modules ported; 140 tests pass including the authoritative wea45 regression. The Streamlit slope-volume implementation is an approximation (boundary-discretized Δh/tan(angle) band, 5-10% typical accuracy) — the plugin still has the geometrically exact slope-polygon construction, which can be ported later if higher precision is required for a specific customer.

## Build, Test, Lint

### QGIS plugin

```bash
# Run the main validation-enhanced suite (no QGIS required)
python test_runner.py

# Run the full pytest suite for the plugin
cd windturbine_earthwork_calculator_v2 && python -m pytest tests/

# Run a single test module or test
python -m pytest windturbine_earthwork_calculator_v2/tests/test_volume_regression.py -v
python -m pytest windturbine_earthwork_calculator_v2/tests/test_multi_param_optimization.py::TestName::test_method -v

# Multi-site PDF generation smoke test (root; uses WeasyPrint)
python test_pdf_generation.py

# Verify module imports (i18n, error_messages, validation)
python windturbine_earthwork_calculator_v2/verify_imports.py

# Install plugin into local QGIS profile (Linux)
cp -r windturbine_earthwork_calculator_v2 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

### Streamlit app

```bash
cd streamlit_app

# Install deps locally
pip install -e ".[dev]"

# Run dev server
streamlit run app/Home.py

# Full Docker stack (app + PostGIS)
docker-compose up -d --build

# Test suite (83 tests, ~25s; regression + e2e need wea45mit3d.zip in the plugin dir)
python -m pytest tests/

# Run only the authoritative regression
python -m pytest tests/regression/test_wea45_regression.py -v
```

### Lint (CI runs via `.github/workflows/lint.yml`)

```bash
# Syntax/undefined errors fail CI; other flake8 warnings are advisory
flake8 windturbine_earthwork_calculator_v2/ --count --select=E9,F63,F7,F82 --show-source --statistics

# Black is enforced (--check); line length 127
black --check windturbine_earthwork_calculator_v2/
```

`flake8` only blocks on `E9,F63,F7,F82`; `pylint` runs with `--exit-zero`. Black, however, is a hard gate — run `black windturbine_earthwork_calculator_v2/` before pushing.

## Conventions

- Python target: **3.12** for both plugin (QGIS 3.34 LTR Python) and Streamlit app. Plugin's `requirements.txt` uses `>=`; Streamlit app's `pyproject.toml` uses `>=` as well.
- Mixed-language codebase: German is common for domain terms in identifiers, strings, comments, and docs (e.g. "Kranstellfläche", "Auslegerfläche", "FOK"). Don't translate these — they are the ubiquitous language with the users.
- Plugin uses `utils/i18n.py` (DE/EN). Streamlit app is single-language German (no i18n layer; messages inline).
- Version bumps touch **`metadata.txt`** (QGIS-visible version + changelog block) AND the plugin source where `Version: X.X.X` is embedded AND `CHANGELOG.md`.
- All geospatial inputs must be **UTM** (EPSG:25832–25836). hoehendaten.de only accepts UTM.
- **DEM buffer is 250 m** by default in both implementations.

## Things that are easy to get wrong

- The repo root contains `test_runner.py` and `test_pdf_generation.py` — these are smoke scripts, not a pytest suite. Actual tests live in `windturbine_earthwork_calculator_v2/tests/` (plugin) and `streamlit_app/tests/` (Streamlit).
- Coordinates: if you see anything treating inputs as lat/lng in backend code it's a bug. The contract is UTM meters.
- Nodata handling: `create_mosaic` was silently producing nodata output until commit `85f57f9`. The Streamlit app uses `rasterio.merge` and retains the same sanity-check (regression guard).
- Don't add modules to `streamlit_app/app/core/` that import QGIS — the whole point of the Streamlit version is that it runs without QGIS.
- When porting a new plugin module, the wea45 regression must stay green. Add a focused regression case for each new module if numbers are involved.
- `AGENTS.md` is a more detailed developer guide (in German) for the plugin; check it for module-level specifics before making architectural changes there.
