"""Tests Wave 10: Slope-Volumen-Approximation + Multi-Surface-Vollausbau."""

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
from app.core.slope_volume import SlopeVolumeResult, estimate_slope_volume


@pytest.fixture
def flat_dem(tmp_path):
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
def sloped_dem(tmp_path):
    """100x100 m DEM mit linearem Anstieg in x: z = 100 + 0.1 * x."""
    arr = np.fromfunction(lambda y, x: 100.0 + x * 0.1, (100, 100), dtype=np.float32)
    path = tmp_path / "dem_slope.tif"
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


def test_slope_volume_flat_terrain_zero(flat_dem):
    """Flaches Gelände + Plateau auf gleicher Höhe → kein Slope."""
    polygon = Polygon([(20, 20), (40, 20), (40, 40), (20, 40), (20, 20)])
    r = estimate_slope_volume(str(flat_dem), polygon, plateau_height=100.0)
    assert r.cut_m3 == pytest.approx(0.0, abs=0.1)
    assert r.fill_m3 == pytest.approx(0.0, abs=0.1)


def test_slope_volume_invalid_angle():
    polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    with pytest.raises(ValueError, match="slope_angle"):
        estimate_slope_volume("/dev/null", polygon, 100.0, slope_angle_deg=0)


def test_slope_volume_sloped_dem_has_both_cut_and_fill(sloped_dem):
    """Sloped DEM mit Plateau auf mittlerer Höhe → Slope hat Cut und Fill."""
    polygon = Polygon([(10, 10), (90, 10), (90, 90), (10, 90), (10, 10)])
    r = estimate_slope_volume(str(sloped_dem), polygon, plateau_height=105.0)
    # Polygon umfasst die volle Sloped Range; Cut & Fill müssen beide > 0 sein
    assert r.cut_m3 > 0
    assert r.fill_m3 > 0
    assert r.slope_area_m2 > 0


def test_multi_surface_with_slope_volume(sloped_dem):
    crane = Polygon([(10, 10), (50, 10), (50, 50), (10, 50), (10, 10)])
    foundation = Polygon([(60, 60), (70, 60), (70, 70), (60, 70), (60, 60)])
    project = MultiSurfaceProject(
        crane_pad=SurfaceConfig(SurfaceType.CRANE_PAD, crane, HeightMode.FIXED, height_value=104.0),
        foundation=SurfaceConfig(SurfaceType.FOUNDATION, foundation, HeightMode.FIXED, height_value=104.0),
        fok=104.0,
        foundation_depth=2.0,
        gravel_thickness=0.5,
        include_slope_volume=True,
        slope_angle_deg=45.0,
    )
    res = calculate_multi_surface(str(sloped_dem), project)
    # Slope-Result muss für beide Surfaces vorhanden sein
    assert SurfaceType.CRANE_PAD in res.slope_results
    assert SurfaceType.FOUNDATION in res.slope_results
    # Total müssen platform + slope kombinieren
    assert res.total_cut_m3 >= res.total_platform_cut_m3
    assert res.total_slope_cut_m3 >= 0


def test_multi_surface_with_boom_sweep(flat_dem):
    crane = Polygon([(10, 10), (40, 10), (40, 40), (10, 40), (10, 10)])
    foundation = Polygon([(50, 50), (60, 50), (60, 60), (50, 60), (50, 50)])
    boom = Polygon([(40, 10), (80, 10), (80, 40), (40, 40), (40, 10)])
    project = MultiSurfaceProject(
        crane_pad=SurfaceConfig(SurfaceType.CRANE_PAD, crane, HeightMode.FIXED, height_value=100.0),
        foundation=SurfaceConfig(SurfaceType.FOUNDATION, foundation, HeightMode.FIXED, height_value=100.0),
        boom=SurfaceConfig(SurfaceType.BOOM, boom, HeightMode.OPTIMIZED),
        fok=100.0,
        foundation_depth=2.0,
        gravel_thickness=0.5,
        include_slope_volume=False,
        boom_slope_optimize=True,
        boom_slope_min_percent=-4.0,
        boom_slope_max_percent=4.0,
        boom_slope_step_percent=1.0,
    )
    res = calculate_multi_surface(str(flat_dem), project)
    assert SurfaceType.BOOM in res.surface_results
    # Bei flachem Gelände sollte das beste Boom-Slope nahe 0 % sein
    assert abs(res.boom_slope_percent) < 1.5


def test_multi_surface_with_rotor_offset_sweep(flat_dem):
    crane = Polygon([(10, 10), (40, 10), (40, 40), (10, 40), (10, 10)])
    foundation = Polygon([(50, 50), (60, 50), (60, 60), (50, 60), (50, 50)])
    rotor = Polygon([(70, 10), (90, 10), (90, 30), (70, 30), (70, 10)])
    project = MultiSurfaceProject(
        crane_pad=SurfaceConfig(SurfaceType.CRANE_PAD, crane, HeightMode.FIXED, height_value=100.0),
        foundation=SurfaceConfig(SurfaceType.FOUNDATION, foundation, HeightMode.FIXED, height_value=100.0),
        rotor_storage=SurfaceConfig(SurfaceType.ROTOR_STORAGE, rotor, HeightMode.OPTIMIZED),
        fok=100.0,
        foundation_depth=2.0,
        gravel_thickness=0.5,
        include_slope_volume=False,
        rotor_offset_optimize=True,
        rotor_offset_min_m=-0.5,
        rotor_offset_max_m=0.5,
        rotor_offset_step_m=0.1,
    )
    res = calculate_multi_surface(str(flat_dem), project)
    assert SurfaceType.ROTOR_STORAGE in res.surface_results
    # Flaches Gelände -> Offset ~ 0
    assert abs(res.rotor_offset_m) < 0.2
