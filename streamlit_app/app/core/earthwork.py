"""
Cut/Fill-Mathematik + Höhen-Sweep (portiert aus core/earthwork_calculator.py
und multi_surface_calculator.py, MVP-Scope).

Pixel-weise Cut/Fill gegen ein konstantes Plateau, identisch zum
Plugin-Regression-Test (wea45mit3d.zip). Eingabe: DEM-Pfad + shapely-Polygon
in EPSG:25832, Plateauhöhe in m ü.NN.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry.base import BaseGeometry

log = logging.getLogger(__name__)


@dataclass
class CutFillResult:
    """Ergebnis einer einzelnen Plateau-Berechnung."""

    plateau_height: float
    cut_m3: float
    fill_m3: float
    platform_area_m2: float
    terrain_min: float
    terrain_max: float
    terrain_mean: float
    num_pixels: int

    @property
    def net_m3(self) -> float:
        return self.cut_m3 - self.fill_m3

    @property
    def total_moved_m3(self) -> float:
        return self.cut_m3 + self.fill_m3


def cut_fill_for_polygon(
    dem_path: str | Path,
    polygon: BaseGeometry,
    plateau_height: float,
) -> CutFillResult:
    """Pixel-weise Cut/Fill für ein Polygon gegen ein konstantes Plateau.

    Spiegelt MultiSurfaceCalculator._calculate_foundation /_calculate_crane_pad
    (Plugin): für jedes Pixel innerhalb des Polygons (und gültig != nodata) wird
    diff = z - plateau_height berechnet; positives diff zählt als Abtrag,
    negatives als Auftrag, jeweils multipliziert mit der Pixelfläche.
    """
    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype(float)
        transform = src.transform
        shape_ = src.shape
        nodata = src.nodata
        pixel_area = abs(transform.a) * abs(transform.e)

    mask = geometry_mask(
        [polygon.__geo_interface__],
        transform=transform,
        out_shape=shape_,
        invert=True,
    )
    valid = (dem != nodata) if nodata is not None else np.ones_like(dem, dtype=bool)
    elev = dem[mask & valid]

    if elev.size == 0:
        log.warning("Kein gültiges DEM-Pixel im Polygon — leeres Ergebnis")
        return CutFillResult(plateau_height, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)

    diff = elev - plateau_height
    pos = diff[diff > 0]
    neg = diff[diff < 0]
    cut = float(pos.sum() * pixel_area)
    fill = float((-neg).sum() * pixel_area)

    return CutFillResult(
        plateau_height=plateau_height,
        cut_m3=cut,
        fill_m3=fill,
        platform_area_m2=float(elev.size * pixel_area),
        terrain_min=float(elev.min()),
        terrain_max=float(elev.max()),
        terrain_mean=float(elev.mean()),
        num_pixels=int(elev.size),
    )


def height_sweep(
    dem_path: str | Path,
    polygon: BaseGeometry,
    h_min: float,
    h_max: float,
    step: float,
    objective: str = "min_total",
) -> tuple[float, CutFillResult, list[CutFillResult]]:
    """Sweep der Plateauhöhe in [h_min, h_max] mit Schrittweite step.

    Objective:
        'min_total' — minimiere Cut+Fill (kleinster Massenumfang)
        'min_net'   — minimiere |Cut-Fill| (ausgeglichene Bilanz)
        'min_cut'   — minimiere reinen Abtrag

    Liefert (best_plateau, best_result, alle_results).
    """
    if step <= 0:
        raise ValueError(f"step muss > 0 sein, bekommen {step}")
    if h_max < h_min:
        raise ValueError(f"h_max ({h_max}) < h_min ({h_min})")

    candidates: list[CutFillResult] = []
    h = h_min
    # Schleife inkl. h_max + numerischer Spielraum
    while h <= h_max + 1e-9:
        candidates.append(cut_fill_for_polygon(dem_path, polygon, h))
        h += step

    if not candidates:
        raise RuntimeError("Höhen-Sweep lieferte keine Kandidaten")

    def key(r: CutFillResult) -> float:
        if objective == "min_net":
            return abs(r.net_m3)
        if objective == "min_cut":
            return r.cut_m3
        return r.total_moved_m3

    best = min(candidates, key=key)
    return best.plateau_height, best, candidates


def coarse_then_fine_sweep(
    dem_path: str | Path,
    polygon: BaseGeometry,
    h_min: float,
    h_max: float,
    coarse_step: float = 0.5,
    fine_step: float = 0.01,
    fine_radius: float = 0.5,
    objective: str = "min_total",
) -> tuple[float, CutFillResult, list[CutFillResult]]:
    """Zweistufiger Sweep: coarse über volle Range, fine um das Minimum.

    Spart Rechenzeit gegenüber direktem feinem Sweep über die Gesamtspanne.
    """
    _, best_coarse, all_coarse = height_sweep(
        dem_path, polygon, h_min, h_max, coarse_step, objective
    )
    fine_lo = max(h_min, best_coarse.plateau_height - fine_radius)
    fine_hi = min(h_max, best_coarse.plateau_height + fine_radius)
    _, best_fine, all_fine = height_sweep(
        dem_path, polygon, fine_lo, fine_hi, fine_step, objective
    )
    combined = all_coarse + all_fine
    return best_fine.plateau_height, best_fine, combined
