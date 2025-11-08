"""
Simple standalone test for DXF import (without QGIS)

This tests the ezdxf package directly to verify the DXF file structure.
"""

import sys
from pathlib import Path

try:
    import ezdxf
except ImportError:
    print("ERROR: ezdxf not installed!")
    print("Install it with: pip install --user --break-system-packages ezdxf")
    sys.exit(1)


def test_dxf_structure(dxf_path):
    """
    Test DXF file structure.

    Args:
        dxf_path (str): Path to DXF file
    """
    print("=" * 60)
    print("DXF STRUCTURE TEST")
    print("=" * 60)
    print(f"\nDXF File: {dxf_path}\n")

    try:
        # Load DXF
        print("1. Loading DXF file...")
        doc = ezdxf.readfile(dxf_path)
        print(f"   ✓ DXF loaded")
        print(f"   - Version: {doc.dxfversion}")
        print(f"   - Units: {doc.units}")

        # Get modelspace
        msp = doc.modelspace()

        # Count entities by type
        print("\n2. Entity Summary:")
        entity_types = {}
        for entity in msp:
            etype = entity.dxftype()
            entity_types[etype] = entity_types.get(etype, 0) + 1

        for etype, count in sorted(entity_types.items()):
            print(f"   - {etype}: {count}")

        # Extract LWPOLYLINE entities
        print("\n3. Analyzing LWPOLYLINE entities...")
        lwpolylines = list(msp.query('LWPOLYLINE'))
        print(f"   ✓ Found {len(lwpolylines)} LWPOLYLINE entities")

        if lwpolylines:
            for i, entity in enumerate(lwpolylines[:5]):  # Show first 5
                points = list(entity.get_points('xy'))
                layer = entity.dxf.layer
                is_closed = entity.is_closed
                print(f"   - LWPOLYLINE {i+1}: {len(points)} points, layer='{layer}', closed={is_closed}")

        # Extract regular POLYLINE entities
        polylines = list(msp.query('POLYLINE'))
        if polylines:
            print(f"\n   ✓ Found {len(polylines)} POLYLINE entities")
            for i, entity in enumerate(polylines[:5]):
                vertices = list(entity.vertices)
                layer = entity.dxf.layer
                print(f"   - POLYLINE {i+1}: {len(vertices)} vertices, layer='{layer}'")

        # Extract LINE entities
        lines = list(msp.query('LINE'))
        if lines:
            print(f"\n   ✓ Found {len(lines)} LINE entities")
            for i, entity in enumerate(lines[:5]):
                start = entity.dxf.start
                end = entity.dxf.end
                layer = entity.dxf.layer
                length = ((end.x - start.x)**2 + (end.y - start.y)**2)**0.5
                print(f"   - LINE {i+1}: length={length:.2f}m, layer='{layer}'")

        # Extract all polyline coordinates
        print("\n4. Extracting coordinates...")
        all_coords = []

        # From LWPOLYLINE
        for entity in lwpolylines:
            coords = []
            for point in entity.get_points('xy'):
                coords.append((point[0], point[1]))
            if coords:
                all_coords.append(coords)

        # From POLYLINE
        for entity in polylines:
            coords = []
            for vertex in entity.vertices:
                coords.append((vertex.dxf.location.x, vertex.dxf.location.y))
            if coords:
                all_coords.append(coords)

        # From LINE
        for entity in lines:
            start = entity.dxf.start
            end = entity.dxf.end
            all_coords.append([(start.x, start.y), (end.x, end.y)])

        print(f"   ✓ Extracted {len(all_coords)} polylines/lines")

        # Calculate total point count
        total_points = sum(len(coords) for coords in all_coords)
        print(f"   ✓ Total points: {total_points}")

        # Show first polyline in detail
        if all_coords:
            print(f"\n5. First Polyline Details:")
            first_coords = all_coords[0]
            print(f"   - Points: {len(first_coords)}")
            print(f"   - First point: {first_coords[0]}")
            print(f"   - Last point: {first_coords[-1]}")

            # Check if closed
            gap = ((first_coords[0][0] - first_coords[-1][0])**2 +
                   (first_coords[0][1] - first_coords[-1][1])**2)**0.5
            print(f"   - Closure gap: {gap:.6f}m")

        # Calculate bounding box of all coordinates
        print("\n6. Bounding Box:")
        all_x = [p[0] for coords in all_coords for p in coords]
        all_y = [p[1] for coords in all_coords for p in coords]

        if all_x and all_y:
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)

            print(f"   - X: {min_x:.2f} - {max_x:.2f} (width: {max_x - min_x:.2f}m)")
            print(f"   - Y: {min_y:.2f} - {max_y:.2f} (height: {max_y - min_y:.2f}m)")
            print(f"   - Centroid: {(min_x + max_x)/2:.2f}, {(min_y + max_y)/2:.2f}")

            # Check CRS (should be UTM32N ~ EPSG:25832)
            if 400000 < min_x < 600000 and 5000000 < min_y < 6000000:
                print(f"   ✓ Coordinates look like EPSG:25832 (UTM 32N)")
            else:
                print(f"   ⚠ Coordinates may not be EPSG:25832")

        print("\n" + "=" * 60)
        print("✓ TEST PASSED")
        print("=" * 60)
        print("\nDXF file structure is valid and ready for import!")
        print(f"Found {len(all_coords)} polylines with {total_points} total points.")

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
        print("Usage: python3 test_dxf_simple.py <path_to_dxf_file>")
        print("\nExample:")
        print("  python3 test_dxf_simple.py 'Kranstellfläche Marsberg V172-7.2-175m.dxf'")
        sys.exit(1)

    dxf_path = sys.argv[1]

    if not Path(dxf_path).exists():
        print(f"Error: File not found: {dxf_path}")
        sys.exit(1)

    success = test_dxf_structure(dxf_path)
    sys.exit(0 if success else 1)
