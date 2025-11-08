"""
Main plugin class for Wind Turbine Earthwork Calculator V2
"""

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QCoreApplication
from .processing_provider.provider import WindTurbineProvider


class WindTurbineEarthworkCalculatorPlugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        Args:
            iface (QgsInterface): An interface instance that will be passed to
                this class which provides the hook by which you can manipulate
                the QGIS application at run time.
        """
        self.iface = iface
        self.provider = None

    def initProcessing(self):
        """Initialize the Processing provider"""
        self.provider = WindTurbineProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        self.initProcessing()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)

    @staticmethod
    def tr(message):
        """Get the translation for a string using Qt translation API.

        Args:
            message (str): String for translation.

        Returns:
            str: Translated string.
        """
        return QCoreApplication.translate('WindTurbineEarthworkCalculator', message)
