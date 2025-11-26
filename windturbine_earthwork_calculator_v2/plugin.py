"""
Main plugin class for Wind Turbine Earthwork Calculator V2
"""

import os
import sys
from pathlib import Path

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox

from .processing_provider.provider import WindTurbineProvider
from .gui.main_dialog import MainDialog
from .core.workflow_runner import WorkflowRunner


def check_dependencies():
    """
    Check if required dependencies are available.

    Returns:
        tuple: (all_available, missing_packages, error_messages)
    """
    missing = []
    errors = []

    # Check ezdxf
    try:
        import ezdxf
    except ImportError as e:
        missing.append('ezdxf')
        errors.append(f"ezdxf: {e}")

    # Check shapely
    try:
        import shapely
    except ImportError as e:
        missing.append('shapely')
        errors.append(f"shapely: {e}")

    # Check requests
    try:
        import requests
    except ImportError as e:
        missing.append('requests')
        errors.append(f"requests: {e}")

    return len(missing) == 0, missing, errors


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
        icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'icon.png')
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
        # Check dependencies first
        all_available, missing, errors = check_dependencies()

        if not all_available:
            # Show warning dialog with installation instructions
            python_exe = sys.executable
            site_packages = [p for p in sys.path if 'site-packages' in p.lower()]

            missing_str = ' '.join(missing)
            errors_str = '<br>'.join(errors)

            msg = (
                f"<b>Fehlende Python-Pakete:</b><br>"
                f"{', '.join(missing)}<br><br>"
                f"<b>Fehlermeldungen:</b><br>"
                f"{errors_str}<br><br>"
                f"<b>Python-Umgebung:</b><br>"
                f"{python_exe}<br><br>"
                f"<b>Installation für QGIS unter Windows:</b><br>"
                f"1. Öffnen Sie die OSGeo4W Shell<br>"
                f"   (Start → OSGeo4W → OSGeo4W Shell)<br>"
                f"2. Führen Sie aus:<br>"
                f"   <code>pip install {missing_str}</code><br><br>"
                f"<b>Alternativ in der QGIS Python-Konsole:</b><br>"
                f"<code>import subprocess<br>"
                f"subprocess.check_call(['pip', 'install', '{missing_str}'])</code>"
            )

            QMessageBox.warning(
                self.iface.mainWindow(),
                "Erdmassenberechnung WKA - Fehlende Abhängigkeiten",
                msg
            )
            return

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
