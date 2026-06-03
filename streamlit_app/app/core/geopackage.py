"""
GeoPackage-Export: bündelt Multi-Surface-Geometrien + Berechnungsergebnis
in ein einziges GeoPackage (kein QGIS nötig, geopandas+fiona).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Mapping, Optional

import geopandas as gpd
from shapely.geometry.base import BaseGeometry

from .multi_surface import MultiSurfaceResult, SurfaceType

log = logging.getLogger(__name__)


def write_multisurface_geopackage(
    output_path: str | Path,
    surfaces: Mapping[SurfaceType, BaseGeometry],
    result: Optional[MultiSurfaceResult] = None,
    crs_epsg: int = 25832,
) -> str:
    """Schreibt ein GeoPackage mit einem Layer je Surface plus Attribute aus dem Result.

    Layer-Namen entsprechen den deutschen Konventionen (kranstellflaeche,
    fundamentflaeche, etc., analog zum Plugin-Output).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    written_layers: list[str] = []
    for stype, geom in surfaces.items():
        attrs = {
            "name": [stype.display_name],
            "surface_type": [stype.value],
        }
        if result is not None and stype in result.surface_results:
            r = result.surface_results[stype]
            attrs.update(
                {
                    "plateau_height_m": [r.plateau_height],
                    "cut_m3": [r.cut_m3],
                    "fill_m3": [r.fill_m3],
                    "platform_area_m2": [r.platform_area_m2],
                    "net_m3": [r.net_m3],
                    "terrain_min": [r.terrain_min],
                    "terrain_max": [r.terrain_max],
                    "terrain_mean": [r.terrain_mean],
                }
            )
        gdf = gpd.GeoDataFrame(attrs, geometry=[geom], crs=f"EPSG:{crs_epsg}")
        gdf.to_file(output_path, layer=stype.value, driver="GPKG")
        written_layers.append(stype.value)

    log.info("GeoPackage geschrieben: %s (Layer: %s)", output_path, ", ".join(written_layers))
    return str(output_path)
