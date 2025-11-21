"""
Processing Provider for Wind Turbine Earthwork Calculator V2

Author: Wind Energy Site Planning
Version: 2.0.0
"""

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .optimize_algorithm import OptimizePlatformHeightAlgorithm


class WindTurbineProvider(QgsProcessingProvider):
    """QGIS Processing Provider for Wind Turbine Earthwork Calculator."""

    def __init__(self):
        """Initialize provider."""
        super().__init__()

    def id(self):
        """Return provider ID."""
        return 'windturbine_v2'

    def name(self):
        """Return provider name."""
        return 'Wind Turbine Earthwork Calculator V2'

    def longName(self):
        """Return provider long name."""
        return 'Wind Turbine Earthwork Calculator V2 - Platform Height Optimization'

    def icon(self):
        """Return provider icon."""
        # Return default icon for now
        return QgsProcessingProvider.icon(self)

    def loadAlgorithms(self):
        """Load all algorithms."""
        self.addAlgorithm(OptimizePlatformHeightAlgorithm())

    def unload(self):
        """Cleanup when provider is unloaded."""
        pass
