"""
Input validation utilities for Wind Turbine Earthwork Calculator V2

Provides validation functions for user inputs and data with bilingual error messages.
"""

import os
from pathlib import Path
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsRasterLayer,
    QgsGeometry,
    QgsProcessingException,
    QgsWkbTypes
)

from .i18n import get_message, get_language
from .error_messages import ERROR_MESSAGES


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def _format_error(error_key, **params):
    """
    Format error message with fix suggestion.

    Args:
        error_key (str): Error message key
        **params: Parameters for message formatting

    Returns:
        str: Formatted error message with fix suggestion
    """
    error_msg = get_message(error_key, ERROR_MESSAGES, **params)
    lang = get_language()
    fix_msg = ERROR_MESSAGES[error_key]['fix'][lang]
    return f"{error_msg}\n{fix_msg}"


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
        raise ValidationError(_format_error('file_not_found', file_path=file_path))

    if not path.is_file():
        raise ValidationError(_format_error('not_a_file', file_path=file_path))

    if extension and path.suffix.lower() != extension.lower():
        raise ValidationError(_format_error('wrong_file_extension',
                                           actual=path.suffix, expected=extension))

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
        raise ValidationError(_format_error('height_max_less_than_min',
                                           max_height=max_height,
                                           min_height=min_height))

    if step <= 0:
        raise ValidationError(_format_error('height_step_not_positive', step=step))

    if step > (max_height - min_height):
        raise ValidationError(_format_error('height_step_too_large',
                                           step=step,
                                           range=(max_height - min_height)))

    # Check for reasonable number of scenarios
    num_scenarios = int((max_height - min_height) / step) + 1
    if num_scenarios > 10000:
        raise ValidationError(_format_error('height_too_many_scenarios',
                                           num_scenarios=num_scenarios))

    if num_scenarios < 2:
        raise ValidationError(_format_error('height_too_few_scenarios',
                                           num_scenarios=num_scenarios))


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
        raise ValidationError(_format_error('crs_invalid'))

    actual_epsg = crs.postgisSrid()
    if actual_epsg != expected_epsg:
        raise ValidationError(_format_error('crs_mismatch',
                                           actual=actual_epsg,
                                           expected=expected_epsg))


def validate_polygon(geometry):
    """
    Validate polygon geometry with detailed error reporting and location.

    Args:
        geometry (QgsGeometry): Polygon to validate

    Raises:
        ValidationError: If polygon is invalid, with detailed location info when available
    """
    if geometry.isEmpty():
        raise ValidationError(_format_error('geometry_empty'))

    # Check if geometry is simple (no self-intersections)
    if not geometry.isSimple():
        raise ValidationError(_format_error('geometry_not_simple'))

    # Detailed geometry validation
    if not geometry.isGeosValid():
        errors = geometry.validateGeometry()
        if errors:
            # Extract first error with location details
            first_error = errors[0]
            error_text = first_error.what if hasattr(first_error, 'what') else str(first_error)

            # Try to extract location if available
            if hasattr(first_error, 'hasWhere') and first_error.hasWhere():
                error_location = first_error.where()
                x = error_location.x()
                y = error_location.y()

                # Categorize error type based on message
                error_lower = error_text.lower()
                if 'self' in error_lower and 'intersect' in error_lower:
                    raise ValidationError(_format_error('geometry_self_intersection', x=x, y=y))
                elif 'spike' in error_lower or 'duplicat' in error_lower:
                    raise ValidationError(_format_error('geometry_spike_vertex', x=x, y=y))
                else:
                    # Generic error with location
                    raise ValidationError(_format_error('geometry_invalid', error=f"{error_text} at ({x:.2f}, {y:.2f})"))
            else:
                # No location available, use generic error
                # Collect all error messages
                error_msgs = []
                for e in errors:
                    msg = e.what if hasattr(e, 'what') else str(e)
                    error_msgs.append(msg)
                combined_error = "; ".join(error_msgs)
                raise ValidationError(_format_error('geometry_invalid', error=combined_error))
        else:
            # No specific errors, but geometry is invalid
            raise ValidationError(_format_error('geometry_invalid', error='Unknown validation error'))

    # Validate area
    area = geometry.area()
    if area <= 0:
        raise ValidationError(_format_error('geometry_invalid_area', area=area))


def validate_polygon_topology(geometry):
    """
    Validate polygon topology including orientation and vertex checks.

    This function performs comprehensive topology validation:
    - Checks for empty geometry
    - Validates GEOS topology
    - Verifies geometry type is polygon
    - Checks for minimum vertices (4 including closing vertex)
    - Validates area is positive
    - Checks polygon orientation (exterior rings must be counter-clockwise)
    - Ensures single-part geometry

    Args:
        geometry (QgsGeometry): Polygon geometry to validate

    Raises:
        ValidationError: If topology is invalid with detailed error message
    """
    # Check for empty geometry
    if geometry.isEmpty():
        raise ValidationError(_format_error('geometry_empty'))

    # Validate GEOS topology
    if not geometry.isGeosValid():
        errors = geometry.validateGeometry()
        if errors:
            first_error = errors[0]
            error_text = first_error.what if hasattr(first_error, 'what') else str(first_error)

            if hasattr(first_error, 'hasWhere') and first_error.hasWhere():
                error_location = first_error.where()
                x = error_location.x()
                y = error_location.y()
                error_lower = error_text.lower()

                if 'self' in error_lower and 'intersect' in error_lower:
                    raise ValidationError(_format_error('geometry_self_intersection', x=x, y=y))
                elif 'spike' in error_lower or 'duplicat' in error_lower:
                    raise ValidationError(_format_error('geometry_spike_vertex', x=x, y=y))
                else:
                    raise ValidationError(_format_error('geometry_invalid', error=f"{error_text} at ({x:.2f}, {y:.2f})"))
            else:
                error_msgs = [e.what if hasattr(e, 'what') else str(e) for e in errors]
                combined_error = "; ".join(error_msgs)
                raise ValidationError(_format_error('geometry_invalid', error=combined_error))
        else:
            raise ValidationError(_format_error('geometry_invalid', error='Unknown validation error'))

    # Check geometry type
    if geometry.type() != QgsWkbTypes.PolygonGeometry:
        geom_type_names = {
            QgsWkbTypes.PointGeometry: 'Point',
            QgsWkbTypes.LineGeometry: 'Line',
            QgsWkbTypes.PolygonGeometry: 'Polygon',
            QgsWkbTypes.UnknownGeometry: 'Unknown',
            QgsWkbTypes.NullGeometry: 'Null'
        }
        geom_type_name = geom_type_names.get(geometry.type(), f'Type {geometry.type()}')
        raise ValidationError(_format_error('geometry_wrong_type', geom_type=geom_type_name))

    # Check if simple (no self-intersections)
    if not geometry.isSimple():
        raise ValidationError(_format_error('geometry_not_simple'))

    # Validate area
    area = geometry.area()
    if area <= 0:
        raise ValidationError(_format_error('geometry_invalid_area', area=area))

    # Check for multipart geometries
    if geometry.isMultipart():
        raise ValidationError(_format_error('geometry_multipart'))

    # Get polygon and check minimum vertices
    polygon = geometry.asPolygon()
    if not polygon or not polygon[0]:
        raise ValidationError(_format_error('geometry_empty'))

    exterior_ring = polygon[0]
    num_vertices = len(exterior_ring)

    if num_vertices < 4:  # Minimum 3 vertices + closing vertex
        raise ValidationError(_format_error('geometry_too_few_vertices', vertices=num_vertices))

    # Check polygon orientation (exterior ring should be counter-clockwise)
    # Calculate signed area to determine orientation
    # Positive area = counter-clockwise (correct for exterior rings)
    # Negative area = clockwise (incorrect for exterior rings)
    signed_area = 0.0
    for i in range(num_vertices - 1):
        p1 = exterior_ring[i]
        p2 = exterior_ring[i + 1]
        signed_area += (p2.x() - p1.x()) * (p2.y() + p1.y())

    # If signed area is positive, the ring is clockwise (incorrect)
    if signed_area > 0:
        raise ValidationError(_format_error('geometry_clockwise_orientation'))


def validate_raster_layer(raster_layer, required_crs_epsg=25832, max_resolution=5.0):
    """
    Validate raster layer with detailed extent and resolution checks.

    Args:
        raster_layer (QgsRasterLayer): Raster layer to validate
        required_crs_epsg (int): Required EPSG code
        max_resolution (float): Maximum acceptable resolution in meters (default: 5.0m)

    Raises:
        ValidationError: If raster is invalid
    """
    if not raster_layer.isValid():
        raise ValidationError(_format_error('raster_invalid'))

    # Check CRS
    crs = raster_layer.crs()
    validate_crs(crs, required_crs_epsg)

    # Check that it's a single-band raster
    if raster_layer.bandCount() != 1:
        raise ValidationError(_format_error('raster_wrong_band_count',
                                           band_count=raster_layer.bandCount()))

    # Validate extent
    extent = raster_layer.extent()
    if extent.isEmpty():
        raise ValidationError(_format_error('raster_invalid'))

    # Check extent dimensions are reasonable (not zero or negative)
    width = extent.width()
    height = extent.height()
    if width <= 0 or height <= 0:
        raise ValidationError(_format_error('raster_invalid'))

    # Validate resolution
    # Resolution is in CRS units (meters for projected CRS)
    pixel_size_x = raster_layer.rasterUnitsPerPixelX()
    pixel_size_y = raster_layer.rasterUnitsPerPixelY()

    # Use the larger of the two resolutions for the check
    resolution = max(abs(pixel_size_x), abs(pixel_size_y))

    # Warn if resolution is too coarse (e.g., > 5m for detailed earthwork calculations)
    if resolution > max_resolution:
        raise ValidationError(_format_error('raster_resolution_too_coarse',
                                           resolution=resolution,
                                           recommended=max_resolution))


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
        raise ValidationError(_format_error('raster_does_not_cover_geometry',
                                           raster_extent=raster_extent.toString(),
                                           geom_extent=geom_extent.toString(),
                                           buffer_m=buffer_m))


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
        raise ValidationError(_format_error('value_below_minimum',
                                           name=name, minimum=minimum, value=value))

    if maximum is not None and value > maximum:
        raise ValidationError(_format_error('value_above_maximum',
                                           name=name, maximum=maximum, value=value))


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
        raise ValidationError(_format_error('output_dir_not_found',
                                           dir_path=str(path.parent)))

    # Check if parent directory is writable
    if not os.access(path.parent, os.W_OK):
        raise ValidationError(_format_error('output_dir_not_writable',
                                           dir_path=str(path.parent)))

    # Check extension
    if extension and path.suffix.lower() != extension.lower():
        raise ValidationError(_format_error('wrong_file_extension',
                                           actual=path.suffix, expected=extension))

    return path
