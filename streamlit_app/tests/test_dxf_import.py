"""Tests für app/core/dxf_import.py (synthetisches DXF via ezdxf)."""

import ezdxf
import pytest
from shapely.geometry import Polygon

from app.core.dxf_import import DXFImporter


def _make_square_dxf(tmp_path, layer_name="CRANE"):
    """Schreibt ein 10×10 m Quadrat als LWPOLYLINE in den Layer."""
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline(
        [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)],
        dxfattribs={"layer": layer_name},
    )
    path = tmp_path / "square.dxf"
    doc.saveas(str(path))
    return path


def _make_open_lines_dxf(tmp_path, layer_name="CRANE"):
    """Vier LINE-Entities, die zusammen ein Quadrat ergeben (Lücken testen)."""
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 0), dxfattribs={"layer": layer_name})
    msp.add_line((10, 0), (10, 10), dxfattribs={"layer": layer_name})
    msp.add_line((10, 10), (0, 10), dxfattribs={"layer": layer_name})
    msp.add_line((0, 10), (0, 0), dxfattribs={"layer": layer_name})
    path = tmp_path / "lines.dxf"
    doc.saveas(str(path))
    return path


def _make_two_polygons_dxf(tmp_path, layer_name="HOLMS"):
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline(
        [(0, 0), (5, 0), (5, 5), (0, 5), (0, 0)], dxfattribs={"layer": layer_name}
    )
    msp.add_lwpolyline(
        [(10, 10), (15, 10), (15, 15), (10, 15), (10, 10)],
        dxfattribs={"layer": layer_name},
    )
    path = tmp_path / "two.dxf"
    doc.saveas(str(path))
    return path


def test_load_and_layers(tmp_path):
    path = _make_square_dxf(tmp_path)
    imp = DXFImporter(path, tolerance=0.01, crs_epsg=25832)
    imp.load_dxf()
    assert imp.doc is not None
    assert "CRANE" in imp.get_available_layers()


def test_extract_lwpolyline(tmp_path):
    path = _make_square_dxf(tmp_path)
    imp = DXFImporter(path)
    polylines = imp.extract_polylines()
    assert len(polylines) == 1
    assert len(polylines[0]) == 5


def test_validate_entity_types_warns_on_arc(tmp_path):
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    msp.add_arc(center=(5, 5), radius=2.0, start_angle=0, end_angle=180)
    p = tmp_path / "mix.dxf"
    doc.saveas(str(p))

    imp = DXFImporter(p)
    counts = imp.validate_entity_types()
    assert counts["LWPOLYLINE"] == 1
    assert counts["ARC"] == 1
    assert any("CIRCLE/ARC" in w for w in counts["warnings"])


def test_import_as_polygon_closed_lwpolyline(tmp_path):
    path = _make_square_dxf(tmp_path)
    imp = DXFImporter(path, tolerance=0.01)
    poly, meta = imp.import_as_polygon(layer_name="CRANE")
    assert isinstance(poly, Polygon)
    assert poly.area == pytest.approx(100.0, abs=0.1)
    assert meta["num_polylines"] == 1
    assert meta["crs_epsg"] == 25832


def test_import_as_polygon_from_lines(tmp_path):
    """Vier LINE-Entities zusammenführen -> 100 m² Polygon."""
    path = _make_open_lines_dxf(tmp_path)
    imp = DXFImporter(path, tolerance=0.01)
    poly, meta = imp.import_as_polygon(layer_name="CRANE")
    assert isinstance(poly, Polygon)
    assert poly.area == pytest.approx(100.0, abs=0.1)


def test_import_holms_two_polygons(tmp_path):
    path = _make_two_polygons_dxf(tmp_path)
    imp = DXFImporter(path, tolerance=0.01)
    holms, meta = imp.import_holms(layer_name="HOLMS")
    assert len(holms) == 2
    assert meta["num_holms"] == 2
    assert meta["total_area"] == pytest.approx(50.0, abs=0.1)


def test_detect_coordinate_system_utm32(tmp_path):
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    # Realistische UTM-32-Koords
    msp.add_lwpolyline(
        [(345000, 5700000), (345010, 5700000), (345010, 5700010), (345000, 5700010), (345000, 5700000)]
    )
    p = tmp_path / "utm32.dxf"
    doc.saveas(str(p))

    imp = DXFImporter(p)
    det = imp.detect_coordinate_system()
    assert det["detected_epsg"] == 25832
    assert det["confidence"] == "high"


def test_detect_coordinate_system_wgs84(tmp_path):
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline([(7.5, 51.5), (7.51, 51.5), (7.51, 51.51), (7.5, 51.51), (7.5, 51.5)])
    p = tmp_path / "wgs84.dxf"
    doc.saveas(str(p))

    imp = DXFImporter(p)
    det = imp.detect_coordinate_system()
    assert any(s["epsg"] == 4326 for s in det["suggestions"])
    assert any("WGS84" in w for w in det["warnings"])


def test_validate_coordinate_system_ok(tmp_path):
    doc = ezdxf.new(dxfversion="R2010")
    doc.modelspace().add_lwpolyline(
        [(345000, 5700000), (345010, 5700000), (345010, 5700010), (345000, 5700010), (345000, 5700000)]
    )
    p = tmp_path / "ok.dxf"
    doc.saveas(str(p))
    imp = DXFImporter(p, crs_epsg=25832)
    ok, msg = imp.validate_coordinate_system()
    assert ok


def test_layer_not_found(tmp_path):
    path = _make_square_dxf(tmp_path)
    imp = DXFImporter(path)
    with pytest.raises(Exception, match="nicht gefunden"):
        imp.validate_layer_exists("NICHT_DA")
