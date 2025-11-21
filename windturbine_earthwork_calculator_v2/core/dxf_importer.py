"""
DXF Importer for Wind Turbine Earthwork Calculator V2

Imports DXF files containing crane pad outlines (LWPOLYLINE entities)
and converts them to QGIS polygon geometries.

Author: Wind Energy Site Planning
Version: 2.0
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
