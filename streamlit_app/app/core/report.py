"""
Report-Erzeugung (HTML + optional PDF) für ein Multi-Surface-Ergebnis.

Pragmatischer MVP-Port von core/report_generator.py: Jinja2 + WeasyPrint
(optional), eingebettete PNG-Profile per base64, statische Übersichtskarte
über matplotlib.
"""

from __future__ import annotations

import base64
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from jinja2 import Environment, FileSystemLoader, select_autoescape  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402
from shapely.geometry.base import BaseGeometry  # noqa: E402

from .multi_surface import MultiSurfaceResult, SurfaceType  # noqa: E402

log = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _b64(path: str | Path) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def render_overview_map(
    dem_path: str | Path,
    surfaces: dict[str, BaseGeometry],
    output_path: str | Path,
    figsize: tuple[float, float] = (8.0, 6.0),
) -> str:
    """Matplotlib-Karte: DEM-Hillshade + Polygon-Outlines."""
    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype(float)
        nodata = src.nodata
        bounds = src.bounds
    if nodata is not None:
        dem = np.where(dem == nodata, np.nan, dem)

    fig, ax = plt.subplots(figsize=figsize, dpi=150)
    im = ax.imshow(
        dem,
        cmap="terrain",
        extent=(bounds.left, bounds.right, bounds.bottom, bounds.top),
        origin="upper",
    )
    fig.colorbar(im, ax=ax, label="Höhe [m ü.NN]", shrink=0.7)

    colors = {"crane": "#d04848", "foundation": "#1f6feb", "boom": "#5bb35b", "road": "#a06bff"}
    for name, geom in surfaces.items():
        color = colors.get(name, "#444")
        if isinstance(geom, Polygon):
            xs, ys = geom.exterior.xy
            ax.plot(xs, ys, color=color, lw=2.0, label=name)
        elif geom.geom_type == "MultiPolygon":
            for i, part in enumerate(geom.geoms):
                xs, ys = part.exterior.xy
                ax.plot(xs, ys, color=color, lw=2.0, label=name if i == 0 else None)

    ax.set_xlabel("UTM Easting [m]")
    ax.set_ylabel("UTM Northing [m]")
    ax.set_title("Übersicht")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_aspect("equal")
    fig.tight_layout()

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out)


def render_html_report(
    result: MultiSurfaceResult,
    project_name: str,
    crs_epsg: int,
    output_html: str | Path,
    map_image_path: Optional[str | Path] = None,
    profile_paths: Optional[Iterable[dict]] = None,
) -> str:
    """Rendert HTML aus dem MVP-Template."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html")

    surfaces_ctx = []
    for stype, r in result.surface_results.items():
        surfaces_ctx.append(
            {
                "display_name": stype.display_name,
                "plateau_height": r.plateau_height,
                "platform_area_m2": r.platform_area_m2,
                "cut_m3": r.cut_m3,
                "fill_m3": r.fill_m3,
                "net_m3": r.net_m3,
                "terrain_min": r.terrain_min,
                "terrain_max": r.terrain_max,
                "terrain_mean": r.terrain_mean,
            }
        )

    profiles_ctx = []
    if profile_paths:
        for prof in profile_paths:
            p = Path(prof["path"])
            if not p.exists():
                continue
            profiles_ctx.append(
                {
                    "title": f"{prof.get('type', 'Profil')} {prof.get('index', 0):02d}",
                    "length": prof.get("length", 0.0),
                    "b64": _b64(p),
                }
            )

    html = template.render(
        project_name=project_name,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        crs_epsg=crs_epsg,
        fok=result.fok,
        foundation_depth=result.foundation_depth,
        gravel_thickness=result.gravel_thickness,
        crane_optimum_height=result.crane_optimum_height,
        total_cut_m3=result.total_cut_m3,
        total_fill_m3=result.total_fill_m3,
        net_m3=result.net_m3,
        total_moved_m3=result.total_moved_m3,
        surfaces=surfaces_ctx,
        profiles=profiles_ctx,
        map_image_b64=_b64(map_image_path) if map_image_path else None,
    )
    out = Path(output_html)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return str(out)


def render_pdf_from_html(html_path: str | Path, output_pdf: str | Path) -> str:
    """Konvertiert HTML zu PDF via WeasyPrint, wenn installiert."""
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError as e:
        raise RuntimeError("WeasyPrint nicht installiert — PDF-Erzeugung übersprungen") from e
    HTML(filename=str(html_path)).write_pdf(str(output_pdf))
    return str(output_pdf)
