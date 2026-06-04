"""Slope-Stability XML-Export (1:1-Port aus core/slope_stability_export.py)."""

from __future__ import annotations

import math
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Sequence


@dataclass(frozen=True)
class ProfilePoint:
    x_m: float
    terrain_z_m: float
    design_z_m: Optional[float] = None


@dataclass(frozen=True)
class SoilMaterial:
    name: str
    unit_weight_kN_per_m3: float
    friction_angle_deg: float
    cohesion_kPa: float
    top_z_m: Optional[float] = None

    def __post_init__(self) -> None:
        if self.unit_weight_kN_per_m3 <= 0:
            raise ValueError("unit_weight must be positive")
        if not (0.0 <= self.friction_angle_deg < 90.0):
            raise ValueError("friction_angle must be in [0, 90)")
        if self.cohesion_kPa < 0:
            raise ValueError("cohesion must be non-negative")


@dataclass
class SlopeSection:
    name: str
    profile: list[ProfilePoint] = field(default_factory=list)
    materials: list[SoilMaterial] = field(default_factory=list)
    piezometric: list[tuple[float, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("section name required")


_NS = "urn:wtec:slope-stability-export:v1"
ET.register_namespace("", _NS)


def _q(tag: str) -> str:
    return f"{{{_NS}}}{tag}"


def build_slope_xml(sections: Sequence[SlopeSection], project_name: str = "WEA") -> ET.ElementTree:
    root = ET.Element(
        _q("SlopeStabilityExport"),
        {
            "version": "1.0",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "generator": "wtec-streamlit",
        },
    )
    ET.SubElement(root, _q("Project"), {"name": project_name})
    for section in sections:
        sec_el = ET.SubElement(root, _q("Section"), {"name": section.name})
        prof_el = ET.SubElement(sec_el, _q("Profile"), {"count": str(len(section.profile))})
        for pt in section.profile:
            attrs = {"x_m": f"{pt.x_m:.4f}", "terrain_z_m": f"{pt.terrain_z_m:.4f}"}
            if pt.design_z_m is not None:
                attrs["design_z_m"] = f"{pt.design_z_m:.4f}"
            ET.SubElement(prof_el, _q("Point"), attrs)

        mats_el = ET.SubElement(sec_el, _q("Materials"), {"count": str(len(section.materials))})
        for mat in section.materials:
            attrs = {
                "name": mat.name,
                "unit_weight_kN_per_m3": f"{mat.unit_weight_kN_per_m3:.3f}",
                "friction_angle_deg": f"{mat.friction_angle_deg:.2f}",
                "cohesion_kPa": f"{mat.cohesion_kPa:.2f}",
            }
            if mat.top_z_m is not None:
                attrs["top_z_m"] = f"{mat.top_z_m:.4f}"
            ET.SubElement(mats_el, _q("Material"), attrs)

        if section.piezometric:
            piezo_el = ET.SubElement(sec_el, _q("Piezometric"), {"count": str(len(section.piezometric))})
            for x, z in section.piezometric:
                ET.SubElement(piezo_el, _q("Point"), {"x_m": f"{x:.4f}", "z_m": f"{z:.4f}"})
    return ET.ElementTree(root)


def write_slope_xml(path: str, sections: Sequence[SlopeSection], project_name: str = "WEA") -> str:
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    tree = build_slope_xml(sections, project_name=project_name)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass
    tree.write(abs_path, encoding="UTF-8", xml_declaration=True)
    return abs_path


def default_materials() -> list[SoilMaterial]:
    return [
        SoilMaterial("Mutterboden", 17.0, 22.0, 5.0),
        SoilMaterial("Schluff (anstehend)", 19.0, 27.5, 10.0),
        SoilMaterial("Schottertragschicht", 22.0, 38.0, 0.0),
    ]
