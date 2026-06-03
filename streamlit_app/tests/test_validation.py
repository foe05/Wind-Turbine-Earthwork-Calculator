"""Tests für app/core/validation.py."""

import pytest
from shapely.geometry import MultiPolygon, Polygon

from app.core.validation import (
    ValidationError,
    validate_crs_epsg,
    validate_file_exists,
    validate_height_range,
    validate_polygon,
    validate_polygon_topology,
    validate_positive_number,
)


def test_validate_height_range_ok():
    validate_height_range(0.0, 10.0, 0.5)


def test_validate_height_range_max_le_min():
    with pytest.raises(ValidationError, match="muss > minimale Höhe"):
        validate_height_range(10.0, 10.0, 0.5)


def test_validate_height_range_step_zero():
    with pytest.raises(ValidationError, match="muss > 0"):
        validate_height_range(0.0, 10.0, 0.0)


def test_validate_height_range_too_many_scenarios():
    with pytest.raises(ValidationError, match="Zu viele"):
        validate_height_range(0.0, 100.0, 0.001)


def test_validate_positive_number_ok():
    validate_positive_number(5.0, "x", minimum=0, maximum=10)


def test_validate_positive_number_below_minimum():
    with pytest.raises(ValidationError, match="kleiner als das Minimum"):
        validate_positive_number(-1.0, "x", minimum=0)


def test_validate_positive_number_above_maximum():
    with pytest.raises(ValidationError, match="größer als das Maximum"):
        validate_positive_number(20.0, "x", maximum=10)


def test_validate_crs_epsg_utm_de():
    validate_crs_epsg(25832, expected_epsg=25832)
    validate_crs_epsg(25833, expected_epsg=25832)  # erlaubt: alle UTM-DE


def test_validate_crs_epsg_wrong_when_utm_expected():
    with pytest.raises(ValidationError, match="UTM-Zone aus DE"):
        validate_crs_epsg(4326, expected_epsg=25832)


def test_validate_crs_epsg_none():
    with pytest.raises(ValidationError, match="nicht ermittelt"):
        validate_crs_epsg(None)


def test_validate_polygon_valid():
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    validate_polygon(poly)


def test_validate_polygon_empty():
    with pytest.raises(ValidationError, match="leer"):
        validate_polygon(Polygon())


def test_validate_polygon_topology_valid():
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    validate_polygon_topology(poly)


def test_validate_polygon_topology_clockwise_rejected():
    # CW statt CCW
    poly = Polygon([(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)])
    with pytest.raises(ValidationError, match="Uhrzeigersinn"):
        validate_polygon_topology(poly)


def test_validate_polygon_topology_multipart_rejected():
    p1 = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    p2 = Polygon([(20, 0), (30, 0), (30, 10), (20, 10), (20, 0)])
    mp = MultiPolygon([p1, p2])
    with pytest.raises(ValidationError, match="Multipart"):
        validate_polygon_topology(mp)


def test_validate_file_exists_not_found(tmp_path):
    with pytest.raises(ValidationError, match="nicht gefunden"):
        validate_file_exists(tmp_path / "nope.dxf")


def test_validate_file_exists_wrong_extension(tmp_path):
    p = tmp_path / "data.txt"
    p.write_text("hi")
    with pytest.raises(ValidationError, match="Falsche Dateiendung"):
        validate_file_exists(p, extension=".dxf")


def test_validate_file_exists_ok(tmp_path):
    p = tmp_path / "data.dxf"
    p.write_text("hi")
    result = validate_file_exists(p, extension=".dxf")
    assert result == p
