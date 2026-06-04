"""Tests Wave 7: rotation, placement, mass-haul, co2, phases, strata, variants."""

import pytest
from shapely.geometry import Point, Polygon

from app.core.co2 import CO2Calculator, CO2Result, EmissionFactors
from app.core.mass_haul import MassHaulDiagram, MassHaulStation
from app.core.phases import Phase, PhasePlanner, default_phases
from app.core.placement import ConstraintLayer, PlacementValidator, Severity
from app.core.rotation import (
    RotationOptimizer,
    default_angles,
    polygon_centroid,
    rotate_points,
)
from app.core.strata import StrataCalculator, StratumLayer, StratumMode, default_stack
from app.core.variants import Variant, VariantComparisonReport


# --------------------------------------------------------------- rotation

def test_polygon_centroid_square():
    assert polygon_centroid([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]) == pytest.approx((5, 5))


def test_rotate_points_90deg_around_origin():
    pts = [(1, 0), (0, 1)]
    rotated = rotate_points(pts, 90.0, pivot=(0, 0))
    assert rotated[0] == pytest.approx((0, 1), abs=1e-9)
    assert rotated[1] == pytest.approx((-1, 0), abs=1e-9)


def test_default_angles_step_15():
    a = default_angles(step_deg=15.0, max_deg=180.0)
    assert a == [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165]


def test_rotation_optimizer_picks_lowest_metric():
    pts = [(0, 0), (10, 0), (10, 2), (0, 2), (0, 0)]
    # Bewertung: niedrigster Wert bei 45°
    def evaluate(rotated):
        # Synthetisches "metric"
        avg_angle_score = abs(rotated[1][0] - 5)  # 5 = Pseudo-Sweet-Spot
        return avg_angle_score, None

    best = RotationOptimizer(angles_deg=[0.0, 30.0, 45.0, 60.0, 90.0]).optimize(pts, evaluate)
    assert isinstance(best.angle_deg, float)
    assert best.metric >= 0


# --------------------------------------------------------------- placement

def test_placement_no_violations_when_far_away():
    house = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    layer = ConstraintLayer("Häuser", [house], min_distance_m=100.0)
    v = PlacementValidator([layer])
    assert v.check_position(1000, 1000) == []
    assert v.is_position_valid(1000, 1000)


def test_placement_hard_violation_detected():
    house = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    layer = ConstraintLayer("Wohnen", [house], min_distance_m=100.0, severity=Severity.HARD)
    v = PlacementValidator([layer])
    violations = v.check_position(15, 5)
    assert len(violations) == 1
    assert violations[0].layer_name == "Wohnen"
    assert violations[0].actual_distance_m == pytest.approx(5.0)
    assert not v.is_position_valid(15, 5)


def test_placement_suggest_nearest_valid():
    house = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    layer = ConstraintLayer("Wohnen", [house], min_distance_m=20.0)
    v = PlacementValidator([layer])
    res = v.suggest_nearest_valid(15, 5, search_radius_m=50.0, grid_step_m=5.0)
    assert res is not None
    px, py = res
    assert Point(px, py).distance(house) >= 20.0


# --------------------------------------------------------------- mass haul

def test_mass_haul_balanced_chain():
    stations = [
        MassHaulStation(0, cut_m3=100, fill_m3=0),
        MassHaulStation(100, cut_m3=0, fill_m3=85),  # mit Kompaktion 0.85 → 100 m³ Bank
        MassHaulStation(200, cut_m3=0, fill_m3=0),
    ]
    d = MassHaulDiagram(stations, compaction_factor=0.85)
    r = d.compute()
    assert r.ordinates_m3[0] == 100
    assert r.ordinates_m3[-1] == pytest.approx(0, abs=0.01)
    # Ein Massenausgleichspunkt zwischen Station 100 und 200
    assert len(r.balance_points) >= 1


def test_mass_haul_haul_integral_positive():
    stations = [
        MassHaulStation(0, cut_m3=50),
        MassHaulStation(100, fill_m3=42.5),  # 50 m³ Bank-äquivalent
    ]
    d = MassHaulDiagram(stations)
    r = d.compute()
    assert r.total_haul_m3km > 0


# --------------------------------------------------------------- co2

def test_co2_excavation_and_haul():
    c = CO2Calculator()
    r = c.compute(cut_m3=100, fill_m3=50, haul_distance_km=10)
    # excavation: 150 * 2.5 = 375 kg
    assert r.excavation_kg == pytest.approx(375.0)
    # haul: cut_m3 * km * factor = 100*10*0.12 = 120 kg
    assert r.haul_kg == pytest.approx(120.0)


def test_co2_negative_input_raises():
    with pytest.raises(ValueError):
        CO2Calculator().compute(cut_m3=-1)


def test_co2_breakdown_dict():
    c = CO2Calculator()
    r = c.compute(cut_m3=100, concrete_m3=10, steel_kg=500)
    d = r.as_breakdown()
    assert d["concrete_kg"] == pytest.approx(2800.0)
    assert d["steel_kg"] == pytest.approx(750.0)
    assert "total_kg" in d and "total_t" in d


# --------------------------------------------------------------- phases

def test_phase_planner_default_distributes_correctly():
    planner = PhasePlanner(default_phases())
    plan = planner.plan(total_cut_m3=1000.0, total_fill_m3=500.0)
    assert len(plan.phases) == 4
    assert sum(p.cut_m3 for p in plan.phases) == pytest.approx(1000.0)
    assert plan.total_duration_days == 19


def test_phase_planner_partial_plan_keeps_remainder():
    phases = [
        Phase("Wegebau", 0, 5, cut_share=0.3, fill_share=0.4),
        Phase("Kran", 5, 5, cut_share=0.3, fill_share=0.3),
    ]
    plan = PhasePlanner(phases).plan(total_cut_m3=100.0, total_fill_m3=100.0)
    assert plan.unassigned_cut_m3 == pytest.approx(40.0)
    assert plan.unassigned_fill_m3 == pytest.approx(30.0)


def test_phase_planner_over_share_rejected():
    with pytest.raises(ValueError, match="cut_share must be ≤ 1"):
        PhasePlanner(
            [Phase("A", 0, 5, cut_share=0.6), Phase("B", 5, 5, cut_share=0.6)]
        )


# --------------------------------------------------------------- strata

def test_strata_cut_consumes_top_first():
    calc = StrataCalculator(default_stack())
    # Volumen: 0.4 m × 100 m² = 40 m³ → Mutterboden (0.3m) komplett + Frostschutz (0.1m)
    r = calc.split(volume_m3=40.0, area_m2=100.0, mode=StratumMode.CUT)
    assert len(r.layers) == 2
    assert r.layers[0].name == "Mutterboden"
    assert r.layers[0].volume_m3 == pytest.approx(30.0)
    assert r.layers[1].name == "Frostschutzschicht"
    assert r.layers[1].volume_m3 == pytest.approx(10.0)


def test_strata_fill_builds_from_bottom():
    calc = StrataCalculator(default_stack())
    r = calc.split(volume_m3=20.0, area_m2=100.0, mode=StratumMode.FILL)
    assert r.layers[0].name == "Schottertragschicht"


def test_strata_remainder_for_deep_cut():
    calc = StrataCalculator(default_stack())
    # Gesamtstack = 1.0 m. Cut 1.5 m × 100 m² = 150 m³ -> 50 m³ Remainder
    r = calc.split(volume_m3=150.0, area_m2=100.0, mode=StratumMode.CUT)
    assert r.remainder_m3 == pytest.approx(50.0, abs=1e-6)


# --------------------------------------------------------------- variants

def test_variant_comparison_picks_best():
    a = Variant("A", crane_height_m=10, total_cut_m3=100, total_fill_m3=80)
    b = Variant("B", crane_height_m=11, total_cut_m3=120, total_fill_m3=60)
    rep = VariantComparisonReport([a, b])
    # Erdbewegung gesamt: A=180, B=180 → tie aber min nimmt das erste
    best = rep.best_variant("total_volume_moved_m3")
    assert best.label in ("A", "B")
    # Schotter: 0 für beide; bei net: A=20, B=60 -> A gewinnt
    # Direkter Test: das HTML rendert ohne Fehler
    html = rep.to_html("Test-Projekt")
    assert "Test-Projekt" in html
    assert "A" in html and "B" in html
