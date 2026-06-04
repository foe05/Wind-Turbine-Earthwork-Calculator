"""
End-to-End-Pipeline: DXF → DEM → Multi-Surface-Calc → Profile → Report.

UI-unabhängige Orchestrierung. Die Streamlit-Page ruft diese Funktion mit den
gesammelten Eingaben auf und bekommt den fertigen Ergebnis-Ordner zurück.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional

from shapely.geometry.base import BaseGeometry

from ..core.co2 import CO2Calculator, EmissionFactors
from ..core.dem_download import DEMDownloader
from ..core.dxf_import import DXFImporter
from ..core.geopackage import write_multisurface_geopackage
from ..core.landxml import LandXMLSurface, write_landxml
from ..core.mesh import (
    build_gltf_dict,
    dem_to_mesh,
    polygon_to_mesh_at_height,
    write_gltf,
    write_obj,
    write_three_js_viewer,
)
from ..core.multi_surface import (
    HeightMode,
    MultiSurfaceProject,
    MultiSurfaceResult,
    SurfaceConfig,
    SurfaceType,
    calculate_multi_surface,
)
from ..core.phases import PhasePlanner, default_phases
from ..core.profiles import generate_profiles_for_polygon
from ..core.report import render_html_report, render_overview_map
from ..core.strata import StrataCalculator, StratumMode, default_stack

log = logging.getLogger(__name__)


@dataclass
class PipelineInputs:
    """Eingaben für einen kompletten Berechnungslauf."""

    project_name: str
    crane_pad_dxf: str
    foundation_dxf: str
    fok: float
    foundation_depth: float
    gravel_thickness: float
    output_dir: str
    crs_epsg: int = 25832

    # DEM-Quelle: entweder existierender Pfad oder hoehendaten.de
    dem_path: Optional[str] = None  # falls None → hoehendaten.de
    dem_cache_dir: Optional[str] = None  # für hoehendaten.de
    dem_buffer_m: float = 250.0

    # Optimierung
    optimize_crane_height: bool = True
    search_range_below_fok: float = 0.5
    search_range_above_fok: float = 0.5
    coarse_step: float = 0.1
    fine_step: float = 0.01
    optimize_objective: str = "min_total"

    # Profile
    generate_profiles: bool = True
    profile_spacing: float = 10.0
    profile_type: str = "cross"  # 'cross' | 'long' | 'both'

    # Optionale Surfaces (DXF-Pfade)
    boom_dxf: Optional[str] = None
    rotor_storage_dxf: Optional[str] = None
    road_access_dxf: Optional[str] = None
    holms_dxf: Optional[str] = None  # Multi-Polygon → wird als list[Polygon] importiert

    # Boom-Slope-Sweep
    boom_slope_optimize: bool = True
    boom_slope_min_percent: float = -4.0
    boom_slope_max_percent: float = 4.0
    boom_slope_step_percent: float = 0.5
    boom_height_fixed: Optional[float] = None  # falls optimize=False

    # Rotor-Offset-Sweep
    rotor_offset_optimize: bool = True
    rotor_offset_min_m: float = -0.5
    rotor_offset_max_m: float = 0.5
    rotor_offset_step_m: float = 0.05
    rotor_height_fixed: Optional[float] = None

    # Road-Slope-Sweep
    road_slope_optimize: bool = True
    road_slope_min_percent: float = -8.0
    road_slope_max_percent: float = 8.0
    road_slope_step_percent: float = 1.0
    road_height_fixed: Optional[float] = None

    # Slope-Volumen
    include_slope_volume: bool = True
    slope_angle_deg: float = 45.0
    slope_sample_spacing_m: float = 1.0

    # Zusätzliche Outputs (Wave 7-9 Module)
    generate_geopackage: bool = True
    generate_landxml: bool = True
    generate_3d_viewer: bool = True
    mesh_decimation: int = 4
    compute_co2: bool = True
    co2_haul_distance_km: float = 5.0
    co2_concrete_m3: float = 0.0
    co2_steel_kg: float = 0.0
    compute_phases: bool = True
    compute_strata: bool = True
    strata_area_m2: Optional[float] = None  # default: crane platform area


@dataclass
class PipelineOutputs:
    """Pfade aller generierten Artefakte + zentrales Result."""

    project_name: str
    output_dir: str
    dem_path: str
    crane_polygon: BaseGeometry
    foundation_polygon: BaseGeometry
    result: MultiSurfaceResult
    map_image_path: str
    profile_paths: list[dict]
    html_report_path: str
    json_report_path: str
    boom_polygon: Optional[BaseGeometry] = None
    rotor_polygon: Optional[BaseGeometry] = None
    road_polygon: Optional[BaseGeometry] = None
    holm_polygons: Optional[list[BaseGeometry]] = None
    geopackage_path: Optional[str] = None
    landxml_path: Optional[str] = None
    gltf_path: Optional[str] = None
    three_viewer_path: Optional[str] = None
    co2_breakdown: Optional[dict] = None
    phase_plan: Optional[dict] = None
    strata_breakdown: Optional[dict] = None


def run_pipeline(
    inputs: PipelineInputs,
    progress: Optional[Callable[[str], None]] = None,
) -> PipelineOutputs:
    """Komplett-Workflow. progress(message) wird optional aufgerufen."""

    def _say(m: str):
        log.info(m)
        if progress:
            progress(m)

    out_dir = Path(inputs.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. DXF importieren
    _say(f"Lade Kranstellfläche aus {inputs.crane_pad_dxf}")
    crane_imp = DXFImporter(inputs.crane_pad_dxf, crs_epsg=inputs.crs_epsg)
    crane_poly, crane_meta = crane_imp.import_as_polygon()

    _say(f"Lade Fundamentfläche aus {inputs.foundation_dxf}")
    found_imp = DXFImporter(inputs.foundation_dxf, crs_epsg=inputs.crs_epsg)
    foundation_poly, found_meta = found_imp.import_as_polygon()

    # Optionale Surfaces — fail-soft: wenn DXF fehlt oder nicht parsbar, nur loggen
    boom_poly = None
    rotor_poly = None
    road_poly = None
    holm_polys = None

    def _import_optional(path: str | None, label: str):
        if not path or not Path(path).exists():
            return None
        try:
            _say(f"Lade {label} aus {path}")
            imp = DXFImporter(path, crs_epsg=inputs.crs_epsg)
            poly, _ = imp.import_as_polygon()
            return poly
        except Exception as e:
            log.warning("%s konnte nicht geladen werden: %s", label, e)
            _say(f"⚠ {label} übersprungen: {e}")
            return None

    boom_poly = _import_optional(inputs.boom_dxf, "Auslegerfläche")
    rotor_poly = _import_optional(inputs.rotor_storage_dxf, "Blattlagerfläche")
    road_poly = _import_optional(inputs.road_access_dxf, "Zufahrtsstraße")
    if inputs.holms_dxf and Path(inputs.holms_dxf).exists():
        try:
            _say(f"Lade Holme aus {inputs.holms_dxf}")
            holm_imp = DXFImporter(inputs.holms_dxf, crs_epsg=inputs.crs_epsg)
            holm_polys, _ = holm_imp.import_holms()
            _say(f"  {len(holm_polys)} Holm-Polygone")
        except Exception as e:
            log.warning("Holme konnten nicht geladen werden: %s", e)
            _say(f"⚠ Holme übersprungen: {e}")
            holm_polys = None

    # 2. DEM beschaffen
    if inputs.dem_path and Path(inputs.dem_path).exists():
        _say(f"Verwende vorhandenes DEM: {inputs.dem_path}")
        dem_path = str(inputs.dem_path)
    else:
        if not inputs.dem_cache_dir:
            raise ValueError("Weder dem_path noch dem_cache_dir gesetzt")
        _say("Lade DEM von hoehendaten.de…")
        dl = DEMDownloader(cache_dir=inputs.dem_cache_dir)
        # Bounds aller geladenen Polygone vereinigen, damit das DEM auch
        # Boom/Rotor/Road/Holme komplett abdeckt.
        all_polys = [crane_poly, foundation_poly]
        for p in (boom_poly, rotor_poly, road_poly):
            if p is not None:
                all_polys.append(p)
        if holm_polys:
            all_polys.extend(holm_polys)
        combined_bounds = _union_bounds_many(all_polys)
        mosaic_path = out_dir / "dem_mosaic.tif"
        dem_path = dl.download_for_bbox(
            combined_bounds,
            str(mosaic_path),
            buffer_m=inputs.dem_buffer_m,
            progress=progress,
        )

    # 3. Multi-Surface-Berechnung
    _say("Berechne Multi-Surface Cut/Fill…")
    project = MultiSurfaceProject(
        crane_pad=SurfaceConfig(
            SurfaceType.CRANE_PAD,
            crane_poly,
            HeightMode.OPTIMIZED if inputs.optimize_crane_height else HeightMode.FIXED,
            height_value=None if inputs.optimize_crane_height else inputs.fok,
        ),
        foundation=SurfaceConfig(
            SurfaceType.FOUNDATION, foundation_poly, HeightMode.FIXED, height_value=inputs.fok
        ),
        boom=SurfaceConfig(
            SurfaceType.BOOM,
            boom_poly,
            HeightMode.OPTIMIZED if inputs.boom_slope_optimize else HeightMode.FIXED,
            height_value=inputs.boom_height_fixed,
        ) if boom_poly is not None else None,
        rotor_storage=SurfaceConfig(
            SurfaceType.ROTOR_STORAGE,
            rotor_poly,
            HeightMode.OPTIMIZED if inputs.rotor_offset_optimize else HeightMode.FIXED,
            height_value=inputs.rotor_height_fixed,
        ) if rotor_poly is not None else None,
        road_access=SurfaceConfig(
            SurfaceType.ROAD_ACCESS,
            road_poly,
            HeightMode.OPTIMIZED if inputs.road_slope_optimize else HeightMode.FIXED,
            height_value=inputs.road_height_fixed,
        ) if road_poly is not None else None,
        holms=holm_polys,
        fok=inputs.fok,
        foundation_depth=inputs.foundation_depth,
        gravel_thickness=inputs.gravel_thickness,
        search_range_below_fok=inputs.search_range_below_fok,
        search_range_above_fok=inputs.search_range_above_fok,
        coarse_step=inputs.coarse_step,
        fine_step=inputs.fine_step,
        optimize_objective=inputs.optimize_objective,
        include_slope_volume=inputs.include_slope_volume,
        slope_angle_deg=inputs.slope_angle_deg,
        slope_sample_spacing_m=inputs.slope_sample_spacing_m,
        boom_slope_optimize=inputs.boom_slope_optimize,
        boom_slope_min_percent=inputs.boom_slope_min_percent,
        boom_slope_max_percent=inputs.boom_slope_max_percent,
        boom_slope_step_percent=inputs.boom_slope_step_percent,
        rotor_offset_optimize=inputs.rotor_offset_optimize,
        rotor_offset_min_m=inputs.rotor_offset_min_m,
        rotor_offset_max_m=inputs.rotor_offset_max_m,
        rotor_offset_step_m=inputs.rotor_offset_step_m,
        road_slope_optimize=inputs.road_slope_optimize,
        road_slope_min_percent=inputs.road_slope_min_percent,
        road_slope_max_percent=inputs.road_slope_max_percent,
        road_slope_step_percent=inputs.road_slope_step_percent,
    )
    result = calculate_multi_surface(dem_path, project)
    _say(
        f"Optimale Kranhöhe = {result.crane_optimum_height:.2f} m, "
        f"Gesamt-Cut={result.total_cut_m3:.0f} m³, Gesamt-Fill={result.total_fill_m3:.0f} m³"
    )

    # 4. Übersichtskarte (zeigt alle vorhandenen Surfaces)
    _say("Erzeuge Übersichtskarte…")
    map_path = out_dir / "map_overview.png"
    overview_layers: dict = {"crane": crane_poly, "foundation": foundation_poly}
    if boom_poly is not None:
        overview_layers["boom"] = boom_poly
    if rotor_poly is not None:
        overview_layers["rotor"] = rotor_poly
    if road_poly is not None:
        overview_layers["road"] = road_poly
    render_overview_map(dem_path, overview_layers, str(map_path))

    # 5. Profile
    profiles: list[dict] = []
    if inputs.generate_profiles:
        _say("Rendere Geländeschnitte…")
        # Plateau der Kranstellfläche = Optimum - Schotter
        crane_planum = result.crane_optimum_height - inputs.gravel_thickness
        profiles = generate_profiles_for_polygon(
            dem_path,
            crane_poly,
            plateau_height=crane_planum,
            output_dir=str(out_dir / "profiles"),
            spacing=inputs.profile_spacing,
            profile_type=inputs.profile_type,
        )

    # 6. Reports (HTML + JSON)
    _say("Schreibe Reports…")
    html_path = out_dir / "report.html"
    render_html_report(
        result,
        project_name=inputs.project_name,
        crs_epsg=inputs.crs_epsg,
        output_html=str(html_path),
        map_image_path=str(map_path),
        profile_paths=profiles,
    )
    # 7. Zusätzliche Exporte (Wave 9)
    geopackage_path = None
    if inputs.generate_geopackage:
        _say("Schreibe GeoPackage…")
        geopackage_path = write_multisurface_geopackage(
            str(out_dir / "result.gpkg"),
            {SurfaceType.CRANE_PAD: crane_poly, SurfaceType.FOUNDATION: foundation_poly},
            result=result,
            crs_epsg=inputs.crs_epsg,
        )

    landxml_path = None
    gltf_path = None
    three_viewer_path = None
    if inputs.generate_landxml or inputs.generate_3d_viewer:
        crane_planum_for_mesh = result.crane_optimum_height - inputs.gravel_thickness
        crane_mesh = polygon_to_mesh_at_height(
            list(crane_poly.exterior.coords),
            crane_planum_for_mesh,
            name="kranstellflaeche",
        )
        foundation_planum = inputs.fok - inputs.foundation_depth
        foundation_mesh = polygon_to_mesh_at_height(
            list(foundation_poly.exterior.coords),
            foundation_planum,
            name="fundamentsohle",
        )
        if inputs.generate_landxml:
            _say("Schreibe LandXML…")
            landxml_path = write_landxml(
                str(out_dir / "result.xml"),
                [
                    LandXMLSurface("Kranstellfläche", list(crane_mesh.vertices), list(crane_mesh.faces)),
                    LandXMLSurface("Fundamentsohle", list(foundation_mesh.vertices), list(foundation_mesh.faces)),
                ],
                project_name=inputs.project_name,
            )
        if inputs.generate_3d_viewer:
            _say("Erzeuge 3D-Viewer (DEM + Surfaces)…")
            terrain_mesh = dem_to_mesh(dem_path, decimation=inputs.mesh_decimation, name="terrain")
            gltf_dict = build_gltf_dict([terrain_mesh, crane_mesh, foundation_mesh])
            gltf_path = str(out_dir / "scene.gltf")
            write_gltf(gltf_path, [terrain_mesh, crane_mesh, foundation_mesh])
            three_viewer_path = write_three_js_viewer(
                str(out_dir / "scene.html"), gltf_dict, title=f"{inputs.project_name} 3D"
            )

    # 8. CO₂, Phasen, Strata (Wave 7)
    co2_breakdown = None
    if inputs.compute_co2:
        _say("Berechne CO₂-Bilanz…")
        co2 = CO2Calculator(EmissionFactors()).compute(
            cut_m3=result.total_cut_m3,
            fill_m3=result.total_fill_m3,
            haul_distance_km=inputs.co2_haul_distance_km,
            concrete_m3=inputs.co2_concrete_m3,
            steel_kg=inputs.co2_steel_kg,
        )
        co2_breakdown = co2.as_breakdown()

    phase_plan_dict = None
    if inputs.compute_phases:
        _say("Verteile Massen auf Bauphasen…")
        planner = PhasePlanner(default_phases())
        plan = planner.plan(total_cut_m3=result.total_cut_m3, total_fill_m3=result.total_fill_m3)
        phase_plan_dict = {
            "phases": [
                {
                    "name": p.name,
                    "start_day": p.start_day,
                    "end_day": p.end_day,
                    "cut_m3": round(p.cut_m3, 1),
                    "fill_m3": round(p.fill_m3, 1),
                    "cost_eur": round(p.cost_eur, 0),
                    "co2_kg": round(p.co2_kg, 0),
                }
                for p in plan.phases
            ],
            "total_cost_eur": round(plan.total_cost_eur, 0),
            "total_co2_kg": round(plan.total_co2_kg, 0),
            "total_duration_days": plan.total_duration_days,
            "unassigned_cut_m3": round(plan.unassigned_cut_m3, 1),
            "unassigned_fill_m3": round(plan.unassigned_fill_m3, 1),
        }

    strata_breakdown_dict = None
    if inputs.compute_strata:
        _say("Verteile Cut auf Bodenschichten…")
        crane_area = (
            inputs.strata_area_m2
            if inputs.strata_area_m2 is not None
            else result.surface_results[SurfaceType.CRANE_PAD].platform_area_m2
        )
        if crane_area > 0:
            strata_res = StrataCalculator(default_stack()).split(
                volume_m3=result.surface_results[SurfaceType.CRANE_PAD].cut_m3,
                area_m2=crane_area,
                mode=StratumMode.CUT,
            )
            strata_breakdown_dict = {
                "layers": [
                    {
                        "name": layer.name,
                        "depth_m": round(layer.depth_m, 3),
                        "volume_m3": round(layer.volume_m3, 1),
                        "cost_eur": round(layer.cost_eur, 0),
                        "co2_kg": round(layer.co2_kg, 0),
                    }
                    for layer in strata_res.layers
                ],
                "remainder_m3": round(strata_res.remainder_m3, 1),
                "total_cost_eur": round(strata_res.total_cost_eur, 0),
                "total_co2_kg": round(strata_res.total_co2_kg, 0),
            }

    json_path = out_dir / "result.json"
    json_path.write_text(
        json.dumps(
            {
                "project_name": inputs.project_name,
                "inputs": _serialize_inputs(inputs),
                "crane_polygon_meta": crane_meta,
                "foundation_polygon_meta": found_meta,
                "result": result.to_dict(),
                "profile_count": len(profiles),
                "co2_breakdown": co2_breakdown,
                "phase_plan": phase_plan_dict,
                "strata_breakdown": strata_breakdown_dict,
                "exports": {
                    "geopackage_path": geopackage_path,
                    "landxml_path": landxml_path,
                    "gltf_path": gltf_path,
                    "three_viewer_path": three_viewer_path,
                },
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    _say(f"Fertig — Artefakte in {out_dir}")
    return PipelineOutputs(
        project_name=inputs.project_name,
        output_dir=str(out_dir),
        dem_path=str(dem_path),
        crane_polygon=crane_poly,
        foundation_polygon=foundation_poly,
        result=result,
        map_image_path=str(map_path),
        profile_paths=profiles,
        html_report_path=str(html_path),
        json_report_path=str(json_path),
        boom_polygon=boom_poly,
        rotor_polygon=rotor_poly,
        road_polygon=road_poly,
        holm_polygons=holm_polys,
        geopackage_path=geopackage_path,
        landxml_path=landxml_path,
        gltf_path=gltf_path,
        three_viewer_path=three_viewer_path,
        co2_breakdown=co2_breakdown,
        phase_plan=phase_plan_dict,
        strata_breakdown=strata_breakdown_dict,
    )


def bundle_artifacts_zip(out_dir: str | Path, zip_path: str | Path) -> str:
    """Packt alle Output-Artefakte in ein ZIP."""
    zip_base = str(Path(zip_path).with_suffix(""))
    shutil.make_archive(zip_base, "zip", root_dir=str(out_dir))
    return f"{zip_base}.zip"


def _union_bounds(g1: BaseGeometry, g2: BaseGeometry) -> tuple[float, float, float, float]:
    minx = min(g1.bounds[0], g2.bounds[0])
    miny = min(g1.bounds[1], g2.bounds[1])
    maxx = max(g1.bounds[2], g2.bounds[2])
    maxy = max(g1.bounds[3], g2.bounds[3])
    return (minx, miny, maxx, maxy)


def _union_bounds_many(polygons: list[BaseGeometry]) -> tuple[float, float, float, float]:
    if not polygons:
        raise ValueError("Keine Polygone für Bounds")
    minx = min(p.bounds[0] for p in polygons)
    miny = min(p.bounds[1] for p in polygons)
    maxx = max(p.bounds[2] for p in polygons)
    maxy = max(p.bounds[3] for p in polygons)
    return (minx, miny, maxx, maxy)


def _serialize_inputs(inputs: PipelineInputs) -> dict:
    d = asdict(inputs)
    # Pfade als-Strings (sind schon Strings)
    return d
