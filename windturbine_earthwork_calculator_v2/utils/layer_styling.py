"""
Layer styling utilities for Wind Turbine Earthwork Calculator V2

Provides functions for styling raster layers with contour rendering and labels.
"""

from qgis.core import (
    QgsRasterLayer,
    QgsVectorLayer,
    QgsProject,
    QgsContrastEnhancement,
    QgsRasterContourRenderer,
    QgsPalLayerSettings,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsVectorLayerSimpleLabeling,
    QgsPropertyCollection,
    QgsProperty,
    QgsRuleBasedLabeling,
    QgsCoordinateReferenceSystem
)
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtGui import QColor, QFont


def apply_contour_styling_to_raster(raster_layer, contour_interval=1.0, index_interval=5.0):
    """
    Apply contour rendering to a raster layer.

    Args:
        raster_layer (QgsRasterLayer): The raster layer to style
        contour_interval (float): Interval between contour lines in meters (default: 1.0)
        index_interval (float): Interval for index contours in meters (default: 5.0)

    Returns:
        bool: True if successful, False otherwise
    """
    if not raster_layer or not raster_layer.isValid():
        return False

    try:
        # Create contour renderer
        renderer = QgsRasterContourRenderer(raster_layer.dataProvider())

        # Set contour interval (regular contour lines every 1m)
        renderer.setContourInterval(contour_interval)

        # Set index contour interval (thicker lines every 5m)
        renderer.setContourIndexInterval(index_interval)

        # Create symbol for regular contours (thin black line)
        from qgis.core import QgsLineSymbol, QgsSimpleLineSymbolLayer
        contour_symbol = QgsLineSymbol.createSimple({
            'line_color': '35,35,35,255',
            'line_width': '0.26',
            'line_width_unit': 'MM',
            'line_style': 'solid',
            'capstyle': 'square',
            'joinstyle': 'bevel'
        })
        renderer.setContourSymbol(contour_symbol)

        # Create symbol for index contours (thicker black line)
        index_symbol = QgsLineSymbol.createSimple({
            'line_color': '35,35,35,255',
            'line_width': '0.5',
            'line_width_unit': 'MM',
            'line_style': 'solid',
            'capstyle': 'square',
            'joinstyle': 'bevel'
        })
        renderer.setContourIndexSymbol(index_symbol)

        # Set downscale factor for performance
        renderer.setDownscale(4.0)

        # Apply renderer to layer
        raster_layer.setRenderer(renderer)

        # Trigger repaint
        raster_layer.triggerRepaint()

        return True

    except Exception as e:
        print(f"Error applying contour styling: {e}")
        return False


def add_contour_labels_to_layer(raster_layer, label_index_only=True):
    """
    Add labels to contour lines on a raster layer.

    Note: QGIS contour renderer doesn't directly support labels.
    This function is a placeholder for future implementation or
    requires generating a vector contour layer separately.

    Args:
        raster_layer (QgsRasterLayer): The raster layer with contour rendering
        label_index_only (bool): If True, only label index contours

    Returns:
        bool: True if successful, False otherwise
    """
    # Note: Direct labeling of raster contours is not supported in QGIS
    # Labels would need to be added to a vector contour layer instead
    # This is a known limitation of the contour renderer

    # For now, return False to indicate this isn't implemented
    # A workaround would be to:
    # 1. Generate vector contours using gdal:contour
    # 2. Add labels to the vector layer
    # 3. Display both raster (for visualization) and vector (for labels)

    return False


def load_dem_with_contours_to_map(dem_path, layer_name="DEM Contours",
                                   contour_interval=1.0, index_interval=5.0):
    """
    Load a DEM raster to the QGIS map with contour rendering applied.

    Args:
        dem_path (str): Path to the DEM raster file
        layer_name (str): Name for the layer in QGIS (default: "DEM Contours")
        contour_interval (float): Interval between contour lines (default: 1.0m)
        index_interval (float): Interval for index contours (default: 5.0m)

    Returns:
        QgsRasterLayer: The loaded and styled raster layer, or None if failed
    """
    try:
        # Create raster layer
        raster_layer = QgsRasterLayer(dem_path, layer_name)

        if not raster_layer.isValid():
            print(f"Failed to load raster layer from {dem_path}")
            return None

        # Apply contour styling
        success = apply_contour_styling_to_raster(
            raster_layer,
            contour_interval=contour_interval,
            index_interval=index_interval
        )

        if not success:
            print("Failed to apply contour styling")
            return None

        # Add to project
        QgsProject.instance().addMapLayer(raster_layer)

        return raster_layer

    except Exception as e:
        print(f"Error loading DEM with contours: {e}")
        return None


def create_vector_contours_with_labels(dem_path, output_path,
                                       contour_interval=1.0, index_interval=5.0):
    """
    Create vector contour lines from DEM with labels for index contours.

    This uses GDAL to generate actual vector contour lines which can be labeled.

    Args:
        dem_path (str): Path to the DEM raster file
        output_path (str): Path for output vector contours (GeoPackage)
        contour_interval (float): Interval between contour lines (default: 1.0m)
        index_interval (float): Interval for index contours (default: 5.0m)

    Returns:
        QgsVectorLayer: The contour vector layer with labels, or None if failed
    """
    try:
        import processing
        from qgis.core import QgsVectorLayer

        # Generate contours using GDAL
        result = processing.run("gdal:contour", {
            'INPUT': dem_path,
            'BAND': 1,
            'INTERVAL': contour_interval,
            'FIELD_NAME': 'ELEV',
            'CREATE_3D': False,
            'IGNORE_NODATA': False,
            'NODATA': None,
            'OFFSET': 0,
            'EXTRA': '',
            'OUTPUT': output_path
        })

        contour_layer = QgsVectorLayer(result['OUTPUT'], 'Contour Lines', 'ogr')

        if not contour_layer.isValid():
            return None

        # Configure labels for index contours only
        # Index contours are those where elevation is divisible by index_interval
        layer_settings = QgsPalLayerSettings()
        layer_settings.fieldName = 'ELEV'
        layer_settings.enabled = True

        # Text format
        text_format = QgsTextFormat()
        text_format.setFont(QFont('Arial', 8))
        text_format.setSize(8)
        text_format.setColor(QColor(0, 0, 0))

        # Text buffer (white outline)
        buffer_settings = QgsTextBufferSettings()
        buffer_settings.setEnabled(True)
        buffer_settings.setSize(0.5)
        buffer_settings.setColor(QColor(255, 255, 255))
        text_format.setBuffer(buffer_settings)

        layer_settings.setFormat(text_format)

        # Placement settings for lines
        layer_settings.placement = QgsPalLayerSettings.Line
        layer_settings.lineSettings().setPlacementFlags(
            QgsPalLayerSettings.OnLine | QgsPalLayerSettings.MapOrientation
        )

        # Filter to only show labels on index contours
        # Use expression to check if ELEV is divisible by index_interval
        layer_settings.dataDefinedProperties().setProperty(
            QgsPalLayerSettings.Show,
            QgsProperty.fromExpression(f'"ELEV" % {index_interval} = 0')
        )

        # Apply labeling
        labeling = QgsVectorLayerSimpleLabeling(layer_settings)
        contour_layer.setLabeling(labeling)
        contour_layer.setLabelsEnabled(True)

        # Add to project
        QgsProject.instance().addMapLayer(contour_layer)

        return contour_layer

    except Exception as e:
        print(f"Error creating vector contours with labels: {e}")
        import traceback
        traceback.print_exc()
        return None


def add_labels_to_profile_lines(layer, label_field='type'):
    """
    Add labels to profile/cross-section lines.

    Args:
        layer (QgsVectorLayer): The vector layer with profile lines
        label_field (str): Field name to use for labels (default: 'type')

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not layer or not layer.isValid():
            return False

        # Configure label settings
        layer_settings = QgsPalLayerSettings()
        layer_settings.fieldName = label_field
        layer_settings.enabled = True

        # Text format
        text_format = QgsTextFormat()
        text_format.setFont(QFont('Arial', 10, QFont.Bold))
        text_format.setSize(10)
        text_format.setColor(QColor(0, 0, 139))  # Dark blue

        # Text buffer (white outline)
        buffer_settings = QgsTextBufferSettings()
        buffer_settings.setEnabled(True)
        buffer_settings.setSize(1.0)
        buffer_settings.setColor(QColor(255, 255, 255))
        text_format.setBuffer(buffer_settings)

        layer_settings.setFormat(text_format)

        # Placement settings for lines
        layer_settings.placement = QgsPalLayerSettings.Line
        layer_settings.lineSettings().setPlacementFlags(
            QgsPalLayerSettings.OnLine | QgsPalLayerSettings.MapOrientation
        )

        # Center the label on the line
        layer_settings.dist = 0
        layer_settings.distUnits = QgsPalLayerSettings.MM

        # Apply labeling
        labeling = QgsVectorLayerSimpleLabeling(layer_settings)
        layer.setLabeling(labeling)
        layer.setLabelsEnabled(True)

        # Trigger repaint
        layer.triggerRepaint()

        return True

    except Exception as e:
        print(f"Error adding labels to profile lines: {e}")
        import traceback
        traceback.print_exc()
        return False
