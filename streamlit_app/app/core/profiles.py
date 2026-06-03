"""
Geländeschnitte (portiert/MVP aus core/profile_generator.py).

Sampelt das DEM entlang Querschnitt-/Längslinien, plottet Gelände + Plateau
mit Cut-/Fill-Flächen über matplotlib Agg (headless).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Sequence

import matplotlib

matplotlib.use("Agg")  # headless

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from rasterio.sample import sample_gen as rio_sample  # noqa: E402
from shapely.geometry import LineString  # noqa: E402
from shapely.geometry.base import BaseGeometry  # noqa: E402

from .geometry import (  # noqa: E402
    create_parallel_longitudinal_sections,
    create_perpendicular_cross_sections,
)

log = logging.getLogger(__name__)


def sample_dem_along_line(
    dem_path: str | Path, line: LineString, step: float = 0.5
) -> tuple[np.ndarray, np.ndarray]:
    """Sampelt das DEM entlang einer Linie in step-Meter-Schritten.

    Returns (distances_m, elevations_m). NoData wird per np.nan markiert.
    """
    if line.length == 0:
        return np.array([]), np.array([])

    num = max(2, int(line.length / step) + 1)
    distances = np.linspace(0.0, line.length, num)
    points = [line.interpolate(d) for d in distances]
    xy = [(p.x, p.y) for p in points]

    with rasterio.open(dem_path) as src:
        nodata = src.nodata
        values = np.array(list(rio_sample(src, xy, indexes=1)), dtype=float).ravel()
    if nodata is not None:
        values[values == nodata] = np.nan
    return distances, values


def plot_section(
    distances: np.ndarray,
    elevations: np.ndarray,
    plateau_height: float,
    title: str,
    output_path: str | Path,
    vertical_exaggeration: float = 1.0,
) -> str:
    """Plot: Gelände-Kurve + Plateau + Cut/Fill-Schraffur."""
    fig, ax = plt.subplots(figsize=(10, 4), dpi=150)
    valid = ~np.isnan(elevations)
    d = distances[valid]
    z = elevations[valid]

    ax.plot(d, z, color="#5a3a22", lw=1.6, label="Gelände")
    ax.axhline(plateau_height, color="#1f6feb", lw=1.4, label=f"Plateau {plateau_height:.2f} m")

    # Cut (Gelände über Plateau) — orange
    ax.fill_between(d, z, plateau_height, where=z > plateau_height, color="#f4a259", alpha=0.55, label="Abtrag")
    # Fill (Gelände unter Plateau) — blau
    ax.fill_between(d, z, plateau_height, where=z < plateau_height, color="#4a90d9", alpha=0.55, label="Auftrag")

    ax.set_xlabel("Distanz [m]")
    ax.set_ylabel("Höhe [m ü.NN]")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=8)
    if vertical_exaggeration != 1.0:
        ax.set_aspect(1.0 / vertical_exaggeration)

    fig.tight_layout()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out)


def generate_profiles_for_polygon(
    dem_path: str | Path,
    polygon: BaseGeometry,
    plateau_height: float,
    output_dir: str | Path,
    spacing: float = 10.0,
    profile_type: str = "cross",  # 'cross' | 'long' | 'both'
    sample_step: float = 0.5,
    vertical_exaggeration: float = 1.0,
) -> list[dict]:
    """Erzeugt PNG-Profile durch ein Polygon.

    Returns list of dicts: {'path': str, 'type': str, 'index': int, 'length': float}.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    profiles: list[dict] = []

    def _render(sections: Sequence[dict], type_prefix: str, file_prefix: str):
        for i, sec in enumerate(sections, start=1):
            line = sec["geometry"]
            if not isinstance(line, LineString) or line.length == 0:
                continue
            distances, elevations = sample_dem_along_line(dem_path, line, step=sample_step)
            if distances.size == 0:
                continue
            title = f"{type_prefix} {i:02d} ({line.length:.1f} m)"
            out_path = output_dir / f"{file_prefix}_{i:02d}.png"
            plot_section(
                distances,
                elevations,
                plateau_height,
                title,
                out_path,
                vertical_exaggeration=vertical_exaggeration,
            )
            profiles.append(
                {
                    "path": str(out_path),
                    "type": type_prefix,
                    "index": i,
                    "length": float(line.length),
                }
            )

    if profile_type in ("cross", "both"):
        cross_sections = create_perpendicular_cross_sections(polygon, spacing=spacing)
        _render(cross_sections, "Querschnitt", "querschnitt")

    if profile_type in ("long", "both"):
        long_sections = create_parallel_longitudinal_sections(polygon, spacing=spacing)
        _render(long_sections, "Längsprofil", "laengsprofil")

    log.info("%d Profile gerendert -> %s", len(profiles), output_dir)
    return profiles
