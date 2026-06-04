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
| #1 Constraint-basierte Platzierung | ✅ **Komplett** — Core-Modul (17 Tests) + GUI-Tab „🚧 Restriktionen" + Workflow-Preflight: `workflow_runner._run_constraint_preflight` prüft den Kran-Centroid vor dem DEM-Download, harte Verletzung bricht ab, weiche warnt | — |
| #2 Park-weite Batch-Optimierung | ✅ **Komplett** — Transport-LP + Kandidaten-MILP + N-Best-Extraktion + Report-Anbindung (`park_optimizer.solve`/`solve_milp`; `MultiSurfaceCalculator.find_n_best`; Multi-Site-Report zeigt Park-Transport-Sektion via LP; 24 Tests grün). MILP-im-Report (statt LP) bräuchte Kandidaten-Persistierung pro Lauf — optionaler Ausbau | — |
| #4 Terrain-Intersection & Differenz-Raster | ✅ **~95 % implementiert** (`utils/terrain_intersection.py`, 622 LOC; wired in `multi_surface_calculator.py:3301+`); 14-Layer/7-Raster-Output, Cleanup-Härtung + Test-Skelett ergänzt | klein (3D-Renderer-Konfig optional) |
| #5 3D-Mesh-Export & 3D-Viewer | ✅ **Komplett** — OBJ + STL (ASCII/binär) + glTF + selbst-enthaltener Three.js-Viewer (`core/mesh_exporter.py`, 25 Tests); `workflow_runner._export_meshes` schreibt OBJ je Fläche + `scene.gltf` + `viewer.html` nach `WKA_*_meshes/`. Geneigte Flächen werden noch flach approximiert (optionaler Ausbau) | — |
| #9 DXF-Import langsam (>1000 Polylinien) | 🟢 **Großteils entschärft:** `connect_polylines` nutzt im Normalfall effizientes Shapely (`linemerge`/`unary_union`); die O(n²)-Sequenz ist nur selten erreichter Fallback. Die vektorisierten Volumen-Schleifen beschleunigen zusätzlich große Flächen | klein (Fallback-Index optional) |
| #10 DEM-RAM (>10 km²) | 🟢 **Großteils entschärft:** DEM-Sampling liest bereits nur das Polygon-Fenster (`_sample_dem_vectorized`), nicht das ganze Band; LRU-Cache vermeidet N-faches Re-Sampling im Sweep; Cut/Fill-Schleifen vektorisiert; Warn-Log bei >10 km² | klein (Legacy-Pfad + terrain_intersection windowen) |

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

### Konkurrenz-Features als Neuentwicklung (Stand 2026-05-29)

Vier weitere QGIS-unabhängige Kern-Module aus der Wettbewerbsanalyse
(`RECHERCHE_2026-05-26.md` Teil 3), jeweils mit plain-Python-Tests:

- **`core/mass_haul.py`** — Mass-Haul-Diagramm: kumulative Massenkurve
  (Compaction-adjustiert), Balance-Punkte, Free-Haul/Overhaul-Split. **11/11.**
  *(Inspiration: DynaRoad, Carlson Takeoff.)*
- **`core/rotation_optimizer.py`** — Kranstellflächen-Rotation: Polygon-Rotation
  um Centroid + Winkel-Sweep mit injiziertem Evaluate-Callback (QGIS-aware
  Caller liefert die DEM-Bewertung). **16/16.** *(Inspiration: windfarmbop,
  Wind Farm Optimizer.)*
- **`core/co2_balance.py`** — CO₂-Bilanz: Erdmassen × LKW-km × Faktor +
  Beton/Stahl, konfigurierbare Emissionsfaktoren. **8/8.** *(Inspiration: EC3,
  One Click LCA.)*
- **`core/landxml_export.py`** — LandXML-1.2-TIN-Surface-Export für
  Machine-Control (Trimble/Topcon/Leica) + BIM. Stdlib-XML, Adapter aus
  `MeshData`. **9/9.** *(Inspiration: RoadEng, Civil 3D.)*

### Weitere Feature-Module (Stand 2026-06-01)

Fünf zusätzliche QGIS-unabhängige Module aus der erweiterten Recherche,
jeweils mit plain-Python-Tests:

- **`core/strata_quantities.py`** — Bodenschichten-Aufschlüsselung
  (Mutterboden → Frostschutz → Schotter), Kosten + CO₂ je Schicht. **14/14.**
- **`core/construction_phases.py`** — Bauphasen-Planung mit Default-Plan
  (Wegebau → Kranstellfläche → Fundament → Restarbeiten). **11/11.**
- **`core/slope_stability_export.py`** — Querschnitt-XML mit Material- +
  Piezometer-Daten als Slide/GeoStudio-Interchange. **12/12.**
- **`core/variant_comparison.py`** — Side-by-Side HTML-Vergleich mehrerer
  Planungs-Varianten. **9/9.**
- `docs/PYTHON_API.md` — dokumentierte Public-API für headless Nutzung aller
  QGIS-unabhängigen Module.

**Anbindung (2026-06-01):**
- Strata + Bauphasen: automatische Sektionen im Single-Site-Report
  (Default-Stacks/-Phasen, abschaltbar durch Konfiguration).
- Slope-Stability: opt-in Workflow-Schritt → `slope_stability.xml` aus den
  Längsprofilen.
- Variantenvergleich: bleibt als Python-API; Beispielcode in `PYTHON_API.md`.
- **Drohnen-DEM:** GUI-Filepicker für ein lokales DEM (GeoTIFF) im
  Ausgabe-Tab; STEP 4 überspringt die hoehendaten.de-Abfrage wenn ein Pfad
  gesetzt ist.

**GUI-/Workflow-Anbindung erledigt (2026-05-29):**
- **LandXML:** `workflow_runner._export_meshes` schreibt zusätzlich `surfaces.xml`
  (TIN je Fläche) aus den gesammelten MeshData.
- **CO₂:** `report_generator._generate_co2_section` zeigt die CO₂-Bilanz im
  Einzelstandort-Report (Beton aus Fundamentfläche×-tiefe, Stahl 120 kg/m³,
  Transport 5 km Default).
- **Rotation:** opt-in Checkbox „Optimale Plattform-Ausrichtung" →
  `calculator.analyze_crane_rotation` (non-fatal) → Report-Sektion mit bestem
  Winkel + Einsparung. Ändert die berechnete Geometrie nicht.
- **Mass-Haul:** opt-in Checkbox „Massenmassenkurve" →
  `workflow_runner._compute_mass_haul` aus dem repräsentativen Längsprofil
  (per-Streifenbreite) → Report-Sektion mit Bilanz + Ausgleichspunkten.

Beide opt-in Analysen sind default aus, non-fatal gekapselt, und ändern den
Hauptlauf nicht. **Restrisiko:** die QGIS-abhängigen Pfade (DEM-Sampling der
rotierten Fläche, Profil-Stationierung) sind erst im echten QGIS testbar.

Was noch fehlt, um die Features in der GUI nutzbar zu machen:
1. **#1 GUI + Preflight:** ✅ **Komplett (2026-05-29).** Tab „🚧 Restriktionen"
   in `gui/main_dialog.py` (drei Kategorien mit QgsMapLayerComboBox + Distanz +
   Hard/Soft, interaktiver Positions-Checker). **Workflow-Preflight erledigt:**
   `_on_start` baut den Validator im Main-Thread und reicht ihn als
   `params['placement_validator']` weiter; `workflow_runner._run_constraint_preflight`
   prüft den Kran-Centroid nach dem DXF-Import / vor dem DEM-Download — harte
   Verletzung wirft (Abbruch), weiche warnt nur.
2. **#2 MILP-Stufe + N-Best:** ✅ **Solver + Datenquelle erledigt (2026-05-29).**
   `core/park_optimizer.py::solve_milp()` wählt per `scipy.optimize.milp`
   gemeinsam einen Höhen-Kandidaten pro Standort UND den Transportplan
   (Datenklassen `SiteCandidate`, `SiteWithCandidates`, `ParkMILPSolution`).
   `MultiSurfaceCalculator.find_n_best(n, min_spacing_m)` liefert die
   Top-N Höhen-Kandidaten (Metrik-sortiert, Spacing-gefiltert) als Datenquelle.
   Mapping: `cut_excess = max(0, net_volume)`, `fill_need = max(0, -net_volume)`.
   **Report-Anbindung erledigt (2026-05-29):** der Multi-Site-Report ruft
   `_compute_park_optimization` (LP über die ausgewählten Standort-Bilanzen)
   auf und zeigt die Sektion „🚚 Park-Transport-Optimierung" mit Transportplan
   + Einsparung. **Optionaler Ausbau:** MILP statt LP im Report — bräuchte
   Persistierung der `find_n_best`-Kandidaten pro Lauf (heute hält `SiteData`
   nur die eine gewählte Bilanz).
3. **#5 Workflow-Anbindung + Formate:** ✅ **Komplett (2026-05-29).**
   `core/workflow_runner.py::_export_meshes()` schreibt nach der
   GeoPackage-Speicherung je ein OBJ pro Fläche + Terrain-OBJ (decimated DEM),
   dazu ein kombiniertes `scene.gltf` (Y-up, recentred, farbige Materialien
   pro Fläche) und einen selbst-enthaltenen `viewer.html` (Three.js via CDN,
   glTF inline eingebettet → kein lokales CORS-Problem) in `WKA_<x>_<y>_meshes/`.
   Writer in `mesh_exporter`: `write_obj`, `write_stl` (ASCII/binär),
   `write_gltf`/`build_gltf_dict`, `write_three_js_viewer`. Auto-on, per Param
   `export_obj=False` abschaltbar, non-fatal. **Optionaler Ausbau:** geneigte
   Flächen werden noch flach auf Kranhöhe approximiert (per-pixel Soll-Raster
   nötig für exakte Schrägmeshes).

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

### Stand (2026-05-29)
Nach Code-Audit ist der Engpass kleiner als befürchtet:
- `connect_polylines` nutzt im **Normalfall** Shapelys `linemerge`/`unary_union`
  (`_connect_with_shapely`) und einen Graph-Ansatz — beide effizient.
- Die O(n²)-Methode `_connect_polylines_sequential` ist nur **Last-Resort-Fallback**,
  wenn sowohl Shapely- als auch Graph-Ansatz scheitern (selten).
- `detect_coordinate_system` ist ein einzelner O(n)-Vertex-Scan, kein O(n²).

### Verbleibend (optional, niedrige Priorität)
- Endpoint-Hash-/Grid-Index für die Sequenz-Fallback-Verbindung (O(n²)→~O(n)),
  nur falls echte Dateien diesen Pfad häufig treffen — vorher mit `cProfile`
  gegen eine reale 1000+-Polylinien-Datei profilen.
- Vertex-Extraktion via `np.fromiter` statt `.append()`.

**Aufwand:** klein, nur bei nachgewiesenem Bedarf.

---

## #10 — DEM-RAM bei >10 km²

### Stand (2026-05-29)
Mehrere Maßnahmen umgesetzt:
- ✅ **Windowed Reads:** `_sample_dem_vectorized` liest schon immer nur das
  Polygon-Bounding-Box-Fenster (`read_band_as_array(band, x_off, y_off, w, h)`),
  nicht das gesamte 10 000×10 000-Band. Der RAM-Peak skaliert mit der
  Flächengröße, nicht der DEM-Größe.
- ✅ **Sample-Cache:** kleiner LRU-Cache (`MultiSurfaceCalculator._dem_sample_cache`,
  maxsize 16) verhindert N-faches Re-Sampling derselben (höhen-invarianten)
  Flächen-Polygone über den Höhen-Sweep. Bounded → kein RAM-Blowup durch
  transiente Böschungs-Buffer.
- ✅ **Vektorisierte Cut/Fill-Schleifen** (Kranstellfläche, Fundament): keine
  Python-Schleife über jeden Pixel mehr → weniger temporäre Objekte, schneller.
  Math-Äquivalenz mit `tests/test_cutfill_vectorization.py` bewiesen (10 Tests).
- ✅ **Warn-Log** bei >10 km² in `dem_downloader.calculate_tiles`.

### Verbleibend (optional, niedrige Priorität)
- `_sample_dem_legacy` (Fallback) und die 4 `gdal.Open`-Stellen in
  `utils/terrain_intersection.py` lesen noch volle Bänder — windowing dort
  würde den seltenen Fallback/Großflächen-Fall weiter entschärfen.
- Geneigte Cut/Fill-Schleifen (Ausleger/Rotor/Zufahrt) sind noch
  Python-Schleifen (per-Pixel-Zielhöhe); Vektorisierung möglich, aber
  korrektheitskritischer — vor Umsetzung gegen die Fixture absichern.

---

## Nächste konkrete Schritte (empfohlene Reihenfolge)

1. **Quick Win:** `dem_downloader.py` 10-km²-Warn-Log (siehe #10 Sicherheitsnetz)
2. **#4 abschließen:** Diff-Run gegen Spec, Tests ergänzen — 1–3 Tage
3. **Fixture-Restore für #3:** entweder Original zurück oder synthetische Mini-Version
4. **#1 ODER #2 ODER #5** wählen — alle 1.5–2 Wochen, klare Differenzierung
   gegen die Konkurrenz (siehe `RECHERCHE_2026-05-26.md` Teil 3)
5. **#9 / #10** wenn echte Performance-Probleme auftauchen, sonst zurückstellen
