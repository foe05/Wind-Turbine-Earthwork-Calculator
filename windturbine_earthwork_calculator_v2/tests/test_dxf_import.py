"""
Test script for DXF import functionality

This script can be run standalone to test the DXF importer without QGIS.

Usage:
    python test_dxf_import.py <path_to_dxf_file>
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.dxf_importer import DXFImporter


def test_dxf_import(dxf_path):
    """
    Test DXF import functionality.

    Args:
        dxf_path (str): Path to DXF file
    """
    print("=" * 60)
    print("DXF IMPORT TEST")
    print("=" * 60)
    print(f"\nDXF File: {dxf_path}\n")

    try:
        # Initialize importer
        print("1. Initializing DXF importer...")
        importer = DXFImporter(dxf_path, tolerance=0.01)
        print("   ✓ Importer created")

        # Load DXF
        print("\n2. Loading DXF file...")
        importer.load_dxf()
        print(f"   ✓ DXF loaded (version: {importer.doc.dxfversion()})")

        # Extract polylines
        print("\n3. Extracting polylines...")
        polylines = importer.extract_polylines()
        print(f"   ✓ Found {len(polylines)} polylines")

        # Show first few polylines
        for i, pl in enumerate(polylines[:3]):
            print(f"   - Polyline {i+1}: {len(pl)} points")

        # Connect polylines
        print("\n4. Connecting polylines to polygon...")
        coords = importer.connect_polylines(polylines)
        print(f"   ✓ Connected polygon with {len(coords)} vertices")

        # Show first and last points
        print(f"   - First point: {coords[0]}")
        print(f"   - Last point: {coords[-1]}")

        # Check if closed
        from utils.geometry_utils import point_distance
        gap = point_distance(coords[0], coords[-1])
        print(f"   - Closure gap: {gap:.6f}m")

        if gap < 0.01:
            print("   ✓ Polygon is closed")
        else:
            print("   ⚠ Polygon may not be fully closed")

        # Calculate stats
        print("\n5. Polygon Statistics:")

        # Simple area calculation (shoelace formula)
        area = 0.0
        for i in range(len(coords) - 1):
            area += coords[i][0] * coords[i+1][1]
            area -= coords[i+1][0] * coords[i][1]
        area = abs(area) / 2.0

        print(f"   - Area: {area:,.2f} m²")

        # Perimeter
        perimeter = 0.0
        for i in range(len(coords) - 1):
            perimeter += point_distance(coords[i], coords[i+1])

        print(f"   - Perimeter: {perimeter:,.2f} m")

        # Bounding box
        x_coords = [c[0] for c in coords]
        y_coords = [c[1] for c in coords]

        bbox_min_x = min(x_coords)
        bbox_max_x = max(x_coords)
        bbox_min_y = min(y_coords)
        bbox_max_y = max(y_coords)

        print(f"   - Bounding Box:")
        print(f"     X: {bbox_min_x:.2f} - {bbox_max_x:.2f} (width: {bbox_max_x - bbox_min_x:.2f}m)")
        print(f"     Y: {bbox_min_y:.2f} - {bbox_max_y:.2f} (height: {bbox_max_y - bbox_min_y:.2f}m)")

        # Centroid (simple average)
        centroid_x = sum(x_coords) / len(x_coords)
        centroid_y = sum(y_coords) / len(y_coords)
        print(f"   - Centroid: {centroid_x:.2f}, {centroid_y:.2f}")

        print("\n" + "=" * 60)
        print("✓ TEST PASSED")
        print("=" * 60)
        print("\nThe DXF file was successfully imported and processed.")
        print("Ready for QGIS integration!")

        return True

    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ TEST FAILED")
        print("=" * 60)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_dxf_import.py <path_to_dxf_file>")
        print("\nExample:")
        print("  python test_dxf_import.py ../Kranstellfläche_Marsberg_V172-7.2-175m.dxf")
        sys.exit(1)

    dxf_path = sys.argv[1]

    if not Path(dxf_path).exists():
        print(f"Error: File not found: {dxf_path}")
        sys.exit(1)

    success = test_dxf_import(dxf_path)
    sys.exit(0 if success else 1)
