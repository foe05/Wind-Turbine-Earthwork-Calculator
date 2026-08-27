"""
Vorabprüfung der Pipeline-Eingaben.

`core/validation.py` ist portiert, getestet — und wurde bisher von niemandem
aufgerufen. Die Pipeline stolperte stattdessen über schlechte Eingaben, im
ungünstigen Fall erst nach dem DEM-Download, also nach dem teuersten Schritt.

Dieses Modul bündelt die Prüfungen an den drei Stellen, an denen sie etwas
sparen:

1. `check_inputs()`   — reine Parameter und Dateien, vor allem anderen
2. `check_geometries()` — nach dem DXF-Import, **vor** der DEM-Beschaffung
3. `check_dem()`      — nach der DEM-Beschaffung, vor dem Höhen-Sweep

Alles wirft `ValidationError` mit deutscher Meldung; die Pipeline reicht sie
unverändert nach oben, wo sie in der Oberfläche landet und — seit der
Lauf-Mitschrift — als `failed` in der Historie steht.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import rasterio
from shapely.geometry.base import BaseGeometry

from ..core.validation import (
    UTM_ZONES_DE,
    ValidationError,
    validate_crs_epsg,
    validate_file_exists,
    validate_height_range,
    validate_polygon,
    validate_positive_number,
    validate_raster_covers_geometry,
    validate_raster_dataset,
)

if TYPE_CHECKING:  # pragma: no cover - nur für Typprüfung
    from .pipeline import PipelineInputs

log = logging.getLogger(__name__)

#: Maximale Ausdehnung eines Standorts. Greift nur bei groben Verwechslungen —
#: etwa wenn Kranstellfläche und Fundament aus zwei verschiedenen WEA stammen.
#: Bewusst großzügig: es geht um "offensichtlich falsche Datei", nicht um
#: geometrische Feinheiten.
MAX_SITE_EXTENT_M = 5_000.0

#: Gröbste noch sinnvolle DEM-Auflösung. hoehendaten.de liefert 1 m.
MAX_DEM_RESOLUTION_M = 5.0


def check_inputs(inputs: "PipelineInputs") -> None:
    """Parameter und Dateien prüfen, bevor irgendetwas geladen wird."""
    validate_crs_epsg(inputs.crs_epsg, 25832)

    validate_file_exists(inputs.crane_pad_dxf, extension=".dxf")
    validate_file_exists(inputs.foundation_dxf, extension=".dxf")
    for path, label in (
        (inputs.boom_dxf, "Auslegerfläche"),
        (inputs.rotor_storage_dxf, "Blattlagerfläche"),
        (inputs.road_access_dxf, "Zufahrtsstraße"),
        (inputs.holms_dxf, "Holme"),
    ):
        # Optionale Surfaces bleiben fail-soft: fehlt die Datei, wird sie
        # später übersprungen. Eine *falsche* Endung ist aber ein Tippfehler.
        if path and not str(path).lower().endswith(".dxf"):
            raise ValidationError(f"{label}: erwartet eine .dxf-Datei, bekommen {path}")

    if inputs.dem_path:
        validate_file_exists(inputs.dem_path)

    validate_positive_number(inputs.foundation_depth, "Fundament-Tiefe", minimum=0.01, maximum=50.0)
    validate_positive_number(inputs.gravel_thickness, "Schotterdicke", minimum=0.0, maximum=5.0)
    validate_positive_number(inputs.dem_buffer_m, "DEM-Puffer", minimum=1.0, maximum=5_000.0)

    if inputs.optimize_crane_height:
        validate_positive_number(
            inputs.search_range_below_fok, "Suchbereich unter FOK", minimum=0.0, maximum=50.0
        )
        validate_positive_number(
            inputs.search_range_above_fok, "Suchbereich über FOK", minimum=0.0, maximum=50.0
        )
        validate_height_range(
            inputs.fok - inputs.search_range_below_fok,
            inputs.fok + inputs.search_range_above_fok,
            inputs.coarse_step,
        )
        validate_positive_number(inputs.fine_step, "Feine Schrittweite", minimum=0.001, maximum=1.0)

    _check_sweep(
        inputs.boom_slope_optimize,
        inputs.boom_slope_min_percent,
        inputs.boom_slope_max_percent,
        inputs.boom_slope_step_percent,
        "Ausleger-Neigung",
    )
    _check_sweep(
        inputs.rotor_offset_optimize,
        inputs.rotor_offset_min_m,
        inputs.rotor_offset_max_m,
        inputs.rotor_offset_step_m,
        "Blattlager-Versatz",
    )
    _check_sweep(
        inputs.road_slope_optimize,
        inputs.road_slope_min_percent,
        inputs.road_slope_max_percent,
        inputs.road_slope_step_percent,
        "Zufahrts-Neigung",
    )

    if inputs.generate_profiles:
        validate_positive_number(
            inputs.profile_spacing, "Profil-Abstand", minimum=0.1, maximum=1_000.0
        )

    if inputs.include_slope_volume:
        if not 0.0 < inputs.slope_angle_deg < 90.0:
            raise ValidationError(
                f"Böschungswinkel muss zwischen 0° und 90° liegen, bekommen {inputs.slope_angle_deg}°"
            )
        validate_positive_number(
            inputs.slope_sample_spacing_m, "Böschungs-Stützstellenabstand", minimum=0.01, maximum=100.0
        )

    validate_positive_number(inputs.mesh_decimation, "Mesh-Dezimierung", minimum=1, maximum=100)


def _check_sweep(enabled: bool, low: float, high: float, step: float, label: str) -> None:
    """Ein Optimierungs-Sweep muss einen sinnvollen Bereich haben."""
    if not enabled:
        return
    if high <= low:
        raise ValidationError(f"{label}: Maximum ({high}) muss größer sein als Minimum ({low})")
    if step <= 0:
        raise ValidationError(f"{label}: Schrittweite muss > 0 sein, bekommen {step}")
    steps = (high - low) / step
    if steps > 10_000:
        raise ValidationError(
            f"{label}: {int(steps)} Schritte sind zu viele (Maximum 10000) — "
            f"Schrittweite vergrößern oder Bereich verkleinern"
        )


def check_geometries(
    crane: BaseGeometry,
    foundation: BaseGeometry,
    optional: Optional[dict[str, BaseGeometry]] = None,
) -> None:
    """Geometrien nach dem DXF-Import prüfen — vor der DEM-Beschaffung.

    Der Standortabgleich ist der eigentliche Zweck: liegen die Flächen
    kilometerweit auseinander, stammen sie aus verschiedenen Anlagen. Ohne
    diese Prüfung würde die Pipeline erst einen DEM über den gemeinsamen
    Umgriff herunterladen und dann Unsinn rechnen.
    """
    validate_polygon(crane)
    validate_polygon(foundation)

    named = {"Kranstellfläche": crane, "Fundamentfläche": foundation}
    for label, geom in (optional or {}).items():
        if geom is None:
            continue
        validate_polygon(geom)
        named[label] = geom

    reference = crane.centroid
    for label, geom in named.items():
        distance = reference.distance(geom.centroid)
        if distance > MAX_SITE_EXTENT_M:
            raise ValidationError(
                f"{label} liegt {distance / 1000:.1f} km von der Kranstellfläche entfernt "
                f"(Grenze {MAX_SITE_EXTENT_M / 1000:.0f} km). Stammen die DXF-Dateien aus "
                f"derselben Anlage?"
            )


def check_dem(
    dem_path: str,
    inputs: "PipelineInputs",
    geometries: list[BaseGeometry],
) -> None:
    """DEM prüfen, bevor der Höhen-Sweep darüber läuft.

    Fängt vor allem den Fall ab, dass ein selbst mitgebrachtes DEM den
    Standort gar nicht abdeckt — sonst rechnet der Sweep über nodata.
    """
    with rasterio.open(dem_path) as dataset:
        validate_raster_dataset(
            dataset,
            required_crs_epsg=inputs.crs_epsg,
            max_resolution=MAX_DEM_RESOLUTION_M,
        )
        for geom in geometries:
            if geom is not None and not geom.is_empty:
                validate_raster_covers_geometry(dataset, geom)


__all__ = [
    "MAX_DEM_RESOLUTION_M",
    "MAX_SITE_EXTENT_M",
    "UTM_ZONES_DE",
    "ValidationError",
    "check_dem",
    "check_geometries",
    "check_inputs",
]
