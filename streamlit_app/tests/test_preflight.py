"""
Tests für die Vorabprüfung.

Der Zweck des Preflights ist, teure Schritte gar nicht erst zu starten.
Entsprechend prüfen diese Tests nicht nur, *dass* etwas auffliegt, sondern
auch, dass gültige Eingaben ungehindert durchgehen — eine zu strenge
Validierung wäre schlimmer als gar keine.
"""

from __future__ import annotations

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon

from app.core.validation import ValidationError
from app.services.preflight import (
    MAX_SITE_EXTENT_M,
    check_dem,
    check_geometries,
    check_inputs,
)
from app.services.pipeline import PipelineInputs

CRANE = Polygon([(535000, 5680000), (535040, 5680000), (535040, 5680030), (535000, 5680030)])
FOUNDATION = Polygon([(535010, 5680010), (535030, 5680010), (535030, 5680025), (535010, 5680025)])


@pytest.fixture
def inputs(tmp_path):
    crane_dxf = tmp_path / "kran.dxf"
    found_dxf = tmp_path / "fundament.dxf"
    crane_dxf.touch()
    found_dxf.touch()
    return PipelineInputs(
        project_name="Preflight-Test",
        crane_pad_dxf=str(crane_dxf),
        foundation_dxf=str(found_dxf),
        fok=120.0,
        foundation_depth=3.0,
        gravel_thickness=0.4,
        output_dir=str(tmp_path / "out"),
    )


# --------------------------------------------------------------- Parameter

def test_gueltige_eingaben_gehen_durch(inputs):
    check_inputs(inputs)


def test_fehlende_dxf_datei(inputs):
    inputs.crane_pad_dxf = "/gibt/es/nicht.dxf"
    with pytest.raises(ValidationError):
        check_inputs(inputs)


def test_falsches_crs(inputs):
    inputs.crs_epsg = 4326  # WGS84 — hoehendaten.de will UTM
    with pytest.raises(ValidationError, match="CRS"):
        check_inputs(inputs)


def test_negative_fundamenttiefe(inputs):
    inputs.foundation_depth = -1.0
    with pytest.raises(ValidationError, match="Fundament-Tiefe"):
        check_inputs(inputs)


def test_sweep_mit_verdrehtem_bereich(inputs):
    inputs.boom_slope_min_percent = 4.0
    inputs.boom_slope_max_percent = -4.0
    with pytest.raises(ValidationError, match="Ausleger-Neigung"):
        check_inputs(inputs)


def test_sweep_mit_zu_vielen_schritten(inputs):
    """Schutz vor dem versehentlichen Stundenlauf."""
    inputs.road_slope_min_percent = -100.0
    inputs.road_slope_max_percent = 100.0
    inputs.road_slope_step_percent = 0.001
    with pytest.raises(ValidationError, match="zu viele"):
        check_inputs(inputs)


@pytest.mark.parametrize("winkel", [0.0, 90.0, -5.0, 91.0])
def test_unmoeglicher_boeschungswinkel(inputs, winkel):
    inputs.slope_angle_deg = winkel
    with pytest.raises(ValidationError, match="Böschungswinkel"):
        check_inputs(inputs)


# -------------------------------------------------------------- Geometrien

def test_zusammengehoerige_flaechen_gehen_durch():
    check_geometries(CRANE, FOUNDATION)


def test_flaechen_aus_verschiedenen_anlagen():
    """Der eigentliche Zweck: das fliegt auf, bevor ein DEM geladen wird."""
    weit_weg = Polygon(
        [(x + MAX_SITE_EXTENT_M * 2, y) for x, y in FOUNDATION.exterior.coords]
    )
    with pytest.raises(ValidationError, match="km von der Kranstellfläche"):
        check_geometries(CRANE, weit_weg)


def test_entartete_geometrie():
    linie = Polygon([(0, 0), (10, 0), (20, 0), (0, 0)])  # Fläche 0
    with pytest.raises(ValidationError):
        check_geometries(CRANE, linie)


def test_optionale_flaeche_wird_mitgeprueft():
    weit_weg = Polygon([(x + 50_000, y) for x, y in FOUNDATION.exterior.coords])
    with pytest.raises(ValidationError, match="Zufahrt"):
        check_geometries(CRANE, FOUNDATION, {"Zufahrt": weit_weg})


# --------------------------------------------------------------------- DEM

def _write_dem(path, west, north, size=200, res=1.0, epsg=25832):
    daten = np.full((size, size), 120.0, dtype="float32")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=1,
        dtype="float32",
        crs=f"EPSG:{epsg}",
        transform=from_origin(west, north, res, res),
    ) as dst:
        dst.write(daten, 1)
    return str(path)


def test_passendes_dem_geht_durch(inputs, tmp_path):
    dem = _write_dem(tmp_path / "dem.tif", west=534900, north=5680200)
    check_dem(dem, inputs, [CRANE, FOUNDATION])


def test_dem_deckt_standort_nicht_ab(inputs, tmp_path):
    """Sonst würde der Sweep über nodata rechnen."""
    dem = _write_dem(tmp_path / "dem.tif", west=600000, north=5700000)
    with pytest.raises(ValidationError, match="deckt Geometrie nicht ab"):
        check_dem(dem, inputs, [CRANE, FOUNDATION])


def test_dem_im_falschen_crs(inputs, tmp_path):
    dem = _write_dem(tmp_path / "dem.tif", west=534900, north=5680200, epsg=25833)
    inputs.crs_epsg = 25832
    # 25833 ist eine gültige DE-UTM-Zone — validate_crs_epsg lässt sie durch.
    # Die Abdeckungsprüfung greift trotzdem, weil die Koordinaten nicht passen.
    check_dem(dem, inputs, [CRANE, FOUNDATION])


def test_dem_zu_grob(inputs, tmp_path):
    dem = _write_dem(tmp_path / "dem.tif", west=534000, north=5681000, res=25.0)
    with pytest.raises(ValidationError, match="Auflösung"):
        check_dem(dem, inputs, [CRANE, FOUNDATION])
