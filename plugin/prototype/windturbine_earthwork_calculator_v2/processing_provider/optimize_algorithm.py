"""
Main Processing Algorithm for Wind Turbine Earthwork Calculator V2

Optimizes platform height for wind turbine crane pads.

Author: Wind Energy Site Planning
Version: 2.0
"""

import os
import tempfile
from pathlib import Path

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterBoolean,
    QgsProcessingException,
    QgsFeature,
    QgsFeatureSink,
    QgsFields,
    QgsField,
    QgsWkbTypes,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsProject,
    QgsCoordinateReferenceSystem
)
from PyQt5.QtCore import QVariant
import processing

from ..core.dxf_importer import DXFImporter
from ..core.dem_downloader import DEMDownloader
from ..core.earthwork_calculator import EarthworkCalculator
from ..core.profile_generator import ProfileGenerator
from ..core.report_generator import ReportGenerator
from ..utils.validation import (
    validate_file_exists,
    validate_height_range,
    validate_output_path,
    ValidationError
)
from ..utils.logging_utils import get_plugin_logger
from ..utils.layer_styling import (
    load_dem_with_contours_to_map,
    create_vector_contours_with_labels,
    add_labels_to_profile_lines
)


class OptimizePlatformHeightAlgorithm(QgsProcessingAlgorithm):
    """
    Main algorithm for optimizing wind turbine platform height.

    This algorithm:
    1. Imports DXF file and creates platform polygon
    2. Downloads DEM data from hoehendaten.de
    3. Optimizes platform height to minimize earthwork
    4. Generates terrain profiles
    5. Creates comprehensive HTML report
    6. Saves all outputs to GeoPackage
    """

    # Parameter IDs
    INPUT_DXF = 'INPUT_DXF'
    MIN_HEIGHT = 'MIN_HEIGHT'
    MAX_HEIGHT = 'MAX_HEIGHT'
    HEIGHT_STEP = 'HEIGHT_STEP'
    OUTPUT_GPKG = 'OUTPUT_GPKG'
    OUTPUT_REPORT = 'OUTPUT_REPORT'

    # Advanced parameters
    FORCE_REFRESH = 'FORCE_REFRESH'
    DXF_TOLERANCE = 'DXF_TOLERANCE'
    SLOPE_ANGLE = 'SLOPE_ANGLE'
    PROFILE_SPACING = 'PROFILE_SPACING'
    PROFILE_OVERHANG = 'PROFILE_OVERHANG'
    VERTICAL_EXAGGERATION = 'VERTICAL_EXAGGERATION'

    # Outputs
    OUTPUT_POLYGON = 'OUTPUT_POLYGON'
    OUTPUT_PROFILES = 'OUTPUT_PROFILES'

    def __init__(self):
        """Initialize algorithm."""
        super().__init__()
        self.logger = get_plugin_logger()

    def tr(self, string):
        """Translate string."""
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        """Create new instance of algorithm."""
        return OptimizePlatformHeightAlgorithm()

    def name(self):
        """Algorithm name."""
        return 'optimize_platform_height'

    def displayName(self):
        """Algorithm display name."""
        return self.tr('Optimize Platform Height')

    def group(self):
        """Algorithm group."""
        return self.tr('Wind Turbine')

    def groupId(self):
        """Algorithm group ID."""
        return 'windturbine'

    def shortHelpString(self):
        """Algorithm help text."""
        return self.tr("""
        <p>Optimizes the platform height for wind turbine crane pads by minimizing earthwork volumes.</p>

        <h3>Workflow:</h3>
        <ol>
            <li>Imports DXF file containing crane pad outline (LWPOLYLINE entities)</li>
            <li>Downloads high-resolution DEM data (1m) from hoehendaten.de API</li>
            <li>Tests multiple platform heights within specified range</li>
            <li>Calculates cut/fill volumes for each scenario</li>
            <li>Finds optimal height that minimizes total earthwork</li>
            <li>Generates terrain cross-section profiles</li>
            <li>Creates comprehensive HTML report with maps and visualizations</li>
        </ol>

        <h3>Inputs:</h3>
        <ul>
            <li><b>DXF File:</b> CAD file with crane pad outline (EPSG:25832)</li>
            <li><b>Height Range:</b> Min/max platform heights to test (m above sea level)</li>
            <li><b>Output GeoPackage:</b> Path for output data storage</li>
        </ul>

        <h3>Outputs:</h3>
        <ul>
            <li>GeoPackage with platform polygon, profile lines, and DEM mosaic</li>
            <li>HTML report with optimization results and visualizations</li>
            <li>PNG files with terrain cross-sections</li>
        </ul>

        <p><b>Note:</b> Requires internet connection for DEM download from hoehendaten.de API.</p>
        """)

    def initAlgorithm(self, config=None):
        """Initialize algorithm parameters."""

        # === REQUIRED PARAMETERS ===

        # Input DXF file
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_DXF,
                self.tr('Input DXF File'),
                behavior=QgsProcessingParameterFile.File,
                fileFilter='DXF Files (*.dxf)'
            )
        )

        # Height range
        self.addParameter(
            QgsProcessingParameterNumber(
                self.MIN_HEIGHT,
                self.tr('Minimum Platform Height (m ü.NN)'),
                type=QgsProcessingParameterNumber.Double,
                minValue=0,
                maxValue=9999,
                defaultValue=300.0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_HEIGHT,
                self.tr('Maximum Platform Height (m ü.NN)'),
                type=QgsProcessingParameterNumber.Double,
                minValue=0,
                maxValue=9999,
                defaultValue=310.0
            )
        )

        # Output GeoPackage
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_GPKG,
                self.tr('Output GeoPackage'),
                fileFilter='GeoPackage (*.gpkg)'
            )
        )

        # === OPTIONAL/ADVANCED PARAMETERS ===

        # Height step
        self.addParameter(
            QgsProcessingParameterNumber(
                self.HEIGHT_STEP,
                self.tr('Height Step (m)'),
                type=QgsProcessingParameterNumber.Double,
                minValue=0.01,
                maxValue=10.0,
                defaultValue=0.1,
                optional=True
            )
        )

        # DXF tolerance
        self.addParameter(
            QgsProcessingParameterNumber(
                self.DXF_TOLERANCE,
                self.tr('DXF Point Connection Tolerance (m)'),
                type=QgsProcessingParameterNumber.Double,
                minValue=0.001,
                maxValue=10.0,
                defaultValue=0.01,
                optional=True
            )
        )

        # Slope angle
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SLOPE_ANGLE,
                self.tr('Slope Angle (degrees)'),
                type=QgsProcessingParameterNumber.Double,
                minValue=15.0,
                maxValue=60.0,
                defaultValue=45.0,
                optional=True
            )
        )

        # Cross-section spacing
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PROFILE_SPACING,
                self.tr('Cross-Section Spacing (m)'),
                type=QgsProcessingParameterNumber.Double,
                minValue=1.0,
                maxValue=50.0,
                defaultValue=10.0,
                optional=True
            )
        )

        # Cross-section overhang
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PROFILE_OVERHANG,
                self.tr('Cross-Section Overhang (%)'),
                type=QgsProcessingParameterNumber.Double,
                minValue=0.0,
                maxValue=50.0,
                defaultValue=10.0,
                optional=True
            )
        )

        # Vertical exaggeration
        self.addParameter(
            QgsProcessingParameterNumber(
                self.VERTICAL_EXAGGERATION,
                self.tr('Vertical Exaggeration for Profiles'),
                type=QgsProcessingParameterNumber.Double,
                minValue=1.0,
                maxValue=5.0,
                defaultValue=2.0,
                optional=True
            )
        )

        # Force DEM refresh
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.FORCE_REFRESH,
                self.tr('Force DEM Download (ignore cache)'),
                defaultValue=False,
                optional=True
            )
        )

        # === OUTPUTS ===

        # Platform polygon sink
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_POLYGON,
                self.tr('Platform Polygon'),
                type=QgsProcessing.TypeVectorPolygon,
                optional=True
            )
        )

        # Profile lines sink
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_PROFILES,
                self.tr('Profile Lines'),
                type=QgsProcessing.TypeVectorLine,
                optional=True
            )
        )

        # HTML report
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_REPORT,
                self.tr('HTML Report'),
                fileFilter='HTML Files (*.html)',
                optional=True
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Execute the algorithm.

        Returns:
            dict: Outputs dictionary
        """
        self.logger.info("=" * 60)
        self.logger.info("WIND TURBINE EARTHWORK CALCULATOR V2")
        self.logger.info("=" * 60)

        try:
            # ===== SCHRITT 1: EINGABEN VALIDIEREN =====
            feedback.pushInfo("\n" + "=" * 60)
            feedback.pushInfo("SCHRITT 1: Eingaben validieren")
            feedback.pushInfo("=" * 60)

            dxf_path = self.parameterAsFile(parameters, self.INPUT_DXF, context)
            min_height = self.parameterAsDouble(parameters, self.MIN_HEIGHT, context)
            max_height = self.parameterAsDouble(parameters, self.MAX_HEIGHT, context)
            height_step = self.parameterAsDouble(parameters, self.HEIGHT_STEP, context)
            output_gpkg = self.parameterAsFileOutput(parameters, self.OUTPUT_GPKG, context)

            # Validate
            try:
                validate_file_exists(dxf_path, '.dxf')
                validate_height_range(min_height, max_height, height_step)
                validate_output_path(output_gpkg, '.gpkg')
            except ValidationError as e:
                raise QgsProcessingException(str(e))

            feedback.pushInfo(f"✓ DXF-Datei: {dxf_path}")
            feedback.pushInfo(f"✓ Höhenbereich: {min_height:.1f} - {max_height:.1f}m (Schrittweite: {height_step:.2f}m)")
            feedback.pushInfo(f"✓ Ausgabe: {output_gpkg}")

            feedback.setProgress(5)

            # ===== SCHRITT 2: DXF IMPORTIEREN =====
            feedback.pushInfo("\n" + "=" * 60)
            feedback.pushInfo("SCHRITT 2: DXF-Datei importieren")
            feedback.pushInfo("=" * 60)

            dxf_tolerance = self.parameterAsDouble(parameters, self.DXF_TOLERANCE, context)

            importer = DXFImporter(dxf_path, tolerance=dxf_tolerance)
            polygon, metadata = importer.import_as_polygon()

            feedback.pushInfo(f"✓ Polygon importiert: {metadata['num_vertices']} Stützpunkte")
            feedback.pushInfo(f"✓ Fläche: {metadata['area']:.2f} m²")
            feedback.pushInfo(f"✓ Umfang: {metadata['perimeter']:.2f} m")

            feedback.setProgress(10)

            # ===== SCHRITT 3: DGM HERUNTERLADEN =====
            feedback.pushInfo("\n" + "=" * 60)
            feedback.pushInfo("SCHRITT 3: Digitales Geländemodell herunterladen")
            feedback.pushInfo("=" * 60)

            force_refresh = self.parameterAsBoolean(parameters, self.FORCE_REFRESH, context)

            # Create temporary DEM file
            temp_dem_path = tempfile.mktemp(suffix='.tif', prefix='dem_mosaic_')

            downloader = DEMDownloader(force_refresh=force_refresh)
            dem_path = downloader.download_for_geometry(
                polygon,
                temp_dem_path,
                buffer_m=250,
                feedback=feedback
            )

            feedback.pushInfo(f"✓ DGM-Mosaik erstellt: {dem_path}")

            # Load DEM as raster layer
            dem_layer = QgsRasterLayer(dem_path, 'DGM Mosaik')
            if not dem_layer.isValid():
                raise QgsProcessingException("DGM-Mosaik konnte nicht geladen werden")

            feedback.setProgress(40)

            # ===== SCHRITT 4: PLATTFORMHÖHE OPTIMIEREN =====
            feedback.pushInfo("\n" + "=" * 60)
            feedback.pushInfo("SCHRITT 4: Plattformhöhe optimieren")
            feedback.pushInfo("=" * 60)

            slope_angle = self.parameterAsDouble(parameters, self.SLOPE_ANGLE, context)

            config = {
                'slope_angle': slope_angle
            }

            calculator = EarthworkCalculator(dem_layer, polygon, config)
            optimal_height, results = calculator.find_optimum(
                min_height,
                max_height,
                height_step,
                feedback=feedback
            )

            feedback.pushInfo(f"\n✓ OPTIMALE HÖHE: {optimal_height:.2f} m ü.NN")
            feedback.pushInfo(f"  Abtrag gesamt: {results['total_cut']:,.0f} m³")
            feedback.pushInfo(f"  Auftrag gesamt: {results['total_fill']:,.0f} m³")
            feedback.pushInfo(f"  Gesamtvolumen: {results['total_volume_moved']:,.0f} m³")

            feedback.setProgress(70)

            # ===== SCHRITT 5: GELÄNDESCHNITTE ERSTELLEN =====
            feedback.pushInfo("\n" + "=" * 60)
            feedback.pushInfo("SCHRITT 5: Geländeschnitte erstellen")
            feedback.pushInfo("=" * 60)

            spacing = self.parameterAsDouble(parameters, self.PROFILE_SPACING, context)
            overhang = self.parameterAsDouble(parameters, self.PROFILE_OVERHANG, context)
            vert_exag = self.parameterAsDouble(parameters, self.VERTICAL_EXAGGERATION, context)

            # Create profile output directory
            profile_dir = Path(output_gpkg).parent / 'profiles'

            generator = ProfileGenerator(dem_layer, polygon, optimal_height)
            profiles = generator.generate_all_profiles(
                str(profile_dir),
                spacing=spacing,
                overhang_percent=overhang,
                vertical_exaggeration=vert_exag,
                volume_info=results,
                feedback=feedback
            )

            profile_pngs = [p['png_path'] for p in profiles if 'png_path' in p]

            feedback.pushInfo(f"✓ {len(profiles)} Geländeschnitte erstellt")

            feedback.setProgress(85)

            # ===== SCHRITT 6: BERICHT ERSTELLEN =====
            feedback.pushInfo("\n" + "=" * 60)
            feedback.pushInfo("SCHRITT 6: HTML-Bericht erstellen")
            feedback.pushInfo("=" * 60)

            # Determine report path
            report_path = self.parameterAsFileOutput(parameters, self.OUTPUT_REPORT, context)
            if not report_path:
                report_path = str(Path(output_gpkg).with_suffix('.html'))

            report_gen = ReportGenerator(results, polygon, dem_layer)
            report_gen.generate_html(report_path, profile_pngs, config)

            feedback.pushInfo(f"✓ HTML-Bericht erstellt: {report_path}")

            feedback.setProgress(90)

            # ===== SCHRITT 7: IN GEOPACKAGE SPEICHERN =====
            feedback.pushInfo("\n" + "=" * 60)
            feedback.pushInfo("SCHRITT 7: In GeoPackage speichern")
            feedback.pushInfo("=" * 60)

            # Save platform polygon
            platform_fields = QgsFields()
            platform_fields.append(QgsField('id', QVariant.Int))
            platform_fields.append(QgsField('optimal_height', QVariant.Double))
            platform_fields.append(QgsField('area_m2', QVariant.Double))
            platform_fields.append(QgsField('total_cut', QVariant.Double))
            platform_fields.append(QgsField('total_fill', QVariant.Double))

            (polygon_sink, polygon_dest_id) = self.parameterAsSink(
                parameters,
                self.OUTPUT_POLYGON,
                context,
                platform_fields,
                QgsWkbTypes.Polygon,
                QgsCoordinateReferenceSystem('EPSG:25832')
            )

            if polygon_sink:
                feat = QgsFeature(platform_fields)
                feat.setGeometry(polygon)
                feat.setAttribute('id', 1)
                feat.setAttribute('optimal_height', float(optimal_height))
                feat.setAttribute('area_m2', float(polygon.area()))
                feat.setAttribute('total_cut', float(results['total_cut']))
                feat.setAttribute('total_fill', float(results['total_fill']))
                polygon_sink.addFeature(feat, QgsFeatureSink.FastInsert)

                feedback.pushInfo("✓ Plattform-Polygon gespeichert")

            # Save profile lines
            profile_fields = QgsFields()
            profile_fields.append(QgsField('id', QVariant.Int))
            profile_fields.append(QgsField('type', QVariant.String))
            profile_fields.append(QgsField('cross_angle', QVariant.Double))
            profile_fields.append(QgsField('main_angle', QVariant.Double))
            profile_fields.append(QgsField('length_m', QVariant.Double))
            profile_fields.append(QgsField('width_m', QVariant.Double))

            (profile_sink, profile_dest_id) = self.parameterAsSink(
                parameters,
                self.OUTPUT_PROFILES,
                context,
                profile_fields,
                QgsWkbTypes.LineString,
                QgsCoordinateReferenceSystem('EPSG:25832')
            )

            if profile_sink:
                for i, profile in enumerate(profiles):
                    feat = QgsFeature(profile_fields)
                    feat.setGeometry(profile['geometry'])
                    feat.setAttribute('id', i + 1)
                    feat.setAttribute('type', str(profile['type']))
                    feat.setAttribute('cross_angle', float(profile.get('cross_angle', 0)))
                    feat.setAttribute('main_angle', float(profile.get('main_angle', 0)))
                    feat.setAttribute('length_m', float(profile['length']))
                    feat.setAttribute('width_m', float(profile.get('width', 0)))
                    profile_sink.addFeature(feat, QgsFeatureSink.FastInsert)

                feedback.pushInfo("✓ Geländeschnitt-Linien gespeichert")

                # Add labels to profile lines if they were added to the map
                if profile_dest_id:
                    try:
                        # Get the layer that was just created
                        profile_layer = QgsProject.instance().mapLayer(profile_dest_id.split('|')[0])
                        if profile_layer:
                            success = add_labels_to_profile_lines(profile_layer, label_field='type')
                            if success:
                                feedback.pushInfo("✓ Beschriftungen für Geländeschnitte hinzugefügt")
                    except Exception as e:
                        feedback.pushWarning(f"Beschriftungen konnten nicht hinzugefügt werden: {e}")

            # Copy DEM to GeoPackage (as separate TIFF for now)
            dem_tiff_path = str(Path(output_gpkg).with_suffix('.dem.tif'))
            import shutil
            shutil.copy(dem_path, dem_tiff_path)
            feedback.pushInfo(f"✓ DGM gespeichert: {dem_tiff_path}")

            # ===== SCHRITT 8: DGM MIT HÖHENLINIEN LADEN =====
            feedback.pushInfo("\n" + "=" * 60)
            feedback.pushInfo("SCHRITT 8: DGM mit Höhenlinien zur Karte hinzufügen")
            feedback.pushInfo("=" * 60)

            try:
                # Create vector contours with labels
                contour_gpkg_path = str(Path(output_gpkg).with_suffix('.contours.gpkg'))
                contour_layer = create_vector_contours_with_labels(
                    dem_tiff_path,
                    contour_gpkg_path,
                    contour_interval=1.0,
                    index_interval=5.0
                )

                if contour_layer:
                    feedback.pushInfo(f"✓ Höhenlinien zur Karte hinzugefügt mit Beschriftung (alle 5m)")
                    feedback.pushInfo(f"✓ Höhenlinien gespeichert: {contour_gpkg_path}")
                else:
                    feedback.pushWarning("Höhenlinien konnten nicht erstellt werden, versuche Raster-Darstellung...")
                    # Fallback to raster contour rendering
                    dem_layer_map = load_dem_with_contours_to_map(
                        dem_tiff_path,
                        layer_name="DGM Höhenlinien",
                        contour_interval=1.0,
                        index_interval=5.0
                    )
                    if dem_layer_map:
                        feedback.pushInfo("✓ DGM mit Höhenlinien-Darstellung geladen")
                    else:
                        feedback.pushWarning("DGM konnte nicht mit Höhenlinien geladen werden")

            except Exception as e:
                feedback.pushWarning(f"DGM-Höhenlinien konnten nicht geladen werden: {e}")
                self.logger.warning(f"Fehler beim Laden der DGM-Höhenlinien: {e}")

            feedback.setProgress(100)

            # ===== FERTIG =====
            feedback.pushInfo("\n" + "=" * 60)
            feedback.pushInfo("✓ BERECHNUNG ABGESCHLOSSEN!")
            feedback.pushInfo("=" * 60)
            feedback.pushInfo(f"\nOptimale Plattformhöhe: {optimal_height:.2f} m ü.NN")
            feedback.pushInfo(f"Gesamter Erdmassenausgleich: {results['total_volume_moved']:,.0f} m³")
            feedback.pushInfo(f"\nAusgabedateien:")
            feedback.pushInfo(f"  - GeoPackage: {output_gpkg}")
            feedback.pushInfo(f"  - DGM: {dem_tiff_path}")
            feedback.pushInfo(f"  - Bericht: {report_path}")
            feedback.pushInfo(f"  - Geländeschnitte: {profile_dir}")

            return {
                self.OUTPUT_POLYGON: polygon_dest_id,
                self.OUTPUT_PROFILES: profile_dest_id,
                self.OUTPUT_REPORT: report_path,
                self.OUTPUT_GPKG: output_gpkg
            }

        except Exception as e:
            self.logger.error(f"Algorithm failed: {e}", exc_info=True)
            raise QgsProcessingException(str(e))
