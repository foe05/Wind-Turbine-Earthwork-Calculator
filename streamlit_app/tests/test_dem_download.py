"""Tests für app/core/dem_download.py — Tile-Berechnung + Mosaik (Offline)."""

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from app.core.dem_download import DEMDownloader


@pytest.fixture
def dl(tmp_path):
    return DEMDownloader(cache_dir=tmp_path / "cache")


def test_calculate_tiles_single_km(dl):
    # 10×10 m BBox bei (345_500, 5_700_500), Buffer 0 -> 1 Tile
    bbox = (345500, 5700500, 345510, 5700510)
    tiles = dl.calculate_tiles(bbox, buffer_m=0.0)
    assert len(tiles) == 1
    assert tiles[0] == "dgm1_32_345_5700_1m"


def test_calculate_tiles_with_buffer(dl):
    # 250 m Buffer um BBox am Tile-Rand -> 4 Tiles (2×2 Block)
    bbox = (345990, 5700990, 346010, 5701010)
    tiles = dl.calculate_tiles(bbox, buffer_m=250.0)
    assert len(tiles) == 4


def _write_tile(path, x_origin, y_origin, value, size=32, nodata=-9999.0):
    arr = np.full((size, size), value, dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=1,
        dtype="float32",
        transform=from_origin(x_origin, y_origin, 1, 1),
        crs="EPSG:25832",
        nodata=nodata,
    ) as ds:
        ds.write(arr, 1)


def test_create_mosaic_passthrough_for_single_tile(dl, tmp_path):
    src_path = tmp_path / "src.tif"
    _write_tile(src_path, 345000, 5700032, 100.0)
    out = tmp_path / "out.tif"
    dl.create_mosaic([str(src_path)], str(out))
    assert out.exists()
    with rasterio.open(out) as ds:
        assert ds.read(1).mean() == pytest.approx(100.0)


def test_create_mosaic_two_tiles(dl, tmp_path):
    """Zwei aneinandergrenzende Tiles, beide Werte müssen sich im Mosaik wiederfinden."""
    _write_tile(tmp_path / "tile_0.tif", 345000, 5700032, 100.0)
    _write_tile(tmp_path / "tile_1.tif", 345032, 5700032, 200.0)
    out = tmp_path / "out.tif"
    dl.create_mosaic([str(tmp_path / "tile_0.tif"), str(tmp_path / "tile_1.tif")], str(out))
    with rasterio.open(out) as ds:
        data = ds.read(1)
    unique = set(np.unique(data).tolist())
    assert 100.0 in unique
    assert 200.0 in unique


def test_create_mosaic_raises_on_all_nodata(dl, tmp_path):
    _write_tile(tmp_path / "nd.tif", 345000, 5700032, -9999.0)
    _write_tile(tmp_path / "nd2.tif", 345032, 5700032, -9999.0)
    out = tmp_path / "out.tif"
    with pytest.raises(RuntimeError, match="leer"):
        dl.create_mosaic([str(tmp_path / "nd.tif"), str(tmp_path / "nd2.tif")], str(out))


def test_cache_info_empty(dl):
    info = dl.get_cache_info()
    assert info["num_tiles"] == 0
    assert info["total_size_mb"] == 0


def test_clear_cache(dl):
    # Lege Dummy-Datei an
    (dl.cache_dir / "dgm1_32_345_5700_1m.tif").write_bytes(b"x")
    assert dl.get_cache_info()["num_tiles"] == 1
    n = dl.clear_cache()
    assert n == 1
    assert dl.get_cache_info()["num_tiles"] == 0


def test_invalid_tile_name_returns_none(dl):
    # download_tile mit kaputtem Namen darf nie raisen, nur None liefern
    assert dl.download_tile("not_a_valid_name") is None
