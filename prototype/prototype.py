"""
Wind Turbine Earthwork Calculator - Version 5.5
================================================

NEUE FEATURES v5.5 (Polygon Refactoring):
- Beliebige Polygon-Formen für Kranstellflächen (L, Trapez, Kreis, Freiform)
- Polygon-basierte Fundamente (Oktagon, Quadrat, etc.) als Alternative zu Kreis
- Exakte Volumen-Berechnung entlang Polygon-Kontur (kein Bounding-Box-Fehler)
- Böschungen folgen Polygon-Form (konkave Formen unterstützt)
- Höhen-Interpolation auf Böschung (beliebige Geometrien)
- Multi-Polygon und Polygon-mit-Loch Support

FEATURES v5.0:
- Geländeschnitt-Modul: Automatische Profil-Generierung (8 Schnitte pro Standort)
- Matplotlib-basierte 2D-Visualisierung (Cut/Fill-Darstellung)
- 2-stufiger Workflow: Auto-generierte oder benutzerdefinierte Schnittlinien
- PNG-Export (300 DPI) mit Info-Boxen und Legenden
- Höhenübertreibung konfigurierbar (1.0-5.0x)

FEATURES v4.0:
- Polygon-Input-Modus: Angepasste Standflächen als Input verwenden
- Automatische Rotation-Erkennung (Oriented Bounding Box)
- Auto-Rotation-Optimierung: Findet beste Ausrichtung (0°-360°)
- Rotiertes DEM-Sampling für präzise Berechnungen
- Performance: Rotation-Matrix-Caching

FEATURES v3.0:
- Fundament-Berechnung (Durchmesser, Tiefe, Typ)
- Material-Wiederverwendung (Aushub → Auftrag)
- Intelligente Material-Bilanz
- Überschuss/Mangel-Berechnung
- Erweiterte Kostenbetrachtung
- Standflächen-Polygon-Export

AUTOR: Windkraft-Standortplanung
VERSION: 5.5 (Polygon-based Sampling)
DATUM: Oktober 2025
"""

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterEnum,
    QgsProcessingParameterBoolean,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsField,
    QgsFields,
    QgsWkbTypes,
    QgsProcessingException,
    QgsRasterLayer,
    QgsProject,
    QgsRaster
)
from PyQt5.QtCore import QVariant
import processing
import math
import numpy as np
import os

# HTML Report Generator (v5.5)
try:
    from html_report_generator import HTMLReportGenerator
    HTML_REPORT_AVAILABLE = True
except ImportError:
    HTML_REPORT_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPLPolygon
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class WindTurbineEarthworkCalculatorV3(QgsProcessingAlgorithm):
    """Berechnet Cut/Fill-Volumen für WKA inkl. Fundament und Kranstellfläche"""
    
    INPUT_DEM = 'INPUT_DEM'
    INPUT_POINTS = 'INPUT_POINTS'
    INPUT_POLYGONS = 'INPUT_POLYGONS'
    PLATFORM_LENGTH = 'PLATFORM_LENGTH'
    PLATFORM_WIDTH = 'PLATFORM_WIDTH'
    MAX_SLOPE = 'MAX_SLOPE'
    SLOPE_ANGLE = 'SLOPE_ANGLE'
    SLOPE_WIDTH = 'SLOPE_WIDTH'
    FOUNDATION_DIAMETER = 'FOUNDATION_DIAMETER'
    FOUNDATION_DEPTH = 'FOUNDATION_DEPTH'
    FOUNDATION_TYPE = 'FOUNDATION_TYPE'
    USE_CIRCULAR_FOUNDATIONS = 'USE_CIRCULAR_FOUNDATIONS'
    FOUNDATION_POLYGONS = 'FOUNDATION_POLYGONS'
    SOIL_TYPE = 'SOIL_TYPE'
    SWELL_FACTOR = 'SWELL_FACTOR'
    COMPACTION_FACTOR = 'COMPACTION_FACTOR'
    MATERIAL_REUSE = 'MATERIAL_REUSE'
    OPTIMIZATION_METHOD = 'OPTIMIZATION_METHOD'
    AUTO_ROTATE = 'AUTO_ROTATE'
    ROTATION_STEP = 'ROTATION_STEP'
    COST_EXCAVATION = 'COST_EXCAVATION'
    COST_TRANSPORT = 'COST_TRANSPORT'
    COST_FILL_IMPORT = 'COST_FILL_IMPORT'
    COST_GRAVEL = 'COST_GRAVEL'
    COST_COMPACTION = 'COST_COMPACTION'
    GRAVEL_LAYER_THICKNESS = 'GRAVEL_LAYER_THICKNESS'
    GENERATE_PROFILES = 'GENERATE_PROFILES'
    PROFILE_OUTPUT_FOLDER = 'PROFILE_OUTPUT_FOLDER'
    CUSTOM_PROFILES = 'CUSTOM_PROFILES'
    VERTICAL_EXAGGERATION = 'VERTICAL_EXAGGERATION'
    OUTPUT_POINTS = 'OUTPUT_POINTS'
    OUTPUT_PLATFORMS = 'OUTPUT_PLATFORMS'
    OUTPUT_PROFILES = 'OUTPUT_PROFILES'
    OUTPUT_REPORT = 'OUTPUT_REPORT'
    
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
    
    def createInstance(self):
        return WindTurbineEarthworkCalculatorV3()
    
    def name(self):
        return 'windturbineearthworkv3'
    
    def displayName(self):
        return self.tr('Wind Turbine Earthwork Calculator v5.5')
    
    def group(self):
        return self.tr('Windkraft')
    
    def groupId(self):
        return 'windkraft'
    
    def shortHelpString(self):
        return self.tr("""
        <b>Windkraftanlagen Erdarbeitsrechner v5.5</b>
        
        <p><b>🆕 NEU in Version 5.5:</b></p>
        <ul>
            <li><b>Beliebige Polygon-Formen</b>: L, Trapez, Kreis, Freiform für Kranstellflächen</li>
            <li><b>Polygon-Fundamente</b>: Oktagon, Quadrat, etc. als Alternative zu Kreis</li>
            <li><b>Exakte Volumen-Berechnung</b>: Entlang Polygon-Kontur (kein Bounding-Box)</li>
            <li><b>Böschungen folgen Polygon-Form</b>: Auch für konkave Formen</li>
        </ul>
        
        <p><b>Features v5.0:</b></p>
        <ul>
            <li><b>Geländeschnitt-Modul</b>: 8 Profile pro Standort (Fundament + Kranfläche)</li>
            <li><b>Matplotlib-Plots</b>: Cut/Fill-Visualisierung mit PNG-Export (300 DPI)</li>
            <li><b>2-Stufen-Workflow</b>: Auto-Schnitte → Optional manuell anpassen</li>
        </ul>
        
        <p><b>Features v4.0:</b></p>
        <ul>
            <li><b>Polygon-Input-Modus</b>: Angepasste Standflächen als Input verwenden</li>
            <li><b>Automatische Rotation-Erkennung</b> aus Polygon-Geometrie (Oriented Bounding Box)</li>
            <li><b>Auto-Rotation-Optimierung</b>: Findet beste Ausrichtung (0°-360°)</li>
            <li><b>2-Schritt-Workflow</b>: Generieren → Anpassen → Neuberechnen</li>
        </ul>
        
        <p><b>Features v3.0:</b></p>
        <ul>
            <li>Fundament-Berechnung mit 3 Typen</li>
            <li>Material-Wiederverwendung & Kostenmodul</li>
            <li>Standflächen-Polygon-Export</li>
        </ul>
        
        <p><b>📖 Verwendung:</b></p>
        <ol>
            <li><b>Schritt 1</b>: Punkte angeben → Polygone werden generiert (Nord-Süd)
                <br><i>Optional: "Auto-Rotation" aktivieren für automatische Optimierung!</i></li>
            <li><b>Schritt 2</b>: Polygone in QGIS manuell anpassen (rotieren/verschieben)</li>
            <li><b>Schritt 3</b>: Angepasste Polygone als Input → Neuberechnung mit Rotation!</li>
        </ol>
        
        <p><i>💡 Tipps:</i></p>
        <ul>
            <li>Aktivieren Sie "Standflächen (Polygone)" Output in Schritt 1!</li>
            <li>Auto-Rotation findet beste Ausrichtung (testet 0°-360° in konfigurierbaren Schritten)</li>
            <li>Im Polygon-Modus wird Rotation automatisch aus Geometrie extrahiert</li>
        </ul>
        """)
    
    def initAlgorithm(self, config=None):
        """Definition aller Parameter"""
        
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.INPUT_DEM, self.tr('Digitales Geländemodell (DEM)')))
        
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT_POINTS, self.tr('WKA-Standorte (Punkte)'),
            [QgsProcessing.TypeVectorPoint]))
        
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT_POLYGONS, self.tr('🔄 WKA-Standflächen (Polygone)'),
            [QgsProcessing.TypeVectorPolygon],
            optional=True))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.PLATFORM_LENGTH, self.tr('Plattformlänge (m)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=45.0, minValue=20.0, maxValue=100.0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.PLATFORM_WIDTH, self.tr('Plattformbreite (m)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=40.0, minValue=20.0, maxValue=100.0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.MAX_SLOPE, self.tr('Max. Plattform-Neigung (%)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=2.0, minValue=0.0, maxValue=5.0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.SLOPE_ANGLE, self.tr('Böschungswinkel (Grad)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=34.0, minValue=20.0, maxValue=60.0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.SLOPE_WIDTH, self.tr('Böschungsbreite (m)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=10.0, minValue=5.0, maxValue=30.0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.FOUNDATION_DIAMETER, self.tr('🔧 Fundament-Durchmesser (m)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=22.0, minValue=10.0, maxValue=40.0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.FOUNDATION_DEPTH, self.tr('🔧 Fundament-Tiefe (m)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=4.0, minValue=2.0, maxValue=8.0))
        
        self.addParameter(QgsProcessingParameterEnum(
            self.FOUNDATION_TYPE, self.tr('🔧 Fundament-Typ'),
            options=['Flachgründung', 'Tiefgründung', 'Pfahlgründung'],
            defaultValue=0))
        
        self.addParameter(QgsProcessingParameterBoolean(
            self.USE_CIRCULAR_FOUNDATIONS,
            self.tr('🔧 Runde Fundamente verwenden'),
            defaultValue=True))
        
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.FOUNDATION_POLYGONS,
            self.tr('🔧 Fundament-Polygone (nur wenn nicht rund)'),
            [QgsProcessing.TypeVectorPolygon],
            optional=True))
        
        self.addParameter(QgsProcessingParameterEnum(
            self.SOIL_TYPE, self.tr('Bodenart'),
            options=['Sand/Kies', 'Lehm/Ton', 'Fels', 'Benutzerdefiniert'],
            defaultValue=1))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.SWELL_FACTOR, self.tr('Auflockerungsfaktor'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=1.25, minValue=1.0, maxValue=1.5))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.COMPACTION_FACTOR, self.tr('Verdichtungsfaktor'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.85, minValue=0.7, maxValue=1.0))
        
        self.addParameter(QgsProcessingParameterBoolean(
            self.MATERIAL_REUSE,
            self.tr('♻️ Material-Wiederverwendung'),
            defaultValue=True))
        
        self.addParameter(QgsProcessingParameterEnum(
            self.OPTIMIZATION_METHOD, self.tr('Optimierung'),
            options=['Mittelwert', 'Min. Aushub', 'Ausgeglichen'],
            defaultValue=2))
        
        self.addParameter(QgsProcessingParameterBoolean(
            self.AUTO_ROTATE,
            self.tr('🔄 Auto-Rotation (nur Punkt-Modus)'),
            defaultValue=False))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.ROTATION_STEP, self.tr('Rotations-Schrittweite (Grad)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=15.0, minValue=5.0, maxValue=45.0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.COST_EXCAVATION, self.tr('💰 Kosten Erdaushub (€/m³)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=8.0, minValue=0.0, maxValue=50.0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.COST_TRANSPORT, self.tr('💰 Kosten Transport (€/m³)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=12.0, minValue=0.0, maxValue=50.0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.COST_FILL_IMPORT, self.tr('💰 Kosten Material-Einkauf (€/m³)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=15.0, minValue=0.0, maxValue=50.0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.COST_GRAVEL, self.tr('💰 Kosten Schotter-Einbau (€/m³)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=25.0, minValue=0.0, maxValue=100.0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.COST_COMPACTION, self.tr('💰 Kosten Verdichtung (€/m³)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=5.0, minValue=0.0, maxValue=30.0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.GRAVEL_LAYER_THICKNESS, self.tr('Schotter-Schichtdicke (m)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.5, minValue=0.3, maxValue=1.0))
        
        self.addParameter(QgsProcessingParameterBoolean(
            self.GENERATE_PROFILES,
            self.tr('📊 Geländeschnitte erstellen'),
            defaultValue=False))
        
        self.addParameter(QgsProcessingParameterFolderDestination(
            self.PROFILE_OUTPUT_FOLDER,
            self.tr('Ordner für Profilschnitt-PNGs'),
            optional=True))
        
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.CUSTOM_PROFILES,
            self.tr('Benutzerdefinierte Schnittlinien (optional)'),
            [QgsProcessing.TypeVectorLine],
            optional=True))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.VERTICAL_EXAGGERATION, self.tr('Höhenübertreibung (Profil)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=1.5, minValue=1.0, maxValue=5.0))
        
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT_POINTS, self.tr('Ausgabe: Volumendaten')))
        
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT_PLATFORMS, self.tr('Ausgabe: Standflächen (Polygone)'),
            optional=True))
        
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT_PROFILES, self.tr('Ausgabe: Schnittlinien'),
            optional=True))
        
        self.addParameter(QgsProcessingParameterFileDestination(
            self.OUTPUT_REPORT, self.tr('Ausgabe: HTML-Report'),
            fileFilter='HTML files (*.html)'))
    
    def processAlgorithm(self, parameters, context, feedback):
        """Hauptverarbeitung"""
        
        feedback.pushInfo('=' * 70)
        feedback.pushInfo('Wind Turbine Earthwork Calculator v5.5')
        feedback.pushInfo('=' * 70)
        
        dem_layer = self.parameterAsRasterLayer(parameters, self.INPUT_DEM, context)
        points_source = self.parameterAsSource(parameters, self.INPUT_POINTS, context)
        polygons_source = self.parameterAsSource(parameters, self.INPUT_POLYGONS, context)
        
        # Modus bestimmen: Polygone überschreiben Punkte
        use_polygons = (polygons_source is not None and polygons_source.featureCount() > 0)
        
        platform_length = self.parameterAsDouble(parameters, self.PLATFORM_LENGTH, context)
        platform_width = self.parameterAsDouble(parameters, self.PLATFORM_WIDTH, context)
        max_slope = self.parameterAsDouble(parameters, self.MAX_SLOPE, context)
        slope_angle = self.parameterAsDouble(parameters, self.SLOPE_ANGLE, context)
        slope_width = self.parameterAsDouble(parameters, self.SLOPE_WIDTH, context)
        foundation_diameter = self.parameterAsDouble(parameters, self.FOUNDATION_DIAMETER, context)
        foundation_depth = self.parameterAsDouble(parameters, self.FOUNDATION_DEPTH, context)
        foundation_type = self.parameterAsEnum(parameters, self.FOUNDATION_TYPE, context)
        use_circular_foundations = self.parameterAsBool(parameters, self.USE_CIRCULAR_FOUNDATIONS, context)
        foundation_polygons_source = self.parameterAsSource(parameters, self.FOUNDATION_POLYGONS, context)
        soil_type = self.parameterAsEnum(parameters, self.SOIL_TYPE, context)
        swell_factor = self.parameterAsDouble(parameters, self.SWELL_FACTOR, context)
        compaction_factor = self.parameterAsDouble(parameters, self.COMPACTION_FACTOR, context)
        material_reuse = self.parameterAsBool(parameters, self.MATERIAL_REUSE, context)
        optimization_method = self.parameterAsEnum(parameters, self.OPTIMIZATION_METHOD, context)
        auto_rotate = self.parameterAsBool(parameters, self.AUTO_ROTATE, context)
        rotation_step = self.parameterAsDouble(parameters, self.ROTATION_STEP, context)
        cost_excavation = self.parameterAsDouble(parameters, self.COST_EXCAVATION, context)
        cost_transport = self.parameterAsDouble(parameters, self.COST_TRANSPORT, context)
        cost_fill_import = self.parameterAsDouble(parameters, self.COST_FILL_IMPORT, context)
        cost_gravel = self.parameterAsDouble(parameters, self.COST_GRAVEL, context)
        cost_compaction = self.parameterAsDouble(parameters, self.COST_COMPACTION, context)
        gravel_thickness = self.parameterAsDouble(parameters, self.GRAVEL_LAYER_THICKNESS, context)
        
        if soil_type == 0:
            swell_factor = 1.15
            compaction_factor = 0.90
        elif soil_type == 1:
            swell_factor = 1.25
            compaction_factor = 0.85
        elif soil_type == 2:
            swell_factor = 1.40
            compaction_factor = 0.95
        
        foundation_type_names = ['Flachgründung', 'Tiefgründung', 'Pfahlgründung']
        
        if dem_layer is None:
            raise QgsProcessingException('DEM konnte nicht geladen werden!')
        
        # DEM CRS-Validierung (CRITICAL für korrekte Berechnungen)
        dem_crs = dem_layer.crs()
        if dem_crs.isGeographic():
            raise QgsProcessingException(
                f'DEM muss in projiziertem CRS sein (z.B. UTM)!\n'
                f'Aktuelles CRS: {dem_crs.authid()} ({dem_crs.description()})\n'
                f'Bitte reprojizieren Sie das DEM vor der Verwendung.\n'
                f'→ Sonst sind Entfernungen in Grad statt Metern!')
        
        # Prüfe Input-Quelle
        if use_polygons:
            feature_source = polygons_source
            input_mode = 'Polygon-Modus'
            
            # CRS-Validierung für Polygone
            poly_crs = polygons_source.sourceCrs()
            if poly_crs.isGeographic():
                raise QgsProcessingException(
                    f'Polygone müssen in projiziertem CRS sein (z.B. UTM)!\n'
                    f'Aktuelles CRS: {poly_crs.authid()} ({poly_crs.description()})\n'
                    f'Bitte reprojizieren Sie die Polygone vor der Verwendung.')
            
            # CRS-Match mit DEM prüfen
            dem_crs = dem_layer.crs()
            if poly_crs.authid() != dem_crs.authid():
                feedback.pushWarning(
                    f'⚠️ CRS-Mismatch:\n'
                    f'  Polygone: {poly_crs.authid()}\n'
                    f'  DEM: {dem_crs.authid()}\n'
                    f'  → Automatische Reprojizierung wird versucht')
        else:
            if points_source is None or points_source.featureCount() == 0:
                raise QgsProcessingException('Keine WKA-Standorte gefunden!')
            feature_source = points_source
            input_mode = 'Punkt-Modus'
        
        feedback.pushInfo(f'\nKonfiguration:')
        feedback.pushInfo(f'  Modus: {input_mode}')
        feedback.pushInfo(f'  Plattform: {platform_length}m x {platform_width}m (Standard)')
        feedback.pushInfo(f'  Fundament: Ø{foundation_diameter}m, {foundation_depth}m tief')
        feedback.pushInfo(f'  Wiederverwendung: {"Ja" if material_reuse else "Nein"}')
        feedback.pushInfo(f'  Standorte: {feature_source.featureCount()}')
        
        fields = self._create_output_fields()
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT_POINTS, context,
            fields, QgsWkbTypes.Point, points_source.sourceCrs())
        
        # Standflächen-Polygone (optional)
        platform_fields = self._create_platform_fields()
        platform_sink = None
        platform_dest_id = None
        
        if self.OUTPUT_PLATFORMS in parameters and parameters[self.OUTPUT_PLATFORMS] is not None:
            (platform_sink, platform_dest_id) = self.parameterAsSink(
                parameters, self.OUTPUT_PLATFORMS, context,
                platform_fields, QgsWkbTypes.Polygon, feature_source.sourceCrs())
        
        total = feature_source.featureCount()
        results = []
        
        for current, feature in enumerate(feature_source.getFeatures()):
            if feedback.isCanceled():
                break
            
            feedback.setProgress(int(current / total * 100))
            feedback.pushInfo(f'\nStandort {current + 1}/{total}')
            
            # Punkt und Plattform-Parameter extrahieren
            if use_polygons:
                # Polygon-Modus: Eigenschaften aus Polygon extrahieren
                poly_props = self._extract_polygon_properties(feature)
                point = poly_props['centroid']
                current_platform_length = poly_props['length']
                current_platform_width = poly_props['width']
                rotation_angle = poly_props['rotation']
                feedback.pushInfo(f'  Polygon → Zentrum: ({point.x():.1f}, {point.y():.1f})')
                feedback.pushInfo(f'  Maße: {current_platform_length:.1f}m × {current_platform_width:.1f}m, Rotation: {rotation_angle:.1f}°')
            else:
                # Punkt-Modus: Standard-Werte verwenden
                point = feature.geometry().asPoint()
                current_platform_length = platform_length
                current_platform_width = platform_width
                
                # Auto-Rotation im Punkt-Modus
                if auto_rotate:
                    rotation_result = self._optimize_platform_rotation(
                        dem_layer, point, platform_length, platform_width,
                        max_slope, slope_angle, slope_width,
                        swell_factor, compaction_factor, optimization_method,
                        rotation_step, feedback)
                    rotation_angle = rotation_result['best_rotation']
                else:
                    rotation_angle = 0.0
            
            try:
                # v5.5: Polygon-Support vorbereiten
                crane_poly = None
                foundation_poly = None
                
                # Kranstellflächen-Polygon (wenn im Polygon-Modus)
                if use_polygons:
                    crane_poly = feature.geometry()
                
                # Fundament-Polygon (wenn aktiviert)
                if not use_circular_foundations and foundation_polygons_source is not None:
                    # Finde passendes Fundament für diesen Standort
                    site_id = current + 1
                    foundation_feat = self._get_foundation_polygon_for_site(
                        site_id, foundation_polygons_source
                    )
                    if foundation_feat:
                        foundation_poly = foundation_feat.geometry()
                        # Tiefe aus Attribut lesen (falls vorhanden)
                        if 'depth_m' in [f.name() for f in foundation_feat.fields()]:
                            foundation_depth = foundation_feat['depth_m']
                
                result = self._calculate_complete_earthwork(
                    dem_layer, point, current_platform_length, current_platform_width,
                    max_slope, slope_angle, slope_width,
                    foundation_diameter, foundation_depth, foundation_type,
                    swell_factor, compaction_factor, material_reuse,
                    optimization_method, cost_excavation, cost_transport,
                    cost_fill_import, cost_gravel, cost_compaction,
                    gravel_thickness, rotation_angle, feedback,
                    crane_polygon=crane_poly,
                    use_circular_foundation=use_circular_foundations,
                    foundation_polygon=foundation_poly,
                    site_id=current + 1)
                
                out_feature = self._create_output_feature(
                    point, fields, current + 1, result)
                sink.addFeature(out_feature)
                results.append(result)
                
                # Standflächen-Polygon erstellen (wenn aktiviert)
                if platform_sink is not None:
                    # Im Polygon-Modus: Original-Geometrie verwenden
                    # Im Punkt-Modus: Neues Rechteck erstellen
                    if use_polygons:
                        platform_polygon = feature.geometry()
                    else:
                        platform_polygon = self._create_platform_polygon(
                            point, current_platform_length, current_platform_width)
                    
                    # Safe-Funktion für Attribut-Werte
                    def safe_value(value, default=0.0):
                        if value is None or value == '':
                            return default
                        try:
                            return float(value)
                        except (ValueError, TypeError):
                            return default
                    
                    platform_feature = QgsFeature()
                    platform_feature.setGeometry(platform_polygon)
                    platform_feature.setFields(platform_fields)
                    platform_feature.setAttribute('id', current + 1)
                    platform_feature.setAttribute('length', safe_value(current_platform_length))
                    platform_feature.setAttribute('width', safe_value(current_platform_width))
                    platform_feature.setAttribute('area', safe_value(current_platform_length * current_platform_width))
                    platform_feature.setAttribute('cost_total', safe_value(result.get('cost_total', 0.0)))
                    platform_feature.setAttribute('found_vol', safe_value(result.get('foundation_volume', 0.0)))
                    platform_feature.setAttribute('total_cut', safe_value(result.get('total_cut', 0.0)))
                    platform_feature.setAttribute('total_fill', safe_value(result.get('total_fill', 0.0)))
                    platform_sink.addFeature(platform_feature)
                
                self._log_result(result, material_reuse, feedback)
                
            except Exception as e:
                feedback.reportError(f'Fehler: {str(e)}')
                continue
        
        # Report-Datei früh initialisieren (wird später für Profilordner benötigt)
        report_file = self.parameterAsFileOutput(parameters, self.OUTPUT_REPORT, context)
        
        # === PROFILSCHNITTE ERSTELLEN ===
        generate_profiles = self.parameterAsBool(parameters, self.GENERATE_PROFILES, context)
        profile_output_folder = self.parameterAsFileOutput(parameters, self.PROFILE_OUTPUT_FOLDER, context)
        vertical_exaggeration = self.parameterAsDouble(parameters, self.VERTICAL_EXAGGERATION, context)
        
        profile_dest_id = None
        
        if generate_profiles:
            if not MATPLOTLIB_AVAILABLE:
                feedback.pushWarning('⚠️ Matplotlib nicht verfügbar - Profile werden übersprungen!')
            else:
                # Ordner erstellen
                if not profile_output_folder:
                    report_dir = os.path.dirname(report_file) if report_file else os.getcwd()
                    profile_output_folder = os.path.join(report_dir, 'Profile')
                
                os.makedirs(profile_output_folder, exist_ok=True)
                feedback.pushInfo(f'\nErstelle Geländeschnitte in: {profile_output_folder}')
                
                # Profile-Sink (optional)
                profile_fields = self._create_profile_line_fields()
                profile_sink = None
                
                if self.OUTPUT_PROFILES in parameters and parameters[self.OUTPUT_PROFILES] is not None:
                    (profile_sink, profile_dest_id) = self.parameterAsSink(
                        parameters, self.OUTPUT_PROFILES, context,
                        profile_fields, QgsWkbTypes.LineString, feature_source.sourceCrs())
                
                # Für jeden Standort Profile generieren
                feature_source2 = self.parameterAsSource(parameters, self.INPUT_POINTS if not use_polygons else self.INPUT_POLYGONS, context)
                for idx, (feature, result) in enumerate(zip(feature_source2.getFeatures(), results)):
                    site_id = idx + 1
                    
                    # Punkt extrahieren (wie in Haupt-Schleife)
                    if use_polygons:
                        poly_props = self._extract_polygon_properties(feature)
                        point = poly_props['centroid']
                        curr_length = poly_props['length']
                        curr_width = poly_props['width']
                        rot_angle = poly_props['rotation']
                    else:
                        point = feature.geometry().asPoint()
                        curr_length = platform_length
                        curr_width = platform_width
                        rot_angle = 0.0
                        if auto_rotate and result.get('rotation_angle') is not None:
                            rot_angle = result.get('rotation_angle', 0.0)
                    
                    # Schnittlinien generieren
                    profile_lines = self._generate_profile_lines(
                        point, site_id, curr_length, curr_width,
                        foundation_diameter, slope_width, rot_angle)
                    
                    # Für jede Linie: Sampeln und Plotten
                    for pline_idx, pline in enumerate(profile_lines):
                        # In Layer speichern
                        if profile_sink:
                            pfeature = QgsFeature()
                            pfeature.setGeometry(pline['geometry'])
                            pfeature.setFields(profile_fields)
                            pfeature.setAttribute('id', idx * 8 + pline_idx)
                            pfeature.setAttribute('site_id', site_id)
                            pfeature.setAttribute('profile_type', pline['type'])
                            pfeature.setAttribute('length_m', pline['length'])
                            pfeature.setAttribute('auto_generated', True)
                            profile_sink.addFeature(pfeature)
                        
                        # Sampeln
                        try:
                            pdata = self._sample_profile_data(
                                pline['geometry'], dem_layer, result.get('platform_height', 0),
                                foundation_depth, point, curr_length, curr_width,
                                foundation_diameter, slope_angle, slope_width, rot_angle)
                            
                            # Plot erstellen
                            plot_filename = f"Site_{site_id}_{pline['type']}.png"
                            plot_path = os.path.join(profile_output_folder, plot_filename)
                            
                            self._create_profile_plot(
                                pdata, site_id, pline['type'], plot_path,
                                vertical_exaggeration,
                                {'cut': result.get('total_cut', 0), 'fill': result.get('total_fill', 0)})
                        except Exception as e:
                            feedback.pushWarning(f'⚠️ Profil {pline["type"]} für Standort {site_id} fehlgeschlagen: {str(e)}')
                            continue
                
                feedback.pushInfo(f'✅ Profile erstellt in: {profile_output_folder}')
        
        # HTML-Report generieren (v5.5: Neues Modul)
        if HTML_REPORT_AVAILABLE:
            feedback.pushInfo('📄 Generiere HTML-Report (Professional White Template)...')
            try:
                report_generator = HTMLReportGenerator()
                report_generator.create_report(
                    results_list=results,
                    output_path=report_file,
                    project_name="Windpark-Projekt",
                    profile_output_folder=profile_output_folder if generate_profiles else None
                )
                feedback.pushInfo('✅ Professional Report erstellt!')
            except Exception as e:
                feedback.pushWarning(f'⚠️ Neuer Report fehlgeschlagen: {e}')
                feedback.pushInfo('→ Fallback auf Legacy-Report...')
                html_content = self._create_html_report(
                    results, swell_factor, compaction_factor, material_reuse,
                    foundation_diameter, foundation_depth,
                    foundation_type_names[foundation_type],
                    platform_length, platform_width,
                    slope_angle, slope_width,
                    cost_excavation, cost_transport,
                    cost_fill_import, cost_gravel,
                    cost_compaction, gravel_thickness)
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
        else:
            feedback.pushInfo('📄 HTML Report Generator nicht verfügbar - nutze Legacy-Report')
            # Fallback: Alte Methode (Legacy)
            html_content = self._create_html_report(
                results, swell_factor, compaction_factor, material_reuse,
                foundation_diameter, foundation_depth,
                foundation_type_names[foundation_type],
                platform_length, platform_width,
                slope_angle, slope_width,
                cost_excavation, cost_transport,
                cost_fill_import, cost_gravel,
                cost_compaction, gravel_thickness)
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        feedback.pushInfo(f'\n✅ Fertig! Report: {report_file}')
        
        result_dict = {
            self.OUTPUT_POINTS: dest_id,
            self.OUTPUT_REPORT: report_file
        }
        
        if platform_dest_id is not None:
            result_dict[self.OUTPUT_PLATFORMS] = platform_dest_id
        
        if profile_dest_id is not None:
            result_dict[self.OUTPUT_PROFILES] = profile_dest_id
        
        return result_dict
    
    def _calculate_complete_earthwork(self, dem_layer, point, length, width,
                                     max_slope, slope_angle, slope_width,
                                     foundation_dia, foundation_depth, foundation_type,
                                     swell_factor, compaction_factor, material_reuse,
                                     optimization_method, cost_excavation, cost_transport,
                                     cost_fill_import, cost_gravel, cost_compaction,
                                     gravel_thickness, rotation_angle, feedback,
                                     crane_polygon=None, use_circular_foundation=True,
                                     foundation_polygon=None, site_id=None):
        """
        Vollständige Berechnung inkl. Kosten und Rotation (v5.5: Polygon-Support)
        
        Args (NEU in v5.5):
            crane_polygon: QgsGeometry - Wenn gesetzt, wird Polygon-Modus verwendet
            use_circular_foundation: bool - True = Kreis, False = Polygon
            foundation_polygon: QgsGeometry - Fundament-Polygon (wenn use_circular=False)
            site_id: int - Standort-ID (für Logging)
        """
        
        # FUNDAMENT-BERECHNUNG (v5.5: Zwei Modi)
        if use_circular_foundation:
            # MODUS A: Kreisförmiges Fundament (DEFAULT, wie v5.0)
            foundation_result = self._calculate_foundation_circular(
                dem_layer, point, foundation_dia, foundation_depth, foundation_type)
        else:
            # MODUS B: Polygon-Fundament (NEU in v5.5)
            if foundation_polygon is None:
                raise QgsProcessingException(
                    f'Standort {site_id}: Kein Fundament-Polygon gefunden, '
                    f'aber "Runde Fundamente" ist deaktiviert!'
                )
            foundation_result = self._calculate_foundation_polygon(
                foundation_polygon, foundation_depth, foundation_type, dem_layer
            )
        
        # KRANSTELLFLÄCHEN-BERECHNUNG (v5.5: Zwei Modi)
        if crane_polygon is not None:
            # MODUS A: Polygon-basiert (NEU in v5.5)
            crane_result = self._calculate_crane_pad_polygon(
                crane_polygon, dem_layer, slope_angle, slope_width, optimization_method
            )
        else:
            # MODUS B: Rechteck-basiert mit Rotation (wie v5.0)
            crane_result = self._calculate_crane_pad(
                dem_layer, point, length, width, max_slope, slope_angle,
                slope_width, swell_factor, compaction_factor, optimization_method, rotation_angle)
        
        if material_reuse:
            material_balance = self._calculate_material_balance(
                foundation_result["volume"], crane_result["total_cut"],
                crane_result["total_fill"], swell_factor, compaction_factor)
        else:
            material_balance = {
                'available': 0, 'required': 0, 'surplus': 0,
                'deficit': 0, 'reused': 0}
        
        # Kostenberechnung
        cost_result = self._calculate_costs(
            foundation_result['volume'],
            crane_result['total_cut'],
            crane_result['total_fill'],
            crane_result['platform_area'],
            material_balance,
            material_reuse,
            swell_factor,
            compaction_factor,
            cost_excavation,
            cost_transport,
            cost_fill_import,
            cost_gravel,
            cost_compaction,
            gravel_thickness
        )
        
        result = {
            'foundation_volume': round(foundation_result['volume'], 1),
            'foundation_depth_avg': round(foundation_depth, 2),
            'platform_height': crane_result['platform_height'],
            'terrain_min': crane_result['terrain_min'],
            'terrain_max': crane_result['terrain_max'],
            'terrain_mean': crane_result['terrain_mean'],
            'terrain_std': crane_result.get('terrain_std', 0),
            'terrain_range': crane_result.get('terrain_range', 0),
            'platform_cut': crane_result['platform_cut'],
            'platform_fill': crane_result['platform_fill'],
            'slope_cut': crane_result['slope_cut'],
            'slope_fill': crane_result['slope_fill'],
            'crane_total_cut': crane_result['total_cut'],
            'crane_total_fill': crane_result['total_fill'],
            'total_cut': round(foundation_result['volume'] + crane_result['total_cut'], 1),
            'total_fill': round(crane_result['total_fill'], 1),
            'net_volume': round(foundation_result['volume'] + crane_result['total_cut'] - crane_result['total_fill'], 1),
            'excavated_volume': round((foundation_result['volume'] + crane_result['total_cut']) * swell_factor, 1),
            'compacted_volume': round(crane_result['total_fill'] * compaction_factor, 1),
            'material_available': round(material_balance['available'], 1),
            'material_required': round(material_balance['required'], 1),
            'material_surplus': round(material_balance['surplus'], 1),
            'material_deficit': round(material_balance['deficit'], 1),
            'material_reused': round(material_balance['reused'], 1),
            'platform_area': crane_result['platform_area'],
            'total_area': crane_result.get('total_area', 0),
            # Kosten-Felder hinzufügen
            'cost_total': cost_result['cost_total'],
            'cost_excavation': cost_result['cost_excavation'],
            'cost_transport': cost_result['cost_transport'],
            'cost_fill': cost_result['cost_fill'],
            'cost_gravel': cost_result['cost_gravel'],
            'cost_compaction': cost_result['cost_compaction'],
            'cost_saving': cost_result['cost_saving'],
            'saving_pct': cost_result['saving_pct'],
            'gravel_vol': cost_result['gravel_vol'],
            'cost_total_without_reuse': cost_result['cost_total_without_reuse'],
            'cost_total_with_reuse': cost_result['cost_total_with_reuse']
        }
        
        return result
    
    def _calculate_foundation_circular(self, dem_layer, center_point, diameter, depth, foundation_type):
        """
        Berechnet Fundament-Volumen für kreisförmiges Fundament
        (Umbenannt in v5.5, Logik bleibt identisch zu v5.0)
        """
        radius = diameter / 2
        if foundation_type == 0:
            volume = math.pi * radius**2 * depth
        elif foundation_type == 1:
            cylinder_depth = depth * 0.6
            cone_depth = depth * 0.4
            volume_cylinder = math.pi * radius**2 * cylinder_depth
            volume_cone = (1/3) * math.pi * radius**2 * cone_depth
            volume = volume_cylinder + volume_cone
        else:
            volume = math.pi * radius**2 * depth * 0.8
        return {'volume': volume, 'diameter': diameter, 'depth': depth, 'type': foundation_type}
    
    def _calculate_foundation_polygon(self, foundation_polygon, depth, foundation_type,
                                      dem_raster, resolution=0.5):
        """
        Berechnet Fundament-Aushub für BELIEBIGE Polygon-Form (NEU in v5.5)
        
        Args:
            foundation_polygon: QgsGeometry - Fundament-Polygon (vom User)
            depth: float - Fundamenttiefe in Metern
            foundation_type: int - Typ (0=shallow, 1=deep, 2=pile)
            dem_raster: QgsRasterLayer - Digitales Geländemodell
            resolution: float - Sample-Auflösung (m)
        
        Returns:
            dict - {'volume': float, 'area': float, 'depth': float, 'type': int}
        """
        # 1. DEM samplen innerhalb Fundament-Polygon
        foundation_points = self._sample_dem_polygon(foundation_polygon, dem_raster, resolution)
        
        if len(foundation_points) == 0:
            raise QgsProcessingException('Keine DEM-Daten in Fundament-Polygon!')
        
        # 2. Mittlere Geländehöhe ermitteln
        elevations = [z for (x, y, z) in foundation_points]
        avg_existing_z = np.mean(elevations)
        
        # 3. Fundament-Sohle = Mittelwert - depth
        foundation_bottom = avg_existing_z - depth
        
        # 4. Cut-Volumen berechnen (Pixel-basiert)
        foundation_cut = 0.0
        cell_area = resolution * resolution
        
        for (x, y, existing_z) in foundation_points:
            if existing_z > foundation_bottom:
                cut_height = existing_z - foundation_bottom
                foundation_cut += cut_height * cell_area
        
        # 5. Typ-basierte Anpassung (wie bei circular)
        if foundation_type == 1:  # Tiefgründung mit Konus
            foundation_cut *= 1.1  # Zusätzliches Volumen für Konus
        elif foundation_type == 2:  # Pfahlgründung
            foundation_cut *= 0.8  # Weniger Aushub (Pfähle)
        
        # 6. Fläche berechnen
        foundation_area = foundation_polygon.area()
        
        return {
            'volume': round(foundation_cut, 1),
            'area': round(foundation_area, 1),
            'depth': depth,
            'type': foundation_type
        }
    
    def _get_foundation_polygon_for_site(self, site_id, foundation_polygon_layer):
        """
        Findet Fundament-Polygon für gegebenen Standort (NEU in v5.5)
        
        Args:
            site_id: int - WKA-Standort-ID
            foundation_polygon_layer: QgsVectorLayer - Layer mit Fundament-Polygonen
        
        Returns:
            QgsFeature mit Polygon-Geometrie + Attributen oder None
        """
        if foundation_polygon_layer is None:
            return None
        
        # Filter nach site_id
        from qgis.core import QgsExpression, QgsFeatureRequest
        expression = QgsExpression(f'"site_id" = {site_id}')
        request = QgsFeatureRequest(expression)
        
        features = list(foundation_polygon_layer.getFeatures(request))
        
        if len(features) == 0:
            return None
        elif len(features) > 1:
            # Warnung bei mehreren Treffern (nutze ersten)
            pass
        
        return features[0]
    
    def _calculate_crane_pad_polygon(self, crane_polygon, dem_raster, 
                                     slope_angle, slope_width, 
                                     optimization_method, resolution=0.5):
        """
        Berechnet Cut/Fill für BELIEBIGE Polygon-Form (NEU in v5.5)
        
        Args:
            crane_polygon: QgsGeometry - Kranstellflächen-Polygon
            dem_raster: QgsRasterLayer - DEM
            slope_angle: float - Böschungswinkel (Grad)
            slope_width: float - Böschungsbreite (m)
            optimization_method: int - 0=Mittelwert, 1=Min.Aushub, 2=Ausgeglichen
            resolution: float - Sample-Auflösung (m)
        
        Returns:
            dict - Volumina und Statistiken
        """
        # 1. Plattform-Bereich samplen
        platform_points = self._sample_dem_polygon(crane_polygon, dem_raster, resolution)
        
        if len(platform_points) == 0:
            raise QgsProcessingException('Keine DEM-Daten in Kranstellflächen-Polygon!')
        
        # 2. Plattform-Höhe optimieren (FIX: explizit float dtype!)
        elevations = np.asarray([float(z) for (_, _, z) in platform_points], dtype=float)
        
        if optimization_method == 0:  # Mittelwert
            platform_height = np.mean(elevations)
        elif optimization_method == 1:  # Min. Aushub
            platform_height = np.percentile(elevations, 40)
        else:  # Ausgeglichen (Cut/Fill-Balance)
            platform_height = self._optimize_balanced_cutfill(elevations)
        
        # 3. Böschungs-Polygon erstellen
        slope_polygon = self._create_slope_polygon(crane_polygon, slope_width)
        
        # 4. Böschungs-Bereich samplen
        slope_points = self._sample_dem_polygon(slope_polygon, dem_raster, resolution)
        
        # 5. Cut/Fill auf Plattform berechnen
        platform_cut = 0.0
        platform_fill = 0.0
        cell_area = resolution * resolution
        
        for (x, y, existing_z) in platform_points:
            diff = existing_z - platform_height
            if diff > 0:  # Cut
                platform_cut += diff * cell_area
            else:  # Fill
                platform_fill += abs(diff) * cell_area
        
        # 6. Cut/Fill auf Böschung berechnen
        slope_cut = 0.0
        slope_fill = 0.0
        
        for (x, y, existing_z) in slope_points:
            existing_z = float(existing_z)  # FIX: explizit float!
            point = QgsPointXY(x, y)
            target_z = self._calculate_slope_height(
                point, crane_polygon, platform_height, slope_angle, slope_width
            )
            
            diff = existing_z - target_z
            if diff > 0:  # Cut
                slope_cut += diff * cell_area
            else:  # Fill
                slope_fill += abs(diff) * cell_area
        
        # 7. Statistiken
        platform_area = crane_polygon.area()
        total_area = crane_polygon.buffer(slope_width, 16).area()
        
        return {
            'platform_height': round(platform_height, 2),
            'terrain_min': round(float(np.min(elevations)), 2),
            'terrain_max': round(float(np.max(elevations)), 2),
            'terrain_mean': round(float(np.mean(elevations)), 2),
            'terrain_std': round(float(np.std(elevations)), 2),
            'terrain_range': round(float(np.max(elevations) - np.min(elevations)), 2),
            'platform_cut': round(platform_cut, 1),
            'platform_fill': round(platform_fill, 1),
            'slope_cut': round(slope_cut, 1),
            'slope_fill': round(slope_fill, 1),
            'total_cut': round(platform_cut + slope_cut, 1),
            'total_fill': round(platform_fill + slope_fill, 1),
            'platform_area': round(platform_area, 1),
            'total_area': round(total_area, 1)
        }
    
    def _calculate_crane_pad(self, dem_layer, point, length, width, max_slope,
                            slope_angle, slope_width, swell_factor, compaction_factor,
                            optimization_method, rotation_angle=0.0):
        """Berechnet Kranstellflächen-Volumen mit optionaler Rotation"""
        provider = dem_layer.dataProvider()
        pixel_size_x = dem_layer.rasterUnitsPerPixelX()
        pixel_size_y = dem_layer.rasterUnitsPerPixelY()
        pixel_area = pixel_size_x * pixel_size_y
        
        total_width = length + 2 * slope_width
        total_height = width + 2 * slope_width
        
        dem_data, x_coords, y_coords = self._sample_dem_grid(
            provider, point, total_width, total_height, pixel_size_x, pixel_size_y)
        
        if dem_data is None or len(dem_data) == 0:
            raise QgsProcessingException('Keine DEM-Daten!')
        
        platform_mask = self._create_platform_mask(x_coords, y_coords, point, length, width, rotation_angle)
        platform_elevations = np.asarray(dem_data[platform_mask], dtype=float)  # FIX: explizit float!
        
        if len(platform_elevations) == 0:
            raise QgsProcessingException('Keine Plattform-Daten!')
        
        if optimization_method == 0:
            platform_height = np.mean(platform_elevations)
        elif optimization_method == 1:
            platform_height = np.percentile(platform_elevations, 40)
        else:
            platform_height = self._optimize_balanced_cutfill(platform_elevations)
        
        target_dem = self._create_target_dem(
            x_coords, y_coords, point, length, width,
            platform_height, slope_angle, slope_width, dem_data, rotation_angle)
        
        # Fix: Explizit float arrays verwenden (NumPy 1.20+ compatibility)
        dem_data_float = dem_data.astype(float)
        target_dem_float = target_dem.astype(float)
        diff_dem = dem_data_float - target_dem_float
        slope_mask = self._create_slope_mask(x_coords, y_coords, point, length, width, slope_width, rotation_angle)
        
        platform_cut = np.sum(np.maximum(diff_dem[platform_mask], 0)) * pixel_area
        platform_fill = np.sum(np.maximum(-diff_dem[platform_mask], 0)) * pixel_area
        slope_cut = np.sum(np.maximum(diff_dem[slope_mask], 0)) * pixel_area
        slope_fill = np.sum(np.maximum(-diff_dem[slope_mask], 0)) * pixel_area
        
        return {
            'platform_height': round(platform_height, 2),
            'terrain_min': round(float(np.min(platform_elevations)), 2),
            'terrain_max': round(float(np.max(platform_elevations)), 2),
            'terrain_mean': round(float(np.mean(platform_elevations)), 2),
            'terrain_std': round(float(np.std(platform_elevations)), 2),
            'terrain_range': round(float(np.max(platform_elevations) - np.min(platform_elevations)), 2),
            'platform_cut': round(platform_cut, 1),
            'platform_fill': round(platform_fill, 1),
            'slope_cut': round(slope_cut, 1),
            'slope_fill': round(slope_fill, 1),
            'total_cut': round(platform_cut + slope_cut, 1),
            'total_fill': round(platform_fill + slope_fill, 1),
            'platform_area': round(length * width, 1),
            'total_area': round(total_width * total_height, 1)
        }
    
    def _calculate_material_balance(self, foundation_volume, crane_cut, crane_fill,
                                    swell_factor, compaction_factor):
        """Berechnet Material-Bilanz"""
        available = foundation_volume * swell_factor
        required = crane_fill / compaction_factor
        if available >= required:
            surplus = available - required
            deficit = 0
            reused = required
        else:
            surplus = 0
            deficit = required - available
            reused = available
        return {
            'available': available, 'required': required,
            'surplus': surplus, 'deficit': deficit, 'reused': reused
        }
    
    def _calculate_costs(self, foundation_volume, crane_cut, crane_fill,
                        platform_area, material_balance, material_reuse,
                        swell_factor, compaction_factor,
                        cost_excavation, cost_transport, cost_fill_import,
                        cost_gravel, cost_compaction, gravel_thickness):
        """
        Berechnet detaillierte Kosten für Erdarbeiten
        
        Args:
            foundation_volume: Fundament-Aushubvolumen (m³)
            crane_cut: Kranflächen-Aushub (m³)
            crane_fill: Kranflächen-Auftrag (m³)
            platform_area: Plattformfläche (m²)
            material_balance: Dict mit Material-Bilanz (available, required, surplus, deficit, reused)
            material_reuse: Boolean - Wiederverwendung aktiv?
            swell_factor: Auflockerungsfaktor
            compaction_factor: Verdichtungsfaktor
            cost_excavation: Kosten pro m³ Aushub
            cost_transport: Kosten pro m³ Transport
            cost_fill_import: Kosten pro m³ Material-Einkauf
            cost_gravel: Kosten pro m³ Schotter
            cost_compaction: Kosten pro m³ Verdichtung
            gravel_thickness: Schotterschicht-Dicke (m)
        
        Returns:
            Dict mit allen Kosten-Komponenten
            
        Beispiel:
            >>> # Mit Wiederverwendung: Foundation 1000m³, Crane Cut 500m³, Fill 800m³
            >>> # Material verfügbar: 1250m³, benötigt: 941m³ → Überschuss: 309m³
            >>> result = _calculate_costs(1000, 500, 800, 1800, {...}, True, 1.25, 0.85, ...)
            >>> # Kosten: Aushub + Transport Überschuss + Wiederverwendung + Schotter
        """
        
        # A) BASIS-KOSTEN (immer)
        kosten_fundament_aushub = foundation_volume * cost_excavation
        kosten_fundament_transport = foundation_volume * swell_factor * cost_transport
        kosten_kranflaeche_aushub = crane_cut * cost_excavation
        
        # D) SCHOTTER-KOSTEN (immer)
        schotter_volumen = platform_area * gravel_thickness
        kosten_schotter = schotter_volumen * cost_gravel
        
        # B) KOSTEN MIT Material-Wiederverwendung
        if material_reuse:
            # Wiederverwendetes Material kostet nur Verdichtung
            kosten_wiederverwendung = material_balance['reused'] * cost_compaction
            
            # Überschuss muss abtransportiert werden
            kosten_ueberschuss = material_balance['surplus'] * cost_transport
            
            # Mangel muss eingekauft werden (inkl. Transport + Verdichtung)
            kosten_mangel = material_balance['deficit'] * (
                cost_fill_import + cost_transport + cost_compaction
            )
            
            # E) GESAMT-KOSTEN mit Wiederverwendung
            kosten_transport_gesamt = kosten_fundament_transport + kosten_ueberschuss
            kosten_fill_gesamt = kosten_mangel
            kosten_verdichtung_gesamt = kosten_wiederverwendung
            
            total_kosten_mit = (
                kosten_fundament_aushub +
                kosten_kranflaeche_aushub +
                kosten_wiederverwendung +
                kosten_ueberschuss +
                kosten_mangel +
                kosten_schotter
            )
        else:
            kosten_transport_gesamt = 0
            kosten_fill_gesamt = 0
            kosten_verdichtung_gesamt = 0
            total_kosten_mit = 0
        
        # C) KOSTEN OHNE Material-Wiederverwendung (für Vergleich)
        # Alles muss abtransportiert werden
        kosten_abtransport_ohne = (foundation_volume + crane_cut) * swell_factor * cost_transport
        
        # Alles für Fill muss eingekauft werden
        kosten_fill_ohne = crane_fill * (cost_fill_import + cost_transport + cost_compaction)
        
        total_kosten_ohne = (
            kosten_fundament_aushub +
            kosten_kranflaeche_aushub +
            kosten_abtransport_ohne +
            kosten_fill_ohne +
            kosten_schotter
        )
        
        # F) EINSPARUNG durch Wiederverwendung
        if material_reuse:
            total_kosten = total_kosten_mit
            einsparung = total_kosten_ohne - total_kosten_mit
            if total_kosten_ohne > 0:
                einsparung_prozent = (einsparung / total_kosten_ohne) * 100
            else:
                einsparung_prozent = 0
        else:
            total_kosten = total_kosten_ohne
            kosten_transport_gesamt = kosten_abtransport_ohne
            kosten_fill_gesamt = kosten_fill_ohne
            kosten_verdichtung_gesamt = crane_fill * cost_compaction
            einsparung = 0
            einsparung_prozent = 0
        
        # Gesamt-Kosten nach Kategorie
        kosten_aushub_gesamt = kosten_fundament_aushub + kosten_kranflaeche_aushub
        
        return {
            'cost_total': round(total_kosten, 2),
            'cost_excavation': round(kosten_aushub_gesamt, 2),
            'cost_transport': round(kosten_transport_gesamt, 2),
            'cost_fill': round(kosten_fill_gesamt, 2),
            'cost_gravel': round(kosten_schotter, 2),
            'cost_compaction': round(kosten_verdichtung_gesamt, 2),
            'cost_saving': round(einsparung, 2),
            'saving_pct': round(einsparung_prozent, 2),
            'gravel_vol': round(schotter_volumen, 2),
            'cost_total_without_reuse': round(total_kosten_ohne, 2),
            'cost_total_with_reuse': round(total_kosten_mit if material_reuse else 0, 2)
        }
    
    def _sample_dem_grid(self, provider, center_point, width, height, pixel_size_x, pixel_size_y):
        """Sampelt DEM-Daten mit provider.block() - VIEL schneller als identify()!"""
        start_x = center_point.x() - width / 2
        start_y = center_point.y() - height / 2
        
        # Extent definieren
        from qgis.core import QgsRectangle
        extent = QgsRectangle(start_x, start_y, start_x + width, start_y + height)
        
        # Pixelanzahl berechnen
        num_x = int(width / pixel_size_x) + 1
        num_y = int(height / pixel_size_y) + 1
        
        # SICHERHEIT: Cap bei 5000 Pixeln
        if num_x > 5000 or num_y > 5000:
            raise QgsProcessingException(
                f'DEM-Sampling-Block zu groß! ({num_x}×{num_y} Pixel)\n'
                f'→ CRS oder Plattformgröße ungültig!')
        
        # Block holen (nur EIN Raster-Zugriff!)
        block = provider.block(1, extent, num_x, num_y)
        
        # In NumPy konvertieren
        dem_data = np.zeros((num_y, num_x), dtype=np.float32)
        for i in range(num_y):
            for j in range(num_x):
                if block.isNoData(i, j):
                    dem_data[i, j] = np.nan
                else:
                    dem_data[i, j] = block.value(j, i)  # Achtung: block ist (col, row)!
        
        # NaN füllen
        if np.any(np.isnan(dem_data)):
            mean_value = np.nanmean(dem_data)
            if np.isnan(mean_value):
                mean_value = 0.0
            dem_data = np.where(np.isnan(dem_data), mean_value, dem_data)
        
        # Koordinaten wie zuvor
        x_coords = np.linspace(start_x, start_x + width, num_x)
        y_coords = np.linspace(start_y, start_y + height, num_y)
        
        return dem_data, x_coords, y_coords
    
    def _sample_dem_polygon(self, polygon_geom, dem_raster, resolution=0.5):
        """
        Sampelt DEM innerhalb beliebiger Polygon-Form (NEU in v5.5)
        
        Args:
            polygon_geom: QgsGeometry - Polygon (beliebige Form, auch Multi-Polygon)
            dem_raster: QgsRasterLayer - Digitales Geländemodell
            resolution: float - Sample-Auflösung in Metern (z.B. 0.5m)
        
        Returns:
            list of tuples: [(x, y, z), ...] - Koordinaten mit DEM-Höhe
            
        Beispiel:
            >>> polygon = QgsGeometry.fromWkt('POLYGON((0 0, 30 0, 30 20, 0 20, 0 0))')
            >>> points = self._sample_dem_polygon(polygon, dem_layer, 0.5)
            >>> print(len(points))  # Ca. 2400 Punkte (30m × 20m / 0.5²)
        """
        # 1. Bounding Box des Polygons
        bbox = polygon_geom.boundingBox()
        if bbox.isEmpty():
            raise QgsProcessingException('Polygon Bounding Box ist leer!')
        
        # 2. Grid-Punkte generieren
        x_min, y_min = bbox.xMinimum(), bbox.yMinimum()
        x_max, y_max = bbox.xMaximum(), bbox.yMaximum()
        
        # Grid-Arrays
        x_coords = np.arange(x_min, x_max + resolution, resolution)
        y_coords = np.arange(y_min, y_max + resolution, resolution)
        
        # 3. DEM-Provider für schnelles Sampling
        provider = dem_raster.dataProvider()
        
        # 4. Point-in-Polygon-Test + DEM-Sampling
        sample_points = []
        
        for x in x_coords:
            for y in y_coords:
                # Point-in-Polygon-Test
                point_geom = QgsGeometry.fromPointXY(QgsPointXY(x, y))
                
                if polygon_geom.contains(point_geom):
                    # DEM-Höhe sampeln (FIX: korrekte Tuple-Reihenfolge!)
                    val, ok = provider.sample(QgsPointXY(x, y), 1)
                    
                    if ok and val is not None:
                        z = float(val)
                        if not math.isnan(z):
                            sample_points.append((x, y, z))
        
        # 5. Validierung
        if len(sample_points) == 0:
            raise QgsProcessingException(
                f'Keine gültigen DEM-Daten innerhalb Polygon!\n'
                f'Bbox: {bbox.toString()}\n'
                f'Resolution: {resolution}m'
            )
        
        return sample_points
    
    def _create_slope_polygon(self, platform_polygon, slope_width):
        """
        Erstellt Böschungs-Polygon um beliebige Plattform-Form (NEU in v5.5)
        
        Args:
            platform_polygon: QgsGeometry - Plattform-Polygon
            slope_width: float - Böschungsbreite in Metern
        
        Returns:
            QgsGeometry - Böschungs-Zone (Ring um Plattform)
            
        Beispiel:
            >>> platform = QgsGeometry.fromWkt('POLYGON((0 0, 30 0, 30 20, 0 20, 0 0))')
            >>> slope = self._create_slope_polygon(platform, 10.0)
            >>> print(slope.area())  # Fläche der Böschungszone
        """
        # 1. Äußere Böschungs-Grenze (Buffer)
        outer_boundary = platform_polygon.buffer(
            distance=slope_width,
            segments=16  # Glatte Kurven bei runden Ecken
        )
        
        # 2. Böschungs-Zone = Differenz (Outer - Inner)
        slope_zone = outer_boundary.difference(platform_polygon)
        
        # 3. Validierung
        if slope_zone.isEmpty():
            raise QgsProcessingException('Böschungs-Polygon ist leer!')
        
        return slope_zone
    
    def _calculate_slope_height(self, point, platform_polygon, platform_height, 
                               slope_angle, slope_width):
        """
        Berechnet Ziel-Höhe für Punkt auf Böschung (NEU in v5.5)
        
        Args:
            point: QgsPointXY - Punkt auf Böschung
            platform_polygon: QgsGeometry - Plattform-Polygon
            platform_height: float - Plattform-Höhe (m ü. NN)
            slope_angle: float - Böschungswinkel (Grad)
            slope_width: float - Maximale Böschungsbreite (m)
        
        Returns:
            float - Ziel-Höhe an diesem Punkt (m ü. NN)
            
        Logik:
            - Distanz zum nächsten Plattform-Rand: d
            - Höhen-Differenz: Δh = d × tan(slope_angle)
            - Ziel-Höhe: h = platform_height ± Δh (je nach Cut/Fill)
        """
        # 1. Nächster Punkt auf Plattform-Rand
        point_geom = QgsGeometry.fromPointXY(point)
        nearest_geom = platform_polygon.nearestPoint(point_geom)
        nearest_point = nearest_geom.asPoint()
        
        # 2. Distanz berechnen
        distance = math.sqrt(
            (point.x() - nearest_point.x())**2 + 
            (point.y() - nearest_point.y())**2
        )
        
        # 3. Sicherheit: Clamp auf slope_width
        distance = min(distance, slope_width)
        
        # 4. Höhe interpolieren
        # Böschung fällt vom Plattform-Niveau ab
        slope_tan = math.tan(math.radians(slope_angle))
        height_drop = distance / slope_tan
        
        target_height = platform_height - height_drop
        
        return target_height
    
    def _get_rotation_matrix(self, rotation_angle):
        """
        Berechnet und cached Rotations-Matrix-Komponenten
        
        Args:
            rotation_angle: Rotationswinkel in Grad
            
        Returns:
            tuple: (cos_a, sin_a) für Rotation
        """
        angle_rad = math.radians(-rotation_angle)
        return math.cos(angle_rad), math.sin(angle_rad)
    
    def _create_platform_mask(self, x_coords, y_coords, center, length, width, rotation_angle=0.0):
        """
        Erstellt Plattform-Maske mit optionaler Rotation
        
        Args:
            rotation_angle: Rotationswinkel in Grad (0° = Nord, positiv = im Uhrzeigersinn)
        """
        X, Y = np.meshgrid(x_coords, y_coords)
        
        if abs(rotation_angle) < 0.1:
            # Keine Rotation: Schnelle Berechnung
            dx = np.abs(X - center.x())
            dy = np.abs(Y - center.y())
            return (dx <= length / 2) & (dy <= width / 2)
        else:
            # Mit Rotation: Koordinaten transformieren (mit cached Matrix)
            cos_a, sin_a = self._get_rotation_matrix(rotation_angle)
            
            # Verschiebe zum Ursprung, rotiere, prüfe Grenzen
            dx = X - center.x()
            dy = Y - center.y()
            
            # Rotation um Zentrum
            dx_rot = dx * cos_a - dy * sin_a
            dy_rot = dx * sin_a + dy * cos_a
            
            return (np.abs(dx_rot) <= width / 2) & (np.abs(dy_rot) <= length / 2)
    
    def _create_slope_mask(self, x_coords, y_coords, center, length, width, slope_width, rotation_angle=0.0):
        """
        Erstellt Böschungs-Maske mit optionaler Rotation
        
        Args:
            rotation_angle: Rotationswinkel in Grad (0° = Nord, positiv = im Uhrzeigersinn)
        """
        X, Y = np.meshgrid(x_coords, y_coords)
        
        if abs(rotation_angle) < 0.1:
            # Keine Rotation: Schnelle Berechnung
            dx = np.abs(X - center.x())
            dy = np.abs(Y - center.y())
            outer = (dx <= (length / 2 + slope_width)) & (dy <= (width / 2 + slope_width))
            inner = (dx <= length / 2) & (dy <= width / 2)
            return outer & ~inner
        else:
            # Mit Rotation (cached Matrix)
            cos_a, sin_a = self._get_rotation_matrix(rotation_angle)
            
            dx = X - center.x()
            dy = Y - center.y()
            
            dx_rot = dx * cos_a - dy * sin_a
            dy_rot = dx * sin_a + dy * cos_a
            
            outer = (np.abs(dx_rot) <= (width / 2 + slope_width)) & (np.abs(dy_rot) <= (length / 2 + slope_width))
            inner = (np.abs(dx_rot) <= width / 2) & (np.abs(dy_rot) <= length / 2)
            return outer & ~inner
    
    def _create_target_dem(self, x_coords, y_coords, center, length, width,
                          platform_height, slope_angle, slope_width, original_dem, rotation_angle=0.0):
        """
        Erstellt Ziel-DEM mit optionaler Rotation
        
        Args:
            rotation_angle: Rotationswinkel in Grad (0° = Nord, positiv = im Uhrzeigersinn)
        """
        X, Y = np.meshgrid(x_coords, y_coords)
        
        if abs(rotation_angle) < 0.1:
            # Keine Rotation
            dx = np.maximum(0, np.abs(X - center.x()) - length / 2)
            dy = np.maximum(0, np.abs(Y - center.y()) - width / 2)
            distance = np.sqrt(dx**2 + dy**2)
        else:
            # Mit Rotation: Koordinaten transformieren (cached Matrix)
            cos_a, sin_a = self._get_rotation_matrix(rotation_angle)
            
            x_centered = X - center.x()
            y_centered = Y - center.y()
            
            x_rot = x_centered * cos_a - y_centered * sin_a
            y_rot = x_centered * sin_a + y_centered * cos_a
            
            dx = np.maximum(0, np.abs(x_rot) - width / 2)
            dy = np.maximum(0, np.abs(y_rot) - length / 2)
            distance = np.sqrt(dx**2 + dy**2)
        target_dem = np.copy(original_dem)
        platform_mask = distance == 0
        target_dem[platform_mask] = platform_height
        slope_mask = (distance > 0) & (distance <= slope_width)
        if np.any(slope_mask):
            slope_tan = math.tan(math.radians(slope_angle))
            height_change = distance[slope_mask] / slope_tan
            # Fix: Explizit float arrays verwenden, nicht boolean
            slope_elevations = original_dem[slope_mask].astype(float)
            height_diff = slope_elevations - platform_height
            target_dem[slope_mask] = platform_height + np.sign(height_diff) * height_change
            target_dem[slope_mask] = np.where(
                slope_elevations > platform_height,
                np.minimum(target_dem[slope_mask], slope_elevations),
                np.maximum(target_dem[slope_mask], slope_elevations))
        return target_dem
    
    def _optimize_balanced_cutfill(self, elevations):
        """Optimiert Cut/Fill-Balance"""
        elevations = np.asarray(elevations, dtype=float)  # FIX: explizit float!
        heights = np.linspace(np.min(elevations), np.max(elevations), 50)
        best_height = np.mean(elevations)
        best_balance = float('inf')
        for h in heights:
            cut = np.sum(np.maximum(elevations - h, 0))
            fill = np.sum(np.maximum(h - elevations, 0))
            balance = abs(cut - fill)
            if balance < best_balance:
                best_balance = balance
                best_height = h
        return best_height
    
    def _optimize_platform_rotation(self, dem_layer, point, length, width,
                                    max_slope, slope_angle, slope_width,
                                    swell_factor, compaction_factor,
                                    optimization_method, rotation_step, feedback):
        """
        Optimiert Plattform-Rotation durch Testen verschiedener Winkel
        
        Args:
            rotation_step: Schrittweite in Grad (z.B. 15° → testet 0, 15, 30, ..., 345)
            
        Returns:
            Dict mit:
            - best_rotation: Optimaler Rotationswinkel
            - best_result: Berechnungs-Ergebnis für optimale Rotation
            - tested_angles: Liste aller getesteten Winkel
        """
        feedback.pushInfo(f'  🔄 Auto-Rotation: Teste Winkel 0°-{360-rotation_step}° (Schritt: {rotation_step}°)...')
        
        best_rotation = 0.0
        best_balance = float('inf')
        best_result = None
        tested_angles = []
        
        # Teste verschiedene Rotationen
        angles = np.arange(0, 360, rotation_step)
        
        for angle in angles:
            try:
                result = self._calculate_crane_pad(
                    dem_layer, point, length, width, max_slope, slope_angle,
                    slope_width, swell_factor, compaction_factor, optimization_method, angle)
                
                # Minimiere Ungleichgewicht zwischen Cut und Fill
                balance = abs(result['total_cut'] - result['total_fill'])
                
                tested_angles.append({
                    'angle': angle,
                    'balance': balance,
                    'cut': result['total_cut'],
                    'fill': result['total_fill']
                })
                
                if balance < best_balance:
                    best_balance = balance
                    best_rotation = angle
                    best_result = result
                    
            except Exception as e:
                feedback.pushWarning(f'  Rotation {angle}° fehlgeschlagen: {str(e)}')
                continue
        
        feedback.pushInfo(f'  ✅ Beste Rotation: {best_rotation:.1f}° (Balance: {best_balance:.1f} m³)')
        
        return {
            'best_rotation': best_rotation,
            'best_result': best_result,
            'tested_angles': tested_angles
        }
    
    def _create_profile_line_fields(self):
        """Felder für Schnittlinien-Layer"""
        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int))
        fields.append(QgsField('site_id', QVariant.Int))
        fields.append(QgsField('profile_type', QVariant.String, len=50))
        fields.append(QgsField('length_m', QVariant.Double, 'double', 10, 2))
        fields.append(QgsField('auto_generated', QVariant.Bool))
        return fields

    def _generate_profile_lines(self, center_point, site_id, platform_length, platform_width, 
                                foundation_diameter, slope_width, rotation_angle):
        """
        Generiert 8 Schnittlinien pro Standort:
        - 2 Fundament-Schnitte (NS, EW)
        - 2 Kranflächen-Hauptschnitte (Längs, Quer)
        - 4 Kranflächen-Rand-Schnitte (N, S, E, W)
        
        Returns: Liste von Dicts mit {geometry, type, length}
        """
        lines = []
        puffer = 10.0
        
        # Fundament-Schnitte (immer NS/EW, keine Rotation)
        found_len = foundation_diameter + 2*slope_width + 2*puffer
        # NS-Schnitt
        lines.append({
            'geometry': QgsGeometry.fromPolylineXY([
                QgsPointXY(center_point.x(), center_point.y() - found_len/2),
                QgsPointXY(center_point.x(), center_point.y() + found_len/2)
            ]),
            'type': 'foundation_ns',
            'length': found_len
        })
        # EW-Schnitt
        lines.append({
            'geometry': QgsGeometry.fromPolylineXY([
                QgsPointXY(center_point.x() - found_len/2, center_point.y()),
                QgsPointXY(center_point.x() + found_len/2, center_point.y())
            ]),
            'type': 'foundation_ew',
            'length': found_len
        })
        
        # Kranflächen-Schnitte (MIT Rotation)
        # Konvertiere Rotation für Berechnungen
        angle_rad = math.radians(rotation_angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        # Längsschnitt (parallel zur Längsachse)
        crane_long_len = platform_length + 2*slope_width + 2*puffer
        half_len = crane_long_len / 2
        # Richtungsvektor: rotiert
        dx_long = sin_a * half_len
        dy_long = cos_a * half_len
        lines.append({
            'geometry': QgsGeometry.fromPolylineXY([
                QgsPointXY(center_point.x() - dx_long, center_point.y() - dy_long),
                QgsPointXY(center_point.x() + dx_long, center_point.y() + dy_long)
            ]),
            'type': 'crane_longitudinal',
            'length': crane_long_len
        })
        
        # Querschnitt (parallel zur Querachse, 90° gedreht)
        crane_cross_len = platform_width + 2*slope_width + 2*puffer
        half_cross = crane_cross_len / 2
        dx_cross = cos_a * half_cross
        dy_cross = -sin_a * half_cross
        lines.append({
            'geometry': QgsGeometry.fromPolylineXY([
                QgsPointXY(center_point.x() - dx_cross, center_point.y() - dy_cross),
                QgsPointXY(center_point.x() + dx_cross, center_point.y() + dy_cross)
            ]),
            'type': 'crane_cross',
            'length': crane_cross_len
        })
        
        # Rand-Schnitte (vereinfacht: parallel zu Achsen am Rand)
        # North Edge
        offset_n = (platform_length/2) * cos_a, (platform_length/2) * sin_a
        lines.append({
            'geometry': QgsGeometry.fromPolylineXY([
                QgsPointXY(center_point.x() + offset_n[0] - dx_cross, center_point.y() + offset_n[1] - dy_cross),
                QgsPointXY(center_point.x() + offset_n[0] + dx_cross, center_point.y() + offset_n[1] + dy_cross)
            ]),
            'type': 'crane_edge_n',
            'length': crane_cross_len
        })
        
        # South Edge
        offset_s = -(platform_length/2) * cos_a, -(platform_length/2) * sin_a
        lines.append({
            'geometry': QgsGeometry.fromPolylineXY([
                QgsPointXY(center_point.x() + offset_s[0] - dx_cross, center_point.y() + offset_s[1] - dy_cross),
                QgsPointXY(center_point.x() + offset_s[0] + dx_cross, center_point.y() + offset_s[1] + dy_cross)
            ]),
            'type': 'crane_edge_s',
            'length': crane_cross_len
        })
        
        # East Edge
        offset_e = (platform_width/2) * cos_a, -(platform_width/2) * sin_a
        lines.append({
            'geometry': QgsGeometry.fromPolylineXY([
                QgsPointXY(center_point.x() + offset_e[0] - dx_long, center_point.y() + offset_e[1] - dy_long),
                QgsPointXY(center_point.x() + offset_e[0] + dx_long, center_point.y() + offset_e[1] + dy_long)
            ]),
            'type': 'crane_edge_e',
            'length': crane_long_len
        })
        
        # West Edge
        offset_w = -(platform_width/2) * cos_a, (platform_width/2) * sin_a
        lines.append({
            'geometry': QgsGeometry.fromPolylineXY([
                QgsPointXY(center_point.x() + offset_w[0] - dx_long, center_point.y() + offset_w[1] - dy_long),
                QgsPointXY(center_point.x() + offset_w[0] + dx_long, center_point.y() + offset_w[1] + dy_long)
            ]),
            'type': 'crane_edge_w',
            'length': crane_long_len
        })
        
        return lines

    def _sample_profile_data(self, profile_line_geom, dem_layer, platform_height, 
                            foundation_depth, center_point, platform_length, platform_width,
                            foundation_diameter, slope_angle, slope_width, rotation_angle):
        """
        Sampelt DEM entlang Schnittlinie in 0.5m Schritten
        
        Returns: Dict mit:
            - distances: np.array - Distanzen ab Start
            - existing_z: np.array - Bestehende Geländehöhen
            - planned_z: np.array - Geplante Höhen
            - material_type: np.array - 'cut', 'fill', 'unchanged'
        """
        # Linie in Punkte umwandeln mit Cap
        MAX_SAMPLES = 3000
        step_size = 0.5
        
        line_length = profile_line_geom.length()
        
        # Sample-Anzahl limitieren (verhindert Absturz bei langen Linien)
        if line_length / step_size > MAX_SAMPLES:
            step_size = line_length / MAX_SAMPLES
        
        num_samples = int(line_length / step_size) + 1
        distances = np.linspace(0, line_length, num_samples)
        
        existing_z = []
        planned_z = []
        
        provider = dem_layer.dataProvider()
        
        for dist in distances:
            # Punkt auf Linie bei Distanz
            point = profile_line_geom.interpolate(dist).asPoint()
            
            # DEM-Höhe sampeln (MIT sample() statt identify() - viel schneller!)
            val, ok = provider.sample(point, 1)
            z_existing = float(val) if (ok and val is not None) else 0.0
            existing_z.append(z_existing)
            
            # Geplante Höhe berechnen (basierend auf Position)
            dx_to_center = point.x() - center_point.x()
            dy_to_center = point.y() - center_point.y()
            dist_to_center = math.sqrt(dx_to_center**2 + dy_to_center**2)
            
            # Vereinfacht: Prüfe ob in Plattform, Böschung, oder Fundament
            if dist_to_center <= foundation_diameter/2:
                z_planned = existing_z[-1] - foundation_depth  # Fundament-Sohle
            elif dist_to_center <= max(platform_length, platform_width)/2:
                z_planned = platform_height  # Plattform
            elif dist_to_center <= max(platform_length, platform_width)/2 + slope_width:
                # Böschung (vereinfacht linear)
                z_planned = platform_height  # Vereinfachung
            else:
                z_planned = existing_z[-1]  # Unverändert
            
            planned_z.append(z_planned)
        
        # Material-Typ bestimmen
        existing_z = np.array(existing_z)
        planned_z = np.array(planned_z)
        material_type = np.where(existing_z > planned_z, 'cut',
                                 np.where(existing_z < planned_z, 'fill', 'unchanged'))
        
        return {
            'distances': distances,
            'existing_z': existing_z,
            'planned_z': planned_z,
            'material_type': material_type
        }

    def _create_profile_plot(self, profile_data, site_id, profile_type, output_path, 
                            vertical_exaggeration, site_info):
        """
        Erstellt Matplotlib-Plot und speichert als PNG
        
        Args:
            profile_data: Dict von _sample_profile_data
            site_info: Dict mit cut/fill Volumina für Info-Box
            output_path: Vollständiger Pfad zur PNG-Datei
            
        Returns: output_path wenn erfolgreich, None bei Fehler
        """
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
            
            distances = profile_data['distances']
            existing = profile_data['existing_z']
            planned = profile_data['planned_z']
            
            # Höhenübertreibung nur für Y-Achse (visuell)
            # NICHT für Daten (sonst falsche Darstellung)
            
            # Linien plotten
            ax.plot(distances, existing, 'k-', linewidth=2, label='Bestehendes Gelände')
            ax.plot(distances, planned, 'b-', linewidth=2, label='Geplante Oberfläche')
            
            # Füllflächen
            # Cut (rot)
            cut_mask = existing > planned
            if np.any(cut_mask):
                ax.fill_between(distances, existing, planned, where=cut_mask, 
                               color='red', alpha=0.3, label='Cut')
            
            # Fill (grün)
            fill_mask = existing < planned
            if np.any(fill_mask):
                ax.fill_between(distances, existing, planned, where=fill_mask,
                               color='green', alpha=0.3, label='Fill')
            
            # Achsen
            ax.set_xlabel('Distanz [m]', fontsize=12)
            ax.set_ylabel('Höhe [m ü. NN]', fontsize=12)
            ax.set_title(f'Profil: Standort {site_id} - {profile_type}', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='best')
            
            # Aspect Ratio setzen (damit Höhe nicht verzerrt wird)
            ax.set_aspect('auto')
            
            # Info-Box
            textstr = f"Cut: {site_info.get('cut', 0):.0f} m³\nFill: {site_info.get('fill', 0):.0f} m³"
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax.text(0.95, 0.95, textstr, transform=ax.transAxes, fontsize=10,
                   verticalalignment='top', horizontalalignment='right', bbox=props)
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight', transparent=False)
            plt.close(fig)
            fig.clear()
            del fig, ax
            
            return output_path
            
        except Exception as e:
            print(f"Fehler beim Erstellen des Profil-Plots: {e}")
            return None
    
    def _create_platform_fields(self):
        """Erstellt Felder für Standflächen-Polygone"""
        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int))
        fields.append(QgsField('length', QVariant.Double, 'double', 10, 2))
        fields.append(QgsField('width', QVariant.Double, 'double', 10, 2))
        fields.append(QgsField('area', QVariant.Double, 'double', 10, 2))
        fields.append(QgsField('cost_total', QVariant.Double, 'double', 12, 2))
        fields.append(QgsField('found_vol', QVariant.Double, 'double', 10, 2))
        fields.append(QgsField('total_cut', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('total_fill', QVariant.Double, 'double', 12, 1))
        return fields
    
    def _create_platform_polygon(self, center_point, length, width):
        """
        Erstellt Rechteck-Polygon für Standfläche (Nord-Süd ausgerichtet)
        
        Args:
            center_point: QgsPointXY - Zentrum der WKA
            length: Plattformlänge (Nord-Süd-Ausdehnung) in Metern
            width: Plattformbreite (Ost-West-Ausdehnung) in Metern
            
        Returns:
            QgsGeometry - Rechteck-Polygon
        """
        half_length = length / 2.0
        half_width = width / 2.0
        
        # Rechteck-Ecken definieren (gegen Uhrzeigersinn)
        # Nord-Süd = Y-Achse, Ost-West = X-Achse
        points = [
            QgsPointXY(center_point.x() - half_width, center_point.y() + half_length),  # NW
            QgsPointXY(center_point.x() + half_width, center_point.y() + half_length),  # NE
            QgsPointXY(center_point.x() + half_width, center_point.y() - half_length),  # SE
            QgsPointXY(center_point.x() - half_width, center_point.y() - half_length),  # SW
            QgsPointXY(center_point.x() - half_width, center_point.y() + half_length)   # NW (geschlossen)
        ]
        
        return QgsGeometry.fromPolygonXY([points])
    
    def _extract_polygon_properties(self, polygon_feature):
        """
        Extrahiert Eigenschaften aus einem Polygon-Feature
        
        Args:
            polygon_feature: QgsFeature mit Polygon-Geometrie
            
        Returns:
            Dict mit:
            - centroid: QgsPointXY - Zentrum des Polygons
            - length: float - Länge (Nord-Süd)
            - width: float - Breite (Ost-West)
            - rotation: float - Rotationswinkel in Grad (0° = Nord)
            
        Raises:
            QgsProcessingException: Wenn Polygon ungültig ist
        """
        geom = polygon_feature.geometry()
        
        # Validierung
        if geom is None or geom.isEmpty():
            raise QgsProcessingException('Polygon-Geometrie ist leer oder ungültig!')
        
        if geom.type() != QgsWkbTypes.PolygonGeometry:
            raise QgsProcessingException(f'Geometrie-Typ muss Polygon sein, ist aber: {geom.type()}')
        
        # Centroid berechnen
        centroid_geom = geom.centroid()
        if centroid_geom is None or centroid_geom.isEmpty():
            raise QgsProcessingException('Centroid konnte nicht berechnet werden!')
        centroid = centroid_geom.asPoint()
        
        # Oriented Bounding Box für präzisere Maße bei rotierten Polygonen
        try:
            obb_geom, obb_area, obb_angle, obb_width, obb_height = geom.orientedMinimumBoundingBox()
            
            # OBB gibt Width/Height, wir wollen Length (länger) und Width (kürzer)
            if obb_height >= obb_width:
                length = obb_height
                width = obb_width
            else:
                length = obb_width
                width = obb_height
            
            # Fallback auf normale BBox wenn OBB fehlschlägt
            if length == 0 or width == 0:
                bbox = geom.boundingBox()
                length = bbox.height()
                width = bbox.width()
        except Exception:
            # Fallback: Normale Bounding Box
            bbox = geom.boundingBox()
            if bbox.isEmpty():
                raise QgsProcessingException('Bounding Box ist leer!')
            length = bbox.height()
            width = bbox.width()
        
        # Validierung: Minimale Größe
        if length < 10.0 or width < 10.0:
            raise QgsProcessingException(f'Polygon zu klein! Länge: {length:.1f}m, Breite: {width:.1f}m (Min: 10m)')
        
        # Validierung: Maximale Größe
        if length > 200.0 or width > 200.0:
            raise QgsProcessingException(f'Polygon zu groß! Länge: {length:.1f}m, Breite: {width:.1f}m (Max: 200m)')
        
        # Rotation berechnen
        rotation = self._calculate_polygon_rotation(geom)
        
        return {
            'centroid': centroid,
            'length': length,
            'width': width,
            'rotation': rotation
        }
    
    def _calculate_polygon_rotation(self, polygon_geom):
        """
        Berechnet Rotationswinkel eines Rechteck-Polygons
        
        Args:
            polygon_geom: QgsGeometry - Polygon-Geometrie
            
        Returns:
            float - Rotationswinkel in Grad (0° = Nord, positiv = im Uhrzeigersinn)
            
        Methode:
            Verwendet die längste Kante des Polygons zur Rotations-Bestimmung
        """
        # Vertices extrahieren
        try:
            polygon_parts = polygon_geom.asPolygon()
            if not polygon_parts or len(polygon_parts) == 0:
                return 0.0
            vertices = polygon_parts[0]
        except Exception:
            return 0.0  # Fehler beim Extrahieren → keine Rotation
        
        if len(vertices) < 3:
            return 0.0  # Kein gültiges Polygon
        
        # Längste Kante finden
        max_length = 0
        longest_edge_angle = 0
        
        for i in range(len(vertices) - 1):
            p1 = vertices[i]
            p2 = vertices[i + 1]
            
            # Kantenlänge
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            edge_length = math.sqrt(dx**2 + dy**2)
            
            if edge_length > max_length:
                max_length = edge_length
                # Winkel berechnen (von Nord aus, im Uhrzeigersinn)
                # atan2 gibt Winkel von Ost-Achse, wir wollen von Nord
                angle_rad = math.atan2(dx, dy)
                angle_deg = math.degrees(angle_rad)
                longest_edge_angle = angle_deg
        
        return longest_edge_angle
    
    def _create_output_fields(self):
        """Erstellt Output-Felder"""
        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int))
        fields.append(QgsField('found_vol', QVariant.Double, 'double', 10, 2))
        fields.append(QgsField('found_depth', QVariant.Double, 'double', 10, 2))
        fields.append(QgsField('plat_height', QVariant.Double, 'double', 10, 2))
        fields.append(QgsField('terr_min', QVariant.Double, 'double', 10, 2))
        fields.append(QgsField('terr_max', QVariant.Double, 'double', 10, 2))
        fields.append(QgsField('terr_mean', QVariant.Double, 'double', 10, 2))
        fields.append(QgsField('terr_range', QVariant.Double, 'double', 10, 2))
        fields.append(QgsField('plat_cut', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('plat_fill', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('slope_cut', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('slope_fill', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('crane_cut', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('crane_fill', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('total_cut', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('total_fill', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('net_volume', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('excavated', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('compacted', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('mat_avail', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('mat_req', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('mat_surplus', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('mat_deficit', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('mat_reused', QVariant.Double, 'double', 12, 1))
        fields.append(QgsField('plat_area', QVariant.Double, 'double', 10, 1))
        fields.append(QgsField('cost_total', QVariant.Double, 'double', 12, 2))
        fields.append(QgsField('cost_excavation', QVariant.Double, 'double', 12, 2))
        fields.append(QgsField('cost_transport', QVariant.Double, 'double', 12, 2))
        fields.append(QgsField('cost_fill', QVariant.Double, 'double', 12, 2))
        fields.append(QgsField('cost_gravel', QVariant.Double, 'double', 12, 2))
        fields.append(QgsField('cost_compaction', QVariant.Double, 'double', 12, 2))
        fields.append(QgsField('cost_saving', QVariant.Double, 'double', 12, 2))
        fields.append(QgsField('saving_pct', QVariant.Double, 'double', 10, 2))
        fields.append(QgsField('gravel_vol', QVariant.Double, 'double', 10, 2))
        return fields
    
    def _create_output_feature(self, point, fields, feature_id, result):
        """Erstellt Output-Feature"""
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPointXY(point))
        feature.setFields(fields)
        
        # Sicher Attribute setzen (mit Fallback auf 0)
        def safe_get(key, default=0.0):
            value = result.get(key, default) if result else default
            # Sicherstellen, dass der Wert eine Zahl ist
            if value is None or value == '':
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        feature.setAttribute('id', feature_id)
        feature.setAttribute('found_vol', safe_get('foundation_volume'))
        feature.setAttribute('found_depth', safe_get('foundation_depth_avg'))
        feature.setAttribute('plat_height', safe_get('platform_height'))
        feature.setAttribute('terr_min', safe_get('terrain_min'))
        feature.setAttribute('terr_max', safe_get('terrain_max'))
        feature.setAttribute('terr_mean', safe_get('terrain_mean'))
        feature.setAttribute('terr_range', safe_get('terrain_range'))
        feature.setAttribute('plat_cut', safe_get('platform_cut'))
        feature.setAttribute('plat_fill', safe_get('platform_fill'))
        feature.setAttribute('slope_cut', safe_get('slope_cut'))
        feature.setAttribute('slope_fill', safe_get('slope_fill'))
        feature.setAttribute('crane_cut', safe_get('crane_total_cut'))
        feature.setAttribute('crane_fill', safe_get('crane_total_fill'))
        feature.setAttribute('total_cut', safe_get('total_cut'))
        feature.setAttribute('total_fill', safe_get('total_fill'))
        feature.setAttribute('net_volume', safe_get('net_volume'))
        feature.setAttribute('excavated', safe_get('excavated_volume'))
        feature.setAttribute('compacted', safe_get('compacted_volume'))
        feature.setAttribute('mat_avail', safe_get('material_available'))
        feature.setAttribute('mat_req', safe_get('material_required'))
        feature.setAttribute('mat_surplus', safe_get('material_surplus'))
        feature.setAttribute('mat_deficit', safe_get('material_deficit'))
        feature.setAttribute('mat_reused', safe_get('material_reused'))
        feature.setAttribute('plat_area', safe_get('platform_area'))
        feature.setAttribute('cost_total', safe_get('cost_total'))
        feature.setAttribute('cost_excavation', safe_get('cost_excavation'))
        feature.setAttribute('cost_transport', safe_get('cost_transport'))
        feature.setAttribute('cost_fill', safe_get('cost_fill'))
        feature.setAttribute('cost_gravel', safe_get('cost_gravel'))
        feature.setAttribute('cost_compaction', safe_get('cost_compaction'))
        feature.setAttribute('cost_saving', safe_get('cost_saving'))
        feature.setAttribute('saving_pct', safe_get('saving_pct'))
        feature.setAttribute('gravel_vol', safe_get('gravel_vol'))
        
        return feature
    
    def _log_result(self, result, material_reuse, feedback):
        """Gibt Ergebnis im Log aus"""
        feedback.pushInfo(f'  Fundament: {result["foundation_volume"]:,.1f} m³')
        feedback.pushInfo(f'  Kranfläche Cut: {result["crane_total_cut"]:,.1f} m³')
        feedback.pushInfo(f'  Kranfläche Fill: {result["crane_total_fill"]:,.1f} m³')
        feedback.pushInfo(f'  Gesamt Cut: {result["total_cut"]:,.1f} m³')
        feedback.pushInfo(f'  Gesamt Fill: {result["total_fill"]:,.1f} m³')
        if material_reuse:
            feedback.pushInfo(f'  Wiederverwendet: {result["material_reused"]:,.1f} m³')
            if result["material_surplus"] > 0:
                feedback.pushInfo(f'  Überschuss: {result["material_surplus"]:,.1f} m³')
            elif result["material_deficit"] > 0:
                feedback.pushInfo(f'  Mangel: {result["material_deficit"]:,.1f} m³')
        
        # Kosten-Ausgabe
        feedback.pushInfo(f'')
        feedback.pushInfo(f'  💰 KOSTEN:')
        feedback.pushInfo(f'     Gesamt:          {result["cost_total"]:>10,.2f} €')
        feedback.pushInfo(f'     Aushub:          {result["cost_excavation"]:>10,.2f} €')
        feedback.pushInfo(f'     Transport:       {result["cost_transport"]:>10,.2f} €')
        feedback.pushInfo(f'     Material-Fill:   {result["cost_fill"]:>10,.2f} €')
        feedback.pushInfo(f'     Schotter:        {result["cost_gravel"]:>10,.2f} €')
        feedback.pushInfo(f'     Verdichtung:     {result["cost_compaction"]:>10,.2f} €')
        if material_reuse and result["cost_saving"] > 0:
            feedback.pushInfo(f'     💚 Einsparung:   {result["cost_saving"]:>10,.2f} € ({result["saving_pct"]:.1f}%)')
    
    def _create_html_report(self, results, swell, compaction, material_reuse,
                           found_dia, found_depth, found_type_name,
                           platform_length=45.0, platform_width=40.0,
                           slope_angle=34.0, slope_width=10.0,
                           cost_excavation=8.0, cost_transport=12.0,
                           cost_fill_import=15.0, cost_gravel=25.0,
                           cost_compaction=5.0, gravel_thickness=0.5):
        """Erstellt HTML-Report"""
        total_foundation = sum(r['foundation_volume'] for r in results)
        total_crane_cut = sum(r['crane_total_cut'] for r in results)
        total_crane_fill = sum(r['crane_total_fill'] for r in results)
        total_cut = sum(r['total_cut'] for r in results)
        total_fill = sum(r['total_fill'] for r in results)
        
        # Kosten-Summen
        total_kosten = sum(r['cost_total'] for r in results)
        total_kosten_aushub = sum(r['cost_excavation'] for r in results)
        total_kosten_transport = sum(r['cost_transport'] for r in results)
        total_kosten_fill = sum(r['cost_fill'] for r in results)
        total_kosten_schotter = sum(r['cost_gravel'] for r in results)
        total_kosten_verdichtung = sum(r['cost_compaction'] for r in results)
        total_einsparung = sum(r['cost_saving'] for r in results)
        
        # Durchschnitt und Prozent
        num_sites = len(results)
        durchschnitt_kosten = total_kosten / num_sites if num_sites > 0 else 0
        
        # Einsparung in Prozent (gewichtet)
        if material_reuse:
            total_kosten_ohne = sum(r.get('cost_total_without_reuse', 0) for r in results)
            if total_kosten_ohne > 0:
                einsparung_prozent = (total_einsparung / total_kosten_ohne) * 100
            else:
                einsparung_prozent = 0
        else:
            total_kosten_ohne = 0
            einsparung_prozent = 0
        
        # Prozentuale Anteile
        if total_kosten > 0:
            anteil_aushub = (total_kosten_aushub / total_kosten) * 100
            anteil_transport = (total_kosten_transport / total_kosten) * 100
            anteil_fill = (total_kosten_fill / total_kosten) * 100
            anteil_schotter = (total_kosten_schotter / total_kosten) * 100
            anteil_verdichtung = (total_kosten_verdichtung / total_kosten) * 100
        else:
            anteil_aushub = anteil_transport = anteil_fill = anteil_schotter = anteil_verdichtung = 0
        
        html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Wind Turbine Earthwork Report v5.0</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f0f0f0; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #3498db; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .cut {{ color: #e74c3c; font-weight: bold; }}
        .fill {{ color: #27ae60; font-weight: bold; }}
        .cost {{ color: #f39c12; font-weight: bold; }}
        .info-box {{ background: #e8f4fd; padding: 20px; margin: 20px 0; border-left: 5px solid #3498db; border-radius: 5px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
        .summary-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .summary-card h3 {{ margin: 0 0 10px 0; font-size: 16px; opacity: 0.9; }}
        .summary-card .value {{ font-size: 32px; font-weight: bold; margin: 10px 0; }}
        .summary-card .unit {{ font-size: 14px; opacity: 0.8; }}
        .comparison-box {{ display: flex; justify-content: space-around; align-items: center; margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 10px; }}
        .compare-column {{ text-align: center; flex: 1; }}
        .compare-column h3 {{ color: #34495e; margin-bottom: 15px; }}
        .cost-value {{ font-size: 28px; font-weight: bold; color: #2c3e50; }}
        .compare-arrow {{ font-size: 24px; font-weight: bold; color: #95a5a6; padding: 0 20px; }}
        .saving-highlight {{ background: linear-gradient(135deg, #27ae60 0%, #229954 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: bold; margin-top: 15px; }}
        .cost-breakdown {{ background: #fff; border: 2px solid #3498db; border-radius: 8px; padding: 15px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌬️ Windkraftanlagen - Erdarbeitsberechnung v5.0</h1>
        
        <div class="info-box">
            <strong>📋 Projekt-Parameter:</strong><br><br>
            <strong>Plattform:</strong><br>
            • Länge: {platform_length}m | Breite: {platform_width}m<br>
            • Fläche: {platform_length * platform_width}m²<br><br>
            
            <strong>Fundament:</strong><br>
            • Durchmesser: {found_dia}m | Tiefe: {found_depth}m<br>
            • Typ: {found_type_name}<br><br>
            
            <strong>Böschung:</strong><br>
            • Winkel: {slope_angle}° | Breite: {slope_width}m<br><br>
            
            <strong>Material:</strong><br>
            • Swell-Faktor: {swell:.2f} | Compaction-Faktor: {compaction:.2f}<br>
            • Material-Wiederverwendung: {"✓ Aktiviert" if material_reuse else "✗ Deaktiviert"}<br>
            • Schotter-Schichtdicke: {gravel_thickness}m<br><br>
            
            <strong>Kostenansätze (€/m³):</strong><br>
            • Aushub: {cost_excavation:.2f} | Transport: {cost_transport:.2f}<br>
            • Material-Einkauf: {cost_fill_import:.2f} | Verdichtung: {cost_compaction:.2f}<br>
            • Schotter-Einbau: {cost_gravel:.2f}
        </div>
        
        <h2>💰 Kosten-Übersicht</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <h3>Gesamt-Kosten</h3>
                <div class="value">{total_kosten:,.0f} €</div>
                <div class="unit">Alle {num_sites} Standorte</div>
            </div>
            <div class="summary-card">
                <h3>Durchschnitt</h3>
                <div class="value">{durchschnitt_kosten:,.0f} €</div>
                <div class="unit">Pro WKA-Standort</div>
            </div>"""
        
        if material_reuse and total_einsparung > 0:
            html += f"""
            <div class="summary-card" style="background: linear-gradient(135deg, #27ae60 0%, #229954 100%);">
                <h3>💚 Einsparung</h3>
                <div class="value">{total_einsparung:,.0f} €</div>
                <div class="unit">{einsparung_prozent:.1f}% durch Wiederverwendung</div>
            </div>"""
        
        html += f"""
        </div>
        
        <h2>📊 Volumen-Zusammenfassung</h2>
        <table>
            <tr>
                <th>Komponente</th>
                <th>Volumen (m³)</th>
            </tr>
            <tr>
                <td>Fundamente (gesamt)</td>
                <td class="cut">{total_foundation:,.0f}</td>
            </tr>
            <tr>
                <td>Kranflächen Cut</td>
                <td class="cut">{total_crane_cut:,.0f}</td>
            </tr>
            <tr>
                <td>Kranflächen Fill</td>
                <td class="fill">{total_crane_fill:,.0f}</td>
            </tr>
            <tr style="background: #e8f4fd; font-weight: bold;">
                <td>GESAMT Cut</td>
                <td class="cut">{total_cut:,.0f}</td>
            </tr>
            <tr style="background: #e8f4fd; font-weight: bold;">
                <td>GESAMT Fill</td>
                <td class="fill">{total_fill:,.0f}</td>
            </tr>
        </table>
        
        <h2>💶 Kosten-Aufschlüsselung</h2>
        <table>
            <thead>
                <tr>
                    <th>Kostenart</th>
                    <th>Gesamt (€)</th>
                    <th>Anteil (%)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Aushub (Fundament + Kranfläche)</td>
                    <td class="cost">{total_kosten_aushub:,.2f}</td>
                    <td>{anteil_aushub:.1f}%</td>
                </tr>
                <tr>
                    <td>Transport / Abtransport</td>
                    <td class="cost">{total_kosten_transport:,.2f}</td>
                    <td>{anteil_transport:.1f}%</td>
                </tr>
                <tr>
                    <td>Material-Einkauf</td>
                    <td class="cost">{total_kosten_fill:,.2f}</td>
                    <td>{anteil_fill:.1f}%</td>
                </tr>
                <tr>
                    <td>Schotter-Einbau</td>
                    <td class="cost">{total_kosten_schotter:,.2f}</td>
                    <td>{anteil_schotter:.1f}%</td>
                </tr>
                <tr>
                    <td>Verdichtung</td>
                    <td class="cost">{total_kosten_verdichtung:,.2f}</td>
                    <td>{anteil_verdichtung:.1f}%</td>
                </tr>
                <tr style="background: #e8f4fd; font-weight: bold;">
                    <td>GESAMT</td>
                    <td class="cost">{total_kosten:,.2f}</td>
                    <td>100.0%</td>
                </tr>
            </tbody>
        </table>"""
        
        # Vergleichsbox nur wenn Material-Wiederverwendung aktiv
        if material_reuse and total_kosten_ohne > 0:
            html += f"""
        
        <h2>♻️ Kosten-Vergleich: Mit vs. Ohne Wiederverwendung</h2>
        <div class="comparison-box">
            <div class="compare-column">
                <h3>MIT Wiederverwendung</h3>
                <div class="cost-value">{total_kosten:,.0f} €</div>
            </div>
            <div class="compare-arrow">⟷</div>
            <div class="compare-column">
                <h3>OHNE Wiederverwendung</h3>
                <div class="cost-value">{total_kosten_ohne:,.0f} €</div>
            </div>
        </div>
        <div class="saving-highlight">
            💰 Einsparung: {total_einsparung:,.0f} € ({einsparung_prozent:.1f}%)
        </div>"""
        
        html += """
        
        <h2>📍 Details pro Standort</h2>
        <table>
            <thead>
                <tr>
                    <th>WKA</th>
                    <th>Fundament (m³)</th>
                    <th>Kran Cut (m³)</th>
                    <th>Kran Fill (m³)</th>
                    <th>Total Cut (m³)</th>
                    <th>Total Fill (m³)</th>
                    <th>Netto (m³)</th>
                    <th>Kosten (€)</th>"""
        
        if material_reuse:
            html += """
                    <th>Einsparung (€)</th>"""
        
        html += """
                </tr>
            </thead>
            <tbody>
"""
        
        for i, r in enumerate(results, 1):
            html += f"""
                <tr>
                    <td><strong>WKA-{i}</strong></td>
                    <td class="cut">{r['foundation_volume']:,.0f}</td>
                    <td class="cut">{r['crane_total_cut']:,.0f}</td>
                    <td class="fill">{r['crane_total_fill']:,.0f}</td>
                    <td class="cut">{r['total_cut']:,.0f}</td>
                    <td class="fill">{r['total_fill']:,.0f}</td>
                    <td>{r['net_volume']:,.0f}</td>
                    <td class="cost">{r['cost_total']:,.0f}</td>"""
            
            if material_reuse:
                html += f"""
                    <td class="fill">{r['cost_saving']:,.0f}</td>"""
            
            html += """
                </tr>
"""
        
        html += f"""
                <tr style="background: #e8f4fd; font-weight: bold;">
                    <td><strong>SUMME</strong></td>
                    <td class="cut">{total_foundation:,.0f}</td>
                    <td class="cut">{total_crane_cut:,.0f}</td>
                    <td class="fill">{total_crane_fill:,.0f}</td>
                    <td class="cut">{total_cut:,.0f}</td>
                    <td class="fill">{total_fill:,.0f}</td>
                    <td>{total_cut - total_fill:,.0f}</td>
                    <td class="cost">{total_kosten:,.0f}</td>"""
        
        if material_reuse:
            html += f"""
                    <td class="fill">{total_einsparung:,.0f}</td>"""
        
        html += """
                </tr>
            </tbody>
        </table>
        
        <div class="info-box" style="margin-top: 40px;">
            <strong>Wind Turbine Earthwork Calculator v5.0</strong><br>
            Erstellt mit QGIS Processing Framework<br>
            © 2025
        </div>
    </div>
</body>
</html>
"""
        return html