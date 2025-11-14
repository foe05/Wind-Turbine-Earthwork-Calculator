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
    QgsPointXY,
    QgsMapSettings,
    QgsMapRendererCustomPainterJob,
    QgsVectorLayer,
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsProject
)
from qgis.PyQt.QtGui import QImage, QPainter, QColor
from qgis.PyQt.QtCore import QSize

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
                 dem_layer: Optional[QgsRasterLayer] = None,
                 platform_layer: Optional[QgsVectorLayer] = None,
                 profile_lines_layer: Optional[QgsVectorLayer] = None,
                 dxf_layer: Optional[QgsVectorLayer] = None):
        """
        Initialize report generator.

        Args:
            results (Dict): Optimization results from EarthworkCalculator
            polygon (QgsGeometry): Platform polygon geometry
            dem_layer (QgsRasterLayer): DEM layer (optional, for map generation)
            platform_layer (QgsVectorLayer): Platform polygon layer (optional)
            profile_lines_layer (QgsVectorLayer): Profile lines layer (optional)
            dxf_layer (QgsVectorLayer): DXF import layer (optional)
        """
        self.results = results
        self.polygon = polygon
        self.dem_layer = dem_layer
        self.platform_layer = platform_layer
        self.profile_lines_layer = profile_lines_layer
        self.dxf_layer = dxf_layer
        self.logger = get_plugin_logger()

        # Get centroid coordinates
        centroid = get_centroid(polygon)
        self.centroid_x = centroid.x()
        self.centroid_y = centroid.y()

    def generate_html(self, output_path: str, profile_pngs: Optional[List[str]] = None,
                     config: Optional[Dict] = None, profiles_dir: Optional[str] = None):
        """
        Generate complete HTML report.

        Args:
            output_path (str): Path to save HTML file
            profile_pngs (List[str]): Paths to profile PNG files (optional)
            config (Dict): Configuration parameters (optional)
            profiles_dir (str): Directory where profiles are saved (for overview map)
        """
        self.logger.info(f"Generating HTML report: {output_path}")

        # Generate overview map if layers are available
        overview_map_path = None
        if profiles_dir and (self.platform_layer or self.profile_lines_layer or self.dxf_layer):
            try:
                overview_map_path = str(Path(profiles_dir) / "overview_map.png")
                self._generate_overview_map(overview_map_path, scale=2000)
            except Exception as e:
                self.logger.error(f"Failed to generate overview map: {e}")

        # Generate HTML sections
        html_header = self._generate_header()
        html_summary = self._generate_summary()
        html_parameters = self._generate_parameters(config)
        html_results = self._generate_results()
        html_overview = self._generate_overview_section(overview_map_path)
        html_profiles = self._generate_profiles_section(profile_pngs)
        html_footer = self._generate_footer()

        # Combine all sections
        html_content = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Erdmassenberechnung Windenergieanlagen</title>
    {self._get_css_styles()}
</head>
<body>
    {html_header}
    <div class="container">
        {html_summary}
        {html_parameters}
        {html_results}
        {html_overview}
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
        <h1>🌬️ Erdmassenberechnung Windenergieanlagen</h1>
        <p>Professioneller Bericht zur Plattformhöhen-Optimierung</p>
        <p style="font-size: 0.9rem;">Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
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
        <h2>📊 Zusammenfassung</h2>

        <div class="highlight-box optimal">
            <h3 style="margin-top: 0;">Optimale Plattformhöhe</h3>
            <div class="highlight-value">{optimal_height:.2f} m ü.NN</div>
            <p>Diese Höhe minimiert das Gesamtvolumen der Erdbewegungen unter Einhaltung der baulichen Anforderungen.</p>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Abtrag (Schnitt)</h3>
                <div class="value">{total_cut:,.0f}</div>
                <div class="unit">m³</div>
            </div>
            <div class="card">
                <h3>Auftrag (Schüttung)</h3>
                <div class="value">{total_fill:,.0f}</div>
                <div class="unit">m³</div>
            </div>
            <div class="card">
                <h3>Gesamt Erdbewegungen</h3>
                <div class="value">{total_volume:,.0f}</div>
                <div class="unit">m³</div>
            </div>
            <div class="card">
                <h3>Netto-Bilanz</h3>
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
        <h2>⚙️ Projektparameter</h2>

        <table>
            <tr>
                <th>Parameter</th>
                <th>Wert</th>
                <th>Einheit</th>
            </tr>
            <tr>
                <td>Standortkoordinaten (Zentrum)</td>
                <td>{self.centroid_x:.0f}, {self.centroid_y:.0f}</td>
                <td>EPSG:25832</td>
            </tr>
            <tr>
                <td>Plattformfläche</td>
                <td>{self.results.get('platform_area', 0):,.1f}</td>
                <td>m²</td>
            </tr>
            <tr>
                <td>Gesamtfläche (inkl. Böschung)</td>
                <td>{self.results.get('total_area', 0):,.1f}</td>
                <td>m²</td>
            </tr>
            <tr>
                <td>Böschungswinkel</td>
                <td>{config.get('slope_angle', 45.0):.1f}</td>
                <td>°</td>
            </tr>
            <tr>
                <td>Böschungsbreite</td>
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
        <h2>📈 Detaillierte Ergebnisse</h2>

        <h3>Geländestatistik</h3>
        <table>
            <tr>
                <th>Kennwert</th>
                <th>Wert</th>
                <th>Einheit</th>
            </tr>
            <tr>
                <td>Minimale Geländehöhe</td>
                <td>{terrain_min:.2f}</td>
                <td>m ü.NN</td>
            </tr>
            <tr>
                <td>Maximale Geländehöhe</td>
                <td>{terrain_max:.2f}</td>
                <td>m ü.NN</td>
            </tr>
            <tr>
                <td>Mittlere Geländehöhe</td>
                <td>{terrain_mean:.2f}</td>
                <td>m ü.NN</td>
            </tr>
            <tr>
                <td>Höhenunterschied</td>
                <td>{terrain_range:.2f}</td>
                <td>m</td>
            </tr>
        </table>

        <h3>Volumenaufschlüsselung</h3>
        <table>
            <tr>
                <th>Komponente</th>
                <th>Abtrag</th>
                <th>Auftrag</th>
            </tr>
            <tr>
                <td>Plattform</td>
                <td>{platform_cut:,.0f} m³</td>
                <td>{platform_fill:,.0f} m³</td>
            </tr>
            <tr>
                <td>Böschung</td>
                <td>{slope_cut:,.0f} m³</td>
                <td>{slope_fill:,.0f} m³</td>
            </tr>
            <tr style="font-weight: bold; background-color: #f0f0f0;">
                <td>Gesamt</td>
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
        <h2>📉 Geländeschnitte</h2>
        <p>Keine Profilbilder verfügbar.</p>
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
        <h2>📉 Geländeschnitte</h2>
        <p>Fehler beim Laden der Profilbilder.</p>
    </div>
"""

        return f"""
    <div class="section">
        <h2>📉 Geländeschnitte</h2>
        <p>Querschnitte mit bestehendem Gelände, geplanter Plattform und Abtrag/Auftrag-Bereichen.</p>
        <div class="profile-grid">
            {''.join(profile_html)}
        </div>
    </div>
"""

    def _generate_overview_section(self, overview_map_path: Optional[str] = None) -> str:
        """Generate overview map section."""
        if not overview_map_path or not Path(overview_map_path).exists():
            return ""

        try:
            # Read and encode image
            with open(overview_map_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')

            return f"""
    <div class="section">
        <h2>🗺️ Lageplan</h2>
        <p>Übersichtskarte im Maßstab 1:2000 mit Plattform, Geländeschnitten und DXF-Import.</p>
        <div style="text-align: center;">
            <img src="data:image/png;base64,{img_data}" alt="Lageplan" style="max-width: 100%; border: 1px solid #ddd; border-radius: 4px;">
        </div>
    </div>
"""
        except Exception as e:
            self.logger.error(f"Failed to embed overview map: {e}")
            return ""

    def _generate_overview_map(self, output_path: str, scale: int = 2000):
        """
        Generate overview map using QGIS rendering.

        Args:
            output_path (str): Path to save map image
            scale (int): Map scale (default: 2000 for 1:2000)
        """
        # Calculate extent based on polygon with buffer
        polygon_extent = self.polygon.boundingBox()
        
        # Add 20% buffer
        buffer_size = max(polygon_extent.width(), polygon_extent.height()) * 0.2
        extent = QgsRectangle(
            polygon_extent.xMinimum() - buffer_size,
            polygon_extent.yMinimum() - buffer_size,
            polygon_extent.xMaximum() + buffer_size,
            polygon_extent.yMaximum() + buffer_size
        )

        # Map settings
        map_settings = QgsMapSettings()
        map_settings.setExtent(extent)
        
        # Get CRS from polygon or use EPSG:25832
        crs = QgsCoordinateReferenceSystem("EPSG:25832")
        if self.dem_layer:
            crs = self.dem_layer.crs()
        map_settings.setDestinationCrs(crs)
        
        # Calculate output size based on scale
        # Scale 1:2000 means 1mm on screen = 2000mm = 2m in reality
        # DPI 300 → 1 inch = 25.4mm → 1 pixel = 25.4/300 mm
        dpi = 300
        mm_per_pixel = 25.4 / dpi
        m_per_pixel = (mm_per_pixel / 1000) * scale
        
        width_pixels = int(extent.width() / m_per_pixel)
        height_pixels = int(extent.height() / m_per_pixel)
        
        # Limit size to reasonable values
        max_size = 4000
        if width_pixels > max_size or height_pixels > max_size:
            scale_factor = max_size / max(width_pixels, height_pixels)
            width_pixels = int(width_pixels * scale_factor)
            height_pixels = int(height_pixels * scale_factor)
        
        map_settings.setOutputSize(QSize(width_pixels, height_pixels))
        map_settings.setOutputDpi(dpi)

        # Build layer list combining memory layers and QGIS project layers
        # Layer order in list: LAST layer in list is rendered FIRST (background)
        # So we reverse the visual order
        layers = []
        project_layers = QgsProject.instance().mapLayers()
        
        # Helper function to find layer by name pattern
        def find_layer(name_patterns):
            """Find layer by name pattern (case-insensitive)"""
            for layer_id, layer in project_layers.items():
                layer_name = layer.name().lower()
                for pattern in name_patterns:
                    if pattern.lower() in layer_name:
                        return layer
            return None
        
        # Find background layers from project
        dgm_layer_project = find_layer(['dgm', 'höhenlinien', 'contour'])
        kataster_layer_project = find_layer(['kataster', 'flurstück'])
        luftbild_layer_project = find_layer(['luftbild', 'orthophoto', 'aerial'])
        
        # Add layers in reverse order (background first in rendering)
        # QGS renders the LAST item in the list as the BOTTOM layer
        
        # Top layers: Use memory layers (just calculated) with priority
        if self.profile_lines_layer:
            layers.append(self.profile_lines_layer)
            self.logger.info(f"Using memory layer for profile lines")
        
        if self.dxf_layer:
            layers.append(self.dxf_layer)
            self.logger.info(f"Using DXF layer: {self.dxf_layer.name()}")
        
        if self.platform_layer:
            layers.append(self.platform_layer)
            self.logger.info(f"Using memory layer for platform")
        
        # Background layers: Use project layers
        if dgm_layer_project:
            layers.append(dgm_layer_project)
            self.logger.info(f"Found DGM layer: {dgm_layer_project.name()}")
        
        if kataster_layer_project:
            layers.append(kataster_layer_project)
            self.logger.info(f"Found Kataster layer: {kataster_layer_project.name()}")
        
        if luftbild_layer_project:
            layers.append(luftbild_layer_project)
            self.logger.info(f"Found Luftbild layer: {luftbild_layer_project.name()}")
        
        map_settings.setLayers(layers)
        map_settings.setBackgroundColor(QColor(255, 255, 255))

        # Render map
        image = QImage(QSize(width_pixels, height_pixels), QImage.Format_ARGB32_Premultiplied)
        image.fill(QColor(255, 255, 255).rgb())
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        job = QgsMapRendererCustomPainterJob(map_settings, painter)
        job.start()
        job.waitForFinished()
        
        painter.end()
        
        # Save image
        image.save(output_path)
        self.logger.info(f"Overview map saved: {output_path} ({width_pixels}×{height_pixels})")

    def _generate_footer(self) -> str:
        """Generate HTML footer."""
        return f"""
    <div class="footer">
        <p>Erdmassenberechnung Windenergieanlagen V2</p>
        <p>Erstellt mit QGIS Processing Plugin</p>
        <p style="font-size: 0.8rem;">Bericht erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
    </div>
"""
