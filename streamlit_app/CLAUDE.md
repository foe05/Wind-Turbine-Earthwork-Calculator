# CLAUDE.md — streamlit_app

Streamlit-Implementierung des Wind Turbine Earthwork Calculators als Single-Tenant-SaaS. Migrationsziel des QGIS-Plugins unter `../windturbine_earthwork_calculator_v2/` (siehe Repo-Root `CLAUDE.md` für Plugin-Architektur und Domänenvokabular).

## Zweck

DXF-Upload → DEM-Akquise (hoehendaten.de) → Multi-Surface-Höhen-/Cut-Fill-Optimierung → Profile, 3D-Mesh, Reports → Download-Bundle (PDF, GeoPackage, LandXML, glTF). Optional Monte-Carlo, Rotation-Sweep, Park-Optimierung.

## Stack

- **UI:** Streamlit + `streamlit-folium` (Karte) + iframe-glTF (3D)
- **Berechnung:** NumPy, Shapely, rasterio, GeoPandas, scipy, pyproj, ezdxf, matplotlib (Agg)
- **Persistenz:** PostgreSQL + PostGIS — Schema in `app/core/models.py`, Migrationen unter `migrations/` (Alembic)
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

## Persistenz

Vier Tabellen: `projects` → `runs` → `run_surfaces` / `run_artifacts`. `runs.inputs`
haelt `_serialize_inputs()` als JSONB; eigene Spalten bekommen nur Werte, nach denen
gelistet oder ausgewertet wird. Je Flaeche eine Zeile in `run_surfaces` mit
`CutFillResult` und `SlopeVolumeResult` zusammen.

Geometrien liegen kanonisch in **EPSG:4326**, nicht im Arbeits-CRS — nur so bleiben
Laeufe aus verschiedenen UTM-Zonen ueber einen gemeinsamen GiST-Index abfragbar. Das
Arbeits-CRS steht je Lauf in `runs.crs_epsg`, die Transformation macht
`db.to_storage_geometry()`. An der 4326-Kopie haengt keine Massszahl: Volumen und
Flaechen sind im nativen CRS vorberechnete Zahlen.

```bash
# Schema anlegen/aktualisieren (DATABASE_URL wie in der App)
alembic upgrade head
alembic check          # Modelle vs. Migrationen deckungsgleich?
```

`run_pipeline()` schreibt jeden Lauf mit (`services/persistence.py`): vorher als
`running`, danach als `succeeded` bzw. bei einer Exception als `failed`. Die
Mitschrift ist Beiwerk — ohne `DATABASE_URL` ist der Recorder ein No-op, und ein
DB-Ausfall loggt eine Warnung, statt die Rechnung zu verlieren. Wer selbst eine
Session oeffnet, prueft vorher `db.is_configured()`.

## Nicht anfassen

- `../windturbine_earthwork_calculator_v2/` — bleibt authoritative Plugin-Quelle. Modul-Portierungen entstehen als neue Dateien hier, nicht als Edits dort.
