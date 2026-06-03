"""
Multi-Surface-Projekt-Container und Berechnungs-Orchestrierung.

Pragmatischer MVP-Port von core/multi_surface_calculator.py + surface_types.py.
Volle Plugin-Tiefe (Boom-Slope, Rotor-Offset, Road-Slope-Sweep, Connection-Edges)
folgt iterativ — hier reicht: Foundation-Cut/Fill auf FOK-depth, Crane-Pad mit
optionalem Höhen-Sweep, optional Boom/Rotor/Holms/Road mit fester Höhe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from shapely.geometry.base import BaseGeometry

from .earthwork import CutFillResult, coarse_then_fine_sweep, cut_fill_for_polygon


class SurfaceType(str, Enum):
    CRANE_PAD = "kranstellflaeche"
    FOUNDATION = "fundamentflaeche"
    BOOM = "auslegerflaeche"
    ROTOR_STORAGE = "rotorflaeche"
    ROAD_ACCESS = "zufahrt"
    HOLMS = "holme"

    @property
    def display_name(self) -> str:
        names = {
            SurfaceType.CRANE_PAD: "Kranstellfläche",
            SurfaceType.FOUNDATION: "Fundamentfläche",
            SurfaceType.BOOM: "Auslegerfläche",
            SurfaceType.ROTOR_STORAGE: "Blattlagerfläche",
            SurfaceType.ROAD_ACCESS: "Zufahrtsstraße",
            SurfaceType.HOLMS: "Holme",
        }
        return names[self]


class HeightMode(str, Enum):
    FIXED = "fixed"
    OPTIMIZED = "optimized"


@dataclass
class SurfaceConfig:
    """Ein Surface im Multi-Surface-Projekt."""

    surface_type: SurfaceType
    polygon: BaseGeometry
    height_mode: HeightMode = HeightMode.FIXED
    height_value: Optional[float] = None  # m ü.NN bei FIXED


@dataclass
class MultiSurfaceProject:
    """Projektkonfiguration. Mindestens crane_pad + foundation + fok."""

    crane_pad: SurfaceConfig
    foundation: SurfaceConfig
    fok: float
    foundation_depth: float = 3.5
    gravel_thickness: float = 0.5

    boom: Optional[SurfaceConfig] = None
    rotor_storage: Optional[SurfaceConfig] = None
    road_access: Optional[SurfaceConfig] = None
    holms: Optional[list[BaseGeometry]] = None

    # Höhen-Sweep für Kranstellfläche
    search_range_below_fok: float = 0.5
    search_range_above_fok: float = 0.5
    coarse_step: float = 0.1
    fine_step: float = 0.01
    optimize_objective: str = "min_total"  # 'min_total' | 'min_net' | 'min_cut'

    @property
    def search_min_height(self) -> float:
        return self.fok - self.search_range_below_fok

    @property
    def search_max_height(self) -> float:
        return self.fok + self.search_range_above_fok

    @property
    def foundation_bottom_elevation(self) -> float:
        return self.fok - self.foundation_depth


@dataclass
class MultiSurfaceResult:
    """Aggregierte Ergebnisse aller Surfaces für einen Berechnungslauf."""

    crane_optimum_height: float  # m ü.NN (Plattformoberkante = Sohle + Schotter)
    surface_results: dict[SurfaceType, CutFillResult]
    fok: float
    foundation_depth: float
    gravel_thickness: float

    @property
    def total_cut_m3(self) -> float:
        return sum(r.cut_m3 for r in self.surface_results.values())

    @property
    def total_fill_m3(self) -> float:
        return sum(r.fill_m3 for r in self.surface_results.values())

    @property
    def net_m3(self) -> float:
        return self.total_cut_m3 - self.total_fill_m3

    @property
    def total_moved_m3(self) -> float:
        return self.total_cut_m3 + self.total_fill_m3

    def to_dict(self) -> dict:
        return {
            "crane_optimum_height": round(self.crane_optimum_height, 3),
            "fok": round(self.fok, 3),
            "foundation_depth": round(self.foundation_depth, 3),
            "gravel_thickness": round(self.gravel_thickness, 3),
            "total_cut_m3": round(self.total_cut_m3, 1),
            "total_fill_m3": round(self.total_fill_m3, 1),
            "net_m3": round(self.net_m3, 1),
            "total_moved_m3": round(self.total_moved_m3, 1),
            "surfaces": {
                t.value: {
                    "plateau_height": round(r.plateau_height, 3),
                    "cut_m3": round(r.cut_m3, 1),
                    "fill_m3": round(r.fill_m3, 1),
                    "platform_area_m2": round(r.platform_area_m2, 1),
                    "terrain_min": round(r.terrain_min, 2),
                    "terrain_max": round(r.terrain_max, 2),
                    "terrain_mean": round(r.terrain_mean, 2),
                }
                for t, r in self.surface_results.items()
            },
        }


def calculate_multi_surface(
    dem_path: str | Path, project: MultiSurfaceProject
) -> MultiSurfaceResult:
    """Komplette Multi-Surface-Berechnung gegen ein DEM-Mosaik."""

    results: dict[SurfaceType, CutFillResult] = {}

    # Foundation: festes Plateau auf FOK - depth
    foundation_planum = project.foundation_bottom_elevation
    results[SurfaceType.FOUNDATION] = cut_fill_for_polygon(
        dem_path, project.foundation.polygon, foundation_planum
    )

    # Crane Pad: Plateau ist Optimum - Schotter; optional über Höhen-Sweep
    if project.crane_pad.height_mode == HeightMode.OPTIMIZED:
        h_lo = project.search_min_height - project.gravel_thickness
        h_hi = project.search_max_height - project.gravel_thickness
        best_planum, best_result, _ = coarse_then_fine_sweep(
            dem_path,
            project.crane_pad.polygon,
            h_lo,
            h_hi,
            coarse_step=project.coarse_step,
            fine_step=project.fine_step,
            objective=project.optimize_objective,
        )
        crane_optimum = best_planum + project.gravel_thickness
        results[SurfaceType.CRANE_PAD] = best_result
    else:
        crane_top = (
            project.crane_pad.height_value
            if project.crane_pad.height_value is not None
            else project.fok
        )
        crane_planum = crane_top - project.gravel_thickness
        crane_optimum = crane_top
        results[SurfaceType.CRANE_PAD] = cut_fill_for_polygon(
            dem_path, project.crane_pad.polygon, crane_planum
        )

    # Boom / Rotor Storage / Road Access mit fester Höhe (MVP)
    for surface in (project.boom, project.rotor_storage, project.road_access):
        if surface is None or surface.height_value is None:
            continue
        results[surface.surface_type] = cut_fill_for_polygon(
            dem_path, surface.polygon, surface.height_value
        )

    # Holms: aggregiert auf FOK (Plugin-Default)
    if project.holms:
        cut_total = 0.0
        fill_total = 0.0
        area_total = 0.0
        for h_poly in project.holms:
            r = cut_fill_for_polygon(dem_path, h_poly, project.fok)
            cut_total += r.cut_m3
            fill_total += r.fill_m3
            area_total += r.platform_area_m2
        results[SurfaceType.HOLMS] = CutFillResult(
            plateau_height=project.fok,
            cut_m3=cut_total,
            fill_m3=fill_total,
            platform_area_m2=area_total,
            terrain_min=0.0,
            terrain_max=0.0,
            terrain_mean=0.0,
            num_pixels=0,
        )

    return MultiSurfaceResult(
        crane_optimum_height=crane_optimum,
        surface_results=results,
        fok=project.fok,
        foundation_depth=project.foundation_depth,
        gravel_thickness=project.gravel_thickness,
    )
