"""
Platform Height Optimization

Extrahiert aus QGIS Plugin WindTurbine_Earthwork_Calculator.py
3 Methoden: mean, min_cut, balanced
"""
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def optimize_platform_height_mean(elevations: np.ndarray) -> float:
    """
    Method 0: Mittelwert der Geländehöhen

    Einfachste Methode, oft gute Balance zwischen Cut und Fill.

    Args:
        elevations: Array of terrain elevations

    Returns:
        Platform height (mean)
    """
    return float(np.mean(elevations))


def optimize_platform_height_min_cut(elevations: np.ndarray) -> float:
    """
    Method 1: Minimaler Aushub (40. Perzentil)

    Bevorzugt niedrigere Plattformhöhe → weniger Aushub, mehr Auftrag.

    Args:
        elevations: Array of terrain elevations

    Returns:
        Platform height (40th percentile)
    """
    return float(np.percentile(elevations, 40))


def optimize_platform_height_balanced(elevations: np.ndarray) -> float:
    """
    Method 2: Ausgeglichene Cut/Fill-Balance

    Findet Höhe, bei der Cut-Volumen ≈ Fill-Volumen.
    Verwendet iterative Suche.

    Args:
        elevations: Array of terrain elevations

    Returns:
        Platform height (balanced cut/fill)
    """
    # Start mit Median
    min_elev = float(np.min(elevations))
    max_elev = float(np.max(elevations))

    # Binary search für beste Balance
    tolerance = 0.01  # 1cm Genauigkeit
    max_iterations = 50

    for _ in range(max_iterations):
        mid_height = (min_elev + max_elev) / 2

        # Berechne Cut und Fill bei dieser Höhe
        diff = elevations - mid_height
        cut_volume = np.sum(np.maximum(diff, 0))
        fill_volume = np.sum(np.maximum(-diff, 0))

        # Balance berechnen
        balance = cut_volume - fill_volume

        if abs(balance) < tolerance:
            return mid_height

        # Anpassen
        if balance > 0:  # Zu viel Cut → Höhe erhöhen
            min_elev = mid_height
        else:  # Zu viel Fill → Höhe senken
            max_elev = mid_height

    # Falls nicht konvergiert, nutze letzte Iteration
    logger.warning(f"Balanced optimization did not fully converge (balance: {balance:.2f})")
    return (min_elev + max_elev) / 2


def optimize_platform_height(
    elevations: np.ndarray,
    method: str = "mean"
) -> float:
    """
    Optimize platform height using specified method

    Args:
        elevations: Array of terrain elevations within platform area
        method: Optimization method ("mean", "min_cut", "balanced")

    Returns:
        Optimized platform height

    Raises:
        ValueError: If method is unknown
    """
    if len(elevations) == 0:
        raise ValueError("No elevation data provided")

    # Ensure float dtype
    elevations = np.asarray(elevations, dtype=float)

    if method == "mean":
        return optimize_platform_height_mean(elevations)
    elif method == "min_cut":
        return optimize_platform_height_min_cut(elevations)
    elif method == "balanced":
        return optimize_platform_height_balanced(elevations)
    else:
        raise ValueError(f"Unknown optimization method: {method}")
