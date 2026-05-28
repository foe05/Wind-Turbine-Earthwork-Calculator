# V3-Roadmap — Wind Turbine Earthwork Calculator V2

**Erstellt:** 2026-05-27
**Quelle:** `RECHERCHE_2026-05-26.md` Teil 1+3 (offene Punkte + Wettbewerbsanalyse)
**Status:** Lebendiges Dokument, pro Feature ein Plan-Abschnitt.

Dieses Dokument konsolidiert die als „groß" eingestuften Roadmap-Items aus
`CHANGELOG.md` (Sektion *Geplant für v3.0*) zu konkreten Implementierungsplänen,
plus die zwei größeren Performance-Punkte aus den Known Issues.

---

## Status-Snapshot (Stand 2026-05-27)

| Roadmap-Item | Code-Realität | Restaufwand |
|---|---|---|
| #1 Constraint-basierte Platzierung | 🟡 **Core-Modul fertig** (`core/placement_constraints.py` + 16 Tests grün); GUI/Workflow-Anbindung noch offen | mittel (GUI) |
| #2 Park-weite Batch-Optimierung | 🟡 **Transport-LP fertig** (`core/park_optimizer.py` + 9 Tests grün); MILP über Kandidaten + Workflow-Anbindung noch offen | mittel (MILP-Erweiterung + GUI) |
| #4 Terrain-Intersection & Differenz-Raster | ✅ **~95 % implementiert** (`utils/terrain_intersection.py`, 622 LOC; wired in `multi_surface_calculator.py:3301+`); 14-Layer/7-Raster-Output, Cleanup-Härtung + Test-Skelett ergänzt | klein (3D-Renderer-Konfig optional) |
| #5 3D-Mesh-Export & 3D-Viewer | 🟡 **OBJ-Export fertig** (`core/mesh_exporter.py` + 16 Tests, 11 grün/5 gdal-skip); STL/glTF + Three.js-Viewer noch offen | mittel (zusätzliche Formate + Viewer) |
| #9 DXF-Import langsam (>1000 Polylinien) | nicht profiliert | mittel |
| #10 DEM-RAM (>10 km²) | DEM komplett im RAM via `gdal_compat.read_band_as_array`; Warn-Log bei >10 km² eingebaut | mittel (windowed reads) |

### Stand nach Foundation-Session (2026-05-27)

In dieser Session entstanden drei neue QGIS-unabhängige Kern-Module mit
testabgedeckten APIs, die als Grundlage für die finale Feature-Integration
dienen:

- **`core/placement_constraints.py`** — Validator + STRtree-Lookup +
  Snap-to-Grid-Suche. Pure Shapely. **16/16 Tests grün.**
- **`core/park_optimizer.py`** — LP-Solver für park-weiten Material-Transport
  via `scipy.optimize.linprog`. **9/9 Tests grün.**
- **`core/mesh_exporter.py`** — OBJ-Writer + Polygon-zu-Mesh (Ear-Clipping) +
  DEM-zu-Mesh mit Decimation. **11/11 Pure-Python-Tests grün; 5 GDAL-Tests
  skippen in CI ohne osgeo-Bindings.**

Was noch fehlt, um die Features in der GUI nutzbar zu machen:
1. **#1 GUI:** Tab „Restriktionen" in `gui/main_dialog.py` (Layer-Picker,
   Distanz-Spinbox, Hard/Soft-Toggle) + Hook in `core/workflow_runner.py`
   vor DEM-Download.
2. **#2 MILP-Stufe:** N-Best-Kandidaten aus `MultiSurfaceCalculator` (statt
   nur 1-Best) sammeln, dann Kandidaten + Transport als MILP über
   `scipy.optimize.milp` lösen.
3. **#5 Workflow-Anbindung:** `core/workflow_runner.py` so erweitern, dass
   die berechneten Plattform-Polygone + das DEM zusätzlich als OBJ ins
   Output-Verzeichnis geschrieben werden; optional zusätzliche Writer für
   STL und glTF.

### Blockierte Items (außerhalb Code-Reichweite)

| Item | Blocker |
|---|---|
| #3 Multi-Param-Praxistest gegen Fixture | ✅ **Behoben (2026-05-28):** Fixture `wea45mit3d.zip` (19.5 MB) aus der Git-Historie (`5374657^`) wiederhergestellt; `test_volume_regression.py` läuft wieder (4/4 grün mit rasterio/fiona/shapely). |
| #11 E2E-Manual-Test Multi-Site-Report | Manueller Test, braucht echte DEM/DXF-Daten + Sign-Off. |
| #13 Manuelle Excel-/PDF-Verifikation | Manueller Test, braucht Augenmerk-Review. |

---

## #1 — Constraint-basierte Platzierung

### Ziel
Automatische Konflikt-Vermeidung beim Platzieren der WEA-Plattform: Buffer um
Gebäude/Straßen/Schutzzonen einhalten, Snap-to-Grid für standardisierte
Platzierung, Warnung bei Verletzungen.

### Umfang (User Story)
> Als Planer möchte ich eine WEA-Position vorschlagen und sofort sehen, ob sie
> Mindestabstände zu Gebäuden, Straßen oder Schutzgebieten verletzt, damit ich
> die Position interaktiv anpassen kann, ohne den vollen Workflow durchlaufen
> zu müssen.

### Vorgeschlagene Architektur

**Neues Modul:** `core/placement_constraints.py`

```python
@dataclass
class ConstraintLayer:
    name: str
    geom_source: QgsVectorLayer
    min_distance_m: float
    severity: Literal['hard', 'soft']  # hard = block, soft = warn

class PlacementValidator:
    def __init__(self, constraints: list[ConstraintLayer]):
        ...

    def check_position(self, point: QgsPointXY) -> list[Violation]:
        """Returns hard+soft violations for a candidate WEA position."""

    def suggest_nearest_valid(self, point: QgsPointXY,
                              search_radius_m: float = 100.0,
                              grid_step_m: float = 5.0) -> QgsPointXY | None:
        """Snap-to-grid search for the closest constraint-respecting position."""
```

**GUI-Integration:** In `gui/main_dialog.py` neue Tab „Restriktionen" mit
Layer-Picker pro Constraint, Distanz-Spinbox, Hard/Soft-Toggle. Aufruf von
`check_position()` bei Live-Eingabe der Koordinaten.

**Workflow-Integration:** Vor Schritt 2 (DEM-Download) ein „Constraint Check"
einschieben. Bei Hard-Violation: Abbruch mit `feedback.reportError`.

### Datenquellen für DACH
- OSM-Buildings (über QGIS QuickOSM oder pyrosm)
- DTK-25 für Straßen (BKG WMS)
- ALKIS-Flurstücke (separates Roadmap-Item, hier nutzbar)
- Schutzgebiete: WMS BfN (Naturschutzgebiete, FFH)

### Aufwand
- Kern-Modul: 3–5 Tage
- GUI-Anbindung: 2 Tage
- Tests: 1 Tag
- **Summe: ~1.5 Wochen**

### Tests
- `tests/test_placement_constraints.py`: Geometrische Edge Cases (Punkt genau
  auf Buffer-Grenze, mehrere überlappende Constraints, leere Constraint-Liste).
- Headless run mit Synthetic Constraint Layer.

---

## #2 — Park-weite Batch-Optimierung

### Ziel
Statt jeden Standort einzeln optimieren: Optimierungsproblem über *alle* WEA
eines Windparks gemeinsam lösen, mit Park-weiter Kostenfunktion inkl.
Material-Transport zwischen Standorten.

### Aktuelle Situation
- `core/site_aggregator.py` aggregiert Ergebnisse von n Einzelläufen.
- `MultiSiteReportGenerator` vergleicht visualisiert sie.
- **Keine** gemeinsame Optimierung — jede WEA hat ihr eigenes lokales Optimum.

### Vorgeschlagene Architektur

**Neues Modul:** `core/park_optimizer.py`

Zwei-Stufen-Ansatz:
1. **Single-Site-Stage:** für jeden Standort die 5–10 besten Höhen-Kandidaten
   ausrechnen (statt nur das lokale Optimum). Existierender
   `MultiSurfaceCalculator._find_optimum_multi_parameter` liefert das bereits;
   muss nur n-best statt 1-best zurückgeben.
2. **Park-Stage:** Mixed-Integer-Optimierung über alle Standorte:
   - **Variablen:** pro Standort welcher Kandidat gewählt wird
   - **Constraint:** Park-Gesamtbudget (optional)
   - **Zielfunktion:** Σ Standortkosten + Σ Transportkosten(i→j) × ausgetauschtes
     Material

**Lösung:** `scipy.optimize.linprog` (LP) oder `pulp` (MILP). Für realistische
Parkgrößen (5–30 WEA × 5 Kandidaten) ist das in Sekunden lösbar.

**Transport-Modell:**
- Matrix `T[i,j]` = Distanz Standort i → Standort j (Haversine oder
  Straßennetz via OSRM)
- Aushubmaterial Standort i kann fehlende Auffüllung bei Standort j
  decken — wenn die Bilanz stimmt
- Kostenfaktor `€/m³·km` aus `cost_config`

### Aufwand
- Park-Stage-Solver: 4–6 Tage
- N-Best-Erweiterung der Single-Stage: 1 Tag
- Transport-Matrix-Modul: 2 Tage
- Report-Erweiterung (Park-Optimum-Vergleich vs. Einzeloptima): 2 Tage
- **Summe: ~2 Wochen**

### Tests
- Synthetic Park mit 3 Standorten, einer Cut-only und einer Fill-only →
  erwarteter Optimum-Transport berechenbar von Hand.
- Regression gegen Site-Aggregator: Park-Optimum-Kosten ≤ Σ Einzeloptimum-Kosten.

---

## #4 — Terrain-Intersection & Differenz-Raster (90 % done)

### Aktueller Stand
- `utils/terrain_intersection.py`: 622 LOC, alle 8 Public-Funktionen aus dem
  Spec implementiert
- `core/surface_types.py:300–360`: Fields für `terrain_intersection_2d/3d/raster_path`
  existieren auf SurfaceCalculationResult und MultiSurfaceCalculationResult
- `core/multi_surface_calculator.py:3301+`: Wiring vorhanden (`extract_terrain_intersection_horizontal`
  bzw. `_sloped` werden aufgerufen)

### Vermutlich offene Lücken (ohne Vollaudit, bitte einmal verifizieren)
1. **GeoPackage-Output:** Werden die 14 Linien-Layer wirklich geschrieben?
   `_save_to_geopackage` (`workflow_runner.py:1073+`) prüfen.
2. **Styling:** Die `IMPLEMENTATION_TERRAIN_INTERSECTION.md` spezifiziert eine
   Farb-/Strichstärken-Matrix. Vergleichen mit `utils/layer_styling.py`.
3. **Report-Integration:** Werden Schnittkanten im HTML-Report visualisiert?
4. **Tests:** Gibt es ein `tests/test_terrain_intersection.py`? (Aktuell nicht
   gefunden.)

### Empfohlene Vorgehensweise
1. Diff-Run gegen die Spec (kann ein Sub-Agent in 30 Min machen)
2. Punktuelle Tests ergänzen
3. Status in `IMPLEMENTATION_TERRAIN_INTERSECTION.md` aktualisieren (Doku sagt
   noch „geplant", obwohl Code fertig ist)

### Aufwand
- **Restaufwand: 1–3 Tage** (deutlich kleiner als ursprünglich angenommen)

---

## #5 — 3D-Mesh-Export & 3D-Viewer

### Ziel
- Export der konstruierten Flächen + Differenz-Geländes als 3D-Mesh
  (OBJ, STL, glTF)
- Embed-Viewer im HTML-Report (Three.js / Cesium)

### Vorgeschlagene Architektur

**Neues Modul:** `core/mesh_exporter.py`

```python
class MeshExporter:
    def export_surface_as_obj(
        self,
        surface_polygon: QgsGeometry,
        height_field: Callable[[float, float], float],  # für gekrümmte Flächen
        output_path: Path,
        resolution_m: float = 0.5,
    ) -> Path: ...

    def export_dem_as_obj(self, dem_path: Path, output_path: Path,
                          decimation_factor: int = 4) -> Path: ...

    def export_combined_gltf(self, ...) -> Path: ...
```

**Implementation:**
- DEM → Triangle-Mesh via `numpy` + Greedy-Decimation (oder `trimesh.smooth`)
- Surface-Geometrien aus `multi_surface_calculator` als Polygone bekannt → einfache
  Triangulation via `mapbox-earcut` oder `shapely.ops.triangulate`
- OBJ-Writer: 100 LOC. STL: 80 LOC. glTF: lieber `pygltflib` als
  Eigenimplementierung.

**Viewer:** Three.js (statischer ES-Modul-Import) ist die geringste-Friction-Variante.
Embed-HTML-Template (Single-File mit Inline-Mesh-Daten) wird vom
`MultiSiteReportGenerator` als Anhang generiert.

### Aufwand
- Mesh-Generierung: 4 Tage
- glTF + OBJ Writer: 2 Tage
- Three.js-Viewer-Template: 2 Tage
- Report-Integration: 1 Tag
- **Summe: ~1.5 Wochen**

### Abhängigkeiten
- `pygltflib` (BSD, klein)
- `trimesh` (MIT) — optional, für Mesh-Optimierung

---

## #9 — DXF-Import-Performance bei >1000 Polylinien

### Profiling-Hypothesen (ungeprüft)
- `detect_coordinate_system` (Zeilen 175–190 in `dxf_importer.py`): Python-Schleife
  mit `.append()` pro Vertex. Bei 1000 Polylinien × 50 Vertices = 50 000 Appends
  → 0.5–1 s, vermutlich nicht der Hotspot.
- Vermutlicher Hotspot: die Polyline-zu-Polygon-Konvertierung mit Shapely
  `unary_union` und `polygonize`, weil O(n²) im Worst Case.

### Vorgeschlagene Schritte
1. **Profilen** mit `cProfile` gegen eine 1000+-Polylinien-Testdatei
2. Engste Schleifen vectorisieren: `np.fromiter(entity.get_points('xy'), dtype=...)`
3. STRtree für nächste-Punkt-Suche statt linearer Scan (Shapely 2.x hat es bereits)
4. Falls Connect-Polylines-Schritt der Engpass ist: parallele Polygonisierung
   pro Layer/Color

### Aufwand
- Profiling: 0.5 Tag
- Optimierungen: 2–4 Tage (abhängig vom Profilergebnis)

---

## #10 — DEM-RAM bei >10 km²

### Aktueller Stand
`utils/gdal_compat.read_band_as_array` lädt das gesamte Band als float32-Array.
Bei 10 km² × 1 m = 10 000 × 10 000 Pixel = **400 MB pro DEM**. Mit Maske,
Differenz-Raster und Kopien beim Sampling kommt man schnell auf 2–3 GB.

### Vorgeschlagene Architektur

**Refactoring:** Sampling-Operationen auf *Windowed Reads* umstellen.

```python
# utils/gdal_compat.py — neu
def read_band_in_window(ds, x_off, y_off, x_size, y_size) -> np.ndarray: ...

def sample_dem_at_polygon(ds, polygon: QgsGeometry) -> np.ndarray:
    """Read only the bounding box of `polygon` from disk, mask, return values."""
```

**Betroffene Module:**
- `core/earthwork_calculator.py:_sample_dem_vectorized`
- `core/multi_surface_calculator.py` (alle `_calculate_*` Funktionen)
- `utils/terrain_intersection.py` (4 GDAL-Open-Stellen)

### Aufwand
- Helper schreiben + Tests: 2 Tage
- Migration der 5+ Aufrufer: 3 Tage
- Regression-Test (Multi-Param-Sweep auf großem DEM): 1 Tag
- **Summe: ~1 Woche**

### Sicherheitsnetz
Solange #10 nicht umgesetzt ist, sollte `dem_downloader.py` einen
Warn-Log werfen, wenn die berechnete DEM-Fläche > 10 km². Quick-Win
(<30 Min), Hilft Anwendern, Out-of-Memory zu antizipieren.

---

## Nächste konkrete Schritte (empfohlene Reihenfolge)

1. **Quick Win:** `dem_downloader.py` 10-km²-Warn-Log (siehe #10 Sicherheitsnetz)
2. **#4 abschließen:** Diff-Run gegen Spec, Tests ergänzen — 1–3 Tage
3. **Fixture-Restore für #3:** entweder Original zurück oder synthetische Mini-Version
4. **#1 ODER #2 ODER #5** wählen — alle 1.5–2 Wochen, klare Differenzierung
   gegen die Konkurrenz (siehe `RECHERCHE_2026-05-26.md` Teil 3)
5. **#9 / #10** wenn echte Performance-Probleme auftauchen, sonst zurückstellen
