"""
Wind Turbine Earthwork Calculator V2
====================================

A QGIS Processing plugin for optimizing wind turbine crane pad heights
in hilly terrain by minimizing earthwork volumes.

Author: Wind Energy Site Planning
Version: 2.0.0
Date: November 2025
"""


def classFactory(iface):
    """
    Load WindTurbineEarthworkCalculatorPlugin class from file plugin.py

    Args:
        iface: A QGIS interface instance.

    Returns:
        WindTurbineEarthworkCalculatorPlugin instance
    """
    from .plugin import WindTurbineEarthworkCalculatorPlugin
    return WindTurbineEarthworkCalculatorPlugin(iface)
