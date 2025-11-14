"""
Profile Generator for Wind Turbine Earthwork Calculator V2

Generates terrain cross-sections and visualizations.

Adapted from WindTurbine_Earthwork_Calculator.py

Author: Wind Energy Site Planning
Version: 2.0
"""

import math
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np

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
    create_radial_lines,
    create_perpendicular_cross_sections,
    create_parallel_longitudinal_sections
)
from ..utils.logging_utils import get_plugin_logger


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
                 platform_height: float):
        """
        Initialize profile generator.

        Args:
            dem_layer (QgsRasterLayer): Digital elevation model
            polygon (QgsGeometry): Platform polygon
            platform_height (float): Optimized platform height (m above sea level)
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

        # Get polygon properties
        self.centroid = get_centroid(polygon)
        self.radius = get_polygon_radius(polygon)

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
                - planned_z: np.array of planned elevations (platform height)
                - cut_fill: np.array of cut (+) / fill (-) values
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
        planned_z = []

        for dist in distances:
            # Interpolate point on line at distance
            point = line_geom.interpolate(dist).asPoint()

            # Sample DEM at point
            val, ok = self.provider.sample(point, 1)
            z_existing = float(val) if (ok and val is not None) else 0.0
            existing_z.append(z_existing)

            # Calculate planned elevation
            # Check if point is within platform polygon
            point_geom = QgsGeometry.fromPointXY(point)
            if self.polygon.contains(point_geom):
                z_planned = self.platform_height
            else:
                # Outside platform: use existing terrain
                z_planned = z_existing

            planned_z.append(z_planned)

        # Convert to arrays
        existing_z = np.array(existing_z, dtype=float)
        planned_z = np.array(planned_z, dtype=float)

        # Calculate cut/fill
        # Positive = cut (remove material), Negative = fill (add material)
        cut_fill = existing_z - planned_z

        profile_data = {
            'distances': distances,
            'existing_z': existing_z,
            'planned_z': planned_z,
            'cut_fill': cut_fill
        }

        return profile_data

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
            planned = profile_data['planned_z']
            cut_fill = profile_data['cut_fill']

            # Plot terrain and platform lines
            ax.plot(distances, existing, 'k-', linewidth=2, label='Bestehendes Gelände')
            ax.plot(distances, planned, 'b-', linewidth=2, label='Geplante Plattform')

            # Fill areas
            # Cut (red) - where existing > planned
            cut_mask = cut_fill > 0
            if np.any(cut_mask):
                ax.fill_between(
                    distances, existing, planned,
                    where=cut_mask,
                    color='red', alpha=0.3, label='Abtrag'
                )

            # Fill (green) - where existing < planned
            fill_mask = cut_fill < 0
            if np.any(fill_mask):
                ax.fill_between(
                    distances, existing, planned,
                    where=fill_mask,
                    color='green', alpha=0.3, label='Auftrag'
                )

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
            
            # Legend below plot (horizontal)
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08), 
                     ncol=4, fontsize=10, frameon=True, fancybox=True)

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

    def generate_all_profiles(self, output_dir: str,
                             spacing: float = 10.0,
                             overhang_percent: float = 10.0,
                             vertical_exaggeration: float = 2.0,
                             volume_info: Optional[Dict] = None,
                             feedback: Optional[QgsProcessingFeedback] = None) -> List[Dict]:
        """
        Generate all cross-section profile lines, extract data, and create plots.

        Args:
            output_dir (str): Directory to save PNG files
            spacing (float): Distance between cross-sections in meters (default: 10m)
            overhang_percent (float): Percentage to extend beyond polygon (default: 10%)
            vertical_exaggeration (float): Vertical exaggeration for plots
            volume_info (Dict): Volume information for annotations
            feedback (QgsProcessingFeedback): Feedback object

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
                max_line_length = max(max_line_length, profile['length'])
                
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

        # Second pass: Create plots with unified scale
        results = []

        for profile, profile_data in all_profile_data:
            if feedback and feedback.isCanceled():
                break

            try:
                # Create plot with unified scale
                png_filename = f"{profile['type']}.png"
                png_path = output_path / png_filename

                self.plot_profile(
                    profile_data,
                    str(png_path),
                    profile_type=profile['type'],
                    vertical_exaggeration=vertical_exaggeration,
                    volume_info=volume_info,
                    line_length=profile['length'],
                    xlim=(0, max_line_length),
                    ylim=global_ylim
                )

                # Add to results
                profile['data'] = profile_data
                profile['png_path'] = str(png_path)
                results.append(profile)

                if feedback:
                    feedback.pushInfo(f"  ✓ {png_filename} (length: {profile['length']:.1f}m)")

            except Exception as e:
                self.logger.error(f"Failed to generate profile {profile['type']}: {e}")
                if feedback:
                    feedback.reportError(
                        f"Error generating profile {profile['type']}: {e}",
                        fatalError=False
                    )

        self.logger.info(f"Generated {len(results)}/{len(profiles)} profiles")

        return results

    def generate_all_longitudinal_profiles(self, output_dir: str,
                                          spacing: float = 10.0,
                                          overhang_percent: float = 10.0,
                                          vertical_exaggeration: float = 2.0,
                                          volume_info: Optional[Dict] = None,
                                          feedback: Optional[QgsProcessingFeedback] = None) -> List[Dict]:
        """
        Generate all longitudinal profile lines, extract data, and create plots.

        Args:
            output_dir (str): Directory to save PNG files
            spacing (float): Distance between longitudinal sections in meters (default: 10m)
            overhang_percent (float): Percentage to extend beyond polygon (default: 10%)
            vertical_exaggeration (float): Vertical exaggeration for plots
            volume_info (Dict): Volume information for annotations
            feedback (QgsProcessingFeedback): Feedback object

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
                max_line_length = max(max_line_length, profile['length'])

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

        # Second pass: Create plots with unified scale
        results = []

        for profile, profile_data in all_profile_data:
            if feedback and feedback.isCanceled():
                break

            try:
                # Create plot with unified scale
                png_filename = f"{profile['type']}.png"
                png_path = output_path / png_filename

                self.plot_profile(
                    profile_data,
                    str(png_path),
                    profile_type=profile['type'],
                    vertical_exaggeration=vertical_exaggeration,
                    volume_info=volume_info,
                    line_length=profile['length'],
                    xlim=(0, max_line_length),
                    ylim=global_ylim
                )

                # Add to results
                profile['data'] = profile_data
                profile['png_path'] = str(png_path)
                results.append(profile)

                if feedback:
                    feedback.pushInfo(f"  ✓ {png_filename} (length: {profile['length']:.1f}m)")

            except Exception as e:
                self.logger.error(f"Failed to generate profile {profile['type']}: {e}")
                if feedback:
                    feedback.reportError(
                        f"Error generating profile {profile['type']}: {e}",
                        fatalError=False
                    )

        self.logger.info(f"Generated {len(results)}/{len(profiles)} longitudinal profiles")

        return results
