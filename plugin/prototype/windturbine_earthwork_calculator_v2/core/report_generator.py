"""
Report Generator for Wind Turbine Earthwork Calculator V2

Generates HTML reports with results, maps, and profile images.

Author: Wind Energy Site Planning
Version: 2.0
"""

import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from qgis.core import (
    QgsGeometry,
    QgsRasterLayer,
    QgsPointXY
)

from ..utils.geometry_utils import get_centroid
from ..utils.logging_utils import get_plugin_logger


class ReportGenerator:
    """
    Generates professional HTML reports for wind turbine earthwork calculations.

    The report includes:
    - Project summary and parameters
    - Optimization results
    - Volume calculations
    - Terrain profile images
    - Site map (optional)
    """

    def __init__(self, results: Dict, polygon: QgsGeometry,
                 dem_layer: Optional[QgsRasterLayer] = None):
        """
        Initialize report generator.

        Args:
            results (Dict): Optimization results from EarthworkCalculator
            polygon (QgsGeometry): Platform polygon geometry
            dem_layer (QgsRasterLayer): DEM layer (optional, for map generation)
        """
        self.results = results
        self.polygon = polygon
        self.dem_layer = dem_layer
        self.logger = get_plugin_logger()

        # Get centroid coordinates
        centroid = get_centroid(polygon)
        self.centroid_x = centroid.x()
        self.centroid_y = centroid.y()

    def generate_html(self, output_path: str, profile_pngs: Optional[List[str]] = None,
                     config: Optional[Dict] = None):
        """
        Generate complete HTML report.

        Args:
            output_path (str): Path to save HTML file
            profile_pngs (List[str]): Paths to profile PNG files (optional)
            config (Dict): Configuration parameters (optional)
        """
        self.logger.info(f"Generating HTML report: {output_path}")

        # Generate HTML sections
        html_header = self._generate_header()
        html_summary = self._generate_summary()
        html_parameters = self._generate_parameters(config)
        html_results = self._generate_results()
        html_profiles = self._generate_profiles_section(profile_pngs)
        html_footer = self._generate_footer()

        # Combine all sections
        html_content = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wind Turbine Earthwork Calculation Report</title>
    {self._get_css_styles()}
</head>
<body>
    {html_header}
    <div class="container">
        {html_summary}
        {html_parameters}
        {html_results}
        {html_profiles}
    </div>
    {html_footer}
</body>
</html>
"""

        # Write to file
        Path(output_path).write_text(html_content, encoding='utf-8')
        self.logger.info(f"HTML report generated: {output_path}")

    def _get_css_styles(self) -> str:
        """Get CSS styles for the report."""
        return """
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5rem;
        }
        .header p {
            margin: 0.5rem 0 0 0;
            font-size: 1.1rem;
        }
        .container {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 1rem;
        }
        .section {
            background: white;
            margin: 2rem 0;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .section h2 {
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 0.5rem;
            margin-top: 0;
        }
        .highlight-box {
            background: #e8f5e9;
            border-left: 4px solid #4caf50;
            padding: 1rem;
            margin: 1rem 0;
        }
        .highlight-box.optimal {
            background: #fff3e0;
            border-left-color: #ff9800;
        }
        .highlight-value {
            font-size: 2rem;
            font-weight: bold;
            color: #ff9800;
            margin: 0.5rem 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }
        th, td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #667eea;
            color: white;
            font-weight: bold;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        .card {
            background: #f9f9f9;
            padding: 1rem;
            border-radius: 4px;
            border-left: 4px solid #667eea;
        }
        .card h3 {
            margin: 0 0 0.5rem 0;
            color: #667eea;
            font-size: 0.9rem;
            text-transform: uppercase;
        }
        .card .value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #333;
        }
        .card .unit {
            font-size: 0.9rem;
            color: #666;
        }
        .profile-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 2rem;
            margin: 2rem 0;
        }
        .profile-item img {
            width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .profile-item p {
            text-align: center;
            margin: 0.5rem 0;
            font-weight: bold;
            color: #667eea;
        }
        .footer {
            background: #333;
            color: white;
            text-align: center;
            padding: 1rem;
            margin-top: 2rem;
        }
        @media print {
            .section {
                page-break-inside: avoid;
            }
            body {
                background: white;
            }
        }
    </style>
"""

    def _generate_header(self) -> str:
        """Generate HTML header section."""
        return f"""
    <div class="header">
        <h1>🌬️ Wind Turbine Earthwork Calculation</h1>
        <p>Professional Platform Height Optimization Report</p>
        <p style="font-size: 0.9rem;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
"""

    def _generate_summary(self) -> str:
        """Generate summary section."""
        optimal_height = self.results.get('platform_height', 0)
        total_cut = self.results.get('total_cut', 0)
        total_fill = self.results.get('total_fill', 0)
        total_volume = self.results.get('total_volume_moved', 0)

        return f"""
    <div class="section">
        <h2>📊 Executive Summary</h2>

        <div class="highlight-box optimal">
            <h3 style="margin-top: 0;">Optimal Platform Height</h3>
            <div class="highlight-value">{optimal_height:.2f} m ü.NN</div>
            <p>This height minimizes total earthwork volume while maintaining structural requirements.</p>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Total Cut Volume</h3>
                <div class="value">{total_cut:,.0f}</div>
                <div class="unit">m³</div>
            </div>
            <div class="card">
                <h3>Total Fill Volume</h3>
                <div class="value">{total_fill:,.0f}</div>
                <div class="unit">m³</div>
            </div>
            <div class="card">
                <h3>Total Earthwork</h3>
                <div class="value">{total_volume:,.0f}</div>
                <div class="unit">m³</div>
            </div>
            <div class="card">
                <h3>Net Balance</h3>
                <div class="value">{self.results.get('net_volume', 0):,.0f}</div>
                <div class="unit">m³</div>
            </div>
        </div>
    </div>
"""

    def _generate_parameters(self, config: Optional[Dict] = None) -> str:
        """Generate parameters section."""
        if config is None:
            config = {}

        return f"""
    <div class="section">
        <h2>⚙️ Project Parameters</h2>

        <table>
            <tr>
                <th>Parameter</th>
                <th>Value</th>
                <th>Unit</th>
            </tr>
            <tr>
                <td>Site Location (Centroid)</td>
                <td>{self.centroid_x:.0f}, {self.centroid_y:.0f}</td>
                <td>EPSG:25832</td>
            </tr>
            <tr>
                <td>Platform Area</td>
                <td>{self.results.get('platform_area', 0):,.1f}</td>
                <td>m²</td>
            </tr>
            <tr>
                <td>Total Area (incl. Slope)</td>
                <td>{self.results.get('total_area', 0):,.1f}</td>
                <td>m²</td>
            </tr>
            <tr>
                <td>Slope Angle</td>
                <td>{config.get('slope_angle', 45.0):.1f}</td>
                <td>°</td>
            </tr>
            <tr>
                <td>Slope Width</td>
                <td>{self.results.get('slope_width', 0):.2f}</td>
                <td>m</td>
            </tr>
        </table>
    </div>
"""

    def _generate_results(self) -> str:
        """Generate detailed results section."""
        terrain_min = self.results.get('terrain_min', 0)
        terrain_max = self.results.get('terrain_max', 0)
        terrain_mean = self.results.get('terrain_mean', 0)
        terrain_range = self.results.get('terrain_range', 0)

        platform_cut = self.results.get('platform_cut', 0)
        platform_fill = self.results.get('platform_fill', 0)
        slope_cut = self.results.get('slope_cut', 0)
        slope_fill = self.results.get('slope_fill', 0)

        return f"""
    <div class="section">
        <h2>📈 Detailed Results</h2>

        <h3>Terrain Statistics</h3>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Unit</th>
            </tr>
            <tr>
                <td>Minimum Elevation</td>
                <td>{terrain_min:.2f}</td>
                <td>m ü.NN</td>
            </tr>
            <tr>
                <td>Maximum Elevation</td>
                <td>{terrain_max:.2f}</td>
                <td>m ü.NN</td>
            </tr>
            <tr>
                <td>Mean Elevation</td>
                <td>{terrain_mean:.2f}</td>
                <td>m ü.NN</td>
            </tr>
            <tr>
                <td>Elevation Range</td>
                <td>{terrain_range:.2f}</td>
                <td>m</td>
            </tr>
        </table>

        <h3>Volume Breakdown</h3>
        <table>
            <tr>
                <th>Component</th>
                <th>Cut Volume</th>
                <th>Fill Volume</th>
            </tr>
            <tr>
                <td>Platform</td>
                <td>{platform_cut:,.0f} m³</td>
                <td>{platform_fill:,.0f} m³</td>
            </tr>
            <tr>
                <td>Slope/Embankment</td>
                <td>{slope_cut:,.0f} m³</td>
                <td>{slope_fill:,.0f} m³</td>
            </tr>
            <tr style="font-weight: bold; background-color: #f0f0f0;">
                <td>Total</td>
                <td>{self.results.get('total_cut', 0):,.0f} m³</td>
                <td>{self.results.get('total_fill', 0):,.0f} m³</td>
            </tr>
        </table>
    </div>
"""

    def _generate_profiles_section(self, profile_pngs: Optional[List[str]] = None) -> str:
        """Generate terrain profiles section."""
        if not profile_pngs:
            return """
    <div class="section">
        <h2>📉 Terrain Profiles</h2>
        <p>No profile images available.</p>
    </div>
"""

        # Embed profile images
        profile_html = []
        for i, png_path in enumerate(profile_pngs):
            try:
                # Read and encode image
                with open(png_path, 'rb') as f:
                    img_data = base64.b64encode(f.read()).decode('utf-8')

                profile_name = Path(png_path).stem
                profile_html.append(f"""
            <div class="profile-item">
                <img src="data:image/png;base64,{img_data}" alt="{profile_name}">
                <p>{profile_name}</p>
            </div>
""")
            except Exception as e:
                self.logger.error(f"Failed to embed profile image {png_path}: {e}")

        if not profile_html:
            return """
    <div class="section">
        <h2>📉 Terrain Profiles</h2>
        <p>Failed to load profile images.</p>
    </div>
"""

        return f"""
    <div class="section">
        <h2>📉 Terrain Profiles</h2>
        <p>Cross-sections showing existing terrain, planned platform, and cut/fill areas.</p>
        <div class="profile-grid">
            {''.join(profile_html)}
        </div>
    </div>
"""

    def _generate_footer(self) -> str:
        """Generate HTML footer."""
        return f"""
    <div class="footer">
        <p>Wind Turbine Earthwork Calculator V2</p>
        <p>Generated with QGIS Processing Plugin</p>
        <p style="font-size: 0.8rem;">Report created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
"""
