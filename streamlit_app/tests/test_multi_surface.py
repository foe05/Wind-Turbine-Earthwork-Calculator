"""Tests für app/core/multi_surface.py mit synthetischem DEM."""

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon

from app.core.multi_surface import (
    HeightMode,
    MultiSurfaceProject,
    SurfaceConfig,
    SurfaceType,
    calculate_multi_surface,
)


@pytest.fixture
def dem_path(tmp_path):
    """100×100 m flaches DEM @ 100 m ü.NN."""
    arr = np.full((100, 100), 100.0, dtype=np.float32)
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


@pytest.fixture
def crane_polygon():
    return Polygon([(20, 20), (40, 20), (40, 40), (20, 40), (20, 20)])


@pytest.fixture
def foundation_polygon():
    return Polygon([(60, 60), (70, 60), (70, 70), (60, 70), (60, 60)])


def test_multi_surface_flat_terrain(dem_path, crane_polygon, foundation_polygon):
    """Flaches Gelände @ 100m, FOK auf 100m, depth=3 -> nur Foundation hat Cut."""
    project = MultiSurfaceProject(
        crane_pad=SurfaceConfig(SurfaceType.CRANE_PAD, crane_polygon, HeightMode.FIXED, height_value=100.0),
        foundation=SurfaceConfig(SurfaceType.FOUNDATION, foundation_polygon, HeightMode.FIXED, height_value=100.0),
        fok=100.0,
        foundation_depth=3.0,
        gravel_thickness=0.5,
    )
    res = calculate_multi_surface(str(dem_path), project)
    # Foundation: 100 m² × 3 m = 300 m³ Cut
    assert res.surface_results[SurfaceType.FOUNDATION].cut_m3 == pytest.approx(300.0, abs=2.0)
    # Crane Pad: Plateau = 100 - 0.5 = 99.5 -> 400 m² × 0.5 m = 200 m³ Cut
    assert res.surface_results[SurfaceType.CRANE_PAD].cut_m3 == pytest.approx(200.0, abs=2.0)


def test_multi_surface_optimize_finds_terrain(dem_path, crane_polygon, foundation_polygon):
    """Höhen-Sweep findet das Minimum bei Plateau = Geländeniveau."""
    project = MultiSurfaceProject(
        crane_pad=SurfaceConfig(SurfaceType.CRANE_PAD, crane_polygon, HeightMode.OPTIMIZED),
        foundation=SurfaceConfig(SurfaceType.FOUNDATION, foundation_polygon, HeightMode.FIXED, height_value=100.0),
        fok=100.5,  # damit Sweep bei 100m das Minimum trifft
        foundation_depth=3.0,
        gravel_thickness=0.5,
        search_range_below_fok=1.0,
        search_range_above_fok=1.0,
        coarse_step=0.1,
        fine_step=0.01,
        optimize_objective="min_total",
    )
    res = calculate_multi_surface(str(dem_path), project)
    # Crane-Plateau-Soll = 100.0 (gleich Gelände), Optimum = 100.5 m
    assert res.crane_optimum_height == pytest.approx(100.5, abs=0.05)
    assert res.surface_results[SurfaceType.CRANE_PAD].cut_m3 == pytest.approx(0.0, abs=2.0)
    assert res.surface_results[SurfaceType.CRANE_PAD].fill_m3 == pytest.approx(0.0, abs=2.0)


def test_multi_surface_to_dict(dem_path, crane_polygon, foundation_polygon):
    project = MultiSurfaceProject(
        crane_pad=SurfaceConfig(SurfaceType.CRANE_PAD, crane_polygon, HeightMode.FIXED, height_value=100.0),
        foundation=SurfaceConfig(SurfaceType.FOUNDATION, foundation_polygon, HeightMode.FIXED, height_value=100.0),
        fok=100.0,
        foundation_depth=3.0,
    )
    res = calculate_multi_surface(str(dem_path), project)
    d = res.to_dict()
    assert "surfaces" in d
    assert SurfaceType.FOUNDATION.value in d["surfaces"]
    assert "total_cut_m3" in d
