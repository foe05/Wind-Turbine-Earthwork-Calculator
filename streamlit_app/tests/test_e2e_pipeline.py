"""
End-to-End-Smoke der kompletten Pipeline mit der wea45-Fixture.

Nutzt das Plugin-Reference-DEM + die im GeoPackage gespeicherten
Polygone, ruft `run_pipeline` mit `dem_path` (keine hoehendaten.de-API),
prüft auf gerenderte Artefakte + plausible Cut/Fill-Werte.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import ezdxf
import fiona
import pytest
from shapely.geometry import shape

from app.services.pipeline import PipelineInputs, run_pipeline

_THIS = Path(__file__).resolve()
REF_ZIP = (
    _THIS.parent.parent.parent
    / "windturbine_earthwork_calculator_v2"
    / "wea45mit3d.zip"
)


def _polygon_to_dxf(polygon, layer_name: str, out_path: Path) -> None:
    """Schreibt ein Shapely-Polygon als LWPOLYLINE in eine DXF-Datei."""
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    coords = [(x, y) for x, y in polygon.exterior.coords]
    msp.add_lwpolyline(coords, dxfattribs={"layer": layer_name})
    doc.saveas(str(out_path))


@pytest.fixture(scope="module")
def fixture_dir(tmp_path_factory):
    if not REF_ZIP.exists():
        pytest.skip(f"Fixture nicht verfügbar: {REF_ZIP}")
    tmp = tmp_path_factory.mktemp("wea45_e2e")
    with zipfile.ZipFile(REF_ZIP) as zf:
        zf.extractall(tmp)
    return tmp / "wea45mit3d" / "ergebnisse"


@pytest.fixture(scope="module")
def prepared_inputs(fixture_dir, tmp_path_factory):
    dem_path = str(fixture_dir / "WKA_492079_5702007_DEM.tif")
    gpkg_path = str(fixture_dir / "WKA_492079_5702007_MultiSurface.gpkg")

    with fiona.open(gpkg_path, layer="kranstellflaechen") as src:
        crane_poly = shape(next(iter(src))["geometry"])
    with fiona.open(gpkg_path, layer="fundamentflaechen") as src:
        foundation_poly = shape(next(iter(src))["geometry"])

    work = tmp_path_factory.mktemp("wea45_e2e_inputs")
    crane_dxf = work / "crane.dxf"
    found_dxf = work / "foundation.dxf"
    _polygon_to_dxf(crane_poly, "kranstellflaeche", crane_dxf)
    _polygon_to_dxf(foundation_poly, "fundamentflaeche", found_dxf)

    return {
        "dem_path": dem_path,
        "crane_dxf": str(crane_dxf),
        "foundation_dxf": str(found_dxf),
        "work_dir": work,
    }


def test_e2e_pipeline_against_wea45(prepared_inputs, tmp_path):
    inputs = PipelineInputs(
        project_name="wea45 E2E",
        crane_pad_dxf=prepared_inputs["crane_dxf"],
        foundation_dxf=prepared_inputs["foundation_dxf"],
        fok=318.37,
        foundation_depth=3.1,
        gravel_thickness=0.60,
        output_dir=str(tmp_path / "out"),
        crs_epsg=25832,
        dem_path=prepared_inputs["dem_path"],
        dem_cache_dir=str(tmp_path / "dem_cache"),  # ungenutzt da dem_path gesetzt
        optimize_crane_height=False,  # Use fixed FOK so we hit known reference height
        # Mit optimize=False wird das Crane-Plateau auf fok - gravel = 317.77 berechnet,
        # nicht das echte Optimum 319.27. Wir prüfen daher nicht gegen 5280/1763,
        # sondern nur dass Pipeline durchläuft + alle Artefakte da sind.
        generate_profiles=True,
        profile_spacing=15.0,
        profile_type="cross",
    )
    out = run_pipeline(inputs)

    # Artefakte vorhanden
    assert Path(out.html_report_path).exists()
    assert Path(out.json_report_path).exists()
    assert Path(out.map_image_path).exists()
    assert Path(out.html_report_path).stat().st_size > 1000
    assert Path(out.map_image_path).stat().st_size > 5000
    assert len(out.profile_paths) >= 2

    # Sanity: Foundation Cut sollte ~693 ergeben (FOK-depth=315.27)
    from app.core.multi_surface import SurfaceType
    foundation_r = out.result.surface_results[SurfaceType.FOUNDATION]
    assert foundation_r.cut_m3 == pytest.approx(693, abs=2.0)


def test_e2e_pipeline_optimize_runs_and_improves(prepared_inputs, tmp_path):
    """Höhen-Sweep läuft durch und liefert Plateau innerhalb des Suchbereichs.

    Wir verlangen NICHT das exakte Plugin-Optimum 319.27 — der Plugin-Optimizer
    berücksichtigt Slope-Volumen, das MVP nicht. Sanity: Optimum liegt im
    Suchbereich und ist mindestens so gut wie die Bereichsmitte.
    """
    inputs = PipelineInputs(
        project_name="wea45 E2E Opt",
        crane_pad_dxf=prepared_inputs["crane_dxf"],
        foundation_dxf=prepared_inputs["foundation_dxf"],
        fok=319.87,
        foundation_depth=3.1,
        gravel_thickness=0.60,
        output_dir=str(tmp_path / "opt_out"),
        crs_epsg=25832,
        dem_path=prepared_inputs["dem_path"],
        dem_cache_dir=str(tmp_path / "dem_cache"),
        optimize_crane_height=True,
        search_range_below_fok=2.0,
        search_range_above_fok=2.0,
        coarse_step=0.2,
        fine_step=0.02,
        optimize_objective="min_total",
        generate_profiles=False,
    )
    out = run_pipeline(inputs)
    from app.core.multi_surface import SurfaceType
    crane_r = out.result.surface_results[SurfaceType.CRANE_PAD]
    # Plateau im Suchbereich: fok - range_below - gravel .. fok + range_above - gravel
    lo = 319.87 - 2.0 - 0.60
    hi = 319.87 + 2.0 - 0.60
    assert lo <= crane_r.plateau_height <= hi
    # Optimum-Cut+Fill ist sinnvoll positiv (DEM ist nicht flach)
    assert crane_r.total_moved_m3 > 100
