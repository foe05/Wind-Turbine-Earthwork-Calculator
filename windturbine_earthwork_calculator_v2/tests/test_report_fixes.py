
import unittest
from unittest.mock import MagicMock, patch
import os
import sys
from qgis.core import QgsGeometry, QgsPointXY

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from windturbine_earthwork_calculator_v2.core.surface_types import SurfaceType, SurfaceConfig, MultiSurfaceProject, HeightMode
from windturbine_earthwork_calculator_v2.core.multi_surface_calculator import MultiSurfaceCalculator

class TestReportFixes(unittest.TestCase):
    def setUp(self):
        # Create mock geometries
        self.crane_geom = QgsGeometry.fromWkt("POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))")
        self.foundation_geom = QgsGeometry.fromWkt("POLYGON((2 2, 8 2, 8 8, 2 8, 2 2))")
        self.boom_geom = QgsGeometry.fromWkt("POLYGON((10 2, 20 2, 20 8, 10 8, 10 2))")
        self.road_geom = QgsGeometry.fromWkt("POLYGON((0 4, -10 4, -10 6, 0 6, 0 4))")
        
        # Create mock configs
        self.crane_config = SurfaceConfig(
            surface_type=SurfaceType.CRANE_PAD,
            geometry=self.crane_geom,
            dxf_path="dummy.dxf",
            height_mode=HeightMode.OPTIMIZED
        )
        
        self.foundation_config = SurfaceConfig(
            surface_type=SurfaceType.FOUNDATION,
            geometry=self.foundation_geom,
            dxf_path="dummy.dxf",
            height_mode=HeightMode.FIXED,
            height_value=100.0
        )
        
        self.boom_config = SurfaceConfig(
            surface_type=SurfaceType.BOOM,
            geometry=self.boom_geom,
            dxf_path="dummy.dxf",
            height_mode=HeightMode.SLOPED,
            slope_longitudinal=2.0
        )
        
        self.road_config = SurfaceConfig(
            surface_type=SurfaceType.ROAD_ACCESS,
            geometry=self.road_geom,
            dxf_path="dummy.dxf",
            height_mode=HeightMode.SLOPED,
            slope_longitudinal=5.0
        )
        
        # Create project
        self.project = MultiSurfaceProject(
            crane_pad=self.crane_config,
            foundation=self.foundation_config,
            boom=self.boom_config,
            road_access=self.road_config,
            fok=100.0,
            foundation_depth=2.0,
            gravel_thickness=0.5
        )
        
        # Mock DEM layer
        self.dem_layer = MagicMock()
        self.dem_layer.rasterUnitsPerPixelX.return_value = 1.0
        self.dem_layer.rasterUnitsPerPixelY.return_value = 1.0
        
    def test_missing_dem_data_returns_area(self):
        """Test that missing DEM data still returns the correct area."""
        calculator = MultiSurfaceCalculator(self.dem_layer, self.project)
        
        # Mock sample_dem_in_polygon to return empty list (simulating no data)
        with patch.object(calculator, 'sample_dem_in_polygon', return_value=[]):
            with patch.object(calculator, 'sample_dem_with_positions', return_value=[]):
                # We also need to mock connection edges for boom and road
                calculator.boom_connection_edge = MagicMock()
                calculator.boom_connection_edge.isEmpty.return_value = False
                calculator.road_connection_edge = MagicMock()
                calculator.road_connection_edge.isEmpty.return_value = False
                
                # Calculate scenario
                result = calculator.calculate_scenario(crane_height=100.0)
                
                # Check foundation area
                foundation_res = result.surface_results[SurfaceType.FOUNDATION]
                self.assertAlmostEqual(foundation_res.platform_area, self.foundation_geom.area())
                
                # Check boom area
                boom_res = result.surface_results[SurfaceType.BOOM]
                self.assertAlmostEqual(boom_res.platform_area, self.boom_geom.area())
                
                # Check road area and additional data
                road_res = result.surface_results[SurfaceType.ROAD_ACCESS]
                self.assertAlmostEqual(road_res.platform_area, self.road_geom.area())
                self.assertIn('max_distance', road_res.additional_data)
                # Since we have no valid DEM data, max_distance will be 0.0, but key should exist
                self.assertEqual(road_res.additional_data['max_distance'], 0.0)
                
                # Check crane area
                crane_res = result.surface_results[SurfaceType.CRANE_PAD]
                self.assertAlmostEqual(crane_res.platform_area, self.crane_geom.area())

if __name__ == '__main__':
    unittest.main()
