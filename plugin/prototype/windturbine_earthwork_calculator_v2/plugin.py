"""
Main plugin class for Wind Turbine Earthwork Calculator V2
"""

import os
from pathlib import Path

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .processing_provider.provider import WindTurbineProvider
from .gui.main_dialog import MainDialog
from .core.workflow_runner import WorkflowRunner


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
        self.action = None
        self.dialog = None
        self.workflow_runner = None

    def initProcessing(self):
        """Initialize the Processing provider"""
        self.provider = WindTurbineProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        self.initProcessing()
        
        # Create action for toolbar/menu
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.action = QAction(
            QIcon(icon_path) if os.path.exists(icon_path) else QIcon(),
            "Erdmassenberechnung WKA",
            self.iface.mainWindow()
        )
        self.action.setWhatsThis("Erdmassenberechnung für Windenergieanlagen")
        self.action.setStatusTip("Optimierung der Plattformhöhe für WKA-Kranstellflächen")
        self.action.triggered.connect(self.run)
        
        # Add toolbar button
        self.iface.addToolBarIcon(self.action)
        
        # Add menu item
        self.iface.addPluginToMenu("&Windenergie", self.action)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
        
        # Remove toolbar/menu
        if self.action:
            self.iface.removePluginMenu("&Windenergie", self.action)
            self.iface.removeToolBarIcon(self.action)
    
    def run(self):
        """Run the plugin - show dialog."""
        # Create dialog if not exists
        if not self.dialog:
            self.dialog = MainDialog(self.iface.mainWindow())
            self.dialog.processing_requested.connect(self._on_processing_requested)
        
        # Show dialog
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
    
    def _on_processing_requested(self, params):
        """Handle processing request from dialog."""
        # Create workflow runner
        self.workflow_runner = WorkflowRunner(self.iface, params, self.dialog)
        self.workflow_runner.start()

    @staticmethod
    def tr(message):
        """Get the translation for a string using Qt translation API.

        Args:
            message (str): String for translation.

        Returns:
            str: Translated string.
        """
        return QCoreApplication.translate('WindTurbineEarthworkCalculator', message)
