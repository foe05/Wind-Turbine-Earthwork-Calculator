"""
Tests for chart generation module.

Tests all chart generation functions including volume charts, pie charts,
breakdown charts, and comparison charts.
"""

import unittest
import base64
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.chart_generator import (
    generate_volume_chart,
    generate_volume_pie_chart,
    generate_volume_breakdown_chart,
    generate_multi_site_comparison_chart,
    generate_cost_comparison_chart,
    is_matplotlib_available,
    MATPLOTLIB_AVAILABLE
)


class TestMatplotlibAvailability(unittest.TestCase):
    """Tests for matplotlib availability check."""

    def test_is_matplotlib_available(self):
        """Test matplotlib availability function."""
        result = is_matplotlib_available()
        self.assertIsInstance(result, bool)
        self.assertEqual(result, MATPLOTLIB_AVAILABLE)


@unittest.skipIf(not MATPLOTLIB_AVAILABLE, "matplotlib not available")
class TestGenerateVolumeChart(unittest.TestCase):
    """Tests for generate_volume_chart function."""

    def test_basic_volume_chart(self):
        """Test basic volume chart generation."""
        result = generate_volume_chart(
            cut_volume=1000.0,
            fill_volume=800.0
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        # Should be valid base64
        try:
            base64.b64decode(result)
        except Exception as e:
            self.fail(f"Invalid base64 output: {e}")

    def test_zero_volumes(self):
        """Test chart with zero volumes."""
        result = generate_volume_chart(
            cut_volume=0.0,
            fill_volume=0.0
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_large_volumes(self):
        """Test chart with large volumes."""
        result = generate_volume_chart(
            cut_volume=1000000.0,
            fill_volume=500000.0
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_custom_title(self):
        """Test chart with custom title."""
        result = generate_volume_chart(
            cut_volume=1000.0,
            fill_volume=800.0,
            title="Custom Title"
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_custom_figsize(self):
        """Test chart with custom figure size."""
        result = generate_volume_chart(
            cut_volume=1000.0,
            fill_volume=800.0,
            figsize=(8, 4)
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_custom_dpi(self):
        """Test chart with custom DPI."""
        result = generate_volume_chart(
            cut_volume=1000.0,
            fill_volume=800.0,
            dpi=100
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_non_base64_output(self):
        """Test chart with non-base64 output format."""
        result = generate_volume_chart(
            cut_volume=1000.0,
            fill_volume=800.0,
            output_format="file"
        )

        # Should return None for non-base64 output
        self.assertIsNone(result)

    def test_negative_volumes(self):
        """Test chart handles negative volumes gracefully."""
        # Should still generate chart (matplotlib will handle it)
        result = generate_volume_chart(
            cut_volume=-100.0,
            fill_volume=800.0
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)


@unittest.skipIf(not MATPLOTLIB_AVAILABLE, "matplotlib not available")
class TestGenerateVolumePieChart(unittest.TestCase):
    """Tests for generate_volume_pie_chart function."""

    def test_basic_pie_chart(self):
        """Test basic pie chart generation."""
        result = generate_volume_pie_chart(
            cut_volume=1000.0,
            fill_volume=800.0
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        # Should be valid base64
        try:
            base64.b64decode(result)
        except Exception as e:
            self.fail(f"Invalid base64 output: {e}")

    def test_equal_volumes(self):
        """Test pie chart with equal volumes."""
        result = generate_volume_pie_chart(
            cut_volume=1000.0,
            fill_volume=1000.0
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_one_zero_volume(self):
        """Test pie chart with one zero volume."""
        result = generate_volume_pie_chart(
            cut_volume=1000.0,
            fill_volume=0.0
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_custom_title(self):
        """Test pie chart with custom title."""
        result = generate_volume_pie_chart(
            cut_volume=1000.0,
            fill_volume=800.0,
            title="Custom Distribution"
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_custom_figsize(self):
        """Test pie chart with custom figure size."""
        result = generate_volume_pie_chart(
            cut_volume=1000.0,
            fill_volume=800.0,
            figsize=(6, 6)
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_non_base64_output(self):
        """Test pie chart with non-base64 output format."""
        result = generate_volume_pie_chart(
            cut_volume=1000.0,
            fill_volume=800.0,
            output_format="file"
        )

        # Should return None for non-base64 output
        self.assertIsNone(result)


@unittest.skipIf(not MATPLOTLIB_AVAILABLE, "matplotlib not available")
class TestGenerateVolumeBreakdownChart(unittest.TestCase):
    """Tests for generate_volume_breakdown_chart function."""

    def test_basic_breakdown_chart(self):
        """Test basic breakdown chart generation."""
        result = generate_volume_breakdown_chart(
            platform_cut=500.0,
            platform_fill=400.0,
            slope_cut=300.0,
            slope_fill=200.0,
            foundation_volume=100.0
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        # Should be valid base64
        try:
            base64.b64decode(result)
        except Exception as e:
            self.fail(f"Invalid base64 output: {e}")

    def test_zero_values(self):
        """Test breakdown chart with all zero values."""
        result = generate_volume_breakdown_chart(
            platform_cut=0.0,
            platform_fill=0.0,
            slope_cut=0.0,
            slope_fill=0.0,
            foundation_volume=0.0
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_large_values(self):
        """Test breakdown chart with large values."""
        result = generate_volume_breakdown_chart(
            platform_cut=500000.0,
            platform_fill=400000.0,
            slope_cut=300000.0,
            slope_fill=200000.0,
            foundation_volume=100000.0
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_custom_title(self):
        """Test breakdown chart with custom title."""
        result = generate_volume_breakdown_chart(
            platform_cut=500.0,
            platform_fill=400.0,
            slope_cut=300.0,
            slope_fill=200.0,
            foundation_volume=100.0,
            title="Custom Breakdown"
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_custom_figsize(self):
        """Test breakdown chart with custom figure size."""
        result = generate_volume_breakdown_chart(
            platform_cut=500.0,
            platform_fill=400.0,
            slope_cut=300.0,
            slope_fill=200.0,
            foundation_volume=100.0,
            figsize=(10, 5)
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_non_base64_output(self):
        """Test breakdown chart with non-base64 output format."""
        result = generate_volume_breakdown_chart(
            platform_cut=500.0,
            platform_fill=400.0,
            slope_cut=300.0,
            slope_fill=200.0,
            foundation_volume=100.0,
            output_format="file"
        )

        # Should return None for non-base64 output
        self.assertIsNone(result)

    def test_only_platform_volumes(self):
        """Test breakdown chart with only platform volumes."""
        result = generate_volume_breakdown_chart(
            platform_cut=1000.0,
            platform_fill=800.0,
            slope_cut=0.0,
            slope_fill=0.0,
            foundation_volume=0.0
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)


@unittest.skipIf(not MATPLOTLIB_AVAILABLE, "matplotlib not available")
class TestGenerateMultiSiteComparisonChart(unittest.TestCase):
    """Tests for generate_multi_site_comparison_chart function."""

    def test_basic_multi_site_chart(self):
        """Test basic multi-site comparison chart."""
        sites_data = [
            {'id': 'WKA-01', 'total_cut': 1000.0, 'total_fill': 800.0},
            {'id': 'WKA-02', 'total_cut': 1200.0, 'total_fill': 900.0},
            {'id': 'WKA-03', 'total_cut': 800.0, 'total_fill': 700.0},
        ]

        result = generate_multi_site_comparison_chart(sites_data)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        # Should be valid base64
        try:
            base64.b64decode(result)
        except Exception as e:
            self.fail(f"Invalid base64 output: {e}")

    def test_single_site(self):
        """Test comparison chart with single site."""
        sites_data = [
            {'id': 'WKA-01', 'total_cut': 1000.0, 'total_fill': 800.0},
        ]

        result = generate_multi_site_comparison_chart(sites_data)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_empty_sites_list(self):
        """Test comparison chart with empty sites list."""
        sites_data = []

        result = generate_multi_site_comparison_chart(sites_data)

        # Should return None for empty list
        self.assertIsNone(result)

    def test_many_sites(self):
        """Test comparison chart with many sites."""
        sites_data = [
            {'id': f'WKA-{i:02d}', 'total_cut': 1000.0 + i*100, 'total_fill': 800.0 + i*50}
            for i in range(1, 11)
        ]

        result = generate_multi_site_comparison_chart(sites_data)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_zero_volumes(self):
        """Test comparison chart with zero volumes."""
        sites_data = [
            {'id': 'WKA-01', 'total_cut': 0.0, 'total_fill': 0.0},
            {'id': 'WKA-02', 'total_cut': 0.0, 'total_fill': 0.0},
        ]

        result = generate_multi_site_comparison_chart(sites_data)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_custom_title(self):
        """Test comparison chart with custom title."""
        sites_data = [
            {'id': 'WKA-01', 'total_cut': 1000.0, 'total_fill': 800.0},
            {'id': 'WKA-02', 'total_cut': 1200.0, 'total_fill': 900.0},
        ]

        result = generate_multi_site_comparison_chart(
            sites_data,
            title="Custom Comparison"
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_custom_figsize(self):
        """Test comparison chart with custom figure size."""
        sites_data = [
            {'id': 'WKA-01', 'total_cut': 1000.0, 'total_fill': 800.0},
        ]

        result = generate_multi_site_comparison_chart(
            sites_data,
            figsize=(10, 5)
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_non_base64_output(self):
        """Test comparison chart with non-base64 output format."""
        sites_data = [
            {'id': 'WKA-01', 'total_cut': 1000.0, 'total_fill': 800.0},
        ]

        result = generate_multi_site_comparison_chart(
            sites_data,
            output_format="file"
        )

        # Should return None for non-base64 output
        self.assertIsNone(result)


@unittest.skipIf(not MATPLOTLIB_AVAILABLE, "matplotlib not available")
class TestGenerateCostComparisonChart(unittest.TestCase):
    """Tests for generate_cost_comparison_chart function."""

    def test_basic_cost_chart(self):
        """Test basic cost comparison chart."""
        sites_data = [
            {'id': 'WKA-01', 'cost_total': 50000.0},
            {'id': 'WKA-02', 'cost_total': 60000.0},
            {'id': 'WKA-03', 'cost_total': 45000.0},
        ]

        result = generate_cost_comparison_chart(sites_data)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        # Should be valid base64
        try:
            base64.b64decode(result)
        except Exception as e:
            self.fail(f"Invalid base64 output: {e}")

    def test_single_site_cost(self):
        """Test cost chart with single site."""
        sites_data = [
            {'id': 'WKA-01', 'cost_total': 50000.0},
        ]

        result = generate_cost_comparison_chart(sites_data)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_empty_sites_list_cost(self):
        """Test cost chart with empty sites list."""
        sites_data = []

        result = generate_cost_comparison_chart(sites_data)

        # Should return None for empty list
        self.assertIsNone(result)

    def test_many_sites_cost(self):
        """Test cost chart with many sites."""
        sites_data = [
            {'id': f'WKA-{i:02d}', 'cost_total': 50000.0 + i*5000}
            for i in range(1, 11)
        ]

        result = generate_cost_comparison_chart(sites_data)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_zero_costs(self):
        """Test cost chart with zero costs."""
        sites_data = [
            {'id': 'WKA-01', 'cost_total': 0.0},
            {'id': 'WKA-02', 'cost_total': 0.0},
        ]

        result = generate_cost_comparison_chart(sites_data)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_large_costs(self):
        """Test cost chart with large costs."""
        sites_data = [
            {'id': 'WKA-01', 'cost_total': 5000000.0},
            {'id': 'WKA-02', 'cost_total': 6000000.0},
        ]

        result = generate_cost_comparison_chart(sites_data)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_custom_title_cost(self):
        """Test cost chart with custom title."""
        sites_data = [
            {'id': 'WKA-01', 'cost_total': 50000.0},
            {'id': 'WKA-02', 'cost_total': 60000.0},
        ]

        result = generate_cost_comparison_chart(
            sites_data,
            title="Custom Cost Comparison"
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_custom_figsize_cost(self):
        """Test cost chart with custom figure size."""
        sites_data = [
            {'id': 'WKA-01', 'cost_total': 50000.0},
        ]

        result = generate_cost_comparison_chart(
            sites_data,
            figsize=(10, 5)
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_non_base64_output_cost(self):
        """Test cost chart with non-base64 output format."""
        sites_data = [
            {'id': 'WKA-01', 'cost_total': 50000.0},
        ]

        result = generate_cost_comparison_chart(
            sites_data,
            output_format="file"
        )

        # Should return None for non-base64 output
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
