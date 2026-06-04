"""Tests Wave 8: uncertainty, soil_stabilization, bgr_api."""

import numpy as np
import pytest

from app.core.bgr_api import BGR_SOIL_TYPE_MAPPING, BGRSoilAPI
from app.core.soil_stabilization import (
    DIN_SOIL_CLASSIFICATION,
    GRAVEL_THICKNESS_TABLE,
    SoilStabilizationCalculator,
)
from app.core.uncertainty import (
    TerrainType,
    UncertaintyAnalysisResult,
    UncertaintyConfig,
    UncertaintyResult,
    run_uncertainty_analysis,
    sample_parameters,
)


# --------------------------------------------------------------- uncertainty

def test_uncertainty_config_terrain_defaults():
    c_flat = UncertaintyConfig.for_terrain(TerrainType.FLAT)
    c_steep = UncertaintyConfig.for_terrain(TerrainType.STEEP)
    assert c_flat.dem_vertical_std == pytest.approx(0.075)
    assert c_steep.dem_vertical_std == pytest.approx(0.15)


def test_uncertainty_result_from_samples():
    samples = np.array([100, 105, 110, 95, 102, 98, 103, 99, 101, 100])
    r = UncertaintyResult.from_samples(samples)
    assert r.mean == pytest.approx(101.3, abs=0.5)
    assert r.std > 0
    assert r.percentile_50 == pytest.approx(np.median(samples))
    assert r.coefficient_of_variation > 0
    assert len(r.samples) == 10


def test_sample_parameters_lhs_normal():
    config = UncertaintyConfig(
        dem_vertical_std=0.1,
        foundation_depth_std=0.1,
        num_samples=500,
        random_seed=42,
    )
    samples = sample_parameters(config, {"foundation_depth": 3.0})
    assert "dem_bias" in samples
    assert "foundation_depth" in samples
    assert len(samples["dem_bias"]) == 500
    # Mittelwert sollte nahe dem Sollwert sein
    assert samples["foundation_depth"].mean() == pytest.approx(3.0, abs=0.05)


def test_run_uncertainty_analysis_linear():
    """Wenn output = 2 * dem_bias + 5 * foundation_depth, müssen Sensitivitäten erkennbar sein."""
    config = UncertaintyConfig(
        dem_vertical_std=0.1,
        foundation_depth_std=0.5,
        num_samples=300,
        random_seed=42,
    )

    def evaluate(params):
        dem = params.get("dem_bias", 0.0)
        depth = params.get("foundation_depth", 3.0)
        return {"volume": 2.0 * dem + 5.0 * depth}

    result = run_uncertainty_analysis(
        config, {"foundation_depth": 3.0}, evaluate, output_names=["volume"]
    )
    assert "volume" in result.outputs
    # Sensitivität: foundation_depth korreliert stärker (Std 0.5 * 5 = 2.5)
    # als dem_bias (Std 0.1 * 2 = 0.2)
    sens = result.sensitivities["volume"]
    assert sens["foundation_depth"].correlation > sens["dem_bias"].correlation
    # Ranking: foundation_depth zuerst
    ranking = result.get_sensitivity_ranking("volume")
    assert ranking[0][0] == "foundation_depth"


# --------------------------------------------------------------- soil stabilization

def test_lime_dosage_for_clay():
    c = SoilStabilizationCalculator()
    r = c.estimate_lime_dosage(
        soil_type="Ton",
        water_content=20.0,
        optimum_water=16.0,
        current_ev2=20.0,
        target_ev2=60.0,
    )
    # Basis 5%, Wasserüberschuss 4% * 0.3 = +1.2%, kein ev2_corr (Ratio = 3.0, nicht > 3.0)
    assert r["percentage"] == pytest.approx(6.2, abs=0.1)
    assert r["kg_per_m2"] > 0
    assert r["expected_ev2_after"] > 20


def test_lime_dosage_for_sand_not_recommended():
    c = SoilStabilizationCalculator()
    r = c.estimate_lime_dosage("Sand", 10, 10, 30)
    assert r["percentage"] == 0.0
    assert "nicht empfohlen" in r["note"]


def test_gravel_layer_thickness_lookup():
    c = SoilStabilizationCalculator()
    # Ev2 = 90 -> Dicke 0.25 m
    r = c.calculate_gravel_layer(subgrade_ev2=90.0, area_m2=100.0)
    assert r["thickness_m"] == 0.25
    # Volume = 0.25 * 100 * 1.15 = 28.75
    assert r["volume_m3"] == pytest.approx(28.75, abs=0.1)


def test_din18196_classification():
    c = SoilStabilizationCalculator()
    assert c.soil_type_from_din18196("TM") == "Ton"
    assert c.soil_type_from_din18196("SU") == "Sand"
    assert c.soil_type_from_din18196("xx") is None


# --------------------------------------------------------------- bgr api

def test_bgr_coord_transform_utm_to_wgs():
    # Punkt nahe Münster (UTM32: ~404000, 5760000) -> sollte ~7.6°E, 51.96°N werden
    lon, lat = BGRSoilAPI._to_wgs84(404000, 5760000, 25832)
    assert 6 < lon < 8
    assert 51 < lat < 53


def test_bgr_endpoint_unavailable_handling(monkeypatch):
    """Bei HTTP 404 muss endpoint_unavailable flag gesetzt werden."""
    api = BGRSoilAPI(timeout=2)

    class FakeResp:
        status_code = 404

        def raise_for_status(self):
            raise RuntimeError("404")

        def json(self):
            return {}

    monkeypatch.setattr("requests.get", lambda *a, **kw: FakeResp())
    r = api.query_soil_at_point(404000, 5760000)
    assert not r["success"]
    assert r.get("endpoint_unavailable") is True


def test_bgr_no_features_returns_useful_message(monkeypatch):
    api = BGRSoilAPI(timeout=2)

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"features": []}

    monkeypatch.setattr("requests.get", lambda *a, **kw: FakeResp())
    r = api.query_soil_at_point(404000, 5760000)
    assert not r["success"]
    assert "Keine Bodendaten" in r["error"]
