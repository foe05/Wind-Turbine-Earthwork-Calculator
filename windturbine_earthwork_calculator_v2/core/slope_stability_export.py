"""
Slope-Stability Cross-Section Export

Writes a vendor-neutral XML description of a slope cross section — terrain
and design profiles, soil-material parameters, optional piezometric line — so
a geotechnical engineer can feed it into the slope-stability solver of their
choice (Slide2/RS2, GeoStudio SLOPE/W, Plaxis-LE) without re-keying the data.

The format is intentionally simple and explicit (one ``<Section>`` per slope,
explicit units in attribute names) rather than emulating a vendor format we
cannot test against. It is a documentation/interchange artifact.

Built on stdlib ``xml.etree.ElementTree``, QGIS-independent, testable by
re-parsing.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Sequence


@dataclass(frozen=True)
class ProfilePoint:
    """One station along the slope cross section."""

    x_m: float
    terrain_z_m: float
    design_z_m: Optional[float] = None  # None if no design surface at x


@dataclass(frozen=True)
class SoilMaterial:
    """Geotechnical parameters of one soil layer.

    Units are explicit in the field names to avoid downstream confusion in
    slope-stability software.
    """

    name: str
    unit_weight_kN_per_m3: float
    friction_angle_deg: float
    cohesion_kPa: float
    top_z_m: Optional[float] = None  # top elevation if the material has a planar top

    def __post_init__(self) -> None:
        if self.unit_weight_kN_per_m3 <= 0:
            raise ValueError("unit_weight must be positive")
        if not (0.0 <= self.friction_angle_deg < 90.0):
            raise ValueError("friction_angle must be in [0, 90)")
        if self.cohesion_kPa < 0:
            raise ValueError("cohesion must be non-negative")


@dataclass
class SlopeSection:
    """One slope cross section."""

    name: str
    profile: list[ProfilePoint] = field(default_factory=list)
    materials: list[SoilMaterial] = field(default_factory=list)
    piezometric: list[tuple[float, float]] = field(default_factory=list)  # (x, z) pairs

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("section name required")


_NS = "urn:windturbine-calculator:slope-stability-export:v1"


def _q(tag: str) -> str:
    return f"{{{_NS}}}{tag}"


# Register as the default namespace for clean serialisation.
ET.register_namespace("", _NS)


def build_slope_xml(sections: Sequence[SlopeSection],
                    project_name: str = "WEA") -> ET.ElementTree:
    """Build an ElementTree for the slope-stability export."""
    root = ET.Element(_q("SlopeStabilityExport"), {
        "version": "1.0",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generator": "windturbine-earthwork-calculator",
    })
    ET.SubElement(root, _q("Project"), {"name": project_name})

    for section in sections:
        sec_el = ET.SubElement(root, _q("Section"), {"name": section.name})

        prof_el = ET.SubElement(sec_el, _q("Profile"), {
            "count": str(len(section.profile)),
        })
        for pt in section.profile:
            attrs = {
                "x_m": f"{pt.x_m:.4f}",
                "terrain_z_m": f"{pt.terrain_z_m:.4f}",
            }
            if pt.design_z_m is not None:
                attrs["design_z_m"] = f"{pt.design_z_m:.4f}"
            ET.SubElement(prof_el, _q("Point"), attrs)

        mats_el = ET.SubElement(sec_el, _q("Materials"), {
            "count": str(len(section.materials)),
        })
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
            piezo_el = ET.SubElement(sec_el, _q("Piezometric"), {
                "count": str(len(section.piezometric)),
            })
            for x, z in section.piezometric:
                ET.SubElement(piezo_el, _q("Point"), {
                    "x_m": f"{x:.4f}", "z_m": f"{z:.4f}",
                })

    return ET.ElementTree(root)


def write_slope_xml(path: str, sections: Sequence[SlopeSection],
                    project_name: str = "WEA") -> str:
    """Write a slope-stability export XML. Returns the absolute output path."""
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    tree = build_slope_xml(sections, project_name=project_name)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass
    tree.write(abs_path, encoding="UTF-8", xml_declaration=True)
    return abs_path


def section_from_profile(name: str, profile: dict,
                         materials: Optional[Sequence[SoilMaterial]] = None
                         ) -> SlopeSection:
    """Adapter: build a SlopeSection from a profile_generator profile dict
    (``distances``, ``existing_z``, ``bottom_z``).

    NaN/None entries in ``bottom_z`` become ``design_z_m=None`` so the
    consumer knows where the design surface is absent.
    """
    distances = profile.get("distances")
    existing = profile.get("existing_z")
    bottom = profile.get("bottom_z")
    if distances is None or existing is None or bottom is None:
        raise ValueError("profile missing distances/existing_z/bottom_z")

    pts = []
    for i in range(len(distances)):
        x = float(distances[i])
        ez = float(existing[i])
        b = bottom[i]
        # NaN check works for floats; treat None and NaN as missing.
        if b is None or b != b:
            pts.append(ProfilePoint(x_m=x, terrain_z_m=ez, design_z_m=None))
        else:
            pts.append(ProfilePoint(x_m=x, terrain_z_m=ez, design_z_m=float(b)))

    return SlopeSection(name=name, profile=pts, materials=list(materials or []))


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def default_materials() -> list[SoilMaterial]:
    """Indicative German-construction soil parameters for a quick export."""
    return [
        SoilMaterial(
            name="Mutterboden", unit_weight_kN_per_m3=17.0,
            friction_angle_deg=22.0, cohesion_kPa=5.0,
        ),
        SoilMaterial(
            name="Schluff (anstehend)", unit_weight_kN_per_m3=19.0,
            friction_angle_deg=27.5, cohesion_kPa=10.0,
        ),
        SoilMaterial(
            name="Schottertragschicht", unit_weight_kN_per_m3=22.0,
            friction_angle_deg=38.0, cohesion_kPa=0.0,
        ),
    ]
