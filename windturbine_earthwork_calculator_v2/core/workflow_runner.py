"""
Workflow Runner for Wind Turbine Earthwork Calculator V2 - Multi-Surface Edition

Orchestrates the complete workflow from multi-DXF import to report generation.

Author: Wind Energy Site Planning
Version: 2.0 - Multi-Surface Extension
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
    QgsVectorFileWriter
)
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

        # === STEP 1: Import all 4 DXF files ===
        self.progress_updated.emit(10, "📂 DXF-Dateien werden importiert...")
        self.logger.info("Importing 4 DXF files...")

        surfaces = {}
        dxf_files = [
            ('crane', 'dxf_crane', SurfaceType.CRANE_PAD, "Kranstellfläche"),
            ('foundation', 'dxf_foundation', SurfaceType.FOUNDATION, "Fundamentfläche"),
            ('boom', 'dxf_boom', SurfaceType.BOOM, "Auslegerfläche"),
            ('rotor', 'dxf_rotor', SurfaceType.ROTOR_STORAGE, "Blattlagerfläche"),
        ]

        progress_per_dxf = 5
        current_progress = 10

        for key, param_key, surface_type, display_name in dxf_files:
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

        self.progress_updated.emit(30, "✓ Alle DXF-Dateien importiert")

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

            rotor_config = SurfaceConfig(
                surface_type=SurfaceType.ROTOR_STORAGE,
                geometry=surfaces['rotor']['geometry'],
                dxf_path=surfaces['rotor']['dxf_path'],
                height_mode=HeightMode.RELATIVE,
                height_reference='crane',
                metadata=surfaces['rotor']['metadata']
            )

            # Create project
            project = MultiSurfaceProject(
                crane_pad=crane_config,
                foundation=foundation_config,
                boom=boom_config,
                rotor_storage=rotor_config,
                fok=self.params['fok'],
                foundation_depth=self.params['foundation_depth'],
                foundation_diameter=self.params.get('foundation_diameter'),
                gravel_thickness=self.params['gravel_thickness'],
                rotor_height_offset=self.params['rotor_height_offset'],
                slope_angle=self.params['slope_angle'],
                search_range_below_fok=self.params['search_range_below_fok'],
                search_range_above_fok=self.params['search_range_above_fok'],
                search_step=self.params['height_step']
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
            all_geoms = [
                surfaces['crane']['geometry'],
                surfaces['foundation']['geometry'],
                surfaces['boom']['geometry'],
                surfaces['rotor']['geometry']
            ]

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

        try:
            calculator = MultiSurfaceCalculator(dem_layer, project)

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
            # For now, we use the existing ProfileGenerator with crane pad
            # In a full implementation, this would need to be extended for multi-surface
            profile_gen = ProfileGenerator(
                dem_layer,
                project.crane_pad.geometry,
                optimal_crane_height
            )

            all_profiles = []

            # Generate cross-section profiles
            if self.params.get('generate_cross_profiles', True):
                self.logger.info("Generating cross-section profiles...")
                self.progress_updated.emit(74, "📊 Querprofile werden erstellt...")

                cross_profiles = profile_gen.generate_all_profiles(
                    output_dir=str(profiles_dir),
                    spacing=self.params.get('cross_profile_spacing', 10.0),
                    overhang_percent=self.params.get('cross_profile_overhang', 10.0),
                    vertical_exaggeration=self.params['vertical_exaggeration'],
                    volume_info=results.to_dict()
                )
                all_profiles.extend(cross_profiles)
                self.logger.info(f"Generated {len(cross_profiles)} cross-section profiles")

            # Generate longitudinal profiles
            if self.params.get('generate_long_profiles', True):
                self.logger.info("Generating longitudinal profiles...")
                self.progress_updated.emit(78, "📊 Längsprofile werden erstellt...")

                long_profiles = profile_gen.generate_all_longitudinal_profiles(
                    output_dir=str(profiles_dir),
                    spacing=self.params.get('long_profile_spacing', 10.0),
                    overhang_percent=self.params.get('long_profile_overhang', 10.0),
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

        # Create memory layers for overview map
        platform_layer, profile_lines_layer = self._create_memory_layers(
            project.crane_pad.geometry,
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
            platform_layer=platform_layer,
            profile_lines_layer=profile_lines_layer
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
            self._add_to_qgis(str(gpkg_path), str(report_path))
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

    def _create_memory_layers(self, polygon, profiles, crs):
        """Create memory layers for map rendering."""
        # Platform layer
        platform_layer = QgsVectorLayer(
            f"Polygon?crs={crs.authid()}", "Kranstellfläche", "memory"
        )
        platform_prov = platform_layer.dataProvider()
        platform_feat = QgsFeature()
        platform_feat.setGeometry(polygon)
        platform_prov.addFeatures([platform_feat])
        platform_layer.updateExtents()

        # Apply symbology
        symbol = QgsFillSymbol.createSimple({
            'color': '0,0,0,255',
            'style': 'dense4',
            'outline_color': '0,0,0,255',
            'outline_width': '0.5'
        })
        platform_layer.renderer().setSymbol(symbol)

        # Profile lines layer
        profile_lines_layer = QgsVectorLayer(
            f"LineString?crs={crs.authid()}", "Geländeschnitte", "memory"
        )
        profile_lines_prov = profile_lines_layer.dataProvider()
        profile_features = []
        for profile in profiles:
            feat = QgsFeature()
            feat.setGeometry(profile['geometry'])
            profile_features.append(feat)
        profile_lines_prov.addFeatures(profile_features)
        profile_lines_layer.updateExtents()

        # Apply symbology
        line_symbol = QgsLineSymbol.createSimple({
            'color': '255,255,255,255',
            'width': '0.8'
        })
        profile_lines_layer.renderer().setSymbol(line_symbol)

        return platform_layer, profile_lines_layer

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

        # Layer 3: auslegerflaechen (Polygon)
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

        # Layer 4: rotorflaechen (Polygon)
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

        # Layer 5: schnitte (LineString)
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

        self.logger.info(f"GeoPackage saved with 4 surface layers + profiles: {gpkg_path}")

    def _add_to_qgis(self, gpkg_path, report_path):
        """Add layers to QGIS project."""
        layer_names = [
            ('kranstellflaechen', 'Kranstellflächen'),
            ('fundamentflaechen', 'Fundamentflächen'),
            ('auslegerflaechen', 'Auslegerflächen'),
            ('rotorflaechen', 'Blattlagerflächen'),
            ('schnitte', 'Geländeschnitte'),
        ]

        for layer_name, display_name in layer_names:
            layer = QgsVectorLayer(
                f"{gpkg_path}|layername={layer_name}",
                display_name,
                "ogr"
            )
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                self.logger.info(f"Added layer: {display_name}")

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
