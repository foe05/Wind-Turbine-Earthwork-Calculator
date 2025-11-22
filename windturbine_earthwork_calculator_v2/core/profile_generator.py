"""
Profile Generator for Wind Turbine Earthwork Calculator V2

Generates terrain cross-sections and visualizations.

Adapted from WindTurbine_Earthwork_Calculator.py

Author: Wind Energy Site Planning
Version: 2.0.0
"""

import math
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
import multiprocessing as mp

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from qgis.core import (
    QgsGeometry,
    QgsPointXY,
    QgsRasterLayer,
    QgsProcessingFeedback
)

from ..utils.geometry_utils import (
    get_centroid,
    get_polygon_radius,
    get_polygon_orientation,
    create_radial_lines,
    create_perpendicular_cross_sections,
    create_parallel_longitudinal_sections,
    create_oriented_bounding_box,
    create_cross_sections_over_bbox,
    create_longitudinal_sections_over_bbox,
    calculate_distance_from_edge,
    calculate_slope_height
)
from ..utils.logging_utils import get_plugin_logger


# ============================================================================
# PARALLEL PROCESSING WORKER FUNCTIONS
# ============================================================================

def _plot_single_profile(profile_data: Dict, output_path: str, profile_type: str,
                        vertical_exaggeration: float, volume_info: Optional[Dict],
                        line_length: Optional[float], xlim: Optional[Tuple[float, float]],
                        ylim: Optional[Tuple[float, float]]) -> str:
    """
    Worker function to plot a single profile.

    Must be module-level for pickle serialization.

    Args:
        profile_data: Profile data with distances, elevations, etc.
        output_path: Path to save PNG
        profile_type: Profile type label
        vertical_exaggeration: Vertical exaggeration factor
        volume_info: Optional volume info
        line_length: Optional line length
        xlim: Optional x-axis limits
        ylim: Optional y-axis limits

    Returns:
        Path to created PNG file
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    try:
        fig_width = 12
        fig_height = 8
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=300)

        distances = profile_data['distances']
        existing = profile_data['existing_z']
        bottom_z = profile_data.get('bottom_z', profile_data['planned_z'])
        cut_fill = profile_data['cut_fill']

        # Get additional surface data
        crane_top_z = profile_data.get('crane_top_z', None)
        foundation_fok_z = profile_data.get('foundation_fok_z', profile_data.get('foundation_z', None))
        foundation_bottom_z = profile_data.get('foundation_bottom_z', None)
        boom_z = profile_data.get('boom_z', None)
        rotor_z = profile_data.get('rotor_z', None)

        # Helper function to extract valid data for plotting
        def extract_valid_data(arr, distances):
            if arr is None:
                return [], []
            dist_list = []
            height_list = []
            for i, z in enumerate(arr):
                if z is not None:
                    dist_list.append(distances[i])
                    height_list.append(z)
            return dist_list, height_list

        # Plot terrain (existing ground)
        ax.plot(distances, existing, 'k-', linewidth=2, label='Bestehendes Gelände', zorder=10)

        # Plot unified bottom line (Unterkante aller Flächen) - blue solid line
        ax.plot(distances, bottom_z, color='#1f77b4', linewidth=2,
                label='Unterkante (Planum/Sohle)', zorder=6)

        # Plot crane pad top (gravel surface) - black dashed line
        crane_top_dist, crane_top_heights = extract_valid_data(crane_top_z, distances)
        if crane_top_dist:
            ax.plot(crane_top_dist, crane_top_heights, color='black',
                   linewidth=2, label='Kranstellfläche (OK Schotter)', zorder=7, linestyle='--')

        # Plot foundation FOK - red dashed line
        fok_dist, fok_heights = extract_valid_data(foundation_fok_z, distances)
        if fok_dist:
            ax.plot(fok_dist, fok_heights, color='#d62728',
                   linewidth=2.5, label='Fundament (FOK)', zorder=8, linestyle='--')

        # Plot foundation bottom - red dotted line (optional, for detail)
        foundation_bottom_dist, foundation_bottom_heights = extract_valid_data(foundation_bottom_z, distances)
        if foundation_bottom_dist:
            ax.plot(foundation_bottom_dist, foundation_bottom_heights, color='#d62728',
                   linewidth=1.5, label='Fundament (UK)', zorder=5, linestyle=':')

        # Plot boom surface - orange solid line
        boom_dist, boom_heights = extract_valid_data(boom_z, distances)
        if boom_dist:
            ax.plot(boom_dist, boom_heights, color='#ff7f0e',
                   linewidth=2, label='Auslegerfläche', zorder=6)

        # Plot rotor storage - green solid line
        rotor_dist, rotor_heights = extract_valid_data(rotor_z, distances)
        if rotor_dist:
            ax.plot(rotor_dist, rotor_heights, color='#2ca02c',
                   linewidth=2, label='Blattlagerfläche', zorder=6)

        # Fill areas (Cut/Fill between existing terrain and bottom_z)
        cut_mask = cut_fill > 0
        if np.any(cut_mask):
            ax.fill_between(
                distances, existing, bottom_z,
                where=cut_mask,
                color='red', alpha=0.3, label='Abtrag', zorder=1
            )

        fill_mask = cut_fill < 0
        if np.any(fill_mask):
            ax.fill_between(
                distances, existing, bottom_z,
                where=fill_mask,
                color='green', alpha=0.3, label='Auftrag', zorder=1
            )

        # Plot slope lines (Böschungen)
        slope_lines = profile_data.get('slope_lines', [])
        slope_plotted = False
        for slope in slope_lines:
            slope_label = 'Böschung' if not slope_plotted else None
            ax.plot(
                [slope['start_dist'], slope['end_dist']],
                [slope['start_z'], slope['end_z']],
                color='#8B4513',  # Brown color for slopes
                linewidth=1.5,
                linestyle='-.',
                label=slope_label,
                zorder=4
            )
            slope_plotted = True

        # Labels
        max_distance = distances[-1] if len(distances) > 0 else 0
        ax.set_xlabel(f'Entfernung [m] (0 - {max_distance:.1f} m)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Höhe [m ü.NN]', fontsize=12, fontweight='bold')

        # Title
        if line_length:
            title = f'Geländeschnitt: {profile_type} (Länge: {line_length:.1f} m)'
        else:
            title = f'Geländeschnitt: {profile_type}'

        if vertical_exaggeration != 1.0:
            title += f' (Überhöhung {vertical_exaggeration}x)'

        ax.set_title(title, fontsize=14, fontweight='bold')

        # Grid and legend
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

        # Dynamic column count based on number of legend entries
        handles, labels = ax.get_legend_handles_labels()
        ncols = min(5, len(handles))  # Max 5 columns
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08),
                 ncol=ncols, fontsize=8, frameon=True, fancybox=True)

        # Set limits
        if xlim:
            ax.set_xlim(xlim)
        else:
            ax.set_xlim(0, max_distance)

        if ylim:
            ax.set_ylim(ylim)

        # Save
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        return output_path

    except Exception as e:
        raise RuntimeError(f"Failed to create profile plot: {e}")


class ProfileGenerator:
    """
    Generates terrain profiles (cross-sections) for wind turbine platforms.

    The generator:
    - Creates radial profile lines from polygon center
    - Samples DEM along profile lines
    - Creates matplotlib visualizations showing cut/fill
    - Exports profiles as PNG files
    """

    def __init__(self, dem_layer: QgsRasterLayer, polygon: QgsGeometry,
                 platform_height: float,
                 foundation_geometry: QgsGeometry = None,
                 foundation_height: float = None,
                 foundation_depth: float = 3.5,
                 gravel_thickness: float = 0.5,
                 slope_angle: float = 45.0,
                 boom_geometry: QgsGeometry = None,
                 boom_connection_edge: QgsGeometry = None,
                 boom_slope_direction: float = None,
                 boom_slope_percent: float = 0.0,
                 rotor_geometry: QgsGeometry = None,
                 rotor_height: float = None,
                 rotor_holms: list = None):
        """
        Initialize profile generator.

        Args:
            dem_layer (QgsRasterLayer): Digital elevation model
            polygon (QgsGeometry): Platform polygon (crane pad)
            platform_height (float): Optimized platform height (m above sea level)
            foundation_geometry (QgsGeometry): Foundation polygon (optional)
            foundation_height (float): Foundation height (FOK) in m ü.NN (optional)
            foundation_depth (float): Depth below FOK to foundation bottom (default: 3.5m)
            gravel_thickness (float): Gravel layer thickness on crane pad (default: 0.5m)
            slope_angle (float): Embankment slope angle in degrees (default: 45°)
            boom_geometry (QgsGeometry): Boom surface polygon (optional)
            boom_connection_edge (QgsGeometry): Connection edge between crane and boom (optional)
            boom_slope_direction (float): Slope direction angle in degrees (optional)
            boom_slope_percent (float): Boom slope in percent (optional)
            rotor_geometry (QgsGeometry): Rotor storage polygon (optional)
            rotor_height (float): Rotor storage height in m ü.NN (optional)
            rotor_holms (list): List of QgsGeometry polygons for rotor support beams (optional)
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError(
                "matplotlib is required for profile generation. "
                "Please install it using: pip install matplotlib"
            )

        self.dem_layer = dem_layer
        self.polygon = polygon
        self.platform_height = platform_height
        self.logger = get_plugin_logger()

        # Additional surface geometries and heights
        self.foundation_geometry = foundation_geometry
        self.foundation_height = foundation_height
        self.foundation_depth = foundation_depth
        self.gravel_thickness = gravel_thickness
        self.slope_angle = slope_angle
        self.boom_geometry = boom_geometry
        self.boom_connection_edge = boom_connection_edge
        self.boom_slope_direction = boom_slope_direction
        self.boom_slope_percent = boom_slope_percent
        self.rotor_geometry = rotor_geometry
        self.rotor_height = rotor_height
        self.rotor_holms = rotor_holms or []

        # Get polygon properties
        self.centroid = get_centroid(polygon)
        self.radius = get_polygon_radius(polygon)

        # Debug logging for boom parameters
        self.logger.info(f"ProfileGenerator initialized with boom parameters:")
        self.logger.info(f"  boom_slope_percent: {self.boom_slope_percent}")
        self.logger.info(f"  boom_connection_edge: {self.boom_connection_edge is not None}")
        self.logger.info(f"  boom_slope_direction: {self.boom_slope_direction}")
        self.logger.info(f"  boom_geometry: {self.boom_geometry is not None}")
        self.logger.info(f"  platform_height: {self.platform_height}")

        self.provider = dem_layer.dataProvider()

    def generate_auto_profiles(self, num_profiles: int = 8,
                              extension_m: float = 50.0) -> List[Dict]:
        """
        Generate radial profile lines automatically.

        DEPRECATED: Use generate_cross_section_profiles() instead.

        Args:
            num_profiles (int): Number of radial profiles (default: 8)
            extension_m (float): Extension beyond polygon radius (default: 50m)

        Returns:
            List[Dict]: List of profile dictionaries with 'geometry', 'type', 'azimuth'
        """
        # Calculate total line length
        line_length = self.radius + extension_m

        self.logger.info(
            f"Generating {num_profiles} radial profiles "
            f"(length: {line_length:.1f}m)"
        )

        # Create radial lines
        geometries = create_radial_lines(
            self.centroid,
            line_length,
            num_profiles,
            angle_offset=0
        )

        # Package into profile dicts
        profiles = []
        for i, geom in enumerate(geometries):
            azimuth = (360.0 / num_profiles) * i
            profile = {
                'geometry': geom,
                'type': f'profile_{i+1:03d}',
                'azimuth': azimuth,
                'length': line_length
            }
            profiles.append(profile)

        return profiles

    def generate_cross_section_profiles(self, spacing: float = 10.0,
                                       overhang_percent: float = 10.0) -> List[Dict]:
        """
        Generate perpendicular cross-section profile lines.

        Creates cross-sections perpendicular to the main polygon orientation,
        spaced at regular intervals, extending beyond polygon edges.

        Args:
            spacing (float): Distance between cross-sections in meters (default: 10m)
            overhang_percent (float): Percentage to extend beyond polygon on each side (default: 10%)

        Returns:
            List[Dict]: List of profile dictionaries with 'geometry', 'type', etc.
        """
        self.logger.info(
            f"Generating cross-section profiles "
            f"(spacing: {spacing:.1f}m, overhang: {overhang_percent:.0f}%)"
        )

        # Create cross-section lines
        profiles = create_perpendicular_cross_sections(
            self.polygon,
            spacing=spacing,
            overhang_percent=overhang_percent
        )

        self.logger.info(f"Generated {len(profiles)} cross-section profiles")

        return profiles

    def generate_longitudinal_profiles(self, spacing: float = 10.0,
                                       overhang_percent: float = 10.0) -> List[Dict]:
        """
        Generate longitudinal profile lines parallel to main polygon orientation.

        Creates longitudinal sections parallel to the main polygon orientation,
        spaced at regular intervals, extending beyond polygon edges.

        Args:
            spacing (float): Distance between longitudinal sections in meters (default: 10m)
            overhang_percent (float): Percentage to extend beyond polygon on each side (default: 10%)

        Returns:
            List[Dict]: List of profile dictionaries with 'geometry', 'type', etc.
        """
        self.logger.info(
            f"Generating longitudinal profiles "
            f"(spacing: {spacing:.1f}m, overhang: {overhang_percent:.0f}%)"
        )

        # Create longitudinal section lines
        profiles = create_parallel_longitudinal_sections(
            self.polygon,
            spacing=spacing,
            overhang_percent=overhang_percent
        )

        self.logger.info(f"Generated {len(profiles)} longitudinal profiles")

        return profiles

    def generate_cross_sections_bbox(self, all_geometries: list, buffer_percent: float = 10.0,
                                      spacing: float = 10.0) -> List[Dict]:
        """
        Generate cross-section profiles over bounding box encompassing all surfaces.

        Creates a bounding box aligned with the main orientation (longest edge) of the
        crane pad, encompassing all provided geometries with a buffer, then generates
        cross-sections across the entire bounding box.

        Args:
            all_geometries (list): List of QgsGeometry objects (all surface polygons)
            buffer_percent (float): Buffer as percentage of bbox size (default: 10%)
            spacing (float): Distance between cross-sections in meters (default: 10m)

        Returns:
            List[Dict]: List of profile dictionaries with 'geometry', 'type', etc.
        """
        self.logger.info(
            f"Generating cross-sections over bounding box "
            f"(buffer: {buffer_percent:.0f}%, spacing: {spacing:.1f}m)"
        )

        # Get main angle from crane pad (self.polygon)
        main_angle = get_polygon_orientation(self.polygon)
        self.logger.info(f"Main orientation angle: {main_angle:.1f}°")

        # Create oriented bounding box
        bbox_info = create_oriented_bounding_box(
            all_geometries,
            main_angle,
            buffer_percent=buffer_percent
        )

        if not bbox_info:
            self.logger.warning("Failed to create bounding box")
            return []

        self.logger.info(
            f"Bounding box: {bbox_info['length']:.1f}m × {bbox_info['width']:.1f}m"
        )

        # Create cross-sections
        profiles = create_cross_sections_over_bbox(bbox_info, spacing=spacing)

        self.logger.info(f"Generated {len(profiles)} cross-section profiles over bbox")

        return profiles

    def generate_longitudinal_sections_bbox(self, all_geometries: list, buffer_percent: float = 10.0,
                                            spacing: float = 10.0) -> List[Dict]:
        """
        Generate longitudinal profiles over bounding box encompassing all surfaces.

        Creates a bounding box aligned with the main orientation (longest edge) of the
        crane pad, encompassing all provided geometries with a buffer, then generates
        longitudinal sections across the entire bounding box.

        Args:
            all_geometries (list): List of QgsGeometry objects (all surface polygons)
            buffer_percent (float): Buffer as percentage of bbox size (default: 10%)
            spacing (float): Distance between longitudinal sections in meters (default: 10m)

        Returns:
            List[Dict]: List of profile dictionaries with 'geometry', 'type', etc.
        """
        self.logger.info(
            f"Generating longitudinal sections over bounding box "
            f"(buffer: {buffer_percent:.0f}%, spacing: {spacing:.1f}m)"
        )

        # Get main angle from crane pad (self.polygon)
        main_angle = get_polygon_orientation(self.polygon)
        self.logger.info(f"Main orientation angle: {main_angle:.1f}°")

        # Create oriented bounding box
        bbox_info = create_oriented_bounding_box(
            all_geometries,
            main_angle,
            buffer_percent=buffer_percent
        )

        if not bbox_info:
            self.logger.warning("Failed to create bounding box")
            return []

        self.logger.info(
            f"Bounding box: {bbox_info['length']:.1f}m × {bbox_info['width']:.1f}m"
        )

        # Create longitudinal sections
        profiles = create_longitudinal_sections_over_bbox(bbox_info, spacing=spacing)

        self.logger.info(f"Generated {len(profiles)} longitudinal profiles over bbox")

        return profiles

    def extract_profile_data(self, line_geom: QgsGeometry,
                            step_size: float = 0.5,
                            max_samples: int = 3000) -> Dict:
        """
        Extract elevation data along a profile line.

        Args:
            line_geom (QgsGeometry): Profile line geometry
            step_size (float): Sampling interval in meters (default: 0.5m)
            max_samples (int): Maximum number of samples (default: 3000)

        Returns:
            Dict: Profile data with:
                - distances: np.array of distances from line start
                - existing_z: np.array of existing terrain elevations
                - bottom_z: np.array of bottom elevations for all surfaces (for Cut/Fill)
                - crane_top_z: np.array of crane pad top (gravel surface) heights
                - foundation_fok_z: np.array of foundation FOK heights (top edge)
                - foundation_bottom_z: np.array of foundation bottom heights
                - boom_z: np.array of boom surface heights
                - rotor_z: np.array of rotor storage heights
                - cut_fill: np.array of cut (+) / fill (-) values
                - in_holm: np.array of boolean flags for holm areas
        """
        line_length = line_geom.length()

        # Adjust step size if line is too long
        if line_length / step_size > max_samples:
            step_size = line_length / max_samples
            self.logger.warning(
                f"Line too long, adjusted step size to {step_size:.2f}m"
            )

        num_samples = int(line_length / step_size) + 1
        distances = np.linspace(0, line_length, num_samples)

        existing_z = []
        bottom_z = []  # Unified bottom line for Cut/Fill
        crane_top_z = []  # Crane pad top (gravel surface)
        foundation_fok_z = []  # Foundation top (FOK)
        foundation_bottom_z = []  # Foundation bottom
        boom_z = []
        rotor_z = []
        in_holm = []  # Flag for holm areas

        # Debug counters
        boom_point_count = 0
        boom_debug_logged = False

        # Calculate derived heights
        crane_planum_height = self.platform_height - self.gravel_thickness
        foundation_bottom_height = None
        if self.foundation_height is not None:
            foundation_bottom_height = self.foundation_height - self.foundation_depth

        for dist in distances:
            # Interpolate point on line at distance
            point = line_geom.interpolate(dist).asPoint()
            point_geom = QgsGeometry.fromPointXY(point)

            # Sample DEM at point
            val, ok = self.provider.sample(point, 1)
            z_existing = float(val) if (ok and val is not None) else 0.0
            existing_z.append(z_existing)

            # Initialize values for this point
            z_bottom = z_existing  # Default: terrain level (outside all surfaces)
            z_crane_top = None
            z_foundation_fok = None
            z_foundation_bottom = None
            z_boom = None
            z_rotor = None
            is_in_holm = False

            # Check which surface contains the point (priority order matters)
            in_foundation = self.foundation_geometry and self.foundation_geometry.contains(point_geom)
            in_crane_pad = self.polygon.contains(point_geom)
            in_boom = self.boom_geometry and self.boom_geometry.contains(point_geom)
            in_rotor = self.rotor_geometry and self.rotor_geometry.contains(point_geom)

            # Check if point is in any holm (support beam)
            if self.rotor_holms:
                for holm_geom in self.rotor_holms:
                    if holm_geom and holm_geom.contains(point_geom):
                        is_in_holm = True
                        break

            # Determine bottom elevation based on surface type
            if in_foundation and foundation_bottom_height is not None:
                # Foundation area: bottom is foundation base
                z_bottom = foundation_bottom_height
                z_foundation_fok = self.foundation_height
                z_foundation_bottom = foundation_bottom_height
            elif in_crane_pad:
                # Crane pad area: bottom is planum (below gravel)
                z_bottom = crane_planum_height
                z_crane_top = self.platform_height
            elif in_boom:
                # Boom surface: calculate sloped height
                # Positive slope_percent = height increases with distance (terrain rises)
                # Negative slope_percent = height decreases with distance (terrain falls)
                boom_point_count += 1
                if self.boom_connection_edge:
                    distance_from_edge = calculate_distance_from_edge(
                        point,
                        self.boom_connection_edge,
                        self.boom_slope_direction
                    )
                    if distance_from_edge < 0:
                        z_boom = self.platform_height
                    else:
                        # Direct formula: positive slope = height increases with distance
                        z_boom = self.platform_height + distance_from_edge * self.boom_slope_percent / 100.0

                    # Debug logging for first few boom points
                    if not boom_debug_logged and boom_point_count <= 5:
                        self.logger.info(
                            f"  Boom point {boom_point_count}: dist_from_edge={distance_from_edge:.1f}m, "
                            f"z_boom={z_boom:.2f}m (platform={self.platform_height:.2f}, "
                            f"slope={self.boom_slope_percent}%)"
                        )
                        if boom_point_count == 5:
                            boom_debug_logged = True
                else:
                    z_boom = self.platform_height
                    if not boom_debug_logged:
                        self.logger.warning("  No boom_connection_edge - using flat platform_height")
                        boom_debug_logged = True
                z_bottom = z_boom  # Boom has no separate top/bottom
            elif in_rotor:
                # Rotor storage area
                if self.rotor_height is not None:
                    z_rotor = self.rotor_height
                    # Special logic for rotor storage:
                    # - If terrain is above rotor height: full cut to rotor height
                    # - If terrain is below rotor height: only fill at holm positions
                    if z_existing >= z_rotor:
                        # Cut needed: bottom is rotor height
                        z_bottom = z_rotor
                    elif is_in_holm:
                        # Fill only at holm positions
                        z_bottom = z_rotor
                    else:
                        # No fill outside holms when terrain is below rotor
                        z_bottom = z_existing

            # Append values
            bottom_z.append(z_bottom)
            crane_top_z.append(z_crane_top)
            foundation_fok_z.append(z_foundation_fok)
            foundation_bottom_z.append(z_foundation_bottom)
            boom_z.append(z_boom)
            rotor_z.append(z_rotor)
            in_holm.append(is_in_holm)

        # Convert to arrays
        existing_z = np.array(existing_z, dtype=float)
        bottom_z = np.array(bottom_z, dtype=float)
        crane_top_z = np.array(crane_top_z, dtype=object)  # Can contain None
        foundation_fok_z = np.array(foundation_fok_z, dtype=object)  # Can contain None
        foundation_bottom_z = np.array(foundation_bottom_z, dtype=object)  # Can contain None
        boom_z = np.array(boom_z, dtype=object)  # Can contain None
        rotor_z = np.array(rotor_z, dtype=object)  # Can contain None
        in_holm = np.array(in_holm, dtype=bool)

        # Calculate cut/fill based on bottom elevations
        # Positive = cut (remove material), Negative = fill (add material)
        cut_fill = existing_z - bottom_z

        # Legacy: planned_z for backward compatibility (now equals bottom_z)
        planned_z = bottom_z.copy()

        # Calculate slope lines (Böschungen)
        # Slopes connect surface edges to terrain at the configured slope angle
        slope_lines = self._calculate_slope_lines(
            distances, existing_z, bottom_z, crane_top_z,
            foundation_fok_z, foundation_bottom_z, crane_planum_height,
            foundation_bottom_height
        )

        # Debug summary
        boom_points_with_height = sum(1 for z in boom_z if z is not None)
        if boom_point_count > 0:
            self.logger.info(
                f"Profile extraction: {boom_point_count} boom points, "
                f"{boom_points_with_height} with calculated height"
            )

        profile_data = {
            'distances': distances,
            'existing_z': existing_z,
            'planned_z': planned_z,  # Legacy compatibility
            'bottom_z': bottom_z,  # Unified bottom line
            'crane_top_z': crane_top_z,  # Gravel top surface
            'foundation_fok_z': foundation_fok_z,  # Foundation top edge (FOK)
            'foundation_bottom_z': foundation_bottom_z,  # Foundation bottom
            'foundation_z': foundation_fok_z,  # Legacy compatibility
            'boom_z': boom_z,
            'rotor_z': rotor_z,
            'cut_fill': cut_fill,
            'in_holm': in_holm,
            'slope_lines': slope_lines  # Slope visualization data
        }

        return profile_data

    def _calculate_slope_lines(self, distances, existing_z, bottom_z, crane_top_z,
                               foundation_fok_z, foundation_bottom_z,
                               crane_planum_height, foundation_bottom_height):
        """
        Calculate slope lines (Böschungen) for visualization.

        Detects transitions between surfaces and terrain, and calculates
        slope lines at the configured slope angle.

        Returns:
            List of slope line segments: [{'start_dist', 'start_z', 'end_dist', 'end_z', 'type'}, ...]
        """
        slope_lines = []
        slope_ratio = 1.0 / math.tan(math.radians(self.slope_angle))  # horizontal/vertical

        n = len(distances)
        if n < 2:
            return slope_lines

        # Track state changes along the profile
        for i in range(1, n):
            prev_in_foundation = foundation_bottom_z[i-1] is not None
            curr_in_foundation = foundation_bottom_z[i] is not None
            prev_in_crane = crane_top_z[i-1] is not None
            curr_in_crane = crane_top_z[i] is not None

            # Foundation to Crane Pad transition (internal slope)
            # From foundation bottom to crane pad top (gravel)
            if prev_in_foundation and curr_in_crane and not curr_in_foundation:
                # Transition from foundation to crane pad
                # Draw slope from foundation bottom (prev) to crane top (curr)
                height_diff = self.platform_height - foundation_bottom_height
                if height_diff > 0:
                    slope_horizontal = height_diff * slope_ratio
                    slope_lines.append({
                        'start_dist': distances[i-1],
                        'start_z': foundation_bottom_height,
                        'end_dist': distances[i-1] + slope_horizontal,
                        'end_z': self.platform_height,
                        'type': 'foundation_to_crane'
                    })

            elif curr_in_foundation and prev_in_crane and not prev_in_foundation:
                # Transition from crane pad to foundation
                height_diff = self.platform_height - foundation_bottom_height
                if height_diff > 0:
                    slope_horizontal = height_diff * slope_ratio
                    slope_lines.append({
                        'start_dist': distances[i] - slope_horizontal,
                        'start_z': self.platform_height,
                        'end_dist': distances[i],
                        'end_z': foundation_bottom_height,
                        'type': 'crane_to_foundation'
                    })

            # Crane pad to terrain transition (external slope)
            if prev_in_crane and not curr_in_crane and not curr_in_foundation:
                # Leaving crane pad to terrain
                terrain_z = existing_z[i]
                height_diff = crane_planum_height - terrain_z
                if abs(height_diff) > 0.1:  # Only show significant slopes
                    slope_horizontal = abs(height_diff) * slope_ratio
                    if height_diff > 0:
                        # Cut slope (terrain is lower)
                        slope_lines.append({
                            'start_dist': distances[i-1],
                            'start_z': crane_planum_height,
                            'end_dist': distances[i-1] + slope_horizontal,
                            'end_z': terrain_z,
                            'type': 'crane_to_terrain_cut'
                        })
                    else:
                        # Fill slope (terrain is higher)
                        slope_lines.append({
                            'start_dist': distances[i-1],
                            'start_z': crane_planum_height,
                            'end_dist': distances[i-1] + slope_horizontal,
                            'end_z': terrain_z,
                            'type': 'crane_to_terrain_fill'
                        })

            elif curr_in_crane and not prev_in_crane and not prev_in_foundation:
                # Entering crane pad from terrain
                terrain_z = existing_z[i-1]
                height_diff = crane_planum_height - terrain_z
                if abs(height_diff) > 0.1:
                    slope_horizontal = abs(height_diff) * slope_ratio
                    if height_diff > 0:
                        # Cut slope
                        slope_lines.append({
                            'start_dist': distances[i] - slope_horizontal,
                            'start_z': terrain_z,
                            'end_dist': distances[i],
                            'end_z': crane_planum_height,
                            'type': 'terrain_to_crane_cut'
                        })
                    else:
                        # Fill slope
                        slope_lines.append({
                            'start_dist': distances[i] - slope_horizontal,
                            'start_z': terrain_z,
                            'end_dist': distances[i],
                            'end_z': crane_planum_height,
                            'type': 'terrain_to_crane_fill'
                        })

        return slope_lines

    def plot_profile(self, profile_data: Dict, output_path: str,
                    profile_type: str = "profile",
                    vertical_exaggeration: float = 1.0,
                    volume_info: Optional[Dict] = None,
                    line_length: Optional[float] = None,
                    xlim: Optional[Tuple[float, float]] = None,
                    ylim: Optional[Tuple[float, float]] = None) -> str:
        """
        Create matplotlib plot of terrain profile.

        Args:
            profile_data (Dict): Profile data from extract_profile_data()
            output_path (str): Path to save PNG file
            profile_type (str): Profile type label
            vertical_exaggeration (float): Vertical exaggeration factor
            volume_info (Dict): Optional volume info for annotation
            line_length (float): Optional total line length for x-axis scaling
            xlim (Tuple[float, float]): Optional x-axis limits (min, max)
            ylim (Tuple[float, float]): Optional y-axis limits (min, max)

        Returns:
            str: Path to created PNG file

        Raises:
            Exception: If plotting fails
        """
        try:
            # Fixed aspect ratio 3:2 (width:height) for consistent image sizes
            fig_width = 12  # inches
            fig_height = 8  # inches (12/8 = 3/2 = 1.5)

            fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=300)

            distances = profile_data['distances']
            existing = profile_data['existing_z']
            bottom_z = profile_data.get('bottom_z', profile_data['planned_z'])
            cut_fill = profile_data['cut_fill']

            # Get additional surface data
            crane_top_z = profile_data.get('crane_top_z', None)
            foundation_fok_z = profile_data.get('foundation_fok_z', profile_data.get('foundation_z', None))
            foundation_bottom_z = profile_data.get('foundation_bottom_z', None)
            boom_z = profile_data.get('boom_z', None)
            rotor_z = profile_data.get('rotor_z', None)

            # Helper function to extract valid data for plotting
            def extract_valid_data(arr, distances):
                if arr is None:
                    return [], []
                dist_list = []
                height_list = []
                for i, z in enumerate(arr):
                    if z is not None:
                        dist_list.append(distances[i])
                        height_list.append(z)
                return dist_list, height_list

            # Plot terrain (existing ground)
            ax.plot(distances, existing, 'k-', linewidth=2, label='Bestehendes Gelände', zorder=10)

            # Plot unified bottom line (Unterkante aller Flächen) - blue solid line
            ax.plot(distances, bottom_z, color='#1f77b4', linewidth=2,
                    label='Unterkante (Planum/Sohle)', zorder=6)

            # Plot crane pad top (gravel surface) - black dashed line
            crane_top_dist, crane_top_heights = extract_valid_data(crane_top_z, distances)
            if crane_top_dist:
                ax.plot(crane_top_dist, crane_top_heights, color='black',
                       linewidth=2, label='Kranstellfläche (OK Schotter)', zorder=7, linestyle='--')

            # Plot foundation FOK - red dashed line
            fok_dist, fok_heights = extract_valid_data(foundation_fok_z, distances)
            if fok_dist:
                ax.plot(fok_dist, fok_heights, color='#d62728',
                       linewidth=2.5, label='Fundament (FOK)', zorder=8, linestyle='--')

            # Plot foundation bottom - red dotted line
            foundation_bottom_dist, foundation_bottom_heights = extract_valid_data(foundation_bottom_z, distances)
            if foundation_bottom_dist:
                ax.plot(foundation_bottom_dist, foundation_bottom_heights, color='#d62728',
                       linewidth=1.5, label='Fundament (UK)', zorder=5, linestyle=':')

            # Plot boom surface - orange solid line
            boom_dist, boom_heights = extract_valid_data(boom_z, distances)
            if boom_dist:
                ax.plot(boom_dist, boom_heights, color='#ff7f0e',
                       linewidth=2, label='Auslegerfläche', zorder=6)

            # Plot rotor storage - green solid line
            rotor_dist, rotor_heights = extract_valid_data(rotor_z, distances)
            if rotor_dist:
                ax.plot(rotor_dist, rotor_heights, color='#2ca02c',
                       linewidth=2, label='Blattlagerfläche', zorder=6)

            # Fill areas (Cut/Fill between existing terrain and bottom_z)
            cut_mask = cut_fill > 0
            if np.any(cut_mask):
                ax.fill_between(
                    distances, existing, bottom_z,
                    where=cut_mask,
                    color='red', alpha=0.3, label='Abtrag', zorder=1
                )

            fill_mask = cut_fill < 0
            if np.any(fill_mask):
                ax.fill_between(
                    distances, existing, bottom_z,
                    where=fill_mask,
                    color='green', alpha=0.3, label='Auftrag', zorder=1
                )

            # Plot slope lines (Böschungen)
            slope_lines = profile_data.get('slope_lines', [])
            slope_plotted = False
            for slope in slope_lines:
                slope_label = 'Böschung' if not slope_plotted else None
                ax.plot(
                    [slope['start_dist'], slope['end_dist']],
                    [slope['start_z'], slope['end_z']],
                    color='#8B4513',  # Brown color for slopes
                    linewidth=1.5,
                    linestyle='-.',
                    label=slope_label,
                    zorder=4
                )
                slope_plotted = True

            # Labels and title with actual distance range
            max_distance = distances[-1] if len(distances) > 0 else 0
            ax.set_xlabel(f'Entfernung [m] (0 - {max_distance:.1f} m)', fontsize=12, fontweight='bold')
            ax.set_ylabel('Höhe [m ü.NN]', fontsize=12, fontweight='bold')

            # Set title with line length info
            if line_length:
                title = f'Geländeschnitt: {profile_type} (Länge: {line_length:.1f} m)'
            else:
                title = f'Geländeschnitt: {profile_type}'

            if vertical_exaggeration != 1.0:
                title += f' (Überhöhung {vertical_exaggeration}x)'

            ax.set_title(title, fontsize=14, fontweight='bold')

            # Enhanced grid
            ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

            # Dynamic column count based on number of legend entries
            handles, labels = ax.get_legend_handles_labels()
            ncols = min(5, len(handles))
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08),
                     ncol=ncols, fontsize=8, frameon=True, fancybox=True)

            # Set axis limits
            if xlim:
                ax.set_xlim(xlim)
            else:
                ax.set_xlim(0, max_distance)

            if ylim:
                ax.set_ylim(ylim)

            # Save figure
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close(fig)

            self.logger.info(f"Profile plot saved: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to create profile plot: {e}")
            raise

    def visualize_multiple_profiles(self, profiles: List[Dict], output_dir: str,
                                    vertical_exaggeration: float = 2.0,
                                    volume_info: Optional[Dict] = None,
                                    feedback: Optional[QgsProcessingFeedback] = None,
                                    use_parallel: bool = True,
                                    max_workers: int = None) -> List[Dict]:
        """
        Visualize multiple profile lines with unified scale.

        This method takes pre-generated profile line geometries and creates
        matplotlib plots with a unified scale across all profiles.

        Args:
            profiles (List[Dict]): List of profile dictionaries with 'geometry' key
            output_dir (str): Directory to save PNG files
            vertical_exaggeration (float): Vertical exaggeration for plots
            volume_info (Dict): Volume information for annotations
            feedback (QgsProcessingFeedback): Feedback object
            use_parallel (bool): Use parallel processing (default: True)
            max_workers (int): Maximum number of parallel workers

        Returns:
            List[Dict]: List of profile data with paths to PNG files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Visualizing {len(profiles)} profiles in {output_dir}")

        if feedback:
            feedback.pushInfo(f"Visualizing {len(profiles)} profiles...")

        # First pass: Extract all profile data to determine global scale
        all_profile_data = []
        max_line_length = 0
        min_elevation = float('inf')
        max_elevation = float('-inf')

        for profile in profiles:
            try:
                profile_data = self.extract_profile_data(profile['geometry'])
                all_profile_data.append((profile, profile_data))

                # Track maximum line length
                line_length = profile.get('length', profile['geometry'].length())
                max_line_length = max(max_line_length, line_length)

                # Track elevation range
                min_elevation = min(min_elevation, np.min(profile_data['existing_z']))
                max_elevation = max(max_elevation, np.max(profile_data['existing_z']))
                min_elevation = min(min_elevation, np.min(profile_data['planned_z']))
                max_elevation = max(max_elevation, np.max(profile_data['planned_z']))

            except Exception as e:
                self.logger.error(f"Failed to extract data for profile {profile['type']}: {e}")

        # Add padding to elevation range (5%)
        elevation_range = max_elevation - min_elevation
        elevation_padding = elevation_range * 0.05
        global_ylim = (min_elevation - elevation_padding, max_elevation + elevation_padding)

        if feedback:
            feedback.pushInfo(f"  Global scale - Length: {max_line_length:.1f}m, Elevation: {global_ylim[0]:.1f} - {global_ylim[1]:.1f} m")

        # Decide parallel vs sequential
        if use_parallel and len(all_profile_data) >= 4:
            self.logger.info(f"Using parallel rendering for {len(all_profile_data)} profiles")
            return self._visualize_parallel(
                all_profile_data, output_path, max_line_length, global_ylim,
                vertical_exaggeration, volume_info, feedback, max_workers
            )
        else:
            self.logger.info(f"Using sequential rendering for {len(all_profile_data)} profiles")
            return self._visualize_sequential(
                all_profile_data, output_path, max_line_length, global_ylim,
                vertical_exaggeration, volume_info, feedback
            )

    def _visualize_sequential(self, all_profile_data, output_path, max_line_length,
                             global_ylim, vertical_exaggeration, volume_info, feedback) -> List[Dict]:
        """Sequential profile visualization (original implementation)."""
        results = []

        for profile, profile_data in all_profile_data:
            if feedback and feedback.isCanceled():
                break

            try:
                png_filename = f"{profile['type']}.png"
                png_path = output_path / png_filename

                line_length = profile.get('length', profile['geometry'].length())

                self.plot_profile(
                    profile_data,
                    str(png_path),
                    profile_type=profile['type'],
                    vertical_exaggeration=vertical_exaggeration,
                    volume_info=volume_info,
                    line_length=line_length,
                    xlim=(0, max_line_length),
                    ylim=global_ylim
                )

                profile['data'] = profile_data
                profile['png_path'] = str(png_path)
                results.append(profile)

                if feedback:
                    feedback.pushInfo(f"  ✓ {png_filename} (length: {line_length:.1f}m)")

            except Exception as e:
                self.logger.error(f"Failed to generate profile {profile['type']}: {e}")
                if feedback:
                    feedback.reportError(
                        f"Error generating profile {profile['type']}: {e}",
                        fatalError=False
                    )

        self.logger.info(f"Generated {len(results)}/{len(all_profile_data)} profile visualizations")
        return results

    def _visualize_parallel(self, all_profile_data, output_path, max_line_length,
                           global_ylim, vertical_exaggeration, volume_info, feedback,
                           max_workers=None) -> List[Dict]:
        """Parallel profile visualization using ProcessPoolExecutor."""
        if max_workers is None:
            max_workers = max(1, mp.cpu_count() - 1)

        self.logger.info(f"Rendering {len(all_profile_data)} profiles in parallel ({max_workers} workers)")

        results = []
        completed = 0

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {}
            for profile, profile_data in all_profile_data:
                png_filename = f"{profile['type']}.png"
                png_path = output_path / png_filename
                line_length = profile.get('length', profile['geometry'].length())

                future = executor.submit(
                    _plot_single_profile,
                    profile_data,
                    str(png_path),
                    profile['type'],
                    vertical_exaggeration,
                    volume_info,
                    line_length,
                    (0, max_line_length),
                    global_ylim
                )
                futures[future] = (profile, profile_data, str(png_path), png_filename)

            # Process results as they complete
            for future in as_completed(futures):
                profile, profile_data, png_path, png_filename = futures[future]
                completed += 1

                if feedback and feedback.isCanceled():
                    self.logger.info("Profile rendering cancelled by user")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                try:
                    _ = future.result()

                    profile['data'] = profile_data
                    profile['png_path'] = png_path
                    results.append(profile)

                    if feedback:
                        feedback.pushInfo(f"  ✓ [{completed}/{len(all_profile_data)}] {png_filename}")

                except Exception as e:
                    self.logger.error(f"Failed to generate profile {profile['type']}: {e}")
                    if feedback:
                        feedback.reportError(
                            f"Error generating profile {profile['type']}: {e}",
                            fatalError=False
                        )

        self.logger.info(f"Generated {len(results)}/{len(all_profile_data)} profile visualizations (parallel)")
        return results

    def generate_all_profiles(self, output_dir: str,
                             spacing: float = 10.0,
                             overhang_percent: float = 10.0,
                             vertical_exaggeration: float = 2.0,
                             volume_info: Optional[Dict] = None,
                             feedback: Optional[QgsProcessingFeedback] = None,
                             use_parallel: bool = True,
                             max_workers: int = None) -> List[Dict]:
        """
        Generate all cross-section profile lines, extract data, and create plots.

        Args:
            output_dir (str): Directory to save PNG files
            spacing (float): Distance between cross-sections in meters (default: 10m)
            overhang_percent (float): Percentage to extend beyond polygon (default: 10%)
            vertical_exaggeration (float): Vertical exaggeration for plots
            volume_info (Dict): Volume information for annotations
            feedback (QgsProcessingFeedback): Feedback object
            use_parallel (bool): Use parallel processing (default: True)
            max_workers (int): Maximum number of parallel workers

        Returns:
            List[Dict]: List of profile data with paths to PNG files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Generating cross-section profiles in {output_dir}")

        if feedback:
            feedback.pushInfo(f"Generating cross-section profiles (spacing: {spacing}m)...")

        # Generate cross-section profile lines
        profiles = self.generate_cross_section_profiles(
            spacing=spacing,
            overhang_percent=overhang_percent
        )

        if feedback:
            feedback.pushInfo(f"  Created {len(profiles)} cross-section lines")

        # Use the parallel visualize_multiple_profiles method
        results = self.visualize_multiple_profiles(
            profiles=profiles,
            output_dir=output_dir,
            vertical_exaggeration=vertical_exaggeration,
            volume_info=volume_info,
            feedback=feedback,
            use_parallel=use_parallel,
            max_workers=max_workers
        )

        self.logger.info(f"Generated {len(results)}/{len(profiles)} profiles")

        return results

    def generate_all_longitudinal_profiles(self, output_dir: str,
                                          spacing: float = 10.0,
                                          overhang_percent: float = 10.0,
                                          vertical_exaggeration: float = 2.0,
                                          volume_info: Optional[Dict] = None,
                                          feedback: Optional[QgsProcessingFeedback] = None,
                                          use_parallel: bool = True,
                                          max_workers: int = None) -> List[Dict]:
        """
        Generate all longitudinal profile lines, extract data, and create plots.

        Args:
            output_dir (str): Directory to save PNG files
            spacing (float): Distance between longitudinal sections in meters (default: 10m)
            overhang_percent (float): Percentage to extend beyond polygon (default: 10%)
            vertical_exaggeration (float): Vertical exaggeration for plots
            volume_info (Dict): Volume information for annotations
            feedback (QgsProcessingFeedback): Feedback object
            use_parallel (bool): Use parallel processing (default: True)
            max_workers (int): Maximum number of parallel workers

        Returns:
            List[Dict]: List of profile data with paths to PNG files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Generating longitudinal profiles in {output_dir}")

        if feedback:
            feedback.pushInfo(f"Generating longitudinal profiles (spacing: {spacing}m)...")

        # Generate longitudinal profile lines
        profiles = self.generate_longitudinal_profiles(
            spacing=spacing,
            overhang_percent=overhang_percent
        )

        if feedback:
            feedback.pushInfo(f"  Created {len(profiles)} longitudinal section lines")

        # Use the parallel visualize_multiple_profiles method
        results = self.visualize_multiple_profiles(
            profiles=profiles,
            output_dir=output_dir,
            vertical_exaggeration=vertical_exaggeration,
            volume_info=volume_info,
            feedback=feedback,
            use_parallel=use_parallel,
            max_workers=max_workers
        )

        self.logger.info(f"Generated {len(results)}/{len(profiles)} longitudinal profiles")

        return results
