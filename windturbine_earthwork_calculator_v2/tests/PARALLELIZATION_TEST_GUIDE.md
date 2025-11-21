# Parallelization Test Guide

**Version:** 2.0.0
**Date:** 2025-11-21

## Overview

This guide describes how to test the parallel optimization implementation for crane pad height calculation.

## Test Suite Location

```
windturbine_earthwork_calculator_v2/tests/test_parallel_optimization.py
```

## Prerequisites

- QGIS 3.x with Python support
- GDAL/OGR Python bindings
- NumPy

## Running the Tests

### Option 1: QGIS Python Console

```python
import sys
sys.path.insert(0, '/path/to/Wind-Turbine-Earthwork-Calculator')
exec(open('/path/to/tests/test_parallel_optimization.py').read())
```

### Option 2: Command Line (with QGIS environment)

```bash
# On Linux with QGIS installed:
export PYTHONPATH=/usr/share/qgis/python:$PYTHONPATH
python3 windturbine_earthwork_calculator_v2/tests/test_parallel_optimization.py

# Quick smoke test:
python3 test_parallel_optimization.py --quick
```

### Option 3: qgis_process

```bash
qgis_process run script:test_parallel_optimization
```

## Test Descriptions

### Test 1: GDAL ProcessPool Safety

**Purpose:** Verify that GDAL can safely be used in separate processes via ProcessPoolExecutor.

**What it does:**
- Spawns multiple worker processes
- Each worker opens the same DEM file with GDAL
- Reads and calculates statistics
- Compares results across all workers

**Pass Criteria:**
- All workers return identical results (within floating-point tolerance)
- No crashes or deadlocks

**Why this matters:**
ProcessPoolExecutor uses separate processes (not threads), so each process has its own memory space and GDAL instance. This test validates that this approach is safe.

### Test 2: Sequential Baseline

**Purpose:** Establish reference results from sequential execution.

**What it does:**
- Creates synthetic DEM and test geometries
- Runs optimization in sequential mode
- Records optimal height, volumes, and computation time

**Pass Criteria:**
- Optimization completes without errors
- Returns valid results

### Test 3: Parallel vs Sequential Comparison

**Purpose:** Verify that parallel execution produces identical results to sequential.

**What it does:**
- Runs the same optimization in parallel mode
- Compares all result values with the sequential baseline

**Pass Criteria:**
- Optimal height matches within 1mm
- Cut/fill volumes match within 0.1m³
- Boom slope matches within 0.01%
- Rotor offset matches within 1mm

**Why this matters:**
If parallel and sequential results differ, it indicates a race condition, serialization issue, or numerical instability.

### Test 4: Stability (Race Condition Detection)

**Purpose:** Detect race conditions through multiple runs.

**What it does:**
- Runs parallel optimization N times (default: 5)
- Records results from each run
- Calculates standard deviation of results

**Pass Criteria:**
- All runs produce identical results
- Standard deviation is essentially zero

**Why this matters:**
Race conditions may not appear on every run. Multiple runs increase the chance of detecting intermittent issues.

### Test 5: Vectorized vs Legacy Sampling

**Purpose:** Verify that vectorized GDAL sampling produces same results as legacy pixel-by-pixel method.

**What it does:**
- Runs optimization with vectorized=True
- Runs optimization with vectorized=False
- Compares results

**Pass Criteria:**
- Results match within tolerance (small differences allowed due to pixel boundary effects)

**Why this matters:**
The vectorized method is 100-1000x faster but uses different algorithms. Results must be consistent.

### Test 6: Performance Benchmark

**Purpose:** Measure and document performance improvements.

**What it does:**
- Runs optimization with different worker counts
- Measures elapsed time for each configuration
- Calculates speedup ratios

**Expected Results:**
- 2 workers: ~1.5-2x speedup
- 4 workers: ~2.5-4x speedup
- N workers: diminishing returns due to overhead

## Interpreting Results

### All Tests Pass

Safe to use parallel optimization in production.

### Test 1 Fails

GDAL has issues in your environment. Consider:
- Checking GDAL version compatibility
- Verifying environment variables
- Using legacy (sequential) mode only

### Test 3 or 4 Fails

There's a race condition or serialization issue:
- Check for shared state between workers
- Verify all data is properly serialized
- Check for floating-point comparison issues

### Test 5 Fails

Significant differences between sampling methods:
- May indicate coordinate transformation issues
- Could be pixel alignment differences
- Consider using legacy method if differences are unacceptable

## Troubleshooting

### Workers Fail with Pickling Errors

Ensure all objects passed to workers are pickle-able:
- QgsGeometry → convert to WKT string
- QgsRasterLayer → pass file path instead
- Custom objects → use to_dict()/from_dict()

### Workers Timeout

Increase timeout or reduce scenario count:
```python
with ProcessPoolExecutor(max_workers=N) as executor:
    future = executor.submit(worker, timeout=300)  # 5 minutes
```

### Memory Issues

Each worker loads its own DEM copy. For large DEMs:
- Reduce worker count
- Use memory-mapped files
- Consider chunking strategies

## Implementation Details

### Key Changes Made

1. **Worker vectorization enabled** (`multi_surface_calculator.py:149-152`)
   - Changed from `_use_vectorized = False` to `_use_vectorized = use_vectorized`
   - ProcessPoolExecutor uses separate processes, so GDAL is safe

2. **Parallel method actually called** (`multi_surface_calculator.py:1505`)
   - Changed `_find_optimum_sequential` to `_find_optimum_parallel`
   - Added fallback to sequential on failure

3. **Multi-parameter parallel execution** (`multi_surface_calculator.py:1377-1494, 1614-1725`)
   - Coarse search parallelized when scenarios >= 20
   - Fine search parallelized when scenarios >= 20
   - Sequential fallback for small scenario counts

4. **New worker function** (`multi_surface_calculator.py:169-275`)
   - `_calculate_multi_param_scenario()` for (height, slope, offset) tuples

### Architecture

```
find_optimum()
├── _find_optimum_single_parameter()
│   ├── _find_optimum_parallel()     [ProcessPoolExecutor]
│   └── _find_optimum_sequential()   [Fallback]
│
└── _find_optimum_multi_parameter()
    ├── Coarse Search
    │   ├── Parallel execution       [ProcessPoolExecutor]
    │   └── Sequential execution     [Fallback]
    │
    └── Fine Search
        ├── Parallel execution       [ProcessPoolExecutor]
        └── Sequential execution     [Fallback]
```

## Expected Performance

| Scenario Count | Workers | Expected Speedup |
|----------------|---------|------------------|
| 100            | 2       | 1.5-2x           |
| 100            | 4       | 2-3x             |
| 500            | 4       | 3-4x             |
| 2000           | 4       | 3.5-4x           |
| 2000           | 8       | 4-6x             |

Note: Speedup depends on:
- DEM size (affects I/O overhead)
- CPU core count
- Available memory
- Disk speed

## Safety Fallbacks

The implementation includes multiple safety nets:

1. **Scenario count threshold**: Only parallelize if >= 20 scenarios
2. **Worker count limit**: Uses `cpu_count - 1` by default
3. **Exception handling**: Falls back to sequential on any parallel error
4. **Result validation**: Logs successful/failed scenario counts

## Next Steps

After running tests successfully:

1. Test with real DEM and DXF data
2. Benchmark on target hardware
3. Adjust worker count for optimal performance
4. Consider adding progress callbacks for GUI integration
