"""
Tests for uncertainty propagation module.

Tests the UncertaintyConfig, UncertaintyResult, and related functions.
"""

import unittest
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.uncertainty import (
    UncertaintyConfig,
    UncertaintyResult,
    UncertaintyAnalysisResult,
    SensitivityResult,
    TerrainType,
    generate_parameter_samples,
    calculate_sobol_indices,
)


class TestUncertaintyConfig(unittest.TestCase):
    """Tests for UncertaintyConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = UncertaintyConfig()

        self.assertEqual(config.fok_std, 0.0)  # FOK default is 0
        self.assertEqual(config.dem_vertical_std, 0.075)  # Flat terrain default
        self.assertEqual(config.num_samples, 1000)
        self.assertTrue(config.use_latin_hypercube)
        self.assertEqual(config.terrain_type, TerrainType.FLAT)

    def test_terrain_type_adjustment(self):
        """Test DEM uncertainty adjustment based on terrain type."""
        # Flat terrain
        config_flat = UncertaintyConfig.for_terrain(TerrainType.FLAT)
        self.assertAlmostEqual(config_flat.dem_vertical_std, 0.075, places=3)

        # Moderate terrain
        config_mod = UncertaintyConfig.for_terrain(TerrainType.MODERATE)
        self.assertAlmostEqual(config_mod.dem_vertical_std, 0.10, places=3)

        # Steep terrain
        config_steep = UncertaintyConfig.for_terrain(TerrainType.STEEP)
        self.assertAlmostEqual(config_steep.dem_vertical_std, 0.15, places=3)

    def test_custom_config(self):
        """Test custom configuration."""
        config = UncertaintyConfig(
            fok_std=0.1,
            dem_vertical_std=0.2,
            num_samples=500,
            random_seed=42
        )

        self.assertEqual(config.fok_std, 0.1)
        self.assertEqual(config.dem_vertical_std, 0.2)
        self.assertEqual(config.num_samples, 500)
        self.assertEqual(config.random_seed, 42)

    def test_to_dict(self):
        """Test serialization to dictionary."""
        config = UncertaintyConfig()
        config_dict = config.to_dict()

        self.assertIn('dem_vertical_std', config_dict)
        self.assertIn('fok_std', config_dict)
        self.assertIn('num_samples', config_dict)
        self.assertEqual(config_dict['terrain_type'], 'flat')


class TestUncertaintyResult(unittest.TestCase):
    """Tests for UncertaintyResult dataclass."""

    def test_from_samples(self):
        """Test creating result from samples."""
        # Create known distribution
        np.random.seed(42)
        samples = np.random.normal(100, 10, 1000)

        result = UncertaintyResult.from_samples(samples, "test")

        # Check statistics
        self.assertAlmostEqual(result.mean, 100, delta=1)
        self.assertAlmostEqual(result.std, 10, delta=1)
        self.assertLess(result.percentile_5, result.mean)
        self.assertGreater(result.percentile_95, result.mean)
        self.assertEqual(len(result.samples), 1000)

    def test_confidence_intervals(self):
        """Test confidence interval methods."""
        samples = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        result = UncertaintyResult.from_samples(samples, "test")

        ci_90 = result.confidence_interval_90()
        ci_50 = result.confidence_interval_50()

        # 90% CI should be wider than 50% CI
        self.assertGreater(ci_90[1] - ci_90[0], ci_50[1] - ci_50[0])

    def test_format_summary(self):
        """Test formatted summary string."""
        samples = np.array([100, 101, 102, 103, 104])
        result = UncertaintyResult.from_samples(samples, "test")

        summary = result.format_summary("m³", 1)
        self.assertIn("m³", summary)
        self.assertIn("CV:", summary)

    def test_coefficient_of_variation(self):
        """Test CV calculation."""
        # Samples with mean=100, std=10 -> CV=0.1
        samples = np.array([90, 95, 100, 105, 110])
        result = UncertaintyResult.from_samples(samples, "test")

        self.assertGreater(result.coefficient_of_variation, 0)
        self.assertLess(result.coefficient_of_variation, 1)

    def test_to_dict(self):
        """Test serialization to dictionary."""
        samples = np.array([1, 2, 3, 4, 5])
        result = UncertaintyResult.from_samples(samples, "test")
        result_dict = result.to_dict()

        self.assertIn('mean', result_dict)
        self.assertIn('std', result_dict)
        self.assertIn('cv', result_dict)
        self.assertIn('n_samples', result_dict)
        self.assertEqual(result_dict['n_samples'], 5)


class TestSensitivityResult(unittest.TestCase):
    """Tests for SensitivityResult dataclass."""

    def test_from_samples(self):
        """Test creating sensitivity result from samples."""
        # Create correlated data
        param_values = np.array([1, 2, 3, 4, 5])
        output_values = np.array([10, 20, 30, 40, 50])

        result = SensitivityResult.from_samples("test_param", param_values, output_values)

        # Perfect positive correlation
        self.assertAlmostEqual(result.correlation, 1.0, places=5)
        self.assertGreater(result.linear_slope, 0)

    def test_negative_correlation(self):
        """Test with negative correlation."""
        param_values = np.array([1, 2, 3, 4, 5])
        output_values = np.array([50, 40, 30, 20, 10])

        result = SensitivityResult.from_samples("test_param", param_values, output_values)

        self.assertAlmostEqual(result.correlation, -1.0, places=5)
        self.assertLess(result.linear_slope, 0)

    def test_no_correlation(self):
        """Test with no correlation."""
        np.random.seed(42)
        param_values = np.random.random(100)
        output_values = np.random.random(100)

        result = SensitivityResult.from_samples("test_param", param_values, output_values)

        # Should be close to zero
        self.assertLess(abs(result.correlation), 0.3)


class TestParameterSampling(unittest.TestCase):
    """Tests for parameter sampling functions."""

    def test_generate_samples_shape(self):
        """Test that generated samples have correct shape."""
        config = UncertaintyConfig(num_samples=100, random_seed=42)
        base_values = {
            'fok': 305.5,
            'slope_angle': 45.0,
            'foundation_depth': 3.5,
            'gravel_thickness': 0.5,
        }

        samples = generate_parameter_samples(config, base_values)

        # Check all expected keys present
        self.assertIn('fok', samples)
        self.assertIn('slope_angle', samples)
        self.assertIn('dem_noise', samples)

        # Check correct number of samples
        for key, values in samples.items():
            self.assertEqual(len(values), 100, f"Wrong number of samples for {key}")

    def test_reproducibility_with_seed(self):
        """Test that samples are reproducible with same seed."""
        config = UncertaintyConfig(num_samples=50, random_seed=42)
        base_values = {'fok': 305.5, 'slope_angle': 45.0,
                       'foundation_depth': 3.5, 'gravel_thickness': 0.5}

        samples1 = generate_parameter_samples(config, base_values)
        samples2 = generate_parameter_samples(config, base_values)

        # Should be identical with same seed
        np.testing.assert_array_almost_equal(samples1['fok'], samples2['fok'])

    def test_zero_uncertainty(self):
        """Test with zero uncertainty for FOK."""
        config = UncertaintyConfig(
            num_samples=100,
            fok_std=0.0,  # No FOK uncertainty
            dem_vertical_std=0.1,
            random_seed=42
        )
        base_values = {'fok': 305.5, 'slope_angle': 45.0,
                       'foundation_depth': 3.5, 'gravel_thickness': 0.5}

        samples = generate_parameter_samples(config, base_values)

        # FOK should be constant
        self.assertTrue(np.all(samples['fok'] == 305.5))

    def test_sample_distribution(self):
        """Test that samples follow expected distributions."""
        config = UncertaintyConfig(
            num_samples=10000,
            fok_std=0.2,
            dem_vertical_std=0.1,
            random_seed=42
        )
        base_values = {'fok': 305.5, 'slope_angle': 45.0,
                       'foundation_depth': 3.5, 'gravel_thickness': 0.5}

        samples = generate_parameter_samples(config, base_values)

        # Check FOK distribution
        fok_mean = np.mean(samples['fok'])
        fok_std = np.std(samples['fok'])

        self.assertAlmostEqual(fok_mean, 305.5, delta=0.05)
        self.assertAlmostEqual(fok_std, 0.2, delta=0.02)


class TestSobolIndices(unittest.TestCase):
    """Tests for Sobol sensitivity index calculation."""

    def test_single_dominant_parameter(self):
        """Test with one dominant parameter."""
        n = 1000
        np.random.seed(42)

        # Create samples where only param1 affects output
        samples = {
            'param1': np.random.normal(0, 1, n),
            'param2': np.random.normal(0, 1, n),
        }

        # Output only depends on param1
        output_values = 2 * samples['param1'] + 0.01 * np.random.random(n)

        indices = calculate_sobol_indices(samples, output_values, ['param1', 'param2'])

        # param1 should have much higher index
        self.assertGreater(indices['param1'][0], indices['param2'][0])
        self.assertGreater(indices['param1'][0], 0.8)

    def test_equal_parameters(self):
        """Test with equally important parameters."""
        n = 1000
        np.random.seed(42)

        samples = {
            'param1': np.random.normal(0, 1, n),
            'param2': np.random.normal(0, 1, n),
        }

        # Output depends equally on both
        output_values = samples['param1'] + samples['param2']

        indices = calculate_sobol_indices(samples, output_values, ['param1', 'param2'])

        # Both should have similar indices
        diff = abs(indices['param1'][0] - indices['param2'][0])
        self.assertLess(diff, 0.2)

    def test_no_variance_output(self):
        """Test with constant output (no variance)."""
        n = 100
        samples = {
            'param1': np.random.normal(0, 1, n),
        }
        output_values = np.ones(n) * 100  # Constant

        indices = calculate_sobol_indices(samples, output_values, ['param1'])

        # Should be zero (no sensitivity)
        self.assertEqual(indices['param1'][0], 0.0)


if __name__ == '__main__':
    unittest.main()
