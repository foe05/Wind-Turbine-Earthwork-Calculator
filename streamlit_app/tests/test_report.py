"""Tests für app/core/report.py — HTML-Rendering ohne WeasyPrint."""

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon

from app.core.earthwork import CutFillResult
from app.core.multi_surface import MultiSurfaceResult, SurfaceType
from app.core.report import render_html_report, render_overview_map


@pytest.fixture
def dem_path(tmp_path):
    arr = np.fromfunction(lambda y, x: 100.0 + x * 0.1, (50, 50), dtype=np.float32)
    path = tmp_path / "dem.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=50,
        width=50,
        count=1,
        dtype="float32",
        transform=from_origin(0, 50, 1, 1),
        crs="EPSG:25832",
        nodata=-9999.0,
    ) as ds:
        ds.write(arr, 1)
    return path


@pytest.fixture
def sample_result():
    return MultiSurfaceResult(
        crane_optimum_height=104.7,
        fok=104.5,
        foundation_depth=3.1,
        gravel_thickness=0.6,
        surface_results={
            SurfaceType.CRANE_PAD: CutFillResult(
                plateau_height=104.1,
                cut_m3=5280.0,
                fill_m3=1763.0,
                platform_area_m2=2500.0,
                terrain_min=98.0,
                terrain_max=110.0,
                terrain_mean=104.0,
                num_pixels=2500,
            ),
            SurfaceType.FOUNDATION: CutFillResult(
                plateau_height=101.4,
                cut_m3=693.0,
                fill_m3=0.0,
                platform_area_m2=200.0,
                terrain_min=101.5,
                terrain_max=104.0,
                terrain_mean=102.8,
                num_pixels=200,
            ),
        },
    )


def test_render_overview_map(dem_path, tmp_path):
    crane = Polygon([(10, 10), (40, 10), (40, 40), (10, 40), (10, 10)])
    foundation = Polygon([(20, 20), (30, 20), (30, 30), (20, 30), (20, 20)])
    out = tmp_path / "map.png"
    render_overview_map(
        str(dem_path),
        {"crane": crane, "foundation": foundation},
        str(out),
    )
    assert out.exists()
    assert out.stat().st_size > 5000


def test_render_html_report_minimal(sample_result, tmp_path):
    out = tmp_path / "report.html"
    render_html_report(
        sample_result,
        project_name="WKA Test",
        crs_epsg=25832,
        output_html=str(out),
    )
    html = out.read_text(encoding="utf-8")
    assert "WKA Test" in html
    assert "5280" in html  # crane cut
    assert "693" in html   # foundation cut
    assert "Kranstellfläche" in html
    assert "Fundamentfläche" in html


def test_render_html_report_with_map_and_profiles(sample_result, tmp_path, dem_path):
    # Erzeuge Map
    crane = Polygon([(10, 10), (40, 10), (40, 40), (10, 40), (10, 10)])
    map_path = tmp_path / "map.png"
    render_overview_map(str(dem_path), {"crane": crane}, str(map_path))

    # Dummy-Profil-PNG
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    prof_path = tmp_path / "prof_01.png"
    fig.savefig(prof_path)
    plt.close(fig)

    out = tmp_path / "report.html"
    render_html_report(
        sample_result,
        project_name="WKA Map+Profile",
        crs_epsg=25832,
        output_html=str(out),
        map_image_path=str(map_path),
        profile_paths=[{"path": str(prof_path), "type": "Querschnitt", "index": 1, "length": 25.0}],
    )
    html = out.read_text(encoding="utf-8")
    assert "data:image/png;base64," in html
    assert "Querschnitt 01" in html
