"""
Multi-Site Report Generator for Wind Turbine Earthwork Calculator V2

Generates HTML comparison reports across multiple wind turbine sites showing
total project earthwork volumes, costs, and optimization recommendations.

Author: Wind Energy Site Planning
Version: 2.0.0
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from ..utils.logging_utils import get_plugin_logger


class MultiSiteReportGenerator:
    """
    Generates professional HTML reports comparing multiple wind turbine sites.

    The report includes:
    - Project-wide summary with total volumes and costs
    - Individual site comparisons
    - Sites ranked by earthwork complexity
    - Statistical analysis (avg, min, max volumes)
    - Cost breakdowns per site
    """

    def __init__(self, site_results: List[Dict], cost_config: Optional[Dict] = None):
        """
        Initialize multi-site report generator.

        Args:
            site_results (List[Dict]): List of site results, each containing:
                - site_id: Unique site identifier
                - site_name: Display name for the site
                - results: Optimization results from EarthworkCalculator
                - coordinates: (x, y) centroid coordinates
                - config: Site-specific configuration (optional)
            cost_config (Dict): Cost calculation parameters (optional):
                - cut_cost_per_m3: Cost per cubic meter of cut
                - fill_cost_per_m3: Cost per cubic meter of fill
                - gravel_cost_per_m3: Cost per cubic meter of gravel
                - transport_cost_per_m3_km: Transport cost per m3 per km
        """
        self.site_results = site_results
        self.cost_config = cost_config or {
            'cut_cost_per_m3': 5.0,
            'fill_cost_per_m3': 8.0,
            'gravel_cost_per_m3': 25.0,
            'transport_cost_per_m3_km': 0.5
        }
        self.logger = get_plugin_logger()

        # Calculate aggregated statistics
        self._calculate_statistics()

    def _calculate_statistics(self):
        """Calculate project-wide statistics from all sites."""
        if not self.site_results:
            self.total_cut = 0
            self.total_fill = 0
            self.total_volume_moved = 0
            self.total_net_volume = 0
            self.total_gravel = 0
            self.total_cost = 0
            self.avg_cut = 0
            self.avg_fill = 0
            self.min_cut = 0
            self.max_cut = 0
            self.min_fill = 0
            self.max_fill = 0
            return

        # Aggregate totals
        self.total_cut = 0
        self.total_fill = 0
        self.total_volume_moved = 0
        self.total_net_volume = 0
        self.total_gravel = 0
        self.total_cost = 0

        cut_values = []
        fill_values = []

        for site in self.site_results:
            results = site.get('results', {})

            cut = results.get('total_cut', 0)
            fill = results.get('total_fill', 0)
            net = results.get('net_volume', 0)
            gravel = results.get('gravel_fill_external', 0)

            self.total_cut += cut
            self.total_fill += fill
            self.total_volume_moved += (cut + fill)
            self.total_net_volume += net
            self.total_gravel += gravel

            cut_values.append(cut)
            fill_values.append(fill)

            # Calculate site cost
            site_cost = self._calculate_site_cost(results)
            site['calculated_cost'] = site_cost
            self.total_cost += site_cost

        # Calculate statistics
        if cut_values:
            self.avg_cut = sum(cut_values) / len(cut_values)
            self.min_cut = min(cut_values)
            self.max_cut = max(cut_values)
        else:
            self.avg_cut = 0
            self.min_cut = 0
            self.max_cut = 0

        if fill_values:
            self.avg_fill = sum(fill_values) / len(fill_values)
            self.min_fill = min(fill_values)
            self.max_fill = max(fill_values)
        else:
            self.avg_fill = 0
            self.min_fill = 0
            self.max_fill = 0

    def _calculate_site_cost(self, results: Dict) -> float:
        """
        Calculate estimated cost for a single site.

        Args:
            results (Dict): Site optimization results

        Returns:
            float: Estimated total cost in currency units
        """
        cut = results.get('total_cut', 0)
        fill = results.get('total_fill', 0)
        gravel = results.get('gravel_fill_external', 0)

        cut_cost = cut * self.cost_config['cut_cost_per_m3']
        fill_cost = fill * self.cost_config['fill_cost_per_m3']
        gravel_cost = gravel * self.cost_config['gravel_cost_per_m3']

        # Simplified transport cost (assume average distance)
        # In real implementation, this would use actual transport distances
        avg_transport_distance = 5.0  # km
        transport_cost = (cut + fill) * self.cost_config['transport_cost_per_m3_km'] * avg_transport_distance

        total_cost = cut_cost + fill_cost + gravel_cost + transport_cost

        return total_cost

    def generate_html(self, output_path: str, project_name: Optional[str] = None):
        """
        Generate complete multi-site HTML report.

        Args:
            output_path (str): Path to save HTML file
            project_name (str): Project name for the report header (optional)
        """
        self.logger.info(f"Generating multi-site HTML report: {output_path}")

        project_name = project_name or "Windpark-Projekt"

        # Generate HTML sections
        html_header = self._generate_header(project_name)
        html_summary = self._generate_summary()
        html_statistics = self._generate_statistics()
        html_site_ranking = self._generate_site_ranking()
        html_site_comparison = self._generate_site_comparison()
        html_cost_breakdown = self._generate_cost_breakdown()
        html_footer = self._generate_footer()

        # Combine all sections
        html_content = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Site Erdmassenvergleich - {project_name}</title>
    {self._get_css_styles()}
</head>
<body>
    {html_header}
    <div class="container">
        {html_summary}
        {html_statistics}
        {html_site_ranking}
        {html_site_comparison}
        {html_cost_breakdown}
    </div>
    {html_footer}
</body>
</html>
"""

        # Write to file
        Path(output_path).write_text(html_content, encoding='utf-8')
        self.logger.info(f"Multi-site HTML report generated: {output_path}")

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
            max-width: 1400px;
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
        .highlight-box.info {
            background: #e3f2fd;
            border-left-color: #2196f3;
        }
        .highlight-box.warning {
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
        tr.high-complexity {
            background-color: #ffebee;
        }
        tr.medium-complexity {
            background-color: #fff3e0;
        }
        tr.low-complexity {
            background-color: #e8f5e9;
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
        .rank-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.85rem;
            font-weight: bold;
            color: white;
        }
        .rank-1 { background-color: #d32f2f; }
        .rank-2 { background-color: #f57c00; }
        .rank-3 { background-color: #fbc02d; color: #333; }
        .rank-low { background-color: #388e3c; }
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

    def _generate_header(self, project_name: str) -> str:
        """Generate HTML header section."""
        return f"""
    <div class="header">
        <h1>🌬️ Multi-Site Erdmassenvergleich</h1>
        <p>{project_name}</p>
        <p style="font-size: 0.9rem;">Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
    </div>
"""

    def _generate_summary(self) -> str:
        """Generate project summary section."""
        num_sites = len(self.site_results)

        return f"""
    <div class="section">
        <h2>📊 Projektzusammenfassung</h2>

        <div class="highlight-box info">
            <h3 style="margin-top: 0;">Projektumfang</h3>
            <p><strong>{num_sites}</strong> Windenergieanlagen-Standorte</p>
            <p>Gesamtkosten (geschätzt): <strong>{self.total_cost:,.0f} €</strong></p>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Gesamt Abtrag</h3>
                <div class="value">{self.total_cut:,.0f}</div>
                <div class="unit">m³</div>
            </div>
            <div class="card">
                <h3>Gesamt Auftrag</h3>
                <div class="value">{self.total_fill:,.0f}</div>
                <div class="unit">m³</div>
            </div>
            <div class="card">
                <h3>Gesamt Erdbewegungen</h3>
                <div class="value">{self.total_volume_moved:,.0f}</div>
                <div class="unit">m³</div>
            </div>
            <div class="card">
                <h3>Netto-Bilanz</h3>
                <div class="value">{self.total_net_volume:,.0f}</div>
                <div class="unit">m³</div>
            </div>
            <div class="card">
                <h3>Externes Schottermaterial</h3>
                <div class="value">{self.total_gravel:,.0f}</div>
                <div class="unit">m³</div>
            </div>
            <div class="card">
                <h3>Durchschn. Kosten/Standort</h3>
                <div class="value">{self.total_cost / max(num_sites, 1):,.0f}</div>
                <div class="unit">€</div>
            </div>
        </div>
    </div>
"""

    def _generate_statistics(self) -> str:
        """Generate statistical analysis section."""
        return f"""
    <div class="section">
        <h2>📈 Statistische Auswertung</h2>

        <h3>Abtrag-Statistik</h3>
        <table>
            <tr>
                <th>Kennwert</th>
                <th>Wert</th>
                <th>Einheit</th>
            </tr>
            <tr>
                <td>Durchschnitt</td>
                <td>{self.avg_cut:,.0f}</td>
                <td>m³</td>
            </tr>
            <tr>
                <td>Minimum</td>
                <td>{self.min_cut:,.0f}</td>
                <td>m³</td>
            </tr>
            <tr>
                <td>Maximum</td>
                <td>{self.max_cut:,.0f}</td>
                <td>m³</td>
            </tr>
        </table>

        <h3>Auftrag-Statistik</h3>
        <table>
            <tr>
                <th>Kennwert</th>
                <th>Wert</th>
                <th>Einheit</th>
            </tr>
            <tr>
                <td>Durchschnitt</td>
                <td>{self.avg_fill:,.0f}</td>
                <td>m³</td>
            </tr>
            <tr>
                <td>Minimum</td>
                <td>{self.min_fill:,.0f}</td>
                <td>m³</td>
            </tr>
            <tr>
                <td>Maximum</td>
                <td>{self.max_fill:,.0f}</td>
                <td>m³</td>
            </tr>
        </table>
    </div>
"""

    def _generate_site_ranking(self) -> str:
        """Generate site ranking section by complexity/cost."""
        # Sort sites by total volume moved (complexity indicator)
        ranked_sites = sorted(
            self.site_results,
            key=lambda s: s['results'].get('total_cut', 0) + s['results'].get('total_fill', 0),
            reverse=True
        )

        # Generate ranking table rows
        ranking_rows = []
        for i, site in enumerate(ranked_sites, 1):
            site_name = site.get('site_name', site.get('site_id', f'Site {i}'))
            results = site.get('results', {})

            cut = results.get('total_cut', 0)
            fill = results.get('total_fill', 0)
            total_moved = cut + fill
            cost = site.get('calculated_cost', 0)
            crane_height = results.get('crane_height', results.get('platform_height', 0))

            # Determine complexity class
            if i <= 3:
                complexity_class = f'rank-{i}'
                complexity_label = f'Rang {i}'
            else:
                complexity_class = 'rank-low'
                complexity_label = f'Rang {i}'

            # Determine row class for coloring
            if total_moved > self.avg_cut + self.avg_fill:
                row_class = 'high-complexity'
            elif total_moved > (self.avg_cut + self.avg_fill) * 0.7:
                row_class = 'medium-complexity'
            else:
                row_class = 'low-complexity'

            ranking_rows.append(f"""
            <tr class="{row_class}">
                <td><span class="rank-badge {complexity_class}">{complexity_label}</span></td>
                <td><strong>{site_name}</strong></td>
                <td>{total_moved:,.0f} m³</td>
                <td>{cut:,.0f} m³</td>
                <td>{fill:,.0f} m³</td>
                <td>{crane_height:.2f} m</td>
                <td>{cost:,.0f} €</td>
            </tr>""")

        return f"""
    <div class="section">
        <h2>🏆 Standort-Rangliste nach Komplexität</h2>
        <p>Standorte sortiert nach Gesamterdbewegungen (höchste zuerst). Standorte mit höheren Erdbewegungen erfordern mehr Planungs- und Bauaufwand.</p>

        <table>
            <tr>
                <th>Rang</th>
                <th>Standort</th>
                <th>Gesamt Erdbewegungen</th>
                <th>Abtrag</th>
                <th>Auftrag</th>
                <th>Kranstellflächen-Höhe</th>
                <th>Kosten (geschätzt)</th>
            </tr>
            {''.join(ranking_rows)}
        </table>

        <div class="highlight-box warning" style="margin-top: 1rem;">
            <p><strong>Empfehlung:</strong> Die Top 3 Standorte mit der höchsten Komplexität sollten prioritär in der detaillierten Planung bearbeitet werden.</p>
        </div>
    </div>
"""

    def _generate_site_comparison(self) -> str:
        """Generate detailed site comparison table."""
        comparison_rows = []

        for site in self.site_results:
            site_name = site.get('site_name', site.get('site_id', 'Unknown'))
            results = site.get('results', {})
            coords = site.get('coordinates', (0, 0))

            crane_height = results.get('crane_height', results.get('platform_height', 0))
            cut = results.get('total_cut', 0)
            fill = results.get('total_fill', 0)
            net = results.get('net_volume', 0)
            gravel = results.get('gravel_fill_external', 0)

            terrain_min = results.get('terrain_min', 0)
            terrain_max = results.get('terrain_max', 0)
            terrain_mean = results.get('terrain_mean', 0)
            terrain_range = terrain_max - terrain_min

            platform_area = results.get('total_platform_area', results.get('platform_area', 0))

            comparison_rows.append(f"""
            <tr>
                <td><strong>{site_name}</strong></td>
                <td>{coords[0]:.0f}, {coords[1]:.0f}</td>
                <td>{crane_height:.2f} m</td>
                <td>{cut:,.0f} m³</td>
                <td>{fill:,.0f} m³</td>
                <td>{net:,.0f} m³</td>
                <td>{gravel:,.0f} m³</td>
                <td>{terrain_range:.2f} m</td>
                <td>{platform_area:,.1f} m²</td>
            </tr>""")

        return f"""
    <div class="section">
        <h2>🔍 Detaillierter Standortvergleich</h2>

        <table>
            <tr>
                <th>Standort</th>
                <th>Koordinaten</th>
                <th>Kranstellflächen-Höhe</th>
                <th>Abtrag</th>
                <th>Auftrag</th>
                <th>Netto</th>
                <th>Externes Schotter</th>
                <th>Höhenunterschied</th>
                <th>Plattformfläche</th>
            </tr>
            {''.join(comparison_rows)}
        </table>
    </div>
"""

    def _generate_cost_breakdown(self) -> str:
        """Generate cost breakdown section."""
        cost_rows = []

        for site in self.site_results:
            site_name = site.get('site_name', site.get('site_id', 'Unknown'))
            results = site.get('results', {})

            cut = results.get('total_cut', 0)
            fill = results.get('total_fill', 0)
            gravel = results.get('gravel_fill_external', 0)

            cut_cost = cut * self.cost_config['cut_cost_per_m3']
            fill_cost = fill * self.cost_config['fill_cost_per_m3']
            gravel_cost = gravel * self.cost_config['gravel_cost_per_m3']

            # Simplified transport cost
            avg_transport_distance = 5.0
            transport_cost = (cut + fill) * self.cost_config['transport_cost_per_m3_km'] * avg_transport_distance

            total_cost = cut_cost + fill_cost + gravel_cost + transport_cost

            cost_rows.append(f"""
            <tr>
                <td><strong>{site_name}</strong></td>
                <td>{cut_cost:,.0f} €</td>
                <td>{fill_cost:,.0f} €</td>
                <td>{gravel_cost:,.0f} €</td>
                <td>{transport_cost:,.0f} €</td>
                <td style="font-weight: bold;">{total_cost:,.0f} €</td>
            </tr>""")

        return f"""
    <div class="section">
        <h2>💰 Kostenaufschlüsselung</h2>

        <div class="highlight-box info">
            <h3 style="margin-top: 0;">Kostenkalkulations-Parameter</h3>
            <p>Abtrag: <strong>{self.cost_config['cut_cost_per_m3']:.2f} €/m³</strong> |
               Auftrag: <strong>{self.cost_config['fill_cost_per_m3']:.2f} €/m³</strong> |
               Schotter: <strong>{self.cost_config['gravel_cost_per_m3']:.2f} €/m³</strong> |
               Transport: <strong>{self.cost_config['transport_cost_per_m3_km']:.2f} €/m³·km</strong></p>
        </div>

        <table>
            <tr>
                <th>Standort</th>
                <th>Abtrag-Kosten</th>
                <th>Auftrag-Kosten</th>
                <th>Schotter-Kosten</th>
                <th>Transport-Kosten</th>
                <th>Gesamtkosten</th>
            </tr>
            {''.join(cost_rows)}
            <tr style="font-weight: bold; background-color: #f0f0f0;">
                <td>GESAMT</td>
                <td colspan="4"></td>
                <td>{self.total_cost:,.0f} €</td>
            </tr>
        </table>

        <p style="margin-top: 1rem; font-size: 0.9rem; color: #666;">
            <strong>Hinweis:</strong> Die Kosten sind Schätzungen basierend auf Standardwerten.
            Tatsächliche Kosten können je nach regionalen Gegebenheiten, Marktpreisen und Projektbedingungen variieren.
        </p>
    </div>
"""

    def _generate_footer(self) -> str:
        """Generate HTML footer."""
        return f"""
    <div class="footer">
        <p>Multi-Site Erdmassenvergleich V2.0.0</p>
        <p>Erstellt mit QGIS Processing Plugin</p>
        <p style="font-size: 0.8rem;">Bericht erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
    </div>
"""
