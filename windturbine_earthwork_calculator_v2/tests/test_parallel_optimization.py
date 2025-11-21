"""
Parallelization Tests for Multi-Surface Earthwork Calculator

Comprehensive tests to validate parallel processing implementation:
- GDAL thread safety in ProcessPoolExecutor
- Result consistency between sequential and parallel execution
- Race condition detection through multiple runs
- Performance benchmarks

Author: Wind Energy Site Planning
Version: 2.0.0
"""

import sys
import os
import time
import tempfile
import statistics
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Environment setup for headless QGIS
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Try to import QGIS/GDAL - these are only available in QGIS environment
try:
    from osgeo import gdal, ogr, osr
    from qgis.core import (
        QgsApplication,
        QgsRasterLayer,
        QgsGeometry,
        QgsPointXY,
        QgsProcessingFeedback
    )
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False
    print("WARNING: QGIS/GDAL not available. Tests require QGIS environment.")

if QGIS_AVAILABLE:
    from windturbine_earthwork_calculator_v2.core.multi_surface_calculator import (
        MultiSurfaceCalculator,
        _calculate_single_height_scenario
    )
    from windturbine_earthwork_calculator_v2.core.surface_types import (
        MultiSurfaceProject,
        SurfaceConfig,
        SurfaceType,
        HeightMode
    )


# =============================================================================
# TEST DATA GENERATION
# =============================================================================

def create_synthetic_dem(filepath: str,
                         size: Tuple[int, int] = (100, 100),
                         origin: Tuple[float, float] = (500000.0, 5500000.0),
                         pixel_size: float = 1.0,
                         base_height: float = 128.0,
                         slope_x: float = 0.01,
                         slope_y: float = 0.005,
                         noise_amplitude: float = 0.5,
                         seed: int = 42) -> str:
    """
    Create a synthetic DEM GeoTIFF for testing.

    Args:
        filepath: Output path for GeoTIFF
        size: (width, height) in pixels
        origin: (x, y) origin in CRS units
        pixel_size: Pixel size in CRS units
        base_height: Base elevation in meters
        slope_x: Slope in X direction (m/m)
        slope_y: Slope in Y direction (m/m)
        noise_amplitude: Random noise amplitude
        seed: Random seed for reproducibility

    Returns:
        Path to created GeoTIFF
    """
    np.random.seed(seed)

    width, height = size

    # Create coordinate grids
    x = np.arange(width) * pixel_size
    y = np.arange(height) * pixel_size
    xx, yy = np.meshgrid(x, y)

    # Generate elevation data
    elevation = (base_height
                 + xx * slope_x
                 + yy * slope_y
                 + np.random.randn(height, width) * noise_amplitude)

    # Create GeoTIFF
    driver = gdal.GetDriverByName('GTiff')
    ds = driver.Create(filepath, width, height, 1, gdal.GDT_Float32)

    # Set geotransform: (origin_x, pixel_width, 0, origin_y, 0, -pixel_height)
    geotransform = (origin[0], pixel_size, 0, origin[1] + height * pixel_size, 0, -pixel_size)
    ds.SetGeoTransform(geotransform)

    # Set projection (UTM Zone 32N for Germany)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(25832)
    ds.SetProjection(srs.ExportToWkt())

    # Write data
    band = ds.GetRasterBand(1)
    band.WriteArray(elevation.astype(np.float32))
    band.SetNoDataValue(-9999)
    band.FlushCache()

    ds = None

    return filepath


def create_test_geometries(center: Tuple[float, float],
                           crane_size: float = 30.0,
                           boom_length: float = 50.0,
                           rotor_size: float = 15.0) -> Dict[str, QgsGeometry]:
    """
    Create test geometries for crane pad, foundation, boom, and rotor storage.

    Args:
        center: Center point (x, y)
        crane_size: Crane pad side length
        boom_length: Boom surface length
        rotor_size: Rotor storage side length

    Returns:
        Dict with geometry types as keys
    """
    cx, cy = center

    # Crane pad (square)
    crane_points = [
        QgsPointXY(cx - crane_size/2, cy - crane_size/2),
        QgsPointXY(cx + crane_size/2, cy - crane_size/2),
        QgsPointXY(cx + crane_size/2, cy + crane_size/2),
        QgsPointXY(cx - crane_size/2, cy + crane_size/2),
        QgsPointXY(cx - crane_size/2, cy - crane_size/2)
    ]
    crane_geom = QgsGeometry.fromPolygonXY([crane_points])

    # Foundation (smaller square inside crane pad)
    foundation_size = crane_size * 0.5
    foundation_points = [
        QgsPointXY(cx - foundation_size/2, cy - foundation_size/2),
        QgsPointXY(cx + foundation_size/2, cy - foundation_size/2),
        QgsPointXY(cx + foundation_size/2, cy + foundation_size/2),
        QgsPointXY(cx - foundation_size/2, cy + foundation_size/2),
        QgsPointXY(cx - foundation_size/2, cy - foundation_size/2)
    ]
    foundation_geom = QgsGeometry.fromPolygonXY([foundation_points])

    # Boom surface (rectangle extending from crane pad)
    boom_width = crane_size * 0.8
    boom_points = [
        QgsPointXY(cx - boom_width/2, cy + crane_size/2),
        QgsPointXY(cx + boom_width/2, cy + crane_size/2),
        QgsPointXY(cx + boom_width/2, cy + crane_size/2 + boom_length),
        QgsPointXY(cx - boom_width/2, cy + crane_size/2 + boom_length),
        QgsPointXY(cx - boom_width/2, cy + crane_size/2)
    ]
    boom_geom = QgsGeometry.fromPolygonXY([boom_points])

    # Rotor storage (square on opposite side)
    rotor_points = [
        QgsPointXY(cx - rotor_size/2, cy - crane_size/2 - rotor_size),
        QgsPointXY(cx + rotor_size/2, cy - crane_size/2 - rotor_size),
        QgsPointXY(cx + rotor_size/2, cy - crane_size/2),
        QgsPointXY(cx - rotor_size/2, cy - crane_size/2),
        QgsPointXY(cx - rotor_size/2, cy - crane_size/2 - rotor_size)
    ]
    rotor_geom = QgsGeometry.fromPolygonXY([rotor_points])

    return {
        'crane': crane_geom,
        'foundation': foundation_geom,
        'boom': boom_geom,
        'rotor': rotor_geom
    }


def create_test_project(geometries: Dict[str, QgsGeometry],
                        fok: float = 128.0,
                        height_range: Tuple[float, float] = (127.0, 129.0),
                        optimize_boom: bool = True,
                        optimize_rotor: bool = True) -> MultiSurfaceProject:
    """
    Create a test MultiSurfaceProject.

    Args:
        geometries: Dict with crane, foundation, boom, rotor geometries
        fok: Fertigoberkante (finished floor level)
        height_range: (min, max) for optimization
        optimize_boom: Enable boom slope optimization
        optimize_rotor: Enable rotor height optimization

    Returns:
        MultiSurfaceProject instance
    """
    crane_config = SurfaceConfig(
        surface_type=SurfaceType.CRANE_PAD,
        geometry=geometries['crane'],
        dxf_path='test.dxf',
        height_mode=HeightMode.OPTIMIZED
    )

    foundation_config = SurfaceConfig(
        surface_type=SurfaceType.FOUNDATION,
        geometry=geometries['foundation'],
        dxf_path='test.dxf',
        height_mode=HeightMode.FIXED,
        height_value=fok
    )

    boom_config = SurfaceConfig(
        surface_type=SurfaceType.BOOM,
        geometry=geometries['boom'],
        dxf_path='test.dxf',
        height_mode=HeightMode.SLOPED,
        slope_longitudinal=3.0
    )

    rotor_config = SurfaceConfig(
        surface_type=SurfaceType.ROTOR_STORAGE,
        geometry=geometries['rotor'],
        dxf_path='test.dxf',
        height_mode=HeightMode.RELATIVE
    )

    return MultiSurfaceProject(
        crane_pad=crane_config,
        foundation=foundation_config,
        boom=boom_config,
        rotor_storage=rotor_config,
        fok=fok,
        foundation_depth=3.5,
        gravel_thickness=0.5,
        rotor_height_offset=0.0,
        rotor_height_offset_max=0.5,
        slope_angle=45.0,
        search_range_below_fok=fok - height_range[0],
        search_range_above_fok=height_range[1] - fok,
        search_step=0.1,
        boom_slope_max=4.0,
        boom_slope_optimize=optimize_boom,
        boom_slope_step_coarse=0.5,
        boom_slope_step_fine=0.1,
        rotor_height_optimize=optimize_rotor,
        rotor_height_step_coarse=0.2,
        rotor_height_step_fine=0.05,
        optimize_for_net_earthwork=True
    )


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

class ParallelizationTestSuite:
    """Comprehensive test suite for parallelization validation."""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix='wt_parallel_test_')
        self.dem_path = None
        self.results = {}

    def setup(self):
        """Set up test environment."""
        print("\n" + "="*60)
        print("SETUP: Creating test environment")
        print("="*60)

        # Create synthetic DEM
        self.dem_path = os.path.join(self.temp_dir, 'test_dem.tif')
        create_synthetic_dem(
            self.dem_path,
            size=(200, 200),
            origin=(500000.0, 5500000.0),
            pixel_size=1.0,
            base_height=128.0,
            slope_x=0.01,
            slope_y=0.005,
            noise_amplitude=0.3
        )
        print(f"  Created DEM: {self.dem_path}")

        # Verify DEM
        dem_layer = QgsRasterLayer(self.dem_path, "test_dem")
        if not dem_layer.isValid():
            raise RuntimeError(f"Could not load DEM: {self.dem_path}")
        print(f"  DEM size: {dem_layer.width()} x {dem_layer.height()}")
        print(f"  DEM extent: {dem_layer.extent().toString()}")

    def cleanup(self):
        """Clean up test environment."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"\n  Cleaned up: {self.temp_dir}")

    def test_1_gdal_process_pool_safety(self) -> bool:
        """
        TEST 1: Verify GDAL works correctly in ProcessPoolExecutor.

        This tests the core assumption that GDAL is safe in separate processes.
        """
        print("\n" + "="*60)
        print("TEST 1: GDAL ProcessPool Safety")
        print("="*60)

        def gdal_worker(task: Tuple[int, str]) -> Tuple[int, float, float]:
            """Worker that reads DEM with GDAL."""
            task_id, dem_path = task

            ds = gdal.Open(dem_path, gdal.GA_ReadOnly)
            band = ds.GetRasterBand(1)
            data = band.ReadAsArray()

            mean_val = float(np.mean(data))
            std_val = float(np.std(data))

            ds = None
            return (task_id, mean_val, std_val)

        num_workers = min(mp.cpu_count(), 4)
        num_tasks = 20

        print(f"  Running {num_tasks} parallel GDAL reads with {num_workers} workers...")

        tasks = [(i, self.dem_path) for i in range(num_tasks)]

        start_time = time.time()

        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            results = list(executor.map(gdal_worker, tasks))

        elapsed = time.time() - start_time

        # Verify all results are consistent
        means = [r[1] for r in results]
        stds = [r[2] for r in results]

        mean_diff = max(means) - min(means)
        std_diff = max(stds) - min(stds)

        print(f"  Completed in {elapsed:.2f}s")
        print(f"  Mean elevation: {statistics.mean(means):.4f}m (range: {mean_diff:.6f})")
        print(f"  Std deviation: {statistics.mean(stds):.4f}m (range: {std_diff:.6f})")

        # Results should be identical (within floating point tolerance)
        if mean_diff < 1e-6 and std_diff < 1e-6:
            print("  RESULT: All workers returned identical results")
            print("  CONCLUSION: GDAL is safe in ProcessPoolExecutor")
            return True
        else:
            print("  RESULT: Results differ between workers!")
            print("  WARNING: Potential race condition detected")
            return False

    def test_2_sequential_baseline(self) -> bool:
        """
        TEST 2: Establish sequential baseline results.

        Run optimization sequentially to get reference results.
        """
        print("\n" + "="*60)
        print("TEST 2: Sequential Baseline")
        print("="*60)

        # Create test setup
        dem_layer = QgsRasterLayer(self.dem_path, "test_dem")
        center = (500050.0, 5500050.0)  # Center of DEM
        geometries = create_test_geometries(center)
        project = create_test_project(geometries)

        calculator = MultiSurfaceCalculator(dem_layer, project)

        # Force sequential execution
        calculator._use_vectorized = True  # Use fast method

        print("  Running sequential optimization...")
        start_time = time.time()

        optimal_height, result = calculator.find_optimum(
            feedback=None,
            use_parallel=False,  # Force sequential
            max_workers=1
        )

        elapsed = time.time() - start_time

        # Store baseline
        self.results['sequential'] = {
            'optimal_height': optimal_height,
            'total_cut': result.total_cut,
            'total_fill': result.total_fill,
            'net_volume': result.net_volume,
            'total_volume': result.total_volume_moved,
            'boom_slope': result.boom_slope_percent,
            'rotor_offset': result.rotor_height_offset_optimized,
            'elapsed_time': elapsed
        }

        print(f"  Completed in {elapsed:.2f}s")
        print(f"  Optimal height: {optimal_height:.2f}m")
        print(f"  Total cut: {result.total_cut:.1f}m³")
        print(f"  Total fill: {result.total_fill:.1f}m³")
        print(f"  Net volume: {result.net_volume:.1f}m³")
        print(f"  Boom slope: {result.boom_slope_percent:.2f}%")
        print(f"  Rotor offset: {result.rotor_height_offset_optimized:.3f}m")

        return True

    def test_3_parallel_vs_sequential(self) -> bool:
        """
        TEST 3: Compare parallel results with sequential baseline.

        Results must be identical (within tolerance).
        """
        print("\n" + "="*60)
        print("TEST 3: Parallel vs Sequential Comparison")
        print("="*60)

        if 'sequential' not in self.results:
            print("  ERROR: No sequential baseline. Run test_2 first.")
            return False

        baseline = self.results['sequential']

        # Create test setup
        dem_layer = QgsRasterLayer(self.dem_path, "test_dem")
        center = (500050.0, 5500050.0)
        geometries = create_test_geometries(center)
        project = create_test_project(geometries)

        calculator = MultiSurfaceCalculator(dem_layer, project)
        calculator._use_vectorized = True  # Enable vectorized GDAL

        num_workers = min(mp.cpu_count() - 1, 4)

        print(f"  Running parallel optimization with {num_workers} workers...")
        start_time = time.time()

        optimal_height, result = calculator.find_optimum(
            feedback=None,
            use_parallel=True,
            max_workers=num_workers
        )

        elapsed = time.time() - start_time

        # Store parallel results
        self.results['parallel'] = {
            'optimal_height': optimal_height,
            'total_cut': result.total_cut,
            'total_fill': result.total_fill,
            'net_volume': result.net_volume,
            'total_volume': result.total_volume_moved,
            'boom_slope': result.boom_slope_percent,
            'rotor_offset': result.rotor_height_offset_optimized,
            'elapsed_time': elapsed
        }

        print(f"  Completed in {elapsed:.2f}s")
        print(f"  Optimal height: {optimal_height:.2f}m")

        # Compare with baseline
        print("\n  Comparison with sequential baseline:")

        tolerance = {
            'optimal_height': 0.001,  # 1mm
            'total_cut': 0.1,         # 0.1m³
            'total_fill': 0.1,
            'net_volume': 0.1,
            'total_volume': 0.1,
            'boom_slope': 0.01,       # 0.01%
            'rotor_offset': 0.001     # 1mm
        }

        all_match = True
        for key, tol in tolerance.items():
            seq_val = baseline[key]
            par_val = self.results['parallel'][key]
            diff = abs(seq_val - par_val)

            if diff <= tol:
                status = "MATCH"
            else:
                status = "DIFF!"
                all_match = False

            print(f"    {key}: seq={seq_val:.4f}, par={par_val:.4f}, "
                  f"diff={diff:.6f} [{status}]")

        speedup = baseline['elapsed_time'] / elapsed
        print(f"\n  Speedup: {speedup:.2f}x")

        if all_match:
            print("  RESULT: All values match within tolerance")
            return True
        else:
            print("  RESULT: Values differ! Parallel implementation has issues.")
            return False

    def test_4_stability_multiple_runs(self, num_runs: int = 5) -> bool:
        """
        TEST 4: Stability test with multiple runs.

        Detect race conditions by running optimization multiple times
        and checking for consistent results.
        """
        print("\n" + "="*60)
        print(f"TEST 4: Stability Test ({num_runs} runs)")
        print("="*60)

        results_list = []

        dem_layer = QgsRasterLayer(self.dem_path, "test_dem")
        center = (500050.0, 5500050.0)
        geometries = create_test_geometries(center)

        for run in range(num_runs):
            project = create_test_project(geometries)
            calculator = MultiSurfaceCalculator(dem_layer, project)
            calculator._use_vectorized = True

            optimal_height, result = calculator.find_optimum(
                feedback=None,
                use_parallel=True,
                max_workers=min(mp.cpu_count() - 1, 4)
            )

            results_list.append({
                'run': run + 1,
                'optimal_height': optimal_height,
                'total_volume': result.total_volume_moved,
                'net_volume': result.net_volume
            })

            print(f"  Run {run + 1}: height={optimal_height:.3f}m, "
                  f"volume={result.total_volume_moved:.1f}m³")

        # Analyze variance
        heights = [r['optimal_height'] for r in results_list]
        volumes = [r['total_volume'] for r in results_list]

        height_std = statistics.stdev(heights) if len(heights) > 1 else 0
        volume_std = statistics.stdev(volumes) if len(volumes) > 1 else 0

        print(f"\n  Height std dev: {height_std:.6f}m")
        print(f"  Volume std dev: {volume_std:.6f}m³")

        # All runs should produce identical results
        if height_std < 1e-6 and volume_std < 1e-6:
            print("  RESULT: All runs produced identical results")
            print("  CONCLUSION: No race conditions detected")
            return True
        else:
            print("  RESULT: Results vary between runs!")
            print("  WARNING: Potential race condition or non-determinism")
            return False

    def test_5_vectorized_vs_legacy(self) -> bool:
        """
        TEST 5: Compare vectorized GDAL with legacy pixel-by-pixel.

        Both methods should produce identical results.
        """
        print("\n" + "="*60)
        print("TEST 5: Vectorized vs Legacy Sampling")
        print("="*60)

        dem_layer = QgsRasterLayer(self.dem_path, "test_dem")
        center = (500050.0, 5500050.0)
        geometries = create_test_geometries(center)
        project = create_test_project(geometries, optimize_boom=False, optimize_rotor=False)

        # Test with vectorized
        calculator_vec = MultiSurfaceCalculator(dem_layer, project)
        calculator_vec._use_vectorized = True

        print("  Running with vectorized sampling...")
        start_vec = time.time()
        height_vec, result_vec = calculator_vec.find_optimum(
            feedback=None, use_parallel=False
        )
        time_vec = time.time() - start_vec

        # Test with legacy
        project_legacy = create_test_project(geometries, optimize_boom=False, optimize_rotor=False)
        calculator_leg = MultiSurfaceCalculator(dem_layer, project_legacy)
        calculator_leg._use_vectorized = False

        print("  Running with legacy sampling...")
        start_leg = time.time()
        height_leg, result_leg = calculator_leg.find_optimum(
            feedback=None, use_parallel=False
        )
        time_leg = time.time() - start_leg

        print(f"\n  Vectorized: {time_vec:.2f}s, height={height_vec:.3f}m")
        print(f"  Legacy:     {time_leg:.2f}s, height={height_leg:.3f}m")
        print(f"  Speedup:    {time_leg/time_vec:.1f}x")

        # Compare results
        height_diff = abs(height_vec - height_leg)
        volume_diff = abs(result_vec.total_volume_moved - result_leg.total_volume_moved)

        print(f"\n  Height difference: {height_diff:.6f}m")
        print(f"  Volume difference: {volume_diff:.2f}m³")

        # Allow small differences due to pixel boundary effects
        if height_diff < 0.1 and volume_diff < 10.0:
            print("  RESULT: Results match within tolerance")
            return True
        else:
            print("  WARNING: Significant difference between methods")
            return False

    def test_6_performance_benchmark(self) -> bool:
        """
        TEST 6: Performance benchmark.

        Measure and report performance metrics.
        """
        print("\n" + "="*60)
        print("TEST 6: Performance Benchmark")
        print("="*60)

        dem_layer = QgsRasterLayer(self.dem_path, "test_dem")
        center = (500050.0, 5500050.0)
        geometries = create_test_geometries(center)

        configs = [
            ("Sequential (1 worker)", False, 1),
            ("Parallel (2 workers)", True, 2),
            ("Parallel (4 workers)", True, 4),
        ]

        if mp.cpu_count() > 4:
            configs.append((f"Parallel ({mp.cpu_count()-1} workers)", True, mp.cpu_count()-1))

        benchmark_results = []

        for name, parallel, workers in configs:
            project = create_test_project(geometries)
            calculator = MultiSurfaceCalculator(dem_layer, project)
            calculator._use_vectorized = True

            start = time.time()
            _, result = calculator.find_optimum(
                feedback=None,
                use_parallel=parallel,
                max_workers=workers
            )
            elapsed = time.time() - start

            benchmark_results.append({
                'name': name,
                'time': elapsed,
                'volume': result.total_volume_moved
            })

            print(f"  {name}: {elapsed:.2f}s")

        # Calculate speedups
        base_time = benchmark_results[0]['time']
        print("\n  Speedups relative to sequential:")
        for r in benchmark_results[1:]:
            speedup = base_time / r['time']
            print(f"    {r['name']}: {speedup:.2f}x")

        self.results['benchmark'] = benchmark_results
        return True

    def run_all(self) -> bool:
        """Run all tests and report results."""
        print("\n")
        print("=" * 60)
        print(" PARALLELIZATION TEST SUITE")
        print("=" * 60)

        if not QGIS_AVAILABLE:
            print("\nERROR: This test suite requires QGIS environment.")
            print("Please run in QGIS Python console or with qgis_process.")
            return False

        try:
            self.setup()

            tests = [
                ("GDAL ProcessPool Safety", self.test_1_gdal_process_pool_safety),
                ("Sequential Baseline", self.test_2_sequential_baseline),
                ("Parallel vs Sequential", self.test_3_parallel_vs_sequential),
                ("Stability (Race Conditions)", self.test_4_stability_multiple_runs),
                ("Vectorized vs Legacy", self.test_5_vectorized_vs_legacy),
                ("Performance Benchmark", self.test_6_performance_benchmark),
            ]

            results = []
            for name, test_func in tests:
                try:
                    result = test_func()
                    results.append((name, result))
                except Exception as e:
                    print(f"\n  ERROR in {name}: {e}")
                    import traceback
                    traceback.print_exc()
                    results.append((name, False))

            # Summary
            print("\n")
            print("=" * 60)
            print(" TEST SUMMARY")
            print("=" * 60)

            passed = sum(1 for _, r in results if r)
            total = len(results)

            for name, result in results:
                status = "PASS" if result else "FAIL"
                print(f"  [{status}] {name}")

            print("-" * 60)
            print(f"  Results: {passed}/{total} tests passed")

            if passed == total:
                print("\n  ALL TESTS PASSED - Safe to enable parallelization")
            else:
                print("\n  SOME TESTS FAILED - Review issues before enabling")

            return passed == total

        finally:
            self.cleanup()


def run_quick_test():
    """Run a quick smoke test for basic functionality."""
    print("\n")
    print("=" * 60)
    print(" QUICK SMOKE TEST")
    print("=" * 60)

    if not QGIS_AVAILABLE:
        print("\nERROR: QGIS not available. Cannot run tests.")
        return False

    suite = ParallelizationTestSuite()
    try:
        suite.setup()

        # Just run the most critical tests
        result1 = suite.test_1_gdal_process_pool_safety()
        result2 = suite.test_2_sequential_baseline()

        print("\n  Quick test completed.")
        return result1 and result2

    finally:
        suite.cleanup()


if __name__ == "__main__":
    # Initialize QGIS application if needed
    if QGIS_AVAILABLE:
        qgs = QgsApplication([], False)
        qgs.initQgis()

        try:
            # Parse arguments
            if len(sys.argv) > 1 and sys.argv[1] == '--quick':
                success = run_quick_test()
            else:
                suite = ParallelizationTestSuite()
                success = suite.run_all()

            sys.exit(0 if success else 1)

        finally:
            qgs.exitQgis()
    else:
        print("ERROR: QGIS/GDAL not available.")
        print("This test must be run in a QGIS environment.")
        print("\nTo run in QGIS Python console:")
        print("  exec(open('path/to/test_parallel_optimization.py').read())")
        print("\nOr with qgis_process:")
        print("  python3 test_parallel_optimization.py")
        sys.exit(1)
