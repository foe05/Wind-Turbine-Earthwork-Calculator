# Public Python API

This plugin's `core/` modules are deliberately split into two layers:

1. **QGIS-aware modules** (`workflow_runner`, `multi_surface_calculator`,
   `report_generator`, `dem_downloader`, `dxf_importer`, …) — usable from
   inside QGIS / the Processing toolbox.
2. **QGIS-independent core libraries** (`park_optimizer`, `placement_constraints`,
   `mesh_exporter`, `mass_haul`, `rotation_optimizer`, `co2_balance`,
   `landxml_export`, `strata_quantities`, `construction_phases`,
   `slope_stability_export`, `variant_comparison`) — pure Python with NumPy /
   SciPy / Shapely.

The latter group is what you import from headless Python scripts, batch
portfolio runs, CI jobs, or your own GUI/web service. None of them touch
`qgis.core`. Each one ships its own `tests/test_*.py` and stays
backwards-compatible: existing keyword arguments are not renamed silently.

The path-loading trick used in the test suite is **only** required there,
because `core/__init__.py` eager-imports `surface_types` (which imports
`qgis.core`). In your own code, just import the module file directly:

```python
import sys
sys.path.insert(0, "windturbine_earthwork_calculator_v2/core")
import park_optimizer, mass_haul, mesh_exporter   # etc.
```

In a QGIS Python console or processing script, normal package imports work:

```python
from windturbine_earthwork_calculator_v2.core import park_optimizer
```

---

## Park optimisation

```python
from windturbine_earthwork_calculator_v2.core.park_optimizer import (
    SiteEarthwork, SiteWithCandidates, SiteCandidate,
    TransportConfig, ParkOptimizer,
)

cfg = TransportConfig(
    cost_per_m3_km=0.5,
    dump_cost_per_m3=0.0,
    external_gravel_cost_per_m3=45.0,
    max_distance_km=20.0,
)

# Transport-only LP across sites with a single fixed balance each.
sites = [
    SiteEarthwork(site_id="WEA01", x=492000, y=5702000, cut_excess_m3=1200),
    SiteEarthwork(site_id="WEA02", x=494000, y=5703000, fill_need_m3=900),
]
sol = ParkOptimizer(cfg).solve(sites)
for f in sol.flows:
    print(f.from_site, "→", f.to_site, f.volume_m3, "m³")
print("Savings:", sol.savings_eur, "€")

# Joint candidate-selection MILP: each site offers several height options.
sites_milp = [
    SiteWithCandidates("WEA01", 492000, 5702000, [
        SiteCandidate(cut_excess_m3=1200, fill_need_m3=0, site_cost_eur=0,
                      label="h=319.5m"),
        SiteCandidate(cut_excess_m3=0,    fill_need_m3=0, site_cost_eur=1500,
                      label="balanced"),
    ]),
    # … one entry per site
]
sol = ParkOptimizer(cfg).solve_milp(sites_milp)
for site_id, cand in sol.chosen_candidate.items():
    print(site_id, cand.label)
```

## Placement constraints

```python
from windturbine_earthwork_calculator_v2.core.placement_constraints import (
    PlacementValidator, ConstraintLayer, Severity, default_angles,
)
from shapely.geometry import Polygon, LineString

validator = PlacementValidator([
    ConstraintLayer("Wohnbebauung", [Polygon([(0,0),(50,0),(50,50),(0,50)])],
                    min_distance_m=600, severity=Severity.HARD),
    ConstraintLayer("Strassen", [LineString([(0,200),(1000,200)])],
                    min_distance_m=50, severity=Severity.SOFT),
])

for v in validator.check_position(700, 100):
    print(v.layer_name, v.severity.value, v.shortfall_m, "m short")

candidate = validator.suggest_nearest_valid(700, 100, search_radius_m=500)
```

## 3D mesh export (OBJ / STL / glTF + viewer)

```python
from windturbine_earthwork_calculator_v2.core import mesh_exporter

pad = mesh_exporter.polygon_to_mesh_at_height(
    [(0,0),(10,0),(10,10),(0,10)], height=320.0, name="kranstellflaeche",
)
mesh_exporter.write_obj("kranstellflaeche.obj", pad)
mesh_exporter.write_stl("kranstellflaeche.stl", pad, binary=True)
mesh_exporter.write_gltf("kranstellflaeche.gltf", [pad])
mesh_exporter.write_three_js_viewer(
    "viewer.html",
    mesh_exporter.build_gltf_dict([pad]),
    title="WEA Test",
)
```

## LandXML export (for Trimble / Topcon / Leica / Civil 3D)

```python
from windturbine_earthwork_calculator_v2.core import landxml_export, mesh_exporter

mesh = mesh_exporter.polygon_to_mesh_at_height(
    [(0,0),(10,0),(10,10),(0,10)], 320.0, name="kranstellflaeche")
landxml_export.write_landxml(
    "surfaces.xml",
    [landxml_export.surface_from_mesh("kranstellflaeche", mesh)],
    project_name="Windpark Nord",
)
```

## Mass-haul

```python
from windturbine_earthwork_calculator_v2.core.mass_haul import (
    MassHaulStation, MassHaulDiagram,
)

stations = [
    MassHaulStation(0,     cut_m3=100),
    MassHaulStation(50,    cut_m3=50),
    MassHaulStation(100,   fill_m3=150),
]
result = MassHaulDiagram(stations).compute(free_haul_distance_m=20.0)
print(result.balance_points)
print("Free haul:", result.free_haul_m3km, "m³·km")
print("Overhaul:", result.overhaul_m3km, "m³·km")
```

## Rotation optimisation

The angle-sweep is QGIS-independent; the evaluation callback can use whatever
geometry/DEM library you prefer.

```python
from windturbine_earthwork_calculator_v2.core.rotation_optimizer import (
    RotationOptimizer, polygon_centroid,
)

pad = [(0,0),(20,0),(20,10),(0,10)]

def evaluate(rotated):
    # … compute cut/fill against your DEM, return (metric, payload)
    return some_metric, payload

best = RotationOptimizer().optimize(pad, evaluate)
print("Best angle:", best.angle_deg, "metric:", best.metric)
```

## CO₂ balance

```python
from windturbine_earthwork_calculator_v2.core.co2_balance import (
    CO2Calculator, EmissionFactors,
)

factors = EmissionFactors(concrete_kg_per_m3=260.0)  # project-specific EPD
result = CO2Calculator(factors).compute(
    cut_m3=8500, fill_m3=2400, gravel_m3=150,
    haul_distance_km=5.0,
    concrete_m3=350, steel_kg=42000,
)
print(result.total_t, "t CO₂e")
print(result.as_breakdown())
```

## Strata / Bodenschichten

```python
from windturbine_earthwork_calculator_v2.core.strata_quantities import (
    StrataCalculator, StratumLayer, StratumMode, default_stack,
)

calc = StrataCalculator(default_stack())  # Mutterboden / Frostschutz / Schotter
cut = calc.split(volume_m3=400.0, area_m2=1000.0, mode=StratumMode.CUT)
for q in cut.layers:
    print(q.name, q.volume_m3, "m³", q.cost_eur, "€")
```

## Construction phases

```python
from windturbine_earthwork_calculator_v2.core.construction_phases import (
    PhasePlanner, default_phases,
)

plan = PhasePlanner(default_phases(),
                    cut_cost_per_m3=8, fill_cost_per_m3=12).plan(
    total_cut_m3=5000, total_fill_m3=2000,
)
for p in plan.phases:
    print(p.name, "day", p.start_day, "-", p.end_day, p.cost_eur, "€")
```

## Slope-stability export

```python
from windturbine_earthwork_calculator_v2.core.slope_stability_export import (
    SlopeSection, ProfilePoint, write_slope_xml, default_materials,
)

section = SlopeSection(
    name="kranstellflaeche_long",
    profile=[ProfilePoint(0.0, 320.0, 318.5),
             ProfilePoint(50.0, 321.5, 318.5)],
    materials=default_materials(),
)
write_slope_xml("slope.xml", [section])
```

## Variant comparison

```python
from windturbine_earthwork_calculator_v2.core.variant_comparison import (
    Variant, VariantComparisonReport,
)

variants = [
    Variant("319.5 m / 0°",  crane_height_m=319.5,
            total_cut_m3=6500, total_fill_m3=2400, total_cost_eur=180_000),
    Variant("320.0 m / 45°", crane_height_m=320.0,
            total_cut_m3=5800, total_fill_m3=2800, total_cost_eur=170_000),
]
VariantComparisonReport(variants).write("vergleich.html", "Windpark Nord")
```

---

## Running the test suite

The QGIS-independent modules are all unit-tested. From a plain Python env
(no QGIS installation needed):

```bash
pip install --user pytest shapely scipy numpy
pytest windturbine_earthwork_calculator_v2/tests/test_park_optimizer.py \
       windturbine_earthwork_calculator_v2/tests/test_placement_constraints.py \
       windturbine_earthwork_calculator_v2/tests/test_mesh_exporter.py \
       windturbine_earthwork_calculator_v2/tests/test_mass_haul.py \
       windturbine_earthwork_calculator_v2/tests/test_rotation_optimizer.py \
       windturbine_earthwork_calculator_v2/tests/test_co2_balance.py \
       windturbine_earthwork_calculator_v2/tests/test_landxml_export.py \
       windturbine_earthwork_calculator_v2/tests/test_strata_quantities.py \
       windturbine_earthwork_calculator_v2/tests/test_construction_phases.py \
       windturbine_earthwork_calculator_v2/tests/test_slope_stability_export.py \
       windturbine_earthwork_calculator_v2/tests/test_variant_comparison.py
```

GDAL-bound mesh tests skip cleanly when `osgeo` is missing.

## Stability notes

These public APIs follow the same convention used in the rest of the plugin:
existing keyword arguments will not be renamed without a deprecation cycle,
and dataclass field names are part of the contract. New optional parameters
may be added with safe defaults.
