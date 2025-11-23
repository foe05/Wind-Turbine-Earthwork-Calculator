"""
Workflow Runner for Wind Turbine Earthwork Calculator V2 - Multi-Surface Edition

Orchestrates the complete workflow from multi-DXF import to report generation.

Author: Wind Energy Site Planning
Version: 2.0.0 - Multi-Surface Extension
"""

import os
from pathlib import Path
from datetime import datetime
import tempfile

from qgis.PyQt.QtCore import QObject, QThread, pyqtSignal
from qgis.core import (
    QgsVectorLayer,
    QgsRasterLayer,
    QgsFeature,
    QgsFields,
    QgsField,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransformContext,
    QgsProject,
    QgsFillSymbol,
    QgsLineSymbol,
    QgsVectorFileWriter,
    QgsPalLayerSettings,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsVectorLayerSimpleLabeling,
    QgsLayerTreeGroup
)
import shutil
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtCore import QVariant

from .dxf_importer import DXFImporter
from .dem_downloader import DEMDownloader
from .multi_surface_calculator import MultiSurfaceCalculator
from .profile_generator import ProfileGenerator
from .report_generator import ReportGenerator
from .surface_types import (
    MultiSurfaceProject,
    SurfaceConfig,
    SurfaceType,
    HeightMode
)
from .surface_validators import validate_project
from .uncertainty import UncertaintyConfig, TerrainType
from ..utils.geometry_utils import get_centroid
from ..utils.logging_utils import get_plugin_logger


class WorkflowWorker(QObject):
    """
    Worker class that runs the multi-surface workflow in a separate thread.
    """

    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, iface, params):
        """Initialize worker."""
        super().__init__()
        self.iface = iface
        self.params = params
        self.logger = get_plugin_logger()
        self.is_cancelled = False

    def run(self):
        """Run the workflow (called in thread)."""
        try:
            self.logger.info("=" * 60)
            self.logger.info("MULTI-SURFACE WORKFLOW GESTARTET")
            self.logger.info("=" * 60)
            self._run_workflow()
        except Exception as e:
            self.logger.error(f"Workflow failed: {e}", exc_info=True)
            self.finished.emit(False, f"Fehler: {str(e)}")

    def cancel(self):
        """Cancel workflow."""
        self.is_cancelled = True

    def _run_workflow(self):
        """Run the complete multi-surface workflow."""
        self.logger.info("Starting multi-surface workflow execution...")
        workspace = Path(self.params['workspace'])

        # Create workspace structure
        self.progress_updated.emit(5, "📁 Workspace-Struktur wird erstellt...")
        self.logger.info(f"Workspace: {workspace}")

        results_dir = workspace / "ergebnisse"
        profiles_dir = workspace / "gelaendeschnitte"
        cache_dir = workspace / "cache" / "dem_tiles"

        results_dir.mkdir(parents=True, exist_ok=True)
        profiles_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # === STEP 1: Import DXF files ===
        self.progress_updated.emit(10, "📂 DXF-Dateien werden importiert...")
        self.logger.info("Importing DXF files...")

        surfaces = {}

        # Required DXF files
        required_dxf_files = [
            ('crane', 'dxf_crane', SurfaceType.CRANE_PAD, "Kranstellfläche"),
            ('foundation', 'dxf_foundation', SurfaceType.FOUNDATION, "Fundamentfläche"),
        ]

        # Optional DXF files
        optional_dxf_files = [
            ('boom', 'dxf_boom', SurfaceType.BOOM, "Auslegerfläche"),
            ('rotor', 'dxf_rotor', SurfaceType.ROTOR_STORAGE, "Blattlagerfläche"),
            ('road', 'dxf_road', SurfaceType.ROAD_ACCESS, "Zufahrtsstraße"),
        ]

        progress_per_dxf = 5
        current_progress = 10

        # Import required DXF files
        for key, param_key, surface_type, display_name in required_dxf_files:
            dxf_path = self.params[param_key]
            self.progress_updated.emit(
                current_progress,
                f"  📄 Importiere {display_name}..."
            )

            try:
                importer = DXFImporter(
                    dxf_path,
                    tolerance=self.params['dxf_tolerance']
                )
                polygon, metadata = importer.import_as_polygon()

                if not polygon or polygon.isEmpty():
                    raise Exception(f"Keine gültige Geometrie in {display_name} DXF gefunden")

                surfaces[key] = {
                    'geometry': polygon,
                    'metadata': metadata,
                    'dxf_path': dxf_path
                }

                self.logger.info(
                    f"{display_name}: {metadata['num_vertices']} Punkte, "
                    f"{metadata['area']:.2f} m²"
                )

            except Exception as e:
                self.logger.error(f"DXF Import failed for {display_name}: {e}", exc_info=True)
                raise Exception(f"Fehler beim Import von {display_name}: {e}")

            current_progress += progress_per_dxf

        # Import optional DXF files
        for key, param_key, surface_type, display_name in optional_dxf_files:
            dxf_path = self.params.get(param_key)

            if dxf_path:
                self.progress_updated.emit(
                    current_progress,
                    f"  📄 Importiere {display_name}..."
                )

                try:
                    importer = DXFImporter(
                        dxf_path,
                        tolerance=self.params['dxf_tolerance']
                    )
                    polygon, metadata = importer.import_as_polygon()

                    if not polygon or polygon.isEmpty():
                        raise Exception(f"Keine gültige Geometrie in {display_name} DXF gefunden")

                    surfaces[key] = {
                        'geometry': polygon,
                        'metadata': metadata,
                        'dxf_path': dxf_path
                    }

                    self.logger.info(
                        f"{display_name}: {metadata['num_vertices']} Punkte, "
                        f"{metadata['area']:.2f} m²"
                    )

                except Exception as e:
                    self.logger.error(f"DXF Import failed for {display_name}: {e}", exc_info=True)
                    raise Exception(f"Fehler beim Import von {display_name}: {e}")
            else:
                self.logger.info(f"{display_name}: nicht angegeben (optional)")
                surfaces[key] = None

            current_progress += progress_per_dxf

        self.progress_updated.emit(30, "✓ DXF-Dateien importiert")

        # === STEP 2: Create MultiSurfaceProject ===
        self.progress_updated.emit(32, "🔧 Erstelle Multi-Surface Projekt...")
        self.logger.info("Creating MultiSurfaceProject...")

        try:
            # Create surface configs
            crane_config = SurfaceConfig(
                surface_type=SurfaceType.CRANE_PAD,
                geometry=surfaces['crane']['geometry'],
                dxf_path=surfaces['crane']['dxf_path'],
                height_mode=HeightMode.OPTIMIZED,
                metadata=surfaces['crane']['metadata']
            )

            foundation_config = SurfaceConfig(
                surface_type=SurfaceType.FOUNDATION,
                geometry=surfaces['foundation']['geometry'],
                dxf_path=surfaces['foundation']['dxf_path'],
                height_mode=HeightMode.FIXED,
                height_value=self.params['fok'],
                metadata=surfaces['foundation']['metadata']
            )

            # Create optional surface configs (boom and rotor)
            boom_config = None
            if surfaces.get('boom'):
                boom_config = SurfaceConfig(
                    surface_type=SurfaceType.BOOM,
                    geometry=surfaces['boom']['geometry'],
                    dxf_path=surfaces['boom']['dxf_path'],
                    height_mode=HeightMode.SLOPED,
                    slope_longitudinal=self.params['boom_slope'],
                    auto_slope=self.params['boom_auto_slope'],
                    slope_min=2.0,
                    slope_max=8.0,
                    metadata=surfaces['boom']['metadata']
                )

            rotor_config = None
            if surfaces.get('rotor'):
                rotor_config = SurfaceConfig(
                    surface_type=SurfaceType.ROTOR_STORAGE,
                    geometry=surfaces['rotor']['geometry'],
                    dxf_path=surfaces['rotor']['dxf_path'],
                    height_mode=HeightMode.RELATIVE,
                    height_reference='crane',
                    metadata=surfaces['rotor']['metadata']
                )

            # Create road access config
            road_config = None
            if surfaces.get('road'):
                road_config = SurfaceConfig(
                    surface_type=SurfaceType.ROAD_ACCESS,
                    geometry=surfaces['road']['geometry'],
                    dxf_path=surfaces['road']['dxf_path'],
                    height_mode=HeightMode.SLOPED,
                    slope_longitudinal=self.params.get('road_slope_percent', 8.0),
                    auto_slope=True,  # Auto-detect slope direction from terrain
                    slope_min=1.0,
                    slope_max=15.0,
                    metadata=surfaces['road']['metadata']
                )

            # Import holms if holm DXF path is provided
            rotor_holms = None
            if self.params.get('holm_dxf_path'):
                try:
                    self.logger.info(f"Importing holms from: {self.params['holm_dxf_path']}")
                    holm_importer = DXFImporter(
                        self.params['holm_dxf_path'],
                        tolerance=0.1,
                        crs_epsg=self.params.get('crs_epsg', 25832)
                    )
                    rotor_holms, holm_metadata = holm_importer.import_holms()
                    self.logger.info(
                        f"Imported {len(rotor_holms)} holms, "
                        f"total area: {holm_metadata['total_area']:.2f}m²"
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to import holms: {e}. Continuing without holms.")
                    rotor_holms = None

            # Create project
            project = MultiSurfaceProject(
                crane_pad=crane_config,
                foundation=foundation_config,
                boom=boom_config,
                rotor_storage=rotor_config,
                road_access=road_config,
                rotor_holms=rotor_holms,
                fok=self.params['fok'],
                foundation_depth=self.params['foundation_depth'],
                foundation_diameter=self.params.get('foundation_diameter'),
                gravel_thickness=self.params['gravel_thickness'],
                rotor_height_offset=self.params['rotor_height_offset'],
                rotor_height_offset_max=self.params.get('rotor_height_offset_max', 0.5),
                slope_angle=self.params['slope_angle'],
                search_range_below_fok=self.params['search_range_below_fok'],
                search_range_above_fok=self.params['search_range_above_fok'],
                search_step=self.params['height_step'],
                boom_slope_max=self.params.get('boom_slope_max', 4.0),
                boom_slope_optimize=self.params.get('boom_slope_optimize', True),
                boom_slope_step_coarse=self.params.get('boom_slope_step_coarse', 0.5),
                boom_slope_step_fine=self.params.get('boom_slope_step_fine', 0.1),
                rotor_height_optimize=self.params.get('rotor_height_optimize', True),
                rotor_height_step_coarse=self.params.get('rotor_height_step_coarse', 0.2),
                rotor_height_step_fine=self.params.get('rotor_height_step_fine', 0.05),
                optimize_for_net_earthwork=self.params.get('optimize_for_net_earthwork', True),
                # Road access parameters
                road_slope_percent=self.params.get('road_slope_percent', 8.0),
                road_gravel_enabled=self.params.get('road_gravel_enabled', True),
                road_gravel_thickness=self.params.get('road_gravel_thickness', 0.3),
                road_slope_optimize=self.params.get('road_slope_optimize', False),
                road_slope_min=self.params.get('road_slope_min', 4.0),
                road_slope_max=self.params.get('road_slope_max', 12.0)
            )

            self.logger.info("MultiSurfaceProject created successfully")

        except Exception as e:
            self.logger.error(f"Failed to create project: {e}", exc_info=True)
            raise Exception(f"Fehler beim Erstellen des Projekts: {e}")

        # === STEP 3: Validate project ===
        self.progress_updated.emit(35, "✅ Validiere Flächenbeziehungen...")
        self.logger.info("Validating project spatial relationships...")

        is_valid, errors = validate_project(project)
        if not is_valid:
            error_msg = "Validierungsfehler:\n" + "\n".join(errors)
            self.logger.error(error_msg)
            raise Exception(error_msg)

        self.progress_updated.emit(38, "✓ Alle Validierungen bestanden")

        # === STEP 4: DEM Download ===
        self.progress_updated.emit(40, "🌍 DEM-Daten werden heruntergeladen...")
        self.logger.info("Starting DEM download...")

        try:
            # Use crane pad as reference for DEM extent (it should cover all surfaces)
            # But we buffer generously to cover all surfaces
            # Only include geometries that exist (boom and rotor are optional)
            all_geoms = [
                surfaces['crane']['geometry'],
                surfaces['foundation']['geometry'],
            ]

            # Add optional surfaces if they exist
            if surfaces['boom'] is not None:
                all_geoms.append(surfaces['boom']['geometry'])
            if surfaces['rotor'] is not None:
                all_geoms.append(surfaces['rotor']['geometry'])
            if surfaces['road'] is not None:
                all_geoms.append(surfaces['road']['geometry'])

            # Create union of all geometries
            from qgis.core import QgsGeometry
            combined_geom = all_geoms[0]
            for geom in all_geoms[1:]:
                combined_geom = combined_geom.combine(geom)

            temp_dem_path = tempfile.mktemp(suffix='.tif', prefix='dem_mosaic_')
            self.logger.info(f"Temp DEM path: {temp_dem_path}")

            downloader = DEMDownloader(
                cache_dir=str(cache_dir),
                force_refresh=self.params['force_refresh']
            )

            self.progress_updated.emit(42, "⬇️ Lade DEM-Kacheln...")
            dem_path = downloader.download_for_geometry(
                combined_geom,
                temp_dem_path,
                buffer_m=250
            )

            self.logger.info(f"DEM downloaded: {dem_path}")

            dem_layer = QgsRasterLayer(dem_path, "DGM Mosaik")
            if not dem_layer.isValid():
                raise Exception(f"DEM konnte nicht geladen werden: {dem_path}")

            # Save DEM mosaic to results directory
            dem_result_name = f"WKA_{int(get_centroid(surfaces['crane']['geometry']).x())}_{int(get_centroid(surfaces['crane']['geometry']).y())}_DEM.tif"
            dem_result_path = results_dir / dem_result_name
            shutil.copy2(dem_path, dem_result_path)
            self.logger.info(f"DEM mosaic saved to results: {dem_result_path}")

            self.progress_updated.emit(50, "✓ DGM-Mosaik erstellt")

        except Exception as e:
            self.logger.error(f"DEM Download failed: {e}", exc_info=True)
            raise

        # === STEP 5: Multi-Surface Optimization ===
        self.progress_updated.emit(52, "⚙️ Optimiere Kranstellflächen-Höhe...")
        self.logger.info(
            f"Starting optimization: {project.search_min_height:.2f}m - "
            f"{project.search_max_height:.2f}m ü.NN"
        )

        uncertainty_result = None  # Will be set if uncertainty analysis is enabled

        try:
            calculator = MultiSurfaceCalculator(dem_layer, project)

            # Check if uncertainty analysis is enabled
            if self.params.get('uncertainty_enabled', False):
                self.progress_updated.emit(54, "📊 Unsicherheitsanalyse wird durchgeführt...")
                self.logger.info("Uncertainty analysis enabled - running Monte Carlo simulation")

                # Map terrain type index to TerrainType enum
                terrain_type_map = {
                    0: TerrainType.FLAT,
                    1: TerrainType.MODERATE,
                    2: TerrainType.STEEP
                }
                terrain_type = terrain_type_map.get(
                    self.params.get('terrain_type_index', 0),
                    TerrainType.FLAT
                )

                # Create uncertainty configuration
                uncertainty_config = UncertaintyConfig(
                    num_samples=self.params.get('mc_samples', 1000),
                    terrain_type=terrain_type,
                    foundation_depth_std=self.params.get('foundation_depth_std', 0.1),
                    slope_angle_std=self.params.get('slope_angle_std', 3.0),
                    use_latin_hypercube=True
                )

                self.logger.info(
                    f"Monte Carlo config: {uncertainty_config.num_samples} samples, "
                    f"terrain={terrain_type.value}, DEM σ={uncertainty_config.dem_vertical_std*100:.1f}cm"
                )

                # Run optimization with uncertainty analysis
                uncertainty_result = calculator.find_optimum_with_uncertainty(uncertainty_config)

                # Extract optimal height and results from uncertainty analysis
                optimal_crane_height = uncertainty_result.crane_height.mean
                results = uncertainty_result.nominal_result

                self.logger.info(
                    f"Uncertainty analysis complete: {optimal_crane_height:.2f} m ü.NN "
                    f"(90% CI: [{uncertainty_result.crane_height.percentile_5:.2f}, "
                    f"{uncertainty_result.crane_height.percentile_95:.2f}])"
                )
                self.logger.info(
                    f"Total volume moved: {uncertainty_result.total_volume_moved.mean:.0f} m³ "
                    f"± {uncertainty_result.total_volume_moved.std:.0f} m³"
                )

                self.progress_updated.emit(
                    70,
                    f"✓ Optimale Höhe: {optimal_crane_height:.2f} m ü.NN "
                    f"(90% CI: [{uncertainty_result.crane_height.percentile_5:.2f}, "
                    f"{uncertainty_result.crane_height.percentile_95:.2f}])"
                )
            else:
                # Standard optimization without uncertainty
                optimal_crane_height, results = calculator.find_optimum()

                self.logger.info(f"Optimization complete: {optimal_crane_height:.2f} m ü.NN")
                self.logger.info(
                    f"Results: Total cut={results.total_cut:.0f} m³, "
                    f"Total fill={results.total_fill:.0f} m³"
                )

                self.progress_updated.emit(
                    70,
                    f"✓ Optimale Kranstellflächen-Höhe: {optimal_crane_height:.2f} m ü.NN"
                )

        except Exception as e:
            self.logger.error(f"Optimization failed: {e}", exc_info=True)
            raise

        # === STEP 6: Profile Generation ===
        self.progress_updated.emit(72, "📊 Geländeschnitte werden erstellt...")
        self.logger.info(f"Generating profiles in: {profiles_dir}")

        try:
            # Get boom connection info from calculator
            boom_connection_edge = None
            boom_slope_direction = None
            if hasattr(calculator, 'boom_connection_edge'):
                boom_connection_edge = calculator.boom_connection_edge
            if hasattr(calculator, 'boom_slope_direction'):
                boom_slope_direction = calculator.boom_slope_direction

            # Create ProfileGenerator with all surface information
            # Use the optimized boom slope from results, not the project default
            optimized_boom_slope = results.boom_slope_percent if hasattr(results, 'boom_slope_percent') else (
                project.boom.slope_longitudinal if project.boom else 0.0
            )

            # Debug logging for boom parameters passed to ProfileGenerator
            self.logger.info(f"Creating ProfileGenerator with boom parameters:")
            self.logger.info(f"  optimized_boom_slope: {optimized_boom_slope}")
            self.logger.info(f"  boom_connection_edge: {boom_connection_edge is not None}")
            self.logger.info(f"  boom_slope_direction: {boom_slope_direction}")

            profile_gen = ProfileGenerator(
                dem_layer,
                project.crane_pad.geometry,
                optimal_crane_height,
                foundation_geometry=project.foundation.geometry,
                foundation_height=project.fok,
                foundation_depth=project.foundation_depth,
                gravel_thickness=project.gravel_thickness,
                slope_angle=project.slope_angle,
                boom_geometry=project.boom.geometry if project.boom else None,
                boom_connection_edge=boom_connection_edge,
                boom_slope_direction=boom_slope_direction,
                boom_slope_percent=optimized_boom_slope,
                rotor_geometry=project.rotor_storage.geometry if project.rotor_storage else None,
                rotor_height=optimal_crane_height + results.rotor_height_offset_optimized if hasattr(results, 'rotor_height_offset_optimized') else optimal_crane_height + project.rotor_height_offset,
                rotor_holms=project.rotor_holms if project.rotor_holms else None
            )

            # Collect all surface geometries for bounding box
            all_geometries = [
                project.crane_pad.geometry,
                project.foundation.geometry,
            ]
            if project.boom:
                all_geometries.append(project.boom.geometry)
            if project.rotor_storage:
                all_geometries.append(project.rotor_storage.geometry)

            # Get buffer parameter
            bbox_buffer = self.params.get('bbox_buffer', 10.0)

            all_profiles = []

            # Generate cross-section profiles over bounding box
            if self.params.get('generate_cross_profiles', True):
                self.logger.info("Generating cross-section profiles over bounding box...")
                self.progress_updated.emit(74, "📊 Querprofile werden erstellt...")

                cross_profiles_raw = profile_gen.generate_cross_sections_bbox(
                    all_geometries=all_geometries,
                    buffer_percent=bbox_buffer,
                    spacing=self.params.get('cross_profile_spacing', 10.0)
                )

                # Generate visualizations for each profile
                cross_profiles = profile_gen.visualize_multiple_profiles(
                    cross_profiles_raw,
                    output_dir=str(profiles_dir),
                    vertical_exaggeration=self.params['vertical_exaggeration'],
                    volume_info=results.to_dict()
                )
                all_profiles.extend(cross_profiles)
                self.logger.info(f"Generated {len(cross_profiles)} cross-section profiles")

            # Generate longitudinal profiles over bounding box
            if self.params.get('generate_long_profiles', True):
                self.logger.info("Generating longitudinal profiles over bounding box...")
                self.progress_updated.emit(78, "📊 Längsprofile werden erstellt...")

                long_profiles_raw = profile_gen.generate_longitudinal_sections_bbox(
                    all_geometries=all_geometries,
                    buffer_percent=bbox_buffer,
                    spacing=self.params.get('long_profile_spacing', 10.0)
                )

                # Generate visualizations for each profile
                long_profiles = profile_gen.visualize_multiple_profiles(
                    long_profiles_raw,
                    output_dir=str(profiles_dir),
                    vertical_exaggeration=self.params['vertical_exaggeration'],
                    volume_info=results.to_dict()
                )
                all_profiles.extend(long_profiles)
                self.logger.info(f"Generated {len(long_profiles)} longitudinal profiles")

            profiles = all_profiles
            profile_pngs = [p['png_path'] for p in profiles if 'png_path' in p]
            self.logger.info(f"Total: Generated {len(profile_pngs)} profile images")
            self.progress_updated.emit(82, f"✓ {len(profiles)} Geländeschnitte erstellt")

        except Exception as e:
            self.logger.error(f"Profile generation failed: {e}", exc_info=True)
            raise

        # === STEP 7: Report Generation ===
        self.progress_updated.emit(85, "📝 HTML-Bericht wird erstellt...")
        self.logger.info("Generating HTML report")

        # Get centroid for naming
        centroid = get_centroid(project.crane_pad.geometry)
        x_coord = int(centroid.x())
        y_coord = int(centroid.y())

        # Create memory layers for overview map (all surfaces)
        surface_layers = self._create_memory_layers(
            project,
            profiles,
            dem_layer.crs()
        )

        # Generate filenames
        gpkg_name = f"WKA_{x_coord}_{y_coord}_MultiSurface.gpkg"
        gpkg_path = results_dir / gpkg_name
        report_path = results_dir / f"WKA_{x_coord}_{y_coord}_Bericht_MultiSurface.html"

        # Generate report
        report_config = {
            'slope_angle': self.params['slope_angle'],
            'fok': self.params['fok'],
            'foundation_depth': self.params['foundation_depth'],
            'gravel_thickness': self.params['gravel_thickness'],
            'boom_slope': self.params['boom_slope'],
            'boom_auto_slope': self.params['boom_auto_slope'],
            'rotor_height_offset': self.params['rotor_height_offset'],
            'generate_cross_profiles': self.params.get('generate_cross_profiles', True),
            'cross_profile_spacing': self.params.get('cross_profile_spacing', 10.0),
            'generate_long_profiles': self.params.get('generate_long_profiles', True),
            'long_profile_spacing': self.params.get('long_profile_spacing', 10.0)
        }

        report_gen = ReportGenerator(
            results.to_dict(),
            project.crane_pad.geometry,
            dem_layer,
            platform_layer=surface_layers.get('crane_pad'),
            foundation_layer=surface_layers.get('foundation'),
            boom_layer=surface_layers.get('boom'),
            rotor_layer=surface_layers.get('rotor_storage'),
            road_access_layer=surface_layers.get('road_access'),
            profile_lines_layer=surface_layers.get('profile_lines'),
            uncertainty_result=uncertainty_result
        )
        report_gen.generate_html(
            str(report_path),
            profile_pngs,
            report_config,
            profiles_dir=str(profiles_dir)
        )

        # === STEP 8: Save to GeoPackage ===
        self.progress_updated.emit(90, "💾 Daten werden in GeoPackage gespeichert...")
        self.logger.info(f"Saving to GeoPackage: {gpkg_path}")

        self._save_to_geopackage(
            str(gpkg_path),
            project,
            profiles,
            dem_path,
            optimal_crane_height,
            results
        )

        # === STEP 9: Add to QGIS ===
        self.progress_updated.emit(95, "🗺️ Layer werden zu QGIS hinzugefügt...")
        self.logger.info("Adding layers to QGIS project")

        try:
            # Collect DXF paths for loading
            dxf_paths = {
                'crane': surfaces['crane']['dxf_path'],
                'foundation': surfaces['foundation']['dxf_path'],
            }
            if surfaces.get('boom'):
                dxf_paths['boom'] = surfaces['boom']['dxf_path']
            if surfaces.get('rotor'):
                dxf_paths['rotor'] = surfaces['rotor']['dxf_path']

            self._add_to_qgis(
                str(gpkg_path),
                str(report_path),
                str(dem_result_path),
                dxf_paths,
                workspace.name  # Use workspace folder name for layer group
            )
        except Exception as e:
            self.logger.warning(f"Could not add layers to QGIS: {e}")

        # Finished
        self.logger.info("=" * 60)
        self.logger.info("MULTI-SURFACE WORKFLOW ABGESCHLOSSEN")
        self.logger.info("=" * 60)

        self.progress_updated.emit(100, "✅ Fertig!")
        self.finished.emit(
            True,
            f"Multi-Surface Berechnung erfolgreich abgeschlossen!\n\n"
            f"📦 GeoPackage: {gpkg_path.name}\n"
            f"📄 Bericht: {report_path.name}\n"
            f"📏 Optimale Kranstellflächen-Höhe: {optimal_crane_height:.2f} m ü.NN\n"
            f"📐 FOK: {project.fok:.2f} m ü.NN\n"
            f"📊 Gesamterdmasse bewegt: {results.total_volume_moved:.0f} m³\n\n"
            f"Alle Dateien in: {workspace}"
        )

    def _create_memory_layers(self, project, profiles, crs):
        """Create memory layers for all surfaces for map rendering.

        Args:
            project: MultiSurfaceProject with all surface geometries
            profiles: List of profile dictionaries with geometry
            crs: Coordinate reference system

        Returns:
            Dict with layer names as keys and QgsVectorLayer as values
        """
        layers = {}

        # Crane pad layer (Kranstellfläche) - Black outline, no fill
        crane_layer = QgsVectorLayer(
            f"Polygon?crs={crs.authid()}", "Kranstellfläche", "memory"
        )
        crane_prov = crane_layer.dataProvider()
        crane_feat = QgsFeature()
        crane_feat.setGeometry(project.crane_pad.geometry)
        crane_prov.addFeatures([crane_feat])
        crane_layer.updateExtents()

        # Thin black outline, no fill
        crane_symbol = QgsFillSymbol.createSimple({
            'color': '0,0,0,0',  # Transparent fill
            'style': 'no',
            'outline_color': '0,0,0,255',
            'outline_width': '0.3'  # Reduced from 0.5
        })
        crane_layer.renderer().setSymbol(crane_symbol)
        layers['crane_pad'] = crane_layer

        # Foundation layer (Fundament) - Red outline
        if project.foundation and project.foundation.geometry:
            foundation_layer = QgsVectorLayer(
                f"Polygon?crs={crs.authid()}", "Fundament", "memory"
            )
            foundation_prov = foundation_layer.dataProvider()
            foundation_feat = QgsFeature()
            foundation_feat.setGeometry(project.foundation.geometry)
            foundation_prov.addFeatures([foundation_feat])
            foundation_layer.updateExtents()

            foundation_symbol = QgsFillSymbol.createSimple({
                'color': '255,0,0,30',  # Light red transparent fill
                'style': 'solid',
                'outline_color': '255,0,0,255',  # Red outline
                'outline_width': '0.3'
            })
            foundation_layer.renderer().setSymbol(foundation_symbol)
            layers['foundation'] = foundation_layer

        # Boom surface layer (Auslegerfläche) - Orange outline
        if project.boom and project.boom.geometry:
            boom_layer = QgsVectorLayer(
                f"Polygon?crs={crs.authid()}", "Auslegerfläche", "memory"
            )
            boom_prov = boom_layer.dataProvider()
            boom_feat = QgsFeature()
            boom_feat.setGeometry(project.boom.geometry)
            boom_prov.addFeatures([boom_feat])
            boom_layer.updateExtents()

            boom_symbol = QgsFillSymbol.createSimple({
                'color': '255,165,0,30',  # Light orange transparent fill
                'style': 'solid',
                'outline_color': '255,165,0,255',  # Orange outline
                'outline_width': '0.3'
            })
            boom_layer.renderer().setSymbol(boom_symbol)
            layers['boom'] = boom_layer

        # Rotor storage layer (Blattlagerfläche) - Green outline
        if project.rotor_storage and project.rotor_storage.geometry:
            rotor_layer = QgsVectorLayer(
                f"Polygon?crs={crs.authid()}", "Blattlagerfläche", "memory"
            )
            rotor_prov = rotor_layer.dataProvider()
            rotor_feat = QgsFeature()
            rotor_feat.setGeometry(project.rotor_storage.geometry)
            rotor_prov.addFeatures([rotor_feat])
            rotor_layer.updateExtents()

            rotor_symbol = QgsFillSymbol.createSimple({
                'color': '0,255,0,30',  # Light green transparent fill
                'style': 'solid',
                'outline_color': '0,128,0,255',  # Dark green outline
                'outline_width': '0.3'
            })
            rotor_layer.renderer().setSymbol(rotor_symbol)
            layers['rotor_storage'] = rotor_layer

        # Road access layer (Zufahrtsstraße) - Blue outline
        if project.road_access and project.road_access.geometry:
            road_layer = QgsVectorLayer(
                f"Polygon?crs={crs.authid()}", "Zufahrtsstraße", "memory"
            )
            road_prov = road_layer.dataProvider()
            road_feat = QgsFeature()
            road_feat.setGeometry(project.road_access.geometry)
            road_prov.addFeatures([road_feat])
            road_layer.updateExtents()

            road_symbol = QgsFillSymbol.createSimple({
                'color': '0,102,204,30',  # Light blue transparent fill
                'style': 'solid',
                'outline_color': '0,102,204,255',  # Blue outline
                'outline_width': '0.3'
            })
            road_layer.renderer().setSymbol(road_symbol)
            layers['road_access'] = road_layer

        # Profile lines layer - Thin gray lines with labels
        profile_lines_layer = QgsVectorLayer(
            f"LineString?crs={crs.authid()}&field=name:string(50)", "Geländeschnitte", "memory"
        )
        profile_lines_prov = profile_lines_layer.dataProvider()
        profile_features = []
        for profile in profiles:
            feat = QgsFeature()
            feat.setGeometry(profile['geometry'])
            # Set the profile name/type as attribute
            feat.setAttributes([profile.get('type', '')])
            profile_features.append(feat)
        profile_lines_prov.addFeatures(profile_features)
        profile_lines_layer.updateExtents()

        # Thin gray lines for better visibility on aerial/OSM
        line_symbol = QgsLineSymbol.createSimple({
            'color': '128,128,128,200',  # Gray with slight transparency
            'width': '0.2'  # Reduced from 0.8
        })
        profile_lines_layer.renderer().setSymbol(line_symbol)

        # Add labels with white halo - positioned at start of line
        label_settings = QgsPalLayerSettings()
        label_settings.fieldName = 'name'
        label_settings.placement = QgsPalLayerSettings.Line
        label_settings.placementFlags = QgsPalLayerSettings.AboveLine

        # Position label at start of line by using a small repeat distance
        # and limiting to one label per feature
        label_settings.repeatDistance = 0
        label_settings.overrunDistance = 0
        label_settings.labelPerPart = False

        # Use priority to place at start (lower distance from start)
        label_settings.priority = 5

        # Offset to position outside the main area
        label_settings.dist = 1.5  # Distance from line in mm

        # Text format - smaller font (5pt instead of 7pt)
        text_format = QgsTextFormat()
        text_format.setFont(QFont('Arial', 5))
        text_format.setSize(5)
        text_format.setColor(QColor(0, 0, 0))  # Black text

        # White halo/buffer around text (smaller buffer for smaller text)
        buffer_settings = QgsTextBufferSettings()
        buffer_settings.setEnabled(True)
        buffer_settings.setSize(0.8)
        buffer_settings.setColor(QColor(255, 255, 255))  # White buffer
        buffer_settings.setOpacity(0.9)
        text_format.setBuffer(buffer_settings)

        label_settings.setFormat(text_format)

        # Apply labeling
        labeling = QgsVectorLayerSimpleLabeling(label_settings)
        profile_lines_layer.setLabeling(labeling)
        profile_lines_layer.setLabelsEnabled(True)

        layers['profile_lines'] = profile_lines_layer

        return layers

    def _save_to_geopackage(self, gpkg_path, project: MultiSurfaceProject,
                           profiles, dem_path, optimal_crane_height, results):
        """Save all data to single GeoPackage."""
        crs = QgsCoordinateReferenceSystem('EPSG:25832')
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'GPKG'
        options.fileEncoding = 'UTF-8'

        # Layer 1: kranstellflaechen (Polygon)
        fields_crane = QgsFields()
        fields_crane.append(QgsField('id', QVariant.Int))
        fields_crane.append(QgsField('optimal_height', QVariant.Double))
        fields_crane.append(QgsField('fok', QVariant.Double))
        fields_crane.append(QgsField('area_m2', QVariant.Double))
        fields_crane.append(QgsField('total_cut', QVariant.Double))
        fields_crane.append(QgsField('total_fill', QVariant.Double))

        feat_crane = QgsFeature(fields_crane)
        feat_crane.setGeometry(project.crane_pad.geometry)
        feat_crane.setAttribute('id', 1)
        feat_crane.setAttribute('optimal_height', float(optimal_crane_height))
        feat_crane.setAttribute('fok', float(project.fok))
        feat_crane.setAttribute('area_m2', float(project.crane_pad.geometry.area()))
        feat_crane.setAttribute('total_cut', float(results.total_cut))
        feat_crane.setAttribute('total_fill', float(results.total_fill))

        options.layerName = 'kranstellflaechen'
        writer = QgsVectorFileWriter.create(
            gpkg_path, fields_crane, QgsWkbTypes.Polygon, crs,
            QgsCoordinateTransformContext(), options
        )
        writer.addFeature(feat_crane)
        del writer

        # Layer 2: fundamentflaechen (Polygon)
        fields_foundation = QgsFields()
        fields_foundation.append(QgsField('id', QVariant.Int))
        fields_foundation.append(QgsField('fok', QVariant.Double))
        fields_foundation.append(QgsField('depth', QVariant.Double))
        fields_foundation.append(QgsField('area_m2', QVariant.Double))

        feat_foundation = QgsFeature(fields_foundation)
        feat_foundation.setGeometry(project.foundation.geometry)
        feat_foundation.setAttribute('id', 1)
        feat_foundation.setAttribute('fok', float(project.fok))
        feat_foundation.setAttribute('depth', float(project.foundation_depth))
        feat_foundation.setAttribute('area_m2', float(project.foundation.geometry.area()))

        options.layerName = 'fundamentflaechen'
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        writer = QgsVectorFileWriter.create(
            gpkg_path, fields_foundation, QgsWkbTypes.Polygon, crs,
            QgsCoordinateTransformContext(), options
        )
        writer.addFeature(feat_foundation)
        del writer

        # Layer 3: auslegerflaechen (Polygon) - optional
        if project.boom:
            fields_boom = QgsFields()
            fields_boom.append(QgsField('id', QVariant.Int))
            fields_boom.append(QgsField('slope_percent', QVariant.Double))
            fields_boom.append(QgsField('area_m2', QVariant.Double))

            feat_boom = QgsFeature(fields_boom)
            feat_boom.setGeometry(project.boom.geometry)
            feat_boom.setAttribute('id', 1)
            feat_boom.setAttribute('slope_percent', float(project.boom.slope_longitudinal))
            feat_boom.setAttribute('area_m2', float(project.boom.geometry.area()))

            options.layerName = 'auslegerflaechen'
            writer = QgsVectorFileWriter.create(
                gpkg_path, fields_boom, QgsWkbTypes.Polygon, crs,
                QgsCoordinateTransformContext(), options
            )
            writer.addFeature(feat_boom)
            del writer

        # Layer 4: rotorflaechen (Polygon) - optional
        if project.rotor_storage:
            fields_rotor = QgsFields()
            fields_rotor.append(QgsField('id', QVariant.Int))
            fields_rotor.append(QgsField('height_offset', QVariant.Double))
            fields_rotor.append(QgsField('area_m2', QVariant.Double))

            feat_rotor = QgsFeature(fields_rotor)
            feat_rotor.setGeometry(project.rotor_storage.geometry)
            feat_rotor.setAttribute('id', 1)
            feat_rotor.setAttribute('height_offset', float(project.rotor_height_offset))
            feat_rotor.setAttribute('area_m2', float(project.rotor_storage.geometry.area()))

            options.layerName = 'rotorflaechen'
            writer = QgsVectorFileWriter.create(
                gpkg_path, fields_rotor, QgsWkbTypes.Polygon, crs,
                QgsCoordinateTransformContext(), options
            )
            writer.addFeature(feat_rotor)
            del writer

        # Layer 5: zufahrtflaechen (Polygon) - optional
        if project.road_access:
            fields_road = QgsFields()
            fields_road.append(QgsField('id', QVariant.Int))
            fields_road.append(QgsField('slope_percent', QVariant.Double))
            fields_road.append(QgsField('gravel_thickness', QVariant.Double))
            fields_road.append(QgsField('area_m2', QVariant.Double))

            feat_road = QgsFeature(fields_road)
            feat_road.setGeometry(project.road_access.geometry)
            feat_road.setAttribute('id', 1)
            feat_road.setAttribute('slope_percent', float(project.road_slope_percent))
            feat_road.setAttribute('gravel_thickness', float(project.road_gravel_thickness) if project.road_gravel_enabled else 0.0)
            feat_road.setAttribute('area_m2', float(project.road_access.geometry.area()))

            options.layerName = 'zufahrtflaechen'
            writer = QgsVectorFileWriter.create(
                gpkg_path, fields_road, QgsWkbTypes.Polygon, crs,
                QgsCoordinateTransformContext(), options
            )
            writer.addFeature(feat_road)
            del writer

        # Layer 6: schnitte (LineString)
        fields_lines = QgsFields()
        fields_lines.append(QgsField('id', QVariant.Int))
        fields_lines.append(QgsField('type', QVariant.String))
        fields_lines.append(QgsField('length_m', QVariant.Double))

        options.layerName = 'schnitte'
        writer = QgsVectorFileWriter.create(
            gpkg_path, fields_lines, QgsWkbTypes.LineString, crs,
            QgsCoordinateTransformContext(), options
        )

        for i, profile in enumerate(profiles):
            feat_line = QgsFeature(fields_lines)
            feat_line.setGeometry(profile['geometry'])
            feat_line.setAttribute('id', i + 1)
            feat_line.setAttribute('type', profile['type'])
            feat_line.setAttribute('length_m', float(profile['length']))
            writer.addFeature(feat_line)

        del writer

        # === 3D LAYERS ===
        # Layer 6: kranstellflaechen_3d (PolygonZ)
        if SurfaceType.CRANE_PAD in results.surface_results:
            crane_result = results.surface_results[SurfaceType.CRANE_PAD]
            if crane_result.geometry_3d and not crane_result.geometry_3d.isEmpty():
                fields_crane_3d = QgsFields()
                fields_crane_3d.append(QgsField('id', QVariant.Int))
                fields_crane_3d.append(QgsField('height', QVariant.Double))
                fields_crane_3d.append(QgsField('surface_type', QVariant.String))

                feat_crane_3d = QgsFeature(fields_crane_3d)
                feat_crane_3d.setGeometry(crane_result.geometry_3d)
                feat_crane_3d.setAttribute('id', 1)
                feat_crane_3d.setAttribute('height', float(crane_result.target_height))
                feat_crane_3d.setAttribute('surface_type', 'kranstellflaeche')

                options.layerName = 'kranstellflaechen_3d'
                writer = QgsVectorFileWriter.create(
                    gpkg_path, fields_crane_3d, QgsWkbTypes.PolygonZ, crs,
                    QgsCoordinateTransformContext(), options
                )
                writer.addFeature(feat_crane_3d)
                del writer

        # Layer 7: fundamentflaechen_3d (PolygonZ)
        if SurfaceType.FOUNDATION in results.surface_results:
            foundation_result = results.surface_results[SurfaceType.FOUNDATION]
            if foundation_result.geometry_3d and not foundation_result.geometry_3d.isEmpty():
                fields_foundation_3d = QgsFields()
                fields_foundation_3d.append(QgsField('id', QVariant.Int))
                fields_foundation_3d.append(QgsField('height', QVariant.Double))
                fields_foundation_3d.append(QgsField('surface_type', QVariant.String))

                feat_foundation_3d = QgsFeature(fields_foundation_3d)
                feat_foundation_3d.setGeometry(foundation_result.geometry_3d)
                feat_foundation_3d.setAttribute('id', 1)
                feat_foundation_3d.setAttribute('height', float(foundation_result.target_height))
                feat_foundation_3d.setAttribute('surface_type', 'fundamentflaeche')

                options.layerName = 'fundamentflaechen_3d'
                writer = QgsVectorFileWriter.create(
                    gpkg_path, fields_foundation_3d, QgsWkbTypes.PolygonZ, crs,
                    QgsCoordinateTransformContext(), options
                )
                writer.addFeature(feat_foundation_3d)
                del writer

        # Layer 8: auslegerflaechen_3d (PolygonZ) - optional
        if project.boom and SurfaceType.BOOM in results.surface_results:
            boom_result = results.surface_results[SurfaceType.BOOM]
            if boom_result.geometry_3d and not boom_result.geometry_3d.isEmpty():
                fields_boom_3d = QgsFields()
                fields_boom_3d.append(QgsField('id', QVariant.Int))
                fields_boom_3d.append(QgsField('height', QVariant.Double))
                fields_boom_3d.append(QgsField('slope_percent', QVariant.Double))
                fields_boom_3d.append(QgsField('surface_type', QVariant.String))

                feat_boom_3d = QgsFeature(fields_boom_3d)
                feat_boom_3d.setGeometry(boom_result.geometry_3d)
                feat_boom_3d.setAttribute('id', 1)
                feat_boom_3d.setAttribute('height', float(boom_result.target_height))
                feat_boom_3d.setAttribute('slope_percent', float(results.boom_slope_percent))
                feat_boom_3d.setAttribute('surface_type', 'auslegerflaeche')

                options.layerName = 'auslegerflaechen_3d'
                writer = QgsVectorFileWriter.create(
                    gpkg_path, fields_boom_3d, QgsWkbTypes.PolygonZ, crs,
                    QgsCoordinateTransformContext(), options
                )
                writer.addFeature(feat_boom_3d)
                del writer

        # Layer 9: rotorflaechen_3d (PolygonZ) - optional
        if project.rotor_storage and SurfaceType.ROTOR_STORAGE in results.surface_results:
            rotor_result = results.surface_results[SurfaceType.ROTOR_STORAGE]
            if rotor_result.geometry_3d and not rotor_result.geometry_3d.isEmpty():
                fields_rotor_3d = QgsFields()
                fields_rotor_3d.append(QgsField('id', QVariant.Int))
                fields_rotor_3d.append(QgsField('height', QVariant.Double))
                fields_rotor_3d.append(QgsField('height_offset', QVariant.Double))
                fields_rotor_3d.append(QgsField('surface_type', QVariant.String))

                feat_rotor_3d = QgsFeature(fields_rotor_3d)
                feat_rotor_3d.setGeometry(rotor_result.geometry_3d)
                feat_rotor_3d.setAttribute('id', 1)
                feat_rotor_3d.setAttribute('height', float(rotor_result.target_height))
                feat_rotor_3d.setAttribute('height_offset', float(results.rotor_height_offset_optimized))
                feat_rotor_3d.setAttribute('surface_type', 'rotorflaeche')

                options.layerName = 'rotorflaechen_3d'
                writer = QgsVectorFileWriter.create(
                    gpkg_path, fields_rotor_3d, QgsWkbTypes.PolygonZ, crs,
                    QgsCoordinateTransformContext(), options
                )
                writer.addFeature(feat_rotor_3d)
                del writer

        # Layer 10: zufahrtflaechen_3d (PolygonZ) - optional
        if project.road_access and SurfaceType.ROAD_ACCESS in results.surface_results:
            road_result = results.surface_results[SurfaceType.ROAD_ACCESS]
            if road_result.geometry_3d and not road_result.geometry_3d.isEmpty():
                fields_road_3d = QgsFields()
                fields_road_3d.append(QgsField('id', QVariant.Int))
                fields_road_3d.append(QgsField('height', QVariant.Double))
                fields_road_3d.append(QgsField('slope_percent', QVariant.Double))
                fields_road_3d.append(QgsField('gravel_thickness', QVariant.Double))
                fields_road_3d.append(QgsField('surface_type', QVariant.String))

                feat_road_3d = QgsFeature(fields_road_3d)
                feat_road_3d.setGeometry(road_result.geometry_3d)
                feat_road_3d.setAttribute('id', 1)
                feat_road_3d.setAttribute('height', float(road_result.target_height))
                feat_road_3d.setAttribute('slope_percent', float(results.road_slope_percent))
                feat_road_3d.setAttribute('gravel_thickness', float(project.road_gravel_thickness) if project.road_gravel_enabled else 0.0)
                feat_road_3d.setAttribute('surface_type', 'zufahrtflaeche')

                options.layerName = 'zufahrtflaechen_3d'
                writer = QgsVectorFileWriter.create(
                    gpkg_path, fields_road_3d, QgsWkbTypes.PolygonZ, crs,
                    QgsCoordinateTransformContext(), options
                )
                writer.addFeature(feat_road_3d)
                del writer

        # Layer 11: boeschungen_3d (MultiPolygonZ) - slope surfaces
        # Collect all slope geometries
        slope_geometries = []
        for surface_type, surface_result in results.surface_results.items():
            if surface_result.slope_geometry_3d and not surface_result.slope_geometry_3d.isEmpty():
                slope_geometries.append((surface_type.value, surface_result.slope_geometry_3d))

        if slope_geometries:
            fields_slope_3d = QgsFields()
            fields_slope_3d.append(QgsField('id', QVariant.Int))
            fields_slope_3d.append(QgsField('surface_type', QVariant.String))

            options.layerName = 'boeschungen_3d'
            writer = QgsVectorFileWriter.create(
                gpkg_path, fields_slope_3d, QgsWkbTypes.MultiPolygonZ, crs,
                QgsCoordinateTransformContext(), options
            )

            for i, (surface_name, slope_geom) in enumerate(slope_geometries):
                feat_slope = QgsFeature(fields_slope_3d)
                feat_slope.setGeometry(slope_geom)
                feat_slope.setAttribute('id', i + 1)
                feat_slope.setAttribute('surface_type', surface_name)
                writer.addFeature(feat_slope)

            del writer

        self.logger.info(f"GeoPackage saved with 2D layers, 3D layers, and profiles: {gpkg_path}")

    def _add_to_qgis(self, gpkg_path, report_path, dem_path=None, dxf_paths=None, group_name=None):
        """Add all result layers to QGIS project in a layer group.

        Args:
            gpkg_path: Path to the GeoPackage with result layers
            report_path: Path to the HTML report
            dem_path: Path to the DEM mosaic GeoTIFF
            dxf_paths: Dict with DXF file paths {type: path}
            group_name: Name for the layer group (usually workspace folder name)
        """
        project = QgsProject.instance()
        root = project.layerTreeRoot()

        # Create layer group
        if group_name:
            group = root.insertGroup(0, group_name)
            self.logger.info(f"Created layer group: {group_name}")
        else:
            group = root

        # Layer order in QGIS: first added = top in layer panel (rendered on top)
        # Desired order from bottom to top: DEM -> Polygons -> Lines
        # So we add: Lines first, then Polygons, then DEM last

        # === TOP: Add line layers first (will be at top) ===
        # Add profile lines (topmost layer)
        profile_layer = QgsVectorLayer(
            f"{gpkg_path}|layername=schnitte",
            "Geländeschnitte",
            "ogr"
        )
        if profile_layer.isValid():
            project.addMapLayer(profile_layer, False)
            if group_name:
                group.addLayer(profile_layer)
            else:
                root.addLayer(profile_layer)
            self.logger.info("Added layer: Geländeschnitte")

        # Add DXF layers
        if dxf_paths:
            dxf_display_names = {
                'crane': 'DXF Kranstellfläche',
                'foundation': 'DXF Fundament',
                'boom': 'DXF Ausleger',
                'rotor': 'DXF Blattlager',
                'road': 'DXF Zufahrtsstraße'
            }

            for dxf_type, dxf_path in dxf_paths.items():
                if dxf_path and os.path.exists(dxf_path):
                    display_name = dxf_display_names.get(dxf_type, f'DXF {dxf_type}')
                    # Load DXF as vector layer (entities sublayer)
                    dxf_layer = QgsVectorLayer(
                        f"{dxf_path}|layername=entities",
                        display_name,
                        "ogr"
                    )
                    if dxf_layer.isValid():
                        project.addMapLayer(dxf_layer, False)
                        if group_name:
                            group.addLayer(dxf_layer)
                        else:
                            root.addLayer(dxf_layer)
                        self.logger.info(f"Added DXF layer: {display_name}")
                    else:
                        self.logger.warning(f"Could not load DXF layer: {dxf_path}")

        # === MIDDLE: Add polygon layers ===
        # GeoPackage polygon layer names (order: top to bottom within polygons)
        gpkg_polygon_layers = [
            ('fundamentflaechen', 'Fundamentflächen'),
            ('kranstellflaechen', 'Kranstellflächen'),
            ('auslegerflaechen', 'Auslegerflächen'),
            ('rotorflaechen', 'Blattlagerflächen'),
            ('zufahrtflaechen', 'Zufahrtsflächen'),
        ]

        for layer_name, display_name in gpkg_polygon_layers:
            layer = QgsVectorLayer(
                f"{gpkg_path}|layername={layer_name}",
                display_name,
                "ogr"
            )
            if layer.isValid():
                project.addMapLayer(layer, False)  # Don't add to legend yet
                if group_name:
                    group.addLayer(layer)
                else:
                    root.addLayer(layer)
                self.logger.info(f"Added layer: {display_name}")

        # === BOTTOM: Add DEM mosaic layer last (will be at bottom) ===
        if dem_path:
            dem_layer = QgsRasterLayer(dem_path, "DGM Mosaik")
            if dem_layer.isValid():
                project.addMapLayer(dem_layer, False)
                if group_name:
                    group.addLayer(dem_layer)
                else:
                    root.addLayer(dem_layer)
                self.logger.info(f"Added DEM layer: {dem_path}")
            else:
                self.logger.warning(f"Could not load DEM layer: {dem_path}")

        self.logger.info("All layers added to QGIS project")


class WorkflowRunner(QObject):
    """
    Orchestrates the multi-surface workflow execution in a separate thread.
    """

    def __init__(self, iface, params, dialog):
        """
        Initialize workflow runner.

        Args:
            iface: QGIS interface
            params (dict): Parameters from dialog
            dialog: Main dialog for progress updates
        """
        super().__init__()
        self.iface = iface
        self.params = params
        self.dialog = dialog
        self.logger = get_plugin_logger()

        self.thread = None
        self.worker = None

    def start(self):
        """Start the workflow in a separate thread."""
        self.logger.info("Starting multi-surface workflow in separate thread...")

        # Create thread and worker
        self.thread = QThread()
        self.worker = WorkflowWorker(self.iface, self.params)
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.worker.progress_updated.connect(self.dialog.update_progress)
        self.worker.finished.connect(self._on_finished)
        self.thread.started.connect(self.worker.run)

        # Start thread
        self.thread.start()

    def _on_finished(self, success, message):
        """Handle workflow finished."""
        # Clean up thread
        if self.thread:
            self.thread.quit()
            self.thread.wait()

        # Forward to dialog
        self.dialog.processing_finished(success, message)
