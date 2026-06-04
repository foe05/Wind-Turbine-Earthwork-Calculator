"""LandXML 1.2 Export (1:1-Port aus core/landxml_export.py)."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

Point3D = tuple[float, float, float]
Face = tuple[int, int, int]


@dataclass
class LandXMLSurface:
    name: str
    points: Sequence[Point3D]
    faces: Sequence[Face]


_LANDXML_NS = "http://www.landxml.org/schema/LandXML-1.2"
ET.register_namespace("", _LANDXML_NS)


def _q(tag: str) -> str:
    return f"{{{_LANDXML_NS}}}{tag}"


def build_landxml(
    surfaces: Sequence[LandXMLSurface],
    project_name: str = "WEA",
    application: str = "Wind Turbine Earthwork Calculator (Streamlit)",
) -> ET.ElementTree:
    root = ET.Element(
        _q("LandXML"),
        {
            "version": "1.2",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
        },
    )
    units = ET.SubElement(root, _q("Units"))
    ET.SubElement(
        units,
        _q("Metric"),
        {
            "areaUnit": "squareMeter",
            "linearUnit": "meter",
            "volumeUnit": "cubicMeter",
            "temperatureUnit": "celsius",
            "pressureUnit": "mmHG",
        },
    )
    ET.SubElement(root, _q("Application"), {"name": application, "desc": project_name})
    surfaces_el = ET.SubElement(root, _q("Surfaces"))
    for s in surfaces:
        _append_surface(surfaces_el, s)
    return ET.ElementTree(root)


def _append_surface(parent: ET.Element, surface: LandXMLSurface) -> None:
    surf_el = ET.SubElement(parent, _q("Surface"), {"name": surface.name})
    defn = ET.SubElement(surf_el, _q("Definition"), {"surfType": "TIN"})
    pnts = ET.SubElement(defn, _q("Pnts"))
    for i, (x, y, z) in enumerate(surface.points, start=1):
        p = ET.SubElement(pnts, _q("P"), {"id": str(i)})
        p.text = f"{y:.4f} {x:.4f} {z:.4f}"
    faces = ET.SubElement(defn, _q("Faces"))
    for a, b, c in surface.faces:
        f = ET.SubElement(faces, _q("F"))
        f.text = f"{a + 1} {b + 1} {c + 1}"


def write_landxml(path: str, surfaces: Sequence[LandXMLSurface], project_name: str = "WEA") -> str:
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    tree = build_landxml(surfaces, project_name=project_name)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass
    tree.write(abs_path, encoding="UTF-8", xml_declaration=True)
    return abs_path


def surface_from_mesh(name: str, mesh) -> LandXMLSurface:
    """Adapter: MeshData → LandXMLSurface."""
    return LandXMLSurface(name=name, points=list(mesh.vertices), faces=list(mesh.faces))
