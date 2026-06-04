"""
Multi-Surface-Projekt-Container und Berechnungs-Orchestrierung.

Vollausbau: Foundation + Crane-Pad (mit optionalem Höhen-Sweep), Boom mit
Slope-Sweep, Rotor-Storage mit Offset-Sweep, Road-Access mit Slope-Sweep,
Holme. Optionale Slope-/Böschungs-Volumen-Approximation (siehe slope_volume).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from shapely.geometry.base import BaseGeometry

from .earthwork import CutFillResult, coarse_then_fine_sweep, cut_fill_for_polygon
from .slope_volume import SlopeVolumeResult, estimate_slope_volume


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
    surface_type: SurfaceType
    polygon: BaseGeometry
    height_mode: HeightMode = HeightMode.FIXED
    height_value: Optional[float] = None


@dataclass
class MultiSurfaceProject:
    crane_pad: SurfaceConfig
    foundation: SurfaceConfig
    fok: float
    foundation_depth: float = 3.5
    gravel_thickness: float = 0.5

    boom: Optional[SurfaceConfig] = None
    rotor_storage: Optional[SurfaceConfig] = None
    road_access: Optional[SurfaceConfig] = None
    holms: Optional[list[BaseGeometry]] = None

    # Crane-Pad-Sweep
    search_range_below_fok: float = 0.5
    search_range_above_fok: float = 0.5
    coarse_step: float = 0.1
    fine_step: float = 0.01
    optimize_objective: str = "min_total"

    # Böschungs-Approximation
    include_slope_volume: bool = True
    slope_angle_deg: float = 45.0
    slope_sample_spacing_m: float = 1.0

    # Boom-Slope-Sweep (% in Prozent)
    boom_slope_optimize: bool = False
    boom_slope_min_percent: float = -4.0
    boom_slope_max_percent: float = 4.0
    boom_slope_step_percent: float = 0.5

    # Rotor-Offset-Sweep (m relativ zur Kran-OK)
    rotor_offset_optimize: bool = False
    rotor_offset_min_m: float = -0.5
    rotor_offset_max_m: float = 0.5
    rotor_offset_step_m: float = 0.05

    # Road-Slope-Sweep (% in Prozent)
    road_slope_optimize: bool = False
    road_slope_min_percent: float = -8.0
    road_slope_max_percent: float = 8.0
    road_slope_step_percent: float = 1.0

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
    crane_optimum_height: float
    surface_results: dict[SurfaceType, CutFillResult]
    fok: float
    foundation_depth: float
    gravel_thickness: float
    slope_results: dict[SurfaceType, SlopeVolumeResult] = field(default_factory=dict)
    boom_slope_percent: float = 0.0
    rotor_offset_m: float = 0.0
    road_slope_percent: float = 0.0

    @property
    def total_cut_m3(self) -> float:
        platform = sum(r.cut_m3 for r in self.surface_results.values())
        slope = sum(r.cut_m3 for r in self.slope_results.values())
        return platform + slope

    @property
    def total_fill_m3(self) -> float:
        platform = sum(r.fill_m3 for r in self.surface_results.values())
        slope = sum(r.fill_m3 for r in self.slope_results.values())
        return platform + slope

    @property
    def total_platform_cut_m3(self) -> float:
        return sum(r.cut_m3 for r in self.surface_results.values())

    @property
    def total_platform_fill_m3(self) -> float:
        return sum(r.fill_m3 for r in self.surface_results.values())

    @property
    def total_slope_cut_m3(self) -> float:
        return sum(r.cut_m3 for r in self.slope_results.values())

    @property
    def total_slope_fill_m3(self) -> float:
        return sum(r.fill_m3 for r in self.slope_results.values())

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
            "boom_slope_percent": round(self.boom_slope_percent, 2),
            "rotor_offset_m": round(self.rotor_offset_m, 3),
            "road_slope_percent": round(self.road_slope_percent, 2),
            "total_cut_m3": round(self.total_cut_m3, 1),
            "total_fill_m3": round(self.total_fill_m3, 1),
            "net_m3": round(self.net_m3, 1),
            "total_moved_m3": round(self.total_moved_m3, 1),
            "total_slope_cut_m3": round(self.total_slope_cut_m3, 1),
            "total_slope_fill_m3": round(self.total_slope_fill_m3, 1),
            "surfaces": {
                t.value: {
                    "plateau_height": round(r.plateau_height, 3),
                    "cut_m3": round(r.cut_m3, 1),
                    "fill_m3": round(r.fill_m3, 1),
                    "platform_area_m2": round(r.platform_area_m2, 1),
                    "terrain_min": round(r.terrain_min, 2),
                    "terrain_max": round(r.terrain_max, 2),
                    "terrain_mean": round(r.terrain_mean, 2),
                    "slope_cut_m3": round(self.slope_results[t].cut_m3, 1)
                    if t in self.slope_results else 0.0,
                    "slope_fill_m3": round(self.slope_results[t].fill_m3, 1)
                    if t in self.slope_results else 0.0,
                    "slope_area_m2": round(self.slope_results[t].slope_area_m2, 1)
                    if t in self.slope_results else 0.0,
                }
                for t, r in self.surface_results.items()
            },
        }


def _sweep_boom_slope(
    dem_path: str | Path,
    boom_polygon: BaseGeometry,
    crane_optimum: float,
    project: MultiSurfaceProject,
) -> tuple[float, CutFillResult]:
    """Sweep Boom-Plateau-Höhe als crane_optimum + delta (parametrisiert über Slope)."""
    if project.boom_slope_step_percent <= 0:
        raise ValueError("boom_slope_step_percent muss > 0 sein")
    best: Optional[CutFillResult] = None
    best_slope = 0.0
    pct = project.boom_slope_min_percent
    # Approximation: Slope wird über mittlere Distanz zur Kran-OK umgerechnet
    # in Höhendelta. Wir nehmen 30 m als Plug-in-Mittelwert.
    avg_distance_m = 30.0
    while pct <= project.boom_slope_max_percent + 1e-9:
        delta = avg_distance_m * (pct / 100.0)
        h = crane_optimum + delta
        r = cut_fill_for_polygon(dem_path, boom_polygon, h)
        if best is None or r.total_moved_m3 < best.total_moved_m3:
            best = r
            best_slope = pct
        pct += project.boom_slope_step_percent
    return best_slope, best  # type: ignore[return-value]


def _sweep_rotor_offset(
    dem_path: str | Path,
    rotor_polygon: BaseGeometry,
    crane_optimum: float,
    project: MultiSurfaceProject,
) -> tuple[float, CutFillResult]:
    if project.rotor_offset_step_m <= 0:
        raise ValueError("rotor_offset_step_m muss > 0 sein")
    best: Optional[CutFillResult] = None
    best_offset = 0.0
    o = project.rotor_offset_min_m
    while o <= project.rotor_offset_max_m + 1e-9:
        h = crane_optimum + o
        r = cut_fill_for_polygon(dem_path, rotor_polygon, h)
        if best is None or r.total_moved_m3 < best.total_moved_m3:
            best = r
            best_offset = o
        o += project.rotor_offset_step_m
    return best_offset, best  # type: ignore[return-value]


def _sweep_road_slope(
    dem_path: str | Path,
    road_polygon: BaseGeometry,
    crane_optimum: float,
    project: MultiSurfaceProject,
) -> tuple[float, CutFillResult]:
    if project.road_slope_step_percent <= 0:
        raise ValueError("road_slope_step_percent muss > 0 sein")
    best: Optional[CutFillResult] = None
    best_slope = 0.0
    pct = project.road_slope_min_percent
    avg_distance_m = 50.0  # Typische Zufahrtslänge
    while pct <= project.road_slope_max_percent + 1e-9:
        delta = avg_distance_m * (pct / 100.0)
        h = crane_optimum + delta
        r = cut_fill_for_polygon(dem_path, road_polygon, h)
        if best is None or r.total_moved_m3 < best.total_moved_m3:
            best = r
            best_slope = pct
        pct += project.road_slope_step_percent
    return best_slope, best  # type: ignore[return-value]


def calculate_multi_surface(
    dem_path: str | Path, project: MultiSurfaceProject
) -> MultiSurfaceResult:
    """Vollausbau-Berechnung Multi-Surface gegen ein DEM-Mosaik."""
    results: dict[SurfaceType, CutFillResult] = {}
    slope_results: dict[SurfaceType, SlopeVolumeResult] = {}

    # Foundation: festes Plateau auf FOK - depth
    foundation_planum = project.foundation_bottom_elevation
    results[SurfaceType.FOUNDATION] = cut_fill_for_polygon(
        dem_path, project.foundation.polygon, foundation_planum
    )

    # Crane Pad
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

    # Boom — optional Sweep
    boom_slope = 0.0
    if project.boom is not None:
        if project.boom_slope_optimize:
            boom_slope, r_boom = _sweep_boom_slope(
                dem_path, project.boom.polygon, crane_optimum, project
            )
        else:
            h = (
                project.boom.height_value
                if project.boom.height_value is not None
                else crane_optimum
            )
            r_boom = cut_fill_for_polygon(dem_path, project.boom.polygon, h)
        results[SurfaceType.BOOM] = r_boom

    # Rotor Storage — optional Sweep
    rotor_offset = 0.0
    if project.rotor_storage is not None:
        if project.rotor_offset_optimize:
            rotor_offset, r_rotor = _sweep_rotor_offset(
                dem_path, project.rotor_storage.polygon, crane_optimum, project
            )
        else:
            h = (
                project.rotor_storage.height_value
                if project.rotor_storage.height_value is not None
                else crane_optimum
            )
            r_rotor = cut_fill_for_polygon(dem_path, project.rotor_storage.polygon, h)
        results[SurfaceType.ROTOR_STORAGE] = r_rotor

    # Road Access — optional Sweep
    road_slope = 0.0
    if project.road_access is not None:
        if project.road_slope_optimize:
            road_slope, r_road = _sweep_road_slope(
                dem_path, project.road_access.polygon, crane_optimum, project
            )
        else:
            h = (
                project.road_access.height_value
                if project.road_access.height_value is not None
                else crane_optimum
            )
            r_road = cut_fill_for_polygon(dem_path, project.road_access.polygon, h)
        results[SurfaceType.ROAD_ACCESS] = r_road

    # Holms aggregiert
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

    # Slope/Böschungs-Volumen pro Surface
    if project.include_slope_volume:
        if SurfaceType.CRANE_PAD in results:
            slope_results[SurfaceType.CRANE_PAD] = estimate_slope_volume(
                dem_path,
                project.crane_pad.polygon,
                results[SurfaceType.CRANE_PAD].plateau_height,
                project.slope_angle_deg,
                project.slope_sample_spacing_m,
            )
        if SurfaceType.FOUNDATION in results:
            slope_results[SurfaceType.FOUNDATION] = estimate_slope_volume(
                dem_path,
                project.foundation.polygon,
                results[SurfaceType.FOUNDATION].plateau_height,
                project.slope_angle_deg,
                project.slope_sample_spacing_m,
            )
        for st, src_cfg in (
            (SurfaceType.BOOM, project.boom),
            (SurfaceType.ROTOR_STORAGE, project.rotor_storage),
            (SurfaceType.ROAD_ACCESS, project.road_access),
        ):
            if src_cfg is not None and st in results:
                slope_results[st] = estimate_slope_volume(
                    dem_path,
                    src_cfg.polygon,
                    results[st].plateau_height,
                    project.slope_angle_deg,
                    project.slope_sample_spacing_m,
                )

    return MultiSurfaceResult(
        crane_optimum_height=crane_optimum,
        surface_results=results,
        fok=project.fok,
        foundation_depth=project.foundation_depth,
        gravel_thickness=project.gravel_thickness,
        slope_results=slope_results,
        boom_slope_percent=boom_slope,
        rotor_offset_m=rotor_offset,
        road_slope_percent=road_slope,
    )
