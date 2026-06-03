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

from ..core.dem_download import DEMDownloader
from ..core.dxf_import import DXFImporter
from ..core.multi_surface import (
    HeightMode,
    MultiSurfaceProject,
    MultiSurfaceResult,
    SurfaceConfig,
    SurfaceType,
    calculate_multi_surface,
)
from ..core.profiles import generate_profiles_for_polygon
from ..core.report import render_html_report, render_overview_map

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

    # 2. DEM beschaffen
    if inputs.dem_path and Path(inputs.dem_path).exists():
        _say(f"Verwende vorhandenes DEM: {inputs.dem_path}")
        dem_path = str(inputs.dem_path)
    else:
        if not inputs.dem_cache_dir:
            raise ValueError("Weder dem_path noch dem_cache_dir gesetzt")
        _say("Lade DEM von hoehendaten.de…")
        dl = DEMDownloader(cache_dir=inputs.dem_cache_dir)
        combined_bounds = _union_bounds(crane_poly, foundation_poly)
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
        fok=inputs.fok,
        foundation_depth=inputs.foundation_depth,
        gravel_thickness=inputs.gravel_thickness,
        search_range_below_fok=inputs.search_range_below_fok,
        search_range_above_fok=inputs.search_range_above_fok,
        coarse_step=inputs.coarse_step,
        fine_step=inputs.fine_step,
        optimize_objective=inputs.optimize_objective,
    )
    result = calculate_multi_surface(dem_path, project)
    _say(
        f"Optimale Kranhöhe = {result.crane_optimum_height:.2f} m, "
        f"Gesamt-Cut={result.total_cut_m3:.0f} m³, Gesamt-Fill={result.total_fill_m3:.0f} m³"
    )

    # 4. Übersichtskarte
    _say("Erzeuge Übersichtskarte…")
    map_path = out_dir / "map_overview.png"
    render_overview_map(
        dem_path,
        {"crane": crane_poly, "foundation": foundation_poly},
        str(map_path),
    )

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


def _serialize_inputs(inputs: PipelineInputs) -> dict:
    d = asdict(inputs)
    # Pfade als-Strings (sind schon Strings)
    return d
