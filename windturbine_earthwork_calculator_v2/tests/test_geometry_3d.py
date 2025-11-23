"""
Test script for 3D geometry functionality

This script tests the 3D geometry creation functions for QGIS 3D visualization.

Usage:
    python test_geometry_3d.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qgis.core import (
    QgsApplication,
    QgsGeometry,
    QgsPointXY,
    QgsWkbTypes
)

from utils.geometry_3d import (
    polygon_to_polygonz,
    polygon_to_sloped_polygonz,
    create_profile_vertical_wall,
    get_geometry_z_range
)


def init_qgis():
    """Initialize QGIS application for testing."""
    qgis_prefix = "/usr"
    QgsApplication.setPrefixPath(qgis_prefix, True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    return qgs


def test_polygon_to_polygonz():
    """Test conversion of 2D polygon to 3D PolygonZ."""
    print("\n" + "=" * 60)
    print("TEST: polygon_to_polygonz")
    print("=" * 60)

    # Create a simple square polygon
    points = [
        QgsPointXY(0, 0),
        QgsPointXY(10, 0),
        QgsPointXY(10, 10),
        QgsPointXY(0, 10),
        QgsPointXY(0, 0)
    ]
    polygon_2d = QgsGeometry.fromPolygonXY([points])

    print(f"Input 2D polygon: {polygon_2d.asWkt()[:100]}...")
    print(f"  - Type: {QgsWkbTypes.displayString(polygon_2d.wkbType())}")
    print(f"  - Area: {polygon_2d.area():.2f} m²")

    # Convert to 3D at height 100m
    z_height = 100.0
    polygon_3d = polygon_to_polygonz(polygon_2d, z_height)

    if polygon_3d.isEmpty():
        print("  ✗ ERROR: Result is empty!")
        return False

    print(f"\nOutput 3D polygon: {polygon_3d.asWkt()[:100]}...")
    print(f"  - Type: {QgsWkbTypes.displayString(polygon_3d.wkbType())}")

    # Check if it's actually 3D
    is_3d = QgsWkbTypes.hasZ(polygon_3d.wkbType())
    print(f"  - Has Z: {is_3d}")

    if not is_3d:
        print("  ✗ ERROR: Result is not 3D!")
        return False

    # Get Z range
    z_min, z_max = get_geometry_z_range(polygon_3d)
    print(f"  - Z range: {z_min:.2f} - {z_max:.2f}")

    if abs(z_min - z_height) > 0.001 or abs(z_max - z_height) > 0.001:
        print(f"  ✗ ERROR: Z values don't match expected {z_height}!")
        return False

    print("  ✓ Test passed!")
    return True


def test_polygon_to_sloped_polygonz():
    """Test creation of sloped 3D polygon."""
    print("\n" + "=" * 60)
    print("TEST: polygon_to_sloped_polygonz")
    print("=" * 60)

    # Create a rectangular polygon (20m x 10m)
    points = [
        QgsPointXY(0, 0),
        QgsPointXY(20, 0),
        QgsPointXY(20, 10),
        QgsPointXY(0, 10),
        QgsPointXY(0, 0)
    ]
    polygon_2d = QgsGeometry.fromPolygonXY([points])

    base_height = 300.0
    slope_percent = 5.0  # 5% slope
    slope_direction = 0.0  # East direction

    print(f"Input 2D polygon: 20m x 10m rectangle")
    print(f"  - Base height: {base_height}m")
    print(f"  - Slope: {slope_percent}%")
    print(f"  - Direction: {slope_direction}° (East)")

    polygon_3d = polygon_to_sloped_polygonz(
        polygon_2d,
        base_height,
        slope_percent,
        slope_direction
    )

    if polygon_3d.isEmpty():
        print("  ✗ ERROR: Result is empty!")
        return False

    # Check if it's 3D
    is_3d = QgsWkbTypes.hasZ(polygon_3d.wkbType())
    print(f"\nOutput 3D polygon:")
    print(f"  - Has Z: {is_3d}")

    if not is_3d:
        print("  ✗ ERROR: Result is not 3D!")
        return False

    # Get Z range - should vary due to slope
    z_min, z_max = get_geometry_z_range(polygon_3d)
    print(f"  - Z range: {z_min:.2f} - {z_max:.2f}")

    # With 5% slope over ~10m from center, expect ~0.5m variation
    z_variation = z_max - z_min
    print(f"  - Z variation: {z_variation:.2f}m")

    if z_variation < 0.1:
        print("  ⚠ WARNING: Very little Z variation, slope may not be applied correctly")
    else:
        print("  ✓ Z variation indicates slope is applied")

    print("  ✓ Test passed!")
    return True


def test_create_profile_vertical_wall():
    """Test creation of vertical wall polygon from profile line."""
    print("\n" + "=" * 60)
    print("TEST: create_profile_vertical_wall")
    print("=" * 60)

    # Create a simple line
    line_points = [
        QgsPointXY(0, 0),
        QgsPointXY(50, 0)
    ]
    line_geom = QgsGeometry.fromPolylineXY(line_points)

    z_min = 280.0
    z_max = 320.0

    print(f"Input line: 50m long")
    print(f"  - Z range: {z_min}m to {z_max}m")

    wall_3d = create_profile_vertical_wall(
        line_geom,
        z_min,
        z_max,
        num_samples=10
    )

    if wall_3d.isEmpty():
        print("  ✗ ERROR: Result is empty!")
        return False

    # Check if it's 3D
    is_3d = QgsWkbTypes.hasZ(wall_3d.wkbType())
    print(f"\nOutput 3D polygon (vertical wall):")
    print(f"  - Type: {QgsWkbTypes.displayString(wall_3d.wkbType())}")
    print(f"  - Has Z: {is_3d}")

    if not is_3d:
        print("  ✗ ERROR: Result is not 3D!")
        return False

    # Get Z range
    actual_z_min, actual_z_max = get_geometry_z_range(wall_3d)
    print(f"  - Actual Z range: {actual_z_min:.2f} - {actual_z_max:.2f}")

    if abs(actual_z_min - z_min) > 0.001 or abs(actual_z_max - z_max) > 0.001:
        print(f"  ✗ ERROR: Z values don't match expected range!")
        return False

    print("  ✓ Test passed!")
    return True


def test_multipolygon():
    """Test handling of MultiPolygon geometries."""
    print("\n" + "=" * 60)
    print("TEST: MultiPolygon handling")
    print("=" * 60)

    # Create a MultiPolygon
    polygon1 = [
        QgsPointXY(0, 0),
        QgsPointXY(10, 0),
        QgsPointXY(10, 10),
        QgsPointXY(0, 10),
        QgsPointXY(0, 0)
    ]
    polygon2 = [
        QgsPointXY(20, 0),
        QgsPointXY(30, 0),
        QgsPointXY(30, 10),
        QgsPointXY(20, 10),
        QgsPointXY(20, 0)
    ]
    multi_polygon_2d = QgsGeometry.fromMultiPolygonXY([[polygon1], [polygon2]])

    print(f"Input MultiPolygon: 2 polygons")
    print(f"  - Type: {QgsWkbTypes.displayString(multi_polygon_2d.wkbType())}")

    # Convert to 3D
    z_height = 150.0
    multi_polygon_3d = polygon_to_polygonz(multi_polygon_2d, z_height)

    if multi_polygon_3d.isEmpty():
        print("  ✗ ERROR: Result is empty!")
        return False

    is_3d = QgsWkbTypes.hasZ(multi_polygon_3d.wkbType())
    print(f"\nOutput 3D MultiPolygon:")
    print(f"  - Type: {QgsWkbTypes.displayString(multi_polygon_3d.wkbType())}")
    print(f"  - Has Z: {is_3d}")

    if not is_3d:
        print("  ✗ ERROR: Result is not 3D!")
        return False

    # Get Z range
    z_min, z_max = get_geometry_z_range(multi_polygon_3d)
    print(f"  - Z range: {z_min:.2f} - {z_max:.2f}")

    print("  ✓ Test passed!")
    return True


def run_all_tests():
    """Run all 3D geometry tests."""
    print("=" * 60)
    print("3D GEOMETRY TESTS")
    print("=" * 60)

    # Initialize QGIS
    print("\nInitializing QGIS...")
    try:
        qgs = init_qgis()
        print("  ✓ QGIS initialized")
    except Exception as e:
        print(f"  ✗ Failed to initialize QGIS: {e}")
        return False

    # Run tests
    results = []

    try:
        results.append(("polygon_to_polygonz", test_polygon_to_polygonz()))
        results.append(("polygon_to_sloped_polygonz", test_polygon_to_sloped_polygonz()))
        results.append(("create_profile_vertical_wall", test_create_profile_vertical_wall()))
        results.append(("MultiPolygon handling", test_multipolygon()))
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
