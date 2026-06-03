"""Tests für app/core/earthwork.py mit synthetischem DEM."""

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon

from app.core.earthwork import (
    coarse_then_fine_sweep,
    cut_fill_for_polygon,
    height_sweep,
)


@pytest.fixture
def synthetic_dem(tmp_path):
    """40×40 m DEM, Höhe = 100 m flach, Pixel = 1 m."""
    arr = np.full((40, 40), 100.0, dtype=np.float32)
    path = tmp_path / "dem_flat.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=40,
        width=40,
        count=1,
        dtype="float32",
        transform=from_origin(0, 40, 1, 1),
        crs="EPSG:25832",
        nodata=-9999.0,
    ) as ds:
        ds.write(arr, 1)
    return path


@pytest.fixture
def square_polygon():
    return Polygon([(5, 5), (15, 5), (15, 15), (5, 15), (5, 5)])


def test_cut_fill_flat_at_terrain_height(synthetic_dem, square_polygon):
    """Plateau auf Geländeniveau -> Cut=Fill=0."""
    r = cut_fill_for_polygon(str(synthetic_dem), square_polygon, plateau_height=100.0)
    assert r.cut_m3 == 0.0
    assert r.fill_m3 == 0.0
    assert r.platform_area_m2 == pytest.approx(100.0, abs=1.0)


def test_cut_fill_below_terrain(synthetic_dem, square_polygon):
    """Plateau 5 m unter dem flachen Gelände -> nur Cut, kein Fill."""
    r = cut_fill_for_polygon(str(synthetic_dem), square_polygon, plateau_height=95.0)
    assert r.cut_m3 == pytest.approx(500.0, abs=1.0)  # 100 m² × 5 m
    assert r.fill_m3 == 0.0


def test_cut_fill_above_terrain(synthetic_dem, square_polygon):
    """Plateau 5 m über flachem Gelände -> nur Fill."""
    r = cut_fill_for_polygon(str(synthetic_dem), square_polygon, plateau_height=105.0)
    assert r.cut_m3 == 0.0
    assert r.fill_m3 == pytest.approx(500.0, abs=1.0)


def test_cut_fill_slope_balance(tmp_path, square_polygon):
    """DEM mit linearem Anstieg: Plateau auf Mittelwert -> Cut = Fill."""
    arr = np.fromfunction(lambda y, x: 100.0 + x * 0.5, (40, 40), dtype=np.float32)
    path = tmp_path / "dem_slope.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=40,
        width=40,
        count=1,
        dtype="float32",
        transform=from_origin(0, 40, 1, 1),
        crs="EPSG:25832",
        nodata=-9999.0,
    ) as ds:
        ds.write(arr, 1)

    r = cut_fill_for_polygon(str(path), square_polygon, plateau_height=104.75)
    # Mittelwert von x*0.5 für x in 5..14 ist (5+14)/2*0.5 = 4.75 -> 104.75
    assert r.cut_m3 == pytest.approx(r.fill_m3, abs=2.0)


def test_height_sweep_finds_terrain_mean(tmp_path, square_polygon):
    arr = np.fromfunction(lambda y, x: 100.0 + x * 0.5, (40, 40), dtype=np.float32)
    path = tmp_path / "dem.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=40,
        width=40,
        count=1,
        dtype="float32",
        transform=from_origin(0, 40, 1, 1),
        crs="EPSG:25832",
        nodata=-9999.0,
    ) as ds:
        ds.write(arr, 1)
    h, best, all_ = height_sweep(str(path), square_polygon, 100.0, 110.0, 0.25, "min_net")
    # Mittelwert ≈ 104.75
    assert h == pytest.approx(104.75, abs=0.25)
    assert abs(best.net_m3) < abs(all_[0].net_m3)


def test_coarse_then_fine_sweep(tmp_path, square_polygon):
    arr = np.fromfunction(lambda y, x: 100.0 + x * 0.5, (40, 40), dtype=np.float32)
    path = tmp_path / "dem.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=40,
        width=40,
        count=1,
        dtype="float32",
        transform=from_origin(0, 40, 1, 1),
        crs="EPSG:25832",
        nodata=-9999.0,
    ) as ds:
        ds.write(arr, 1)
    h, best, all_ = coarse_then_fine_sweep(
        str(path), square_polygon, 100.0, 110.0,
        coarse_step=0.5, fine_step=0.05, objective="min_net"
    )
    assert h == pytest.approx(104.75, abs=0.05)


def test_nodata_skipped(tmp_path, square_polygon):
    arr = np.full((40, 40), 100.0, dtype=np.float32)
    # Polygon (5,5)-(15,15) world coords mit from_origin(0,40,1,1)
    # → Pixel-Rows 25..34, Cols 5..14. Loch (6x6) in arr[25:31, 5:11]
    arr[25:31, 5:11] = -9999.0
    path = tmp_path / "dem.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=40,
        width=40,
        count=1,
        dtype="float32",
        transform=from_origin(0, 40, 1, 1),
        crs="EPSG:25832",
        nodata=-9999.0,
    ) as ds:
        ds.write(arr, 1)
    r = cut_fill_for_polygon(str(path), square_polygon, plateau_height=95.0)
    # 100 Pixel im Polygon, 36 davon nodata -> 64 valid
    assert r.num_pixels == 64
    assert r.cut_m3 == pytest.approx(320.0, abs=1.0)  # 64 × 5 m × 1 m²
