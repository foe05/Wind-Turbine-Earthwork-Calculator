"""Tests Wave 9: landxml, slope_stability, mesh, geopackage."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon

from app.core.earthwork import CutFillResult
from app.core.geopackage import write_multisurface_geopackage
from app.core.landxml import LandXMLSurface, build_landxml, write_landxml
from app.core.mesh import (
    MeshData,
    build_gltf_dict,
    dem_to_mesh,
    polygon_to_mesh_at_height,
    write_gltf,
    write_obj,
    write_stl,
    write_three_js_viewer,
)
from app.core.multi_surface import MultiSurfaceResult, SurfaceType
from app.core.slope_stability import (
    ProfilePoint,
    SlopeSection,
    SoilMaterial,
    build_slope_xml,
    write_slope_xml,
)


# --------------------------------------------------------------- landxml

def test_landxml_build_and_parse(tmp_path):
    surf = LandXMLSurface(
        name="Kranstellfläche",
        points=[(0, 0, 100), (10, 0, 100), (10, 10, 101)],
        faces=[(0, 1, 2)],
    )
    out = tmp_path / "wea.xml"
    write_landxml(str(out), [surf], project_name="WEA1")
    tree = ET.parse(out)
    root = tree.getroot()
    assert root.tag.endswith("LandXML")
    assert root.attrib["version"] == "1.2"


def test_landxml_point_order_y_x_z(tmp_path):
    surf = LandXMLSurface("S", [(1.5, 2.5, 100.0)], [])
    out = tmp_path / "p.xml"
    write_landxml(str(out), [surf])
    txt = out.read_text()
    # Northing(y) Easting(x) Elev(z) -> "2.5000 1.5000 100.0000"
    assert "2.5000 1.5000 100.0000" in txt


# --------------------------------------------------------------- slope stability

def test_slope_section_validates_material():
    with pytest.raises(ValueError, match="unit_weight"):
        SoilMaterial("X", -1, 20, 5)
    with pytest.raises(ValueError, match="friction"):
        SoilMaterial("X", 18, 95, 5)


def test_slope_xml_writes_profile_and_materials(tmp_path):
    section = SlopeSection(
        "Querschnitt A",
        profile=[
            ProfilePoint(0, 100),
            ProfilePoint(5, 99, design_z_m=98),
            ProfilePoint(10, 98),
        ],
        materials=[SoilMaterial("Schluff", 19, 27, 10)],
    )
    out = tmp_path / "slope.xml"
    write_slope_xml(str(out), [section])
    txt = out.read_text()
    assert "Schluff" in txt
    assert "design_z_m" in txt


# --------------------------------------------------------------- mesh OBJ/STL

def test_polygon_to_mesh_at_height():
    coords = [(0, 0), (10, 0), (10, 10), (0, 10)]
    mesh = polygon_to_mesh_at_height(coords, height=100.0)
    assert mesh.vertex_count == 4
    assert mesh.triangle_count == 2
    assert all(v[2] == 100.0 for v in mesh.vertices)


def test_write_obj_file(tmp_path):
    mesh = polygon_to_mesh_at_height([(0, 0), (10, 0), (10, 10)], 100.0, "test")
    out = tmp_path / "m.obj"
    write_obj(str(out), mesh)
    txt = out.read_text()
    assert "v 0.0000 0.0000 100.0000" in txt
    assert "f 1 2 3" in txt or "f 1 3 2" in txt or "f 2 3 1" in txt


def test_write_stl_ascii_and_binary(tmp_path):
    mesh = polygon_to_mesh_at_height([(0, 0), (10, 0), (10, 10)], 100.0, "tri")
    a_path = tmp_path / "m.stl"
    write_stl(str(a_path), mesh, binary=False)
    assert "solid tri" in a_path.read_text()
    b_path = tmp_path / "m_bin.stl"
    write_stl(str(b_path), mesh, binary=True)
    data = b_path.read_bytes()
    # Header 80 + count 4 + 1 facet * 50 = 134 Bytes
    assert len(data) == 134


def test_dem_to_mesh_with_rasterio(tmp_path):
    arr = np.full((20, 20), 100.0, dtype=np.float32)
    p = tmp_path / "dem.tif"
    with rasterio.open(
        p,
        "w",
        driver="GTiff",
        height=20,
        width=20,
        count=1,
        dtype="float32",
        transform=from_origin(0, 20, 1, 1),
        crs="EPSG:25832",
        nodata=-9999.0,
    ) as ds:
        ds.write(arr, 1)
    mesh = dem_to_mesh(str(p), decimation=2)
    assert mesh.vertex_count > 0
    assert mesh.triangle_count > 0


# --------------------------------------------------------------- glTF + viewer

def test_build_gltf_dict_basic():
    mesh = polygon_to_mesh_at_height([(0, 0), (10, 0), (10, 10)], 100.0, "kranstellflaeche")
    gltf = build_gltf_dict([mesh])
    assert gltf["asset"]["version"] == "2.0"
    assert len(gltf["meshes"]) == 1
    assert len(gltf["materials"]) == 1
    # base64-Embedded Buffer
    assert gltf["buffers"][0]["uri"].startswith("data:application/octet-stream;base64,")


def test_write_gltf_and_three_viewer(tmp_path):
    mesh1 = polygon_to_mesh_at_height([(0, 0), (10, 0), (10, 10)], 100.0, "kranstellflaeche")
    mesh2 = polygon_to_mesh_at_height([(20, 0), (30, 0), (30, 10)], 99.0, "fundamentsohle")
    gltf_path = tmp_path / "scene.gltf"
    write_gltf(str(gltf_path), [mesh1, mesh2])
    gltf = json.loads(gltf_path.read_text())
    assert len(gltf["meshes"]) == 2

    viewer = tmp_path / "viewer.html"
    write_three_js_viewer(str(viewer), gltf, title="Testszene")
    txt = viewer.read_text()
    assert "Testszene" in txt
    assert "OrbitControls" in txt


# --------------------------------------------------------------- geopackage

def test_geopackage_export(tmp_path):
    crane = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    foundation = Polygon([(20, 0), (25, 0), (25, 5), (20, 5), (20, 0)])
    surfaces = {SurfaceType.CRANE_PAD: crane, SurfaceType.FOUNDATION: foundation}
    result = MultiSurfaceResult(
        crane_optimum_height=104.7,
        fok=104.5,
        foundation_depth=3.1,
        gravel_thickness=0.6,
        surface_results={
            SurfaceType.CRANE_PAD: CutFillResult(104.1, 5280, 1763, 2500, 98, 110, 104, 2500),
            SurfaceType.FOUNDATION: CutFillResult(101.4, 693, 0, 200, 101.5, 104, 102.8, 200),
        },
    )
    out = tmp_path / "wea.gpkg"
    write_multisurface_geopackage(str(out), surfaces, result)
    assert out.exists()

    # Layer auslesen
    gdf_crane = gpd.read_file(out, layer="kranstellflaeche")
    assert len(gdf_crane) == 1
    assert gdf_crane.iloc[0]["cut_m3"] == 5280
    gdf_found = gpd.read_file(out, layer="fundamentflaeche")
    assert gdf_found.iloc[0]["cut_m3"] == 693
