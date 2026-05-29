"""
LandXML Export for Wind Turbine Earthwork Calculator V2

LandXML is the de-facto interchange format for civil-engineering surfaces and
the input most machine-control systems (Trimble, Topcon, Leica) and CAD tools
(Civil 3D, RoadEng) consume directly. Exporting the constructed surfaces as
LandXML TIN surfaces makes the plugin's output usable on the construction site
without a manual conversion step — a capability the commercial tools charge for.

This writes LandXML 1.2 with one ``<Surface>`` per input surface, each a TIN
``<Definition>`` of points + triangle faces. Coordinates follow the LandXML
convention of ``northing easting elevation`` (Y X Z) order.

Built on stdlib ``xml.etree.ElementTree`` — no extra dependency, QGIS-independent,
and unit-testable by parsing the output back.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

Point3D = tuple[float, float, float]   # (x=easting, y=northing, z=elevation)
Face = tuple[int, int, int]            # 0-based vertex indices


@dataclass
class LandXMLSurface:
    """A named TIN surface: (x, y, z) points and 0-based triangle faces."""

    name: str
    points: Sequence[Point3D]
    faces: Sequence[Face]


_LANDXML_NS = "http://www.landxml.org/schema/LandXML-1.2"

# Serialise with the LandXML namespace as the default (no prefix).
ET.register_namespace("", _LANDXML_NS)


def _q(tag: str) -> str:
    """Qualify a tag with the LandXML namespace (Clark notation)."""
    return f"{{{_LANDXML_NS}}}{tag}"


def build_landxml(
    surfaces: Sequence[LandXMLSurface],
    project_name: str = "WEA",
    application: str = "Wind Turbine Earthwork Calculator V2",
) -> ET.ElementTree:
    """Build a LandXML 1.2 ElementTree with a TIN surface per input surface.

    All elements are namespace-qualified so the in-memory tree and the
    serialised/re-parsed tree expose identical (namespaced) tags.
    """
    root = ET.Element(_q("LandXML"), {
        "version": "1.2",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
    })

    # Units (metric). LandXML requires a Units element.
    units = ET.SubElement(root, _q("Units"))
    ET.SubElement(units, _q("Metric"), {
        "areaUnit": "squareMeter",
        "linearUnit": "meter",
        "volumeUnit": "cubicMeter",
        "temperatureUnit": "celsius",
        "pressureUnit": "mmHG",
    })

    ET.SubElement(root, _q("Application"), {
        "name": application,
        "desc": project_name,
    })

    surfaces_el = ET.SubElement(root, _q("Surfaces"))
    for surface in surfaces:
        _append_surface(surfaces_el, surface)

    return ET.ElementTree(root)


def _append_surface(parent: ET.Element, surface: LandXMLSurface) -> None:
    surf_el = ET.SubElement(parent, _q("Surface"), {"name": surface.name})
    defn = ET.SubElement(surf_el, _q("Definition"), {"surfType": "TIN"})

    pnts = ET.SubElement(defn, _q("Pnts"))
    # LandXML point ids are 1-based; coordinate order is northing easting elev.
    for i, (x, y, z) in enumerate(surface.points, start=1):
        p = ET.SubElement(pnts, _q("P"), {"id": str(i)})
        p.text = f"{y:.4f} {x:.4f} {z:.4f}"

    faces = ET.SubElement(defn, _q("Faces"))
    for (a, b, c) in surface.faces:
        f = ET.SubElement(faces, _q("F"))
        # 0-based → 1-based point references
        f.text = f"{a + 1} {b + 1} {c + 1}"


def write_landxml(
    path: str,
    surfaces: Sequence[LandXMLSurface],
    project_name: str = "WEA",
) -> str:
    """Write the surfaces to a LandXML 1.2 file. Returns the absolute path."""
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    tree = build_landxml(surfaces, project_name=project_name)
    # ET.indent is available from Python 3.9+ (QGIS 3.34 ships 3.12).
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass
    tree.write(abs_path, encoding="UTF-8", xml_declaration=True)
    return abs_path


def surface_from_mesh(name: str, mesh) -> LandXMLSurface:
    """Adapter: build a LandXMLSurface from a mesh_exporter.MeshData
    (or any object exposing ``vertices`` and ``faces``).
    """
    return LandXMLSurface(name=name, points=list(mesh.vertices), faces=list(mesh.faces))
