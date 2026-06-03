"""Tests für app/core/profiles.py."""

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString, Polygon

from app.core.profiles import (
    generate_profiles_for_polygon,
    plot_section,
    sample_dem_along_line,
)


@pytest.fixture
def dem_path(tmp_path):
    """100×100 m DEM mit linearem Anstieg in x."""
    arr = np.fromfunction(lambda y, x: 100.0 + x * 0.1, (100, 100), dtype=np.float32)
    path = tmp_path / "dem.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=100,
        width=100,
        count=1,
        dtype="float32",
        transform=from_origin(0, 100, 1, 1),
        crs="EPSG:25832",
        nodata=-9999.0,
    ) as ds:
        ds.write(arr, 1)
    return path


def test_sample_dem_along_horizontal_line(dem_path):
    """Linie entlang X bei y=50 sollte rising elevations liefern."""
    line = LineString([(10, 50), (90, 50)])
    d, z = sample_dem_along_line(str(dem_path), line, step=1.0)
    assert d.size > 50
    assert z[0] < z[-1]  # rising
    assert z[0] == pytest.approx(101.0, abs=0.5)
    assert z[-1] == pytest.approx(109.0, abs=0.5)


def test_plot_section_produces_png(tmp_path):
    distances = np.linspace(0, 100, 101)
    elevations = 100 + 0.1 * distances
    out = tmp_path / "section.png"
    plot_section(distances, elevations, 105.0, "Test", out)
    assert out.exists()
    assert out.stat().st_size > 1000  # echtes PNG


def test_generate_profiles_for_polygon_cross(dem_path, tmp_path):
    poly = Polygon([(20, 20), (80, 20), (80, 80), (20, 80), (20, 20)])
    out_dir = tmp_path / "profiles"
    results = generate_profiles_for_polygon(
        str(dem_path),
        poly,
        plateau_height=105.0,
        output_dir=str(out_dir),
        spacing=15.0,
        profile_type="cross",
    )
    assert len(results) >= 2
    assert all(r["type"] == "Querschnitt" for r in results)
    for r in results:
        assert r["path"].endswith(".png")
        assert (out_dir / Path(r["path"]).name).exists()


def test_generate_profiles_for_polygon_both(dem_path, tmp_path):
    poly = Polygon([(20, 20), (80, 20), (80, 80), (20, 80), (20, 20)])
    out_dir = tmp_path / "profiles"
    results = generate_profiles_for_polygon(
        str(dem_path),
        poly,
        plateau_height=105.0,
        output_dir=str(out_dir),
        spacing=15.0,
        profile_type="both",
    )
    types = {r["type"] for r in results}
    assert "Querschnitt" in types
    assert "Längsprofil" in types


