"""
Authoritative Cut/Fill-Regression gegen die wea45mit3d-Fixture aus dem Plugin.

Stellt sicher, dass die Streamlit-Implementierung dieselben Zahlen liefert wie
die QGIS-Plugin-Pipeline (Stand 2025-11-26): Foundation-Cut 693 m³, Crane-Pad
Platform-only Cut 5280 m³ / Fill 1763 m³.

Die Fixture wird aus dem Plugin-Verzeichnis gelesen (nicht ins Streamlit-Repo
dupliziert, ~16 MB DEM).
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import fiona
import pytest
from shapely.geometry import shape

from app.core.earthwork import cut_fill_for_polygon

# Plugin-Verzeichnis hängt am Repo-Root
_THIS = Path(__file__).resolve()
REF_ZIP = (
    _THIS.parent.parent.parent.parent
    / "windturbine_earthwork_calculator_v2"
    / "wea45mit3d.zip"
)

# Werte aus dem Reference-HTML-Report (wea45mit3d/ergebnisse/...Bericht_MultiSurface.html)
EXPECTED_FOUNDATION_CUT_M3 = 693
EXPECTED_CRANE_PLATFORM_CUT_M3 = 5280
EXPECTED_CRANE_PLATFORM_FILL_M3 = 1763

OPTIMAL_CRANE_HEIGHT = 319.87
GRAVEL_THICKNESS = 0.60
FOK = 318.37
FOUNDATION_DEPTH = 3.1


@pytest.fixture(scope="module")
def fixture(tmp_path_factory):
    if not REF_ZIP.exists():
        pytest.skip(f"Fixture nicht verfügbar: {REF_ZIP}")
    tmp = tmp_path_factory.mktemp("wea45")
    with zipfile.ZipFile(REF_ZIP) as zf:
        zf.extractall(tmp)
    base = tmp / "wea45mit3d" / "ergebnisse"
    return {
        "dem": str(base / "WKA_492079_5702007_DEM.tif"),
        "gpkg": str(base / "WKA_492079_5702007_MultiSurface.gpkg"),
    }


@pytest.fixture(scope="module")
def crane_polygon(fixture):
    with fiona.open(fixture["gpkg"], layer="kranstellflaechen") as src:
        return shape(next(iter(src))["geometry"])


@pytest.fixture(scope="module")
def foundation_polygon(fixture):
    with fiona.open(fixture["gpkg"], layer="fundamentflaechen") as src:
        return shape(next(iter(src))["geometry"])


def test_foundation_cut_matches_plugin_reference(fixture, foundation_polygon):
    """Fundament-Abtrag entspricht der Plugin-Berechnung (±1 m³)."""
    planum = FOK - FOUNDATION_DEPTH
    r = cut_fill_for_polygon(fixture["dem"], foundation_polygon, planum)
    assert r.cut_m3 == pytest.approx(EXPECTED_FOUNDATION_CUT_M3, abs=1.0), (
        f"Foundation Cut driftete: bekommen {r.cut_m3:.1f}, "
        f"erwartet {EXPECTED_FOUNDATION_CUT_M3}"
    )


def test_crane_platform_cut_fill_match_plugin_reference(fixture, crane_polygon):
    """Plateau-only Cut/Fill der Kranstellfläche stimmen mit Plugin überein (±2 m³)."""
    planum = OPTIMAL_CRANE_HEIGHT - GRAVEL_THICKNESS
    r = cut_fill_for_polygon(fixture["dem"], crane_polygon, planum)
    assert r.cut_m3 == pytest.approx(EXPECTED_CRANE_PLATFORM_CUT_M3, abs=2.0), (
        f"Crane Cut driftete: bekommen {r.cut_m3:.1f}, "
        f"erwartet {EXPECTED_CRANE_PLATFORM_CUT_M3}"
    )
    assert r.fill_m3 == pytest.approx(EXPECTED_CRANE_PLATFORM_FILL_M3, abs=2.0), (
        f"Crane Fill driftete: bekommen {r.fill_m3:.1f}, "
        f"erwartet {EXPECTED_CRANE_PLATFORM_FILL_M3}"
    )


def test_crane_sampling_nonzero(fixture, crane_polygon):
    """Pixel-Sampling liefert > 1000 Pixel (gegen den dc778d9-Regression-Bug)."""
    planum = OPTIMAL_CRANE_HEIGHT - GRAVEL_THICKNESS
    r = cut_fill_for_polygon(fixture["dem"], crane_polygon, planum)
    assert r.num_pixels > 1000, (
        "Kranstellflächen-Sampling liefert ~0 Pixel — das ist der dc778d9-Bug."
    )
