"""
Eingabe-Validierung (deutschsprachige Fehlermeldungen).

Portiert aus windturbine_earthwork_calculator_v2/utils/validation.py.
QGIS- und i18n-Layer entfernt; rasterio statt QgsRasterLayer; shapely statt QgsGeometry.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import rasterio
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry


class ValidationError(Exception):
    """Validierungsfehler mit deutscher Meldung."""


# ---------------------------------------------------------------------------
# Dateien / Pfade
# ---------------------------------------------------------------------------

def validate_file_exists(file_path: str | os.PathLike, extension: Optional[str] = None) -> Path:
    """Existenz und optionale Endung einer Datei prüfen."""
    path = Path(file_path)
    if not path.exists():
        raise ValidationError(f"Datei nicht gefunden: {file_path}")
    if not path.is_file():
        raise ValidationError(f"Pfad ist keine Datei: {file_path}")
    if extension and path.suffix.lower() != extension.lower():
        raise ValidationError(
            f"Falsche Dateiendung: erwartet '{extension}', bekommen '{path.suffix}'"
        )
    return path


def validate_output_path(output_path: str | os.PathLike, extension: Optional[str] = None) -> Path:
    """Ausgabe-Pfad: Elternverzeichnis existiert und ist schreibbar."""
    path = Path(output_path)
    if not path.parent.exists():
        raise ValidationError(f"Ausgabe-Verzeichnis existiert nicht: {path.parent}")
    if not os.access(path.parent, os.W_OK):
        raise ValidationError(f"Ausgabe-Verzeichnis ist nicht schreibbar: {path.parent}")
    if extension and path.suffix.lower() != extension.lower():
        raise ValidationError(
            f"Falsche Dateiendung: erwartet '{extension}', bekommen '{path.suffix}'"
        )
    return path


# ---------------------------------------------------------------------------
# Numerische Parameter
# ---------------------------------------------------------------------------

def validate_height_range(min_height: float, max_height: float, step: float) -> None:
    if max_height <= min_height:
        raise ValidationError(
            f"Maximale Höhe ({max_height}) muss > minimale Höhe ({min_height}) sein"
        )
    if step <= 0:
        raise ValidationError(f"Höhen-Schrittweite muss > 0 sein, bekommen {step}")
    if step > (max_height - min_height):
        raise ValidationError(
            f"Schrittweite ({step}) ist größer als der Höhenbereich ({max_height - min_height})"
        )
    num = int((max_height - min_height) / step) + 1
    if num > 10_000:
        raise ValidationError(f"Zu viele Höhen-Szenarien: {num} (Maximum 10000)")
    if num < 2:
        raise ValidationError(f"Zu wenige Höhen-Szenarien: {num} (Minimum 2)")


def validate_positive_number(
    value: float,
    name: str,
    minimum: float = 0.0,
    maximum: Optional[float] = None,
) -> None:
    if value < minimum:
        raise ValidationError(f"{name} = {value} ist kleiner als das Minimum {minimum}")
    if maximum is not None and value > maximum:
        raise ValidationError(f"{name} = {value} ist größer als das Maximum {maximum}")


# ---------------------------------------------------------------------------
# CRS / Geometrie
# ---------------------------------------------------------------------------

UTM_ZONES_DE = {25832, 25833, 25834, 25835, 25836}


def validate_crs_epsg(epsg: Optional[int], expected_epsg: int = 25832) -> None:
    """Prüft einen EPSG-Code (rasterio liefert .crs.to_epsg())."""
    if epsg is None:
        raise ValidationError("CRS konnte nicht ermittelt werden (None)")
    if expected_epsg in UTM_ZONES_DE:
        # Wenn der erwartete Code eine UTM-DE-Zone ist, erlaube alle UTM-DE-Zonen
        if epsg not in UTM_ZONES_DE:
            raise ValidationError(
                f"CRS-Mismatch: EPSG {epsg}, erwartet UTM-Zone aus DE "
                f"(25832–25836)"
            )
    else:
        if epsg != expected_epsg:
            raise ValidationError(f"CRS-Mismatch: EPSG {epsg}, erwartet EPSG {expected_epsg}")


def validate_polygon(geometry: BaseGeometry) -> None:
    """Basisvalidierung Polygon: nicht leer, valid, simple, Fläche > 0."""
    if geometry.is_empty:
        raise ValidationError("Geometrie ist leer")
    if not geometry.is_simple:
        raise ValidationError("Geometrie hat Selbst-Überschneidungen")
    if not geometry.is_valid:
        raise ValidationError(f"Ungültige Geometrie: {geometry.is_valid}")  # shapely .is_valid returns bool; explain_validity hat Details
    if geometry.area <= 0:
        raise ValidationError(f"Ungültige Fläche: {geometry.area}")


def validate_polygon_topology(geometry: BaseGeometry) -> None:
    """Umfassende Topologie-Prüfung: Typ, Vertices, Orientierung, Multipart."""
    if geometry.is_empty:
        raise ValidationError("Geometrie ist leer")
    if not geometry.is_valid:
        raise ValidationError("Ungültige Geometrie (GEOS-Topologie verletzt)")
    if not isinstance(geometry, (Polygon, MultiPolygon)):
        raise ValidationError(
            f"Falscher Geometrie-Typ: {geometry.geom_type}, erwartet Polygon"
        )
    if isinstance(geometry, MultiPolygon):
        raise ValidationError("Multipart-Polygon nicht zulässig (nur Single-Part)")
    if not geometry.is_simple:
        raise ValidationError("Polygon hat Selbst-Überschneidungen")
    if geometry.area <= 0:
        raise ValidationError(f"Ungültige Fläche: {geometry.area}")

    coords = list(geometry.exterior.coords)
    if len(coords) < 4:
        raise ValidationError(
            f"Zu wenige Vertices: {len(coords)} (Minimum 4 inkl. Schlussvertex)"
        )

    # Außenring soll counter-clockwise sein (signed area > 0 in mathematischer Konvention).
    # shapely: exterior.is_ccw == True bedeutet counter-clockwise.
    if not geometry.exterior.is_ccw:
        raise ValidationError("Außenring ist im Uhrzeigersinn — muss gegen den Uhrzeigersinn sein")


# ---------------------------------------------------------------------------
# Raster (rasterio.DatasetReader)
# ---------------------------------------------------------------------------

def validate_raster_dataset(
    dataset: "rasterio.DatasetReader",
    required_crs_epsg: int = 25832,
    max_resolution: float = 5.0,
) -> None:
    """Prüfung eines geöffneten rasterio-Datasets."""
    if dataset.closed:
        raise ValidationError("Raster-Dataset ist geschlossen")

    epsg = dataset.crs.to_epsg() if dataset.crs else None
    validate_crs_epsg(epsg, required_crs_epsg)

    if dataset.count != 1:
        raise ValidationError(
            f"Raster muss einbändig sein, bekommen {dataset.count} Bänder"
        )

    if dataset.width <= 0 or dataset.height <= 0:
        raise ValidationError("Raster-Extent ist leer")

    px, py = dataset.res
    resolution = max(abs(px), abs(py))
    if resolution > max_resolution:
        raise ValidationError(
            f"Raster-Auflösung {resolution:.2f} m ist gröber als das Maximum {max_resolution} m"
        )


def validate_raster_covers_geometry(
    dataset: "rasterio.DatasetReader",
    geometry: BaseGeometry,
    buffer_m: float = 0.0,
) -> None:
    """Raster muss die (gepufferte) Geometry-Bounds abdecken."""
    minx, miny, maxx, maxy = geometry.bounds
    minx -= buffer_m
    miny -= buffer_m
    maxx += buffer_m
    maxy += buffer_m
    r = dataset.bounds  # rasterio BoundingBox(left, bottom, right, top)
    if not (r.left <= minx and r.bottom <= miny and r.right >= maxx and r.top >= maxy):
        raise ValidationError(
            f"Raster deckt Geometrie nicht ab. Raster=({r.left},{r.bottom},{r.right},{r.top}) "
            f"Geom+Buffer=({minx},{miny},{maxx},{maxy}) Puffer={buffer_m}m"
        )
