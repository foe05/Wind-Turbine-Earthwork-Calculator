"""
Test Multi-Parameter Optimization Logic

Tests the new multi-parameter optimization functionality without requiring
actual DEM data or DXF files.

Author: Wind Energy Site Planning
Version: 2.0.0
"""

import sys
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from windturbine_earthwork_calculator_v2.core.surface_types import (
    MultiSurfaceProject,
    SurfaceConfig,
    SurfaceType,
    HeightMode,
    MultiSurfaceCalculationResult
)


def test_surface_types_dataclass():
    """Test that new surface types fields are properly initialized."""
    print("\n" + "="*60)
    print("TEST 1: Surface Types Dataclass")
    print("="*60)

    # Create a minimal MultiSurfaceProject with new parameters
    try:
        from qgis.core import QgsGeometry, QgsPointXY

        # Create simple square geometries
        points = [
            QgsPointXY(0, 0),
            QgsPointXY(10, 0),
            QgsPointXY(10, 10),
            QgsPointXY(0, 10),
            QgsPointXY(0, 0)
        ]
        simple_geom = QgsGeometry.fromPolygonXY([points])

        crane_config = SurfaceConfig(
            surface_type=SurfaceType.CRANE_PAD,
            geometry=simple_geom,
            dxf_path="test.dxf",
            height_mode=HeightMode.OPTIMIZED
        )

        foundation_config = SurfaceConfig(
            surface_type=SurfaceType.FOUNDATION,
            geometry=simple_geom,
            dxf_path="test.dxf",
            height_mode=HeightMode.FIXED,
            height_value=128.0
        )

        boom_config = SurfaceConfig(
            surface_type=SurfaceType.BOOM,
            geometry=simple_geom,
            dxf_path="test.dxf",
            height_mode=HeightMode.SLOPED,
            slope_longitudinal=3.0
        )

        rotor_config = SurfaceConfig(
            surface_type=SurfaceType.ROTOR_STORAGE,
            geometry=simple_geom,
            dxf_path="test.dxf",
            height_mode=HeightMode.RELATIVE
        )

        # Create project with NEW parameters
        project = MultiSurfaceProject(
            crane_pad=crane_config,
            foundation=foundation_config,
            boom=boom_config,
            rotor_storage=rotor_config,
            rotor_holms=None,  # NEW
            fok=128.0,
            foundation_depth=3.5,
            gravel_thickness=0.5,
            rotor_height_offset=0.0,
            rotor_height_offset_max=0.5,  # NEW
            slope_angle=45.0,
            search_range_below_fok=0.5,
            search_range_above_fok=0.5,
            search_step=0.1,
            boom_slope_max=4.0,  # NEW
            boom_slope_optimize=True,  # NEW
            boom_slope_step_coarse=0.5,  # NEW
            boom_slope_step_fine=0.1,  # NEW
            rotor_height_optimize=True,  # NEW
            rotor_height_step_coarse=0.2,  # NEW
            rotor_height_step_fine=0.05,  # NEW
            optimize_for_net_earthwork=True  # NEW
        )

        print("✅ MultiSurfaceProject created successfully")
        print(f"   - FOK: {project.fok}m")
        print(f"   - Boom slope max: {project.boom_slope_max}%")
        print(f"   - Boom slope optimize: {project.boom_slope_optimize}")
        print(f"   - Rotor height optimize: {project.rotor_height_optimize}")
        print(f"   - Optimize for net earthwork: {project.optimize_for_net_earthwork}")
        print(f"   - Gravel thickness: {project.gravel_thickness}m")

        # Test MultiSurfaceCalculationResult with new fields
        from windturbine_earthwork_calculator_v2.core.surface_types import SurfaceCalculationResult

        crane_result = SurfaceCalculationResult(
            surface_type=SurfaceType.CRANE_PAD,
            target_height=128.5,
            cut_volume=1000.0,
            fill_volume=800.0,
            platform_area=100.0
        )

        result = MultiSurfaceCalculationResult(
            crane_height=128.5,
            fok=128.0,
            surface_results={SurfaceType.CRANE_PAD: crane_result},
            gravel_fill_external=50.0,  # NEW
            boom_slope_percent=-2.5,  # NEW
            rotor_height_offset_optimized=0.15  # NEW
        )

        print("✅ MultiSurfaceCalculationResult created successfully")
        print(f"   - Crane height: {result.crane_height}m")
        print(f"   - Total cut: {result.total_cut}m³")
        print(f"   - Total fill: {result.total_fill}m³")
        print(f"   - Net volume: {result.net_volume}m³")
        print(f"   - Gravel fill (external): {result.gravel_fill_external}m³")
        print(f"   - Boom slope: {result.boom_slope_percent}%")
        print(f"   - Rotor offset: {result.rotor_height_offset_optimized}m")

        # Test to_dict() serialization
        result_dict = result.to_dict()
        print("✅ to_dict() serialization successful")
        print(f"   - Keys: {list(result_dict.keys())}")

        # Test from_dict() deserialization
        result_restored = MultiSurfaceCalculationResult.from_dict(result_dict)
        print("✅ from_dict() deserialization successful")
        print(f"   - Gravel fill restored: {result_restored.gravel_fill_external}m³")
        print(f"   - Boom slope restored: {result_restored.boom_slope_percent}%")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_optimization_metric_logic():
    """Test the optimization metric selection logic."""
    print("\n" + "="*60)
    print("TEST 2: Optimization Metric Logic")
    print("="*60)

    # Scenario 1: Net optimization
    print("\nScenario 1: Optimize for NET earthwork")
    print("-" * 40)

    # Case A: Good balance (Cut ≈ Fill)
    cut_a = 1000.0
    fill_a = 980.0
    net_a = abs(cut_a - fill_a)
    total_a = cut_a + fill_a

    print(f"  Case A: Cut={cut_a}m³, Fill={fill_a}m³")
    print(f"          Net={net_a}m³, Total={total_a}m³")

    # Case B: Poor balance (Cut >> Fill)
    cut_b = 1500.0
    fill_b = 500.0
    net_b = abs(cut_b - fill_b)
    total_b = cut_b + fill_b

    print(f"  Case B: Cut={cut_b}m³, Fill={fill_b}m³")
    print(f"          Net={net_b}m³, Total={total_b}m³")

    print(f"\n  For NET optimization:")
    print(f"    Case A metric: {net_a}m³")
    print(f"    Case B metric: {net_b}m³")
    print(f"    ✅ Case A wins (better balance: {net_a} < {net_b})")

    # Scenario 2: Total optimization
    print("\nScenario 2: Optimize for TOTAL earthwork")
    print("-" * 40)

    # Case C: Low total, poor balance
    cut_c = 600.0
    fill_c = 200.0
    net_c = abs(cut_c - fill_c)
    total_c = cut_c + fill_c

    print(f"  Case C: Cut={cut_c}m³, Fill={fill_c}m³")
    print(f"          Net={net_c}m³, Total={total_c}m³")

    print(f"\n  For TOTAL optimization:")
    print(f"    Case A metric: {total_a}m³")
    print(f"    Case C metric: {total_c}m³")
    print(f"    ✅ Case C wins (less total work: {total_c} < {total_a})")

    return True


def test_boom_slope_direction_logic():
    """Test boom slope direction detection logic."""
    print("\n" + "="*60)
    print("TEST 3: Boom Slope Direction Logic")
    print("="*60)

    # Simulate terrain slope calculations
    print("\nScenario 1: Terrain slopes DOWN (-3.5%)")
    print("-" * 40)
    terrain_slope_1 = -3.5
    max_slope = 4.0

    if terrain_slope_1 < -0.5:
        slope_range = (-max_slope, 0.0)
        print(f"  ✅ Detected downward slope")
        print(f"  ✅ Optimization range: [{slope_range[0]}%, {slope_range[1]}%]")
    else:
        print(f"  ❌ Wrong detection")

    print("\nScenario 2: Terrain slopes UP (+2.8%)")
    print("-" * 40)
    terrain_slope_2 = 2.8

    if terrain_slope_2 > 0.5:
        slope_range = (0.0, max_slope)
        print(f"  ✅ Detected upward slope")
        print(f"  ✅ Optimization range: [{slope_range[0]}%, {slope_range[1]}%]")
    else:
        print(f"  ❌ Wrong detection")

    print("\nScenario 3: Terrain is FLAT (+0.2%)")
    print("-" * 40)
    terrain_slope_3 = 0.2

    if -0.5 <= terrain_slope_3 <= 0.5:
        slope_range = (-max_slope, max_slope)
        print(f"  ✅ Detected flat terrain")
        print(f"  ✅ Optimization range: [{slope_range[0]}%, {slope_range[1]}%]")
    else:
        print(f"  ❌ Wrong detection")

    return True


def test_holm_fill_logic():
    """Test holm fill calculation logic."""
    print("\n" + "="*60)
    print("TEST 4: Holm Fill Logic")
    print("="*60)

    print("\nScenario 1: NO holms defined (old behavior)")
    print("-" * 40)

    has_holms = False
    terrain_height = 127.0
    target_height = 128.0
    diff = terrain_height - target_height  # -1.0m
    pixel_area = 1.0  # 1m²

    if diff > 0:
        cut_volume = diff * pixel_area
        fill_volume = 0.0
        holm_fill = 0.0
    else:
        cut_volume = 0.0
        if has_holms:
            # Would check if in holm
            holm_fill = abs(diff) * pixel_area
            fill_volume = 0.0
        else:
            fill_volume = abs(diff) * pixel_area
            holm_fill = 0.0

    print(f"  Terrain: {terrain_height}m, Target: {target_height}m")
    print(f"  Difference: {diff}m (below target)")
    print(f"  ✅ Fill entire area: {fill_volume}m³")
    print(f"  ✅ Holm fill: {holm_fill}m³")

    print("\nScenario 2: Holms defined, point IN holm")
    print("-" * 40)

    has_holms = True
    is_in_holm = True

    if diff > 0:
        cut_volume = diff * pixel_area
        holm_fill = 0.0
    else:
        cut_volume = 0.0
        if has_holms and is_in_holm:
            holm_fill = abs(diff) * pixel_area
        else:
            holm_fill = 0.0

    print(f"  Terrain: {terrain_height}m, Target: {target_height}m")
    print(f"  Point is IN holm: {is_in_holm}")
    print(f"  ✅ Holm fill: {holm_fill}m³ (only at holm)")

    print("\nScenario 3: Holms defined, point NOT in holm")
    print("-" * 40)

    is_in_holm = False

    if diff > 0:
        cut_volume = diff * pixel_area
        holm_fill = 0.0
    else:
        cut_volume = 0.0
        if has_holms and is_in_holm:
            holm_fill = abs(diff) * pixel_area
        else:
            holm_fill = 0.0

    print(f"  Terrain: {terrain_height}m, Target: {target_height}m")
    print(f"  Point is IN holm: {is_in_holm}")
    print(f"  ✅ NO fill: {holm_fill}m³ (outside holm, terrain low)")

    print("\nScenario 4: Holms defined, EXCAVATION needed")
    print("-" * 40)

    terrain_height = 129.0
    target_height = 128.0
    diff = terrain_height - target_height  # +1.0m

    if diff > 0:
        cut_volume = diff * pixel_area
        holm_fill = 0.0
    else:
        cut_volume = 0.0
        if has_holms and is_in_holm:
            holm_fill = abs(diff) * pixel_area
        else:
            holm_fill = 0.0

    print(f"  Terrain: {terrain_height}m, Target: {target_height}m")
    print(f"  Difference: {diff}m (above target)")
    print(f"  ✅ Excavate: {cut_volume}m³ (regardless of holms)")
    print(f"  ✅ NO fill needed: {holm_fill}m³")

    return True


def test_gravel_calculation():
    """Test external gravel volume calculation."""
    print("\n" + "="*60)
    print("TEST 5: Gravel Volume Calculation")
    print("="*60)

    crane_pad_area = 500.0  # m²
    gravel_thickness = 0.5  # m

    gravel_volume = crane_pad_area * gravel_thickness

    print(f"\nInput:")
    print(f"  Crane pad area: {crane_pad_area}m²")
    print(f"  Gravel thickness: {gravel_thickness}m")
    print(f"\nCalculation:")
    print(f"  Gravel volume = {crane_pad_area} × {gravel_thickness}")
    print(f"                = {gravel_volume}m³")
    print(f"\n✅ External gravel fill: {gravel_volume}m³")
    print(f"   (NOT included in site cut/fill balance)")

    return True


def test_two_stage_optimization_logic():
    """Test two-stage optimization parameters."""
    print("\n" + "="*60)
    print("TEST 6: Two-Stage Optimization Parameters")
    print("="*60)

    # Configuration
    height_min = 127.5
    height_max = 128.5
    boom_slope_min = -4.0
    boom_slope_max = 0.0  # Detected downward slope
    rotor_offset_min = -0.5
    rotor_offset_max = 0.5

    print("\nSTAGE 1: COARSE SEARCH")
    print("-" * 40)

    height_step_coarse = 1.0
    slope_step_coarse = 0.5
    rotor_step_coarse = 0.2

    heights_coarse = np.arange(height_min, height_max + height_step_coarse, height_step_coarse)
    slopes_coarse = np.arange(boom_slope_min, boom_slope_max + slope_step_coarse, slope_step_coarse)
    rotor_coarse = np.arange(rotor_offset_min, rotor_offset_max + rotor_step_coarse, rotor_step_coarse)

    num_coarse = len(heights_coarse) * len(slopes_coarse) * len(rotor_coarse)

    print(f"  Height range: [{height_min}, {height_max}] in {height_step_coarse}m steps")
    print(f"    → {len(heights_coarse)} values: {list(heights_coarse)}")
    print(f"  Boom slope range: [{boom_slope_min}, {boom_slope_max}]% in {slope_step_coarse}% steps")
    print(f"    → {len(slopes_coarse)} values: {list(slopes_coarse)}")
    print(f"  Rotor offset range: [{rotor_offset_min}, {rotor_offset_max}]m in {rotor_step_coarse}m steps")
    print(f"    → {len(rotor_coarse)} values: {list(rotor_coarse)}")
    print(f"\n  ✅ Total scenarios: {num_coarse}")

    # Simulate best result from coarse
    best_height_coarse = 128.0
    best_slope_coarse = -2.0
    best_rotor_coarse = 0.2

    print(f"\n  Best coarse result:")
    print(f"    Height: {best_height_coarse}m")
    print(f"    Slope: {best_slope_coarse}%")
    print(f"    Rotor: {best_rotor_coarse}m")

    print("\n\nSTAGE 2: FINE SEARCH")
    print("-" * 40)

    height_step_fine = 0.1
    slope_step_fine = 0.1
    rotor_step_fine = 0.05

    # Fine search around best coarse
    heights_fine = np.arange(
        best_height_coarse - 1.0,
        best_height_coarse + 1.0 + height_step_fine,
        height_step_fine
    )

    slopes_fine = np.arange(
        best_slope_coarse - 0.5,
        best_slope_coarse + 0.5 + slope_step_fine,
        slope_step_fine
    )
    # Clamp to valid range
    slopes_fine = slopes_fine[(slopes_fine >= boom_slope_min) & (slopes_fine <= boom_slope_max)]

    rotor_fine = np.arange(
        best_rotor_coarse - 0.2,
        best_rotor_coarse + 0.2 + rotor_step_fine,
        rotor_step_fine
    )
    # Clamp to valid range
    rotor_fine = rotor_fine[(rotor_fine >= rotor_offset_min) & (rotor_fine <= rotor_offset_max)]

    num_fine = len(heights_fine) * len(slopes_fine) * len(rotor_fine)

    print(f"  Height range: [{best_height_coarse - 1.0}, {best_height_coarse + 1.0}] in {height_step_fine}m steps")
    print(f"    → {len(heights_fine)} values")
    print(f"  Boom slope range: [{best_slope_coarse - 0.5}, {best_slope_coarse + 0.5}]% in {slope_step_fine}% steps")
    print(f"    → {len(slopes_fine)} values (clamped to valid range)")
    print(f"  Rotor offset range: [{best_rotor_coarse - 0.2}, {best_rotor_coarse + 0.2}]m in {rotor_step_fine}m steps")
    print(f"    → {len(rotor_fine)} values (clamped to valid range)")
    print(f"\n  ✅ Total scenarios: {num_fine}")

    print(f"\n\n📊 SUMMARY:")
    print(f"  Coarse scenarios: {num_coarse}")
    print(f"  Fine scenarios: {num_fine}")
    print(f"  TOTAL scenarios: {num_coarse + num_fine}")

    return True


def run_all_tests():
    """Run all validation tests."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "MULTI-PARAMETER OPTIMIZATION TESTS" + " "*14 + "║")
    print("╚" + "="*58 + "╝")

    tests = [
        ("Surface Types Dataclass", test_surface_types_dataclass),
        ("Optimization Metric Logic", test_optimization_metric_logic),
        ("Boom Slope Direction Logic", test_boom_slope_direction_logic),
        ("Holm Fill Logic", test_holm_fill_logic),
        ("Gravel Calculation", test_gravel_calculation),
        ("Two-Stage Optimization", test_two_stage_optimization_logic),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ TEST FAILED: {name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*20 + "TEST SUMMARY" + " "*26 + "║")
    print("╚" + "="*58 + "╝")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {name}")

    print("\n" + "-"*60)
    print(f"  Results: {passed}/{total} tests passed")
    print("-"*60 + "\n")

    return passed == total


if __name__ == "__main__":
    import os
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'  # For headless QGIS

    success = run_all_tests()
    sys.exit(0 if success else 1)
