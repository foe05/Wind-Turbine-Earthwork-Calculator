"""
Input validation utilities for Wind Turbine Earthwork Calculator V2

Provides validation functions for user inputs and data.
"""

import os
from pathlib import Path
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsRasterLayer,
    QgsGeometry,
    QgsProcessingException
)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_file_exists(file_path, extension=None):
    """
    Validate that a file exists and optionally has the correct extension.

    Args:
        file_path (str): Path to file
        extension (str): Expected file extension (e.g., '.dxf'), optional

    Returns:
        Path: Validated file path

    Raises:
        ValidationError: If file doesn't exist or has wrong extension
    """
    path = Path(file_path)

    if not path.exists():
        raise ValidationError(f"File does not exist: {file_path}")

    if not path.is_file():
        raise ValidationError(f"Path is not a file: {file_path}")

    if extension and path.suffix.lower() != extension.lower():
        raise ValidationError(
            f"Wrong file extension: {path.suffix}, expected {extension}"
        )

    return path


def validate_height_range(min_height, max_height, step):
    """
    Validate height optimization parameters.

    Args:
        min_height (float): Minimum height
        max_height (float): Maximum height
        step (float): Height step

    Raises:
        ValidationError: If parameters are invalid
    """
    if max_height <= min_height:
        raise ValidationError(
            f"max_height ({max_height}) must be greater than "
            f"min_height ({min_height})"
        )

    if step <= 0:
        raise ValidationError(f"Height step must be positive, got {step}")

    if step > (max_height - min_height):
        raise ValidationError(
            f"Height step ({step}) is larger than height range "
            f"({max_height - min_height})"
        )

    # Check for reasonable number of scenarios
    num_scenarios = int((max_height - min_height) / step) + 1
    if num_scenarios > 10000:
        raise ValidationError(
            f"Too many scenarios ({num_scenarios}). "
            f"Please increase step size or reduce height range."
        )

    if num_scenarios < 2:
        raise ValidationError(
            f"Not enough scenarios ({num_scenarios}). "
            f"Please decrease step size or increase height range."
        )


def validate_crs(crs, expected_epsg=25832):
    """
    Validate coordinate reference system.

    Args:
        crs (QgsCoordinateReferenceSystem): CRS to validate
        expected_epsg (int): Expected EPSG code

    Raises:
        ValidationError: If CRS is not the expected one
    """
    if not crs.isValid():
        raise ValidationError("Invalid coordinate reference system")

    actual_epsg = crs.postgisSrid()
    if actual_epsg != expected_epsg:
        raise ValidationError(
            f"Wrong CRS: EPSG:{actual_epsg}, expected EPSG:{expected_epsg}"
        )


def validate_polygon(geometry):
    """
    Validate polygon geometry.

    Args:
        geometry (QgsGeometry): Polygon to validate

    Raises:
        ValidationError: If polygon is invalid
    """
    if geometry.isEmpty():
        raise ValidationError("Polygon is empty")

    if not geometry.isGeosValid():
        errors = geometry.validateGeometry()
        if errors:
            # what is a property/string, not a method
            error_msg = "; ".join([e.what if hasattr(e, 'what') else str(e) for e in errors])
            raise ValidationError(f"Invalid polygon geometry: {error_msg}")
        raise ValidationError("Invalid polygon geometry")

    area = geometry.area()
    if area <= 0:
        raise ValidationError(f"Polygon has invalid area: {area}")


def validate_raster_layer(raster_layer, required_crs_epsg=25832):
    """
    Validate raster layer.

    Args:
        raster_layer (QgsRasterLayer): Raster layer to validate
        required_crs_epsg (int): Required EPSG code

    Raises:
        ValidationError: If raster is invalid
    """
    if not raster_layer.isValid():
        raise ValidationError("Raster layer is not valid")

    # Check CRS
    crs = raster_layer.crs()
    validate_crs(crs, required_crs_epsg)

    # Check that it's a single-band raster
    if raster_layer.bandCount() != 1:
        raise ValidationError(
            f"Raster must have exactly 1 band, got {raster_layer.bandCount()}"
        )


def validate_raster_covers_geometry(raster_layer, geometry, buffer_m=0):
    """
    Validate that raster covers the geometry (with optional buffer).

    Args:
        raster_layer (QgsRasterLayer): Raster layer
        geometry (QgsGeometry): Geometry to check
        buffer_m (float): Buffer distance in meters

    Raises:
        ValidationError: If raster doesn't cover geometry
    """
    raster_extent = raster_layer.extent()
    geom_extent = geometry.boundingBox()

    # Add buffer
    geom_extent.setXMinimum(geom_extent.xMinimum() - buffer_m)
    geom_extent.setYMinimum(geom_extent.yMinimum() - buffer_m)
    geom_extent.setXMaximum(geom_extent.xMaximum() + buffer_m)
    geom_extent.setYMaximum(geom_extent.yMaximum() + buffer_m)

    if not raster_extent.contains(geom_extent):
        raise ValidationError(
            f"Raster does not cover geometry extent. "
            f"Raster: {raster_extent.toString()}, "
            f"Geometry (with {buffer_m}m buffer): {geom_extent.toString()}"
        )


def validate_positive_number(value, name, minimum=0, maximum=None):
    """
    Validate that a number is positive and within range.

    Args:
        value (float): Value to validate
        name (str): Parameter name (for error message)
        minimum (float): Minimum allowed value
        maximum (float): Maximum allowed value (optional)

    Raises:
        ValidationError: If value is invalid
    """
    if value < minimum:
        raise ValidationError(
            f"{name} must be >= {minimum}, got {value}"
        )

    if maximum is not None and value > maximum:
        raise ValidationError(
            f"{name} must be <= {maximum}, got {value}"
        )


def validate_output_path(output_path, extension=None):
    """
    Validate output file path.

    Args:
        output_path (str): Output file path
        extension (str): Expected file extension (optional)

    Returns:
        Path: Validated output path

    Raises:
        ValidationError: If path is invalid
    """
    path = Path(output_path)

    # Check if parent directory exists
    if not path.parent.exists():
        raise ValidationError(
            f"Output directory does not exist: {path.parent}"
        )

    # Check if parent directory is writable
    if not os.access(path.parent, os.W_OK):
        raise ValidationError(
            f"Output directory is not writable: {path.parent}"
        )

    # Check extension
    if extension and path.suffix.lower() != extension.lower():
        raise ValidationError(
            f"Wrong output file extension: {path.suffix}, expected {extension}"
        )

    return path
