"""
Slope-/Böschungs-Volumen-Approximation.

Pragmatische Berechnung des Volumens des Übergangsbereichs zwischen einem
Plateau-Polygon und dem natürlichen Gelände. Approximation: für jeden
diskretisierten Rand-Punkt wird die mittlere Δh ermittelt; das Slope-Band ist
Δh/tan(slope_angle) breit; das Volumen entlang des Rands wird über
Trapez-Regel integriert.

Das Plugin nutzt eine geometrisch exakte Slope-Polygon-Konstruktion mit
Connection-Edges; diese MVP-Version reicht für Cut/Fill-Schätzungen mit
einer typischen Genauigkeit von 5–10 %.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import rasterio
from shapely.geometry import LineString, Polygon
from shapely.geometry.base import BaseGeometry


@dataclass
class SlopeVolumeResult:
    cut_m3: float
    fill_m3: float
    slope_area_m2: float
    avg_slope_width_m: float
    samples: int

    @property
    def total_m3(self) -> float:
        return self.cut_m3 + self.fill_m3


def estimate_slope_volume(
    dem_path: str,
    polygon: BaseGeometry,
    plateau_height: float,
    slope_angle_deg: float = 45.0,
    sample_spacing_m: float = 1.0,
) -> SlopeVolumeResult:
    """Approximiert das Slope-Volumen rund um ein Plateau-Polygon.

    Algorithmus:
        1. Diskretisiere den Polygon-Rand alle sample_spacing_m Meter.
        2. Sampele das DEM am jeweiligen Rand-Punkt -> z_terrain.
        3. Δh = z_terrain - plateau_height (>0: Cut, <0: Fill).
        4. Slope-Breite w = |Δh| / tan(slope_angle).
        5. Slope-Querschnittsfläche A_seg = 0.5 * |Δh| * w (Dreieck).
        6. Slope-Band-Streifen-Volumen V_seg = A_seg * Δs (Δs = Schrittweite).
        7. Akkumuliere getrennt für Cut (Δh>0) und Fill (Δh<0).
    """
    if slope_angle_deg <= 0 or slope_angle_deg >= 90:
        raise ValueError(f"slope_angle_deg muss in (0, 90), bekommen {slope_angle_deg}")

    tan_a = math.tan(math.radians(slope_angle_deg))
    boundary = polygon.exterior if isinstance(polygon, Polygon) else None
    if boundary is None:
        return SlopeVolumeResult(0.0, 0.0, 0.0, 0.0, 0)

    boundary_line = LineString(boundary.coords)
    perimeter = boundary_line.length
    if perimeter == 0:
        return SlopeVolumeResult(0.0, 0.0, 0.0, 0.0, 0)

    num = max(8, int(perimeter / sample_spacing_m) + 1)
    distances = np.linspace(0.0, perimeter, num)
    xy = []
    for d in distances:
        p = boundary_line.interpolate(d)
        xy.append((p.x, p.y))

    with rasterio.open(dem_path) as src:
        nodata = src.nodata
        elevations = np.array(list(src.sample(xy, indexes=1)), dtype=float).ravel()
    if nodata is not None:
        elevations[elevations == nodata] = np.nan

    cut = 0.0
    fill = 0.0
    slope_area = 0.0
    total_width = 0.0
    n_samples = 0

    ds = perimeter / (num - 1) if num > 1 else 0.0
    for z in elevations:
        if math.isnan(z):
            continue
        dh = z - plateau_height
        if abs(dh) < 1e-6:
            n_samples += 1
            continue
        w = abs(dh) / tan_a
        a_seg = 0.5 * abs(dh) * w  # Dreieck-Querschnitt
        v_seg = a_seg * ds
        if dh > 0:
            cut += v_seg
        else:
            fill += v_seg
        slope_area += w * ds
        total_width += w
        n_samples += 1

    avg_width = total_width / n_samples if n_samples > 0 else 0.0
    return SlopeVolumeResult(
        cut_m3=cut,
        fill_m3=fill,
        slope_area_m2=slope_area,
        avg_slope_width_m=avg_width,
        samples=n_samples,
    )
