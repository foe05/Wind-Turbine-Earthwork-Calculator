# CLAUDE.md — streamlit_app

Streamlit-Implementierung des Wind Turbine Earthwork Calculators als Single-Tenant-SaaS. Migrationsziel des QGIS-Plugins unter `../windturbine_earthwork_calculator_v2/` (siehe Repo-Root `CLAUDE.md` für Plugin-Architektur und Domänenvokabular).

## Zweck

DXF-Upload → DEM-Akquise (hoehendaten.de) → Multi-Surface-Höhen-/Cut-Fill-Optimierung → Profile, 3D-Mesh, Reports → Download-Bundle (PDF, GeoPackage, LandXML, glTF). Optional Monte-Carlo, Rotation-Sweep, Park-Optimierung.

## Stack

- **UI:** Streamlit + `streamlit-folium` (Karte) + iframe-glTF (3D)
- **Berechnung:** NumPy, Shapely, rasterio, GeoPandas, scipy, pyproj, ezdxf, matplotlib (Agg)
- **Persistenz:** PostgreSQL + PostGIS (Projekte, Jobs, Ergebnisse)
- **Reports:** Jinja2 + WeasyPrint
- **Background-Jobs (lang):** `dramatiq` oder `rq` (entscheiden bei Bedarf; Default ist `concurrent.futures` inline)
- **Auth:** Authelia-Reverse-Proxy davor — keine app-eigene User-Tabelle
- **Container:** `docker-compose.yml` mit App + Postgres pro Kunde

## Verzeichnis-Konvention

```
app/
  Home.py          Streamlit-Entry, Multi-Page-Root
  pages/           Streamlit-Pages (jede Datei = ein Tab/Seite)
  core/            Portierte Plugin-Module (NumPy/shapely/rasterio, KEIN QGIS-Import)
  services/        DEM-Cache, Persistence, Report-Bundler, Auth-Shim
  templates/       Jinja2-Templates (HTML/PDF)
tests/
  regression/      wea45mit3d.zip + Erwartungswerte (Cut 6546 / Fill 2411 m³)
```

## Conventions

- Domänenvokabular bleibt deutsch (Kranstellfläche, Auslegerfläche, FOK, Böschung) — nicht übersetzen.
- Kein QGIS-Import in `streamlit_app/` — falls Plugin-Code Portierung braucht, vorher QGIS-API ersetzen (rasterio statt QgsRasterLayer, shapely statt QgsGeometry, pyproj statt QgsCoordinateTransform).
- Eingaben müssen UTM sein (EPSG:25832–25836). Frontend konvertiert WGS84→UTM mit pyproj/proj4 vor jeder Berechnung.
- DEM-Buffer fest 250 m (analog Plugin).
- Volume-Regression `wea45mit3d.zip` ist Quelle der Wahrheit; jede Änderung an Cut/Fill-Logik muss dagegen grün bleiben.

## Nicht anfassen

- `../windturbine_earthwork_calculator_v2/` — bleibt authoritative Plugin-Quelle. Modul-Portierungen entstehen als neue Dateien hier, nicht als Edits dort.
