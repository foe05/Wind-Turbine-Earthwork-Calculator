"""Tests für app/core/geometry.py (portiert aus utils/geometry_utils.py)."""

import math

import pytest
from shapely.geometry import LineString, Point, Polygon

from app.core import geometry as g


@pytest.fixture
def square_10m():
    """10×10 m Quadrat mit Untergrenze bei (0,0)."""
    return Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])


@pytest.fixture
def rectangle_20x5():
    """20×5 m Rechteck — Hauptachse entlang X."""
    return Polygon([(0, 0), (20, 0), (20, 5), (0, 5), (0, 0)])


def test_point_distance():
    assert g.point_distance((0, 0), (3, 4)) == pytest.approx(5.0)


def test_find_nearest_point():
    pt, dist, idx = g.find_nearest_point((0, 0), [(10, 0), (3, 4), (5, 5)])
    assert idx == 1
    assert dist == pytest.approx(5.0)
    assert pt == (3, 4)


def test_find_nearest_point_with_max_distance():
    result = g.find_nearest_point((0, 0), [(100, 0)], max_distance=10)
    assert result == (None, None, None)


def test_centroid_square(square_10m):
    c = g.get_centroid(square_10m)
    assert (c.x, c.y) == pytest.approx((5.0, 5.0))


def test_polygon_radius(square_10m):
    # Mittelpunkt (5,5), entferntester Vertex (0,0)/(10,10) etc. => √50
    assert g.get_polygon_radius(square_10m) == pytest.approx(math.sqrt(50))


def test_get_polygon_vertices(square_10m):
    verts = g.get_polygon_vertices(square_10m)
    assert len(verts) == 5  # 4 Ecken + Schluss
    assert verts[0] == verts[-1]


def test_get_polygon_boundary_returns_linestring(square_10m):
    boundary = g.get_polygon_boundary(square_10m)
    assert isinstance(boundary, LineString)
    assert boundary.length == pytest.approx(40.0)


def test_orientation_horizontal_rectangle(rectangle_20x5):
    angle = g.get_polygon_orientation(rectangle_20x5)
    assert angle == pytest.approx(0.0, abs=0.1)


def test_orientation_vertical_rectangle():
    rect = Polygon([(0, 0), (5, 0), (5, 20), (0, 20), (0, 0)])
    angle = g.get_polygon_orientation(rect)
    assert angle == pytest.approx(90.0, abs=0.1)


def test_perpendicular_direction():
    assert g.perpendicular_direction(45.0) == pytest.approx(135.0)
    assert g.perpendicular_direction(300.0) == pytest.approx(30.0)


def test_buffer_geometry(square_10m):
    buf = g.buffer_geometry(square_10m, 1.0)
    minx, miny, maxx, maxy = buf.bounds
    assert minx == pytest.approx(-1.0)
    assert maxx == pytest.approx(11.0)


def test_create_bbox_with_buffer(square_10m):
    bbox = g.create_bbox_with_buffer(square_10m, 2.0)
    assert bbox == (-2.0, -2.0, 12.0, 12.0)


def test_get_polygon_width_at_point(rectangle_20x5):
    # Breite des 20×5-Rechtecks senkrecht zur X-Achse am Punkt (10, 2.5) = 5
    width = g.get_polygon_width_at_point(rectangle_20x5, Point(10, 2.5), direction_angle=0.0)
    assert width == pytest.approx(5.0, abs=0.01)


def test_calculate_slope_height_down():
    # 5 % Gefälle über 20 m -> -1.0 m
    assert g.calculate_slope_height(100.0, 20.0, 5.0, "down") == pytest.approx(99.0)


def test_calculate_slope_height_up():
    assert g.calculate_slope_height(100.0, 20.0, 5.0, "up") == pytest.approx(101.0)


def test_identify_surface_at_point(square_10m, rectangle_20x5):
    surfaces = {"crane": square_10m, "boom": rectangle_20x5}
    # Punkt (5,5) liegt in beiden (crane gewinnt, weil erste)
    assert g.identify_surface_at_point(Point(5, 5), surfaces) == "crane"
    # Punkt außerhalb beider
    assert g.identify_surface_at_point(Point(50, 50), surfaces) is None


def test_calculate_terrain_slope_flat():
    elevs = [100.0, 100.0, 100.0]
    dists = [0.0, 10.0, 20.0]
    assert g.calculate_terrain_slope(elevs, dists) == pytest.approx(0.0)


def test_calculate_terrain_slope_rising():
    elevs = [100.0, 101.0, 102.0]  # 1 m je 10 m = 10 %
    dists = [0.0, 10.0, 20.0]
    assert g.calculate_terrain_slope(elevs, dists) == pytest.approx(10.0)


def test_create_radial_lines():
    lines = g.create_radial_lines(Point(0, 0), 10.0, num_lines=4)
    assert len(lines) == 4
    # Erste Linie: Winkel 0 -> Endpunkt (10, 0)
    assert lines[0].coords[1] == pytest.approx((10.0, 0.0), abs=1e-6)


def test_oriented_bounding_box(square_10m):
    info = g.create_oriented_bounding_box([square_10m], main_angle=0.0, buffer_percent=0)
    assert info is not None
    assert info["length"] == pytest.approx(10.0, abs=0.01)
    assert info["width"] == pytest.approx(10.0, abs=0.01)


def test_create_cross_sections_over_bbox(rectangle_20x5):
    info = g.create_oriented_bounding_box([rectangle_20x5], main_angle=0.0, buffer_percent=0)
    sections = g.create_cross_sections_over_bbox(info, spacing=5.0)
    assert len(sections) >= 4  # 0, 5, 10, 15, 20 entlang 20 m


def test_create_perpendicular_cross_sections(rectangle_20x5):
    sections = g.create_perpendicular_cross_sections(rectangle_20x5, spacing=5.0)
    assert len(sections) >= 3
    # Alle haben dieselbe Länge (einheitlich)
    lengths = {round(s["length"], 3) for s in sections}
    assert len(lengths) == 1


def test_find_connection_edge_shared():
    # Zwei aneinandergrenzende Quadrate
    a = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    b = Polygon([(10, 0), (20, 0), (20, 10), (10, 10), (10, 0)])
    edge, length = g.find_connection_edge(a, b, tolerance=0.5)
    assert length == pytest.approx(10.0, abs=0.1)


def test_get_edge_direction():
    edge = LineString([(0, 0), (10, 0)])  # entlang X-Achse
    assert g.get_edge_direction(edge) == pytest.approx(0.0)
    edge2 = LineString([(0, 0), (0, 10)])  # entlang Y-Achse
    assert g.get_edge_direction(edge2) == pytest.approx(90.0)


def test_calculate_distance_from_edge():
    edge = LineString([(0, 0), (10, 0)])  # entlang X-Achse
    # Punkt 5 m über der Edge, Messrichtung "nach oben" (90°) -> +5
    d = g.calculate_distance_from_edge(Point(5, 5), edge, direction=90.0)
    assert d == pytest.approx(5.0, abs=0.001)
