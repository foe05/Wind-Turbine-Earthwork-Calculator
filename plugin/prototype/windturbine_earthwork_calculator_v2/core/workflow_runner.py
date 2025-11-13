"""
Workflow Runner for Wind Turbine Earthwork Calculator V2

Orchestrates the complete workflow from DXF import to report generation.

Author: Wind Energy Site Planning  
Version: 2.0
"""

import os
from pathlib import Path
from datetime import datetime

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
from .earthwork_calculator import EarthworkCalculator
from .profile_generator import ProfileGenerator
from .report_generator import ReportGenerator
from ..utils.geometry_utils import get_centroid
from ..utils.logging_utils import get_plugin_logger


class WorkflowWorker(QObject):
    """
    Worker class that runs in a separate thread.
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
            self.logger.info("WORKFLOW GESTARTET")
            self.logger.info("=" * 60)
            self._run_workflow()
        except Exception as e:
            self.logger.error(f"Workflow failed: {e}", exc_info=True)
            self.finished.emit(False, f"Fehler: {str(e)}")
    
    def cancel(self):
        """Cancel workflow."""
        self.is_cancelled = True


    def _run_workflow(self):
        """Run the complete workflow."""
        import tempfile
        
        self.logger.info("Starting workflow execution...")
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
        
        self.logger.info(f"Directories created: {results_dir}, {profiles_dir}, {cache_dir}")
        
        # === STEP 1: DXF Import ===
        self.progress_updated.emit(10, "📂 DXF-Datei wird importiert...")
        self.logger.info(f"Importing DXF: {self.params['dxf_file']}")
        
        try:
            importer = DXFImporter(
                self.params['dxf_file'],
                tolerance=self.params['dxf_tolerance']
            )
            polygon, metadata = importer.import_as_polygon()
            
            if not polygon or polygon.isEmpty():
                raise Exception("Keine gültige Plattform-Geometrie im DXF gefunden")
            
            self.logger.info(f"DXF imported: {metadata}")
            self.progress_updated.emit(15, f"✓ Polygon: {metadata['num_vertices']} Punkte, {metadata['area']:.2f} m²")
        except Exception as e:
            self.logger.error(f"DXF Import failed: {e}", exc_info=True)
            raise
        
        # Get centroid for naming
        centroid = get_centroid(polygon)
        x_coord = int(centroid.x())
        y_coord = int(centroid.y())
        
        # === STEP 2: DEM Download ===
        self.progress_updated.emit(20, "🌍 DEM-Daten werden heruntergeladen...")
        self.logger.info(f"Starting DEM download, cache_dir: {cache_dir}")
        
        try:
            # Create temporary DEM file
            temp_dem_path = tempfile.mktemp(suffix='.tif', prefix='dem_mosaic_')
            self.logger.info(f"Temp DEM path: {temp_dem_path}")
            
            downloader = DEMDownloader(
                cache_dir=str(cache_dir),
                force_refresh=self.params['force_refresh']
            )
            
            self.progress_updated.emit(25, "⬇️ Lade DEM-Kacheln...")
            dem_path = downloader.download_for_geometry(
                polygon,
                temp_dem_path,
                buffer_m=250
            )
            
            self.logger.info(f"DEM downloaded: {dem_path}")
            
            dem_layer = QgsRasterLayer(dem_path, "DGM Mosaik")
            if not dem_layer.isValid():
                raise Exception(f"DEM konnte nicht geladen werden: {dem_path}")
            
            self.progress_updated.emit(40, "✓ DGM-Mosaik erstellt")
        except Exception as e:
            self.logger.error(f"DEM Download failed: {e}", exc_info=True)
            raise
        
        # === STEP 3: Optimization ===
        self.progress_updated.emit(45, "⚙️ Optimale Plattformhöhe wird berechnet...")
        self.logger.info(f"Starting optimization: {self.params['min_height']:.1f} - {self.params['max_height']:.1f} m")
        
        try:
            config = {
                'slope_angle': self.params['slope_angle']
            }
            
            calculator = EarthworkCalculator(dem_layer, polygon, config)
            optimal_height, results = calculator.find_optimum(
                self.params['min_height'],
                self.params['max_height'],
                self.params['height_step']
            )
            
            self.logger.info(f"Optimization complete: {optimal_height:.2f} m ü.NN")
            self.logger.info(f"Results: Cut={results.get('total_cut', 0):.0f} m³, Fill={results.get('total_fill', 0):.0f} m³")
            self.progress_updated.emit(60, f"✓ Optimale Höhe: {optimal_height:.2f} m ü.NN")
        except Exception as e:
            self.logger.error(f"Optimization failed: {e}", exc_info=True)
            raise
        
        # === STEP 4: Profile Generation ===
        self.progress_updated.emit(65, "📊 Geländeschnitte werden erstellt...")
        self.logger.info(f"Generating profiles in: {profiles_dir}")

        try:
            profile_gen = ProfileGenerator(dem_layer, polygon, optimal_height)
            all_profiles = []

            # Generate cross-section profiles if enabled
            if self.params.get('generate_cross_profiles', True):
                self.logger.info("Generating cross-section profiles...")
                self.progress_updated.emit(67, "📊 Querprofile werden erstellt...")

                cross_profiles = profile_gen.generate_all_profiles(
                    output_dir=str(profiles_dir),
                    spacing=self.params.get('cross_profile_spacing', 10.0),
                    overhang_percent=self.params.get('cross_profile_overhang', 10.0),
                    vertical_exaggeration=self.params['vertical_exaggeration'],
                    volume_info=results
                )
                all_profiles.extend(cross_profiles)
                self.logger.info(f"Generated {len(cross_profiles)} cross-section profiles")

            # Generate longitudinal profiles if enabled
            if self.params.get('generate_long_profiles', True):
                self.logger.info("Generating longitudinal profiles...")
                self.progress_updated.emit(72, "📊 Längsprofile werden erstellt...")

                long_profiles = profile_gen.generate_all_longitudinal_profiles(
                    output_dir=str(profiles_dir),
                    spacing=self.params.get('long_profile_spacing', 10.0),
                    overhang_percent=self.params.get('long_profile_overhang', 10.0),
                    vertical_exaggeration=self.params['vertical_exaggeration'],
                    volume_info=results
                )
                all_profiles.extend(long_profiles)
                self.logger.info(f"Generated {len(long_profiles)} longitudinal profiles")

            profiles = all_profiles
            profile_pngs = [p['png_path'] for p in profiles if 'png_path' in p]
            self.logger.info(f"Total: Generated {len(profile_pngs)} profile images")
            self.progress_updated.emit(75, f"✓ {len(profiles)} Geländeschnitte erstellt")
        except Exception as e:
            self.logger.error(f"Profile generation failed: {e}", exc_info=True)
            raise
        
        # === STEP 5: Report Generation ===
        self.progress_updated.emit(80, "📝 HTML-Bericht wird erstellt...")
        self.logger.info("Generating HTML report")
        
        # Create memory layers for overview map
        platform_layer, profile_lines_layer = self._create_memory_layers(
            polygon, profiles, dem_layer.crs()
        )
        
        # Generate filename
        gpkg_name = f"WKA_{x_coord}_{y_coord}.gpkg"
        gpkg_path = results_dir / gpkg_name
        report_path = results_dir / f"WKA_{x_coord}_{y_coord}_Bericht.html"
        
        # Prepare results dict for report (add optimal_height)
        results_for_report = results.copy()
        results_for_report['platform_height'] = optimal_height
        
        # Generate report
        report_config = {
            'slope_angle': self.params['slope_angle'],
            'generate_cross_profiles': self.params.get('generate_cross_profiles', True),
            'cross_profile_spacing': self.params.get('cross_profile_spacing', 10.0),
            'generate_long_profiles': self.params.get('generate_long_profiles', True),
            'long_profile_spacing': self.params.get('long_profile_spacing', 10.0)
        }
        
        report_gen = ReportGenerator(
            results_for_report, polygon, dem_layer,
            platform_layer=platform_layer,
            profile_lines_layer=profile_lines_layer
        )
        report_gen.generate_html(
            str(report_path), profile_pngs, report_config,
            profiles_dir=str(profiles_dir)
        )
        
        # === STEP 6: Save to GeoPackage ===
        self.progress_updated.emit(85, "💾 Daten werden in GeoPackage gespeichert...")
        self.logger.info(f"Saving to GeoPackage: {gpkg_path}")
        
        self._save_to_geopackage(
            str(gpkg_path),
            polygon,
            profiles,
            dem_path,
            optimal_height,
            results
        )
        
        # === STEP 7: Add to QGIS ===
        self.progress_updated.emit(95, "🗺️ Layer werden zu QGIS hinzugefügt...")
        self.logger.info("Adding layers to QGIS project")
        
        try:
            self._add_to_qgis(str(gpkg_path), str(report_path))
        except Exception as e:
            self.logger.warning(f"Could not add layers to QGIS: {e}")
        
        # Finished
        self.logger.info("=" * 60)
        self.logger.info("WORKFLOW ABGESCHLOSSEN")
        self.logger.info("=" * 60)
        
        self.progress_updated.emit(100, "✅ Fertig!")
        self.finished.emit(
            True,
            f"Berechnung erfolgreich abgeschlossen!\n\n"
            f"📦 GeoPackage: {gpkg_path.name}\n"
            f"📄 Bericht: {report_path.name}\n"
            f"📏 Optimale Höhe: {optimal_height:.2f} m ü.NN\n\n"
            f"Alle Dateien in: {workspace}"
        )
    
    def _create_memory_layers(self, polygon, profiles, crs):
        """Create memory layers for map rendering."""
        # Platform layer
        platform_layer = QgsVectorLayer(
            f"Polygon?crs={crs.authid()}", "Plattform", "memory"
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
    
    def _save_to_geopackage(self, gpkg_path, polygon, profiles, dem_path,
                           optimal_height, results):
        """Save all data to single GeoPackage."""
        crs = QgsCoordinateReferenceSystem('EPSG:25832')
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'GPKG'
        options.fileEncoding = 'UTF-8'
        
        # Layer 1: kranflaechen (Polygon)
        fields_polygon = QgsFields()
        fields_polygon.append(QgsField('id', QVariant.Int))
        fields_polygon.append(QgsField('optimal_height', QVariant.Double))
        fields_polygon.append(QgsField('area_m2', QVariant.Double))
        fields_polygon.append(QgsField('total_cut', QVariant.Double))
        fields_polygon.append(QgsField('total_fill', QVariant.Double))
        
        feat_polygon = QgsFeature(fields_polygon)
        feat_polygon.setGeometry(polygon)
        feat_polygon.setAttribute('id', 1)
        feat_polygon.setAttribute('optimal_height', float(optimal_height))
        feat_polygon.setAttribute('area_m2', float(polygon.area()))
        feat_polygon.setAttribute('total_cut', float(results['total_cut']))
        feat_polygon.setAttribute('total_fill', float(results['total_fill']))
        
        options.layerName = 'kranflaechen'
        writer = QgsVectorFileWriter.create(
            gpkg_path, fields_polygon, QgsWkbTypes.Polygon, crs,
            QgsCoordinateTransformContext(), options
        )
        writer.addFeature(feat_polygon)
        del writer
        
        # Layer 2: schnitte (LineString)
        fields_lines = QgsFields()
        fields_lines.append(QgsField('id', QVariant.Int))
        fields_lines.append(QgsField('type', QVariant.String))
        fields_lines.append(QgsField('length_m', QVariant.Double))
        
        options.layerName = 'schnitte'
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        
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
        
        self.logger.info(f"GeoPackage saved: {gpkg_path}")
    
    def _add_to_qgis(self, gpkg_path, report_path):
        """Add layers to QGIS project."""
        # Add polygon layer
        layer_polygon = QgsVectorLayer(
            f"{gpkg_path}|layername=kranflaechen",
            "Kranstellflächen",
            "ogr"
        )
        if layer_polygon.isValid():
            QgsProject.instance().addMapLayer(layer_polygon)
        
        # Add lines layer
        layer_lines = QgsVectorLayer(
            f"{gpkg_path}|layername=schnitte",
            "Geländeschnitte",
            "ogr"
        )
        if layer_lines.isValid():
            QgsProject.instance().addMapLayer(layer_lines)
        
        self.logger.info("Layers added to QGIS project")


class WorkflowRunner(QObject):
    """
    Orchestrates the workflow execution in a separate thread.
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
        self.logger.info("Starting workflow in separate thread...")
        
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
