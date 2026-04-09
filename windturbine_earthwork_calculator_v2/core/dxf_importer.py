"""
DXF Importer for Wind Turbine Earthwork Calculator V2

Imports DXF files containing crane pad outlines (LWPOLYLINE entities)
and converts them to QGIS polygon geometries.

Author: Wind Energy Site Planning
Version: 2.0.0
"""

from pathlib import Path
from typing import List, Tuple, Optional
import math
import sys

try:
    import ezdxf
    EZDXF_AVAILABLE = True
    EZDXF_ERROR = None
except ImportError as e:
    EZDXF_AVAILABLE = False
    EZDXF_ERROR = str(e)

try:
    from shapely.geometry import LineString, Polygon as ShapelyPolygon
    from shapely.ops import linemerge, polygonize, unary_union
    import shapely
    SHAPELY_AVAILABLE = True
    SHAPELY_ERROR = None
except ImportError as e:
    SHAPELY_AVAILABLE = False
    SHAPELY_ERROR = str(e)

from qgis.core import (
    QgsGeometry,
    QgsPointXY,
    QgsCoordinateReferenceSystem,
    QgsWkbTypes
)

from ..utils.geometry_utils import (
    point_distance,
    find_nearest_point,
    validate_polygon_topology
)
from ..utils.logging_utils import get_plugin_logger
from ..utils.i18n import get_message
from ..utils.error_messages import ERROR_MESSAGES


class DXFImporter:
    """
    Imports DXF files and converts polylines to polygons.

    The importer handles:
    - Reading LWPOLYLINE entities from DXF files
    - Connecting multiple polylines to form closed polygons
    - Validating polygon topology
    - Converting to QGIS geometries with correct CRS
    """

    def __init__(self, dxf_path: str, tolerance: float = 0.01, crs_epsg: int = 25832):
        """
        Initialize DXF importer.

        Args:
            dxf_path (str): Path to DXF file
            tolerance (float): Tolerance for connecting polyline endpoints (meters)
            crs_epsg (int): EPSG code for coordinate reference system (default: 25832)

        Raises:
            ImportError: If ezdxf is not available
            FileNotFoundError: If DXF file doesn't exist
        """
        if not EZDXF_AVAILABLE:
            # Get Python executable path for better error message
            python_path = sys.executable
            site_packages = [p for p in sys.path if 'site-packages' in p]

            error_msg = (
                f"ezdxf package is required for DXF import.\n"
                f"Original error: {EZDXF_ERROR}\n\n"
                f"Python executable: {python_path}\n"
                f"Site-packages paths: {site_packages[:3]}\n\n"
                f"For QGIS on Windows, install using OSGeo4W Shell:\n"
                f"  1. Open OSGeo4W Shell (Start Menu -> OSGeo4W -> OSGeo4W Shell)\n"
                f"  2. Run: pip install ezdxf shapely\n\n"
                f"Or use the Python Console in QGIS:\n"
                f"  import subprocess; subprocess.check_call(['pip', 'install', 'ezdxf', 'shapely'])"
            )
            raise ImportError(error_msg)

        self.dxf_path = Path(dxf_path)
        if not self.dxf_path.exists():
            raise FileNotFoundError(f"DXF file not found: {dxf_path}")

        self.tolerance = tolerance
        self.crs_epsg = crs_epsg
        self.logger = get_plugin_logger()

        self.doc = None
        self.polylines = []

    def load_dxf(self):
        """
        Load DXF file.

        Raises:
            Exception: If DXF file cannot be loaded
        """
        try:
            self.logger.info(f"Loading DXF file: {self.dxf_path}")
            self.doc = ezdxf.readfile(self.dxf_path)
            self.logger.info(f"DXF file loaded successfully: {self.doc.dxfversion}")
        except Exception as e:
            self.logger.error(f"Failed to load DXF file: {e}")
            raise

    def detect_coordinate_system(self) -> dict:
        """
        Detect likely coordinate system from DXF coordinate values.

        DXF files typically don't contain CRS metadata, so this method analyzes
        coordinate ranges to suggest likely coordinate systems.

        Returns:
            dict: Dictionary with detection results:
                  {
                      'detected_epsg': int or None,
                      'confidence': str ('high', 'medium', 'low', 'unknown'),
                      'coordinate_range': {'x_min': float, 'x_max': float,
                                           'y_min': float, 'y_max': float},
                      'suggestions': [list of {epsg, name, reason}],
                      'warnings': [list of warning messages]
                  }

        Raises:
            Exception: If DXF file is not loaded or has no entities
        """
        if self.doc is None:
            self.load_dxf()

        modelspace = self.doc.modelspace()

        # Collect all coordinates from entities
        all_x = []
        all_y = []

        for entity in modelspace:
            entity_type = entity.dxftype()

            if entity_type == 'LWPOLYLINE':
                for point in entity.get_points('xy'):
                    all_x.append(point[0])
                    all_y.append(point[1])
            elif entity_type == 'POLYLINE':
                for vertex in entity.vertices:
                    all_x.append(vertex.dxf.location.x)
                    all_y.append(vertex.dxf.location.y)
            elif entity_type == 'LINE':
                all_x.append(entity.dxf.start.x)
                all_x.append(entity.dxf.end.x)
                all_y.append(entity.dxf.start.y)
                all_y.append(entity.dxf.end.y)

        if not all_x or not all_y:
            self.logger.warning("No coordinates found in DXF file")
            return {
                'detected_epsg': None,
                'confidence': 'unknown',
                'coordinate_range': None,
                'suggestions': [],
                'warnings': ['No coordinates found in DXF file']
            }

        # Calculate coordinate ranges
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)

        coord_range = {
            'x_min': x_min,
            'x_max': x_max,
            'y_min': y_min,
            'y_max': y_max
        }

        self.logger.info(
            f"Coordinate range: X=[{x_min:.2f}, {x_max:.2f}], "
            f"Y=[{y_min:.2f}, {y_max:.2f}]"
        )

        # Analyze coordinate ranges to suggest CRS
        suggestions = []
        warnings = []
        detected_epsg = None
        confidence = 'unknown'

        # Check for geographic coordinates (WGS84 / EPSG:4326)
        if abs(x_min) < 180 and abs(x_max) < 180 and abs(y_min) < 90 and abs(y_max) < 90:
            suggestions.append({
                'epsg': 4326,
                'name': 'WGS84 (Geographic)',
                'reason': 'Coordinates in geographic range (±180°, ±90°)'
            })
            warnings.append(
                'Geographic CRS (WGS84) detected. This plugin requires projected CRS '
                'with meter units. Please transform to EPSG:25832 or similar.'
            )
            confidence = 'high'

        # Check for UTM Zone 32N (EPSG:25832) - Common in western/central Germany
        elif 200000 <= x_min and x_max <= 500000 and 5400000 <= y_min and y_max <= 6100000:
            if 300000 <= x_min and x_max <= 400000:
                suggestions.append({
                    'epsg': 25832,
                    'name': 'ETRS89 / UTM Zone 32N',
                    'reason': 'Coordinates match UTM Zone 32N range (300k-400k E, 5.4M-6.1M N)'
                })
                detected_epsg = 25832
                confidence = 'high'
            else:
                suggestions.append({
                    'epsg': 25832,
                    'name': 'ETRS89 / UTM Zone 32N',
                    'reason': 'Coordinates in extended UTM Zone 32N range'
                })
                confidence = 'medium'

        # Check for UTM Zone 33N (EPSG:25833) - Common in eastern Germany
        elif 300000 <= x_min and x_max <= 600000 and 5400000 <= y_min and y_max <= 6100000:
            if 400000 <= x_min and x_max <= 500000:
                suggestions.append({
                    'epsg': 25833,
                    'name': 'ETRS89 / UTM Zone 33N',
                    'reason': 'Coordinates match UTM Zone 33N range (400k-500k E, 5.4M-6.1M N)'
                })
                detected_epsg = 25833
                confidence = 'high'
            else:
                suggestions.append({
                    'epsg': 25833,
                    'name': 'ETRS89 / UTM Zone 33N',
                    'reason': 'Coordinates in extended UTM Zone 33N range'
                })
                confidence = 'medium'

        # Check for Gauss-Krüger Zone 3 (EPSG:31467) - Legacy German system
        elif 3200000 <= x_min and x_max <= 3900000 and 5400000 <= y_min and y_max <= 6100000:
            if 3300000 <= x_min and x_max <= 3700000:
                suggestions.append({
                    'epsg': 31467,
                    'name': 'DHDN / Gauss-Krüger Zone 3',
                    'reason': 'Coordinates match Gauss-Krüger Zone 3 (3.3M-3.7M E)'
                })
                detected_epsg = 31467
                confidence = 'high'
            else:
                suggestions.append({
                    'epsg': 31467,
                    'name': 'DHDN / Gauss-Krüger Zone 3',
                    'reason': 'Coordinates in extended Gauss-Krüger Zone 3 range'
                })
                confidence = 'medium'
            warnings.append(
                'Gauss-Krüger detected (legacy system). Consider transforming to '
                'ETRS89/UTM (EPSG:25832 or 25833) for modern projects.'
            )

        # Check for Gauss-Krüger Zone 4 (EPSG:31468) - Legacy German system
        elif 4200000 <= x_min and x_max <= 4900000 and 5400000 <= y_min and y_max <= 6100000:
            if 4300000 <= x_min and x_max <= 4700000:
                suggestions.append({
                    'epsg': 31468,
                    'name': 'DHDN / Gauss-Krüger Zone 4',
                    'reason': 'Coordinates match Gauss-Krüger Zone 4 (4.3M-4.7M E)'
                })
                detected_epsg = 31468
                confidence = 'high'
            else:
                suggestions.append({
                    'epsg': 31468,
                    'name': 'DHDN / Gauss-Krüger Zone 4',
                    'reason': 'Coordinates in extended Gauss-Krüger Zone 4 range'
                })
                confidence = 'medium'
            warnings.append(
                'Gauss-Krüger detected (legacy system). Consider transforming to '
                'ETRS89/UTM (EPSG:25832 or 25833) for modern projects.'
            )

        # Unknown coordinate system
        else:
            confidence = 'low'
            warnings.append(
                f'Could not confidently detect CRS from coordinate range. '
                f'Please verify that coordinates are in EPSG:{self.crs_epsg}.'
            )

        # Log results
        if detected_epsg:
            self.logger.info(
                f"Detected CRS: EPSG:{detected_epsg} "
                f"({suggestions[0]['name']}) with {confidence} confidence"
            )
        else:
            self.logger.warning(f"Could not detect CRS (confidence: {confidence})")

        for warning in warnings:
            self.logger.warning(warning)

        return {
            'detected_epsg': detected_epsg,
            'confidence': confidence,
            'coordinate_range': coord_range,
            'suggestions': suggestions,
            'warnings': warnings
        }

    def suggest_coordinate_system(self, coordinate_range: dict = None) -> List[dict]:
        """
        Suggest appropriate coordinate systems for German wind energy projects.

        Args:
            coordinate_range (dict): Optional coordinate range from detect_coordinate_system()

        Returns:
            List[dict]: List of suggested CRS with metadata:
                        [{'epsg': int, 'name': str, 'description': str, 'use_case': str}]
        """
        suggestions = [
            {
                'epsg': 25832,
                'name': 'ETRS89 / UTM Zone 32N',
                'description': 'Modern standard for western and central Germany',
                'use_case': 'Recommended for projects in NRW, Lower Saxony (west), Hesse, Rhineland-Palatinate',
                'x_range': '300,000 - 400,000',
                'y_range': '5,400,000 - 6,100,000'
            },
            {
                'epsg': 25833,
                'name': 'ETRS89 / UTM Zone 33N',
                'description': 'Modern standard for eastern Germany',
                'use_case': 'Recommended for projects in Brandenburg, Saxony, Thuringia, Mecklenburg-Vorpommern',
                'x_range': '400,000 - 500,000',
                'y_range': '5,400,000 - 6,100,000'
            },
            {
                'epsg': 31467,
                'name': 'DHDN / Gauss-Krüger Zone 3',
                'description': 'Legacy system (being phased out)',
                'use_case': 'Historic projects, western Germany. Consider transforming to EPSG:25832.',
                'x_range': '3,300,000 - 3,700,000',
                'y_range': '5,400,000 - 6,100,000'
            },
            {
                'epsg': 31468,
                'name': 'DHDN / Gauss-Krüger Zone 4',
                'description': 'Legacy system (being phased out)',
                'use_case': 'Historic projects, eastern Germany. Consider transforming to EPSG:25833.',
                'x_range': '4,300,000 - 4,700,000',
                'y_range': '5,400,000 - 6,100,000'
            }
        ]

        # If coordinate range provided, filter suggestions to most likely matches
        if coordinate_range:
            x_min = coordinate_range.get('x_min', 0)
            x_max = coordinate_range.get('x_max', 0)

            filtered = []
            for suggestion in suggestions:
                epsg = suggestion['epsg']

                # Check if coordinates match this CRS range
                if epsg == 25832 and 250000 <= x_min and x_max <= 450000:
                    filtered.append(suggestion)
                elif epsg == 25833 and 350000 <= x_min and x_max <= 550000:
                    filtered.append(suggestion)
                elif epsg == 31467 and 3200000 <= x_min and x_max <= 3800000:
                    filtered.append(suggestion)
                elif epsg == 31468 and 4200000 <= x_min and x_max <= 4800000:
                    filtered.append(suggestion)

            if filtered:
                return filtered

        return suggestions

    def validate_coordinate_system(self, expected_epsg: int = None) -> Tuple[bool, str]:
        """
        Validate coordinate system of DXF data against expected CRS.

        Args:
            expected_epsg (int): Expected EPSG code (uses self.crs_epsg if None)

        Returns:
            Tuple[bool, str]: (is_valid, message)
                              is_valid: True if coordinates match expected CRS
                              message: Validation message or error with suggestions

        Raises:
            ValueError: If DXF contains no coordinate data
        """
        if expected_epsg is None:
            expected_epsg = self.crs_epsg

        # Detect CRS from coordinates
        detection = self.detect_coordinate_system()

        if not detection['coordinate_range']:
            raise ValueError("DXF file contains no coordinate data")

        detected_epsg = detection['detected_epsg']
        confidence = detection['confidence']
        warnings = detection['warnings']

        # Build validation message
        coord_range = detection['coordinate_range']
        range_str = (
            f"X=[{coord_range['x_min']:.2f}, {coord_range['x_max']:.2f}], "
            f"Y=[{coord_range['y_min']:.2f}, {coord_range['y_max']:.2f}]"
        )

        # Case 1: High confidence detection matches expected
        if detected_epsg == expected_epsg and confidence == 'high':
            message = (
                f"✓ Coordinate system validated: EPSG:{expected_epsg}\n"
                f"  Coordinate range: {range_str}\n"
                f"  Confidence: {confidence}"
            )
            self.logger.info(message)
            return True, message

        # Case 2: High confidence detection, but doesn't match expected
        if detected_epsg and detected_epsg != expected_epsg and confidence == 'high':
            # Get bilingual error message
            error_msg = get_message(
                'crs_mismatch',
                ERROR_MESSAGES,
                actual=detected_epsg,
                expected=expected_epsg
            )
            fix_msg = get_message(
                'crs_mismatch',
                {k: v['fix'] for k, v in ERROR_MESSAGES.items()},
                expected=expected_epsg
            )

            message = (
                f"{error_msg}\n"
                f"  Detected: EPSG:{detected_epsg} (confidence: {confidence})\n"
                f"  Expected: EPSG:{expected_epsg}\n"
                f"  Coordinate range: {range_str}\n\n"
                f"{fix_msg}"
            )

            # Add suggestions
            if detection['suggestions']:
                message += "\n\nDetected coordinate system:"
                for suggestion in detection['suggestions'][:1]:  # Show top suggestion
                    message += (
                        f"\n  • EPSG:{suggestion['epsg']}: {suggestion['name']}\n"
                        f"    {suggestion['reason']}"
                    )

            self.logger.warning(message)
            return False, message

        # Case 3: Low confidence or unknown - warn but don't fail
        if confidence in ['low', 'unknown']:
            message = (
                f"⚠ Could not confidently detect coordinate system\n"
                f"  Coordinate range: {range_str}\n"
                f"  Assuming EPSG:{expected_epsg} as specified\n"
                f"  Confidence: {confidence}\n\n"
                f"Please verify that your DXF coordinates are in EPSG:{expected_epsg}.\n"
            )

            # Add suggestions if available
            suggestions = self.suggest_coordinate_system(coord_range)
            if suggestions:
                message += "\nCommon German coordinate systems:\n"
                for suggestion in suggestions[:2]:  # Show top 2
                    message += (
                        f"  • EPSG:{suggestion['epsg']}: {suggestion['name']}\n"
                        f"    X: {suggestion['x_range']}, Y: {suggestion['y_range']}\n"
                    )

            # Add warnings
            for warning in warnings:
                message += f"\n⚠ {warning}"

            self.logger.warning(message)
            # Return True (with warning) since we can't be certain
            return True, message

        # Case 4: Medium confidence detection matches expected
        if detected_epsg == expected_epsg:
            message = (
                f"✓ Coordinate system likely correct: EPSG:{expected_epsg}\n"
                f"  Coordinate range: {range_str}\n"
                f"  Confidence: {confidence}"
            )

            for warning in warnings:
                message += f"\n⚠ {warning}"

            self.logger.info(message)
            return True, message

        # Case 5: Medium confidence, different from expected
        message = (
            f"⚠ Coordinate system mismatch (medium confidence)\n"
            f"  Detected: EPSG:{detected_epsg or 'unknown'} (confidence: {confidence})\n"
            f"  Expected: EPSG:{expected_epsg}\n"
            f"  Coordinate range: {range_str}\n\n"
            f"The coordinates may not match EPSG:{expected_epsg}. "
            f"Please verify your data."
        )

        if detection['suggestions']:
            message += "\n\nSuggested coordinate systems:\n"
            for suggestion in detection['suggestions'][:2]:
                message += (
                    f"  • EPSG:{suggestion['epsg']}: {suggestion['name']}\n"
                    f"    {suggestion['reason']}\n"
                )

        self.logger.warning(message)
        return False, message

    def get_available_layers(self) -> List[str]:
        """
        Get list of available layer names in DXF file.

        Returns:
            List[str]: List of layer names found in the DXF file

        Raises:
            Exception: If DXF file is not loaded
        """
        if self.doc is None:
            self.load_dxf()

        layers = []
        modelspace = self.doc.modelspace()

        # Collect unique layer names from all entities
        for entity in modelspace:
            layer_name = entity.dxf.layer
            if layer_name and layer_name not in layers:
                layers.append(layer_name)

        # Sort layers alphabetically for consistent output
        layers.sort()

        self.logger.info(f"Found {len(layers)} layers in DXF: {', '.join(layers)}")
        return layers

    def validate_layer_exists(self, layer_name: str) -> None:
        """
        Validate that a specified layer exists in the DXF file.

        Args:
            layer_name (str): Layer name to check

        Raises:
            ValueError: If layer does not exist (with bilingual error message)
        """
        available_layers = self.get_available_layers()

        if layer_name not in available_layers:
            # Build bilingual error message
            error_msg = get_message(
                'dxf_layer_not_found',
                ERROR_MESSAGES,
                layer_name=layer_name
            )
            fix_msg = get_message(
                'dxf_layer_not_found',
                {k: v['fix'] for k, v in ERROR_MESSAGES.items()},
                available_layers=', '.join(available_layers) if available_layers else '(none)'
            )

            full_msg = f"{error_msg}\n{fix_msg}"
            self.logger.error(full_msg)
            raise ValueError(full_msg)

        self.logger.info(f"Layer '{layer_name}' found in DXF file")

    def validate_entity_types(self, layer_name: Optional[str] = None) -> dict:
        """
        Validate entity types in DXF file and check for supported types.

        Checks for LWPOLYLINE entities (preferred) and warns about other types
        (LINE, POLYLINE, CIRCLE, etc.) that may need conversion.

        Args:
            layer_name (str): Layer name to filter (None = all layers)

        Returns:
            dict: Dictionary with entity type counts:
                  {
                      'LWPOLYLINE': count,
                      'POLYLINE': count,
                      'LINE': count,
                      'CIRCLE': count,
                      'ARC': count,
                      'other': {entity_type: count},
                      'total_entities': count,
                      'supported_entities': count,
                      'unsupported_entities': count,
                      'warnings': [list of warning messages],
                      'preferred_type': 'LWPOLYLINE'
                  }

        Raises:
            ValueError: If no supported entities are found (with bilingual error)
        """
        if self.doc is None:
            self.load_dxf()

        modelspace = self.doc.modelspace()

        # Track all entity types
        entity_counts = {
            'LWPOLYLINE': 0,
            'POLYLINE': 0,
            'LINE': 0,
            'CIRCLE': 0,
            'ARC': 0,
            'other': {},  # Track all other entity types
            'total_entities': 0,
            'supported_entities': 0,
            'unsupported_entities': 0,
            'warnings': [],
            'preferred_type': 'LWPOLYLINE'
        }

        # Supported geometry types for polygon creation
        supported_types = {'LWPOLYLINE', 'POLYLINE', 'LINE'}
        # Known unsupported types
        known_unsupported = {'CIRCLE', 'ARC', 'POINT', 'TEXT', 'MTEXT',
                            'DIMENSION', 'HATCH', 'SPLINE', 'ELLIPSE',
                            'INSERT', 'BLOCK', 'ATTRIB', 'ATTDEF'}

        # Count entities by type
        for entity in modelspace:
            # Filter by layer if specified
            if layer_name and entity.dxf.layer != layer_name:
                continue

            entity_type = entity.dxftype()
            entity_counts['total_entities'] += 1

            # Count specific known types
            if entity_type in ['LWPOLYLINE', 'POLYLINE', 'LINE', 'CIRCLE', 'ARC']:
                entity_counts[entity_type] += 1
            else:
                # Track other types in 'other' dict
                if entity_type not in entity_counts['other']:
                    entity_counts['other'][entity_type] = 0
                entity_counts['other'][entity_type] += 1

            # Count supported vs unsupported
            if entity_type in supported_types:
                entity_counts['supported_entities'] += 1
            else:
                entity_counts['unsupported_entities'] += 1

        # Log entity counts
        log_msg = f"Entity types found (layer: {layer_name or 'all'}): "
        log_msg += f"LWPOLYLINE={entity_counts['LWPOLYLINE']}, "
        log_msg += f"POLYLINE={entity_counts['POLYLINE']}, "
        log_msg += f"LINE={entity_counts['LINE']}, "
        log_msg += f"CIRCLE={entity_counts['CIRCLE']}, "
        log_msg += f"ARC={entity_counts['ARC']}"

        if entity_counts['other']:
            other_summary = ', '.join([f"{k}={v}" for k, v in entity_counts['other'].items()])
            log_msg += f", Other=[{other_summary}]"

        log_msg += f" | Total={entity_counts['total_entities']}, "
        log_msg += f"Supported={entity_counts['supported_entities']}, "
        log_msg += f"Unsupported={entity_counts['unsupported_entities']}"

        self.logger.info(log_msg)

        # Check if we have any supported entities
        total_supported = (
            entity_counts['LWPOLYLINE'] +
            entity_counts['POLYLINE'] +
            entity_counts['LINE']
        )

        if total_supported == 0:
            # No supported entities - this is an error
            error_msg = get_message('dxf_no_entities', ERROR_MESSAGES)
            fix_msg = get_message(
                'dxf_no_entities',
                {k: v['fix'] for k, v in ERROR_MESSAGES.items()}
            )

            # List what was found instead
            found_types = []
            if entity_counts['CIRCLE'] > 0:
                found_types.append(f"CIRCLE ({entity_counts['CIRCLE']})")
            if entity_counts['ARC'] > 0:
                found_types.append(f"ARC ({entity_counts['ARC']})")
            for etype, count in entity_counts['other'].items():
                found_types.append(f"{etype} ({count})")

            if found_types:
                found_msg = f"\nFound entity types: {', '.join(found_types)}"
            else:
                found_msg = "\nNo entities found in the specified layer/file."

            full_msg = f"{error_msg}{found_msg}\n{fix_msg}"
            self.logger.error(full_msg)
            raise ValueError(full_msg)

        # Warn about non-LWPOLYLINE entities (which is the preferred type)
        if entity_counts['POLYLINE'] > 0:
            warning_msg = (
                f"Found {entity_counts['POLYLINE']} POLYLINE entities. "
                f"These will be converted, but LWPOLYLINE is preferred for better compatibility."
            )
            entity_counts['warnings'].append(warning_msg)
            self.logger.warning(warning_msg)

        if entity_counts['LINE'] > 0:
            warning_msg = (
                f"Found {entity_counts['LINE']} LINE entities. "
                f"These will be connected to form polygons, but LWPOLYLINE is preferred. "
                f"Consider converting LINE entities to LWPOLYLINE in your CAD software."
            )
            entity_counts['warnings'].append(warning_msg)
            self.logger.warning(warning_msg)

        # Warn about unsupported curved entities
        if entity_counts['CIRCLE'] > 0 or entity_counts['ARC'] > 0:
            unsupported_types = []
            if entity_counts['CIRCLE'] > 0:
                unsupported_types.append(f"CIRCLE ({entity_counts['CIRCLE']})")
            if entity_counts['ARC'] > 0:
                unsupported_types.append(f"ARC ({entity_counts['ARC']})")

            error_msg = get_message(
                'dxf_wrong_entity_type',
                ERROR_MESSAGES,
                entity_types=', '.join(unsupported_types)
            )
            fix_msg = get_message(
                'dxf_wrong_entity_type',
                {k: v['fix'] for k, v in ERROR_MESSAGES.items()}
            )
            warning_msg = f"{error_msg}\n{fix_msg}"
            entity_counts['warnings'].append(warning_msg)
            self.logger.warning(warning_msg)

        # Warn about other unsupported entity types
        unsupported_other = []
        for etype, count in entity_counts['other'].items():
            if etype in known_unsupported:
                unsupported_other.append(f"{etype} ({count})")

        if unsupported_other:
            warning_msg = (
                f"Found unsupported entity types that will be ignored: {', '.join(unsupported_other)}. "
                f"Only LWPOLYLINE, POLYLINE, and LINE entities can be used for polygon import."
            )
            entity_counts['warnings'].append(warning_msg)
            self.logger.warning(warning_msg)

        # Info message about LWPOLYLINE preference
        if entity_counts['LWPOLYLINE'] == 0 and total_supported > 0:
            info_msg = (
                f"Note: No LWPOLYLINE entities found. LWPOLYLINE is the preferred geometry type "
                f"for crane pad outlines. Current file uses {entity_counts['POLYLINE']} POLYLINE "
                f"and {entity_counts['LINE']} LINE entities."
            )
            entity_counts['warnings'].append(info_msg)
            self.logger.info(info_msg)
        elif entity_counts['LWPOLYLINE'] > 0:
            self.logger.info(
                f"✓ Good: Found {entity_counts['LWPOLYLINE']} LWPOLYLINE entities "
                f"(preferred type for crane pad geometry)."
            )

        return entity_counts

    def extract_polylines(self, layer_name: Optional[str] = None) -> List[List[Tuple[float, float]]]:
        """
        Extract LWPOLYLINE entities from DXF file.

        Args:
            layer_name (str): Layer name to filter (None = all layers)

        Returns:
            List[List[Tuple[float, float]]]: List of polylines, where each polyline
                                              is a list of (x, y) coordinates
        """
        if self.doc is None:
            self.load_dxf()

        self.polylines = []
        modelspace = self.doc.modelspace()

        # Extract LWPOLYLINE entities
        lwpolylines = modelspace.query('LWPOLYLINE')
        self.logger.info(f"Found {len(lwpolylines)} LWPOLYLINE entities")

        for entity in lwpolylines:
            # Filter by layer if specified
            if layer_name and entity.dxf.layer != layer_name:
                continue

            # Extract coordinates
            coords = []
            for point in entity.get_points('xy'):
                coords.append((point[0], point[1]))

            if coords:
                self.polylines.append(coords)
                self.logger.debug(
                    f"Extracted polyline with {len(coords)} points "
                    f"from layer '{entity.dxf.layer}'"
                )

        # Also check for regular POLYLINE entities
        polylines = modelspace.query('POLYLINE')
        self.logger.info(f"Found {len(polylines)} POLYLINE entities")

        for entity in polylines:
            if layer_name and entity.dxf.layer != layer_name:
                continue

            coords = []
            for vertex in entity.vertices:
                coords.append((vertex.dxf.location.x, vertex.dxf.location.y))

            if coords:
                self.polylines.append(coords)
                self.logger.debug(
                    f"Extracted polyline with {len(coords)} points "
                    f"from layer '{entity.dxf.layer}'"
                )

        # Also check for LINE entities (in case polylines are broken into lines)
        lines = modelspace.query('LINE')
        if lines:
            self.logger.info(f"Found {len(lines)} LINE entities")
            for entity in lines:
                if layer_name and entity.dxf.layer != layer_name:
                    continue

                start = (entity.dxf.start.x, entity.dxf.start.y)
                end = (entity.dxf.end.x, entity.dxf.end.y)
                self.polylines.append([start, end])
                self.logger.debug(f"Extracted LINE from layer '{entity.dxf.layer}'")

        self.logger.info(f"Extracted {len(self.polylines)} total polylines/lines")
        return self.polylines

    def _build_segment_graph(self, polylines: List) -> dict:
        """
        Build a graph from line segments where nodes are endpoints.

        Returns:
            dict: Graph where keys are points and values are lists of connected points
        """
        from collections import defaultdict

        graph = defaultdict(list)

        # Flatten all polylines to individual segments
        for polyline in polylines:
            for i in range(len(polyline) - 1):
                p1 = polyline[i]
                p2 = polyline[i + 1]

                # Round coordinates to avoid floating point issues
                p1_rounded = (round(p1[0], 3), round(p1[1], 3))
                p2_rounded = (round(p2[0], 3), round(p2[1], 3))

                # Add edge in both directions
                if p2_rounded not in graph[p1_rounded]:
                    graph[p1_rounded].append(p2_rounded)
                if p1_rounded not in graph[p2_rounded]:
                    graph[p2_rounded].append(p1_rounded)

        return graph

    def _find_outer_boundary(self, graph: dict) -> List[Tuple[float, float]]:
        """
        Find the outer boundary polygon from a graph of connected segments.
        Uses the leftmost-then-rightmost approach to find exterior ring.
        """
        if not graph:
            return []

        # Find leftmost point (start of outer boundary)
        start_point = min(graph.keys(), key=lambda p: (p[0], p[1]))

        self.logger.info(f"Starting boundary trace from leftmost point: {start_point}")

        # Trace the boundary
        boundary = [start_point]
        current = start_point
        previous = None

        max_iterations = len(graph) * 10
        iterations = 0

        while iterations < max_iterations:
            iterations += 1

            neighbors = graph.get(current, [])
            if not neighbors:
                self.logger.warning(f"Dead end at {current}")
                break

            # Filter out the point we came from
            candidates = [n for n in neighbors if n != previous]

            if not candidates:
                # Only one neighbor and it's where we came from
                if len(neighbors) == 1:
                    break
                candidates = neighbors

            if len(candidates) == 0:
                break

            # Choose the rightmost turn (for exterior boundary)
            if previous is not None:
                # Calculate angles - choose rightmost turn (smallest angle difference)
                incoming_angle = math.atan2(current[1] - previous[1], current[0] - previous[0])

                best_angle_diff = float('inf')
                next_point = candidates[0]

                for candidate in candidates:
                    outgoing_angle = math.atan2(candidate[1] - current[1], candidate[0] - current[0])
                    angle_diff = (outgoing_angle - incoming_angle) % (2 * math.pi)
                    if angle_diff < best_angle_diff:
                        best_angle_diff = angle_diff
                        next_point = candidate
            else:
                # First step: go to rightmost neighbor (highest angle)
                best_angle = -math.pi
                next_point = candidates[0]

                for candidate in candidates:
                    angle = math.atan2(candidate[1] - current[1], candidate[0] - current[0])
                    if angle > best_angle:
                        best_angle = angle
                        next_point = candidate

            # Check if we've completed the loop
            if next_point == start_point:
                self.logger.info(f"Boundary loop completed after {len(boundary)} vertices")
                break

            # Check if we're revisiting a point (but not the start)
            if next_point in boundary:
                self.logger.warning(f"Revisiting point {next_point}, stopping trace")
                break

            boundary.append(next_point)
            previous = current
            current = next_point

        # Ensure closed
        if boundary and boundary[0] != boundary[-1]:
            boundary.append(boundary[0])

        return boundary

    def _connect_with_shapely(self, polylines: List, gap_tolerance: float = 0.5) -> Optional[List[Tuple[float, float]]]:
        """
        Robust polygon connection using Shapely with gap tolerance.

        This method:
        1. Converts all polylines to LineStrings
        2. Merges lines that touch
        3. Uses buffer trick to close small gaps
        4. Polygonizes the result
        5. Returns the largest polygon

        Args:
            polylines (List): List of polylines
            gap_tolerance (float): Maximum gap to close in meters (default: 0.5m)

        Returns:
            Optional[List[Tuple[float, float]]]: Polygon coordinates or None if failed
        """
        if not SHAPELY_AVAILABLE:
            self.logger.warning("Shapely not available, cannot use robust connection method")
            return None

        try:
            self.logger.info(f"Trying Shapely-based connection with gap tolerance {gap_tolerance}m...")
            self.logger.info(f"Input: {len(polylines)} polylines")

            # Convert polylines to Shapely LineStrings
            lines = []
            for i, polyline in enumerate(polylines):
                if len(polyline) >= 2:
                    try:
                        # Reduce to 2D (ignore Z if present)
                        coords_2d = []
                        for p in polyline:
                            if isinstance(p, (list, tuple)):
                                coords_2d.append((float(p[0]), float(p[1])))
                            else:
                                self.logger.warning(f"Unexpected point format in polyline {i}: {type(p)}")
                                continue

                        if len(coords_2d) >= 2:
                            line = LineString(coords_2d)
                            lines.append(line)
                            self.logger.debug(f"Polyline {i}: {len(coords_2d)} points, length={line.length:.2f}m")
                    except Exception as e:
                        self.logger.warning(f"Failed to create LineString from polyline {i}: {e}")
                        continue

            if not lines:
                self.logger.error("No valid lines to process")
                return None

            self.logger.info(f"Created {len(lines)} Shapely LineStrings")

            # Try to merge lines that touch
            merged = linemerge(lines)
            self.logger.info(f"Merged result type: {type(merged).__name__}")

            # Convert to geometry collection if needed
            if hasattr(merged, 'geoms'):
                geoms = list(merged.geoms)
                self.logger.info(f"Merged contains {len(geoms)} separate geometries")
            else:
                geoms = [merged]
                self.logger.info(f"Merged is a single geometry: {type(merged).__name__}")

            # Apply buffer trick to close small gaps
            if gap_tolerance > 0:
                self.logger.info(f"Applying buffer trick with tolerance {gap_tolerance}m")
                union_geom = unary_union(geoms)
                self.logger.info(f"Union geometry type: {type(union_geom).__name__}, area={union_geom.area:.2f}m²")

                buffered = union_geom.buffer(gap_tolerance)
                self.logger.info(f"After +buffer: type={type(buffered).__name__}, area={buffered.area:.2f}m²")

                # Check if buffered is already a good polygon
                if isinstance(buffered, ShapelyPolygon) and not buffered.is_empty and buffered.area > 100:
                    self.logger.info(f"Buffered result is a valid polygon (area={buffered.area:.2f}m²), using it directly")
                    largest_poly = buffered
                else:
                    # Try negative buffer
                    cleaned = buffered.buffer(-gap_tolerance)
                    self.logger.info(f"After -buffer: type={type(cleaned).__name__}, area={cleaned.area:.2f}m²")

                    # If cleaned is a polygon, use it directly
                    if isinstance(cleaned, ShapelyPolygon) and not cleaned.is_empty:
                        self.logger.info("Cleaned geometry is a polygon, using it directly")
                        largest_poly = cleaned
                    else:
                        # Need to polygonize
                        if hasattr(cleaned, 'boundary'):
                            boundary = cleaned.boundary
                            self.logger.info(f"Extracted boundary: type={type(boundary).__name__}")
                        else:
                            boundary = cleaned
                            self.logger.info(f"No boundary attribute, using cleaned geometry directly")

                        # Polygonize
                        if hasattr(boundary, 'geoms'):
                            boundary_geoms = list(boundary.geoms)
                            self.logger.info(f"Boundary contains {len(boundary_geoms)} geometries")
                        else:
                            boundary_geoms = [boundary]
                            self.logger.info(f"Boundary is single geometry: {type(boundary).__name__}")

                        polygons = list(polygonize(boundary_geoms))
                        self.logger.info(f"Polygonize produced {len(polygons)} polygon(s)")

                        if not polygons:
                            self.logger.warning("Polygonize did not produce any polygons")
                            return None

                        # Take the largest polygon
                        largest_poly = max(polygons, key=lambda p: p.area)
                        self.logger.info(f"Largest polygon from polygonize: area={largest_poly.area:.2f}m²")
            else:
                cleaned = unary_union(geoms)
                self.logger.info(f"No buffer applied, using union: type={type(cleaned).__name__}")

                # If cleaned is already a polygon, use it
                if isinstance(cleaned, ShapelyPolygon) and not cleaned.is_empty:
                    largest_poly = cleaned
                else:
                    return None

            # Validate and repair if needed
            if not largest_poly.is_valid:
                self.logger.warning("Polygon not valid, attempting to repair with buffer(0)")
                largest_poly = largest_poly.buffer(0)

            if not largest_poly.is_valid or largest_poly.is_empty:
                self.logger.error("Failed to create valid polygon after repair attempt")
                return None

            # Extract coordinates
            coords = list(largest_poly.exterior.coords)

            self.logger.info(
                f"Shapely method successful: {len(coords)} vertices, "
                f"area = {largest_poly.area:.2f} m²"
            )

            return coords

        except Exception as e:
            import traceback
            self.logger.error(f"Shapely connection method failed with exception: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def connect_polylines(self, polylines: Optional[List] = None) -> List[Tuple[float, float]]:
        """
        Connect multiple polylines to form a closed polygon.

        This method tries to connect polylines by matching endpoints within the
        specified tolerance. It builds a chain of connected polylines.

        Args:
            polylines (List): List of polylines (uses self.polylines if None)

        Returns:
            List[Tuple[float, float]]: Ordered list of coordinates forming polygon

        Raises:
            ValueError: If polylines cannot be connected
        """
        if polylines is None:
            polylines = self.polylines

        if not polylines:
            raise ValueError("No polylines to connect")

        # If only one polyline, check if it's already closed
        if len(polylines) == 1:
            coords = polylines[0]
            # Check if first and last points are the same (closed)
            if point_distance(coords[0], coords[-1]) <= self.tolerance:
                self.logger.info("Single closed polyline detected")
                return coords
            else:
                # Try to close it
                self.logger.warning(
                    f"Single polyline is not closed (gap: {point_distance(coords[0], coords[-1]):.3f}m). "
                    f"Adding closing segment."
                )
                return coords + [coords[0]]

        # FIRST: Try robust Shapely-based method with gap tolerance
        self.logger.info(f"SHAPELY_AVAILABLE: {SHAPELY_AVAILABLE}")
        if SHAPELY_AVAILABLE:
            # Try different gap tolerances
            for gap_tol in [0.5, 1.0, 2.0, 5.0]:
                self.logger.info(f"Calling _connect_with_shapely with gap_tol={gap_tol}m")
                coords = self._connect_with_shapely(polylines, gap_tolerance=gap_tol)
                self.logger.info(f"_connect_with_shapely returned: {coords is not None}, coords={len(coords) if coords else 0}")
                if coords and len(coords) >= 4:
                    return coords
        else:
            self.logger.warning("Shapely is not available, skipping Shapely method")

        # FALLBACK: Multiple polylines - use graph-based approach
        self.logger.info(f"Shapely method failed, trying graph-based approach...")
        self.logger.info(f"Connecting {len(polylines)} line segments using graph-based approach...")

        # Build graph from segments
        graph = self._build_segment_graph(polylines)
        self.logger.info(f"Built graph with {len(graph)} nodes")

        # Find outer boundary
        boundary = self._find_outer_boundary(graph)

        if not boundary or len(boundary) < 4:
            self.logger.error(f"Failed to find valid boundary (got {len(boundary)} points)")
            # Fall back to old method
            self.logger.info("Falling back to sequential connection method...")
            return self._connect_polylines_sequential(polylines)

        self.logger.info(f"Successfully traced boundary with {len(boundary)} vertices")
        return boundary

    def _connect_polylines_sequential(self, polylines: List) -> List[Tuple[float, float]]:
        """
        Original sequential connection method (fallback).
        """
        self.logger.info(f"Using sequential connection for {len(polylines)} polylines...")

        # Start with first polyline
        connected = list(polylines[0])
        remaining = [list(pl) for pl in polylines[1:]]

        iterations = 0
        max_iterations = len(remaining) * 2

        while remaining and iterations < max_iterations:
            iterations += 1

            # Get current endpoints
            start_point = connected[0]
            end_point = connected[-1]

            # Try to find a polyline that connects to either endpoint
            best_dist = float('inf')
            best_idx = None
            best_reverse = False
            best_at_start = False

            for idx, polyline in enumerate(remaining):
                pl_start = polyline[0]
                pl_end = polyline[-1]

                # Check all possible connections
                connections = [
                    (point_distance(end_point, pl_start), False, False),  # end → start
                    (point_distance(end_point, pl_end), True, False),     # end → end (reverse)
                    (point_distance(start_point, pl_end), False, True),   # start ← end
                    (point_distance(start_point, pl_start), True, True),  # start ← start (reverse)
                ]

                for dist, reverse, at_start in connections:
                    if dist < best_dist and dist <= self.tolerance:
                        best_dist = dist
                        best_idx = idx
                        best_reverse = reverse
                        best_at_start = at_start

            if best_idx is not None:
                # Connect the polyline
                polyline = remaining.pop(best_idx)

                if best_reverse:
                    polyline = list(reversed(polyline))

                if best_at_start:
                    # Connect to start
                    connected = polyline[:-1] + connected
                else:
                    # Connect to end
                    connected = connected[:-1] + polyline

                self.logger.debug(
                    f"Connected polyline {best_idx} (distance: {best_dist:.3f}m)"
                )
            else:
                # No connection found
                if remaining:
                    self.logger.warning(
                        f"Could not connect {len(remaining)} remaining polyline(s)."
                    )
                break

        # Check if polygon is closed
        if point_distance(connected[0], connected[-1]) > self.tolerance:
            self.logger.warning(
                f"Polygon not fully closed (gap: {point_distance(connected[0], connected[-1]):.3f}m). "
                f"Adding closing segment."
            )
            connected.append(connected[0])

        self.logger.info(
            f"Successfully connected polygon with {len(connected)} vertices"
        )

        return connected

    def to_qgs_polygon(self, coords: Optional[List[Tuple[float, float]]] = None) -> QgsGeometry:
        """
        Convert coordinates to QGIS polygon geometry.

        Args:
            coords (List): List of coordinates (uses connected polylines if None)

        Returns:
            QgsGeometry: QGIS polygon geometry

        Raises:
            ValueError: If coordinates are invalid
        """
        if coords is None:
            coords = self.connect_polylines()

        if not coords:
            raise ValueError("No coordinates to convert")

        # Ensure polygon is closed
        if point_distance(coords[0], coords[-1]) > 1e-6:
            coords = coords + [coords[0]]

        # Convert to QgsPointXY
        qgs_points = [QgsPointXY(x, y) for x, y in coords]

        # Create polygon geometry
        polygon = QgsGeometry.fromPolygonXY([qgs_points])

        return polygon

    def validate_polygon(self, polygon: QgsGeometry) -> Tuple[bool, str]:
        """
        Validate polygon topology.

        Args:
            polygon (QgsGeometry): Polygon to validate

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        return validate_polygon_topology(polygon)

    def import_as_polygon(self, layer_name: Optional[str] = None) -> Tuple[QgsGeometry, dict]:
        """
        Complete import workflow: load DXF, extract, connect, and validate.

        Args:
            layer_name (str): DXF layer to import (None = all layers)

        Returns:
            Tuple[QgsGeometry, dict]: (polygon_geometry, metadata)

        Raises:
            Exception: If import fails
        """
        # Extract polylines
        polylines = self.extract_polylines(layer_name)

        if not polylines:
            raise ValueError(f"No polylines found in DXF file (layer: {layer_name or 'all'})")

        # Connect all polylines to form polygon boundary
        coords = self.connect_polylines(polylines)

        # Convert to QGIS geometry
        polygon = self.to_qgs_polygon(coords)

        # Try to fix invalid geometry
        if not polygon.isGeosValid():
            self.logger.warning("Polygon is not valid, attempting to fix...")
            fixed_polygon = polygon.makeValid()
            if fixed_polygon and not fixed_polygon.isEmpty():
                self.logger.info("Polygon successfully repaired")
                polygon = fixed_polygon
            else:
                self.logger.error("Could not repair polygon")

        # Validate
        is_valid, error_msg = self.validate_polygon(polygon)
        if not is_valid:
            # Log more details for debugging
            self.logger.error(f"Polygon validation failed: {error_msg}")
            self.logger.error(f"Polygon area: {polygon.area()}")
            self.logger.error(f"Polygon is empty: {polygon.isEmpty()}")
            self.logger.error(f"Polygon type: {polygon.type()}")
            raise ValueError(f"Invalid polygon: {error_msg}")

        # Create metadata
        metadata = {
            'source_file': str(self.dxf_path),
            'num_polylines': len(polylines),
            'num_vertices': len(coords),
            'area': polygon.area(),
            'perimeter': polygon.length(),
            'crs_epsg': self.crs_epsg,
            'tolerance': self.tolerance
        }

        self.logger.info(
            f"Successfully imported polygon: "
            f"{metadata['num_vertices']} vertices, "
            f"{metadata['area']:.2f} m² area"
        )

        return polygon, metadata

    def get_crs(self) -> QgsCoordinateReferenceSystem:
        """
        Get the coordinate reference system.

        Returns:
            QgsCoordinateReferenceSystem: CRS for the imported geometries
        """
        crs = QgsCoordinateReferenceSystem(f"EPSG:{self.crs_epsg}")
        return crs

    def import_holms(self, layer_name: Optional[str] = None) -> Tuple[List[QgsGeometry], dict]:
        """
        Import multiple holm (blade support beam) polygons from DXF.

        Holms are imported as separate polygons. Each closed polyline or
        set of connected lines forms one holm polygon.

        Args:
            layer_name (str): Layer name to filter (None = all layers)

        Returns:
            Tuple[List[QgsGeometry], dict]: List of holm polygons and metadata

        Raises:
            ImportError: If required packages are not available
            ValueError: If no holms can be imported
        """
        self.logger.info(f"Importing holms from DXF: {self.dxf_path}")

        # Extract polylines from DXF
        polylines = self.extract_polylines(layer_name=layer_name)

        if not polylines:
            raise ValueError(f"No polylines found in DXF file")

        self.logger.info(f"Found {len(polylines)} polylines for holm import")

        # Group polylines into separate closed polygons
        holm_geometries = []
        failed_holms = 0

        # Strategy 1: Each polyline is a separate holm (if closed)
        for i, polyline in enumerate(polylines):
            try:
                # Check if polyline is closed
                if len(polyline) >= 3:
                    first_pt = polyline[0]
                    last_pt = polyline[-1]

                    is_closed = point_distance(first_pt, last_pt) <= self.tolerance

                    if is_closed:
                        # Create polygon from closed polyline
                        qgs_points = [QgsPointXY(x, y) for x, y in polyline]
                        holm_geom = QgsGeometry.fromPolygonXY([qgs_points])

                        if holm_geom and not holm_geom.isEmpty() and holm_geom.isGeosValid():
                            holm_geometries.append(holm_geom)
                            self.logger.info(
                                f"Holm {len(holm_geometries)}: {len(polyline)} vertices, "
                                f"area={holm_geom.area():.2f}m²"
                            )
                        else:
                            self.logger.warning(f"Polyline {i} forms invalid holm geometry")
                            failed_holms += 1
                    else:
                        self.logger.debug(
                            f"Polyline {i} is not closed (gap: {point_distance(first_pt, last_pt):.3f}m)"
                        )

            except Exception as e:
                self.logger.error(f"Error creating holm from polyline {i}: {e}")
                failed_holms += 1

        # Strategy 2: If we didn't find enough closed polylines, try to connect lines
        if len(holm_geometries) == 0 and SHAPELY_AVAILABLE:
            self.logger.info("No closed polylines found, attempting to polygonize all lines...")

            try:
                from shapely.ops import polygonize
                from shapely.geometry import LineString

                # Convert all polylines to shapely LineStrings
                shapely_lines = []
                for polyline in polylines:
                    if len(polyline) >= 2:
                        shapely_lines.append(LineString(polyline))

                # Polygonize to find all closed polygons
                polygons = list(polygonize(shapely_lines))

                self.logger.info(f"Polygonize found {len(polygons)} polygons")

                for poly in polygons:
                    if not poly.is_empty and poly.is_valid and poly.area > 1.0:  # Min 1m² area
                        coords = list(poly.exterior.coords)
                        qgs_points = [QgsPointXY(x, y) for x, y in coords]
                        holm_geom = QgsGeometry.fromPolygonXY([qgs_points])

                        if holm_geom and not holm_geom.isEmpty():
                            holm_geometries.append(holm_geom)
                            self.logger.info(
                                f"Holm {len(holm_geometries)} (from polygonize): "
                                f"area={holm_geom.area():.2f}m²"
                            )

            except Exception as e:
                self.logger.error(f"Polygonize method failed: {e}")

        if not holm_geometries:
            raise ValueError(
                f"No valid holm geometries could be created from {len(polylines)} polylines. "
                f"Failed attempts: {failed_holms}"
            )

        # Create metadata
        total_area = sum(h.area() for h in holm_geometries)
        metadata = {
            'source_file': str(self.dxf_path),
            'num_holms': len(holm_geometries),
            'total_area': total_area,
            'failed_holms': failed_holms,
            'crs_epsg': self.crs_epsg,
            'tolerance': self.tolerance,
            'individual_areas': [round(h.area(), 2) for h in holm_geometries]
        }

        self.logger.info(
            f"Successfully imported {len(holm_geometries)} holms: "
            f"total area = {total_area:.2f}m², "
            f"failed = {failed_holms}"
        )

        return holm_geometries, metadata
