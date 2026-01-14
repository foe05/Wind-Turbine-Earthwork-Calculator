
import unittest
from unittest.mock import MagicMock
import os
import sys
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qgis.core import QgsPointXY

from windturbine_earthwork_calculator_v2.core.site_aggregator import SiteAggregator
from windturbine_earthwork_calculator_v2.core.site_data import SiteData, MultiSiteProject
from windturbine_earthwork_calculator_v2.core.surface_types import MultiSurfaceCalculationResult, SurfaceType

class TestSiteAggregator(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.aggregator = SiteAggregator()

        # Create mock calculation results for site 1
        self.calc_result_1 = MagicMock(spec=MultiSurfaceCalculationResult)
        self.calc_result_1.total_cut = 1000.0
        self.calc_result_1.total_fill = 800.0
        self.calc_result_1.net_volume = 200.0
        self.calc_result_1.total_volume_moved = 1800.0
        self.calc_result_1.crane_height = 100.0
        self.calc_result_1.fok = 102.0

        # Create mock calculation results for site 2
        self.calc_result_2 = MagicMock(spec=MultiSurfaceCalculationResult)
        self.calc_result_2.total_cut = 1500.0
        self.calc_result_2.total_fill = 1200.0
        self.calc_result_2.net_volume = 300.0
        self.calc_result_2.total_volume_moved = 2700.0
        self.calc_result_2.crane_height = 105.0
        self.calc_result_2.fok = 107.0

        # Create mock calculation results for site 3
        self.calc_result_3 = MagicMock(spec=MultiSurfaceCalculationResult)
        self.calc_result_3.total_cut = 800.0
        self.calc_result_3.total_fill = 600.0
        self.calc_result_3.net_volume = 200.0
        self.calc_result_3.total_volume_moved = 1400.0
        self.calc_result_3.crane_height = 98.0
        self.calc_result_3.fok = 100.0

        # Create costs dictionaries
        self.costs_1 = {
            'cost_total': 50000.0,
            'cost_excavation': 10000.0,
            'cost_transport': 15000.0,
            'cost_fill': 8000.0,
            'cost_gravel': 12000.0,
            'cost_compaction': 5000.0,
            'cost_saving': 2000.0
        }

        self.costs_2 = {
            'cost_total': 75000.0,
            'cost_excavation': 15000.0,
            'cost_transport': 22000.0,
            'cost_fill': 12000.0,
            'cost_gravel': 18000.0,
            'cost_compaction': 8000.0,
            'cost_saving': 3000.0
        }

        self.costs_3 = {
            'cost_total': 40000.0,
            'cost_excavation': 8000.0,
            'cost_transport': 12000.0,
            'cost_fill': 6000.0,
            'cost_gravel': 10000.0,
            'cost_compaction': 4000.0,
            'cost_saving': 1500.0
        }

        # Create SiteData objects
        self.site_1 = SiteData(
            site_id='WEA01',
            site_name='Turbine 01',
            location=QgsPointXY(100.0, 200.0),
            calculation_result=self.calc_result_1,
            costs=self.costs_1,
            calculation_timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )

        self.site_2 = SiteData(
            site_id='WEA02',
            site_name='Turbine 02',
            location=QgsPointXY(150.0, 250.0),
            calculation_result=self.calc_result_2,
            costs=self.costs_2,
            calculation_timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )

        self.site_3 = SiteData(
            site_id='WEA03',
            site_name='Turbine 03',
            location=QgsPointXY(120.0, 220.0),
            calculation_result=self.calc_result_3,
            costs=self.costs_3,
            calculation_timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )

        self.sites = [self.site_1, self.site_2, self.site_3]

    def test_aggregate_volumes_empty_list(self):
        """Test aggregate_volumes with empty site list."""
        result = self.aggregator.aggregate_volumes([])

        self.assertEqual(result['total_cut'], 0.0)
        self.assertEqual(result['total_fill'], 0.0)
        self.assertEqual(result['net_volume'], 0.0)
        self.assertEqual(result['total_volume_moved'], 0.0)
        self.assertEqual(result['avg_cut'], 0.0)
        self.assertEqual(result['avg_fill'], 0.0)
        self.assertEqual(result['avg_volume_moved'], 0.0)
        self.assertEqual(result['min_volume_moved'], 0.0)
        self.assertEqual(result['max_volume_moved'], 0.0)
        self.assertEqual(result['site_count'], 0)

    def test_aggregate_volumes_single_site(self):
        """Test aggregate_volumes with single site."""
        result = self.aggregator.aggregate_volumes([self.site_1])

        self.assertEqual(result['total_cut'], 1000.0)
        self.assertEqual(result['total_fill'], 800.0)
        self.assertEqual(result['net_volume'], 200.0)
        self.assertEqual(result['total_volume_moved'], 1800.0)
        self.assertEqual(result['avg_cut'], 1000.0)
        self.assertEqual(result['avg_fill'], 800.0)
        self.assertEqual(result['avg_volume_moved'], 1800.0)
        self.assertEqual(result['min_volume_moved'], 1800.0)
        self.assertEqual(result['max_volume_moved'], 1800.0)
        self.assertEqual(result['site_count'], 1)

    def test_aggregate_volumes_multiple_sites(self):
        """Test aggregate_volumes with multiple sites."""
        result = self.aggregator.aggregate_volumes(self.sites)

        # Total cut: 1000 + 1500 + 800 = 3300
        self.assertEqual(result['total_cut'], 3300.0)
        # Total fill: 800 + 1200 + 600 = 2600
        self.assertEqual(result['total_fill'], 2600.0)
        # Net volume: 3300 - 2600 = 700
        self.assertEqual(result['net_volume'], 700.0)
        # Total volume moved: 1800 + 2700 + 1400 = 5900
        self.assertEqual(result['total_volume_moved'], 5900.0)
        # Averages
        self.assertAlmostEqual(result['avg_cut'], 1100.0, places=2)
        self.assertAlmostEqual(result['avg_fill'], 866.67, places=2)
        self.assertAlmostEqual(result['avg_volume_moved'], 1966.67, places=2)
        # Min/Max
        self.assertEqual(result['min_volume_moved'], 1400.0)
        self.assertEqual(result['max_volume_moved'], 2700.0)
        self.assertEqual(result['site_count'], 3)

    def test_aggregate_costs_empty_list(self):
        """Test aggregate_costs with empty site list."""
        result = self.aggregator.aggregate_costs([])

        self.assertEqual(result['total_cost'], 0.0)
        self.assertEqual(result['cost_excavation'], 0.0)
        self.assertEqual(result['cost_transport'], 0.0)
        self.assertEqual(result['cost_fill'], 0.0)
        self.assertEqual(result['cost_gravel'], 0.0)
        self.assertEqual(result['cost_compaction'], 0.0)
        self.assertEqual(result['cost_saving'], 0.0)
        self.assertEqual(result['avg_cost'], 0.0)
        self.assertEqual(result['min_cost'], 0.0)
        self.assertEqual(result['max_cost'], 0.0)
        self.assertEqual(result['site_count'], 0)

    def test_aggregate_costs_single_site(self):
        """Test aggregate_costs with single site."""
        result = self.aggregator.aggregate_costs([self.site_1])

        self.assertEqual(result['total_cost'], 50000.0)
        self.assertEqual(result['cost_excavation'], 10000.0)
        self.assertEqual(result['cost_transport'], 15000.0)
        self.assertEqual(result['cost_fill'], 8000.0)
        self.assertEqual(result['cost_gravel'], 12000.0)
        self.assertEqual(result['cost_compaction'], 5000.0)
        self.assertEqual(result['cost_saving'], 2000.0)
        self.assertEqual(result['avg_cost'], 50000.0)
        self.assertEqual(result['min_cost'], 50000.0)
        self.assertEqual(result['max_cost'], 50000.0)
        self.assertEqual(result['site_count'], 1)

    def test_aggregate_costs_multiple_sites(self):
        """Test aggregate_costs with multiple sites."""
        result = self.aggregator.aggregate_costs(self.sites)

        # Total cost: 50000 + 75000 + 40000 = 165000
        self.assertEqual(result['total_cost'], 165000.0)
        # Sum each category
        self.assertEqual(result['cost_excavation'], 33000.0)
        self.assertEqual(result['cost_transport'], 49000.0)
        self.assertEqual(result['cost_fill'], 26000.0)
        self.assertEqual(result['cost_gravel'], 40000.0)
        self.assertEqual(result['cost_compaction'], 17000.0)
        self.assertEqual(result['cost_saving'], 6500.0)
        # Average
        self.assertEqual(result['avg_cost'], 55000.0)
        # Min/Max
        self.assertEqual(result['min_cost'], 40000.0)
        self.assertEqual(result['max_cost'], 75000.0)
        self.assertEqual(result['site_count'], 3)

    def test_aggregate_project(self):
        """Test aggregate_project with MultiSiteProject."""
        project = MultiSiteProject(
            project_name='Test Wind Farm',
            sites=self.sites
        )

        result = self.aggregator.aggregate_project(project)

        self.assertEqual(result['project_name'], 'Test Wind Farm')
        self.assertEqual(result['site_count'], 3)
        self.assertIn('volumes', result)
        self.assertIn('costs', result)
        self.assertIn('statistics', result)

        # Check volumes
        self.assertEqual(result['volumes']['total_cut'], 3300.0)
        self.assertEqual(result['volumes']['total_fill'], 2600.0)

        # Check costs
        self.assertEqual(result['costs']['total_cost'], 165000.0)

        # Check statistics
        stats = result['statistics']
        self.assertEqual(stats['site_count'], 3)
        self.assertEqual(stats['total_cost'], 165000.0)

    def test_get_cost_breakdown_by_site(self):
        """Test get_cost_breakdown_by_site returns detailed breakdown."""
        result = self.aggregator.get_cost_breakdown_by_site(self.sites)

        self.assertEqual(len(result), 3)

        # Check first site breakdown
        site1_breakdown = result[0]
        self.assertEqual(site1_breakdown['site_id'], 'WEA01')
        self.assertEqual(site1_breakdown['site_name'], 'Turbine 01')
        self.assertEqual(site1_breakdown['total_cost'], 50000.0)
        self.assertEqual(site1_breakdown['cost_excavation'], 10000.0)
        self.assertEqual(site1_breakdown['cost_transport'], 15000.0)
        self.assertEqual(site1_breakdown['cost_fill'], 8000.0)
        self.assertEqual(site1_breakdown['cost_gravel'], 12000.0)
        self.assertEqual(site1_breakdown['cost_compaction'], 5000.0)
        self.assertEqual(site1_breakdown['cost_saving'], 2000.0)
        self.assertEqual(site1_breakdown['total_volume_moved'], 1800.0)
        self.assertEqual(site1_breakdown['total_cut'], 1000.0)
        self.assertEqual(site1_breakdown['total_fill'], 800.0)
        self.assertIn('complexity_score', site1_breakdown)

    def test_get_volume_breakdown_by_site(self):
        """Test get_volume_breakdown_by_site returns detailed breakdown."""
        result = self.aggregator.get_volume_breakdown_by_site(self.sites)

        self.assertEqual(len(result), 3)

        # Check second site breakdown
        site2_breakdown = result[1]
        self.assertEqual(site2_breakdown['site_id'], 'WEA02')
        self.assertEqual(site2_breakdown['site_name'], 'Turbine 02')
        self.assertEqual(site2_breakdown['total_cut'], 1500.0)
        self.assertEqual(site2_breakdown['total_fill'], 1200.0)
        self.assertEqual(site2_breakdown['net_volume'], 300.0)
        self.assertEqual(site2_breakdown['total_volume_moved'], 2700.0)
        self.assertEqual(site2_breakdown['crane_height'], 105.0)
        self.assertEqual(site2_breakdown['fok'], 107.0)
        self.assertEqual(site2_breakdown['location_x'], 150.0)
        self.assertEqual(site2_breakdown['location_y'], 250.0)

    def test_get_ranked_sites_by_complexity(self):
        """Test get_ranked_sites sorts by complexity correctly."""
        result = self.aggregator.get_ranked_sites(self.sites, sort_by='complexity')

        # Site 2 should be first (highest volume and cost)
        self.assertEqual(result[0].site_id, 'WEA02')
        # Site 1 should be second
        self.assertEqual(result[1].site_id, 'WEA01')
        # Site 3 should be last (lowest complexity)
        self.assertEqual(result[2].site_id, 'WEA03')

    def test_get_ranked_sites_by_cost(self):
        """Test get_ranked_sites sorts by cost correctly."""
        result = self.aggregator.get_ranked_sites(self.sites, sort_by='cost')

        # Site 2: 75000, Site 1: 50000, Site 3: 40000
        self.assertEqual(result[0].site_id, 'WEA02')
        self.assertEqual(result[1].site_id, 'WEA01')
        self.assertEqual(result[2].site_id, 'WEA03')

    def test_get_ranked_sites_by_volume(self):
        """Test get_ranked_sites sorts by volume moved correctly."""
        result = self.aggregator.get_ranked_sites(self.sites, sort_by='volume')

        # Site 2: 2700, Site 1: 1800, Site 3: 1400
        self.assertEqual(result[0].site_id, 'WEA02')
        self.assertEqual(result[1].site_id, 'WEA01')
        self.assertEqual(result[2].site_id, 'WEA03')

    def test_get_ranked_sites_by_cut(self):
        """Test get_ranked_sites sorts by cut volume correctly."""
        result = self.aggregator.get_ranked_sites(self.sites, sort_by='cut')

        # Site 2: 1500, Site 1: 1000, Site 3: 800
        self.assertEqual(result[0].site_id, 'WEA02')
        self.assertEqual(result[1].site_id, 'WEA01')
        self.assertEqual(result[2].site_id, 'WEA03')

    def test_get_ranked_sites_invalid_criterion(self):
        """Test get_ranked_sites raises error for invalid criterion."""
        with self.assertRaises(ValueError) as context:
            self.aggregator.get_ranked_sites(self.sites, sort_by='invalid')

        self.assertIn('Invalid sort_by criterion', str(context.exception))
        self.assertIn('invalid', str(context.exception))

    def test_calculate_cost_distribution_empty_list(self):
        """Test calculate_cost_distribution with empty site list."""
        result = self.aggregator.calculate_cost_distribution([])

        self.assertEqual(result['pct_excavation'], 0.0)
        self.assertEqual(result['pct_transport'], 0.0)
        self.assertEqual(result['pct_fill'], 0.0)
        self.assertEqual(result['pct_gravel'], 0.0)
        self.assertEqual(result['pct_compaction'], 0.0)

    def test_calculate_cost_distribution_zero_total(self):
        """Test calculate_cost_distribution when total cost is zero."""
        # Create site with zero costs
        calc_result = MagicMock(spec=MultiSurfaceCalculationResult)
        calc_result.total_cut = 0.0
        calc_result.total_fill = 0.0
        calc_result.net_volume = 0.0
        calc_result.total_volume_moved = 0.0

        zero_costs = {
            'cost_total': 0.0,
            'cost_excavation': 0.0,
            'cost_transport': 0.0,
            'cost_fill': 0.0,
            'cost_gravel': 0.0,
            'cost_compaction': 0.0,
            'cost_saving': 0.0
        }

        site = SiteData(
            site_id='ZERO',
            site_name='Zero Site',
            location=QgsPointXY(0.0, 0.0),
            calculation_result=calc_result,
            costs=zero_costs
        )

        result = self.aggregator.calculate_cost_distribution([site])

        self.assertEqual(result['pct_excavation'], 0.0)
        self.assertEqual(result['pct_transport'], 0.0)
        self.assertEqual(result['pct_fill'], 0.0)
        self.assertEqual(result['pct_gravel'], 0.0)
        self.assertEqual(result['pct_compaction'], 0.0)

    def test_calculate_cost_distribution_multiple_sites(self):
        """Test calculate_cost_distribution calculates percentages correctly."""
        result = self.aggregator.calculate_cost_distribution(self.sites)

        # Total cost: 165000
        # Excavation: 33000 / 165000 = 20.0%
        # Transport: 49000 / 165000 = 29.7%
        # Fill: 26000 / 165000 = 15.8%
        # Gravel: 40000 / 165000 = 24.2%
        # Compaction: 17000 / 165000 = 10.3%

        self.assertAlmostEqual(result['pct_excavation'], 20.0, places=1)
        self.assertAlmostEqual(result['pct_transport'], 29.7, places=1)
        self.assertAlmostEqual(result['pct_fill'], 15.8, places=1)
        self.assertAlmostEqual(result['pct_gravel'], 24.2, places=1)
        self.assertAlmostEqual(result['pct_compaction'], 10.3, places=1)

        # Sum should be approximately 100%
        total_pct = sum(result.values())
        self.assertAlmostEqual(total_pct, 100.0, places=0)

    def test_get_cost_breakdown_empty_list(self):
        """Test get_cost_breakdown_by_site with empty site list."""
        result = self.aggregator.get_cost_breakdown_by_site([])

        self.assertEqual(len(result), 0)
        self.assertEqual(result, [])

    def test_get_volume_breakdown_empty_list(self):
        """Test get_volume_breakdown_by_site with empty site list."""
        result = self.aggregator.get_volume_breakdown_by_site([])

        self.assertEqual(len(result), 0)
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()
